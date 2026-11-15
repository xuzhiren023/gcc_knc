# S12-30: phase-one sparse routes

## Current continuation: legal-form proof before GCC implementation

The lead rejected the phase-two red below on 2026-11-14 at 23:50. It did
not prove an executing short-row lookahead, the disabled mode also disabled
stream hints, and unconditional enablement contradicted the cache-sized
losses. Its straight-line scanner controls do not prove post-ivopts loop
handling. That red is **not accepted** and the earlier native result does
not validate a compiler transform. Step 1 has now passed the lead card run (2026-11-15 02:29 ticket answer).
Step 2 is in progress; the revised scanner is blocked as described below.
No GCC source has changed.

`LEGAL_PROOF` in the same C test file supplies a new, separately compiled
driver and kernel family. Its kernel ABI has rows, row bounds or per-row
pointers/counts, col/val/x and output, **no nnz or RHS-size parameter**.
The old nnz-based experiment remains available only as historical Phase 1.
The Python staging command accepts `--legal`, uses the installed prefixes
(no GCC checkout/build), and writes `legal-gate` in the existing shared
S12-30 directory. No third test file was added.

The two forms are:

- Flat CSR: R=3; load `row[i+4]` only under `rows-i > 3`, otherwise use
  the current `row[i+1]`. Hint `x[col[j+32]]` only under
  `(long long)bound-j > 32`. The subtraction cannot overflow, and the
  guard proves the int addition representable. The lead's union-of-row
  intervals argument applies even to non-monotone rows. There are no
  early exits, calls with observable effects, volatile loads or stores
  aliasing the int bounds. Output has double type under strict aliasing.
- HPCG layout: under `rows-i > 1`, load row i+1's own index pointer and
  count. At current-row position j, hint `x[next_col[j]]` only if
  `j < next_count`. It never extends the current row's allocation, and
  never loads a future value. This is one-row lookahead (13 or 27
  positions in the uniform timing cases), not a claim of fixed d=32.

Each has scalar, unconditional-hint and policy versions. The policy tests
`rows >= 16384` once outside the nest, selecting whole hint/scalar loop
versions. It is a deliberately conservative **hypothesis**, not a proof
that RHS accesses miss cache: row count cannot establish RHS locality.
No default-on recommendation follows without measurements. A compiler
implementation would still need the lead's switch and alias/control-flow
proofs; these hand-written kernels only exercise the permitted forms.

All three compiler/contraction tables (donor-off, installed KNC-off and
KNC-contract-fast) run both layouts and all three routes. The kernels use
ordinary ordered scalar multiplication/addition with `-O2`; the legal
experiment does not disable tree vectorization. There is no vector product
rounding change. Both compiler scalar outputs and every new route must
equal an independent long-double ordered reference bit for bit on exact
small-integer inputs generated at runtime.

Each kernel's guard-page suite runs in a child. It covers lengths 1..33;
0, 1, 2, 4, 7, 16384 and 16385 outer rows; regular, empty-last-row and
non-monotone CSR bounds. Large outer counts contain empty prefixes and
seven active trailing rows, exercising both policy arms at the allocation
end. CSR row[], col and val end exactly at protected pages. HPCG counts
and pointer tables also end at protected pages; every nonempty row has
independent col/val allocations ending at guards, and empty rows point
directly at protected memory. Signal termination is failure. The future
ordinary loads are tested against these guards, not padded buffers.

The new native batch is one single-core timing launch:

```
tools/card_run --threads 1 --timeout 590
# binary: .work/_shared/S12-30/legal-gate
# argument: 12345
```

An internal 570-second alarm includes correctness and timing. Timeout is
an infrastructure failure, never a pass. This is single-core timing, not
a long-running parallel correctness job. The process records its granted
affinity and pins to its first granted CPU; the lead reserves the timed
turn and records the card profile/sibling activity.

There are 24 cases: two layouts, n=13/27, grouped-eight/spread indices,
and three working-set sizes. Cache-sized is 32 rows with a 32-KiB RHS;
CG-A-sized is 14000 rows with a 112000-byte RHS; memory-sized is 32768
rows with a 16-MiB RHS. The memory case is larger than the historical
8192-row case, to exercise the conservative policy's enabled arm. The
policy disables hints for both smaller cases. These sizes are proxies,
not measured cache residency or whole-application inputs. HPCG layout
uses independent row allocations in shuffled physical order, with the
same mathematical data as CSR; indices are not a geometric HPCG stencil.

Each case times donor scalar, KNC scalar, KNC legal-hint and KNC
legal-policy, five samples of at least 0.5 seconds each, reversing order
on alternate samples: 480 samples, at least 240 seconds of kernel timing.
Only baselines and KNC variants are timed to fit the ten-minute budget;
donor hint/policy and contract-fast still receive the complete correctness
suite. Every timed output is checked before and after sampling. Raw
seconds, call counts and paired ratios against both baselines are printed.
The lead must decide whether either legal form gains at least 5% for
memory-sized n=13 and 27, and whether policy cases stay within 2% on the
smaller inputs. No native result for these forms is claimed yet.

Staging and the host model passed once:

```
python tools/run.py --name s12_30_legal_proof --inputs tools/s12_30_precision.c tools/s12_30_precision.py -- ..\_shared\toolchain\cygwin\bin\python3.12.exe tools/s12_30_precision.py --legal
```

Log: `.work/_state/logs/s12_30_legal_proof-20261114-235659.log`.
Target compile/assemble/link and lint passed. All 18 host guard suites
passed with zero failures. Host tables use the same host compiler under
all three labels; they establish control-flow/fixture correctness, not
native donor/KNC agreement or card hint behavior. Each child's printed
comparison counter includes the parent's previously completed child checks;
the final parent count is 18 successful suites, not 18 scalar comparisons.
Installed KNC assembly shows scalar `fmull`/`faddp`, the explicit indirect
`vprefetch0`, and both policy entry comparisons against 16383. Existing
stream-prefetch paths remain in the scalar bodies. This is a static
observation, not a performance or native-correctness result. No previously
passing Phase 1/T1 tests were rerun and no GCC source was changed.

Step 2 remains pending: explicit on/off switch in T1, stream hints still
on in the disabled mode, strictly higher assembly hint counts with the
switch, HPCG-shaped nest, later-row-bound dependence, int-output alias
negative, and an in-loop explicit hint scanner control. Existing volatile,
early-exit, -Os and baseline-identity checks are to be preserved. GCC
implementation, T0-T2, sweeps and paired whole-NPB-CG/HPCG plus controls
follow only after the legal-form result. x86 not run.

2026-11-14, updated after the lead card run. All three handwritten routes
passed native correctness. Route B wins on the memory-sized cases but loses
on every cache-sized case. The lead authorized phase two for Route B only.
The same two test files are reused; no GCC source is changed in this red.

## Numerical contract

ADR-0003 item 2 and DEVELOPMENT_CYCLE's Oracles section permit differences
caused by x87 excess precision. The former witness is a known permitted
difference: `-1 + (1 + 2^-27) * (1 - 2^-27)` yields `-2^-54` when the
extended product survives until addition, and zero when the product is first
rounded to FP64. It is no longer an equality gate. No control word is changed
and no new card run is requested for that witness.

The driver and kernels are separately compiled translation units from
`tools/s12_30_precision.c`, without LTO. The driver generates inputs from a
command-line seed. The kernel ABI accepts a CSR row slice and an independent
`nnz` bound on the accessible index/value arrays. All kernels receive the
same arrays. Objects use `-O2 -ffp-contract=off`; a third kernel object uses
`-ffp-contract=fast` only, not `-ffast-math`. Scalar baselines disable tree
vectorization. The baseline fold uses x87, not a zmm lane. A and A+B
materialize FP64 products and fold them in order through x87. Their C
accumulator is long double so helper calls preserve the accumulator with
80-bit stores, rather than introducing a double rounding at each chunk.

The checks are:

- Every length 1..33: small integer products and partial sums are exact;
  each implemented strict route must match the long-double reference and
  both separately compiled donor/GCC-KNC scalar loops bit for bit.
- Order twins at lengths 13, 16, 17, 27, 32 and 33: sweep all triples of
  positions for `2^70, 1, -2^70` and `2^70, -2^70, 1`, with other entries
  zero. Their ordered results are respectively zero and one under both
  53- and 64-bit accumulation. Placements include both sides of the
  16-element boundary. This bank detects common tree/lane reordering;
  it does not claim a finite test proves the absence of every reordering.
- Eight positive inexact cases at each length: within one FP64 ULP of an
  independently evaluated long-double in-order reference. Both contraction
  settings are included. These fixtures are not an arbitrary-input error proof.
- At each length, separate mappings end `col` and `val` exactly at a
  `PROT_NONE` page. Unguarded future index loads fault. A second case exposes
  64 valid future entries whose indices point into a protected x page;
  only the selected row is evaluated, so these x addresses are prefetch-only.
  Each call runs in a child; a signal or wrong output is a failure. All
  three compiler tables, including contract-fast, run these bounds cases.

The approved red deliberately contained null A/B/A+B slots for donor-off,
knc-off and knc-contract-fast. All slots now contain implementations; the
missing-slot gate remains. Timing cannot run until all routes exist and
correctness succeeds. No test or tolerance was weakened.

## Implementations and static audit

Route A processes up to 16 products per chunk using two eight-FP64 vector
operations. The product helper is file-scope inline assembly identical under
all three prefixes, including the donor. It loads the low active index/value
lanes, conditionally loads a second cache line only when active data crosses
the boundary, completes the masked gather with its retry loop, multiplies
under the original active mask, and stores into a 64-byte-aligned product
array. The C loop consumes only active products, in increasing source order.
No padded source arrays or speculative ordinary tail loads are required.

Instruction semantics were verified in R27 pp.297-299 (gather), pp.349-354
and 361-366 (unpack loads), and pp.399-401 (multiply). This is the early KNC
architectural specification, not a production measurement. Helper argument
registers and clobbers follow R03 pp.15-22, verified ABI facts independent of
production stepping. The normal helper call lets the scalar-only donor
account for clobbers without pretending it has an IMCI register allocator.
The call, product-array transfers and 80-bit accumulator spill/reload are
included in timing; they are costs of this prototype, not a claimed lower
bound for an inlined compiler implementation.

Route B prefetches `x[col[j+32]]` only when `nnz-j > 32`. This guards the
ordinary index load at the array end and permits lookahead across CSR rows.
It never evaluates a future product. A+B issues the same hints for each
active position before calling the vector helper for that chunk. R27 p.641
verifies the non-faulting hint interface (early architectural specification,
not a production measurement); ordinary col/val loads do not inherit it.
The protected-x bounds fixture tests that distinction natively.

Distance 32 is a fixed hypothesis from knc-costs.md's estimated 360-instruction
prefetch latency: allowing roughly 11 instructions per scalar nonzero gives
about 33 entries. Static inspection of the installed KNC output actually
finds 7 instructions in the short scalar loop, and 16 on Route B's hint-taken
path (including its guard and address generation). Thus 32 entries spans
roughly 224 to 512 instructions in those bodies. This bracket is an inference,
not a measured issue/latency conversion or a queue-capacity claim. Gather
retry and chunked hint scheduling further change A+B's effective lead time.
No distance sweep or stream hints were added to this one-run experiment.

Generated donor/off, KNC/off and KNC/fast assembly was inspected under
`.work/_shared/S12-30/*-precision.s`: A/A+B call the IMCI helper, accumulate
with ordered `faddl`, preserve the running sum with `fstpt`/`fldt`, and store
FP64 only at row output. B retains ordered scalar `fmull`/`faddp` and the
guarded indirect hint. Fast enables contraction only; the explicit vector
multiply and x87 fold cannot become an FMA. There is no zmm-lane fold.

## Approved red evidence

Ran once:

```
python tools/run.py --name s12_30_phase1_red --inputs tools/s12_30_precision.c tools/s12_30_precision.py -- ..\_shared\toolchain\cygwin\bin\python3.12.exe tools/s12_30_precision.py
```

Log: `.work/_state/logs/s12_30_phase1_red-20261114-211543.log`.
Target compilation/link and `knc_lint` succeeded. Installed drivers report
GCC 5.1.1 and GCC-KNC 16.2.0. No shared GCC build was performed.

The staging script also builds host fixture objects with x87 arithmetic.
It seeds balanced tree folds once, separately imposing 53-bit double stores
and 64-bit long-double stores. Both were caught by the order oracle at
length 13 (zero instead of one); the mutation process exited 1 and printed
`tree53_caught=1 tree64_caught=1`.

The normal host fixture then exited 1 with exactly nine failures, all missing
route slots. Its 60,458 executed scalar/reference/bounds comparisons passed.
The host objects use the host compiler under all three labels; they do not
establish donor-versus-GCC-KNC native agreement. No A/B/A+B correctness or
speed result is claimed. Neither the native binary nor the timing path has run.

## Current build and host model

Ran through tools/run.py with the same staging command and name
`s12_30_phase1_routes`. The first target assembly attempt rejected `cmovl`
under `--march=k1om`; replacing it with a branch resolved that error without
opaque encodings. The second attempt passed target compile/link/lint and
the host model: **599,300 comparisons, zero failures, zero missing routes**.
Log: `.work/_state/logs/s12_30_phase1_routes-20261114-213007.log`.
The failed attempt is in `s12_30_phase1_routes-20261114-212930.log` in the
same log directory.

The host build is explicitly marked HOST_MODEL. It replaces only the IMCI
product helper with scalar products rounded through volatile doubles and
uses the host prefetch hint. It checks C control flow, ordered folds,
fixtures and guards; it cannot validate IMCI masking, register behavior or
card accuracy/performance. Native binaries never contain this substitute.
The approved seeded-tree demonstration was not rerun.

## Single card entry point and continuation

Staged binary: `.work/_shared/S12-30/precision-gate`, argument `12345`.
Lead launch: `tools/card_run --threads 1 --timeout 1150`, passing that binary
and argument using the wrapper's normal interface. The program's alarm is
1100 seconds, keeping the process budget below 20 minutes. It performs
native correctness first and exits before timing on any failure. On success,
the same entry point performs the entire paired timing batch in one launch.
It is explicitly single-core timing, pins to one granted CPU,
and prints the original affinity and chosen CPU. Other granted CPUs are not
claimed to be idle siblings. Record actual sibling activity and resource/
frequency profile with the lead-run output.

The timing path has row lengths 13 and 27; 32 rows with a 32 KiB RHS, and
8192 rows with a 16 MiB RHS; grouped-eight versus spread indices. Exact
integer data permits bit comparisons before and after timed samples. Each
case uses five samples reversing route/compiler execution order. Every
route/compiler sample accumulates at least 0.5 seconds of timed kernel calls,
doubling batch size when a batch is shorter than 0.25 seconds. Repetition
counts can differ: raw seconds and actual call counts are printed, and
paired speedups compare seconds per call against both scalar baselines.
Identical rows and nonzeros are processed by every call. This prevents a
faster route from receiving a sample below 0.5 seconds and keeps slow routes
from dominating the 20-minute budget. There are 320 timed samples (160 seconds
minimum); the alarm bounds unexpected runtime. A timeout is not a pass.
These are
cache-sized and memory-sized working sets, not measured cache-residence or
GDDR traffic claims. The isolated CSR experiment is not whole-CG/HPCG evidence.

Source context: S12-07's reproducer/results informed the paired batch, but
its feature-disable experiments are not evidence for either new route.
S12-15 survey item 01 (Ainsworth/Jones CGO pp.4-5; TOCS pp.7-9,17-28) motivates
bounds-safe indirect address generation and counting its overhead. Items
05/06/14 motivate separating useful nonzeros, extra traffic, setup and
whole-solver effects. S12-10/R05 section V.D, Table II p.4 (reported here
through the research notes; production-model 5110P, stepping unspecified)
concerns complete gather loops and line/cache distributions, not a universal
single-instruction cost. `knc-costs.md` explicitly labels the gather
interpolation and prefetch-distance model as estimates. The fixed lookahead
and actual scalar instruction counts are recorded above. These were the
pre-run hypotheses; native results follow below.

The following sections supersede the pre-run status above. No card job was
started by the engineer. T0-T2, ICE sweeps and whole-program A/B staging are
phase-two work; x86 not run.


## Native results: every paired sample

Lead-run evidence: `.work/_shared/tmp/claude-s12-window3/s12-30-sparse.out`,
window 3, 03:14-03:18Z on 2026-11-15 (local 2026-11-14). The ticket reports
256 seconds elapsed and exit 0, an exclusive timed turn. The output reports
599,300 initial correctness comparisons and **2,178,308 total comparisons,
zero failures** after timing. Both contraction tables passed correctness,
including guard pages; only the off tables were timed. The x87 ordered fold
met the stated oracle; there was no zmm-lane fold to evaluate.

All 320 samples are present, five for each of eight routes/compiler pairs
in each of eight cases. The shortest sample is 0.500551365 seconds, meeting
the 0.5-second requirement. The program reports affinity 1..240, then pins
to CPU 1. The card wrapper records profile `null` and a foreign `sleep`
process, with an overlapping coordination turn. Exclusivity is attributed
to the lead, not inferred from that JSON. These are single-core results,
not full/3100/5100 paired application results or a sibling-load study.

Each cell below is **speedup versus KNC scalar / speedup versus donor
scalar**, computed from that sample's seconds per call. Larger is better;
1.05 is the phase-two threshold. No samples are discarded or pooled across
working sets. The scalar rows make baseline drift visible. Raw durations,
call counts and higher-precision ratios remain in the source output.

### cache-sized n=13 rows=32 rhs_bytes=32768 packed=0

