# Phase 5 vector-math source scaffold

This directory contains interfaces and six narrow-wrapper C definitions. **No
mathematical kernel is implemented or numerically qualified.** It is not a usable
`libknc_mvec.a`, a G5 pass, or a mask-preserving library profile.

`symbols.json` is derived directly from the accepted G0 receipt, SHA256
`3ef5147e0b87124c3191734c5d7d86be1f246de00ce9342d557efe95c4998374`.
There is no assembly rescan: the specification preserves all 36 observed names
and their actual call counts, including 23 full-width e names and 13 b/d names.
`include/knc_mvec_abi.h` declares all 36 with GCC vector-extension types and the
observed unmasked N ABI arities. Declarations are not binary exports or proof of
the translated calling convention.

| Initial family | e calls | b calls | d calls | Total |
|---|---:|---:|---:|---:|
| expf | 440 | 13 | 5 | 458 |
| exp | 366 | 4 | 17 | 387 |
| logf | 359 | 13 | 1 | 373 |
| log | 106 | 0 | 0 | 106 |
| Initial families | 1,271 | 30 | 23 | 1,324 |

These four families account for 1,324 of 2,879 calls (45.99%), not a majority.
The other 26 symbols remain declaration-only, including the pow families.
All specification qualification flags are false and no rule is enabled.

## Source architecture

`src/exp_log_wrappers.c` implements exactly the six observed b/d expf, logf and
exp signatures. Each wrapper initializes a local full-width vector, copies its
active input lanes into the low positions, calls the corresponding full-width
e kernel and returns the low result lanes. Exp padding uses positive zero;
log padding uses positive one. Thus the C source does not feed arbitrary upper
lanes into an inactive log operation. No b/d double-log name was observed and
none is invented.

The four full-width initial interfaces `_ZGVeN16v_expf`, `_ZGVeN16v_logf`,
`_ZGVeN8v_exp` and `_ZGVeN8v_log` are deliberately undefined. The wrappers
reference the first three; double log currently has only its full-width
declaration. A normal link using the wrapper object without real kernels fails.
There is no scalar-libm fallback, identity return, numerical placeholder,
approximation instruction, imported coefficient set or hand-edited IMCI source.
Future kernels must implement range reduction and an independently tested
approximation, then follow the C translation pipeline.

## Mask and ABI obligations remain open

Reserving k5-k7 with compiler flags does not initialize their contents.
Generated functions still require qualified entry materialization of the
reserved mask constants before translated narrow/scalar operations. Lane masks
must respect precision as well as physical register width. Wrapper-to-kernel
calls also require the qualified post-call refresh contract. This scaffold
inserts no assembly prologue and enables no refresh exemption; it makes no
mask-preservation claim.

The host test's internal vector calling convention is not the target ABI.
Actual translated callers/callees still need card measurements of lane order,
all argument and return widths, stack alignment, upper-lane behavior, scratch
registers, masks and preserved state. Ordinary KNL output must never be run
directly on KNC.

## Required qualification before G5

- Qualify the C instruction templates first; compile to Linux System V
  assembly, translate on Windows, and assemble/link through `K1OM_REMOTE`.
  Require actual EM_K1OM and the target call-boundary evidence. No manual
  WRF `.k1om.s` edit or new rule follows from these sources.
- Implement the full-width kernels with the required maximum 4-ULP SP/DP
  accuracy against an independent high-precision oracle. Test at least
  1,000,000 inputs per exported symbol, with ULP histograms and worst cases.
  Cover the full valid finite domain, range-reduction boundaries, near-one log
  inputs, tiny/subnormal values and overflow/underflow thresholds.
- Define and test NaNs (including signaling NaNs and the payload policy),
  infinities, signed zero, negative/zero log inputs, rounding modes,
  denormal/FTZ state and floating exception behavior. Neutral padding does not
  prove that the future kernels handle these cases.
