"""Cycle-level core model: four in-order hardware contexts, U/V issue with pairing rules,
same-context issue spacing, round-robin context selection, scoreboarded register
dependencies (including x87 physical registers from the functional trace), address-
generation interlock, demand-miss stalls, nonblocking software prefetches, resource
occupancy. No speculation, no out-of-order issue.

Cycles here are predicted KNC core cycles. Python wall time is reported separately.
"""
import time

from .cache import MemoryModel
from .errors import BudgetExhausted, MissingParameter, Unsupported
from . import isa

X87_ARITH = ("x87_add", "x87_mul", "x87_div", "x87_sqrt")
STALL_REASONS = ("spacing", "miss_stall", "dependency", "agi", "flags", "explicit_dep", "x87_serial", "resource",
                 "outstanding_limit", "l1_port", "core_busy", "not_picked", "branch_penalty", "done")


def _vector_access(insn):
    """False for scalar accesses, True for plain vector loads/stores, "merge" for masked,
    converting or unpacking vector loads (longer measured load-to-use path)."""
    if not (insn.cls.startswith("vector") or insn.folded_load or insn.has_conv):
        return False
    if insn.is_load and (insn.mask is not None or insn.has_conv or insn.op.startswith("vloadunpack")):
        return "merge"
    return True


def _reads(insn, ev):
    if ev.xreads is not None:
        return (insn.reads - {"x87"}) | ev.xreads
    return insn.reads


def _writes(insn, ev):
    if ev.xwrites is not None:
        return (insn.writes - {"x87"}) | ev.xwrites
    return insn.writes


class CtxState(object):
    def __init__(self, ctx, events):
        self.ctx = ctx
        self.events = events
        self.pos = 0
        self.next_issue = 0
        self.last_issue = -1
        self.stall_until = 0
        self.reg_ready = {}
        self.reg_written_at = {}
        self.flags_ready = 0
        self.last_done = {}
        self.issued = 0
        self.pairs = 0
        self.stalls = {r: 0 for r in STALL_REASONS}
        self.prev_direction = {}
        self.first_issue = None
        self.last_issue_cycle = None
        self.max_done = 0

    @property
    def done(self):
        return self.pos >= len(self.events)


