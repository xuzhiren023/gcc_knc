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
    # 0.3.0: rows that exposed a rule or re-derived a value (they were held-out misses in 0.2.x and are no longer counted as held out)
    "spill_reload.rt": "pairing.load_store_pair, store.load_after_store_interlock_cycles (two- and four-thread values)",
    "c9.memory.u2": "store.load_after_store_interlock_cycles (one-thread value)",
    "c9.memory.u4": "store.load_after_store_interlock_cycles (one-thread value)",
    "gather_scattered.rt": "model rule: one cache line per gather execution, merge dependency on the previous execution (one-thread value)",
    "c9.vector.u1": "model rule: the taken-branch core bubble applies to forward transfers, not loop back-edges (two-thread value)",
    "c9.vector.u2": "same rule (two-thread value)", "c9.vector.u4": "same rule (two-thread value)",
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
RANK_THRESHOLD = 0.03          # characterization groups: measured difference above 3%
BAR = {"median_abs_error_pct": 10.0, "winner_accuracy": 0.90, "min_difference": 0.05, "min_rows": 50, "min_programs": 5}
# which M4 program (or microbenchmark family) each case's loops come from: the bar wants breadth, not only rows
CASE_PROGRAM = {"s12-31-microbench": "hpcg (row-loop microbenchmark)", "s12-31-hpcg-toy": "hpcg", "s12-31-hpcg-104": "hpcg", "s12-30-small": "sparse-gate (microbenchmark)"}


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


# ---------------------------------------------------------------------------------------------
# Compiled-code and card cases (tests/heldout_native/<case>/case.json, S13-06): one directory per
# case with the assembly or kernel, measurement.json citing its native log and prediction.json
# recorded before the comparison. predict_case() is deterministic; tests/regress/test_knc_twin.py
# checks that it reproduces prediction.json for the same engine and profile.

def _case_profile(profile_id):
    return load_profile(profile_id)


def _run_kernel(raw, path, profile, max_seconds):
    kernel = Kernel(raw, path)
    deadline = time.time() + max_seconds
    interp, steps, check = functional.run_functional(kernel, deadline=deadline)
    if check["status"] == "mismatch":
        raise TwinError("functional_mismatch: %s" % json.dumps(check["mismatches"][:3]))
    sim = timing.CoreSim(kernel, profile, interp.traces, deadline=deadline, record_issue=False)
    res = sim.run()
    return res, check["status"]


def _predict_compiled_function(case_dir, case, variant, profile, max_seconds):
    """A function region; per-unit cycles = slope of completion cycles between two unit counts."""
    source = os.path.join(case_dir, variant.get("source", case["source"]))
    kernel, rows, summary = from_gcc_s.convert(source, variant["function"], profile=profile)
    if not summary["complete"]["isa"] or not summary["complete"]["functional"] or not summary["complete"]["timing"]:
        return {"status": "unsupported", "message": "; ".join(summary["unsupported"] + summary["timing_only_or_missing"])[:400]}
    points = []
    res = None
    checks = []
    for units in case["slope_units"]:
        raw = json.loads(json.dumps(kernel))
        raw["init"]["registers"].update(case["init"]["registers"])
        raw["init"]["registers"][case["slope_register"]] = units
        raw["init"]["memory"] = raw["init"].get("memory", []) + case["init"]["memory"]
        raw["expected"] = case["expected"][str(units)]
        raw["scenario"] = case["scenario"]
        raw["memory_default"] = 0
        raw["max_steps"] = 4000000
        raw["unit_of_work"] = {"description": case["unit"], "count": units}
        res, chk = _run_kernel(raw, source, profile, max_seconds)
        checks.append(chk)
        points.append(res["completion_cycles"])
    per_unit = (points[1] - points[0]) / float(case["slope_units"][1] - case["slope_units"][0])
    return {"status": "ok", "functional": checks, "completion_cycles": points, "predicted_cycles_per_unit": round(per_unit, 3),
            "limiting": timing.limiting_constraints(res)[:2]}


