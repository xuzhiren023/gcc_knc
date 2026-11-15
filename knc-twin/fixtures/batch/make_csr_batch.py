#!/usr/bin/env python3
"""Build the real candidate batch: the S12-30 gate's CSR SpMV kernel as GCC-KNC and the donor
compiler emitted it in seven variants, on one deterministic CSR input, with the expected result
computed independently (integer-valued data, so no rounding question).

  python make_csr_batch.py --asm-dir <dir with compiler-*.s> --out <dir> [--profile card-7120-measured]

Writes <out>/csr_input.json, <out>/<variant>.json kernels (via the adapter), <out>/manifest.json
(frozen to the profile hash) and <out>/measured.json (the card's seconds per call for the same
case from the S12-30 gate log, for the comparison in references/validation.md).

Signature recovered from the assembly: csr_raw(int nrows=edi, const int *rowptr=rsi,
const int *colidx=rdx, const double *values=rcx, const double *x=r8, double *y=r9).
"""
import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import from_gcc_s  # noqa: E402
from knc_model.profile import load_profile  # noqa: E402
from knc_model.util import dump_json  # noqa: E402

VARIANTS = [
    ("donor-off", "compiler-donor.s", "donor_csr_raw", "GCC 5.1.1 donor, -O2"),
    ("knc-switch-off", "compiler-knc.s", "knc_csr_raw", "GCC-KNC -O2 -march=knc, S12-30 switch off"),
    ("knc-switch-on", "compiler-enabled.s", "enabled_csr_raw", "GCC-KNC, S12-30 switch on"),
    ("knc-switch-on-contract-fast", "compiler-fast.s", "fast_csr_raw", "GCC-KNC, switch on, contraction fast"),
    ("knc-switch-on-min4", "compiler-min4.s", "min4_csr_raw", "GCC-KNC, switch on, min4 policy"),
    ("knc-handwritten-policy", "compiler-manual.s", "manual_csr_raw", "GCC-KNC, hand-written policy"),
    ("knc-switch-off-two-nests", "compiler-twin.s", "twin_csr_raw", "GCC-KNC, switch off, two nests"),
]
# S12-30 gate, window 8 (.work/_shared/tmp/claude-s12-window8/s12-30-gate-hpcg.out), case small CSR n=13 rows=32,
# median of 5 samples, seconds per call; TSC 1.232 GHz on this card (ticks = seconds x 1.232e9)
MEASURED_SECONDS_PER_CALL = {"donor-off": 6.749e-6, "knc-switch-off": 6.853e-6, "knc-switch-on": 6.850e-6, "knc-switch-off-two-nests": 6.690e-6}

ROWS, NNZ_PER_ROW, NCOLS = 32, 13, 4096
ROWPTR, COLIDX, VALUES, X, Y, STACK = 0x1000000, 0x1001000, 0x1010000, 0x1020000, 0x1030000, 0x7f00000


