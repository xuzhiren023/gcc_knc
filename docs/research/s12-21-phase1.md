# S12-21 phase-one density and IMUL diagnostic

The lead authorized recovery into `.work/_shared/S12-21/r2/` after stopping
the duplicate session. The old mixed outputs under `.work/_shared/S12-21/`
remain untouched and must not be run. Stage, package and collect share one
output-directory constant. Staging refuses any nonempty destination before
building, preventing stale assembly from entering the census.

The recovered stage uses gzip and one copy of each runtime DSO to stay within
the card runner's 64 MiB payload limit. All 28 fresh builds and lints passed. The compressed payload is
16,329,850 bytes after the card-window fix; package size and shell syntax
checks passed during repackaging.

This phase uses the installed `gcc-knc-16.2.0` prefix and the fourteen
development programs only. There is no GCC source or default change.
The comparison is serial `-O2 -march=knc` versus the same flags plus
`--param=knc-threads-per-core=1`. The lead corrected the ticket's nonexistent
`-mknc-density` spelling during red review.

## Code census

`tools/s12_21_stage.py` builds and lints each variant once, retaining compiler
assembly under `.work/_shared/S12-21/r2/{default,density1}/PROGRAM/`.
`code-summary.json` records instruction counts, IMUL counts, backward loops,
and static loop-carried register counts. `code/PROGRAM.json` contains the
normalized instruction sequence per function, each IMUL's zero-based
instruction position, backward-loop intervals and their register sets, and
the changed instruction ranges for each variant.

Normalization removes assembler directives/comments and canonicalizes local
numeric labels by first use within each function. Function and data-symbol
names, instructions and operands remain. A sequence diff is computed per
function; each changed block contributes the larger of its two instruction
counts. The four programs with the largest totals are selected, with program
name as the deterministic tie-breaker. These are static code differences,
not hot-path weights or predictions of performance.

The chain count is explicitly a static recurrence census: within each
backward-branch interval, count registers read before their first write that
are also written in the interval. General-register width aliases are merged;
stack/frame pointers, flags, memory dependencies and implicit x87 stack state
are excluded. Nested loop intervals are counted separately. Vector-register
and IMUL-destination subsets are also recorded. This approximation does not
claim to recover GCC's chosen unroll factor, dynamic critical paths, or
path-sensitive data flow.

Recovered static census (each count pair is default / density 1):

| Program | Changed instructions | Instructions | IMUL | Register chains |
| --- | ---: | ---: | ---: | ---: |
| PB-gemm | 282 | 796 / 820 | 2 / 2 | 65 / 65 |
| PB-atax | 471 | 804 / 838 | 2 / 2 | 168 / 168 |
| PB-cholesky | 60 | 631 / 635 | 2 / 2 | 75 / 75 |
| PB-ludcmp | 778 | 1419 / 1088 | 2 / 2 | 268 / 163 |
| PB-jacobi-2d | 96 | 870 / 870 | 2 / 2 | 98 / 98 |
| PB-heat-3d | 157 | 796 / 796 | 2 / 2 | 198 / 198 |
| STREAM | 449 | 885 / 851 | 0 / 0 | 81 / 81 |
| NPB-CG | 3470 | 5155 / 5135 | 11 / 11 | 1663 / 1519 |
| NPB-EP | 147 | 1382 / 1387 | 11 / 11 | 95 / 95 |
| NPB-MG | 4249 | 9086 / 9011 | 64 / 65 | 2173 / 2147 |
| NPB-IS | 216 | 1310 / 1267 | 2 / 2 | 142 / 142 |
| HPCG | 1333 | 6701 / 6437 | 35 / 35 | 831 / 809 |
| zlib | 1041 | 11419 / 11419 | 19 / 19 | 2738 / 2738 |
| SQLite | 15191 | 171426 / 171601 | 529 / 529 | 37997 / 38078 |

## Staged card experiment

