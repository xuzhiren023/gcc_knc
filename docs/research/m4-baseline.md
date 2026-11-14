# M4 development baseline: S11-15

## Review summary

The qualified serial ranking below estimates CPU exposure, not measured
removal. Estimated seconds are `A = primary KNC median * (sampled user CPU /
sampled launch wall) * PC share`; the final column assumes a **hypothetical
1.20x local speedup**, giving `A / 6` removable seconds. System, off-CPU and
unsampled boundary time receive no gain. Proven removable time is **0 s**.

| Rank | Disjoint region | Estimated CPU exposure, s | Conditional removal, s |
| --- | --- | --- | --- |
| 1 | NPB-EP scalar transform/call site | 51.174 | 8.529 |
| 2 | NPB-EP log wrapper/internal path | 36.794 | 6.132 |
| 3 | NPB-CG indexed reduction | 24.547 | 4.091 |
| 4 | PB-ludcmp initialization | 10.985 | 1.831 |
| 5 | NPB-EP random generation | 8.402 | 1.400 |
| 6 | PB-ludcmp factorization reductions | 6.849 | 1.142 |
| 7 | NPB-IS random generator | 5.169 | 0.862 |
| 8 | STREAM vector loops | 4.289 | 0.715 |
| 9 | NPB-IS rank bucket loop | 4.197 | 0.699 |
| 10 | STREAM libc copy helper | 2.823 | 0.470 |
| 11 | NPB-CG sparse setup search | 2.046 | 0.341 |
| 12 | PB-gemm vector inner loop | 0.719 | 0.120 |

Exclusions: NPB-MG serial remains pending S11-27; OpenMP profiles fail sample
cadence qualification, and cholesky fails overhead qualification. Low-count
profiles also receive no numerical gain. HPCG now has S11-28 equal-work
results: GCC-KNC is about 1.8% slower across six serial pairs (two per
profile), superseding the duration-based proxy. It still has no qualified
profile and stays outside the removable-seconds sum. SQLite's donor uses
the documented -O3 exception, so its comparison is not at equal flags.

At most three Sprint 12 proof candidates, in priority order:

1. Strict scalar FP conversions and call boundaries: EP transform/log plus
   IS randlc, 93.137 s exposure; separate math from transfers before claiming
   any compiler-removable cost.
2. Indexed-load scheduling with strict sparse reduction: CG, 24.547 s
   exposure; preserve index and accumulation order.
3. Dependency-preserving scalar updates and locality: ludcmp initialization,
   10.985 s exposure; retain setup work and per-element arithmetic order.

These disjoint candidates imply only a conditional 11.70-21.44 s removal
at local gains of 1.10-1.20x. They are bounded proof proposals, not forecast
gains or an aggregate performance vote; correctness and paired A/B evidence
must precede implementation selection. Detailed constraints and allowances
appear under "Planning estimates and removable-time ranking" below.

## Evidence status

The lead completed the S11-18 pilot at 2026-11-13 19:47Z. This report uses
`.work/_shared/S11-18/raw-results.jsonl`, the collector's `results.jsonl`,
and development HPCG stdout captures. There are 414 development launches:
252 primary and 162 GCC-KNC OpenMP. The lead's 468-launch total includes sealed
programs; their data was not opened and is not included here.

The 2026-11-13 14:47 EST profiling attempt failed because the card has no
`perf` executable. Its log is
`.work/_state/logs/S11_15_profile_cpu-20261113-144706.log`.
The replacement SIGPROF pilot completed on the card; host attribution is now
available from `.work/_state/logs/S11_15_profile_sigprof-20261113-150906.log`.
It identifies PB-gemm's vector inner loop as the dominant sampled region.
Capture, overhead and CPU-accounting gates pass. The lead's 2026-11-14 00:23
decision accepts the sysroot libc naming and bounded CPU-share estimates;
these are not measured wall-time fractions. The development batch is now
attributed. The ranking below uses qualified serial CPU estimates and clearly
marked local-speedup scenarios. OpenMP delivery loses 96.5-97.5% of the nominal
sample cadence and cannot supply qualified wait seconds. Donor and restricted-
profile sampling were waived by the lead; paired primary timings retain those
comparisons. The S11-28 fixed-work HPCG pilot now replaces its primary proxy;
serial MG remains excluded.

## Completed batch and scope decisions

The lead ran nine serial plain/sample pairs on 2026-11-14, 01:07-01:32 EST,
then serial zlib/SQLite and five OpenMP pairs at 01:57-02:02 EST. All **32
planned non-HPCG launches passed** their existing collector and perturbation
checks, including complete PolyBench live-outs. This does not mean every
profile qualifies. The first batch's serial HPCG plain launch hit the 600 s
cap; the lead attributes this to its requested-duration workload taking
10-14 minutes including setup, not a workload fault. HPCG was then omitted
from both profiling panels, as authorized. No failed duration enters a table.

Evidence is in `.work/_shared/S11-15/batch-capture/` and:

- `.work/_state/logs/S11_15_profile_batch-20261114-010719.log`
- `.work/_state/logs/S11_15_profile_remaining-20261114-015727.log`
- Final host attribution: `.work/_state/logs/S11_15_batch_attribution-20261114-021134.log`

The unchanged S11-18 GCC-KNC strict -O2 executables used their original inputs,
one plain and one sampled launch per build, 600 s cap, full 7120 allocation,
one selected CPU for serial and 60 workers for OpenMP. NPB-MG serial was not
opened; PB-gemm uses its completed six-sample pilot. No donor profiling,
held-out capture, corpus edit, compiler rebuild or engineer card job occurred.

The batch's separate `profile-batch.so` uses process-wide ITIMER_PROF at 10 ms,
atomic slot reservation and PC/TID records. Shutdown disables the timer,
closes admission and drains handlers. Its bounded four-million-record buffer
had no reported overflow. Buffer completeness does not measure lost signals.
The existing staging, lint and shell checks remain valid; they were not rerun.
`lead.ps1` remains the historical remaining-batch entry point, **not a request
to rerun**. The host script only reads the explicit development allowlist.

Per the lead's 00:23 decision, region CPU seconds are `PC share * user CPU`.
System time and `wall - user - system` remain unassigned for serial runs;
negative residuals are accounting-resolution uncertainty. Launcher minus
interior wall is separately unsampled. OpenMP unused capacity is
`wall * 60 - user - system`, not elapsed waiting time. No waiting fractions
are inferred from low utilization alone. The lead accepted libc naming
against the sysroot without a further card identity check. HPCG's S11-28
fixed-work rating supplies a primary comparison but, without a qualified
profile, contributes no removable seconds.

## Primary pilot observations

Each cell is **donor median / GCC-KNC median; median paired speedup [min, max]**.
Durations are seconds, except HPCG, which reports S11-28's valid GFLOP/s rating
for equal work from its existing stdout. For latency, speedup is
`donor_seconds / knc_seconds`; for HPCG it is `knc_GFLOPs / donor_GFLOPs`.
A value above one favors GCC-KNC. The paired median need not equal the ratio
of the two marginal medians. Ranges cover the three observed pairs, not a
confidence interval. Pair order was AB, BA, AB. HPCG instead has two pairs
per profile (AB, BA), six across all profiles, from S11-28. These are pilot observations,
not ADR-0015's six-pair gate, a regression decision, or a 17-program aggregate.

Serial builds use donor `-O2` and GCC-KNC `-O2 -march=knc`. SQLite is explicitly
the authorized exception: donor `-O2` failed assembly with an operand-size
mismatch for `kmov`; the recorded fallback uses **donor -O3 versus KNC -O2**.
It must not be described as a strict -O2 comparison or as an optimization win
at equal flags. Original diagnostics remain in S11-18 build records.

The full 7120 profile grants 60 compute cores; the 3100/5100 profiles grant
56/59. Primary launches pin one worker. Restricted profiles are measurements
on the same 7120 with resource restrictions, not on physical 3100/5100 cards;
clock speed is not emulated. Keep profile observations separate.