| Compiler / route | Sample 0 | Sample 1 | Sample 2 | Sample 3 | Sample 4 |
|---|---:|---:|---:|---:|---:|
| donor-off/scalar | 1.0115 / 1.0000 | 1.0125 / 1.0000 | 1.0132 / 1.0000 | 1.0129 / 1.0000 | 1.0146 / 1.0000 |
| donor-off/A | 0.7720 / 0.7633 | 0.7739 / 0.7644 | 0.7740 / 0.7639 | 0.7701 / 0.7603 | 0.7731 / 0.7620 |
| donor-off/B | 0.6891 / 0.6813 | 0.6897 / 0.6812 | 0.6902 / 0.6812 | 0.6888 / 0.6801 | 0.6898 / 0.6799 |
| donor-off/A+B | 0.4828 / 0.4773 | 0.4839 / 0.4779 | 0.4845 / 0.4782 | 0.4839 / 0.4778 | 0.4837 / 0.4768 |
| knc-off/scalar | 1.0000 / 0.9886 | 1.0000 / 0.9877 | 1.0000 / 0.9870 | 1.0000 / 0.9873 | 1.0000 / 0.9856 |
| knc-off/A | 0.7602 / 0.7516 | 0.7602 / 0.7509 | 0.7605 / 0.7506 | 0.7606 / 0.7509 | 0.7586 / 0.7476 |
| knc-off/B | 0.5209 / 0.5150 | 0.5219 / 0.5155 | 0.5209 / 0.5141 | 0.5212 / 0.5146 | 0.5213 / 0.5138 |
| knc-off/A+B | 0.4261 / 0.4212 | 0.4267 / 0.4214 | 0.4271 / 0.4216 | 0.4262 / 0.4208 | 0.4261 / 0.4200 |

### cache-sized n=13 rows=32 rhs_bytes=32768 packed=1

| Compiler / route | Sample 0 | Sample 1 | Sample 2 | Sample 3 | Sample 4 |
|---|---:|---:|---:|---:|---:|
| donor-off/scalar | 1.0183 / 1.0000 | 1.0153 / 1.0000 | 1.0129 / 1.0000 | 1.0153 / 1.0000 | 1.0158 / 1.0000 |
| donor-off/A | 0.9885 / 0.9707 | 0.9857 / 0.9709 | 0.9844 / 0.9718 | 0.9850 / 0.9701 | 0.9864 / 0.9711 |
| donor-off/B | 0.6771 / 0.6649 | 0.6751 / 0.6650 | 0.6752 / 0.6666 | 0.6727 / 0.6625 | 0.6756 / 0.6650 |
| donor-off/A+B | 0.5436 / 0.5338 | 0.5421 / 0.5339 | 0.5418 / 0.5349 | 0.5414 / 0.5333 | 0.5420 / 0.5335 |
| knc-off/scalar | 1.0000 / 0.9820 | 1.0000 / 0.9850 | 1.0000 / 0.9872 | 1.0000 / 0.9849 | 1.0000 / 0.9844 |
| knc-off/A | 0.9598 / 0.9426 | 0.9587 / 0.9443 | 0.9601 / 0.9478 | 0.9585 / 0.9440 | 0.9594 / 0.9445 |
| knc-off/B | 0.5114 / 0.5022 | 0.5097 / 0.5020 | 0.5096 / 0.5031 | 0.5099 / 0.5022 | 0.5102 / 0.5022 |
| knc-off/A+B | 0.4712 / 0.4627 | 0.4694 / 0.4623 | 0.4686 / 0.4626 | 0.4693 / 0.4622 | 0.4695 / 0.4622 |

### cache-sized n=27 rows=32 rhs_bytes=32768 packed=0

| Compiler / route | Sample 0 | Sample 1 | Sample 2 | Sample 3 | Sample 4 |
|---|---:|---:|---:|---:|---:|
| donor-off/scalar | 1.0051 / 1.0000 | 1.0049 / 1.0000 | 1.0055 / 1.0000 | 1.0060 / 1.0000 | 1.0073 / 1.0000 |
| donor-off/A | 0.7899 / 0.7858 | 0.7889 / 0.7850 | 0.7907 / 0.7864 | 0.7891 / 0.7844 | 0.7917 / 0.7860 |
| donor-off/B | 0.7809 / 0.7769 | 0.7830 / 0.7792 | 0.7815 / 0.7773 | 0.7831 / 0.7785 | 0.7839 / 0.7782 |
| donor-off/A+B | 0.5469 / 0.5441 | 0.5479 / 0.5453 | 0.5468 / 0.5438 | 0.5482 / 0.5449 | 0.5483 / 0.5443 |
| knc-off/scalar | 1.0000 / 0.9949 | 1.0000 / 0.9951 | 1.0000 / 0.9945 | 1.0000 / 0.9941 | 1.0000 / 0.9928 |
| knc-off/A | 0.7874 / 0.7834 | 0.7862 / 0.7824 | 0.7886 / 0.7843 | 0.7874 / 0.7827 | 0.7895 / 0.7837 |
| knc-off/B | 0.5843 / 0.5814 | 0.5841 / 0.5813 | 0.5849 / 0.5817 | 0.5847 / 0.5813 | 0.5854 / 0.5812 |
| knc-off/A+B | 0.4858 / 0.4833 | 0.4860 / 0.4836 | 0.4862 / 0.4835 | 0.4864 / 0.4835 | 0.4870 / 0.4834 |

### cache-sized n=27 rows=32 rhs_bytes=32768 packed=1

| Compiler / route | Sample 0 | Sample 1 | Sample 2 | Sample 3 | Sample 4 |
|---|---:|---:|---:|---:|---:|
| donor-off/scalar | 1.0071 / 1.0000 | 1.0062 / 1.0000 | 1.0081 / 1.0000 | 1.0080 / 1.0000 | 1.0081 / 1.0000 |
| donor-off/A | 0.9614 / 0.9546 | 0.9609 / 0.9550 | 0.9614 / 0.9537 | 0.9621 / 0.9545 | 0.9605 / 0.9527 |
| donor-off/B | 0.6525 / 0.6479 | 0.6530 / 0.6489 | 0.6532 / 0.6480 | 0.6531 / 0.6479 | 0.6512 / 0.6460 |
| donor-off/A+B | 0.5124 / 0.5088 | 0.5135 / 0.5104 | 0.5138 / 0.5096 | 0.5130 / 0.5089 | 0.5131 / 0.5090 |
| knc-off/scalar | 1.0000 / 0.9929 | 1.0000 / 0.9939 | 1.0000 / 0.9920 | 1.0000 / 0.9920 | 1.0000 / 0.9919 |
| knc-off/A | 0.9505 / 0.9438 | 0.9511 / 0.9452 | 0.9514 / 0.9438 | 0.9512 / 0.9437 | 0.9524 / 0.9447 |
| knc-off/B | 0.4777 / 0.4743 | 0.4769 / 0.4739 | 0.4770 / 0.4732 | 0.4780 / 0.4742 | 0.4779 / 0.4741 |
| knc-off/A+B | 0.4440 / 0.4409 | 0.4434 / 0.4407 | 0.4445 / 0.4409 | 0.4444 / 0.4409 | 0.4444 / 0.4408 |

### memory-sized n=13 rows=8192 rhs_bytes=16777216 packed=0

| Compiler / route | Sample 0 | Sample 1 | Sample 2 | Sample 3 | Sample 4 |
|---|---:|---:|---:|---:|---:|
| donor-off/scalar | 0.9998 / 1.0000 | 1.0017 / 1.0000 | 1.0019 / 1.0000 | 1.0105 / 1.0000 | 1.0001 / 1.0000 |
| donor-off/A | 0.9917 / 0.9919 | 0.9937 / 0.9920 | 0.9941 / 0.9922 | 1.0034 / 0.9929 | 0.9932 / 0.9931 |
| donor-off/B | 7.7151 / 7.7166 | 7.7146 / 7.7012 | 7.6935 / 7.6789 | 7.7836 / 7.7023 | 7.7111 / 7.7103 |
| donor-off/A+B | 5.7773 / 5.7784 | 5.7740 / 5.7640 | 5.7775 / 5.7666 | 5.8289 / 5.7681 | 5.7588 / 5.7582 |
| knc-off/scalar | 1.0000 / 1.0002 | 1.0000 / 0.9983 | 1.0000 / 0.9981 | 1.0000 / 0.9896 | 1.0000 / 0.9999 |
| knc-off/A | 0.9937 / 0.9939 | 0.9925 / 0.9908 | 0.9941 / 0.9922 | 0.9939 / 0.9836 | 0.9929 / 0.9928 |
| knc-off/B | 7.2840 / 7.2855 | 7.2338 / 7.2213 | 7.2867 / 7.2729 | 7.3454 / 7.2688 | 7.2772 / 7.2764 |
| knc-off/A+B | 5.5501 / 5.5512 | 5.5357 / 5.5261 | 5.5500 / 5.5395 | 5.5960 / 5.5376 | 5.5440 / 5.5434 |

### memory-sized n=13 rows=8192 rhs_bytes=16777216 packed=1

| Compiler / route | Sample 0 | Sample 1 | Sample 2 | Sample 3 | Sample 4 |
|---|---:|---:|---:|---:|---:|
| donor-off/scalar | 1.0050 / 1.0000 | 1.0057 / 1.0000 | 1.0038 / 1.0000 | 0.9984 / 1.0000 | 1.0007 / 1.0000 |
| donor-off/A | 1.0031 / 0.9981 | 1.0037 / 0.9981 | 0.9950 / 0.9912 | 1.0034 / 1.0050 | 1.0039 / 1.0032 |
| donor-off/B | 1.9626 / 1.9528 | 1.9902 / 1.9789 | 1.9866 / 1.9791 | 1.9880 / 1.9912 | 1.9892 / 1.9878 |
| donor-off/A+B | 1.6364 / 1.6283 | 1.6535 / 1.6442 | 1.6527 / 1.6465 | 1.6525 / 1.6552 | 1.6531 / 1.6519 |
| knc-off/scalar | 1.0000 / 0.9950 | 1.0000 / 0.9944 | 1.0000 / 0.9962 | 1.0000 / 1.0016 | 1.0000 / 0.9993 |
| knc-off/A | 0.9950 / 0.9901 | 0.9998 / 0.9941 | 1.0005 / 0.9967 | 1.0004 / 1.0020 | 0.9999 / 0.9992 |
| knc-off/B | 1.5679 / 1.5601 | 1.5596 / 1.5508 | 1.5584 / 1.5525 | 1.5562 / 1.5587 | 1.5535 / 1.5524 |
| knc-off/A+B | 1.4600 / 1.4527 | 1.4521 / 1.4440 | 1.4517 / 1.4462 | 1.4458 / 1.4481 | 1.4529 / 1.4519 |

### memory-sized n=27 rows=8192 rhs_bytes=16777216 packed=0

| Compiler / route | Sample 0 | Sample 1 | Sample 2 | Sample 3 | Sample 4 |
|---|---:|---:|---:|---:|---:|
| donor-off/scalar | 1.0011 / 1.0000 | 1.0008 / 1.0000 | 1.0009 / 1.0000 | 0.9993 / 1.0000 | 0.9999 / 1.0000 |
| donor-off/A | 0.9841 / 0.9830 | 0.9830 / 0.9822 | 0.9848 / 0.9839 | 0.9822 / 0.9829 | 0.9848 / 0.9849 |
| donor-off/B | 7.7765 / 7.7678 | 7.7563 / 7.7500 | 7.7717 / 7.7650 | 7.7677 / 7.7732 | 7.7688 / 7.7697 |
| donor-off/A+B | 5.6992 / 5.6929 | 5.6994 / 5.6947 | 5.6973 / 5.6924 | 5.6964 / 5.7004 | 5.6939 / 5.6945 |
| knc-off/scalar | 1.0000 / 0.9989 | 1.0000 / 0.9992 | 1.0000 / 0.9991 | 1.0000 / 1.0007 | 1.0000 / 1.0001 |
| knc-off/A | 0.9779 / 0.9768 | 0.9849 / 0.9841 | 0.9847 / 0.9839 | 0.9849 / 0.9856 | 0.9843 / 0.9844 |
| knc-off/B | 7.3147 / 7.3066 | 7.3628 / 7.3568 | 7.3206 / 7.3144 | 7.3579 / 7.3630 | 7.3609 / 7.3618 |
| knc-off/A+B | 5.5322 / 5.5261 | 5.5311 / 5.5266 | 5.4992 / 5.4945 | 5.5302 / 5.5341 | 5.4885 / 5.4891 |

### memory-sized n=27 rows=8192 rhs_bytes=16777216 packed=1

| Compiler / route | Sample 0 | Sample 1 | Sample 2 | Sample 3 | Sample 4 |
|---|---:|---:|---:|---:|---:|
| donor-off/scalar | 1.0026 / 1.0000 | 1.0027 / 1.0000 | 1.0040 / 1.0000 | 1.0074 / 1.0000 | 1.0029 / 1.0000 |
| donor-off/A | 0.9908 / 0.9882 | 0.9897 / 0.9870 | 0.9914 / 0.9875 | 0.9964 / 0.9891 | 0.9912 / 0.9883 |
| donor-off/B | 2.0081 / 2.0029 | 1.9961 / 1.9906 | 2.0110 / 2.0030 | 2.0186 / 2.0038 | 2.0041 / 1.9983 |
| donor-off/A+B | 1.6425 / 1.6382 | 1.6418 / 1.6373 | 1.6434 / 1.6369 | 1.6441 / 1.6321 | 1.6426 / 1.6379 |
| knc-off/scalar | 1.0000 / 0.9974 | 1.0000 / 0.9973 | 1.0000 / 0.9960 | 1.0000 / 0.9927 | 1.0000 / 0.9971 |
| knc-off/A | 0.9886 / 0.9860 | 0.9912 / 0.9885 | 0.9921 / 0.9882 | 0.9961 / 0.9888 | 0.9910 / 0.9881 |
| knc-off/B | 1.5422 / 1.5382 | 1.5435 / 1.5393 | 1.5449 / 1.5388 | 1.5513 / 1.5399 | 1.5430 / 1.5386 |
| knc-off/A+B | 1.4467 / 1.4429 | 1.4472 / 1.4433 | 1.4478 / 1.4421 | 1.4544 / 1.4438 | 1.4464 / 1.4423 |

## Interpretation and phase-two constraints

The lead's 1.54-2.00x shorthand describes the grouped-eight memory-sized
cases, across both compilers. It does not describe the cache-sized cases
or the spread-index memory-sized cases. For KNC-compiled Route B, all five
samples beat 1.05 in each memory-sized case, and none do in any cache-sized
case. Medians (minimum..maximum), relative to current KNC scalar:

| Working set / layout | Row length | Route A | Route B | Route A+B |
|---|---:|---:|---:|---:|
| cache-sized / spread | 13 | 0.760 (0.759..0.761) | 0.521 (0.521..0.522) | 0.426 (0.426..0.427) |
| cache-sized / grouped-eight | 13 | 0.959 (0.958..0.960) | 0.510 (0.510..0.511) | 0.469 (0.469..0.471) |
| cache-sized / spread | 27 | 0.787 (0.786..0.789) | 0.585 (0.584..0.585) | 0.486 (0.486..0.487) |
| cache-sized / grouped-eight | 27 | 0.951 (0.951..0.952) | 0.478 (0.477..0.478) | 0.444 (0.443..0.445) |
| memory-sized / spread | 13 | 0.994 (0.993..0.994) | 7.284 (7.234..7.345) | 5.550 (5.536..5.596) |
| memory-sized / grouped-eight | 13 | 1.000 (0.995..1.000) | 1.558 (1.554..1.568) | 1.452 (1.446..1.460) |
| memory-sized / spread | 27 | 0.985 (0.978..0.985) | 7.358 (7.315..7.363) | 5.530 (5.488..5.532) |
| memory-sized / grouped-eight | 27 | 0.991 (0.989..0.996) | 1.544 (1.542..1.551) | 1.447 (1.446..1.454) |

Route A alone never clears 5%; its chunk helper call and product-array
stores are included. Adding A to B reduces the gain in every memory-sized
case and worsens the cache-sized losses. Route B is the only implementation
candidate justified by this experiment. Its cache-sized speedups correspond
to roughly 1.71-2.09x elapsed-time regressions, so a blanket performance win
must not be claimed. Both compilers show the same sign of the result;
the donor compiles the handwritten B loop faster than current KNC does.
Compiler code quality for the added address/guard instructions is therefore
part of the phase-two opportunity, not measurement noise to discard.

The 32-KiB and 16-MiB RHS sizes are proxies, not measured residence. The CG-A
RHS of about 112 KiB is between them and was not measured. Grouped-eight
indices approximate locality; they are not the geometric HPCG stencil.
The spread fixture uses a deterministic LCG, not an independently sampled
random permutation. No whole-CG/HPCG speedup or bandwidth claim follows.

A further legality/performance distinction matters: handwritten B receives
an independent `nnz` array bound and looks ahead across rows. The ordinary
CSR source has only the current row bound available to the inner loop.
A compiler cannot infer a dereferenceable `col[j+32]` from an unused `nnz`
parameter name, assume all rows monotone, or use a future row/array bound
without proving those loads safe and unchanged by intervening writes.
Guarding a distance of 32 solely at the current row end yields no hints
for rows of 13 or 27. Phase two therefore must explicitly solve short-row
lookahead and profitability; the handwritten speedups do not establish
that a conservative row-local compiler transform will win. Bounds checks
must avoid signed overflow, and prefetch address evaluation must not create
observable volatile accesses or ordinary loads beyond an early exit.

## Phase-two T1 red

`tools/check.py t1 --compiler gcc16 --sparse-indirect` uses the dispatched
GCC lane (gcc2 here). `PHASE2_T1` in the existing C file supplies plain CSR
and indexed-slice strict reductions without any programmer hint, plus
volatile-index and early-exit exclusions. The same Python file implements
the T1 selector; no additional test file was created. Separate explicit
indirect and affine hints exercise the scanner's positive/negative controls.

