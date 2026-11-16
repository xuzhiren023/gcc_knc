#!/usr/bin/env python3
"""Run the example cases and write examples/RESULTS.md with the actual outputs.

Usage: python examples/run_examples.py [--out DIR]
Every example runs in its own directory under DIR (default examples/out-<utc>).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KT = os.path.join(ROOT, "scripts", "knc_twin.py")
FX = os.path.join(ROOT, "fixtures")

CASES = [
    ("capabilities", "What is implemented", ["capabilities"]),
    ("functional-saxpy", "Exact execution and expected-output check", ["functional", "saxpy_loop.json"]),
    ("functional-fp-edge", "FP edge cases (fused FMA, directed rounding, NaN, subnormal)", ["functional", "fp_edge.json"]),
    ("functional-int-mask", "Scalar flags, counted loop, mask ops, masked merge", ["functional", "int_mask_edge.json"]),
    ("functional-bad", "Deliberately wrong candidate: functional_mismatch", ["functional", "saxpy_bad_candidate.json"]),
    ("simulate-saxpy-1ctx", "saxpy loop, one context", ["simulate", "saxpy_loop.json"]),
    ("simulate-saxpy-4ctx", "saxpy loop on four contexts", ["simulate", "saxpy_4ctx.json"]),
    ("simulate-saxpy-asm", "the same loop given as GAS AT&T assembly", ["simulate", "saxpy_asm.json"]),
    ("simulate-saxpy-overlay", "sensitivity: vector load latency 3 instead of 12", ["simulate", "saxpy_loop.json", "--overlay", os.path.join(ROOT, "profiles", "overlay-vector-load-12.json")]),
    ("simulate-cold-nopf", "cold stream without prefetch: demand-miss stalls", ["simulate", "stream_cold_nopf.json"]),
    ("simulate-cold-pf", "cold stream with vprefetch0: nonblocking prefetch", ["simulate", "stream_cold_pf.json"]),
    ("simulate-reduce-1acc", "reduction, one accumulator", ["simulate", "reduce_1acc.json"]),
    ("simulate-reduce-2acc", "reduction, two accumulators", ["simulate", "reduce_2acc.json"]),
    ("simulate-gather-one-line", "gather, all lanes in one line", ["simulate", "gather_one_line.json"]),
    ("simulate-gather-scattered", "gather, 16 lines", ["simulate", "gather_scattered.json"]),
    ("simulate-synthetic", "same kernel on the SYNTHETIC profile (labeled)", ["simulate", "saxpy_loop.json", "--profile", "synthetic-demo"]),
    ("bounds-saxpy", "trace lower bound", ["bounds", "saxpy_loop.json"]),
    ("bounds-loop-1acc", "loop MII, one accumulator (recurrence-bound)", ["bounds", "reduce_1acc.json", "--loop"]),
    ("bounds-loop-2acc", "loop MII, two accumulators (resource-bound)", ["bounds", "reduce_2acc.json", "--loop"]),
    ("bounds-search", "exhaustive reorder search on a small block", ["bounds", "agi_gap1.json", "--search"]),
    ("card-stream", "card scenario: bandwidth-bound stream", ["bounds", "--scale", "card", "--params", "card_params_stream.json"]),
    ("card-readonly-missing", "card scenario needing an unknown bandwidth: needs_parameters", ["bounds", "--scale", "card", "--params", "card_params_readonly_missing.json"]),
    ("card-readonly-sweep", "card scenario with a declared bandwidth sweep", ["bounds", "--scale", "card", "--params", "card_params_readonly_sweep.json"]),
    ("pair", "pair scenario with a concurrency sweep", ["bounds", "--scale", "pair", "--params", "pair_params.json"]),
    ("unsupported-insn", "unknown mnemonic: unsupported", ["simulate", "unknown_insn.json"]),
    ("missing-param", "vpermd on the common profile: missing_parameter", ["simulate", "vpermd_common_profile.json", "--profile", "knc-common"]),
    ("missing-fence", "fence latency unknown on the measured profile: missing_parameter (static trace)", ["simulate", "fence_unknown_param.json", "--trace-source", "static"]),
    ("budget", "cycle budget exhausted: partial, not a result", ["simulate", "budget_long_loop.json", "--max-cycles", "2000"]),
    ("compare-prefetch", "compare cold stream without/with prefetch", ["compare", "@simulate-cold-nopf", "@simulate-cold-pf"]),
    ("compare-incompatible", "compare across different profiles: incompatible", ["compare", "@simulate-saxpy-1ctx", "@simulate-synthetic"]),
    ("prepare-native", "export a hardware-queue request (no card)", ["prepare-native", "saxpy_loop.json", "--prediction", "@simulate-saxpy-1ctx"]),
    ("gcc-x87-f", "GCC-KNC x87 double function, adapter output, exact check", ["functional", os.path.join(FX, "gcc", "x87test_f.json")]),
    ("gcc-x87-g", "GCC-KNC x87 float dot-product loop with prefetches, timing", ["simulate", os.path.join(FX, "gcc", "x87test_g.json")]),
    ("gcc-int-h", "GCC-KNC scalar integer loop, loop bounds", ["bounds", os.path.join(FX, "gcc", "x87test_h.json")]),
    ("batch-gate-csr", "real candidate batch: S12-30 gate CSR variants from the gate's objects, frozen profile, queue routing", ["batch", os.path.join(FX, "batch", "manifest.json")]),
    ("binary-hpcg-spmv", "HPCG ComputeSPMV_ref from the linked S12-31 bench binary (layout, padding, call and ret), toy problem", ["simulate", os.path.join(ROOT, "tests", "heldout_native", "s12-31-hpcg-toy", "kernels", "knc_spmv.json"), "--max-seconds", "600"]),
    ("binary-mb-gas13", "S12-31 row loop behind a 13-byte assembler NOP with 66/2e prefixes (decode delay modeled)", ["simulate", os.path.join(ROOT, "tests", "heldout_native", "s12-31-microbench", "kernels", "gas_13.json")]),
    ("binary-mb-adj0", "the same loop with the compare next to its jump (x87 issues alone)", ["simulate", os.path.join(ROOT, "tests", "heldout_native", "s12-31-microbench", "kernels", "adj_0.json")]),
    ("rollup-hpcg", "program roll-up: S12-31 rule A over the HPCG pilot's SpMV and SymGS shares", ["rollup", os.path.join(FX, "rollup", "manifest.json")]),
    ("calibration-plan", "what the next card window should measure", ["calibration-plan"]),
    ("profile-3120", "the same kernel on the 3120 profile: transferred core timing, unvalidated", ["simulate", "saxpy_loop.json", "--profile", "card-3120-documented"]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = args.out or os.path.join(HERE, "out-%s" % stamp)
    os.makedirs(out_root, exist_ok=True)
    rows = []
    results = {}
    for name, desc, argv in CASES:
        argv = list(argv)
        for i, a in enumerate(argv):
            if a.startswith("@"):
                argv[i] = os.path.join(results[a[1:]], "result.json")
            elif a.endswith(".json") and not os.path.isabs(a) and os.path.exists(os.path.join(FX, a)):
                argv[i] = os.path.join(FX, a)
        out = os.path.join(out_root, name)
        results[name] = out
        cmd = [sys.executable, KT] + argv + ["--out", out]
        if name.startswith("gcc-") or name.startswith("batch-"):
            cmd += ["--force"]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        rp = os.path.join(out, "result.json")
        status, msg = "(no result.json)", p.stderr.strip()
        if os.path.exists(rp):
            with open(rp, encoding="utf-8") as f:
                r = json.load(f)
            status = r["status"]
            msg = r.get("message", "")
        shown = " ".join(("fixtures/" + os.path.basename(a)) if a.startswith(FX) else (("<" + os.path.basename(os.path.dirname(a)) + ">/result.json") if a.endswith("result.json") else a) for a in argv)
        rows.append((name, desc, "python scripts/knc_twin.py " + shown, p.returncode, status, msg))
    lines = ["# Example runs", "", "Generated %s by `examples/run_examples.py` (engine output, not hand-written). Outputs: `%s`." % (stamp, out_root), "",
             "| example | what | command | exit | status | message |", "|---|---|---|---:|---|---|"]
    for name, desc, cmd, rc, status, msg in rows:
        lines.append("| %s | %s | `%s` | %d | %s | %s |" % (name, desc, cmd, rc, status, msg.replace("|", "/").replace("\n", " ")[:300]))
    text = "\n".join(lines) + "\n"
    with open(os.path.join(HERE, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
