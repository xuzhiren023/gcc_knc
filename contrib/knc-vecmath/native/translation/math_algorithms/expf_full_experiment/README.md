# Full-input expf host experiment

This fresh experiment extends the earlier finite [-80,80] algorithm without
changing its sources, lock or successful report. It admits all binary32 input
encodings under the environment below. Admission of every encoding is not an
exhaustive accuracy proof. There is no `_ZGV` export, translated pipeline,
card execution, BIND change or G5 claim.

The arithmetic is adapted from official Arm optimized-routines v26.01, resolved
commit `649ccc8411e7c4862965710f25c570d854a1483f`, selecting MIT. The original
N32 table, scaled cubic coefficients, range reduction and expf cutoffs remain
exact. The separately pinned `math_errf.c` supplement supplies the documented
overflow/underflow factors. Their runtime multiplication is preserved with a
volatile input, rather than folding to a constant. Integer classification
neutralizes huge/special lanes before the double-vector core. Exceptional
paths contain arithmetic and bit selection; none delegates to scalar expf.

The current obligations are:

| Input | Required output | Standard exception flags |
|---|---|---|
| either zero | exactly +1 | none |
| finite nonzero with finite normal result | within 4 ULP | inexact |
| finite with subnormal/rounded-zero result | within 4 ULP, positive zero sign | underflow and inexact |
| finite overflow | exactly +Inf | overflow and inexact |
| +Inf | exactly +Inf | none |
| -Inf | exactly +0 | none |
| quiet NaN | identical sign/payload, quiet | none |
| signaling NaN | identical sign/payload with quiet bit set | invalid |

The finite-nonzero inexact obligation follows because exp of a nonzero
algebraic number is transcendental. The underflow policy uses tininess after
rounding; boundary samples test it on this host. NaN payload preservation is
an explicit experimental x86 policy, to be measured rather than assumed for
KNC. Divide-by-zero is never allowed. Vector flags must exactly equal the
union of lane obligations. The x86 denormal-operand status bit is recorded
separately and is permitted only when a lane has a nonzero subnormal input.

Only nearest-even, all exceptions masked and MXCSR FTZ=DAZ=0 are admitted by
the recorder. Actual upward-rounding, FTZ and DAZ controls must reject before
publishing an output file. Other rounding modes, enabled traps, errno, NaN
policy on the target VPU, asynchronous state, and a target vector ABI remain
unqualified. These are deliberate limits, not implicit success.

`HostExpfFullReference.py` reads no implementation tables, thresholds or
coefficients. Active finite inputs use the preserved independent exact
integer binary32 rounding with Decimal.exp intervals at 100 and 160 digits.
Both interval endpoint roundings must agree and the higher-precision interval
must nest. Huge inputs are classified using e>2, so exp(x)>2^256 for x>256
and exp(x)<2^-256 for x<-256. These bounds prove overflow or rounding to zero
without overflowing Decimal's exponent range. Special results and exception
obligations are independently classified by bits.

The record layout is six little-endian u32 words per four-lane vector: four
output encodings, `fetestexcept(FE_ALL_EXCEPT)`, and the entire MXCSR. The
recorder clears both standard flags and the denormal-operand bit before each
call. Input and output byte counts fail closed. Isolated special/threshold
vectors prevent unrelated flags from concealing a missing exceptional effect.

The corpus keeps one million seeded uniform raw-bit draws, directed dense
normal/subnormal/overflow/zero threshold neighborhoods, table/reduction edges,
payload/sign/quieting cases, and isolated and mixed vectors. The seeded random
generator used here is recorded explicitly; this is not the kit's eventual
LCG Fortran/conformance program. Neither a million sampled inputs nor the
directed subsets exhaust all binary32 encodings.

Both GCC 14.4 Cygwin-host native AVX2 builds use `-fno-fast-math`, nearest-rounding
and signaling/exception-aware options, with separate `-ffp-contract=off` and
`fast`. Actual hardware capabilities, host/compiler/tool/DLL identities,
assembly, imports, warnings, raw commands, inputs, results, reference words and
source snapshots are retained per fresh attempt. This compiler is separate
from the project's GCC 14.3 Linux-target assembly generator.

