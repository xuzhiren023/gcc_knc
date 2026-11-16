"""Incremental, single-context loop sampling. No timing parameter is fitted here.

Functional execution and timing both stop at the sampled prefix. Cache, branch,
register and interpreter state survive every window. Unseen input remains an
assumption, not a correctness check or a statistically guaranteed error bound.
"""
import math
import time

from . import functional, timing
from .errors import InvalidInput, Unsupported, FunctionalMismatch


DEFAULTS = {"warmup": None, "window": 32, "tolerance": 0.01,
            "max_iterations": 4096}
AGREE_WINDOWS = 3


def options(raw):
    if not isinstance(raw, dict) or not raw.get("loop"):
        raise InvalidInput("sampling needs a loop label")
    if set(raw) - set(DEFAULTS) - {"loop"}:
        raise InvalidInput("unknown sampling options: %s" % sorted(set(raw) - set(DEFAULTS) - {"loop"}))
    out = dict(DEFAULTS, **raw)
    for key in ("window", "max_iterations", "warmup"):
        v = out[key]
        if key == "warmup" and v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, int) or v < (0 if key == "warmup" else 1):
            raise InvalidInput("sampling.%s must be a %s integer" % (key, "nonnegative" if key == "warmup" else "positive"))
    t = out["tolerance"]
    if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or not 0 <= t < 1:
        raise InvalidInput("sampling.tolerance must be a finite fraction in [0, 1)")
    if out["warmup"] is not None and out["warmup"] >= out["max_iterations"]:
        raise InvalidInput("sampling.warmup must be less than max_iterations")
    return out


def _signature(events):
    """Within-iteration address differences detect irregular input shapes.

    Translation of a regular stream preserves its shape; indirect/random rows
    generally do not. Exact equality is conservative, with no learned threshold.
    """
    origins = {}
    shape = []
    for ev in events:
        if ev.addr is not None:
            origin = origins.setdefault(ev.insn.id, ev.addr)
            shape.append((ev.insn.id, ev.addr - origin, ev.nbytes, ev.mask_bits))
    return tuple(shape)