For `-O2 -march=knc`, with contraction off and fast separately, the two
eligible reductions must acquire an indirect prefetch and retain their
scalar x87 fold. The optimized GIMPLE scanner traces the hint address back
to both `x` and a loaded `col` value; a stream prefetch alone cannot satisfy
it. Assembly must also contain a prefetch instruction. Negative cases and
`-fno-prefetch-loop-arrays` / `-Os` must not acquire indirect prefetches.
All variants must assemble under k1om and pass lint. The installed compiler
also compiles the original Phase 1 scalar function with plain -O2 and with
-fno-tree-vectorize, checking function-body identity as requested by the lead.

This red checks transformation presence and exclusions. It does not prove
a positive lookahead distance, guard dominance, alias safety or native
correctness. Green must audit the actual SSA guard/address dependence and
feed compiler-generated kernels through the existing exact/order/inexact
and guard-page harness, extended for empty rows, cross-row aliasing and
long rows around the selected distance. Phase-one handwritten guard tests
are not a substitute for that compiler validation. Whole-program A/B on
NPB-CG and HPCG, plus two controls at full/3100/5100, remains pending.

Ran once through `tools/run.py --name s12_30_phase2_red --inputs
tools/s12_30_precision.c tools/s12_30_precision.py tools/check.py -- python
tools/check.py t1 --compiler gcc16 --sparse-indirect --worker`.
Log: `.work/_state/logs/s12_30_phase2_red-20261114-234408.log`.
The run exited 1 with exactly four missing-indirect-prefetch failures:
CSR and slice, under each contraction setting. Assembly/lint, scanner
controls, all negative cases and both scalar-fold checks passed. Existing
stream prefetch instructions did not satisfy the indirect-address check.
The installed compiler's plain -O2 and measured -fno-tree-vectorize scalar
function bodies were identical. The selector is also included in default
GCC16 T1. No GCC build or native phase-two test ran; no compiler speedup is
claimed. Red approval precedes the compiler implementation.


## Legal-form native result and revised T1 continuation (2026-11-15)

Lead card window 4 returned exit 0 and PASS 8,985,618 comparisons and
children, zero failures. Source output:
`.work/_shared/tmp/claude-s12-window4/s12-30-legal.out`.
The lead authorized Phase 2 for the legal forms. These are handwritten
kernels; no compiler-generated transformation has passed natively.

Every legal-hint/policy timing sample below is shown as speedup over
current KNC scalar / donor scalar, using the same sample number. All
samples are retained, including 0 and 1. Values below 1 are regressions.

| Case | Route | Sample 0 | Sample 1 | Sample 2 | Sample 3 | Sample 4 |
|---|---|---:|---:|---:|---:|---:|
| cache-sized CSR n=13 rows=32 RHS=32768 packed=0 | legal-hint | 0.5006 / 0.5068 | 0.5006 / 0.5072 | 0.4999 / 0.5061 | 0.5006 / 0.5070 | 0.5011 / 0.5073 |
| cache-sized CSR n=13 rows=32 RHS=32768 packed=0 | legal-policy | 0.9782 / 0.9903 | 0.9768 / 0.9898 | 0.9763 / 0.9885 | 0.9776 / 0.9901 | 0.9790 / 0.9912 |
| cache-sized HPCG-pointers n=13 rows=32 RHS=32768 packed=0 | legal-hint | 0.6544 / 0.6272 | 0.6551 / 0.6279 | 0.6560 / 0.6281 | 0.6551 / 0.6300 | 0.6552 / 0.6281 |
| cache-sized HPCG-pointers n=13 rows=32 RHS=32768 packed=0 | legal-policy | 0.9986 / 0.9571 | 1.0015 / 0.9599 | 1.0025 / 0.9597 | 1.0015 / 0.9630 | 1.0012 / 0.9599 |
| cache-sized CSR n=13 rows=32 RHS=32768 packed=1 | legal-hint | 0.4908 / 0.4966 | 0.4903 / 0.4978 | 0.4902 / 0.4975 | 0.4901 / 0.4961 | 0.4903 / 0.4967 |
| cache-sized CSR n=13 rows=32 RHS=32768 packed=1 | legal-policy | 0.9785 / 0.9902 | 0.9775 / 0.9924 | 0.9776 / 0.9920 | 0.9781 / 0.9901 | 0.9769 / 0.9895 |
| cache-sized HPCG-pointers n=13 rows=32 RHS=32768 packed=1 | legal-hint | 0.6316 / 0.6057 | 0.6321 / 0.6045 | 0.6315 / 0.6048 | 0.6310 / 0.6038 | 0.6312 / 0.6045 |
| cache-sized HPCG-pointers n=13 rows=32 RHS=32768 packed=1 | legal-policy | 1.0016 / 0.9605 | 1.0025 / 0.9587 | 1.0008 / 0.9585 | 1.0002 / 0.9571 | 1.0000 / 0.9578 |
| cache-sized CSR n=27 rows=32 RHS=32768 packed=0 | legal-hint | 0.5848 / 0.5884 | 0.5864 / 0.5905 | 0.5851 / 0.5893 | 0.5852 / 0.5889 | 0.5853 / 0.5885 |
| cache-sized CSR n=27 rows=32 RHS=32768 packed=0 | legal-policy | 0.9898 / 0.9960 | 0.9925 / 0.9996 | 0.9902 / 0.9974 | 0.9913 / 0.9976 | 0.9912 / 0.9966 |
| cache-sized HPCG-pointers n=27 rows=32 RHS=32768 packed=0 | legal-hint | 0.7683 / 0.7562 | 0.7683 / 0.7563 | 0.7669 / 0.7559 | 0.7678 / 0.7553 | 0.7682 / 0.7566 |
| cache-sized HPCG-pointers n=27 rows=32 RHS=32768 packed=0 | legal-policy | 0.9981 / 0.9824 | 0.9965 / 0.9810 | 0.9995 / 0.9852 | 0.9986 / 0.9824 | 0.9998 / 0.9846 |
| cache-sized CSR n=27 rows=32 RHS=32768 packed=1 | legal-hint | 0.4781 / 0.4815 | 0.4780 / 0.4813 | 0.4776 / 0.4808 | 0.4765 / 0.4799 | 0.4778 / 0.4807 |
| cache-sized CSR n=27 rows=32 RHS=32768 packed=1 | legal-policy | 0.9889 / 0.9958 | 0.9888 / 0.9956 | 0.9880 / 0.9947 | 0.9869 / 0.9939 | 0.9873 / 0.9933 |
| cache-sized HPCG-pointers n=27 rows=32 RHS=32768 packed=1 | legal-hint | 0.6127 / 0.5989 | 0.6136 / 0.5983 | 0.6126 / 0.5992 | 0.6127 / 0.5989 | 0.6128 / 0.5990 |
| cache-sized HPCG-pointers n=27 rows=32 RHS=32768 packed=1 | legal-policy | 1.0006 / 0.9780 | 1.0031 / 0.9781 | 1.0004 / 0.9785 | 0.9999 / 0.9774 | 0.9987 / 0.9762 |
| CG-A-sized CSR n=13 rows=14000 RHS=112000 packed=0 | legal-hint | 0.9241 / 0.9295 | 0.9200 / 0.9268 | 0.9225 / 0.9298 | 0.9236 / 0.9293 | 0.9222 / 0.9275 |
| CG-A-sized CSR n=13 rows=14000 RHS=112000 packed=0 | legal-policy | 0.9902 / 0.9960 | 0.9895 / 0.9968 | 0.9865 / 0.9943 | 0.9839 / 0.9899 | 0.9897 / 0.9953 |
| CG-A-sized HPCG-pointers n=13 rows=14000 RHS=112000 packed=0 | legal-hint | 1.1243 / 1.1167 | 1.1361 / 1.1262 | 1.1228 / 1.1188 | 1.1242 / 1.1198 | 1.1251 / 1.1167 |
| CG-A-sized HPCG-pointers n=13 rows=14000 RHS=112000 packed=0 | legal-policy | 0.9991 / 0.9924 | 1.0083 / 0.9995 | 0.9974 / 0.9938 | 0.9987 / 0.9947 | 1.0005 / 0.9930 |
| CG-A-sized CSR n=13 rows=14000 RHS=112000 packed=1 | legal-hint | 0.7421 / 0.7488 | 0.7420 / 0.7482 | 0.7422 / 0.7486 | 0.7420 / 0.7487 | 0.7394 / 0.7459 |
| CG-A-sized CSR n=13 rows=14000 RHS=112000 packed=1 | legal-policy | 0.9829 / 0.9918 | 0.9805 / 0.9887 | 0.9821 / 0.9905 | 0.9860 / 0.9949 | 0.9830 / 0.9916 |
| CG-A-sized HPCG-pointers n=13 rows=14000 RHS=112000 packed=1 | legal-hint | 1.1134 / 1.1051 | 1.1130 / 1.1086 | 1.1130 / 1.1062 | 1.1133 / 1.1046 | 1.1207 / 1.1139 |
| CG-A-sized HPCG-pointers n=13 rows=14000 RHS=112000 packed=1 | legal-policy | 0.9988 / 0.9913 | 0.9985 / 0.9945 | 0.9985 / 0.9924 | 1.0005 / 0.9926 | 1.0055 / 0.9994 |
| CG-A-sized CSR n=27 rows=14000 RHS=112000 packed=0 | legal-hint | 0.9764 / 0.9802 | 0.9768 / 0.9801 | 0.9774 / 0.9765 | 0.9771 / 0.9814 | 0.9766 / 0.9817 |
| CG-A-sized CSR n=27 rows=14000 RHS=112000 packed=0 | legal-policy | 0.9930 / 0.9969 | 0.9939 / 0.9973 | 0.9982 / 0.9973 | 0.9940 / 0.9984 | 0.9937 / 0.9989 |
| CG-A-sized HPCG-pointers n=27 rows=14000 RHS=112000 packed=0 | legal-hint | 1.4245 / 1.4160 | 1.4324 / 1.4265 | 1.4318 / 1.4250 | 1.4323 / 1.4260 | 1.4330 / 1.4261 |
| CG-A-sized HPCG-pointers n=27 rows=14000 RHS=112000 packed=0 | legal-policy | 1.0001 / 0.9941 | 0.9996 / 0.9954 | 0.9966 / 0.9920 | 1.0001 / 0.9958 | 0.9990 / 0.9941 |
| CG-A-sized CSR n=27 rows=14000 RHS=112000 packed=1 | legal-hint | 0.7453 / 0.7527 | 0.7371 / 0.7326 | 0.7285 / 0.7319 | 0.7314 / 0.7372 | 0.7281 / 0.7326 |
| CG-A-sized CSR n=27 rows=14000 RHS=112000 packed=1 | legal-policy | 0.9946 / 1.0046 | 0.9836 / 0.9776 | 0.9933 / 0.9979 | 0.9970 / 1.0050 | 0.9920 / 0.9981 |
| CG-A-sized HPCG-pointers n=27 rows=14000 RHS=112000 packed=1 | legal-hint | 1.3400 / 1.3315 | 1.3408 / 1.3363 | 1.3416 / 1.3429 | 1.3432 / 1.3339 | 1.3408 / 1.3347 |
| CG-A-sized HPCG-pointers n=27 rows=14000 RHS=112000 packed=1 | legal-policy | 1.0007 / 0.9944 | 0.9996 / 0.9962 | 0.9999 / 1.0008 | 1.0014 / 0.9945 | 0.9977 / 0.9931 |
| memory-sized CSR n=13 rows=32768 RHS=16777216 packed=0 | legal-hint | 6.9602 / 6.9710 | 6.9719 / 7.0123 | 6.9516 / 6.9542 | 6.9639 / 6.9998 | 6.9506 / 7.0166 |
| memory-sized CSR n=13 rows=32768 RHS=16777216 packed=0 | legal-policy | 6.9136 / 6.9243 | 6.9123 / 6.9524 | 6.9513 / 6.9539 | 6.9165 / 6.9522 | 6.9697 / 7.0359 |
| memory-sized HPCG-pointers n=13 rows=32768 RHS=16777216 packed=0 | legal-hint | 3.6362 / 3.6258 | 3.6378 / 3.6292 | 3.6312 / 3.6233 | 3.6373 / 3.6309 | 3.6354 / 3.6288 |
| memory-sized HPCG-pointers n=13 rows=32768 RHS=16777216 packed=0 | legal-policy | 3.6346 / 3.6242 | 3.6467 / 3.6381 | 3.6131 / 3.6053 | 3.6434 / 3.6370 | 3.6312 / 3.6246 |
| memory-sized CSR n=13 rows=32768 RHS=16777216 packed=1 | legal-hint | 1.5011 / 1.5076 | 1.5223 / 1.5138 | 1.5063 / 1.5125 | 1.5117 / 1.5138 | 1.5054 / 1.5125 |
| memory-sized CSR n=13 rows=32768 RHS=16777216 packed=1 | legal-policy | 1.4773 / 1.4837 | 1.4968 / 1.4885 | 1.4822 / 1.4883 | 1.4861 / 1.4882 | 1.4814 / 1.4884 |
| memory-sized HPCG-pointers n=13 rows=32768 RHS=16777216 packed=1 | legal-hint | 1.3419 / 1.4024 | 1.3421 / 1.3346 | 1.3457 / 1.3351 | 1.3432 / 1.3352 | 1.3449 / 1.3450 |
| memory-sized HPCG-pointers n=13 rows=32768 RHS=16777216 packed=1 | legal-policy | 1.3555 / 1.4166 | 1.3466 / 1.3391 | 1.3503 / 1.3398 | 1.3476 / 1.3396 | 1.3485 / 1.3486 |
| memory-sized CSR n=27 rows=32768 RHS=16777216 packed=0 | legal-hint | 6.9725 / 6.9790 | 7.0189 / 7.0207 | 6.9870 / 6.9816 | 7.0127 / 7.0123 | 7.0158 / 7.0125 |
| memory-sized CSR n=27 rows=32768 RHS=16777216 packed=0 | legal-policy | 6.9654 / 6.9719 | 6.9719 / 6.9737 | 6.9086 / 6.9032 | 6.9680 / 6.9677 | 6.9606 / 6.9574 |
| memory-sized HPCG-pointers n=27 rows=32768 RHS=16777216 packed=0 | legal-hint | 5.1782 / 4.9148 | 4.9080 / 4.8882 | 4.8616 / 4.8568 | 4.8636 / 4.8668 | 4.8163 / 4.8219 |
| memory-sized HPCG-pointers n=27 rows=32768 RHS=16777216 packed=0 | legal-policy | 5.1849 / 4.9212 | 4.9156 / 4.8958 | 4.8618 / 4.8570 | 4.8611 / 4.8643 | 4.8924 / 4.8980 |
| memory-sized CSR n=27 rows=32768 RHS=16777216 packed=1 | legal-hint | 1.5138 / 1.5171 | 1.5179 / 1.5208 | 1.5184 / 1.5208 | 1.5175 / 1.5209 | 1.5138 / 1.5157 |
| memory-sized CSR n=27 rows=32768 RHS=16777216 packed=1 | legal-policy | 1.4950 / 1.4984 | 1.4993 / 1.5022 | 1.5002 / 1.5026 | 1.5055 / 1.5089 | 1.4961 / 1.4979 |
| memory-sized HPCG-pointers n=27 rows=32768 RHS=16777216 packed=1 | legal-hint | 1.6071 / 1.6009 | 1.6198 / 1.5539 | 1.6262 / 1.6209 | 1.6187 / 1.6137 | 1.6260 / 1.6195 |
| memory-sized HPCG-pointers n=27 rows=32768 RHS=16777216 packed=1 | legal-policy | 1.6075 / 1.6013 | 1.6219 / 1.5559 | 1.6270 / 1.6217 | 1.6192 / 1.6142 | 1.6286 / 1.6222 |

Across all memory-sized cases, both legal routes beat 1.05 in every
sample: KNC-relative speedup range 1.3419..7.0189. The layouts and locality
patterns must remain separate; the ticket's 1.62x is not a universal
speedup for every case. The HPCG fixture is indexed synthetic work,
not the application stencil. NPB-CG/HPCG application A/B is pending.

For cache/CG-A cases the policy chooses the scalar arm, but that does
not establish identical generated code or timings. 10 of the policy
samples exceed a 2% elapsed-time regression; the largest is 2.429%
(cache-sized CSR n=13 rows=32 RHS=32768 packed=0, sample 2). Default-on is not justified by this result alone.
The implementation switch remains explicit; the lead decides its default.

### Revised red is not ready for approval

The same two test files now request `-mknc-indirect-prefetch` for
positive off/fast contraction modes and for the `-Os` exclusion.
Disabled requests `-mno-knc-indirect-prefetch -fprefetch-loop-arrays`.
Positive assembly counts must strictly exceed that disabled baseline.
The HPCG per-row-pointer/count reduction and aliasing `int *out`
negative nest are present. No absent switch is silently substituted:
each requested compilation fails on the current compiler.

The new scanner follows dotted SSA names and PHI ancestry. A compiled
in-loop hint exercises actual post-ivopts `ivtmp.N_M` PHIs and passes;
the straight hint, stream rejection and row-local rejection controls
also pass. It attempts to require a branch edge dominating the ordinary
hinted-index load, with that index bounded by a later row's bound.
However, both legal cross-row positive controls fail the scanner, so
this is NOT an acceptable missing-feature-only red yet.

Reduced cause, visible in `phase2-controls.optimized`: CSR has a
pointer PHI initialized from `row`, incremented by four bytes; the
start load uses that PHI and the future bound loads at byte offset 16.
The scanner treats PHIs as independent affine atoms and cannot recover
the `row` base. HPCG has separate count-pointer and cols-pointer PHIs
(four/eight-byte strides, matching predecessors); it cannot prove that
the count and pointer refer to the same next row. Presence scanning
works because ancestry tracing crosses PHIs; affine normalization does not.

