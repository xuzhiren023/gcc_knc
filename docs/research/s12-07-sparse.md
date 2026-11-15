# S12-07: ordered sparse reductions, phase-one decision

2026-11-14. **Decision: stop at phase one; the required gain premise is not
established.** The lead-run diagnostic passed all 14 ordered-output comparisons.
Disabling post-reload scheduling helps cache-resident sparse reproducers, but
only saves about 0.5-3.2% in the memory-sized CG cases. No general compiler
change with the planning benefit is demonstrated. Phase two is not started;
proven removable whole-program time remains zero. This is the research closure
permitted by the lead's 2026-11-14 20:19 ticket answer, not code acceptance.

## Assembly comparison

`tools/s12_07_stage.py` uses the installed GCC-KNC 16.2.0 and donor GCC 5.1.1
drivers selected by `corpus.compiler_path`. Both use serial `-O2`; GCC-KNC also
uses `-march=knc`. Actual NPB 3.4.2 CG and HPCG 3.1 SpMV/SymGS source files
are compiled to assembly, with HPCG's MPI and OpenMP disabled. These are
assembly audits, not whole-program builds or native checks. No held-out source
or binary was opened. All generated files remain in `.work/_shared/S12-07/`.

| Inner loop | Donor | GCC-KNC | Interpretation |
| --- | --- | --- | --- |
| CG indexed reductions, source lines 523 and 624 | Signed index load, descriptor-base addition, indexed x87 load, memory multiply, increment/compare, ordered x87 add | Same short-row dependence chain; increment uses `addq` rather than `incq`. Additional guarded, unrolled long-row path prefetches the linear index/value streams | Index-to-address dependence remains. Neither version spills inside the short-row reduction. Register saves and descriptor loads outside it are not inner-loop spills. |
| HPCG SpMV, source line 67 | Index load, indexed x87 load, memory multiply, increment/compare, ordered add | Same instruction ordering, with `addq` rather than `incq` | No inner-loop spill, prefetch or gather. Row pointers are loaded outside the reduction. |
| HPCG SymGS, source lines 74 and 93 | Same indexed load/multiply chain, ordered subtraction | Same chain and subtraction order | Both forward and backward sweeps retain their dependency. Diagonal correction/division remains outside each sparse sum. No inner-loop spill, prefetch or gather. |

The GCC-KNC vectorizer reports the target sparse loops unprofitable and HPCG
SpMV/SymGS each vectorize zero loops. CG has gathers elsewhere in `conj_grad_`:
for example, a contiguous-reduction tail gathers products, stores a vector to
the stack and adds its lanes through x87. Those masked tails and their retry,
mask and vector-to-memory costs must not be charged to the scalar indexed
reduction. Counting gathers across the whole function would misidentify the
target loop.

The CG short-row path is `.L22` in the installed compiler's assembly; its
long-row `.L20` path advances the index stream by 64 bytes and the value stream
by 128 bytes per unrolled group, with near/far hints for those streams. There
is no indirect prefetch of the future RHS value. The independent C and Fortran
reproducers similarly guard the long-row path with a comparison against 1022
on `row_length - 1`. Their 27/128-entry rows take the scalar path. Disabling
loop prefetch removes the guard and alternate path, so this diagnostic's
`nopf` difference measures code/guard effects, not active hints' latency hiding.
Disabling scheduling is also a diagnostic perturbation, not a proposed default.

## Paired diagnostic design

Binary: `.work/_shared/S12-07/sparse-paired`.

One executable links separately compiled donor, GCC-KNC, GCC-KNC without
post-reload scheduling, and GCC-KNC without loop prefetch. The driver is built
with the donor. Independent C SpMV/SymGS and Fortran CG kernels retain index
and accumulation order; a C contiguous reduction supplies the control. The
reproducers use flat CSR storage, not HPCG's per-row pointer layout, and cannot
by themselves establish a whole-HPCG speedup.

The batch covers:

- 32-row cases with a 32 KiB RHS and small matrix streams, intended to fit L2;
  these are not claimed to fit L1.
- 8192-row cases with a 16 MiB RHS and larger matrix streams, exceeding one
  core's private caches. Repeated runs may still benefit from distributed
  caches; this is not proof that every access reaches GDDR.