def _predict_compiled_kernel(case_dir, case, variant, profile, max_seconds):
    """A ready kernel (adapter output plus input and expected result). Without case["slope"]: cycles of the
    kernel's one unit. With it: the kernel is run at two unit counts (a register holds the count) and the
    per-unit cycles are the slope, which removes entry code and reaches the steady cache state."""
    path = os.path.normpath(os.path.join(case_dir, variant["kernel"]))
    raw = load_json(path, "kernel")
    slope = case.get("slope")
    if not slope:
        if raw["unit_of_work"]["count"] != 1:
            raise TwinError("compiled_kernel variants without a slope must define one unit of work")
        res, chk = _run_kernel(raw, path, profile, max_seconds)
        return {"status": "ok", "functional": [chk], "completion_cycles": [res["completion_cycles"]],
                "predicted_cycles_per_unit": float(res["completion_cycles"]), "limiting": timing.limiting_constraints(res)[:2],
                "frontend": res.get("frontend"), "memory_submodels": res["memory"].get("submodels")}
    points, checks, res = [], [], None
    for units in slope["units"]:
        k = json.loads(json.dumps(raw))
        if slope.get("register"):
            k["init"].setdefault("registers", {})[slope["register"]] = units
        for a in slope.get("memory_i32", []):
            k["init"]["memory"].append({"addr": a, "i32": [units]})
        k["unit_of_work"] = dict(k["unit_of_work"], count=units)
        if "expected_f64_per_unit" in slope:
            k["expected"] = {"memory": [{"addr": slope["expected_addr"], "f64": [slope["expected_f64_per_unit"] * units]}]}
        elif "expected_by_units" in slope:
            k["expected"] = slope["expected_by_units"].get(str(units), {})
        elif not slope.get("expected_same"):
            k["expected"] = {}
        res, chk = _run_kernel(k, path, profile, max_seconds)
        checks.append(chk)
        points.append(res["completion_cycles"])
    per_unit = (points[1] - points[0]) / float(slope["units"][1] - slope["units"][0])
    return {"status": "ok", "functional": checks, "completion_cycles": points, "predicted_cycles_per_unit": round(per_unit, 3),
            "limiting": timing.limiting_constraints(res)[:2], "frontend": res.get("frontend"), "memory_submodels": res["memory"].get("submodels")}


