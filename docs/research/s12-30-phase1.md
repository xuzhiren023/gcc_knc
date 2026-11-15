# S12-30: phase-one sparse routes

2026-11-14. The approved replacement red now has Route A, B and A+B
implementations. Target build/lint and the host model pass. The single native
correctness/timing run is staged for the lead; no native result or speedup is
claimed. The same two test files are reused; no GCC source is changed.

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
and actual scalar instruction counts are recorded above; no gain has yet
been measured.

Phase two remains conditional on at least a 5% gain over current GCC-KNC on
realistic inputs. T0-T2, ICE sweeps and whole-program A/B staging belong to
that later phase; x86 not run. No card job was started by the engineer.