First attempt failed on a missing C closing brace (fixed). The second
compiled/assembled/linted controls and passed scalar-fold and installed
baseline identity checks, but had the two scanner failures above plus
four expected missing-switch errors. No third attempt, GCC modification,
GCC build, native rerun or x86 run was performed. Logs:
`.work/_state/logs/s12_30_phase2_revised_red-20261115-023501.log` and
`.work/_state/logs/s12_30_phase2_revised_red-20261115-023546.log`.

Per AGENTS.md's two-failed-attempt rule, ask whether to prove bounds in
the transformation's SSA dump before ivopts (retaining optimized-dump
loop controls/count checks), or add paired pointer-PHI recurrence
normalization to the optimized-dump checker. No checks were weakened.

### Pre-ivopts bounds dump attempt (2026-11-15)

Applied the lead's 02:48 ruling: controls explicitly enable stream
prefetch; bounds checks use `-fdump-tree-aprefetch` for controls and
positive modes. Missing dumps or required function bodies fail. Presence,
post-ivopts loop control, negatives, instruction counts, scalar folds and
installed baseline identity still use optimized GIMPLE/assembly.

The one T1 attempt still fails CSR and HPCG bounds controls, in addition
to the four expected missing-switch compilations. Compile/assemble/lint,
the required aprefetch bodies, presence controls, row-local rejection,
scalar folds and baseline identity pass. Log:
`.work/_state/logs/s12_30_phase2_aprefetch_red-20261115-030417.log`;
inner results: `.work/_state/logs/check_gcc16_t1-20261115-030418.log`.

Reduced GIMPLE in `.work/_shared/S12-30/phase2-controls.aprefetch`:

* `explicit_csr` (function begins at line 2420): `_22 = (unsigned long)
  row_27(D); _21 = _22 + _6; _7 = (const int *) _21;`, where
  `_6 = (_1 + 4) * 4` and `_1` comes from the outer `i_40` PHI.
  `bound_30 = *_7` is guarded by `rows_25(D) - i_40 > 3`;
  the hinted index load is guarded by `bound_30 - j_41 > 32`.
* `explicit_hpcg` (function begins at line 2675): `_35 = (unsigned long)
  count_24(D); _19 = _35 + _3; _4 = (const int *) _19;` and
  `_18 = (unsigned long) cols_26(D); _17 = _18 + _6;
  _7 = (const int * const *) _17;`. Both offsets use `_31 + 1`,
  scaled by four/eight. `_5 = *_4; if (_5 > j_37)` guards
  `_8 = *_7; _11 = _8 + j_37 * 4; _12 = *_11` feeding the hint.

Unlike the optimized dump, these addresses retain the outer integer PHI.
The affine cast-removal regex accepts `long unsigned int` but does not
accept `unsigned long` (its `long ` alternative requires a trailing space).
Thus these pointer-to-integer casts remain unsupported expressions.
This is a source inspection diagnosis, not a verified fix. Per ruling
item 4, stopped after the failed aprefetch controls; no affine walker
extension, second test, GCC change, build or native run. Ask whether to
make the small cast-token parsing correction and rerun the T1 red.

### Cast-token correction and accepted-shape red (2026-11-15)

Applied the lead's 03:15 ruling: made the trailing space optional on
the const/unsigned/signed/long/short cast tokens, and included the
unsupported expression in the affine ValueError diagnostic. No other
affine-walker changes or new test files.

The single authorized T1 rerun passes CSR future-bound and HPCG
future-pointer/count controls on the aprefetch dump, the row-local
rejection, optimized presence and ivtmp PHI controls, compile/assemble/
lint, scalar folds, negatives and installed baseline identity. Its only
four failures are the unrecognized indirect-prefetch switch in disabled,
off, fast and size modes. This is the missing-feature-only phase-two red.

Command: `python tools/run.py --name s12_30_phase2_cast_red --inputs
tools/s12_30_precision.py tools/s12_30_precision.c -- python tools/check
t1 --compiler gcc16 --sparse-indirect` (lane gcc2). Exit 1 as expected.
Log: `.work/_state/logs/s12_30_phase2_cast_red-20261115-031754.log`;
inner results: `.work/_state/logs/check_gcc16_t1-20261115-031754.log`.
No GCC change/build or native phase-two run; application A/B, T0/T2,
ICE sweeps and x86 identity remain pending. The implementation must keep
the switch explicit and default off, test the threshold outside a
versioned nest, and insert hints in or before loop prefetch with target
specifics behind a hook, as ruled on the ticket.

### Compiler implementation awaiting the lead build (2026-11-15)

The gcc2 branch now has an opt-in `-mknc-indirect-prefetch` policy hook
and a transformation at the start of the existing loop-prefetch pass,
before stream prefetch and ivopts. Shared i386 wiring is isolated in its
own commit (ADR-0006); target policy lives in `i386-knc.cc`. The switch
initially defaults off, as required for the compiler guard proof. The
ticket's eventual default-on requirement still needs the application A/B.

The recognizer requires a scalar add/product recurrence and a signed
32-bit, unit-step counted index with a proven ascending entry test. It
matches natural-stride indirect loads, without symbol or application-name
tests. It leaves the original arithmetic and memory operations intact.
Unsupported loop/address shapes fail closed. This first implementation
does not claim complete coverage of application-generated GIMPLE.

For a flat CSR nest it matches the same row array at outer index `i` and
`i+1`, then guards `row[i+4]` by a widened `rows-i > 3`. The subsequent
ordinary `col[j+32]` load is guarded by widened `bound-j > 32`. For a
per-row-pointer nest it matches the count and pointer arrays at the same
outer index, guards the next count by `rows-i > 1`, and guards the next
pointer and index loads by `j < next_count`. Empty future rows therefore
do not require a usable column pointer. These guards currently execute
inside the original inner loop; performance is not inferred from the
handwritten gate, whose metadata work was outside that loop.

Cross-row eligibility requires a zero-based counted outer loop, one inner
loop, an empty-row test executed on every outer iteration, no other
conditionals, no calls/volatile operations, and no store whose alias type
can overlap either metadata array. The store check is conservative for
the whole array, rather than testing just the current element. It rejects
cross-row speculation with strict aliasing disabled. A single loop, or a
nest failing these extra checks, may still receive a row-local guarded
hint if its inner loop has no stores, early exit, calls or volatile work.
Non-call exceptions and trapping integer arithmetic disable the transform.

Eligible nests are versioned before adding any hint, with a single outer
trip-count policy test at 16384 rows. The unchanged arm remains available
to the normal stream-prefetch pass. The guard scales a widened count, as
the existing stream versioning helper does, to avoid introducing a new
IV upper-bound constraint into the unchanged arm. Generated assembly and
cache-sized timings remain unverified.

The existing T1 checker now enforces the lead's accepted-red follow-ups:
controls mode has no automatic hints and its probe bodies must equal
explicit switch-off; `alias_bounds` may have a row-local hint but cannot
have a later-row-bounded hint. No affine-walker changes or new test files.

`tools/s12_30_precision.py --compiler-proof` is prepared to build the same
legal guard-page and timing fixtures from unhinted C using donor, gcc2
switch-off, gcc2 switch-on, and gcc2 switch-on/contract-fast TUs. It requires
the pass to report both cross-row shapes in their dumps before linking;
a missing transformation fails staging. This command has **not run** and
`compiler-gate` has **not been staged**. After the lead's build, run through
`tools/run.py`, then request one lead card run of
`.work/_shared/S12-30/compiler-gate 12345` with
`card_run --threads 1 --timeout 590`. The timing remains single-core,
five samples of at least 0.5 seconds, with the existing cache/CG-A/memory
fixtures and both layouts. A crash or timeout is not a correctness pass.

No GCC build or new test was run in this session: AGENTS.md reserves GCC
builds for the lead. T1 green, T0/T2, ICE sweeps, compiler-generated native
guard/timing results, NPB-CG/HPCG/control A/B, and default-on are pending;
x86 not run. Resume with the built gcc2 compiler, not the installed prefix.


### First built compiler T1 and guard-placement correction (2026-11-15)

Ran the requested default-off T1 once against lane gcc2 at
`4e2b026712d`, through `tools/run.py --name s12_30_phase2_green --inputs
tools/s12_30_precision.py tools/s12_30_precision.c -- python tools/check
t1 --compiler gcc16 --sparse-indirect`. It failed only the two
`sparse_slice` assembly-count assertions (contract-off and contract-fast).
Compile/assemble/lint, all presence/exclusion and bounds checks,
default-off identity, scalar folds and installed baseline identity passed.
Log: `.work/_state/logs/s12_30_phase2_green-20261115-041029.log`.

The emitted slice with the switch off has four static stream-prefetch
instructions in its long-loop arm. With the switch on it has one bounded
indirect hint and no stream hints: inserting the conditional index load
prevents the ordinary stream pass from recognizing its straight-line
body. The checker correctly fails the required greater-than comparison;
its assertions have not been changed. This is a compiler interaction,
not a missing or unsafe indirect hint.

The correction versions lone/row-local loops on their widened trip count
at 16384, just as nests are versioned on their outer count. Its unchanged
short arm remains eligible for the existing stream pass. This also avoids
unconditional short-loop hints in the eventual default-on step. That
threshold for lone loops is a conservative policy choice, not a measured
lone-loop speedup. The current switch still defaults off pending the
required intermediate green and native proof.

Also addressed the lead's 03:41 row-invariant-work request. The measured
handwritten legal gate computed metadata outside the inner loop; the
first compiler build did not. The correction versions the inner loop
once per nonempty current row on `rows-i > R`, loads the future bound in
its true preheader, and keeps only the column bound check and hint in
the inner body. HPCG additionally versions on a positive future count
before loading its future pointer once. Empty future rows therefore do
not read an uninitialized pointer. The false versions keep the original
reduction; no speculative sentinel or merged pointer is needed. This
adds loop copies, whose code-size and timing costs remain to be checked.
The existing pre-ivopts structural scanner is unchanged.

The implementation uses the existing `loop_version` mechanism in
`gcc/cfgloopmanip.cc`; the new metadata blocks are reached only after the
current inner-loop entry test. Index bounds and arithmetic order are
unchanged. These are source-level claims awaiting the lead build and
native guard-page proof, not passing test or performance results.

GCC builds remain reserved for the lead by AGENTS.md. No second T1 run,
GCC build, T0/T2, ICE sweep or native run was attempted against these
unbuilt edits. `compiler-gate` is not staged. After the build, resume T1,
check for duplicate per-iteration stream hints in the new hinted arms,
then T0/T2, ICE and compiler-proof staging. Default-on and the default
-O2 NPB-CG/HPCG/control A/B remain pending; x86 not run.

GCC correction commit: `a36fc224773` (lane gcc2). GCC diff against `knc`
has no whitespace errors. The three ticket-owned main-repository source
and note files are LF. Hook documentation and its generated copy were
updated together; no i386 file changed in this correction.

### Built hoisted version: intermediate green and native staging (2026-11-15)

The targeted T1 rerun against built gcc2 `a36fc224773` passes. This is
the required default-off intermediate step: default probe identity with
explicit switch-off, cross-row and slice bounds, scalar folds, exclusions,
compile/assemble/lint and the installed baseline check all pass. The slice
now has five static hints with the switch on and four with it off.
Command: `python tools/run.py --name s12_30_phase2_green_hoisted --inputs
tools/s12_30_precision.py tools/s12_30_precision.c -- python tools/check
t1 --compiler gcc16 --sparse-indirect`.
Log: `.work/_state/logs/s12_30_phase2_green_hoisted-20261115-043829.log`.

The first compiler-proof staging attempt correctly rejected its struct
kernels: both received only `row-local bound`, which does nothing at
13/27 entries. Fields loaded within the outer loop do not satisfy the
current recognizer's outer-invariant requirements. The proof now uses
raw-argument, noinline/noclone kernels matching T1, called by identical
matrix wrappers in all slots. It still requires the exact `future row
bound` and `next-row pointers` diagnostics, plus a row-local transformation
in the separate lone-loop kernel. No assertion was weakened. This is a
compiler coverage limitation, not proof that the real applications are
transformed: their dumps must be checked when their A/B is staged.
Source inspection also finds that HPCG 3.1 `SparseMatrix.hpp` declares
`nonzerosInRow` as `char *`, promoted to `int` in `ComputeSPMV_ref.cpp`;
the present raw probe uses `int *`. `indirect_array` currently requires a
direct load, without stripping that promotion. SymGS uses subtraction,
whereas `indirect_product` currently matches addition. These are additional
application-coverage risks, not measured application outcomes, and must
be resolved or explicitly reported before claiming the HPCG A/B acceptance.
Failed staging log:
`.work/_state/logs/s12_30_compiler_gate-20261115-044149.log`.

Code size (ELF `.text`, including the three kernels and their wrappers):

| Build | Bytes | Static hints CSR / HPCG / lone |
| --- | ---: | --- |
| GCC 5.1.1 | 364 | 0 / 0 / 0 |
| gcc2 switch off | 1334 | 4 / 4 / 4 |
| gcc2 switch on, contract off | 2891 | 9 / 13 / 5 |
| gcc2 switch on, contract fast | 2891 | 9 / 13 / 5 |
| gcc2 handwritten forced hint, automatic switch off | 606 | 1 / 1 / 1 |

Versioning adds 1557 bytes (116.7%) to this three-kernel `.text`. These
are static instruction counts across mutually exclusive versions. The
hinted inner arms contain one indirect hint and no stream hints; the
remaining eight/twelve/four stream instructions are in unhinted versions.
There is no second per-iteration hint for the new future-column load.

The detailed dump corrects the earlier suggestion that stream references
were not recognized. `compiler-enabled.aprefetch` does recognize val/col
streams, with prefetch moduli 8/16, but chooses unroll factor 1 in the
hinted arms (CSR lines 1397-1547, HPCG 4751-4873). In
`tree-ssa-loop-prefetch.cc::schedule_prefetches`, the existing rule rejects
`prefetch_mod / unroll_factor > 4`. The extra CSR column reference is also
pruned by `prefetch_before`. Unhinted copies have factor 8 and receive
their ordinary stream hints. The dump establishes that scheduling reason;
no performance benefit from the changed scheduling is assumed.

`compiler-gate` compares donor, gcc2 switch-off, gcc2 switch-on, and a
handwritten forced-hint slot on identical runtime inputs. Contract-fast
also runs the full guard suite. The raw kernels retain the legal gate's
metadata placement and guard rules. Cross-row guard fixtures cover empty
and decreasing rows, every length 1..33, metadata/index/value arrays ending
at protected pages, and both policy arms. A separate lone-loop guard check
covers lengths 0/1/32/33/16383/16384/16385. Exact arithmetic is compared
against the ordered long-double reference. No native result is claimed.

The timing grid has 34 cases, five alternating-order paired samples of at
least 0.5 seconds for four kernels per case. Batches target 25 ms to limit
overshoot within the one 590-second lead window; the program alarms at
570 seconds. It pins one granted CPU for this single-core timing experiment.
Cases: CSR and independent shuffled per-row pointers, n=13/27, 32 KiB RHS
at 32/4096/8192/14000/16384/32768 rows; CG-A-sized 14000-row/112000-byte RHS;
32768 rows with 16 MiB RHS; a 104^3 HPCG-shaped 27-neighbor stencil with
real boundary counts; and a 262144-entry lone loop with 16 MiB RHS.
The stencil is a SpMV shape fixture, not the full HPCG fixed-work benchmark.

Threshold selection is pending those measurements. The manual slot forces
hints on below 16384, while the existing compiler switch retains its
16384-row/trip policy. Output labels distinguish these facts. Consequently
the below-threshold manual comparison is policy evidence, not a claim
that the compiler's hinted arm ran there. Select the smallest measured
candidate that meets the ticket's <=1% slowdown criterion on all relevant
small/cache controls; if none does, report that rather than inventing a
threshold. Any changed compiler threshold still requires its own proof.
M4's application A/B must use NPB class A (CG 14000 rows), HPCG S11-28 fixed
work and two controls at full/3100/5100, with default `-O2 -march=knc` on.
It is not staged with the current default-off compiler.

Final staging command: `python tools/run.py --name
s12_30_compiler_gate_final --inputs tools/s12_30_precision.py
tools/s12_30_precision.c --
..\_shared\toolchain\cygwin\bin\python3.12.exe
tools/s12_30_precision.py --compiler-proof`. PASS compile/assemble/lint
and the three required transformation diagnostics for both contraction
modes. Log:
`.work/_state/logs/s12_30_compiler_gate_final-20261115-044552.log`.
Binary: `.work/_shared/S12-30/compiler-gate`, argument `12345`; lead only,
`tools/card_run --threads 1 --timeout 590`. All inputs are generated at
runtime; no additional staged files are needed. A timeout or fault is a
failure, not a partial timing pass. The final source/note files are LF and
both main-worktree and GCC `knc...HEAD` whitespace checks are clean.

T0/T2 command: `python tools/run.py --name s12_30_t0_t2 --inputs tools
tests/regress tests/tools -- python tools/check t0 t2 --compiler gcc16`.
T0 passes all 56 tests (36 regressions, 8 doctor, 6 portability, 6 lint).
T2 passes the initial short-vector cross-compiler link/ABI checks, then
stops with `[Errno 13] Permission denied` writing
`.work/_shared/S10-01/vecarg-O0-O2.mic`. This is an infrastructure failure;
T2 is incomplete, not passed. No permission change, removal of the existing
binary, or rerun was attempted. Logs:
`.work/_state/logs/s12_30_t0_t2-20261115-043930.log` and
`.work/_state/logs/check_gcc16_t0_t2-20261115-043930.log`.

