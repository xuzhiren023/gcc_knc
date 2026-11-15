"""Memory scenarios for the timing engine.

fixed_level    every access is served from one level; prefetches have no effect.
classified     address ranges name the level; prefetches have no effect.
line_tracking  set-associative LRU L1 and inclusive L2 with per-line arrival times;
               first touch of a cold line costs the cold level; software prefetches
               install lines ahead of time; demand accesses to an in-flight line wait
               for its arrival. The L2 hardware prefetcher is NOT modeled.
"""
from collections import OrderedDict

from .errors import Unsupported

LINE = 64
LEVEL_ORDER = {"l1": 0, "l2": 1, "memory": 2}


class SetAssoc(object):
    def __init__(self, size, ways, line=LINE):
        self.sets = size // (ways * line)
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


class MemoryModel(object):
    def __init__(self, scenario, profile, assume):
        self.sc = scenario["memory"]
        self.type = self.sc["type"]
        self.p = profile
        self.assume = assume
        self.inflight = []  # arrival cycles of outstanding fills (demand or prefetch)
        self.max_outstanding = profile.get("l1.outstanding_demand_misses_per_core")
        self.line_store_ready = {}
        self.stats = {"accesses": 0, "l1_hits": 0, "l2_hits": 0, "memory": 0, "inflight_waits": 0, "prefetches": 0,
                      "prefetches_useless": 0, "outstanding_limit_stalls": 0, "store_misses": 0}
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
            assume("line_tracking: true LRU replacement stands in for the hardware's pseudo-LRU; the L2 hardware prefetcher is not modeled; the L1 and L2 are modeled as private to the core with no coherence traffic")
        else:
            assume("%s memory scenario: access levels are asserted by the scenario, so software prefetches change no access level and only cost issue slots" % self.type)

    # -- latencies --------------------------------------------------------------------------
    def latency(self, level, vector):
        if level == "l1":
            return self.p.get("latency.vector_load_l1") if vector else self.p.get("latency.scalar_load_l1")
        base = self.p.get("latency.l2_hit") if level == "l2" else self.p.get("latency.memory")
        extra = 0
        if vector:
            extra = max(0, self.p.get("latency.vector_load_l1") - self.p.get("latency.scalar_load_l1"))
            if extra:
                self.assume("vector load-to-use beyond L1 = level latency + (vector_load_l1 - scalar_load_l1); the extra vector path cost is assumed additive")
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
                if arr2 > now:
                    waits = True
                    base = arr2
                else:
                    base = now
                ready = max(ready, base + (0 if is_store else self.latency("l2", vector)))
            else:
                lvl = self.sc["cold_level"]
                ready = max(ready, now + (0 if is_store else self.latency(lvl, vector)))
            if LEVEL_ORDER[lvl] > LEVEL_ORDER[worst]:
                worst = lvl
            if not ngo:
                new_fills += 1
        return ready, worst, new_fills, waits

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
        if self.type == "line_tracking":
            for la in lines:
                if ngo and self.l1.lookup(la, touch=False) is None:
                    continue  # no-read store: no fill
                arr1 = self.l1.lookup(la)
                if arr1 is None:
                    arr2 = self.l2.lookup(la)
                    lvl = "l2" if arr2 is not None else self.sc["cold_level"]
                    if arr2 is not None:
                        arrival = (arr2 if arr2 > now else now) + self.p.get("latency.l2_hit")
                    else:
                        arrival = now + self.p.get("latency.memory")
                    self.l1.insert(la, arrival)
                    if arr2 is None:
                        self.l2.insert(la, arrival)
                    self.inflight.append(arrival)
                else:
                    self.l2.lookup(la)  # keep L2 LRU in step
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
        if self.l1.lookup(la, touch=False) is not None:
            self.stats["prefetches_useless"] += 1
            return False
        arr2 = self.l2.lookup(la, touch=False)
        if level == "l2":
            if arr2 is not None:
                self.stats["prefetches_useless"] += 1
                return False
            arrival = now + self.p.get("latency.memory")
            self.l2.insert(la, arrival)
            self.inflight.append(arrival)
            return True
        # level l1: bring to L1 (and L2)
        if arr2 is not None:
            arrival = (arr2 if arr2 > now else now) + self.p.get("latency.l2_hit")
        else:
            arrival = now + self.p.get("latency.memory")
            self.l2.insert(la, arrival)
        self.l1.insert(la, arrival)
        self.inflight.append(arrival)
        return True

    def describe(self):
        d = {"type": self.type, "stats": dict(self.stats)}
        if self.type == "line_tracking":
            d["cold_level"] = self.sc["cold_level"]
            d["warm_ranges"] = len(self.sc.get("warm", []))
        elif self.type == "fixed_level":
            d["level"] = self.sc["level"]
        else:
            d["default"] = self.sc["default"]
            d["ranges"] = len(self.sc.get("ranges", []))
        return d