- Randomize otherwise arbitrary physical inactive lanes, including exceptional
  values, and entry mask contents on the card. Prove active-bit preservation,
  lane order, neutralization and absence of unwanted inactive-lane exceptions.
  Repeat across all observed b/d widths and full-width calls.
- Complete and qualify every symbol in `symbols.json`, including the other
  26 declarations, before claiming full observed-ABI coverage or G5.

## Focused source checks

```powershell
.tools/python/Scripts/python.exe scripts/KncMvecScaffold.py
.tools/python/Scripts/python.exe -m unittest discover -s tests -p test_knc_mvec_scaffold.py
```

The C wrapper-contract test uses test-only sentinel kernels, not exp/log
implementations. It compiles both sides with the same Cygwin host C compiler,
baseline x86-64/SSE2, AVX/AVX2/AVX-512 disabled and vectorization disabled.
This allows the host compiler's internal wide-vector argument convention
without requiring AVX-512 hardware; `-Wno-psabi` suppresses warnings about that
test configuration. A host assembly guard rejects YMM/ZMM/mask operands.
No raw KNL output or target code is executed.

Across 12,288 randomized wrapper calls, the stubs check 163,840 input lanes,
including 102,400 neutral inactive lanes, and 61,440 returned lanes. Active
inputs are integer-generated bit patterns. The positive test has zero errors;
a deliberately wrong exp-neutral expectation produces exactly 61,440 errors
and nonzero exit. A separate link control requires failure without the full
kernels. These are wrapper-contract checks only, not math, floating-exception,
target ABI or G5 evidence. Sentinel sources require an explicit test macro and
must never enter the production library.

For a fresh private source-only preparation:

```powershell
.tools/python/Scripts/python.exe scripts/Prepare-KncMvecScaffold.py --directory artifacts/test-state/knc-mvec-source-preparation-01
```

This records a future C `-S` command with actual compiler/source hashes and
unchanged BIND/OPT flags. It does not run the compiler, translate, assemble,
link, contact the card or execute generated code. The future `.knl.s` remains
unqualified input to the pipeline.

## Actual source-only Linux-target compilation

The exact prepared GCC 14.3.0 command was subsequently run once in an owned
Windows job. Compiler PID 26564 exited 0; the owned job drained to zero and all
frozen preparation/source/compiler inputs matched afterward. It emitted 3,387
bytes of raw Linux-target KNL assembly, with 20 instructions mentioning ZMM
registers and six vector call sites. The six narrow wrapper definitions import
`_ZGVeN16v_expf`, `_ZGVeN16v_logf` and `_ZGVeN8v_exp`; these full kernels remain
undefined. Double log remains a declared future full-width interface.

The retained outcome is
`artifacts/test-state/knc-mvec-source-preparation-01/compile.json`, with raw
`exp_log_wrappers.knl.s`, command, stdout/stderr and before/after hashes beside
it. This is source compilation evidence only: no translator, assembler, linker,
card job or generated-code execution occurred. No ABI, mask, numerical or G5
qualification follows from a ZMM count.

The existing histogram tool was run on this one new 3,387-byte assembly only:
121 instructions /21 mnemonic names, I61/B44/C16, A0/D0/?0. Its private
`histogram.md` records all16 C instructions and witnesses. Shuffles, unpacking,
extraction and GPR/vector transport therefore remain real dependencies of even
these six wrappers. This does not change the frozen WRF G0 census or qualify
the proposed mappings.

The emitted `_ZGVdN8v_expf` body also provides a concrete input for the later
register-width rules: `vxorps %xmm1,%xmm1,%xmm1` precedes a full-width
`vmovaps %zmm1,(%rsp)` when constructing zero padding. Translation must
preserve that full-zero dependency. Merely renaming XMM to ZMM with a low-lane
merge mask can retain arbitrary upper data and break the wrapper contract.
The existing catalog's full-width zero-idiom proposal still needs its own
assembler witness and randomized card test before activation. This observed
dependency does not qualify any template or justify a flag change.
