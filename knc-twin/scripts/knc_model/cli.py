"""Command-line entry: capabilities, selftest, validate, functional, simulate, bounds, compare,
prepare-native, import-native."""
import argparse
import datetime
import json
import os
import re
import sys
import time

from . import ENGINE_VERSION, KERNEL_SCHEMA
from .errors import (BudgetExhausted, FunctionalMismatch, InvalidInput, MissingParameter, NeedsParameters, STATUS_EXIT_CODES,
                     TwinError, Unsupported)
from .util import dump_json, load_json, resource_path, sha256_of_file, sha256_of_obj, skill_root
from . import isa
from .profile import list_profiles, load_profile
from .kernel import load_kernel
from .report import base_result, write_result
from . import functional as fmod
from . import trace as tmod
from . import timing
from . import bounds as bmod
from . import analytic
from . import native as nmod

SCALES = ("instruction", "region", "core", "pair", "card")


def _calib(prof):
    return dict(prof.calibration, synthetic=prof.synthetic,
                note="Simulated/analytical outputs are model results, never native measurements. " + ("This profile is SYNTHETIC." if prof.synthetic else ""))


def _default_out(cmd, name):
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name or "run")
    return os.path.join(os.getcwd(), "knc-twin-runs", "%s-%s-%s" % (stamp, cmd, safe))


def _prepare_out(args, cmd, name):
    out = args.out or _default_out(cmd, name)
    if os.path.isdir(out) and os.listdir(out) and not getattr(args, "force", False):
        raise InvalidInput("output directory %s exists and is not empty; each experiment gets its own directory (use --force to overwrite)" % out)
    os.makedirs(out, exist_ok=True)
    return out


def _deadline(args):
    return time.time() + args.max_seconds if getattr(args, "max_seconds", None) else None


def _finish(r, out, args, extra_print=None):
    r["python_execution_seconds"] = round(time.time() - args._t0, 4)
    rp, sp = write_result(out, r)
    if getattr(args, "json", False):
        print(json.dumps(r, indent=2, sort_keys=True))
    else:
        print("%s: %s" % (r["result_type"], r["status"]))
        if r.get("message"):
            print(r["message"])
        if extra_print:
            for line in extra_print:
                print(line)
        print("result: %s" % rp)
        print("summary: %s" % sp)
    return STATUS_EXIT_CODES.get(r["status"], 1)


def _fail(r, out, args, err):
    r["status"] = err.status
    r["message"] = err.message
    r["error_details"] = json.dumps(err.details, sort_keys=True) if err.details else None
    if isinstance(err, BudgetExhausted):
        r["partial"] = dict(err.partial, note="partial execution; NOT a completed result")
    if isinstance(err, Unsupported):
        r["unsupported"].append(err.message)
    return _finish(r, out, args)


def _kernel_and_hash(path):
    k = load_kernel(path)
    return k, sha256_of_obj(k.raw)


# --- commands --------------------------------------------------------------------------------

