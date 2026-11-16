#!/usr/bin/env python3
"""Build the S12-31 compiled-code cases from the binary that ran on the card.

  make_s12_31_cases.py --bench .work/_shared/S12-31/build/s12-31-bench --disassembly bench.dis
                       --log .work/_shared/S12-31/native-mb.log [--log3 .work/_shared/S12-31/native.log]

Writes, next to this file:
  s12-31-microbench/   68 row-loop variants (padding styles and lengths, loop-top offsets, loop-body orders),
                       converted from the linked binary with their real addresses and NOP encodings
  s12-31-hpcg-toy/     HPCG 3.1 ComputeSPMV_ref and ComputeSYMGS_ref, eight builds each, on the 8x8x8 problem
                       the same run timed (27-point stencil, 512 rows, 10648 nonzeros), with the bench's
                       data layout and an independently computed expected result

The inputs are the bench's own (tools/s12_31_bench.cpp): nothing is sampled or simplified.
Nothing here reads a measurement to choose a model value; measurement.json only records the log.
"""
import argparse
import json
import os
import re
import struct
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import from_binary  # noqa: E402
from knc_model.util import dump_json  # noqa: E402

CLOCK_HZ = 1238000000.0
STACK_TOP = 0x7F0000000000
HPCG_VARIANTS = ["donor", "donor_pf", "knc", "knc_pf", "knc_noalign", "knc_skip7", "knc_nosched", "knc_nosched_noalign"]
# rows that fixed a model rule (see references/validation.md); every other row is held out
MB_CALIBRATION = {"gas_0": "pairing.x87_pairs_with_scalar", "adj_0": "pairing.x87_pairs_with_scalar", "one_15": "pairing.v_nop_pairs"}


def scenario(warm):
    return {"memory": {"type": "line_tracking", "cold_level": "memory", "warm": warm},
            "branch": {"type": "exit_mispredicted"}}


def stack_warm():
    return {"start": "0x%x" % (STACK_TOP - 0x1000), "end": "0x%x" % (STACK_TOP + 0x100), "level": "l1"}


