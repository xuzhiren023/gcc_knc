# DP8/SP16 sine and cosine source experiment

The experiment implements complete finite-domain range reduction through the
exact official musl v1.2.5 `__rem_pio2` and `__rem_pio2_large` bodies. The latter
is the full 24-bit-chunk Payne–Hanek reduction, including cancellation-driven
recomputation. Internal `floor` and `scalbn` are the pinned musl implementations,
with private symbol names; no scalar sine/cosine function is called. Exact
upstream bytes, URLs, lengths and source identity hashes live in `upstream/`.
The Sun permission notice is preserved in each original and adaptation, and
musl's complete copyright/license record is retained.

The Sun sine/cosine polynomials run as GCC8-DP vectors with both reduced parts;
integer quadrant selection follows. SP16 processes two DP8 groups and rounds
once to SP. Small values are selected before polynomial arithmetic, preserving
sin(±0)=±0 and cos(±0)=1. Inactive/nonfinite lanes become zero before reduction
or polynomial operations. Active NaNs/infinities use a vector x−x special path.

Private APIs use full readable64-byte input/merge/output buffers and software
masks. Exact input/output and merge/output aliases are supported; partial
overlap is unspecified. Invalid high mask bits return1 without reading inputs,
writing output or FP effects. Only nearest-even, masked exceptions and FTZ/DAZ
off are admitted. Full errno, inexact/underflow behavior, directed rounding,
unmasked exceptions and NaN payload propagation are unqualified.

Before the first host execution, the bounded experiment is declared as:

- Vary only new sin/cos mathematical family and strict contraction-off/fast
  builds; both use Cygwin GCC14.4 baselineSSE2 without AVX/FMA.
- Expected signature: ≤1ULP finite error against independent MPFR down/up
  endpoints; exact inactive bits and zero identities; required invalid status
  for active sNaN/infinity; no divide-by-zero or overflow.
- Metrics: ULP distribution/worst input, small/medium/large reduction counts,
  signed zeros, raw exponent/subnormal coverage, masks, aliases, FP/MXCSR state.
- Falsifier: any over1ULP result, wrong quiet-NaN classification, wrong zero
  sign, inactive poison effect, packet mismatch or runtime-profile mismatch.
- Bounded effort: one32K-per-format/function screen and focused corrections;
  only after it passes, optionally one fresh1M-per-format/function corpus.
  Stop numerical promotion on a failing screen; retain every failed receipt.

This is actual source work, not a G5 result. Target compilation/translation,
qualified arithmetic/width rules, target ABI and generic FP runtime, actual
card accuracy and performance remain open. No target compiler or card is used.
