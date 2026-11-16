# Worked example: C7, a second reduction accumulator

This is a retrospective standard-tier application to existing measurements, not
a new optimization or native run. It uses the C7 reduction at four workers on
one core. It demonstrates a stop decision; it does not claim deep-tier validation
on a second program/profile. No card run or GCC build is needed to reproduce the
reasoning.

The reported experiment is
[knc-characterization.md, C7](../../../../docs/research/knc-characterization.md),
S8-01, 2026-11-07/08, binary revision `3f5ccb2`, one launch. Its two rows report
the same update time. Evidence is R (reported project measurement), production
project card, stepping unspecified. Architecture sources below are R01 p.19
(issue) and R02 pp.32-34,56 (resource/pairing qualifications), architectural
descriptions rather than stepping-qualified timing experiments.

## Scope and characterization

The scope is C7's repeated reduction body and reported time per vector update.
Set `p=1` for this deliberately isolated metric; no whole-application profile
share is available. A screening assumption of `s=1.02` would therefore yield an
Amdahl cap of 1.02 for this metric only. It predicts no application speedup.

[s8_compute.py:15](../../../../tests/bench/knc-char/s8_compute.py) constructs
32 folded-load additions per thread, updating one or two accumulators, with the
same inputs and vector operation count. The second variant adds a final combine
outside the repeated body. These are counted source-generator facts, not claimed
retired-instruction measurements or fresh disassembly of the historical binary.
Do not assume this alternative reduction order is legal for an arbitrary strict
FP program; this example evaluates the existing microbenchmark alternatives.

One accounting quantum is 32 updates on each of the four workers, completed on
one core: 128 vector updates in total. All modeled times below use core cycles
for that quantum. Data addresses advance by one line within the body; input
loads do not carry the accumulator dependency through memory. Repeated input
footprint is 8192 bytes across the workers, before output/control data. The
prediction assumes hot, nonconflicting L1 data and amortized setup/completion.

Machine values come exclusively from
[knc-machine.yaml](../../../../docs/research/knc-machine.yaml):

| Symbol | Key / evidence | Value used and qualification |
| --- | --- | --- |
| g | `thread_issue_interval` V | 2 core cycles/bundle, R01 pp.19,23-24 |
| r_b | `core_bundle_rate` V | 1 bundle/core cycle, eligible pairs only |
| r_U | `u_pipe_rate` E | 1 U instruction/core cycle for this arithmetic class |
| r_V | `vpu_arithmetic_rate` R | Rounded 1 arithmetic op/core cycle, S6-03 point 1 |
| L | `vector_arithmetic_latency` R | Rounded 4 core cycles, register-carried add chain |
| C / L1 | `cache_line_bytes` / `l1_data_capacity` V | 64 bytes / 32 KiB, R01 pp.22-23 |
| f_core / f_TSC | `characterization_core_clock` / `characterization_tsc_clock` R | 1.238 / approximately 1.232 GHz, S6-03 Units |
| q_control | `vector_add_reciprocal_throughput.threads_4` R | 4.18 TSC ticks/update/thread, S6-03 vaddps.rt |
| q_meas | `c7_reduction_update_time` R | 4.13 TSC ticks/update/thread for both accumulator counts; spreads 0.2% and 0.0% |

Density comes from the C7 experiment, not the hardware context limit or a compiler
default. Reusing the earlier clock conversion is an approximation, with roughly
0.5% tick/cycle sensitivity; no fresh S8 clock calibration is claimed. Hardware
is the project 7120; effective profile is full. The physical 5110P/3120 and the
restricted 3100/5100 profiles have no C7 result in this evidence.

## Model

`a` is the number of independent accumulators per worker. Bundle counts below
are lower bounds on the body: at least one per arithmetic update. Loop/control
work is not silently declared absent; omitting it weakens this lower bound.

