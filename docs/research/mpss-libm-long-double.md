# MPSS long-double libm hazard audit (S11-16)

The lead's native run found **only cbrtl** faulting among the 12 probed functions;
the other 11 completed the corpus without a crash. The disassembly identifies **cbrtl**
as the one direct match for the negative 32-bit table-offset pattern in the
reviewed long-double code. This is a bounded crash audit, not an accuracy or
memory-safety proof. The ticket supplies the earlier cbrtl fault and S10-13 guard;
no additional native fault was observed in this sweep.

## Library and method

Input: `.work/_shared/toolchain/sysroot/lib64/libm-2.21.so`, the target of the
sysroot's `libm.so.6`; `usr/lib64/libm.so` links that SONAME. Commands, using
`.work/_shared/toolchain/cross/bin/` on PATH:

```
k1om-mpss-linux-objdump -T .work/_shared/toolchain/sysroot/lib64/libm-2.21.so
k1om-mpss-linux-objdump -d --no-show-raw-insn .work/_shared/toolchain/sysroot/lib64/libm-2.21.so
```

All addresses below are ELF virtual addresses before runtime relocation.
Reviewed the long-double implementation region `0x21ae0..0x2cf13`, including
unlabelled local helpers between exported functions, and the two mixed-precision
`nexttoward` entry points. Indexed memory operands were distinguished from LEA
and alignment NOPs; preceding index arithmetic, masks, range branches and
extensions were read. The shared argument reducer called at `0x24e4c` was also
followed into `0x91c0`. Symbol suffixes alone are insufficient: for example,
`ceil` and `creal` are double functions, whereas `lgammal_r` and the finite
entry points belong in this inventory.

## Indexed-load evidence and probe candidates

| Code / public callers | Load addresses | Index preparation / disposition |
| --- | --- | --- |
| `cbrtl` (`0x25e70`) | `0x25f5a`, `fldt (%rdx,%rcx,1)` | Exponent reduction starts at `0x25ec1`; signed division by 3 at `0x25ef7..0x25f0a`; remainder subtraction into ECX at `0x25f48`, shift in ECX at `0x25f4c`, no sign extension before the RCX address. Negative remainder becomes a large positive offset from table base `0x33e70`. **Direct hazard candidate.** |
| Local power helper (`0x24b10`), `powl` | `0x24c6d`, `0x24cce`, `0x24cf5`, `0x24d0d` | Indices masked to 2 (`0x24c63`), shifted logically to 0/1 (`0x24cc4`, `0x24d03`), or masked to 8 (`0x24ceb`). No negative offset at these loads. Probe as a control. |
| Local scale helper (`0x24ef0`), `scalbl` | `0x24f5a` | EAX masked to 8 at `0x24f49`; sign masked to `0x8000` at `0x24f43`, then shifted by 11 at `0x24f4e` and added. Offset is 0, 8, 16 or 24. Probe as a control. |
| `__lgammal_r_finite`, reached by `lgammal`, `lgammal_r`, `gammal` | `0x243e6`, `0x246c2` | Jump-table loads. Unsigned bound 6 (`0x243d6..0x243d9`); second index subtracts 3 and is bounded by 4 (`0x24616..0x2461c`, branch `0x246b5`). Loaded branch displacements are sign extended. Probe public callers as controls. |
| Local trig helpers (`0x25810`, `0x259d0`), `sinl`, `cosl`, `sincosl`; trig reduction also used by `tanl`, and `cosl` called by gamma internals used by `tgammal` | `0x258e4`, `0x25932`, `0x2596b`, `0x25a90`, `0x25ad3`, `0x25b12` | Signed conversion/extension at `0x258d3`, `0x258ed`, `0x258f4`, `0x25a8a`, `0x25a96`, `0x25a9d`, before the 64-bit shift/address. These do not have cbrtl's missing extension. Probe public callers as controls. |
| `cexpl` | `0x291fa`, `0x2925e`, `0x292b1`, `0x292f3`, `0x292f6` | Index masked to `0x10` at `0x291e5`, `0x292a7`, or combined with another `0x20` mask (`0x292e4..0x292ea`). Probe as a control. |
| Shared reduction helper `0x91c0`, reached by long-double trig reduction at `0x24e4c` | `0x91f0`, `0x926f` | Precision index sign extended at `0x91e4`; exponent-dependent table index sign extended at `0x925c`. Negative indices are excluded at `0x9281..0x9283` before `0x926f`. No cbrtl-style missing extension identified. Covered through trig controls. |

Other entries in the inventory have no additional direct indexed-table hazard
identified in this review. Complex wrappers may call the same trig/gamma paths;
this bounded probe exercises the public callers listed above, not every complex
argument combination or every internal entry separately.

## Probe and reproducible lead command

Source: `tools/s11_16_long_double.c`; build/stage through:

```
python tools/run.py --name s11-16-stage --inputs tools/s11_16_checks.py tools/s11_16_long_double.c -- python tools/s11_16_checks.py stage
```

