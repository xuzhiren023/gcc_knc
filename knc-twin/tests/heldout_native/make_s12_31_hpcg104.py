#!/usr/bin/env python3
"""Build the memory-bound S12-31 case: HPCG ComputeSPMV_ref on the 104x104x104 problem (card window 3).

  make_s12_31_hpcg104.py --bench .work/_shared/S12-31/build/s12-31-bench --disassembly bench.dis
                         --log .work/_shared/S12-31/native.log
  make_s12_31_hpcg104.py --inputs-only        (re)create s12-31-hpcg-104/input/*.bin (not kept in git: 5 MB)

The card ran two passes over 1,124,864 rows (29,791,000 nonzeros, about 360 MB of matrix): far outside the
caches, so every array streams from memory. The twin runs the same compiled function on a window of interior
rows of the same matrix: the row-pointer, count and output arrays handed to the function start at row R0 of
the real problem, with the real column indices and the real x. The per-row cost is the slope between two
window lengths (4000 and 8000 rows), which starts cold and reaches the streaming steady state. The measured
figure is converted to the same unit (27 nonzeros). Nothing in the code is changed.
"""
import argparse
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))

NX = 104
R0 = 52 * NX * NX + 10 * NX         # first row of the window: an interior row in the middle plane
NMAX = 8000                         # rows of matrix data provided
VARIANTS = ["donor", "donor_pf", "knc", "knc_pf", "knc_noalign", "knc_skip7", "knc_nosched", "knc_nosched_noalign"]
CLOCK_HZ = 1238000000.0
TOTAL_NNZ = 29791000
A, XV, YV = 0x30000000, 0x30000100, 0x30000140
NNZ_AT, IND_PTRS, VAL_PTRS = 0x30010000, 0x30100000, 0x30200000
IND_ROWS, VAL_ROWS = 0x40000020, 0x50000020         # index_mod64 32, value_mod64 32 (the run's layout line)
X_AT, Y_AT = 0x60000010, 0x70000000                 # x_mod64 16
OUT_DIR = os.path.join(HERE, "s12-31-hpcg-104")


def row_entries(row):
    iz, iy, ix = row // (NX * NX), row // NX % NX, row % NX
    ci, cv = [], []
    for sz in (-1, 0, 1):
        if 0 <= iz + sz < NX:
            for sy in (-1, 0, 1):
                if 0 <= iy + sy < NX:
                    for sx in (-1, 0, 1):
                        if 0 <= ix + sx < NX:
                            col = row + sz * NX * NX + sy * NX + sx
                            cv.append(26.0 if col == row else -1.0)
                            ci.append(col)
    return ci, cv


def x_value(i):
    return 1.0 + 0.125 * (i % 7)


def x_range():
    lo = R0 - NX * NX - NX - 1
    hi = R0 + NMAX + NX * NX + NX + 2
    return lo, hi


def write_inputs():
    idir = os.path.join(OUT_DIR, "input")
    os.makedirs(idir, exist_ok=True)
    ind, val, cnt = bytearray(), bytearray(), bytearray()
    for r in range(R0, R0 + NMAX):
        ci, cv = row_entries(r)
        cnt.append(len(ci))
        ind += struct.pack("<%di" % len(ci), *ci).ljust(128, bytes(1))
        val += struct.pack("<%dd" % len(cv), *cv).ljust(224, bytes(1))
    lo, hi = x_range()
    files = {"nnz.bin": bytes(cnt),
             "ind_ptrs.bin": b"".join(struct.pack("<Q", IND_ROWS + 128 * i) for i in range(NMAX)),
             "val_ptrs.bin": b"".join(struct.pack("<Q", VAL_ROWS + 224 * i) for i in range(NMAX)),
             "ind_rows.bin": bytes(ind), "val_rows.bin": bytes(val),
             "x.bin": struct.pack("<%dd" % (hi - lo), *[x_value(i) for i in range(lo, hi)]),
             "y_4000.bin": struct.pack("<4000d", *expected_y(4000)), "y_8000.bin": struct.pack("<8000d", *expected_y(8000))}
    for name, data in files.items():
        with open(os.path.join(idir, name), "wb") as f:
            f.write(data)
    return files