def _period(shapes):
    """Require two complete observed repetitions, including any trailing prefix."""
    n = len(shapes)
    for p in range(1, n // 2 + 1):
        if shapes[p] == shapes[0] and all(shapes[i] == shapes[i % p] for i in range(p, n)):
            return p
    return None


def run(kernel, profile, config, max_steps=None, max_cycles=None, deadline=None,
        record_issue=False):
    config = options(config)
    if len(kernel.streams) != 1:
        raise Unsupported("loop sampling currently needs exactly one context; interleaved sampled contexts are not modeled")
    stream = kernel.streams[0]
    label = config["loop"]
    if label not in stream.labels:
        raise InvalidInput("sampling loop label %r is absent" % label)
    head = stream.labels[label]
    if not any(i.is_branch and i.target == label and i.index >= head for i in stream.insns):
        raise InvalidInput("sampling label %r has no loop back-edge" % label)
    t0 = time.perf_counter()
    interp = functional.Interpreter(kernel, max_steps=max_steps, deadline=deadline)
    generator = interp.iter_stream(stream)
    boundaries = []
    exhausted = False
    functional_seconds = time.perf_counter() - t0

    def advance():
        nonlocal exhausted, functional_seconds
        t0 = time.perf_counter()
        try:
            ev = next(generator)
            if ev.insn.index == head:
                boundaries.append(len(interp.traces[stream.context]) - 1)
        except StopIteration:
            exhausted = True
        finally:
            functional_seconds += time.perf_counter() - t0

    def fill(iteration):
        # Include the next header plus one further instruction. Timing may pair
        # across the observation boundary; it must still see prefix lookahead.
        while not exhausted and len(boundaries) <= iteration:
            advance()
        if len(boundaries) > iteration:
            end = boundaries[iteration]
            while not exhausted and len(interp.traces[stream.context]) <= end + 1:
                advance()
            return end
        return len(interp.traces.get(stream.context, []))

    fill(1)
    if not boundaries:
        raise InvalidInput("sampling loop %r was never reached" % label)
    traces = interp.traces
    events = traces[stream.context]
    sim = timing.CoreSim(kernel, profile, traces, max_cycles=max_cycles,
                         deadline=deadline, record_issue=record_issue)
    sim.run({stream.context: boundaries[0]})
    previous_cycle = sim.cycle
    seen_lines = set()
    shape_ids = {}
    shapes = []
    windows = []
    widenings = []
    current_width = config["window"]
    window_start = None
    window_cycles = 0
    window_count = 0
    warmup = config["warmup"]
    # The default first-touch warmup is bounded; a streaming input may never
    # repeat a line. Explicit --warmup always discards exactly N iterations.
    warmup_limit = min(64, config["max_iterations"] - 1) if warmup is None else warmup
    warmed = warmup_limit == 0
    discarded = 0
    stop = "max_iterations"
    period = None
    res = None
    for n in range(1, config["max_iterations"] + 1):
        end = fill(n)
        if n > len(boundaries):
            break
        begin = boundaries[n - 1]
        iteration = events[begin:end]
        shape = _signature(iteration)
        shapes.append(shape_ids.setdefault(shape, len(shape_ids)))
        lines = set(l for ev in iteration for l in ev.lines)
        new_lines = lines - seen_lines
        seen_lines.update(lines)
        res = sim.run({stream.context: end})
        cycles = sim.cycle - previous_cycle
        previous_cycle = sim.cycle
        if not warmed:
            discarded += 1
            warmed = n >= warmup_limit or (warmup is None and not new_lines)
        else:
            if window_start is None:
                window_start = n
            window_count += 1
            window_cycles += cycles
            terminal = exhausted and n == len(boundaries)
            if window_count == current_width or terminal or n == config["max_iterations"]:
                windows.append({"first_iteration": window_start, "last_iteration": n,
                                "iterations": window_count, "window_size": current_width,
                                "cycles_per_iteration": window_cycles / float(window_count)})
                window_start, window_count, window_cycles = None, 0, 0
                recent = windows[-AGREE_WINDOWS:]
                full = len(recent) == AGREE_WINDOWS and all(w["iterations"] == current_width for w in recent)
                if full:
                    values = [w["cycles_per_iteration"] for w in recent]
                    mean = sum(values) / len(values)
                    lag1 = max(abs(values[i] - values[i - 1]) for i in range(1, len(values)))
                    lag2 = abs(values[-1] - values[-3])
                    period = _period(shapes)
                    if period is not None and period <= current_width and max(lag1, lag2) <= config["tolerance"] * mean:
                        stop = "converged"
                        break
                    # Alternation requires a wider window; ordinary warmup
                    # drift needs more observations at the current width. Do
                    # not spend the budget doubling away transient drift.
                    uncovered = period is None or period > current_width
                    alternating = lag2 <= config["tolerance"] * mean < lag1
                    if uncovered or alternating:
                        reason = "input period not covered" if uncovered else "lag two agrees but lag one disagrees"
                        width = max(2 * current_width, period or 0)
                        widenings.append({"after_iteration": n, "from": current_width, "to": width, "reason": reason})
                        current_width = width
        if exhausted and n == len(boundaries):
            stop = "loop_finished"
            break
    if not windows:
        raise InvalidInput("no post-warmup iteration was sampled; reduce warmup or increase the iteration budget")
    recent = windows[-AGREE_WINDOWS:]
    values = [w["cycles_per_iteration"] for w in recent]
    count = sum(w["iterations"] for w in recent)
    cpi = sum(w["cycles_per_iteration"] * w["iterations"] for w in recent) / count
    check = {"status": "not_run", "note": "functional trace sampled too: final expected outputs were not reached"}
    if exhausted:
        check = functional.check_expected(kernel, interp)
        if check["status"] == "mismatch":
            raise FunctionalMismatch("sampled execution reached incorrect final outputs", {"first": check["mismatches"][0]})
    if interp.memory.touched_default:
        interp.assume("reads of uninitialized memory returned the kernel's memory_default byte 0x%02x" % (kernel.memory_default or 0))
    sampling = {"loop": label, "options": config, "windows": windows,
                "iterations_sampled": n, "warmup_iterations": discarded,
                "stop_reason": stop, "agreement_windows": AGREE_WINDOWS,
                "observed_input_period": period, "window_widenings": widenings,
                "cycles_per_iteration_band": [min(values), max(values)],
                "trace_sampled": not exhausted,
                "rule": "three full windows; lag-one and lag-two differences <= tolerance * mean; observed input period covered"}
    return sim, res, interp, check, sampling, cpi, functional_seconds