def cmd_capabilities(args):
    args._t0 = time.time()
    out = _prepare_out(args, "capabilities", "")
    r = base_result("capabilities", "ok", "capabilities", out_dir=out)
    caps = {
        "engine_version": ENGINE_VERSION,
        "target": "Intel Xeon Phi Knights Corner (K1OM, IMCI). Not Knights Landing, not AVX-512, not an out-of-order x86 model.",
        "scales": {
            "instruction": "implemented: latency/pipe class per supported mnemonic (capabilities table), exact functional semantics where 'functional' is true",
            "region": "implemented: straight-line or single-loop records per context; functional execution, timing, bounds, exhaustive reorder search (<= 12 instructions)",
            "core": "implemented: 1-4 in-order contexts, U/V pairing rules, same-context issue spacing, round-robin picker, AGI, demand-miss stalls, nonblocking prefetch, outstanding-miss limit, L1/L2 LRU line tracking, resource occupancy (gather, x87, L2 prefetch issue)",
            "pair": "analytical scenario only (two cores exchanging lines over the ring); needs core-scale cycles and transfer counts as parameters",
            "card": "analytical scenario only (compute vs bandwidth roofline with barriers and imbalance); never one-core throughput x cores",
        },
        "commands": ["capabilities", "selftest", "validate", "functional", "simulate", "bounds", "compare", "prepare-native", "import-native"],
        "input_representations": ["normalized-records (JSON, knc-twin.kernel/1)", "gas-att-subset (GAS AT&T assembly subset, see references/input-format.md)"],
        "memory_scenarios": ["fixed_level", "classified", "line_tracking (LRU L1+L2, software prefetch, no hardware prefetcher)"],
        "branch_scenarios": ["all_predicted", "all_mispredicted", "exit_mispredicted (direction change)", "ids_mispredicted"],
        "functional_coverage": {
            "exact": "scalar integer ALU (add/sub/and/or/xor/cmp/test/mov/lea/inc/dec/neg/not/shl/shr/sar/imul), conditional branches, mask ops, int32 vector ops, f32/f64 add/sub/mul/FMA with single rounding and explicit rounding mode/FTZ/DAZ, f32/f64 compares to mask, dq<->ps conversions, masked loads/stores, broadcast, dword gather, vpermd",
            "timing_only": sorted(n for n, rec in isa.INSTRUCTIONS.items() if rec["fn"] is None and "alias_of" not in rec),
        },
        "not_implemented": [
            "any mnemonic outside the table (rejected, no default cost)",
            "swizzles other than {1toN} broadcasts; vloadunpack/vpackstore semantics; scatter semantics; x87 semantics",
            "transcendental approximations (vrcp23ps etc.) exact bit patterns",
            "the L2 hardware prefetcher; instruction cache and TLB effects; cross-core coherence traffic in core scale",
            "contexts communicating through memory (functional model runs contexts sequentially)",
            "C, Fortran, arbitrary assembly or binaries: no translation is attempted",
            "ABI, encodings, executable loading",
        ],
        "profiles": list_profiles(),
        "instructions": isa.capabilities_table(),
    }
    r["prediction"] = None
    r["capabilities"] = caps
    code = _finish(r, out, args, extra_print=["profiles: " + ", ".join(p["id"] for p in caps["profiles"])])
    cap_path = os.path.join(out, "capabilities.json")
    dump_json(caps, cap_path)
    return code


def cmd_selftest(args):
    import unittest
    args._t0 = time.time()
    out = _prepare_out(args, "selftest", "")
    tests_dir = resource_path("tests")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    loader = unittest.TestLoader()
    pattern = args.pattern or "test_*.py"
    suite = loader.discover(tests_dir, pattern=pattern, top_level_dir=tests_dir)
    import io
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    res = runner.run(suite)
    text = stream.getvalue()
    r = base_result("selftest", "ok" if res.wasSuccessful() else "error", "selftest", out_dir=out)
    r["prediction"] = None
    r["selftest"] = {"tests_run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
                     "note": "synthetic model tests; passing them is not validation against hardware"}
    with open(os.path.join(out, "unittest.log"), "w", encoding="utf-8") as f:
        f.write(text)
    r["artifacts"]["unittest_log"] = os.path.join(out, "unittest.log")
    r["message"] = "%d tests, %d failures, %d errors" % (res.testsRun, len(res.failures), len(res.errors))
    code = _finish(r, out, args)
    if not res.wasSuccessful():
        print(text[-4000:])
        return 1
    return code


