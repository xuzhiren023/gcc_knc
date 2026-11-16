"""result.json and summary.md writers."""
import os
import sys

from . import ENGINE_VERSION, RESULT_SCHEMA
from .util import dump_json, utc_now_iso

RESULT_TYPES = ("functional", "timing_prediction", "analytical_bound", "analytical_scenario_estimate",
                "imported_native_measurement", "capabilities", "comparison", "native_request", "validation", "selftest", "search",
                "program_rollup", "calibration_plan")


def base_result(result_type, status, command, profile=None, kernel=None, input_path=None, input_hash=None, scale=None, out_dir=None):
    assert result_type in RESULT_TYPES, result_type
    r = {
        "schema": RESULT_SCHEMA,
        "result_type": result_type,
        "status": status,
        "engine_version": ENGINE_VERSION,
        "timestamp_utc": utc_now_iso(),
        "invocation": {"argv": list(sys.argv), "cwd": os.getcwd(), "python": sys.version.split()[0], "command": command},
        "scale": scale,
        "artifacts": {"output_dir": os.path.abspath(out_dir) if out_dir else None},
        "assumptions": [],
        "unsupported": [],
        "limiting_constraints": [],
        "python_execution_seconds": None,
    }
    if profile is not None:
        r["profile"] = profile.describe()
        r["calibration_status"] = dict(profile.calibration, synthetic=profile.synthetic,
                                       note="Simulated/analytical outputs are model results, never native measurements. "
                                            + ("This profile is SYNTHETIC." if profile.synthetic else ""))
    else:
        r["profile"] = None
        r["calibration_status"] = None
    if kernel is not None:
        r["input"] = {"path": os.path.abspath(kernel.path) if kernel.path else None, "hash_sha256": input_hash, "kernel": kernel.describe()}
        r["representation_evaluated"] = kernel.representation
    elif input_path is not None:
        r["input"] = {"path": os.path.abspath(input_path), "hash_sha256": input_hash}
        r["representation_evaluated"] = None
    else:
        r["input"] = None
        r["representation_evaluated"] = None
    r["functional_check"] = {"status": "not_run"}
    return r


def _fmt_val(v):
    if isinstance(v, float):
        return "%.6g" % v
    return str(v)


