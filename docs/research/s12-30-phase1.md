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