def cmd_validate(args):
    args._t0 = time.time()
    out = _prepare_out(args, "validate", os.path.basename(args.kernel))
    r = base_result("validation", "ok", "validate", out_dir=out)
    try:
        kernel, h = _kernel_and_hash(args.kernel)
        r["input"] = {"path": os.path.abspath(args.kernel), "hash_sha256": h, "kernel": kernel.describe()}
        r["representation_evaluated"] = kernel.representation
        if args.profile:
            prof = load_profile(args.profile, args.overlay)
            r["profile"] = prof.describe()
            r["calibration_status"] = _calib(prof)
            missing = []
            for s in kernel.streams:
                for i in s.insns:
                    key = isa.CLASSES[i.cls]["latency"]
                    if key not in (None, "memory", "gather") and not prof.has(key):
                        missing.append({"instruction": i.id, "op": i.op, "parameter": key})
            if missing:
                r["message"] = "kernel is well-formed, but %d instruction(s) need parameters this profile leaves unknown" % len(missing)
                r["missing_parameters"] = missing
        r["unsupported"] = ["functional: %s (%s)" % (u["op"], u["note"]) for u in kernel.unsupported_functional()]
        for s in kernel.streams:
            r["assumptions"].extend(getattr(s, "asm_notes", []))
        r["message"] = r.get("message") or "kernel is well-formed: %d stream(s), %s" % (len(kernel.streams), kernel.representation)
        r["prediction"] = None
        return _finish(r, out, args)
    except TwinError as e:
        return _fail(r, out, args, e)


def _run_functional(kernel, args):
    interp, steps, check = fmod.run_functional(kernel, max_steps=args.max_steps, deadline=_deadline(args))
    return interp, steps, check


def cmd_functional(args):
    args._t0 = time.time()
    out = _prepare_out(args, "functional", os.path.basename(args.kernel))
    r = base_result("functional", "ok", "functional", out_dir=out, scale="region")
    try:
        kernel, h = _kernel_and_hash(args.kernel)
        r["input"] = {"path": os.path.abspath(kernel.path), "hash_sha256": h, "kernel": kernel.describe()}
        r["representation_evaluated"] = kernel.representation
        interp, steps, check = _run_functional(kernel, args)
        r["functional_check"] = check
        r["assumptions"].extend(interp.assumptions)
        r["prediction"] = {"dynamic_instructions": steps, "contexts": len(kernel.streams), "functional_check_status": check["status"],
                           "checked_items": check["checked"], "mismatches": len(check["mismatches"])}
        final = {str(c): interp.contexts[c].snapshot() for c in interp.contexts}
        dump_json(final, os.path.join(out, "final-state.json"))
        dump_json({"memory": interp.memory.snapshot()}, os.path.join(out, "final-memory.json"))
        if args.trace:
            dump_json({str(c): [e.to_dict() for e in evs] for c, evs in interp.traces.items()}, os.path.join(out, "trace.json"))
        r["artifacts"]["final_state"] = os.path.join(out, "final-state.json")
        if check["status"] == "mismatch":
            r["status"] = "functional_mismatch"
            r["prediction"] = None
            r["message"] = "%d mismatch(es) against expected outputs; first: %s" % (len(check["mismatches"]), json.dumps(check["mismatches"][0]))
        elif check["status"] == "not_specified":
            r["message"] = "executed %d dynamic instructions; no expected outputs were given, so nothing was checked" % steps
        else:
            r["message"] = "executed %d dynamic instructions; all %d expected items match" % (steps, check["checked"])
        return _finish(r, out, args)
    except TwinError as e:
        return _fail(r, out, args, e)


def _traces_for(kernel, args, r):
    """Dynamic traces per context, from functional execution or static unrolling."""
    if args.trace_source == "functional":
        interp, steps, check = _run_functional(kernel, args)
        r["functional_check"] = check
        r["assumptions"].extend(interp.assumptions)
        if check["status"] == "mismatch":
            raise FunctionalMismatch("candidate produced wrong results (%d mismatches); its timing is not reported as a valid result" % len(check["mismatches"]),
                                     {"first": check["mismatches"][0]})
        return interp.traces
    traces = {}
    for s in kernel.streams:
        evs, notes = tmod.static_trace(kernel, s, args.trip_count)
        traces[s.context] = evs
        r["assumptions"].extend(notes)
    r["functional_check"] = {"status": "not_run", "note": "static trace: results were not computed, so correctness is not established by this run"}
    return traces