The lead entry point is `.work/_shared/S12-21/r2/batch.sh`, with `payload.tar.gz`
listed in `files.txt`. It uses one exclusive `full` reservation, a 1740-second
outer deadline enforced by `card_run`. The 120-second IMUL and 24 workload
budgets of 60 seconds each (1560 seconds total) are estimates, not enforced
inner deadlines: the card BusyBox has no `timeout` command. A nonzero exit
stops the batch; the runner bounds the entire job. Fixed corpus sizes are
retained; an incomplete batch requires lead review, not smaller input.

The IMUL executable pins itself to one granted CPU and reports actual
affinity, core/sibling topology, available frequency before/after, and timer
overhead. Its eight assembly kernels cover 32/64-bit register and hot-memory
operands, each with one dependent chain or eight independent chains. Each
iteration contains 64 multiplies; each case runs 200000 iterations after a
short warm-up, for three samples. Results are checked against modular
exponentiation outside the timed region. The disassembly is `imul.asm`.

Samples report serialized TSC ticks and `CLOCK_MONOTONIC_RAW` elapsed time.
Ticks/op include loop overhead; the back-to-back timer cost is reported and
not subtracted. Independent-stream ticks/op measure throughput, not latency.
TSC ticks must not be called core cycles without reviewing actual clock
conditions. Memory forms reuse one warmed operand and do not measure cache
miss latency. R02 p.56 motivates this experiment; no published ten-cycle
number is asserted as a native result.

The selected programs run three adjacent pairs, alternating default/density1,
density1/default, default/density1. The existing corpus launcher pins the
serial child to the first granted CPU, records launch-to-exit timing, and
preserves each program's correctness output. Both variants use the same
fixed input and runtime prefix. zlib additionally cross-decodes with the
opposite density build and rejects a corrupted stream.

After the lead saves combined stdout/stderr as `native.log`, the `collect`
subcommand rejects missing, duplicate, reordered or incomplete pairs and
IMUL samples, validates corpus correctness output, compares full PolyBench
arrays and HPCG work where applicable, and checks paired affinity. It writes
the three default/density1 time ratios and their median to
`native-analysis.json`. The lead must also review reservation/environment
evidence and variation before deciding whether phase two is justified.

From the project root, lead only:

```text
python tools/card_run --benchmark --profile full --threads 240 --timeout 1740 --file-list .work/_shared/S12-21/r2/files.txt .work/_shared/S12-21/r2/batch.sh
python tools/s12_21_stage.py collect .work/_shared/S12-21/r2/native.log
```

The four staging-contract tests passed, including rejection of an existing
assembly tree before building:
`.work/_state/logs/s12_21_r2_contracts-20261114-160635.log`.
The complete fresh stage passed in 5.7 minutes, building/linting all 28 serial
variants, the launcher and the eight-form IMUL executable, and generating the
census and compressed package:
`.work/_state/logs/s12_21_r2_stage-20261114-160641.log`.
The measured code-difference selection is SQLite, NPB-MG, NPB-CG and HPCG.
The lead's first card window exited 127 in 22 seconds because BusyBox has no
`timeout`; extraction also warned about pax extended headers. That is an
infrastructure failure, with no native latency, speedup, or phase-two
eligibility result. Lead output:
`.work/_shared/tmp/claude-s12-window1/s12-21-sched.out`.

The card-window fix removes both shell `timeout` invocations and writes the
payload and zlib peer archives in ustar format. The existing r2 binaries were
repackaged without rebuilding. All four contracts passed:
`.work/_state/logs/s12_21_window_fix_contracts-20261114-175732.log`.
The refreshed package passed its size and shell syntax checks:
`.work/_state/logs/s12_21_window_fix_package-20261114-175739.log`.
The lead command above is ready for the next window; no engineer card run
was made. x86 identity and ICE sweeps are not phase-one checks.

