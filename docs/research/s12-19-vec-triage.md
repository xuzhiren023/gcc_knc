# S12-19: development-corpus vectorization triage

Per-function matching attributes **1,715 of 15,109 workload samples (11.35%)**,
up from 98 with whole-section byte identity. This is still well below half:
the observed subset cannot establish a representative corpus-wide top three.
The 14 development programs have reports; no held-out program was compiled,
opened or analyzed. HPCG has no capture and receives static-only analysis.

## Collection and the function gate

`tools/vec_triage.py collect` replays the compiler commands referenced by
`S11-18/builds.json`, retaining optimization flags, source order, defines,
include directories and link arguments, adding `-g` and `-fopt-info-vec-all`.
Outputs go to `S12-19/debug/<variant-program>`. Missing S11-18 corpus support
paths are relocated to this worktree; original NPB generated headers and the
existing patched HPCG source remain inputs. The NPB C timer keeps its original
non-OpenMP flags. All 19 development program/variant builds completed in the
previous session. This session reused those builds without recompilation.

Whole `.text` equality is retained as historical metadata, not a mapping gate.
`analyze` captures `objdump -h -t -d --no-show-raw-insn` for each frozen/debug
pair. Each frozen function must have a unique same-name debug function, an
explicit nonzero symbol size, identical sizes, and identical instruction
mnemonics, operands, registers and instruction offsets after normalization.
Normalization removes symbol annotations and address comments, replaces direct
branch/call destinations and RIP-relative displacements, and replaces numeric
absolute addresses within allocated ELF sections. Stack displacements, other
constants and registers remain significant. Ambiguous names, zero sizes,
missing symbols and failed decoding stay rejected. This is the lead-requested
instruction-layout gate, not a proof that referenced data or call targets have
identical semantics; address normalization deliberately omits that information.

A passing function translates `frozen_symbol + offset` to
`debug_symbol + offset`. Only observed workload PCs are queried with the newer
Cygwin `addr2line -a -f -C`; returned addresses are translated back before the
source join. A query establishes only that byte, never a neighboring address.
Failed functions, unknown lines and unresolved source ownership stay unmapped.
PB-gemm uses the actual S11-15 pilot ELF, not its later S11-18 executable.

All rejected function names and reasons are listed separately for each
program/variant in `S12-19/rankings.md` and its `function-map.json`. Important
rejections include STREAM `main`, NPB-CG `conj_grad_`, NPB-EP `MAIN__`, NPB-IS
`main` and `randlc`, each PolyBench `main`, and SQLite `sqlite3VdbeExec`.
Zero-size startup functions also remain rejected, including in zlib.

### Installed compiler comparison

The frozen S11-18 STREAM `runtime-prefix.json` records the prefix
`_shared/gcc-knc-16.2.0` and version `k1om-mpss-linux-gcc (GCC) 16.2.0`.
The debug collection command uses that same prefix, and the installed compiler
still reports that same version. Those records do **not** record an exact
compiler source revision or immutable installation identity, so whether the
installed compiler changed since S11-18 is unknown; a reused version string
cannot establish equality. There are real generated-code changes beyond
relocation: STREAM `mysecond` has size 0x34 versus 0x32 and changes its spill
slot from `0x8(%rsp)` to `(%rsp)`. Its frozen PC is rejected. The captured
PB-atax `__libc_csu_fini` instead moves from 0x401870 to 0x401cb0 with identical
one-byte code and maps by offset. The data do not isolate compiler revision,
input drift or debug-sensitive code generation as the cause of the changes.

## Source attribution and interpretation

Regions come from balanced C-family loop statements and structured Fortran DO
statements. Comments, literals and preprocessor directives are excluded. This
lexical scanner is not a preprocessor: macro-generated or conditionally
unbalanced source can remain unresolved. A compiler loop-site diagnostic can
establish its single source line when lexical bounds are unavailable, never
neighboring lines. Each PC belongs to at most one innermost source region.
Ambiguous overlaps and unrecognized diagnostics remain explicit unknowns.
Only explicit return statements outside loops establish straight-line regions.