- Packed groups of eight indices versus spread indices, with deterministic
  values and identical input for every compiler variant within each case.
- Three paired timing samples, reversing variant order on alternate samples;
  one calibration determines identical repetition counts for all variants.

Every output is compared byte-for-byte with the donor, including repeated
SymGS updates, outside timing. These finite dyadic inputs are an equivalence
check for the diagnostic, not a proof for arbitrary FP values. CLOCK_MONOTONIC
times whole kernel calls. The program pins itself to the first granted CPU,
verifies the resulting singleton affinity, and prints the original grant and
remaining CPUs as reserved idle siblings. With `card_run --threads 1`, the
grant is one whole core (four logical CPUs), so three siblings remain unused
by this diagnostic. This reservation does not measure unrelated OS activity;
the lead must still record sibling activity. The program also prints the
executing CPU and page-size information from `smaps`, and has a
180-second alarm. This is explicitly single-core timing; parallel case
execution would change the cache and bandwidth experiment.

Lead launch: use `tools/card_run` with `--threads 1 --timeout 200` for this
binary, recording sibling activity, power/resource profile and stdout. One
launch is below the ticket's 20-minute card cap. Success requires exit zero,
all ordered-output checks, and the final `PASS S12-07 diagnostic complete`.
Do not interpret a timeout or infrastructure error as a native pass.

## Decision boundary and literature

The static comparison has not found a demonstrated scheduling regression in
the short sparse bodies. Candidate removable costs are per-row guards/setup
and exposed dependent RHS loads. The paired results below do not isolate
those costs from the strict FP recurrence, instruction layout, cache-line
traffic and translation effects sufficiently to select a general change.
A large load-PC share, a longer assembly listing or a memory-sized allocation
does not establish latency or bandwidth as the bottleneck.

If indexed latency remains a supported candidate, indirect prefetch needs
bounded look-ahead index loads, proof those ordinary loads are safe, and
explicit accounting for extra address instructions and traffic. It is not
enabled or evaluated by this batch. Gather profitability likewise has not
been measured and no gather change is justified yet.

Required reading: `knc-reference-gaps.md`, part 2, S12-07 facts and residual
G03 experiment; `phi-literature-survey.md`, items 01, 05, 06 and 14 (the latter
read from the main checkout because this worktree predates the file). The
Ainsworth/Jones CGO 2017 pp. 4-6 and TOCS 2019 pp. 7-9, 17-28 discussion
motivates bounds-safe dependent-address look-ahead and its overhead checks.
SELL-C-sigma and CSR5 separate useful nonzeros, padding, RHS reloads and
conversion costs; their format changes are outside this ticket. The HPCG
SC14 slides' traffic and convergence considerations prohibit inferring a
complete-solver gain from an isolated sparse kernel.

S11-06 and S11-09 in `knc-memory-bandwidth.md` also caution against transferring
whole-card streaming rates or one format's prefetch winner to serial sparse
loops. Their cache/page, timing-envelope and instruction-overhead distinctions
apply here; their measured bandwidths are not this diagnostic's ceiling.

## Validation history

Card window 1 failed before any cases: the previous driver required a
singleton grant, but `card_run --threads 1` grants four logical CPUs. The
lead reported exit 2 after 17 seconds in
`.work/_shared/tmp/claude-s12-window1/s12-07-sparse.out`. This is an affinity
infrastructure failure, not a native correctness or timing result. The driver
now narrows the grant before allocation or timing. The `--driver-only` staging
option reuses the unchanged kernel objects from the previous successful host
build and rebuilds/links the driver, then runs `knc_lint`.

Restaging passed once (exit 0, including `knc_lint`):

```
python tools/run.py --name s12_07_restage --inputs tools/s12_07_stage.py tools/s12_07_sparse.c -- ..\_shared\toolchain\cygwin\bin\python3.12.exe tools/s12_07_stage.py --driver-only
```

Log: `.work/_state/logs/s12_07_restage-20261114-175645.log`.
The restaged binary is at the same path. The lead subsequently ran it in
window 2; results and resource limitations are recorded below.

Passed once after the lead's installed-driver correction:

