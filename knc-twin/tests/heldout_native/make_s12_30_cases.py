#!/usr/bin/env python3
"""Build the S12-30 gate cases (small sparse products) and the candidate batch from the gate's objects.

  make_s12_30_cases.py --objects .work/_shared/S12-30 --log .work/_shared/tmp/claude-s12-window8/s12-30-gate-hpcg.out
                       [--seed 1] [--batch-out ../../fixtures/batch]

Cases written next to this file:
  s12-30-small/   the gate's four "small" cases (CSR and HPCG-pointer layout, 13 and 27 nonzeros per row,
                  32 rows, uniformly random columns into a 32 KiB x) for the four timed builds: 16 variants.
                  Each kernel is the timed entry (`<build>_csr_scalar` or `<build>_hpcg_scalar`) with its
                  callee (`*_raw`) taken into the region from the object file, real layout, called from a
                  loop as the gate's sample loop does. Per-call cycles are the slope between 2 and 3 calls,
                  so the cache state is the steady state of repeated identical calls.

Input: the gate's own generator (the linear congruential generator and value ranges of
tools/s12_30_precision.c). The gate's generator state at this case depends on everything it ran before, so
the card's exact columns are not reproduced; --seed names the stream used here. The sensitivity to the seed
is reported by input_sensitivity.py. To bind the card's exact arrays, dump them in the gate and give them
as init.memory file blocks (references/input-format.md).
"""
import argparse
import json
import os
import re
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import from_binary  # noqa: E402
from knc_model.profile import load_profile  # noqa: E402
from knc_model.util import dump_json  # noqa: E402

CLOCK_HZ = 1238000000.0
SLOTS = [("donor-off", "compiler-donor.o", "donor"), ("knc-switch-off", "compiler-knc.o", "knc"),
         ("knc-switch-on", "compiler-enabled.o", "enabled"), ("knc-switch-off-two-nests", "compiler-twin.o", "twin")]
BATCH_SLOTS = SLOTS + [("knc-switch-on-contract-fast", "compiler-fast.o", "fast"), ("knc-switch-on-min4", "compiler-min4.o", "min4"),
                       ("knc-handwritten-policy", "compiler-manual.o", "manual")]
ROWS, NX = 32, 4096
MATRIX, OUT, ROWPTR, COL, COUNT, VAL, X, COLS_PTRS, VALS_PTRS, ROW_HEAP = (
    0x1000000, 0x1001000, 0x1002000, 0x1010000, 0x1003000, 0x1020000, 0x1040000, 0x1004000, 0x1005000, 0x1060000)
STACK_TOP = 0x7F0000000000


class Lcg(object):
    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def next(self):
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.s


def build_input(n, layout, seed):
    """compiler_case(label, layout, rows=32, n, nx=4096, pattern=0) of the gate, in its order of draws."""
    g = Lcg(seed)
    x = [float(int(g.next() % 9) - 4) for _ in range(NX)]
    cols, vals = [], []
    for i in range(ROWS):
        ci, vi = [], []
        for j in range(n):
            ci.append(g.next() % NX)
            vi.append(float(int(g.next() % 7) - 3))
        cols.append(ci)
        vals.append(vi)
    perm = list(range(ROWS))
    if layout == 1:
        for i in range(ROWS - 1, 0, -1):
            j = g.next() % (i + 1)
            perm[i], perm[j] = perm[j], perm[i]
    want = [float(sum(int(v) * int(x[c]) for c, v in zip(cols[i], vals[i]))) for i in range(ROWS)]
    mem = []
    warm = []

    def block(addr, key, values, level="l1"):
        mem.append({"addr": "0x%x" % addr, key: values})
        size = len(values) * {"i32": 4, "f64": 8, "u64": 8}[key]
        warm.append({"start": "0x%x" % (addr & ~63), "end": "0x%x" % (addr + size), "level": level})

    row = [i * n for i in range(ROWS + 1)]
    block(ROWPTR, "i32", row)
    block(COL, "i32", [c for r in cols for c in r])
    block(COUNT, "i32", [n] * ROWS)
    block(VAL, "f64", [v for r in vals for v in r])
    block(X, "f64", x, "l2")
    cols_p = [COL + 4 * n * i for i in range(ROWS)]
    vals_p = [VAL + 8 * n * i for i in range(ROWS)]
    if layout == 1:
        # each row's indices and values are separate 64-byte-aligned allocations, made in shuffled order
        heap = ROW_HEAP
        for r in range(ROWS):
            i = perm[r]
            cols_p[i] = heap
            block(heap, "i32", cols[i])
            heap += (4 * n + 16 + 63) // 64 * 64
            vals_p[i] = heap
            block(heap, "f64", vals[i])
            heap += (8 * n + 16 + 63) // 64 * 64
    block(COLS_PTRS, "u64", cols_p)
    block(VALS_PTRS, "u64", vals_p)
    m = bytearray(64)
    struct.pack_into("<i", m, 0, ROWS)
    struct.pack_into("<QQQQQQQ", m, 8, ROWPTR, COL, COUNT, VAL, X, COLS_PTRS, VALS_PTRS)
    mem.append({"addr": "0x%x" % MATRIX, "hex": bytes(m).hex()})
    warm.append({"start": "0x%x" % MATRIX, "end": "0x%x" % (MATRIX + 64), "level": "l1"})
    warm.append({"start": "0x%x" % OUT, "end": "0x%x" % (OUT + 8 * ROWS), "level": "l1"})
    warm.append({"start": "0x%x" % (STACK_TOP - 0x1000), "end": "0x%x" % (STACK_TOP + 0x100), "level": "l1"})
    return mem, warm, want


