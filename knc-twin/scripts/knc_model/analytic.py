"""Pair and card scales: labeled analytical scenario models, never cycle simulations.

Both return an explicit needs_parameters result when a required parameter is unknown,
unless the caller supplies a sweep for it.
"""
from .errors import InvalidInput, MissingParameter, NeedsParameters
from .util import parse_int


def _num(params, key, what, required=True, default=None):
    if key not in params:
        if required:
            raise NeedsParameters("analytic parameter %r is required (%s)" % (key, what), {"parameter": key})
        return default
    v = params[key]
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise InvalidInput("analytic parameter %r must be a number" % key)
    return v


def pair_estimate(profile, params):
    """Two cores exchanging cache lines through their private L2s over the ring.

    T = max(core_a_cycles, core_b_cycles) + handoffs * remote_line_cycles
        + lines_exchanged * remote_line_cycles / concurrency
    """
    assumptions = [
        "pair scale is an analytical scenario, not a simulation: the two cores' instruction streams are summarized by their core-scale cycle counts",
        "each line crossing between the two cores costs the measured/literature remote-L2 line latency; ring bandwidth and contention from other cores are ignored",
        "a handoff (synchronization event) costs one remote line round trip; spinning and OS effects are ignored",
        "lines in flight overlap up to the given concurrency; no hardware limit on cross-core concurrency is modeled",
    ]
    a = _num(params, "core_a_cycles", "cycles of the producer core's work per unit")
    b = _num(params, "core_b_cycles", "cycles of the consumer core's work per unit")
    lines = _num(params, "lines_exchanged", "cache lines crossing between the cores per unit")
    handoffs = _num(params, "handoffs", "synchronization events per unit", required=False, default=0)
    clock = profile.get("card.clock_hz")
    remote_ns = profile.get("latency.remote_l2_line_ns")
    remote_cycles = remote_ns * clock / 1e9
    conc_values = params.get("concurrency_sweep")
    if conc_values is None:
        if "concurrency" in params:
            conc_values = [_num(params, "concurrency", "overlapping line transfers")]
        else:
            conc_values = [1, 2, 4, 8]
            assumptions.append("cross-core transfer concurrency is not a known parameter; results are a declared sweep over 1, 2, 4, 8 overlapping lines")
    scenarios = []
    for c in conc_values:
        if c <= 0:
            raise InvalidInput("concurrency must be positive")
        transfer = lines * remote_cycles / float(c)
        sync = handoffs * remote_cycles
        total = max(a, b) + transfer + sync
        scenarios.append({"concurrency": c, "compute_cycles": max(a, b), "transfer_cycles": round(transfer, 1), "sync_cycles": round(sync, 1),
                          "total_cycles": round(total, 1), "total_seconds": total / clock, "binding": "compute" if max(a, b) >= transfer + sync else "communication"})
    return {"kind": "pair_analytical_scenario", "scenarios": scenarios, "remote_line_cycles": round(remote_cycles, 1),
            "parameters_used": {"card.clock_hz": clock, "latency.remote_l2_line_ns": remote_ns}, "assumptions": assumptions}


def card_estimate(profile, params):
    """Whole-card scenario: compute term from per-core cycles, memory term from bytes and
    sustained bandwidth, plus barriers and an imbalance factor. The compute-only product
    (per-core throughput x cores) is reported but explicitly not used as the estimate."""
    assumptions = [
        "card scale is an analytical scenario, not a simulation: T = max(compute, memory) x imbalance + barriers",
        "compute term: per-core cycles per unit (from a core-scale result or given) x units / cores / clock; perfect static division of units over cores",
        "memory term: bytes per unit x units / sustained bandwidth of the named traffic type; bandwidth is treated as a flat ceiling independent of access pattern and core count",
        "barrier cost: measured or literature all-core barrier time per barrier; no other synchronization",
        "no modeling of ring contention, tag-directory placement, TLB, page size, frequency or thermal effects",
    ]
    units = _num(params, "units", "units of work")
    bytes_per_unit = _num(params, "bytes_per_unit", "bytes moved to or from memory per unit")
    traffic = params.get("traffic_type", "read_only")
    if traffic not in ("read_only", "read_modify_write", "write_normal", "write_ngo"):
        raise InvalidInput("traffic_type must be read_only, read_modify_write, write_normal or write_ngo")
    per_core = _num(params, "per_core_cycles_per_unit", "core-scale predicted cycles per unit (use a simulate result)")
    clock = profile.get("card.clock_hz")
    cores = params.get("cores")
    if cores is None:
        cores = profile.get("card.usable_cores")
        assumptions.append("cores = profile card.usable_cores (%d)" % cores)
    cores = int(cores)
    barriers = _num(params, "barriers", "all-core barriers", required=False, default=0)
    barrier_kind = params.get("barrier_kind", "tree")
    imbalance = _num(params, "imbalance_factor", "load imbalance multiplier", required=False, default=None)
    if imbalance is None:
        imbalance = 1.0
        assumptions.append("imbalance_factor not given: perfect load balance assumed (1.0)")
    bw_list = params.get("bandwidth_sweep_gbs")
    if bw_list is None:
        try:
            bw = profile.get_sub("card.sustained_bandwidth_gbs", traffic)
        except MissingParameter as e:
            alts = []
            p = profile.params.get("card.sustained_bandwidth_gbs")
            raise NeedsParameters(
                "sustained bandwidth for traffic type %r is unknown in profile %s; give bandwidth_sweep_gbs: [...] to run a declared sweep, or import a native measurement" % (traffic, profile.id),
                {"parameter": "card.sustained_bandwidth_gbs.%s" % traffic, "profile": profile.id, "known_values": p.value if p else None})
        bw_list = [bw]
    else:
        assumptions.append("memory bandwidth is a declared sweep given by the caller, not a profile value")
    barrier_s = 0.0
    if barriers:
        barrier_ns = profile.get_sub("card.barrier_ns", barrier_kind)
        barrier_s = barriers * barrier_ns * 1e-9
    compute_s = per_core * units / float(cores) / clock
    naive_s = compute_s
    scenarios = []
    for bw in bw_list:
        if bw <= 0:
            raise InvalidInput("bandwidth must be positive")
        mem_s = bytes_per_unit * units / (bw * 1e9)
        total = max(compute_s, mem_s) * imbalance + barrier_s
        scenarios.append({"bandwidth_gbs": bw, "compute_seconds": compute_s, "memory_seconds": mem_s, "barrier_seconds": barrier_s,
                          "imbalance_factor": imbalance, "total_seconds": total,
                          "binding": "memory" if mem_s > compute_s else "compute",
                          "achieved_bandwidth_gbs_if_total": (bytes_per_unit * units / total) / 1e9 if total > 0 else None})
    return {"kind": "card_analytical_scenario", "scenarios": scenarios,
            "not_an_estimate": {"single_core_throughput_times_cores_seconds": naive_s,
                                "note": "compute term alone; ignores memory, barriers and imbalance and is NOT the card estimate"},
            "parameters_used": {"card.clock_hz": clock, "cores": cores, "traffic_type": traffic, "barrier_kind": barrier_kind if barriers else None},
            "assumptions": assumptions}
