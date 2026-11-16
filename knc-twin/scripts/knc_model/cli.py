"""Command-line entry: capabilities, selftest, validate, functional, simulate, bounds, compare,
batch, prepare-native, import-native."""
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
from .kernel import load_kernel, Kernel
from .report import base_result, write_result
from . import functional as fmod
from . import trace as tmod
from . import timing
from . import bounds as bmod
from . import analytic
from . import native as nmod

SCALES = ("instruction", "region", "core", "pair", "card")
BATCH_SCHEMA = "knc-twin.batch/1"


def _calib(prof):
    return dict(prof.calibration, synthetic=prof.synthetic,
                note="Simulated/analytical outputs are model results, never native measurements. " + ("This profile is SYNTHETIC." if prof.synthetic else ""))


def memory_result_class(kind, kernel, prof, mem_stats=None, scenario=None):
    """Every timing/memory number is one of: conditional_bound, unvalidated_scenario_estimate, calibrated_forecast.
    A formula is never a bound by itself; a forecast is calibrated only when a held-out validation case covers
    the kernel's declared shape in this profile."""
    if kind == "bound":
        return {"class": "conditional_bound", "conditions": "valid under the model's resource and latency assumptions listed in 'assumptions'; a bound on this model, not a hardware guarantee"}
    shape = (kernel.raw.get("provenance") or {}).get("shape") if kernel is not None else None
    validated = (prof.calibration or {}).get("validated_shapes", {}) if prof is not None else {}
    if shape and shape in validated:
        v = validated[shape]
        return {"class": "calibrated_forecast", "shape": shape, "evidence": v}
    reason = []
    if shape:
        reason.append("declared shape %r has no held-out validation in profile %s" % (shape, prof.id if prof else "?"))
    else:
        reason.append("the kernel declares no provenance.shape, so no held-out validation can vouch for it")
    if scenario:
        sm = scenario.get("memory", {})
        if sm.get("type") in ("fixed_level", "classified"):
            reason.append("memory levels are asserted by the scenario (%s)" % sm.get("type"))
        if sm.get("type") == "line_tracking":
            reason.append("TLB, L2 hardware prefetcher and memory service sub-models are part of the memory domain (scenario: %s)" % ", ".join(
                "%s=%s" % (sub, sm.get(sub, "auto")) for sub in ("tlb", "hardware_prefetcher", "memory_service")))
    if mem_stats and (mem_stats.get("l2_hits") or mem_stats.get("memory")):
        reason.append("the trace misses L1 (%d L2, %d memory accesses): cache behaviour is modeled, not validated" % (mem_stats.get("l2_hits", 0), mem_stats.get("memory", 0)))
    return {"class": "unvalidated_scenario_estimate", "reasons": reason}


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
    r["prediction"] = None
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
            "region": "implemented: function or loop regions from GCC-KNC assembly (scripts/from_gcc_s.py) or hand-written records, 1-4 contexts; functional execution, timing, bounds, exhaustive reorder search (<= 12 instructions)",
            "core": "implemented: 1-4 in-order contexts, U/V pairing rules, same-context issue spacing, round-robin picker, x87 stack with physical-register dependencies, AGI, demand-miss stalls, nonblocking prefetch, outstanding-miss limit, L1/L2 LRU line tracking, optional first-level DTLB, streaming L2 hardware prefetcher and per-core memory service sub-models, gather/scatter/x87/L2-prefetch occupancy",
            "pair": "analytical scenario only (two cores exchanging lines over the ring); needs core-scale cycles and transfer counts as parameters",
            "card": "analytical scenario only (compute vs bandwidth roofline with barriers and imbalance); never one-core throughput x cores",
        },
        "commands": ["capabilities", "selftest", "validate", "functional", "simulate", "bounds", "compare", "batch", "prepare-native", "import-native"],
        "adapters": ["scripts/from_gcc_s.py: GCC-KNC / GCC 5.1.1 k1om assembly -> records (function or loop regions, data symbols, coverage audit)",
                     "scripts/from_binary.py: objects/ELF listings -> whole functions, relocated switches, loop regions and complete per-line reports",
                     "scripts/validate_heldout.py: held-out validation against the gcc_knc characterization catalog"],
        "input_representations": ["normalized-records (JSON, knc-twin.kernel/1)", "gas-att-subset (GAS AT&T assembly, see references/input-format.md)"],
        "memory_scenarios": ["fixed_level", "classified", "line_tracking (LRU L1+L2, software prefetch; optional tlb/hardware_prefetcher/memory_service sub-models)"],
        "memory_result_classes": ["conditional_bound (bounds command)", "unvalidated_scenario_estimate (simulate without a validated shape; every pair/card total)", "calibrated_forecast (simulate on a kernel whose declared provenance.shape has a held-out validation entry in the profile)"],
        "branch_scenarios": ["all_predicted", "all_mispredicted", "exit_mispredicted (direction change)", "ids_mispredicted"],
        "functional_coverage": {
            "exact": "scalar integer ALU (8/16/32/64-bit, flags, adc/sbb/setcc/bt/movsx/movzx/cltq/cqto/idiv/imul/push/pop/leave), conditional branches, mask ops, int32 and int64-logic vector ops, f32/f64 add/sub/subr/mul/max/min/FMA with single rounding and explicit rounding mode/FTZ/DAZ, compares to mask, blends, conversions (dq<->ps, pd->dq, ps<->pd, round), register swizzles, broadcasts, up/down conversions (float16/uint8/sint8/uint16/sint16), masked loads/stores, vloadunpack/vpackstore halves, dword/qword gather and scatter with completion masks, vpermd/vpermf32x4, x87 stack with extended precision, control word (RC/PC), fld/fst/fild/fistp/fxch/fchs/fabs/fsqrt/fcom/fnstsw/fldcw",
            "timing_only": sorted(n for n, rec in isa.INSTRUCTIONS.items() if rec["fn"] is None and "alias_of" not in rec),
        },
        "not_implemented": [
            "any mnemonic outside the table (rejected, no default cost); call/ret are region boundaries",
            "vrcp23ps/vrsqrt23ps exact bit patterns without opt-in captured tables; vlog2ps/vexp223ps exact bit patterns",
            "second-level TLB and page walks; the instruction cache; cross-core coherence traffic in core scale; card-level bandwidth sharing",
            "contexts communicating through memory (functional model runs contexts sequentially)",
            "C, Fortran or binaries: no translation is attempted; ABI, encodings, executable loading",
            "symbolic immediates (addresses of labels), TLS @gottpoff operands, rep/lock prefixes other than 'rep ret' and 'lock add'",
        ],
        "profiles": list_profiles(),
        "instructions": isa.capabilities_table(),
    }
    r["prediction"] = None
    r["capabilities"] = caps
    code = _finish(r, out, args, extra_print=["profiles: " + ", ".join(p["id"] for p in caps["profiles"])])
    dump_json(caps, os.path.join(out, "capabilities.json"))
    return code