## Card window 2: completed-prefix evidence and phase-two decision

The lead's second window reached the 1740-second card deadline (exit 124).
The log has **12 completed variant runs, or six A/B pairs**, not 12 complete
A/B pairs. Runs 0 through 11 finished; run 12 (NPB-CG, density 1, repetition
1) started but has no timing or completion marker. The batch did not pass,
and the original three-pair-per-program acceptance was not completed.

Per the lead's 20:19 instruction to collect the completed prefix, a one-off
analysis is saved at `.work/_shared/S12-21/r2/collect-window2.py`. The normal
`collect` command requires the entire batch and remains unchanged. The
one-off analysis checks the exact contiguous BEGIN/END sequence, all 24
IMUL samples and their PASS marker, and the timeout result. It uses
`corpus.output_result` for every completed run, retaining the timing,
correctness, paired affinity and equal-work checks. All 12 completed runs
passed these checks. HPCG executed one set in each variant, with 50
reference and 51 optimized iterations in each. Run 12 is excluded.

Run from this worktree:

```text
python tools/run.py --name s12-21-window2-collect --inputs ../_shared/S12-21/r2/collect-window2.py ../_shared/S12-21/r2/native.log ../_shared/S12-21/r2/card-plan.json tools/corpus.py -- python ../_shared/S12-21/r2/collect-window2.py
```

Analysis completed successfully; log:
`.work/_state/logs/s12_21_window2_collect-20261114-202215.log`.
Machine-readable results are in `.work/_shared/S12-21/r2/native-analysis.json`.
This is analysis of the lead's native run, not another card execution or a
claim that the timed-out batch passed.

Launch-to-exit seconds and default/density-1 ratios (greater than one favors
density 1):

| Program | Repetition | Default seconds | Density 1 seconds | Ratio |
| --- | ---: | ---: | ---: | ---: |
| SQLite | 0 | 1.790561 | 1.793010 | 0.998634 |
| SQLite | 1 | 1.773421 | 1.761188 | 1.006946 |
| NPB-MG | 0 | 21.299893 | 23.168503 | 0.919347 |
| NPB-MG | 1 | 21.321205 | 23.163091 | 0.920482 |
| NPB-CG | 0 | 29.676750 | 29.188097 | 1.016742 |
| HPCG | 0 | 770.315665 | 771.717820 | 0.998183 |

The second repetition reverses variant order. NPB-MG's density-1 build is
about 8.7% slower in both orders. SQLite changes direction; CG has only one
pair with a small gain; HPCG has only one near-equal pair. These observations
do not justify changing the default scheduling density. HPCG alone consumed
1542.03 seconds, exceeding a 25-minute budget for just one pair; the original
60-second-per-workload estimate was wrong. Do not rerun the unchanged batch
expecting it to finish within the reservation.

IMUL medians over three samples, in **TSC ticks per operation**:

| Width | Operand | Dependent | Eight independent chains |
| --- | --- | ---: | ---: |
| 32 | Register | 9.062066 | 9.073468 |
| 32 | Hot memory | 9.063495 | 9.070754 |
| 64 | Register | 9.074920 | 9.068290 |
| 64 | Hot memory | 9.080660 | 9.068793 |

All samples lie between 9.057370 and 9.093656 ticks/op. The diagnostic used
CPU 1, core 0, with siblings 1-4 and a grant of 240 CPUs. Reported frequency
was 1238094 kHz before and after; measured TSC frequency ranged from
1232030464 to 1232112228 Hz. Timer overhead was 161 ticks for samples of
12800000 operations. Loop overhead remains included. These observations put
the serial IMUL path far from a three-cycle model at approximately matching
reported core/TSC frequencies, but do not establish an exact core-cycle
latency. Independent chains show no throughput improvement, so the result
alone cannot distinguish dependency latency from a shared execution limit.

