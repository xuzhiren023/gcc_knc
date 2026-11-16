"""Causal ring/TD/channel simulation, standard library only.

Geometry and effective service assumptions: references/multicore-design.md.
This is a scenario model, never hardware validation or a complete MESI engine.
Events at a timestamp complete before core issue; new requests arbitrate later
at that timestamp. Link arrivals reserve only their current link, not a route.
"""
import copy
import heapq
import math
import time
from collections import Counter, deque

from .cache import MemoryModel, SetAssoc
from .errors import BudgetExhausted, InvalidInput, Unsupported
from .profile import Param, load_profile
from .timing import CoreSim, _reads, _writes, _vector_access


class Transaction(object):
    def __init__(self, **info):
        self.done = False
        self.info = info
        self.callbacks = []

    def result(self):
        if not self.done:
            raise RuntimeError("transaction has not completed")
        return dict(self.info)

    def then(self, callback):
        if self.done:
            callback(self)
        else:
            self.callbacks.append(callback)
        return self

    def finish(self, now, **info):
        self.info.update(info, completed_cycle=now)
        self.done = True
        callbacks, self.callbacks = self.callbacks, []
        for callback in callbacks:
            callback(self)


class Fabric(object):
    def __init__(self, profile, placement, background=False, scenario=None,
                 max_events=2000000, max_pending=200000, max_cycles=None, deadline=None):
        self.p = profile
        # Direct protocol probes use the same explicit layer as CLI simulations.
        layer = load_profile("multicore-assumed")
        for key, value in layer.params.items():
            if key not in profile.params:
                profile.params[key] = value
        self.sc = scenario or {}
        self.positions = self.p.get("ring.positions")
        self.placement = dict(placement)
        if (not self.placement or len(set(self.placement.values())) != len(self.placement)
                or any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < self.positions
                       for v in self.placement.values())):
            raise InvalidInput("placement must give distinct ring positions for every detailed core")
        self.ntd = self.p.get("td.slices")
        self.nmc = self.p.get("memory.controllers")
        self.nch = self.nmc * self.p.get("memory.channels_per_controller")
        self.td_map = self.sc.get("td_interleave", self.p.get("td.interleave"))
        self.ch_map = self.sc.get("channel_interleave", self.p.get("memory.channel_interleave"))
        if self.td_map not in ("xor", "line_modulo", "single_slice") or self.ch_map not in (
                "xor", "line_modulo", "page", "single_channel"):
            raise InvalidInput("unknown TD/channel interleave")
        self.td_positions = self._positions("td_positions", self.ntd)
        self.mc_positions = self._positions("controller_positions", self.nmc)
        self.hop = self.p.get("ring.hop_cycles")
        self.control = self.p.get("ring.control_service_cycles")
        self.data = math.ceil(64 / self.p.get("ring.data_slot_bytes"))
        self.shared = self.p.get("ring.shared_fabrics")
        self.credits = self.p.get("ring.injection_credits")
        self.lookup = self.p.get("td.lookup_cycles")
        self.td_interval = self.p.get("td.initiation_cycles")
        self.core_interval = self.p.get("memory.core_service_cycles_per_line")
        self.write_ratio = self.p.get("memory.write_read_service_ratio")
        if any(v < 0 for v in (self.hop, self.control, self.lookup, self.td_interval, self.core_interval)) or self.credits < 1:
            raise InvalidInput("fabric latencies must be nonnegative and credits positive")
        if not self.p.has("memory.channel_service_cycles_per_line"):
            self._derived("memory.channel_service_cycles_per_line",
                          self.nch * 64 * self.p.get("card.clock_hz") /
                          (self.p.get_sub("card.sustained_bandwidth_gbs", "read_only") * 1e9),
                          "equal channel sharing derived from selected card read calibration; not a channel measurement")
        self.interval = self.p.get("memory.channel_service_cycles_per_line")
        if self.interval <= 0 or self.write_ratio <= 0:
            raise InvalidInput("channel intervals must be positive")
        # Unloaded reference path averaged over ALL contracted positions and
        # slices, independently of the user's detailed-core placement.
        avg_req_td = sum(self.distance(a, d) for a in range(self.positions)
                         for d in self.td_positions) / float(self.positions * self.ntd)
        avg_pair = sum(self.distance(a, b) for a in range(self.positions)
                       for b in range(self.positions)) / float(self.positions ** 2)
        remote_ref = ((2 * avg_req_td + avg_pair) * self.hop + self.lookup
                      + self.p.get("latency.l2_hit") + 2 * self.control + self.data)
        anchor = self.p.get("latency.remote_l2_line_ns") * self.p.get("card.clock_hz") / 1e9
        self._derived("multicore.remote_reference_path_cycles", remote_ref,
                      "unloaded requester/TD/source paths averaged over contracted geometry")
        self._derived("multicore.remote_endpoint_residual_cycles", anchor - remote_ref,
                      "S8-10 C11 192 ns anchor (reported production card), minus reference route/TD/L2 costs; calibration")
        self.remote_residual = self.p.get("multicore.remote_endpoint_residual_cycles")
        self.remote_extra = self.p.get("multicore.remote_extra_cycles")
        avg_td_mc = sum(self.distance(d, m) for d in self.td_positions for m in self.mc_positions) / float(self.ntd * self.nmc)
        avg_mc_req = sum(self.distance(m, a) for m in self.mc_positions for a in range(self.positions)) / float(self.nmc * self.positions)
        memory_ref = (avg_req_td + avg_td_mc + avg_mc_req) * self.hop + self.lookup + 2 * self.control + self.data
        self._derived("multicore.memory_reference_path_cycles", memory_ref,
                      "unloaded requester/TD/controller paths averaged over contracted geometry")
        self._derived("multicore.memory_endpoint_residual_cycles", self.p.get("latency.memory") - memory_ref,
                      "S6-03 memory latency calibration minus reference route/TD; DTLB charged separately")
        self.memory_residual = self.p.get("multicore.memory_endpoint_residual_cycles")
        if min(self.remote_residual, self.memory_residual) < 0:
            raise InvalidInput("route costs exceed latency anchor; negative endpoint residual")
        self.now = 0.0
        self.seq = 0
        self.events = []
        self.event_count = 0
        self.max_events, self.max_pending = max_events, max_pending
        self.max_cycles, self.deadline = max_cycles, deadline
        self.link_free = {}
        self.link_stats = {}
        self.td_free = [0.0] * self.ntd
        self.channel_free = [0.0] * self.nch
        self.injection_free = {}
        self.outstanding = Counter()
        self.injection_wait = {}
        self.lines = [{} for _ in range(self.ntd)]
        self.backends = {}
        self.offers = Counter()
        self.sources = Counter()
        self.completed_by_core = Counter()
        self.controllers = [dict(controller=c, detailed_issued=0, detailed_served=0,
                                 background_issued=0, background_served=0, read_transactions=0,
                                 write_transactions=0, queue_wait_cycles=0.0,
                                 physical_bytes=0, peak_queued=0) for c in range(self.nmc)]
        self.channel_queued = [0] * self.nch
        self.background = background
        self.background_stopped = False
        self.background_serial = 0
        self.epoch_history = []

    def _derived(self, key, value, source):
        self.p.params[key] = Param(key, dict(value=value, unit="cycles", status="derived", source=source))
        self.p.get(key)

    def _positions(self, key, count):
        out = self.sc.get(key, [i * self.positions // count for i in range(count)])
        if len(out) != count or any(not isinstance(x, int) or not 0 <= x < self.positions for x in out):
            raise InvalidInput("invalid %s" % key)
        return list(out)

    def parameters_used(self):
        return self.p.used_summary()

    def distance(self, a, b):
        return min((b - a) % self.positions, (a - b) % self.positions)

    def directory(self, address):
        line = address // 64
        return 0 if self.td_map == "single_slice" else ((line ^ (line >> 6)) if self.td_map == "xor" else line) % self.ntd

    def channel(self, address):
        line = address // 64
        if self.ch_map == "single_channel":
            return 0
        return (line ^ (line >> 6) if self.ch_map == "xor" else
                line // 64 if self.ch_map == "page" else line) % self.nch

    def schedule(self, at, callback, *args):
        if len(self.events) >= self.max_pending:
            raise BudgetExhausted("fabric pending-event budget exhausted", partial=self.partial())
        self.seq += 1
        heapq.heappush(self.events, (max(at, self.now), self.seq, callback, args))

    def partial(self):
        return dict(cycles=self.now, events=self.event_count, pending_events=len(self.events))

    def advance(self, until):
        while self.events and self.events[0][0] <= until:
            at, _, callback, args = heapq.heappop(self.events)
            if self.max_cycles is not None and at > self.max_cycles:
                raise BudgetExhausted("fabric cycle budget exhausted", partial=self.partial())
            self.now = at
            self.event_count += 1
            if self.event_count > self.max_events:
                raise BudgetExhausted("fabric event budget exhausted", partial=self.partial())
            if self.deadline is not None and self.event_count % 1024 == 0 and time.time() > self.deadline:
                raise BudgetExhausted("fabric wall-time budget exhausted", partial=self.partial())
            callback(*args)
        self.now = until

    def drain(self):
        while self.events:
            self.advance(self.events[0][0])

    def route(self, src, dst, kind, callback):
        """Wormhole-like pipelined packet: per-link occupancy, tail at destination.

        Service holds a link independently of propagation. No whole-route
        reservation; a downstream arrival competes with already arrived traffic.
        This effective packet model is an assumption, not a wire-width claim.
        """
        service = self.data if kind == "data" else self.control
        if src == dst:
            self.schedule(self.now, callback)
            return
        direction = 1 if (dst - src) % self.positions <= (src - dst) % self.positions else -1
        def hop(pos):
            key = ("shared" if self.shared else kind, pos, direction)
            start = max(self.now, self.link_free.get(key, 0))
            stat = self.link_stats.setdefault(key, dict(hops=0, occupied_cycles=0, wait_cycles=0, bytes=0))
            stat["hops"] += 1
            stat["occupied_cycles"] += service
            stat["wait_cycles"] += start - self.now
            stat["bytes"] += 64 if kind == "data" else 0
            self.link_free[key] = start + service
            nxt = (pos + direction) % self.positions
            if nxt == dst:
                self.schedule(start + self.hop + service, callback)
            else:
                self.schedule(start + self.hop, hop, nxt)
        hop(src)

    def request(self, core, address, operation, background=False, destination=None):
        if operation not in ("read", "write", "no_read", "writeback"):
            raise Unsupported("unknown fabric operation %r" % operation)
        if core not in self.placement:
            raise InvalidInput("request from core without placement")
        address = address // 64 * 64
        td, ch = destination or (self.directory(address), self.channel(address))
        tx = Transaction(core=core, address=address, operation=operation, issued_cycle=self.now,
                         directory=td, channel=ch, memory_transactions=0, background=background)
        if not background:
            self.offers[(operation, td, ch)] += 1
        q = self.injection_wait.setdefault(core, deque())
        q.append(tx)
        if sum(map(len, self.injection_wait.values())) > self.max_pending:
            raise BudgetExhausted("injection storage budget exhausted", partial=self.partial())
        self._inject(core)
        return tx

    def _inject(self, core):
        q = self.injection_wait[core]
        while q and self.outstanding[core] < self.credits:
            tx = q.popleft()
            self.outstanding[core] += 1
            start = max(self.now, self.injection_free.get(core, 0))
            self.injection_free[core] = start + self.core_interval
            self.schedule(start, self._to_td, tx)

    def _to_td(self, tx):
        i = tx.info
        self.route(self.placement[i["core"]], self.td_positions[i["directory"]], "address",
                   lambda: self._at_td(tx))

    def _at_td(self, tx):
        i = tx.info
        td = i["directory"]
        start = max(self.now, self.td_free[td])
        self.td_free[td] = start + self.td_interval
        self.schedule(start + self.lookup, self._line_queue, tx)

    def _line_queue(self, tx):
        i = tx.info
        state = self.lines[i["directory"]].setdefault(i["address"],
                    dict(owner=None, sharers=set(), pending=deque(), busy=False))
        state["pending"].append(tx)
        if not state["busy"]:
            self._serve_line(state)
        elif (i["operation"] == "read" and not state["pending"][0].done
              and all(p.info["operation"] == "read" for p in state["pending"])):
            # Compatible reads join the outstanding fill. Conflicting writes
            # keep FIFO order; no sharer or cache copy is installed early.
            primary = state["pending"][0]
            state["active"].add(tx)
            i.update(source="merged_read", source_core=primary.info["core"],
                     response_path_hops=self.distance(self.placement[primary.info["core"]],
                                                     self.placement[i["core"]]))
            primary.then(lambda _: self.route(self.placement[primary.info["core"]],
                         self.placement[i["core"]], "data", lambda: self._finish_line(tx, state)))

    def _serve_line(self, state):
        if not state["pending"]:
            state["busy"] = False
            return
        state["busy"] = True
        tx = state["pending"][0]
        state["active"] = {tx}
        i = tx.info
        core, td, op = i["core"], i["directory"], i["operation"]
        reqpos, tdpos = self.placement[core], self.td_positions[td]
        owner = state["owner"]
        source = owner if owner is not None else (min(state["sharers"], key=lambda c: (self.distance(self.placement[c], reqpos), c)) if state["sharers"] else None)
        if op == "writeback":
            i["source"] = "writeback"
            self._memory(tx, True, lambda: self._finish_line(tx, state))
        elif op == "no_read":
            i["source"] = "no_read"
            self._invalidate(tx, state, lambda: self._memory(tx, True, lambda: self._finish_line(tx, state)))
        elif source is not None:
            i["source"], i["source_core"] = ("local_l2" if source == core else "remote_l2"), source
            sourcepos = self.placement[source]
            i["response_path_hops"] = self.distance(reqpos, tdpos) + self.distance(tdpos, sourcepos) + self.distance(sourcepos, reqpos)
            latency = self.p.get("latency.l2_hit") + (self.remote_residual + self.remote_extra if source != core else 0)
            def sourced():
                self.schedule(self.now + latency, lambda: self.route(sourcepos, reqpos, "data",
                              lambda: self._after_data(tx, state)))
            self.route(tdpos, sourcepos, "address", sourced)
        else:
            i["source"] = "memory"
            self._memory(tx, False, lambda: self._after_data(tx, state))

    def _after_data(self, tx, state):
        if tx.info["operation"] == "write":
            self._invalidate(tx, state, lambda: self._finish_line(tx, state))
        else:
            self._finish_line(tx, state)

    def _invalidate(self, tx, state, callback):
        core = tx.info["core"]
        targets = sorted(state["sharers"] - {core})
        if not targets:
            callback()
            return
        left = [len(targets)]
        tdpos = self.td_positions[tx.info["directory"]]
        def ack():
            left[0] -= 1
            if not left[0]:
                callback()
        for other in targets:
            def invalidate(c=other):
                backend = self.backends.get(c)
                if backend:
                    backend.l1.remove(tx.info["address"])
                    backend.l2.remove(tx.info["address"])
                state["sharers"].discard(c)
                self.route(self.placement[c], tdpos, "ack", ack)
            self.route(tdpos, self.placement[other], "address", invalidate)

    def _memory(self, tx, write, callback):
        i = tx.info
        ch = i["channel"]
        mc = ch // self.p.get("memory.channels_per_controller")
        stat = self.controllers[mc]
        who = "background" if i["background"] else "detailed"
        stat[who + "_issued"] += 1
        stat["write_transactions" if write else "read_transactions"] += 1
        i["memory_transactions"] += 1
        src = self.placement[i["core"]] if write else self.td_positions[i["directory"]]
        def arrival():
            start = max(self.now, self.channel_free[ch])
            stat["queue_wait_cycles"] += start - self.now
            # Fractional service is accumulated, not ceil-rounded for every line.
            self.channel_free[ch] = start + self.interval * (self.write_ratio if write else 1)
            self.channel_queued[ch] += 1
            stat["peak_queued"] = max(stat["peak_queued"], self.channel_queued[ch])
            def served():
                self.channel_queued[ch] -= 1
                stat[who + "_served"] += 1
                stat["physical_bytes"] += 64
                self.route(self.mc_positions[mc], self.placement[i["core"]], "ack" if write else "data", callback)
            self.schedule(start + self.memory_residual, served)
        self.route(src, self.mc_positions[mc], "data" if write else "address", arrival)

    def _finish_line(self, tx, state):
        i = tx.info
        core, op = i["core"], i["operation"]
        if op == "writeback":
            if state["owner"] == core:
                state["owner"] = None
            state["sharers"].discard(core)
        else:
            state["sharers"].add(core)
            if op in ("write", "no_read"):
                state["owner"] = core if op == "write" else None
        i["owner"] = state["owner"]
        self.sources[("background:" if i["background"] else "") + i["source"]] += 1
        self.completed_by_core[core] = max(self.completed_by_core[core], self.now)
        tx.finish(self.now)
        # Data is usable now; directory serialization/credits release after ack.
        def acknowledged():
            state["pending"].remove(tx)
            state["active"].discard(tx)
            self.outstanding[core] -= 1
            self._inject(core)
            if not state["active"]:
                self._serve_line(state)
            if not state["pending"] and (i["background"] or not state["sharers"]):
                self.lines[i["directory"]].pop(i["address"], None)
        self.route(self.placement[core], self.td_positions[i["directory"]], "ack", acknowledged)

    def evict(self, core, address):
        state = self.lines[self.directory(address)].get(address)
        if state is None:
            return
        if state["owner"] == core:
            self.request(core, address, "writeback")
        else:
            state["sharers"].discard(core)
            if not state["sharers"] and not state["pending"]:
                self.lines[self.directory(address)].pop(address, None)

    def flush(self):
        for table in self.lines:
            for address, state in list(table.items()):
                if state["owner"] is not None:
                    self.request(state["owner"], address, "writeback")

    def start_background(self, detailed, active, epoch, seed, warmup_offers):
        unused = [p for p in range(self.positions) if p not in self.placement.values()]
        count = active - detailed
        if count < 0 or count > len(unused) or epoch <= 0:
            raise InvalidInput("invalid background active_cores/epoch_cycles")
        ids = [max(self.placement) + 1 + i for i in range(count)]
        for i, core in enumerate(ids):
            self.placement[core] = unused[i]
        carry = {}
        destination_credit = {}
        def begin(offered):
            if self.background_stopped:
                return
            self.epoch_history.append(dict(cycle=self.now, offered=sum(offered.values()), background_cores=count))
            if len(self.epoch_history) > 256:
                self.epoch_history.pop(0)
            for core in ids:
                # Carry the total offered rate, then apportion whole packets by
                # accumulated destination debt. Rounding each (core, TD, channel)
                # separately can starve a short stream that visits many slices.
                credit = carry.get(core, 0) + sum(offered.values()) / float(detailed)
                whole = int(credit)
                carry[core] = credit - whole
                debt = destination_credit.setdefault(core, Counter())
                for dest, n in offered.items():
                    debt[dest] += n / float(detailed)
                for j in range(whole):
                    dest = min(debt, key=lambda d: (-debt[d], d))
                    debt[dest] -= 1
                    phase = ((core * 17 + seed) % 61) / 61.0
                    self.schedule(self.now + epoch * (j + phase) / max(1, whole), inject, core, dest)
            self.schedule(self.now + epoch, boundary)
        def inject(core, dest):
            if self.background_stopped:
                return
            self.background_serial += 1
            # Separate namespace; explicit destinations preserve measured histogram.
            self.request(core, (1 << 80) + self.background_serial * 64, dest[0],
                         background=True, destination=dest[1:])
        def boundary():
            offered = self.offers.copy()
            self.offers.clear()
            begin(offered)
        self.offers.clear()
        begin(warmup_offers)

    def describe(self):
        return dict(controllers=self.controllers, source_counts=dict(self.sources),
                    directory_slices=self.ntd, channels=self.nch,
                    ring_links=[dict(fabric=k[0], stop=k[1], direction=k[2], **v)
                                for k, v in sorted(self.link_stats.items())],
                    events_processed=self.event_count, epochs=self.epoch_history,
                    background_drain_cycles=self.now)


class TileMemory(MemoryModel):
    """Existing private cache/DTLB/prefetch policy with completion handles."""
    def __init__(self, scenario, profile, assume, fabric, core):
        # Suppress the old independent completion throttle and its assumption.
        sc = copy.deepcopy(scenario)
        sc["memory"]["memory_service"] = "unlimited"
        super().__init__(sc, profile, lambda s: assume(s) if "no coherence" not in s else None)
        if self.type != "line_tracking":
            raise Unsupported("unit/ring memory accesses need line_tracking (fixed L1 is supported for register-only streams)")
        if self.sc["cold_level"] != "memory":
            raise Unsupported("unit/ring cold lines must start in memory; use warm ranges for resident L2")
        self.fabric, self.core = fabric, core
        self.pending = {}
        self.waiting = []
        self.fabric.backends[core] = self
        for cache_set in self.l2.data.values():
            for address in cache_set:
                td = fabric.directory(address)
                state = fabric.lines[td].setdefault(address, dict(owner=None, sharers=set(), pending=deque(), busy=False))
                state["sharers"].add(core)

    def can_take_fill(self, now, n):
        self.waiting = [h for h in self.waiting if not h.done]
        return len(self.waiting) + n <= self.max_outstanding

    def plan_demand(self, lines, now, vector, is_store, ngo=False):
        fills = sum(self.l1.lookup(la, False) is None and la not in self.pending for la in lines)
        worst = "memory" if any(self.l2.lookup(la, False) is None for la in lines) else "l2"
        if all(self.l1.lookup(la, False) is not None for la in lines):
            worst = "l1"
        return now, worst, fills, any(la in self.pending for la in lines)

    def _install(self, la, l1=True):
        victim = self.l2.insert(la, self.fabric.now)
        if victim is not None:
            self.l1.remove(victim)
            self.fabric.evict(self.core, victim)
        if l1:
            self.l1.insert(la, self.fabric.now)

    def _fetch(self, la, operation, l1=True):
        if la in self.pending and operation == "read":
            h = self.pending[la]
            if l1:
                h.then(lambda _: self._install(la))
            return h
        h = self.fabric.request(self.core, la, operation)
        self.pending[la] = h
        def filled(_):
            self._install(la, l1)
            if self.pending.get(la) is h:
                del self.pending[la]
        h.then(filled)
        return h

    def demand(self, ev, now, vector, is_store):
        lines = ev.lines
        ngo = ev.insn.op.startswith("vmovnr")
        if ngo and (ev.nbytes != 64 or len(lines) != 1 or ev.addr % 64 or ev.insn.mask is not None):
            raise Unsupported("no-read requires one proven full unmasked aligned line")
        _, worst, _, waits = self.plan_demand(lines, now, vector, is_store, ngo)
        self.stats["accesses"] += 1
        self.stats[{"l1": "l1_hits", "l2": "l2_hits", "memory": "memory"}[worst]] += 1
        self.stats["inflight_waits"] += int(waits)
        tlb = self._tlb_cost(lines)
        handles = []
        for la in lines:
            h = Transaction(issued_cycle=now)
            state = self.fabric.lines[self.fabric.directory(la)].get(la, {})
            local = self.l1.lookup(la) is not None
            owned = state.get("owner") == self.core
            if local and (not is_store or owned) and not ngo:
                if is_store:
                    self.line_store_ready[la] = now + self.p.get("latency.store_to_load_same_line")
                delay = 0 if is_store else self.latency("l1", vector)
                self.fabric.schedule(now + delay + tlb, h.finish, now + delay + tlb)
            elif not is_store and self.l2.lookup(la) is not None:
                ready = now + self.latency("l2", vector) + tlb
                def local_fill(target=h, address=la, at=ready):
                    self._install(address)
                    target.finish(at)
                self.fabric.schedule(ready, local_fill)
            else:
                op = "no_read" if ngo else "write" if is_store else "read"
                fetch = self._fetch(la, op, not ngo)
                extra = max(0, self.latency("l1", vector) - self.p.get("latency.scalar_load_l1")) if not is_store else 0
                def arrived(_, target=h, delay=tlb + extra):
                    at = self.fabric.now + delay
                    self.fabric.schedule(at, target.finish, at)
                fetch.then(arrived)
                self.waiting.append(h)
            handles.append(h)
            if not is_store or self.p.get("l2.hw_prefetch_trains_on_stores"):
                self._hwp_observe(la, now)
        joined = Transaction(issued_cycle=now, level=worst)
        def completed(_):
            if not joined.done and all(h.done for h in handles):
                joined.finish(max(h.info["completed_cycle"] for h in handles))
        for h in handles:
            h.then(completed)
        return joined, worst

    def _hwp_issue(self, page, line_in_page, stride, now):
        for k in range(1, self.hwp_depth + 1):
            nxt = line_in_page + k * stride
            if not 0 <= nxt < 64:
                break
            la = page * 4096 + nxt * 64
            if self.l2.lookup(la, False) is None and la not in self.pending:
                self._fetch(la, "read", False)
                self.stats["hw_prefetches"] += 1

    def prefetch(self, la, level, now):
        self.stats["prefetches"] += 1
        if self.l1.lookup(la, False) is not None or (level == "l2" and self.l2.lookup(la, False) is not None):
            self.stats["prefetches_useless"] += 1
            return False
        self.waiting.append(self._fetch(la, "read", level == "l1"))
        return True


class Tile(CoreSim):
    """Core issue selection is inherited; only off-core readiness is asynchronous."""
    def __init__(self, kernel, profile, traces, fabric, core, **kw):
        super().__init__(kernel, profile, traces, **kw)
        self.fabric, self.core = fabric, core
        self.pending_regs, self.pending_deps, self.pending_stalls = {}, {}, {}
        has_memory = any(ev.lines for c in self.ctx for ev in c.events)
        if has_memory:
            self.assumptions = [s for s in self.assumptions if "no coherence" not in s and "card-level sharing not modeled" not in s]
            self.mem = TileMemory(kernel.scenario, profile, self.assume, fabric, core)
        for c in self.ctx:
            for ev in c.events:
                if ev.stub or ev.insn.cls in ("locked_rmw", "fence", "vector_scatter"):
                    raise Unsupported("unit/ring does not simulate stubs, atomics, fences or scatter")

    def _blockers(self, cs, ev, now, l1_used, paired_with=None):
        pending = self.pending_stalls.get(cs.ctx)
        if pending is not None and not pending.done:
            return "miss_stall"
        for r in _reads(ev.insn, ev) | ev.insn.addr_regs:
            h = self.pending_regs.get((cs.ctx, r))
            if h is not None and not h.done:
                return "dependency"
        for dep in ev.insn.explicit_deps:
            h = self.pending_deps.get((cs.ctx, dep))
            if h is not None and not h.done:
                return "explicit_dep"
        if ev.insn.flags_r:
            h = self.pending_regs.get((cs.ctx, "flags"))
            if h is not None and not h.done:
                return "flags"
        return super()._blockers(cs, ev, now, l1_used, paired_with)

    def _retire(self, cs, ev, now, pipe):
        insn = ev.insn
        if not ev.lines or insn.cls in ("prefetch_l1", "prefetch_l2"):
            # A younger independent register write supersedes a pending load.
            for r in _writes(insn, ev):
                self.pending_regs.pop((cs.ctx, r), None)
            return super()._retire(cs, ev, now, pipe)
        if not (insn.is_load or insn.is_store or insn.folded_load):
            raise Unsupported("unit/ring unsupported memory instruction %s" % insn.op)
        cs.issued += 1
        cs.last_issue_cycle = now
        if cs.first_issue is None:
            cs.first_issue = now
        handle, level = self.mem.demand(ev, now, _vector_access(insn), insn.is_store)
        result = Transaction(issued_cycle=now)
        writes = _writes(insn, ev)
        for r in writes:
            self.pending_regs[(cs.ctx, r)] = result
            cs.reg_written_at[r] = now
        if insn.flags_w:
            self.pending_regs[(cs.ctx, "flags")] = result
        self.pending_deps[(cs.ctx, insn.id)] = result
        should_stall = (level != "l1" and (self.miss_stalls if not insn.is_store else self._param("l1.store_miss_stalls_context")))
        if insn.cls in ("x87_load", "x87_add", "x87_mul", "x87_div", "x87_sqrt"):
            should_stall = bool(self._param("x87.mem_operand_serializes")) or should_stall
        if insn.op.startswith("vmovnr"):
            should_stall = True
            self.nr_store_free_at = now + self._param("store.nr_occupancy_core_cycles")
        if should_stall:
            self.pending_stalls[cs.ctx] = result
        if insn.is_store:
            cs.last_store_issue = now
        log = dict(cycle=now, ctx=cs.ctx, id=insn.id, op=insn.op, pipe=pipe, done=None, level=level)
        if self.record_issue and len(self.issue_log) < 20000:
            self.issue_log.append(log)
        def ready(h):
            at = h.info["completed_cycle"]
            if insn.folded_load:
                at = max(now + self.latency_of(insn, ev), at - self.mem.latency("l1", True) + self.latency_of(insn, ev))
            elif insn.cls == "scalar_rmw":
                at += self._param("latency.scalar_alu")
            elif insn.cls == "x87_load":
                at = max(now, at - self.mem.latency("l1", False)) + self._param("latency.x87_load")
            elif insn.cls.startswith("x87_"):
                at = max(now, at - self.mem.latency("l1", False)) + self._param("latency.x87_mem_operand_load") + self.latency_of(insn, ev)
            elif insn.cls == "vector_gather":
                at += max(0, self._param("latency.gather_first_line") - self.mem.latency("l1", True))
            elif not insn.is_store:
                at += self._extend_extra(insn)
            if insn.op.startswith("vmovnr"):
                at = max(at, now + self._param("store.nr_stall_cycles_resident" if level in ("l1", "l2") else "store.nr_stall_cycles_memory"))
            def finish():
                for r in writes:
                    if self.pending_regs.get((cs.ctx, r)) is result:
                        cs.reg_ready[r] = at
                        del self.pending_regs[(cs.ctx, r)]
                if self.pending_regs.get((cs.ctx, "flags")) is result:
                    cs.flags_ready = at
                    del self.pending_regs[(cs.ctx, "flags")]
                cs.last_done[insn.id] = at
                cs.max_done = max(cs.max_done, at)
                log["done"] = at
                result.finish(at)
            self.fabric.schedule(at, finish)
        handle.then(ready)
        return None


def simulate(kernel, profile, traces, scale, max_cycles, deadline, record_issue=True):
    cores = sorted({s.core for s in kernel.streams})
    if not 1 <= len(cores) <= 8:
        raise InvalidInput("unit/ring needs 1..8 detailed cores")
    sc = copy.deepcopy(kernel.scenario.get("multicore", {}))
    allowed = {"placement", "channel_interleave", "td_interleave", "td_positions", "controller_positions", "background", "max_events", "max_pending"}
    if set(sc) - allowed:
        raise InvalidInput("unknown multicore scenario keys %s" % sorted(set(sc) - allowed))
    placement = sc.get("placement", {str(c): i * profile.get("ring.positions") // len(cores) for i, c in enumerate(cores)})
    try:
        placement = {int(k): v for k, v in placement.items()}
    except (ValueError, AttributeError):
        raise InvalidInput("placement must map core IDs to stops")
    if set(placement) != set(cores):
        raise InvalidInput("placement must name every detailed core exactly once")
    bg = sc.setdefault("background", {})
    enabled = bg.setdefault("enabled", scale == "ring")
    active = bg.setdefault("active_cores", profile.get("card.usable_cores"))
    epoch = bg.setdefault("epoch_cycles", profile.get("multicore.background_epoch_cycles"))
    seed = bg.setdefault("seed", profile.get("multicore.background_seed"))
    sc["placement"] = {str(k): v for k, v in placement.items()}
    kernel.scenario["multicore"] = sc
    def make():
        fabric = Fabric(profile, placement, background=enabled, scenario=sc,
                        max_events=sc.get("max_events", 2000000), max_pending=sc.get("max_pending", 200000),
                        max_cycles=max_cycles, deadline=deadline)
        tiles = [Tile(kernel, profile, {s.context: traces[s.context] for s in kernel.streams if s.core == c},
                      fabric, c, max_cycles=max_cycles, deadline=deadline, record_issue=record_issue) for c in cores]
        return fabric, tiles
    warmup_offers = Counter()
    warmup_cycles = 0
    if enabled and any(ev.lines for events in traces.values() for ev in events):
        warm, warmtiles = make()
        # One complete epoch of the same cold detailed workload, no synthetic
        # traffic, excluded from results; cache state resets before measurement.
        for cycle in range(epoch):
            warm.advance(cycle)
            for tile in warmtiles:
                tile.cycle = cycle
                if not all(c.done for c in tile.ctx):
                    tile.step()
            warm.advance(cycle)
        warmup_offers = warm.offers.copy()
        warmup_cycles = epoch
    fabric, tiles = make()
    if enabled:
        fabric.start_background(len(tiles), active, epoch, seed, warmup_offers)
    start = time.time()
    cycle = 0
    while not all(c.done for tile in tiles for c in tile.ctx):
        if max_cycles is not None and cycle > max_cycles:
            raise BudgetExhausted("multicore cycle budget exhausted", partial=fabric.partial())
        if deadline is not None and cycle % 1024 == 0 and time.time() > deadline:
            raise BudgetExhausted("multicore wall-time budget exhausted", partial=fabric.partial())
        fabric.advance(cycle)
        for tile in tiles:
            tile.cycle = cycle
            if not all(c.done for c in tile.ctx):
                tile.step()
        fabric.advance(cycle)
        cycle += 1
    fabric.background_stopped = True
    last_issue = cycle
    fabric.drain()
    fabric.flush()
    fabric.drain()
    rows = []
    for tile in tiles:
        end = max((c.last_issue_cycle or 0) for c in tile.ctx) + 1
        completion = max(end, max(c.max_done for c in tile.ctx), fabric.completed_by_core[tile.core])
        tile.python_seconds = time.time() - start
        row = tile._result(end, completion, sum(len(c.events) for c in tile.ctx))
        row.update(core=tile.core, predicted_cycles=completion, placement=placement[tile.core])
        rows.append(row)
    envelope = max(max(r["completion_cycles"] for r in rows), fabric.now if any(ev.lines for ts in traces.values() for ev in ts) else 0)
    useful = sum(ev.nbytes for ts in traces.values() for ev in ts if ev.insn.cls not in ("prefetch_l1", "prefetch_l2"))
    pred = dict(predicted_cycles=envelope, predicted_cycles_per_unit=envelope / kernel.unit_count,
                issue_span_cycles=last_issue, unit_count=kernel.unit_count, unit_of_work=kernel.unit_of_work.get("description"),
                dynamic_instructions=sum(r["dynamic_instructions"] for r in rows),
                issue_events=sum(r["issue_events"] for r in rows), cores=rows, memory=fabric.describe(),
                result_class=dict(class_="unvalidated_scenario_estimate"),
                detailed_useful_bytes=useful, detailed_bytes_per_cycle=useful / max(1, envelope),
                background=dict(enabled=enabled, cores=active-len(tiles) if enabled else 0,
                                warmup_cycles=warmup_cycles, stop_cycle=last_issue, drain_cycle=fabric.now,
                                approximation="previous-epoch offered traffic; cold one-epoch warmup resets caches; phase/epoch sensitivity pending"))
    pred["result_class"] = {"class": "unvalidated_scenario_estimate", "reasons": ["multi-core scaling and full-card held-out validation pending"]}
    if enabled:
        pred["symmetry_full_card_bytes_per_cycle"] = useful / max(1, envelope) * active / len(tiles)
    assumptions = ["61 contracted ring positions and assumed TD/channel maps; virtual addresses are physical surrogates",
                   "separate pipelined address/data/ack link queues (or explicit shared-fabric overlay); R01 pp.13,19,22 verified early guide, production stepping unspecified",
                   "private inclusive LRU caches; reduced owner/sharer protocol; compatible pending reads share a fill and forward its data",
                   "memory delay decomposed once; channel interval derived from sustained read calibration; banks/refresh/turnaround not simulated",
                   "background is synthetic prior-epoch traffic with excluded cold warmup, not additional executed work; symmetry stability and epoch sensitivity unvalidated"]
    for tile in tiles:
        assumptions.extend(s for s in tile.assumptions if s not in assumptions)
    return pred, assumptions, time.time() - start, [dict(e, core=t.core) for t in tiles for e in t.issue_log]
