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
| S0-07 | Benchmark corpus and coverage estimate | Standard |
| S0-08 | Toolchain independent of PhiWeather | Light |

## E1 GCC 16 skeleton (S1, Milestone M0)

Refined into tickets S1-01 to S1-07; see [SPRINT-01](sprints/SPRINT-01.md).

| ID | Story | Acceptance | Depth |
|---|---|---|---|
| E1-01 | `k1om-mpss-linux` configures in GCC 16.2 | `configure` succeeds with `--with-as`, `--with-ld` and `--with-sysroot`; `all-gcc` builds; `-dumpmachine` is right | Standard |
| E1-02 | `-march=knc` and `TARGET_ISA_KNC`, with no SSE, AVX, CMOV, FCOMI or MFENCE-type features | T1 tests: predefined macros and feature set; `-mavx512f`, `-msse2` are rejected on this target | Deep |
| E1-03 | Output syntax and directives acceptable to `as` 2.22 | A corpus of integer C at `-O0`, `-O2`, `-g` assembles with `--march=k1om` and lints clean | Standard |
| E1-04 | Integer C without SSE assumptions: moves, calls, branches, no CMOV | T1: no `cmov` even in patterns that favour it; integer `gcc.c-torture/compile` subset without ICE | Standard |
| E1-05 | Port the K1OM defaults: loader path, link spec, `long double` as x87 80-bit in 16 bytes, assembler flags | T2: links against the sysroot; correct loader and ELF machine | Standard |
| E1-06 | Milestone M0 evidence note | Times measured; blockers recorded; recommendation | Deep |

## E2 Scalar native (S2)

Drafted as tickets S2-01 to S2-08; see [SPRINT-02](sprints/SPRINT-02.md).

| ID | Story | Acceptance | Depth |
|---|---|---|---|
| E2-01 | KNC ABI: SF and DF arguments and returns in `zmm` lane 0, varargs with `%al`, and x87 bodies | ABI fixture cross-linked with donor objects in both directions, including overflow arguments, structs and callbacks; T3 | Deep |
| E2-02 | Scalar transfer lowering: `vpackstore`/`vbroadcast` through memory with no direct GPR moves; mask scratch handling | T1 and T3 mixed-pressure tests; the donor's secondary-reload failure reproducer passes, whether or not its mechanism still exists (`tests/regress/knc-secondary-reload.f90`, compile-only; its header gives the RTL symptom check to wire in) | Deep |
| E2-03 | x87 compare and branch without `fcomi`, and stack-alignment rules for `zmm` spills | T3 with NaN, signed zero and unordered cases; T1 no `fcomi` | Deep |
| E2-04 | Memory barriers and atomics without `mfence` and without `cmpxchg16b`; spin hint via `delay` where appropriate | T1 lint; T3 threaded smoke test | Standard |
| E2-05 | Build static libgcc: disable SSE-dependent parts, keep soft-float helpers working | T2 lint across `libgcc.a`; T3 helpers | Standard |
| E2-06 | Reach `hello`, scalar FP and `printf`; first `c-torture/execute` subset baseline (T4) | T3 pass; T4 baseline recorded | Standard |

## E3 Core IMCI (S3, Milestone M1)

| ID | Story | Acceptance | Depth |
|---|---|---|---|
| E3-01 | **Native probe, before any design:** behaviour of `vloadunpack` and `vpackstore` pairs and masked aligned forms at page boundaries, including which addresses fault | Probe source and results in `docs/research/`, citing the ISA manual | Deep |
| E3-02 | Vector modes valid under `TARGET_KNC`; `preferred_simd_mode` and vector sizes; register printing | T1 dumps; no regressions in scalar tests | Deep |
| E3-03 | Aligned and unaligned vector moves, spills, and constant loads in `imci.md` | T1 and T3, with register pressure | Deep |
| E3-04 | Add, sub, mul, and FMA for V16SF and V8DF; integer add, sub, logic for V16SI and V8DI; broadcasts | T1 and T3 per operation against exact oracles | Standard |
| E3-05 | Scalar peel and remainder through x87, so mixed loops work | `m1_affine` T1 and T2 green | Standard |
| E3-06 | Milestone M1: full `m1_affine` T3, with ABI cross-check and Fortran twin; shared-file line count; ICE classes | Evidence note and recommendation | Deep |

## E4 Masks and semantics (S4–S5)

