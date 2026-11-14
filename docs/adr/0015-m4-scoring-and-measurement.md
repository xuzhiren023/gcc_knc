# ADR-0015: M4 scoring and whole-program measurement

**Status:** Accepted 2026-11-12 by the lead, with the owner's decisions of 2026-11-12 (S11-13 review answers; donor-failure rule "Serial vs serial primary"). Changing a rule after any M4 result is seen requires a new owner decision, recorded here.
**Ticket:** S11-14; S11-11 implements the runner and its correctness checks.

## Authority and scope

The owner's decisions in [Sprint 11, goal 1](../sprints/SPRINT-11.md) control
the comparison, resources, corpus, models and retry policy, as amended by the
owner's **2026-11-12 17:00 EST** decision recorded on S11-14: serial versus serial
primary, the SQLite donor assembly exception, and the HPCG shared-list fix.
That later decision supersedes the earlier OpenMP primary and HPCG blocker rules.
The numbered findings
below refer to the [S11-S13 scope review](../reviews/2026-11-12-s11-s13-scope-review.md).
This ADR adapts [ADR-0010](0010-knc-measurement-protocol.md) to separate executables;
it does not replace its kernel experiment rules. No native result is asserted here.

## Frozen comparison and eligibility

1. Strict matched `-O2` GCC-KNC versus `-O2` GCC 5.1.1 decides M4, with the
   owner's explicit SQLite donor exception below. Source,
   completed work, input, FP semantics and resources match. Each compiler uses its
   own compatible runtime; do not mix objects across incompatible ABIs. Publish
   `-O3`, `-mphinix` and PGO alongside with explicit compiler/flag/runtime labels.
   State relaxed errno/FP behavior; no fast-math, FTZ or reassociation enters the
   primary track. PGO training inputs are separate from evaluation inputs and
   exclude held-out programs. A PGO competitiveness claim needs donor PGO too.
   Side tracks never replace a failed primary result. (Owner; findings 1, 6, 7.)
   **SQLite exception:** GCC-KNC remains at `-O2`; the donor uses its highest
   ordinary optimization level that assembles. The pilot records assembly
   outcomes at `-O3`, `-O2`, `-O1`, `-O0`, choosing the first success in that
   descending order without consulting timings. If none assembles, the row
   blocks the gate. Freeze that level before timing, use it on all three models,
   and label the SQLite primary row with the actual donor level. Retain the
   donor's `kmov` operand-size assembler error and failed-level diagnostics in
   the pilot record and row label. This is an explicit exception to matched
   `-O2`, not an unlabelled matched-flags claim; every corpus headline must
   disclose it. (Owner decision 2026-11-12 17:00 EST; findings 1, 2.)
2. Exactly 17 program units receive one vote each: gemm, atax, cholesky, ludcmp,
   jacobi-2d, heat-3d, adi, durbin, STREAM, NPB CG, EP, MG, IS, HPCG, zlib,
   SQLite and bzip2. Operations, input variants, launches, flag sets and densities
   are subordinate observations, never extra votes. Retain every failed or blocked
   row. Missing or invalid primary data prevents a complete M4 pass; never take
   the median of only successful programs. No exclusions after results.
   (Owner; findings 1, 8.)
   The scorer imports the canonical identifiers from `tools/corpus.py`: PolyBench
   identifiers have the `PB-` prefix; STREAM, NPB-CG/EP/MG/IS, HPCG and SQLite
   retain the harness's capitalization. No independent alias list defines votes.
3. HPCG remains a mandatory vote. The owner authorizes exactly one source
   compatibility change: add the missing variable `n` to the OpenMP
   `default(none)` shared list in a one-line fix, applied identically for both
   compilers. Document this as the **only corpus source change**, preserving its
   patch and source revision in the build record. Apply it for the serial
   primary and OpenMP panel builds; record the same source-fix label for both
   compilers. A remaining build or validity failure blocks the gate rather than
   removing HPCG. (Owner decision 2026-11-12 17:00 EST resolves finding 8.)
4. Every benchmark and A/B comparison runs on the full 7120 and through
   `card_run --profile 3100` and `card_run --profile 5100`. Score each model
   independently; M4 passes only if all three pass. A claimed tuning gain must
   hold on all three. Every result states: profiles model cores and memory,
   not clock or per-core bandwidth; these are resource-profile results on a
   7120, not native 3120/5110 measurements. (Owner; findings 8, 9.)