def summary_markdown(r):
    L = []
    L.append("# knc-twin %s: %s" % (r["result_type"], r["status"].upper()))
    L.append("")
    L.append("- Engine %s, %s" % (r["engine_version"], r["timestamp_utc"]))
    if r.get("profile"):
        p = r["profile"]
        L.append("- Profile %s v%s (hash %s...)%s" % (p["id"], p["version"], p["hash"][:12], " **SYNTHETIC**" if p["synthetic"] else ""))
        cs = r.get("calibration_status") or {}
        L.append("- Calibration: %s. %s" % (cs.get("state"), cs.get("statement", "")))
    if r.get("input"):
        L.append("- Input %s (sha256 %s...)" % (r["input"].get("path"), (r["input"].get("hash_sha256") or "")[:12]))
    if r.get("scale"):
        L.append("- Scale: %s; representation: %s" % (r["scale"], r.get("representation_evaluated")))
    fc = r.get("functional_check") or {}
    L.append("- Functional check: %s%s" % (fc.get("status"), (" (%d mismatches)" % len(fc["mismatches"])) if fc.get("mismatches") else ""))
    if r.get("message"):
        L.append("")
        L.append("**%s**" % r["message"])
    if r.get("error_details"):
        L.append("")
        L.append("Details: `%s`" % r["error_details"])
    pred = r.get("prediction")
    if pred:
        L.append("")
        L.append("## Result")
        if pred.get("result_class"):
            classification = pred["result_class"]
            L.append("- result_class: %s" % classification.get("class", classification))
        for k, v in pred.items():
            if isinstance(v, (dict, list)):
                continue
            L.append("- %s: %s" % (k, _fmt_val(v)))
        for key in ("predicted_cycles_per_unit_band", "predicted_cycles_band",
                    "predicted_time_ratio_band", "predicted_candidate_per_unit_band"):
            if key in pred:
                L.append("- %s: %s to %s" % (key, *pred[key]))
        if pred.get("sampling"):
            sample = pred["sampling"]
            L.extend(["", "## Loop sampling (estimate)", "",
                      "Stop: %s after %s iterations; %s warmup iterations discarded." %
                      (sample["stop_reason"], sample["iterations_sampled"], sample["warmup_iterations"]),
                      "Rule: %s." % sample["rule"], "",
                      "| first iteration | last iteration | iterations | predicted cycles/iteration |",
                      "|---:|---:|---:|---:|"])
            for window in sample["windows"]:
                L.append("| %s | %s | %s | %.6g |" % (window["first_iteration"], window["last_iteration"],
                                                       window["iterations"], window["cycles_per_iteration"]))
        if pred.get("phases"):
            L.extend(["", "## Phases", "",
                      "| phase | share of program time | covered fraction of phase | predicted time ratio | band | result class |",
                      "|---|---:|---:|---:|---|---|"])
            for phase in pred["phases"]:
                L.append("| %s | %.1f%% | %.1f%% | %.5f | %.5f to %.5f | %s |" % (
                    phase["name"], 100 * phase["share"], 100 * phase["modeled_share_of_phase_time"],
                    phase["predicted_time_ratio"], *phase["predicted_time_ratio_band"], phase["result_class"]["class"]))
            if all("predicted_candidate_per_unit" in phase for phase in pred["phases"]):
                L.extend(["", "Phase contributions in %s:" % pred["unit"], "",
                          "| phase | measured baseline | predicted candidate | band |", "|---|---:|---:|---|"])
                for phase in pred["phases"]:
                    L.append("| %s | %.6g | %.6g | %.6g to %.6g |" % (
                        phase["name"], phase["measured_baseline_per_unit"], phase["predicted_candidate_per_unit"],
                        *phase["predicted_candidate_per_unit_band"]))
        if isinstance(pred.get("terms"), dict):
            L.append("")
            L.append("| bound term | cycles |")
            L.append("|---|---:|")
            for k, v in sorted(pred["terms"].items(), key=lambda kv: -kv[1]):
                L.append("| %s | %s |" % (k, v))
        if isinstance(pred.get("scenarios"), list):
            L.append("")
            keys = [k for k in pred["scenarios"][0].keys()]
            L.append("| " + " | ".join(keys) + " |")
            L.append("|" + "---|" * len(keys))
            for s in pred["scenarios"]:
                L.append("| " + " | ".join(_fmt_val(s[k]) for k in keys) + " |")
        if isinstance(pred.get("per_context"), dict):
            L.append("")
            L.append("| context | " + " | ".join(k for k in next(iter(pred["per_context"].values())).keys() if not isinstance(next(iter(pred["per_context"].values()))[k], (dict, list))) + " |")
            first = next(iter(pred["per_context"].values()))
            keys = [k for k in first.keys() if not isinstance(first[k], (dict, list))]
            L[-1] = "| context | " + " | ".join(keys) + " |"
            L.append("|" + "---|" * (len(keys) + 1))
            for c, d in sorted(pred["per_context"].items()):
                L.append("| %s | " % c + " | ".join(_fmt_val(d.get(k)) for k in keys) + " |")
    if r.get("limiting_constraints"):
        L.append("")
        L.append("## Limiting constraints")
        for c in r["limiting_constraints"]:
            L.append("- " + ", ".join("%s=%s" % (k, v) for k, v in c.items()))
    if r.get("assumptions"):
        L.append("")
        L.append("## Assumptions")
        for a in r["assumptions"]:
            L.append("- " + a)
    if r.get("unsupported"):
        L.append("")
        L.append("## Unsupported / not modeled")
        for u in r["unsupported"]:
            L.append("- " + (u if isinstance(u, str) else str(u)))
    if r.get("parameters_used"):
        L.append("")
        L.append("## Parameters consulted")
        L.append("| parameter | value | status | unit |")
        L.append("|---|---|---|---|")
        for k, v in r["parameters_used"].items():
            L.append("| %s | %s | %s | %s |" % (k, _fmt_val(v["value"]), v["status"], v["unit"]))
    L.append("")
    L.append("Invocation: `%s`" % " ".join(r["invocation"]["argv"]))
    L.append("Artifacts: %s" % r["artifacts"].get("output_dir"))
    if r.get("python_execution_seconds") is not None:
        L.append("Python execution time: %.3f s (not KNC time)" % r["python_execution_seconds"])
    return "\n".join(L) + "\n"


def write_result(out_dir, r):
    os.makedirs(out_dir, exist_ok=True)
    rp = os.path.join(out_dir, "result.json")
    sp = os.path.join(out_dir, "summary.md")
    r["artifacts"]["result_json"] = os.path.abspath(rp)
    r["artifacts"]["summary_md"] = os.path.abspath(sp)
    dump_json(r, rp)
    with open(sp, "w", encoding="utf-8") as f:
        f.write(summary_markdown(r))
    return rp, sp
