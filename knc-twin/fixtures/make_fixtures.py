#!/usr/bin/env python3
"""Regenerates the example kernels in this directory.

Expected outputs are derived here independently of the engine: integer arithmetic with
Python ints, exactly representable floating-point values (so no rounding question
arises), and hand-derived IEEE bit patterns for the floating-point edge cases, each with
a comment saying why the value is what it is. Nothing in this file imports knc_model.
"""
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = "knc-twin.kernel/1"


def f32(x):
    """bit pattern string of a Python float rounded to binary32 (used only for exactly representable values)."""
    b = struct.unpack("<I", struct.pack("<f", x))[0]
    assert struct.unpack("<f", struct.pack("<I", b))[0] == x, x
    return "0x%08x" % b


def write(name, obj):
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
        f.write("\n")
    print("wrote", path)


def mem(addr, base_mem, u32=None, f32s=None):
    pass


# ---------------------------------------------------------------------------------------------
# saxpy: y[i] = a*x[i] + y[i] over N floats, 16 per iteration. Integer-valued inputs keep every
# intermediate exact, so the expected output does not depend on FMA fusion or rounding.
def saxpy_records(prefetch=False, prefetch_distance=4):
    body = [
        {"id": "ldx", "op": "vmovaps", "ops": ["zmm0", {"base": "rax", "index": "rcx", "scale": 4}]},
        {"id": "ldy", "op": "vmovaps", "ops": ["zmm1", {"base": "rbx", "index": "rcx", "scale": 4}]},
    ]
    if prefetch:
        body += [
            {"id": "pfx", "op": "vprefetch0", "ops": [{"base": "rax", "index": "rcx", "scale": 4, "disp": 64 * prefetch_distance}]},
            {"id": "pfy", "op": "vprefetch0", "ops": [{"base": "rbx", "index": "rcx", "scale": 4, "disp": 64 * prefetch_distance}]},
        ]
    body += [
        {"id": "fma", "op": "vfmadd231ps", "ops": ["zmm1", "zmm2", "zmm0"], "comment": "zmm1 = zmm2*zmm0 + zmm1"},
        {"id": "sty", "op": "vmovaps", "ops": [{"base": "rbx", "index": "rcx", "scale": 4}, "zmm1"]},
        {"id": "adv", "op": "add", "ops": ["rcx", 16]},
        {"id": "cnt", "op": "dec", "ops": ["rdx"]},
        {"id": "br", "op": "jnz", "ops": ["L"]},
    ]
    body[0]["label"] = "L"
    return body


