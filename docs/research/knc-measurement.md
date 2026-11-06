# S6-01: KNC measurement proposal

Status: measured from six lead-run exclusive card windows. The 60-core,
four-thread production configuration meets the proposed <2% variation criterion;
density 3 does not. TSC invariance remains unproven. No compiler change.

Evidence shorthand: `R1` through `R6` mean
`.work/_shared/S6-01/claude-bench/run1.out` through `run6.out`, with physical
line numbers below. These outputs stay in the shared area. Intel 330991 pages
and Klemm slides are cited through [knc-microarch.md](knc-microarch.md), as the
lead directed; the Intel document itself is not stored locally.

## Proposed ADR protocol (one-page body)

1. **Clock.** Use `CLOCK_MONOTONIC_RAW` wall makespan; retain serialized RDTSC
   only as same-worker ticks. Observed rate is about 1232.199 MHz; neither
   absent invariant-TSC flags nor calibration against a TSC-backed OS clock
   proves invariance (R1:2,245,249,260-265,619-624; 330991 pp.35-37).
   Clock reads cost about 500-521 ns; serialized TSC about 259-277 ns
   (R1-R6:246-248). Record clocksource and power policy each launch.
2. **Placement.** Production is **60 cores (0-59), four workers/core, 240
   workers**. Group cpuinfo by core, sort siblings, and pin worker `c*d+t`
   to sibling `t`, for density `d=1,2,3,4`, over cores `0..N-1`.
   This card maps to CPU `4*c+1+t`; exclude OS-core CPUs `{0,241,242,243}`.
   `claude-pin` supplies the allowed mask; use checked singleton
   `sched_setaffinity` in each worker (R1:1-244,267-506).
3. **Footprints.** Align arrays to 64 bytes. For three FP32 arrays, per-worker
   lengths below budget approximately 12 KiB/core in L1, 192 KiB/core in L2,
   or 3 MiB/worker in memory. Count all siblings' live arrays; these are
   capacity budgets, not measured residency (330991 p.14; Klemm slides 13-14).

   | Threads/core | L1 | L2 | Memory |
   |---|---:|---:|---:|
   | 1 | 1024 | 16384 | 262144 |
   | 2 | 512 | 8192 | 262144 |
   | 3 | 336 | 5456 | 262144 |
   | 4 | 256 | 4096 | 262144 |

4. **Repetition.** Pinned first-touch, one pilot targeting 100 ms/batch, five
   groups each with three warm-up and 21 timed batches. Report median of group
   medians divided by batch, minimum, and full spread; retain every sample.
   Require <2% `(max-min)/median` both across group medians and across three
   independent launch medians. Production measured **0.128741%** across launches
   (R1-R3:266,617). Density 3 fails (R6:557); retain fixed sibling placement,
   report instability, and diagnose before accepting gains. More groups alone
   are not a demonstrated remedy.
5. **M2.** Tested length is elements/worker; work is `N*d*length`. Use
   `{15,16,17,255,256,257,1023,1024,1025,4096,16384,262144}` plus footprint
   rows, at N=1 and N=60 (16 FP32 lanes: Klemm slide 12). Compare identical
   inputs, placement, FP semantics and work with x87, disabling loop/SLP
   vectorization for baseline; alternate execution order. For normalized
   times, speedup=`T_x87/T_new`, throughput gain=`100*(speedup-1)%`, and
   time saved=`100*(1-T_new/T_x87)%`. No candidate gain measured here.
6. **Isolation.** Lead-only `card_run --benchmark` windows reserve cores 0-59,
   drain running coordinated jobs, and alternate queued projects. Stage before
   timing; exclude PhiWeather jobs and host transfers, which compete for shared
   ring/memory (Klemm slide 13). OS-core activity remains possible. Supplied
   windows report no overlapping jobs, but retain background daemons and residual
   noise (R1:636; R3:616). Validate noise each configuration.

## Native evidence and interpretation (outside the one-page protocol)