| Program | 7120 | 3100 | 5100 |
| --- | --- | --- | --- |
| PB-gemm | 2.4082 / 0.89267; **2.698x** [2.661, 2.727] | 2.4089 / 0.89629; **2.688x** [2.679, 2.701] | 2.4157 / 0.8894; **2.717x** [2.699, 2.723] |
| PB-atax | 1.435 / 0.93928; **1.528x** [1.527, 1.528] | 1.4354 / 0.93933; **1.527x** [1.489, 1.528] | 1.4347 / 0.93988; **1.526x** [1.522, 1.530] |
| PB-cholesky | 43.783 / 11.29; **3.925x** [3.858, 3.926] | 42.865 / 11.175; **3.910x** [3.616, 3.952] | 43.064 / 11.516; **3.740x** [3.433, 3.836] |
| PB-ludcmp | 54.968 / 18.15; **3.028x** [2.979, 3.084] | 55.253 / 18.366; **3.002x** [3.000, 3.098] | 54.733 / 18.137; **2.979x** [2.866, 3.381] |
| PB-jacobi-2d | 1.5478 / 0.69857; **2.205x** [2.203, 2.226] | 1.548 / 0.69802; **2.220x** [2.217, 2.230] | 1.5505 / 0.69552; **2.228x** [2.227, 2.229] |
| PB-heat-3d | 1.1399 / 0.51108; **2.238x** [2.230, 2.248] | 1.1411 / 0.50484; **2.259x** [2.256, 2.268] | 1.1378 / 0.50343; **2.263x** [2.259, 2.268] |
| STREAM | 24.573 / 7.9535; **3.090x** [3.088, 3.093] | 24.562 / 7.9448; **3.091x** [3.091, 3.092] | 24.56 / 7.948; **3.091x** [3.088, 3.095] |
| NPB-CG | 79.052 / 29.224; **2.716x** [2.505, 2.872] | 91.696 / 29.355; **3.108x** [2.603, 3.139] | 78.436 / 29.346; **2.689x** [2.315, 2.898] |
| NPB-EP | 106.69 / 97.394; **1.096x** [1.095, 1.096] | 106.68 / 97.41; **1.095x** [1.095, 1.096] | 106.68 / 97.372; **1.096x** [1.095, 1.096] |
| NPB-MG | Excluded: 3/6 failed; S11-27 | Excluded: 3/6 failed; S11-27 | Excluded: 3/6 failed; S11-27 |
| NPB-IS | 13.241 / 11.997; **1.104x** [1.104, 1.105] | 13.246 / 12.007; **1.105x** [1.102, 1.106] | 13.238 / 11.995; **1.104x** [1.104, 1.105] |
| HPCG (S11-28 fixed work) | 0.086248 / 0.084613; **0.981x** [0.980, 0.982] | 0.086140 / 0.084593; **0.982x** [0.980, 0.984] | 0.086185 / 0.084722; **0.983x** [0.983, 0.983] |
| zlib | 1.3176 / 1.251; **1.054x** [1.049, 1.055] | 1.3158 / 1.259; **1.051x** [1.042, 1.077] | 1.3191 / 1.2523; **1.053x** [1.050, 1.055] |
| SQLite | 1.8412 / 1.7585; **1.038x** [1.030, 1.051] | 1.8328 / 1.7483; **1.048x** [1.037, 1.059] | 1.8327 / 1.7625; **1.048x** [1.032, 1.049] |

The collector reports passes for every primary pair other than NPB-MG.
NPB-MG's nine GCC-KNC serial launches fail verification; all its primary speed
numbers are withheld pending S11-27. The report preserves existing collector
checks, including PolyBench's complete live-out comparison against the donor.
That comparison is not an independent high-precision oracle; the harness's
independent-reference follow-up remains a gate prerequisite.

HPCG now uses `.work/_shared/S11-28/results.jsonl` and its referenced stdout,
with input `104x104x104`, requested time `rt=0`, and equal work in all six
serial pairs: one set, 50 reference iterations and 51 optimized iterations.
All 12 serial launches pass the collector. The reported metric is the valid
GFLOP/s rating including convergence and optimization overhead, not the
historical 2.4 rating or launch-to-exit latency. GCC-KNC ranges from
0.084495 to 0.084728 GFLOP/s versus donor 0.086065 to 0.086263; the median
paired ratio across the six pairs is 0.98263x, about 1.8% slower. The table
keeps profiles separate; two pairs per profile do not establish a six-pair
gate for any one profile. This replaces the requested-duration primary proxy.
No HPCG removable wall seconds are inferred from the throughput ratio.

Cholesky and CG show substantial across-pair spread, and ludcmp's 5100 range
is also broad. Three pairs cannot establish causes or statistical significance.
The comparisons describe existing compilers; they do not validate the review's
prospective gains from future GCC-KNC work.

## OpenMP side panel

HPCG rows in this historical S11-18 panel retain the duration-based proxy;
they are not S11-28 fixed-work results or qualified profiling evidence.

**The donor toolchain has no OpenMP runtime.** These are GCC-KNC-only
`-O2 -march=knc -fopenmp` observations, with one, two or four threads per
compute core. Values are median [min, max] seconds across three launches,
except HPCG's historical GFLOP/s rating. No donor speedup or primary vote is
assigned. All 12 HPCG launches at two/four threads per core in restricted
profiles fail (the lead diagnoses `bad_alloc`; for example capture/340.stderr).
Their short failure durations are excluded. The other 150 OpenMP launches
pass the existing collector checks. The returned wait/compute sample split is
reported below; its cadence failure prevents a quantitative wait-time claim.