def saxpy_kernel(name, n, contexts=1, prefetch=False, scenario=None, wrong=False, description=""):
    a = 2.0
    streams = []
    expected_mem = []
    init_mem = []
    for c in range(contexts):
        xb = 0x1000000 + c * 0x400000   # 4 MiB per context, x and y 16 MiB apart: no overlap up to 1M floats
        yb = 0x2000000 + c * 0x400000
        xs = [float(i + 1) for i in range(n)]
        ys = [1.0] * n
        init_mem.append({"addr": "0x%x" % xb, "f32": xs})
        init_mem.append({"addr": "0x%x" % yb, "f32": ys})
        out = [a * x + y for x, y in zip(xs, ys)]
        if wrong:
            out[3] += 1.0  # deliberately wrong expected value
        expected_mem.append({"addr": "0x%x" % yb, "f32": out})
        streams.append({"context": c, "init": {"registers": {"rax": "0x%x" % xb, "rbx": "0x%x" % yb, "rcx": 0, "rdx": n // 16, "zmm2": {"f32_broadcast": a}}},
                        "instructions": saxpy_records(prefetch)})
    k = {"schema": SCHEMA, "name": name,
         "description": description or "y = a*x + y over %d floats per context, 16 lanes per iteration, %d context(s)%s. Inputs are small integers, so the result is exact under any rounding." % (n, contexts, " with vprefetch0 four lines ahead" if prefetch else ""),
         "unit_of_work": {"description": "16 floats of y = a*x + y (one loop iteration) per context", "count": (n // 16) * contexts},
         "numerical_policy": {"rounding": "rn", "ftz": False, "daz": False, "nan_compare": "any_nan"},
         "init": {"memory": init_mem},
         "streams": streams,
         "loop": {"label": "L", "trip_count": n // 16},
         "expected": {"memory": expected_mem}}
    if scenario:
        k["scenario"] = scenario
    return k


write("saxpy_loop.json", saxpy_kernel("saxpy_loop", 64))
write("saxpy_4ctx.json", saxpy_kernel("saxpy_4ctx", 64, contexts=4, description="saxpy on four hardware contexts with disjoint arrays: shows the core reaching one vector op per cycle with two or more threads"))
write("saxpy_bad_candidate.json", saxpy_kernel("saxpy_bad_candidate", 64, wrong=True, description="DELIBERATELY WRONG expected output (lane 3 off by one): functional must report functional_mismatch and simulate must refuse to report a timing"))
cold = {"memory": {"type": "line_tracking", "cold_level": "memory", "hardware_prefetcher": "off"}, "branch": {"type": "all_predicted"}}
write("stream_cold_nopf.json", saxpy_kernel("stream_cold_nopf", 512, scenario=cold, description="saxpy over 512 floats with every line cold in memory and no software prefetch: demand misses stall the context"))
write("stream_cold_pf.json", saxpy_kernel("stream_cold_pf", 512, prefetch=True, scenario=cold, description="same as stream_cold_nopf with vprefetch0 four lines ahead: nonblocking prefetches hide part of the miss latency"))
write("budget_long_loop.json", {"schema": SCHEMA, "name": "budget_long_loop",
                                 "description": "20000 iterations adding the same 16 ones into an accumulator (result 20000.0 exactly); run with --max-cycles 2000 or --max-steps 500 to see budget_exhausted reported as partial, not as a result",
                                 "unit_of_work": {"description": "one 16-lane add", "count": 20000},
                                 "init": {"memory": [{"addr": "0x700000", "fill": {"f32": 1.0, "count": 16}}],
                                          "registers": {"rax": "0x700000", "rdx": 20000, "zmm0": {"f32_broadcast": 0.0}}},
                                 "streams": [{"context": 0, "instructions": [
                                     {"id": "acc", "op": "vaddps", "ops": ["zmm0", "zmm0", {"base": "rax"}], "label": "L"},
                                     {"id": "cnt", "op": "dec", "ops": ["rdx"]},
                                     {"id": "br", "op": "jnz", "ops": ["L"]}]}],
                                 "loop": {"label": "L", "trip_count": 20000},
                                 "expected": {"registers": {"0": {"zmm0": {"f32_broadcast": 20000.0}}}}})

# ---------------------------------------------------------------------------------------------
# scalar / mask edge cases: expected values from Python ints
k = {"schema": SCHEMA, "name": "int_mask_edge",
     "description": "scalar flag edge cases (signed overflow, borrow, dec to zero), a counted loop, kortest all-ones and all-zero, kandn/knot, vpaddd wrap-around, vpcmpd to mask, masked merge",
     "unit_of_work": {"description": "whole kernel", "count": 1},
     "init": {"registers": {"rax": "0x7fffffffffffffff", "rbx": 1, "rcx": 0, "rdx": 5, "k1": "0xffff", "k2": "0x00ff",
                            "zmm0": {"u32": [0xFFFFFFFF, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
                            "zmm1": {"u32_broadcast": 1}, "zmm3": {"u32_broadcast": 0xAAAAAAAA}}},
     "streams": [{"context": 0, "instructions": [
         {"id": "i0", "op": "add", "ops": ["rax", "rbx"], "comment": "0x7fff..f + 1 -> signed overflow: OF=1 SF=1 CF=0"},
         {"id": "i1", "op": "mov", "ops": ["rsi", 0]},
         {"id": "i2", "op": "sub", "ops": ["rsi", "rbx"], "comment": "0 - 1 -> borrow CF=1, result -1"},
         {"id": "i3", "op": "mov", "ops": ["rdi", 0], "label": "LP"},
         {"id": "i3b", "op": "add", "ops": ["rcx", 3], "comment": "loop body: rcx += 3, five times"},
         {"id": "i4", "op": "dec", "ops": ["rdx"]},
         {"id": "i5", "op": "jnz", "ops": ["LP"]},
         {"id": "i6", "op": "kortest", "ops": ["k1", "k2"], "comment": "0xffff|0x00ff = 0xffff -> CF=1 ZF=0"},
         {"id": "i7", "op": "kandn", "ops": ["k2", "k1"], "comment": "k2 = ~k2 & k1 = 0xff00"},
         {"id": "i8", "op": "knot", "ops": ["k3", "k1"], "comment": "k3 = 0"},
         {"id": "i9", "op": "kortest", "ops": ["k3", "k3"], "comment": "0 -> ZF=1 CF=0"},
         {"id": "i10", "op": "vpaddd", "ops": ["zmm4", "zmm0", "zmm1"], "comment": "lane0 wraps to 0"},
         {"id": "i11", "op": "vpcmpd", "ops": ["k4", "zmm4", "zmm1", 6], "comment": "k4 = zmm4 > 1 signed: lanes 1..15 (values 2..16) -> 0xfffe"},
         {"id": "i12", "op": "vmovdqa32", "ops": ["zmm5", "zmm3"]},
         {"id": "i13", "op": "vpxord", "ops": ["zmm5", "zmm5", "zmm5"], "mask": "k2", "comment": "merge: lanes 8..15 zeroed, 0..7 keep 0xAAAAAAAA"},
     ]}],
     "expected": {"registers": {"0": {
         "rax": "0x8000000000000000", "rsi": "0xffffffffffffffff", "rcx": 15, "rdx": 0,
         "k2": "0xff00", "k3": 0, "k4": "0xfffe",
         "zmm4": {"u32": [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]},
         "zmm5": {"u32": [0xAAAAAAAA] * 8 + [0] * 8},
         "flags": {"ZF": 1, "CF": 0, "SF": 0, "OF": 0}}}}}
write("int_mask_edge.json", k)

# ---------------------------------------------------------------------------------------------
# floating-point edge cases, hand-derived bit patterns
ONE = 0x3f800000
k = {"schema": SCHEMA, "name": "fp_edge",
     "description": "binary32 edge cases with hand-derived expected bits: fused vs unfused FMA, directed rounding, exact cancellation sign, inf-inf, NaN propagation, subnormal result with and without FTZ",
     "unit_of_work": {"description": "whole kernel", "count": 1},
     "numerical_policy": {"rounding": "rn", "ftz": False, "daz": False, "nan_compare": "any_nan"},
     "init": {"registers": {
         "k1": "0xffff",
         "zmm0": {"u32_broadcast": 0x3f800001},   # 1 + 2^-23
         "zmm1": {"u32_broadcast": 0x3f7fffff},   # 1 - 2^-24
         "zmm2": {"u32_broadcast": 0xbf800000},   # -1
         "zmm3": {"u32_broadcast": 0x33800000},   # 2^-24
         "zmm4": {"u32_broadcast": 0x7f800000},   # +inf
         "zmm5": {"u32_broadcast": 0xff800000},   # -inf
         "zmm6": {"u32_broadcast": 0x7fc00001},   # quiet NaN with payload
         "zmm7": {"u32_broadcast": 0x00800000},   # smallest normal 2^-126
         "zmm8": {"u32_broadcast": 0x3f000000},   # 0.5
         "zmm9": {"u32_broadcast": ONE},
     }},
     "streams": [{"context": 0, "instructions": [
         {"id": "fma", "op": "vmovaps", "ops": ["zmm10", "zmm2"]},
         {"id": "fma2", "op": "vfmadd231ps", "ops": ["zmm10", "zmm0", "zmm1"],
          "comment": "(1+2^-23)(1-2^-24) - 1 = 2^-24 - 2^-47 exactly, representable as 0x337ffffe (fused, single rounding). Unfused: the product 1 + 2^-24 - 2^-47 rounds to 1.0 and the result is 0."},
         {"id": "rd", "op": "vaddps", "ops": ["zmm11", "zmm9", "zmm3"], "rounding": "rd", "comment": "1 + 2^-24 rounded down = 1"},
         {"id": "ru", "op": "vaddps", "ops": ["zmm12", "zmm9", "zmm3"], "rounding": "ru", "comment": "1 + 2^-24 rounded up = 1 + 2^-23 (0x3f800001)"},
         {"id": "rn", "op": "vaddps", "ops": ["zmm13", "zmm9", "zmm3"], "comment": "1 + 2^-24 nearest-even = 1 (tie to even)"},
         {"id": "canc", "op": "vaddps", "ops": ["zmm14", "zmm9", "zmm2"], "comment": "1 + (-1) = +0 under rn"},
         {"id": "cancrd", "op": "vaddps", "ops": ["zmm15", "zmm9", "zmm2"], "rounding": "rd", "comment": "1 + (-1) = -0 under rd"},
         {"id": "infinf", "op": "vaddps", "ops": ["zmm16", "zmm4", "zmm5"], "comment": "inf + -inf = default NaN"},
         {"id": "nanp", "op": "vmulps", "ops": ["zmm17", "zmm6", "zmm9"], "comment": "NaN * 1 = NaN (payload propagation not asserted: any NaN matches)"},
         {"id": "sub", "op": "vmulps", "ops": ["zmm18", "zmm7", "zmm8"], "comment": "2^-126 * 0.5 = 2^-127, a subnormal (0x00400000) with FTZ off"},
     ]}],
     "expected": {"registers": {"0": {
         "zmm10": {"u32_broadcast": 0x337ffffe},
         "zmm11": {"u32_broadcast": ONE},
         "zmm12": {"u32_broadcast": 0x3f800001},
         "zmm13": {"u32_broadcast": ONE},
         "zmm14": {"u32_broadcast": 0x00000000},
         "zmm15": {"u32_broadcast": 0x80000000},
         "zmm16": {"f32": ["nan"] * 16},
         "zmm17": {"f32": ["nan"] * 16},
         "zmm18": {"u32_broadcast": 0x00400000},
     }}}}
write("fp_edge.json", k)
k2 = json.loads(json.dumps(k))
k2["name"] = "fp_edge_ftz"
k2["description"] = "fp_edge with FTZ on: the subnormal product flushes to +0; everything else unchanged"
k2["numerical_policy"]["ftz"] = True
k2["expected"]["registers"]["0"]["zmm18"] = {"u32_broadcast": 0}
write("fp_edge_ftz.json", k2)

# ---------------------------------------------------------------------------------------------
# gathers: one line vs 16 lines
table = list(range(0, 4096))  # u32 table at 0x300000: value == index
for name, idx, desc in (("gather_one_line", list(range(16)), "all 16 lanes in one cache line"),
                        ("gather_scattered", [i * 16 for i in range(16)], "each lane in a different cache line (stride 64 bytes)")):
    k = {"schema": SCHEMA, "name": name, "description": "vgatherdps %s; expected lanes are the gathered indices themselves" % desc,
         "unit_of_work": {"description": "one 16-lane gather", "count": 1},
         "init": {"memory": [{"addr": "0x300000", "u32": table[:256]}],
                  "registers": {"rax": "0x300000", "k1": "0xffff", "zmm1": {"u32": idx}}},
         "streams": [{"context": 0, "instructions": [
             {"id": "g", "op": "vgatherdps", "ops": ["zmm0", {"base": "rax", "vindex": "zmm1", "scale": 4}], "mask": "k1", "lines": 1 if name == "gather_one_line" else 16},
             {"id": "use", "op": "vpaddd", "ops": ["zmm2", "zmm0", "zmm0"]},
         ]}],
         "expected": {"registers": {"0": {"zmm0": {"u32": idx}, "k1": 0, "zmm2": {"u32": [2 * i for i in idx]}}}}}
    write(name + ".json", k)

# ---------------------------------------------------------------------------------------------
# unknown instruction, missing parameter
write("unknown_insn.json", {"schema": SCHEMA, "name": "unknown_insn", "description": "uses a mnemonic outside the supported subset: every command must stop with status unsupported",
                            "unit_of_work": {"description": "whole kernel", "count": 1},
                            "streams": [{"context": 0, "instructions": [{"id": "a", "op": "vpmadd52luq", "ops": ["zmm0", "zmm1", "zmm2"]}]}]})
write("fence_unknown_param.json", {"schema": SCHEMA, "name": "fence_unknown_param",
                                   "description": "a lock-prefixed add used as a publication fence (timing-only, so use --trace-source static; addr fields supply the addresses); latency.fence is unknown in every bundled profile, so simulate stops with missing_parameter instead of guessing",
                                   "unit_of_work": {"description": "whole kernel", "count": 1},
                                   "init": {"memory": [{"addr": "0x4000", "u32": [0] * 16}], "registers": {"rax": "0x4000", "zmm0": {"u32_broadcast": 7}}},
                                   "streams": [{"context": 0, "instructions": [
                                       {"id": "st", "op": "vmovaps", "ops": [{"base": "rax"}, "zmm0"], "addr": {"start": "0x4000"}},
                                       {"id": "fence", "op": "lock_add", "ops": [{"base": "rax", "disp": 64}, 0], "width": 32, "addr": {"start": "0x4040"}},
                                   ]}]})
write("vpermd_common_profile.json", {"schema": SCHEMA, "name": "vpermd_common_profile",
                                     "description": "vpermd has no documented latency; with --profile knc-common simulate stops with missing_parameter, with card-7120-measured it uses the measured 6 cycles",
                                     "unit_of_work": {"description": "whole kernel", "count": 1},
                                     "init": {"registers": {"zmm0": {"u32": list(range(16))}, "zmm1": {"u32": list(reversed(range(16)))}}},
                                     "streams": [{"context": 0, "instructions": [
                                         {"id": "p", "op": "vpermd", "ops": ["zmm2", "zmm1", "zmm0"]},
                                         {"id": "u", "op": "vpaddd", "ops": ["zmm3", "zmm2", "zmm2"]},
                                     ]}],
                                     "expected": {"registers": {"0": {"zmm2": {"u32": list(reversed(range(16)))}, "zmm3": {"u32": [2 * x for x in reversed(range(16))]}}}}})

# ---------------------------------------------------------------------------------------------
# reductions: 1 vs 2 accumulators, 32 vectors of ones. Sum of 32 vectors of 1.0 = 32.0 exactly.
def reduce_kernel(name, accs):
    n_vec = 32
    body = []
    per_iter = accs
    if accs == 1:
        body = [{"id": "ld", "op": "vaddps", "ops": ["zmm0", "zmm0", {"base": "rax", "index": "rcx", "scale": 4}], "label": "L"}]
    else:
        body = [{"id": "ld0", "op": "vaddps", "ops": ["zmm0", "zmm0", {"base": "rax", "index": "rcx", "scale": 4}], "label": "L"},
                {"id": "ld1", "op": "vaddps", "ops": ["zmm1", "zmm1", {"base": "rax", "index": "rcx", "scale": 4, "disp": 64}]}]
    body += [{"id": "adv", "op": "add", "ops": ["rcx", 16 * per_iter]},
             {"id": "cnt", "op": "dec", "ops": ["rdx"]},
             {"id": "br", "op": "jnz", "ops": ["L"]}]
    tail = [] if accs == 1 else [{"id": "fin", "op": "vaddps", "ops": ["zmm0", "zmm0", "zmm1"]}]
    return {"schema": SCHEMA, "name": name,
            "description": "sum of 32 vectors of 1.0 with %d accumulator(s): recurrence-bound at one thread with one accumulator (RecMII 4), issue-bound with two" % accs,
            "unit_of_work": {"description": "one 16-lane vector added", "count": n_vec},
            "init": {"memory": [{"addr": "0x500000", "fill": {"f32": 1.0, "count": 16 * n_vec}}],
                     "registers": {"rax": "0x500000", "rcx": 0, "rdx": n_vec // per_iter, "zmm0": {"f32_broadcast": 0.0}, "zmm1": {"f32_broadcast": 0.0}}},
            "streams": [{"context": 0, "instructions": body + tail}],
            "loop": {"label": "L", "trip_count": n_vec // per_iter},
            "expected": {"registers": {"0": {"zmm0": {"f32_broadcast": 32.0}}}}}


write("reduce_1acc.json", reduce_kernel("reduce_1acc", 1))
write("reduce_2acc.json", reduce_kernel("reduce_2acc", 2))

# ---------------------------------------------------------------------------------------------
# AGI: pointer update right before its use vs one instruction apart (static timing demo)
for name, gap in (("agi_gap0", 0), ("agi_gap1", 1)):
    ins = [{"id": "p", "op": "add", "ops": ["rax", 64]}]
    if gap:
        ins.append({"id": "x", "op": "add", "ops": ["rbx", 1]})
    ins.append({"id": "ld", "op": "mov", "ops": ["rcx", {"base": "rax"}], "width": 64})
    ins.append({"id": "use", "op": "add", "ops": ["rdx", "rcx"]})
    write(name + ".json", {"schema": SCHEMA, "name": name,
                           "description": "address-generation interlock: the load uses rax %s after it is written" % ("immediately" if gap == 0 else "one instruction"),
                           "unit_of_work": {"description": "whole kernel", "count": 1}, "memory_default": 0,
                           "init": {"registers": {"rax": "0x6000", "rbx": 0, "rdx": 0}},
                           "streams": [{"context": 0, "instructions": ins}]})

# ---------------------------------------------------------------------------------------------
# GAS subset version of saxpy
asm = """# saxpy inner loop in the knc-twin GAS subset (AT&T, k1om)
\t.text
L:
\tvmovaps (%rax,%rcx,4), %zmm0
\tvmovaps (%rbx,%rcx,4), %zmm1
\tvfmadd231ps %zmm0, %zmm2, %zmm1
\tvmovaps %zmm1, (%rbx,%rcx,4)
\taddq $16, %rcx
\tdecq %rdx
\tjnz L
"""
with open(os.path.join(HERE, "saxpy.s"), "w", encoding="utf-8", newline="\n") as f:
    f.write(asm)
k = saxpy_kernel("saxpy_asm", 64)
k["streams"][0].pop("instructions")
k["streams"][0]["asm_file"] = "saxpy.s"
k["description"] = "the saxpy loop given as GAS AT&T assembly (fixtures/saxpy.s); same inputs and expected output as saxpy_loop.json"
write("saxpy_asm.json", k)

# ---------------------------------------------------------------------------------------------
# analytic parameters
write("card_params_stream.json", {"schema": "knc-twin.analytic-params/1", "description": "card scenario for a bandwidth-bound stream: 16 M units of 128 bytes read-modify-write, one barrier",
                                  "units": 16777216, "bytes_per_unit": 128, "traffic_type": "read_modify_write",
                                  "per_core_cycles_per_unit": 6.0, "barriers": 1, "barrier_kind": "tree", "imbalance_factor": 1.05})
write("card_params_readonly_sweep.json", {"schema": "knc-twin.analytic-params/1", "description": "read-only traffic has no measured bandwidth in the 7120 profile; without bandwidth_sweep_gbs the result is needs_parameters",
                                          "units": 16777216, "bytes_per_unit": 64, "traffic_type": "read_only", "per_core_cycles_per_unit": 3.0,
                                          "bandwidth_sweep_gbs": [160, 200, 264, 299]})
write("card_params_readonly_missing.json", {"schema": "knc-twin.analytic-params/1", "description": "same as the sweep file but without a sweep: must stop with needs_parameters",
                                            "units": 16777216, "bytes_per_unit": 64, "traffic_type": "read_only", "per_core_cycles_per_unit": 3.0})
write("pair_params.json", {"schema": "knc-twin.analytic-params/1", "description": "producer/consumer pair exchanging 64 lines per unit with one handoff",
                           "core_a_cycles": 2000, "core_b_cycles": 1500, "lines_exchanged": 64, "handoffs": 1})