5. All 17 primary programs use **serial builds against serial builds**, without
   `-fopenmp`, with one pinned worker for each compiler. In particular this
   covers STREAM, NPB CG/EP/MG/IS and HPCG, the six OpenMP-capable programs.
   GCC-KNC's OpenMP builds form a separate panel labelled **"the donor toolchain
   has no OpenMP runtime"**. That panel uses all benchmark hardware threads of
   the card/profile (240 on the full 7120), plus one and two threads per core
   as separate side panels, with verified topology and affinity. These panels
   never enter the 17-vote median or substitute for serial primary data.
   No hindsight-best density, parallel copies of a serial program counted as
   acceleration, or harness rewrite to add algorithm parallelism.
   (Owner decision 2026-11-12 17:00 EST amends findings 1, 2.)

The host scorer's `freeze_primary_spec(sqlite_pilot)` consumes the pilot's four
SQLite donor assembly outcomes (`assembled` boolean and `diagnostic` string).
It returns immutable per-program specifications with `build_mode="serial"`,
`workers=1`, donor/new flag labels, and a source-fix label. The primary compiler
flag labels are `("-O2",)` for the donor, except SQLite's selected level, and
`("-O2", "-march=knc")` for GCC-KNC. No extra optimization, OpenMP or PGO flags
are permitted in those labels. Include paths, library linkage and fixed workload
defines remain in the separately frozen complete build-command record; these
labels do not replace that record. HPCG's source-fix label is
`default(none): add n to shared list; both compilers`; all other source labels
are `unchanged`. SQLite's donor diagnostic label retains failed pilot levels.

Each model maps the 17 canonical names to rows with `pairs` and `primary`
metadata matching these specification fields. Pass the same frozen specification
to `score_models(..., primary_spec=spec)` for all models and both sampling blocks;
`score_model` rejects missing metadata, mismatched modes, workers, flags or source
labels, and extra panel rows. Results retain the primary metadata beside each
score. The harness publishes the OpenMP panel separately, using
`OPENMP_PANEL_LABEL`; there is no donor OpenMP speedup claim. Freeze and archive
the pilot/spec before timing: the pure scorer cannot attest assembly or verify
that the runner actually used the declared build commands. (Findings 1, 2, 8;
owner decision 2026-11-12 17:00 EST.)

## Timed boundaries and fixed work

The primary measurement is fresh-process, launch-to-exit wall latency measured
on the card with `CLOCK_MONOTONIC_RAW`: the resident supervisor timestamps
immediately before process creation and after reaping that child. Include process
startup, loader/runtime setup, input reads, allocation, initialization, the full
declared application work, required output materialization on card, cleanup and
exit. Do not start the clock on the host or include SSH/card_run queue time.
Use precisely the same supervisor boundary and work for both compilers.
Staging and input generation precede timing; output transfer and independent
validation follow it. Correctness-only runs are separate from timed windows.
If a package intrinsically performs verification before exit, its cost remains
inside both launch-to-exit times and is identified; do not subtract it.
(Findings 1, 2; ADR-0010 clock and isolation rules.)

| Program vote | Complete work inside the launch-to-exit boundary | Secondary phases when separable |
|---|---|---|
| gemm | Initialize matrices, complete frozen matrix multiplication, materialize output | Allocation/init; multiplication |
| atax | Initialize inputs, complete both matrix/vector stages, materialize output | Allocation/init; each stage |
| cholesky | Initialize matrix, complete factorization, materialize factor | Allocation/init; factorization |
| ludcmp | Initialize system, complete decomposition and solve, materialize outputs | Allocation/init; decomposition; solve |
| jacobi-2d | Initialize grids, complete frozen step count, materialize final grid | Allocation/init; time stepping |
| heat-3d | Initialize volumes, complete frozen step count, materialize final volume | Allocation/init; time stepping |
| adi | Initialize grids, complete frozen steps and directional solves, materialize result | Allocation/init; stepping |
| durbin | Initialize recurrence inputs, complete frozen recurrence, materialize result | Allocation/init; recurrence |
| STREAM | Allocate/init arrays, perform all four operations with frozen repetitions, finish output | Init; Copy/Scale/Add/Triad separately |
| NPB CG | Initialize frozen class, complete prescribed inverse iterations and output | Init; solver; built-in verification |
| NPB EP | Generate and process the complete frozen class workload and output | Init; computation; verification |
| NPB MG | Initialize frozen class, complete prescribed cycles and output | Init; multigrid; verification |
| NPB IS | Generate frozen class keys, complete ranking iterations and output | Init; ranking; verification |
| HPCG | Initialize frozen grid, complete reference/optimization setup and fixed work, emit validity output | Setup; solver; validity checks |
| zlib | Read fixed content, compress then decompress the complete content, emit both artifacts | Read/init; compression; decompression |
| SQLite | Create/open fresh in-memory database, load fixed data, execute full frozen transaction mix, emit results | Setup/load; transactions; teardown |
| bzip2 | Read fixed content, compress then decompress the complete content, emit both artifacts | Read/init; compression; decompression |