```powershell
.tools\python\Scripts\python.exe -m unittest discover -s tests -p test_host_expf_full.py
.tools\python\Scripts\python.exe scripts/Check-HostExpfFull.py --random-count 1000000
```

The result is a private host experiment. Failed attempts are retained in
`artifacts/test-state/host-expf-full/`; no public compiler gate is created.

The first actual result is
`artifacts/test-state/host-expf-full/f2a1c047df2c4990a1ac120458a88291/experiment.json`,
SHA256 `0f092cd34c46391f7508cf9c42b797ea90ac559b34837ac0a9f786433a0288f1`.
It checked 1,220,356 lanes (1,219,580 unique inputs). Both contraction variants
have 957,985 exact finite-result matches and 123 one-step differences, with
maximum conservative absolute error 0.501584174251554 ULP. The other 262,248
lanes require exact nonfinite/special comparison and have no mismatches.
Each variant checked 305,089 vector exception records with zero mismatches.
Kernel assemblies contain 0/5 FMA instructions for off/fast. All compilation
stderr files are empty; raw undefined-symbol listings are retained and have
no scalar expf/logf import or `_ZGV` export.

The reference corpus includes 73,127 subnormal results, 253,260 finite rounded
zeros, 254,207 finite overflow results, 3,974 quiet NaNs, 4,064 signaling NaNs,
and 3,850 subnormal inputs. Each actual executable rejected empty, truncated,
extra-byte, upward-rounding, FTZ and DAZ controls without creating output.
Seven focused pure Python oracle/assay tests passed before compilation.
Source/tool identities show no drift during the attempt. Both numerical
variants use the same independent exact-rounding reference, not each other.

The seed is `0x46554c4c45585046`, using Python MT19937 as stated above. These
measurements expand sampled coverage across the entire admitted input space;
they do not prove all encodings, a directed-rounding contract, errno behavior,
the target mask/ABI state or G5. The earlier four bounded reports and their
source snapshots remain immutable.

The precise new component files for a checkpoint are:

- `native/translation/math_algorithms/expf_full_experiment/README.md`
- `native/translation/math_algorithms/expf_full_experiment/expf_full.c`
- `native/translation/math_algorithms/expf_full_experiment/expf_full.h`
- `native/translation/math_algorithms/expf_full_experiment/host_driver.c`
- `scripts/HostExpfFullReference.py`
- `scripts/Check-HostExpfFull.py`
- `tests/test_host_expf_full.py`

The ignored vendor supplement requires exactly these five paths if added to
Git: `native/upstream/arm-optimized-routines-v26.01-expf-special/` followed by
`.gitattributes`, `README.phiweather.md`, `LICENSE`, `math_errf.c`, and
`upstream.lock.json`. Do not add the entire ignored upstream/toolchain tree.
The helper file SHA256 is
`2c5d68148296649b10743b2fec80bf4234fbb14e8d00a05a2dc0ba25930fedb8`.

The current compiler-policy revision is the strict-errno rerun at
`artifacts/test-state/host-expf-full-strict/c74a714c45474547a2648b5770f61529/experiment.json`,
SHA256 `94950124777249787add0b45118dd7e287332a80dc386f4b344e121c69044542`.
It replaces the earlier unnecessary `-fno-math-errno` option with
`-fmath-errno`, retaining all other options and the exact algorithm/oracle.
The earlier successful result and its used controller remain immutable
historical evidence; the change is in the new
`scripts/Check-HostExpfFullStrict.py`. Two focused controls verify the old
controller identity and the exact one-option delta under both contraction
policies, in addition to the existing seven oracle controls.

Both strict executables reran all 1,220,356 lanes and all 12 actual negative
controls. Independently recomputed reference bytes and actual output/flag
records are byte-identical to the prior result. The same value/special and
exception policies pass with zero mismatches and unchanged ULP histograms.
Compile warning logs are empty and source/tool drift is absent. Enabling
compiler errno semantics does not implement the explicitly excluded library
errno contract. Add the new strict controller and
`tests/test_host_expf_full_strict.py` to the component whitelist above.
