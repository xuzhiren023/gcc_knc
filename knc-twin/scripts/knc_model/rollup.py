"""Program-level roll-up and the calibration plan.

rollup            weight per-region predictions by each region's measured share of run time and
                  report the predicted change of a program-level figure (for example seconds per
                  step). It ranks compiler or loop changes; it does not replace the measurement.
calibration_plan  what to measure in the next card window: the staged microbenchmarks that settle
                  uncertain parameters, the open misses, and the held-out cases to add.
"""
import math

from .errors import InvalidInput
from .sampling import options as sampling_options
from .util import load_json, resource_path

ROLLUP_SCHEMA = "knc-twin.rollup/1"
PLAN_SCHEMA = "knc-twin.calibration-plan/1"
DEFAULT_UNVALIDATED_BAND_PCT = 30.0


def load_rollup(path):
    m = load_json(path, "rollup manifest")
    if m.get("schema") != ROLLUP_SCHEMA:
        raise InvalidInput("rollup manifest schema must be %r" % ROLLUP_SCHEMA)
    if ("regions" in m) == ("phases" in m):
        raise InvalidInput("rollup manifest needs either regions or phases, not both")
    if "phases" in m:
        _shares(m["phases"], "phases", ("name", "share", "regions"))
        for phase in m["phases"]:
            _regions(phase["regions"], "phase %s regions" % phase["name"])
    else:
        _regions(m["regions"], "regions")
    return m


def _shares(rows, where, required):
    if not isinstance(rows, list) or not rows:
        raise InvalidInput("%s must be a non-empty list" % where)
    total = 0.0
    names = set()
    for i, r in enumerate(rows):
        for k in required:
            if not isinstance(r, dict) or k not in r:
                raise InvalidInput("%s[%d] needs %r" % (where, i, k))
        if not isinstance(r["name"], str) or not r["name"] or r["name"] in names:
            raise InvalidInput("%s names must be nonempty and unique" % where)
        names.add(r["name"])
        share = r["share"]
        if isinstance(share, bool) or not isinstance(share, (int, float)) or not math.isfinite(share) or not 0 < share <= 1:
            raise InvalidInput("%s[%d].share must be a finite fraction in (0, 1]" % (where, i))
        total += float(r["share"])
    if total > 1.0 + 1e-9:
        raise InvalidInput("%s shares sum to %.3f, more than the whole" % (where, total))


def _regions(regions, where):
    _shares(regions, where, ("name", "share", "baseline"))
    for region in regions:
        for side in ("baseline", "candidate"):
            if side in region and (not isinstance(region[side], str) or not region[side]):
                raise InvalidInput("region %s.%s must name a kernel file" % (region["name"], side))
        sampling = region.get("sampling", {})
        if not isinstance(sampling, dict) or set(sampling) - {"baseline", "candidate"}:
            raise InvalidInput("region sampling must contain baseline/candidate options")
        for side, config in sampling.items():
            if side not in region:
                raise InvalidInput("sampling.%s has no kernel" % side)
            sampling_options(config)


def region_specs(manifest):
    if "regions" in manifest:
        return manifest["regions"]
    return [dict(region, phase=phase["name"], share_within_phase=float(region["share"]),
                 share=float(phase["share"]) * float(region["share"]))
            for phase in manifest["phases"] for region in phase["regions"]]


def result_class(regions, skipped=()):
    """calibrated_forecast only when at least one region has a candidate, every candidate region's band comes
    from a held-out shape, no region is sampled and nothing was skipped (S14-15 rule plus S14-12's sampled exclusion).
    A manifest with no candidates, or with only ratio-1.0 regions, is never calibrated."""
    candidates = [r for r in regions if "candidate" in r]
    calibrated = bool(regions) and bool(candidates) and not skipped and all(
        not r.get("sampled") and ("candidate" not in r or str(r.get("band_basis", "")).startswith("held-out"))
        for r in regions)
    return {"class": "calibrated_forecast" if calibrated else "unvalidated_scenario_estimate",
            "note": "a ranking aid for compiler or loop changes; the program's final speed is a card measurement"}