```
python tools/run.py --name s12_07_stage --inputs tools/s12_07_stage.py tools/s12_07_sparse.c tools/s12_07_sparse.F90 -- ..\_shared\toolchain\cygwin\bin\python3.12.exe tools/s12_07_stage.py
```

Log: `.work/_state/logs/s12_07_stage-20261114-145549.log` (exit 0, including
`knc_lint`). Assembly, objects and vectorizer/scheduler dumps are beside the
binary in fixed variant directories. No engineer GCC build or card job was launched.
No compiler patch or red/green T1 was made. T0-T2, the ICE sweep and the
whole-program before/after batch (CG, HPCG, PB-gemm and zlib at full/3100/5100)
were not run or staged: they are the conditional phase-two gates, and phase
one stops here. x86 not run. No held-out program was built, read or run.
Existing passing build/lint checks and the card batch were not repeated.


## Card window 2: all samples

Source: `.work/_shared/tmp/claude-s12-window2/s12-07-sparse.out`, lead-run
window reported at 00:35Z in the ticket. The ticket reports 41 s elapsed;
the card JSON reports 0.4145833 card minutes (24.875 s). These are different
reported timing envelopes; neither is a sum of kernel samples. Together with
window 1's reported 17 s, the reported launch durations total 58 s, below the
20-minute cap. Both JSON exit codes are zero, all 14 case comparisons pass,
and stdout ends with `PASS S12-07 diagnostic complete`.

Resource context: the actual inherited affinity and JSON CPU list contain
CPUs 1-240, rather than the requested four-CPU core grant. The driver narrows
that mask to CPU 1 and verifies singleton affinity; `CLOCK` also reports CPU 1.
Its `idle_siblings_reserved` label lists CPUs 2-240, which are merely the
unused members of the original grant, not 239 hardware siblings or a measured
idle-state report. Actual sibling activity and power/frequency were not
recorded. The JSON has `profile: null`, one foreign `sleep` process and an
`overlapping_jobs` entry `claude-turn-s12-w2-20261114T230113`; it does not show
whether that entry is only the enclosing reservation. Thus the supplied
resource record alone does not establish exclusive timing. The boot ID is
unchanged. Every case reports 4 KiB kernel and MMU pages. These limits do not
invalidate the observed output comparisons, but prohibit promoting these
short timings to a qualified whole-program performance claim.

Each row below is a complete timed batch in seconds, preserving all nine
printed decimal places. Repetitions are identical across variants within a
case; divide time by repetitions to compare per-call costs across cases.
Samples 0 and 2 execute donor/knc/nosched/nopf; sample 1 reverses that order.
`nosched` means `-fno-schedule-insns2`, and `nopf` means
`-fno-prefetch-loop-arrays`; neither changes source index or accumulation order.

