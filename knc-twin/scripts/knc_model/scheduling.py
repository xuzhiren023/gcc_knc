"""Deterministic schedule exploration; predictions, not compiler transformations.

Orders retain physical-register hazards and conservative memory order. Modulo
placement is a feasibility search for a fixed list order, without renaming or
prologue/epilogue generation. The ordinary timing engine evaluates executable
candidates; no held-out measurements or new timing parameters enter this module.
"""
import copy
import random

from . import asm, bounds, functional, isa, timing
from .errors import BudgetExhausted, FunctionalMismatch, InvalidInput, Unsupported
from .kernel import Kernel
from .trace import loop_body


def _memory(i):
    return i.is_load or i.is_store or i.folded_load


def _hazard(a, b):
    return bool(a.writes & (b.reads | b.addr_regs | b.writes)
                or b.writes & (a.reads | a.addr_regs)
                or a.flags_w and (b.flags_r or b.flags_w)
                or a.flags_r and b.flags_w
                or a.id in b.explicit_deps
                or a.sets_mxcsr and "mxcsr" in b.reads
                or b.sets_mxcsr and "mxcsr" in a.reads
                or a.cls in ("fence", "locked_rmw", "x87_control")
                or b.cls in ("fence", "locked_rmw", "x87_control")
                or a.kind.startswith("x87") and b.kind.startswith("x87")
                or _memory(a) and _memory(b) and (a.is_store or b.is_store))


def _normalized(kernel):
    raw = copy.deepcopy(kernel.raw)
    for s, stream in zip(raw["streams"], kernel.streams):
        if "instructions" not in s:
            text = s.get("asm")
            if text is None:
                with open(stream.asm_source, encoding="utf-8") as f:
                    text = f.read()
            if isinstance(text, list):
                text = "\n".join(text)
            s["instructions"] = asm.parse_gas(text)[0]
        s.pop("asm", None)
        s.pop("asm_file", None)
        for rec, insn in zip(s["instructions"], stream.insns):
            rec["id"] = insn.id
            rec.pop("encoding", None)
    # Moving records invalidates byte addresses and any binary-layout validation.
    raw.pop("representation", None)
    if any(i.encoding for s in kernel.streams for i in s.insns):
        raw.get("provenance", {}).pop("shape", None)
    return raw


def _run(k, p):
    interp, _, check = functional.run_functional(k)
    if check["status"] == "mismatch":
        raise FunctionalMismatch("scheduling candidate fails expected outputs", check)
    sim = timing.CoreSim(k, p, interp.traces)
    return sim.run(), sim, interp.traces, check