| Program | Profile | Threads | GCC-KNC median [min, max] | Status |
| --- | --- | --- | --- | --- |
| HPCG | 3100 | 56 | 0.12367 [0.12215, 0.1247] | 3/3 collector pass |
| HPCG | 3100 | 112 | Excluded | 3/3 failed |
| HPCG | 3100 | 224 | Excluded | 3/3 failed |
| HPCG | 5100 | 59 | 0.12346 [0.12109, 0.12423] | 3/3 collector pass |
| HPCG | 5100 | 118 | Excluded | 3/3 failed |
| HPCG | 5100 | 236 | Excluded | 3/3 failed |
| HPCG | 7120 | 60 | 0.12422 [0.12203, 0.12785] | 3/3 collector pass |
| HPCG | 7120 | 120 | 0.12145 [0.12135, 0.12198] | 3/3 collector pass |
| HPCG | 7120 | 240 | 0.12234 [0.12025, 0.12326] | 3/3 collector pass |
| NPB-CG | 3100 | 56 | 0.88275 [0.86199, 0.88799] | 3/3 collector pass |
| NPB-CG | 3100 | 112 | 0.67117 [0.64851, 0.67819] | 3/3 collector pass |
| NPB-CG | 3100 | 224 | 0.71305 [0.67352, 0.71406] | 3/3 collector pass |
| NPB-CG | 5100 | 59 | 0.85598 [0.85186, 0.86738] | 3/3 collector pass |
| NPB-CG | 5100 | 118 | 0.67525 [0.63662, 0.67529] | 3/3 collector pass |
| NPB-CG | 5100 | 236 | 0.68018 [0.65788, 0.68184] | 3/3 collector pass |
| NPB-CG | 7120 | 60 | 0.8587 [0.85127, 0.86163] | 3/3 collector pass |
| NPB-CG | 7120 | 120 | 0.6606 [0.65693, 0.66479] | 3/3 collector pass |
| NPB-CG | 7120 | 240 | 0.72908 [0.7138, 0.74265] | 3/3 collector pass |
| NPB-EP | 3100 | 56 | 2.1309 [2.1171, 2.1846] | 3/3 collector pass |
| NPB-EP | 3100 | 112 | 1.9599 [1.8078, 1.9699] | 3/3 collector pass |
| NPB-EP | 3100 | 224 | 2.1073 [2.0829, 2.1585] | 3/3 collector pass |
| NPB-EP | 5100 | 59 | 2.0278 [2.0163, 2.0422] | 3/3 collector pass |
| NPB-EP | 5100 | 118 | 1.9626 [1.9012, 1.9699] | 3/3 collector pass |
| NPB-EP | 5100 | 236 | 2.1706 [2.0528, 2.1772] | 3/3 collector pass |
| NPB-EP | 7120 | 60 | 1.9867 [1.9489, 1.9965] | 3/3 collector pass |
| NPB-EP | 7120 | 120 | 1.9324 [1.8979, 1.9619] | 3/3 collector pass |
| NPB-EP | 7120 | 240 | 2.1559 [2.0871, 2.1588] | 3/3 collector pass |
| NPB-IS | 3100 | 56 | 0.36729 [0.35752, 0.37811] | 3/3 collector pass |
| NPB-IS | 3100 | 112 | 0.39403 [0.38224, 0.40072] | 3/3 collector pass |
| NPB-IS | 3100 | 224 | 0.54998 [0.54545, 0.55119] | 3/3 collector pass |
| NPB-IS | 5100 | 59 | 0.35782 [0.35706, 0.36299] | 3/3 collector pass |
| NPB-IS | 5100 | 118 | 0.40426 [0.40012, 0.40559] | 3/3 collector pass |
| NPB-IS | 5100 | 236 | 0.56783 [0.56667, 0.5731] | 3/3 collector pass |
| NPB-IS | 7120 | 60 | 0.36715 [0.36482, 0.37146] | 3/3 collector pass |
| NPB-IS | 7120 | 120 | 0.39792 [0.39456, 0.40585] | 3/3 collector pass |
| NPB-IS | 7120 | 240 | 0.57266 [0.56024, 0.57414] | 3/3 collector pass |
| NPB-MG | 3100 | 56 | 0.50502 [0.49425, 0.50752] | 3/3 collector pass |
| NPB-MG | 3100 | 112 | 0.52372 [0.51551, 0.52889] | 3/3 collector pass |
| NPB-MG | 3100 | 224 | 0.57772 [0.56642, 0.59014] | 3/3 collector pass |
| NPB-MG | 5100 | 59 | 0.50033 [0.47942, 0.53506] | 3/3 collector pass |
| NPB-MG | 5100 | 118 | 0.51764 [0.50939, 0.52639] | 3/3 collector pass |
| NPB-MG | 5100 | 236 | 0.58859 [0.55568, 0.59927] | 3/3 collector pass |
| NPB-MG | 7120 | 60 | 0.50521 [0.49951, 0.52403] | 3/3 collector pass |
| NPB-MG | 7120 | 120 | 0.5002 [0.49449, 0.50833] | 3/3 collector pass |
| NPB-MG | 7120 | 240 | 0.58332 [0.56392, 0.58455] | 3/3 collector pass |
| STREAM | 3100 | 56 | 0.6379 [0.62817, 0.64052] | 3/3 collector pass |
| STREAM | 3100 | 112 | 0.64993 [0.64766, 0.65143] | 3/3 collector pass |
| STREAM | 3100 | 224 | 0.76313 [0.75218, 0.76581] | 3/3 collector pass |
| STREAM | 5100 | 59 | 0.62429 [0.62009, 0.62855] | 3/3 collector pass |
| STREAM | 5100 | 118 | 0.65269 [0.64654, 0.65375] | 3/3 collector pass |
| STREAM | 5100 | 236 | 0.7651 [0.76182, 0.76842] | 3/3 collector pass |
| STREAM | 7120 | 60 | 0.63023 [0.62978, 0.6322] | 3/3 collector pass |
| STREAM | 7120 | 120 | 0.65536 [0.65135, 0.66263] | 3/3 collector pass |
| STREAM | 7120 | 240 | 0.7662 [0.76449, 0.78548] | 3/3 collector pass |

## Replacement profiling-method pilot (completed history)

`tools/s11_15_profile.py` builds `profile-sigprof.so` with the installed
GCC-KNC prefix, lints it, checks its dynamic dependencies, and stages it under
`.work/_shared/S11-15/`. It reuses the unchanged, previously linted S11-18
strict -O2 serial PB-gemm executable and launcher. No GCC build, corpus source
edit, installation on the card, MPSS change or AutoFDO infrastructure is involved.

Only the sampled `gemm` process receives `LD_PRELOAD`. The library installs
an SA_SIGINFO handler and a 10,000 microsecond ITIMER_PROF interval, then records
the interrupted REG_RIP in a preallocated 20,000-PC buffer. The handler does no
allocation, symbol lookup or I/O. SIGPROF blocks itself while the handler runs.
The pilot is serial-only; this buffer and process timer do not qualify worker
coverage for OpenMP. Existing signal/timer use, setup failures, empty capture,
buffer overflow, missing maps or incomplete output are explicit blockers.

After disabling and blocking SIGPROF, the destructor emits constructor-to-
destructor CLOCK_MONOTONIC_RAW wall time, getrusage user/system time, PCs and
bounded `/proc/self/maps` text. ASLR-sensitive library addresses retain mappings.
A missing completion marker is a failure, including an ignored preload.
The original PB-gemm executable's symbol table and disassembly are staged as
`symbols.txt` and `gemm.asm`. Its `main` symbol is at `0x400940`, size `0xb96`;
there is no separate `kernel_gemm` symbol. Distinguish its loop ranges from
allocation, initialization and output. No source-line information is promised.

There are three AB/BA/AB pair blocks, each with two adjacent plain/sampled
pairs: 12 independent launches, six sampled. This extends the original
three-pair pilot only to meet its existing 300-sample minimum: measured
GCC-KNC PB-gemm takes about 0.89 seconds, so three runs at nominal 100 Hz
would supply fewer than 300 samples. The 600-second whole-job cap remains.
Each launch retains its block, repetition, mode, affinity and launcher timing.
Complete binary live-outs are compared across all 12 launches. Plain mode
has no preload; sampled latency includes loading, handling and dumping the
profile. This gives conservative end-to-end overhead, not interrupt cost alone.
Neither diagnostic latency replaces the primary pilot above.

Host staging command (completed; do not repeat unchanged work):

```powershell
python tools/run.py --name S11-15-sigprof-stage --inputs tools/s11_15_profile.py tools/corpus/profile-pilot.sh tools/corpus/profile-sigprof.c -- python tools/s11_15_profile.py
```

Lead-only card command, from this worktree:

```powershell
python tools/run.py --name S11-15-profile-sigprof -- powershell -NoProfile -File ..\_shared\S11-15\lead.ps1
```

From the main checkout:

```powershell
python tools/run.py --name S11-15-profile-sigprof -- powershell -NoProfile -File .work\_shared\S11-15\lead.ps1
```

The staged lead script calls `tools/card_run --benchmark --threads 240
--timeout 600 --file-list <absolute S11-15/files.txt>
<absolute S11-15/profile-pilot.sh>`. The launcher pins PB-gemm to one CPU.
This short diagnostic should finish well below one minute; it does not require
all-CPU parallelization. Return the wrapper log path through S11-15. All
PROFILE sections, launcher timings and affinity records are returned in that
log. No card job was started by the engineer.

## Original pilot qualification rules

These describe the completed serial pilot. The completed-batch scope above records
the lead's subsequent exceptions for libc naming and CPU-share estimates;
the old wall-share blocker is not a prerequisite for the new batch.

1. Require all 12 successful exits, matching affinity and complete live-outs,
   six sampler completion markers and no PROFILE_BLOCKED output. Keep each
   sampled launch separate; do not combine maps across ASLR instances.
2. Require at least 300 samples overall and samples in all six sampled launches,
   no buffer overflow, and at most 5% unattributed samples. Keep library and
   unknown PCs in the denominator. Map executable PCs against `symbols.txt`
   and `gemm.asm`; library PCs require the mapped module and load bias.
   Host `k1om-mpss-linux-addr2line -f -e gemm <PC...>` can identify functions,
   but unavailable source lines remain unknown. Do not label all main samples
   as GEMM or infer per-instruction wall time from disassembly.
