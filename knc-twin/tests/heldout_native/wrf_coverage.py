#!/usr/bin/env python3
"""Coverage of PhiWeather's patched WRF hot routines by the twin (read-only inputs).

  wrf_coverage.py --objects DIR --objdump TOOL [--routines mynn_tendencies,...] --out REPORT.json

For each routine named in the PhiWeather twin study (object file and function symbol), run the
binary adapter and report instructions, padding, prefixed instructions, calls, and what is still not
complete, per category (parser, ISA, functional, timing) and per innermost loop. Writes JSON and
prints a table. One process; each object is disassembled once (`objdump -dr`).
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import from_binary  # noqa: E402
from knc_model.errors import TwinError  # noqa: E402
from knc_model.profile import load_profile  # noqa: E402
from knc_model.util import dump_json  # noqa: E402

ROUTINES = {
    "mynn_tendencies": ("phys/module_bl_mynnedmf.o", "__module_bl_mynnedmf_MOD_mynn_tendencies"),
    "mynnedmf_driver": ("phys/module_bl_mynnedmf.o", "__module_bl_mynnedmf_MOD_mynnedmf_driver"),
    "dmp_mf": ("phys/module_bl_mynnedmf.o", "__module_bl_mynnedmf_MOD_dmp_mf"),
    "mp_thompson": ("phys/module_mp_thompson.o", "__module_mp_thompson_MOD_mp_thompson"),
    "mp_gt_driver": ("phys/module_mp_thompson.o", "__module_mp_thompson_MOD_mp_gt_driver"),
    "rslf": ("phys/module_mp_thompson.o", "__module_mp_thompson_MOD_rslf"),
    "advect_scalar": ("dyn_em/module_advect_em.o", "__module_advect_em_MOD_advect_scalar"),
    "advect_scalar_pd": ("dyn_em/module_advect_em.o", "__module_advect_em_MOD_advect_scalar_pd"),
    "advance_uv": ("dyn_em/module_small_step_em.o", "__module_small_step_em_MOD_advance_uv"),
    "advance_mu_t": ("dyn_em/module_small_step_em.o", "__module_small_step_em_MOD_advance_mu_t"),
    "horizontal_diffusion_s": ("dyn_em/module_diffusion_em.o", "__module_diffusion_em_MOD_horizontal_diffusion_s"),
    "sixth_order_diffusion": ("dyn_em/module_em.o", "__module_em_MOD_sixth_order_diffusion"),
    "rk_update_scalar": ("dyn_em/module_em.o", "__module_em_MOD_rk_update_scalar"),
}


def innermost_loops(records):
    """Innermost loops of the converted records: a backward branch whose target has no other backward branch inside."""
    labels = {}
    for i, r in enumerate(records):
        if r.get("label"):
            labels[r["label"]] = i
    loops = []
    for i, r in enumerate(records):
        if r["op"].startswith("j") and r["op"] != "jmp" or r["op"] == "jmp":
            tgt = [o for o in r["ops"] if isinstance(o, str) and o in labels]
            if tgt and labels[tgt[0]] < i:
                loops.append((labels[tgt[0]], i))
    inner = [(a, b) for a, b in loops if not any(a < c and d < b for c, d in loops if (c, d) != (a, b))]
    return inner


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", required=True, help="WRF build directory (holds phys/, dyn_em/)")
    ap.add_argument("--objdump", default=os.environ.get("KNC_OBJDUMP"))
    ap.add_argument("--routines", default=",".join(ROUTINES))
    ap.add_argument("--out")
    args = ap.parse_args()
    prof = load_profile("card-7120-measured")
    dis_cache = {}
    report = {"routines": [], "unsupported_total": collections.Counter()}
    print("%-24s %8s %6s %6s %5s %5s  %s" % ("routine", "instrs", "pad", "prefix", "calls", "loops", "complete loops / blockers"))
    for name in args.routines.split(","):
        obj, fn = ROUTINES[name]
        path = os.path.join(args.objects, obj)
        if path not in dis_cache:
            dis_cache[path] = from_binary.disassemble(path, tool=args.objdump)
        row = {"routine": name, "object": obj, "function": fn}
        try:
            conv = from_binary.Converter(path, dis_cache[path])
            kernel, rows, summary = conv.convert(fn, profile=prof)
        except TwinError as e:
            row.update(status=e.status, message=e.message)
            report["routines"].append(row)
            print("%-24s %s: %s" % (name, e.status, e.message[:90]))
            continue
        recs = kernel["streams"][0]["instructions"]
        reasons = collections.Counter(r["reason"].split(":")[0] + ": " + r["text"].split()[0] for r in rows if r["reason"])
        loops = innermost_loops(recs)
        bad_by_index = {i for i, r in enumerate(rows) if r["reason"]}
        complete = sum(1 for a, b in loops if not any(a <= i <= b for i in bad_by_index))
        row.update(status="ok", instructions=summary["instructions"], padding_nops=kernel["provenance"]["padding_nops"],
                   prefixed=kernel["provenance"]["slow_prefix_instructions"], calls=sum(1 for r in recs if r["op"] == "call"),
                   undeclared_callees=kernel["provenance"]["undeclared_callees"], complete=summary["complete"],
                   innermost_loops=len(loops), innermost_loops_complete=complete, blockers=dict(reasons))
        for k, v in reasons.items():
            report["unsupported_total"][k] += v
        report["routines"].append(row)
        print("%-24s %8d %6d %6d %5d %5d  %d / %s" % (name, summary["instructions"], row["padding_nops"], row["prefixed"], row["calls"], len(loops), complete,
                                                       "; ".join("%s x%d" % kv for kv in reasons.most_common(3)) or "none"))
    report["unsupported_total"] = dict(report["unsupported_total"])
    if args.out:
        dump_json(report, args.out)


if __name__ == "__main__":
    main()
