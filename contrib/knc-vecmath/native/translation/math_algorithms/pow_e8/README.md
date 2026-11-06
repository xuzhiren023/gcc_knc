# Double-precision pow e8 source

This is the next family after the source-defined powf extension. Its retained
calls are291 e,33 d and4 b (328 total). The new e8 kernel and b2/d4 wrappers add
three real definitions, bringing the cumulative source count to16/36 if the
new sources are included. Target-qualified count remains zero.

`pow_e8.c` adapts official Arm optimized-routines v26.01 pow.c and
pow_log_data.c at commit`649ccc8411e7c4862965710f25c570d854a1483f`; exact source,
hashes, URLs and the selected MIT license are in `upstream/`. The reused exp
table/polynomial is the unchanged pinned
`native/upstream/arm-optimized-routines-v26.01-dp/math/exp_data.c`.

The8-DP GCC-vector arithmetic preserves the non-FMA scalar algorithm's
128-entry compensated log table, exact high/low residual split, compensated
log/product, exp tail, signed subnormal rounding correction and explicit
underflow effect. It never delegates to scalar pow/log/exp or composes the
existing approximate exp/log kernels. The upstream0.54ULP comment does not
qualify this adaptation. The source rejects unsupported table/scaling/FMA/
round-to-int configurations and fast-math.

Integer-only classification handles negative-base integer parity, NaNs, zeros,
infinities, tiny/huge exponents and sign. Exceptional lanes are neutralized
before vector arithmetic. The private pointer interface provides all8 software
mask bits, unchanged invalid-high-mask rejection, arbitrary inactive data,
exact x/output, y/output and merge/output aliases with full64-byte readable
buffers. Partial overlap is outside its contract. This does not implement a
GNU masked-vector function ABI. Binary e/b/d source adapters fill inactive
wide arguments with x=1/y=0 and remain target-unqualified.

The new assay uses the same MPFR directed-endpoint method and strict baseline
host profile as powf: Cygwin GCC14.4, x86-64/SSE2, AVX/AVX2/FMA/AVX512 off,
nearest-even, masked exceptions, FTZ/DAZ off, separate contraction-off/fast
builds. Both are non-FMA builds. MPFR4.2.2 evaluates independent pow down/up at
256 and384 bits, requiring agreement of every endpoint's binary64 rounding.
Numerical negatives use complete streams and must fail numerically, separately
from packet/control-state checks. The harness records special/finite/range
coverage honestly; the sample is not exhaustive binary64 conformance.

```powershell
.tools/python/Scripts/python.exe -X utf8 native/translation/math_algorithms/pow_e8/check_accuracy.py --mpfr-million
.tools/python/Scripts/python.exe -X utf8 native/translation/math_algorithms/pow_e8/check_exports.py
```

No KNC, FMA, target vector ABI/mask, errno, directed rounding, unmasked
exceptions or complete inexact/underflow conformance is established. The source
still needs the qualified translation pipeline and actual target1e6-input
accuracy/mask/special runs. No card work or BIND change occurs here.
