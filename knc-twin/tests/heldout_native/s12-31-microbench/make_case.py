#!/usr/bin/env python3
"""Write case.json for the S12-31 row-loop microbenchmark (held out; S13-06 merge).

The input is the driver's (tools/s12_31_bench.cpp in gcc_knc): xs[j] = 0.5 + 0.03125 j (32
doubles), vals[j] = 1 / 2^(j % 5) and idx[j] = (j * 7) % 32 (27 each); mb_<v>(rows, 27, xs,
vals, idx, &out) accumulates every row into one x87 register and stores the sum. All products
and partial sums are dyadic with few bits, so the expected result rows * rowsum is exact in
binary64 and in the x87 extended format. The prediction is the slope of completion cycles
between 4 and 8 rows (prologue and cold start cancel); data is declared warm in L1 (the
driver's arrays are a few hundred bytes and reused 100000 times).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
XS, VALS, IDX, OUT = 0x100000, 0x101000, 0x102000, 0x103000
xs = [0.5 + 0.03125 * j for j in range(32)]
vals = [1.0 / (1 << (j % 5)) for j in range(27)]
idx = [(j * 7) % 32 for j in range(27)]
rowsum = 0.0
for j in range(27):
    rowsum += xs[idx[j]] * vals[j]
ROWS = (4, 8)
warm = [{"start": hex(a), "end": hex(a + 0x100), "level": "l1"} for a in (XS, VALS, IDX, OUT)]
case = {
    "schema": "knc-twin.heldout-case/2",
    "scale": "core",
    "kind": "compiled_function",
    "description": "S12-31 SpMV-shaped x87 row loop, 27 products per row, data in L1, one thread; the variants differ "
                   "only in the order of counter, compare and FP add (and a dead movl)",
    "source": "mb.s",
    "unit": "one 27-product row (27 inner iterations plus the outer loop step)",
    "slope_register": "rdi",
    "slope_units": list(ROWS),
    "init": {"registers": {"rsi": 27, "rdx": hex(XS), "rcx": hex(VALS), "r8": hex(IDX), "r9": hex(OUT), "rax": 0},
             "memory": [{"addr": hex(XS), "f64": xs}, {"addr": hex(VALS), "f64": vals}, {"addr": hex(IDX), "i32": idx}]},
    "expected": {str(r): {"memory": [{"addr": hex(OUT), "f64": [r * rowsum]}]} for r in ROWS},
    "scenario_name": "harness scenario A (line tracking, TLB modeled, hardware prefetcher off), arrays warm in L1, branches predicted",
    "scenario": {"memory": {"type": "line_tracking", "cold_level": "memory", "tlb": "modeled", "hardware_prefetcher": "off",
                            "memory_service": "modeled", "warm": warm},
                 "branch": {"type": "all_predicted"}},
    "variants": [{"name": v, "function": "mb_" + v}
                 for v in ("gas_0", "mis_44", "inc_0", "adj_0", "mid_0", "mov_adj_0", "mov_split_0")],
}
with open(os.path.join(HERE, "case.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(case, f, indent=1)
    f.write("\n")
print("rowsum", rowsum)
