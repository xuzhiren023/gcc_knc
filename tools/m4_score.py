"""Pure host-side M4 scoring and report routing; see proposed ADR-0015.

Input pairs are (old_seconds, new_seconds), already validated by the runner.
The runner owns launch order, equal work, correctness, environment validation,
and sealed-directory ACLs. This module neither runs programs nor grants ACLs.
"""

import json
import math
from pathlib import Path
import random
from statistics import median


PROGRAMS = (
    "gemm", "atax", "cholesky", "ludcmp", "jacobi-2d", "heat-3d",
    "adi", "durbin", "stream", "npb-cg", "npb-ep", "npb-mg", "npb-is",
    "hpcg", "zlib", "sqlite", "bzip2",
)
MODELS = ("7120", "3100", "5100")
SEALED_ROOT = Path(__file__).resolve().parents[2] / "_shared" / "m4-sealed"


def regression_status(lower, upper):
    """Classify a time-ratio interval against the strict >1.05 rule."""
    if not (0 < lower <= upper < math.inf):
        raise ValueError("invalid time-ratio interval")
    if upper <= 1.05:
        return "clear"
    if lower > 1.05:
        return "regression"
    return "unresolved"


def _ratios(pairs):
    if len(pairs) not in (6, 12):
        raise ValueError("expected six initial pairs or all twelve extended pairs")
    ratios = []
    for old, new in pairs:
        if not (0 < old < math.inf and 0 < new < math.inf):
            raise ValueError("durations must be finite and positive")
        ratio = old / new
        if not (0 < ratio < math.inf and 0 < 1 / ratio < math.inf):
            raise ValueError("unrepresentable pair ratio")
        ratios.append(ratio)
    return ratios


def _percentile(ordered, fraction):
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def _bootstrap(series, seed, draws):
    if not isinstance(draws, int) or draws < 1:
        raise ValueError("bootstrap draws must be a positive integer")
    rng = random.Random(seed)
    programs = [[] for _ in series]
    corpus = []
    for _ in range(draws):
        values = []
        for ratios, samples in zip(series, programs):
            value = median([ratios[rng.randrange(len(ratios))]
                            for _ in ratios])
            samples.append(value)
            values.append(value)
        corpus.append(median(values))
    return [sorted(samples) for samples in programs], sorted(corpus)


def _program_result(ratios, bootstrap):
    speedup = median(ratios)
    low = _percentile(bootstrap, .025)
    high = _percentile(bootstrap, .975)
    time_interval = [1 / high, 1 / low]
    return {
        "pair_speedups": ratios,
        "pair_time_ratios": [1 / ratio for ratio in ratios],
        "speedup": speedup,
        "time_ratio": 1 / speedup,
        "speedup_ci95": [low, high],
        "time_ratio_ci95": time_interval,
        "regression": regression_status(*time_interval),
    }


def score_program(pairs, *, seed=1514, draws=10000):
    """Median paired speedup and percentile interval for one program."""
    ratios = _ratios(pairs)
    programs, _ = _bootstrap([ratios], seed, draws)
    return _program_result(ratios, programs[0])


def score_model(rows, *, known_causes=None, seed=1514, draws=10000):
    """Score all 17 primary programs; causes must already be lead-reviewed.

    Nondefault seed/draws are for host diagnostics, not an ADR-0015 gate.
    A result always carries held_out=True so publishing requires sealed output.
    """
    if set(rows) != set(PROGRAMS):
        raise ValueError("a model requires exactly the frozen 17 programs")
    known_causes = known_causes or {}
    if not set(known_causes).issubset(PROGRAMS):
        raise ValueError("unknown program in regression review")
    ratios = [_ratios(rows[name]) for name in PROGRAMS]
    if len({len(values) for values in ratios}) != 1:
        raise ValueError("extension must include every program")
    boot_programs, boot_corpus = _bootstrap(ratios, seed, draws)
    programs = {}
    reviewed = True
    for name, values, samples in zip(PROGRAMS, ratios, boot_programs):
        result = _program_result(values, samples)
        cause = known_causes.get(name, "")
        if not isinstance(cause, str):
            raise ValueError("known causes must be reviewed reference strings")
        result["known_cause"] = cause
        status = result["regression"]
        reviewed &= (status == "clear" or
                     (status == "regression" and bool(cause.strip())))
        programs[name] = result
    lower = _percentile(boot_corpus, .05)
    upper = _percentile(boot_corpus, .975)
    estimate = median([programs[name]["speedup"] for name in PROGRAMS])
    return {
        "held_out": True,
        "programs": programs,
        "pairs": len(ratios[0]),
        "seed": seed,
        "draws": draws,
        "median_speedup": estimate,
        "time_ratio": 1 / estimate,
        "lower95": lower,
        "speedup_ci95": [_percentile(boot_corpus, .025), upper],
        "inconclusive": (lower < 1.25 <= upper or
                         any(p["regression"] == "unresolved" for p in programs.values())),
        "pass": lower >= 1.25 and reviewed,
    }


def score_models(rows, *, known_causes=None, seed=1514, draws=10000):
    """All three models must independently pass the primary-track gate."""
    if set(rows) != set(MODELS):
        raise ValueError("expected full 7120 and both 3100/5100 profiles")
    known_causes = known_causes or {}
    models = {name: score_model(rows[name], known_causes=known_causes.get(name),
                                seed=seed, draws=draws) for name in MODELS}
    if len({model["pairs"] for model in models.values()}) != 1:
        raise ValueError("extension must include every model")
    return {"held_out": True, "models": models,
            "pass": all(model["pass"] for model in models.values()),
            "extend": (models["7120"]["pairs"] == 6 and
                       any(model["inconclusive"] for model in models.values()))}


def write_report(report, destination, *, held_out, ready, passed):
    """Write details, returning ONLY public readiness/pass status.

    Caller marks any held-out diagnostic; full score reports mark themselves.
    Lead-provisioned ACLs on destination and ancestors are a prerequisite.
    Canonical routing handles traversal/symlinks, not hostile concurrent changes
    to directories: ACLs must also prevent untrusted writers.
    """
    destination = Path(destination).resolve()
    if held_out or report.get("held_out", False):
        try:
            destination.relative_to(SEALED_ROOT.resolve())
        except ValueError:
            raise ValueError("held-out report requires sealed output") from None
    # Do not create directories with accidentally public permissions.
    with destination.open("w", encoding="utf-8") as output:
        json.dump(report, output, allow_nan=False, indent=2)
        output.write("\n")
    return {"ready": bool(ready), "pass": bool(passed)}
