# WRF optimization trials on KNC: plan (for the PhiWeather final optimization sprint)

Owner, 2026-11-08: the PhiWeather WRF project's final optimization sprint tests, at application
scale, optimizations that GCC-KNC and PhiNix plan to build later. GCC-KNC supplies this plan, a
card-side telemetry script (`telemetry.sh`) and an analysis script (`analyze.py`); PhiWeather runs
the trials in its own tree and writes results to
`C:\Users\xuzhi\Documents\card-coordination\wrf-trials\` (shared, outside both repos).

## 1. Questions and what each decides for us

| # | Trial | Question | Decides (GCC-KNC / PhiNix) |
|---|---|---|---|
| T1 | 2 MB pages for the large fields (root reserves `nr_hugepages`; WRF maps fields with `MAP_HUGETLB` or a hugetlbfs file) | How much time is TLB misses? Does software prefetch still matter inside a 2 MB page? | E5-13 allocator path; PhiNix huge pages; check C4 |
| T2 | Threads per core 2, 3, 4, with and without T1 | Was "2 per core is best" caused by the 64-entry TLB (about 29 arrays x 4 threads = 116 pages)? | ADR-0009 point 2 default |
| T3 | `OMP_WAIT_POLICY=PASSIVE` vs `ACTIVE`; `GOMP_SPINCOUNT` 0, 1e3, 1e5, default | Do spinning siblings steal issue slots from the working thread? (54-58% of thread time is barrier wait) | E6-03 spin-wait `delay` and spin count |
| T4 | Hand-kernel prefetch distances: `vprefetch1`/`vprefetch0` at (32,16), (64,32), (128,64) iterations, plus prefetching the first lines of the next 4 KB page | Best distances at application scale | E5-07; check C5 |
| T5 | `vmovnrngoaps` + fence for write-only outputs in the hand kernels | Do no-read stores help a real stencil code at 60 cores? | E5-08; check C1 |
| T6 | 64-byte alignment of the main arrays and 64-byte padding of per-thread reduction data | Alignment and false-sharing effect | E5-13, E5-16 |
| T7 | Barrier and fork microbenchmark at WRF's own team shape (8 ranks x 15 threads) | Baseline cost for a tree barrier | E6-03, check C11 |

Order: T1 first (it changes the baseline for everything else), then T2 with T1 on, then T3; T4-T6
only in kernels WRF already hand-wrote; T7 any time. One change per arm; the baseline arm is the
current production configuration.

## 2. The test case

Use WRF's existing short screen of the production domain (9 km parent + 3 km nest, 51 levels, the
production physics and the 8 x 15 layout), not a 24-h run:

- **Steady state only:** history and auxiliary output off (I/O is not under test and is 10-15% of
  wall time with a fixed cost per write); restart off; the same start time and inputs in every run.
- **Radiation inside the window:** radiation runs every 12th step (radt 9 min at dt 45 s), so the
  measured window must contain the same whole number of radiation steps in every arm (at least 2).
- **Deterministic:** the baseline must be bit-reproducible over repeats (WRF's 5x3 tiling is), so
  any output difference in an arm is the arm's doing. Arms that cannot change arithmetic (T1-T3, T6,
  T7) must stay bit-identical; T4-T5 must stay bit-identical too (prefetch and store kind do not
  change values). A non-identical arm is a bug, not a result.
- **The 24-h run** only confirms the final winning configuration, once, against the baseline.

## 3. How long (not too short, not too long)

A pilot sets the window before any arm runs:

1. Run the baseline screen 5 times with at least 72 steps (6 radiation steps).
2. `analyze.py --pilot` reads the per-step times from `rsl.out.0000`, drops the start-up steps
   (initialization and the first radiation step), and reports for each candidate window length N
   (24, 36, 48, 60 measured steps, always a whole number of 12-step radiation cycles): the median
   step time, its run-to-run spread, and how far it is from the 60-step value.
3. Choose the smallest N whose median is within 1% of the 60-step value and whose run-to-run spread
   is under 2%; that N plus the start-up steps is the screen length for every arm. Record it.

With WRF at about 4-6 s per step, N = 36 gives roughly 4 minutes per run.

**Repeats and order:** 5 runs per arm, interleaved with the baseline (B, A, B, A, ...) in the same
card window, so drift and the early slow regime (GCC-KNC found up to 20% launch-to-launch swings
from lagging threads) hit both arms alike. Decision statistic: the per-pair ratio
T_arm / T_baseline of median step time; `analyze.py` reports the median ratio and a bootstrap 95%
interval. A change counts only if the interval excludes 1 and the effect is above 2%; smaller
effects are reported as "no measurable effect".

**Card time budget (estimate):** pilot 5 x ~7 min; T1 10 runs; T2 30 runs (3 densities x 2 page
modes x 5); T3 25 runs; T4 20; T5 10; T6 10; T7 a few minutes. About 110 runs x ~5 min = 9-10 hours
of card time, to be scheduled in blocks under the announced-block rule.

## 4. Telemetry per run

`telemetry.sh` runs on the card beside the model (started by the job script, stopped at exit) and
writes CSV files into the run directory. It reads only `/proc` and `/sys`, once per second, so it
costs well under 0.1% of one core:

| File | Content | Why |
|---|---|---|
| `power.csv` | whole-card power from `/sys/class/micras/power` line 1 (microwatts) | energy per step (GCC-KNC S6-13 confirmed the format) |
| `mem.csv` | `HugePages_Total/Free/Rsvd`, `AnonHugePages`, `MemFree` | proves 2 MB pages are in use (T1) |
| `threads.csv` | per thread of the model: last CPU, voluntary and involuntary context switches, user and system ticks | placement, preemption, spin cost (T2, T3) |
| `env.txt` | all `OMP_*`/`GOMP_*`/`KMP_*` variables, `nr_hugepages`, clocksource, cpufreq governor and frequency, kernel and MPSS versions | reproducibility |
| `maps.txt` | one snapshot of `/proc/<pid>/smaps` lines `KernelPageSize`/`AnonHugePages` per mapping, 30 s into the run | proves which arrays sit on 2 MB pages |

Plus, from WRF itself: `rsl.out.0000` (per-step "Timing for main" lines, the decision data), the
model outputs' checksums for the bit-identity check, and, for one run per arm, WRF's existing
instruction-pointer profile (barrier-wait share).

## 5. Deliverables back to GCC-KNC

Per trial: `card-coordination/wrf-trials/<trial>/` with the raw run directories (rsl, CSVs), the
`analyze.py` report, and one paragraph: the arm, the median ratio with its interval, bit-identity,
the telemetry evidence (for example "HugePages in use: 3.1 GB"), and anything surprising. GCC-KNC
cites these in its own notes; PhiWeather stays independent.

## 6. Owner steps

- Huge-page reservation (root on the card), sized to WRF's need, recorded in the ledger notes and
  released after the trials: `echo <N> > /proc/sys/vm/nr_hugepages` (N x 2 MB). It reduces memory
  for other card jobs (GCC-KNC uses up to 6-7.5 GB), so reserve only during WRF trial blocks.
- Card time in announced blocks.