def cmd_selftest(args):
    import unittest
    import io
    args._t0 = time.time()
    out = _prepare_out(args, "selftest", "")
    tests_dir = resource_path("tests")
    loader = unittest.TestLoader()
    pattern = args.pattern or "test_*.py"
    suite = loader.discover(tests_dir, pattern=pattern, top_level_dir=tests_dir)
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    res = runner.run(suite)
    text = stream.getvalue()
    r = base_result("selftest", "ok" if res.wasSuccessful() else "error", "selftest", out_dir=out)
    r["prediction"] = None
    r["selftest"] = {"tests_run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
                     "note": "synthetic model tests and oracle checks; passing them is not validation against hardware"}
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
                    occ = isa.CLASSES[i.cls].get("occupancy")
                    if occ and not prof.has(occ):
                        missing.append({"instruction": i.id, "op": i.op, "parameter": occ})
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
        if interp.heap_allocations:
            r["prediction"]["heap_allocations"] = interp.heap_allocations
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
        args._interp = interp
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
    if getattr(args, "contexts", None):
        wanted = [int(x) for x in args.contexts.split(",")]
        for w in wanted:
            if w not in traces:
                raise InvalidInput("--contexts names context %d which has no stream" % w)
        return {c: traces[c] for c in wanted}
    return traces