The transport record reports profile `full`, unchanged boot ID, and overlap
`claude-turn-s12-w2-20261114T230113`. It also lists shell/awk/sleep/launcher/
workload processes as foreign. This may reflect the lead's enclosing window,
but exclusive ownership and idle siblings cannot be established from this
record alone. The lead must reconcile that overlap before treating the
timings as uncontended measurements.

Decision: retain the density-4 default and request phase two on a GCC lane
to investigate/correct IMUL cost, subject to lead confirmation of the window
environment. The measured IMUL discrepancy is enough to select that work;
more whole-program phase-one pairs are not needed to select it. Do not set
the cost mechanically to nine or ten from these ticks alone. Phase two still
needs its intended cost-decision red test, lead-built compiler and required
validation. No GCC changes, compiler rebuilds, new card jobs, held-out reads,
x86 checks or ICE sweeps were performed in this continuation.

## Phase two: scalar IMUL cost red test

The lead confirmed that window 2 was uncontended and accepted phase one.
The default density remains four. Phase two is limited to scalar integer
multiply cost, on lane `gcc2`; HPCG is excluded from the later paired batch.

`tests/t1/knc-imul-cost.c` checks the optimizer's decision for unsigned
32-bit and 64-bit multiplication by 123 at `-O2 -march=knc`. Unsigned
arithmetic preserves defined modular results for every input. The test
requires arithmetic strength reduction in both functions and rejects IMUL;
it does not inspect the cost-table source or hardcode a replacement cost.
A dedicated `--imul-cost` selection runs just this T1 case, which is also
included in the ordinary complete T1 suite.

With `KNC_GCC_SLOT=2`, ran once:

```text
python tools/run.py --name s12-21-imul-red --inputs tools/check.py tests/t1/knc-imul-cost.c -- python tools/check.py t1 --compiler gcc16 --imul-cost --worker
```

The existing GCC 16.2.0 compiler compiled the case successfully; the test
failed on the forbidden IMUL instruction, as intended. Log:
`.work/_state/logs/s12_21_imul_red-20261114-203002.log`.
The lane's build stamp names GCC commit `02f32213c0d6eda6fbf5a262b6c3cc25501a4748`.
No GCC source changes, rebuild, whole-program restaging or native execution
were made. Red review precedes the cost correction and lead-owned rebuild;
T0-T2, ICE sweeps and the short affected-program/control A/B remain pending,
with x86 identity reserved for the lead.

## Phase two: scalar IMUL cost correction

Following the lead's phase-two red approval, the KNC-only integer multiply
cost is 10 for QI/HI/SI/DI and 20 for TI, preserving the existing estimate
of two scalar multiplies for TI. R02 p.56 describes a ten-cycle scalar
multiply path. The uncontended phase-one SI/DI register and memory results
of approximately nine TSC ticks per operation, with no independent-chain
throughput improvement, support replacing the old three-cycle estimate.
Ten uses the documented cycle model without equating TSC ticks with exact
core-cycle latency or choosing the smallest cost that flips the red test.
QI/HI and the TI composition remain estimates, not new native measurements.

Only the multiply entries in `knc_processor_costs` change. Density remains
four; scheduler reservations, division costs and x86 cost tables are
unchanged. The existing T1 red test supplies the intended strength-reduction
decision check after the rebuild.

The GCC change is committed before requesting a lane-2 build. Per AGENTS.md,
Codex engineers cannot build the shared GCC tree, so no build or green tests
were attempted in this continuation. After the lead builds, T0-T2 and ICE
sweeps remain due, along with a short full-profile paired A/B for affected
development programs and two controls, excluding HPCG, within 25 minutes.
The lead owns x86 identity and card execution; neither has run for this change.

## Phase two: host validation and short A/B staging

