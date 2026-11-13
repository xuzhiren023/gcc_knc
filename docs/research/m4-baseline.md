# M4 development baseline: S11-15

## Evidence status

The lead completed the S11-18 pilot at 2026-11-13 19:47Z. This report uses
`.work/_shared/S11-18/raw-results.jsonl`, the collector's `results.jsonl`,
and development HPCG stdout captures. There are 414 development launches:
252 primary and 162 GCC-KNC OpenMP. The lead's 468-launch total includes sealed
programs; their data was not opened and is not included here.

The 2026-11-13 14:47 EST profiling attempt failed because the card has no
`perf` executable. Its log is
`.work/_state/logs/S11_15_profile_cpu-20261113-144706.log`.
A replacement SIGPROF pilot is built and staged, but has not run on the card.
No hot-function/loop time share, removable-time ranking, or S12 implementation
theme is established. Baseline timing analysis is available; profiling acceptance
remains blocked on native method qualification and subsequent program profiles.

## Primary pilot observations

Each cell is **donor median / GCC-KNC median; median paired speedup [min, max]**.
Durations are seconds, except HPCG, which reports the historical GFLOP/s rating
from its existing stdout as directed by the lead. For latency, speedup is
`donor_seconds / knc_seconds`; for HPCG it is `knc_GFLOPs / donor_GFLOPs`.
A value above one favors GCC-KNC. The paired median need not equal the ratio
of the two marginal medians. Ranges cover the three observed pairs, not a
confidence interval. Pair order was AB, BA, AB. These are pilot observations,
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
| HPCG | 0.086358 / 0.085054; **0.985x** [0.983, 0.986] | 0.086383 / 0.084921; **0.983x** [0.982, 0.984] | 0.086362 / 0.084906; **0.982x** [0.981, 0.988] |
| zlib | 1.3176 / 1.251; **1.054x** [1.049, 1.055] | 1.3158 / 1.259; **1.051x** [1.042, 1.077] | 1.3191 / 1.2523; **1.053x** [1.050, 1.055] |
| SQLite | 1.8412 / 1.7585; **1.038x** [1.030, 1.051] | 1.8328 / 1.7483; **1.048x** [1.037, 1.059] | 1.8327 / 1.7625; **1.048x** [1.032, 1.049] |

The collector reports passes for every primary pair other than NPB-MG.
NPB-MG's nine GCC-KNC serial launches fail verification; all its primary speed
numbers are withheld pending S11-27. The report preserves existing collector
checks, including PolyBench's complete live-out comparison against the donor.
That comparison is not an independent high-precision oracle; the harness's
independent-reference follow-up remains a gate prerequisite.

HPCG's requested-duration workload does not have equal work across compilers,
so its launch-to-exit latency is excluded from performance comparisons.
The historical throughput observations put GCC-KNC about 1.5-1.8% below the
donor in the three profile medians. These are the lead-authorized pilot
throughput proxy, not a substitute for S11-28's fixed-work scoring contract.
No HPCG removable wall seconds are inferred from the throughput ratio.

Cholesky and CG show substantial across-pair spread, and ludcmp's 5100 range
is also broad. Three pairs cannot establish causes or statistical significance.
The comparisons describe existing compilers; they do not validate the review's
prospective gains from future GCC-KNC work.

## OpenMP side panel

**The donor toolchain has no OpenMP runtime.** These are GCC-KNC-only
`-O2 -march=knc -fopenmp` observations, with one, two or four threads per
compute core. Values are median [min, max] seconds across three launches,
except HPCG's historical GFLOP/s rating. No donor speedup or primary vote is
assigned. All 12 HPCG launches at two/four threads per core in restricted
profiles fail (the lead diagnoses `bad_alloc`; for example capture/340.stderr).
Their short failure durations are excluded. The other 150 OpenMP launches
pass the existing collector checks. Runtime wait versus compute is unmeasured.

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

## Replacement profiling-method pilot

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

## Qualification after the lead run

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

## Planning estimates and removable-time ranking

All 14 programs still have unknown hot functions/loops with wall shares,
vectorization decisions tied to hot paths, bridge/spill cost, hot code size,
and (where applicable) OpenMP wait versus compute. The review ranges below
are future-work scenarios, not predictions validated by donor comparisons.
Every program's admitted prospective gain remains **unestimated**; no gain
is admitted to the S12 budget from these scenarios.

| Program | Review scenario | Updated planning evidence and next constraint |
| --- | --- | --- |
| PB-gemm | 1.33-1.60x | KNC 0.89 s; bounded sampler staged; hot fraction/local gain unknown |
| PB-atax | 1.33-1.60x | KNC 0.94 s; strict-reduction/reuse share unknown |
| PB-cholesky | 1.11-1.25x | KNC 11.2-11.5 s profile medians; recurrence/scalar-FP share unknown; pair spread |
| PB-ludcmp | 1.11-1.25x | KNC 18.1-18.4 s; recurrence/scalar-replacement share unknown; pair spread |
| PB-jacobi-2d | 1.25-1.43x | KNC 0.70 s; stencil/locality share unknown |
| PB-heat-3d | 1.25-1.43x | KNC 0.50-0.51 s; stencil/locality share unknown |
| STREAM | 1.08-1.23x | KNC 7.94-7.95 s serial; memory-cost share unknown; OpenMP separate |
| NPB-CG | 1.09-1.36x | KNC 29.2-29.4 s; sparse/reduction share unknown; donor pair spread |
| NPB-EP | 1.05-1.28x | KNC 97.4 s; largest valid non-HPCG serial latency, but math-call share/binding unknown |
| NPB-MG | 1.20-1.36x | Serial estimate withheld until S11-27 validity repair; OpenMP pass does not repair it |
| NPB-IS | 1.05-1.19x | KNC 12.0 s; address/branch/memory share unknown |
| HPCG | 1.09-1.36x | Historical throughput slightly lower; fixed-work contract S11-28 and sparse/reduction profile pending |
| zlib | 1.10-1.20x | KNC 1.25-1.26 s; scalar profile needed; optional PGO grants no baseline credit |
| SQLite | 1.10-1.20x | KNC 1.75-1.76 s against donor -O3 fallback; scalar profile and equal-flags qualification absent |

There is no defensible removable-time ordering yet. Total runtime only sets
an upper bound, and a donor speedup does not identify removable KNC costs.
The next ranking must report measured KNC wall seconds, hot wall fraction,
justified local improvement and overlap, separately for each resource profile.
The scenario `T * f * (1 - 1/s)` is usable only with supported quantities.
Select at most three general mechanisms with uncertainty, implementation cost
and unaffected controls after profiles qualify; do not sum overlapping gains.

## Reproduction and handoff

`tools/s11_15_baseline.py` reads the public raw and checked records, matches
launch metadata, preserves collector failures and extracts HPCG historical
ratings only from development captures. It emits pilot tables under
`.work/_shared/S11-15/baseline-tables.md`, reproduced above. It does not run
programs, modify the primary harness, rescore held-out programs or issue a vote.

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

Native sampling, overhead and attribution are untested. Full profiling and
removable-time acceptance remain open. x86 was not run.

References: S11-15 lead notes dated 2026-11-13; `docs/sprints/SPRINT-11.md`,
Theme B; `docs/reviews/2026-11-12-s11-s13-scope-review.md`, planning table and
finding 3; `tools/corpus/README.md`; `tools/corpus.py`, `tools/corpus/launch.c`,
`tools/corpus/timing.h`; `tools/m4_score.py` (gate requires six pairs).