# ------------------------------------------------------------------------------------------------- microbench
def microbench(conv_factory, out_dir, medians5, medians3):
    kdir = os.path.join(out_dir, "kernels")
    os.makedirs(kdir, exist_ok=True)
    xs = [0.5 + 0.03125 * j for j in range(32)]
    vals = [1.0 / (1 << (j % 5)) for j in range(27)]
    idx = [(j * 7) % 32 for j in range(27)]
    row = sum(Fraction(vals[j]) * Fraction(xs[idx[j]]) for j in range(27))
    mem = [{"addr": "0x100000", "f64": xs}, {"addr": "0x101000", "f64": vals}, {"addr": "0x102000", "i32": idx}]
    warm = [{"start": "0x100000", "end": "0x100100", "level": "l1"}, {"start": "0x101000", "end": "0x1010d8", "level": "l1"},
            {"start": "0x102000", "end": "0x10206c", "level": "l1"}, {"start": "0x103000", "end": "0x103008", "level": "l1"}, stack_warm()]
    variants = []
    for name in medians5:
        conv = conv_factory()
        overlay = {"init": {"registers": {"rdi": 8, "rsi": 27, "rdx": "0x100000", "rcx": "0x101000", "r8": "0x102000", "r9": "0x103000"},
                            "memory": mem},
                   "scenario": scenario(warm), "max_steps": 4000000,
                   "unit_of_work": {"description": "one 27-product row", "count": 8},
                   "expected": {"memory": [{"addr": "0x103000", "f64": [float(row * 8)]}]},
                   "provenance": {"shape": "x87_row_loop_l1"}}
        kernel, rows, summary = conv.convert("mb_" + name, init_overlay=overlay)
        kernel["name"] = "s12-31-mb-" + name
        kernel["description"] = "S12-31 microbench mb_%s from the linked bench binary (27 products per row, data in L1)" % name
        _portable(kernel)
        dump_json(kernel, os.path.join(kdir, name + ".json"))
        variants.append({"name": name, "kernel": "kernels/%s.json" % name, "calibrates": MB_CALIBRATION.get(name)})
    case = {"schema": "knc-twin.heldout-case/3", "scale": "core", "kind": "compiled_kernel",
            "description": "S12-31 SpMV-shaped x87 row loop (27 products per row, data in L1, one thread) in 68 variants: assembler padding of 0-15 bytes "
                           "before the loop top (gas_K), the same in single-byte NOPs (one_K) and in prefix-free long NOPs (pf_K), the loop top at other "
                           "offsets with no padding (mis_K), and loop-body orders (inc, adj, mid, mov_adj, mov_split). Converted from the binary that ran.",
            "unit": "one 27-product row (27 inner iterations plus the outer loop step)", "variants": variants,
            "slope": {"register": "rdi", "units": [4, 8], "expected_addr": "0x103000", "expected_f64_per_unit": float(row)},
            "rank_groups": [{"name": "S12-31 loop-body orders", "variants": ["gas_0", "inc_0", "adj_0", "mid_0", "mov_adj_0", "mov_split_0"]},
                            {"name": "S12-31 padding styles at 13-15 bytes", "variants": ["gas_13", "gas_14", "gas_15", "pf_13", "pf_14", "pf_15", "one_13", "one_14", "one_15", "gas_0"]}],
            "scenario_name": "arrays warm in L1, default memory sub-models, branches predicted from their history"}
    dump_json(case, os.path.join(out_dir, "case.json"))
    meas = {"schema": "knc-twin.heldout-measurement/1", "case": "s12-31-microbench",
            "source_log": ".work/_shared/S12-31/native-mb.log (card window 5, 2026-11-15 09:17-09:23Z): lines 'S12_31 mb_median <variant> ns_per_row'; "
                          "window 3 (.work/_shared/S12-31/native.log) is listed for the variants it has",
            "source_doc": "docs/research/s12-31-hpcg.md, first and second diagnostic",
            "unit": "median ns per row over five samples of 100000 rows, one core, one thread",
            "clock": "core cycles = ns x 1.238 GHz (card.clock_hz of card-7120-measured)",
            "used_to_set_parameters": "only the variants marked 'calibrates' in case.json (gas_0, adj_0, one_15); the others are held out",
            "per_variant": {n: round(v * CLOCK_HZ / 1e9, 1) for n, v in medians5.items()},
            "ns_per_row_window5": medians5, "ns_per_row_window3": medians3}
    dump_json(meas, os.path.join(out_dir, "measurement.json"))
    return len(variants)


# ------------------------------------------------------------------------------------------------- HPCG toy
def round_bits(x, bits):
    """Round a Fraction to `bits` significant bits, ties to even (no overflow or underflow in this use)."""
    if x == 0:
        return x
    s = -1 if x < 0 else 1
    a = abs(x)
    e = a.numerator.bit_length() - a.denominator.bit_length()
    if Fraction(2) ** e > a:
        e -= 1
    scale = Fraction(2) ** (bits - 1 - e)
    q = a * scale
    n = q.numerator // q.denominator
    r = q - n
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and n & 1):
        n += 1
    return s * Fraction(n) / scale


def build_problem(nx):
    n = nx ** 3
    idx, vals, nnz, diag = [], [], [], []
    for iz in range(nx):
        for iy in range(nx):
            for ix in range(nx):
                row = iz * nx * nx + iy * nx + ix
                ci, cv = [], []
                for sz in (-1, 0, 1):
                    if 0 <= iz + sz < nx:
                        for sy in (-1, 0, 1):
                            if 0 <= iy + sy < nx:
                                for sx in (-1, 0, 1):
                                    if 0 <= ix + sx < nx:
                                        col = row + sz * nx * nx + sy * nx + sx
                                        if col == row:
                                            diag.append(len(ci))
                                            cv.append(26.0)
                                        else:
                                            cv.append(-1.0)
                                        ci.append(col)
                idx.append(ci)
                vals.append(cv)
                nnz.append(len(ci))
    b = [26.0 - (c - 1) for c in nnz]
    xexact = [1.0 + 0.125 * (i % 7) for i in range(n)]
    return n, idx, vals, nnz, diag, b, xexact