| Case | Sample | Reps | Donor | GCC-KNC | nosched | nopf |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cache cg packed | 0 | 512 | 0.035024659 | 0.035103431 | 0.031698303 | 0.034974265 |
| cache cg packed | 1 | 512 | 0.035007403 | 0.035110587 | 0.031717373 | 0.034948561 |
| cache cg packed | 2 | 512 | 0.035145818 | 0.035104921 | 0.031702195 | 0.035126304 |
| cache cg spread | 0 | 256 | 0.027097801 | 0.027050554 | 0.025374675 | 0.026967685 |
| cache cg spread | 1 | 256 | 0.027019529 | 0.026973425 | 0.025461701 | 0.026916341 |
| cache cg spread | 2 | 256 | 0.026944531 | 0.026990328 | 0.025281424 | 0.026953242 |
| cache spmv packed | 0 | 2048 | 0.025412156 | 0.026260609 | 0.023122078 | 0.025421576 |
| cache spmv packed | 1 | 2048 | 0.025422844 | 0.025998311 | 0.023139925 | 0.025422754 |
| cache spmv packed | 2 | 2048 | 0.025427403 | 0.025996984 | 0.023139698 | 0.025416210 |
| cache spmv spread | 0 | 1024 | 0.022018570 | 0.022373748 | 0.020897255 | 0.022173507 |
| cache spmv spread | 1 | 1024 | 0.022020131 | 0.022442740 | 0.021081850 | 0.022039403 |
| cache spmv spread | 2 | 1024 | 0.022007030 | 0.022521396 | 0.020895388 | 0.022291166 |
| cache symgs packed | 0 | 1024 | 0.029451527 | 0.030654604 | 0.027778336 | 0.028874058 |
| cache symgs packed | 1 | 1024 | 0.029287877 | 0.030641539 | 0.027846244 | 0.028886465 |
| cache symgs packed | 2 | 1024 | 0.029282167 | 0.030656374 | 0.027769442 | 0.028890253 |
| cache symgs spread | 0 | 1024 | 0.035340231 | 0.036765548 | 0.033830203 | 0.035007381 |
| cache symgs spread | 1 | 1024 | 0.035433130 | 0.036725165 | 0.033909211 | 0.035021869 |
| cache symgs spread | 2 | 1024 | 0.035341320 | 0.036733534 | 0.033867538 | 0.034966807 |
| cache contiguous packed | 0 | 512 | 0.029677743 | 0.018060249 | 0.019214258 | 0.018001189 |
| cache contiguous packed | 1 | 512 | 0.029542307 | 0.018038030 | 0.019210841 | 0.018003568 |
| cache contiguous packed | 2 | 512 | 0.029546251 | 0.018050617 | 0.019210279 | 0.017987987 |
| memory cg packed | 0 | 1 | 0.057760158 | 0.057350703 | 0.055807172 | 0.057916500 |
| memory cg packed | 1 | 1 | 0.057619869 | 0.057885760 | 0.055900193 | 0.057424468 |
| memory cg packed | 2 | 1 | 0.057223798 | 0.057910595 | 0.056061409 | 0.057185077 |
| memory cg spread | 0 | 1 | 0.341837846 | 0.341776815 | 0.340068426 | 0.341187877 |
| memory cg spread | 1 | 1 | 0.341569825 | 0.341397903 | 0.339874065 | 0.341226678 |
| memory cg spread | 2 | 1 | 0.341682798 | 0.341979859 | 0.340089928 | 0.341881475 |
| memory spmv packed | 0 | 2 | 0.028137816 | 0.028475410 | 0.027615312 | 0.028645981 |
| memory spmv packed | 1 | 2 | 0.028110154 | 0.028365119 | 0.027805676 | 0.028374612 |
| memory spmv packed | 2 | 2 | 0.028378442 | 0.028380730 | 0.027992890 | 0.028364211 |
| memory spmv spread | 0 | 1 | 0.072572363 | 0.072824615 | 0.072308048 | 0.072705336 |
| memory spmv spread | 1 | 1 | 0.072593004 | 0.072715962 | 0.072023876 | 0.072713893 |
| memory spmv spread | 2 | 1 | 0.072546858 | 0.072714610 | 0.072316119 | 0.072326025 |
| memory symgs packed | 0 | 1 | 0.031007338 | 0.031284570 | 0.031708843 | 0.030847715 |
| memory symgs packed | 1 | 1 | 0.030561901 | 0.031110162 | 0.030271998 | 0.031162861 |
| memory symgs packed | 2 | 1 | 0.030692373 | 0.030925911 | 0.030439846 | 0.030926197 |
| memory symgs spread | 0 | 1 | 0.144570661 | 0.145318153 | 0.144089164 | 0.144942704 |
| memory symgs spread | 1 | 1 | 0.145116983 | 0.145018685 | 0.144463111 | 0.144870310 |
| memory symgs spread | 2 | 1 | 0.144466114 | 0.145299910 | 0.144198706 | 0.144656465 |
| memory contiguous packed | 0 | 2 | 0.032814324 | 0.021583551 | 0.022908735 | 0.022339171 |
| memory contiguous packed | 1 | 2 | 0.032858753 | 0.022226293 | 0.022835055 | 0.021629878 |
| memory contiguous packed | 2 | 2 | 0.033601833 | 0.021481426 | 0.022702730 | 0.021925661 |

The summary uses the median of the three **paired ratios**, not a ratio of
independently selected samples. Donor/KNC above 1 means GCC-KNC is faster.
Savings are `100 * (1 - variant_time / knc_time)`; negative means slower.
Three short samples in one launch describe this experiment, not confidence
intervals or independent six-pair corpus qualification.

