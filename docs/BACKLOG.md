# Product backlog

Ordered by priority within each epic. Claude maintains this file, and the owner sets
priorities. A story is refined to Definition of Ready only as its sprint approaches, so
later entries are intentionally short. **Depth** is the review depth from
[DEVELOPMENT_CYCLE.md](DEVELOPMENT_CYCLE.md#7-review-protocol).

## E0 Foundation (S0)

Full details are in [SPRINT-00](sprints/SPRINT-00.md).

| ID | Story | Depth |
|---|---|---|
| S0-01 | Toolchain manifest and `tools/doctor` | Light |
| S0-02 | ISA lint | Standard |
| S0-03 | T0 to T2 runner, with the acceptance fixture recorded red on the donor | Standard |
| S0-04 | Card runner and shared-lock behaviour | Deep |
| S0-05 | Donor inventory, including runtime libraries | Standard |
| S0-06 | GCC 16.2 fork and measured build and TDD-loop times | Standard |
| S0-07 | WRF and PhiChat coverage estimate | Standard |

## E1 GCC 16 skeleton (S1, Gate A)

| ID | Story | Acceptance | Depth |
|---|---|---|---|
| E1-01 | `k1om-mpss-linux` configures in GCC 16.2 | `configure` succeeds with `--with-as`, `--with-ld` and `--with-sysroot`; `all-gcc` builds; `-dumpmachine` is right | Standard |
| E1-02 | `-march=knc` and `TARGET_ISA_KNC`, with no SSE, AVX, CMOV, FCOMI or MFENCE-type features | T1 tests: predefined macros and feature set; `-mavx512f`, `-msse2` are rejected on this target | Deep |
| E1-03 | Output syntax and directives acceptable to `as` 2.22 | A corpus of integer C at `-O0`, `-O2`, `-g` assembles with `--march=k1om` and lints clean | Standard |
| E1-04 | Integer C without SSE assumptions: moves, calls, branches, no CMOV | T1: no `cmov` even in patterns that favour it; integer `gcc.c-torture/compile` subset without ICE | Standard |
| E1-05 | Port the K1OM defaults: loader path, link spec, 128-bit `long double`, assembler flags | T2: links against the sysroot; correct loader and ELF machine | Standard |
| E1-06 | Gate A evidence note | Times measured; blockers recorded; recommendation | Deep |

## E2 Scalar native (S2)

| ID | Story | Acceptance | Depth |
|---|---|---|---|
| E2-01 | KNC ABI: SF and DF arguments and returns in `zmm` lane 0, varargs with `%al`, and x87 bodies | ABI fixture cross-linked with donor objects in both directions, including overflow arguments, structs and callbacks; T3 | Deep |
| E2-02 | Scalar transfer lowering: `vpackstore`/`vbroadcast` through memory with no direct GPR moves; mask scratch handling | T1 and T3 mixed-pressure tests; the donor's secondary-reload failure reproducer passes, whether or not its mechanism still exists | Deep |
| E2-03 | x87 compare and branch without `fcomi`, and stack-alignment rules for `zmm` spills | T3 with NaN, signed zero and unordered cases; T1 no `fcomi` | Deep |
| E2-04 | Memory barriers and atomics without `mfence` and without `cmpxchg16b`; spin hint via `delay` where appropriate | T1 lint; T3 threaded smoke test | Standard |
| E2-05 | Build static libgcc: disable SSE-dependent parts, keep soft-float helpers working | T2 lint across `libgcc.a`; T3 helpers | Standard |
| E2-06 | Reach `hello`, scalar FP and `printf`; first `c-torture/execute` subset baseline (T4) | T3 pass; T4 baseline recorded | Standard |

## E3 Core IMCI (S3, Gate B)

| ID | Story | Acceptance | Depth |
|---|---|---|---|
| E3-01 | **Native probe, before any design:** behaviour of `vloadunpack` and `vpackstore` pairs and masked aligned forms at page boundaries, including which addresses fault | Probe source and results in `docs/research/`, citing the ISA manual | Deep |
| E3-02 | Vector modes valid under `TARGET_KNC`; `preferred_simd_mode` and vector sizes; register printing | T1 dumps; no regressions in scalar tests | Deep |
| E3-03 | Aligned and unaligned vector moves, spills, and constant loads in `imci.md` | T1 and T3, with register pressure | Deep |
| E3-04 | Add, sub, mul, and FMA for V16SF and V8DF; integer add, sub, logic for V16SI and V8DI; broadcasts | T1 and T3 per operation against exact oracles | Standard |
| E3-05 | Scalar peel and remainder through x87, so mixed loops work | `m1_affine` T1 and T2 green | Standard |
| E3-06 | Gate B: full `m1_affine` T3, with ABI cross-check and Fortran twin; shared-file line count; ICE classes | Evidence note and recommendation | Deep |

## E4 Masks and semantics (S4–S5)

| ID | Story | Depth |
|---|---|---|
| E4-01 | Mask registers, compares, blends, if-conversion | Deep |
| E4-02 | Gather and scatter loop lowering with `jknzd`; tests prove partial completion handling | Deep |
| E4-03 | Correctly rounded division and square root (ADR-0003): argument, hard cases, MPFR comparison. Until then, no vectorization of these operations | Deep |
| E4-04 | Masked tails, as far as E3-01 allows: scalar vs partial vs full choices across lengths 0–65 | Deep |
| E4-05 | Int and FP conversions, narrowing and widening within IMCI's 32/64-bit elements | Standard |
| E4-06 | Permutes, reductions (with FP ordering contract), min and max semantics | Standard |
| E4-07 | Memory up/down conversions and swizzle use for byte and word data | Standard |

## E5 Profitability (S6, Gate C)

| ID | Story | Depth |
|---|---|---|
| E5-01 | Machine characterization corpus: latency, throughput, transitions, tails, gather, spills, prefetch, at 1–4 threads per core and L1, L2 and larger working sets (T5) | Standard |
| E5-02 | Cost model v1 from measured tables, including vectorizer hooks, register costs and secondary moves | Deep |
| E5-03 | Per-loop reports: vector factor, checks, tail cost, helper calls, spills, and reasons for rejection | Standard |
| E5-04 | Evaluate source-format scalar in `zmm` against x87 (ADR-0003) | Deep |
| E5-05 | U/V scheduler v0, tested at production thread density | Standard |
| E5-06 | Gate C kernels: short-row flux and data-reuse fixtures from PhiWeather and PhiChat | Deep |

## E6 Runtimes (S7–S9, Gate D)

| ID | Story | Depth |
|---|---|---|
| E6-01 | Shared libgcc; symbol-version ceiling tied to glibc 2.21 and kernel 2.6.38 | Deep |
| E6-02 | libgfortran slice: descriptors, allocation, formatted I/O, modules; `real(16)` and libquadmath decision | Deep |
| E6-03 | libgomp with futex; TLS models; a single OpenMP runtime in the process | Deep |
| E6-04 | MPI and netCDF Fortran boundaries rebuilt or adapted; old `.mod` files never reused | Deep |
| E6-05 | IMCI intrinsics header, only for operations with real demand | Standard |
| E6-06 | libstdc++ subset: exceptions, RTTI, atomics, enough for pinned PhiChat. GCC 16's default C++ standard is checked against that code | Standard |

## E7 Math and kernels (S10–S12, Gate E)

| ID | Story | Depth |
|---|---|---|
| E7-01 | Pick functions from actual use; vector function ABI, with its own mangling (ADR required; do not reuse AVX-512's `_ZGVe`, since the code is not AVX-512) | Deep |
| E7-02 | Accurate `exp`, `log`, `pow` first; relaxed entry points separate; exceptional-lane repair compared | Deep |
| E7-03 | WRF representative region from source, carried through GIMPLE, RTL and assembly | Standard |
| E7-04 | PhiChat representative region from source | Standard |
| E7-05 | Gate E projection using the §13 model, overheads included | Deep |

## E8 Applications and release (M5–M6, opt-in)

Selected WRF and PhiChat builds; matched benchmarks; broader suites; packaging without
restricted sysroot content; user manual and support matrix; update procedure.

## Parked research

| Topic | Why parked |
|---|---|
| Prefetch policy | After cost model v1; needs T5 crossover data |
| Small matrix 2-D vectorization | After Gate C; applies to fixed-shape kernels only |
| PGO | After the target works; check threaded profile integrity first |
| Offline tuning-profile generator | After cost model v1 proves its value |
| ICC comparison | Only if a suitable licensed KNC-capable version already exists |
