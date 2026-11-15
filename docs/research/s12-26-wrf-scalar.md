# S12-26: static WRF scalar-loop classification

Status: diagnostics and image inspection collected; exact per-loop prefetch
attribution is incomplete. This is a partial handoff, not a completed hot-loop
ranking. No WRF flag arms, rebuild, relink, install or card job was performed.

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
`U` means per-loop prefetch presence is unresolved even though its containing
function has both prefetch kinds. It must not be read as absent.

| Module / source loop(s) | Nest / trips and dependence | Vectorizer result | Prefetch | Reduced form |
| --- | --- | --- | --- | --- |
| Thompson 3350, inside 3345 | depth 2; fixed three-step nonlinear correction; serial within one level, different levels offer work | M: unsupported use at 3353; enclosing level loop rejected for consecutive inner loops | U; arithmetic chain itself has no streaming array load | `fixed_chain` |
| Thompson 2188 with 2211,2230,2244,2259,2272,2288,2303,2316,2528 | depth 2; short searches inside column loop; early exits and per-level math chains | M: outer consecutive inner loops; inner control flow | U | `conditional_math` (math/control portion, excludes search) |
| Thompson 1744,1918,1951,1972,2103,2802,2904,3160,3213,3233,3264,3446,3546,3589,3609,3641,3680,3880,3906 | depth 1; per-column level passes with branches/calls; independence must be checked per pass | M: unsupported control flow | U | `conditional_math` |
| Thompson 3582 | depth 1; running height plus early exit, true carried sum | M: unsupported control flow | U | `prefix_height` |
| Thompson 2081,2092,3319,3330 | depth 1; backward levels, pointwise parameter/math calculation | V; backward masked epilogue refused, so scalar tail remains | U | `independent_math` |
| Thompson 3134 | depth 1; independent level temperature update | V | U | `pointwise_update` |
| Thompson 3727/3738,3759/3763,3778/3789,3812/3820,3839/3853 | inner level passes; outer substeps carry state between passes, not a licence to reorder substeps | V for listed level loops; outer 3726/3777/3811/3838 rejected for consecutive inner loops | U | `flux_difference` (one pass) |
| MYNN 5877,5912 | depth 1; forward tridiagonal elimination; quotient feeds next level | M: possible dependence at 5878/5913 | No sites in forward scalar bodies in ELF or assembly; address/reuse selection cause needs loop dump | `forward_solve` |
| MYNN 5883,5920 | depth 1; backward substitution, true next-level dependence | M: possible dependence at 5884/5921 | Yes, long-loop version only; details below | `backward_solve` |
| MYNN 5948,5953 | depth 1; backward then forward elimination; genuine carried values | M: possible dependence at 5949/5954 | U; 6 pairs in whole tridiag3, not assigned to a loop here | `forward_solve` / `backward_solve` (recurrence shape) |
| MYNN 5957 | depth 1; independent final quotient | V plus masked epilogue | U | `pointwise_update` (quotient portion) |
| Advection 6305,7287,7451,7554 | inner i in row/level nests; independent stencil evaluation with neighbouring reads | V for these sites; merged branch alternatives are not given independent verdicts | U | `flux_difference` |
| Advection 7623,7638 | depth 3 j/k/i; pointwise low-order field / outward-flux calculation | V; 7623 also masked epilogue | U | `flux_difference` |
| Advection 7655 inside 7652/7653 | depth 3; conditional limiter writes both neighbouring faces, so shared-face ordering matters | M: unsupported control flow at all three loop levels | U; neighbours' prefetches do not prove limiter prefetch | `face_limiter` |
| Advection 7685,7698,7716,7730,7751,7766 | depth 3; tendency divergence passes; i iterations independent within a pass | V plus masked epilogues; outer levels report nested/access-pattern blockers | U | `flux_difference` |
| Scalar update 1689,1740 | inner i, j/k/im nest; independent zeroing | Lowered to memset at 1690/1741, not a missed arithmetic SIMD loop | U; calls may implement their own stores | `pointwise_update` (zeroing is separate) |
| Scalar update 1697,1706,1748,1757 | depth 4 including species; independent per-cell multiplication/addition | V plus masked epilogues | U | `pointwise_update` |
| Scalar update 1714,1765 | row mass setup inside j/species | V plus masked epilogues | U | `pointwise_update` |
| Scalar update 1720,1771,1783 | depth 4; independent cells but divide is on per-cell critical path | V plus masked epilogues; this does not promise vector divide without helpers | U | `pointwise_update` |
| LW 3311 | depth within band/g-point work; downward radiative recurrence and cloud branches | M: unsupported control flow | U | `transport_sweep` |
| LW 3435 | opposite directional recurrence within spectral work | M: unsupported use at 3446/3454 | U | `transport_sweep` |
| LW 3469 | directional accumulation/reset pass, early-exit legality matters | M: unsafe code motion for early exit at 3481 | U | `transport_sweep` (does not model early exit) |
| LW 3496 | independent layer postprocessing | V plus masked epilogue; other candidate also reports cost rejection | U | `pointwise_update` |
| LW taugb1 5101 | nested layer/coefficient work, branched table access | M: unsupported control flow | U; taumol has 98 pairs in total | `conditional_math` (lookup not modelled) |
| SW reftra 2645 | level loop; conditional optical calculation with scalar exp/sqrt/divide chains | M: unsupported control flow | U; out-of-line function 8 pairs, constant-propagated clone 0 | `conditional_math` |
| SW vrtqdr 8130 | depth 1 in helper, nested in spectral work; backward recurrence | M: dependence at 8133; additional cost refusal | U | `transport_sweep` |
| SW vrtqdr 8150 | depth 1 in helper; forward recurrence | M: dependence at 8152/8155 | U | `transport_sweep` |
| SW vrtqdr 8162 | depth 1; independent layer combination after sweeps | V plus masked epilogue; additional cost refusal | U | `pointwise_update` |

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
as uniform 16/32-line behaviour at every site. Exact stream grouping/reuse
reasons require the prefetch pass dump.

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

## Remaining limits and requested follow-up

The six target routine addresses queried with addr2line all return `??:0`.
The image has debug sections from some inputs, but they do not resolve the WRF
targets. Diagnostic assembly has function/local labels but no source `.loc`
mapping. Function-level counts agree; this is insufficient to assign every
prefetch or packed instruction back to a specific source loop in a 351 KB
routine with hundreds of sites. The U cells deliberately preserve that gap.
The exact prefetch *absence cause* is also not in opt-info: vectorizer rejection
and prefetch rejection are separate decisions.

To complete the per-loop classification without inventing mappings, request one
additional diagnostics-only pass for these same six sources with `-g` and
`-fdump-tree-aprefetch-details`, all original code-generation flags retained,
with `-S` output and dumps confined to the ticket's shared output. This supplies
source locations and per-loop prefetch selection/guard reasons. Cross-check its
instruction stream with the already collected plain assembly and the staged ELF;
keep disagreements explicit and let the ELF win. No relink or WRF flag arm is
needed. This additional pass is pending the lead because the ticket specifies
exact per-file flags and AGENTS forbids repeating successful checks without a
new reason/authorization. The shortlist does not exhaust the runtime loops in all six files; the retained
raw reports also cover the remaining branch alternatives and helper loops.
