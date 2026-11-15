# S12-30: phase-one sparse routes

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
