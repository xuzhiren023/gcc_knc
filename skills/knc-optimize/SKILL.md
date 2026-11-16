---
name: knc-optimize
description: Optimize, tune, or speed up code for Intel Xeon Phi x100, KNC, MIC, k1om, or IMCI. Use measured bottlenecks, resource bounds, and KNC-specific practices while preserving the program's numerical contract. For Knights Corner, not Knights Landing or modern AVX-512 targets.
---

# Tune code for Knights Corner

Follow the calling project's build, correctness, card-access and timing rules.
Use existing results when card work is unavailable; this skill grants no access.
Sources and reported card evidence are in [practices](references/practices.md).
Missing original evidence does not turn a reported result into a reproduced one.

1. **Measure and locate the hot region.** Profile representative fixed work.
   Record whole-program time and the region's share; separate host work,
   transfers, native compute and synchronization. Identify compiler/runtime and
   inspect executed assembly. Use project timers if counters are unavailable.
   R02 pp.153-159; R16 slides 7,49,52.

2. **Model before changing code.** Invoke installed `model-first` at the caller's
   ticket tier. Count instructions, bytes, dependent chains and parallel span
   for the same unit of work, including address work, gathers, spills and calls.
   Use [machine inputs](references/machine.md); state omissions and assumptions.
   Keep a valid lower bound separate from a prediction with assumed overlap.
   For one-core loops, invoke installed `knc-twin` through its own skill and
   capability checks. Report its status, assumptions and unsupported forms;
   partial or unsuccessful output is not a prediction. Read
   [model details](references/method.md#model-accounting) for accounting,
   twin qualifications and the Model table required before timed work.

3. **Pick the dominant term.** Compare measurement, prediction and bound.
   Investigate unexplained cost or inadequate overlap; audit accounting if a
   result falls below the bound. Low throughput alone does not prove a memory
   bandwidth limit. R02 p.159; R08 slides 23,28; R19 pp.356-360.

4. **Apply the matching practices in evidence order.** Read the relevant rows
   in [practices](references/practices.md) and the
   [term-specific order](references/method.md#practice-order). Start with the
   smallest legal change: vector legality and register reuse for issue cost;
   reuse and contiguous traversal for bytes; placement and stream-aware prefetch
   for latency; layout for gathers; serialization and imbalance for parallel
   span; residency and batching for transfers. Count costs introduced by changes.
   Check [pitfalls](references/pitfalls.md) before arithmetic or runtime changes.
   Preserve required FP order, precision, exceptions, errno and memory safety.

5. **Verify under the caller's card rules.** Check correctness and emitted code.
   Compare equal work, inputs, placement, backing and completed timing boundaries.
   Follow the project's repetition/noise policy; retain spread and drift.
   Record predicted and measured effects, including negative results. Stage work
   for the designated operator if required. Host checks are not native passes.
   The [worked example](references/example.md) uses existing card measurements.

6. **Stop when further tuning is unjustified.** Stop at an applicable bound
   within uncertainty, below 5% potential whole-program gain, within measured
   noise, or at the caller's budget. The 5% threshold is this skill's policy,
   not a hardware constant. A conditional measured roof is not a proven limit.
   Retain the last validated configuration and record the unresolved term.

For installation, run `sh scripts/install.sh` from this skill folder; it copies
files to `~/.claude/skills/knc-optimize/` without running the workflow. See
[installation details](references/method.md#installation) for a staged copy.