def _simulate_core(kernel, prof, args, r):
    """Shared by simulate and batch: traces, simulation, prediction block."""
    traces = _select_contexts(kernel, _traces_for(kernel, args, r), args)
    sim = timing.CoreSim(kernel, prof, traces, max_cycles=args.max_cycles, deadline=_deadline(args), record_issue=not getattr(args, "no_issue_log", False))
    res = sim.run()
    r["assumptions"].extend(sim.assumptions)
    units = kernel.unit_count
    if len(traces) != len(kernel.streams):
        if kernel.unit_count % len(kernel.streams):
            raise InvalidInput("unit_of_work.count (%d) is not divisible by the number of streams (%d); cannot scale it to %d active context(s)" % (kernel.unit_count, len(kernel.streams), len(traces)))
        units = kernel.unit_count // len(kernel.streams) * len(traces)
        r["assumptions"].append("unit count scaled to the %d active context(s): %d of %d units" % (len(traces), units, kernel.unit_count))
    per_unit = res["completion_cycles"] / float(units)
    pred = {"predicted_cycles": res["completion_cycles"], "predicted_cycles_per_unit": per_unit, "issue_span_cycles": res["issue_span_cycles"],
            "unit_of_work": kernel.unit_of_work.get("description"), "unit_count": units,
            "dynamic_instructions": res["dynamic_instructions"], "issue_events": res["issue_events"],
            "core_issue_utilization": res["core_issue_utilization"], "pair_fraction": res["pair_fraction"],
            "active_contexts": res["active_contexts"], "per_context": res["per_context"], "memory": res["memory"],
            "kind": "timing_prediction_core_cycles"}
    pred["frontend"] = res.get("frontend")
    if res["stub_costs"]:
        pred["stub_cycles_total"] = res["stub_cycles_total"]
        pred["stub_calls"] = {n: dict(cost, cycles_each=kernel.calls[n].get("cycles"),
                                    cycles_per_byte=kernel.calls[n].get("cycles_per_byte", 0),
                                    model=kernel.calls[n].get("model", "none"),
                                    status=kernel.calls[n].get("status", "assumed"),
                                    source=kernel.calls[n].get("source"))
                              for n, cost in sorted(res["stub_costs"].items())}
    interp = getattr(args, "_interp", None)
    args._interp = None
    if interp is not None:
        if interp.input_files:
            pred["input_files"] = interp.input_files
        if interp.heap_allocations:
            pred["heap_allocations"] = [a for a in interp.heap_allocations if a["context"] in traces]
        approx = sorted(interp.approximate_stubs) + sorted(interp.approximate_instructions)
        pred["functional_exactness"] = "exact" if not approx else "approximate: %s are not bit-exact (stub or approximate instruction)" % ", ".join(approx)
        if interp.approximate_instructions:
            pred["approximate_instructions"] = sorted(interp.approximate_instructions)
    pred["result_class"] = memory_result_class("simulate", kernel, prof, res["memory"].get("stats"), kernel.scenario)
    if res["stub_costs"] and pred["result_class"]["class"] == "calibrated_forecast":
        pred["result_class"] = {"class": "unvalidated_scenario_estimate", "reasons": ["the region calls costed stubs (%s): their cycles are inputs, not validated model output" % ", ".join(sorted(res["stub_costs"]))]}
    return sim, res, pred


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
        sim, res, pred = _simulate_core(kernel, prof, args, r)
        r["parameters_used"] = prof.used_summary()
        r["prediction"] = pred
        r["limiting_constraints"] = timing.limiting_constraints(res)
        r["python_execution_seconds_simulation"] = res["python_seconds"]
        if sim.issue_log:
            dump_json(sim.issue_log, os.path.join(out, "issue-log.json"))
            r["artifacts"]["issue_log"] = os.path.join(out, "issue-log.json")
        r["message"] = "predicted %d core cycles (%.3f per unit) for %d dynamic instructions on %d context(s); %s%s" % (
            res["completion_cycles"], pred["predicted_cycles_per_unit"], res["dynamic_instructions"], len(res["active_contexts"]),
            pred["result_class"]["class"], "; SYNTHETIC profile" if prof.synthetic else "")
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
            est["result_class"] = {"total": "unvalidated_scenario_estimate",
                                   "memory_term": "conditional_bound given the stated sustained bandwidth (a byte-count over a measured or declared rate)" if args.scale == "card" else "unvalidated_scenario_estimate",
                                   "note": "no pair/card prediction has been compared with a native run"}
            r["prediction"] = est
            r["parameters_used"] = prof.used_summary()
            r["message"] = "%s analytical scenario estimate (%d scenario(s)); not a cycle simulation; unvalidated_scenario_estimate" % (args.scale, len(est["scenarios"]))
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
            r["message"] = "loop lower bound over the STATIC body (every instruction of the loop body once, both arms of a branch): MII %d cycles/iteration (ResMII %d, RecMII %s), one-iteration critical path %d cycles; conditional_bound" % (
                res["mii_cycles_per_iteration"], res["res_mii"], res["rec_mii"], res["iteration_critical_path_cycles"])
        else:
            traces = _select_contexts(kernel, _traces_for(kernel, args, r), args)
            res = bmod.trace_bounds(kernel, prof, traces, assume)
            r["prediction"] = res
            r["message"] = "trace lower bound: %d cycles (binding term: %s); conditional_bound" % (res["lower_bound_cycles"], res["binding_term"])
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
        r["prediction"]["result_class"] = memory_result_class("bound", kernel, prof)
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
            r["prediction"] = None
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
        r["prediction"]["result_class"] = {"baseline": (pa_.get("result_class") or {}).get("class"), "candidate": (pb_.get("result_class") or {}).get("class"),
                                           "note": "a ranking between two unvalidated estimates is itself unvalidated; see the held-out ranking reliability in references/validation.md"}
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


