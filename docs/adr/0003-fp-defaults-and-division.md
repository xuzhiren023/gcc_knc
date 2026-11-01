# ADR-0003: Floating-point defaults and vector division

**Status:** Accepted for M1–M3; revisit at Gate C. **Date:** 2026-11-01. **Decider:** Claude; the owner may overrule.

## Decision

1. **Scalar FP stays on x87 through M3,** with the existing K1OM ABI (arguments in `zmm`
   lane 0, x87 bodies). That keeps object compatibility with the donor, so the donor can
   serve as a cross-check. Source-format scalar arithmetic in `zmm` is a separately
   evaluated option under E5-04 and does not change the default mid-qualification.
2. **Vectorized code is held to the same value semantics as the scalar source type:**
   FP32 and FP64, with no silent demotion and no implicit fast-math. `-O` levels do not
   change this. Note that x87 excess precision means scalar and vector results can
   legitimately differ. Tests compare against an exact or ULP-bounded reference, not
   against x87 output, except where the values are exactly representable.
3. **FMA contraction follows GCC's `-ffp-contract`.** Test fixtures use `off` by default
   and exercise `fast` explicitly.
4. **Vector division and square root are correctly rounded by default.** They are
   expanded inline or through an internal helper from `vrcp23ps`, `vrsqrt23ps`, FMA and
   fixups, and the implementation must handle zero, infinity, NaN and subnormals.
   Until a correct sequence is implemented and proven for a mode, division in that mode
   **does not vectorize** and stays on x87.
5. **Approximate forms are opt-in only,** behind `-mrecip`-style or `-ffast-math`-style
   options. Each has a documented error bound.

## Why

IMCI has no vector divide or square root, and FP64 has no hardware estimate at all, so
FP64 sequences must start from an FP32 estimate or a table. Taking the fast path by
default would quietly change numerics in programs that never asked for it, which is
exactly what the F/P evidence warns about. Falling back to scalar is safe and easy to
see in reports, and the cost is measurable, so the decision can be revisited with data.

## Verification

An FMA-based sequence needs more than random tests. The E4-03 story requires an argument
for correct rounding (Markstein-style or equivalent), hard-case vectors, and native
comparison against an MPFR reference. A helper is only proven under the rounding mode
and MXCSR state it documents.

## Open question

If correctly rounded FP64 division is too slow to help, the WRF kernels that depend on it
need either explicit opt-in or an application-side change. That is a Gate C input, and
the compiler does not decide it alone.
