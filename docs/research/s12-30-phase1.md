# S12-30: replacement phase-one red

2026-11-14. This replaces the product-precision gate rejected in the ticket.
It is a test-only red, not a Route A/B implementation or a performance result.
The same two test files are reused; no GCC source is changed.

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
vectorization. The baseline fold uses x87, not a zmm lane. A and A+B have no
fold yet: the intended green implementation will materialize FP64 products
and fold them in order through x87; its actual assembly must be checked then.

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
  Each call runs in a child; a signal or wrong output is a failure.

The kernel tables deliberately contain null A/B/A+B slots for donor-off,
knc-off and knc-contract-fast. Every missing slot is an explicit failure;
there is no scalar substitute, xfail or success-on-missing behavior. Timing
cannot run until all routes exist and correctness succeeds. This is the
requested failing test before implementation.

## Host evidence

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

## Single card entry point and green continuation

Staged binary: `.work/_shared/S12-30/precision-gate`, argument `12345`.
Lead launch: `tools/card_run --threads 1 --timeout 1150`, passing that binary
and argument using the wrapper's normal interface. The program's alarm is
1100 seconds, keeping the process budget below 20 minutes. At this red it
reports missing routes and exits 1 before timing; the lead may review the
host red without spending a card window. After implementing the routes,
the same entry point performs correctness and the entire paired timing batch
in one launch. It is explicitly single-core timing, pins to one granted CPU,
and prints the original affinity and chosen CPU. Other granted CPUs are not
claimed to be idle siblings. Record actual sibling activity and resource/
frequency profile with the lead-run output.

The timing path has row lengths 13 and 27; 32 rows with a 32 KiB RHS, and
8192 rows with a 16 MiB RHS; grouped-eight versus spread indices. Exact
integer data permits bit comparisons before and after timed samples. Each
case calibrates repetitions once against current GCC-KNC, then uses identical
counts for every route/compiler, with three samples reversing execution order.
It prints raw seconds and paired speedups against both baselines. These are
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
interpolation and prefetch-distance model as estimates. Green must choose
and document the actual fixed lookahead from that model and its loop's
instruction count; no distance or gain has been measured by this red.

Phase two remains conditional on at least a 5% gain over current GCC-KNC on
realistic inputs. T0-T2, ICE sweeps and whole-program A/B staging belong to
that later phase; x86 not run. No card job was started by the engineer.