3. Report all six adjacent `sample/plain - 1` overhead ratios, their median
   and range, plus each block's median. The original feasibility limits remain:
   median at most 5%, no individual ratio above 10%, and consistent hot-region
   ordering. Larger overhead or unstable ordering blocks expansion.
4. SIGPROF measures scheduled process CPU time, including kernel time, and
   observes the user PC at delivery. Timer rounding and standard-signal
   coalescing can bias it. It has no perf-style lost-record counter; never
   claim zero lost signals. Compare `sample_count * 0.010` with measured
   user+system CPU seconds for each launch; a discrepancy above 20% requires
   investigation and blocks attribution. Passing this sanity gate does not
   prove absence of bias. Report per-launch hot shares/ranges, not independent
   sample confidence intervals.
5. Report user/system CPU divided by the measured interior wall duration,
   and the difference between launcher wall time and interior wall time.
   Library loading, constructor/destructor ordering and output dumping lie
   partly outside the interior interval. System time, off-CPU time and
   unsampled boundaries stay separate. Non-negligible system time or an
   unexplained residual blocks interpreting a conditional PC share as a
   wall-time fraction. The serial pilot cannot establish OpenMP wait/compute.

Once native qualification succeeds, annotate hot ranges with vectorization
diagnostics, x87/vector bridges, address and FP spills, and byte size.
These are code properties until their time cost is measured. Further
per-program profiles and coverage checks are required before choosing themes.

## Returned pilot: attribution and qualification

The lead's successful capture contains all 12 launches, identical complete
live-outs, the same one-worker affinity (`cpus=1`, 60 cores, 240 granted CPUs),
six completion markers and no blocker or overflow. This is perturbation
checking, not a new independent correctness oracle. There are 521 samples.
The counts by launch are 87, 87, 87, 87, 86 and 87. The analysis ran on the
host; no additional card job or compiler build was performed.

| Block/repeat | Plain seconds | Sampled seconds | Overhead | User/interior wall | System/interior wall | Sample-clock deficit | Launcher minus interior |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1/1 | 0.906655 | 0.909943 | 0.363% | 97.892% | 1.112% | 2.247% | 10.991 ms |
| 1/2 | 0.898928 | 0.909115 | 1.133% | 95.779% | 3.341% | 2.247% | 11.218 ms |
| 2/1 | 0.891481 | 0.904835 | 1.498% | 97.413% | 2.239% | 2.247% | 11.731 ms |
| 2/2 | 0.898553 | 0.901651 | 0.345% | 97.698% | 2.246% | 2.247% | 11.151 ms |
| 3/1 | 0.906115 | 0.894623 | -1.268% | 96.197% | 3.395% | 2.273% | 11.018 ms |
| 3/2 | 0.900258 | 0.903486 | 0.359% | 96.384% | 2.241% | 1.136% | 11.222 ms |

Median paired overhead is **0.361%**, range **[-1.268%, 1.498%]**;
block medians are 0.748%, 0.921%, -0.455%. Thus the 5% median and 10%
individual limits pass. A negative observation reflects run variability,
not negative interrupt cost. `samples * 0.010 / (user + system) - 1`
is between -2.273% and -1.136%, within the 20% sanity limit. Signals can
still coalesce; this does not establish zero loss or unbiased sampling.

Each PC uses its own launch's executable map. ELF PT_LOAD offsets and virtual
addresses establish the load bias before host `addr2line -f -C` lookup.
The executable has symbols but no available source lines. `addr2line` alone
leaves 57 PCs unnamed (10.940%): 55 in libc and two PLT entries. Exact
containment in sized dynamic text symbols from `nm -D -S` names the 55 libc
PCs in the sysroot's `libc-2.21.so`; the staged disassembly identifies the two
exact PLT entry addresses. No nearest-symbol interpolation is used.

The card reports glibc 2.21
and maps `/lib64/libc-2.21.so`; the local ELF has that version/name and compatible
executable segment extent. The lead accepted these checks on 2026-11-14;
the libc rows are named against sysroot libc. There are 0/521 unnamed PCs
under that accepted convention. The 55 libc PCs (10.557%) no longer block
qualification. The main-executable hot-region result is independent of
library naming.

| Region/function | Samples | Pooled conditional PC share | Per-launch share range |
| --- | --- | --- | --- |
| main: vector GEMM inner loop | 439 | 84.261% | 82.56-86.21% |
| libc strcmp | 17 | 3.263% | 0.00-6.90% |
| libc _IO_fwrite/fwrite | 15 | 2.879% | 1.15-5.75% |
| corpus_fprintf | 13 | 2.495% | 1.15-5.75% |
| libc memcpy | 11 | 2.111% | 0.00-3.45% |
| main: GEMM setup/outer/scalar path | 8 | 1.536% | 0.00-2.33% |
| libc __write/write | 6 | 1.152% | 0.00-2.30% |
| libc _IO_file_xsputn | 5 | 0.960% | 0.00-1.16% |
| main: live-out emission | 4 | 0.768% | 0.00-2.30% |
| strcmp@plt, fwrite@plt, libc munmap | 1 each | 0.192% each | 0.00-1.16% each |

The vector loop ranks first in every launch. The small functions below it
change order and are not stably ranked. Counts describe interrupted PCs;
there is no call stack to assign every library sample to a caller. Library
and unknown PCs remain in the denominator. Six launches support a descriptive
range, not an independent-sample confidence interval.

The user+system accounting falls 0.056-1.375% below interior wall time;
timer/accounting resolution and unscheduled time are not separated. System
time itself is 1.112-3.395% of interior wall time. SIGPROF can attribute a
kernel interval to its user return PC. The further 10.991-11.731 ms outside
the interior includes launch, loading and sampler output, with no measured
split. Consequently **84.261% is not an established wall-time fraction**.
Per the lead's updated rule, use each run's loop share times its user CPU
seconds as an estimate; keep system, residual and boundary time unassigned.
This supplies bounded CPU evidence for ranking without claiming that every
second in the vector loop can be removed.

### Code properties at the sampled PB-gemm region

The vector inner loop occupies `[0x401320, 0x40135f)`, **63 bytes**,
inside the 2,966-byte `main`. Its observed code loads C and B through paired
unpack loads, performs `vfmadd231pd`, and writes C through paired pack stores,
advancing 64 bytes per iteration. It has no stack references or calls.
Thus no address or FP spill is visible inside this loop. This is observed
vectorized code; optimization-decision diagnostics were not captured for
this frozen executable and have not been reconstructed with a new build.

The enclosing path contains runtime alias checks, an x87 scalar fallback at
`[0x401440, 0x40145a)`, and an x87-to-vector bridge at
`[0x4012fe, 0x40130f)`: multiply, store a double at `-0x48(%rbp)`, then
broadcast it. That stack transfer is outside the vector inner loop, once
per enclosing k iteration on this path; it is not a measured inner-loop spill
cost. The vectorized C-scaling loop is `[0x401290, 0x4012b9)`.
Initialization precedes this kernel; output calls follow it. The 8 samples
in the combined setup/outer/scalar category cannot isolate bridge cost or
prove that the fallback ran. Likewise, the 300 PCs at the load address
`0x40132f` do not establish memory stalls, bandwidth saturation or a profitable
prefetch change: delivery bias and neighboring execution remain possible.

## Returned batch: attribution and qualification

Each PC uses its own launch's executable mapping and ELF PT_LOAD load bias.
The executable and staged runtime DSOs come from that build's frozen file
list; system libraries use the matching mapped path in the toolchain sysroot.
**Libc rows are named against sysroot libc.** No new identity claim is made.
Source-line debug information is unavailable; symbols and inspected code
ranges supply the attribution. Unsampled functions are not declared cold.