def _select_contexts(kernel, traces, args):
    if args.contexts:
        wanted = [int(x) for x in args.contexts.split(",")]
        for w in wanted:
            if w not in traces:
                raise InvalidInput("--contexts names context %d which has no stream" % w)
        return {c: traces[c] for c in wanted}
    return traces


def cmd_simulate(args):
    args._t0 = time.time()
    out = _prepare_out(args, "simulate", os.path.basename(args.kernel))
    r = base_result("timing_prediction", "ok", "simulate", out_dir=out, scale=args.scale)
    prof = None
    try:
        if args.scale not in ("instruction", "region", "core"):
            raise Unsupported("simulate supports instruction, region and core scales; pair and card are analytical (use bounds --scale pair|card)")
        kernel, h = _kernel_and_hash(args.kernel)
        prof = load_profile(args.profile, args.overlay)
        r["profile"] = prof.describe()
        r["calibration_status"] = _calib(prof)
        r["input"] = {"path": os.path.abspath(kernel.path), "hash_sha256": h, "kernel": kernel.describe()}
        r["representation_evaluated"] = kernel.representation
        traces = _select_contexts(kernel, _traces_for(kernel, args, r), args)
        sim = timing.CoreSim(kernel, prof, traces, max_cycles=args.max_cycles, deadline=_deadline(args), record_issue=not args.no_issue_log)
        res = sim.run()
        r["assumptions"].extend(sim.assumptions)
        r["parameters_used"] = prof.used_summary()
        units = kernel.unit_count
        if len(traces) != len(kernel.streams):
            if kernel.unit_count % len(kernel.streams):
                raise InvalidInput("unit_of_work.count (%d) is not divisible by the number of streams (%d); cannot scale it to %d active context(s)" % (kernel.unit_count, len(kernel.streams), len(traces)))
            units = kernel.unit_count // len(kernel.streams) * len(traces)
            r["assumptions"].append("unit count scaled to the %d active context(s): %d of %d units" % (len(traces), units, kernel.unit_count))
        per_unit = res["completion_cycles"] / float(units)
        r["prediction"] = {"predicted_cycles": res["completion_cycles"], "predicted_cycles_per_unit": per_unit, "issue_span_cycles": res["issue_span_cycles"],
                           "unit_of_work": kernel.unit_of_work.get("description"), "unit_count": units,
                           "dynamic_instructions": res["dynamic_instructions"], "issue_events": res["issue_events"],
                           "core_issue_utilization": res["core_issue_utilization"], "pair_fraction": res["pair_fraction"],
                           "active_contexts": res["active_contexts"], "per_context": res["per_context"], "memory": res["memory"],
                           "kind": "timing_prediction_core_cycles"}
        r["limiting_constraints"] = timing.limiting_constraints(res)
        r["python_execution_seconds_simulation"] = res["python_seconds"]
        if sim.issue_log:
            dump_json(sim.issue_log, os.path.join(out, "issue-log.json"))
            r["artifacts"]["issue_log"] = os.path.join(out, "issue-log.json")
        r["message"] = "predicted %d core cycles (%.3f per unit) for %d dynamic instructions on %d context(s)%s" % (
            res["completion_cycles"], per_unit, res["dynamic_instructions"], len(res["active_contexts"]),
            "; SYNTHETIC profile" if prof.synthetic else "")
        return _finish(r, out, args)
    except TwinError as e:
        if prof is not None:
            r["parameters_used"] = prof.used_summary()
        return _fail(r, out, args, e)