Successful loop-vectorization reports take precedence over failed candidate
modes; SLP success and KNC candidate-cost messages do not establish successful
loop vectorization. Categories are alias, unknown stride, control flow, cost
model, unsupported operation and reduction order. A loop can have multiple
reasons, so reason totals overlap. A generic missed-loop message remains unknown;
a source-level inference is not silently promoted to a compiler diagnostic.

Time is the profile's user-plus-system CPU total multiplied by sample share,
including library samples in the denominator. Serial and OpenMP captures are
separate observations: their pooled seconds rank this set of captures, not one
execution or a representative workload mix. PB-gemm's six-launch pilot uses
nominal 10 ms per sample and contributes no mapped loop time. Existing function
rankings and profile qualifications remain in the artifacts. Many OpenMP
captures have few PCs, so their large per-sample weights make small-count
opportunities particularly uncertain.

Dynamic strides and mask occupancy were not captured and remain unknown.
Static KNC candidate access/mask counts do not measure runtime distributions.
Mapped loop time is an opportunity ceiling, not a predicted speedup or proof
that resolving one refusal removes every blocker.

## Reproduction and artifacts

From this worktree (artifact paths below are relative to `.work/_shared`):

```text
python tools/run.py --name s12-19-debug-collection --inputs tools/vec_triage.py -- python tools/vec_triage.py collect
python tools/run.py --name s12-19-function-triage --inputs tools/vec_triage.py -- python tools/vec_triage.py analyze
python tools/vec_triage.py report
```

`--program` accepts only development names. `collect --resume` and
`analyze --resume` reuse completed outputs and must not be used after changes
to their inputs or interpretation. `report` renders completed analyses.
The lower-level `join` accepts established source regions and captured
addr2line output. Full per-program ranked tables, rejected functions and static
inventories are in `S12-19/rankings.md`; the corpus reason summary is
`S12-19/triage-summary.json`. Each debug directory retains opt-info, build
commands, raw frozen/debug disassembly, function mapping, debug/frozen-address
addr2line records and classified rows. No GCC tree was copied or changed.

The 11 host cases pass in the two approved test files. The added captured-pair
case accepts a relocated same-size function, translates an interior offset,
rejects changed code even with equal size, preserves half-open symbol bounds,
and normalizes a changed RIP displacement. Existing cases cover real GCC
reasons, SLP/candidate distinction, exclusive nested time, sample filtering,
deduplication, development allowlisting and unknown source mapping.

Current logs:

- `.work/_state/logs/s12_19_function_gate_tests-20261114-160713.log`
- `.work/_state/logs/s12_19_function_triage-20261114-160720.log`

No GCC build, card job or native execution ran. x86 not run. Debug executables
are analysis inputs, not claimed native validation results.

## Coverage and per-program outcome

Across all captures there are 19,572 samples, of which 15,109 are workload
samples. The function gate admits 1,853 workload samples (12.26%); 1,715 map to
source loops (11.35% of workload, 8.76% of all samples). The remaining 138
admitted PCs have unresolved source-region ownership. Overall 17,857 samples
remain unmapped, including 4,463 library samples. Mapped statuses are 1,134
missed-with-reason, 47 vectorized and 534 unknown; none establishes straight-line
code. Unknown and unmapped are not evidence that a region is not a loop.

