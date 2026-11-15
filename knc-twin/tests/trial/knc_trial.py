#!/usr/bin/env python3
"""S13-06 trial runner: convert each case with from_gcc_s.py, run the twin, check and record.

    python knc_trial.py [--out DIR]           run every trial case, write results.json

Library for tests/regress/test_knc_twin.py: load_cases, check_case, predict_heldout. The held-out
cases themselves belong to scripts/validate_heldout.py (one harness); predict_heldout delegates to it.
Every number written here comes from a twin run with status ok; predictions are model cycles.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TWIN = HERE.parents[1]
SCRIPTS = TWIN / "scripts"
sys.path.insert(0, str(SCRIPTS))

import from_gcc_s  # noqa: E402
import validate_heldout  # noqa: E402


def load_cases(trial_dir=HERE):
    out = []
    for p in sorted((Path(trial_dir) / "cases").glob("*.json")):
        case = json.loads(p.read_text(encoding="utf-8"))
        case["_dir"] = str(Path(trial_dir))
        out.append(case)
    return out


def _source(case):
    return str((Path(case["_dir"]) / case["source"]).resolve())


def convert(case, tmp):
    """(report, kernel path or None)."""
    report, kernel = from_gcc_s.convert_loop(_source(case), case["loop"], case.get("function"), case.get("spec"),
                                        case.get("contexts", 1))
    path = None
    if kernel is not None:
        path = Path(tmp) / (case["name"] + ".kernel.json")
        path.write_text(json.dumps(kernel, indent=1), encoding="utf-8")
    return report, path


def twin(args, out):
    """Run one twin command into a fresh directory; return result.json."""
    out = Path(out)
    proc = subprocess.run([sys.executable, str(SCRIPTS / "knc_twin.py")] + [str(a) for a in args] + ["--out", str(out), "--force"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    result = out / "result.json"
    if not result.exists():
        raise RuntimeError("twin %s wrote no result.json (exit %d): %s" % (args[0], proc.returncode, proc.stdout[-1500:]))
    return json.loads(result.read_text(encoding="utf-8"))


def check_case(case, tmp):
    """What the regress test compares with case['expect']."""
    report, kernel = convert(case, tmp)
    got = {"conversion": report["status"]}
    if report["unsupported"]:
        got["unsupported_lines"] = [u["line"] for u in report["unsupported"]]
    if kernel is not None:
        got["functional"] = twin(["functional", kernel], Path(tmp) / (case["name"] + "-functional"))["status"]
    if got.get("unsupported_lines") and "unsupported_lines" not in case["expect"]:
        got.pop("unsupported_lines")
    return got


def _simulate_summary(r, contexts):
    if r["status"] != "ok":
        return {"status": r["status"], "message": r["message"]}
    p = r["prediction"]
    return {"status": "ok", "contexts": len(contexts), "predicted_cycles": p["predicted_cycles"],
            "cycles_per_unit_core": p["predicted_cycles_per_unit"],
            "cycles_per_unit_per_thread": round(p["predicted_cycles_per_unit"] * len(contexts), 4),
            "pair_fraction": p.get("pair_fraction"), "limiting": r.get("limiting_constraints")}


def run_case(case, tmp):
    """Every run the case asks for; returns a summary for results.json."""
    report, kernel = convert(case, tmp)
    out = {"name": case["name"], "kind": case["kind"], "source": case["source"], "loop": case["loop"],
           "lines": report["lines"], "conversion": report["status"], "unsupported": report["unsupported"]}
    if case.get("measured"):
        out["measured"] = case["measured"]
    if kernel is None:
        return out, None
    base = Path(tmp) / case["name"]
    f = twin(["functional", kernel], str(base) + "-functional")
    out["functional"] = {"status": f["status"], "message": f["message"]}
    trace = ["--trace-source", case.get("trace_source", "functional")]
    sims = {}
    results = {}
    for ctxs in case.get("simulate", []):
        key = ",".join(str(c) for c in ctxs)
        r = twin(["simulate", kernel, "--contexts", key] + trace, "%s-sim-%d" % (base, len(ctxs)))
        sims[str(len(ctxs))] = _simulate_summary(r, ctxs)
        results[len(ctxs)] = "%s-sim-%d/result.json" % (base, len(ctxs))
        if r["status"] == "ok":
            out.setdefault("engine_version", r["engine_version"])
            out.setdefault("profile_hash", r["profile"]["hash"])
    out["simulate"] = sims
    if case.get("bounds_loop"):
        b = twin(["bounds", kernel, "--loop"] + trace, str(base) + "-bounds")
        if b["status"] == "ok":
            p = b["prediction"]
            out["bounds_loop"] = {"status": "ok", "mii_cycles_per_iteration": p["mii_cycles_per_iteration"], "res_mii": p["res_mii"],
                                  "rec_mii": p["rec_mii"], "binding": p["binding"], "critical_path": p["iteration_critical_path_cycles"]}
        else:
            out["bounds_loop"] = {"status": b["status"], "message": b["message"]}
    if case.get("measured"):
        rows = []
        for threads, value in sorted(case["measured"]["threads"].items()):
            s = sims.get(threads)
            pred = s["cycles_per_unit_per_thread"] if s and s["status"] == "ok" else None
            rows.append({"threads": int(threads), "measured_ticks": value, "predicted_cycles": pred,
                         "ratio": round(pred / value, 3) if pred else None})
        out["consistency"] = rows
    return out, results


def predict_heldout(case_dir, tmp):
    """Re-run the prediction a held-out case records in prediction.json (scripts/validate_heldout.py owns it)."""
    return validate_heldout.predict_case(Path(case_dir), tmp=str(tmp))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="directory for twin outputs (default: a temporary one)")
    a = ap.parse_args(argv)
    tmp = Path(a.out) if a.out else Path(tempfile.mkdtemp(prefix="knc-trial-"))
    tmp.mkdir(parents=True, exist_ok=True)
    cases, paths = [], {}
    for case in load_cases():
        summary, results = run_case(case, tmp)
        cases.append(summary)
        paths[case["name"]] = results
        print("%-22s conversion %-11s functional %-11s %s" % (case["name"], summary["conversion"],
              summary.get("functional", {}).get("status", "-"),
              " ".join("%sctx=%s" % (k, v.get("cycles_per_unit_per_thread", v["status"])) for k, v in summary.get("simulate", {}).items())))
    compares = []
    for case in load_cases():
        other = case.get("compare_with")
        if other and paths.get(case["name"]) and paths.get(other):
            r = twin(["compare", Path(paths[other][1]), Path(paths[case["name"]][1])], tmp / ("compare-" + case["name"]))
            compares.append({"baseline": other, "candidate": case["name"], "contexts": 1, "status": r["status"],
                             "message": r["message"], "deltas": r.get("prediction")})
    results = {"schema": "knc-twin.trial-results/1", "cases": cases, "compare": compares,
               "heldout": "scripts/validate_heldout.py --cases tests/heldout_native (references/validation.md)"}
    with open(str(HERE / "results.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(results, indent=1) + "\n")
    print("results:", HERE / "results.json", "outputs:", tmp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