The lead built lane 2 at `1a4f5aab0a2`. The candidate stage uses that lane's
`cc1`/`f951` with the installed drivers, startup files and runtime libraries.
Its baseline is the existing phase-one default build, with unchanged fixed
inputs and density four. These are installed-prefix versus lane-2 compiler
artifacts; the installed prefix does not identify its exact source commit,
so later timing differences require that qualification when attributing them.

`tools/s12_21_phase2.py stage` built and linted all thirteen permitted
development programs, excluding HPCG. It reuses the phase-one baselines
without rebuilding them. Results under `.work/_shared/S12-21/phase2/`:

| Program | Changed instructions | IMUL old / new |
| --- | ---: | ---: |
| PB-gemm | 12 | 2 / 1 |
| PB-atax | 11 | 2 / 1 |
| PB-cholesky | 16 | 2 / 1 |
| PB-ludcmp | 11 | 2 / 1 |
| PB-jacobi-2d | 174 | 2 / 1 |
| PB-heat-3d | 23 | 2 / 1 |
| STREAM | 0 | 0 / 0 |
| NPB-CG | 0 | 11 / 11 |
| NPB-EP | 0 | 11 / 11 |
| NPB-MG | 278 | 64 / 62 |
| NPB-IS | 0 | 2 / 2 |
| zlib | 137 | 19 / 8 |
| SQLite | 9620 | 529 / 148 |

The package selects all nine changed programs and unchanged NPB-IS/STREAM
as controls. It stages two adjacent pairs per program, reversing order on
the second pair: 44 serial runs in one exclusive full-profile reservation.
The runner limit is 1440 seconds, leaving 60 seconds of the 25-minute budget
for transport overhead. There is no inner BusyBox timeout command. The
ustar/gzip payload, peer archives and generated shell syntax checks passed.
No native timings have been collected for this phase.

With `KNC_GCC_SLOT=2`, the host commands were:

```text
python tools/run.py --name s12-21-cost-stage --inputs tools/s12_21_phase2.py tools/corpus.py tools/s12_21_stage.py -- python tools/s12_21_phase2.py stage
python tools/run.py --name s12-21-cost-package --inputs tools/s12_21_phase2.py -- python tools/s12_21_phase2.py package
```

Logs are `.work/_state/logs/s12_21_cost_stage-20261114-210129.log` and
`s12_21_cost_package-20261114-211411.log`. The second command only refreshed
the package to select the shorter unchanged controls and reserve transport
time; it did not repeat any build or lint. The lead command and collection
command are in `.work/_shared/S12-21/phase2/README.txt`.

The sweep tools now select their corpus from the assigned GCC lane.
The vector tool also accepts output/summary paths and compile-only mode,
allowing this check to stay under S12-21 without staging unrelated card jobs
or overwriting the checked-in baseline. The vector sweep compiled 1345 of
2001 files, skipped 632 by target requirements, reported 23 compile errors
and one ICE. The ICE is `O3-vect-pr32243.c`, a `V16QI` to `V16SI` sign
extension failing in `curr_insn_transform` during reload. Compiling its
original, header-free source with the installed compiler and the same flags
reproduced the same ICE. Thus it is not specific to the new IMUL cost,
although the older checked-in baseline calls it compiled. The sweep is not
reported as passing. Logs:
`.work/_state/logs/s12_21_vect-20261114-205847.log` and
`s12_21_ice_baseline-20261114-210942.log`. The detailed vector results and
reproducer command are under `phase2/vect.txt` and
`phase2/vect/O3-vect-pr32243.log`.

The required `git -C ../_shared/gcc-2 rebase knc` failed creating
`gcc/.git/worktrees/gcc-2/rebase-merge` with `Permission denied`; it did not
change the clean GCC branch. No workaround was attempted. `knc` has advanced
to `2e70e4115e2` with the scalar-broadcast alignment fixes. The lead must
perform the rebase and any resulting GCC build before final acceptance.
The current checks and staged candidate refer to `1a4f5aab0a2`. X86 identity
and native card execution have not run here and remain lead-owned.
