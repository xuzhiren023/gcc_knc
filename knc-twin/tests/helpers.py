"""Shared helpers for the synthetic model tests."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")
FIXTURES = os.path.join(ROOT, "fixtures")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from knc_model.kernel import Kernel  # noqa: E402
from knc_model.profile import load_profile  # noqa: E402
from knc_model import functional, timing  # noqa: E402

SCHEMA = "knc-twin.kernel/1"


def kernel(instructions, init=None, expected=None, scenario=None, loop=None, streams=None, **extra):
    raw = {"schema": SCHEMA, "name": extra.pop("name", "test"), "unit_of_work": {"description": "test", "count": 1},
           "init": init or {}, "expected": expected or {}}
    if streams is not None:
        raw["streams"] = streams
    else:
        raw["streams"] = [{"context": 0, "instructions": instructions}]
    if scenario:
        raw["scenario"] = scenario
    if loop:
        raw["loop"] = loop
    raw.update(extra)
    return Kernel(raw, None)


def profile(name="card-7120-measured", overlays=None):
    return load_profile(name, overlays)


def simulate(k, prof=None, contexts=None, **kw):
    prof = prof or profile()
    interp, steps, check = functional.run_functional(k)
    traces = interp.traces
    if contexts is not None:
        traces = {c: traces[c] for c in contexts}
    sim = timing.CoreSim(k, prof, traces, **kw)
    res = sim.run()
    return res, sim, check


def issue_cycles(sim):
    """{(ctx, id, occurrence): cycle} from the issue log."""
    out = {}
    seen = {}
    for e in sim.issue_log:
        key = (e["ctx"], e["id"])
        n = seen.get(key, 0)
        seen[key] = n + 1
        out[(e["ctx"], e["id"], n)] = e["cycle"]
    return out


def fixture(name):
    return os.path.join(FIXTURES, name)