class CoreSim(object):
    def __init__(self, kernel, profile, traces, active_contexts=None, max_cycles=None, deadline=None, record_issue=True):
        self.kernel = kernel
        self.p = profile
        self.assumptions = []
        self._aset = set()
        self.unsupported = []
        self.max_cycles = max_cycles
        self.deadline = deadline
        self.record_issue = record_issue
        ctxs = sorted(traces.keys()) if active_contexts is None else list(active_contexts)
        if not ctxs:
            raise Unsupported("no active contexts")
        if len(ctxs) > profile.get("core.contexts"):
            raise Unsupported("more contexts than the core has (%d)" % profile.get("core.contexts"))
        self.ctx = [CtxState(c, traces[c]) for c in ctxs]
        self.mem = MemoryModel(kernel.scenario, profile, self.assume)
        self.gap = profile.get("core.min_issue_gap_same_context")
        self.agi = profile.get("latency.agi_cycles")
        self.v_eligible = set(profile.get("pairing.v_eligible_classes"))
        self.dep_pairs = [tuple(x) for x in profile.get("pairing.dependent_pairs_allowed")]
        self.enc_rules = profile.get("pairing.encoding_rules")
        self.l1_per_cycle = profile.get("l1.accesses_per_cycle")
        self.miss_stalls = profile.get("l1.demand_load_miss_stalls_context")
        self.taken_bubble = profile.get("latency.branch_taken_bubble")
        self.core_busy_until = 0
        self.x87_free_at = 0
        self.l2pf_free_at = 0
        self.nr_store_free_at = 0
        self.gather_free_at = 0
        self.cycle = 0
        self.issue_log = []
        self.branch_sc = kernel.scenario["branch"]
        self.mispredict_ids = set(self.branch_sc.get("ids", []))
        self._lat_cache = {}
        self.assume("instruction fetch and decode always hit; the two-instruction prefetch buffer per context is not modeled (R02 ch.4 one-clock refill bubble ignored)")
        self.assume("register results are available to any context's dependent instruction exactly latency cycles after issue; no bypass penalties beyond the measured latencies")
        if not any(ev.insn.encoding for c in self.ctx for ev in c.events):
            self.assume("no record carries encoding hints, so every V-eligible instruction is assumed to satisfy the R02 p.56 encoding pairing rules")
        if any(ev.insn.kind in ("x87", "x87load", "x87store") and ev.xreads is None for c in self.ctx for ev in c.events):
            self.assume("x87 instructions without a functional trace are serialized within their context (stack registers unknown statically)")
        if any(ev.insn.kind in ("x87", "x87load", "x87store") for c in self.ctx for ev in c.events):
            self.assume("x87 loads deliver their value at the scalar load latency and x87 stores retire like scalar stores; x87 instructions issue on U only (register-file diagram, R01)")

    # --------------------------------------------------------------------------------------------
    def assume(self, text):
        if text not in self._aset:
            self._aset.add(text)
            self.assumptions.append(text)

    def _param(self, key):
        if key not in self._lat_cache:
            self._lat_cache[key] = self.p.get(key)
        return self._lat_cache[key]

    def latency_of(self, insn, ev):
        """Result latency in cycles for register-writing instructions (not loads)."""
        cls = insn.cls
        key = isa.CLASSES[cls]["latency"]
        if key is None:
            return 0
        if key in ("memory", "gather"):
            return None
        if insn.has_swizzle and cls == "vector_arith":
            self.assume("a swizzled register source raises the operation to the long-vector latency (S6-03 swizzle_*.lat 6)")
            return self._param("latency.vector_long")
        return self._param(key) + self._extend_extra(insn)

    def _extend_extra(self, insn):
        if insn.op not in isa.EXTEND_OPS:
            return 0
        self.assume("sign/zero extensions (movslq, movs*, movz*, cltq) cost a plain mov or scalar load plus latency.scalar_extend_extra "
                    "and pair per pairing.extend_v_pairs: evidence E, inferred, no KNC source")
        return self._param("latency.scalar_extend_extra")

    def _encoding_pairable(self, insn):
        enc = insn.encoding
        if not enc:
            return True
        r = self.enc_rules
        if enc.get("bytes", 0) > r.get("max_bytes", 8):
            return False
        if r.get("no_displacement_and_immediate") and enc.get("disp") and enc.get("imm"):
            return False
        if r.get("no_vex_mvex_with_disp32") and enc.get("disp32") and insn.kind in ("vector", "load", "store", "prefetch") and insn.op.startswith(("v", "k")):
            return False
        return True

    def _occupancy(self, insn, ev):
        """Core cycles both pipes are busy for UV_both instructions (0 = none)."""
        cls = insn.cls
        if cls == "vector_gather":
            n = max(1, len(ev.lines)) if ev.lines else 1
            return self._param("occupancy.gather_cycles_per_line") * n
        if cls == "vector_scatter":
            n = max(1, len(ev.lines)) if ev.lines else 1
            return self._param("occupancy.scatter_cycles_per_line") * n
        if cls == "fence":
            return self._param("latency.fence")
        if cls == "x87_control":
            return self._param("latency.x87_control")
        if cls == "scalar_idiv":
            return self._param("latency.scalar_idiv")
        return 0

    # --------------------------------------------------------------------------------------------
    def _blockers(self, cs, ev, now, l1_used, paired_with=None):
        """Return None if the event can issue now, else the stall reason."""
        insn = ev.insn
        if isa.CLASSES[insn.cls]["pipes"] == "UV_both":
            self._occupancy(insn, ev)  # raises MissingParameter early when the profile lacks it
        for r in _reads(insn, ev):
            if cs.reg_ready.get(r, 0) > now:
                return "dependency"
        for r in insn.addr_regs:
            if cs.reg_written_at.get(r, -10 ** 9) + self.agi > now:
                return "agi"
        if insn.flags_r and cs.flags_ready > now:
            if paired_with is None or (paired_with.insn.op, "jcc") not in self.dep_pairs or not insn.spec.get("cond"):
                return "flags"
        for dep in insn.explicit_deps:
            if cs.last_done.get(dep, 0) > now:
                return "explicit_dep"
        if insn.cls in ("x87_mul", "x87_div", "x87_sqrt") and self.x87_free_at > now:
            return "resource"
        if insn.cls == "prefetch_l2" and self.l2pf_free_at > now:
            return "resource"
        if insn.op.startswith("vmovnr") and self.nr_store_free_at > now:
            return "resource"
        if insn.cls == "vector_gather" and self.gather_free_at > now:
            return "resource"
        touches_l1 = (insn.is_load or insn.is_store or insn.folded_load) and insn.cls not in ("vector_gather", "vector_scatter")
        if touches_l1:
            if l1_used >= self.l1_per_cycle:
                return "l1_port"
            if ev.lines:
                if insn.is_load or insn.folded_load:
                    for la in ev.lines:
                        if self.mem.line_store_ready.get(la, 0) > now:
                            return "dependency"
                ngo = insn.op.startswith("vmovnr")
                _, _, fills, _ = self.mem.plan_demand(ev.lines, now, _vector_access(insn), insn.is_store and not insn.is_load, ngo)
                if fills and not self.mem.can_take_fill(now, fills):
                    return "outstanding_limit"
        if insn.cls in ("vector_gather", "vector_scatter"):
            if l1_used and insn.cls == "vector_scatter":
                return "l1_port"
            if ev.lines:
                _, _, fills, _ = self.mem.plan_demand(ev.lines, now, True, insn.cls == "vector_scatter")
                if fills and not self.mem.can_take_fill(now, min(fills, self.mem.max_outstanding)):
                    return "outstanding_limit"
                if fills > self.mem.max_outstanding:
                    self.assume("a gather/scatter missing on more lines than the outstanding-miss slots is charged all misses in parallel (optimistic by up to one extra latency per window)")
        if insn.cls in ("prefetch_l1", "prefetch_l2") and ev.lines:
            if not self.mem.can_take_fill(now, 1):
                return "outstanding_limit"
        return None

    def _retire(self, cs, ev, now, pipe):
        """Apply the effects of issuing ev at cycle now. Returns completion cycle."""
        insn = ev.insn
        cs.issued += 1
        cs.last_issue_cycle = now
        if cs.first_issue is None:
            cs.first_issue = now
        done = now
        level = None
        cls = insn.cls
        if cls in ("prefetch_l1", "prefetch_l2"):
            if ev.lines:
                self.mem.prefetch(ev.lines[0], insn.spec["level"], now)
            if cls == "prefetch_l2":
                self.l2pf_free_at = now + self._param("occupancy.vprefetch_l2_core_cycles")
        elif cls == "vector_gather":
            lines = ev.lines if ev.lines else ()
            n = max(1, len(lines))
            per = self._param("occupancy.gather_cycles_per_line")
            first = self._param("latency.gather_first_line")
            extra = 0
            if lines:
                ready, level = self.mem.commit_demand(lines, now, True, False)
                extra = max(0, ready - now - self.mem.latency("l1", True))
            self.gather_free_at = now + per * n
            done = now + first + per * (n - 1) + extra
            if extra and self.miss_stalls:
                cs.stall_until = max(cs.stall_until, done)
            if insn.mask is not None:
                # the completion mask is readable long before the data (S6-03 gather_all.rt 7 vs .lat 15)
                cs.reg_ready[insn.mask.base] = now + self._param("latency.gather_mask_cycles") + (per * (n - 1) if n > 1 else 0)
                cs.reg_written_at[insn.mask.base] = now
            self.assume("a gather occupies the gather unit for occupancy.gather_cycles_per_line per distinct line while other instructions keep issuing; its data is ready after latency.gather_first_line plus per-line occupancy")
        elif cls == "vector_scatter":
            lines = ev.lines if ev.lines else ()
            n = max(1, len(lines))
            per = self._param("occupancy.scatter_cycles_per_line")
            if lines:
                self.mem.commit_demand(lines, now, True, True)
                for la in lines:
                    self.mem.line_store_ready[la] = now + per * n
            self.core_busy_until = now + per * n
            done = now + per * n
            self.assume("scatter: occupancy per distinct line like a gather, no result latency, stores visible after the occupancy (assumed)")
        elif cls in ("fence", "x87_control", "scalar_idiv"):
            occ = self._occupancy(insn, ev)
            self.core_busy_until = now + occ
            done = now + occ
            if cls == "x87_control" and ev.lines:
                self.mem.commit_demand(ev.lines, now, False, insn.is_store)
        elif insn.is_load or insn.folded_load or insn.is_store:
            vector = _vector_access(insn)
            ngo = insn.op.startswith("vmovnr")
            if ev.lines:
                ready, level = self.mem.commit_demand(ev.lines, now, vector, insn.is_store and not insn.is_load, ngo)
            else:
                ready, level = now + self.mem.latency("l1", vector), "l1"
                self.assume("memory accesses without addresses (static trace with no addr) are treated as L1 hits")
            if insn.is_store and not insn.is_load:
                for la in ev.lines:
                    self.mem.line_store_ready[la] = now + (self._param("latency.store_to_load_same_line") if self.p.has("latency.store_to_load_same_line") else 1)
                done = now
                if ngo:
                    stall = self._param("store.nr_stall_cycles_resident") if level in ("l1", "l2") else self._param("store.nr_stall_cycles_memory")
                    self.nr_store_free_at = now + self._param("store.nr_occupancy_core_cycles")
                    cs.stall_until = max(cs.stall_until, now + stall)
                    done = now + stall
                    self.assume("no-read stores stall their context for the measured per-line cost and occupy a shared store path (S6-03 store_stream rows)")
                elif level != "l1" and self._param("l1.store_miss_stalls_context"):
                    cs.stall_until = max(cs.stall_until, ready)
                    done = ready
            else:
                if insn.folded_load:
                    base_lat = self.latency_of(insn, ev)
                    l1lat = self.mem.latency("l1", True)
                    done = (now + base_lat) if level == "l1" else max(now + base_lat, ready - l1lat + base_lat)
                    if level != "l1" and self.miss_stalls:
                        cs.stall_until = max(cs.stall_until, ready - l1lat)
                elif cls == "scalar_rmw":
                    alu = self._param("latency.scalar_alu")
                    done = ready + alu
                    for la in ev.lines:
                        self.mem.line_store_ready[la] = done
                    if level != "l1" and self.miss_stalls:
                        cs.stall_until = max(cs.stall_until, ready)
                elif cls in X87_ARITH:
                    # x87 arithmetic with a memory source: the load, then the op on the x87 unit with the
                    # register form's latency and occupancy
                    done = ready + self.latency_of(insn, ev)
                    occ = isa.CLASSES[cls].get("occupancy")
                    if occ:
                        self.x87_free_at = max(self.x87_free_at, ready) + self._param(occ)
                    if level != "l1" and self.miss_stalls:
                        cs.stall_until = max(cs.stall_until, ready)
                else:
                    done = ready + self._extend_extra(insn)
                    if level != "l1" and self.miss_stalls:
                        cs.stall_until = max(cs.stall_until, ready)
                    if insn.is_store:
                        for la in ev.lines:
                            self.mem.line_store_ready[la] = done
        else:
            lat = self.latency_of(insn, ev)
            if lat is None:
                raise Unsupported("instruction %s (%s, class %s) has no result latency rule in the timing model" % (insn.id, insn.op, cls))
            done = now + lat
            if cls in ("x87_mul", "x87_div", "x87_sqrt"):
                occ = isa.CLASSES[cls].get("occupancy")
                self.x87_free_at = now + self._param(occ)
        for r in _writes(insn, ev):
            if cls == "vector_gather" and insn.mask is not None and r == insn.mask.base:
                continue
            cs.reg_ready[r] = done
            cs.reg_written_at[r] = now
        if insn.flags_w:
            if cls in ("scalar_alu", "scalar_imul", "mask_op", "x87_compare"):
                cs.flags_ready = now + (self.latency_of(insn, ev) or 1)
            else:
                cs.flags_ready = max(now + 1, done)
        cs.last_done[insn.id] = done
        if insn.is_branch:
            mis = self._mispredicted(cs, ev)
            if mis:
                pen = self._param("latency.branch_mispredict_penalty")
                cs.next_issue = max(cs.next_issue, now + self.gap + pen)
                cs.stalls["branch_penalty"] += pen
            elif ev.taken and self.taken_bubble:
                cs.next_issue = max(cs.next_issue, now + 1 + self.taken_bubble)
        cs.max_done = max(cs.max_done, done)
        if self.record_issue and len(self.issue_log) < 20000:
            self.issue_log.append({"cycle": now, "ctx": cs.ctx, "id": insn.id, "op": insn.op, "pipe": pipe, "done": done, "level": level})
        return done

    def _mispredicted(self, cs, ev):
        t = self.branch_sc["type"]
        if t == "all_predicted" or ev.insn.op == "jmp":
            return False  # an unconditional jump has no direction to mispredict
        if t == "all_mispredicted":
            return True
        if t == "ids_mispredicted":
            return ev.insn.id in self.mispredict_ids
        prev = cs.prev_direction.get(ev.insn.id)
        cs.prev_direction[ev.insn.id] = ev.taken
        return prev is not None and prev != ev.taken

    def _can_pair(self, cs, u_ev, v_ev, now, l1_used):
        u, v = u_ev.insn, v_ev.insn
        if u.is_branch and not self.p.get("pairing.u_instruction_can_be_branch"):
            return False
        if u.op == "nop" and not self.p.get("pairing.u_nop_pairs"):
            return False
        if v.op == "jmp" and not self.p.get("pairing.v_jmp_pairs"):
            return False
        if v.cls not in self.v_eligible:
            return False
        if v.op in isa.EXTEND_OPS:
            self._extend_extra(v)
            if not self._param("pairing.extend_v_pairs"):
                return False
        if isa.CLASSES[v.cls]["pipes"] == "UV_both" or isa.CLASSES[u.cls]["pipes"] == "UV_both":
            return False
        if not self._encoding_pairable(u) or not self._encoding_pairable(v):
            return False
        uw = _writes(u, u_ev)
        if _reads(v, v_ev) & uw or v.addr_regs & uw:
            return False
        if v.flags_r and u.flags_w:
            if (u.op, "jcc") not in self.dep_pairs or not v.spec.get("cond"):
                return False
        if _writes(v, v_ev) & uw:
            return False
        if u.id in v.explicit_deps:
            return False
        if self._blockers(cs, v_ev, now, l1_used, paired_with=u_ev) is not None:
            return False
        return True

    # --------------------------------------------------------------------------------------------
    def run(self):
        t0 = time.time()
        active = self.ctx
        total_events = sum(len(c.events) for c in active)
        while True:
            now = self.cycle
            if all(c.done for c in active):
                break
            if self.max_cycles is not None and now > self.max_cycles:
                raise BudgetExhausted("cycle budget %d exhausted; %d of %d dynamic instructions issued (partial, not a result)" % (self.max_cycles, sum(c.issued for c in active), total_events),
                                      {"cycles_simulated": now, "issued": sum(c.issued for c in active), "events": total_events},
                                      partial={"cycles": now, "issued": sum(c.issued for c in active)})
            if self.deadline is not None and (now & 1023) == 0 and time.time() > self.deadline:
                raise BudgetExhausted("python time budget exhausted after %d simulated cycles (partial, not a result)" % now,
                                      {"cycles_simulated": now, "issued": sum(c.issued for c in active)})
            if self.core_busy_until > now:
                for c in active:
                    if not c.done:
                        c.stalls["core_busy"] += 1
                self.cycle += 1
                continue
            eligible = []
            for c in active:
                if c.done:
                    continue
                if c.stall_until > now:
                    c.stalls["miss_stall"] += 1
                    continue
                if c.next_issue > now:
                    c.stalls["spacing"] += 1
                    continue
                ev = c.events[c.pos]
                why = self._blockers(c, ev, now, 0)
                if why is not None:
                    c.stalls[why] += 1
                    continue
                eligible.append(c)
            if not eligible:
                self.cycle += 1
                continue
            eligible.sort(key=lambda c: (c.last_issue, c.ctx))
            cs = eligible[0]
            for c in eligible[1:]:
                c.stalls["not_picked"] += 1
            u_ev = cs.events[cs.pos]
            l1_used = 1 if (u_ev.insn.is_load or u_ev.insn.is_store or u_ev.insn.folded_load) else 0
            cs.pos += 1
            self._retire(cs, u_ev, now, "U")
            if cs.pos < len(cs.events) and cs.stall_until <= now and self.core_busy_until <= now:
                v_ev = cs.events[cs.pos]
                if self._can_pair(cs, u_ev, v_ev, now, l1_used):
                    cs.pos += 1
                    cs.pairs += 1
                    self._retire(cs, v_ev, now, "V")
            cs.last_issue = now
            cs.next_issue = max(cs.next_issue, now + self.gap)
            self.cycle += 1
        end_issue = max((c.last_issue_cycle or 0) for c in active) + 1
        completion = max(end_issue, max(c.max_done for c in active))
        self.python_seconds = time.time() - t0
        return self._result(end_issue, completion, total_events)

    def _result(self, end_issue, completion, total_events):
        per_ctx = {}
        for c in self.ctx:
            per_ctx[str(c.ctx)] = {"dynamic_instructions": len(c.events), "issued": c.issued, "pairs": c.pairs,
                                  "first_issue": c.first_issue, "last_issue": c.last_issue_cycle, "completion": c.max_done,
                                  "stall_cycles": {k: v for k, v in c.stalls.items() if v}}
        issue_events = sum(c.issued - c.pairs for c in self.ctx)
        return {
            "completion_cycles": completion,
            "issue_span_cycles": end_issue,
            "dynamic_instructions": total_events,
            "issue_events": issue_events,
            "core_issue_utilization": round(issue_events / float(max(1, end_issue)), 4),
            "pair_fraction": round(sum(c.pairs for c in self.ctx) * 2.0 / max(1, total_events), 4),
            "active_contexts": [c.ctx for c in self.ctx],
            "per_context": per_ctx,
            "memory": self.mem.describe(),
            "python_seconds": round(self.python_seconds, 4),
        }


def limiting_constraints(res):
    """Name the dominant stall reasons across contexts (for the report)."""
    agg = {}
    for c in res["per_context"].values():
        for k, v in c["stall_cycles"].items():
            agg[k] = agg.get(k, 0) + v
    ranked = sorted(agg.items(), key=lambda kv: -kv[1])
    out = []
    for k, v in ranked[:4]:
        out.append({"constraint": k, "context_cycles": v})
    util = res["core_issue_utilization"]
    if util >= 0.9:
        out.insert(0, {"constraint": "core_issue_slots", "detail": "issue utilization %.2f: the core issues nearly every cycle" % util})
    return out