def oracle_spmv(n, idx, vals, x):
    out = []
    for i in range(n):
        s = Fraction(0)
        for c, v in zip(idx[i], vals[i]):
            s = round_bits(s + round_bits(Fraction(v) * Fraction(x[c]), 64), 64)
        out.append(float(round_bits(s, 53)))
    return out


def oracle_symgs(n, idx, vals, diag, r):
    x = [Fraction(0)] * n
    for order in (range(n), range(n - 1, -1, -1)):
        for i in order:
            d = Fraction(vals[i][diag[i]])
            s = Fraction(r[i])
            for c, v in zip(idx[i], vals[i]):
                s = round_bits(s - round_bits(Fraction(v) * x[c], 64), 64)
            s = round_bits(s + round_bits(x[i] * d, 64), 64)
            x[i] = round_bits(round_bits(s / d, 64), 53)
    return [float(v) for v in x]


A, XV, YV, BV, SV = 0x30000000, 0x30000100, 0x30000140, 0x30000180, 0x300001C0
NNZ_AT, IND_PTRS, VAL_PTRS, DIAG_PTRS = 0x30010000, 0x30020000, 0x30030000, 0x30040000
IND_ROWS, VAL_ROWS = 0x31000030, 0x32000030
X_AT, Y_AT, B_AT, S_AT = 0x33000000, 0x33010000, 0x33020000, 0x33030000