| ID | Story | Depth |
|---|---|---|
| E4-01 | Mask registers, compares, blends, if-conversion | Deep |
| E4-02 | Gather and scatter loop lowering with `jknzd`; tests prove partial completion handling | Deep |
| E4-03 | Correctly rounded division and square root (ADR-0003): argument, hard cases, MPFR comparison. Until then, no vectorization of these operations. Division by a constant can be exact with a reciprocal and one FMA correction (`q=RN(a*r); e=fma(-c,q,a); q'=fma(e,r,q)`; the WRF work verified it for `/12` and `/60`): prove which constants it holds for (`docs/research/wrf-input-2026-11-06.md`) | Deep |
| E4-04 | Masked tails, as far as E3-01 allows: scalar vs partial vs full choices across lengths 0–65 Tail strategies in order: aligned masked tail; masked vector peel to alignment; gather/scatter tail for unknown alignment (Tian et al. section IV). Whole-loop masking for trip counts below the vector length. Crossovers by check C6 at lengths 1-33. | Deep |
| E4-05 | Int and FP conversions, narrowing and widening within IMCI's 32/64-bit elements | Standard |
| E4-06 | Permutes, reductions (with FP ordering contract), min and max semantics | Standard |
| E4-07 | Memory up/down conversions and swizzle use for byte and word data Widened (`docs/research/imci-vs-avx512.md`): fold `{1to16}`, `{4to16}` broadcasts and `{float16}`, `{uint8}`, `{uint16}`, `{sint16}` up-converting memory operands into arithmetic and compares within ISA Table 4.2's legality limits (Sf32 has no `{sint8}`; rcp23/rsqrt23/log2 take none). Saves instructions and registers, not latency (memory-operand latency 12). | Standard |

## E5 Profitability (S6, Milestone M2; designed around the KNC machine model, ADR-0009)

| ID | Story | Depth |
|---|---|---|
| E5-01 | Machine characterization corpus: latency, throughput, transitions, tails, gather, spills, prefetch, at 1–4 threads per core and L1, L2 and larger working sets (T5) | Standard |
| E5-02 | Cost model v1 from measured tables, including vectorizer hooks, register costs and secondary moves | Deep |
| E5-03 | Per-loop reports: vector factor, checks, tail cost, helper calls, spills, and reasons for rejection | Standard |
| E5-04 | Evaluate source-format scalar in `zmm` against x87 (ADR-0003) | Deep |
| E5-05 | U/V scheduler v0, tested at production thread density | Standard |
| E5-07 | Software prefetch v1: `vprefetch0/1/2` and `vprefetche*` patterns in `imci.md`, KNC cache and latency parameters from E5-01, and GCC's `-fprefetch-loop-arrays` on at `-O2`/`-O3` for KNC when E5-01 shows a gain; judged on streaming and stencil kernels in exclusive card windows (owner, 2026-11-03) ADR-0009 amendment 1 point 2: L2 distance > L1 distance; prefetch latency and simultaneous prefetches derived from `knc-threads-per-core`; L2 software prefetch also for unit-stride loops with more streams than 16/(threads per core). Sweep against ICC's 64/32 iterations (check C5, `docs/research/knc-optimization-sources.md`). | Standard |
| E5-08 | Streaming (no-read) stores for write-only output that covers whole lines (`vmovnrap*`/`vmovnrngoap*`), legal only when the whole 64-byte line is written; measured against normal stores (ADR-0009 point 5) Measure `vmovaps`, `vmovnraps` and `vmovnrngoaps` with a fence on memory-sized write-only output at 1 core and 60x4 (check C1); S6-03's one-core figure used `vmovnraps` only. NGO needs a fence before publication; never masked or converted. | Standard |
| E5-10 | Inline block move and set (`cpymem`/`setmem`) with IMCI for known and bounded sizes, with line-crossing-safe unaligned halves; measured against the library call (the WRF work saw glibc's word copy at 0.57 GB/s per thread) | Standard |
| E5-11 | Per-loop choice where one KNC scalar cost flips loops both ways: S6-05 round 1 (scalar add cost below 1) made mat8 20% faster and stencil1/2 3-6% slower through induction-variable choices; round 2 restored the stencils and lost mat8 (`docs/research/card-runs-s6.md`, `docs/research/knc-costs.md`) Also: reject vectorization with lane use of 25% or less when full unroll plus SLP is possible (Tian et al. Fig. 6.4), after check C6 and the mat8 diagnosis. | Standard |
| E5-12 | `-mtune=knc` tune-flag audit: `FAST_PREFIX` off (0x66/0x67 prefixes cost 2 decode cycles, SSDG p.16); review partial-register, RMW, inc/dec, memory-operand, macro-fusion and push flags for the in-order core; T1 scans plus one card before/after | Standard |
| E5-13 | Default 64-byte alignment for static, global and local arrays of 64 bytes or more under `-march=knc`, and for gfortran `ALLOCATE` of vectorizable types (with E6-02); measure on the M2 short-length rows | Standard |
| E5-14 | `vpmadd231d` combine for V16SI multiply-add (exact, no flag gate; replaces `vpmulld` + `vpaddd`; also takes `{sint8}`/`{sint16}` memory up-conversion). Card latency/throughput row first. Also check whether `vfmadd132/213` alternatives in the FMA pattern remove copies in reductions (one T1 scan on the M2 kernels) | Standard |
| E5-15 | `vaddsetsps` add-and-sign-mask combine, gated by `-fno-signed-zeros -ffinite-math-only` (k1 takes the raw sign bit: -0.0 and some NaNs set it). Only if a corpus kernel shows the shape | Light |
| E5-09 | `-mtune=knc` tables: a KNC `processor_costs` entry, cache and prefetch parameters, unroll and alignment defaults, each chosen by card measurement, plus the published "GCC-KNC flags" page with ICC `-mmic` equivalents (ADR-0009 points 6 and 8) Unroll factor from `knc-threads-per-core`, so the 4-cycle vector and 12-cycle memory-operand latencies are covered at that density; unroll-then-schedule plus multiple accumulators is the software pipelining (check C9 at 1 and 2 threads per core, unroll 1/2/4; `docs/research/knc-optimization-sources.md` supplement). | Standard |
| E5-06 | Milestone M2 kernels: short-loop, stencil and small-matrix kernels drawn from the corpus, plus hand-written IMCI references written for this project. Include a short-row strided kernel shaped like WRF's hot loops (rows of 7-9 elements, j/k/i order, many arrays per point) and report 2 threads per core next to 4 (`docs/research/wrf-input-2026-11-06.md`) | Deep |

## Proposed for Sprint 8 (lead, 2026-11-07): the M2 weak spots

Recommended to the owner as a tuning block in Sprint 8, after Sprint 7's runtimes; not yet decided.
- E4-04 rest: masked tails that never cross into an unmapped page (line-crossing test for the
  unaligned second half, or peeling/versioning for alignment), so odd short lengths stop falling
  back to x87.
- Small-matrix kernels (mat8 at about 2% of the IMCI gain, mat16 at about 26%): diagnose with the
  per-loop reports (S6-04), then fix. S6-06's scheduler made mat8 a further 10% slower (owner approved S6-06 for
  now, 2026-11-07; `docs/research/card-runs-s6.md`).
