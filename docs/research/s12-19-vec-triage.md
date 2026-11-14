# S12-19: development-corpus vectorization triage

The installed-prefix debug rebuilds match the frozen sampled executable only
for zlib. The other 13 development programs have different `.text`; their old
PCs remain unmapped, as directed by the ticket's 2026-11-14 lead answer.
HPCG has no profile and receives a static-only analysis. This is a limited
attribution result, not evidence that the unmapped programs lack hot missed
loops. No held-out program was compiled, opened or analyzed.

## Collection and interpretation

`tools/vec_triage.py collect` replays the compiler command records referenced
by `S11-18/builds.json`, with their original optimization flags, source order,
defines, include directories and link arguments. It adds `-g` and
`-fopt-info-vec-all`, changes output paths into `S12-19/debug/<variant-program>`,
and relocates missing S11-18 corpus support paths to this worktree. Original
NPB generated headers and the existing patched HPCG source remain inputs.
The NPB C timer's command deliberately lacks the Fortran command's OpenMP flag.
The collector never calls the corpus-wide staging entry point.

The identity check compares `objdump -d -j .text` output after removing only
the filename banner: addresses, bytes, instructions and symbols must agree.
PB-gemm is compared against the actual `S11-15/gemm` pilot executable.
The other programs use their frozen S11-18 workload executables. All 19
selected program/variant builds completed. Eighteen comparisons differ;
serial zlib matches. The comparison is deliberately stricter than instruction
similarity. For example, STREAM's instruction at `0x4005cd` loads `0x401980`
in the frozen ELF and `0x4019c0` in the debug rebuild: the encoded operand
bytes differ. The collection does not establish which intervening compiler,
linker or source detail caused each mismatch. It does not assume that `-g`
itself caused the difference.

`analyze` queries only observed workload PCs, with `addr2line -a -f -C`,
after that identity gate passes, using the newer Cygwin host addr2line. The old
cross-toolchain reader returned unknown/zero lines for the matching debug ELF;
the newer reader resolves them without recompilation. Source regions come from balanced C-family
loop statements and structured Fortran DO statements. Comments, literals and
preprocessor directives are excluded. This is a conservative lexical scanner,
not a C/C++ preprocessor: unbalanced conditional source and macro-created
loops can be unresolved. A compiler loop-site diagnostic can establish its
single source line when full lexical bounds are unavailable. Such a site does
not establish neighboring lines. Ambiguous overlapping regions, unknown lines,
unrecognized diagnostics and library samples remain explicit unknowns.
Unmatched diagnostics are retained in each analysis JSON.

Each sample belongs to at most one innermost region. Reports referring to loop
bodies join to that region, not merely to the nearest preceding loop header.
Successful loop-vectorization reports take precedence over failed candidate
modes; SLP success and KNC candidate-cost messages are not loop-vectorization
successes. The six recognized missed categories are alias, unknown stride,
control flow, cost model, unsupported operation and reduction order. A loop
can have multiple reasons; each receives its sampled time once, so totals
overlap. Unrecognized blockers remain visible rather than becoming a guessed
category. A generic FP sum is not classified as a reduction-order refusal
unless GCC actually reports that refusal.

Times use the existing profile's user-plus-system CPU total multiplied by
sample share. All modules remain in the denominator. Serial and OpenMP captures
are separate observations, not additive estimates of one execution. PB-gemm's
six-launch pilot uses nominal 10 ms per sample and is labeled accordingly;
it contributes no attributable loop time here. Existing hot-function rankings
and profile qualification issues are retained. Function names never substitute
for source-loop ownership.

The profiles did not record dynamic access strides or mask occupancy. These
fields are unknown. KNC diagnostic access/mask counts are static candidate
descriptions, not observations of runtime stride distributions or active lanes.
Mapped loop time is an upper bound on opportunity, not an estimated speedup:
removing one diagnostic need not remove all blockers or make a loop profitable.

## Reproduction and artifacts

Run commands from this worktree; paths below are relative to `.work/_shared`:

```text
python tools/run.py --name s12-19-debug-collection --inputs tools/vec_triage.py -- python tools/vec_triage.py collect
python tools/run.py --name s12-19-corpus-triage --inputs tools/vec_triage.py -- python tools/vec_triage.py analyze
python tools/vec_triage.py report
```

`--program` selects one of the 14 development names. `collect --resume` reuses
completed collection results, for continuing an interrupted collection; it
must not be used to refresh results after changing the installed prefix or
inputs. `report` renders existing analyses without rebuilding or re-attributing.
The lower-level `join` command still accepts explicitly established source
regions and captured addr2line output.

The full per-program ranked tables and static loop inventories are
`S12-19/rankings.md`. Raw opt-info, debug executables, command logs, source
attribution and classified rows are under `S12-19/debug/<variant-program>/`.
The corpus reason summary is `S12-19/triage-summary.json`. Intermediate objects
and Fortran module files were removed; no GCC tree was copied or changed.