| Program / variant | Workload samples | Gate admits | Source mapped | Matched / rejected functions |
| --- | ---: | ---: | ---: | ---: |
| STREAM / serial | 491 | 0 | 0 | 4 / 9 |
| STREAM / openmp | 31 | 11 | 11 | 10 / 11 |
| NPB-CG / serial | 2967 | 1 | 0 | 16 / 12 |
| NPB-CG / openmp | 97 | 6 | 4 | 22 / 12 |
| NPB-EP / serial | 6093 | 847 | 847 | 12 / 10 |
| NPB-EP / openmp | 223 | 14 | 14 | 16 / 9 |
| NPB-MG / serial | no capture | 0 | 0 | 23 / 13 |
| NPB-MG / openmp | 49 | 46 | 44 | 38 / 10 |
| NPB-IS / serial | 1195 | 674 | 674 | 13 / 12 |
| NPB-IS / openmp | 43 | 21 | 21 | 19 / 13 |
| HPCG / serial | no capture | 0 | 0 | 121 / 23 |
| SQLite / serial | 153 | 96 | 2 | 1539 / 25 |
| PB-gemm / serial | 466 | 13 | 0 | 10 / 8 |
| PB-atax / serial | 93 | 1 | 0 | 10 / 8 |
| PB-cholesky / serial | 1238 | 0 | 0 | 10 / 8 |
| PB-ludcmp / serial | 1755 | 0 | 0 | 10 / 8 |
| PB-jacobi-2d / serial | 61 | 5 | 0 | 10 / 8 |
| PB-heat-3d / serial | 37 | 1 | 0 | 10 / 8 |
| zlib / serial | 117 | 117 | 98 | 88 / 6 |

Fresh debug-build captures are needed for the rejected hot functions in
STREAM (serial and OpenMP), NPB-CG (both), NPB-EP (both), NPB-IS (both),
NPB-MG (OpenMP), SQLite, PB-gemm, PB-atax, PB-cholesky, PB-ludcmp,
PB-jacobi-2d and PB-heat-3d. Serial NPB-MG and HPCG need their missing captures.
Zlib's workload functions pass the gate; its remaining mapping gaps need source
region improvements, and a longer capture would improve statistical precision.
Fresh SQLite debug data alone will not solve all lexical source-region gaps.
All captures are lead card jobs; none was started here.

### Largest mapped observations

The following rows illustrate the ranking; the artifact contains every mapped
row and each program's static inventory. A high-ranked unknown row retains its
raw refusal and is not assigned a guessed reason.

| Program / variant | Source interval | Samples | Estimated CPU seconds | Status / reasons |
| --- | --- | ---: | ---: | --- |
| NPB-EP / serial | randi8.f90:59-62 | 847 | 8.4717 | unsupported operation |
| NPB-IS / serial | is.c:685-689 | 423 | 4.2370 | unknown |
| NPB-EP / openmp | randi8.f90:59-62 | 14 | 3.9967 | unsupported operation |
| NPB-IS / openmp | is.c:685-689 | 11 | 3.7237 | unknown |
| NPB-MG / openmp | mg.f90:609-614 | 9 | 3.1465 | vectorized |
| NPB-MG / openmp | mg.f90:615-626 | 9 | 3.1465 | vectorized |
| STREAM / openmp | stream.c:334-335 | 9 | 3.0294 | vectorized |
| NPB-MG / openmp | mg.f90:1145-1160 | 7 | 2.4473 | control flow, unsupported operation |
| NPB-MG / openmp | mg.f90:700-706 | 7 | 2.4473 | vectorized |
| NPB-MG / openmp | mg.f90:544-555 | 5 | 1.7481 | vectorized |
| NPB-IS / openmp | is.c:678-679 | 5 | 1.6926 | unknown |
| NPB-MG / openmp | randi8.f90:59-62 | 3 | 1.0488 | unsupported operation |
| NPB-IS / serial | is.c:459-467 | 76 | 0.7613 | unsupported operation |
| NPB-IS / serial | is.c:723-724 | 73 | 0.7312 | unknown |

### Corpus summary by attributable missed time

These are totals over the observed subset, with overlapping reasons. The
absence of attributable cost-model, stride or reduction-order time is missing
evidence, not a measured zero cost. Unknown mapped rows contribute 11.2653
seconds outside the categorized reason table; vectorized rows contribute
15.9989 seconds. Unique missed-with-reason time is 20.7721 seconds.