Sized symbols alone miss internal helpers. The final analysis verifies the
explicit `memcpy` call at sysroot offset `0x7f5e8` to `0x7f600`, then names
PCs in the inspected aligned-copy helper `[0x7f600,0x7f734)`. Likewise,
libm `log` jumps at `0xc156` to the x87 helper `[0x8090,0x80fc)`; that
helper is labelled by the traced branch, not objdump's misleading nearest
`__lgamma_r_finite` name. Libm attribution is conditional on the mapped
2.21 library matching this sysroot code. EP's `0x400a90` is the exact
`log@plt` entry. No nearest-symbol extrapolation is used. Other unknowns
stay in the denominator (zlib 1/121; SQLite 12/173). SQLite's remaining
libc PCs are not silently reclassified by the lead's naming exception.

### Serial capture quality

One plain/sample pair per build cannot establish a median overhead or
run-to-run stability. The pilot's per-run 10% overhead and 20% cadence limits
are used here; fewer than 300 PCs is a low-count limitation. A negative
overhead is variation, not negative sampler cost. All serial runs observed
one TID; none reported overflow. Cadence is `100*(N*.010/(U+S)-1)`.

| Program | Plain / sample s | PCs | Overhead % | Cadence error % | Interpretation |
| --- | --- | --- | --- | --- | --- |
| STREAM | 7.963383 / 8.018154 | 797 | 0.69 | -0.25 | Pass these checks; single sample launch |
| PB-atax | 0.939344 / 0.956512 | 93 | 1.83 | -1.06 | fewer than 300 PCs |
| PB-cholesky | 10.458517 / 12.481861 | 1244 | 19.35 | -0.16 | overhead |
| PB-heat-3d | 0.510553 / 0.518388 | 49 | 1.53 | -3.92 | fewer than 300 PCs |
| PB-jacobi-2d | 0.703100 / 0.712763 | 68 | 1.37 | -2.86 | fewer than 300 PCs |
| PB-ludcmp | 18.295150 / 17.616010 | 1756 | -3.71 | -0.17 | Pass these checks; single sample launch |
| NPB-CG | 29.278496 / 29.816683 | 2976 | 1.84 | -0.07 | Pass these checks; single sample launch |
| NPB-EP | 97.404273 / 98.081339 | 9798 | 0.70 | -0.02 | Pass these checks; single sample launch |
| NPB-IS | 11.998320 / 12.051705 | 1201 | 0.44 | -0.17 | Pass these checks; single sample launch |
| zlib | 1.245582 / 1.262175 | 121 | 1.33 | -2.42 | fewer than 300 PCs |
| SQLite | 1.754100 / 1.763001 | 173 | 0.51 | -1.14 | unknown PCs, fewer than 300 PCs |

Cholesky's +19.35% observed overhead fails the limit. Its dominant location
is still described, but its seconds are withheld from the qualified ranking.
This does not distinguish profiler perturbation from the existing timing
variability. No automatic retry was authorized. Atax, both stencils, zlib
and SQLite remain descriptive low-count profiles; SQLite also exceeds the
5% function-unknown threshold. They do not enter the qualified sum.

| Program | Interior wall s | User s | System s (unassigned) | Signed wall-U-S s | Unsampled boundary s |
| --- | --- | --- | --- | --- | --- |
| STREAM | 7.993571 | 7.850 | 0.140 | +0.003571 | 0.024583 |
| PB-atax | 0.945022 | 0.860 | 0.080 | +0.005022 | 0.011490 |
| PB-cholesky | 12.462380 | 12.440 | 0.020 | +0.002380 | 0.019481 |
| PB-heat-3d | 0.506034 | 0.500 | 0.010 | -0.003966 | 0.012354 |
| PB-jacobi-2d | 0.701587 | 0.690 | 0.010 | +0.001587 | 0.011176 |
| PB-ludcmp | 17.593218 | 17.580 | 0.010 | +0.003218 | 0.022791 |
| NPB-CG | 29.779208 | 29.730 | 0.050 | -0.000792 | 0.037476 |
| NPB-EP | 97.999557 | 97.990 | 0.010 | -0.000443 | 0.081782 |
| NPB-IS | 12.030315 | 11.970 | 0.060 | +0.000315 | 0.021390 |
| zlib | 1.250411 | 1.180 | 0.060 | +0.010411 | 0.011764 |
| SQLite | 1.750312 | 1.730 | 0.020 | +0.000312 | 0.012689 |

The small negative residuals for heat-3d, CG and EP are retained, not turned
into precise off-CPU estimates. Serial off-CPU estimates are the positive
part of this column. SIGPROF can deliver a kernel interval at a user return
PC, so even a named region's CPU estimate is approximate. Tables never
interpret delivered PCs as measured wall fractions or independent samples.

### Hot functions and inspected regions

Percentages include all delivered PCs, including runtime, setup, correctness
output and unknowns. Function seconds below are `U * share`, exclusive of
callees. The tables show leading functions, not every function. The JSON
retains the complete attribution. Whole-function byte sizes are static code
extents, not a measured instruction-cache footprint.

| Program | Leading functions: PC share; estimated CPU seconds | Largest listed executable function bytes |
| --- | --- | --- |
| STREAM | main 57.84%; 4.541 s; libc-2.21.so: memcpy aligned helper 36.26%; 2.846 s; checkSTREAMresults 3.76%; 0.295 s | main: 1776 |
| PB-atax | main 98.92%; 0.851 s; corpus_fprintf 1.08%; 0.009 s | main: 1820 |
| PB-cholesky | main 99.52%; 12.380 s; libc-2.21.so: memcpy 0.24%; 0.030 s; libc-2.21.so: strcmp 0.16%; 0.020 s | main: 1629 |
| PB-heat-3d | main 73.47%; 0.367 s; libc-2.21.so: strcmp 10.20%; 0.051 s; libc-2.21.so: memcpy 8.16%; 0.041 s | main: 2940 |
| PB-jacobi-2d | main 82.35%; 0.568 s; corpus_fprintf 7.35%; 0.051 s; libc-2.21.so: _IO_fwrite/fwrite 4.41%; 0.030 s | main: 3659 |
| PB-ludcmp | main 99.94%; 17.570 s; libc-2.21.so: munmap 0.06%; 0.010 s | main: 5713 |
| NPB-CG | conj_grad_ 88.98%; 26.453 s; sparse_ 10.55%; 3.137 s; libc-2.21.so: memcpy aligned helper 0.17%; 0.050 s | conj_grad_: 9162 |
| NPB-EP | MAIN__ 53.18%; 52.115 s; libm-2.21.so: log internal x87 path 31.84%; 31.203 s; vranlc_ 8.64%; 8.471 s | MAIN__: 3225 |
| NPB-IS | rank 47.04%; 5.631 s; randlc 43.38%; 5.193 s; create_seq 6.33%; 0.757 s | rank: 1797 |
| zlib | deflate_slow 33.88%; 0.400 s; slide_hash 17.36%; 0.205 s; inflate_fast 11.57%; 0.137 s | deflate_slow: 1537 |
| SQLite | sqlite3VdbeExec 29.48%; 0.510 s; libc-2.21.so: ?? 6.94%; 0.120 s; vdbeSorterCompareInt 6.36%; 0.110 s | sqlite3VdbeExec: 43271 |

These inspected ranges are disjoint within a program. Bytes span the stated
half-open address range. A range may contain a call; its PC count excludes
callee execution. Candidate backedge envelopes in the machine-readable
output can overlap or include non-loop paths and are never summed. The
following ranges were manually checked against disassembly; source-level
setup identification additionally uses the authorized PolyBench sources.

