# M4 development baseline: S11-15

## Evidence status

The S11-18 primary pilot and this profiling pilot have not run in this engineer
session. No native latency, speedup, hot-time share, removable-time ranking or
profiling overhead is available. The lead's ticket note supplies no raw-output
path yet. This is the staged profiling-method step of Sprint 11 Theme B, not
completion of its baseline acceptance.

Only development programs are considered here. No sealed output was read.
The primary comparison remains GCC 5.1.1 versus GCC-KNC at strict `-O2`, with
actual build failures and any authorized SQLite fallback reported separately.
The full 7120 and 3100/5100 resource profiles require separate observations;
the latter are resource restrictions, not measurements of those physical models.

## First profiling-method pilot

Use the card's existing `perf`, if present, to sample the unchanged S11-18
GCC-KNC serial PB-gemm executable with `cpu-clock:u` at 99 Hz. This is a
single development-program feasibility experiment, not an AutoFDO recorder.
The existing S9-19 probe established a procedure, but its report still leaves
native sampling availability unproven. It cannot supply a corpus profile.

`tools/s11_15_profile.py` stages into `.work/_shared/S11-15/`:

- `gemm`: the existing, already-linted strict `-O2 -march=knc` PB-gemm binary,
  with its required compiler runtimes if any, and S11-18's existing `launch`.
- `profile-pilot.sh`, `files.txt`, and `lead.ps1`: one bounded card job, with
  three plain/sampled pairs in AB, BA, AB order. The launcher pins the workload
  to one CPU from the full reserved profile. No corpus source is changed.
- `symbols.txt` and `gemm.asm`: host symbol table and disassembly for the exact
  staged executable. `main` is present at `0x400940`, size `0xb96`; this build
  does not retain a separate `kernel_gemm` symbol. Loop attribution must use
  sampled PCs and the corresponding loop ranges inside `main`, rather than
  treating all of `main` as matrix multiplication.

The shell creates a diagnostic `workload` wrapper in the temporary card job.
Plain mode execs `gemm`; sampled mode execs `perf record -- ./gemm`. Thus perf
records the workload rather than the launcher's later live-out formatting.
Both use the existing CLOCK_MONOTONIC_RAW launch-to-exit timer; sampled latency
includes recorder startup, draining and shutdown. This is a conservative
end-to-end overhead observation, not a pure interrupt-cost measurement.
Neither diagnostic latency replaces the primary harness's unwrapped latency.

The pilot compares complete binary live-outs byte-for-byte across all six
launches. This detects profiler perturbation, not independent correctness;
the primary donor comparison is still required. Each sample run returns
symbol counts, individual sampled IPs, mappings and lost/throttled-record
diagnostics before overwriting its local `perf.data`. Raw sample text is
bounded to 20,000 lines per run; excess or empty output is a blocker, not
silently truncated evidence. The entire job has a 600-second timeout. The
script neither installs perf nor changes kernel settings.

Run on the host to stage (already completed once):

```powershell
python tools/run.py --name S11-15-profile-stage --inputs tools/s11_15_profile.py tools/corpus/profile-pilot.sh -- python tools/s11_15_profile.py
```

Lead-only card command, from this worktree:

```powershell
python tools/run.py --name S11-15-profile-cpu -- powershell -NoProfile -File ..\_shared\S11-15\lead.ps1
```

The generated script calls `tools/card_run --benchmark --threads 240 --timeout
600 --file-list <S11-15/files.txt> <S11-15/profile-pilot.sh> cpu-clock:u` using
absolute staged paths. It falls back to the merged `tools/card_run` path when
this worktree no longer exists. From the main checkout, use
`.work\_shared\S11-15\lead.ps1` in the command above. Return the run-wrapper
log path through S11-15; stdout includes all `PROFILE_*` sections and the
launcher timing/affinity records, while failures remain visible.

Only if the timer event is unavailable but perf exists, try the existing cycle
sampler with the same bound and controls:

```powershell
python tools/run.py --name S11-15-profile-cycles -- powershell -NoProfile -File ..\_shared\S11-15\lead.ps1 -Event cycles:u
```

Do not run both events after a usable timer result merely to reconfirm it.
Missing perf, inaccessible events, unsupported report/script options, or absent
symbols are infrastructure/method blockers. They are not passing profiles.
If neither existing event works, the next bounded fallback is a diagnostic
PB-gemm build with compiler profiling instrumentation (first check `-pg`
runtime support and symbol output), without corpus-source edits. It has not
been built or qualified; do not create a replacement perf recorder. The lead
must return the failure output before choosing that branch of the experiment.

## Qualification and interpretation after the lead run

Capture completion alone is not method acceptance. Apply these provisional
pilot gates before expanding to the remaining development programs:

1. All six exits succeed, affinity records match, and all complete live-outs
   agree. Primary independent correctness must also pass before publishing
   timing comparisons.
2. At least 300 workload samples across the three sampled launches, with
   samples in every launch; retain each launch separately. Require zero lost
   or throttled records and no more than 5% unattributed workload samples.
   Identify shared-library mappings separately. A missing mapped symbol or
   confusing attribution to `perf`/the launcher blocks that attribution.