- E5-11: the per-loop scalar-add cost choice.
- E5-07: two-level software prefetch (ADR-0009 point 5; WRF measured 2.4x on short rows).
- E5-12 tune-flag audit if there is room (cheap).
- E5-14 `vpmadd231d` combine (cheap, exact), and the widened E4-07 operand folding if there is
  room (`docs/research/imci-vs-avx512.md`). Card rows first for `vpmadd231d`, `vexp223ps`, `vlog2ps`,
  `vaddsetsps` and one broadcast/converting memory operand.
- Order (ADR-0009 amendment 1): E4-04 masked tails, E5-07 prefetch, the small-matrix lane-use
  rejection, E5-11, E5-12. Card checks C1-C7 (`docs/research/knc-optimization-sources.md`) come first.

## E6 Runtimes (S7–S9, Milestone M3)

| ID | Story | Depth |
|---|---|---|
| E6-01 | Shared libgcc; symbol-version ceiling tied to glibc 2.21 and kernel 2.6.38 | Deep |
| E6-02 | libgfortran slice: descriptors, allocation, formatted I/O, modules; `real(16)` and libquadmath decision. FP control (`config/fpu-387.h`) must manage KNC's MXCSR: CPUID reports no SSE on KNC, so today it skips MXCSR entirely, and the x86 masks it would write (bits 7-12) are reserved and fault. Keep bit 21 and leave 7-12 alone (lead, 2026-11-03 card probe). Never mix with the card's GCC 5 `libgfortran`: its descriptors predate GCC 8 | Deep |
| E6-03 | libgomp with futex; TLS models (native, after S3-14); a single OpenMP runtime in the process; measure `malloc` arena contention at 60-240 threads in an exclusive card window (the PhiWeather project saw a major slowdown from allocator contention) | Deep |
| E6-04 | MPI Fortran bindings rebuilt or adapted, and common corpus libraries built; old `.mod` files never reused | Deep |
| E6-05 | IMCI intrinsics header, only for operations with real demand | Standard |
| E6-07 | GCC generic vectors narrower than 512 bits (`vector_size` 8, 16, 32) passed or returned by value: today a clean "unsupported KNC register ABI mode" error (S2-02; 16 of the torture sweep's 33 compile errors). Check what the donor GCC 5 does, then pass them in memory or GPRs as an ABI decision (ADR) and test against donor objects. Only if corpus code needs it | Deep |
| E6-06 | libstdc++: exceptions, RTTI, atomics, threads, with coverage measured by its own testsuite and the corpus. Check GCC 16's default C++ standard against corpus code | Standard |

## E7 Math and broad optimization (S10–S12, Milestone M4)

| ID | Story | Depth |
|---|---|---|
| E7-01 | Pick functions from corpus use, starting with common libm calls; vector function ABI and compiler binding (ADR required). Names are settled by ADR-0011 (`__knc_vmath_<name>_<lanes>`, never `_ZGV`); start from the copied sources in `contrib/knc-vecmath/` | Deep |
| E7-02 | Accurate `exp`, `log`, `pow` first; relaxed entry points separate; exceptional-lane repair compared. Requalify the copied functions as built by GCC-KNC, on the card; the PhiWeather receipts are targets, not evidence (ADR-0011 point 4). A card harness is ready in `tests/acceptance/vecmath_qualify/` Extended: relaxed `exp2f`/`expf` on `vexp223ps` (int32 8.24 fixed-point input, 0.99 ulp) and `logf` on `vlog2ps` (4 ulp outside [0.5,2], 2^-21 absolute inside; denormals flushed), bound only under `-ffast-math` with `-fno-math-errno -ffinite-math-only`, never by default; needs an ADR-0011 amendment with the bounds, a card accuracy comparison, and the owner's call on the accuracy tier. | Deep |
| E7-03 | Rank missed optimizations by corpus-wide profile and carry the top regions through GIMPLE, RTL and assembly | Standard |
| E7-04 | Scalar and integer code quality for the in-order core: scheduling, inlining, code size, branches without CMOV Measure the branch-mispredict penalty (check C10) and set `BRANCH_COST` from it; scalar if-conversion through setcc/sbb sequences (no CMOV); evaluate lane-0 `vblendmps` selects for FP with E5-04. | Standard |
| E7-06 | Two-level prefetch like `icc`: L2 far (`vprefetch1`) and L1 near (`vprefetch0`) distances per loop, exclusive prefetch for stores, none for loops that fit in cache; ranked on the corpus against E5-07 (owner, 2026-11-03) | Deep |
| E7-08 | Instrumented PGO on the card: libgcov for k1om, `-fprofile-update=atomic`, `.gcda` under `/tmp`; after the E6 runtimes. AutoFDO stays parked until `perf` sampling works on the card | Standard |
| E7-05 | Milestone M4: corpus comparison against GCC 5.1.1, including held-out programs | Deep |

## E8 Program corpus and release (M5–M6)

Full corpus builds; matched benchmarks; broader suites; packaging without restricted
sysroot content; user manual and support matrix; update procedure.

| ID | Story | Depth |
|---|---|---|
| E8-01 | llama.cpp (KNC fork) as a corpus program (owner, 2026-11-07). Source: the owner's `Project BluePower/llama.cpp-knc`, read-only and not a requirement; GCC-KNC copies a pinned snapshot into its corpus when the work starts, as with ADR-0011. Gates: libstdc++ with threads and atomics (E6-06), libgomp only for ggml's OpenMP mode (E6-03); the whole program built with GCC-KNC (GCC 5 and GCC 16 C++ objects never mixed). Checks: builds without the GCC 5 downgrade patches against a newer upstream; its hand-written IMCI kernels assemble under GCC-KNC (extended-`asm` zmm and mask constraints); generated text and logits match the GCC 5 build; prompt and generation speed versus the GCC 5 build measured by ADR-0010 point 7 (paired, interleaved). A profile shows the time left in non-kernel operators (softmax, SwiGLU, normalization, RoPE), which feeds E7-01/E7-02 (vector `expf`) and E6-05 (intrinsics header, by this program's demand) | Deep |

## Parked research

| Topic | Why parked |
|---|---|
| Small matrix 2-D vectorization | After Milestone M2; applies to fixed-shape kernels only |
| Swing modulo scheduling | Needs an i386 `doloop_end` in shared code (ADR-0006); revisit only if check C9 shows loops still latency-bound at 1-2 threads per core after unrolling and scheduling |
| `vfmadd233ps` / `vpmadd233d` scale-and-bias | Builtins only, no recognizer; revisit with E8-01's quantized llama.cpp blocks |
| AutoFDO | Needs `perf` sampling on the card; instrumented PGO is E7-08 |
| Offline tuning-profile generator | After cost model v1 proves its value |
| ICC comparison | Only if a suitable licensed KNC-capable version already exists |