class _Region:
    def __init__(self, kernel, profile, assume):
        if len(kernel.streams) != 1:
            raise Unsupported("scheduling explorer needs exactly one context")
        self.raw = _normalized(kernel)
        self.k = Kernel(self.raw, kernel.path)
        self.p = profile
        self.s = self.k.streams[0]
        self.head, self.back = loop_body(self.k, self.s) or (0, len(self.s.insns) - 1)
        self.body = self.s.insns[self.head:self.back + 1]
        self.n = len(self.body)
        if self.n < 1:
            raise InvalidInput("empty scheduling region")
        if kernel.loop and self.body[-1].target != kernel.loop["label"]:
            raise InvalidInput("loop.back_branch must target the selected loop head")
        for j, i in enumerate(self.body):
            if i.op in ("call", "ret") or (i.is_branch and (not kernel.loop or j != self.n - 1)):
                raise Unsupported("explored region must be straight-line with only its final loop back branch")
            if j and i.label:
                raise Unsupported("explored region contains an interior label")
            if any(d in self.s.by_id and self.s.by_id[d].index >= i.index for d in i.explicit_deps):
                raise Unsupported("forward explicit dependencies are not reorderable")
        self.before = [set() for _ in self.body]
        for j, b in enumerate(self.body):
            for i, a in enumerate(self.body[:j]):
                if _hazard(a, b) or b.is_branch:
                    self.before[j].add(i)
        self.lat = bounds._Lat(profile, self.k, assume)
        self.baseline, self.sim, self.traces, self.check = _run(self.k, profile)
        first = {}
        for e in self.traces[self.s.context]:
            first.setdefault(e.insn.id, e)
        if any(i.id not in first for i in self.body):
            raise Unsupported("selected region was not fully executed by the input")
        self.events = [first[i.id] for i in self.body]
        self.height = [self.lat.of(i) for i in self.body]
        for i in reversed(range(self.n)):
            self.height[i] += max((self.height[j] for j in range(i + 1, self.n)
                                   if i in self.before[j]), default=0)
        self.defer = set()
        if self.body[-1].flags_r:
            for i, a in enumerate(self.body[:-1]):
                if (a.op, "jcc") in self.sim.dep_pairs and a.flags_w:
                    if not any(i in self.before[j] for j in range(i + 1, self.n - 1)):
                        self.defer.add(i)
        self.prefix_cache = {}

    def ready(self, order):
        used = set(order)
        return [i for i in range(self.n) if i not in used and self.before[i] <= used]

    def score(self, order):
        key = tuple(order)
        if key not in self.prefix_cache:
            events = []
            for n, i in enumerate(order):
                e = copy.copy(self.events[i])
                e.seq = n
                events.append(e)
            sim = timing.CoreSim(self.k, self.p, {self.s.context: events})
            res = sim.run()
            self.prefix_cache[key] = (sim.issue_log[-1]["cycle"], res["completion_cycles"])
        return self.prefix_cache[key]

    def list_order(self, lookahead):
        order = []
        while len(order) < self.n:
            ready = sorted(self.ready(order), key=lambda i: (i in self.defer, -self.height[i], i))
            def priority(i):
                issue, finish = self.score(order + [i])
                return (i in self.defer, issue, -self.height[i], finish, i)
            order.append(min(ready[:lookahead], key=priority))
        return order

    def candidate(self, order):
        raw = copy.deepcopy(self.raw)
        records = raw["streams"][0]["instructions"]
        body = records[self.head:self.back + 1]
        label = body[0].pop("label", None)
        changed = [body[i] for i in order]
        if label:
            changed[0]["label"] = label
        records[self.head:self.back + 1] = changed
        return Kernel(raw, self.k.path)


def _beam(region, budget, width, seed, lower, evaluate, incumbent):
    rng = random.Random(seed)
    frontier = [()]
    visited = 0
    discarded = False
    bound_pruned = False
    while frontier and visited < budget:
        if region.n > 12 and incumbent() <= lower:
            bound_pruned = True
            break
        children = []
        for prefix in frontier:
            if visited >= budget:
                discarded = True
                break
            visited += 1
            for i in region.ready(prefix):
                order = prefix + (i,)
                if len(order) == region.n:
                    evaluate(order)
                else:
                    # Prefix timing ranks the beam, never serves as a pruning
                    # bound: cache/layout changes can make such a bound unsafe.
                    children.append((region.score(order), rng.random(), order))
        children.sort()
        discarded |= len(children) > width
        frontier = [x[2] for x in children[:width]]
    return {"states_visited": visited, "max_states": budget, "beam_width": width,
            "seed": seed, "space_exhausted": not frontier and not discarded and not bound_pruned,
            "budget_exhausted": bool(frontier) and visited >= budget,
            "beam_discarded": discarded, "bound_pruned": bound_pruned,
            "meets_lower_bound": incumbent() <= lower,
            "pruning_bound_cycles": lower}