Compression uses a single driver process calling its compiler's library for both
operations; cross-decoding is external validation. Each timed launch starts fresh.
Loops already inside STREAM, SQLite or a compression driver represent a fixed
batch within that fresh process: report batch size and optional resident throughput
separately, never replace the latency score with per-operation kernel time.
HPCG validity/performance output and PolyBench/STREAM kernel timers are diagnostic,
not substitute scores. Record HPCG actual iterations/work and require equal work;
an adaptive duration setting that changes completed work between compilers cannot
supply a score. Failure to obtain equal work with valid code with only the authorized HPCG source fix is a blocker.
(Findings 1, 2, 8.)

The neutral feasibility pilot selects and records exact source versions, primary
inputs, PolyBench dimensions, NPB classes, HPCG grid/iterations, STREAM sizes and
repetitions, compression bytes/seeds and SQL commands in S11-11's frozen run
configuration before tuning. Select for buildability, correctness, memory limits
and duration, never measured speedup. Use identical primary work across models,
sized to the smallest profile. Compression content mixes text/binary and
redundancy; SQL uses the full fixed transaction mix. Memory/cache sensitivity
inputs stay labelled side panels. A configuration missing any of these values is
not ready for tuning or the gate; there is no permission to choose them after
performance results. (Finding 2.)

## Launch schedule, validity and extension

The first pass is a buildability/correctness/duration pilot, not the final gate.
It cannot contribute timing samples to the gate. Freeze compiler/runtime heads,
flags, runner, inputs, checks and schedule before the final gate. (Findings 1, 2.)

Use **six independent paired launches per program per model per A/B panel**, exceeding
the five-pair minimum while allowing exact balance. A is GCC 5.1.1; B is GCC-KNC.
Pair orders are AB, BA, AB, BA, AB, BA, in that order. Each member is a separate
process with identical inputs and resources; pair members are adjacent. Iterate
models in 7120/3100/5100 order and programs in the table's order within each round;
complete all primary rounds before side panels. GCC-KNC-only OpenMP panels have
six independent launches at each density, without a fictitious donor pair, and
report raw latency separately. Preserve chronological timestamps,
pair IDs, start order, raw times and every attempt. (Finding 2.)

There is exactly one predeclared extension of **six additional pairs for every
program on every model**, orders BA, AB, BA, AB, BA, AB. Trigger it if a corpus
interval straddles 1.25 or any program's regression interval straddles 1.05.
Use all twelve pairs for the final calculation; never keep a favorable first-block
score on one model while extending only another. Clear failures with no unresolved
interval do not trigger extra sampling. No third block, optional sample deletion
or selective repetition of unfavorable pairs. This sampling extension is distinct
from the owner's one compiler-repair retry. Bounds are the frozen percentile
bootstrap estimates, not a claim of simultaneous or sequential confidence coverage.
(Finding 2; ADR-0010 amendment 2 adapted.)

The lead books exclusive `card_run --benchmark` windows; no overlapping/foreign
workload is allowed. Staging is complete first. Use fresh-process first touch,
ordinary unprivileged page allocation, the same predeclared allocator/runtime
policy and no external prewarming; package-internal warm-up remains included.
Do not impose the microbenchmark 50-200 ms batch requirement on whole programs.
Start/end clock/power policy must agree and every worker must verify affinity.
Retain actual page mode and deviations. Incorrect output, failed exit, changed
work, failed pinning, resource violation, foreign workload or changed clock policy
invalidates a pair with a specific reason. Keep both members and the reason in
the raw record. Timing spread alone never invalidates a run. (Finding 2.)

Invalid primary pairs block the gate; do not silently replace them with favorable
samples or feed them into the scorer. Infrastructure recovery requires a recorded
lead decision and a complete replacement gate block under the same frozen policy,
with the aborted block preserved. Correctness failure requires repair and the
owner's retry policy, not infrastructure relabelling. (Findings 2, 8.)

## Arithmetic, uncertainty and decision

For pair i, `s_i = T_old,i / T_new,i`. A program's score is `median(s_i)`;
the corpus score is the median of the 17 program scores. Do not divide unpaired
time medians, pool individual launches across programs, or average model scores.
Report pair `T_new/T_old` values too. At summary level report the program score
and its inverse as `T_new/T_old equivalent`; with an even number of pairs this
inverse need not equal the median of the inverse pair ratios. (Findings 1, 2.)

Use 10,000 bootstrap replicates with Python `random.Random(1514)`, programs
ordered as in the table. In each replicate, independently sample n pair indices
with replacement within each program, keep each pair intact, compute each program
median, then the median of all 17. Do not resample the program population: this
is uncertainty for this fixed convenience corpus, not population generalization.
Use `randrange(n)` for each draw. Each independent scoring call resets the seed.
(Finding 2; finding 8 limits the external claim.)

