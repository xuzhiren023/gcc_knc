# S12-26: static WRF scalar-loop classification

Status: static, unsampled classification. Loop ordering is a source judgement,
not a measured hot-loop ranking. No WRF flag arms, rebuild, relink, install or
card job was performed.

## Scope and evidence

The lead's 2026-11-15 00:35 ticket answer authorizes static, unsampled analysis
and diagnostic-only `-S` compiles of six generated sources. The routine shares
on the ticket come from a different PhiWeather image; they are priorities, not
measurements of this staged executable. No per-loop sampled share is available.
Within routines, the ordering below is judgement from nesting and trip structure,
not a measured ranking. Initialization/table construction is excluded from the
runtime shortlist. `advance_uv` was context on the ticket, outside the requested
six-file collection.

Input: `.work/_shared/wrf-trial/smpar/wrf.exe`, staged by S11-26, WRF 4.8.0
`06d4240a` plus seven pinned physics submodules. RUN-NOTES records a mixed build:
earlier objects from installed knc `619e14b479a`, continuation from `71e9b2d00fc`.
The installed prefix for this collection is the latter, as confirmed on S11-26.
The ELF is authoritative when it differs from new diagnostic assembly.

Raw output: `.work/_shared/S12-26/`. `commands.json` holds the six actual diagnostic
commands, derived from the per-file command lines in S11-26's initial/resumed
build logs. The original optimization, language, OpenMP and include flags are
preserved: `-mphinix -mknc-card=7120`, `-fopenmp`, free form/unlimited line length,
big-endian I/O, record marker 4 and the argument/BOZ compatibility switches.
Only `-c/-o object` and the original vector-report switch are replaced with
`-S`, `-fopt-info-vec-all`, `-fopt-info-loop`, a separate module-output directory
and assembly output. Existing build `.mod` files supply dependencies. All six
compiles exit 0. Generated modules and assembly stay under the shared ticket
folder; the original build is untouched.

Reports are `<module>.opt`; assembly is `<module>.s`. `image.nm`,
`image-summary.json` and `<ELF symbol>.dis` record symbol bounds and disassembly
of 122 functions in the selected modules. No data is joined to another image's
PC samples. The S12-19 tool's `diagnostics`/`reason_for` vocabulary is used below;
its corpus-only join is deliberately not used or modified. Importing those two
functions over all six reports produced `triage-reasons.json`; its counts are
diagnostic rows, not loop counts or time shares. Dependence messages
that its classifier leaves unclassified are retained as dependence evidence,
not relabelled alias failures. An optimized KNC *candidate* message does not
prove vectorization; only an actual loop-vectorized report does.

Logs in `.work/_state/logs/`:

- `S12_26_diagnostics-20261115-003723.log`: six successful `-S` compiles, 2.3 min.
- `S12_26_image-20261115-003820.log`: disassembly collection, exit 0, 0.2 min.
- `S12_26_debug_diagnostics-20261115-004747.log`: all six authorized `-g
  -fdump-tree-aprefetch-details` compiles exit 0. The wrapper exits 1 because
  its literal instruction-text comparison includes renamed internal labels;
  this is a comparison failure, not a failed compile. See the resolved comparison
  below; no source was recompiled to resolve it.
- `S12_26_expanded_shapes-20261115-005502.log`: the expanded standalone shapes
  compile successfully, exit 0.

### Resolving source locations and comparing code

The 00:46 lead authorization supplied a new reason for one further diagnostics
pass. GCC emits a manual DWARF v4 line program, with `.LM` labels rather than
assembler `.loc` directives. `map.py` in the raw output decodes that program
(including its emitted line-base/range), then intersects source locations with
the generated Fortran's DO/ENDDO bounds. `*.sites.json` records source lines,
assembly lines, innermost source loops and corresponding ELF prefetch addresses.
`*.debug.f90.196t.aprefetch` contains the pass decisions.

All six plain/debug assembly instruction sequences have equal length and are
identical after renaming internal `.Lknc_gather`/`.Lknc_scatter` labels, whose
numbers depend on instruction numbering. No changed instruction was found.
The instruction counts, respectively Thompson/MYNN/advection/update/LW/SW,
are 59,523 / 113,273 / 314,669 / 29,048 / 97,836 / 95,928 across each complete
source file. This checks instruction text, not assembled object-byte identity;
no extra object assembly or link was performed.