def cmd_bounds(args):
    args._t0 = time.time()
    out = _prepare_out(args, "bounds", os.path.basename(args.kernel or args.params or "bounds"))
    r = base_result("analytical_bound", "ok", "bounds", out_dir=out, scale=args.scale)
    prof = None
    try:
        prof = load_profile(args.profile, args.overlay)
        r["profile"] = prof.describe()
        r["calibration_status"] = _calib(prof)
        if args.scale in ("pair", "card"):
            if not args.params:
                raise NeedsParameters("%s scale needs --params file.json (see references/analytic-scales.md)" % args.scale)
            params = load_json(args.params, "analytic params")
            r["input"] = {"path": os.path.abspath(args.params), "hash_sha256": sha256_of_obj(params)}
            r["result_type"] = "analytical_scenario_estimate"
            est = analytic.pair_estimate(prof, params) if args.scale == "pair" else analytic.card_estimate(prof, params)
            r["assumptions"].extend(est.pop("assumptions"))
            r["prediction"] = est
            r["parameters_used"] = prof.used_summary()
            r["message"] = "%s analytical scenario estimate (%d scenario(s)); not a cycle simulation" % (args.scale, len(est["scenarios"]))
            return _finish(r, out, args)
        if not args.kernel:
            raise InvalidInput("bounds at instruction/region/core scale needs a kernel")
        kernel, h = _kernel_and_hash(args.kernel)
        r["input"] = {"path": os.path.abspath(kernel.path), "hash_sha256": h, "kernel": kernel.describe()}
        r["representation_evaluated"] = kernel.representation
        assumptions = []

        def assume(t):
            if t not in assumptions:
                assumptions.append(t)
        if args.loop:
            body_events = None
            if args.trace_source == "functional":
                try:
                    traces = _traces_for(kernel, args, r)
                    body_events = {}
                    for c, evs in traces.items():
                        m = {}
                        for e in evs:
                            m.setdefault(e.insn.id, e)
                        body_events[c] = m
                except Unsupported:
                    body_events = None
            res = bmod.loop_bounds(kernel, prof, assume, body_events)
            r["prediction"] = res
            r["message"] = "loop lower bound: MII %d cycles/iteration (ResMII %d, RecMII %s), one-iteration critical path %d cycles" % (
                res["mii_cycles_per_iteration"], res["res_mii"], res["rec_mii"], res["iteration_critical_path_cycles"])
        else:
            traces = _select_contexts(kernel, _traces_for(kernel, args, r), args)
            res = bmod.trace_bounds(kernel, prof, traces, assume)
            r["prediction"] = res
            r["message"] = "trace lower bound: %d cycles (binding term: %s)" % (res["lower_bound_cycles"], res["binding_term"])
            if args.search:
                ctx = sorted(traces.keys())[0]
                if len(traces) != 1:
                    raise Unsupported("--search needs exactly one active context (use --contexts)")

                def factory(tr):
                    return timing.CoreSim(kernel, prof, tr, max_cycles=args.max_cycles, deadline=None, record_issue=False)
                sres = bmod.search_optimal_order(kernel, prof, traces, ctx, args.max_orders, _deadline(args), factory)
                sres["claim"] = ("proven optimum within the search space (dependency-preserving reorderings of this straight-line block, same instructions, same model)"
                                 if sres["space_exhausted"] else "best found; the search space was NOT exhausted, so no optimality claim")
                if sres["best_cycles"] is not None and sres["best_cycles"] == res["lower_bound_cycles"]:
                    sres["claim"] += "; matches the analytical lower bound"
                r["result_type"] = "search"
                r["search"] = sres
                r["message"] += "; reorder search: best %s cycles over %d orders (%s)" % (sres["best_cycles"], sres["orders_evaluated"], "exhausted" if sres["space_exhausted"] else "budget hit")
                if not sres["space_exhausted"]:
                    r["status"] = "budget_exhausted"
        r["assumptions"].extend(assumptions)
        r["parameters_used"] = prof.used_summary()
        return _finish(r, out, args)
    except TwinError as e:
        if prof is not None:
            r["parameters_used"] = prof.used_summary()
        return _fail(r, out, args, e)