| Program / region | Address range | Bytes | PCs / total (%) | Estimated CPU s |
| --- | --- | --- | --- | --- |
| STREAM / scale | `0x400960..0x400996` | 54 | 91/797 (11.42%) | 0.896 |
| STREAM / add | `0x400a00..0x400a4a` | 74 | 165/797 (20.70%) | 1.625 |
| STREAM / triad | `0x400ac0..0x400b0a` | 74 | 183/797 (22.96%) | 1.802 |
| PB-atax / matrix initialization | `0x400be0..0x400c9c` | 188 | 72/93 (77.42%) | 0.666 |
| PB-atax / strict reduction | `0x400d30..0x400da7` | 119 | 15/93 (16.13%) | 0.139 |
| PB-atax / vector update | `0x400e00..0x400e56` | 86 | 5/93 (5.38%) | 0.046 |
| PB-cholesky / matrix initialization | `0x400b50..0x400c5a` | 266 | 1199/1244 (96.38%) | 11.990 |
| PB-cholesky / factorization reduction | `0x400eb0..0x400ec5` | 21 | 37/1244 (2.97%) | 0.370 |
| PB-heat-3d / stencil A | `0x400c20..0x400ce4` | 196 | 13/49 (26.53%) | 0.133 |
| PB-heat-3d / stencil B | `0x400fc0..0x401084` | 196 | 18/49 (36.73%) | 0.184 |
| PB-jacobi-2d / unrolled stencil A | `0x400ba0..0x400f1d` | 893 | 29/68 (42.65%) | 0.294 |
| PB-jacobi-2d / unrolled stencil B | `0x4010b0..0x40142d` | 893 | 26/68 (38.24%) | 0.264 |
| PB-ludcmp / matrix initialization | `0x400c80..0x400d8c` | 268 | 1065/1756 (60.65%) | 10.662 |
| PB-ludcmp / factorization reduction A | `0x400fc0..0x4010b7` | 247 | 342/1756 (19.48%) | 3.424 |
| PB-ludcmp / factorization reduction B | `0x4011e0..0x4012da` | 250 | 322/1756 (18.34%) | 3.224 |
| NPB-CG / indexed reduction | `0x402480..0x402499` | 25 | 2507/2976 (84.24%) | 25.045 |
| NPB-CG / sparse setup search | `0x403e90..0x403eae` | 30 | 209/2976 (7.02%) | 2.088 |
| NPB-EP / scalar transform/call site | `0x4010ff..0x40122f` | 304 | 5153/9798 (52.59%) | 51.535 |
| NPB-EP / random generation loop | `0x402510..0x4025eb` | 219 | 846/9798 (8.63%) | 8.461 |
| NPB-IS / random generator function | `0x400ec0..0x400ffc` | 316 | 521/1201 (43.38%) | 5.193 |
| NPB-IS / rank bucket loop | `0x401743..0x4019bd` | 634 | 423/1201 (35.22%) | 4.216 |
| zlib / slide hash loop A | `0x401d70..0x401d8b` | 27 | 5/121 (4.13%) | 0.049 |
| zlib / slide hash loop B | `0x401da0..0x401dbb` | 27 | 16/121 (13.22%) | 0.156 |
| SQLite / index search envelope | `0x481f60..0x481fb5` | 85 | 7/173 (4.05%) | 0.070 |

The two stencil ranges explain 63.27% of heat-3d PCs and 80.88% of jacobi-2d
PCs. Their output paths and libraries are real costs inside the frozen timing
boundary. Atax's largest region is matrix initialization, not its multiply
kernel. Cholesky and ludcmp construct their input matrix with a substantial
scalar product/update loop before factorization. Those costs cannot be
removed by changing benchmark inputs or timing boundaries.

### Vectorization, transfers, spills and code size

These are properties of the frozen generated code, not measured stall costs.
Original optimization-decision dumps were not captured. Observed scalar or
vector code is reported; a specific compiler rejection reason is unknown.
Stack references alone do not prove register spills: ABI transfers, saved
addresses and local variables are distinguished below. No positive spill
removal budget is inferred from instruction counts.

| Program | Observed code at the hot region; transfer/spill evidence |
| --- | --- |
| PB-gemm | 63-byte vector FMA loop, no stack reference or call; outer x87/store/broadcast bridge described in the pilot above. |
| PB-atax | 188-byte initialization loop uses x87 divides and stack integer-to-FP conversions at `-0x3c(%rbp)`. The 119-byte strict reduction stays x87; the 86-byte update is vector FMA. An x87 result is stored to the program array and broadcast for the update. Neither compute loop has stack spills; conversion traffic is outside them. |
| PB-cholesky | 266-byte initialization inner loop is unrolled scalar x87, with many address calculations and prefetches; no stack access inside it. Outer counters/pointers use stack slots. Factorization remains scalar, including divide/sqrt; overhead failure bars a cost estimate. |
| PB-ludcmp | 268-byte initialization loop and 247/250-byte factorization reductions use x87 and indexed/strided loads with prefetches. No stack access in these selected inner loops; address/counter save/reload traffic appears around them, e.g. `0x400fb1..0x400fb8` and `0x4010b7`. No vector bridge in the selected loops. |
| PB-jacobi-2d | Two 893-byte unrolled loops use unpack loads, vector adds/multiply and pack stores. The inspected inner bodies have no calls or stack accesses; no visible inner FP/address spills. Size alone does not establish instruction-cache stalls. |
| PB-heat-3d | Two 196-byte vector FMA stencil loops use unpack loads and pack stores, with no stack references/calls. Masked gather tails follow; their cost is not isolated by 49 PCs. |
| STREAM | Scale/add/triad loops are 54/74/74 bytes, vector arithmetic with prefetch and non-temporal stores, no inner-loop stack access. The aligned libc copy helper uses scalar loads/stores. Runtime copy PCs are separate from vector-loop PCs; caller stacks are unavailable. |
| NPB-CG | Dominant 25-byte loop performs indexed scalar x87 multiply/add in order, with no call or stack access. Address registers are loaded from stack outside the loop (`0x402450..0x402478`). Other paths include vector/gather code; its presence does not mean this hot reduction is vectorized. |
| NPB-EP | 304-byte transform region uses x87 divide/sqrt and calls log. It stores/broadcasts the argument at `0x40113b..0x401148`, preserves x87 values across the call in stack slots, then pack-stores/reloads the return at `0x40116c..0x401173`. The 108-byte internal log helper also bridges vector ABI to x87 and back; it uses x87 log instructions. Control-word conversion traffic follows. Bridge, math and spill costs overlap and are not isolated. |
| NPB-IS | 316-byte randlc uses x87 arithmetic and repeated control-word save/change/restore for integer conversions; return store/broadcast at `0x400f75..0x400f79`. The 634-byte rank bucket loop uses scalar indexed integer loads/stores and branches. RNG setup is inside primary latency. |
| zlib | 124-byte slide_hash contains two scalar 27-byte loops with narrow loads/stores and conditional updates, no stack access. deflate_slow is 1,537 bytes and branch/call-heavy; sampled function extent does not isolate its spills or branch-misprediction cost. |
| SQLite | sqlite3VdbeExec is 43,271 bytes with dispersed PCs; no single hot VM loop is established. The 85-byte sampled index-search envelope has an indirect comparator call and stack-held pointer arguments. This is address/call traffic, not evidence of a removable FP bridge. Spills across the large interpreter remain unquantified. |
| NPB-MG | Serial invalid and unprofiled under S11-27; no serial code-cost claim. OpenMP function locations are described below, without qualified time attribution. |
| HPCG | Both profiling panels omitted; S11-28 now supplies equal-work throughput, but no hot-code or spill evidence. |

### OpenMP: observed wait/compute, unqualified time attribution

All rows use 60 workers, one per compute core. Wait means named libgomp
spin/barrier/wait functions; compute means all other named PCs (including
setup, runtime and output), not just useful parallel arithmetic. Unknown
PCs stay separate. Here all wait PCs are `gomp_barrier_wait_end` or
`gomp_team_barrier_wait_end`; no other libgomp function received a PC.

| Program | PCs; observed TIDs / 60 (min-max PCs/TID) | Wait / compute / unknown PC % | Overhead % | Cadence error % |
| --- | --- | --- | --- | --- |
| STREAM | 97; 42/60 (1-7) | 56.70 / 43.30 / 0.00 | 7.47 | -97.03 |
| NPB-CG | 130; 46/60 (1-9) | 25.38 / 74.62 / 0.00 | 9.29 | -97.50 |
| NPB-EP | 416; 59/60 (1-22) | 19.23 / 80.77 / 0.00 | 3.78 | -96.50 |
| NPB-MG | 78; 43/60 (1-5) | 33.33 / 66.67 / 0.00 | 10.43 | -97.14 |
| NPB-IS | 54; 35/60 (1-3) | 18.52 / 81.48 / 0.00 | 6.19 | -97.05 |