| Term | Formula | Inputs | Source | Value per profile |
| --- | --- | --- | --- | --- |
| Thread issue | g * B | B >= 32 per worker; g=2 | Counted s8_compute.py:15-20; `thread_issue_interval` V | full: >=64 cycles |
| Core issue | sum(B) / r_b | >=128 bundles; r_b=1 | Same count; `core_bundle_rate` V | full: >=128 cycles |
| U-pipe | N_U / r_U | 128 arithmetic ops; r_U=1 | Same count; `u_pipe_rate` E | full: 128 cycles in this resource model |
| VPU | N_vec / r_V | 128 additions; r_V=1 | Same count; `vpu_arithmetic_rate` R | full: 128 cycles in this resource model |
| Recurrence | 32 * L / a | L=4; a=1 or 2 | Same count; `vector_arithmetic_latency` R | full: 128 cycles for a=1; 64 for a=2 |
| L1 traffic | bytes / applicable service rate | 8192 repeated input bytes; hot folded loads | Counted body; `cache_line_bytes` V; no matching isolated service rate | full: unknown time, excluded from bound |
| L2/memory | cold traffic / bandwidth | No steady-state lower-level traffic assumed | Working-set count and explicit hot-data assumption | full: N/A in this prediction; cold start omitted |
| AGI / gather / synchronization | relevant critical-path cost | Fixed base within body; no gathers or inter-worker reduction in body | Counted s8_compute.py:15-21 | full: no such body term; setup/outer-loop overhead not isolated |

**Lower bound:** `T_lb = max(64,128,128,128,128/a) = 128` core cycles for
either variant. In particular the sourced core-issue limit alone gives this
floor; treating rounded measured VPU/recurrence inputs as approximate does not
strengthen it. It is a steady-state resource bound under the counted-body and
clock assumptions, with omitted terms explicitly shown.

**Prediction:** transfer the existing independent-add control rate to this hot
folded-load case, assuming no additional exposed load stalls:
`T_pred = max(T_lb, 32*q_control*f_core/f_TSC) = approximately 134.4` cycles.
This is an empirical overlap prediction, not a sum of load latency per operation
and not a hardware bound. It assumes the same per-thread rate once aggregate
issue is saturated; it could be falsified by exposed load/conflict costs.

**Measurement:** `T_meas = 32*q_meas*f_core/f_TSC = approximately 132.8` cycles
for either C7 variant (132.16 TSC ticks for the quantum per worker). Conversion
does not divide by four: all four workers' updates occupy the same time interval.

| Term | Profile | T_i / T_meas | Interpretation / uncertainty |
| --- | --- | --- | --- |
| Thread issue floor | full | 48.2% | Per-worker floor, not aggregate instruction utilization |
| Core issue floor | full | 96.4% | Dominant shared-resource floor |
| U / VPU models | full | 96.4% each | Overlapping constraints; percentages must not be added |
| Recurrence, one accumulator | full | 96.4% | Rounded register latency; critical for one chain |
| Recurrence, two accumulators | full | 48.2% | Lower recurrence term leaves the shared issue floor unchanged |
| L1 transfer | full | unknown | No matching standalone service measurement |

`T_lb/T_meas = approximately 0.964`; `T_pred/T_meas = approximately 1.012`.
These are model ratios, not PMU measurements. The prediction is about 1.2% above
the measured time, consistent with the deliberately approximate control transfer;
do not subtract that residual as a measured overhead component.

## Predict, compare and decide

For a second accumulator, the model changes the recurrence term only:
`T_lb_new=128`, `T_pred_new=134.4` cycles, predicted regional speedup 1.00.
The complete-call final combine can add work, so no whole-call gain is forecast.
With the isolated metric's `p=1`, its predicted Amdahl gain is also 1.00; an
application gain is unknown. This is a retrospective reconstruction of a
prediction using the earlier S6-03 control, not a claim it was recorded before
S8-01 ran.

Existing C7 measurement: 4.13 -> 4.13 TSC ticks/update/thread, speedup 1.00.
The model correctly predicts no throughput gain from the extra chain in this
configuration. Near-bound headroom is only about `132.8/128 = 1.038`, well
inside the skill's 15% stop band even allowing the clock approximation. Stop
accumulator tuning for this case. Material improvement would require less work
or a different algorithm/layout, not merely another accumulator at this density.

Keep the negative result and existing parameters; no new machine measurement
is proposed. Lower-density behavior, strict application legality and complete
application gain remain unmeasured here. The example does not establish a new
compiler default or transfer this result to the other models/profiles.