The switch-on ICE sweep compiles the gcc2 lane's C torture and vector
corpora at O2/O3, retaining unselected per-test option directives, with
four workers. It counts ordinary compiler diagnostics separately; it is
not a DejaGnu, assembly, or native pass claim. The C torture portion
completed: 2003 sources per level, 1971 compiled and 32 ordinary compile
errors at each level, zero ICEs or timeouts. The first vector attempt
stopped in the harness option parser on the escaped quotes in
`gcc.dg/vect/pr63530.c`'s directive. The regex now treats escaped characters
inside quoted directives as part of that token. Only the incomplete vector
portion is rerun; the completed torture portion is not repeated. First log:
`.work/_state/logs/s12_30_indirect_ice_sweeps-20261115-044434.log`.

The vector-only rerun completed and **failed**: 2349 sources per level;
O2 has 2168 compiled / 181 ordinary errors / zero ICEs; O3 has 2166
compiled / 181 ordinary errors / two ICEs; zero timeouts. Command:
`python tools/run.py --name s12_30_indirect_vect_ice --inputs
tools/s12_30_precision.py --
..\_shared\toolchain\cygwin\bin\python3.12.exe
tools/s12_30_precision.py --ice-sweep vect`.
Log: `.work/_state/logs/s12_30_indirect_vect_ice-20261115-045317.log`;
commands and diagnostics: `.work/_shared/S12-30/ice-sweep.log`.

The two isolated upstream inputs are in gcc2's `gcc/testsuite/gcc.dg/vect/`:

- `O3-vect-pr32243.c`, `-O3 -fno-ipa-cp-clone -march=knc
  -mknc-indirect-prefetch`: `put_mono_values_s8` cannot reload
  `*knc_sign_extendv16qiv16si2`, then ICEs in `curr_insn_transform`,
  `lra-constraints.cc:4553` (diagnostic starts at log line 1944).
- `vect-pr123221.c`, `-O3 -fno-tree-pre -march=knc
  -mknc-indirect-prefetch`: segmentation fault during `vect`, with
  `vect_analyze_slp_reduc_chain`, `tree-vect-slp.cc:4275` in the backtrace
  (log line 3695).

Both commands also use the gcc2 `-B` prefix and shared sysroot, with
`-w -S <source> -o /dev/null`; the exact invocations are in the log.
No switch-off rerun was made, so neither ICE is claimed to be new or
pre-existing. The scan's ordinary-error category also contains a remaining
harness limitation: `pr63530.c`'s escaped quotes survive into its `--param`
argument, which the driver rejects at both levels (log lines 1506/3482).
Thus that source has not received a valid compiler test. No third sweep
or further parser/compiler fix was attempted after these two failed
sweep attempts, per AGENTS.md.

Handoff requires the lead to classify the two ICE inputs and resolve the
T2 output permission, as well as run the staged compiler guard/timing
binary and return its complete output. No GCC change/build in this session;
native proof, measured threshold choice, default-on, application A/B and
x86 identity remain pending. The intermediate T1 and T0 passes do not
make the ticket ready to submit.

### Real application dump check and default-on preparation (2026-11-15)

Followed the 05:19 ruling: no merge/rebase and no sandbox T2. The lead
reported T2 36/0 at GCC `bfc31546ede`; the earlier pr32243 failure is fixed
there and pr123221 is tracked as S12-38. No sweep or T0/T1 was repeated.

Added `--application-dumps` to the existing Python tool. It compiles the
actual NPB 3.4.2 class-A Fortran CG translation unit and HPCG 3.1 reference
SpMV/SymGS translation units at `-O2 -march=knc -mknc-indirect-prefetch
-fopenmp`, using lane gcc2. Sources stay in the shared corpus; outputs
stay under `.work/_shared/S12-30/application-*`. This is compilation and
dump inspection only, not a native or whole-application performance test.

CG compiled successfully at `bfc31546ede` and its aprefetch dump contains
zero `Bounded indirect prefetch` diagnostics. Both hot sparse nests are
missed, not merely excluded by the 16384-row policy:

| Nest in `conj_grad_._omp_fn.0` | Evidence in `application-cg.aprefetch` |
| --- | --- |
| Repeated `q = A.p` | Lines 5576-5592: `j_139 = _137 + 1`, descriptor data/offset loads and `# j_26 = PHI <j_139(31), _145(71)>`. Lines 5663-5668: column load, conversion, descriptor offset, indexed RHS load, product and ordered addition. |
| Residual `r = A.z` | Lines 4997-5012: `j_292 = _290 + 1`, descriptor data/offset loads and `# j_13 = PHI <j_292(15), _298(63)>`. Lines 5084-5089: column load, conversion, descriptor offset, indexed RHS load, product and ordered addition. |

For example the first nest has:

```text
5663: _159 = MEM <integer(kind=4)[0:]> [(integer(kind=4)[0:] *)_156][_158];
5664: _160 = (integer(kind=8)) _159;
5665: _161 = _155 + _160;
5666: _162 = MEM <real(kind=8)[0:]> [(real(kind=8)[0:] *)_154][_161];
5667: _163 = _153 * _162;
5668: suml_164 = _163 + suml_364;
```

These references are array references with descriptor offsets, whereas
`indirect_load_ref` accepts only a direct zero-offset MEM_REF and
`indirect_product` expects an SSA pointer-plus address. That alone rejects
the products. Cross-row matching also requires an outer start of zero;
the OpenMP partition starts at a thread-dependent value plus one. The
outer continuation compares the current row against the inclusive end
(lines 5027 and 5606), whereas `indirect_counted` matches the incremented
IV. Supporting these forms requires a general recognition/bounds change,
not a program-name exception or a lower threshold. The stream hints in
this dump do not establish indirect-prefetch coverage.

The application-dump command had two infrastructure failures:

1. First attempt: CG could not find `ieee_arithmetic.mod`. Fixed by passing
   the lane build's `k1om-mpss-linux/libgfortran` as the intrinsic module
   directory. Log: `.work/_state/logs/s12_30_application_dumps-20261115-052221.log`.
2. Second attempt: CG succeeded, then HPCG SpMV stopped at
   `bits/stl_pair.h:65:11: fatal error: compare: No such file or directory`.
   The explicit C++ build-tree include directory lacks `compare`; the
   corresponding installed lane-2 include directory contains it:
   `.work/_shared/gcc-knc-16.2.0-2/k1om-mpss-linux/include/c++/16.2.0`.
   Log: `.work/_state/logs/s12_30_application_dumps-20261115-052258.log`.

No third attempt was made, per AGENTS.md. SpMV has no completed dump and
SymGS was not compiled. Their char-count promotion, struct-field loads
and minus reductions therefore remain source-level coverage risks, not
newly proven dump misses. A resumed run should compile only those two
remaining translation units, with the complete lane-2 C++ headers.

Prepared default-on separately in the GCC tree as directed. The KNC
option defaults now enable indirect prefetch at O2 and above, excluding
size optimization, with `SET_OPTION_IF_UNSET` preserving an explicit
`-mno-knc-indirect-prefetch`. The existing pass gate still honors
`-fno-prefetch-loop-arrays`; the policy hook still requires TARGET_KNC.
One named constant, `knc_indirect_prefetch_min_trips`, supplies the
outer-row and lone-loop trip cutoff. Its value remains **provisional
16384**, pending window 6; no measured threshold is claimed.

The prepared T1 keeps scanner controls explicitly switch-off, checks
plain default O2 for bounds-safe indirect hints, compares those probe
bodies with explicit switch-on, and moves the scalar baseline identity
comparison to the current compiler's switch-off build. These changes
are unbuilt/untested; the accepted intermediate default-off green is
the last T1 result. No GCC build is requested before the queued
compiler-gate result. No coverage fix, new native result or application
A/B is claimed; x86 not run.

Default-on preparation commit: GCC `36cb8b9ff30`. Main-worktree whitespace
and GCC diff against `knc` are clean; edits preserve LF. The installed
and build-tree compilers still represent `bfc31546ede`, not this commit.

### HPCG include-path retry (2026-11-15)

Applied the 05:28 authorization to use the installed lane-2 C++ headers.
The tool now accepts `--application-dumps hpcg`, which compiles only SpMV
and SymGS and leaves the completed CG check alone. Fortran recognition
belongs to S12-40 under the narrowed ticket scope.

Two invocations failed in this session:

1. The Windows wrapper could not launch `cygwin/bin/python3.exe`; the
   executable is `python3.12.exe`. No compiler ran in this invocation.
2. Using `python3.12.exe` reached SpMV compilation with the installed C++
   headers, then failed at `ComputeSPMV_ref.cpp:28` because `omp.h` was
   absent from the build-tree driver's include search. Log:
   `.work/_state/logs/s12_30_hpcg_dumps-20261115-053225.log`.

Prepared an explicit system include for the existing lane-2
`gcc-build-2/k1om-mpss-linux/libgomp/omp.h`. This correction has not been
run: stopping for the two-attempt rule. Resume command:

```text
python tools/run.py --name s12_30_hpcg_dumps --inputs tools/s12_30_precision.py -- C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin/python3.12.exe tools/s12_30_precision.py --application-dumps hpcg
```

No HPCG dump or recognition result is available yet. GCC source and the
separate default-on commit are unchanged. Window-6 guard/timing output
is still absent from the ticket; the threshold remains provisional.
No build, native test, application A/B, T0/T1/T2 or sweep was rerun;
x86 not run.

### Completed HPCG dumps and focused coverage red (2026-11-15)

The authorized `--application-dumps hpcg` command now compiles both real
translation units successfully with the installed lane-2 C++ headers and
the libgomp build include. Log:
`.work/_state/logs/s12_30_hpcg_dumps-20261115-054907.log`.
The compiler is the previously built default-off GCC head; every dump
explicitly enables `-mknc-indirect-prefetch`.

Results from `.work/_shared/S12-30/application-*.aprefetch`:

* SpMV: one **row-local** transformation (spmv line 132), no cross-row
  recognition. Lines 318-320 load the matrixValues, mtxIndL and
  nonzerosInRow struct fields. The outer PHI at line 323 starts at `_19`,
  the OpenMP worker's assigned start, rather than zero. Lines 327-329
  load the byte count and widen it to `cur_nnz_33`. Lines 352-354 require
  `_76 > 131071`, where `_76` is eight times that count: the fallback
  needs at least 16384 inner iterations and cannot execute for a byte
  count (or HPCG's 27 entries). This is a functional recognition miss,
  despite the one transformation message.
* SymGS forward: no transformation. Lines 260 and 267-269 load and
  promote the byte count. The reduction at line 300 is
  `sum_95 = sum_106 - _25`, which the addition-only recognizer rejects.
* SymGS backward: no transformation. Lines 334 and 392-393 show the
  descending outer recurrence, with start `nrow_69 - 1` (line 331).
  Lines 338-340 load/promote the byte count; line 371 subtracts the
  product. Both subtraction and descending outer iteration are outside
  the current recognizer.

Source inspection of `gcc/tree-ssa-loop-prefetch.cc` identifies additional
requirements after the first rejection: `indirect_array` only matches an
unconverted load, so it cannot recover the char array behind the promoted
inner limit. `indirect_emit` must load the original byte type and then
widen, rather than load an int from that address. The whole-array alias
gate conservatively rejects a char bound against the outer double store.
Simply removing this check would be unsafe: char accesses may alias that
store. Cross-row speculation needs a valid disjointness proof or a runtime
alias guard. Struct field loads themselves are already hoisted in the real
dumps; they must remain invariant under any new alias proof.

Added three reduced C probes to the existing test file, covering struct
pointer tables and byte counts, a worker interval with a nonzero start,
and forward/backward subtract recurrences with an outer x store. The new
`--hpcg-shapes-t1` entry is also called by normal S12-30 T1. It requires an
actual indexed prefetch plus cross-row transformation, not a stream hint
or an ineffective row-local hint; it also checks scalar add/sub folds.
This is a recognition gate, not a substitute for the native guard suite
or the disjointness proof.

One focused run compiled, assembled and linted on/off probes. All three
switch-off controls pass. Switch-on fails exactly three recognition
checks, with ordered scalar folds retained. Log:
`.work/_state/logs/s12_30_hpcg_shapes_red-20261115-055114.log`.
Command:

```text
python tools/run.py --name s12_30_hpcg_shapes_red --inputs tools/s12_30_precision.c tools/s12_30_precision.py -- C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin/python3.12.exe tools/s12_30_precision.py --hpcg-shapes-t1
```

The narrowed scope assigns nonzero-start recognition to S12-40, but real
OpenMP HPCG SpMV needs that same C mechanism. The interval probe records
this dependency for lead review; it makes no Fortran requirement. No GCC
source was changed or built in this session. The separate default-on
commit and provisional 16384 threshold are unchanged. Window-6 results,
native safety, measured threshold, default-on validation, application A/B,
and lead x86 remain pending. Prior passing suites were not rerun.

### Corrected HPCG-shape red (2026-11-15, after the 05:57 review)

The previous red could not go green: `Gimple.indirect()` looked only for a
`col`/`cols` parameter, and the struct probes have none, so the on-check
failed for any compiler. Two corrections, same two files, no GCC change:

* Gate: `indirect()` now also accepts an index load whose address ancestry
  reaches a `->cols` field load. A hand-written control, `explicit_struct`
  (next-row hint in a struct nest, guarded by `rows-i > 1` and
  `j < count[i+1]`, no reduction), must scan as indirect and must not carry
  a `Bounded indirect prefetch` message. It passes in both builds, so the
  scanner is proven on the struct form and the message is proven to come
  only from the transformation.
* Probes: rewritten in HPCG form. `cur_vals`, `cur_inds` and `int cur_nnz`
  are loaded to locals before the inner loop; both sweeps load a diagonal
  and end with `sum += x[i]*diag; x[i] = sum/diag`. The switch-on dump now
  has the real shape: the four field loads sit in the nest preheader
  (forward: `_1 = m->vals; _5 = m->cols; _7 = m->count; _10 = m->diag`),
  the byte count is loaded and widened in the outer body, the row pointers
  are loaded behind the `cur_nnz > 0` test, the fold is
  `sum_47 = sum_54 - _25`, the SpMV outer PHI starts at `begin_27(D)` and
  the backward PHI starts at `rows - 1` with step -1.

One run (lane gcc2 build of `bfc31546ede`, switch passed explicitly):
compile, assemble and lint pass for both builds; switch-off passes all
three probes and the control; switch-on passes the control and fails
exactly the three probes with `missing cross-row indexed hint`. SpMV gets
only the row-local fallback (`Bounded indirect prefetch in loop 2:
row-local bound`, versioned on `_64 > 131071`), the two sweeps get nothing.
Log: `.work/_state/logs/s12_30_hpcg_shapes_red-20261115-060050.log`.

Policy test in the real outlined SpMV loop (ruling e; read from
`application-spmv.aprefetch`, not measured): the outer loop runs from `_19`
to `_20`, where `_20 - _19` is the worker's share `q.3_1` of the rows. A
cross-row version test on outer trips therefore sees one worker interval,
not the matrix: for 104^3 = 1,124,864 rows on 240 threads that is about
4,687 rows, below the provisional 16384, so SpMV would take the unhinted
arm at the current cutoff. Not changed here; the lead settles the
threshold with the window-6 data.

Still to do for green, per the 05:57 rulings: nonzero loop-invariant outer
start for the C forms; byte count with a run-time overlap test against the
outer double store in the versioning condition (`alias_bounds` stays
statically rejected); `MINUS_EXPR` only as `sum - product`; descending
outer loop with row `i-1` loaded only under `i-1 >=` the lower end; the
struct/byte-count, subtract and backward kernels added to `compiler-gate`
with a guard-page count and one overlapping-count case; then
`--application-dumps hpcg` must print next-row pointers for SpMV and both
sweeps. `compiler-gate` was not rebuilt: the staged binary is the one
queued for window 6. No GCC change or build; no native run; x86 not run.

### HPCG shapes green (2026-11-15, GCC `c70cf1ed484`)

GCC change, `gcc/tree-ssa-loop-prefetch.cc` only (lane gcc2, on top of the
default-on commit `36cb8b9ff30`; `git diff --check knc...HEAD` clean, LF):

* Byte count: the inner end may be one widening of the bound-array load.
  The emitted next-row load uses the array's own element type and repeats
  that one conversion (`_137 = *_136; _138 = (int) _137`). Per-row form
  only; flat CSR bounds stay unwidened.
* Subtract: `MINUS_EXPR` accepted only as `sum - product`.
* Outer start: any loop-invariant start; the zero-start test is gone.
  Nothing else used it: the guards use the loop's own end, and the policy
  count is `end - start`.
* Descending outer loop (per-row form only): step -1 with latch
  `next >= end`, `end` inclusive. No entry test is required, because the
  real SymGS backward nest has none (the forward nest's exit falls into
  it); the version test carries `start >= end` instead, and the
  lookahead guard is `row - 1 >= end`.
* Alias gate: unchanged for same-typed stores (`alias_bounds` still gets
  no cross-row hint) and for stores that may alias the pointer array.
  Where the store conflicts only because the bound array is byte-typed
  (alias set 0) and the store is `BASE[outer iv]` with an invariant base,
  the nest version test also requires the count range and the stored range
  to be disjoint. At most two such stores; anything else is rejected.
  The false arm is the untouched copy, so the unhinted code is today's.

Backward sweep, T1 probe (`hpcg-shapes-on.aprefetch`, function
`sparse_struct_backward`). Version test in the nest preheader, lower end 0,
start `i_35 = rows - 1`:

```text
  _86 = i_35 >= 0;                     start >= end
  _85 = _84 + 1;  _87 = _88 * 8;  _91 = _87 > 131071;     16384 rows
  _81 = _82 + 1;                       count + i_35 + 1
  _79 = _80 >= _81;                    x >= end of the count range
  _74 = _75 + _76;                     x + (i_35 + 1) * 8
  _72 = _73 >= _74;                    count >= end of the stored range
  _70 = (_72 | _79) & (_86 & _91);
```

Hinted row is `i - 1`, loaded only under `i - 1 >= 0` (folded to `i > 0`),
once per nonempty current row:

```text
  <bb 5>:  cur_inds_39 = *_6;
           if (i_54 > 0) goto <bb 28>; else goto <bb 27>;
  <bb 28>: _133 = (long long int) i_54;  _134 = _133 + -1;
           _136 = _7 + (sizetype) _134;  _137 = *_136;  _138 = (int) _137;
           if (_138 > 0) goto <bb 34>; else goto <bb 33>;
  <bb 34>: _159 = _5 + (sizetype) _134 * 8;  _160 = *_159;
  <bb 6>:  if (j_57 < _138) goto <bb 36>; else goto <bb 35>;
  <bb 36>: _163 = _160 + (sizetype) j_57 * 4;  _164 = *_163;
           __builtin_prefetch (x_44(D) + (sizetype) _164 * 8, 0, 3);
  <bb 35>: ... sum_48 = sum_55 - _25;
```

`_7` is `m->count`, `_5` is `m->cols`. Blocks 27 and 33 lead to unhinted
copies of the inner loop. The real SymGS backward nest has the same form
(`application-symgs.aprefetch` lines 2066-2159: `if (i_109 > 0)`, count at
`_9 + (i_109 - 1)`, pointer at `_7 + (i_109 - 1) * 8`).

Results (compiler built by this session, `tools/gcc_build.py --if-stale`,
PASS, 2.3 min, log `s12_30_gcc2_build-20261115-062303.log`):

| Check | Result | Log in `.work/_state/logs/` |
| --- | --- | --- |
| `--hpcg-shapes-t1` | PASS, on and off, three probes and the control | `s12_30_hpcg_shapes_green-20261115-062616.log` |
| `--application-dumps hpcg` | SpMV 1, SymGS 2 transformations, all `next-row pointers` | `s12_30_hpcg_dumps-20261115-062641.log` |
| `check t1 --sparse-indirect` on the default-on build | PASS, 65 results, 0 failures | `s12_30_t1_default_on-20261115-062909.log` |
| `--shape-host` | PASS: plain C passes 24 children; seeded hint faults | `s12_30_shape_host-20261115-062851.log` |
| `--compiler-proof` staging | PASS, six transformation diagnostics in both contraction modes | `s12_30_compiler_gate_hpcg-20261115-063046.log` |
| `check t0` | PASS, 56 tests | `s12_30_t0-20261115-063107.log` |
| `--ice-sweep` (torture and vect, O2 and O3, 8704 compiles) | 0 timeouts, 1 ICE: `vect-pr123221.c` at O3, in `vect_analyze_slp_reduc_chain` before this pass (S12-38) | `s12_30_indirect_ice_sweeps-20261115-063101.log` |

Not run here: T2 (lead; the sandbox cannot write its shared files), x86
identity (lead), any card job. The HPCG paired A/B is not staged: it
measures the default build, so it waits for the measured cutoff.

This is the first T1 run of the default-on end state: plain
`-O2 -march=knc` emits the bounded hints, its probe bodies equal explicit
switch-on, and the scalar baseline identity holds for the switch-off
build. The cutoff is still the provisional 16384.

Native proof staged, not run: `.work/_shared/S12-30/compiler-gate-hpcg`,
argument `12345`, `card_run --threads 1 --timeout 590`; add
`--correctness` to run the guard suites without the timing grid. It is
the compiler-gate program rebuilt with this compiler plus the new suites.
It has a new name because `compiler-gate` (previous compiler head) is in
the window-6 queue and that window had not run when this was staged;
delete the old binary once window 6 is read. New in it, for the donor,
switch-off, switch-on and switch-on contract-fast slots:

* `struct-spmv`, `struct-forward`, `struct-backward` kernels in the T1
  probe form, compiled from unhinted C.
* Guard fixtures: byte counts and the three pointer tables end at a
  protected page, or start right after one (so row `-1` of the backward
  sweep faults); each row's indices and values end at their own page;
  empty rows point at a protected page; row lengths 1/13/27/33 with
  uniform, longer-next, shorter-next and empty-next patterns; 1, 2, 7,
  16384 and 16385 rows so both version arms run; SpMV runs rows 5 to
  rows+5 of biased tables.
* Overlap case, 16384 rows: the byte counts live inside the stored vector.
  Row 3 is nonempty and its store clears the count of the next row in
  sweep order, which read 27 until then and whose index pointer is a
  protected page. The program never enters that row; a hint taken from
  the stale count faults. On the host a seeded next-row hint without the
  overlap test dies in exactly that child (status 11) and nothing else
  fails.

Also fixed in the driver: forked children inherited the parent's failure
count, so one failing kernel made every later child report failure.

Code size, `.text` of the six-kernel proof unit: donor 811, switch off
1926, switch on 4641 (both contraction modes). Static hint counts of the
three earlier kernels are unchanged (9 / 13 / 5).

Policy, unchanged and for the lead: SymGS is serial, so at 104^3 its two
nests see 1,124,864 rows and take the hinted arm; outlined SpMV sees one
worker interval (about 4,687 rows at 240 threads) and takes the unhinted
arm at 16384.

### Window 6 read and the locality policy (2026-11-15, after the 06:48 answer)

#### Window 6: every case and sample

Source: `.work/_shared/tmp/claude-s12-window6/s12-30-gate.out` (compiler
`a36fc224773`, one core, exit 0, 38,731,845 comparisons, 0 failures).
Slots: `donor` GCC 5.1.1, `off` switch off, `on` switch on (compiler
policy, cutoff 16384), `hand` hand-written hint forced on at every size.
`arm` is the arm the compiler policy takes. `vs off` is the range over the
five samples of off time per call divided by this slot's time per call.

Equal work per call, confirmed: within a case every slot is called with
the same matrix (`compiler_case` builds one `struct matrix` and passes it
to all four kernels), so the nonzeros per call are the same number in
every row of a case. Only `calls` differs, because each sample repeats the
call until 0.5 s have passed. All outputs were compared with the same
reference after every sample (the comparisons in the PASS line).

| Case | Form | n | rows | x bytes | nnz per call | arm | slot | calls per sample | s/call, samples 0-4 | vs off, min-max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cache-threshold | CSR | 13 | 32 | 32768 | 416 | scalar | donor | 73727-73728 | 6.917e-06 6.909e-06 6.907e-06 6.908e-06 6.909e-06 | 1.013-1.016 |
| cache-threshold | CSR | 13 | 32 | 32768 | 416 | scalar | off | 73727-73728 | 7.007e-06 7.006e-06 7.017e-06 7.006e-06 7.008e-06 | 1.000-1.000 |
| cache-threshold | CSR | 13 | 32 | 32768 | 416 | scalar | on | 69632-73728 | 7.179e-06 7.177e-06 7.194e-06 7.182e-06 7.179e-06 | 0.975-0.976 |
| cache-threshold | CSR | 13 | 32 | 32768 | 416 | scalar | hand | 36863-36864 | 1.367e-05 1.368e-05 1.37e-05 1.367e-05 1.367e-05 | 0.512-0.513 |
| cache-threshold | CSR | 27 | 32 | 32768 | 864 | scalar | donor | 28671-28672 | 1.801e-05 1.798e-05 1.799e-05 1.798e-05 1.8e-05 | 1.004-1.006 |
| cache-threshold | CSR | 27 | 32 | 32768 | 864 | scalar | off | 28671-28672 | 1.812e-05 1.808e-05 1.808e-05 1.808e-05 1.807e-05 | 1.000-1.000 |
| cache-threshold | CSR | 27 | 32 | 32768 | 864 | scalar | on | 28671-28672 | 1.824e-05 1.825e-05 1.828e-05 1.824e-05 1.826e-05 | 0.989-0.993 |
| cache-threshold | CSR | 27 | 32 | 32768 | 864 | scalar | hand | 17407-17408 | 2.927e-05 2.926e-05 2.934e-05 2.933e-05 2.925e-05 | 0.616-0.619 |
| cache-threshold | per-row | 13 | 32 | 32768 | 416 | scalar | donor | 73727-73728 | 7.068e-06 7.056e-06 7.066e-06 7.064e-06 7.062e-06 | 1.015-1.018 |
| cache-threshold | per-row | 13 | 32 | 32768 | 416 | scalar | off | 73727-73728 | 7.183e-06 7.183e-06 7.175e-06 7.175e-06 7.174e-06 | 1.000-1.000 |
| cache-threshold | per-row | 13 | 32 | 32768 | 416 | scalar | on | 69631-69632 | 7.405e-06 7.401e-06 7.402e-06 7.403e-06 7.398e-06 | 0.969-0.971 |
| cache-threshold | per-row | 13 | 32 | 32768 | 416 | scalar | hand | 49151-49152 | 1.079e-05 1.079e-05 1.081e-05 1.08e-05 1.078e-05 | 0.664-0.666 |
| cache-threshold | per-row | 27 | 32 | 32768 | 864 | scalar | donor | 28671-28672 | 1.869e-05 1.87e-05 1.87e-05 1.871e-05 1.87e-05 | 1.005-1.008 |
| cache-threshold | per-row | 27 | 32 | 32768 | 864 | scalar | off | 26623-26624 | 1.884e-05 1.881e-05 1.883e-05 1.882e-05 1.883e-05 | 1.000-1.000 |
| cache-threshold | per-row | 27 | 32 | 32768 | 864 | scalar | on | 26623-26624 | 1.907e-05 1.906e-05 1.903e-05 1.91e-05 1.903e-05 | 0.985-0.989 |
| cache-threshold | per-row | 27 | 32 | 32768 | 864 | scalar | hand | 22527-22528 | 2.362e-05 2.359e-05 2.361e-05 2.366e-05 2.362e-05 | 0.795-0.798 |
| cache-threshold | CSR | 13 | 4096 | 32768 | 53248 | scalar | donor | 351-352 | 0.001456 0.001456 0.001456 0.001456 0.001455 | 1.006-1.013 |
| cache-threshold | CSR | 13 | 4096 | 32768 | 53248 | scalar | off | 351-352 | 0.001466 0.001465 0.001466 0.001475 0.001468 | 1.000-1.000 |
| cache-threshold | CSR | 13 | 4096 | 32768 | 53248 | scalar | on | 351-352 | 0.00149 0.00149 0.00149 0.001501 0.00149 | 0.982-0.985 |
| cache-threshold | CSR | 13 | 4096 | 32768 | 53248 | scalar | hand | 255-256 | 0.002053 0.002047 0.002047 0.00205 0.002046 | 0.714-0.720 |
| cache-threshold | CSR | 27 | 4096 | 32768 | 110592 | scalar | donor | 175-176 | 0.002923 0.002924 0.002922 0.002932 0.002924 | 1.003-1.008 |
| cache-threshold | CSR | 27 | 4096 | 32768 | 110592 | scalar | off | 175-176 | 0.002933 0.002932 0.002932 0.002956 0.002934 | 1.000-1.000 |
| cache-threshold | CSR | 27 | 4096 | 32768 | 110592 | scalar | on | 175-176 | 0.002957 0.002958 0.002957 0.002964 0.002957 | 0.991-0.997 |
| cache-threshold | CSR | 27 | 4096 | 32768 | 110592 | scalar | hand | 127-128 | 0.004125 0.004123 0.004119 0.004118 0.004119 | 0.711-0.718 |
| cache-threshold | per-row | 13 | 4096 | 32768 | 53248 | scalar | donor | 119-120 | 0.004356 0.004359 0.004359 0.004385 0.004366 | 1.002-1.006 |
| cache-threshold | per-row | 13 | 4096 | 32768 | 53248 | scalar | off | 119-120 | 0.004375 0.004377 0.00437 0.00441 0.004375 | 1.000-1.000 |
| cache-threshold | per-row | 13 | 4096 | 32768 | 53248 | scalar | on | 119-120 | 0.004408 0.004403 0.004406 0.004401 0.004401 | 0.992-1.002 |
| cache-threshold | per-row | 13 | 4096 | 32768 | 53248 | scalar | hand | 111-112 | 0.004568 0.004579 0.004562 0.004563 0.00456 | 0.956-0.967 |
| cache-threshold | per-row | 27 | 4096 | 32768 | 110592 | scalar | donor | 71-72 | 0.007056 0.007051 0.007045 0.007086 0.007107 | 0.997-1.003 |
| cache-threshold | per-row | 27 | 4096 | 32768 | 110592 | scalar | off | 71-72 | 0.007064 0.007067 0.007066 0.007071 0.007083 | 1.000-1.000 |
| cache-threshold | per-row | 27 | 4096 | 32768 | 110592 | scalar | on | 71-72 | 0.007102 0.007127 0.007106 0.00711 0.007107 | 0.992-0.997 |
| cache-threshold | per-row | 27 | 4096 | 32768 | 110592 | scalar | hand | 79-80 | 0.006346 0.006345 0.006345 0.006341 0.006343 | 1.113-1.117 |
| cache-threshold | CSR | 13 | 8192 | 32768 | 106496 | scalar | donor | 175-176 | 0.002948 0.002951 0.00295 0.002957 0.002969 | 1.005-1.011 |
| cache-threshold | CSR | 13 | 8192 | 32768 | 106496 | scalar | off | 175-176 | 0.002973 0.002983 0.002971 0.002972 0.002995 | 1.000-1.000 |
| cache-threshold | CSR | 13 | 8192 | 32768 | 106496 | scalar | on | 175-176 | 0.003016 0.003019 0.003017 0.003019 0.00302 | 0.984-0.992 |
| cache-threshold | CSR | 13 | 8192 | 32768 | 106496 | scalar | hand | 127-128 | 0.004135 0.004134 0.004132 0.004134 0.004133 | 0.719-0.725 |
| cache-threshold | CSR | 27 | 8192 | 32768 | 221184 | scalar | donor | 87-88 | 0.005864 0.00588 0.005863 0.005873 0.00588 | 1.003-1.012 |
| cache-threshold | CSR | 27 | 8192 | 32768 | 221184 | scalar | off | 87-88 | 0.005889 0.005902 0.005886 0.005892 0.005948 | 1.000-1.000 |
| cache-threshold | CSR | 27 | 8192 | 32768 | 221184 | scalar | on | 87-88 | 0.005938 0.005936 0.005937 0.005929 0.00595 | 0.991-1.000 |
| cache-threshold | CSR | 27 | 8192 | 32768 | 221184 | scalar | hand | 63-64 | 0.008246 0.008238 0.008238 0.008241 0.008242 | 0.714-0.722 |
| cache-threshold | per-row | 13 | 8192 | 32768 | 106496 | scalar | donor | 55-56 | 0.009158 0.009188 0.009151 0.00915 0.009209 | 0.991-1.003 |
| cache-threshold | per-row | 13 | 8192 | 32768 | 106496 | scalar | off | 55-56 | 0.009181 0.009184 0.009176 0.009173 0.009127 | 1.000-1.000 |
| cache-threshold | per-row | 13 | 8192 | 32768 | 106496 | scalar | on | 55-56 | 0.009239 0.009249 0.009236 0.009242 0.009181 | 0.993-0.994 |
| cache-threshold | per-row | 13 | 8192 | 32768 | 106496 | scalar | hand | 55-56 | 0.009583 0.009576 0.009575 0.009576 0.009449 | 0.958-0.966 |
| cache-threshold | per-row | 27 | 8192 | 32768 | 221184 | scalar | donor | 34-36 | 0.01508 0.0151 0.01509 0.01526 0.01394 | 0.991-1.006 |
| cache-threshold | per-row | 27 | 8192 | 32768 | 221184 | scalar | off | 34-36 | 0.01511 0.01512 0.01511 0.01512 0.01402 | 1.000-1.000 |
| cache-threshold | per-row | 27 | 8192 | 32768 | 221184 | scalar | on | 33-36 | 0.01518 0.01519 0.01518 0.01518 0.01412 | 0.993-0.996 |
| cache-threshold | per-row | 27 | 8192 | 32768 | 221184 | scalar | hand | 38-40 | 0.01326 0.01327 0.01327 0.01327 0.01284 | 1.092-1.140 |
| cache-threshold | CSR | 13 | 14000 | 32768 | 182000 | scalar | donor | 103-104 | 0.004984 0.004984 0.00499 0.004986 0.004987 | 1.007-1.010 |
| cache-threshold | CSR | 13 | 14000 | 32768 | 182000 | scalar | off | 103-104 | 0.005028 0.005026 0.005039 0.005024 0.005022 | 1.000-1.000 |
| cache-threshold | CSR | 13 | 14000 | 32768 | 182000 | scalar | on | 103-104 | 0.005097 0.0051 0.0051 0.0051 0.005116 | 0.982-0.988 |
| cache-threshold | CSR | 13 | 14000 | 32768 | 182000 | scalar | hand | 72-75 | 0.007024 0.00702 0.007023 0.007023 0.007069 | 0.710-0.718 |
| cache-threshold | CSR | 27 | 14000 | 32768 | 378000 | scalar | donor | 51-52 | 0.009897 0.009875 0.009884 0.009874 0.009885 | 1.002-1.008 |
| cache-threshold | CSR | 27 | 14000 | 32768 | 378000 | scalar | off | 51-52 | 0.009922 0.009922 0.009962 0.00992 0.009917 | 1.000-1.000 |
| cache-threshold | CSR | 27 | 14000 | 32768 | 378000 | scalar | on | 51-52 | 0.009999 0.00999 0.009991 0.009987 0.009989 | 0.992-0.997 |
| cache-threshold | CSR | 27 | 14000 | 32768 | 378000 | scalar | hand | 36-37 | 0.01401 0.01402 0.01401 0.01401 0.01404 | 0.706-0.711 |
| cache-threshold | per-row | 13 | 14000 | 32768 | 182000 | scalar | donor | 31-34 | 0.01622 0.01611 0.01612 0.01553 0.01554 | 0.997-1.004 |
| cache-threshold | per-row | 13 | 14000 | 32768 | 182000 | scalar | off | 31-34 | 0.01618 0.01616 0.01615 0.0156 0.0156 | 1.000-1.000 |
| cache-threshold | per-row | 13 | 14000 | 32768 | 182000 | scalar | on | 31-32 | 0.01625 0.01626 0.01634 0.01619 0.01568 | 0.963-0.996 |
| cache-threshold | per-row | 13 | 14000 | 32768 | 182000 | scalar | hand | 30-32 | 0.01676 0.01675 0.01675 0.01674 0.01631 | 0.932-0.965 |
| cache-threshold | per-row | 27 | 14000 | 32768 | 378000 | scalar | donor | 20-22 | 0.02571 0.02549 0.02546 0.0245 0.02453 | 0.995-1.005 |
| cache-threshold | per-row | 27 | 14000 | 32768 | 378000 | scalar | off | 20-22 | 0.0256 0.02559 0.02558 0.02462 0.02459 | 1.000-1.000 |
| cache-threshold | per-row | 27 | 14000 | 32768 | 378000 | scalar | on | 20-22 | 0.02564 0.0256 0.02572 0.02471 0.0247 | 0.994-0.999 |
| cache-threshold | per-row | 27 | 14000 | 32768 | 378000 | scalar | hand | 22-24 | 0.02286 0.02288 0.02287 0.02319 0.0222 | 1.062-1.120 |
| cache-threshold | CSR | 13 | 16384 | 32768 | 212992 | hint | donor | 87-88 | 0.005879 0.005847 0.005847 0.005846 0.005839 | 1.006-1.008 |
| cache-threshold | CSR | 13 | 16384 | 32768 | 212992 | hint | off | 87-88 | 0.005929 0.00588 0.005886 0.005886 0.00588 | 1.000-1.000 |
| cache-threshold | CSR | 13 | 16384 | 32768 | 212992 | hint | on | 76-79 | 0.006657 0.006661 0.00666 0.006659 0.00666 | 0.883-0.891 |
| cache-threshold | CSR | 13 | 16384 | 32768 | 212992 | hint | hand | 60-64 | 0.008233 0.008232 0.008351 0.008232 0.008231 | 0.705-0.720 |
| cache-threshold | CSR | 27 | 16384 | 32768 | 442368 | hint | donor | 44-47 | 0.01162 0.0116 0.01159 0.01159 0.01159 | 1.003-1.009 |
| cache-threshold | CSR | 27 | 16384 | 32768 | 442368 | hint | off | 43-44 | 0.01172 0.01163 0.01163 0.01164 0.01164 | 1.000-1.000 |
| cache-threshold | CSR | 27 | 16384 | 32768 | 442368 | hint | on | 38-39 | 0.01337 0.01332 0.01334 0.01333 0.01333 | 0.872-0.877 |
| cache-threshold | CSR | 27 | 16384 | 32768 | 442368 | hint | hand | 31-32 | 0.0164 0.01641 0.01643 0.01643 0.0164 | 0.708-0.715 |
| cache-threshold | per-row | 13 | 16384 | 32768 | 212992 | hint | donor | 27-28 | 0.0186 0.0186 0.0186 0.01839 0.0184 | 1.003-1.012 |
| cache-threshold | per-row | 13 | 16384 | 32768 | 212992 | hint | off | 27-28 | 0.01883 0.01865 0.0187 0.01845 0.01846 | 1.000-1.000 |
| cache-threshold | per-row | 13 | 16384 | 32768 | 212992 | hint | on | 27-28 | 0.0191 0.01895 0.01876 0.01877 0.01876 | 0.983-0.996 |
| cache-threshold | per-row | 13 | 16384 | 32768 | 212992 | hint | hand | 26-27 | 0.01948 0.01947 0.01925 0.01934 0.01926 | 0.954-0.971 |
| cache-threshold | per-row | 27 | 16384 | 32768 | 442368 | hint | donor | 16-18 | 0.03082 0.03174 0.02914 0.02917 0.02916 | 0.973-1.009 |
| cache-threshold | per-row | 27 | 16384 | 32768 | 442368 | hint | off | 17-18 | 0.03109 0.0309 0.02925 0.02921 0.02923 | 1.000-1.000 |
| cache-threshold | per-row | 27 | 16384 | 32768 | 442368 | hint | on | 19-20 | 0.02674 0.02657 0.02522 0.02521 0.02518 | 1.159-1.163 |
| cache-threshold | per-row | 27 | 16384 | 32768 | 442368 | hint | hand | 19-20 | 0.02768 0.02764 0.02627 0.02632 0.02627 | 1.110-1.123 |
| cache-threshold | CSR | 13 | 32768 | 32768 | 425984 | hint | donor | 43-44 | 0.01167 0.01168 0.01169 0.01169 0.01169 | 1.006-1.010 |
| cache-threshold | CSR | 13 | 32768 | 32768 | 425984 | hint | off | 43-44 | 0.01179 0.01178 0.01176 0.01178 0.01177 | 1.000-1.000 |
| cache-threshold | CSR | 13 | 32768 | 32768 | 425984 | hint | on | 38-39 | 0.0134 0.01332 0.01332 0.01334 0.01331 | 0.880-0.884 |
| cache-threshold | CSR | 13 | 32768 | 32768 | 425984 | hint | hand | 31-32 | 0.01651 0.01647 0.01646 0.0165 0.01646 | 0.714-0.715 |
| cache-threshold | CSR | 27 | 32768 | 32768 | 884736 | hint | donor | 22-23 | 0.02312 0.02314 0.02313 0.02312 0.02314 | 1.004-1.005 |
| cache-threshold | CSR | 27 | 32768 | 32768 | 884736 | hint | off | 22-23 | 0.02324 0.02323 0.02321 0.0232 0.02324 | 1.000-1.000 |
| cache-threshold | CSR | 27 | 32768 | 32768 | 884736 | hint | on | 19 | 0.02679 0.0266 0.0266 0.02666 0.02658 | 0.867-0.874 |
| cache-threshold | CSR | 27 | 32768 | 32768 | 884736 | hint | hand | 16 | 0.03296 0.03274 0.03274 0.03272 0.03276 | 0.705-0.709 |
| cache-threshold | per-row | 13 | 32768 | 32768 | 425984 | hint | donor | 13-14 | 0.03881 0.0369 0.03693 0.03695 0.03693 | 1.002-1.003 |
| cache-threshold | per-row | 13 | 32768 | 32768 | 425984 | hint | off | 13-14 | 0.0389 0.03702 0.03702 0.03702 0.03704 | 1.000-1.000 |
| cache-threshold | per-row | 13 | 32768 | 32768 | 425984 | hint | on | 13-14 | 0.03966 0.03763 0.03768 0.03782 0.03765 | 0.979-0.984 |
| cache-threshold | per-row | 13 | 32768 | 32768 | 425984 | hint | hand | 13 | 0.04058 0.04118 0.03864 0.03866 0.03865 | 0.899-0.959 |
| cache-threshold | per-row | 27 | 32768 | 32768 | 884736 | hint | donor | 9 | 0.06181 0.05865 0.05866 0.0586 0.05861 | 1.001-1.076 |
| cache-threshold | per-row | 27 | 32768 | 32768 | 884736 | hint | off | 8-9 | 0.06651 0.0587 0.05882 0.05878 0.05879 | 1.000-1.000 |
| cache-threshold | per-row | 27 | 32768 | 32768 | 884736 | hint | on | 10 | 0.05177 0.05101 0.05099 0.05104 0.05102 | 1.151-1.285 |
| cache-threshold | per-row | 27 | 32768 | 32768 | 884736 | hint | hand | 10 | 0.05322 0.05309 0.05314 0.05334 0.05313 | 1.102-1.250 |
| CG-A-sized | CSR | 13 | 14000 | 112000 | 182000 | scalar | donor | 80-83 | 0.006328 0.006324 0.006329 0.006327 0.006323 | 1.004-1.007 |
| CG-A-sized | CSR | 13 | 14000 | 112000 | 182000 | scalar | off | 79-80 | 0.006375 0.006358 0.006354 0.006352 0.006353 | 1.000-1.000 |
| CG-A-sized | CSR | 13 | 14000 | 112000 | 182000 | scalar | on | 79-80 | 0.006504 0.006441 0.006442 0.006456 0.006452 | 0.980-0.987 |
| CG-A-sized | CSR | 13 | 14000 | 112000 | 182000 | scalar | hand | 71-72 | 0.007047 0.007034 0.007033 0.007045 0.007031 | 0.902-0.905 |
| memory-sized | CSR | 13 | 32768 | 16777216 | 425984 | hint | donor | 4 | 0.1396 0.1395 0.1395 0.1395 0.1395 | 1.001-1.009 |
| memory-sized | CSR | 13 | 32768 | 16777216 | 425984 | hint | off | 4 | 0.1408 0.1396 0.1396 0.1396 0.1396 | 1.000-1.000 |
| memory-sized | CSR | 13 | 32768 | 16777216 | 425984 | hint | on | 27-28 | 0.01871 0.01857 0.01859 0.01857 0.01857 | 7.511-7.527 |
| memory-sized | CSR | 13 | 32768 | 16777216 | 425984 | hint | hand | 25-26 | 0.02022 0.02022 0.02021 0.02023 0.02022 | 6.901-6.966 |
| CG-A-sized | CSR | 27 | 14000 | 112000 | 378000 | scalar | donor | 40-43 | 0.01268 0.01267 0.01267 0.01265 0.01268 | 1.000-1.007 |
| CG-A-sized | CSR | 27 | 14000 | 112000 | 378000 | scalar | off | 40-43 | 0.01276 0.01269 0.01268 0.01271 0.01269 | 1.000-1.000 |
| CG-A-sized | CSR | 27 | 14000 | 112000 | 378000 | scalar | on | 39-40 | 0.01286 0.01278 0.0128 0.01279 0.01279 | 0.991-0.993 |
| CG-A-sized | CSR | 27 | 14000 | 112000 | 378000 | scalar | hand | 36-37 | 0.01401 0.01401 0.014 0.01405 0.01401 | 0.905-0.911 |
| memory-sized | CSR | 27 | 32768 | 16777216 | 884736 | hint | donor | 2 | 0.2901 0.2869 0.2866 0.2847 0.2846 | 0.993-1.002 |
| memory-sized | CSR | 27 | 32768 | 16777216 | 884736 | hint | off | 2 | 0.288 0.2867 0.2871 0.2848 0.2846 | 1.000-1.000 |
| memory-sized | CSR | 27 | 32768 | 16777216 | 884736 | hint | on | 14 | 0.03799 0.03804 0.03817 0.03769 0.03772 | 7.522-7.580 |
| memory-sized | CSR | 27 | 32768 | 16777216 | 884736 | hint | hand | 13 | 0.04077 0.04078 0.04072 0.041 0.04059 | 6.945-7.063 |
| CG-A-sized | per-row | 13 | 14000 | 112000 | 182000 | scalar | donor | 29-30 | 0.01756 0.01747 0.01744 0.01744 0.01748 | 1.000-1.007 |
| CG-A-sized | per-row | 13 | 14000 | 112000 | 182000 | scalar | off | 29-30 | 0.01755 0.01751 0.01756 0.01748 0.0175 | 1.000-1.000 |
| CG-A-sized | per-row | 13 | 14000 | 112000 | 182000 | scalar | on | 29-30 | 0.01761 0.01762 0.01767 0.0176 0.01759 | 0.993-0.997 |
| CG-A-sized | per-row | 13 | 14000 | 112000 | 182000 | scalar | hand | 31-32 | 0.01617 0.01618 0.01617 0.01616 0.01623 | 1.078-1.086 |
| memory-sized | per-row | 13 | 32768 | 16777216 | 425984 | hint | donor | 4 | 0.1619 0.1622 0.162 0.1618 0.1631 | 0.998-1.001 |
| memory-sized | per-row | 13 | 32768 | 16777216 | 425984 | hint | off | 4 | 0.162 0.162 0.162 0.162 0.163 | 1.000-1.000 |
| memory-sized | per-row | 13 | 32768 | 16777216 | 425984 | hint | on | 12 | 0.0449 0.0449 0.04493 0.0449 0.04488 | 3.605-3.632 |
| memory-sized | per-row | 13 | 32768 | 16777216 | 425984 | hint | hand | 11 | 0.04553 0.04555 0.04554 0.04557 0.04556 | 3.554-3.578 |
| CG-A-sized | per-row | 27 | 14000 | 112000 | 378000 | scalar | donor | 13-15 | 0.03873 0.03495 0.035 0.03507 0.03539 | 0.993-1.005 |
| CG-A-sized | per-row | 27 | 14000 | 112000 | 378000 | scalar | off | 13-15 | 0.03887 0.03513 0.03504 0.03496 0.03514 | 1.000-1.000 |
| CG-A-sized | per-row | 27 | 14000 | 112000 | 378000 | scalar | on | 13-15 | 0.03901 0.03528 0.0352 0.03517 0.03521 | 0.994-0.998 |
| CG-A-sized | per-row | 27 | 14000 | 112000 | 378000 | scalar | hand | 21-24 | 0.02398 0.02366 0.02218 0.02216 0.02216 | 1.485-1.621 |
| memory-sized | per-row | 27 | 32768 | 16777216 | 884736 | hint | donor | 2 | 0.3197 0.3145 0.3143 0.3142 0.3142 | 0.984-1.014 |
| memory-sized | per-row | 27 | 32768 | 16777216 | 884736 | hint | off | 2 | 0.3146 0.3143 0.3144 0.3143 0.3185 | 1.000-1.000 |
| memory-sized | per-row | 27 | 32768 | 16777216 | 884736 | hint | on | 8 | 0.06706 0.067 0.06702 0.06721 0.06581 | 4.676-4.839 |
| memory-sized | per-row | 27 | 32768 | 16777216 | 884736 | hint | hand | 8 | 0.06824 0.06799 0.06827 0.06859 0.06676 | 4.582-4.771 |
| HPCG-104-cubed-stencil | per-row | 27 | 1124864 | 8998912 | 29791000 | hint | donor | 1 | 0.6281 0.627 0.626 0.627 0.6256 | 1.004-1.012 |
| HPCG-104-cubed-stencil | per-row | 27 | 1124864 | 8998912 | 29791000 | hint | off | 1 | 0.6331 0.6293 0.6293 0.6344 0.6293 | 1.000-1.000 |
| HPCG-104-cubed-stencil | per-row | 27 | 1124864 | 8998912 | 29791000 | hint | on | 1 | 0.8282 0.8282 0.8279 0.8293 0.8281 | 0.760-0.765 |
| HPCG-104-cubed-stencil | per-row | 27 | 1124864 | 8998912 | 29791000 | hint | hand | 1 | 0.9027 0.9029 0.9029 0.9027 0.9031 | 0.697-0.703 |
| lone-memory | lone | 262144 | 1 | 16777216 | 262144 | hint | donor | 6 | 0.08349 0.0835 0.08356 0.08358 0.08349 | 0.927-0.932 |
| lone-memory | lone | 262144 | 1 | 16777216 | 262144 | hint | off | 7 | 0.07779 0.07742 0.07743 0.07746 0.07737 | 1.000-1.000 |
| lone-memory | lone | 262144 | 1 | 16777216 | 262144 | hint | on | 47-48 | 0.01087 0.01087 0.01087 0.01086 0.01087 | 7.121-7.157 |
| lone-memory | lone | 262144 | 1 | 16777216 | 262144 | hint | hand | 47-48 | 0.01124 0.01124 0.01132 0.01131 0.01124 | 6.843-6.918 |

What the table says:

* Stencil (104^3, 27 points, 1,124,864 rows, per-row form): `on` 0.760-0.765,
  `hand` 0.697-0.703. The row count is far above any cutoff, so a row
  cutoff alone cannot protect it.
* Rows of one index array (CSR), x 32 KiB, 16384 and 32768 rows (hinted
  arm): 0.867-0.891. x 112 KB, 14000 rows, forced by hand: 0.902-0.911.
  x 16 MiB: 7.51-7.58.
* Rows with their own index pointer, forced by hand: 14000 rows over 112 KB
  1.078-1.086 (n=13) and 1.485-1.621 (n=27); x 32 KiB 0.90-0.97 (n=13) and
  1.06-1.25 (n=27) from 4096 rows up; x 16 MiB 3.6 (n=13) and 4.7-4.8
  (n=27). This form gains at sizes where the flat form loses. Inference,
  not measured: its hint first loads the next row's index line, which in
  these inputs is a separate allocation. The two forms therefore cannot
  share a cutoff; the policy hook now takes the form (below).
* Lone loop, 262144 iterations over 16 MiB: 7.12-7.16.
* Unhinted arm of the switch-on build (`arm` = scalar): 0.969-0.976 at
  32 rows n=13, 0.985-0.993 at 32 rows n=27, 0.980-0.992 for CSR n=13 at
  4096 to 14000 rows, 0.991-1.000 for CSR n=27, 0.992-1.002 for per-row
  rows (one sample 0.963). Cause and correction below.
* Separate from this ticket: the donor is 1.3-1.8% faster than switch-off
  at 32 rows, n=13, in both forms (1.013-1.018).

Why 7.5x here against 1.62x in window 4: the inputs differ, not the code.
Window 4 timed each memory-sized case twice, with uniformly random columns
(`packed=0`) and with columns in groups of eight neighbours (`packed=1`).
Its `packed=0` numbers were already 6.95-7.02 (CSR) and 3.63-5.18
(per-row); 1.61-1.63 is its `packed=1` per-row n=27 case, the best of the
grouped cases (the others: 1.34-1.52). Window 6 has no grouped input, so
all its memory-sized numbers are the random-column kind, and they agree
with window 4's (CSR 6.9-7.0 by hand there, 6.9-7.1 by hand here; the
compiler's own form reaches 7.5). The unhinted loop takes 0.140 s for
425,984 nonzeros, about 330 ns each. Inference from the inputs, not from
counters: with random columns over 16 MiB every nonzero misses, and
grouped columns miss once per eight nonzeros, which leaves less to hide.
Real matrices lie between the two, so 1.3-1.6 is the fairer expectation
for an application and 7 the upper end.

#### Policy: a locality sample in the version test

Ruling (a). The hinted arm of a nest now needs three things, tested once
per execution of the nest, before the row loop:

1. at least the cutoff number of rows (a lone loop: iterations);
2. for a byte-typed count array, counts disjoint from the stored vector
   (unchanged);
3. new: the first indices of the first three rows in iteration order are
   each more than one cache line of values (8 FP64 elements) from the one
   before. A lone loop uses its first three indices.

Both gaps must be large. On the 104^3 stencil consecutive rows start 0, 1
or 2 elements apart, except twice per plane (after the first grid line,
102 apart, and at the step to the next plane, 106 apart), and those two
are never neighbours; one large gap out of two therefore still means
stencil. With uniformly random columns over nx elements the chance that
a gap is within 8 is 17/nx.

Legality of the sample, as implemented by hand and in the pass:

* nothing is read unless test 1 holds, so the three rows exist, and they
  are rows the nest itself reads (no call or early exit in the nest);
* a row's first index is read only when all three rows are nonempty; the
  per-row pointer only for a positive count; an empty sampled row selects
  the unhinted arm;
* row bounds, counts and pointers are not changed by the nest (alias sets
  as before; test 2 for byte counts comes before the sample);
* the index and value arrays may change before their row runs: that only
  makes the choice stale, never a load invalid.

Nothing runs per element or per row; the stencil takes the unhinted arm.

#### Hand-written proof (host model)

`tools/s12_30_precision.c`, manual slot (`-DMANUAL_PROOF=1`): the policy
above written in C around the legal hinted kernels, for the flat, per-row
and lone forms and for the three struct nests (SpMV, forward sweep,
backward sweep; the backward sample reads rows `rows-1`, `rows-2`,
`rows-3`). The slot records which arm each call took.

Fixtures changed for the sample:

* Long fixtures now begin (in sweep order) with three nonempty rows whose
  first indices are 0, 33 and 66, so the hinted arm runs and the lookahead
  guards at the array end stay exercised; every fourth length starts them
  at 5, 6, 7 instead and takes the unhinted arm.
* New flat shape 3: the first four rows are empty and bounded at the end
  of `col`, which is a protected page. Per-row and struct fixtures keep
  empty sampled rows whose index pointer is a protected page.
* Lone loop: lengths 0 to 5 added (a three-index sample of a shorter loop
  crosses the guard), each with far and near first indices; the lone
  fixtures now run in a child per slot.
* Count-inside-the-stored-vector case: the first three rows in sweep order
  hold one zero-valued entry each, 4096 elements apart, so the sample
  alone would choose the hinted arm; only the disjointness test keeps the
  stale count unread.
* A sweep's vector has 67 elements beyond its rows, so first indices can
  be far apart in a seven-row fixture.

Host run, `--shape-host` (control flow only, no IMCI, no timing), log
`.work/_state/logs/s12_30_shape_host-20261115-075411.log`: PASS.

* Plain C and the manual slot pass all 42 struct children (seven slots),
  the flat, per-row and lone guard children, and every timing case built
  without the clock.
* Decisions of the manual slot, all as expected (32 cases): scalar for
  32-row nests, scalar for 14000 square rows (below the cutoff), hint for
  square 32768 to 262144 rows in both forms and both lengths, hint for
  32768 rows over a 32 KiB x (the known weakness of a row count), scalar
  for the 104^3 stencil in the per-row form
  and in the struct SpMV, forward and backward nests, hint for the random
  lone loop, scalar for the ascending lone loop.
* Three seeded defects are each caught, by a fault, in the seeded slot
  only: a next-row hint without the count/store disjointness test (as
  before); a sample taken below the row cutoff (flat, per-row, lone and
  all three struct children fault); a sample that reads the first index of
  rows not known nonempty (flat, per-row and the three struct children
  fault).

#### Unhinted arm against switch-off (ruling c): cause not settled, control staged

What it is not. The version test and the sample run once, before the row
loop; the unhinted nest is the untouched GIMPLE copy; it keeps all four
stream hints of its unrolled loop (`vprefetch1 2048`/`vprefetch0 1024` on
values, `vprefetch1 1024`/`vprefetch0 512` on indices); nothing is spilled
in either arm.

What differs in the generated code of the unhinted arm (flat form; the
per-row form is alike), from `compiler-knc.s` and `compiler-enabled.s`:

1. A zero stays on the x87 stack for the whole nest: each row starts with
   `fld %st(0)` where switch-off has `fldz`, and the function ends with
   `fstp %st(0)`. RTL invariant motion hoists the zero in both builds;
   `late_combine2` puts it back into its three uses in switch-off code
   (`original cost = 5 + 4 + 4 + 4 ... keeping replacement`) but fails in
   the two-nest function with `no viable insn position assignment`, once
   per nest. This is not specific to this pass: a plain function with two
   strict sparse nests compiled with the switch off shows the same six
   `fld %st(0)` and the same two failures (`.work/_shared/S12-30/scratch/
   two.c`, `one_nest` in the same file has none).
2. The short-row loop is one byte longer (22 against 21): the value
   pointer lives in `%r10` instead of `%rbx`, so `fmull` carries a REX
   prefix.
3. One more taken branch per short row: the row header is laid out after
   the long-row code, so a short row takes `jne`, `jg`, `jbe` where
   switch-off takes `jne`, `jbe`.
4. Per call: `subq`/`movq` saves instead of pushes, the cutoff compare,
   and now the sample (at most 7 loads and 6 branches).

Placement in the linked binaries (functions start on a 64-byte line;
offset of each short loop, its length, start modulo 64, and whether it
crosses a line):

| Binary | Function | Short plain loops |
| --- | --- | --- |
| window 6 | `knc_csr_raw` (off) | +288 len 21 mod 32; +352 len 21 mod 32 |
| window 6 | `enabled_csr_raw` (on) | +480 len 22 mod 32; +560 len 22 mod 48 crosses; +880 len 22 mod 48 crosses; +976 len 22 mod 16 (short rows of the unhinted arm) |
| new | `enabled_csr_raw` (on) | +560 len 22 mod 48 crosses; +656 len 22 mod 16 (short rows of the unhinted arm); +928 len 22 mod 32; +1024 len 22 mod 0 |
| new | `twin_csr_raw` (control) | +320 len 22 mod 0; +400 len 22 mod 16; +752 len 22 mod 48 crosses; +848 len 22 mod 16 |

The loops that cross a line are the remainder loops after an unrolled
loop, which rows of 13 or 27 entries never reach; the short-row loop of
the unhinted arm does not cross one in either binary. So placement does
not explain the loss either.

The loss in window 6 halves from n=13 to n=27 at 32 rows (2.4-3.1% and
0.7-1.5%), so it is a cost per row, about 5 ns (2.4% of 7.0 us per call
over 32 rows), not per nonzero. Items 1 and 3 are per row.
None of the four can be timed on the host, and the donor code, the
fastest slot at 32 rows, also keeps a zero copy (3 `fld %st`), so item 1
alone is unlikely.

Done here: the two arms now have even probability (they were 80/20 for
the hinted arm), so the unhinted copy is no longer optimised as the
unlikely path. That did not remove items 1 to 3.

Staged to settle it in the one card run: a control slot,
`knc-switch-off-two-nests`. It is switch-off code in which the plain nest
appears twice in one function, selected by a flag that is never set (the
copy that never runs negates its store, so the two cannot be merged). It
has the same three properties as the unhinted arm (5 `fld %st`, 22-byte
loop, row header after the long-row code) and none of the policy. It is
timed next to `off` and `on` in the four 32-row cases and the four
14000-row cases.

* If the control loses what `on` loses, the cost comes from two nests
  sharing a function, which any function with two FP reduction nests has
  today; the correction belongs in general code generation (late-combine
  on x87, or block layout) and needs its own ticket.
* If the control equals `off` and `on` still loses, the cost is in the
  policy path and stays in this ticket.

So ruling (c) is reported, not met: the target of 1% on every
policy=scalar case is unproven until that run.

#### GCC change (lane gcc2, `679766e8d25`, two commits on `c70cf1ed484`)

`git diff --check knc...HEAD` clean, LF, 8 files, 877 insertions.

* `gcc/tree-ssa-loop-prefetch.cc`: `indirect_sample` builds the sample
  before the nest as a chain of guarded blocks ending in a PHI (false on
  every skipped edge), and the nest is versioned on that PHI. Order of
  the tests: row count, store disjointness, sampled rows nonempty, then
  the index loads. Flat form: `bounds[s..s+3]`, then `indices[bounds[s+k]]`
  for k = 0..2 under `bounds[s+k] < bounds[s+k+1]`. Per-row form:
  `bounds[s], bounds[s±1], bounds[s±2]` (minus for a descending nest, s its
  first row), then pointer and first index of each under `count > 0`.
  Lone loop: `indices[start..start+2]`. The gap test is
  `(unsigned long long)(b - a + 8) > 16` on 64-bit differences, both
  pairs. The tolerance is the L1 line size divided by the value size.
* Same file: the store-disjointness test of the flat form now covers
  `bounds[high]` (ruling d). It has no effect today, because a byte-typed
  bound array cannot be the flat form.
* Same file: nest version arms even; minimum rows clamped to the three the
  sample reads.
* `gcc/target.def`, `gcc/doc/tm.texi`, `gcc/config/i386/i386-knc.{h,cc}`:
  the policy hook receives the form (0 flat rows, 1 per-row pointers,
  2 lone loop) and KNC keeps one cutoff per form, all still the
  provisional 16384. Reason: window 6 shows the forms break even at
  different sizes (above), and a prototype change costs a full rebuild,
  so it shares the rebuild the new parameter needs anyway.
* `gcc/config/i386/i386.opt`: `--param=knc-indirect-prefetch-min-trips=N`
  overrides the cutoff of all forms (0, the default, keeps the built-in
  values). It exists so that the gate can time the hinted arm below the
  default cutoff with the shipped pass; the locality sample still applies.

Sample in the flat T1 probe (`phase2-default.aprefetch`, `sparse_rows`):

```text
  <bb 13>: _64 = (long long unsigned int) rows * 8;
           if (_64 > 131071) goto <bb 15>; else goto <bb 14>;
  <bb 15>: _68 = *row;  _71 = *(row + 4);  _70 = *(row + 8);  _62 = *(row + 12);
           if (_68 < _71) goto <bb 16>; else goto <bb 14>;
  <bb 16>: if (_71 < _70) goto <bb 17>; else goto <bb 14>;
  <bb 17>: if (_70 < _62) goto <bb 18>; else goto <bb 14>;
  <bb 18>: _58 = *(col + _68 * 4);  _54 = *(col + _71 * 4);  _40 = *(col + _70 * 4);
           _22 = (unsigned long long) (_54 - _58) + 8 > 16;
           _75 = (unsigned long long) (_40 - _54) + 8 > 16;
           _76 = _22 & _75;
  <bb 14>: # _77 = PHI <_76(18), 0(13), 0(15), 0(16), 0(17)>
           if (_77 != 0) goto <bb 27>; [50.00%] else goto <bb 28>; [50.00%]
```

#### Results (compiler built by this session, `tools/gcc_build.py --if-stale`, PASS, 24.7 min)

| Check | Result | Log in `.work/_state/logs/` |
| --- | --- | --- |
| T1 before the GCC change | FAIL as intended, 13 FAIL lines: the hinted probes lack the sample (flat, slice, per-row in default, explicit and contract-fast modes; three struct nests), and the parameter is unknown | `s12_30_t1_locality_red-20261115-071321.log` |
| T1, `check t1 --sparse-indirect` | PASS, 73 results, 0 failures (new mode `min4`: parameter accepted, hints present, assembly differs from the default) | `s12_30_t1_locality-20261115-080944.log` |
| `--application-dumps hpcg` | SpMV 1 and SymGS 2 transformations, all `next-row pointers; locality sample of 3, more than 8 apart` | `s12_30_hpcg_dumps-20261115-075016.log` |
| `--shape-host` (host model, seven slots) | PASS: 42 struct children, 32 decisions as expected, three seeded defects fault in their slot only | `s12_30_shape_host-20261115-075411.log` |
| `--compiler-proof` staging | PASS: six transformation lines with the sample in the default, contract-fast and min4 slots; lint clean | `s12_30_compiler_gate_hpcg-20261115-074953.log` |
| `check t0` | PASS, 56 tests (36 regression, 8 doctor, 6 portability, 6 lint) | `s12_30_t0-20261115-075037.log` |
| `--ice-sweep` (torture and vect, O2 and O3, 8704 compiles, default-on compiler) | 0 timeouts, 1 ICE: `vect-pr123221.c` at O3, the known S12-38 one; 8277 compiled, 426 ordinary errors | `s12_30_indirect_ice_sweeps-20261115-075852.log` |

Not run: T2 and x86 identity (lead), any card job. The HPCG A/B is not
staged (ruling d: only after the card run below).

Code size, `.text` of the proof unit (six kernels): donor 811, switch off
1926, switch on 4938 (4641 before the sample), two-nest control 2886,
hand-written policy 4110.

#### Staged for one card run

`.work/_shared/S12-30/compiler-gate-hpcg`, argument `12345`,
`card_run --threads 1 --timeout 590` (single-core timing; the program
pins itself to the first granted CPU and has `alarm(570)`). Add
`--correctness` for everything except the clock. The old `compiler-gate`
binary (window 6) is superseded.

Slots: `donor-off`; `knc-switch-off`; `knc-switch-on` (default build);
`knc-switch-on-contract-fast`; `knc-switch-on-min4` (default build with
`--param=knc-indirect-prefetch-min-trips=4`); `knc-switch-off-two-nests`
(control above); `knc-handwritten-policy`.

Correctness part: the flat and per-row guard suites (now four shapes),
the lone-loop suite and the struct suites (guards and
count-in-stored-vector) for all seven slots, each in a child. With min4
the hinted arm of compiler-generated code also runs on the 4- and 7-row
nests and on the 4- to 33-iteration lone loops.

Timing part, five samples of at least 0.5 s per slot; each case first
checks every timed slot and the hand-written policy against the
reference and prints the policy's decision:

| Cases | Input | Timed slots |
| --- | --- | --- |
| `small` (4) | 32 rows, x 32 KiB, n 13 and 27, both forms | donor, off, on, two-nests |
| `square` 14000 (4) | x elements = rows, random columns, n 13 and 27, both forms | donor, off, on, min4, two-nests |
| `square` 32768, 65536, 131072, 262144 (16) | same | off, on (the policy hints here; the donor is left out to fit the window) |
| `small-x` (2) | 32768 rows over a 32 KiB x, n 13, both forms: reported control | donor, off, on |
| `stencil-104-cubed` per-row (1) | as window 6 | donor, off, on |
| `stencil-104-cubed` struct SpMV, forward, backward (3) | byte counts, pointer tables, diagonal pointers, values 26 and -1 | donor, off, on |
| `lone-memory`, `lone-ascending` (2) | 262144 iterations over 16 MiB, random and ascending columns | donor, off, on |

The struct stencil cases restart each sweep from the same vector before
every call, outside the clock, and compare every slot bit for bit with
the switch-off result; the values are inexact, so the long-double
reference is only reported (`reference_mismatches=`; 0 on the host).

Estimated card time 6.3 minutes (from window 6 times per nonzero: 41 s
small, 52 s square 14000, 140 s larger squares, 16 s small-x, 16 s and
57 s stencil, 16 s lone, about 40 s correctness). An alarm kill is an
infrastructure failure, not a result.

How to read it:

* Cutoff per form (ruling b): at 14000 rows `min4` against `off`; from
  32768 rows `on` against `off`. The cutoff of a form is the smallest
  size from which the ratio is never below 0.99 for both n. The values
  go into `knc_indirect_prefetch_default_min_trips[]` in `i386-knc.cc`
  (flat, per-row, lone; an `i386-knc.cc`-only build, about 3 minutes) and
  into `LEGAL_MIN_ROWS` of the harness, which today holds one value for
  all forms and would need one per form.
* Stencil: the four `stencil-104-cubed` cases must show `on` within 1%
  of `off` (window 6: 0.76).
* Unhinted arm: `small` and `square` 14000, `on` and `two-nests` against
  `off`, as above.
* Still expected to lose: `small-x`, flat form (window 6: 0.87-0.89). A
  row count cannot see the size of x.

#### For the lead

1. Ruling (c) is not met in this session; the cause is narrowed to code
   generation of two nests in one function, and the control that decides
   it is in the gate.
2. The two-nest behaviour of `late_combine2` on x87 (item 1 above) exists
   without this ticket and may deserve its own ticket whatever the
   control shows.
3. The donor is 1.3-1.8% faster than switch-off at 32 rows, n=13
   (window 6), in both forms: an existing gap under the owner rule, not
   caused by this ticket.
4. OpenMP SpMV at 104^3 and 240 threads still sees about 4,687 rows per
   worker, below 16384; a per-row cutoff measured lower than that would
   bring it into the policy, where the sample then keeps the stencil
   unhinted.
