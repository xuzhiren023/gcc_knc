#!/usr/bin/env python3
"""Record finite cold-read scenarios, without treating them as native validation.

All output paths are stable. Full CLI results stay in --out; the small record
under tests/heldout_native describes predictions and still-missing comparisons.
This does not use the analytical card fixtures as simulated GEMV/STREAM kernels.
"""
import argparse
import json
from pathlib import Path

from knc_model import cli
from stage_multicore import kernel


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--record", required=True)
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for scale in ("unit", "ring"):
        for count in (1, 2, 4, 8):
            name = "%s-%d-cold-read" % (scale, count)
            raw = kernel(name, cores=count, lines=64)
            raw["provenance"] = {
                "description": "Synthetic finite cold read; not a compiled STREAM or GEMV measurement",
                "role": "scenario prediction; independent native validation pending"}
            path = out / (name + ".json")
            path.write_text(json.dumps(raw, indent=2) + "\n")
            result_dir = out / name
            code = cli.main(["simulate", str(path), "--scale", scale,
                             "--max-seconds", "300", "--out", str(result_dir)])
            result = json.loads((result_dir / "result.json").read_text())
            if code:
                return code
            pred = result["prediction"]
            records.append({
                "name": name, "scale": scale, "detailed_cores": count,
                "lines_per_core": 64, "contexts_per_core": 1,
                "status": result["status"],
                "functional_check": result["functional_check"],
                "predicted_cycles": pred["predicted_cycles"],
                "mean_per_core_cycles": sum(c["predicted_cycles"] for c in pred["cores"]) / count,
                "detailed_useful_bytes": pred["detailed_useful_bytes"],
                "detailed_bytes_per_cycle": pred["detailed_bytes_per_cycle"],
                "symmetry_full_card_bytes_per_cycle": pred.get("symmetry_full_card_bytes_per_cycle"),
                "background": pred["background"],
                "result_class": pred["result_class"],
                "assumptions": result["assumptions"],
                "unsupported": result["unsupported"],
                "limiting_constraints": result["limiting_constraints"],
                "calibration_status": result["calibration_status"],
                "parameters_used": result["parameters_used"]})
    record = Path(args.record)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({
        "schema": "knc-twin.multicore-scenarios/1",
        "description": "Finite synthetic predictions, not measured bandwidth or held-out accuracy rows",
        "engineering_target_pct": 10,
        "native_comparisons": "pending; see references/validation.md, multicore section",
        "scenarios": records}, indent=2) + "\n")
    print("recorded %d scenario predictions; no native validation claimed" % len(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