def cmd_compare(args):
    args._t0 = time.time()
    out = _prepare_out(args, "compare", "")
    r = base_result("comparison", "ok", "compare", out_dir=out)
    try:
        a = load_json(args.baseline, "baseline result")
        b = load_json(args.candidate, "candidate result")
        r["input"] = {"baseline": os.path.abspath(args.baseline), "candidate": os.path.abspath(args.candidate),
                      "baseline_hash": sha256_of_file(args.baseline), "candidate_hash": sha256_of_file(args.candidate)}
        problems = []
        for key in ("engine_version", "result_type", "scale"):
            if a.get(key) != b.get(key):
                problems.append("%s differs: %r vs %r" % (key, a.get(key), b.get(key)))
        pa, pb = a.get("profile") or {}, b.get("profile") or {}
        if pa.get("hash") != pb.get("hash"):
            problems.append("profile hash differs (%s vs %s): the model changed between baseline and candidate" % ((pa.get("hash") or "")[:12], (pb.get("hash") or "")[:12]))
        ka, kb = (a.get("input") or {}).get("kernel") or {}, (b.get("input") or {}).get("kernel") or {}
        if ka.get("scenario") != kb.get("scenario"):
            problems.append("memory/branch scenario differs")
        if ka.get("unit_of_work") != kb.get("unit_of_work"):
            problems.append("unit of work differs: %r vs %r" % (ka.get("unit_of_work"), kb.get("unit_of_work")))
        if ka.get("numerical_policy") != kb.get("numerical_policy"):
            problems.append("numerical policy differs")
        for name, res in (("baseline", a), ("candidate", b)):
            if res.get("status") != "ok":
                problems.append("%s status is %s, not ok" % (name, res.get("status")))
            fc = (res.get("functional_check") or {}).get("status")
            if fc not in ("ok",):
                r["assumptions"].append("%s functional check: %s (its timing stands without a verified result)" % (name, fc))
        r["prediction"] = {"baseline_status": a.get("status"), "candidate_status": b.get("status"), "compatible": not problems}
        if problems:
            r["status"] = "incompatible"
            r["message"] = "results are not comparable: " + "; ".join(problems)
            r["incompatibilities"] = problems
            return _finish(r, out, args)
        pa_, pb_ = a.get("prediction") or {}, b.get("prediction") or {}
        rows = []
        for key in ("predicted_cycles", "predicted_cycles_per_unit", "issue_span_cycles", "lower_bound_cycles", "mii_cycles_per_iteration",
                    "iteration_critical_path_cycles", "dynamic_instructions", "issue_events", "core_issue_utilization", "pair_fraction"):
            if key in pa_ and key in pb_ and isinstance(pa_[key], (int, float)) and isinstance(pb_[key], (int, float)):
                base, cand = pa_[key], pb_[key]
                rows.append({"metric": key, "baseline": base, "candidate": cand, "delta": cand - base,
                             "ratio_candidate_over_baseline": (cand / base) if base else None})
        r["prediction"]["metrics"] = rows
        r["prediction"]["scenarios"] = rows
        assum_a, assum_b = set(a.get("assumptions") or []), set(b.get("assumptions") or [])
        r["prediction"]["assumptions_only_in_baseline"] = sorted(assum_a - assum_b)
        r["prediction"]["assumptions_only_in_candidate"] = sorted(assum_b - assum_a)
        main = next((x for x in rows if x["metric"] in ("predicted_cycles_per_unit", "lower_bound_cycles", "mii_cycles_per_iteration")), None)
        if main:
            r["message"] = "%s: baseline %s, candidate %s (ratio %.4f); same engine, profile and scenario" % (
                main["metric"], _fmt(main["baseline"]), _fmt(main["candidate"]), main["ratio_candidate_over_baseline"] or 0)
        else:
            r["message"] = "comparable results; no common numeric metric found"
        return _finish(r, out, args)
    except TwinError as e:
        return _fail(r, out, args, e)