`image-map.py` also compares the ordered SIMD/prefetch instruction signatures
against the retained ELF disassembly in all eleven functions in the summary.
Mnemonic family, register operands and prefetch memory displacement agree.
Comparison accounts for objdump's compare-condition aliases and its `ymm`
spelling of the `vcvtps2pd` source register. It does not compare all scalar
instructions, constants or relocations. There is no SIMD/prefetch disagreement
requiring an ELF override. Prefetch instruction ordinal then identifies the
ELF address, rather than inventing an address from a source line alone.

Inlining needs one manual correction: five Thompson sites at debug source
5247/5250 belong to an inlined helper in the vector body of the 3134 level
loop (debug assembly 40625--40658). Count these with 3134: 22 near and 22 far,
not with a separate helper loop. Location attribution within nested LW loops
can similarly move between the inner and outer lines; do not equate a debug
line with a unique stream or a separate execution count.

## Routine priority and image cross-check

Ticket shares: Thompson 5.81%, MYNN-EDMF 2.27%, advection 2.54%, scalar update
2.00%; radiation significant on radiation steps, with no numerical share.
The requested work order puts MYNN before advection despite the shares.

Counts below are static instruction occurrences, not executions. ZMM operand
occurrences include moves and scalar support, so they alone do not prove SIMD
arithmetic. Each near/far count in new `-S` output matches the ELF count for the
listed function; there is no observed prefetch-count disagreement. This is a
function-level cross-check, not a proof of full instruction identity or exact
source-loop correspondence.

| Routine (ELF module suffix) | ELF start | Bytes | vprefetch0 / vprefetch1 | Interpretation |
| --- | --- | ---: | ---: | --- |
| `module_mp_thompson:mp_thompson` | 0x20d7640 | 168885 | 120 / 120 | Mixed scalar math and vectorized passes |
| `module_bl_mynnedmf:tridiag` | 0x3e354c0 | 708 | 2 / 2 | No ZMM operands; scalar recurrences |
| `module_bl_mynnedmf:tridiag2` | 0x3e35180 | 798 | 3 / 3 | No ZMM operands; scalar recurrences |
| `module_bl_mynnedmf:tridiag3` | 0x3e34500 | 3192 | 6 / 6 | Scalar recurrences plus vectorized final quotient |
| `module_advect_em:advect_scalar_pd` | 0x3011dc0 | 351099 | 544 / 544 | Many vectorized stencil passes, scalar limiter |
| `module_em:rk_update_scalar` | 0x169cbc0 | 20796 | 36 / 36 | Vectorized pointwise update passes |
| `rrtmg_lw_rtrnmc:rtrnmc` | 0x271afc0 | 17570 | 35 / 35 | Directional scalar sweeps plus vectorized postprocessing |
| `rrtmg_lw_setcoef:setcoef` | 0x2720bc0 | 14628 | 16 / 16 | Only 4 ZMM operand occurrences; no general SIMD conclusion |
| `rrtmg_lw_taumol:taumol` | 0x2724500 | 24518 | 98 / 98 | Only 9 ZMM operand occurrences; branched lookup work |
| `rrtmg_sw_reftra:reftra_sw` | 0x2796300 | 3687 | 8 / 8 | No ZMM operands; control-flow refusal |
| `rrtmg_sw_vrtqdr:vrtqdr_sw` | 0x27a6f80 | 8741 | 29 / 29 | Scalar directional recurrences, vectorized final combination |

Prefetch is enabled by the compiler at this optimization level; absence is not
evidence it was disabled globally. The implementation is in
`gcc/config/i386/i386-knc.cc` (`ix86_knc_prefetch_distances`, line 1423 in the
inspected shared tree), and `gcc/tree-ssa-loop-prefetch.cc`
(`target_prefetch_distances`, line 1352). Defaults request near/far 16/32 lines;
the near distance can be halved with stream pressure. Loop stream steps convert
line distances to iteration distances. Therefore not every site uses exactly
16/32 iterations, and distance alone cannot establish execution on short rows.
These are compiler implementation observations, not hardware performance claims.

## Source-loop shortlist