### Clock rate, resolution and policy

All six runs selected clock ID 4 (`CLOCK_MONOTONIC_RAW`). CPU MHz is 1238.094,
both `constant_tsc` and `nonstop_tsc` are absent, and extended CPUID leaf
0x80000007 EDX and its bit 8 are zero (R1-R6:1-245). Intel 327364-001 p.676,
table B.7 reserves that leaf and specifies zero; this is not a positive
invariance guarantee. Intel 330991 pp.35-37, via the microarchitecture note,
describes counter hooks without establishing invariance.

The start/end calibration ranges below include three sleeps and three busy
intervals per phase, each approximately 200 ms. Units are observed TSC MHz
against RAW, not a separately calibrated core frequency.

| Run | Start MHz range (lines 260-265) | End MHz range | End lines |
|---|---|---|---|
| R1 | 1232.147716-1232.198923 | 1232.189286-1232.199190 | 619-624 |
| R2 | 1232.156246-1232.198972 | 1232.189332-1232.199018 | 619-624 |
| R3 | 1232.150370-1232.197679 | 1232.190230-1232.198927 | 619-624 |
| R4 | 1232.156226-1232.198971 | 1232.157264-1232.198982 | 439-444 |
| R5 | 1232.150555-1232.198990 | 1232.157377-1232.199014 | 499-504 |
| R6 | 1232.152890-1232.199044 | 1232.156075-1232.199098 | 559-564 |

Busy calibrations cluster near **1232.199 MHz**, implying a nominal
**0.811557 ns/tick** on this clock scale. The full observed range differs by
only about 0.0042%, but the rate is about 0.476% below cpuinfo MHz. Do not
substitute cpuinfo MHz for the measured rate. Current clocksource is `tsc`,
so RAW and RDTSC are not independent references. These observations establish
neither absolute oscillator accuracy nor behavior across untested power states;
report wall time and TSC ticks separately, not invariant core cycles.

Record-10 bytes decode as follows, identically at start and end in all six
outputs. Evidence: R1-R6:249-259; end R1-R3:625-635, R4:445-455,
R5:505-515, R6:565-575. All record errno fields are zero.

| Interface | Decoded value (whitespace trimmed) |
|---|---|
| clocksource0/current_clocksource | `tsc` |
| clocksource0/available_clocksource | `tsc micetc` |
| cpu0/cpufreq/scaling_driver | `mic` |
| scaling_governor | `performance` |
| scaling_available_governors | `ondemand userspace performance` |
| scaling_min_freq | `619047` kHz |
| scaling_max_freq | `1238094` kHz |
| scaling_cur_freq | `1238094` kHz |
| scaling_available_frequencies | `619047 666666 714285 761904 857142 952380 1047618 1142856 1238094 1333332` kHz |
| scaling_setspeed | `<unsupported>` |
| cpufreq directory enumeration | success, empty value |

The listed 1333332 kHz option is above the configured maximum; it is not the
observed operating setting. These are endpoint snapshots, not continuous
frequency telemetry (R1:251-258,627-634).

| Timer | Minimum positive / median consecutive spacing | Amortized ns/read, six-run range |
|---|---|---:|
| RAW | 518-519 / 519 ns | 500.044-520.868 |
| Raw RDTSC | 28 / 28 ticks | 4.556-4.840 |
| CPUID/RDTSC/CPUID | 332 / 332 ticks | 258.971-276.697 |

Source: R1-R6:246-248. `clock_getres` actually reports **0 ns** here; record
that anomaly, not a claim of zero hardware resolution. Observed RAW read
spacing is about 0.519 us; intrinsic resolution was not independently resolved.
The spacing loop and amortized loop differ, so their numbers need not match.
Raw RDTSC is not serialized and is unsuitable for instruction boundaries.
Costs include loop overhead, and serialized intervals include CPUID boundary
cost. These costs are negligible relative to the measured approximately
70-87 ms batch medians (R1-R6 type 7 lines listed below). Use large batches,
not subtraction of these estimates from tiny measurements. Cross-core TSC
synchronization was not measured; worker-0 ticks are not the global makespan.

