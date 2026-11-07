# Card runs, Sprint 6

Lead-run card jobs for Sprint 6 (`tools/card_run`; timing only in `--benchmark` windows).

## 2026-11-06: S6-01 timing probe, six exclusive windows

`tests/regress/knc-timing-probe.c` (S6-01), 2048 MiB limit, all exclusive `--benchmark` jobs,
raw output in `.work/_shared/S6-01/claude-bench/run1.out` to `run6.out`:

| Run | Cores x threads per core | Group-median spread | Under 2% |
|---|---|---|---|
| 1-3 | 60 x 4, three independent windows | 0.93%, 1.40%, 0.83% | yes |
| 4 | 60 x 1 | 1.37% | yes |
| 5 | 60 x 2 | 0.82% | yes |
| 6 | 60 x 3 | 10.58% (groups at about 72.6M and 80.7M cycles: bimodal) | **no** |

Single repetitions reach 21% above the median, so the protocol uses medians of groups. The TSC
calibrates at 1232.19 MHz against `CLOCK_MONOTONIC_RAW` in every run. Interpretation, including
the 3-thread bimodality, belongs to S6-01's note (`docs/research/knc-measurement.md`).

## 2026-11-06: S6-07 `gcc.dg/vect` run programs

At GCC `knc` after S6-04, 80 at a time on cores 59-40 (`claude-f7b0e10b…`): **776 of 777 pass**.
`pr121126.c` timed out under the driver's per-program limit. Its loop nest runs about 75 million
middle-loop iterations per outer iteration, so it is probably slow rather than wrong; it is rerun
alone with a longer limit at the next free slot.

## 2026-11-06: S6-10 checks, and a lost M2 attempt

At GCC `knc` after S6-10/S6-11, core 59, 18:59-19:13 UTC:
- S6-10 vect run tests `vect-63`, `vect-outer-2b`, `vect-outer-2d`, `vect-double-reduc-3`,
  `vect-double-reduc-7`, `vect-simd-17`: all exit 0. `s4_masks` `o2v` and `o3`: 1,589,070 checks
  each, 0 failures.
- The M2 baseline jobs (42 `--benchmark` jobs) all exited 2 with `ERROR allocation`: they ran under
  the 2 GiB `memoryMB` used for S6-01, and 240 workers' default 8 MiB thread stacks alone take about
  1.9 GiB of address space. Rerun with 6 GiB.
- The characterization jobs were refused by S6-12's check ("foreign workload running: sh"): the
  PhiWeather run was starting. Correct behavior.
- Earlier the same afternoon, two blocks were refused entirely by stale locks left by a force-killed
  card_run (`CURRENT_STATE.md`).

## 2026-11-06: first M2 measurement (one launch)

FP32 affine, L2 working set (length 4096 per worker), 60 cores x 4 threads, launch 1, ADR-0010
(`.work/_shared/tmp/claude-s6-m2-test/l2-1.out`), GCC `knc` after S6-11:

| Build | ns per element | Speedup over x87 | Group spread |
|---|---|---|---|
| x87 | 0.137514 | 1.00 | 0.41% |
| GCC-KNC vector | 0.013819 | 9.95 | 0.29% |
| IMCI reference | 0.011232 | 12.24 | 0.37% |

