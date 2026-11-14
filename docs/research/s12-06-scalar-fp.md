# S12-06: strict scalar FP, phase-one proof

Status: **phase one closed: premise fails**, following the lead's returned
card results and close instruction on 2026-11-14. Native diagnostic checks
passed. The >=3 s compiler-removable exposure gate is **not established**;
no backend change, strict-FP relaxation, or benchmark A/B has been made.

## Scope and construction

The reference is `m4-baseline.md`, "Vectorization, transfers, spills and code
size" and "Planning estimates and removable-time ranking". The qualified
exposures are 51.174 s in EP's transform/call site, 36.794 s in the log
wrapper/internal path, and 5.169 s in IS's recurrence, totaling 93.137 s.
The first and last regions together are 56.343 s. Three seconds would require
3.22% of the combined exposure, or 5.32% of those two compiler-owned regions.
Library execution is not automatically a compiler-removal budget.

`tools/s12_06_transform.F90` and `tools/s12_06_scalar.c` are original small
reproducers of the code properties, not copies of benchmark implementations.
The Fortran transform retains ordered coordinate scaling, radius calculation,
log, divide, sqrt, absolute values, integer bucket conversion, tally and sums.
The C recurrence uses a base-2^23 split for multiplication modulo 2^46, retaining
four double-to-int-to-double conversions. Its loop calls a separately visible
step, preserving the scalar return boundary. Initialization and benchmark
drivers are excluded; the transform also rejects a zero radius explicitly.
These differences mean the reproducer is a diagnostic, not an EP/IS result.
No held-out source or binary was opened, built, or run.

Both C and Fortran are compiled at `-O2`, using the ticket's lane-1 installed
`gcc-knc-16.2.0` prefix with `-march=knc`, and the shared GCC 5.1.1 prefix
`toolchain/cross`. GCC trees and build trees were untouched. Shared-library
packaging uses `-fPIC` for both; neither uses LTO or fast-math. Packaging means
PLT/interposition effects are present, and must not be mistaken for the exact
whole-program link layout. Both use the same card-supplied libm.

## Generated-code comparison

Assembly and linked disassembly are under `.work/_shared/S12-06/`.
Counts below describe executed paths, not cycle estimates.

| Cost | GCC 5.1.1 | GCC-KNC 16.2.0 | Interpretation |
| --- | --- | --- | --- |
| Transform argument and return transfer | x87 store + `vbroadcastsd`; `vpackstorelpd` + x87 load | Same bridges; also an extra `fstl 40(%rsp)` before the argument bridge | Scalar arithmetic is x87 and the scalar FP call ABI uses zmm0. Removing all bridges would require a proved alternative register choice, not simply deleting stores. The extra stack store has no later load in this function and is a candidate for further investigation. |
| Transform integer bucket | One `fnstcw`, two `fldcw`, one `fistpl` per accepted point | Same | Both switch rounding for truncation and restore it before later arithmetic. |
| Recurrence step conversions | Four `fistpl`, four `fildl`, eight `fldcw`, one `fnstcw` | Same | The control word is already saved once per step; arithmetic between conversions prevents assuming that one changed rounding mode can span the entire function. |
| Recurrence return | x87 store + broadcast; caller pack-store/load | Same | The timed recurrence loop also contains caller overhead; its entire time cannot be assigned to the baseline's callee-only 5.169 s. |
| Transform live values across log | Coordinate/radius stores and reloads; also retains a constant through memory | Coordinate/radius stores and reloads; recreates the constant with `fld1` | These preserve needed values across the call. Stack traffic is not all unnecessary spill traffic. |
| Math | `log@PLT`, x87 divide and `fsqrt` | Same | The baseline locates x87 log work and ABI bridges inside libm. Libm bodies remain out of scope; caller improvements cannot claim that whole 36.794 s. |

The independent scalar-conversion probe has feedback from the preceding sum,
so both compilers retain scalar conversions. GCC-KNC unrolls the large loop by
eight and adds prefetches; GCC 5.1.1 leaves a single loop body. Each still has
two control-word loads per conversion. Differences in timing therefore include
loop organization as well as conversion costs.

The no-call scalar control retains a dependent x87 multiply/add recurrence.
The already-vectorized control is identical handwritten IMCI load/add/store
assembly in both libraries. A handwritten `ret` also provides an identical
opaque scalar identity boundary. This avoids conflating call-site traffic with
the two compilers' different lowering of a C identity function. Controls use
ordinary assembler instructions, with no opaque instruction bytes.

## One bounded paired batch

The staged files are `scalar-donor.so`, `scalar-knc.so`,
`scalar-diagnostic.mic`, `diagnostic.sh`, and the transport list `files.txt`.
The runner loads both libraries locally and exercises eight cases:

| Case | Purpose |
| --- | --- |
| `transform_log` | Full transform, including the real math call |
| `transform_table` | Same transform using precomputed log values; no inner math call |
| `transform_identity` | Pass those precomputed values through the opaque `ret` boundary |
| `transform_memory` | Same opaque call through a C callee with x87 arithmetic and memory bridges |
| `recurrence` | Ordered four-conversion recurrence and its scalar return/caller boundary |
| `conversion` | Scalar FP/int/FP conversion with loop-carried dependence |
| `scalar_control` | No-call, no-conversion scalar recurrence |
| `vector_control` | Identical already-vectorized load/add/store control |

