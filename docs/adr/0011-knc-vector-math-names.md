# ADR-0011: Names for KNC vector math functions, and the copied WRF-project sources

**Status:** Accepted 2026-11-06. The owner decided both points ("Reuse the code by duplicate it in
this project repo, so we dont introduce dependencies while dont need to rediscover it again"; "Not to
reuse avx512 scheme, name it properly as plans said"); the lead set the details.
**Input:** `docs/research/wrf-input-2026-11-06.md`; backlog E7-01, E7-02; ADR-0005 point 6.

## Context

The PhiWeather WRF work wrote and qualified 16-lane `expf`, `logf`, `powf` and further float and
double vector math (0.50-0.78 ULP on its translation route, round-to-nearest, all lanes active).
They were exported under x86 vector-function names (`_ZGVeN16v_expf`). The `_ZGV` ISA letters b,
c, d and e mean SSE, AVX, AVX2 and AVX-512 calling conventions. KNC is not AVX-512 (ADR-0002), so a
`_ZGVe` symbol would claim an ABI it does not follow, and an x86 toolchain or `libmvec`-aware
linker could bind it wrongly. GCC-KNC must not depend on the PhiWeather tree.

## Decision

1. **Copy, not depend.** The sources are copied into `contrib/knc-vecmath/` at PhiWeather commit
   `bfc0977d` (2026-11-06), with their upstream licenses (Arm optimized-routines: MIT OR Apache-2.0
   WITH LLVM-exception; musl: MIT; fdlibm notices) and the qualification receipts.
   `contrib/knc-vecmath/PROVENANCE.md` records what was copied and changed. Nothing in GCC-KNC
   reads the PhiWeather folder.
2. **Names.** A KNC vector math entry point is `__knc_vmath_<libm name>_<lanes>`, for example
   `__knc_vmath_expf_16`, `__knc_vmath_pow_8`, `__knc_vmath_atan2f_16`. The double underscore marks
   it as implementation namespace, like libgcc's helpers. **No `_ZGV` name is ever defined or
   referenced by GCC-KNC for KNC code.** Masked variants add `_m` (`__knc_vmath_expf_16_m`); other
   accuracy variants get a suffix chosen in E7-02. The copied narrow 2-, 4- and 8-lane entry points
   (from the translation route's SSE and AVX2 widths) keep the same scheme and are not targets for
   GCC-KNC.
3. **Calling convention and compiler binding are E7-01's ADR.** Vector arguments and results are
   still an error in GCC-KNC (ADR-0005 point 6), so the copied by-value wrappers do not compile yet;
   the algorithms' pointer-form cores (`knc_mvec_algorithm_*`) should. E7-01 decides the register
   convention, and whether the vectorizer calls these names through a `-mveclibabi`-style hook (as
   i386 does for SVML) or through simd clones with a KNC-specific mangling letter. Either way the
   exported names stay as in point 2.
4. **Qualification restarts here.** The receipts qualify the functions as built by the PhiWeather
   route (GCC 14 for KNL, then translated to k1om). They are a starting point and an accuracy target,
   not evidence for GCC-KNC builds: E7-02 requalifies each function compiled by GCC-KNC, on the card.

## Consequences

- E7 starts from working, documented algorithms instead of rediscovering range reduction and tables.
- The copy will not follow later PhiWeather fixes; a refresh is a deliberate copy with a new commit
  recorded in `PROVENANCE.md`.
- The copied tooling (`check_exports.py`, `KncMvecScaffold.py` references) assumes PhiWeather's
  pipeline and does not run here.
