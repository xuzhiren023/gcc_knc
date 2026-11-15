#!/usr/bin/env python3
"""Held-out validation against the gcc_knc characterization microbenchmarks.

  validate_heldout.py --kernels-s kernels.s --kernels-h kernels.h --measured measured.json
                      --profile card-7120-measured --out DIR [--only REGEX] [--threads 1,2,4]

The kernels are the project's own `tests/bench/knc-char` catalog (regenerate with
`python -c "import kernels; kernels.emit(Path(OUT))"` in that directory); the measured
file holds the TSC ticks per unit per thread copied from docs/research/knc-characterization.md.
Each kernel function is read by the compiler-output adapter unchanged (prologue, 32-unit loop,
epilogue), executed functionally with the driver's memory layout (pointer chains for the
latency kinds, random direction bits for C10), and simulated at 1, 2 and 4 contexts with two
rounds counts; the per-unit prediction is the slope between the two, which removes the
prologue and the cold start. Predictions are compared with the measured ticks (TSC and core
clock agree within 0.5% on this card).

Rows whose measurement fixed a profile parameter are labeled "calibration" and excluded from
the held-out error statistics. Ranking reliability is the fraction of measured pairwise
orderings (within named groups, measured difference > 3%) that the predictions reproduce.
"""
import argparse
import datetime
import json
import os
import re
import statistics
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import from_gcc_s  # noqa: E402
from knc_model import functional, timing  # noqa: E402
from knc_model.errors import TwinError  # noqa: E402
from knc_model.kernel import Kernel  # noqa: E402
from knc_model.profile import load_profile  # noqa: E402
from knc_model.util import dump_json, load_json  # noqa: E402

BUF_BASE = 0x40000000
BUF_STRIDE = 0x02000000
STACK_BASE = 0x7F000000
STACK_STRIDE = 0x00100000

# parameters of card-7120-measured that were set from these rows (not held out)
CALIBRATION_ROWS = {
    "vaddps.lat": "latency.vector_arith", "vmulps.lat": "latency.vector_arith", "vfmadd213ps.lat": "latency.vector_arith",
    "vpaddd.lat": "latency.vector_arith", "vpxord.lat": "latency.vector_arith", "vaddpd.lat": "latency.vector_arith",
    "vmulpd.lat": "latency.vector_arith", "vfmadd213pd.lat": "latency.vector_arith",
    "vcvtfxpntdq2ps.lat": "latency.vector_arith", "vcvtfxpntudq2ps.lat": "latency.vector_arith", "vcvtfxpntps2dq.lat": "latency.vector_arith", "vcvtfxpntps2udq.lat": "latency.vector_arith",
    "vpermd.lat": "latency.vector_long", "vpermf32x4.lat": "latency.vector_long", "vrcp23ps.lat": "latency.vector_long",
    "swizzle_cdab.lat": "latency.vector_long", "swizzle_badc.lat": "latency.vector_long", "swizzle_dacb.lat": "latency.vector_long", "swizzle_aaaa.lat": "latency.vector_long",
    "swizzle_bbbb.lat": "latency.vector_long", "swizzle_cccc.lat": "latency.vector_long", "swizzle_dddd.lat": "latency.vector_long",
    "vcvtfxpntpd2dq.lat": "latency.vector_convert_df", "vcvtfxpntpd2udq.lat": "latency.vector_convert_df",
    "x87_add.lat": "latency.x87_add", "x87_mul.lat": "latency.x87_mul", "x87_mul.rt": "occupancy.x87_mul", "x87_div.lat": "latency.x87_div", "x87_div.rt": "occupancy.x87_div",
    "l1.load_lat": "latency.scalar_load_l1", "l2.load_lat": "latency.l2_hit", "memory.load_lat": "latency.memory", "memory.load_rt": "memory.core_service_cycles_per_line",
    "agi.gap0": "latency.agi_cycles", "gather_all.lat": "latency.gather_first_line", "gather_all.rt": "occupancy.gather_cycles_per_line",
    "c2.prefetch1": "occupancy.vprefetch_l2_core_cycles", "c10.branch.random": "latency.branch_mispredict_penalty",
    "vaddps.rt": "core.min_issue_gap_same_context (documented; measurement consistent)", "scalar_add.lat": "latency.scalar_alu (bound only)",
    "l1.store_stream": "store.nr_stall_cycles_resident / store.nr_occupancy_core_cycles", "l2.store_stream": "store.nr_stall_cycles_resident",
    "memory.store_stream": "store.nr_stall_cycles_memory", "l2.store_normal": "l1.store_miss_stalls_context",
    "c9.memory.u1": "latency.store_to_load_same_line", "spill_reload.lat": "latency.vector_load_l1 (derived with the store-to-load path)",
    "masked_load.lat": "latency.vector_load_merge_l1", "convert_up.lat": "latency.vector_load_merge_l1",
    "agi.gap1": "pairing.u_nop_pairs", "agi.gap2": "pairing.u_nop_pairs", "agi.gap3": "pairing.u_nop_pairs", "agi.gap4": "pairing.u_nop_pairs",
    "unpack.lat": "model rule: vloadunpack halves do not serialize on the destination merge",
    "c10.branch.fixed": "pairing.v_jmp_pairs", "l1.store_stream": "store.nr_stall_cycles_resident / store.nr_occupancy_core_cycles / NR residency rule",
    "gather_all.rt": "occupancy.gather_cycles_per_line / model rule: completion mask ready after the occupancy",
}