3. Compute each paired `sample/plain - 1` latency ratio; report all three,
   their median and range. A median above 5%, any pair above 10%, or inconsistent
   hot-region ordering calls for a lower-impact method or more evidence before
   using the profile. With three pairs these are feasibility gates, not a
   statistical significance claim.
4. Report sample shares and their across-launch ranges, preserving unknown
   samples in the denominator. Sampling is correlated and imprecise: avoid
   treating the sample count as independent observations or assigning exact
   source-line blame to skidding cycle samples.

User-mode CPU-clock samples describe scheduled user execution; cycle samples
describe cycle-weighted execution. Neither directly measures wall time,
off-CPU waiting, kernel time, or OpenMP wait/compute balance. Before converting
a share to removable wall seconds, establish scheduled/user time coverage and
off-CPU residual with a bounded accounting measurement or timed diagnostic
instrumentation. If coverage cannot be established, label wall share unknown
and keep it out of the ranking. Multiplying a conditional sample percentage
by whole-program wall latency is not an acceptable substitute.

Once sampling qualifies, map hot PC ranges to disassembly and compiler
vectorization diagnostics. Annotate x87/vector bridges, address and FP spills,
and hot-range byte size; count these as code properties, not measured time
shares of individual instructions. Missing source-line information may require
a separate `-g` diagnostic build and an overhead/layout check. The serial pilot
does not qualify OpenMP profiling; worker coverage and runtime wait require
their own separate panel. No such result is claimed here.

## Development rows and planning estimates

All three profile columns below refer to primary donor/KNC pairs. `Pending`
means no raw results were supplied, not a zero latency or a pass. Hot functions,
loops, vector decisions, bridges, spills, hot code size and runtime split are
likewise unmeasured for every row. The review ranges are conditional planning
scenarios from the first scope review, not measured predictions or confidence
intervals. They remain unvalidated; no uplift is admitted to the S12 budget.

| Program | 7120 | 3100 | 5100 | Review scenario | Updated planning status |
| --- | --- | --- | --- | --- | --- |
| PB-gemm | Pending | Pending | Pending | 1.33-1.60x | Sampling pilot staged; fraction and local gain unknown |
| PB-atax | Pending | Pending | Pending | 1.33-1.60x | Await strict-reduction and reuse profile |
| PB-cholesky | Pending | Pending | Pending | 1.11-1.25x | Await recurrence and scalar-FP profile |
| PB-ludcmp | Pending | Pending | Pending | 1.11-1.25x | Await recurrence and scalar-replacement profile |
| PB-jacobi-2d | Pending | Pending | Pending | 1.25-1.43x | Await stencil/locality profile |
| PB-heat-3d | Pending | Pending | Pending | 1.25-1.43x | Await stencil/locality profile |
| STREAM | Pending | Pending | Pending | 1.08-1.23x | Await serial memory-cost profile; OpenMP separate |
| NPB-CG | Pending | Pending | Pending | 1.09-1.36x | Await sparse-access/reduction profile |
| NPB-EP | Pending | Pending | Pending | 1.05-1.28x | Await measured math-call share and binding |
| NPB-MG | Pending | Pending | Pending | 1.20-1.36x | Await serial stencil profile; OpenMP separate |
| NPB-IS | Pending | Pending | Pending | 1.05-1.19x | Await address/branch/memory profile |
| HPCG | Pending | Pending | Pending | 1.09-1.36x | Await native validity and sparse/reduction profile |
| zlib | Pending | Pending | Pending | 1.10-1.20x | Await scalar profile; optional PGO gives no baseline credit |
| SQLite | Pending | Pending | Pending | 1.10-1.20x | Preserve actual donor flags/failures before comparison |

No removable-time ordering or implementation theme is selected. When valid
paired latency and wall-share coverage arrive, record each candidate's donor
wall seconds, measured hot fraction, justified local improvement and overlap
with other candidates. The scenario `T * f * (1 - 1/s)` is removable time only
when those quantities are supported; it is not obtained from instruction
counts. Choose at most three general mechanisms with affected programs,
uncertainty, implementation cost and unaffected controls. Do not sum overlapping
benefits or pool different resource profiles.

## Host check and handoff

`S11-15-profile-stage` passed shell syntax checking and found executable symbols;
it saved disassembly for IP attribution. It reused S11-18's already-linted
binaries without another build or lint pass. Log:
`.work/_state/logs/S11_15_profile_stage-20261112-180921.log`.
Native sampling, overhead, attribution, wall-time coverage and independent
correctness remain untested. Primary timings and the method pilot's card
output are required to continue. x86 was not run.

References: `docs/sprints/SPRINT-11.md`, Theme B;
`docs/research/s9-19-auto.md`, section 2;
`docs/reviews/2026-11-12-s11-s13-scope-review.md`, planning table and finding 3;
S11-18 staged harness and `tools/corpus.py`, `tools/corpus/launch.c`,
`tools/corpus/timing.h`.