def _fmt(v):
    return ("%.4f" % v) if isinstance(v, float) else str(v)


def cmd_prepare_native(args):
    args._t0 = time.time()
    out = _prepare_out(args, "prepare-native", os.path.basename(args.kernel))
    r = base_result("native_request", "ok", "prepare-native", out_dir=out, scale="core")
    try:
        kernel, h = _kernel_and_hash(args.kernel)
        prof = load_profile(args.profile, args.overlay)
        r["profile"] = prof.describe()
        r["calibration_status"] = _calib(prof)
        r["input"] = {"path": os.path.abspath(kernel.path), "hash_sha256": h, "kernel": kernel.describe()}
        r["representation_evaluated"] = kernel.representation
        if args.check:
            interp, steps, check = _run_functional(kernel, args)
            r["functional_check"] = check
            if check["status"] == "mismatch":
                raise FunctionalMismatch("kernel's expected outputs do not match the model; fix the kernel before requesting card time", {"first": check["mismatches"][0]})
        req = nmod.prepare_native(kernel, prof, out, h, args.prediction)
        r["prediction"] = None
        r["native_request"] = {"request_hash": req["request_hash_sha256"], "files": sorted(os.listdir(out))}
        r["assumptions"].append("prepare-native generated code without contacting any card; kernel.S and driver.c must be reviewed and built with the k1om toolchain by the queue operator")
        r["message"] = "native request written (hash %s...); nothing was executed on hardware" % req["request_hash_sha256"][:12]
        return _finish(r, out, args)
    except TwinError as e:
        return _fail(r, out, args, e)


def cmd_import_native(args):
    args._t0 = time.time()
    out = _prepare_out(args, "import-native", os.path.basename(args.measurement))
    r = base_result("imported_native_measurement", "ok", "import-native", out_dir=out)
    try:
        res = nmod.import_native(args.measurement, args.request, out, args.prediction)
        r["input"] = {"path": os.path.abspath(args.measurement), "hash_sha256": sha256_of_file(args.measurement)}
        r["prediction"] = None
        r["imported"] = res
        r["message"] = "imported native measurement %s (%d result rows)%s%s" % (
            res["measurement"]["job_id"], len(res["measurement"]["results"]),
            "; overlay profile written" if res["overlay_written"] else "; no parameters to overlay",
            "; compared with prediction" if res["comparison"] else "")
        if res["comparison"]:
            r["prediction"] = {"kind": "prediction_vs_native", "scenarios": res["comparison"]["rows"]}
        return _finish(r, out, args)
    except TwinError as e:
        return _fail(r, out, args, e)