def make_kernel(obj, prefix, layout, n, seed, calls, objdump):
    entry = "%s_%s_scalar" % (prefix, "hpcg" if layout else "csr")
    raw_fn = "%s_%s_raw" % (prefix, "hpcg" if layout else "csr")
    conv = from_binary.Converter(obj, from_binary.disassemble(obj, tool=objdump))
    kernel, rows, summary = conv.convert(entry, with_callees=[raw_fn])
    mem, warm, want = build_input(n, layout, seed)
    driver = [{"id": "drv_a", "label": "drv_top", "op": "mov", "ops": ["rdi", {"imm": MATRIX}], "width": 64},
              {"id": "drv_o", "op": "mov", "ops": ["rsi", {"imm": OUT}], "width": 64},
              {"id": "drv_call", "op": "call", "ops": [entry]},
              {"id": "drv_sub", "op": "sub", "ops": ["r15", {"imm": 1}], "width": 64},
              {"id": "drv_jnz", "op": "jnz", "ops": ["drv_top"]},
              {"id": "drv_ret", "op": "ret", "ops": []}]
    kernel["streams"][0]["instructions"] = driver + kernel["streams"][0]["instructions"]
    kernel["init"]["registers"] = {"r15": calls}
    kernel["init"]["memory"] = kernel["init"]["memory"] + mem
    for s in kernel["provenance"]["unresolved_symbols"]:
        kernel["init"]["symbols"][s] = "0x1006000"     # the build's volatile two-nest switch: zero, as in the timed run
    kernel["scenario"] = {"memory": {"type": "line_tracking", "cold_level": "memory", "warm": warm}, "branch": {"type": "exit_mispredicted"}}
    kernel["expected"] = {"memory": [{"addr": "0x%x" % OUT, "f64": want}]}
    kernel["max_steps"] = 4000000
    kernel["unit_of_work"] = {"description": "one timed call of %s (32 rows, %d nonzeros)" % (entry, ROWS * n), "count": calls}
    kernel["provenance"]["source_file"] = ".work/_shared/S12-30/" + os.path.basename(obj)
    kernel["provenance"]["shape"] = "x87_sparse_rows_l1"
    kernel["provenance"]["input"] = {"generator": "tools/s12_30_precision.c compiler_case (LCG 1664525/1013904223)", "seed": seed,
                                     "note": "same generator and ranges as the card run, not its generator state"}
    return kernel, summary


