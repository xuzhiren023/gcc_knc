# S12-07: ordered sparse reductions, phase-one staging

2026-11-14. Host compilation and lint passed. Native measurements are pending;
no removable time or compiler improvement is established. Phase two has not
started. The lead must run the paired diagnostic before selecting a mechanism.

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

## Paired diagnostic staged for the lead

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
and exposed dependent RHS loads. The paired cache/memory and packed/spread
results must distinguish these from the strict FP recurrence before choosing
a change. A large load-PC share, a longer assembly listing or a memory-sized
allocation does not establish latency or bandwidth as the bottleneck.

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

## Validation and pending work

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
The restaged binary is at the same path. Affinity narrowing and all paired
checks still require the lead's next native window; no native pass is claimed.

Passed once after the lead's installed-driver correction:

```
python tools/run.py --name s12_07_stage --inputs tools/s12_07_stage.py tools/s12_07_sparse.c tools/s12_07_sparse.F90 -- ..\_shared\toolchain\cygwin\bin\python3.12.exe tools/s12_07_stage.py
```

Log: `.work/_state/logs/s12_07_stage-20261114-145549.log` (exit 0, including
`knc_lint`). Assembly, objects and vectorizer/scheduler dumps are beside the
binary in fixed variant directories. No GCC build or card job was launched.
No compiler patch or red/green T1 exists yet. T0-T2, ICE sweep, whole-program
before/after staging and x86 identity remain pending the phase-one decision;
x86 was not run. The ticket is not ready for acceptance.