### Topology and working sets

The actual cpuinfo mapping is cores 0-59 -> logical CPUs `4*c+1 .. 4*c+4`;
core 60 -> `{0,241,242,243}` (R1:1-244). In all six windows the inherited
allowed mask is logical CPUs 1-240, including unused siblings at lower density.
Thus `--threads 60` with `--benchmark` still reserves all 60 cores; it does not
itself distribute 60 workers one per core. The probe does that with
`sched_setaffinity`. Requested and observed worker CPUs match in every printed
record: R1-R3:267-506, R4:267-326, R5:267-386, R6:267-446. Density 1 selects
sibling `{0}`, 2 selects `{0,1}`, 3 selects `{0,1,2}`, and 4 selects all four.
These are sorted sibling indices, not independently identified hardware slot
numbers. The probe also checks affinity and CPU before/after each batch.

Four hardware threads and at least two to sustain issue motivate the density
matrix (330991 p.14; Klemm slides 10-12). The controller is also pinned to core
0's first sibling; it waits at barriers during worker computation, but its
wakeups may contribute to measured skew. This is an implementation detail of
this probe, not evidence of a density-3 cause.

For the proposed three-array footprints, bytes/core are `12*d*length`:
L1 rows give 12288, 12288, 12096, 12288 bytes; L2 rows give 196608, 196608,
196416, 196608 bytes. Each length is a multiple of 16, so each FP32 array size
is also a multiple of 64 bytes. The memory row is 3 MiB/worker, or
180/360/540/720 MiB at 60 cores and density 1/2/3/4, exceeding the card's
61 x 512 KiB aggregate L2. Cache capacities and alignment come from 330991
p.14 and Klemm slides 13-14. Allocation alignment and capacity headroom do
not prove residency or eliminate set conflicts. Only the 262144-element
memory row at N=60 was measured here (R1-R6:266).

### Repetitions, independent windows and density 3

The kernel stores FP32 `c[i]=a[i]+2*b[i]`, using x87 in this build. Each
window has 105 timed batches, plus a pilot and 15 warm-up batches (R1-R6:266).
Records 6-8 contain **nanoseconds**, except the last field of record 6 which
is worker-0 TSC ticks. In particular, the lead's approximate 72.6M/80.7M
figures for density 3 are ns, not cycles.

| Run | Threads/core | Sweeps/batch | Median of group medians, ms/batch | ms/sweep | Group-median spread | Evidence lines: setup; summary; correctness; footer |
|---|---:|---:|---:|---:|---:|---|
| R1 | 4 | 8 | 81.472249 | 10.184031 | 0.929140% | 266;617;618;636 |
| R2 | 4 | 8 | 81.400454 | 10.175057 | 1.396219% | 266;617;618;636 |
| R3 | 4 | 8 | 81.367453 | 10.170932 | 0.827542% | 266;617;618;636 |
| R4 | 1 | 15 | 70.192813 | 4.679521 | 1.373987% | 266;437;438;456 |
| R5 | 2 | 13 | 87.103925 | 6.700302 | 0.822402% | 266;497;498;516 |
| R6 | 3 | 9 | 80.715113 | 8.968346 | **10.578920%** | 266;557;558;576 |

Three production launch medians give
`100*(10.184031125-10.170931625)/10.175056750 = 0.128741%`, below 2%.
This is measured independent-launch variation, distinct from the
0.827542-1.396219% within-launch group-median spreads. All windows report
zero incorrect elements. R1-R5 exit 0; **R6 exits 2**, in both `exit_code`
and `program_exit_code` of its JSON footer. The lead's initial statement that
all six exit 0 is contradicted by R6:576; this is a noise-criterion failure,
not an infrastructure or numerical-correctness failure.