All line numbers refer to retained generated `.f90` files under
`wrf-trial/src/WRF-4.8.0-smpar/`; they are not line numbers in upstream `.F` files.
V = actual 64-byte-vector report, M = missed, with reason. Reduced-form names
refer to the accompanying standalone Fortran module. Independence is a source
judgement about the specified dimension; it does not override compiler legality.
Prefetch counts below are static near/far site counts, including transformed
copies. `S` means no site: a scalar stream is not sufficiently unrolled for
the prefetch scheduler. `G` means no site: an early-exit loop has no usable
trip-count guard. `N` means no eligible advancing stream in the small inner
search/correction. These explanations are compiler/source inferences unless
an exact dump loop is identified below; absence itself is checked in mapped
assembly and the matching ELF sequence. An outer nest's inner-loop prefetches
are distinguished from its own streams.

| Module / source loop(s) | Nest / trips and dependence | Vectorizer result | Prefetch | Reduced form |
| --- | --- | --- | --- | --- |
| Thompson 3350, inside 3345 | depth 2; fixed three-step nonlinear correction; serial within one level, different levels offer work | M: unsupported use at 3353; enclosing level loop rejected for consecutive inner loops | No: N in correction; S for enclosing scalar level streams | `fixed_chain` |
| Thompson 2188 with 2211,2230,2244,2259,2272,2288,2303,2316,2528 | depth 2; short searches inside column loop; early exits and per-level math chains | M: outer consecutive inner loops; inner control flow | No: N/G for searches; large surrounding nest also hits reference-selection limits | `bounded_search`, `conditional_math` |
| Thompson 1744,1918,1951,1972,2103,2802,2904,3160,3213,3233,3264,3446,3546,3589,3609,3641,3680,3880,3906 | depth 1; per-column level passes with branches/calls; independent levels for pointwise portions, but search, reduction and sedimentation portions constrain the whole pass | M: unsupported control flow | No: S for scalar streams; early exits additionally require G. Detailed distinction is inferred, not a claim of one identical rejection at every line | `conditional_math`, `bounded_search`, `transport_sweep` |
| Thompson 3582 | depth 1; running height plus early exit, true carried sum | M: unsupported control flow | No: G | `prefix_height` |
| Thompson 2081,2092,3319,3330 | depth 1; backward levels, pointwise parameter/math calculation | V; backward masked epilogue refused, so scalar tail remains | Yes: 7/7 at each loop; guarded main copies | `independent_math` |
| Thompson 3134 | depth 1; independent level temperature update and nonlinear math | V | Yes: 22/22 including inlined helper locations | `pointwise_update`, `conditional_math` |
| Thompson 3727/3738,3759/3763,3778/3789,3812/3820,3839/3853 | inner level passes; outer substeps carry state between passes, not a licence to reorder substeps | V for listed level loops; outer 3726/3777/3811/3838 rejected for consecutive inner loops | Yes: 6/6,8/8; 6/6,8/8; 6/6,8/8; 3/3,5/5; 8/8,11/11 respectively; outer nests have no extra attributed sites | `flux_difference` (one pass) |
| MYNN 5877,5912 | depth 1; forward tridiagonal elimination; quotient feeds next level | M: possible dependence at 5878/5913 | No: S, confirmed in each helper's dump loop 1 | `forward_solve` |
| MYNN 5883,5920 | depth 1; backward substitution, true next-level dependence | M: possible dependence at 5884/5921 | Yes, long-loop version only; details below | `backward_solve` |
| MYNN 5948,5953 | depth 1; backward then forward elimination; genuine carried values | M: possible dependence at 5949/5954 | 5948 no: S (dump loop 1); 5953 yes: 3/3, guarded at 2048 iterations | `forward_solve` / `backward_solve` (recurrence shape) |
| MYNN 5957 | depth 1; independent final quotient | V plus masked epilogue | Yes: 3/3, guarded at 128 iterations | `quotient` |
| Advection 6305,7287,7451,7554 | inner i in row/level nests; independent stencil evaluation with neighbouring reads | V for these sites; merged branch alternatives are not given independent verdicts | Yes: 7/7,29/29,25/25,21/21 respectively | `flux_difference` |
| Advection 7623,7638 | depth 3 j/k/i; pointwise low-order field / outward-flux calculation | V; 7623 also masked epilogue | Yes: 9/9 and 8/8; 7623 also has two each prefetch2/nta | `flux_difference` |
| Advection 7655 inside 7652/7653 | depth 3; conditional limiter writes both neighbouring faces, so shared-face ordering matters | M: unsupported control flow at all three loop levels | No: S in scalar face pass; no sites attributed to enclosing nest either | `face_limiter` |
| Advection 7685,7698,7716,7730,7751,7766 | depth 3; tendency divergence passes; i iterations independent within a pass | V plus masked epilogues; outer levels report nested/access-pattern blockers | Yes: 5/5,5/5,4/4,4/4,6/6,6/6 respectively | `flux_difference` |
| Scalar update 1689,1740 | inner i, j/k/im nest; independent zeroing | Lowered to memset at 1690/1741, not a missed arithmetic SIMD loop | No loop sites: stores lowered to memset, whose internal implementation is outside this classification | `zero_array` |
| Scalar update 1697,1706,1748,1757 | depth 4 including species; independent per-cell multiplication/addition | V plus masked epilogues | Yes: 3/3,2/2,3/3,2/2 respectively | `pointwise_update` |
| Scalar update 1714,1765 | row mass setup inside j/species | V plus masked epilogues | Yes: 5/5 each | `pointwise_update` |
| Scalar update 1720,1771,1783 | depth 4; independent cells but divide is on per-cell critical path | V plus masked epilogues; this does not promise vector divide without helpers | Yes: 5/5,5/5,6/6 respectively | `pointwise_update` |
| LW 3311 | depth within band/g-point work; downward radiative recurrence and cloud branches | M: unsupported control flow | Yes: 7/7 in scalar sweep | `transport_sweep`, `conditional_math` |
| LW 3435 | opposite directional recurrence within spectral work | M: unsupported use at 3446/3454 | Yes: 2/2 in scalar sweep | `transport_sweep` |
| LW 3469 | independent per-layer accumulation/reset pass; no source-level radiative recurrence in this pass | M: compiler reports unsafe code motion for an early exit at 3481 (this does not establish a source-level EXIT) | No: G; dump loop 8 cannot guard trip count | `pointwise_update`, `zero_array` |
| LW 3496 | independent layer postprocessing | V plus masked epilogue; other candidate also reports cost rejection | Yes: 23/23 across transformed copies | `pointwise_update` |
| LW taugb1 5101/5115,5133/5143 | depth 2; independent layers, indirect coefficient reads; ten band coefficients per layer | M: control flow in layer loop; inner coefficient accesses do not yield SIMD | No: outer dump loops 15/13 have no grouped advancing streams; inner loops 16/14 reject estimated trip count 10 against far distances 8/3 iterations (four far distances required) | `table_mix`, `conditional_math` |
| SW reftra 2645 | level loop; independent optical calculations with scalar exp/sqrt/divide chains | M: unsupported control flow | Yes: 8/8, guard at 128 iterations; constant-propagated clone has 0 | `conditional_math` |
| SW vrtqdr 8130 | depth 1 in helper, nested in spectral work; backward recurrence | M: dependence at 8133; additional cost refusal | Yes: 9/9 across scalar/transformed paths | `transport_sweep` |
| SW vrtqdr 8150 | depth 1 in helper; forward recurrence | M: dependence at 8152/8155 | Yes: 7/7 | `transport_sweep` |
| SW vrtqdr 8162 | depth 1; independent layer combination after sweeps | V plus masked epilogue; additional cost refusal | Yes: 13/13 | `pointwise_update` |

