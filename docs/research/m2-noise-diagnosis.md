# M2 within-launch noise: diagnosis and protocol fix

Lead's subagent, 2026-11-06, from the sample lines of every 60-core M2 run on disk
(`.work/_shared/tmp/claude-s6-m2final/`, `claude-s6-placement/`, `claude-s6-slot5/` launches 2-3,
`claude-s6-m2-test/l2-1.out`): 199 build measurements, 24 with `within_launch_ok=0`. Parser:
`scratchpad/m2noise/{parse,steps,series,gf}.py` (session scratchpad, not in the repo). No card job
was run for this note; the jobs at the end are what the lead runs next.

## What the sample lines show (proven from the data)

1. **The failures are step changes, not drift or outliers.** A large failure is one sharp drop of the
   makespan between two consecutive batches, sustained for the rest of the build. Within-group
   spreads stay normal on both sides of the step.

   | Run | Build (position) | Group medians vs launch median | Step | Step time |
   |---|---|---|---|---|
   | m2final len 4096, launch 1, gcc | first | +0.0 +0.4 +0.4 **-12.4 -12.2** % | -14% in one batch (92.7 to 79.8 ms) | 6.5 s into the first build |
   | m2final len 15, launch 1, gcc | first | +1.1 +1.4 +0.0 **-10.8 -11.7** | -12% | 6.6 s |
   | m2final len 17, launch 2, imci | first | +0.3 +0.3 +0.3 **-7.6 -7.6** | -8% | 6.9 s |
   | placement len 4096, launch 2, imci | first | +0.2 +0.1 +0.0 **-18.1 -18.2** | -17% | 6.2 s |
   | slot5 working set L2, launch 3, gcc | first | +0.0 +0.0 +1.4 **-9.8 -9.4** | -10% | 6.5 s |
   | m2final working set L2, launch 1, gcc / imci | first / third | 2.5% / 2.6% jitter, no step | slow regime for the whole launch (`w0/mk` 0.77 for both) | - |

   Every large step is **downward** (the early groups are the slow ones) and lands **6.2-6.9 s after
   the first build's pilot starts**, which is about 10 s after exec (`correctness()` takes 3-4 s).
   The regime does not return later in those launches.
2. **The first build after the threads start is the one that fails.** 19 of the 24 flagged builds are
   at position 0 (65 builds), 3 at position 1 and 2 at position 2 (67 each). Launch parity does not
   matter beyond deciding which build is first (gcc in odd launches, imci in even ones).
3. **Worker 0 usually does not move; another worker does.** `cycles_per_element` is worker 0's own
   time. In the length-4096 step, worker 0 dropped 2.5% while the makespan dropped 13%; the ratio
   of worker 0's time to the makespan (`w0/mk`) went from 0.83-0.85 to 0.94. In 15 of the 24 flagged
   builds worker 0's group spread is under half the makespan's. So the slow regime is **one or more
   straggler workers elsewhere**, 15-20% slower than worker 0, not a uniform slowdown. (In 9 cases
   worker 0 was itself among the stragglers; e.g. placement len 4096 launch 1 gcc: worker 0 stepped
   -12% at 6.1 s while the makespan did not move, because other stragglers remained.)