def cmd_batch(args):
    """Evaluate a candidate batch off-card with a frozen model profile; rank; send uncertain cases to the queue."""
    args._t0 = time.time()
    out = _prepare_out(args, "batch", os.path.basename(args.manifest))
    r = base_result("comparison", "ok", "batch", out_dir=out, scale="core")
    prof = None
    try:
        man = load_json(args.manifest, "batch manifest")
        if man.get("schema") != BATCH_SCHEMA:
            raise InvalidInput("batch manifest schema must be %r" % BATCH_SCHEMA)
        base_dir = os.path.dirname(os.path.abspath(args.manifest))
        prof = load_profile(man.get("profile", args.profile), list(man.get("overlays", [])) + list(args.overlay or []))
        r["profile"] = prof.describe()
        r["calibration_status"] = _calib(prof)
        frozen = man.get("frozen_profile_hash")
        if frozen and frozen != prof.hash:
            raise InvalidInput("manifest freezes profile hash %s... but the loaded profile hashes to %s...; the model changed, so the batch is not comparable with earlier runs" % (frozen[:12], prof.hash[:12]))
        r["input"] = {"path": os.path.abspath(args.manifest), "hash_sha256": sha256_of_obj(man)}
        cands = man.get("candidates") or []
        if not cands:
            raise InvalidInput("manifest has no candidates")
        too_close = float(man.get("too_close_fraction", 0.05))
        rows = []
        queue = []
        for c in cands:
            name = c.get("name") or os.path.basename(c["kernel"])
            kpath = c["kernel"] if os.path.isabs(c["kernel"]) else os.path.join(base_dir, c["kernel"])
            row = {"name": name, "kernel": kpath, "status": "ok", "message": None, "uncertain": False}
            cargs = argparse.Namespace(**vars(args))
            cargs.trace_source = c.get("trace_source", "functional")
            cargs.trip_count = c.get("trip_count")
            cargs.contexts = c.get("contexts")
            cargs.no_issue_log = True
            sub = {"assumptions": [], "functional_check": {"status": "not_run"}}
            try:
                kernel, h = _kernel_and_hash(kpath)
                if c.get("shape"):
                    kernel.raw.setdefault("provenance", {})["shape"] = c["shape"]
                row["kernel_hash"] = h
                sim, res, pred = _simulate_core(kernel, prof, cargs, sub)
                row.update({"predicted_cycles": pred["predicted_cycles"], "predicted_cycles_per_unit": pred["predicted_cycles_per_unit"],
                            "functional_check": sub["functional_check"]["status"], "result_class": pred["result_class"]["class"],
                            "limiting": [x.get("constraint") for x in timing.limiting_constraints(res)[:2]],
                            "memory": {k: res["memory"]["stats"].get(k) for k in ("l1_hits", "l2_hits", "memory", "prefetches", "tlb_misses")},
                            "unit_of_work": pred["unit_of_work"]})
                try:
                    tr = _select_contexts(kernel, fmod.run_functional(kernel)[0].traces, cargs)
                    b = bmod.trace_bounds(kernel, prof, tr, lambda t: None)
                    row["lower_bound_cycles"] = b["lower_bound_cycles"]
                    row["gap_to_bound"] = round(pred["predicted_cycles"] / float(b["lower_bound_cycles"]), 3) if b["lower_bound_cycles"] else None
                except TwinError:
                    pass
                mem = row["memory"]
                if row["result_class"] == "unvalidated_scenario_estimate" and (mem.get("l2_hits") or mem.get("memory")):
                    row["uncertain"] = True
                    row["message"] = "memory behaviour beyond L1 is modeled, not validated"
            except TwinError as e:
                row["status"] = e.status
                row["message"] = e.message
                row["uncertain"] = True
            rows.append(row)
        ok_rows = [x for x in rows if x["status"] == "ok"]
        ok_rows.sort(key=lambda x: x["predicted_cycles_per_unit"])
        baseline_name = man.get("baseline")
        base_row = next((x for x in ok_rows if x["name"] == baseline_name), None)
        for i, x in enumerate(ok_rows):
            x["rank"] = i + 1
            if base_row:
                x["ratio_to_baseline"] = round(x["predicted_cycles_per_unit"] / base_row["predicted_cycles_per_unit"], 4)
                if x is not base_row and abs(x["ratio_to_baseline"] - 1.0) < too_close:
                    x["uncertain"] = True
                    x["message"] = ((x.get("message") or "") + "; " if x.get("message") else "") + "within %.0f%% of the baseline: too close for the model to rank" % (100 * too_close)
        if man.get("queue_uncertain", True):
            for x in rows:
                if x["uncertain"]:
                    qdir = os.path.join(out, "queue", re.sub(r"[^A-Za-z0-9_.-]+", "_", x["name"]))
                    try:
                        kernel, h = _kernel_and_hash(x["kernel"])
                        os.makedirs(qdir, exist_ok=True)
                        nmod.prepare_native(kernel, prof, qdir, h, None)
                        x["queue_request"] = qdir
                        queue.append(x["name"])
                    except TwinError as e:
                        x["queue_request_error"] = "%s: %s" % (e.status, e.message)
        r["prediction"] = {"kind": "batch_ranking", "profile_hash": prof.hash, "candidates": rows, "ranking": [x["name"] for x in ok_rows],
                           "baseline": baseline_name, "queued_for_native": queue,
                           "result_class": {"ranking": "unvalidated_scenario_estimate unless every ranked candidate is a calibrated_forecast; see references/validation.md for the measured ranking reliability of this model"}}
        r["parameters_used"] = prof.used_summary()
        r["message"] = "%d candidates: %d ranked, %d not evaluable, %d sent to the native queue (%s)" % (
            len(rows), len(ok_rows), len(rows) - len(ok_rows), len(queue), ", ".join(queue) if queue else "none")
        L = ["# Batch %s" % man.get("name", os.path.basename(args.manifest)), "", "Profile %s hash %s (frozen: %s). Every number is a model output." % (prof.id, prof.hash[:12], "yes" if frozen else "no"), "",
             "| rank | candidate | status | cycles/unit | ratio to baseline | class | functional | limiting | bound gap | uncertain -> queue |", "|---:|---|---|---:|---:|---|---|---|---:|---|"]
        for x in sorted(rows, key=lambda y: (y.get("rank") or 999)):
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                x.get("rank", "-"), x["name"], x["status"] if x["status"] == "ok" else "%s: %s" % (x["status"], (x["message"] or "")[:80]),
                ("%.3f" % x["predicted_cycles_per_unit"]) if x.get("predicted_cycles_per_unit") is not None else "-",
                x.get("ratio_to_baseline", "-"), x.get("result_class", "-"), x.get("functional_check", "-"), ", ".join(x.get("limiting", [])),
                x.get("gap_to_bound", "-"), ("yes -> " + os.path.basename(x["queue_request"])) if x.get("queue_request") else ("yes" if x["uncertain"] else "no")))
        with open(os.path.join(out, "batch.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(L) + "\n")
        r["artifacts"]["batch_md"] = os.path.join(out, "batch.md")
        return _finish(r, out, args, extra_print=L[4:])
    except TwinError as e:
        return _fail(r, out, args, e)


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

def cmd_rollup(args):
    """Program-level roll-up: per-region predicted ratios weighted by each region's measured share of run time."""
    from . import rollup as rmod
    args._t0 = time.time()
    out = _prepare_out(args, "rollup", os.path.basename(args.manifest))
    r = base_result("program_rollup", "ok", "rollup", out_dir=out, scale="region")
    try:
        m = rmod.load_rollup(args.manifest)
        base_dir = os.path.dirname(os.path.abspath(args.manifest))
        prof = load_profile(m.get("profile", args.profile), args.overlay)
        if m.get("frozen_profile_hash") and m["frozen_profile_hash"] != prof.hash:
            raise InvalidInput("the manifest freezes profile hash %s... but %s resolves to %s...; rerun with the frozen profile or re-freeze the manifest" % (
                m["frozen_profile_hash"][:12], prof.id, prof.hash[:12]))
        r["profile"] = prof.describe()
        r["calibration_status"] = _calib(prof)
        r["input"] = {"path": os.path.abspath(args.manifest), "hash_sha256": sha256_of_obj(m), "manifest": {k: m.get(k) for k in ("name", "program", "card")}}
        band_default = float(m.get("unvalidated_band_pct", rmod.DEFAULT_UNVALIDATED_BAND_PCT))
        regions = []
        for reg in m["regions"]:
            row = {"name": reg["name"], "share": float(reg["share"]), "share_source": reg.get("share_source")}
            sides = {}
            for side in ("baseline", "candidate"):
                if reg.get(side) is None:
                    continue
                kpath = os.path.join(base_dir, reg[side])
                sub = {"assumptions": []}
                try:
                    kernel, h = _kernel_and_hash(kpath)
                    sim, res, pred = _simulate_core(kernel, prof, args, sub)
                    sides[side] = {"status": "ok", "kernel": reg[side], "kernel_hash": h, "cycles_per_unit": pred["predicted_cycles_per_unit"],
                                   "result_class": pred["result_class"], "limiting": timing.limiting_constraints(res)[:2]}
                    for a in sub["assumptions"]:
                        if a not in r["assumptions"]:
                            r["assumptions"].append(a)
                except TwinError as e:
                    sides[side] = {"status": e.status, "kernel": reg[side], "message": e.message}
            row.update(sides)
            if "candidate" not in sides:
                row.update(ratio=1.0, band_pct=0.0, note="no candidate: region unchanged")
            elif sides["baseline"]["status"] == "ok" and sides["candidate"]["status"] == "ok":
                row["ratio"] = sides["candidate"]["cycles_per_unit"] / sides["baseline"]["cycles_per_unit"]
                b1, basis1 = rmod.band_of(sides["baseline"]["result_class"], band_default)
                b2, basis2 = rmod.band_of(sides["candidate"]["result_class"], band_default)
                row["band_pct"] = max(b1, b2)
                row["band_basis"] = basis1 if b1 >= b2 else basis2
            else:
                bad = [s for s in ("baseline", "candidate") if sides[s]["status"] != "ok"]
                row.update(ratio=None, note="not modeled (%s): %s" % (", ".join(bad), "; ".join(sides[s]["message"] for s in bad)[:300]))
            regions.append(row)
        usable = [x for x in regions if x.get("ratio") is not None]
        skipped = [x for x in regions if x.get("ratio") is None]
        bw = None
        card = m.get("card")
        if card:
            bw = prof.get_sub("card.sustained_bandwidth_gbs", card.get("traffic", "read_modify_write"))
        summary = rmod.combine(usable, m.get("program"), card, bw)
        summary["regions_not_modeled"] = [{"name": x["name"], "share": x["share"], "reason": x["note"]} for x in skipped]
        summary["result_class"] = {"class": "calibrated_forecast" if usable and all(x.get("band_basis", "").startswith("held-out") or x["ratio"] == 1.0 for x in usable) and not skipped
                                   else "unvalidated_scenario_estimate",
                                   "note": "a ranking aid for compiler or loop changes; the program's final speed is a card measurement"}
        summary["kind"] = "program_rollup"
        r["prediction"] = dict(summary, regions=regions)
        r["parameters_used"] = prof.used_summary()
        lines = ["%-40s share %5.1f%%  ratio %s  band +/-%s%%" % (x["name"][:40], 100 * x["share"], ("%.4f" % x["ratio"]) if x.get("ratio") is not None else "not modeled",
                                                                 ("%.0f" % x["band_pct"]) if x.get("band_pct") is not None else "-") for x in regions]
        lines.append("modeled share %.1f%%; predicted time ratio %.4f (band %.4f to %.4f)" % (100 * summary["modeled_share_of_run_time"], summary["predicted_time_ratio"],
                                                                                              summary["predicted_time_ratio_band"][0], summary["predicted_time_ratio_band"][1]))
        if "predicted_candidate_per_unit" in summary:
            lines.append("%s: measured baseline %s -> predicted %s (band %s to %s)" % (summary["unit"], summary["measured_baseline_per_unit"], summary["predicted_candidate_per_unit"],
                                                                                         summary["predicted_candidate_per_unit_band"][0], summary["predicted_candidate_per_unit_band"][1]))
        r["message"] = "program roll-up over %d region(s) covering %.1f%% of measured run time: predicted time ratio %.4f; %s" % (
            len(usable), 100 * summary["modeled_share_of_run_time"], summary["predicted_time_ratio"], summary["result_class"]["class"])
        if skipped:
            r["unsupported"].extend("%s: %s" % (x["name"], x["note"]) for x in skipped)
        return _finish(r, out, args, lines)
    except TwinError as e:
        return _fail(r, out, args, e)


def cmd_calibration_plan(args):
    """What to measure in the next card window (no card connection)."""
    from . import rollup as rmod
    args._t0 = time.time()
    out = _prepare_out(args, "calibration-plan", args.profile)
    r = base_result("calibration_plan", "ok", "calibration-plan", out_dir=out, scale="core")
    try:
        prof = load_profile(args.profile, args.overlay)
        r["profile"] = prof.describe()
        r["calibration_status"] = _calib(prof)
        plan = rmod.plan_for(prof)
        counts = prof.status_counts()
        not_measured = sorted(n for n, p in prof.params.items() if p.status in ("assumed", "derived", "unknown", "literature"))
        plan["parameters_not_measured"] = not_measured
        r["prediction"] = plan
        dump_json(plan, os.path.join(out, "calibration-plan.json"))
        r["artifacts"]["plan"] = os.path.join(out, "calibration-plan.json")
        open_items = [it for it in plan["microbenchmarks"] if it["state"] == "open"]
        lines = ["%-18s %s" % (it["id"], it["settles"]) for it in open_items]
        lines.append("%d open microbenchmarks; %d parameters of %s are not measured (%s)" % (len(open_items), len(not_measured), prof.id,
                                                                                            ", ".join("%s %d" % kv for kv in sorted(counts.items()))))
        r["message"] = "%d staged microbenchmarks open for %s; %d open misses; see calibration-plan.json" % (len(open_items), prof.id, len(plan["open_misses"]))
        return _finish(r, out, args, lines)
    except TwinError as e:
        return _fail(r, out, args, e)


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
            sp.add_argument("--max-cycles", type=int, default=20000000, help="simulated cycle budget")
            sp.add_argument("--max-seconds", type=float, default=120.0, help="python wall-time budget")

    s = sub.add_parser("capabilities", help="what is implemented, unsupported, and which profiles exist")
    common(s, profile=False, kernel=False, budgets=False)
    s.set_defaults(fn=cmd_capabilities)

    s = sub.add_parser("selftest", help="run the bundled unit tests")
    common(s, profile=False, kernel=False, budgets=False)
    s.add_argument("--pattern", default=None)
    s.set_defaults(fn=cmd_selftest)

    s = sub.add_parser("validate", help="check a kernel file (and the parameters a profile can supply)")
    common(s, budgets=False)
    s.set_defaults(fn=cmd_validate)

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

    s = sub.add_parser("batch", help="evaluate and rank a candidate batch off-card with a frozen profile; uncertain cases get native requests")
    common(s, kernel=False)
    s.add_argument("manifest", help="batch manifest JSON (knc-twin.batch/1)")
    s.set_defaults(fn=cmd_batch)

    s = sub.add_parser("rollup", help="weight per-region predictions by measured time shares: predicted change of a program-level figure (e.g. seconds per step)")
    common(s, kernel=False)
    s.add_argument("manifest", help="rollup manifest JSON (knc-twin.rollup/1)")
    s.set_defaults(fn=cmd_rollup, trace_source="functional", trip_count=None, contexts=None, no_issue_log=True)

    s = sub.add_parser("calibration-plan", help="what to measure in the next card window: staged microbenchmarks, open misses, held-out cases to add")
    common(s, kernel=False, budgets=False)
    s.set_defaults(fn=cmd_calibration_plan)

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
