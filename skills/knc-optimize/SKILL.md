---
name: knc-optimize
description: Optimize, tune, or speed up code for Intel Xeon Phi x100, KNC, MIC, k1om, or IMCI. Use measured bottlenecks, resource bounds, and KNC-specific practices while preserving the program's numerical contract. For Knights Corner, not Knights Landing or modern AVX-512 targets.
---

# Tune code for Knights Corner

Use the calling project's build, correctness, card-access and measurement rules.
This skill does not grant card time or permission to change system settings.
It can also analyze existing results without running anything on the card.

The method combines R02 pp.153-169, R16 slides 49-54 and R19 pp.261-265,
356-360. These sources were checked locally; their experiments are not results
on the caller's machine. Source identities and hardware scope are in
[practices](references/practices.md#source-editions). Project evidence is cited
by document basename and named row, so this folder works without the original
checkout. If that evidence is unavailable, retain its reported status; do not
claim to have reproduced it.

## Method

1. **Measure and locate the hot region.** Use a representative input and the
   existing profile first. Record fixed useful work, whole-program time and
   the region's time share. Separate host work, transfers, native compute and
   synchronization. Identify the actual compiler and loaded runtime. A
   vectorization report is a lead to inspect, not a performance result.
   Check assembly for the path that executes. If card counters are unavailable,
   use the project's timer/profile; report the access failure instead of
   inventing counter values. R02 pp.153-159; R16 slides 7,49,52.

2. **Model the region before changing it.** Invoke the installed `model-first`
   skill when available, at the calling ticket's tier. Supply the actual
   machine/profile, code, numerical contract and existing measurements. Do not
   transplant that skill's original project's paths or card commands. If it is
   unavailable, use this minimal summary: count executed instructions, bytes at
   each memory level, dependent chains and parallel span for one fixed unit of
   work. Include address/control work, prefetches, complete gather retry loops,
   spills and calls. Derive separate resource times; their maximum is a lower
   bound only if each term is a valid bound for that same work. State omissions.
   Derive a prediction separately, with explicit overlap assumptions. Use
   [machine](references/machine.md) for sourced inputs, replacing reported
   measurements only with applicable evidence. Unknown means unknown.

   For a one-core loop or kernel, invoke installed `knc-twin`: read its skill
   and validation reference, then follow its capability check, faithful input
   import, bounds and simulation workflow. Its directory can be anywhere; use
   the installed skill's resolved entry point, never a guessed sibling-project
   path. Keep the real instruction path, inputs and accounting unit. Report
   `status`, `result_class`, `assumptions`, `unsupported`, `limiting_constraints`
   and `calibration_status` as returned. A non-success result or partial result
   is not a prediction. Do not hand-fill missing simulator parameters.
   Until the installed twin documents the dependency-bound correction, a
   trace's `dependency_critical_path` is a cold-start estimate, not a floor.
   Twin predictions within about 20% do not select a winner here; use the
   calling project's card evidence. This is a conservative project decision
   rule, not an accuracy claim for all loop shapes. Full-card extrapolation is
   outside the validated one-core use: use a qualified whole-card model.

   Before an authorized timed run, put a Model table in the ticket or research
   note: term, formula, counted inputs, source, scope, value, assumptions; then
   `T_lb`, `T_pred`, existing `T_meas`, uncertainty and the proposed change.
   Distinguish core cycles, TSC ticks and seconds. Show the region's Amdahl cap
   using its measured share; leave whole-program gain unknown if share is unknown.

3. **Choose the dominant term.** Compare measured time with prediction and
   bound. A large measured residual calls for a specific missing cost, such as
   address dependence, translation, wasted lines, scalar/vector transfers or
   imbalance. A large prediction-to-bound gap suggests insufficient overlap.
   A result below the bound calls for an accounting audit. Do not call every
   low-GB/s loop bandwidth-bound. R02 p.159; R08 slides 23,28; R19 pp.356-360.

4. **Apply the practices for that term.** Read only the matching rows in
   [practices](references/practices.md). Start with the smallest legal change
   supported by evidence. The order below is a decision order, not a mandate
   to try every item.

   - Issue or compute: inspect vectorization and alias/alignment legality;
     remove redundant control/copies; keep recurrences in registers; expose
     independent work; then consider limited unrolling. Count new spills.
   - Memory bytes: improve reuse and occupied-line density; make the innermost
     traversal contiguous; consider eligible streaming stores for cold output;
     then tune the measured delivery gap. Never remove completion ordering.
   - Memory latency or insufficient overlap: confirm page backing and placement;
     adjust prefetch to actual streams and sibling density; evaluate huge pages
     only where translation matters. A compiler hint does not create workers.
   - Gather/scatter: inspect completion and fault safety; improve layout or lane
     assignment where legal; then consider indirect prefetch. Price scatter
     separately. Do not assume a hint opcode provides asynchronous progress.
   - Parallel span: remove avoidable serialization, enlarge useful regions,
     address load imbalance and false sharing, then tune placement/density and
     the actual runtime's wait policy. Keep required dependencies and barriers.
   - Transfers: preserve resident data and reuse registered buffers; batch work
     and measure completed transfers; consider overlap only within the caller's
     allowed transport and scheduling rules. End-to-end time decides offload.

   Review [pitfalls](references/pitfalls.md) before changing arithmetic, memory
   ordering or runtime policy. Preserve FP order, precision, rounding, exceptions,
   errno and memory safety required by the program. Neither an ICC default nor
   a faster benchmark authorizes a weaker numerical contract.

5. **Verify on the card under the caller's rules.** First check correctness and
   the actual emitted code. Reuse applicable native results; stage missing work
   for the project's designated operator when engineers cannot launch jobs.
   Compare the same useful work, input, placement, backing, compiler and timing
   boundary. Include final completion. Use the project's repetition/noise policy;
   retain spread and drift rather than just the fastest sample. Record predicted
   versus measured effect, negative results and any remaining unsupported forms.
   Host checks and simulator results are not native passes. See the
   [worked example](references/example.md) for an analysis using existing data.

6. **Stop when further tuning is not justified.** Stop when a credible applicable
   bound is reached within the stated uncertainty, when less than 5% potential
   end-to-end gain remains, or when the candidate's change is within measured
   noise. The 5% rule is this skill's task policy, not an Intel hardware fact.
   Also stop at the caller's budget. A conditional empirical roof alone does
   not prove a hardware limit. Report the unresolved term and retain the last
   validated configuration. A larger gain may require changing the algorithm
   or reducing bytes/work, under a new explicit scope.

## Installation

Run `sh scripts/install.sh` from the skill folder, or pass the script's absolute
path to `sh` from any directory. It copies this folder into
`~/.claude/skills/knc-optimize/`; it does not execute the tuning workflow.
It refuses to overwrite an existing installation.
For a staged installation, set `KNC_SKILL_INSTALL_ROOT` to another skills
directory. The user's default installation is then untouched.
