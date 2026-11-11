# ADR-0014: The KNC vector argument ABI, and how loops call vector math

**Status:** Accepted 2026-11-11 by the lead under the owner's blanket approval for Sprint 10
("tonight ... s10 work for almost half; you have my blanket approval for recommended action").
**Input:** ADR-0005 point 6 (vector arguments are an error today), ADR-0011 (names
`__knc_vmath_<name>_<lanes>`, never `_ZGV`), backlog E6-07, E7-01, E7-02; S2-02 (scalar float and
double arguments travel in `zmm` lane 0).

## Context

Sprint 10's goal is vector math v0 and a documented vector function ABI. The copied vector math
(`contrib/knc-vecmath`, ADR-0011) has by-value entry points that GCC-KNC cannot compile, because a
512-bit vector argument or result is an error under `-march=knc`. Loops that call `expf`, `logf` or
`pow` therefore stay scalar x87. The intrinsics work (E6-05) needs the same by-value convention for
any intrinsic that is not inlined.

## Decision

1. **512-bit vectors pass in registers, like the x86-64 psABI's `__m512` rule, on KNC's `zmm`.**
   - Arguments of 64-byte vector type (`__m512`, `__m512d`, `__m512i`, GCC `vector_size (64)`) go in
     `zmm0`-`zmm7` in order, sharing that sequence with the scalar float and double arguments that
     already travel in `zmm` lane 0 (S2-02). Further vector arguments go on the stack, 64-byte
     aligned. A 64-byte vector result returns in `zmm0`.
   - All `zmm` and `k` registers stay caller-saved, as today.
   - Masks (`__mmask16`) are 16-bit integers under the ordinary integer rules.
   - Vector arguments to a variadic function go in memory; `va_arg` of a vector type keeps its
     current error (ADR-0005 point 6) until a ticket needs it.
   - Before implementing, check this against Intel's K1OM psABI supplement if a copy is obtainable,
     and record agreement or differences in the ticket (facts only, ADR-0013).
2. **Loops reach vector math through an i386-style vector library hook, `-mveclibabi=knc`.**
   - The vectorizer replaces a vectorizable call of `expf`, `logf`, `powf`, `exp`, `log`, `pow` (v0
     set) by a call of `__knc_vmath_expf_16` and kin, the way i386 does for SVML. No simd clones and
     no `_ZGV` names (ADR-0011).
   - `-march=knc` turns the hook on by default. It only fires where GCC may vectorize the call, which
     needs `-fno-math-errno`: the default for Fortran, an explicit choice for C and C++. `-mphinix`
     adds `-fno-math-errno` (results stay IEEE; only `errno` is not set); `docs/gcc-knc-flags.md`
     says so.
3. **The library is ours and links automatically.** `libknc_vmath.a` (and `.so`) installs in the
   prefix; the KNC link spec names the static archive after `-lm`, so only programs that reference it
   pull members in. Entry points are the copied algorithms' pointer-form cores behind by-value
   wrappers that use point 1's convention.
4. **Accuracy and IEEE behaviour are the default.** v0 functions must be within the receipts'
   targets (about 1 ulp or better, round to nearest, all lanes) and handle NaN, infinities,
   subnormals, overflow and underflow as the scalar libm does, checked on the card against a host
   high-precision reference. Relaxed variants get their own suffix (ADR-0011) and are never the
   default. Masked variants (`_m`) take the mask as their last, integer argument.

## Consequences

- ADR-0005 point 6 is amended: 64-byte vector arguments and results are legal under `-march=knc`
  (variadic vectors excepted).
- Sprint 10 runs as: the ABI (S10-01), the library and its requalification (S10-02, can start in
  parallel on the pointer-form cores), the vectorizer binding and link spec (S10-03, after S10-01),
  the speed measurement (S10-04), then the batch check (S10-05).