| Program | Interior wall s | User / system CPU s | U/(wall*60) | Unused CPU-capacity s | Unsampled boundary s |
| --- | --- | --- | --- | --- | --- |
| STREAM | 0.634391 | 31.91 / 0.74 | 83.83% | 5.413 | 0.054062 |
| NPB-CG | 0.888459 | 51.80 / 0.12 | 97.17% | 1.388 | 0.053228 |
| NPB-EP | 2.053061 | 118.65 / 0.11 | 96.32% | 4.424 | 0.079267 |
| NPB-MG | 0.497407 | 26.68 / 0.59 | 89.40% | 2.574 | 0.059813 |
| NPB-IS | 0.324744 | 17.66 / 0.62 | 90.64% | 1.205 | 0.049755 |

**Every OpenMP row fails the cadence gate**, with incomplete observed worker
coverage. Delivery is only 2.50-3.50% of nominal process CPU cadence. This is
consistent with coalescing/process-directed delivery bias, not proof of a
specific loss mechanism. No conversion of these wait shares to CPU or wall
seconds is admitted; the analysis leaves OpenMP function seconds unset.
MG also exceeds 10% observed overhead. High CPU occupancy includes spinning
and does not prove useful compute efficiency. The CPU-capacity residual
includes startup, serial work and unscheduled workers, not just blocking.

Among delivered compute PCs, CG's `conj_grad_._omp_fn.0` has 60.77% of all
PCs (7,883-byte function); EP's `MAIN__._omp_fn.1` has 50.24% (1,238 bytes),
plus 27.16% in log and its internal path. MG's `resid_._omp_fn.0` has 23.08%
(2,971 bytes), `rprj3_._omp_fn.0` 11.54% (6,257 bytes) and
`psinv_._omp_fn.0` 8.97% (2,693 bytes). IS's randlc has 38.89% (338 bytes)
and rank worker 37.04% (3,965 bytes). STREAM's leading two worker functions
have 9.28% and 7.22% (545/625 bytes). These locate code for diagnosis but
cannot rank removable parallel seconds. The method is inadequate for a
quantitative OpenMP split; no further recorder project or card retry is
implicitly authorized by this report.

## Planning estimates and removable-time ranking

The ranking is an **opportunity ceiling and conditional-removal ranking**,
not measured speedup from an optimization. For primary full-profile GCC-KNC
median `T`, sampled launch-to-exit time `L`, sampled user CPU `U`, and region
PC fraction `p`, normalize the diagnostic estimate onto the primary boundary:

`A = T * (U / L) * p`; conditional removable seconds `D(s) = A * (1 - 1/s)`.

This preserves the primary timing, discounts system/off-CPU/boundary costs,
and assumes the diagnostic composition represents the primary run. `A` is
an estimated ceiling for that region's opportunity, not a statistical upper
confidence bound or evidence that the whole region is removable. All proven
removable lower bounds are **zero**. A local `s=1.20` below is an explicit
sensitivity assumption, not a forecast. No positive gain is booked into the
M4 budget. Positive gains require a matched implementation A/B and correctness
check. Use the 7120 column for this ranking; do not project sampling shares
onto restricted profiles. Three primary timing pairs and one profile launch
provide no reliable confidence interval for these estimates.

Only serial programs passing the reported cadence, attribution, sample-count
and per-run overhead checks enter this numerical opportunity ordering. GEMM
uses the median of six per-launch normalized estimates (0.719 s; range
0.700-0.740 s). Unknown/system/residual/boundary costs and unlisted regions
receive no assumed gain. Cholesky, low-count programs, serial MG, HPCG and
all OpenMP rows are outside the qualified sum.

| Rank | Program / disjoint opportunity | Primary KNC median T s | Estimated A s | D if local 1.20x, s | Interpretation |
| --- | --- | --- | --- | --- | --- |
| 1 | NPB-EP scalar transform/call site | 97.394 | 51.174 | 8.529 | x87 arithmetic, divide/sqrt, conversions and call-save traffic; no isolated bridge cost |
| 2 | NPB-EP log wrapper + internal path | 97.394 | 36.794 | 6.132 | Library execution; exclusive of row 1; not removable by an ordinary caller scheduling change |
| 3 | NPB-CG indexed reduction | 29.224 | 24.547 | 4.091 | 25-byte scalar loop; indexed access and ordered arithmetic costs unresolved |
| 4 | PB-ludcmp matrix initialization | 18.150 | 10.985 | 1.831 | General scalar update/locality opportunity; setup must remain in the benchmark |
| 5 | NPB-EP random generation loop | 97.394 | 8.402 | 1.400 | Separate RNG code; strict arithmetic/conversions, no independent gain proof |
| 6 | PB-ludcmp two factorization reductions | 18.150 | 6.849 | 1.142 | Two disjoint ranges; recurrence and prefetch/address work overlap within them |
| 7 | NPB-IS random generator function | 11.997 | 5.169 | 0.862 | Control-word conversion and return bridge; includes setup work |
| 8 | STREAM three vector loops | 7.9535 | 4.289 | 0.715 | Already vectorized; bandwidth/scheduling headroom unmeasured |
| 9 | NPB-IS rank bucket loop | 11.997 | 4.197 | 0.699 | Scalar integer indexing; no evidence of a profitable gather replacement |
| 10 | STREAM aligned libc copy helper | 7.9535 | 2.823 | 0.470 | Runtime copy; caller unknown, not all compiler-removable |
| 11 | NPB-CG sparse setup search | 29.224 | 2.046 | 0.341 | Separate from the repeated indexed reduction |
| 12 | PB-gemm vector inner loop | 0.89267 | 0.719 | 0.120 | Already compact vector code; bridge sits outside the counted region |

Rank denotes cost exposure under the same hypothetical local gain. Different
feasible local gains can reverse the ordering. Summing every row would not
be a compiler forecast: library work, conversions and strict recurrences
have different implementation constraints. In particular, reducing ABI
transfers cannot claim the entire EP log/math budget. No sample pinpointing
a load or a sqrt instruction proves a cache miss or instruction latency.

### Updated per-program planning estimates

The review's ranges were conditional donor-relative whole-program scenarios.
The comparison medians above measure changes already present in GCC-KNC;
they cannot be multiplied by those old scenarios. The updated default for
**additional** GCC-KNC improvement is 1.00x budget credit for every program
until a local gain is demonstrated. The sensitivity column below instead
asks what a hypothetical 1.20x change in the specified observed region alone
would do to the current GCC-KNC program: `T/(T-D(1.20))`. It is not a new
baseline measurement or donor-relative prediction.