# --- parser --------------------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(prog="knc_twin.py", description="knc-twin %s: Knights Corner functional/timing twin (standard library only)" % ENGINE_VERSION)
    p.add_argument("--version", action="version", version="knc-twin %s" % ENGINE_VERSION)
    sub = p.add_subparsers(dest="cmd")
    sub.required = True

    def common(sp, profile=True, kernel=True, budgets=True):
        sp.add_argument("--out", help="output directory (one per experiment; default knc-twin-runs/<stamp>-<cmd>-<name>)")
        sp.add_argument("--force", action="store_true", help="allow a non-empty output directory")
        sp.add_argument("--json", action="store_true", help="print result.json to stdout")
        if profile:
            sp.add_argument("--profile", default="card-7120-measured", help="profile id or path (default card-7120-measured)")
            sp.add_argument("--overlay", action="append", default=[], help="overlay profile path (repeatable), e.g. an imported calibration")
        if kernel:
            sp.add_argument("kernel", help="kernel JSON (knc-twin.kernel/1)")
        if budgets:
            sp.add_argument("--max-steps", type=int, default=None, help="functional step budget (default kernel.max_steps or 200000)")
            sp.add_argument("--max-cycles", type=int, default=2000000, help="simulated cycle budget")
            sp.add_argument("--max-seconds", type=float, default=120.0, help="python wall-time budget")

    s = sub.add_parser("capabilities", help="what is implemented, unsupported, and which profiles exist")
    common(s, profile=False, kernel=False, budgets=False)
    s.set_defaults(fn=cmd_capabilities)

    s = sub.add_parser("selftest", help="run the bundled unit tests")
    common(s, profile=False, kernel=False, budgets=False)
    s.add_argument("--pattern", default=None)
    s.set_defaults(fn=cmd_selftest)

    s = sub.add_parser("validate", help="check a kernel file (and optionally the parameters a profile can supply)")
    common(s, budgets=False)
    s.set_defaults(fn=cmd_validate, profile=None)

    s = sub.add_parser("functional", help="execute the kernel exactly and check expected outputs")
    common(s, profile=False)
    s.add_argument("--trace", action="store_true", help="also write trace.json")
    s.set_defaults(fn=cmd_functional)

    s = sub.add_parser("simulate", help="predict core cycles for the kernel")
    common(s)
    s.add_argument("--scale", default="core", choices=SCALES)
    s.add_argument("--trace-source", default="functional", choices=("functional", "static"))
    s.add_argument("--trip-count", type=int, default=None, help="override kernel.loop.trip_count for static traces")
    s.add_argument("--contexts", default=None, help="comma-separated contexts to activate (default: all streams)")
    s.add_argument("--no-issue-log", action="store_true")
    s.set_defaults(fn=cmd_simulate)

    s = sub.add_parser("bounds", help="analytical lower bounds (core), loop MII (--loop), reorder search (--search), pair/card scenarios (--scale pair|card --params)")
    common(s, kernel=False)
    s.add_argument("kernel", nargs="?", default=None)
    s.add_argument("--scale", default="core", choices=SCALES)
    s.add_argument("--params", default=None, help="analytic parameters JSON for pair/card scales")
    s.add_argument("--loop", action="store_true", help="per-iteration ResMII/RecMII/critical path for kernel.loop")
    s.add_argument("--search", action="store_true", help="exhaustive dependency-preserving reorder search (one context, <= 12 instructions)")
    s.add_argument("--max-orders", type=int, default=20000)
    s.add_argument("--trace-source", default="functional", choices=("functional", "static"))
    s.add_argument("--trip-count", type=int, default=None)
    s.add_argument("--contexts", default=None)
    s.set_defaults(fn=cmd_bounds)

    s = sub.add_parser("compare", help="compare two result.json files (same engine, profile hash, scenario)")
    common(s, profile=False, kernel=False, budgets=False)
    s.add_argument("baseline")
    s.add_argument("candidate")
    s.set_defaults(fn=cmd_compare)

    s = sub.add_parser("prepare-native", help="export a reproducible request for the shared hardware queue (no card connection)")
    common(s)
    s.add_argument("--prediction", default=None, help="result.json of the simulate run to compare against later")
    s.add_argument("--no-check", dest="check", action="store_false", help="skip the functional self-check before export")
    s.set_defaults(fn=cmd_prepare_native)

    s = sub.add_parser("import-native", help="validate a native measurement file; write a calibration overlay; compare with a prediction")
    common(s, profile=False, kernel=False, budgets=False)
    s.add_argument("measurement")
    s.add_argument("--request", default=None, help="request.json the measurement answers")
    s.add_argument("--prediction", default=None, help="result.json of the prediction to compare")
    s.set_defaults(fn=cmd_import_native)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except InvalidInput as e:
        print("invalid_input: %s" % e.message, file=sys.stderr)
        return e.exit_code
    except TwinError as e:
        print("%s: %s" % (e.status, e.message), file=sys.stderr)
        return e.exit_code