def phase_results(manifest, regions):
    phases = []
    for phase in manifest.get("phases", []):
        rows = [dict(r, share=r["share_within_phase"]) for r in regions if r.get("phase") == phase["name"]]
        program = dict(manifest.get("program", {}))
        if program.get("measured_per_unit") is not None:
            program["measured_per_unit"] *= phase["share"]
        combined = combine([r for r in rows if r.get("ratio") is not None], program)
        combined["modeled_share_of_phase_time"] = combined.pop("modeled_share_of_run_time")
        phases.append(dict(combined, name=phase["name"], share=phase["share"],
                           share_source=phase.get("share_source"), result_class=result_class(rows)))
    return phases


def band_of(result_class, default_pct):
    """(band_pct, basis) for one region's predicted ratio."""
    if result_class.get("class") == "calibrated_forecast":
        ev = result_class.get("evidence", {})
        pct = ev.get("ratio_error_pct", ev.get("worst_abs_error_pct", default_pct))
        return float(pct), "held-out validation of shape %s" % result_class.get("shape")
    return float(default_pct), "unvalidated shape: default band"


def combine(regions, program, card=None, bandwidth=None):
    """regions: [{name, share, ratio, band_pct, ...}] -> program-level ratio with a band.
    Each region's time scales by its ratio; the unmodeled remainder is unchanged."""
    modeled = sum(r["share"] for r in regions)
    mid = (1.0 - modeled) + sum(r["share"] * r["ratio"] for r in regions)
    def band(r):
        if "ratio_band" in r:
            return r["ratio_band"]
        if r["ratio"] == 1.0:
            return [1.0, 1.0]
        return [max(0.0, r["ratio"] * (1.0 - r["band_pct"] / 100.0)),
                r["ratio"] * (1.0 + r["band_pct"] / 100.0)]
    lo = (1.0 - modeled) + sum(r["share"] * band(r)[0] for r in regions)
    hi = (1.0 - modeled) + sum(r["share"] * band(r)[1] for r in regions)
    out = {"modeled_share_of_run_time": round(modeled, 4), "unmodeled_share_assumed_unchanged": round(1.0 - modeled, 4),
           "predicted_time_ratio": round(mid, 5), "predicted_time_ratio_band": [round(lo, 5), round(hi, 5)],
           "predicted_speedup": round(1.0 / mid, 5) if mid > 0 else None}
    base = (program or {}).get("measured_per_unit")
    if base is not None:
        out["unit"] = program.get("unit", "seconds per step")
        out["measured_baseline_per_unit"] = base
        out["predicted_candidate_per_unit"] = round(base * mid, 6)
        out["predicted_candidate_per_unit_band"] = [round(base * lo, 6), round(base * hi, 6)]
    if card and bandwidth:
        # bytes each unit must move through memory cannot go faster than the card's sustained bandwidth
        floor = card["bytes_per_unit"] / (bandwidth * 1e9)
        out["memory_floor_per_unit"] = round(floor, 6)
        out["memory_floor_basis"] = "bytes_per_unit / sustained bandwidth (%s GB/s, traffic %s): a formula on the profile's bandwidth entry, not a simulation of the ring or the memory controllers" % (bandwidth, card.get("traffic"))
        if base is not None and base * mid < floor:
            out["predicted_candidate_per_unit_capped"] = round(floor, 6)
            out["binding"] = "card memory bandwidth"
    return out


def load_plan():
    return load_json(resource_path("references", "calibration-plan.json"), "calibration plan")


def plan_for(profile, validation_bar=None):
    """Plan items with the profile's current value and status filled in."""
    plan = load_plan()
    items = []
    for it in plan["microbenchmarks"]:
        cur = []
        for name in it.get("parameters", []):
            try:
                p = profile.param(name)
                cur.append({"parameter": name, "value": p.value, "status": p.status})
            except Exception:
                cur.append({"parameter": name, "value": None, "status": "not in profile"})
        settled = cur and all(c["status"] == "measured" for c in cur)
        items.append(dict(it, current=cur, state="settled" if settled else "open"))
    return {"schema": PLAN_SCHEMA, "profile": profile.id, "habit": plan["habit"], "microbenchmarks": items,
            "open_misses": plan["open_misses"], "held_out_additions": plan["held_out_additions"],
            "other_cards": plan["other_cards"], "decision_bar": plan["decision_bar"]}