MYNN's independently recognizable two-loop helpers give an exact warning about
short-loop coverage. In `tridiag`, 0x3e3554a..0x3e3557f is the forward x87
recurrence with no prefetch. Backward substitution has prefetch1 at 0x3e355c6
and 0x3e355d1, and prefetch0 at 0x3e355ca and 0x3e355db. But the compare
at 0x3e3558d is against 0x7fe followed by an unsigned branch to the short
path: the prefetched/unrolled body is used only above about 2048 elements.
The loop still has a scalar short path. This is emitted code, not a statement
that the production column ever reaches that path.

`tridiag2` similarly has no prefetch in the forward recurrence ending at
0x3e35250, and has three pairs starting at
0x3e352a6 in the guarded backward body. These sites include a 0x600 separation
between far and near addresses: the observed distances must not be described
as uniform 16/32-line behaviour at every site. Its dump confirms three streams
with near/far 8/32 lines (128/512 scalar iterations) and a 2048-iteration guard.

The newly available absence explanation is concrete in the three tridiagonal
helpers' dump loop 1: stream `prefetch_mod` is 16, unroll factor is 1, and
`schedule_prefetches` rejects a ratio above 4
(`gcc/tree-ssa-loop-prefetch.cc`, lines 1160--1164 in the inspected tree).
It reaches scheduling and issues nothing; this is not a vectorizer dependence
decision. The scalar-body unroll decision consequently affects memory latency
handling even though the memory references are regular. The same scheduling
signature (mod 8/16, unroll 1, zero issued sites) appears throughout the scalar
Thompson and advection paths. The grouped S entries above infer this mechanism
from those dumps and source stream shapes; their exact individual GIMPLE-loop
IDs are not asserted. Early-exit/guardability refusals are an additional cause,
and a large nested body can exceed the 200-memory-reference selection cap.