def medians(log):
    out, case = {}, None
    with open(log) as f:
        for line in f:
            m = re.match(r"CASE (\S+) (\S+) n=(\d+) rows=(\d+)", line)
            if m:
                case = (m.group(1), m.group(2), int(m.group(3)), int(m.group(4)))
                continue
            m = re.match(r"TIME sample=\d+ (\S+) .*seconds_per_call=([\d.e+-]+)", line)
            if m and case:
                out.setdefault(case, {}).setdefault(m.group(1), []).append(float(m.group(2)))
    return {c: {s: statistics.median(v) for s, v in d.items()} for c, d in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--objdump", default=os.environ.get("KNC_OBJDUMP"))
    ap.add_argument("--batch-out")
    args = ap.parse_args()
    med = medians(args.log)
    out_dir = os.path.join(HERE, "s12-30-small")
    kdir = os.path.join(out_dir, "kernels")
    os.makedirs(kdir, exist_ok=True)
    variants, per_variant, seconds, groups = [], {}, {}, []
    for layout, lname in ((0, "CSR"), (1, "HPCG-pointers")):
        for n in (13, 27):
            tag = "%s%d" % ("csr" if layout == 0 else "ptr", n)
            names = []
            for slot, obj, prefix in SLOTS:
                kernel, summary = make_kernel(os.path.join(args.objects, obj), prefix, layout, n, args.seed, 3, args.objdump)
                kernel["name"] = "s12-30-%s-%s" % (tag, slot)
                kernel["description"] = "S12-30 gate, small %s n=%d rows=32, build %s: timed entry and its kernel from %s" % (lname, n, slot, obj)
                fn = "%s-%s.json" % (tag, slot)
                dump_json(kernel, os.path.join(kdir, fn))
                vname = "%s/%s" % (tag, slot)
                variants.append({"name": vname, "kernel": "kernels/" + fn})
                names.append(vname)
                sec = med[("small", lname, n, 32)][slot]
                seconds[vname] = sec
                per_variant[vname] = round(sec * CLOCK_HZ, 1)
            groups.append({"name": "S12-30 small %s n=%d builds" % (lname, n), "variants": names})
    case = {"schema": "knc-twin.heldout-case/3", "scale": "core", "kind": "compiled_kernel",
            "description": "S12-30 gate 'small' cases: sparse row products (x87 double) over 32 rows of 13 or 27 uniformly random columns into a 32 KiB x, "
                           "CSR and HPCG-pointer layouts, as the GCC 5.1.1 donor and three GCC-KNC builds compiled them. Whole timed call path from the object files.",
            "unit": "one timed call (32 rows)", "variants": variants,
            "slope": {"register": "r15", "units": [2, 3], "expected_same": True},
            "rank_groups": groups,
            "scenario_name": "steady state of repeated identical calls (slope between 2 and 3 calls), default memory sub-models, branches predicted from their history",
            "input_note": "the gate's generator and ranges with seed %d; the card's generator state is not reproduced" % args.seed}
    dump_json(case, os.path.join(out_dir, "case.json"))
    meas = {"schema": "knc-twin.heldout-measurement/1", "case": "s12-30-small",
            "source_log": ".work/_shared/tmp/claude-s12-window8/s12-30-gate-hpcg.out, CASE small CSR / small HPCG-pointers n=13 and n=27 rows=32, TIME samples 0-4",
            "source_doc": "docs/research/s12-30-phase1.md (branch s12/S12-30)",
            "unit": "median seconds per call over five samples, one core, one thread", "clock": "core cycles = seconds x 1.238e9",
            "used_to_set_parameters": False, "per_variant": per_variant, "seconds_per_call": seconds}
    dump_json(meas, os.path.join(out_dir, "measurement.json"))
    print("s12-30-small: %d variants" % len(variants))
    if args.batch_out:
        prof = load_profile("card-7120-measured")
        os.makedirs(args.batch_out, exist_ok=True)
        cands = []
        for slot, obj, prefix in BATCH_SLOTS:
            path = os.path.join(args.objects, obj)
            if not os.path.isfile(path):
                continue
            try:
                kernel, summary = make_kernel(path, prefix, 0, 13, args.seed, 3, args.objdump)
            except Exception as e:   # report, do not drop
                cands.append({"name": slot, "error": "%s: %s" % (type(e).__name__, e)})
                continue
            kernel["name"] = slot
            kernel["description"] = "%s: timed CSR entry and kernel from %s (S12-30 gate, small CSR n=13 rows=32); three calls" % (slot, obj)
            dump_json(kernel, os.path.join(args.batch_out, slot + ".json"))
            sec = med[("small", "CSR", 13, 32)].get(slot)
            cands.append({"name": slot, "kernel": slot + ".json", "shape": "x87_sparse_rows_l1", "coverage": summary["complete"],
                          "measured_seconds_per_call": sec})
        manifest = {"schema": "knc-twin.batch/1", "name": "S12-30 gate CSR variants (small CSR n=13 rows=32), three calls each",
                    "profile": "card-7120-measured", "frozen_profile_hash": prof.hash, "baseline": "knc-switch-off", "too_close_fraction": 0.05,
                    "queue_uncertain": True, "candidates": [c for c in cands if "error" not in c],
                    "not_convertible": [c for c in cands if "error" in c],
                    "notes": ["input: the gate's generator with seed %d; expected output exact (integer-valued data)" % args.seed,
                              "measured_seconds_per_call are the card's medians for the builds the gate timed (window 8)"]}
        dump_json(manifest, os.path.join(args.batch_out, "manifest.json"))
        print("batch: %d candidates, %d not convertible" % (len(manifest["candidates"]), len(manifest["not_convertible"])))
        for c in manifest["not_convertible"]:
            print("  ", c)


if __name__ == "__main__":
    main()