RANK_GROUPS = {
    "c9_register_unroll": ["c9.vector.u1", "c9.vector.u2", "c9.vector.u4"],
    "c9_memory_unroll": ["c9.memory.u1", "c9.memory.u2", "c9.memory.u4"],
    "agi_gap": ["agi.gap0", "agi.gap1", "agi.gap2", "agi.gap3", "agi.gap4"],
    "pairing": ["pair.vector_scalar", "pair.vector_vector", "pair.scalar_scalar"],
    "c7_accumulators": ["c7.reduce.a1", "c7.reduce.a2"],
    "memory_forms": ["masked_load.lat", "unpack.lat", "spill_reload.lat", "masked_load.rt", "unpack.rt", "spill_reload.rt"],
    "load_levels_lat": ["l1.load_lat", "l2.load_lat", "memory.load_lat"],
    "load_levels_rt": ["l1.load_rt", "l2.load_rt", "memory.load_rt"],
    "stores": ["l1.store_normal", "l1.store_stream", "l2.store_normal", "l2.store_stream", "memory.store_normal", "memory.store_stream"],
    "prefetch_pairing": ["c2.vector", "c2.prefetch0", "c2.prefetch1", "c2.vector_prefetch0", "c2.vector_prefetch1"],
    "throughput_rows": ["scalar_add.rt", "kmov.rt", "vaddps.rt", "vpermd.rt", "masked_load.rt", "x87_add.rt", "x87_mul.rt", "x87_div.rt"],
    "latency_rows": ["scalar_add.lat", "vaddps.lat", "vpermd.lat", "vcvtfxpntpd2dq.lat", "x87_add.lat", "masked_load.lat", "x87_div.lat"],
    "gathers": ["gather_all.lat", "gather_scattered.lat", "gather_all.rt", "gather_scattered.rt"],
    "branches": ["c10.branch.fixed", "c10.branch.random"],
}


def xorshift(state):
    state ^= (state << 13) & 0xFFFFFFFFFFFFFFFF
    state ^= state >> 7
    state ^= (state << 17) & 0xFFFFFFFFFFFFFFFF
    return state & 0xFFFFFFFFFFFFFFFF


def budget(name, core_bytes, density):
    if core_bytes:
        return core_bytes // density
    if name.startswith("c5."):
        return 9 * 1024 * 1024
    size = 16 * 1024 * 1024 if name.startswith("memory.") else (256 * 1024 if name.startswith("l2.") else 16 * 1024)
    per = size // density
    result = 2048
    while result * 2 <= per:
        result *= 2
    return result


def parse_header(path):
    tests = []
    text = open(path, encoding="utf-8").read()
    for m in re.finditer(r'\{\s*"([^"]+)",\s*char_kernel_(\d+),\s*(\d+),\s*(\d+),\s*(\d+)', text):
        tests.append({"name": m.group(1), "index": int(m.group(2)), "kind": int(m.group(3)), "unit": int(m.group(4)), "core_bytes": int(m.group(5))})
    return tests


def prepare_memory(interp, test, footprint, contexts):
    """Replicate driver.c prepare(): pointer chains (kinds 1, 3) and direction bits (kinds 5, 6)."""
    kind = test["kind"]
    for c in contexts:
        base = BUF_BASE + c * BUF_STRIDE
        if kind in (1, 3):
            n = footprint // (4096 if kind == 3 else 64)
            order = list(range(n))
            state = 1234567 + c
            for i in range(n - 1, 0, -1):
                state = xorshift(state)
                j = state % (i + 1)
                order[i], order[j] = order[j], order[i]

            def node(i):
                return 4096 * i + 64 * ((5 * i) % 64) if kind == 3 else 64 * i
            for i in range(n):
                interp.memory.write(base + node(order[i]), struct.pack("<Q", base + node(order[(i + 1) % n])))
        elif kind in (5, 6):
            state = 7654321 + c
            data = bytearray(footprint)
            for i in range(footprint):
                if kind == 5:
                    state = xorshift(state)
                    data[i] = state & 1
                else:
                    data[i] = 1
            interp.memory.write(base, bytes(data))


