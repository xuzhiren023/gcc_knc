# Powf e16 algorithm and three export sources

This is the next real mathematical family after expf/exp/logf/log. The retained
36-symbol inventory has609 powf calls:593 e,7 d and9 b. The new e kernel and
two narrow wrappers supply three additional definitions; no target-qualified
symbol or G5 pass follows from their existence.

`powf_e16.c` adapts Arm optimized-routines v26.01 powf, commit
`649ccc8411e7c4862965710f25c570d854a1483f`. Exact upstream powf/data, source URLs,
hashes and the selected MIT license are in `upstream/`. Its log2 reduction uses
the upstream16-entry table and degree-five polynomial. Its exp2 reconstruction
uses the existing pinned32-entry table/cubic in
`native/upstream/arm-optimized-routines-v26.01/math/exp2f_data.c`.
It does not call scalar pow/exp/log and does not compose the existing expf/logf
approximations. The upstream scalar0.82ULP comment is not a measurement of this
adaptation.

The source uses genuine GCC16-SP vectors with16-DP intermediates, integer
special classification, exact subnormal normalization, integer exponent parity,
signed zero/infinity, NaN quieting and explicit exceptional arithmetic. Before
any FP arithmetic, inactive lanes are replaced with x=1/y=0. The pointer ABI
supports all software masks, exact x/output, y/output and merge/output aliases,
with full64-byte readable buffers and no partial-overlap promise. Invalid high
mask bits return1 without a write or FP effect. This is an experimental pointer
ABI, not a GNU masked-vector ABI.

The new production sources are `libknc_mvec/src/e_powf_export.c` and
`src/powf_wrappers.c`. The binary e adapter copies input bits into the pointer
kernel and returns its result. The b4/d8 wrappers fill all other wide lanes with
x=1/y=0, call e16 and return the low lanes. They do not interpret arbitrary
incoming upper lanes as arguments. Fast-math and negative-control production
builds reject. Keep `-DHAVE_FAST_FMA=0` and the pinned `math_config.h`; the
algorithm is the unscaled-log2/shift-scaled-exp2 upstream configuration.

Current host profile: Cygwin GCC14.4, baseline x86-64/SSE2, AVX/AVX2/FMA/AVX512
disabled, nearest-even, masked exceptions and FTZ/DAZ off. Both contraction-off
and contraction-fast are tested, but FMA is disabled in both. These are
algorithm/source-wiring checks, not the project's Linux-target compiler ABI or
KNC evidence. The first AVX2 attempt stopped with exit2816 before validation;
scoped assembly inspection found32-byte-aligned YMM spill forms at RSP-relative
offsets in a16-byte Windows stack profile. A strace-altered run completed only
as diagnostic evidence. That failure and its source snapshots remain in
`artifacts/test-state/host-powf-e16/5d4e2aa785044694967cf2801c94bd9c/`.

The new35k screening assay uses integer binary32 rounding and independent
100/160-digit Decimal power intervals; it exercises directed finite cases,
near-one/large-exponent inputs, raw subnormal bases, all special combinations,
36 masks and four alias modes. The large fresh assay uses installed MPFR4.2.2
directed endpoints at256 and384 bits, without candidate coefficients or source
equations. Both precisions' endpoint pairs must round to the same binary32.
The oracle records finite comparisons, rounded zeros, infinities and NaNs
separately; a large number of trivial range outcomes is not a claim about
difficult finite accuracy. Negative streams must be complete and fail
numerically. Mask/record/MXCSR controls fail independently.

Commands (packaged Python only):

```powershell
.tools/python/Scripts/python.exe -X utf8 native/translation/math_algorithms/powf_e16/check_accuracy.py --mpfr-million
.tools/python/Scripts/python.exe -X utf8 native/translation/math_algorithms/powf_e16/check_exports.py
```

G5 remains blocked on the qualified C translation pipeline and target vector
ABI/mask proof, target FP control and at least1e6 target lanes/specials with
ULP histograms. Existing earlier math source compilations exposed unqualified
vpgatherqq/vpmaskmovq/vpsraq; this work does not silently qualify those forms.
Errno, directed rounding, unmasked exceptions, FMA and target accuracy remain
open. The23 remaining declaration-only names need real implementations too.
No card job, benchmark, runtime change or BIND change occurs here.