def build_input(seed=12345):
    rng = random.Random(seed)
    rowptr = [0]
    colidx = []
    values = []
    for r in range(ROWS):
        cols = sorted(rng.sample(range(NCOLS), NNZ_PER_ROW))
        colidx += cols
        values += [float(rng.randint(-8, 8)) for _ in cols]
        rowptr.append(len(colidx))
    x = [float(rng.randint(-4, 4)) for _ in range(NCOLS)]
    y = []
    for r in range(ROWS):
        s = 0
        for k in range(rowptr[r], rowptr[r + 1]):
            s += int(values[k]) * int(x[colidx[k]])
        y.append(float(s))
    return rowptr, colidx, values, x, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asm-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default="card-7120-measured")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    prof = load_profile(args.profile)
    rowptr, colidx, values, x, y = build_input()
    init = {"unit_of_work": {"description": "one csr_raw call: 32 rows, 13 nonzeros each (S12-30 small CSR n=13)", "count": 1},
            "memory_default": 0,
            "init": {"registers": {"rdi": ROWS, "rsi": "0x%x" % ROWPTR, "rdx": "0x%x" % COLIDX, "rcx": "0x%x" % VALUES, "r8": "0x%x" % X, "r9": "0x%x" % Y,
                                   "rsp": "0x%x" % STACK, "rbp": "0x%x" % STACK},
                     "memory": [{"addr": "0x%x" % ROWPTR, "i32": rowptr}, {"addr": "0x%x" % COLIDX, "i32": colidx},
                                {"addr": "0x%x" % VALUES, "f64": values}, {"addr": "0x%x" % X, "f64": x}]},
            "expected": {"memory": [{"addr": "0x%x" % Y, "f64": y}], "registers": {"0": {"x87_depth": 0}}},
            "scenario": {"memory": {"type": "line_tracking", "cold_level": "memory", "tlb": "modeled", "hardware_prefetcher": "modeled", "memory_service": "modeled",
                                    "warm": [{"start": "0x%x" % ROWPTR, "end": "0x%x" % (ROWPTR + 4 * len(rowptr)), "level": "l1"},
                                             {"start": "0x%x" % COLIDX, "end": "0x%x" % (COLIDX + 4 * len(colidx)), "level": "l1"},
                                             {"start": "0x%x" % VALUES, "end": "0x%x" % (VALUES + 8 * len(values)), "level": "l1"},
                                             {"start": "0x%x" % X, "end": "0x%x" % (X + 8 * len(x)), "level": "l1"}]},
                         "branch": {"type": "all_predicted"}},
            "provenance": {"shape": "x87_csr_spmv_rows_l1_resident"}}
    dump_json(init, os.path.join(args.out, "csr_input.json"))
    cands = []
    for name, fn, sym, desc in VARIANTS:
        path = os.path.join(args.asm_dir, fn)
        try:
            kernel, rows, summary = from_gcc_s.convert(path, sym, init_overlay=init, profile=prof)
        except Exception as e:  # report, do not drop
            cands.append({"name": name, "kernel": name + ".json", "error": str(e), "description": desc})
            continue
        kernel["name"] = name
        kernel["description"] = "%s: %s from %s (S12-30 gate variant); input csr_input.json" % (name, sym, fn)
        kernel["provenance"]["shape"] = "x87_csr_spmv_rows_l1_resident"
        kernel["provenance"]["measured_seconds_per_call"] = MEASURED_SECONDS_PER_CALL.get(name)
        kernel["provenance"]["source_variant"] = {"file": fn, "symbol": sym, "description": desc}
        dump_json(kernel, os.path.join(args.out, name + ".json"))
        cands.append({"name": name, "kernel": name + ".json", "shape": "x87_csr_spmv_rows_l1_resident", "coverage": summary["complete"], "description": desc})
    manifest = {"schema": "knc-twin.batch/1", "name": "S12-30 gate CSR SpMV variants (small CSR n=13 rows=32), warm L1, one call",
                "profile": args.profile, "frozen_profile_hash": prof.hash, "baseline": "knc-switch-off", "too_close_fraction": 0.05,
                "queue_uncertain": True, "candidates": [c for c in cands if "error" not in c],
                "not_convertible": [c for c in cands if "error" in c],
                "measured_seconds_per_call": MEASURED_SECONDS_PER_CALL,
                "notes": ["the input is deterministic (seed 12345) integer-valued data so the expected y is exact under any accumulation order",
                          "measured values are the card's S12-30 gate medians for the same case shape, not for this exact input; they rank the variants within 2.5%"]}
    dump_json(manifest, os.path.join(args.out, "manifest.json"))
    print("wrote %d candidates to %s (profile hash %s...)" % (len(manifest["candidates"]), args.out, prof.hash[:12]))
    for c in cands:
        print(" ", c["name"], c.get("coverage") or c.get("error"))


if __name__ == "__main__":
    main()