def _modulo(region, order, budget, assume):
    """Greedy cyclic placement, retrying every II from MII upwards.

    A failed placement proves nothing: neither order permutations nor alternative
    placements at that II are exhausted. Physical registers are not renamed.
    """
    p, body = region.p, region.body
    lb = bounds.loop_bounds(region.k, p, assume)
    supported = {"scalar_alu", "scalar_imul", "scalar_load", "scalar_store", "scalar_rmw", "branch",
                 "mask_op", "vector_arith", "vector_load", "vector_store", "vector_long",
                 "vector_convert_df", "x87_load", "x87_store", "x87_move", "x87_add", "x87_mul", "x87_div", "x87_sqrt"}
    if any(i.cls not in supported or i.op.startswith("vmovnr") for i in body):
        raise Unsupported("modulo placement does not model this body's resource class")
    assume("modulo placement assumes steady-state L1 hits, no decode or branch-refill stalls; actual candidate simulation retains its memory and branch scenario")
    assume("modulo search retains physical-register anti/output hazards and conservative memory ordering; no register renaming, prologue or epilogue is generated")
    # Ask the timing engine for isolated L1 result/flag latencies and holds.
    # This includes x87 memory-operand costs and masked/converted load forms;
    # bounds._Lat deliberately has a simpler optimistic latency vocabulary.
    latency, flag_latency, holds, occupancies = [], [], [], []
    gap = p.get("core.min_issue_gap_same_context")
    for event in region.events:
        sim = timing.CoreSim(region.k, p, {region.s.context: []})
        e = copy.copy(event)
        e.lines, e.taken = (), False
        latency.append(sim._retire(sim.ctx[0], e, 0, "U"))
        flag_latency.append(sim.ctx[0].flags_ready)
        holds.append(max(gap, sim.ctx[0].stall_until))
        occupancies.append(max(1, sim.x87_free_at))
    edges = {}
    def edge(u, v, lag, distance):
        key = (u, v, distance)
        edges[key] = max(edges.get(key, 0), lag)

    def lag(a, b, u):
        value = 0
        if a.writes & (b.reads | b.addr_regs) or a.id in b.explicit_deps:
            value = latency[u]
        if a.writes & b.addr_regs:
            value = max(value, p.get("latency.agi_cycles"))
        if a.flags_w and b.flags_r:
            value = max(value, 0 if (a.op, "jcc") in region.sim.dep_pairs and b.spec.get("cond") else flag_latency[u])
        if a.sets_mxcsr and "mxcsr" in b.reads:
            value = max(value, latency[u])
        if a.kind.startswith("x87") and b.kind.startswith("x87"):
            value = max(value, latency[u])
        if a.is_store and (b.is_load or b.folded_load):
            value = max(value, p.get("latency.store_to_load_same_line"), region.sim.store_interlock)
        return value

    for v, b in enumerate(body):
        for u in region.before[v]:
            edge(u, v, lag(body[u], b, u), 0)
    # Cross-iteration hazards: preserve the last conflicting operation before
    # the next iteration, including WAR/WAW and unknown memory aliases.
    for u, a in enumerate(body):
        for v, b in enumerate(body):
            if v <= u and _hazard(a, b):
                edge(u, v, max(1, lag(a, b, u)), 1)
    for mc in region.k.loop.get("memory_carried", []):
        by_id = {i.id: n for n, i in enumerate(body)}
        if mc["from"] not in by_id or mc["to"] not in by_id or int(mc.get("distance", 1)) < 1:
            raise InvalidInput("modulo memory_carried must refer to body ids with positive distance")
        edge(by_id[mc["from"]], by_id[mc["to"]], p.get("latency.store_to_load_same_line"), int(mc.get("distance", 1)))

    pair_sim = timing.CoreSim(region.k, p, {region.s.context: []})
    def pair(u, v):
        a = body[u]
        l1 = (1 if a.is_load or a.folded_load else 2 if a.is_store else 0)
        # No dynamic memory-side blockers in the steady-state resource model.
        eu, ev = copy.copy(region.events[u]), copy.copy(region.events[v])
        eu.lines = ev.lines = ()
        return pair_sim._can_pair(pair_sim.ctx[0], eu, ev, 0, l1)

    def hold(u):
        return holds[u]

    def occupancy(u):
        return occupancies[u]

    used = 0
    ii = max(1, lb["mii_cycles_per_iteration"])
    while used < budget:
        placed = {}
        phases = {}
        failed = False
        for u in order:
            earliest = max((placed[v] + l for (v, w, d), l in edges.items()
                            if w == u and d == 0 and v in placed), default=0)
            # Enough stages to cover a serial iteration, but finitely bounded.
            horizon = sum(max(gap, x) for x in latency) + ii
            found = False
            for cycle in range(earliest, horizon + 1):
                if used >= budget:
                    raise BudgetExhausted("modulo placement state budget exhausted", {"states_visited": used, "next_ii": ii})
                used += 1
                if any((w == u and v in placed and cycle < placed[v] + l - d * ii)
                       or (v == u and w in placed and placed[w] < cycle + l - d * ii)
                       or (v == w == u and l > d * ii)
                       for (v, w, d), l in edges.items()):
                    continue
                phase = cycle % ii
                members = phases.get(phase, [])
                if members and (len(members) == 2 or not pair(members[0], u)):
                    continue
                if hold(u) > ii or occupancy(u) > ii:
                    continue
                if any(phase != t % ii and ((phase - t) % ii < hold(v) or (t - phase) % ii < hold(u))
                       for v, t in placed.items()):
                    continue
                if body[u].kind.startswith("x87") and any(
                        body[v].kind.startswith("x87") and ((cycle - t) % ii < occupancy(v) or (t - cycle) % ii < occupancy(u))
                        for v, t in placed.items()):
                    continue
                placed[u] = cycle
                phases.setdefault(phase, []).append(u)
                found = True
                break
            if not found:
                failed = True
                break
        if not failed:
            schedule = [{"id": body[u].id, "cycle": placed[u],
                         "pipe": "UV"[phases[placed[u] % ii].index(u)]} for u in order]
            live = set()
            for (u, v, d), l in edges.items():
                if placed[u] // ii != (placed[v] + d * ii) // ii:
                    live.update(timing._writes(body[u], region.events[u]) &
                                (timing._reads(body[v], region.events[v]) | body[v].addr_regs))
            return dict(res_mii=lb["res_mii"], rec_mii=lb["rec_mii"],
                        mii=lb["mii_cycles_per_iteration"], ii=ii, schedule=schedule,
                        stage_count=1 + max(placed.values()) // ii,
                        registers_live_across_stages=len(live), states_visited=used,
                        register_count_basis="distinct physical register names from the representative functional iteration; no allocation or renamed versions",
                        limiting=lb["binding"], optimal=False,
                        claim="feasible fixed-order cyclic placement; failed smaller IIs do not prove infeasibility",
                        dependencies=[{"from": body[u].id, "to": body[v].id, "latency": l, "distance": d}
                                      for (u, v, d), l in sorted(edges.items())])
        ii += 1
    raise BudgetExhausted("modulo placement state budget exhausted", {"states_visited": used, "next_ii": ii})