The first analysis was interrupted during SQLite: repeated path normalization
made diagnostic matching unnecessarily expensive. Caching normalized paths and
source locations fixed that cost; completed per-program results were reused.
The resumed analysis completed in seconds.

The first collection stopped because its metadata check incorrectly required
the OpenMP flag on NPB's serial C timer command. The check was corrected to
validate the requested base flags while replaying every frozen command's exact
flags, and collection resumed without rebuilding completed programs.

The 10 approved host fixture cases pass, including real GCC reason messages,
SLP/candidate distinction, exclusive nested-loop time, deduplication,
program/module filtering, unknown mapping and captured addr2line addresses.
The captured mapping case now also checks lexical discovery of its two source
loop intervals. No new test file was added beyond the approved two.

Logs:

- `.work/_state/logs/s12_19_debug_collection-20261114-153545.log`
- `.work/_state/logs/s12_19_debug_collection_resume-20261114-153626.log`
- `.work/_state/logs/s12_19_vec_triage_collection_tests-20261114-153940.log`
- `.work/_state/logs/s12_19_corpus_triage_resume-20261114-154915.log`
- `.work/_state/logs/s12_19_zlib_debug_reader-20261114-155000.log`
- `.work/_state/logs/s12_19_zlib_source_triage-20261114-155018.log`
- `.work/_state/logs/s12_19_vec_triage_final_tests-20261114-155031.log`

No new native execution, card job, GCC build or x86 check ran. The debug
executables are analysis inputs, not claimed native validation results.


## Coverage and per-program outcome

The 19 program/variant builds cover exactly the 14 development programs.
Across available captures there are 19,572 samples, including libraries;
98 map to source loops and 19,474 remain unmapped. The original audit counted
15,109 workload samples, so mapped-loop coverage is only 0.65% of workload
samples (0.50% of all samples). Serial NPB-MG and HPCG have no capture; NPB-MG's
OpenMP capture is retained. Unmapped is not the same as not a loop.

The table gives static missed-loop counts for all selected builds. Counts can
overlap across reasons, and different variants are not pooled. Abbreviations:
U = unsupported operation, F = control flow, C = cost model, A = alias,
S = unknown stride, R = reduction order. Absence of a recognized category is
not proof that the underlying problem is absent.

| Program / variant | .text | Samples | Mapped | Static missed loops by reason |
| --- | --- | ---: | ---: | --- |
| STREAM / serial | differs | 797 | 0 | U 5 |
| STREAM / openmp | differs | 97 | 0 | U 6 |
| NPB-CG / serial | differs | 2976 | 0 | U 16, F 7, C 5, A 1 |
| NPB-CG / openmp | differs | 130 | 0 | U 19, F 7, C 5 |
| NPB-EP / serial | differs | 9798 | 0 | U 7, F 2, C 1 |
| NPB-EP / openmp | differs | 416 | 0 | U 8, F 2, C 1 |
| NPB-MG / serial | differs | no capture | 0 | U 17, F 16, C 3 |
| NPB-MG / openmp | differs | 78 | 0 | U 18, F 11, C 4 |
| NPB-IS / serial | differs | 1201 | 0 | U 9, F 3, A 2, C 1 |
| NPB-IS / openmp | differs | 54 | 0 | U 10, F 5, A 4, C 1 |
| HPCG / serial | differs | no capture | 0 | U 30, F 27, C 5, A 2 |
| SQLite / serial | differs | 173 | 0 | F 719, U 269, C 10 |
| PB-gemm / serial | differs | 521 | 0 | F 2, U 1, C 1 |
| PB-atax / serial | differs | 93 | 0 | U 2, F 1, C 1 |
| PB-cholesky / serial | differs | 1244 | 0 | U 6, F 3, C 1 |
| PB-ludcmp / serial | differs | 1756 | 0 | U 7, F 5, C 1 |
| PB-jacobi-2d / serial | differs | 68 | 0 | F 2, U 1, C 1 |
| PB-heat-3d / serial | differs | 49 | 0 | F 3, U 1, C 1 |
| zlib / serial | identical | 121 | 98 | U 58, F 43, C 6, A 1 |


### Ranked mapped loops: zlib only

The zlib profile has 1.24 user-plus-system CPU seconds and 121 samples, of which
117 are workload samples. The 98 mapped samples cover 1.0043 estimated CPU
seconds. Nineteen workload samples and four library samples remain unmapped.
S11-15 flags this capture as fewer than 300 PCs; the ordering is exploratory,
without confidence intervals or a claim of stable differences between close
rows. No mapped row reports successful loop vectorization or established
straight-line code. Fourteen mapped samples have unclassified missed reasons;
their raw diagnostics remain in the output.