The statistic resists isolated slow repetitions without hiding them: R3 group
4 has minimum 80.886880 ms, median 81.243706 ms, maximum 98.635492 ms,
full spread **21.846138%** (R3:616). Retain the minimum as a lower-bound
observation, not the primary comparison statistic. Density 1/2 have only one
launch each; their <2% between-group results do not establish independent-run
stability. Different densities also perform different total work, so their
raw times are not speedups.

Density 3 group medians in chronological order are 81.028543, 80.715113,
81.143456, 72.604669 and 79.500479 ms (R6:468,490,512,534,556).
All 21 samples in group 3 are 72.209009-73.832188 ms (R6:513-533).
The fast regime is therefore sustained, not a single outlier. A fixed
sibling set and successful pin checks rule out an intentional placement
change between these groups. They do not rule out phase-dependent issue,
L1 bank/set contention, barrier skew or ring/memory contention. Shared L1
and issue scheduling make those plausible hypotheses (Klemm slides 10-14),
but this 9 MiB/core working set is far larger than 32 KiB L1, and there are
no counters here to attribute the transition to L1 sharing or any one cause.
Endpoint clock policy is unchanged (R6:249-265,559-575).

**Decision for the ADR:** retain a fixed, reported sorted-sibling rule for
all comparisons; do not claim a special density-3 placement fixes the noise.
Density 3 is currently unstable and cannot support a <2% gain claim. For a
follow-up diagnosis, predeclare ten groups and three independent windows for
each of the four fixed three-of-four sibling subsets, with identical work,
control-thread placement and power policy. Report all regimes and spreads;
do not keep adding groups until a pass or select only the fast regime.
More groups would characterize persistence, not guarantee stability, and
changing sibling subsets would test the placement hypothesis. This additional
experiment is a recommendation, not a run performed or required to accept the
measured production protocol in this ticket.

### Interference and limits of exclusivity

`tools/card_run:302-318` implements draining coordinated jobs and round-robin
admission of queued benchmarks, taking all cores 0-59. R1-R6 JSON footers
(lines 636/636/636/456/516/576) show `overlapping_jobs=[]`, a 2048 MiB budget,
and the same boot ID before and after each job. The foreign-process lists
still contain system daemons such as `coi_daemon`, `sshd`, `udevd` and logging
services; exclusivity is not absence of OS work. Core 60 is excluded from
workers (R1:1,242-244). PhiWeather compute and host DMA/transfers can compete
for the ring and memory system (Klemm slide 13); coordinate them through the
same benchmark window and finish staging before timing. Unregistered work,
interrupts, temperature and controller wakeups remain possible disturbances.
No supplied counter evidence identifies the cause of the R3 outlier or R6
regimes, so exclusivity does not replace the measured noise gate.

## Probe handoff and output key (outside the one-page protocol)

Source: `tests/regress/knc-timing-probe.c`. Shared output:
`.work/_shared/S6-01/knc-timing-probe.mic`. Built with shared GCC **16.2.0**,
`-march=knc -O2 -ffp-contract=off -Wall -Wextra -Werror -pthread -lrt` and the
shared sysroot. Assembly inspection shows the stream loop uses x87; this is the
FP32 storage streaming baseline, not a claim about IMCI performance. No GCC
checkout changes or GCC rebuild. Both assembly and linked ELF passed `knc_lint`.

Lead-only commands used for the six supplied results (not executed by the
engineer). Each line is a separately admitted exclusive window; the first three
are production launches, followed by densities 1, 2 and 3:

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
The memory row has been measured at all four densities, with three production
windows. Other footprint cases and N=1 remain proposed, not measured here.

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
rate calibration is not independent. The decoded native results and start/end
rates are recorded above. Neither matching rates nor absent flags establishes
invariance over untested power states.

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
the invocation. This completion changes only the research note; the previously
built/linted probe is unchanged, so no build or test was repeated. Native
results supplied by the lead are analyzed above; density 3 failed the noise
criterion, while the production configuration met it.
