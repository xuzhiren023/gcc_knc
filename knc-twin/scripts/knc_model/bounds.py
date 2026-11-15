"""Analytical lower bounds and an optional exhaustive reorder search.

Bounds are optimistic by construction and each states its assumptions. They are
separate from (a) the timing of a particular candidate (timing.py) and (b) a proven
optimum within a declared search space (search_optimal_order below), which is only
claimed when the search space was exhausted or the best found schedule meets a bound.

Loop bounds follow Rau's modulo-scheduling vocabulary (HPL-94-115): ResMII from
resource usage per iteration, RecMII from loop-carried recurrences, MII = max.
The one-iteration critical path is reported separately from the initiation interval.
"""
from fractions import Fraction
import itertools
import time

from .errors import BudgetExhausted, InvalidInput, Unsupported
from .trace import loop_body
from . import isa


def _ceil_div(a, b):
    return -(-a // b)


class _Lat(object):
    """Latency lookup for bounds with scenario-level memory assumptions."""

    def __init__(self, profile, kernel, assume):
        self.p = profile
        self.k = kernel
        self.assume = assume
        self.sc = kernel.scenario["memory"]
        self.seen_lines = set()

    def level_for(self, ev):
        t = self.sc["type"]
        if t == "fixed_level":
            return self.sc["level"]
        if ev is None or ev.addr is None:
            self.assume("bound: memory access without an address assumed to hit L1")
            return "l1"
        la = ev.addr & ~63
        if t == "classified":
            for rng in self.sc.get("ranges", []):
                if rng["start"] <= la < rng["end"]:
                    return rng["level"]
            return self.sc["default"]
        # line_tracking: first touch of a line costs the cold level, later touches hit L1 (optimistic, ignores capacity)
        if la in self.seen_lines:
            return "l1"
        self.seen_lines.add(la)
        for rng in self.sc.get("warm", []):
            if rng["start"] <= la < rng["end"]:
                return rng["level"]
        self.assume("bound under line_tracking: each line costs its cold level once and L1 afterwards (capacity and prefetch timing ignored)")
        return self.sc["cold_level"]

    def load_latency(self, level, vector):
        if level == "l1":
            return self.p.get("latency.vector_load_l1") if vector else self.p.get("latency.scalar_load_l1")
        base = self.p.get("latency.l2_hit") if level == "l2" else self.p.get("latency.memory")
        extra = max(0, self.p.get("latency.vector_load_l1") - self.p.get("latency.scalar_load_l1")) if vector else 0
        return base + extra

    def of(self, insn, ev=None):
        """Result latency of insn for a dependent instruction."""
        if insn.is_store and not insn.is_load:
            return 0
        if insn.cls in ("prefetch_l1", "prefetch_l2", "branch"):
            return 0
        if insn.cls == "vector_gather":
            n = len(ev.lines) if ev is not None and ev.lines else (insn.lines_hint or 1)
            return self.p.get("latency.gather_first_line") + self.p.get("occupancy.gather_cycles_per_line") * (n - 1)
        if insn.is_load or insn.folded_load:
            lvl = self.level_for(ev)
            vector = insn.cls.startswith("vector") or insn.folded_load
            lat = self.load_latency(lvl, vector)
            if insn.folded_load:
                arith = self.p.get(isa.CLASSES[insn.cls]["latency"])
                return arith if lvl == "l1" else lat - self.load_latency("l1", True) + arith
            return lat + self._extend(insn)
        key = isa.CLASSES[insn.cls]["latency"]
        if key is None:
            return 1
        return self.p.get(key) + self._extend(insn)

    def _extend(self, insn):
        return self.p.get("latency.scalar_extend_extra") if insn.op in isa.EXTEND_OPS else 0


def _v_eligible(profile):
    return set(profile.get("pairing.v_eligible_classes"))


def _issue_events_lower(insns, v_el):
    """Minimum issue events for a list of static/dynamic instructions: each event is one U
    instruction plus at most one V-eligible instruction."""
    n = len(insns)
    v = sum(1 for i in insns if i.cls in v_el and isa.CLASSES[i.cls]["pipes"] != "UV_both")
    both = sum(1 for i in insns if isa.CLASSES[i.cls]["pipes"] == "UV_both")
    pairs = min(n // 2, v)
    return n - pairs + both  # UV_both instructions cannot pair at all


def _resource_terms(insns_with_ev, profile, assume):
    terms = {}
    gather_cycles = 0
    x87 = 0
    l2pf = 0
    l1acc = 0
    fence = 0
    for insn, ev in insns_with_ev:
        if insn.cls == "vector_gather":
            n = len(ev.lines) if ev is not None and ev.lines else (insn.lines_hint or 1)
            gather_cycles += profile.get("occupancy.gather_cycles_per_line") * n
        elif insn.cls in ("x87_mul", "x87_div"):
            x87 += profile.get(isa.CLASSES[insn.cls]["occupancy"])
        elif insn.cls == "x87_add" or insn.cls == "x87_move":
            x87 += 1
        elif insn.cls == "prefetch_l2":
            l2pf += profile.get("occupancy.vprefetch_l2_core_cycles")
        elif insn.cls == "fence":
            fence += profile.get("latency.fence")
        if insn.is_load or insn.is_store or insn.folded_load:
            l1acc += 1
    if gather_cycles:
        terms["gather_occupancy"] = gather_cycles
    if x87:
        terms["x87_unit_occupancy"] = x87
    if l2pf:
        terms["l2_prefetch_issue_occupancy"] = l2pf
    if fence:
        terms["fence_serialization"] = fence
    if l1acc:
        per = profile.get("l1.accesses_per_cycle")
        terms["l1_port"] = _ceil_div(l1acc, per)
    return terms


def trace_bounds(kernel, profile, traces, assume):
    """Lower bounds for the whole dynamic trace of the active contexts."""
    v_el = _v_eligible(profile)
    gap = profile.get("core.min_issue_gap_same_context")
    lat = _Lat(profile, kernel, assume)
    terms = {}
    issue_total = 0
    spacing_max = 0
    per_ctx = {}
    all_pairs = []
    for ctx, events in sorted(traces.items()):
        insns = [e.insn for e in events]
        ev_c = _issue_events_lower(insns, v_el)
        issue_total += ev_c
        sp = gap * ev_c - (gap - 1) if ev_c else 0
        spacing_max = max(spacing_max, sp)
        per_ctx[str(ctx)] = {"dynamic_instructions": len(insns), "min_issue_events": ev_c, "spacing_bound_cycles": sp}
        all_pairs.extend((e.insn, e) for e in events)
    terms["core_issue_events"] = issue_total
    terms["per_context_issue_spacing"] = spacing_max
    terms.update(_resource_terms(all_pairs, profile, assume))
    # critical path per context (register, flag, explicit and same-line memory dependencies)
    cp_max = 0
    for ctx, events in sorted(traces.items()):
        ready = {}
        flags_ready = 0
        done_by_id = {}
        line_written = {}
        longest = 0
        x87_prev = 0
        for e in events:
            insn = e.insn
            start = 0
            for r in insn.reads:
                start = max(start, ready.get(r, 0))
            if insn.flags_r:
                start = max(start, flags_ready)
            for d in insn.explicit_deps:
                start = max(start, done_by_id.get(d, 0))
            if insn.is_load or insn.folded_load:
                for la in e.lines:
                    start = max(start, line_written.get(la, 0))
            if insn.kind == "x87":
                start = max(start, x87_prev)
            L = lat.of(insn, e)
            fin = start + max(L, 1) if (insn.writes or insn.flags_w or insn.kind == "x87") else start
            for r in insn.writes:
                ready[r] = start + L
            if insn.flags_w:
                flags_ready = start + max(L, 1)
            if insn.is_store:
                for la in e.lines:
                    line_written[la] = start + 1
            if insn.kind == "x87":
                x87_prev = start + L
            done_by_id[insn.id] = start + L
            longest = max(longest, fin)
        per_ctx[str(ctx)]["critical_path_cycles"] = longest
        cp_max = max(cp_max, longest)
    terms["dependency_critical_path"] = cp_max
    # memory concurrency (Little's law): lines that miss / outstanding slots x latency
    miss_lines = {"l2": set(), "memory": set()}
    lat2 = _Lat(profile, kernel, assume)
    for ctx, events in traces.items():
        for e in events:
            if (e.insn.is_load or e.insn.folded_load or e.insn.cls == "vector_gather") and e.lines:
                for la in e.lines:
                    lvl = lat2.level_for(type("E", (), {"addr": la})())
                    if lvl != "l1":
                        miss_lines[lvl].add(la)
    if miss_lines["l2"] or miss_lines["memory"]:
        slots = profile.get("l1.outstanding_demand_misses_per_core")
        cyc = _ceil_div(len(miss_lines["l2"]) * profile.get("latency.l2_hit") + len(miss_lines["memory"]) * profile.get("latency.memory"), slots)
        terms["memory_concurrency"] = cyc
        assume("memory concurrency bound: distinct missing lines x level latency / %d outstanding misses per core; ignores the L2 hardware prefetcher" % slots)
    bound = max(terms.values()) if terms else 0
    binding = sorted(terms.items(), key=lambda kv: -kv[1])[0][0] if terms else None
    return {"kind": "trace_lower_bound", "lower_bound_cycles": bound, "binding_term": binding, "terms": terms, "per_context": per_ctx,
            "statement": "No schedule of these dynamic instructions on this core model can complete in fewer cycles than the largest term; the terms are independent optimistic constraints (issue slots, same-context spacing, resource occupancy, dependency chains, memory concurrency)."}


# --- loop bounds -------------------------------------------------------------------------

def _rec_mii(nodes, edges):
    """Max over cycles of sum(latency)/sum(distance) via binary search on lambda and
    Bellman-Ford positive-cycle detection on weights lat - lambda*dist. Returns a Fraction or 0."""
    if not edges:
        return Fraction(0)
    max_lat = sum(l for (_, _, l, _) in edges)

    def has_positive_cycle(lam):
        dist = {n: Fraction(0) for n in nodes}
        for _ in range(len(nodes)):
            changed = False
            for (u, v, l, d) in edges:
                w = Fraction(l) - lam * d
                if dist[u] + w > dist[v]:
                    dist[v] = dist[u] + w
                    changed = True
            if not changed:
                return False
        for (u, v, l, d) in edges:
            if dist[u] + Fraction(l) - lam * d > dist[v]:
                return True
        return False
    # candidates are rationals; do an exact search over feasible ratios p/q with q <= nodes
    lo, hi = Fraction(0), Fraction(max_lat)
    if not has_positive_cycle(lo):
        return Fraction(0)
    for _ in range(60):
        mid = (lo + hi) / 2
        if has_positive_cycle(mid):
            lo = mid
        else:
            hi = mid
    # snap to the nearest rational with small denominator
    best = lo
    for q in range(1, len(nodes) + 1):
        p = round(lo * q)
        cand = Fraction(p, q)
        if abs(cand - lo) < Fraction(1, 10 ** 9):
            best = cand
            break
    return best


def loop_bounds(kernel, profile, assume, body_events=None):
    """Per-iteration bounds for kernel.loop across all streams: ResMII (core and per context),
    RecMII from loop-carried register/memory recurrences, and one-iteration critical path."""
    if kernel.loop is None:
        raise InvalidInput("bounds --loop needs kernel.loop {label, ...}")
    v_el = _v_eligible(profile)
    gap = profile.get("core.min_issue_gap_same_context")
    lat = _Lat(profile, kernel, assume)
    if kernel.scenario["memory"]["type"] == "line_tracking":
        assume("loop bounds under line_tracking assume steady-state L1 hits for loop loads (prefetch-covered); use fixed_level to bound a miss-dominated loop")
    res_core = 0
    res_ctx_max = 0
    rec_max = Fraction(0)
    cp_max = 0
    per_ctx = {}
    resource_terms_total = {}
    for stream in kernel.streams:
        lb = loop_body(kernel, stream)
        if lb is None:
            continue
        head, back = lb
        body = stream.insns[head:back + 1]
        ev_map = {}
        if body_events and stream.context in body_events:
            ev_map = body_events[stream.context]
        ev_c = _issue_events_lower(body, v_el)
        res_core += ev_c
        res_ctx = gap * ev_c
        res_ctx_max = max(res_ctx_max, res_ctx)
        rterms = _resource_terms([(i, ev_map.get(i.id)) for i in body], profile, assume)
        for k, v in rterms.items():
            resource_terms_total[k] = resource_terms_total.get(k, 0) + v
        # dependence graph of one iteration + loop-carried edges (distance 1 for registers/flags)
        nodes = [i.id for i in body]
        edges = []
        last_writer = {}
        flags_writer = None
        first_reader_before_write = {}
        for i in body:
            L_prod = {}
            for r in i.reads:
                if r in last_writer:
                    w = last_writer[r]
                    edges.append((w.id, i.id, lat.of(w, ev_map.get(w.id)), 0))
            if i.flags_r and flags_writer is not None:
                edges.append((flags_writer.id, i.id, max(1, lat.of(flags_writer)), 0))
            for d in i.explicit_deps:
                if d in stream.by_id and stream.by_id[d].index < i.index and head <= stream.by_id[d].index <= back:
                    w = stream.by_id[d]
                    edges.append((w.id, i.id, lat.of(w, ev_map.get(w.id)), 0))
            for r in i.writes:
                last_writer[r] = i
            if i.flags_w:
                flags_writer = i
        # loop-carried: a read of r before any write of r in the body depends on the last writer of r (distance 1)
        written_so_far = set()
        for i in body:
            for r in i.reads | i.addr_regs:
                if r not in written_so_far and r in last_writer:
                    w = last_writer[r]
                    edges.append((w.id, i.id, lat.of(w, ev_map.get(w.id)), 1))
            if i.flags_r and flags_writer is not None and not any(j.flags_w for j in body[:i.index - head]):
                edges.append((flags_writer.id, i.id, max(1, lat.of(flags_writer)), 1))
            written_so_far |= i.writes
        for mc in kernel.loop.get("memory_carried", []):
            src, dst, dist = mc.get("from"), mc.get("to"), int(mc.get("distance", 1))
            if src not in stream.by_id or dst not in stream.by_id:
                raise InvalidInput("loop.memory_carried refers to unknown ids %r -> %r" % (src, dst))
            s_i = stream.by_id[src]
            lat_store = profile.get("latency.store_to_load_same_line") if profile.has("latency.store_to_load_same_line") else 1
            edges.append((src, dst, lat_store + (lat.of(stream.by_id[dst], ev_map.get(dst)) if False else 0), dist))
            assume("memory-carried recurrence %s -> %s (distance %d) uses the store-to-load latency parameter" % (src, dst, dist))
        rec = _rec_mii(nodes, edges)
        rec_max = max(rec_max, rec)
        # one-iteration critical path (distance-0 edges only)
        dist0 = [e for e in edges if e[3] == 0]
        start = {n: 0 for n in nodes}
        for i in body:  # body is in program order = topological for distance-0 edges
            for (u, v, l, d) in dist0:
                if v == i.id:
                    start[v] = max(start[v], start[u] + l)
        cp = 0
        for i in body:
            L = lat.of(i, ev_map.get(i.id))
            cp = max(cp, start[i.id] + max(L, 1))
        cp_max = max(cp_max, cp)
        per_ctx[str(stream.context)] = {"body_instructions": len(body), "min_issue_events": ev_c, "res_mii_context": res_ctx,
                                       "rec_mii": str(rec), "iteration_critical_path": cp,
                                       "recurrences": [{"from": u, "to": v, "latency": l, "distance": d} for (u, v, l, d) in edges if d > 0]}
    res_mii = max(res_core, res_ctx_max, max(resource_terms_total.values()) if resource_terms_total else 0)
    rec_int = int(_ceil_frac(rec_max))
    mii = max(res_mii, rec_int)
    return {"kind": "loop_lower_bound", "mii_cycles_per_iteration": mii, "res_mii": res_mii,
            "res_mii_terms": dict(resource_terms_total, core_issue_events=res_core, per_context_spacing=res_ctx_max),
            "rec_mii": str(rec_max), "rec_mii_ceiling": rec_int, "iteration_critical_path_cycles": cp_max,
            "binding": "recurrence" if rec_int > res_mii else "resources",
            "per_context": per_ctx,
            "statement": "MII = max(ResMII, RecMII) is a lower bound on the steady-state cycles per iteration for any modulo schedule of this body under the stated model (Rau 1994). The one-iteration critical path bounds the latency of a single iteration, not the throughput."}


def _ceil_frac(fr):
    return -(-fr.numerator // fr.denominator)


# --- exhaustive reorder search ---------------------------------------------------------------

def search_optimal_order(kernel, profile, traces, ctx, max_orders, deadline, sim_factory):
    """Enumerate dependency-preserving orders of one context's straight-line trace and
    simulate each with the unchanged model. Returns the best order and whether the space
    was exhausted. Memory order: a load/store pair is reorderable only when both have
    addresses and touch disjoint lines."""
    events = traces[ctx]
    if any(e.insn.is_branch for e in events):
        raise Unsupported("reorder search needs a straight-line trace (no branches) for context %d" % ctx)
    n = len(events)
    if n > 12:
        raise Unsupported("reorder search is limited to 12 instructions (got %d); the space is n! orders" % n)
    # precedence constraints
    before = [set() for _ in range(n)]
    for j in range(n):
        ej = events[j].insn
        for i in range(j):
            ei = events[i].insn
            dep = bool((ei.writes & (ej.reads | ej.addr_regs)) or (ej.writes & (ei.reads | ei.addr_regs)) or (ei.writes & ej.writes))
            if ei.flags_w and ej.flags_r or ej.flags_w and ei.flags_r or (ei.flags_w and ej.flags_w):
                dep = True
            if ei.id in ej.explicit_deps:
                dep = True
            mem_i = ei.is_load or ei.is_store or ei.folded_load or ei.cls == "vector_gather"
            mem_j = ej.is_load or ej.is_store or ej.folded_load or ej.cls == "vector_gather"
            if mem_i and mem_j and (ei.is_store or ej.is_store):
                li, lj = set(events[i].lines), set(events[j].lines)
                if not li or not lj or (li & lj):
                    dep = True
            if ei.kind == "x87" and ej.kind == "x87":
                dep = True
            if ei.is_branch or ej.is_branch:
                dep = True
            if dep:
                before[j].add(i)
    count = 0
    best = None
    best_cycles = None
    exhausted = True
    baseline = None

    def gen(prefix, remaining):
        for i in sorted(remaining):
            if before[i] <= set(prefix):
                yield i

    stack = [([], frozenset(range(n)))]
    while stack:
        prefix, remaining = stack.pop()
        if not remaining:
            count += 1
            if count > max_orders:
                exhausted = False
                break
            if deadline is not None and time.time() > deadline:
                exhausted = False
                break
            order = list(prefix)
            new_events = [events[i] for i in order]
            for k, e in enumerate(new_events):
                e.seq = k
            sim = sim_factory({ctx: new_events})
            res = sim.run()
            cyc = res["completion_cycles"]
            if baseline is None:
                baseline = cyc if order == list(range(n)) else None
            if order == list(range(n)):
                baseline = cyc
            if best_cycles is None or cyc < best_cycles:
                best_cycles = cyc
                best = order
            continue
        for i in reversed(list(gen(prefix, remaining))):
            stack.append((prefix + [i], remaining - {i}))
    for k, e in enumerate(events):
        e.seq = k
    return {"orders_evaluated": count, "space_exhausted": exhausted, "best_cycles": best_cycles,
            "best_order_ids": [events[i].insn.id for i in best] if best else None,
            "original_order_cycles": baseline}