| Case | Donor/KNC | nosched time saved | nopf time saved |
| --- | ---: | ---: | ---: |
| cache cg packed | 0.9978x | +9.693% | +0.368% |
| cache cg spread | 1.0017x | +6.195% | +0.212% |
| cache spmv packed | 0.9779x | +10.995% | +2.234% |
| cache spmv spread | 0.9812x | +6.599% | +1.022% |
| cache symgs packed | 0.9558x | +9.383% | +5.761% |
| cache symgs spread | 0.9621x | +7.802% | +4.782% |
| cache contiguous packed | 1.6378x | -6.425% | +0.327% |
| memory cg packed | 0.9954x | +3.193% | +0.797% |
| memory cg spread | 1.0002x | +0.500% | +0.050% |
| memory spmv packed | 0.9910x | +1.972% | -0.033% |
| memory spmv spread | 0.9977x | +0.709% | +0.164% |
| memory symgs packed | 0.9911x | +1.572% | -0.001% |
| memory symgs spread | 0.9949x | +0.758% | +0.258% |
| memory contiguous packed | 1.5203x | -5.685% | -2.068% |

## Interpretation and stop decision

The ticket's 0.0336/0.0215-second sample and 1.56x comparison belong to
**memory contiguous packed, sample 2**, not CG, SpMV or SymGS. Across all
three pairs that control has median speedup 1.5203x; the cache control is
1.6378x. Sparse CG is approximately at donor parity; sparse SpMV/SymGS are
slightly slower with the default compiler. The donor advantage is largest
for cache SymGS (about 4-5%). The control's improvement must not be credited
to indexed-load scheduling.

There is a real diagnostic signal worth retaining: `nosched` saves
6.2-9.7% in cache CG, 6.6-11.0% in cache SpMV, and 7.8-9.4% in cache SymGS.
Those gains recur in each of the three samples, including reversed order.
It would be incorrect to describe all scheduling effects as immaterial.
However, the same switch slows the contiguous control by median 5.7-6.4%.
A global scheduler disable is therefore unsuitable, and this switch alone
does not identify a safe instruction/property-specific scheduling correction.

In memory CG the median savings shrink to 3.193% packed and 0.500% spread;
in memory SpMV/SymGS they are approximately 0.7-2.0%. Memory SymGS packed
is particularly variable: `nosched` is slower in sample 0 and faster in the
other two. The larger spread penalty (CG about 5.9x packed time per call)
is consistent with sensitivity to locality, but changing occupied lines also
changes traffic and translation pressure. This batch has no counters or
look-ahead intervention that separates indexed-load latency from bandwidth,
TLB costs or the ordered FP recurrence. It cannot justify indirect prefetch.

`nopf` changes cache CG by less than 0.4%, though cache SymGS improves by
4.8-5.8%. Memory sparse differences are below 1% in median magnitude.
As established in the assembly audit, these 27/128-entry rows do not execute
the long-row prefetch path: the switch compares guards/setup/code layout,
not useful indirect prefetch coverage. No active gather implementation or
indirect-prefetch candidate was timed, so neither profitability is established.

The M4 baseline's theme-2 planning sensitivity was a local 1.10-1.20x gain
on 24.547 s of CG exposure, removing 2.23-4.09 s. Applying the measured
memory CG scheduling fractions to that entire exposure would yield only
0.784 s packed or 0.123 s spread. Even these are hypothetical sensitivity
calculations, not forecasts: the diagnostic's index distribution and cache
mix have not been matched to whole CG. Cache-packed CG alone would suggest
2.379 s (about 1.107x local), but transferring its 32-row cache-resident gain
to all production CG exposure is unsupported; cache-spread would suggest
only 1.521 s. The flat-CSR HPCG reproducers likewise cannot establish fixed-work
HPCG parity or convergence performance.

Stop under the phase-one premise-failure path authorized by the lead. There
is no demonstrated general mechanism delivering the required benefit in the
qualified workload, and resource uncertainty further limits a positive claim.
This is not proof that sparse optimization is impossible. It preserves the
cache scheduling observation while declining to spend phase-two builds and
qualification on an unproven transfer. No format rewrite, reassociation,
gather-cost change, prefetch default or compiler scheduling change is proposed.
