#!/usr/bin/env python3
"""How much the S12-30 small-case predictions move with the random input instance.

  input_sensitivity.py --objects .work/_shared/S12-30 [--seeds 1,2,3,4,5] [--n 13,27] [--layout 0]

The card's columns are one draw of the gate's generator; the twin cannot reproduce that draw (the
generator state depends on everything the gate ran before). This prints the per-call prediction of the
switch-off build for several seeds: the spread is the input uncertainty of the s12-30-small rows.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)
import make_s12_30_cases as gen  # noqa: E402
from knc_model import functional, timing  # noqa: E402
from knc_model.kernel import Kernel  # noqa: E402
from knc_model.profile import load_profile  # noqa: E402


def per_call(obj, prefix, layout, n, seed, objdump, profile):
    pts, misses = [], []
    for calls in (2, 3):
        raw, _ = gen.make_kernel(obj, prefix, layout, n, seed, calls, objdump)
        k = Kernel(raw, obj)
        interp, steps, check = functional.run_functional(k, deadline=time.time() + 600)
        assert check["status"] == "ok", check
        res = timing.CoreSim(k, profile, interp.traces, record_issue=False).run()
        pts.append(res["completion_cycles"])
        misses.append(res["memory"]["stats"]["l2_hits"])
    return pts[1] - pts[0], misses[1] - misses[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", required=True)
    ap.add_argument("--seeds", default="1,2,3,4,5")
    ap.add_argument("--n", default="13,27")
    ap.add_argument("--layout", type=int, default=0)
    ap.add_argument("--objdump", default=os.environ.get("KNC_OBJDUMP"))
    args = ap.parse_args()
    prof = load_profile("card-7120-measured")
    for n in [int(x) for x in args.n.split(",")]:
        vals = []
        for seed in [int(x) for x in args.seeds.split(",")]:
            c, m = per_call(os.path.join(args.objects, "compiler-knc.o"), "knc", args.layout, n, seed, args.objdump, prof)
            vals.append(c)
            print("n=%d seed=%d cycles per call %d (L1 misses served from L2 per call: %d)" % (n, seed, c, m), flush=True)
        print("n=%d: min %d max %d spread %.1f%%" % (n, min(vals), max(vals), 100.0 * (max(vals) - min(vals)) / min(vals)))


if __name__ == "__main__":
    main()
