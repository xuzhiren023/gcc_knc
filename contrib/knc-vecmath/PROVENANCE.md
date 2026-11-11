# knc-vecmath: provenance

Copied 2026-11-06 by the GCC-KNC lead from `C:\Users\xuzhi\Documents\PhiWeather`, commit `bfc0977d`
(both source folders clean at that commit), on the owner's decision (ADR-0011). GCC-KNC does not
depend on the PhiWeather tree; this is a copy.

| Here | PhiWeather source |
|---|---|
| `native/translation/math_algorithms/` | `native/translation/math_algorithms/` (whole folder) |
| `native/translation/libknc_mvec/` | `native/translation/libknc_mvec/` (whole folder) |
| `native/upstream/arm-optimized-routines-v26.01/`, `-dp/` | `LICENSE`, `README.phiweather.md`, `upstream.lock.json`, and `-dp/math/math_config.h` (the header the sources include) |
| `native/upstream/arm-optimized-routines-v26.01/math/exp2f_data.c`, `math_config.h` | same path (added 2026-11-06 for the `powf` build; `math_config.h` is identical to the `-dp` copy) |
| `native/upstream/arm-optimized-routines-v26.01-dp/math/exp_data.c`, `log_data.c` | same path (added 2026-11-11 by S10-02 for `libknc_vmath`'s `exp`, `log` and `pow`; already listed in that folder's `upstream.lock.json` and byte-identical to it) |
| `native/upstream/arm-optimized-routines-v26.01/math/exp2.c`, `exp10.c`, `log.c`, `log2.c`, `log2_data.c`, `erf.c`, `aarch64/v_erf_data.c`, `aarch64/v_erfc_data.c`, `aarch64/advsimd/erf.c`, `aarch64/advsimd/erfc.c` | Arm optimized-routines v26.01, same paths, from the lead's checkout of commit `649ccc8411e7c4862965710f25c570d854a1483f` (added 2026-11-11 by S10-08: the files `libknc_vmath`'s v1b members follow, and the three tables they link; unchanged but for LF line endings, and not listed in `upstream.lock.json`) |
| `receipts/knc-g5-*.json` | `artifacts/native/knc-g5-*.json` (qualification receipts) |

The folder layout is kept so the sources' relative `#include` paths still resolve.

**Licenses:** Arm optimized-routines v26.01, MIT OR Apache-2.0 WITH LLVM-exception
(`native/upstream/*/LICENSE`, `log10_e/upstream/ARM_LICENSE`, `pow*/upstream/LICENSE`); musl v1.2.5,
MIT, with fdlibm notices (`*/upstream/COPYRIGHT`, `hyperbolic_e/NOTICE`).

**Only change:** in `.c`, `.h` and `.py` files, every `_ZGV<isa>N<lanes><v..>_<name>` symbol was
renamed to `__knc_vmath_<name>_<lanes>` (36 names, 66 files; ADR-0011 point 2). For example
`_ZGVeN16v_expf` became `__knc_vmath_expf_16`. Comments that mention `_ZGV` in general, the
`check_exports.py` scanners (which look for `_ZGV` symbols in PhiWeather's pipeline output), and all
`.md` and `.json` files are unchanged, so status notes and receipts still use the old names.
Git stores the files with LF line endings (`.gitattributes`), so file hashes recorded in the receipts
and `source-lock.json` files match the PhiWeather originals only for files that already used LF.

**Status:** the receipts qualify the functions built by PhiWeather's route (GCC 14 for KNL, then
translated to k1om), round-to-nearest with all lanes active only; errno, traps, other rounding modes
and masked lanes are not qualified, and there is no performance claim. None of this is evidence for
a GCC-KNC build. The by-value wrappers do not compile with GCC-KNC until the vector ABI exists
(ADR-0005 point 6, E7-01); the pointer-form cores (`knc_mvec_algorithm_*`) should. Start with
`native/translation/libknc_mvec/README.md`, `EXPORTS_STATUS.md` and
`native/translation/math_algorithms/README.md`.
