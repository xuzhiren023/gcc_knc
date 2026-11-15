#!/usr/bin/env python3
"""Write the S13-06 trial cases (cases/*.json) and char.s.

A case names an assembly file and loop for scripts/from_gcc_s.py, the spec that supplies what
assembly cannot (data, expected outputs computed here in Python integers, unit of work), the
runs to make, and for the characterization kernels the native numbers they are checked against
(docs/research/knc-characterization.md). `expect` holds what the regress test checks: the
conversion status (with every unsupported line) and the functional status.

char.s repeats the bodies of tests/bench/knc-char/s8_compute.py (C7, C9) and kernels.py
(pair.*, agi.*): the same instructions per loop iteration and the `subq $1, %rdi; jnz` back
edge; only the label names differ (written before the parser took numeric local labels).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases")
CHAR_DOC = "docs/research/knc-characterization.md"
F32_ONE = 0x3F800000


def f32_list(values):
    return [float(v) for v in values]


def u32(x):
    return "0x%08x" % (x & 0xFFFFFFFF)


def u64(x):
    return "0x%016x" % (x & 0xFFFFFFFFFFFFFFFF)


def write_case(case):
    case["schema"] = "knc-twin.trial-case/1"
    with open(os.path.join(CASES, case["name"] + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(case, f, indent=1)
        f.write("\n")


# ---------------------------------------------------------------------------------------------
# char.s: characterization bodies
char = ["# S13-06 consistency kernels: bodies of tests/bench/knc-char s8_compute.py / kernels.py", "\t.text"]


def char_loop(label, body):
    char.append(label + ":")
    char.extend("\t" + line for line in body)
    char.extend(["\tsubq\t$1, %rdi", "\tjnz\t" + label])


for u in (1, 2, 4):
    char_loop(".Lc9_vector_u%d" % u, ["vaddps\t%%zmm31, %%zmm%d, %%zmm%d" % (i, i) for i in range(u)])
for a in (1, 2):
    char_loop(".Lc7_reduce_a%d" % a, ["vaddps\t%d(%%rsi), %%zmm%d, %%zmm%d" % (64 * i, i % a, i % a) for i in range(32)])
pair_vs, pair_vv = [], []
for i in range(32):
    pair_vs += ["vaddps\t%%zmm31, %%zmm%d, %%zmm%d" % (i % 8, i % 8), "addq\t$1, %r8"]
    pair_vv += ["vaddps\t%%zmm31, %%zmm%d, %%zmm%d" % (i % 8, i % 8), "vpaddd\t%%zmm31, %%zmm%d, %%zmm%d" % (8 + i % 8, 8 + i % 8)]
char_loop(".Lpair_vector_scalar", pair_vs)
char_loop(".Lpair_vector_vector", pair_vv)
for gap in (0, 1):
    char_loop(".Lagi_gap%d" % gap, (["addq\t$0, %rsi"] + ["nop"] * gap + ["movq\t(%rsi), %r8"]) * 32)
with open(os.path.join(HERE, "char.s"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(char) + "\n")

os.makedirs(CASES, exist_ok=True)
for old in os.listdir(CASES):
    os.remove(os.path.join(CASES, old))

POLICY = {"rounding": "rn", "ftz": False, "daz": False, "nan_compare": "bits"}
L1 = {"memory": {"type": "fixed_level", "level": "l1"}, "branch": {"type": "all_predicted"}}

# ---------------------------------------------------------------------------------------------
# instruction forms added for real -O2 output (fixtures/gcc_o2_forms.s)
values = [3, -2, 5, -7]
zext = [v & 0xFFFFFFFF for v in values]  # movl zero-extends into the 64-bit register
rsi = sum(4 * v for v in zext) + 100  # the jbe loop, then ja not taken (+100), jnb taken (skips +1000)
write_case({
    "name": "gcc_forms_scalar", "kind": "form_fixture", "source": "../../fixtures/gcc_o2_forms.s", "loop": ".Lscalar", "contexts": 1,
    "spec": {"unit_of_work": {"description": "one int32 element", "count": 4}, "numerical_policy": POLICY, "scenario": L1,
             "init": {"memory": [{"addr": "0x10000", "i32": values}],
                      "registers": {"r8": "0x10000", "rax": 0, "rsi": 0, "rdi": 5}},
             "expected": {"registers": {"0": {"rsi": rsi, "rax": 4, "rdi": 10, "r10": u64(zext[-1]), "r11": u64(4 * zext[-1])}}},
             "loop": {"trip_count": 4}},
    "trace_source": "functional", "simulate": [[0]], "bounds_loop": False,
    "expect": {"conversion": "ok", "functional": "ok"}})
# movslq: knc-twin 0.2.0 executes it exactly and times it as a scalar ALU op (cost unsourced: R02
# Table 3-1 p.34 does not list MOVSX/MOVSXD; lead decision pending, docs/research/knc-twin-trial.md)
sext = [v & 0xFFFFFFFFFFFFFFFF for v in values]
write_case({
    "name": "gcc_forms_movslq", "kind": "form_fixture", "source": "../../fixtures/gcc_o2_forms.s", "loop": ".Lmovslq", "contexts": 1,
    "spec": {"unit_of_work": {"description": "one int32 index", "count": 4}, "numerical_policy": POLICY, "scenario": L1,
             "init": {"memory": [{"addr": "0x10000", "i32": values}], "registers": {"r8": "0x10000", "rax": 0}},
             "expected": {"registers": {"0": {"rax": 4, "r10": u64(sext[-1]), "r11": u64(sext[-1])}}},
             "loop": {"trip_count": 4}},
    "trace_source": "functional", "simulate": [[0]], "bounds_loop": False,
    "expect": {"conversion": "ok", "functional": "ok"}})

# vloadunpackl/hps and vpackstorel/hps execute exactly in knc-twin 0.2.0: y[i] = x[i-1] + x[i]
# with x[i] = 16 + i stored from 64 bytes below x (integer-valued, exact in binary32)
write_case({
    "name": "gcc_forms_unpack", "kind": "form_fixture", "source": "../../fixtures/gcc_o2_forms.s", "loop": ".Lunpack", "contexts": 1,
    "spec": {"unit_of_work": {"description": "16 floats", "count": 4}, "numerical_policy": POLICY, "scenario": L1,
             "init": {"memory": [{"addr": "0x2fffc0", "f32": f32_list(range(64 + 32))}],
                      "registers": {"r8": "0x300000", "rsi": "0x400000", "rax": 0, "rdx": 256}},
             "expected": {"memory": [{"addr": "0x400000", "f32": f32_list(31 + 2 * i for i in range(64))}]},
             "memory_default": 0, "loop": {"trip_count": 4}},
    "trace_source": "functional", "simulate": [[0]], "bounds_loop": False,
    "expect": {"conversion": "ok", "functional": "ok"}})

# ---------------------------------------------------------------------------------------------
# trial loops compiled by the frozen prefix (trial.s), no native time
TRIP = 8
memory, expected_mem, stream_l7, stream_l5 = [], [], [], []
for c in range(4):
    x, y = 0x100000 + c * 0x10000, 0x200000 + c * 0x10000
    xs = [i + c for i in range(16 * TRIP)]
    ys = [2 * i for i in range(16 * TRIP)]
    memory += [{"addr": hex(x), "f32": f32_list(xs)}, {"addr": hex(y), "f32": f32_list(ys)}]
    expected_mem.append({"addr": hex(y), "f32": f32_list(3 * a + b for a, b in zip(xs, ys))})
    stream_l7.append({"registers": {"r8": hex(y), "r9": hex(x), "rax": 0, "rdx": 64 * TRIP}})
    stream_l5.append({"registers": {"rax": hex(y), "rdx": hex(x), "rcx": 0, "rsi": TRIP}})
saxpy = {"unit_of_work": {"description": "16 floats of y = a*x + y (one iteration of one context)", "count": 4 * TRIP},
         "numerical_policy": POLICY, "scenario": L1, "memory_default": 0,
         "init": {"memory": memory, "registers": {"zmm1": {"f32_broadcast": 3.0}}},
         "expected": {"memory": expected_mem}, "loop": {"trip_count": TRIP}}
ALL = [[0], [0, 1], [0, 1, 2, 3]]
write_case({"name": "trial_saxpy_L7", "kind": "trial", "source": "trial.s", "loop": ".L7", "contexts": 4,
            "spec": dict(saxpy, name="saxpy_L7", stream_init=stream_l7), "trace_source": "functional",
            "simulate": ALL, "bounds_loop": True, "expect": {"conversion": "ok", "functional": "ok"}})
write_case({"name": "trial_saxpy_L5", "kind": "trial", "source": "trial.s", "loop": ".L5", "contexts": 4,
            "spec": dict(saxpy, name="saxpy_L5", stream_init=stream_l5), "trace_source": "functional",
            "simulate": ALL, "bounds_loop": True, "compare_with": "trial_saxpy_L7",
            "expect": {"conversion": "ok", "functional": "ok"}})
# fsum .L26: x87 float reduction, 16 floats per iteration; the loop is entered after fldz, so
# the x87 stack starts with 0.0. n = 48: rcx = ((n - 17) & -16) + 16 = 32, two iterations.
FS = 32
write_case({"name": "trial_fsum_L26", "kind": "trial", "source": "trial.s", "loop": ".L26", "contexts": 1,
            "spec": {"name": "fsum_L26", "unit_of_work": {"description": "one float added", "count": FS},
                     "numerical_policy": POLICY, "scenario": L1, "memory_default": 0, "loop": {"trip_count": FS // 16},
                     "init": {"memory": [{"addr": "0x200000", "f32": f32_list(range(1, FS + 1))}],
                              "registers": {"rax": "0x200000", "rsi": "0x200000", "rdx": 0, "rcx": FS, "x87": [0.0]}},
                     "expected": {"registers": {"0": {"st0": float(FS * (FS + 1) // 2), "x87_depth": 1, "rdx": FS,
                                                      "rax": hex(0x200000 + 4 * FS)}}}},
            "trace_source": "functional", "simulate": [[0]], "bounds_loop": True,
            "expect": {"conversion": "ok", "functional": "ok"}})

# stencil1 .L51 (the no-prefetch path): y[i] = (x[i-1] + x[i]) + x[i+1], x[i] = 16 + i + c in
# context c (stored from 64 bytes below x), each context with its own x and y
STRIP = 4
st_mem, st_exp, st_init = [], [], []
for c in range(4):
    x, y = 0x300000 + c * 0x10000, 0x400000 + c * 0x10000
    st_mem.append({"addr": hex(x - 64), "f32": f32_list(v + c for v in range(64 * STRIP + 32))})
    st_exp.append({"addr": hex(y), "f32": f32_list(48 + 3 * i + 3 * c for i in range(64 * STRIP))})
    st_init.append({"registers": {"r8": hex(x), "rsi": hex(y)}})
write_case({"name": "trial_stencil_L51", "kind": "trial", "source": "trial.s", "loop": ".L51", "contexts": 4,
            "spec": {"name": "stencil1_L51", "unit_of_work": {"description": "16 outputs y[i] = (x[i-1] + x[i]) + x[i+1]",
                                                              "count": 4 * 4 * STRIP},
                     "numerical_policy": POLICY, "scenario": L1, "loop": {"trip_count": STRIP}, "memory_default": 0,
                     "init": {"memory": st_mem, "registers": {"rax": 0, "r9": 256 * STRIP}},
                     "expected": {"memory": st_exp}, "stream_init": st_init},
            "trace_source": "functional", "simulate": ALL, "bounds_loop": True,
            "expect": {"conversion": "ok", "functional": "ok"}})

# ---------------------------------------------------------------------------------------------
# characterization consistency (these rows built the profile: consistency, not validation)
ONES = {"f32_broadcast": 1.0}


def char_case(name, loop, contexts, trip, units_per_iter, unit, regs, expected_regs, measured, memory=None, stream_init=None,
              memory_default=None):
    spec = {"name": name, "unit_of_work": {"description": unit, "count": units_per_iter * trip * contexts},
            "numerical_policy": POLICY, "scenario": L1, "loop": {"trip_count": trip},
            "init": {"registers": dict(regs, rdi=trip)},
            "expected": {"registers": {str(c): dict(expected_regs, rdi=0) for c in range(contexts)}}}
    if memory:
        spec["init"]["memory"] = memory
    if stream_init:
        spec["stream_init"] = stream_init
    if memory_default is not None:
        spec["memory_default"] = memory_default
    write_case({"name": name, "kind": "consistency", "source": "char.s", "loop": loop, "contexts": contexts, "spec": spec,
                "trace_source": "functional", "simulate": ALL[:2] if contexts == 2 else ALL,
                "bounds_loop": True, "measured": measured,
                "expect": {"conversion": "ok", "functional": "ok"}})


for u, trip, m in ((1, 64, (4.02, 4.02)), (2, 32, (3.02, 3.01)), (4, 16, (2.52, 2.51))):
    regs = dict({"zmm31": ONES}, **{"zmm%d" % i: ONES for i in range(u)})
    char_case("c9_vector_u%d" % u, ".Lc9_vector_u%d" % u, 2, trip, u, "one 16-lane vaddps update", regs,
              {"zmm%d" % i: {"f32_broadcast": 1.0 + trip} for i in range(u)},
              {"source": CHAR_DOC + " C9 (S8-01), register chain", "unit": "TSC ticks per update per thread",
               "threads": {"1": m[0], "2": m[1]}})
for a in (1, 2):
    trip = 4
    mem = [{"addr": hex(0x500000 + c * 0x1000), "f32": [1.0] * 512} for c in range(4)]
    init = [{"registers": {"rsi": hex(0x500000 + c * 0x1000)}} for c in range(4)]
    acc = {"zmm%d" % i: {"f32_broadcast": 32.0 * trip / a} for i in range(a)}
    char_case("c7_reduce_a%d" % a, ".Lc7_reduce_a%d" % a, 4, trip, 32, "one 16-lane vector update",
              {"zmm%d" % i: {"f32_broadcast": 0.0} for i in range(a)}, acc,
              {"source": CHAR_DOC + " C7 (S8-01)", "unit": "TSC ticks per update per thread", "threads": {"4": 4.13}},
              memory=mem, stream_init=init)
trip = 4
regs = dict({"zmm31": ONES, "r8": 1}, **{"zmm%d" % i: ONES for i in range(16)})
char_case("pair_vector_scalar", ".Lpair_vector_scalar", 4, trip, 32, "one vaddps + addq pair", regs,
          dict({"r8": 1 + 32 * trip}, **{"zmm%d" % i: {"f32_broadcast": 1.0 + 4 * trip} for i in range(8)}),
          {"source": CHAR_DOC + " Full table pair.vector_scalar (S6-03)", "unit": "TSC ticks per pair per thread",
           "threads": {"1": 2.08, "2": 2.10, "4": 4.20}})
char_case("pair_vector_vector", ".Lpair_vector_vector", 4, trip, 32, "one vaddps + vpaddd pair", regs,
          dict({"zmm%d" % i: {"f32_broadcast": 1.0 + 4 * trip} for i in range(8)},
               **{"zmm%d" % i: {"u32_broadcast": u32(F32_ONE * (1 + 4 * trip))} for i in range(8, 16)}),
          {"source": CHAR_DOC + " Full table pair.vector_vector (S6-03)", "unit": "TSC ticks per pair per thread",
           "threads": {"1": 4.09, "2": 4.08, "4": 8.20}})
agi_init = [{"registers": {"rsi": hex(0x600000 + c * 0x1000)}} for c in range(4)]
char_case("agi_gap0", ".Lagi_gap0", 4, trip, 32, "one addq + dependent-address movq probe", {"r8": 1}, {"r8": 0},
          {"source": CHAR_DOC + " Full table agi.gap0 (S6-03)", "unit": "TSC ticks per probe per thread",
           "threads": {"1": 3.11, "2": 3.17, "4": 4.26}}, stream_init=agi_init, memory_default=0)
# agi.gap1 converts in knc-twin 0.2.0 (nop is an instruction); it set pairing.u_nop_pairs (calibration)
char_case("agi_gap1", ".Lagi_gap1", 4, trip, 32, "one addq + nop + dependent-address movq probe", {"r8": 1}, {"r8": 0},
          {"source": CHAR_DOC + " Full table agi.gap1 (S6-03)", "unit": "TSC ticks per probe per thread",
           "threads": {"1": 4.15, "2": 4.15, "4": 8.27}}, stream_init=agi_init, memory_default=0)
print("wrote", len(os.listdir(CASES)), "cases and char.s")