4. **The same stragglers explain the 18-21% cross-launch variation at L2.** Worker 0's own time per
   element at length 4096 (gcc) is 3.10-3.17 ns in every launch (2% range; 3.31 in the one launch
   where worker 0 was in the slow regime), while the makespan figure moves 0.01372-0.01708
   (24%). `w0/mk` for gcc at 4096 per launch: 0.85 0.94 0.77 0.94 0.87 0.94 0.78 0.77 0.89 0.76 0.94
   0.94; x87 is 0.92 in all twelve. A launch is "slow" when its stragglers never leave. Physical page
   placement (amendment 1's hypothesis) cannot switch off in one batch at 6.5 s, and would hit
   worker 0 as often as anyone; the data does not support it as the main cause.
5. **It is per CPU, not thermal, power, ring or memory bandwidth.** The L1-resident length 15 (no
   ring traffic) shows the same 12% step as L2; 1-core x 4 runs are clean in every build (`w0/mk`
   0.999, group spreads under 1%); the clock reads 1238094 kHz at both ends. A frequency or ring
   effect would hit worker 0 like everyone else.
6. **x87 at cache sizes is insensitive**, which is why x87 is always clean there: its per-worker
   time is 30.4 ns per element, 10x the vector builds, and the stragglers' extra time is small
   against it (`w0/mk` 0.92). At memory size x87's makespan is 1.8x worker 0's own time
   (`w0/mk` 0.54-0.61 in six launches, within-group spreads 10-76%): an unexplained, larger
   straggler effect that only lowers the x87 baseline (gcc/x87 = 0.32 there, no false pass risk).
7. **The gain fraction is regime-invariant when both vector builds are measured in the same
   regime.** Per-group GF in the clean launches: spread 0.2-1.8% (4 of 30 clean launches 2-2.8%,
   all at short lengths or 16384). At L2 every fast-regime group gives GF 0.796-0.803 (l2-1, L2-2,
   groups 3-4 of 4096-1 and 4096-2); the launch figures 0.69, 0.74, 0.99 are launches where gcc and
   imci sat in different regimes (one slow, one fast). M2's 0.5 threshold is met in every regime
   seen; only the validity rule fails.

## Mechanism

- **Proven:** sustained per-CPU slowdowns of some workers (not a global effect), switching in one
  batch, ending at a near-constant time after the threads start when they end at all, or lasting the
  whole launch.
- **Suggested:** OS activity on worker CPUs (a task or kernel thread that stays runnable on one or
  a few worker CPUs, or on a sibling of a straggler and shares the in-order core's pipeline), ending
  around 10 s after exec. `card_run` opens its first output-read ssh connection at start+10 s and
  polls `cat status` on the control session at 0.5, 1.5, 3.5, 7.5, 12.5 s; a coincidence to test,
  not a finding. S6-01's density-3 bimodality (11%, sustained groups) has the same signature; an
  idle sibling attracts OS work, which then shares the core with the three workers.
- **Not supported:** physical page placement as the main cause (point 4); thermal, power or ring
  regime (point 5); the pilot or re-sizing (fixed repetitions on both sides of the step); barrier
  wake-up cost (would be a fixed cost per batch, visible in every build, not a 6.5 s regime).
- **Unknown, and what distinguishes it:** whether the straggler CPUs are fixed for a regime and
  whether they are preempted. The driver now prints, per batch, the slowest worker and its time,
  the median worker time, the wake-up skew, and `getrusage(RUSAGE_THREAD)` involuntary context
  switches and system time summed over workers and for the worst worker. Preemptions or system time
  on the straggler during the slow regime prove OS activity; a straggler with zero preemptions and a
  longer own time is a hardware effect of its core or its pages. Job A below decides this.

## The fix (`tests/acceptance/m2_kernels/`, built in `.work/_shared/M2-diag/`)

1. **Interleave the builds round by round.** Each group is 3 warm-up + 21 timed *rounds*; a round
   runs gcc, x87 and imci once each, the starting build rotating with the round (even launches
   rotate the other way, keeping the old parity convention). A regime change now hits the three
   builds within 100 ms of each other. Per-build group medians, `group` and `summary` lines keep
   their format; a `pair` line per group gives the same-group `gcc_over_x87`, `imci_over_x87`,
   `gcc_over_imci` and `gain_fraction`.
2. **Paired validity rule.** `launch ... paired_ok=1` (exit 0) when every build is sized 50-200 ms
   and the five same-group gain fractions agree within 2% (`gain_fraction_spread`); when the IMCI
   denominator is not positive in some group, `gcc_over_imci_spread` is used instead. Per-build
   spreads are still printed with `within_launch_ok` but no longer set the exit code. The launch
   figure and arithmetic of ADR-0010 point 6 are unchanged; `gcc_over_x87_max` over groups is
   printed for the 5% rule (conservative: the worst group).
3. **Global warm-up of 10 s** of interleaved rounds before group 0 (`--warmup-seconds`, 0..60;
   every warm-up sample is printed with `group=-1`). Justified by the 6.2-6.9 s clustering; not a
   guarantee (some launches stay slow throughout), which is why point 2 is the real fix.
4. **Straggler diagnostics** on every sample line (`t_ms max_worker max_ns median_ns skew_ns
   nivcsw nivcsw_max nivcsw_worker stime_us`), read outside the timed window.

Why this and not more groups or a per-build retry: the quantity M2 decides on is the gain
fraction, and the data shows it is stable to 1-2% across groups whenever gcc and imci share the
regime, and off by 16% when they do not. Interleaving removes the only thing that made launches
invalid without touching any sample. The 2% rule stays as strict as before, on the decision quantity.

ADR-0010 needs an amendment for point 2 (the validity rule) and point 1; the lead decides, and the
owner accepted amendment 1, so this is theirs to confirm. The gcc/x87 time ratio is **not**
regime-invariant (x87 is insensitive, gcc is not), so the 5% rule is judged per group, worst case.

**Kernel code is unchanged.** The current `xgcc` (`gcc-build/gcc/cc1.exe` rebuilt 17:13 today)
produces `kernels-gcc.s` and `kernels-x87.s` that differ from M2-final (210 diff lines, different
scheduling and address arithmetic), so M2-diag links **M2-final's `kernels-gcc.o` and
`kernels-x87.o`** (`build.py --reuse-kernels M2-final`; objects verified byte-identical). Both
binaries linted; `--correctness` and the negative build are unchanged in behavior.

**GCC-KNC bug found on the way.** The 17:13 `xgcc` ICEs on the first version of the new `batch()`
(`.work/_shared/M2-diag/timing-ice.c`): cprop_hardreg emits `(set (reg:QI k1) (const_int 0))`
for a loop-store-motion flag and `*knc_movqi` has no alternative for an immediate into a mask
register (`recog.cc:2793`, pass `cprop_hardreg`). A conditional update of a static struct field
inside a loop at `-O2` triggers it. Worked around in the driver with local accumulators; needs a
ticket (mask registers must not be an allocation class for QImode immediates, or the pattern needs
the alternative).

## Card jobs for the lead

Script: `.work/_shared/tmp/claude-s6-m2diag.sh` (same form as `claude-s6-m2final.sh`; 6 GiB config;
binary `.work/_shared/M2-diag`; outputs `.work/_shared/tmp/claude-s6-m2diag/`). Run after the
current M2-final block. About 9 card-minutes.

| Job | Command (after the `$CR` prefix) | Look at | Confirms / refutes |
|---|---|---|---|
| 0a, 0b | `--timeout 900 $K/m2-negative.mic --correctness`; `$K/m2-kernels.mic --correctness` | exit 1 with `affine_f32 failing_cases=154`, others 0; exit 0 | driver still correct |
| A1 | `--benchmark --threads 240 $K/m2-kernels.mic --benchmark --kernel affine_f32 --working-set L2 --density 4 --cores 60 --launch 1 --warmup-seconds 0` | warm-up/timed samples with `t_ms` < 12000: `max_ns/median_ns`, `max_worker`, `nivcsw_max`, `stime_us`; the `phase name=correctness_done t_ms` line | Slow regime visible as `max_ns` 10-20% above `median_ns` with `max_worker` fixed and `nivcsw_max`/`stime_us` > 0 on it: **OS activity on that CPU** (then ask what runs there: a `ps -o pid,psr,comm` during a run from the control session). Same with `nivcsw`=0 and `stime_us`=0: **hardware effect of that core or its pages** (then it is placement after all, and a rerun with the stagger changed tells). No slow regime at all: the regime is intermittent; A2 and job B's warm-up samples will show it over more launches. |
| A2 | same as A1 with `--length 15` | same fields | The L1-resident case; the same straggler CPUs as A1 point to the CPU, different ones to the data. |
| B1-B5 | `... --working-set L2 ... --launch N` (default 10 s warm-up), N = 1..5 | `launch` line: `paired_ok`, `gain_fraction`, `gain_fraction_spread`, `gcc_over_imci_spread`; `summary` lines' `group_spread`; warm-up samples with `t_ms` for a step | **Fix works:** `paired_ok=1` in all five with `gain_fraction` about 0.80 and `gain_fraction_spread` under 2% even where a per-build `group_spread` is over 2%. **Refuted:** `gain_fraction_spread` over 2% while the per-build spreads are also over 2% in the same group pattern means gcc and imci are not hit alike (then the stragglers are data-dependent, and the pair line shows which build moved). If `gcc_over_imci_spread` passes where `gain_fraction_spread` fails, x87 noise is the cause and the gate should move to the ratio. |

If B passes, the full baseline (`claude-s6-m2final.sh` with `K=.work/_shared/M2-diag`) is the next
block: 42 jobs per launch as before, the M2 decision from `launch` lines.
