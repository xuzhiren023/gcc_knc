"""Memory scenarios for the timing engine.

fixed_level    every access is served from one level; prefetches have no effect.
classified     address ranges name the level; prefetches have no effect.
line_tracking  set-associative LRU L1 and inclusive L2 with per-line arrival times;
               first touch of a cold line costs the cold level; software prefetches
               install lines ahead of time; demand accesses to an in-flight line wait
               for its arrival. Optional explicit sub-models, each off by default:
                 tlb: "modeled"                 LRU first-level DTLB; a miss adds tlb.l1_miss_penalty_cycles
                 hardware_prefetcher: "modeled" streaming L2 prefetcher: stream per page, strides of
                                                1-2 lines, depth l2.hw_prefetch_depth_lines, page bounded
                 memory_service: "modeled"      one memory fill completes per memory.core_service_cycles_per_line
               Every one of these turns the result into an unvalidated scenario estimate
               unless a held-out validation case covers the kernel's declared shape.
"""
from collections import OrderedDict

from .errors import Unsupported

LINE = 64
LEVEL_ORDER = {"l1": 0, "l2": 1, "memory": 2}


class SetAssoc(object):
    def __init__(self, size, ways, line=LINE):
        self.sets = max(1, size // (ways * line))
        self.ways = ways
        self.line = line
        self.data = {}  # set index -> OrderedDict(line_addr -> arrival_cycle)

    def _set(self, la):
        return (la // self.line) % self.sets

    def lookup(self, la, touch=True):
        s = self.data.get(self._set(la))
        if s is None or la not in s:
            return None
        arr = s[la]
        if touch:
            s.move_to_end(la)
        return arr

    def insert(self, la, arrival):
        idx = self._set(la)
        s = self.data.setdefault(idx, OrderedDict())
        if la in s:
            s[la] = min(s[la], arrival)
            s.move_to_end(la)
            return None
        victim = None
        if len(s) >= self.ways:
            victim, _ = s.popitem(last=False)
        s[la] = arrival
        return victim

    def remove(self, la):
        s = self.data.get(self._set(la))
        if s is not None and la in s:
            del s[la]


class LRU(object):
    """Fully associative LRU set of keys."""

    def __init__(self, entries):
        self.entries = entries
        self.d = OrderedDict()

    def touch(self, key):
        """True on hit."""
        if key in self.d:
            self.d.move_to_end(key)
            return True
        self.d[key] = True
        if len(self.d) > self.entries:
            self.d.popitem(last=False)
        return False


class MemoryModel(object):
    def __init__(self, scenario, profile, assume):
        self.sc = scenario["memory"]
        self.type = self.sc["type"]
        self.p = profile
        self.assume = assume
        self.inflight = []  # arrival cycles of outstanding demand fills and software prefetches
        self.max_outstanding = profile.get("l1.outstanding_demand_misses_per_core")
        self.line_store_ready = {}
        self.stats = {"accesses": 0, "l1_hits": 0, "l2_hits": 0, "memory": 0, "inflight_waits": 0, "prefetches": 0,
                      "prefetches_useless": 0, "outstanding_limit_stalls": 0, "store_misses": 0, "tlb_misses": 0,
                      "hw_prefetches": 0, "hw_prefetch_hits": 0, "memory_service_waits": 0}
        self.submodels = []
        self.tlb = None
        self.hwp = None
        self.service = None
        if self.type == "line_tracking":
            self.l1 = SetAssoc(profile.get("l1.size_bytes"), profile.get("l1.ways"))
            self.l2 = SetAssoc(profile.get("l2.size_bytes"), profile.get("l2.ways"))
            for rng in self.sc.get("warm", []):
                la = rng["start"] & ~(LINE - 1)
                while la < rng["end"]:
                    if rng["level"] == "l1":
                        self.l1.insert(la, -1)
                        self.l2.insert(la, -1)
                    elif rng["level"] == "l2":
                        self.l2.insert(la, -1)
                    la += LINE
            assume("line_tracking: true LRU replacement stands in for the hardware's pseudo-LRU; the L1 and L2 are modeled as private to the core with no coherence traffic")
            def want(key, *params):
                v = self.sc.get(key, "auto")
                if v == "auto":
                    return all(profile.has(p) for p in params)
                return v == "modeled"
            if want("tlb", "tlb.l1_entries_4k", "tlb.l1_miss_penalty_cycles"):
                self.page = self.sc.get("page_bytes", 4096)
                entries = profile.get("tlb.l1_entries_4k") if self.page == 4096 else profile.get("tlb.l1_entries_2m")
                self.tlb = LRU(entries)
                self.tlb_penalty = profile.get("tlb.l1_miss_penalty_cycles")
                # warm ranges are resident data: their pages are in the TLB too (up to its capacity)
                for rng in self.sc.get("warm", []):
                    for pg in range(rng["start"] // self.page, (rng["end"] - 1) // self.page + 1):
                        self.tlb.touch(pg)
                self.submodels.append("tlb")
                assume("TLB sub-model: %d-entry fully associative LRU first-level DTLB for %d-byte pages; a miss adds %d cycles; second-level TLB reach and page walks are not modeled" % (entries, self.page, self.tlb_penalty))
            else:
                assume("TLB not modeled: every access is assumed to hit the first-level DTLB")
            if want("hardware_prefetcher", "l2.hw_prefetch_streams", "l2.hw_prefetch_depth_lines", "l2.hw_prefetch_max_stride_lines", "latency.memory"):
                self.hwp_streams = LRU(profile.get("l2.hw_prefetch_streams"))
                self.hwp_depth = profile.get("l2.hw_prefetch_depth_lines")
                self.hwp_max_stride = profile.get("l2.hw_prefetch_max_stride_lines")
                self.hwp_state = {}  # page -> (last_line, stride_lines)
                self.hwp = True
                self.submodels.append("hardware_prefetcher")
                assume("L2 hardware prefetcher sub-model: a stream per 4 KiB page after two accesses with the same stride (<= %d lines), prefetching %d lines ahead within the page into L2; prefetched fills do not use L1 demand-miss slots (assumed)" % (self.hwp_max_stride, self.hwp_depth))
            else:
                assume("L2 hardware prefetcher not modeled")
            if want("memory_service", "memory.core_service_cycles_per_line"):
                self.service = profile.get("memory.core_service_cycles_per_line")
                self.channel_free = 0
                self.submodels.append("memory_service")
                assume("memory service sub-model: one memory fill per %d core cycles for this core (measured sequential-stream rate, includes the hardware prefetcher); card-level sharing not modeled" % self.service)
        else:
            assume("%s memory scenario: access levels are asserted by the scenario, so software prefetches change no access level and only cost issue slots" % self.type)

    # -- latencies --------------------------------------------------------------------------
    def latency(self, level, vector):
        """vector: False (scalar), True (plain vector load) or "merge" (masked/converting/unpack form)."""
        if vector == "merge":
            l1 = self.p.get("latency.vector_load_merge_l1")
        elif vector:
            l1 = self.p.get("latency.vector_load_l1")
        else:
            l1 = self.p.get("latency.scalar_load_l1")
        if level == "l1":
            return l1
        base = self.p.get("latency.l2_hit") if level == "l2" else self.p.get("latency.memory")
        extra = max(0, l1 - self.p.get("latency.scalar_load_l1"))
        if extra:
            self.assume("load-to-use beyond L1 = level latency + (L1 form latency - scalar L1 latency); the extra form cost is assumed additive")
        return base + extra

    def _level_rule(self, la):
        if self.type == "fixed_level":
            return self.sc["level"]
        for rng in self.sc.get("ranges", []):
            if rng["start"] <= la < rng["end"]:
                return rng["level"]
        return self.sc["default"]

    def _reap(self, now):
        self.inflight = [t for t in self.inflight if t > now]

    def can_take_fill(self, now, n):
        self._reap(now)
        return len(self.inflight) + n <= self.max_outstanding

    def _cold_arrival(self, now, extra_latency=0):
        """Arrival of a line that is in no modeled cache: from the scenario's cold level (L2 hit latency, or a memory fill)."""
        if self.type == "line_tracking" and self.sc.get("cold_level") == "l2":
            self.stats["cold_l2_fills"] = self.stats.get("cold_l2_fills", 0) + 1
            return now + self.p.get("latency.l2_hit") + extra_latency
        return self._memory_arrival(now, extra_latency)

    def _memory_arrival(self, now, extra_latency=0):
        """Arrival time of a memory fill issued now, under the optional service model."""
        lat = self.p.get("latency.memory") + extra_latency
        if self.service is None:
            return now + lat
        start = max(now, self.channel_free)
        if start > now:
            self.stats["memory_service_waits"] += 1
        self.channel_free = start + self.service
        return start + lat

    # -- demand access ------------------------------------------------------------------------
    def plan_demand(self, lines, now, vector, is_store, ngo=False):
        """Without changing state: returns (ready_cycle, worst_level, new_fills, waits_on_inflight)."""
        ready = now
        worst = "l1"
        new_fills = 0
        waits = False
        for la in lines:
            if self.type != "line_tracking":
                lvl = self._level_rule(la)
                if not is_store:
                    ready = max(ready, now + self.latency(lvl, vector))
                if lvl != "l1" and not ngo:
                    new_fills += 1
                if LEVEL_ORDER[lvl] > LEVEL_ORDER[worst]:
                    worst = lvl
                continue
            arr = self.l1.lookup(la, touch=False)
            if arr is not None:
                if arr > now:
                    waits = True
                    ready = max(ready, arr + (0 if is_store else self.latency("l1", vector)))
                else:
                    ready = max(ready, now + (0 if is_store else self.latency("l1", vector)))
                continue
            arr2 = self.l2.lookup(la, touch=False)
            if arr2 is not None:
                lvl = "l2"
                base = arr2 if arr2 > now else now
                if arr2 > now:
                    waits = True
                ready = max(ready, base + (0 if is_store else self.latency("l2", vector)))
            else:
                lvl = self.sc["cold_level"]
                ready = max(ready, now + (0 if is_store else self.latency(lvl, vector)))
            if LEVEL_ORDER[lvl] > LEVEL_ORDER[worst]:
                worst = lvl
            if not ngo:
                new_fills += 1
        return ready, worst, new_fills, waits

    def _tlb_cost(self, lines):
        if self.tlb is None:
            return 0
        cost = 0
        for pg in sorted(set(la // self.page for la in lines)):
            if not self.tlb.touch(pg):
                self.stats["tlb_misses"] += 1
                cost += self.tlb_penalty
        return cost

    def _hwp_observe(self, la, now):
        """Train the hardware prefetcher on a demand line and issue its prefetches."""
        if not self.hwp:
            return
        page = la // 4096
        st = self.hwp_state.get(page)
        line_in_page = (la % 4096) // LINE
        if st is None:
            self.hwp_streams.touch(page)
            self.hwp_state[page] = (line_in_page, None)
            return
        last, stride = st
        delta = line_in_page - last
        if delta == 0:
            return
        if stride is None:
            if abs(delta) <= self.hwp_max_stride:
                self.hwp_state[page] = (line_in_page, delta)
                self._hwp_issue(page, line_in_page, delta, now)
            else:
                self.hwp_state[page] = (line_in_page, None)
            return
        if delta == stride:
            self.hwp_state[page] = (line_in_page, stride)
            self._hwp_issue(page, line_in_page, stride, now)
        else:
            self.hwp_state[page] = (line_in_page, None)

    def _hwp_issue(self, page, line_in_page, stride, now):
        for k in range(1, self.hwp_depth + 1):
            nxt = line_in_page + k * stride
            if nxt < 0 or nxt >= 4096 // LINE:
                break
            la = page * 4096 + nxt * LINE
            if self.l2.lookup(la, touch=False) is not None or self.l1.lookup(la, touch=False) is not None:
                continue
            arrival = self._memory_arrival(now)
            self.l2.insert(la, arrival)
            self.stats["hw_prefetches"] += 1

    def commit_demand(self, lines, now, vector, is_store, ngo=False):
        ready, worst, new_fills, waits = self.plan_demand(lines, now, vector, is_store, ngo)
        self.stats["accesses"] += 1
        if worst == "l1":
            self.stats["l1_hits"] += 1
        elif worst == "l2":
            self.stats["l2_hits"] += 1
        else:
            self.stats["memory"] += 1
        if waits:
            self.stats["inflight_waits"] += 1
        if is_store and worst != "l1":
            self.stats["store_misses"] += 1
        tlb = self._tlb_cost(lines)
        if self.type == "line_tracking":
            for la in lines:
                if ngo and self.l1.lookup(la, touch=False) is None:
                    # no-read store: no L1 fill; a non-resident line is left in L2 after the write (assumed: the store
                    # path writes through the L2, which is what makes later NR stores to a small footprint cheap)
                    if self.l2.lookup(la) is None:
                        self.l2.insert(la, now + self.p.get("store.nr_stall_cycles_memory"))
                    continue
                arr1 = self.l1.lookup(la)
                if arr1 is None:
                    arr2 = self.l2.lookup(la)
                    if arr2 is not None:
                        if arr2 > now:
                            self.stats["hw_prefetch_hits"] += 0  # in-flight line (software or hardware prefetch)
                        arrival = (arr2 if arr2 > now else now) + self.p.get("latency.l2_hit") + tlb
                    else:
                        arrival = self._cold_arrival(now, tlb)
                        self.l2.insert(la, arrival)
                    self.l1.insert(la, arrival)
                    self.inflight.append(arrival)
                    if arrival > ready:
                        ready = arrival if is_store else arrival + (self.latency("l1", vector) if False else 0)
                else:
                    self.l2.lookup(la)  # keep L2 LRU in step
                if not is_store or self.p.get("l2.hw_prefetch_trains_on_stores"):
                    self._hwp_observe(la, now)
            if tlb and worst == "l1":
                ready += tlb
        else:
            for _ in range(new_fills):
                self.inflight.append(ready)
        return ready, worst

    # -- software prefetch ----------------------------------------------------------------------
    def prefetch(self, la, level, now):
        self.stats["prefetches"] += 1
        if self.type != "line_tracking":
            self.stats["prefetches_useless"] += 1
            return False
        tlb = self._tlb_cost([la])
        if self.l1.lookup(la, touch=False) is not None:
            self.stats["prefetches_useless"] += 1
            return False
        arr2 = self.l2.lookup(la, touch=False)
        if level == "l2":
            if arr2 is not None:
                self.stats["prefetches_useless"] += 1
                return False
            arrival = self._cold_arrival(now, tlb)
            self.l2.insert(la, arrival)
            self.inflight.append(arrival)
            return True
        if arr2 is not None:
            arrival = (arr2 if arr2 > now else now) + self.p.get("latency.l2_hit") + tlb
        else:
            arrival = self._cold_arrival(now, tlb)
            self.l2.insert(la, arrival)
        self.l1.insert(la, arrival)
        self.inflight.append(arrival)
        return True

    def describe(self):
        d = {"type": self.type, "stats": dict(self.stats), "submodels": list(self.submodels)}
        if self.type == "line_tracking":
            d["cold_level"] = self.sc["cold_level"]
            d["warm_ranges"] = len(self.sc.get("warm", []))
        elif self.type == "fixed_level":
            d["level"] = self.sc["level"]
        else:
            d["default"] = self.sc["default"]
            d["ranges"] = len(self.sc.get("ranges", []))
        return d
