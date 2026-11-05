# ADR-0003: Floating-point defaults and vector division

**Status:** Accepted for M1–M3; revisit at Milestone M2. **Date:** 2026-11-01. **Decider:** Claude; the owner may overrule.

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
   *Amended 2026-11-05 from S5-03 (`docs/research/knc-div-sqrt.md`):*
   - The vector sequences are correctly rounded in the current MXCSR.RC and raise the IEEE flags
     as x87 does, except which NaN payload is returned when both operands are NaN; C leaves that
     open.
   - They are proven only for FZ = DAZ = 0. Under FTZ or DAZ, for example after `-ffast-math`
     links `crtfastmath`, subnormals flush.
   - Scalar x87 FP64 division and square root on the card are rounded twice (64-bit precision
     control, then the store), so they are not always correctly rounded. Tests must not treat x87
     FP64 output as the reference.
   - FP32 is implemented in Sprint 5. FP64 stays scalar until S5-03's two open proof steps close.
5. **Approximate forms are opt-in only,** behind `-mrecip`-style or `-ffast-math`-style
   options. Each has a documented error bound.

## Why

IMCI has no vector divide or square root, and FP64 has no hardware estimate at all, so
FP64 sequences must start from an FP32 estimate or a table. Taking the fast path by
default would quietly change numerics in programs that never asked for it. Falling back to scalar is safe and easy to
see in reports, and the cost is measurable, so the decision can be revisited with data.

## Verification

An FMA-based sequence needs more than random tests. The E4-03 story requires an argument
for correct rounding (Markstein-style or equivalent), hard-case vectors, and native
comparison against an MPFR reference. A helper is only proven under the rounding mode
and MXCSR state it documents.

## Open question

If correctly rounded FP64 division is too slow to help, loops that depend on it stay
scalar unless the user opts in to approximate forms. How often this matters across the
corpus is a Milestone M2 input.
