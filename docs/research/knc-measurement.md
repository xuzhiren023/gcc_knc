# S6-01: KNC measurement proposal

Status: host build and lint passed; **no native measurements yet**. The lead must
run the probe before accepting the clock rate, topology or <2% noise claim.
Record numbers below describe an output schema, not observations. S5-19 describes
topology discovery but its ticket contains no captured `/proc/cpuinfo` mapping.

## Proposed ADR protocol (one-page body)

1. **Clock.** Use `clock_gettime(CLOCK_MONOTONIC_RAW)`, falling back to
   `CLOCK_MONOTONIC`, for elapsed time. Record resolution, read spacing and cost
   (record 3). Use serialized RDTSC for same-worker ticks, not invariant core
   cycles: Intel 327364-001 p.676, table B.7, reserves CPUID.80000007H, returning
   zero. Actual rate/invariance remain pending CPU MHz/flags (1), CPUID (2),
   start/end sleep/busy calibration against MONOTONIC_RAW (4), and clocksource /
   power policy (10). TSC invariance is unproven; 330991 pp.35–37, as cited in
   `knc-microarch.md`, describe measurement hooks, not an invariant-rate guarantee.
2. **Placement.** Production means **60 cores, IDs 0–59, four workers per core,
   240 workers**; exclude OS core 60. Also measure densities 1, 2, 3 and 4 over
   N=1 and N=60 cores. Group `/proc/cpuinfo` by `core id`, sort logical IDs, and
   pin worker `c*d+t` to entry `t` of core `c`; never assume `4*core+thread`.
   `claude-pin` sets the inherited allowed mask; workers restrict it to singletons
   with `sched_setaffinity`, checking the mask and `sched_getcpu` (records 1, 5;
   pending). Motivation: four hardware threads, minimum two for full issue
   (330991 p.14; Klemm slides 10–12, via `knc-microarch.md`).
3. **Footprints.** Align each array to 64 bytes; budget the sum of all live arrays
   across siblings. For three FP32 arrays use these per-thread lengths, leaving
   headroom in 32 KiB L1 / 512 KiB L2 per core (330991 p.14; Klemm slides 13–14):

   | Threads/core | L1 length | L2 length | Memory length |
   |---|---:|---:|---:|
   | 1 | 1024 | 16384 | 262144 |
   | 2 | 512 | 8192 | 262144 |
   | 3 | 336 | 5456 | 262144 |
   | 4 | 256 | 4096 | 262144 |

   Footprints: approximately 12 KiB/core, 192 KiB/core, 3 MiB/thread respectively;
   the memory case exceeds aggregate card L2 at N=60.
4. **Repetitions.** First-touch on pinned workers; pilot one sweep, choose a common
   batch targeting 100 ms, then five groups of three warm-up batches and 21 timed
   batches. Time earliest worker start to latest finish, excluding allocation,
   printing and verification. Report median/batch, minimum/batch and full spread.
   Records 6–8 measure within-process stability. Require three fresh exclusive
   launches with `(max-min)/median < 2%` across batch-normalized run medians.
   Keep all results. This criterion remains **unmeasured**.
5. **M2 comparison.** A tested length is elements **per worker**; total work is
   `N*d*length`. Propose `{15,16,17,255,256,257,1023,1024,1025,4096,16384,262144}`
   plus the footprint rows above: 16 FP32 lanes and 64-byte cache lines motivate
   boundary cases (Klemm slides 12–14). Compare identical inputs, placement,
   FP semantics and work with x87 (disable loop/SLP vectorization); alternate
   baseline/candidate order across launches. Speedup is `T_x87/T_new`;
   throughput gain is `100*(speedup-1)%`, time saved is `100*(1-T_new/T_x87)%`.
   Report every length/density; native gains are pending.
6. **Isolation.** Only the lead uses `card_run --benchmark`: it reserves cores
   0–59, drains running jobs and arbitrates queued benchmarks round-robin
   (S5-19; `tools/card_run`). PhiWeather jobs/transfers compete for ring/memory
   (Klemm slide 13). Stage first; exclude transfers during timing. OS interrupts,
   thermal drift and unregistered activity remain possible; measure residual
   noise with records 6–8 (pending).

## Probe handoff and output key (outside the one-page protocol)

Source: `tests/regress/knc-timing-probe.c`. Shared output:
`.work/_shared/S6-01/knc-timing-probe.mic`. Built with shared GCC **16.2.0**,
`-march=knc -O2 -ffp-contract=off -Wall -Wextra -Werror -pthread -lrt` and the
shared sysroot. Assembly inspection shows the stream loop uses x87; this is the
FP32 storage streaming baseline, not a claim about IMCI performance. No GCC
checkout changes or GCC rebuild. Both assembly and linked ELF passed `knc_lint`.

Lead-only commands from this worktree (not executed by the engineer). Run each
line as a separately admitted exclusive window; the first three are independent
production launches, followed by densities 1, 2 and 3:

```text
python tools/card_run --benchmark --threads 240 --timeout 300 ../_shared/S6-01/knc-timing-probe.mic 60 4 262144
python tools/card_run --benchmark --threads 240 --timeout 300 ../_shared/S6-01/knc-timing-probe.mic 60 4 262144
python tools/card_run --benchmark --threads 240 --timeout 300 ../_shared/S6-01/knc-timing-probe.mic 60 4 262144
python tools/card_run --benchmark --threads 60 --timeout 300 ../_shared/S6-01/knc-timing-probe.mic 60 1 262144
python tools/card_run --benchmark --threads 120 --timeout 300 ../_shared/S6-01/knc-timing-probe.mic 60 2 262144
python tools/card_run --benchmark --threads 180 --timeout 300 ../_shared/S6-01/knc-timing-probe.mic 60 3 262144
```

Use a card configuration with **at least 2048 MiB memory budget** for this case
(720 MiB arrays plus stacks/runtime). `card_run` has no memory CLI override;
its config's `memoryMB` must permit this allocation. Maximum CLI length is
1048576; that can require over 3 GiB with 240 workers. No program arguments
defaults to `60 4 262144`; otherwise arguments are `cores density length`.
The lead should first measure the memory row at all four densities; collect the
other footprint cases for the proposed cache protocol. Repeat the production
case in three independent admitted windows to evaluate run-to-run noise.

Whitespace-separated, numbers-only stdout, first column is record type:

| Type | Remaining columns |
|---|---|
| 0 | schema=2, cores, density, length/thread, batch, groups=5, reps=21, warmups=3 |
| 1 | logical CPU, core ID, cpuinfo MHz, constant_tsc flag, nonstop_tsc flag, inherited-allowed flag |
| 2 | maximum extended CPUID leaf, leaf 80000007 EDX, bit 8 |
| 3 | kind (0=wall, 1=raw RDTSC, 2=serialized RDTSC), wall clock ID, clock_getres ns (0 for TSC), minimum positive delta, median delta, amortized ns/read |
| 4 | phase (0=start, 1=end), mode (0=sleep, 1=busy), trial, calibration clock ID, errno (0=success), elapsed ns, TSC ticks, observed TSC MHz |
| 5 | worker, core, sorted sibling index, requested logical CPU, observed CPU |
| 6 | group, repetition, elapsed makespan ns, worker-0 serialized TSC ticks |
| 7 | group, minimum ns, median ns, maximum ns, full spread percent |
| 8 | minimum group median ns, median of group medians ns, maximum group median ns, spread percent, below-2-percent flag |
| 9 | incorrect output elements (must be zero) |
| 10 | phase (0=start, 1=end), errno (0=success), path byte count, value byte count, path bytes then value bytes (each unsigned decimal ASCII, including whitespace) |
| 99 | failure stage (see source), errno/pthread error or offending value |

Types 1–4 and 10 first appear before type 0; end-phase types 4 and 10 follow
type 9 after workers join. Type 10 captures `current_clocksource` and
`available_clocksource` under `/sys/devices/system/clocksource/clocksource0/`,
and every `scaling*` or governor-named file under
`/sys/devices/system/cpu/cpu0/cpufreq/`. A directory record with empty value
reports enumeration status; missing/unreadable paths retain their errno.
Values are preserved verbatim as decimal bytes, so unknown clocksource and
governor names remain recoverable without violating numbers-only stdout.
For example, value bytes `116 115 99 10` decode to `tsc` followed by newline.
Values above 4096 bytes report EOVERFLOW with the captured prefix.
Type 1 already captures CPU MHz and both requested TSC flags for every CPU.
Type 3 deltas are ns for kind 0 and ticks otherwise;
minimum delta is observed read spacing, **not** the intrinsic hardware resolution.
The amortized cost includes loop overhead. Serialized reads bracket RDTSC with
CPUID on both sides; the measured interval includes boundary cost. TSC resolution
in seconds requires a validated measured rate; 1/rate is only nominal tick size.
Never subtract worker-0 ticks from another core's timestamp or equate them to
the global makespan. Type 4 uses CLOCK_MONOTONIC_RAW explicitly, even if the
wall timer falls back to MONOTONIC. If RAW is unavailable, mode/trial are -1,
errno is nonzero and durations/rate are zero (clock ID -1 if not compiled in);
this is missing calibration evidence, not a zero TSC rate. Six rate trials at
each of start and end cover the same pinned CPU and cannot prove
invariance across all power states; if the OS clocksource itself uses TSC, the
rate calibration is not independent. Compare start/end rates and decode type 10
with the lead's native results before choosing TSC for comparisons. Neither
matching rates nor absent flags establishes invariance over untested power states.

The pilot targets 100 ms; inspect actual type-6 durations because first-pass
cache/startup effects can change subsequent batch times. Check that timer cost
is negligible relative to observed duration; revise batching if noise fails.
Do not silently drop a slow sample. Exit 0 requires correct results and <2%
between-group spread; exit 2 means noise criterion failed, exit 1 means error.
Even exit 0 does not establish run-to-run stability without independent launches.

Schema-2 rebuild log: `.work/_state/logs/S6_01_probe_build-20261106-075350.log`.
Assembly/ELF lint log: `.work/_state/logs/S6_01_probe_lint-20261106-075407.log`.
Both passed. An initial shell invocation failed before compilation because
prepending Cygwin to PATH shadowed Windows Python; resolving Python first fixed
the invocation. Native output, actual CPU mapping, TSC
rate/cost, and <2% independent-run evidence remain pending the lead's card run.
