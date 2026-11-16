"""Program-level roll-up and the calibration plan.

rollup            weight per-region predictions by each region's measured share of run time and
                  report the predicted change of a program-level figure (for example seconds per
                  step). It ranks compiler or loop changes; it does not replace the measurement.
calibration_plan  what to measure in the next card window: the staged microbenchmarks that settle
                  uncertain parameters, the open misses, and the held-out cases to add.
"""
from .errors import InvalidInput
from .util import load_json, resource_path

ROLLUP_SCHEMA = "knc-twin.rollup/1"
PLAN_SCHEMA = "knc-twin.calibration-plan/1"
DEFAULT_UNVALIDATED_BAND_PCT = 30.0


def load_rollup(path):
    m = load_json(path, "rollup manifest")
    if m.get("schema") != ROLLUP_SCHEMA:
        raise InvalidInput("rollup manifest schema must be %r" % ROLLUP_SCHEMA)
    regions = m.get("regions")
    if not isinstance(regions, list) or not regions:
        raise InvalidInput("rollup manifest needs a non-empty 'regions' list")
    total = 0.0
    for i, r in enumerate(regions):
        for k in ("name", "share", "baseline"):
            if k not in r:
                raise InvalidInput("regions[%d] needs %r" % (i, k))
        if not 0 < float(r["share"]) <= 1:
            raise InvalidInput("regions[%d].share must be a fraction of measured run time in (0, 1]" % i)
        total += float(r["share"])
    if total > 1.0 + 1e-9:
        raise InvalidInput("region shares sum to %.3f, more than the whole run" % total)
    return m


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
    lo = (1.0 - modeled) + sum(r["share"] * r["ratio"] * (1.0 - r["band_pct"] / 100.0) for r in regions if r["ratio"] != 1.0) + sum(r["share"] for r in regions if r["ratio"] == 1.0)
    hi = (1.0 - modeled) + sum(r["share"] * r["ratio"] * (1.0 + r["band_pct"] / 100.0) for r in regions if r["ratio"] != 1.0) + sum(r["share"] for r in regions if r["ratio"] == 1.0)
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