def run_case(kernel_dict, test, profile, threads, rounds, scenario, max_seconds):
    raw = json.loads(json.dumps({k: v for k, v in kernel_dict.items() if k != "_path"}))
    raw["scenario"] = scenario
    raw["memory_default"] = 0
    raw["max_steps"] = 4000000
    raw["unit_of_work"] = {"description": "32 measurement units per round, %d rounds" % rounds, "count": 32 * rounds}
    footprint = budget(test["name"], test["core_bytes"], threads)
    base_stream = raw["streams"][0]
    streams = []
    for c in range(threads):
        s = json.loads(json.dumps(base_stream))
        s["context"] = c
        s["init"] = {"registers": {"rdi": rounds, "rsi": "0x%x" % (BUF_BASE + c * BUF_STRIDE), "rdx": footprint,
                                   "rsp": "0x%x" % (STACK_BASE + c * STACK_STRIDE), "rbp": "0x%x" % (STACK_BASE + c * STACK_STRIDE)}}
        streams.append(s)
    raw["streams"] = streams
    kernel = Kernel(raw, kernel_dict.get("_path"))
    deadline = time.time() + max_seconds
    interp, steps, check = functional.run_functional(kernel, deadline=deadline, pre_init=lambda it: prepare_memory(it, test, footprint, range(threads)))
    sim = timing.CoreSim(kernel, profile, interp.traces, deadline=deadline, record_issue=False)
    res = sim.run()
    return res["completion_cycles"], res, sim.assumptions


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kernels-s", required=True)
    ap.add_argument("--kernels-h", required=True)
    ap.add_argument("--measured", required=True)
    ap.add_argument("--profile", default="card-7120-measured")
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default=None)
    ap.add_argument("--threads", default="1,2,4")
    ap.add_argument("--rounds", default="2,4")
    ap.add_argument("--max-seconds", type=float, default=90.0)
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    profile = load_profile(args.profile)
    measured = load_json(args.measured, "measured")["rows"]
    tests = [t for t in parse_header(args.kernels_h) if t["name"] in measured]
    if args.only:
        tests = [t for t in tests if re.search(args.only, t["name"])]
    threads = [int(x) for x in args.threads.split(",")]
    r1, r2 = [int(x) for x in args.rounds.split(",")]
    scen_a = {"memory": {"type": "line_tracking", "cold_level": "memory", "tlb": "modeled", "hardware_prefetcher": "off", "memory_service": "modeled"}, "branch": {"type": "all_predicted"}}
    scen_b = {"memory": {"type": "line_tracking", "cold_level": "memory", "tlb": "modeled", "hardware_prefetcher": "modeled", "memory_service": "modeled"}, "branch": {"type": "all_predicted"}}
    rows = []
    t_start = time.time()
    for test in tests:
        name = test["name"]
        row = {"name": name, "kind": test["kind"], "unit": test["unit"], "measured": measured[name],
               "class": "calibration" if name in CALIBRATION_ROWS else "held_out", "calibrates": CALIBRATION_ROWS.get(name),
               "predicted": {}, "status": "ok", "message": None}
        try:
            kernel_dict, cov_rows, summary = from_gcc_s.convert(args.kernels_s, "char_kernel_%d" % test["index"], profile=profile)
            kernel_dict["_path"] = args.kernels_s
            if not summary["complete"]["functional"]:
                row["status"] = "unsupported"
                row["message"] = "not functionally complete: " + "; ".join(summary["timing_only_or_missing"][:2] + summary["unsupported"][:2])
                rows.append(row)
                print("%-28s %s" % (name, row["message"][:100]), flush=True)
                continue
            memory_kind = test["kind"] in (1, 2, 3) or name.startswith(("c1.", "c4.", "c5.", "l1.", "l2.", "memory."))
            row_a = json.loads(json.dumps(scen_a))
            row_b = json.loads(json.dumps(scen_b))
            if name.startswith("c10."):
                # fixed direction: predicted; pseudorandom direction bits: every branch charged the measured penalty
                row_a["branch"] = {"type": "all_predicted" if name.endswith("fixed") else "all_mispredicted"}
            scenarios = [("A", row_a)] + ([("B_hwp", row_b)] if memory_kind else [])
            for t in threads:
                if t not in (1, 2, 4):
                    continue
                # rounds: enough to warm a cache-resident footprint before the measured slope; cold for memory-sized ones
                fp = budget(name, test["core_bytes"], t)
                # the driver measures a warm steady state: declare footprints that fit a cache level as resident there
                total = fp * t
                warm_level = "l1" if total <= profile.get("l1.size_bytes") else ("l2" if total <= profile.get("l2.size_bytes") else None)
                rr1, rr2 = r1, r2
                row.setdefault("rounds", {})["threads_%d" % t] = [rr1, rr2]
                row.setdefault("warm", {})["threads_%d" % t] = warm_level
                for label, sc in scenarios:
                    sc = json.loads(json.dumps(sc))
                    if warm_level:
                        sc["memory"]["warm"] = [{"start": "0x%x" % (BUF_BASE + c * BUF_STRIDE), "end": "0x%x" % (BUF_BASE + c * BUF_STRIDE + fp), "level": warm_level} for c in range(t)]
                    c1, res1, _ = run_case(kernel_dict, test, profile, t, rr1, sc, args.max_seconds)
                    c2, res2, assumptions = run_case(kernel_dict, test, profile, t, rr2, sc, args.max_seconds)
                    per_unit = (c2 - c1) / float((rr2 - rr1) * 32)
                    key = "threads_%d" % t
                    row["predicted"].setdefault(label, {})[key] = round(per_unit, 3)
                    if label == "A":
                        row.setdefault("limiting", {})[key] = timing.limiting_constraints(res2)[:2]
            rows.append(row)
            m = row["measured"]
            pa = row["predicted"].get("A", {})
            print("%-28s %-11s meas %s pred %s" % (name, row["class"], " ".join("%s=%.2f" % (k[-1], v) for k, v in sorted(m.items()) if k.startswith("threads")),
                                                   " ".join("%s=%.2f" % (k[-1], v) for k, v in sorted(pa.items()))), flush=True)
        except TwinError as e:
            row["status"] = e.status
            row["message"] = e.message
            rows.append(row)
            print("%-28s %s: %s" % (name, e.status, e.message[:110]), flush=True)
        except Exception as e:  # keep going; record the failure honestly
            row["status"] = "error"
            row["message"] = "%s: %s" % (type(e).__name__, e)
            rows.append(row)
            print("%-28s error: %s" % (name, row["message"][:110]), flush=True)
    report = summarize(rows, threads, profile, args)
    report["python_seconds"] = round(time.time() - t_start, 1)
    dump_json(report, os.path.join(args.out, "validation.json"))
    md = markdown(report)
    with open(os.path.join(args.out, "validation.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


def summarize(rows, threads, profile, args):
    stats = {}
    for t in threads:
        key = "threads_%d" % t
        errs = {"held_out": [], "calibration": []}
        for r in rows:
            if r["status"] != "ok":
                continue
            m = r["measured"].get(key)
            p = r["predicted"].get("A", {}).get(key)
            if m is None or p is None or m == 0:
                continue
            errs[r["class"]].append(100.0 * (p - m) / m)
        for cls, e in errs.items():
            if e:
                ae = [abs(x) for x in e]
                stats["%s_%s" % (cls, key)] = {"rows": len(e), "median_abs_error_pct": round(statistics.median(ae), 1), "worst_abs_error_pct": round(max(ae), 1),
                                              "within_15pct": sum(1 for x in ae if x <= 15), "within_30pct": sum(1 for x in ae if x <= 30),
                                              "mean_signed_error_pct": round(statistics.mean(e), 1)}
    # ranking reliability
    by_name = {r["name"]: r for r in rows if r["status"] == "ok"}
    ranking = {}
    agree_total = disagree_total = 0
    for g, names in RANK_GROUPS.items():
        for t in threads:
            key = "threads_%d" % t
            pairs = []
            present = [n for n in names if n in by_name and by_name[n]["measured"].get(key) is not None and by_name[n]["predicted"].get("A", {}).get(key) is not None]
            for i in range(len(present)):
                for j in range(i + 1, len(present)):
                    a, b = by_name[present[i]], by_name[present[j]]
                    ma, mb = a["measured"][key], b["measured"][key]
                    pa, pb = a["predicted"]["A"][key], b["predicted"]["A"][key]
                    if min(ma, mb) == 0 or abs(ma - mb) / max(ma, mb) < 0.03:
                        continue
                    ok = (ma < mb) == (pa < pb)
                    pairs.append({"a": present[i], "b": present[j], "measured": [ma, mb], "predicted": [pa, pb], "agree": ok})
                    agree_total += 1 if ok else 0
                    disagree_total += 0 if ok else 1
            if pairs:
                ranking["%s@%s" % (g, key)] = {"agree": sum(1 for p in pairs if p["agree"]), "pairs": len(pairs), "detail": [p for p in pairs if not p["agree"]]}
    return {"generated_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z", "profile": profile.describe(),
            "invocation": sys.argv, "scenario_A": "line_tracking cold memory, TLB modeled, hardware prefetcher off, memory service modeled",
            "scenario_B_hwp": "same with the streaming L2 hardware prefetcher sub-model (assumed depth) for memory-kind rows",
            "rows": rows, "error_stats": stats,
            "ranking": {"pairs_agree": agree_total, "pairs_total": agree_total + disagree_total,
                        "reliability": round(agree_total / float(agree_total + disagree_total), 3) if agree_total + disagree_total else None, "groups": ranking},
            "notes": ["predicted = slope of completion cycles between %s and %s rounds, divided by 32 units per round; TSC ticks and core cycles are treated as equal (0.5%% difference on this card)" % (args.rounds.split(",")[0], args.rounds.split(",")[1]),
                      "footprints that fit L1 (L2) with all active threads are declared warm in L1 (L2) because the driver measures a warm steady state; larger footprints start cold",
                      "the kernel catalog was regenerated from tests/bench/knc-char/kernels.py; S8-07 additions shift kernel indices but the measured S6-03 bodies are the same templates",
                      "calibration rows set a parameter of the profile and are excluded from the held-out statistics",
                      "every prediction is a model output; the measured column is native"]}


def markdown(rep):
    L = ["# Held-out validation against the characterization microbenchmarks", "",
         "Generated %s. Profile %s (hash %s...). %s" % (rep["generated_utc"], rep["profile"]["id"], rep["profile"]["hash"][:12], rep["scenario_A"]), ""]
    L.append("## Error statistics (scenario A, per thread count)")
    L.append("")
    L.append("| rows | n | median abs err % | worst abs err % | within 15% | within 30% | mean signed err % |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for k in sorted(rep["error_stats"]):
        s = rep["error_stats"][k]
        L.append("| %s | %d | %.1f | %.1f | %d | %d | %.1f |" % (k, s["rows"], s["median_abs_error_pct"], s["worst_abs_error_pct"], s["within_15pct"], s["within_30pct"], s["mean_signed_error_pct"]))
    rk = rep["ranking"]
    L.append("")
    L.append("## Ranking reliability")
    L.append("")
    L.append("%s of %s measured pairwise orderings (within groups, measured difference > 3%%) reproduced: reliability %s." % (rk["pairs_agree"], rk["pairs_total"], rk["reliability"]))
    L.append("")
    L.append("| group | agree | pairs | disagreements (a, b: measured -> predicted) |")
    L.append("|---|---:|---:|---|")
    for g in sorted(rk["groups"]):
        d = rk["groups"][g]
        det = "; ".join("%s vs %s: %.2f/%.2f -> %.2f/%.2f" % (x["a"], x["b"], x["measured"][0], x["measured"][1], x["predicted"][0], x["predicted"][1]) for x in d["detail"])
        L.append("| %s | %d | %d | %s |" % (g, d["agree"], d["pairs"], det))
    L.append("")
    L.append("## Rows")
    L.append("")
    L.append("| test | class | status | measured 1/2/4 | predicted A 1/2/4 | err % 1/2/4 | predicted B (HWP) 1/2/4 | limiting (1 thread) |")
    L.append("|---|---|---|---|---|---|---|---|")

    def fmt(d, keys=("threads_1", "threads_2", "threads_4")):
        return "/".join(("%.2f" % d[k]) if k in d and d[k] is not None else "-" for k in keys)
    for r in rep["rows"]:
        m = r["measured"]
        pa = r["predicted"].get("A", {})
        pb = r["predicted"].get("B_hwp", {})
        errs = []
        for k in ("threads_1", "threads_2", "threads_4"):
            if k in m and k in pa and m[k]:
                errs.append("%+.0f" % (100.0 * (pa[k] - m[k]) / m[k]))
            else:
                errs.append("-")
        lim = ", ".join(c.get("constraint", "") for c in r.get("limiting", {}).get("threads_1", [])) if r.get("limiting") else ""
        status = r["status"] if r["status"] == "ok" else "%s: %s" % (r["status"], (r["message"] or "")[:70])
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (r["name"], r["class"], status, fmt(m), fmt(pa), "/".join(errs), fmt(pb) if pb else "", lim))
    L.append("")
    for n in rep["notes"]:
        L.append("- " + n)
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