The staged executable is `.work/_shared/S11-16/long-double-probe.mic`.
It opens `libm.so.6` explicitly and resolves symbols with `dlsym`, bypassing the
compiler's S10-13 cbrtl redirect and builtin folding. Each function runs in a
fresh child. That child uses `sched_getaffinity` and one pthread per allowed CPU,
partitioning inputs by worker index. The parent remains single threaded and
waits before launching the next function.

Each function receives both signs and four significands (1, 1.25, 1.5, and the
largest significand below 2), for **every integer binary exponent from -16445
through 16383**: 262632 input records. Values are constructed from their x87
bits, including subnormals, without relying on a libm input generator. At the
smallest subnormal exponents some significands coincide after truncation; every
exponent and sign is still visited. Every residue modulo 3 (and any other
exponent period within this range) is included. This is not exhaustive mantissa
coverage; zero, infinity and NaN are outside this finite-range crash sweep.

Binary functions use variants 0..3: `(x,1.5)`, `(x,-1.5)`, `(1.5,x)`,
`(-1.5,x)`. Complex exponential uses variants 0..1: `(x,1.5)` and `(1.5,x)`
for real/imaginary components. Other functions use variant 0. A `FAULT` record
contains the function, exact input as `sign/exponent:significand` hexadecimal,
enumeration exponent/sign/significand selector and call variant. Reconstruct x
from those ten bytes; the variant supplies the other argument. Formatting occurs
in thread-local storage before each call. The SIGSEGV handler only writes that
record and `_exit`s the child; the parent prints its `RESULT` and continues.
Core dumps are disabled. `OK` reports actual completed call counts; it means no
crash for this corpus, not numerical correctness. Missing symbols, thread/fork
failures and unexpected termination produce `ERROR`, never `OK`.

Lead only, from the main project root:

```
python tools/card_run --threads 240 --timeout 1800 .work/_shared/S11-16/long-double-probe.mic
```

Exit 0: no observed faults; 1: at least one SIGSEGV; 2: infrastructure/driver
error. The timeout remains an infrastructure result. Host acceptance uses the
same enumeration and child/thread driver, with two Cygwin workers and synthetic
healthy/fault/healthy functions; it checks every input bit pattern, isolation,
and result format. Native execution is reserved for the lead.

## Results and follow-up

Host driver: **PASS**, `s11_16_host-20261112-163807.log` (one host test,
8.374 seconds). Red run: `s11_16_red-20261112-162946.log`, expected missing probe
source, committed as `c2d26ca0` before adding the implementation.
GCC-KNC prefix cross build and `knc_lint`: **PASS**,
`s11_16_stage-20261112-163821.log`. All logs are under `.work/_state/logs/`.
The build uses `.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc`
with `-march=knc`, the card sysroot and dynamic libm lookup.
Native run: **completed by the lead**, 2026-11-12 22:22:59–22:23:16 UTC,
with 240 workers and boot ID `da3144f1-552e-4305-bd17-84a3835da020`.
Log: `.work/_shared/tmp/claude-next29/probe.out`; command as above.

| Function | Native result | Completed calls |
| --- | --- | --- |
| `cbrtl` | SIGSEGV (signal 11) | Child exited on fault |
| `powl` | OK | 1,050,528 |
| `scalbl` | OK | 1,050,528 |
| `lgammal` | OK | 262,632 |
| `lgammal_r` | OK | 262,632 |
| `gammal` | OK | 262,632 |
| `tgammal` | OK | 262,632 |
| `sinl` | OK | 262,632 |
| `cosl` | OK | 262,632 |
| `tanl` | OK | 262,632 |
| `sincosl` | OK | 262,632 |
| `cexpl` | OK | 525,264 |

The log contains two concurrent cbrtl fault reports for the same smallest
positive subnormal, with distinct significand selectors:

```
FAULT cbrtl signal=11 input=0000:0000000000000001 exponent=-16445 sign=0 mantissa=2 variant=0
FAULT cbrtl signal=11 input=0000:0000000000000001 exponent=-16445 sign=0 mantissa=3 variant=0
```

The parent continued through all functions and reported
`SUMMARY functions=12 faults=1 errors=0`. Card exit 1 represents the observed
cbrtl fault, not an infrastructure failure. This confirms the known cbrtl
hazard; S10-13 already provides its guard, so no new guard ticket is needed.
The controls' OK results establish only that this finite corpus did not crash;
they do not establish numerical accuracy or safety for other inputs.

## Exported long-double entry points

