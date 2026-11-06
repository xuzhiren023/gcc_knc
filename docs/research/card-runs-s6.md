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