| Program | Review scenario | Updated evidence / incremental planning constraint |
| --- | --- | --- |
| PB-gemm | 1.33-1.60x | 0.719 s estimated vector-loop exposure; hypothetical 1.20x local gives 1.155x whole program. No transfer-removal credit from that loop. |
| PB-atax | 1.33-1.60x | 77.42% initialization versus 21.51% combined reduction/update PCs. This does not support assigning the old 50-75% hot-fraction assumption to remaining kernel work. 93 PCs: numeric gain withheld. |
| PB-cholesky | 1.11-1.25x | 96.38% of sampled PCs in input-matrix construction, 2.97% in one factorization reduction. +19.35% overhead blocks seconds; target diagnosis shifts toward setup, not unqualified divide/sqrt replacement. |
| PB-ludcmp | 1.11-1.25x | 60.65% initialization, 37.81% in two factorization reductions. 1.20x on initialization alone implies 1.112x; on the two reductions alone 1.067x. These are separate conditional cases. |
| PB-jacobi-2d | 1.25-1.43x | 80.88% in two vector stencils, but only 68 PCs. Hot fraction is descriptively compatible with the review; 1.5x local gain is unproved, numeric budget withheld. |
| PB-heat-3d | 1.25-1.43x | 63.27% in two vector loops, only 49 PCs; masked tails/output remain separate. No demonstrated locality headroom or numeric gain. |
| STREAM | 1.08-1.23x | Three vector loops expose 4.289 s, libc copy another 2.823 s. Improving vector loops alone 1.20x would give 1.099x overall. Runtime copy is a separate opportunity, not a fourth recommended theme. |
| NPB-CG | 1.09-1.36x | 84.24% indexed reduction, 24.547 s normalized exposure. Local 1.20x would give 1.163x overall. Scalar reduction order and memory behavior must both be preserved/diagnosed. |
| NPB-EP | 1.05-1.28x | Scalar transform and log expose 87.968 s together; 1.20x on both would give 1.177x overall. Math, ABI and conversions cannot each claim this same budget. |
| NPB-MG | 1.20-1.36x | Serial validity remains S11-27's gate. OpenMP passed workload checks but its profile failed cadence/overhead; no primary speed or removable-time credit. |
| NPB-IS | 1.05-1.19x | randlc is 43.38% of delivered PCs, bucket loop 35.22%. 1.20x on randlc alone implies 1.077x overall; benchmark setup remains included. |
| HPCG | 1.09-1.36x | S11-28 equal-work pilot: paired median 0.98263x across six pairs, about 1.8% slower than donor. Omitted from profiling panels and removable-seconds sum; no latency-based estimate or incremental gain credit. |
| zlib | 1.10-1.20x | Deflate, slide_hash and inflate lead the 121-PC profile; scalar narrow loops are visible. Count is too low for a qualified gain. Optional PGO has no automatic credit. |
| SQLite | 1.10-1.20x | VM 29.48%, distributed B-tree/sorter work; 173 PCs and 6.94% unknown libc PCs. Gain withheld; donor remains the documented -O3 exception. |

### At most three general mechanisms for S12 proof work

These are ranked **diagnostic proposals**, not approved performance changes.
Expected benefit is not yet identified; the ranges are local-1.10x to
local-1.20x sensitivities on disjoint qualified exposure. Engineering hours
are this report's rough planning allowances for one bounded proof, not
measured task durations or commitments. They exclude implementation roll-out,
lead GCC builds, and the sprint-end batch gates. Stop a proof when its gain
or strict-correctness premise fails; do not keep expanding it to meet a vote.

| Priority / mechanism | Qualified exposure and conditional removal | Proof allowance / controls / principal uncertainty |
| --- | --- | --- |
| 1. Strict scalar FP conversions and call boundaries | EP transform + log, plus IS randlc: 93.137 s; **8.47-15.52 s** if the entire selected exposure improves 1.10-1.20x | 8-16 engineer hours, one lead-run paired diagnostic batch of at most 30 min plus any required GCC build. Separate call-save/return transfers, conversions and math before choosing a change. Preserve precision, rounding, exceptions and reduction order; include no-call scalar and already-vectorized controls. Libm body costs may be outside compiler scope. If only bridges change, remeasure their smaller exposure and discard this whole-path sensitivity. |
| 2. Indexed-load scheduling / strict sparse reduction | CG indexed reduction: 24.547 s; **2.23-4.09 s** under the same conditional local gains | 6-12 engineer hours, at most 20 min lead-run diagnostic pairs plus build. Keep input/index order and FP accumulation fixed; compare cache-resident and memory-resident controls and a contiguous loop. Do not infer prefetch or gather profitability from load-PC concentration. |
| 3. Dependency-preserving scalar update / locality transformations | ludcmp initialization only: 10.985 s; **1.00-1.83 s** conditionally. Cholesky is a descriptive second instance, with zero credited seconds | 8-16 engineer hours, at most 20 min lead-run diagnostic pairs plus build. Prove legal alias/dependence handling and preserve per-element arithmetic order; include independent-update and recurrence controls. Keep initialization and live-out checks inside timing. General loop transforms, not a benchmark-specific initialization replacement. |

The three selected exposure sets are disjoint: 128.669 s in total, with a
**conditional** 11.70-21.44 s removal if all of those regions actually attain
the assumed local gains. This sum is not a claim of achievable removal,
aggregate speedup, or a 17-program vote. It excludes low-count profiles,
Cholesky, serial MG, HPCG, every OpenMP profile, output changes and unassigned
time. Expected proven removal remains 0 s; implementation selection awaits
the proof results. The lead should select fewer than three if the estimated
22-44 engineer hours or bounded card windows do not fit. No automatic card
job, compiler change, or further sampling project is requested here.



## Reproduction and handoff

`tools/s11_15_baseline.py` reads the public raw and checked records, matches
launch metadata, preserves collector failures and extracts HPCG historical
ratings only from development captures. It emits pilot tables under
`.work/_shared/S11-15/baseline-tables.md`, reproduced above. It does not run
programs, modify the primary harness, rescore held-out programs or issue a vote.
The primary HPCG row above supersedes that script's historical proxy using
S11-28 results and referenced stdout. The corrected profile-keyed extraction
is logged at `.work/_state/logs/S11_15_fixed_work_by_profile-20261114-075319.log`;
the earlier extraction keyed only by compiler/run and overwrote profiles,
so its summary statistics are discarded. No native run was repeated.

```powershell
python tools/run.py --name S11-15-baseline --inputs tools/s11_15_baseline.py -- python tools/s11_15_baseline.py
```

Host results:

- Sampler build/lint/runtime dependencies and shell/symbol staging passed:
  `.work/_state/logs/S11_15_sigprof_stage-20261113-145305.log`.
- After adding the second repetition, the final staged shell passed syntax:
  `.work/_state/logs/S11_15_sigprof_shell-20261113-145521.log`.
- Baseline extraction passed:
  `.work/_state/logs/S11_15_baseline-20261113-145415.log`.

Native pilot capture and overhead passed; host attribution is recorded above.
The final host analysis log is
`.work/_state/logs/S11_15_attribution-20261114-001302.log`.
The initial addr2line-only attempt is
`.work/_state/logs/S11_15_attribution-20261114-001156.log`; dynamic-symbol
containment resolves its stripped-library naming limitation conditionally.
No baseline extraction or passing native pilot was rerun.

Reproduce the host analysis with:

```powershell
python tools/run.py --name S11-15-attribution --inputs tools/s11_15_attribution.py -- python tools/s11_15_attribution.py
```

It writes `.work/_shared/S11-15/attribution.md` and `attribution-pcs.txt`;
the latter retains per-launch module-relative PCs and symbol/source status.
It does not read held-out data or change any corpus source or primary harness.
The final batch analysis adds the development profiles and bounded ranking above.
Its first symbol-only pass left stripped internal helpers unnamed; the final
pass follows explicit branches from exported entries and retains unresolved
PCs. No native rerun was needed. Host attribution passed with the native
qualification limits retained, not converted into passes.

```powershell
python tools/run.py --name S11-15-batch-attribution --inputs tools/s11_15_batch_attribution.py tools/s11_15_attribution.py -- python tools/s11_15_batch_attribution.py
```

Outputs are `.work/_shared/S11-15/batch-attribution.json`,
`batch-attribution-pcs.txt`, and fixed per-build disassembly files in that
same directory. They are analysis outputs, not primary timing replacements.
Large captures and disassemblies remain outside git. The report contains the
results needed after the engineer worktree is removed. No further card run
is staged by this report. x86 was not run.

References: S11-15 lead notes dated 2026-11-13; `docs/sprints/SPRINT-11.md`,
Theme B; `docs/reviews/2026-11-12-s11-s13-scope-review.md`, planning table and
finding 3; `tools/corpus/README.md`; `tools/corpus.py`, `tools/corpus/launch.c`,
`tools/corpus/timing.h`; `tools/m4_score.py` (gate requires six pairs).
