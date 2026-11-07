# IMCI instructions that AVX-512 lacks: seven claims checked (2026-11-07)

Research note for the lead (owner's request: verify a GPT-written claim set, say how GCC-KNC should
exploit what is true). Nothing here is applied: ADRs, backlog and code are unchanged, no card run.
Tags: **[fact]** Intel 327364-001 (`.work/_shared/intel-327364-001-xeon-phi-isa.txt`, page numbers
are the manual's); **[card]** our measurements; **[knowledge]** my recollection of AVX-512, not
checked against a source here; **[inference]** this note's reasoning.

## 1. Verdict table

| # | Claim | Verdict | Source |
|---|---|---|---|
| 1 | `VLOG2PS`: 16-lane approximate log2; AVX-512F/ER have none | **True, with one omission.** Accuracy and denormal text match. The claim leaves out that it takes **no** broadcast, conversion or swizzle (any other SwizzUpConv raises #UD), and that it also flushes tiny results. AVX-512F/ER have no log: [knowledge] ER has `VEXP2PS`, `VRCP28PS`, `VRSQRT28PS` only (and AVX-512F has `VGETEXPPS`/`VGETMANTPS`, which log code builds on). | p.373; Table 4.2 p.61; App. C.3 |
| 2 | `VFMADD233PS`: fused scale-and-bias on 4-element groups; ~10% fewer shader instructions | **Right on semantics, the 10% is the manual's own marketing line.** Per group of 4: `dst[i] = zmm2[i] * t3[g+1] + t3[g+0]`, where `t3` is the second source (register, `{16to16}` or `{4to16}`; no `{1to16}`, no conversion, no swizzle). The manual says it saves one vector load per interpolant, "around ten percent of shader instructions". That is a graphics-shader estimate, not a measured figure for general code. | p.224-225; Table 4.2 p.61 |
| 3 | `VPMADD231D` integer multiply-add; `VPMADD233D`; no INT8 dot product | **True.** `zmm1 += zmm2 * Si32(zmm3/mt)` as 32-bit modular arithmetic, so one instruction replaces `vpmulld` + `vpaddd`. [knowledge] AVX-512F has no integer FMA (`VPMULLD` + `VPADDD`); AVX-512IFMA (`VPMADD52LUQ/HUQ`) is 52-bit, a different thing. `VPMADD233D` is the integer twin of 233PS (same 4-group scale/bias, `{4to16}` allowed). No byte or word dot-product instruction exists in IMCI; [knowledge] AVX-512 VNNI (`VPDPBUSD`, `VPDPWSSD`) is the one that adds it. **Extra the claim misses:** `VPMADD231D` takes `Si32` memory up-conversion (`{uint8}`, `{sint8}`, `{uint16}`, `{sint16}`, plus broadcasts), so 8/16-bit data times int32 weights accumulates with no separate widening. Latency and throughput are not in the manual. | p.490, p.491-493 (VPMADD233D); Table 2.9 p.33 |
| 4 | MVEX memory up-conversion and register swizzles in arithmetic | **True, but narrower than stated.** Sf32 arithmetic takes `{float16}`, `{uint8}`, `{uint16}`, `{sint16}` and broadcasts `{1to16}`, `{4to16}`, but **no `{sint8}`** (code 101 is absent; Uf32 and Si32 have it). Register swizzles (`cdab`, `badc`, `dacb`, `aaaa`...) apply only to a *register* third operand, and are replaced by the rounding override when EH=1. Memory conversion and swizzle are **not** available on `vrcp23ps`, `vrsqrt23ps`, `vlog2ps` (none), `vexp223ps` (register swizzle only), `vfmadd233ps`/`vpmadd233d` (broadcast only, no conversion), and `vcvtps2pd`/`vcvtdq2pd` (`#UD` for memory conversions, `knc-conversions.md` p.49). Conversions are element-wise but the memory read is only the converted footprint (16 B for `{uint8}`). | Tables 2.4, 2.9 p.30-33; Sf32 tables p.121, p.171; Table 4.2 p.61 |
| 5 | `VADDSETSPS`: add and sign mask in one instruction | **True, with a semantic trap.** `zmm1 = zmm2 + Sf32(zmm3/mt)` and `k1[n] = sign bit of the sum` (it is the raw sign bit, "as opposed to the result of comparison with zero"). So `-0.0` sets the bit and a NaN may. The write-mask `k1` is both the input predicate and the output (bits for masked-off lanes keep their value). No AVX-512 equivalent: [knowledge] you need `VADDPS` then `VCMPPS` (or `VPMOVD2M`/`VFPCLASS` in later parts). | p.120-122 |
| 6 | Gather within 1-2 cache lines is faster on KNC (line-oriented) than on KNL | **KNC half true, KNL half unverified.** The manual says each element touches one 64-byte region and that "depending on the implementation" one access serves all elements in a line (4.5.3, p.62; p.300). Our card data confirm it: 15 cycles latency and 7 per gather when all 16 lanes share a line; ~127 per core for 16 distinct lines **[card]**. [knowledge] KNL gathers are also line-aware (they merge same-line elements) but I cannot give the ratio, and no KNL data exist in this repo. Do not state "faster than KNL" as fact. | p.62, p.300; `knc-characterization.md` p.30, 146-149 |
| 7 | `VEXP223PS` vector exp2; ER has `VEXP2PS`, F has none | **True, but the input is not floating point.** The instruction maps an **int32 fixed-point value (8 integer bits, 24 fraction bits)** to FP32 with **0.99 ulp** relative error. A float `exp2` is the two-instruction sequence `vcvtfxpntps2dq` (exponent adjust 24) then `vexp223ps`. Overflow and underflow ride on the saturation of the convert; NaN becomes 1.0 and tiny inputs give 1.0. Domain is about [-128, 128) since only 8 integer bits exist. [knowledge] `VEXP2PS` in ER is 2^-23 relative on FP input. | p.190-192; `knc-conversions.md` p.61 |
| - | `VLOG2PS`, `VEXP223PS`, `VRCP23PS`, `VRSQRT23PS` are approximations | **Yes, all four.** Documented bounds: rcp 0.912 ulp, rsqrt 0.775 ulp, exp2 0.99 ulp, log2 4 ulp outside [0.5, 2] and absolute error < 2^-21 inside. All four treat input denormals as zero and flush tiny results, and the log/rcp/rsqrt forms accept no memory conversion. They are "23" because they are near full FP32 precision, but none is correctly rounded. | pp.190, 373, 577, 588 |

Corrections to the claim set: items 2 and 3 describe the *same* operand pattern (scale at index
`g+1`, bias at `g+0` of the third operand, applied to the second); VLOG2PS has no memory form with
conversion; and "no INT8 dot product" is correct but understates that `VPMADD231D` with `{sint8}`
or `{sint16}` loads is the closest IMCI has.

## 2. What GCC-KNC already does (checked in `.work/_shared/gcc`, branch `knc`, and docs)

- **`vrcp23ps`, `vrsqrt23ps`**: used. They are the seeds of the correctly rounded division and
  square root sequences (`imci.md` `knc_div_rcp`, `knc_sqrt_rsqrt`, ADR-0003 point 4, S5-03,
  `knc-div-sqrt.md`). Approximate forms alone stay opt-in (ADR-0003 point 5). Measured latency 6
  **[card]**.
- **`vlog2ps`, `vexp223ps`**: not used anywhere. The only hits are `knc-div-sqrt.md` p.73-74, which
  dismisses both for division and square root. `contrib/knc-vecmath/` (the PhiWeather `expf`,
  `logf`, `powf`, ADR-0011, E7-01/02) is built from Arm's `expf` table algorithm, not from these
  instructions.
- **`vfmadd233ps`, `vpmadd231d`, `vpmadd233d`, `vaddsetsps`**: not used, no pattern.
- **Integer multiply-add**: `imci.md` has `vpmulld` and `vpaddd` as separate patterns (lines
  612-630); no combine to `vpmadd231d`.
- **FMA**: `*knc_fma<mode>4` emits only `vfmadd231`, register operands. The 132 and 213 forms,
  the memory operand and the 233 form are not generated.
- **Arithmetic memory operands**: `*knc_<code>v16si3` accepts a plain aligned full-width memory
  source (S4-09). No arithmetic pattern uses `{1to16}`, `{4to16}`, `{float16}`, or a register swizzle
  as an *operand*. Broadcasts exist as separate `vbroadcastss` and `vbroadcast*x4` loads.
- **Up-converting loads**: used. `{uint8}`, `{sint8}`, `{uint16}`, `{sint16}` and `{float16}` appear in
  `vmovaps`/`vmovdqa32` load patterns (S5-16, `knc-conversions.md` section on vectorizer tables),
  plus `vloadunpack`, `vgmin/vgmax`, `kxor/kxnor`, `vcvtfxpnt*`. E4-07 covers the rest.
- **Gather**: costed by lines touched (about 7 per core per line, 15 latency for one line,
  `knc-costs.md`), scattered gather rejected by a T1 check; E4-02 is the lowering.
- **Memory operand latency 12 [card]**: so folding a load into an arithmetic op saves
  an instruction and a register, not latency (the dependent chain still waits for the load).

## 3. How to exploit the true ones (recommendations)

Ranked by value over risk. "Card first" means a measured latency/throughput row is needed before
the cost entry (ADR-0010); do not ask the card for it until the owner lifts the hold.

1. **`VPMADD231D` for `a*b + c` on `V16SI` (cheapest win).**
   - Mechanism: a combine define_insn `(plus (mult a b) c)` in `imci.md`, tied addend like
     `*knc_fma` (231 destroys `c`), next to the existing `vpmulld`/`vpaddd` patterns. No flag gates
     it: both sides are modular int32, so it is exact. Also fires from the vectorizer's `MULT_EXPR` plus
     `PLUS_EXPR` with no new recognizer. `vpmadd231d` also takes a memory/`{sint8}`/`{sint16}` third
     operand, so the same pattern with a widening load covers 8/16-bit weights (E4-07).
   - Benefit: one op instead of two on an in-order, one-issue-per-cycle vector pipe; also lowers
     register pressure on integer indexing (flat 2-D/3-D index math, `(j*nx+i)*4`).
   - Risk: none for values; the only hazard is the tie (one more `mov` when `c` is live).
   - Test: T1 scan that `x[i] = a[i]*b[i] + c[i]` on `int` produces one `vpmadd231d` and no
     `vpmulld`; T3 exact comparison on random and edge (INT_MIN, overflow wrap) values.
   - Card first: latency/throughput of `vpmadd231d` against `vpmulld`+`vpaddd` (cost-model row).
   - Where: Sprint 8 tuning block (new item **E5-14** below), small.
2. **`VEXP223PS` and `VLOG2PS` behind approximate-math options, in the E7 vector library.**
   - Mechanism: not GCC patterns first. Add *relaxed* entry points `__knc_vmath_exp2f_16_relaxed`,
     `__knc_vmath_log2f_16_relaxed`, and the `expf`/`logf`/`powf` relaxed variants, built on
     `vcvtfxpntps2dq` + `vexp223ps` and `vlog2ps` (scale by `log2e`/`ln2` with FMA, fix subnormal
     and out-of-range lanes by masked repair). ADR-0011 already says relaxed entry points are separate
     from accurate ones, so no new name rule is needed. The compiler binds them only under
     `-ffast-math` (more precisely `-funsafe-math-optimizations -fno-math-errno
     -ffinite-math-only`, per ADR-0003 point 5); the default and `-O3` keep the accurate ones.
     An RTL `exp2`/`log2` optab pattern is a second step, only if the library call overhead shows.
   - Benefit: `expf` goes from a table-and-polynomial sequence (about 15+ ops) to about 4 ops
     (convert, `vexp223ps`, range fix); `logf` likewise from a `getmant`+polynomial chain
     to `vlog2ps` + one multiply. This is the part with real upside for WRF-style code.
   - Risk: highest of this list. `vlog2ps` is 4 ulp outside [0.5, 2] and loses relative accuracy
     near 1 (absolute 2^-21, so `log(1+x)` for small `x` is poor, and `powf` that builds on log2
     amplifies the error by `|y*log2(x)|`). Both flush denormals, and `vexp223ps` NaN gives 1.0.
     This is the "relaxed" tier, never default.
   - Test: harness `tests/acceptance/vecmath_qualify/` already exists; add a max-ulp sweep per
     relaxed entry point with documented bounds, special values (0, inf, NaN, denormal, overflow edge
     of the 8-bit integer domain), and a `pow` bound derived from the log2 bound.
   - Card first: yes. The relaxed entry points need measured speed against the accurate ones (and
     the WRF session's correctness bar) before ADR-0011 amendment picks bounds.
   - Where: **E7-02** (relaxed entry points), M4. Not Sprint 8.
3. **`VADDSETSPS` for sign tests of a sum.**
   - Mechanism: a combine pattern `(set zmm (plus a b))` plus `(lt (plus a b) 0)` or
     `signbit(a+b)` into one `vaddsetsps`. A vectorizer-level recognizer is not needed; combine sees
     the two insns inside one basic block after if-conversion. Gate by `-fno-signed-zeros
     -ffinite-math-only`, because the instruction reports the raw sign bit (`-0.0` and some NaNs
     give 1) whereas `a+b < 0` is false for `-0.0`. `signbit(a+b)` needs no gate.
   - Benefit: saves one `vcmpltps` per such select (clamping, ReLU-style `max(a+b,0)` already has
     `vgmax`, so this matters for sign-only tests such as range reduction and bounds checks).
   - Risk: low once gated; semantics of `k1` as an in/out mask must be modelled (the mask register
     is read and written, like the existing `*_flags` volatile patterns).
   - Test: T1 scan plus a T3 sweep on `-0.0`, `+0.0`, NaN, denormal sums.
   - Card first: no; same pipe as `vaddps`. Value is small and speculative, **low priority**.
4. **Memory operand conversions and broadcasts folded into arithmetic (E4-07 extension).**
   - Mechanism: allow `vector_operand` alternatives in the V16SF/V16SI arithmetic and compare patterns
     for `{1to16}` broadcast (`(vec_duplicate (mem))` as an operand), `{4to16}` (for the 4x4 matrix
     work), and `(float_extend/float (mem:V16HF|V16QI|V16HI))` as the memory source, instead of a separate
     `vbroadcastss`/`vmovaps` load. Honour the tables: no `{sint8}` on Sf32, no memory conversion on
     rcp/rsqrt/log/`vcvtps2pd`.
   - Benefit: removes a load instruction and a register per use; **not** latency (memory-operand
     latency is 12, same as the separate load **[card]**). It matters for the in-order front end and
     register pressure, which is the S5-era story on the M2 small-matrix and short-row kernels.
   - Risk: alignment and fault footprint. A `{1to16}` form reads 4 bytes, `{4to16}` reads 16, a
     full-width form reads 64 (must be aligned), so each form needs its own legality
     test; FP16 `{float16}` is exact, and `{uint8}` to float is exact (below 2^24).
   - Test: T1 scans per form and a sweep of 1-byte-before-page-end footprints for each form
     (see `knc-conversions.md` footprint note).
   - Card first: one row (broadcast-operand add vs `vbroadcastss` + `vaddps`, throughput at 4 threads).
   - Where: E4-07, widened (Sprint 8 if room; otherwise S9).
5. **`VFMADD233PS` and `VPMADD233D` (scale-and-bias per 4-group).**
   - Mechanism: no natural GIMPLE shape. It appears in small-matrix, colour or 4-wide interpolation code
     (`out[i] = x[i]*s[i/4] + b[i/4]`) and in a vectorizer SLP form with a 4-lane group sharing scale
     and bias. A pattern recognizer for "FMA whose scale and bias come from `vec_duplicate` of a
     V4SF, with the bias one lane below the scale" is a niche. Not recommended for the compiler.
     Expose as a **builtin/intrinsic only** (`__builtin_ia32_vfmadd233ps`), so hand-tuned
     kernels and the M2 small-matrix references can use it, if the owner wants it.
   - Benefit: real only for AOS/vec4 code; the "10%" is shader-specific.
   - Risk: low (it is a fused FMA, rounding as `vfmadd231ps`), but the scale/bias layout
     (index 1 and 0 of each group) is easy to get wrong.
   - Where: park under E4-07 or the E8-01 llama.cpp work (quantised blocks have a scale and a bias per
     group, which is this shape; check there first, it may justify a recognizer).
6. **Gather cost model (claim 6).** Nothing new to build: the line-aware cost (7 per line) is already
   in `knc-costs.md`. Add a line-clustering case to E4-02's vectorizer test (indices that stay in 1-2
   lines should stay vectorized, which the current cost already allows), and do not write a KNC vs
   KNL comparison anywhere.
7. **`vfmadd132/213`, memory-operand FMA (side finding, not in the claims).** The FMA pattern is
   `vfmadd231` only. Adding the 132/213 alternatives lets the allocator tie either multiplicand
   instead of the addend, which removes copies in reductions; ties to E5-05 (scheduler). Worth one
   T1 scan on the M2 kernels before deciding.

## 4. Proposed backlog text (style of `knc-optimization-sources.md` section 3)

For the lead to add if accepted; I did not edit `docs/BACKLOG.md`.

- **E5-14 (Standard, Sprint 8 tuning block, depends on E5-01 row)**: Integer multiply-add. A
  `vpmadd231d` combine pattern for `V16SI`, with a `{sint8}`/`{sint16}` widening-load alternative
  once E4-07 lands. T1 scan, one exact T3 sweep including wrap-around. Card row: `vpmadd231d` against
  `vpmulld`+`vpaddd`.
- **E4-07, extended (Standard)**: fold `{1to16}`, `{4to16}`, `{float16}`, `{uint8}`, `{uint16}`, `{sint16}`
  operands into V16SF/V16SI arithmetic and compares; Table 4.2 legality per form; footprint tests.
  One card row for the broadcast operand; not a latency gain, so judge on instruction count and register
  pressure on M2 kernels.
- **E7-02, extended (Deep, M4)**: relaxed entry points built on `vexp223ps` (after `vcvtfxpntps2dq`) and
  `vlog2ps`, bounds documented in an ADR-0011 amendment, bound only under `-ffast-math` (with
  `-fno-math-errno -ffinite-math-only`). Never default. Needs the owner's agreement on the accuracy
  tier before building and a card comparison with the accurate versions.
- **E5-15 (Light, optional)**: `vaddsetsps` sign-test combine, gated by `-fno-signed-zeros
  -ffinite-math-only`; do only if a corpus kernel shows the compare-after-add shape.
- **E4-07 or E8-01 (parked)**: `vfmadd233ps` / `vpmadd233d` as builtins only; revisit with the
  llama.cpp quantisation kernels.
- **ADR-0003 point 5, clarification (no change in decision)**: list `vlog2ps` and `vexp223ps` with
  their documented bounds as approved approximate primitives, next to `vrcp23ps` and `vrsqrt23ps`.

## 5. Open items

- Latency and throughput of `vpmadd231d`, `vexp223ps`, `vlog2ps`, `vaddsetsps` and of an
  arithmetic op with a broadcast or converting memory operand: none measured; these need the card
  (on hold) before any cost entry.
- The AVX-512 and KNL statements are recollection, not checked. Re-verify before they reach an ADR.
- The 233 forms: not found elsewhere in the manual beyond the pages above.