Gain fraction (ADR-0010 point 6): (9.95 - 1) / (12.24 - 1) = **0.80** (M2 needs 0.5). One launch
only; the full baseline (three launches, all lengths and working sets) follows. Two fixture fixes
were needed first: explicit 256 KiB worker stacks and `mallopt(M_ARENA_MAX, 2)` (per-thread malloc
arenas and default stacks exceeded card_run's address-space limit).

## 2026-11-06: the full M2 block, launch 1 is invalid (batch sizing)

`.work/_shared/tmp/claude-s6-slot5/m2-*-1.out`: 10 of 15 runs exited 3. The cause is the fixture, not
noise on the card (the ledger shows no other project; the only foreign process is card_run's own
`sleep`). The pilot stopped at the first batch of 10 ms or more; when that batch stalled (usually the
first build of a launch, cold), the batch was sized from it to 8-79 repetitions, and every timed
sample then took 4-9 ms instead of 100 ms. At that size the 240-thread barrier dominates: GCC-KNC
FP32 affine read 230 ns per element at length 15, 0.060 at L2 (against 0.0138 in the first
measurement). **Two short-batch runs still passed the spread check** (length 4096 GCC: 64
repetitions, 4.4 ms samples, 0.0697 ns per element, `within_launch_ok=1`), so a spread check alone
does not prove a valid launch.

Fix (`timing.c`, lead): after the pilot, re-size from a check batch until one lands within 50-200 ms
(at most 10 tries, else the run dies), and a launch is valid only if its median sample is within
50-200 ms. Built into `.work/_shared/M2-sizing/` (`build.py --out`); the block kept
ran on, so the fixed binary was moved into `.work/_shared/S6-02/` by an atomic rename between jobs
at 2026-11-06T19:54:06Z: launch 2 from the memory working set onward, and launch 3, use it. Launch 1
and launch 2's L1 and L2 runs (old binary, kept in `claude-s6-slot5/pre-fix/`) rerun afterwards
(`claude-s6-slot6.sh`).

## 2026-11-06: M2 launches 2 and 3 (fixed sizing), before the launch-1 reruns

ns per element, FP32 affine, 60 x 4; GF = gain fraction. L2 working set and length 4096 are the same
length (4096 per worker).

| Config | Launch | x87 | GCC-KNC | IMCI | GCC/x87 | GF |
|---|---|---|---|---|---|---|
| L2 | 3 | 0.1376 | 0.0153 | 0.0121 | 0.111 | 0.77 |
| len 4096 | 2 | 0.1377 | 0.0169 | 0.0140 | 0.123 | 0.81 |
| len 4096 | 3 | 0.1378 | 0.0147 | 0.0133 | 0.106 | 0.90 |
| memory | 2, 3 | 0.250, 0.243 | 0.0801, 0.0803 | 0.0801, 0.0801 | 0.32-0.33 | 1.00 |
| len 15 | 2, 3 | 0.141 | 0.0616, 0.0615 | 0.0366, 0.0365 | 0.44 | 0.45 |
| len 17 | 2, 3 | 0.136 | 0.0835, 0.0849 | 0.0396, 0.0395 | 0.62 | 0.25 |
| len 256 | 2, 3 | 0.104 | 0.0106, 0.0104 | 0.0189, 0.0194 | 0.10 | 1.96, 2.06 |
| len 1024 | 2, 3 | 0.102, 0.104 | 0.0088, 0.0089 | 0.0090, 0.0074 | 0.085 | 1.03, 0.82 |

Findings:
- **The 5%-of-x87 rule holds at every length** (worst GCC/x87 is 0.62, at length 17).
- **GF at L2 is 0.69-0.90 across four runs** (M2 needs 0.5), but **cross-launch stability fails**:
  GCC-KNC at length 4096 reads 0.0138, 0.0167, 0.0153, 0.0169, 0.0147 over five launches, and IMCI
  moves 0.0074-0.0097 at length 1024. Within each launch most groups agree within 2%. Hypothesis, not
  proven: buffer placement differs between launches (`posix_memalign` to 64 bytes, so the relative
  4 KiB offsets of x, y and the four sibling threads' buffers change with the heap), which changes
  L1/L2 set conflicts. Next: page-aligned buffers with a fixed per-buffer, per-thread stagger, then
  repeat launches to see whether the spread falls under 2% (ADR-0010 amendment if it does).
  Done in the fixture (`driver.c`: x and y page-aligned, staggered 1 KiB per sibling thread and
  512 bytes between x and y; built into `.work/_shared/M2-placement/`). `claude-s6-slot6b.sh` runs
  correctness, then five launches each of lengths 4096 and 1024, after the current block. It replaced
  `claude-s6-slot6.sh` (the launch-1 reruns on the old placement) before that started any job; the
  full three-launch baseline reruns on whichever placement proves stable.
- **The IMCI reference is not a ceiling everywhere:** GCC-KNC beats it 1.3-2x at lengths 255-257 and
  L1. GF above 1 there says the reference has per-call or alignment overhead, not that GCC is
  "better than possible"; M2 judges GF at L2 only.
- **Short odd lengths are GCC-KNC's weak spot:** length 17 is slower per element than 16 (0.084 vs
  0.064) while IMCI barely changes (0.040 vs 0.044): the remainder runs scalar where IMCI uses a
  masked tail. A tuning item for S6-05/S6-06 (masked epilogues).

## 2026-11-06: characterization, 1 core x 1 thread (S6-03 binary)

`.work/_shared/tmp/claude-s6-slot5/char-1x1.out`: 104 results, 103 accepted (spread under 2%;
`vcvtfxpntudq2ps.lat` 2.6%). Units are TSC ticks (about 1232 MHz, core 1238 MHz). Single-thread
headlines, to be confirmed at 2 and 4 threads before `knc-characterization.md` is written:
- Vector add, mul, FMA (SP and DP), integer add and logic: latency 4, one per 2 cycles (a single
  thread issues every other cycle). Permutes and swizzles: latency 6. `vrcp23ps`: latency 6.
- Pairing: vector + scalar pairs (2.08 per pair), vector + vector does not (4.09).
- Mask ops and scalar integer ops: latency 2, about 1 per cycle (paired).
- Memory-operand forms (masked load and store, unpack, convert up and down, spill-reload): latency 12;
  spill-reload throughput 5.
- Address generation interlock: about +2 cycles for each cycle the address is computed closer to its
  use (gap 0 to 4: 3.1, 4.2, 6.2, 8.2, 10.2).
- Gather: 15 cycles latency with all lanes in one line, about 175-184 with lanes on 16 lines.
- x87: add and mul latency 3; divide 38-39.
- Loads: L1 3, L2 24, memory about 357 cycles latency.
- **Streaming stores are slower than normal stores at one thread**: 27 vs 2.2 ticks (L1-sized),
  157 vs 38 (memory-sized). E5-08 must check this at 4 threads and 60 cores before using them.

## 2026-11-06: end of the slot5 block (21:17Z)

- Characterization at 1, 2 and 4 threads on one core: 312 measurements, 5 over 2% spread. Written up
  in `docs/research/knc-characterization.md`.
- `pr121126` alone with a 600 s limit: exit 0. The S6-07 timeout was the driver's per-program limit;
  the `gcc.dg/vect` run baseline is **777 of 777**.
- S6-11 card checks at GCC `knc` after S6-11: `vect-fmax-3` and `vect-fmin-3` exit 0; `s4_masks`
  `o2v` and `o3` each 1,589,070 checks, 0 failures.

## 2026-11-06: placement test (page-aligned, staggered buffers), 21:18-21:25Z

`.work/_shared/tmp/claude-s6-placement/`: correctness negative (affine_f32 154 failing cases, others
0) and positive (all 0) as expected. Launches 4 and 5 were refused by the driver (`--launch` accepts
1-3), so three launches per length:

| Length | Build | Launch 1 | Launch 2 | Launch 3 | Range / median |
|---|---|---|---|---|---|
| 1024 | x87 | 0.10398 | 0.10399 | 0.10403 | 0.0% |
| 1024 | GCC-KNC | 0.00893 | 0.00880 | 0.00898 | 2.0% |
| 1024 | IMCI | 0.00582 | 0.00597 | 0.00586 | 2.5% |
| 4096 (L2) | x87 | 0.13752 | 0.13821 | 0.13701 | 0.9% |
| 4096 (L2) | GCC-KNC | 0.01478 | 0.01383 | 0.01656 | 18.5% |
| 4096 (L2) | IMCI | 0.01121 | 0.01373 | 0.01192 | 21.1% |

Gain fraction per launch: 0.63, 0.66, 0.63 at 1024; 0.74, 0.99, 0.69 at 4096.

- Fixed virtual placement removed most of the variation at 1024 (IMCI moved 0.0074-0.0097 before,
  0.0058-0.0060 now) but **not at the L2 working set**.
- Huge pages are not available to a user program: a card probe (`claude-hugepage/probe.c`, built
  with the card's GCC 5) shows THP `[always]`, `madvise(MADV_HUGEPAGE)` returning 0, yet
  `AnonHugePages` stays 0 kB after touching an aligned 64 MiB region; `nr_hugepages` is 0.
- So each launch gets different physical 4 KiB pages, and the physically indexed 512 KiB L2 sees
  different set conflicts. This looks like a property of the card for any user program, not
  measurement noise: within each launch, groups agree within 2%. Not proven: a run with fixed
  physical pages would prove it, and needs root to reserve huge pages.

## 2026-11-06 (01:06-01:14Z on 11-07): M2 diagnostic block, interleaved driver (`claude-s6-m2diag.sh`)

Binary `.work/_shared/M2-diag` (interleaved builds, amendment-2 flags; kernels from M2-final, GCC
`knc` after S6-11). Correctness: negative 154 failing cases, positive 0. All seven launches valid,
`regime_steps=0` and `paired_step=0` in every one.

| Job | Gain fraction | Paired GF spread | GCC/x87 worst group |
|---|---|---|---|
| A1, L2, no warm-up | 0.750 | 0.63% | 0.111 |
| A2, length 15, no warm-up | 0.447 | 0.80% | 0.440 |
| B1-B5, L2, 10 s warm-up | 0.809, 0.799, 0.798, 0.801, 0.824 | 0.29-1.01% | 0.102-0.105 |

- **The interleaved design gives a stable gain fraction:** B1-B5 mean 0.806, sd 0.011, one-sided 95%
  lower bound 0.796, minimum 0.798. Under amendment 2 the L2 clauses (a) and (b) hold for this
  pre-tuning compiler; clause (c) needs the full length set in five launches (the baseline block).
- **The early slow regime did not appear** in these seven launches, so the run did not catch its
  cause. What the straggler fields do show: a persistent per-worker lag at L2 (max worker 5.5-6.1%
  above the median worker, mostly workers 120-121, that is core 30, in A1; worker 33 in B1), and
  about 26 involuntary context switches and 11 ms of system time per batch summed over 240 workers.
  OS activity versus a per-core hardware effect is still open; it no longer affects M2 decisions.

## S6-05 card correctness (01:14-01:16Z on 11-07, `claude-s6-05-card.sh`)

`.work/_shared/S6-05` at GCC 7fdd15cf40a: M2 kernels `--correctness` exit 0; `s5_ops` o2v and o3
779,984 checks, 0 failures; `fast` 602,384 checks (div/sqrt and FP32/FP64 conversions skipped by
design), 0 failures; `neg` fails exactly the expected sets (div_f32, sqrt_f32, div_f64, sqrt_f64,
div_f64_special, sqrt_f64_special).