Each uses 2,048 fixed dyadic inputs. Three pairs alternate donor/KNC order;
calibration chooses identical work for the two compilers within each pair.
Normalize each reported duration by `rounds * 2048` before comparing cases.
The calibration cap is 1,024 rounds. The process alarm and card timeout are
1,500 s, below the 30-minute budget. No second diagnostic batch is implied.

For the requested serial single-core timing, the lead runs from the main repo:

```powershell
python tools/card_run --benchmark --threads 1 --timeout 1500 --file-list .work/_shared/S12-06/files.txt .work/_shared/S12-06/diagnostic.sh
```

Save stdout/stderr under `.work/_shared/S12-06/` for the resumed ticket.
The runner reads `sched_getaffinity`, launches one pinned worker per granted
CPU, and synchronizes timed cells. It also supports a larger allocation without
silently doing all work on one CPU; this batch requests one for serial timing.

Checks run before timing: donor/KNC finite-result agreement, transform sums
within relative 1e-12 and exact bucket counts, recurrence state against an
independent unsigned-integer modulo-2^46 calculation, conversion feedback
against integer arithmetic, and every vector output against exact dyadic sums.
Any failure makes the process fail. Timing is admissible only with successful
card execution and `S12_06_CHECK PASS`. This finite workload check is not a proof
of all rounding modes, exceptions, or excess-precision behavior for a future
compiler change.

## How to interpret the returned measurements

Use the three normalized paired samples, retaining negative deltas and noise.
`identity - table` is a sensitivity to caller save/restore and ABI bridges plus
call/return; `memory - identity` adds callee memory transfers and the synthetic
x87 operation. `log - identity` includes the real library body, but also changes
argument preparation. These are diagnostic counterfactuals with different
register pressure and memory loads, **not an additive four-way cycle partition**.
Precomputed-log variants are not legal replacements for a strict math call.

The standalone conversion probe and the recurrence locate conversion cost;
their timings do not independently isolate control-word loads from dependent
arithmetic. In particular, a donor/KNC speed difference does not itself prove
that any remaining sequence is removable. Do not project it directly onto the
5.169 s baseline callee exposure.

## Returned native results and conclusion

The lead supplied `.work/_shared/S12-06/card.stdout`, ending in
`S12_06_CHECK PASS`, with program exit code 0 and 0.324 card minutes.
The actual run reports `workers=240` and CPUs 1 through 240, rather than the
requested one-worker serial allocation. The table records the median of the
three paired samples labeled `cpu=240`, matching the lead's cited result;
these are one worker's durations during the concurrent run, not serial
whole-program timings or medians across all workers. The transport metadata
also lists an overlapping job, so no isolated serial performance claim follows.

| Case | Rounds per sample | GCC 5.1.1 median (s) | GCC-KNC median (s) |
| --- | ---: | ---: | ---: |
| `transform_log` | 64 | 0.149616 | 0.144664 |
| `transform_table` | 128 | 0.152983 | 0.150083 |
| `transform_identity` | 128 | 0.175162 | 0.167692 |
| `transform_memory` | 128 | 0.183584 | 0.176304 |
| `recurrence` | 256 | 0.188744 | 0.186465 |
| `conversion` | 1024 | 0.147169 | 0.127164 |
| `scalar_control` | 1024 | 0.044156 | 0.021511 |
| `vector_control` | 1024 | 0.017493 | 0.017689 |

Each round processes 2,048 inputs; durations across different cases require
normalization by that count and the rounds column. GCC-KNC is faster in all
scalar cases in this selected worker's samples. The identical vector control
is slightly slower (about 1.1% by the ratio of medians), so the result is not
literally faster in every case and does not establish statistical significance.

Both compilers retain the same ABI bridges, conversions and necessary call
saves. The extra dead `fstl` in the KNC transform remains a candidate removable
store, but this batch does not isolate its cost or show that removing it saves
>=3 s of the 93.137 s EP+IS exposure. Faster diagnostic timings alone cannot
establish that a shared sequence is removable under strict FP and the ABI.
The demonstrated removable-time lower bound remains **0 s (0% of exposure)**;
the actual removable share is **unknown**, not measured as zero. Libm bodies
remain out of scope.

The phase-two premise therefore fails to be established. Per the lead's
instruction, close at phase one with no GCC change and no further tuning or
card batch. Phase-two T1 red/green, T0-T2, ICE sweep and the whole-program paired
EP/IS/control panel were not run; no benchmark benefit is claimed. x86 not run.

## Host validation

Build, forbidden-instruction lint on both libraries and runner, dynamic-runtime
dependency checks, and launcher syntax passed. The final stage command was:

```text
python tools/run.py --name S12-06-stage --inputs tools/s12_06_scalar.c tools/s12_06_transform.F90 tools/s12_06_controls.S tools/s12_06_stage.py -- python tools/s12_06_stage.py
```

Log: `.work/_state/logs/S12_06_stage-20261114-120126.log`.
Native checks and diagnostic timings passed in the lead's returned run above.
Phase two was not entered because its removable-cost gate was not established.
