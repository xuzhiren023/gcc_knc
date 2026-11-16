"""Cycle-level core model: four in-order hardware contexts, U/V issue with pairing rules,
same-context issue spacing, round-robin context selection, scoreboarded register
dependencies (including x87 physical registers from the functional trace), address-
generation interlock, demand-miss stalls, nonblocking software prefetches, resource
occupancy. No speculation, no out-of-order issue.

Cycles here are predicted KNC core cycles. Python wall time is reported separately.
"""
import time

from .cache import MemoryModel, SetAssoc
from .errors import BudgetExhausted, MissingParameter, Unsupported
from . import isa

X87_ARITH = ("x87_add", "x87_mul", "x87_div", "x87_sqrt")
STALL_REASONS = ("spacing", "miss_stall", "dependency", "agi", "flags", "explicit_dep", "x87_serial", "resource",
                 "outstanding_limit", "l1_port", "core_busy", "not_picked", "branch_penalty", "done",
                 "decode", "icache_miss", "store_interlock", "stub_call", "nr_store")


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
        self.last_store_issue = -10 ** 9
        self.stall_reason = None
        self.decode_until = 0
        self.fetch_checked = -1
        self.prev_ret_target = {}

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
        self.x87_pairs = profile.get("pairing.x87_pairs_with_scalar")
        self.v_nop_pairs = profile.get("pairing.v_nop_pairs")
        self.load_store_pair = profile.get("pairing.load_store_pair")
        self.store_interlock = profile.get("store.load_after_store_interlock_cycles")
        self.slow_prefix = profile.get("frontend.slow_prefix_decode_cycles")
        self.core_bubble = profile.get("frontend.taken_branch_core_bubble_cycles")
        self.has_layout = any(ev.insn.encoding.get("bytes") for c in self.ctx for ev in c.events)
        fe = kernel.scenario.get("frontend", {})
        self.icache = None
        if fe.get("icache", "warm") != "warm":
            if not self.has_layout:
                raise Unsupported("scenario.frontend.icache=%r needs instruction addresses (records with encoding.addr; use scripts/from_binary.py)" % fe.get("icache"))
            self.icache = SetAssoc(profile.get("l1i.size_bytes"), profile.get("l1i.ways"))
            self.icache_latency = profile.get("latency.l2_hit") if fe["icache"] == "cold_l2" else profile.get("latency.memory")
            self.assume("instruction cache sub-model: %s code lines, each first touch stalls the context for the data-side %s latency (assumed equal for code)" % (fe["icache"], "L2" if fe["icache"] == "cold_l2" else "memory"))
        self.frontend_stats = {"layout": self.has_layout, "slow_prefix_instructions": 0, "decode_delay_cycles": 0, "icache_misses": 0,
                               "taken_branch_bubbles": 0, "padding_nops": 0}
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
        if self.has_layout:
            self.assume("front end: instruction bytes come from the listing; each two-cycle prefix (66, 67, lock, segment, rep: R02 p.56) delays that instruction's issue to %d cycles per prefix after the previous issue of its context, which the %d-cycle same-context spacing hides for one prefix (S12-31 padding rows); an instruction with such a prefix does not pair (assumed)" % (self.slow_prefix, self.gap))
            self.assume("front end: crossing a 16-byte or 64-byte boundary and the loop-head offset cost nothing (S12-31 mis_4..mis_60 within 0.45 ns per row)")
        else:
            self.assume("no code layout (records without encoding.bytes): prefix decode delays, alignment padding and encoding pairing limits are not modeled; convert a disassembly with scripts/from_binary.py to include them")
        if self.icache is None:
            self.assume("instruction cache: code is assumed resident in the L1 instruction cache (steady-state hot region)")
        if self.core_bubble:
            self.assume("a taken forward branch, call or return costs the core %d issue cycle(s) for the prefetch-buffer refill (R02 ch.4; S8-01 C10 fixed-direction row at four threads); loop back-edges pay nothing (S8-01 C9 at two threads); hidden at one thread by the same-context spacing" % self.core_bubble)
        self.assume("register results are available to any context's dependent instruction exactly latency cycles after issue; no bypass penalties beyond the measured latencies")
        if not any(ev.insn.encoding for c in self.ctx for ev in c.events):
            self.assume("no record carries encoding hints, so every V-eligible instruction is assumed to satisfy the R02 p.56 encoding pairing rules")
        if any(ev.insn.kind in ("x87", "x87load", "x87store") and ev.xreads is None for c in self.ctx for ev in c.events):
            self.assume("x87 instructions without a functional trace are serialized within their context (stack registers unknown statically)")
        if any(ev.insn.kind in ("x87", "x87load", "x87store") for c in self.ctx for ev in c.events):
            self.assume("x87 instructions issue on U only (register-file diagram, R01) and alone (S12-31); a memory-operand x87 load or arithmetic instruction holds its context until its result is complete; x87 stores retire like scalar stores")

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
        if cls in ("fence", "locked_rmw"):
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
        if ev.stub is not None:
            name = ev.stub
            stub = self.kernel.calls[name]
            if stub.get("cycles") is None:
                raise MissingParameter("call to %s has no cost: give calls.%s.cycles in the kernel (a stub never gets a default cost)" % (name, name),
                                       {"parameter": "calls.%s.cycles" % name})
            return None
        touches_l1 = (insn.is_load or insn.is_store or insn.folded_load) and insn.cls not in ("vector_gather", "vector_scatter")
        reads_mem = insn.is_load or insn.folded_load
        if reads_mem and self.store_interlock and cs.last_store_issue + self.store_interlock > now:
            return "store_interlock"
        if touches_l1:
            # l1_used: bit 1 = a load issued this cycle, bit 2 = a store did. The port takes one load and one store
            # per cycle when pairing.load_store_pair (spill_reload.rt at four threads), else one access.
            if self.load_store_pair:
                busy = (l1_used & 1 and reads_mem) or (l1_used & 2 and insn.is_store and not insn.is_load)
            else:
                busy = l1_used != 0
            if busy:
                return "l1_port"
            if ev.lines:
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
        if insn.encoding.get("slow_prefixes"):
            self.frontend_stats["slow_prefix_instructions"] += 1
        if insn.op == "nop" and insn.encoding.get("bytes"):
            self.frontend_stats["padding_nops"] += 1
        if ev.stub is not None:
            stub = self.kernel.calls[ev.stub]
            cost = stub["cycles"] + stub.get("cycles_per_byte", 0) * ev.nbytes
            cost = int(-(-cost // 1))
            if ev.lines and stub.get("model") in ("memcpy", "memmove", "memset"):
                self.mem.commit_demand(ev.lines, now, False, stub.get("model") == "memset")
            done = now + cost
            self._stall(cs, done, "stub_call")
            self.assume("calls that leave the region are costed stubs: the calling context stalls for the declared cycles; the callee's own cache and resource use is not modeled (mem* stubs touch their lines)")
        elif cls in ("prefetch_l1", "prefetch_l2"):
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
            self.gather_free_at = max(self.gather_free_at, now) + per * n
            done = now + first + per * (n - 1) + extra
            if extra and self.miss_stalls:
                self._stall(cs, done, "miss_stall")
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
        elif cls in ("fence", "x87_control", "scalar_idiv", "locked_rmw"):
            occ = self._occupancy(insn, ev)
            self.core_busy_until = now + occ
            done = now + occ
            if cls in ("x87_control", "locked_rmw") and ev.lines:
                self.mem.commit_demand(ev.lines, now, False, insn.is_store)
            if insn.is_store:
                cs.last_store_issue = now
                for la in ev.lines:
                    self.mem.line_store_ready[la] = done
        elif insn.is_load or insn.folded_load or insn.is_store:
            vector = _vector_access(insn)
            ngo = insn.op.startswith("vmovnr")
            if ev.lines:
                ready, level = self.mem.commit_demand(ev.lines, now, vector, insn.is_store and not insn.is_load, ngo)
            else:
                ready, level = now + self.mem.latency("l1", vector), "l1"
                self.assume("memory accesses without addresses (static trace with no addr) are treated as L1 hits")
            fwd = 0
            if insn.is_load or insn.folded_load:
                # data stored to the same line recently is readable store_to_load_same_line cycles after the store;
                # the load itself issues (it does not block its context) and its result waits for that data
                fwd = max([self.mem.line_store_ready.get(la, 0) for la in ev.lines] or [0])
                if fwd > now and not insn.folded_load:
                    ready = max(ready, fwd + self.mem.latency("l1", vector))
            if insn.is_store:
                cs.last_store_issue = now
            if insn.is_store and not insn.is_load:
                for la in ev.lines:
                    self.mem.line_store_ready[la] = now + (self._param("latency.store_to_load_same_line") if self.p.has("latency.store_to_load_same_line") else 1)
                done = now
                if ngo:
                    stall = self._param("store.nr_stall_cycles_resident") if level in ("l1", "l2") else self._param("store.nr_stall_cycles_memory")
                    self.nr_store_free_at = now + self._param("store.nr_occupancy_core_cycles")
                    self._stall(cs, now + stall, "nr_store")
                    done = now + stall
                    self.assume("no-read stores stall their context for the measured per-line cost and occupy a shared store path (S6-03 store_stream rows)")
                elif level != "l1" and self._param("l1.store_miss_stalls_context"):
                    self._stall(cs, ready, "miss_stall")
                    done = ready
            else:
                if insn.folded_load:
                    base_lat = self.latency_of(insn, ev)
                    l1lat = self.mem.latency("l1", True)
                    done = (now + base_lat) if level == "l1" else max(now + base_lat, ready - l1lat + base_lat)
                    if fwd > now:
                        done = max(done, fwd + base_lat)
                    if level != "l1" and self.miss_stalls:
                        self._stall(cs, ready - l1lat, "miss_stall")
                elif cls == "scalar_rmw":
                    alu = self._param("latency.scalar_alu")
                    done = ready + alu
                    for la in ev.lines:
                        self.mem.line_store_ready[la] = done
                    if level != "l1" and self.miss_stalls:
                        cs.stall_until = max(cs.stall_until, ready)
                elif cls in X87_ARITH or cls == "x87_load":
                    # x87 instruction with a memory operand: the operand read, then (for arithmetic) the op with the
                    # register form's latency and occupancy. The context issues nothing else until the result is
                    # complete (x87.mem_operand_serializes; S12-31 loop-body orders).
                    l1lat = self.mem.latency("l1", False)
                    miss_extra = max(0, ready - now - l1lat)
                    if cls == "x87_load":
                        done = now + miss_extra + self._param("latency.x87_load")
                    else:
                        start = now + miss_extra + self._param("latency.x87_mem_operand_load")
                        done = start + self.latency_of(insn, ev)
                        occ = isa.CLASSES[cls].get("occupancy")
                        if occ:
                            self.x87_free_at = max(self.x87_free_at, start) + self._param(occ)
                    if self._param("x87.mem_operand_serializes"):
                        if level != "l1" and self.miss_stalls:
                            self._stall(cs, ready, "miss_stall")
                        self._stall(cs, done, "x87_serial")
                    elif level != "l1" and self.miss_stalls:
                        self._stall(cs, ready, "miss_stall")
                else:
                    done = ready + self._extend_extra(insn)
                    if level != "l1" and self.miss_stalls:
                        self._stall(cs, ready, "miss_stall")
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
        if getattr(insn, "sets_mxcsr", False):
            cs.reg_ready["mxcsr"] = max(cs.reg_ready.get("mxcsr", 0), done)   # stmxcsr waits for the flags of every earlier FP op
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
            if ev.taken and self.core_bubble and self._forward_transfer(cs, ev):
                self.core_busy_until = max(self.core_busy_until, now + 1 + self.core_bubble)
                self.frontend_stats["taken_branch_bubbles"] += 1
        cs.max_done = max(cs.max_done, done)
        if self.record_issue and len(self.issue_log) < 20000:
            self.issue_log.append({"cycle": now, "ctx": cs.ctx, "id": insn.id, "op": insn.op, "pipe": pipe, "done": done, "level": level})
        return done

    def _forward_transfer(self, cs, ev):
        """A taken control transfer to code after the branch (or a call/return): the prefetch buffer holds the
        fall-through, so it refills. A loop back-edge to an earlier target pays nothing (S8-01 C9 register
        chains at two threads: 4.02/3.01/2.51 per update, no core cycle lost per iteration)."""
        insn = ev.insn
        if insn.op in ("call", "ret"):
            return True
        if insn.target is None:
            return True
        stream = self.kernel.stream_for(cs.ctx)
        tgt = stream.labels.get(insn.target)
        return tgt is None or tgt > insn.index

    def _stall(self, cs, until, reason):
        """Hold the context until `until`; the stall cycles are attributed to `reason` (the latest, longest cause wins)."""
        if until > cs.stall_until:
            cs.stall_until = until
            cs.stall_reason = reason
        elif until > self.cycle and cs.stall_reason is None:
            cs.stall_reason = reason

    def _mispredicted(self, cs, ev):
        t = self.branch_sc["type"]
        if t == "all_predicted" or ev.insn.op in ("jmp", "call"):
            return False  # an unconditional jump or direct call has no direction to mispredict
        if ev.insn.op == "ret":
            if t == "all_mispredicted":
                return True
            prev = cs.prev_ret_target.get(ev.insn.id)
            cs.prev_ret_target[ev.insn.id] = ev.ret_target
            self.assume("a ret is predicted when it returns to the same site as its previous execution (branch-target-buffer behaviour, assumed; no return stack is documented)")
            return prev is not None and prev != ev.ret_target
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
        if v.op == "nop" and not self.v_nop_pairs:
            return False
        if u.kind.startswith("x87") and not self.x87_pairs:
            return False
        if v.encoding.get("slow_prefixes"):
            return False
        if u_ev.stub is not None or v_ev.stub is not None:
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
        if self.icache is not None and not self._fetch_ok(cs, v_ev, now, probe=True):
            return False
        return True

    def _fetch_ok(self, cs, ev, now, probe=False):
        """Instruction-cache check for the event's code lines (only with scenario.frontend.icache cold)."""
        enc = ev.insn.encoding
        if enc.get("addr") is None:
            return True
        a = int(enc["addr"]) if not isinstance(enc["addr"], str) else int(enc["addr"], 0)
        first, last = a // 64 * 64, (a + max(1, enc.get("bytes", 1)) - 1) // 64 * 64
        miss = [la for la in range(first, last + 64, 64) if self.icache.lookup(la) is None]
        if not miss:
            return True
        if probe:
            return False
        for la in miss:
            self.icache.insert(la, now + self.icache_latency)
        self.frontend_stats["icache_misses"] += len(miss)
        self._stall(cs, now + self.icache_latency, "icache_miss")
        return False

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
                    c.stalls[c.stall_reason or "miss_stall"] += 1
                    continue
                if c.next_issue > now:
                    c.stalls["spacing"] += 1
                    continue
                ev = c.events[c.pos]
                if c.decode_until > now:
                    c.stalls["decode"] += 1
                    continue
                if self.icache is not None and c.fetch_checked != c.pos:
                    if not self._fetch_ok(c, ev, now):
                        c.stalls["icache_miss"] += 1
                        continue
                    c.fetch_checked = c.pos
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
            ui = u_ev.insn
            l1_used = (1 if (ui.is_load or ui.folded_load) else 0) | (2 if ui.is_store else 0)
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
            if self.has_layout and cs.pos < len(cs.events):
                k = cs.events[cs.pos].insn.encoding.get("slow_prefixes", 0)
                if k:
                    cs.decode_until = now + self.slow_prefix * k
                    self.frontend_stats["decode_delay_cycles"] += max(0, cs.decode_until - cs.next_issue)
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
            "frontend": dict(self.frontend_stats),
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