def explore(kernel, profile, method="beam", seed=0, max_states=512, beam_width=8, lookahead=8):
    if method not in ("beam", "list", "modulo"):
        raise InvalidInput("unknown scheduling method %r" % method)
    if any(not isinstance(x, int) or x < 1 for x in (max_states, beam_width, lookahead)):
        raise InvalidInput("scheduling budgets, beam width and lookahead must be positive integers")
    assumptions = []
    def assume(s):
        if s not in assumptions:
            assumptions.append(s)
    assume("scheduling uses one context, preserves physical-register/flag/x87 hazards and orders all possibly aliasing stores; memory legality beyond this view is not proved")
    assume("all candidates and baseline use normalized records with byte-layout metadata removed; GAS output is a proposal, not assembled code")
    region = _Region(kernel, profile, assume)
    if method == "beam" and region.n > 60:
        raise Unsupported("beam exploration supports at most 60 body instructions; use list")
    if method == "modulo" and not kernel.loop:
        raise InvalidInput("modulo exploration needs kernel.loop")
    bound = bounds.trace_bounds(region.k, profile, region.traces, assume)
    # Only invariant resource terms are safe for pruning arbitrary reorderings.
    # In particular a reordered prefetch can change the memory/critical-path
    # terms of the original dynamic trace. Keep those out of the search claim.
    terms = {k: v for k, v in bound["terms"].items()
             if k in ("core_issue_events", "per_context_issue_spacing", "l1_port")}
    # trace_bounds charges UV_both as an extra issue event; for a reorder bound
    # it merely prevents pairing. Correct that pessimism without changing the
    # legacy bounds command or its recorded results.
    events = region.traces[region.s.context]
    both = sum(isa.CLASSES[e.insn.cls]["pipes"] == "UV_both" for e in events)
    eligible = sum(e.insn.cls in region.sim.v_eligible and isa.CLASSES[e.insn.cls]["pipes"] != "UV_both" for e in events)
    issue = len(events) - min((len(events) - both) // 2, eligible)
    terms["core_issue_events"] = issue
    terms["per_context_issue_spacing"] = max(0, region.sim.gap * issue - (region.sim.gap - 1))
    bound.update(terms=terms, lower_bound_cycles=max(terms.values()),
                 binding_term=max(terms, key=terms.get), kind="trace_resource_lower_bound",
                 statement="Optimistic trace issue/spacing/L1 resource bound; execution-order-sensitive memory and dependency terms are excluded from pruning.")
    bound.pop("per_context", None)
    assume(bound["statement"])
    best_order = tuple(range(region.n))
    best_k = region.k
    best_res, best_sim, best_traces, best_check = region.baseline, region.sim, region.traces, region.check
    seen = {best_order}
    def evaluate(order):
        nonlocal best_order, best_k, best_res, best_sim, best_traces, best_check
        order = tuple(order)
        if order in seen:
            return
        seen.add(order)
        k = region.candidate(order)
        res, sim, traces, check = _run(k, profile)
        if res["completion_cycles"] < best_res["completion_cycles"]:
            best_order, best_k, best_res, best_sim, best_traces, best_check = order, k, res, sim, traces, check
    list_order = region.list_order(lookahead)
    evaluate(list_order)
    list_cycles = best_res["completion_cycles"]
    search = {"states_visited": 0, "space_exhausted": False, "method": method,
              "lookahead": lookahead, "list_steps": region.n}
    if method == "beam":
        search.update(_beam(region, max_states, beam_width, seed, bound["lower_bound_cycles"], evaluate,
                            lambda: best_res["completion_cycles"]))
    modulo = _modulo(region, best_order, max_states, assume) if method == "modulo" else None
    for a in best_sim.assumptions:
        assume(a)
    # A complete function can execute the selected loop more than once. Count
    # actual back-branch executions, not a unit count or declared trip count.
    iterations = sum(e.insn.id == region.body[-1].id for e in best_traces[region.s.context]) if kernel.loop else 1
    from .cli import memory_result_class
    cls = memory_result_class("simulate", best_k, profile, best_res["memory"].get("stats"), best_k.scenario)
    limits = timing.limiting_constraints(best_res) or [{"constraint": bound["binding_term"]}]
    candidate = {"kernel": best_k.raw, "gas": asm.emit_gas(best_k.streams[0]),
                 "order_ids": [region.body[i].id for i in best_order],
                 "cycles": best_res["completion_cycles"], "cycles_per_iteration": best_res["completion_cycles"] / float(iterations),
                 "iterations": iterations, "iteration_basis": "whole-trace completion divided by executed selected-loop iterations (includes entry/exit)",
                 "pair_fraction": best_res["pair_fraction"], "limiting_constraints": limits,
                 "result_class": cls["class"], "classification": cls}
    result = {"status": "ok", "method": method, "candidate": candidate, "search": search,
              "baseline_cycles": region.baseline["completion_cycles"], "lower_bound_cycles": bound["lower_bound_cycles"],
              "bound": bound, "list_cycles": list_cycles, "best_minus_list_cycles": candidate["cycles"] - list_cycles,
              "assumptions": assumptions, "unsupported": [], "limiting_constraints": limits,
              "functional_check": best_check, "result_class": cls["class"],
              "calibration_status": profile.calibration, "parameters_used": profile.used_summary()}
    search["orders_evaluated"] = len(seen)
    if modulo:
        modulo["simulation_minus_estimate_cycles_per_iteration"] = candidate["cycles_per_iteration"] - modulo["ii"]
        modulo["executable_order_ids"] = candidate["order_ids"]
        modulo["estimate_is_not_executable_pipeline"] = True
        result["modulo"] = modulo
    return result