def expected_y(n):
    out = []
    for r in range(R0, R0 + n):
        ci, cv = row_entries(r)
        out.append(sum(v * x_value(c) for c, v in zip(ci, cv)))   # dyadic values: exact in double and in extended precision
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench")
    ap.add_argument("--disassembly")
    ap.add_argument("--log")
    ap.add_argument("--inputs-only", action="store_true")
    args = ap.parse_args()
    write_inputs()
    if args.inputs_only:
        print("inputs written to %s" % os.path.join(OUT_DIR, "input"))
        return
    import from_binary
    from knc_model.util import dump_json
    with open(args.disassembly, "r", encoding="utf-8", errors="replace") as f:
        dis = f.read()
    med = {}
    with open(args.log) as f:
        for line in f:
            m = re.match(r"S12_31 hpcg_median spmv (\S+) ([\d.]+)", line)
            if m:
                med[m.group(1)] = float(m.group(2))
    kdir = os.path.join(OUT_DIR, "kernels")
    os.makedirs(kdir, exist_ok=True)
    lo, hi = x_range()
    a_struct = bytearray(0x60)
    struct.pack_into("<qq", a_struct, 0x10, NMAX, 27 * NMAX)
    struct.pack_into("<iii", a_struct, 0x20, NMAX, NX ** 3, 27 * NMAX)
    struct.pack_into("<Q", a_struct, 0x30, NNZ_AT)
    struct.pack_into("<QQ", a_struct, 0x40, IND_PTRS, VAL_PTRS)
    mem = [{"addr": "0x%x" % A, "hex": bytes(a_struct).hex()},
           {"addr": "0x%x" % XV, "hex": struct.pack("<iiQ", NX ** 3, 0, X_AT).hex()},      # x.values[col] with the real column numbers
           {"addr": "0x%x" % YV, "hex": struct.pack("<iiQ", NMAX, 0, Y_AT).hex()},
           {"addr": "0x%x" % NNZ_AT, "file": "../input/nnz.bin"}, {"addr": "0x%x" % IND_PTRS, "file": "../input/ind_ptrs.bin"},
           {"addr": "0x%x" % VAL_PTRS, "file": "../input/val_ptrs.bin"}, {"addr": "0x%x" % IND_ROWS, "file": "../input/ind_rows.bin"},
           {"addr": "0x%x" % VAL_ROWS, "file": "../input/val_rows.bin"}, {"addr": "0x%x" % (X_AT + 8 * lo), "file": "../input/x.bin"}]
    warm = [{"start": "0x%x" % a, "end": "0x%x" % (a + 0x40), "level": "l1"} for a in (A, XV, YV)]
    warm.append({"start": "0x%x" % (0x7F0000000000 - 0x1000), "end": "0x%x" % (0x7F0000000000 + 0x100), "level": "l1"})
    variants = []
    for v in VARIANTS:
        fn = v + "_spmv"
        conv = from_binary.Converter(args.bench, dis)
        kernel, rows, summary = conv.convert(fn)
        driver = [{"id": "drv_a", "op": "mov", "ops": ["rdi", {"imm": A}], "width": 64},
                  {"id": "drv_x", "op": "mov", "ops": ["rsi", {"imm": XV}], "width": 64},
                  {"id": "drv_y", "op": "mov", "ops": ["rdx", {"imm": YV}], "width": 64},
                  {"id": "drv_call", "op": "call", "ops": [fn]}, {"id": "drv_ret", "op": "ret", "ops": []}]
        kernel["streams"][0]["instructions"] = driver + kernel["streams"][0]["instructions"]
        kernel["init"]["registers"] = {}
        kernel["init"]["memory"] = kernel["init"]["memory"] + mem
        kernel["scenario"] = {"memory": {"type": "line_tracking", "cold_level": "memory", "warm": warm}, "branch": {"type": "exit_mispredicted"}}
        kernel["max_steps"] = 8000000
        kernel["memory_default"] = 0
        kernel["unit_of_work"] = {"description": "one interior row (27 nonzeros)", "count": NMAX}
        kernel["name"] = "s12-31-hpcg104-" + fn
        kernel["description"] = "HPCG 3.1 ComputeSPMV_ref (%s build) from the linked S12-31 bench binary on a window of interior rows of the 104-cubed problem (rows %d onward), streaming from memory" % (v, R0)
        kernel["provenance"]["source_file"] = ".work/_shared/S12-31/build/" + os.path.basename(args.bench)
        kernel["provenance"]["shape"] = "x87_sparse_rows_memory_stream"
        dump_json(kernel, os.path.join(kdir, fn + ".json"))
        variants.append({"name": v, "kernel": "kernels/%s.json" % fn})
    case = {"schema": "knc-twin.heldout-case/3", "scale": "core", "kind": "compiled_kernel",
            "description": "HPCG 3.1 ComputeSPMV_ref, eight builds, on the 104-cubed problem (memory-bound: 360 MB of matrix, every array streams). "
                           "A window of interior rows of the real matrix with the real x; per-row cost from the slope between 4000 and 8000 rows.",
            "unit": "27 nonzeros (one interior row)", "variants": variants,
            "prepare": "make_s12_31_hpcg104.py --inputs-only",
            "slope": {"memory_i32": ["0x%x" % (A + 0x20), "0x%x" % YV], "units": [4000, 8000],
                      "expected_by_units": {"4000": {"memory": [{"addr": "0x%x" % Y_AT, "file": "../input/y_4000.bin"}]},
                                            "8000": {"memory": [{"addr": "0x%x" % Y_AT, "file": "../input/y_8000.bin"}]}}},
            "rank_groups": [{"name": "HPCG 104-cubed SpMV builds", "variants": VARIANTS}],
            "scenario_name": "cold start, every array from memory, default memory sub-models (TLB with 4 KiB pages, L2 hardware prefetcher, memory service), branches predicted from their history",
            "window_note": "the measured figure is the whole problem (26.48 nonzeros per row on average, 6% boundary rows) converted to cycles per 27 nonzeros; the window holds interior rows only"}
    dump_json(case, os.path.join(OUT_DIR, "case.json"))
    meas = {"schema": "knc-twin.heldout-measurement/1", "case": "s12-31-hpcg-104",
            "source_log": ".work/_shared/S12-31/native.log (card window 3, 2026-11-15 02:57Z, nx=104): lines 'S12_31 hpcg_median spmv <variant> <seconds>' (two passes)",
            "source_doc": "docs/research/s12-31-hpcg.md, first diagnostic",
            "unit": "median seconds for two passes over 29,791,000 nonzeros, one core, one thread; converted to core cycles per 27 nonzeros",
            "clock": "core cycles = seconds x 1.238e9", "used_to_set_parameters": False,
            "per_variant": {v: round(med[v] * CLOCK_HZ / (2.0 * TOTAL_NNZ) * 27.0, 2) for v in VARIANTS},
            "seconds_two_passes": {v: med[v] for v in VARIANTS}}
    dump_json(meas, os.path.join(OUT_DIR, "measurement.json"))
    with open(os.path.join(OUT_DIR, ".gitignore"), "w", newline="\n") as f:
        f.write("input/\n")
    print("s12-31-hpcg-104: %d variants; measured cycles per 27 nonzeros: %s" % (len(variants), meas["per_variant"]))


if __name__ == "__main__":
    main()