def hpcg_toy(conv_factory, out_dir, medians, nx=8):
    kdir = os.path.join(out_dir, "kernels")
    idir = os.path.join(out_dir, "input")
    os.makedirs(kdir, exist_ok=True)
    os.makedirs(idir, exist_ok=True)
    n, idx, vals, nnz, diag, b, xexact = build_problem(nx)
    total = sum(nnz)

    def put(name, data):
        with open(os.path.join(idir, name), "wb") as f:
            f.write(data)
        return len(data)

    a_struct = bytearray(0x60)
    struct.pack_into("<qq", a_struct, 0x10, n, total)
    struct.pack_into("<iii", a_struct, 0x20, n, n, total)
    struct.pack_into("<Q", a_struct, 0x30, NNZ_AT)
    struct.pack_into("<QQQ", a_struct, 0x40, IND_PTRS, VAL_PTRS, DIAG_PTRS)
    sizes = {}
    sizes["A.bin"] = put("A.bin", bytes(a_struct))
    for nm, base in (("x", X_AT), ("y", Y_AT), ("b", B_AT), ("s", S_AT)):
        sizes["vec_%s.bin" % nm] = put("vec_%s.bin" % nm, struct.pack("<iiQ", n, 0, base))
    sizes["nnz.bin"] = put("nnz.bin", bytes(nnz))
    sizes["ind_ptrs.bin"] = put("ind_ptrs.bin", b"".join(struct.pack("<Q", IND_ROWS + 128 * i) for i in range(n)))
    sizes["val_ptrs.bin"] = put("val_ptrs.bin", b"".join(struct.pack("<Q", VAL_ROWS + 224 * i) for i in range(n)))
    sizes["diag_ptrs.bin"] = put("diag_ptrs.bin", b"".join(struct.pack("<Q", VAL_ROWS + 224 * i + 8 * diag[i]) for i in range(n)))
    sizes["ind_rows.bin"] = put("ind_rows.bin", b"".join(struct.pack("<%di" % len(r), *r).ljust(128, bytes(1)) for r in idx))
    sizes["val_rows.bin"] = put("val_rows.bin", b"".join(struct.pack("<%dd" % len(r), *r).ljust(224, bytes(1)) for r in vals))
    sizes["xexact.bin"] = put("xexact.bin", struct.pack("<%dd" % n, *xexact))
    sizes["b.bin"] = put("b.bin", struct.pack("<%dd" % n, *b))
    sizes["zeros.bin"] = put("zeros.bin", bytes(8 * n))
    layout_mem = [(A, "A.bin"), (XV, "vec_x.bin"), (YV, "vec_y.bin"), (BV, "vec_b.bin"), (SV, "vec_s.bin"), (NNZ_AT, "nnz.bin"),
                  (IND_PTRS, "ind_ptrs.bin"), (VAL_PTRS, "val_ptrs.bin"), (DIAG_PTRS, "diag_ptrs.bin"), (IND_ROWS, "ind_rows.bin"),
                  (VAL_ROWS, "val_rows.bin"), (X_AT, "xexact.bin"), (B_AT, "b.bin"), (Y_AT, "zeros.bin"), (S_AT, "zeros.bin")]
    mem = [{"addr": "0x%x" % a, "file": "../input/" + f} for a, f in layout_mem]
    # every array was touched by the previous variant's run: resident in the 512 KiB L2; the output vector was just cleared (L1)
    warm = [{"start": "0x%x" % (a & ~63), "end": "0x%x" % (a + sizes[f]), "level": "l2"} for a, f in layout_mem if a not in (Y_AT, S_AT)]
    warm += [{"start": "0x%x" % Y_AT, "end": "0x%x" % (Y_AT + 8 * n), "level": "l1"}, {"start": "0x%x" % S_AT, "end": "0x%x" % (S_AT + 8 * n), "level": "l1"}, stack_warm()]
    want_spmv = oracle_spmv(n, idx, vals, xexact)
    want_symgs = oracle_symgs(n, idx, vals, diag, b)
    variants = []
    for kern in ("spmv", "symgs"):
        for v in HPCG_VARIANTS:
            fn = "%s_%s" % (v, kern)
            conv = conv_factory()
            kernel, rows, summary = conv.convert(fn)
            if kern == "spmv":
                args = [("rdi", A), ("rsi", XV), ("rdx", YV)]
                reps, expected, unit = 2, {"memory": [{"addr": "0x%x" % Y_AT, "f64": want_spmv}]}, "two ComputeSPMV_ref passes"
            else:
                args = [("rdi", A), ("rsi", BV), ("rdx", SV)]
                reps, expected, unit = 1, {"memory": [{"addr": "0x%x" % S_AT, "f64": want_symgs}]}, "one ComputeSYMGS_ref call (forward and backward sweep)"
            driver = []
            for r in range(reps):
                for reg, val in args:
                    driver.append({"id": "drv%d_%s" % (r, reg), "op": "mov", "ops": [reg, {"imm": val}], "width": 64})
                driver.append({"id": "drv%d_call" % r, "op": "call", "ops": [fn]})
            driver.append({"id": "drv_ret", "op": "ret", "ops": []})
            kernel["streams"][0]["instructions"] = driver + kernel["streams"][0]["instructions"]
            kernel["init"]["registers"] = {}
            kernel["init"]["memory"] = kernel["init"]["memory"] + mem
            kernel["scenario"] = scenario(warm)
            kernel["expected"] = expected
            kernel["max_steps"] = 4000000
            kernel["unit_of_work"] = {"description": unit, "count": 1}
            kernel["name"] = "s12-31-hpcg%d-%s" % (nx, fn)
            kernel["description"] = "HPCG 3.1 %s (%s build) from the linked S12-31 bench binary on the %dx%dx%d problem the same run timed; a driver calls it %d time(s) as the bench does" % (
                "ComputeSPMV_ref" if kern == "spmv" else "ComputeSYMGS_ref", v, nx, nx, nx, reps)
            kernel["provenance"]["shape"] = "x87_sparse_rows_l2"
            _portable(kernel)
            dump_json(kernel, os.path.join(kdir, fn + ".json"))
            variants.append({"name": "%s/%s" % (kern, v), "kernel": "kernels/%s.json" % fn})
    case = {"schema": "knc-twin.heldout-case/3", "scale": "core", "kind": "compiled_kernel",
            "description": "HPCG 3.1 ComputeSPMV_ref and ComputeSYMGS_ref as GCC-KNC and the GCC 5.1.1 donor compiled them (eight builds: today's code, "
                           "prefix-free NOPs, no loop alignment, bounded skip, no second scheduling pass), whole functions from the linked bench binary, "
                           "on the 8x8x8 27-point problem (512 rows, %d nonzeros, about 190 KiB: L2-resident) with the bench's data layout. "
                           "Expected y and x computed independently in exact arithmetic with x87 rounding." % total,
            "unit": "the bench's timed call (SpMV: two passes; SymGS: one call)", "variants": variants,
            "rank_groups": [{"name": "HPCG toy SpMV builds", "variants": ["spmv/" + v for v in HPCG_VARIANTS]},
                            {"name": "HPCG toy SymGS builds", "variants": ["symgs/" + v for v in HPCG_VARIANTS]}],
            "scenario_name": "arrays resident in L2 (touched by the preceding run), output vector in L1, default memory sub-models, branches predicted from their history"}
    dump_json(case, os.path.join(out_dir, "case.json"))
    meas = {"schema": "knc-twin.heldout-measurement/1", "case": "s12-31-hpcg-toy",
            "source_log": ".work/_shared/S12-31/native-mb.log (card window 5, 2026-11-15 09:17-09:23Z, argument nx=8): lines 'S12_31 hpcg_median <kernel> <variant> <seconds>'",
            "source_doc": "docs/research/s12-31-hpcg.md, second diagnostic (the note sets this 8x8x8 part aside as a toy; it is a cache-resident measurement of the real kernels)",
            "unit": "median seconds over five alternating samples, one core, one thread; SpMV times two passes",
            "clock": "core cycles = seconds x 1.238e9", "used_to_set_parameters": False,
            "per_variant": {"%s/%s" % (k, v): round(medians[(k, v)] * CLOCK_HZ, 0) for k in ("spmv", "symgs") for v in HPCG_VARIANTS},
            "seconds": {"%s/%s" % (k, v): medians[(k, v)] for k in ("spmv", "symgs") for v in HPCG_VARIANTS}}
    dump_json(meas, os.path.join(out_dir, "measurement.json"))
    return len(variants)