| Source interval | Samples | Estimated CPU seconds | Status / reasons |
| --- | ---: | ---: | --- |
| deflate.c:1983-1987 | 24 | 0.2460 | control flow |
| deflate.c:1915-2015 | 17 | 0.1742 | unsupported operation |
| deflate.c:201-207 | 16 | 0.1640 | unsupported operation |
| adler32.c:100-103 | 11 | 0.1127 | unsupported operation |
| inffast.c:100-287 | 8 | 0.0820 | unknown (raw missed diagnostics retained) |
| inffast.c:250-255 | 6 | 0.0615 | unknown (raw missed diagnostics retained) |
| deflate.c:1393-1485 | 5 | 0.0512 | control flow |
| deflate.c:194-197 | 5 | 0.0512 | unsupported operation |
| deflate.c:1458-1463 | 4 | 0.0410 | unsupported operation |
| adler32.c:110-114 | 1 | 0.0102 | unsupported operation |
| trees.c:510-510 | 1 | 0.0102 | control flow |


### Corpus summary by attributable missed time

This ranking contains zlib only. It cannot establish the corpus-wide ordering
of compiler opportunities because the other programs contribute no mapped
loop time. Other reason categories have no attributable observations, not a
measured zero cost.

| Reason | Samples | Estimated CPU seconds | Loops |
| --- | ---: | ---: | ---: |
| unsupported operation | 54 | 0.5534 | 6 |
| control flow | 30 | 0.3074 | 3 |


HPCG's static ranking is unsupported operation (30 loops), control flow (27),
cost model (5), then alias (2). Examples are the strict dot-product site
`ComputeDotProduct_ref.cpp:58` and the inner SPMV site
`ComputeSPMV_ref.cpp:67-68`, both with cost refusals. The enclosing SPMV loop
at 61-70 has a control-flow refusal. None has a sampled-time estimate. This
is the static-only treatment requested by the lead, not an inferred profile.

The unmatched programs retain their S11-15 hot-function tables in the full
report. For example, NPB-EP's high sample count does not justify assigning its
function time to any newly compiled source loop. New matching debug information
or a separately authorized replacement capture would be needed to rank those
programs by missed loop time.

## Three general compiler changes to investigate

These are the three largest distinct, source-supported candidate groups in
the mapped subset, ranked by their observed loop time. They are not proven
profitable transformations or a corpus-wide top three. Their combined 57
samples represent 0.5841 estimated CPU seconds, an opportunity ceiling before
guard cost and remaining blockers. The 17 samples in the call-heavy outer
`deflate_slow` loop are excluded: its memory-clobber reports do not establish
one legal vector transformation for its entire state machine. Likewise,
unknown gather/grouped-store and macro-heavy regions are not silently counted
as fixable.

1. **Predication with conflict-checked indirect updates and proven recurrence
   handling** ? `deflate.c:1983-1987`, 24 samples / 0.2460 seconds. The observed
   refusal is control flow. The source includes a conditional hash-table update
   and loop-carried hashing state; simply removing the branch is insufficient.
   Legality requires a static proof or runtime guard that active lane reads and
   writes do not conflict, plus an exact equivalent treatment of the hash
   recurrence, final counters and masked-off accesses. Otherwise retain the
   scalar loop. Measure guard success/fallback rates, active lanes, recurrence
   and conflict-check costs, and native paired runtime with identical compressed
   output. All guard, transfer and helper costs must remain optimizer-visible.

2. **Narrow unsigned integer SLP with widening compare/select and exact
   narrowing stores** ? the two `slide_hash` loops at `deflate.c:194-197` and
   201-207, 21 samples / 0.2152 seconds. GCC reports unsupported SLP instances.
   These independent per-element updates are a concrete general mixed-width
   selection case. Legality requires distinct valid element addresses, correct
   unsigned promotions and truncation, and a bound-safe remainder; use a guard
   where bounds or alignment cannot be proven. Preserve the two loops' order.
   Measure native runtime across lengths, tails and alignments; check every
   output element, spill/transfer counts and widening/narrowing overhead.

3. **Exact integer scan/reduction recognition for chained accumulators** ?
   `adler32.c:100-103` and 110-114, 12 samples / 0.1230 seconds. The captured
   reason is unsupported operation, not a floating-point reduction-order
   refusal. One accumulator depends on a running prefix of another, so two
   independent reductions would be wrong. Legality requires an equivalent
   prefix or weighted-sum formulation with proven range bounds or identical
   unsigned wrap semantics, retaining the original modular-reduction boundaries
   and valid memory extent. Measure exact checksums across block boundaries,
   input lengths and tails, then native paired runtime including carry and
   horizontal-reduction costs. No fast-math or FP reassociation is involved.