def _twin_cli(args, out):
    import subprocess
    proc = subprocess.run([sys.executable, os.path.join(HERE, "knc_twin.py")] + [str(a) for a in args] + ["--out", str(out), "--force"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    result = os.path.join(str(out), "result.json")
    if not os.path.exists(result):
        raise TwinError("twin %s wrote no result.json (exit %d): %s" % (args[0], proc.returncode, proc.stdout[-1500:]))
    return load_json(result, "result")


def _predict_card(case_dir, case, tmp):
    """Card scale: per-core compute term from a simulate of the stand-in loop, then bounds --scale card."""
    core = case["core"]
    report, kernel = from_gcc_s.convert_loop(os.path.join(case_dir, core["source"]), core["loop"], core.get("function"),
                                             core.get("spec"), core.get("contexts", 1))
    name = os.path.basename(case_dir)
    pred = {"case": name}
    if kernel is None:
        pred.update(status="unsupported", unsupported=report["unsupported"])
        return pred
    kpath = os.path.join(tmp, name + "-core.kernel.json")
    dump_json(kernel, kpath)
    r = _twin_cli(["simulate", kpath], os.path.join(tmp, name + "-core"))
    if r["status"] != "ok":
        pred.update(status=r["status"], message=r["message"])
        return pred
    p = r["prediction"]
    pred["core"] = {"status": "ok", "contexts": core.get("contexts", 1), "predicted_cycles": p["predicted_cycles"],
                    "cycles_per_unit_core": p["predicted_cycles_per_unit"], "limiting": r.get("limiting_constraints")}
    params = load_json(os.path.join(case_dir, case["params"]), "params")
    params["per_core_cycles_per_unit"] = pred["core"]["cycles_per_unit_core"]
    ppath = os.path.join(tmp, name + "-params.json")
    dump_json(params, ppath)
    r = _twin_cli(["bounds", "--scale", "card", "--params", ppath], os.path.join(tmp, name + "-card"))
    pred.update(status=r["status"], engine_version=r["engine_version"], profile_hash=r["profile"]["hash"])
    if r["status"] == "ok":
        pred["scenarios"] = [{k: s.get(k) for k in ("bandwidth_gbs", "binding", "compute_seconds", "memory_seconds", "total_seconds",
                                                       "achieved_bandwidth_gbs_if_total")} for s in r["prediction"]["scenarios"]]
    else:
        pred["message"] = r["message"]
    return pred


def predict_case(case_dir, profile_id="card-7120-measured", tmp=None, max_seconds=120.0):
    """The prediction a held-out case records in prediction.json (no timestamps: reproducible)."""
    case_dir = os.path.abspath(str(case_dir))
    case = load_json(os.path.join(case_dir, "case.json"), "case")
    if case.get("prepare") and not os.path.isdir(os.path.join(case_dir, "input")):
        import subprocess
        parts = case["prepare"].split()
        subprocess.check_call([sys.executable, os.path.join(os.path.dirname(case_dir), parts[0])] + parts[1:])
    if case["scale"] == "card":
        import tempfile
        return _predict_card(case_dir, case, tmp or tempfile.mkdtemp(prefix="knc-heldout-"))
    profile = _case_profile(profile_id)
    from knc_model import ENGINE_VERSION
    pred = {"case": os.path.basename(case_dir), "engine_version": ENGINE_VERSION, "profile_hash": profile.hash,
            "unit": case["unit"], "scenario": case.get("scenario_name"), "variants": []}
    for v in case["variants"]:
        try:
            if case["kind"] == "compiled_function":
                row = _predict_compiled_function(case_dir, case, v, profile, max_seconds)
            else:
                row = _predict_compiled_kernel(case_dir, case, v, profile, max_seconds)
        except TwinError as e:
            row = {"status": e.status, "message": e.message}
        pred["variants"].append(dict({"variant": v["name"]}, **row))
    return pred


def compiled_rows(cases_dir, profile_id, record=False, max_seconds=120.0, only=None):
    """Rows for every core-scale case directory, compared with measurement.json; card cases listed apart.
    A variant marked "calibrates" in case.json set a model rule and is a calibration row; the others are held out."""
    rows, card, groups = [], [], {}
    for name in sorted(os.listdir(cases_dir)):
        d = os.path.join(cases_dir, name)
        if not os.path.isfile(os.path.join(d, "case.json")):
            continue
        if only and not re.search(only, name):
            continue
        case = load_json(os.path.join(d, "case.json"), "case")
        pred = predict_case(d, profile_id, max_seconds=None if record else max_seconds)
        rec_path = os.path.join(d, "prediction.json")
        recorded = load_json(rec_path, "prediction") if os.path.exists(rec_path) else None
        if record:
            bad = [v for v in pred.get("variants", []) if v.get("status") != "ok"]
            if bad:
                raise ValueError("refusing to record %s: variant %s: %s" %
                                 (name, bad[0].get("variant"), bad[0].get("message", bad[0].get("status"))))
            dump_json(pred, rec_path)
        elif recorded != pred:
            print("%-28s prediction differs from the recorded prediction.json (engine or profile changed?)" % name, flush=True)
        meas = load_json(os.path.join(d, "measurement.json"), "measurement")
        if case["scale"] == "card":
            card.append({"case": name, "prediction": pred, "measurement": meas})
            print("%-28s card        %s" % (name, pred.get("status")), flush=True)
            continue
        calibrates = {v["name"]: v.get("calibrates") for v in case["variants"]}
        for g in case.get("rank_groups", []):
            groups["%s: %s" % (name, g["name"])] = ["%s/%s" % (name, v) for v in g["variants"]]
        for v in pred["variants"]:
            m = meas["per_variant"].get(v["variant"])
            cal = calibrates.get(v["variant"])
            row = {"name": "%s/%s" % (name, v["variant"]), "suite": "compiled", "case": name, "kind": "compiled", "unit": pred["unit"],
                   "measured": {"threads_1": m} if m is not None else {}, "class": "calibration" if cal else "held_out", "calibrates": cal,
                   "predicted": {}, "status": v["status"], "message": v.get("message"), "source_log": meas["source_log"]}
            if v["status"] == "ok":
                row["predicted"]["A"] = {"threads_1": v["predicted_cycles_per_unit"]}
                row["limiting"] = {"threads_1": v["limiting"]}
            rows.append(row)
            print("%-44s %-11s meas %s pred %s" % (row["name"], row["class"], m, v.get("predicted_cycles_per_unit", v["status"] + ": " + str(v.get("message"))[:80])), flush=True)
    return rows, card, groups


def decision_bar(rows, groups):
    """The bar for relying on the twin to choose between compiled variants (held-out compiled rows only):
    median absolute error at most 10%, and the right winner in at least 90% of the pairs (within a case's
    variant groups) whose measured times differ by more than 5%. It also needs enough loops to mean anything."""
    held = [r for r in rows if r.get("suite") == "compiled" and r["class"] == "held_out" and r["status"] == "ok"
            and r["measured"].get("threads_1") and r["predicted"].get("A", {}).get("threads_1") is not None]
    errs = [abs(100.0 * (r["predicted"]["A"]["threads_1"] - r["measured"]["threads_1"]) / r["measured"]["threads_1"]) for r in held]
    by = {r["name"]: r for r in held}
    pairs = right = 0
    wrong = []
    for g, names in groups.items():
        present = [n for n in names if n in by]
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                a, b = by[present[i]], by[present[j]]
                ma, mb = a["measured"]["threads_1"], b["measured"]["threads_1"]
                pa, pb = a["predicted"]["A"]["threads_1"], b["predicted"]["A"]["threads_1"]
                if abs(ma - mb) / max(ma, mb) <= BAR["min_difference"]:
                    continue
                pairs += 1
                if (ma < mb) == (pa < pb) and pa != pb:
                    right += 1
                else:
                    wrong.append({"group": g, "a": present[i], "b": present[j], "measured": [ma, mb], "predicted": [pa, pb]})
    med = round(statistics.median(errs), 1) if errs else None
    acc = round(right / float(pairs), 3) if pairs else None
    cases = sorted(set(r["case"] for r in held))
    programs = sorted(set(CASE_PROGRAM.get(c, c) for c in cases))
    m4_programs = sorted(p for p in programs if "microbenchmark" not in p)
    met_err = med is not None and med <= BAR["median_abs_error_pct"]
    met_rank = acc is not None and acc >= BAR["winner_accuracy"]
    met_n = len(held) >= BAR["min_rows"] and len(m4_programs) >= BAR["min_programs"]
    return {"bar": BAR, "held_out_compiled_rows": len(held), "cases": cases, "source_programs": programs, "m4_programs": m4_programs,
            "median_abs_error_pct": med, "worst_abs_error_pct": round(max(errs), 1) if errs else None,
            "within_10pct": sum(1 for e in errs if e <= 10.0),
            "pairs_over_5pct": pairs, "right_winner": right, "winner_accuracy": acc, "wrong_pairs": wrong,
            "error_met": met_err, "ranking_met": met_rank, "coverage_met": met_n,
            "met": bool(met_err and met_rank and met_n),
            "statement": ("bar met on %d held-out compiled rows from %d M4 programs" % (len(held), len(m4_programs))) if (met_err and met_rank and met_n) else
                         ("error and ranking criteria met on %d held-out compiled rows, but they come from %d M4 program(s) (%s) and %d microbenchmark families; "
                          "the bar asks for loops from at least %d M4 programs, so it is not met yet" % (len(held), len(m4_programs), ", ".join(m4_programs) or "none",
                                                                                                              len(programs) - len(m4_programs), BAR["min_programs"])) if (met_err and met_rank) else
                         "bar not met: median error %s%% (limit %s), winner accuracy %s (limit %s) on %d rows" % (med, BAR["median_abs_error_pct"], acc, BAR["winner_accuracy"], len(held))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kernels-s", help="characterization catalog assembly (omit to run only --cases)")
    ap.add_argument("--kernels-h")
    ap.add_argument("--measured")
    ap.add_argument("--only-cases", default=None, help="regex on case directory names")
    ap.add_argument("--cases", help="tests/heldout_native: also predict every compiled-code and card case there")
    ap.add_argument("--record", action="store_true", help="with --cases: (re)write each case's prediction.json")
    ap.add_argument("--profile", default="card-7120-measured")
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default=None)
    ap.add_argument("--threads", default="1,2,4")
    ap.add_argument("--rounds", default="2,4")
    ap.add_argument("--max-seconds", type=float, default=90.0,
                    help="simulation wall-clock budget; 0 disables the deadline (held-out replay) ")
    args = ap.parse_args(argv)
    if args.max_seconds == 0:
        args.max_seconds = None
    os.makedirs(args.out, exist_ok=True)
    profile = load_profile(args.profile)
    measured = load_json(args.measured, "measured")["rows"] if args.kernels_s else {}
    tests = [t for t in parse_header(args.kernels_h) if t["name"] in measured] if args.kernels_s else []
    if args.only:
        tests = [t for t in tests if re.search(args.only, t["name"])]
    threads = [int(x) for x in args.threads.split(",")]
    r1, r2 = [int(x) for x in args.rounds.split(",")]
    # A: the engine's default memory domain (TLB, L2 hardware prefetcher and memory service modeled); B: the same without the prefetcher (sensitivity)
    scen_a = {"memory": {"type": "line_tracking", "cold_level": "memory", "tlb": "modeled", "hardware_prefetcher": "modeled", "memory_service": "modeled"}, "branch": {"type": "all_predicted"}}
    scen_b = {"memory": {"type": "line_tracking", "cold_level": "memory", "tlb": "modeled", "hardware_prefetcher": "off", "memory_service": "modeled"}, "branch": {"type": "all_predicted"}}
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
            scenarios = [("A", row_a)] + ([("B_nohwp", row_b)] if memory_kind else [])
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
    for r in rows:
        r.setdefault("suite", "characterization")
    card = []
    case_groups = {}
    if args.cases:
        crow, card, case_groups = compiled_rows(args.cases, args.profile, record=args.record, max_seconds=max(args.max_seconds, 900.0), only=args.only_cases)
        rows += crow
    report = summarize(rows, threads, profile, args, case_groups)
    report["decision_bar"] = decision_bar(rows, case_groups)
    report["card_cases"] = card
    report["python_seconds"] = round(time.time() - t_start, 1)
    dump_json(report, os.path.join(args.out, "validation.json"))
    md = markdown(report)
    with open(os.path.join(args.out, "validation.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print(md)
    return 0


def summarize(rows, threads, profile, args, case_groups=None):
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
            errs.setdefault(r["class"] if r.get("suite", "characterization") == "characterization" else "%s_%s" % (r["suite"], r["class"]), []).append(100.0 * (p - m) / m)
            if r["class"] == "held_out":
                errs.setdefault("all_held_out", []).append(100.0 * (p - m) / m)
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
    all_groups = dict(RANK_GROUPS)
    all_groups.update(case_groups or {})
    for g, names in all_groups.items():
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
            "invocation": sys.argv, "scenario_A": "line_tracking cold memory with the default sub-models: TLB, L2 hardware prefetcher and memory service modeled",
            "scenario_B_nohwp": "the same without the hardware prefetcher (sensitivity, memory-kind rows only)",
            "rows": rows, "error_stats": stats,
            "ranking": {"pairs_agree": agree_total, "pairs_total": agree_total + disagree_total,
                        "reliability": round(agree_total / float(agree_total + disagree_total), 3) if agree_total + disagree_total else None, "groups": ranking},
            "notes": ["predicted = slope of completion cycles between %s and %s rounds, divided by 32 units per round; TSC ticks and core cycles are treated as equal (0.5%% difference on this card)" % (args.rounds.split(",")[0], args.rounds.split(",")[1]),
                      "footprints that fit L1 (L2) with all active threads are declared warm in L1 (L2) because the driver measures a warm steady state; larger footprints start cold",
                      "the kernel catalog was regenerated from tests/bench/knc-char/kernels.py; S8-07 additions shift kernel indices but the measured S6-03 bodies are the same templates",
                      "calibration rows set a parameter of the profile and are excluded from the held-out statistics",
                      "every prediction is a model output; the measured column is native",
                      "compiled rows (tests/heldout_native/<case>/) come from the binaries and objects that ran on the card, with code layout; seconds converted with card.clock_hz 1.238 GHz; variants marked 'calibrates' in a case.json set a model rule and are calibration rows; each prediction is recorded in the case's prediction.json",
                      "decision bar (compiled held-out rows only): median absolute error at most 10%, right winner in at least 90% of within-group pairs measured more than 5% apart, at least 50 loops"]}


def markdown(rep):
    L = ["# Held-out validation against the characterization microbenchmarks", "",
         "Generated %s. Profile %s (hash %s...). %s" % (rep["generated_utc"], rep["profile"]["id"], rep["profile"]["hash"][:12], rep["scenario_A"]), ""]
    L.append("## Error statistics (per thread count)")
    L.append("")
    L.append("| rows | n | median abs err % | worst abs err % | within 15% | within 30% | mean signed err % |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for k in sorted(rep["error_stats"]):
        s = rep["error_stats"][k]
        L.append("| %s | %d | %.1f | %.1f | %d | %d | %.1f |" % (k, s["rows"], s["median_abs_error_pct"], s["worst_abs_error_pct"], s["within_15pct"], s["within_30pct"], s["mean_signed_error_pct"]))
    db = rep.get("decision_bar")
    if db and db["held_out_compiled_rows"]:
        L.append("")
        L.append("## Decision bar (held-out compiled code)")
        L.append("")
        L.append("| criterion | limit | result | met |")
        L.append("|---|---|---|---|")
        L.append("| median absolute error | at most %.0f%% | %s%% over %d rows (worst %s%%, %d within 10%%) | %s |" % (db["bar"]["median_abs_error_pct"], db["median_abs_error_pct"], db["held_out_compiled_rows"], db["worst_abs_error_pct"], db["within_10pct"], "yes" if db["error_met"] else "no"))
        L.append("| right winner, pairs measured more than 5%% apart | at least %.0f%% | %s of %s (%s) | %s |" % (100 * db["bar"]["winner_accuracy"], db["right_winner"], db["pairs_over_5pct"], db["winner_accuracy"], "yes" if db["ranking_met"] else "no"))
        L.append("| held-out compiled loops | at least %d rows from at least %d M4 programs | %d rows in %d cases; sources: %s | %s |" % (db["bar"]["min_rows"], db["bar"]["min_programs"], db["held_out_compiled_rows"], len(db["cases"]), ", ".join(db["source_programs"]), "yes" if db["coverage_met"] else "no"))
        L.append("")
        L.append("Verdict: %s." % db["statement"])
        for w in db["wrong_pairs"]:
            L.append("- wrong winner: %s vs %s, measured %.1f/%.1f, predicted %.1f/%.1f" % (w["a"], w["b"], w["measured"][0], w["measured"][1], w["predicted"][0], w["predicted"][1]))
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
    L.append("| test | class | status | measured 1/2/4 | predicted 1/2/4 | err % 1/2/4 | predicted without HWP 1/2/4 | limiting (1 thread) |")
    L.append("|---|---|---|---|---|---|---|---|")

    def fmt(d, keys=("threads_1", "threads_2", "threads_4")):
        return "/".join(("%.2f" % d[k]) if k in d and d[k] is not None else "-" for k in keys)
    for r in rep["rows"]:
        m = r["measured"]
        pa = r["predicted"].get("A", {})
        pb = r["predicted"].get("B_nohwp", {})
        errs = []
        for k in ("threads_1", "threads_2", "threads_4"):
            if k in m and k in pa and m[k]:
                errs.append("%+.1f" % (100.0 * (pa[k] - m[k]) / m[k]))
            else:
                errs.append("-")
        lim = ", ".join(c.get("constraint", "") for c in r.get("limiting", {}).get("threads_1", [])) if r.get("limiting") else ""
        status = r["status"] if r["status"] == "ok" else "%s: %s" % (r["status"], (r["message"] or "")[:70])
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (r["name"], r["class"], status, fmt(m), fmt(pa), "/".join(errs), fmt(pb) if pb else "", lim))
    if rep.get("card_cases"):
        L.append("")
        L.append("## Card-scale cases (analytical card scale; outside the core model, not in the statistics)")
        L.append("")
        L.append("| case | status | per-core cycles per unit (stand-in loop) | predicted GB/s | measured GB/s (median) |")
        L.append("|---|---|---:|---:|---:|")
        for c in rep["card_cases"]:
            p, m = c["prediction"], c["measurement"]
            bw = "/".join("%.1f" % s["bandwidth_gbs"] for s in p.get("scenarios", []) if s.get("bandwidth_gbs") is not None) or "-"
            meas = "/".join("%.2f" % r["median_GBs"] for r in m.get("rows", []) if "median_GBs" in r) or "-"
            L.append("| %s | %s | %s | %s | %s |" % (c["case"], p.get("status"), p.get("core", {}).get("cycles_per_unit_core", "-"), bw, meas))
    L.append("")
    for n in rep["notes"]:
        L.append("- " + n)
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