Other LW coefficient loops illustrate that scalar code can still prefetch:
setcoef's 3703 band loop has 16/16 sites in branch-specialized copies, and the
inlined taugb2/3/4/6 bodies account for the 98/98 sites in taumol. These are
coefficient/interpolation shapes (`table_mix`), with independent band iterations
within a layer. Their opt-info reports missed loops (control flow, nested loops
or unsupported access/type at the individual statements), not vectorized loops.
This agrees with the very small ZMM counts in those functions; those counts
alone were never used as the vectorization verdict.

Observed counts in those inlined bands: 5217 = 8/8, 5396 = 48/48,
5520 = 16/16, and the 6115/6135 nest together = 8/8; 6159 = 18/18.
The split between 6115 and 6135 source locations is 3/1 and 5/7, respectively,
so only the combined count should be treated as a paired stream count.
These extra sites are evidence of emission, not additional sampled hot loops.

## Reduced forms and compiler work

`s12-26-shapes.f90` is original, standalone Fortran with generic names, no model
modules or data. It preserves loop shapes, not WRF's science or a bitwise oracle.
Parameters must be supplied by a caller; positive log/root operands and nonzero
pivots/denominators are caller preconditions. The standalone module compiled to assembly successfully with the installed
prefix and the normal `-mphinix -mknc-card=7120` flags. Log:
`S12_26_shapes_output_dir-20261115-004428.log`. The first attempt failed to
write its module temporary outside the worktree despite `-J`; running with the
output directory as cwd resolved that infrastructure issue. Initial log:
`S12_26_shapes-20261115-004401.log`. No benchmark score or native result
is claimed. Fixed correction and tridiagonal/transport recurrences are the main
latency cases for S12-21/S12-27. Independent rows provide controls: an inner
iteration's serial arithmetic is different from a carried loop dependence.
A compiler change must preserve strict FP order, expose helper and spill costs,
and prove legality before interleaving independent work. The shared-face limiter
must retain update ordering unless a transformation proves the equivalent result.

The samples do not establish which loop dominates a routine. Do not use the
routine share as each loop's share, sum it across rows, or infer that prefetch
emission solved short-row latency. No per-file flag recommendation is made.

## Compiler handoff and limits

For S12-21/S12-27, the first unscored inputs should be `fixed_chain`,
`forward_solve`, `backward_solve` and `transport_sweep`: arithmetic latency and
true carried state are distinct problems. Compare them with `independent_math`,
`quotient` and `pointwise_update`. `bounded_search` and `face_limiter` exercise
control/ordering obstacles; `table_mix` exercises a small strided spectral nest.
Sweep lengths below and above the existing 128/2048 guards when evaluating a
future compiler change; there are no measurements of such a sweep here.
Investigate the prefetch-mod/unroll interaction before assuming that default
prefetch enables short-row coverage. A latency transformation must expose
helper calls, masks, spills and memory operations to costing, preserve strict
FP semantics, and distinguish independent columns from dependent levels.

The original ELF addresses queried with addr2line return `??:0`. Source mapping
therefore uses authorized debug-only assembly plus the ELF instruction-sequence
cross-check above. It is not recovered ELF DWARF, nor a proof of every scalar
instruction's identity in the mixed-build image. No diagnostics-only compile
was blocked by missing modules or preprocessed inputs.

Routine shares are from a different image; all per-loop shares remain
unsampled. The shortlist chooses representative deep/short nests and scalar
critical-path shapes, not every runtime loop in all six files. Raw reports
retain other branch alternatives, initialization and helpers. Aggregate scalar
prefetch rejection explanations marked inference remain less precise than the
identified tridiagonal and radiation dump decisions. No native correctness,
bitwise equivalence, speedup or card timing is claimed, and no result is staged
for PhiWeather. The lead can share this classification; sampled confirmation
is a separate lead matter. x86 not run (research-only ticket).
