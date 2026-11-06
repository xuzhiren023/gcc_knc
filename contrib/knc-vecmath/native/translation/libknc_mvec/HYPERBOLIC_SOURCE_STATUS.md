# Six hyperbolic source definitions

The final six observed source names now have genuine vector implementations:
`_ZGVeN16v_sinhf`, `_ZGVeN8v_sinh`, `_ZGVeN16v_coshf`, `_ZGVeN8v_cosh`,
`_ZGVeN16v_tanhf` and `_ZGVeN8v_tanh`. They cover 93 of the unchanged 2,879
census calls. With the prior 30 definitions, source coverage is 36/36; target
qualification remains 0/36 and G5 remains open. The additive binding is
`hyperbolic-exports-v1.json`; earlier manifests remain unchanged historical
checkpoints.

`src/e_hyperbolic_export.c` includes the assayed new pointer implementation
unchanged except its two linker names. Six unmasked e-width adapters pass the
full software active mask and preserve input/result encodings using integer
memcpy. They are source integration only. Their library pointer entries still
support arbitrary inactive data and exact input/output or merge/output aliases.

Official musl v1.2.5 sources, Sun notices and a source lock are retained in
`../math_algorithms/hyperbolic_e/upstream/`. The algorithm uses the official
expm1 rational coefficients and split-ln2 reduction with compensated GCC vector
arithmetic, cancellation-safe identities, finite overflow classification,
tanh saturation and explicit special/exception handling. No scalar hyperbolic,
exp or expm1 function supplies a lane value. The strict profile is nearest-even,
masked exceptions and FTZ/DAZ off. Errno, directed rounding and KNC remain open.

The first 32K screen exposed an exponent-1025 scale construction above the true
double overflow boundary. That stopped attempt remains preserved; a classifier
at |x|>710.5 prevents the invalid construction while leaving the true overflow
boundary inside the computed path. The repaired screen and fresh million test
are separate records, with no relaxed ULP or special-value condition.

Fresh MPFR 4.2.2 directed 256/384-bit bounds checked 1,048,576 new unique finite
inputs per function/precision, plus boundaries, subnormals, signed zeros,
infinities, signaling/quiet NaNs, inactive poison, aliases and wrong-output
controls. Both contraction-off/fast source builds passed:

| Function | Worst ULP upper bound |
| --- | ---: |
| sinhf | 0.499998875 |
| sinh | 0.530940535 |
| coshf | 0.499997815 |
| cosh | 0.533171500 |
| tanhf | 0.499998883 |
| tanh | 0.499998984 |

The retained accuracy record is
`artifacts/test-state/host-hyperbolic-e/a9c8afc6431b42e18fc30d04c164637d/accuracy.json`.
It is host algorithm evidence, not an exhaustive correct-rounding claim.

Compact six-export wiring also passed off/fast builds: 384 public calls /4,608
lanes and 384 private mask calls /2,304 inactive poison lanes each, with zero
bit/standard-flag/full-MXCSR differences. Exactly six expected symbols were
defined; scalar math imports were absent. Missing-export linking and forbidden
fast-math/negative-control builds rejected. Its record is
`artifacts/test-state/host-hyperbolic-exports/7c053dee887f45d3a4696fde87be05fd/wiring.json`.

Full-library source integration is a separate new concern. These six records
alone do not prove that every prior object coexists in one linked library, a
target ABI, mask exemption, translated execution, runtime integration or G5.