def _portable(kernel):
    p = kernel["provenance"]
    p["source_file"] = ".work/_shared/S12-31/build/" + os.path.basename(p["source_file"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--disassembly", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--log3")
    args = ap.parse_args()
    with open(args.disassembly, "r", encoding="utf-8", errors="replace") as f:
        dis = f.read()

    def factory():
        return from_binary.Converter(args.bench, dis)

    def medians_of(path, pat):
        out = {}
        with open(path) as f:
            for line in f:
                m = re.match(pat, line)
                if m:
                    out[m.groups()[:-1] if len(m.groups()) > 2 else m.group(1)] = float(m.groups()[-1])
        return out

    mb5 = medians_of(args.log, r"S12_31 mb_median (\S+) ns_per_row ([\d.]+)")
    mb3 = medians_of(args.log3, r"S12_31 mb_median (\S+) ns_per_row ([\d.]+)") if args.log3 else {}
    hp = medians_of(args.log, r"S12_31 hpcg_median (\S+) (\S+) ([\d.]+)")
    n1 = microbench(factory, os.path.join(HERE, "s12-31-microbench"), mb5, mb3)
    n2 = hpcg_toy(factory, os.path.join(HERE, "s12-31-hpcg-toy"), hp)
    print("s12-31-microbench: %d variants; s12-31-hpcg-toy: %d variants" % (n1, n2))


if __name__ == "__main__":
    main()