The inventory includes public real and complex APIs, GNU extensions, finite
exports and classification helpers. `nexttoward`/`nexttowardf` accept a long
double second operand despite their different return types. Aliases are retained.
| ELF virtual address | Exported entry points (aliases share a row) |
| --- | --- |
| `0xaaa0` | `nexttoward` |
| `0x1a520` | `nexttowardf` |
| `0x21ae0` | `__acosl_finite` |
| `0x21ba0` | `__asinl_finite` |
| `0x21e00` | `__atan2l_finite` |
| `0x21ec0` | `__coshl_finite` |
| `0x22020` | `__expl_finite` |
| `0x220d0` | `__fmodl_finite` |
| `0x220f0` | `__hypotl_finite` |
| `0x22980` | `__j0l_finite` |
| `0x22bf0` | `__y0l_finite` |
| `0x23490` | `__j1l_finite` |
| `0x236c0` | `__y1l_finite` |
| `0x23990` | `__jnl_finite` |
| `0x23df0` | `__ynl_finite` |
| `0x241a0` | `__lgammal_r_finite` |
| `0x24a60` | `__logl_finite` |
| `0x24ae0` | `__log10l_finite` |
| `0x24ed0` | `__remainderl_finite` |
| `0x24f80` | `__sinhl_finite` |
| `0x25130` | `__sqrtl_finite` |
| `0x25540` | `__gammal_r_finite` |
| `0x25d80` | `asinhl` |
| `0x25e60` | `atanl` |
| `0x25e70` | `cbrtl` |
| `0x25f80` | `ceill` |
| `0x25fb0` | `cosl` |
| `0x26100` | `erfl` |
| `0x26560` | `erfcl` |
| `0x26a70` | `expm1l` |
| `0x26b30` | `fabsl` |
| `0x26b40` | `floorl` |
| `0x26b70` | `log1pl` |
| `0x26bc0` | `logbl` |
| `0x26bd0` | `nextafterl`, `nexttowardl` |
| `0x26e50` | `rintl` |
| `0x26f90` | `scalblnl` |
| `0x27030` | `significandl` |
| `0x27040` | `sinl` |
| `0x27190` | `tanl` |
| `0x27250` | `tanhl` |
| `0x27360` | `acosl` |
| `0x273b0` | `acoshl` |
| `0x27400` | `asinl` |
| `0x27450` | `atan2l` |
| `0x27540` | `atanhl` |
| `0x275a0` | `coshl` |
| `0x27630` | `dreml` |
| `0x27640` | `expl` |
| `0x27700` | `exp2l` |
| `0x277c0` | `exp10l`, `pow10l` |
| `0x27880` | `fmodl` |
| `0x27950` | `tgammal` |
| `0x27b10` | `hypotl` |
| `0x27bc0` | `j0l` |
| `0x27c20` | `y0l` |
| `0x27d00` | `j1l` |
| `0x27d60` | `y1l` |
| `0x27e40` | `jnl` |
| `0x27ee0` | `ynl` |
| `0x28010` | `gammal`, `lgammal` |
| `0x28110` | `lgammal_r` |
| `0x28200` | `logl` |
| `0x28290` | `log10l` |
| `0x28320` | `powl` |
| `0x28600` | `remainderl` |
| `0x287d0` | `scalbl` |
| `0x28960` | `sinhl` |
| `0x289f0` | `sqrtl` |
| `0x28a40` | `ilogbl` |
| `0x28a80` | `__fpclassifyl` |
| `0x28ae0` | `fmaxl` |
| `0x28b00` | `fminl` |
| `0x28b20` | `fdiml` |
| `0x28b50` | `nanl` |
| `0x28be0` | `truncl` |
| `0x28c10` | `remquol` |
| `0x28cb0` | `__log2l_finite` |
| `0x28ce0` | `__exp2l_finite` |
| `0x28d20` | `roundl` |
| `0x28e70` | `nearbyintl` |
| `0x28ea0` | `sincosl` |
| `0x290d0` | `conjl` |
| `0x290e0` | `cimagl` |
| `0x290f0` | `creall` |
| `0x29100` | `cabsl` |
| `0x29110` | `cargl` |
| `0x29130` | `cexpl` |
| `0x29320` | `csinhl` |
| `0x296c0` | `ccoshl` |
| `0x29a20` | `clogl` |
| `0x29e10` | `catanl` |
| `0x2a2f0` | `casinl` |
| `0x2a3e0` | `ccosl` |
| `0x2a400` | `csinl` |
| `0x2a7d0` | `ctanl` |
| `0x2aa70` | `ctanhl` |
| `0x2ad20` | `cacosl` |
| `0x2adf0` | `casinhl` |
| `0x2af10` | `cacoshl` |
| `0x2b0b0` | `catanhl` |
| `0x2b540` | `csqrtl` |
| `0x2b950` | `cpowl` |
| `0x2b9c0` | `cprojl` |
| `0x2ba30` | `__clog10l`, `clog10l` |
| `0x2bdf0` | `fmal` |
| `0x2c890` | `llrintl`, `lrintl` |
| `0x2c8a0` | `lroundl` |
| `0x2c9b0` | `llroundl` |
| `0x2cae0` | `log2l` |
| `0x2cba0` | `__issignalingl` |
| `0x2cc80` | `__finitel`, `finitel` |
| `0x2cc90` | `copysignl` |
| `0x2ccb0` | `modfl` |
| `0x2cdd0` | `scalbnl` |
| `0x2cdf0` | `frexpl` |
| `0x2ce60` | `ldexpl` |
| `0x2cf00` | `__signbitl` |