For a sorted bootstrap vector of length B, percentile p is element
`max(0, ceil(p*B)-1)` (zero-based). Report the corpus 5th percentile as its
one-sided 95% lower bound, and the 2.5th/97.5th percentiles as a two-sided
diagnostic interval. Program speedup intervals use the corresponding bootstrap
program medians. Invert speedup interval endpoints in reverse order for the
time-ratio interval. Reusing the paired indices is essential. (Finding 2.)

On **each** model, the lower bound must be **at least 1.25**, and every program
must pass correctness and regression review. A slowdown is strictly
`T_new/T_old > 1.05`, equivalently speedup `< 1/1.05`, not `< 0.95`.
Classify a time-ratio interval [L,U] as clear if U <= 1.05, regression if
L > 1.05, otherwise unresolved. Unresolved evidence cannot pass, including
after the extension. A confirmed regression needs a recorded, lead-reviewed
known cause backed by a diagnostic/ticket reference; otherwise M4 fails.
A cause does not remove its vote, change its score, or resolve an interval
crossing the threshold. Preserve the regression and cause in the report.
Numeric scoring cannot establish whether a supplied cause is substantively sound;
the lead owns that review. (Owner; findings 1, 2.)

Missing model/program/pair data, nonfinite or nonpositive durations and failed
correctness never become zero timings or absent rows. There are no successful
partial-corpus gates. A final miss permits the owner's one bounded repair retry
on the same corpus and protocol; a miss after that means release with documented
limits, not a changed denominator or threshold. (Owner; findings 1, 8.)

## Correctness and environment record

Before timing, S11-11 must freeze and exercise independent correctness oracles:
complete outputs or deterministic references/residuals, not only array sums or
agreement with the donor. For all eight PolyBench programs compare every output
component with an independent reference using
`abs(actual-reference) <= 1e-8 + 1e-6*abs(reference)`. STREAM compares every
array component with its independently computed expected value using the same
formula. Store enough digits to preserve the source floating-point value; no
rounded display or aggregate sum is an oracle. All primary floating outputs must
be finite: NaN or either infinity fails even when the donor agrees. Check
finiteness before arithmetic comparisons. These tolerances are frozen here;
an inadequate reference/check blocks readiness and requires an explicit contract
amendment before tuning, never a tolerance relaxation after a failure. (Finding 2.)

Retain NPB 3.4.2 verification with its packaged class-specific reference/tolerance
and HPCG 3.1's full validity conditions and packaged tolerances; record the exact
selected class/reference and checker revision in the frozen configuration.
Neither built-in check is replaced with donor agreement. Compression must
round-trip byte for byte and be cross-decoded with the other compiler's build
where feasible; a feasibility exception requires a recorded technical reason.
SQLite checks complete expected results, ordering where required, counts and
transaction effects. The harness must reject a deliberately corrupted result
through the same validation path for each checker family before declaring it
ready. Keep failure details and raw artifacts with the proper access policy.
(Finding 2; finding 7 for runtime/oracle prerequisites.)

Each launch records clocksource and start/end clock/power policy, actual page
mode, allocator settings, OpenMP/runtime environment, compiler and runtime
revisions, complete build/run flags, installed and actually linked runtimes,
input/configuration identity, completed work, CPU topology/verified affinity,
thread count, model/profile and its limitations, launch order and validity reason.
Git revisions identify code; do not create content-hash manifests. Keep invalid
runs with reasons rather than deleting them. (Findings 2, 7, 9.)

## Held-out access and reporting

adi, durbin and all of bzip2 remain held out. The runner writes their timings,
profiles, compiler/runtime diagnostics, output artifacts and detailed correctness
results only under `.work/_shared/m4-sealed/`. Full-corpus scores and uncertainty
reports also belong there because they include held-out observations. Tuning
tickets and their logs receive only readiness and pass/fail. Avoid diagnostic
text in exceptions, console output, temporary files or visible summaries.
A `held_out` field alone is not access separation. (Finding 8.)

The lead provisions and verifies OS access controls on that directory and all
runner scratch/log paths: lead/runner access only, no tuning-engineer read access.
If isolation cannot be enforced, do not run or expose held-out data. The scoring
module checks canonical destination containment and redacts public status;
path routing is not an ACL implementation. The harness must apply this policy
before starting any held-out build/check/run, including error paths and symlinks.
The host routing test does not claim that the shared filesystem is already sealed.
(Finding 8.)

Before freeze, diagnose an actual held-out correctness failure only through a
lead-authorized minimized reproducer, recording what was exposed and the loss of
independence. No held-out diagnostics guide ordinary tuning. If held-out evidence
triggers the one retry, label it **exposed-set confirmation**, never fresh held-out
validation. The lead publishes final program/family diagnostics with the unchanged
17-vote median after choices freeze; this bounded corpus does not establish MPI,
LLM decode or broad production performance. (Owner; finding 8.)