| Reason | Samples | Estimated CPU seconds | Loops |
| --- | ---: | ---: | ---: |
| unsupported operation | 1005 | 18.4875 | 15 |
| control flow | 38 | 3.0933 | 5 |
| alias | 99 | 1.9772 | 5 |

HPCG's static ranking remains unsupported operation (30 loops), control flow
(27), cost model (5), alias (2). `ComputeDotProduct_ref.cpp:58` and
`ComputeSPMV_ref.cpp:67-68` have cost refusals; the enclosing SPMV loop at
61-70 has a control-flow refusal. None has a sampled-time estimate.

## Three general compiler changes to investigate

These candidates replace the earlier zlib-only list. They cover the largest
source-supported missed-loop groups in the mapped subset, including generic
missed diagnostics whose precise cause remains unclassified. They are
conditional research priorities, not a proven corpus-wide ordering or speedup.
Their disjoint groups total 1,477 samples and 26.6337 estimated CPU seconds,
including 507 samples whose compiler reason remains unknown. Re-rank after
fresh captures before choosing implementation work.

1. **Recognize exact modular integer recurrences and generate parallel prefix
   or skip-ahead evaluation** - NPB-EP serial/OpenMP and NPB-MG OpenMP,
   `randi8.f90:59-62`: 864 samples / 13.5173 seconds. GCC reports an unsupported
   use. The source computes a masked integer multiply recurrence and converts
   each state to double; it is not a freely reassociable floating-point sum.
   Legality requires proof of the low-46-bit modular equivalence within the
   language's defined arithmetic domain (or explicit semantics-preserving
   unsigned lowering), invariant multiplier, exact output sequence and final
   state, valid nonaliasing output, and identical integer-to-double conversion
   and scaling. Guard any unproven bounds/overlap and retain the scalar path.
   This must be a general recurrence transformation, not benchmark recognition.
   Measure exact sequence/state equality over seeds, multipliers, lengths and
   tails, then native paired runtime including wide-multiply lowering, prefix
   cost, conversions, guards and spills. No FP precision relaxation is allowed.

2. **Version indirect updates with lane-conflict checks and ordered fallback** -
   NPB-IS `is.c:549-552`, 665-666, 685-689 and 723-724 across serial/OpenMP:
   606 samples / 10.6691 seconds. The alias-tagged subset is 99 samples / 1.9772
   seconds; the other 507 samples / 8.6920 seconds have generic missed messages,
   so conflict handling is a source-supported hypothesis for that subset.
   These loops update bucket counts/cursors and sometimes scatter through the
   updated cursor; a pointer-disjointness guard alone is insufficient.
   Legality requires valid indices, nonoverlapping relevant arrays, no active
   lane read/write collisions (or an exact ordered conflict resolution), valid
   integer ranges and preserved cursor/output order. Any failing batch must
   run scalar. Measure duplicate/conflict rates, guard/fallback costs and exact
   counts, cursors and sorted outputs across adversarial distributions, then
   native runtime including gather/scatter and all temporary transfers. Do not
   count the unknown subset as a confirmed alias diagnostic or guaranteed win.

3. **Vectorize batches that provably avoid stateful conditional side paths** -
   NPB-MG OpenMP `mg.f90:1145-1160`: 7 samples / 2.4473 seconds, with control-flow
   and memory-clobber refusals. The loop tests values against running extrema
   and conditionally calls `bubble` to change values and coordinate lists.
   A general guarded batch path may compare all valid lanes with the current
   thresholds and skip a batch only when no lane would enter either side path;
   otherwise process the whole batch in original scalar order. Legality needs
   proof that the guard reads cannot trap or alias changing state, the
   comparisons preserve FP/NaN behavior, and the no-hit batch has no other
   observable effect. It must never reorder updates or assume the calls are
   independent. Measure active-mask/no-hit rates and guard overhead, verify
   exact extrema and coordinate ordering (including ties and tails), then
   paired native runtime. Seven weighted samples are weak evidence; confirm
   the hotness and profitable no-hit rate in a fresh capture first.
