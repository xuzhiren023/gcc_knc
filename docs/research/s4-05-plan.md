# S4-05 implementation plan (read at `knc`; R = read, I = inferred)

## Part A: S4-05a, aligned masked epilogues

**1. Decision path and the KNC term.**
- R: the main loop's `finish_cost` sets `m_suggested_epilogue_mode`/`m_masked_epilogue` (i386.cc:26913-27075; fields tree-vectorizer.h:1833-1839). The vectorizer reads them only when the cost model is not unlimited (tree-vect-loop.cc:3093-3099, 3206-3212). `masked_p = 1` overrides param 0 (2082-2083, 3106-3107).
- R: the existing masked-epilogue block (i386.cc:26999-27072) is gated by `ix86_tune_features[X86_TUNE_AVX512_MASKED_EPILOGUES]` (27007). That tune is set only for znver4-6 and C86 (x86-tune.def:667-668), so KNC never reaches it.
- **Term (one shared line):** at i386.cc:27007, use `&& (ix86_tune_features[X86_TUNE_AVX512_MASKED_EPILOGUES] || ix86_knc_masked_epilogue_p (loop_vinfo))`. This keeps the upstream avoid logic: pow2 known remainder, outer-loop RAW, fold-left reductions. The helper goes in i386-knc.cc. It returns true only if all of these hold:
  - `TARGET_KNC && ix86_knc_packed_mode_p (loop_vinfo->vector_mode)`;
  - `LOOP_VINFO_PEELING_FOR_ALIGNMENT (loop_vinfo) == 0`;
  - `!LOOP_REQUIRES_VERSIONING_FOR_ALIGNMENT (loop_vinfo)`;
  - for every `dr` in `LOOP_VINFO_DATAREFS`, with `dr_info = loop_vinfo->lookup_dr (dr)` and `stmt = dr_info->stmt`: skip the DR if `!STMT_VINFO_RELEVANT_P` or the step is zero (invariant). Otherwise return false if `STMT_VINFO_GATHER_SCATTER_P`, `STMT_VINFO_STRIDED_P`, `dr_misalignment (dr_info, STMT_VINFO_VECTYPE (stmt)) != 0`, or `!known_eq (DR_TARGET_ALIGNMENT (dr_info), 64)` (accessors tree-vectorizer.h:2145-2210; grouped handling tree-vect-data-refs.cc:1337-1380).
- **Finding (R), why the peel count must be 0:** if the main loop peeled for alignment, every epilogue DR gets unknown misalignment (PR 92351, tree-vect-data-refs.cc:1512-1522). Its masked accesses then reach the expander misaligned, and S4-03's ×1000 term (i386.cc:26802-26806) rejects the epilogue. So the ticket's example "aligned after the vectorizer's peel" cannot work without a generic change. Cases that do qualify (known aligned, no peel): global arrays (decl alignment forced, 1612-1640), `aligned(64)`, and `__builtin_assume_aligned`.
- R: plain `-O2` is very-cheap: no peeling (tree-vect-loop.cc:1846) and no epilogue vectorization (3082). `-O2 -ftree-vectorize` uses cheap (opts.cc:1440-1446), which allows both.

**2. `while_ult`.**
- R: the optab is `while_ult$a$b` (optabs.def:118). For an integer mask mode, operand 3 is a CONST_INT lane count (internal-fn.cc:4111-4120; md.texi:7563-7583): op0 = mask (`n`), op1/op2 = scalar `m`, unsigned compare.
- R: `vect_verify_full_masking` (tree-vect-loop.cc:999-1103) scans the integer modes upward. `can_produce_all_loop_masks_p` (899-910) needs `direct_internal_fn_supported_p (IFN_WHILE_ULT, cmp, mask)`, and the scan stops at the first Pmode-wide type. It runs before the AVX-512 style (2386-2387). sse.md has no `while_ult`, so AVX-512 uses the IV compare.
- Mask modes are HI for V16SF/V16SI and QI for V8DF/V8DI (`knc_maskmode`, imci.md:536).
- Design (imci.md): `(define_mode_iterator KNC_WCMP [SI DI])` and `(define_mode_iterator KNC_WMASK [HI QI])`, with `define_expand "while_ult<KNC_WCMP:mode><KNC_WMASK:mode>"` taking 4 operands and condition `TARGET_KNC`. Body:
  1. `r = op2 - op1` in `<KNC_WCMP>`.
  2. Clamp to `L = INTVAL (op3)` with `cmpu`/cmov: when `op1 >= op2`, `r = 0`, else `r = umin (r, L)`.
  3. `m = (1 << r) - 1` in SImode. `r ≤ 16`, so there is no out-of-range shift.
  4. Move `gen_lowpart (HImode, m)` into an HI pseudo with `knc_mask` (imci.md:105) or a plain move, which `*knc_movhi` takes to `kmov k, r32`. For QI, take the QI lowpart of that HI pseudo.
  - It uses no sse.md names.
- I: SI and DI cover every `cmp_type` choice for an `unsigned long`/`int` IV, and QI/HI never satisfy `min_ni_width`.

**3. `cond_<op>`.**
- R: trapping FP operations need `cond_fn` (tree-vect-stmts.cc:6805-6831). The else value is zero (`default_preferred_else_value`, targhooks.cc:2779; used at tree-vect-stmts.cc:7104).
- cond_add/cond_sub: already work (sse.md:2659 with `VFH_KNC`, insn imci.md:734).
- **cond_mul:** sse.md:2749 uses `VFH`, which is AVX512F only (sse.md:392-398). Change it to `VFH_KNC` (one shared hunk). `mul<mode>3_mask` already exists (VF_BHSD includes KNC, sse.md:400-406) and matches `*knc_mul<mode>3_mask` (KNC_FP_BINARY covers mult, imci.md:376).
- **cond_fma:** sse.md:6346 requires `TARGET_AVX512F`. R: the math-opts pass fuses COND_MUL+COND_ADD into COND_FMA only if `cond_fma` is supported (tree-ssa-math-opts.cc:3572-3581, 6610-6621). That makes it optional: without it, m1_affine's epilogue is `vmulps{k}`+`vaddps{k}`, which is correct and still exact (driver.c:14).
  - If added: change the sse.md:6346 condition to `TARGET_AVX512F || ix86_knc_packed_mode_p (<MODE>mode)` and add an imci.md insn that emits `vfmadd231ps zmm{k}` (manual p.220). The zero else needs a `vblendmps` first, so it costs 2 instructions: there is no `{z}` (imci.md:610).
  - Recommendation: cond_mul now, cond_fma deferred.

**4. Epilogue-only masking with param 0 (R).** Yes. i386 sets the param to 0 (i386-options.cc:3176). `masked_p == 1` is honored (tree-vect-loop.cc:2082-2083, 3106-3107), and for an epilogue `USING_PARTIAL_VECTORS_P` becomes true (2104-2110). The AVX-512 masked epilogues already rely on this (i386.cc:27008).

**5. T1 scans (red today), new `tests/t1/knc-mask-tail-O2.c` and `-O3.c`**, options `-O2 -ftree-vectorize` and `-O3`:
- `tail_f32`: global `float a[N], b[N]`, unknown `n`, `a[i] = a[i] + b[i]`. Scans:
  - `\bkmov\s+%\w+,\s*%k[1-7]`
  - `\bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}`
  - `\bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}`
  - `\bjkzd\b`
  - `\A(?![\s\S]*\bfld)`: no x87 remainder.
- `tail_f64`: the same with `vmovapd` and a byte test (`testb`).
- `tail_ptr_f32`: `float *p` of unknown alignment. Keeps `fld`/`fstp`, and no masked `vmov`.
- `tail_mul_f32`: `vmulps[^\n]*\{%k`.

Risks:
- **QI high byte:** `kmov r32,k` copies bits 15:8 (imci.md:136-140; manual KMOV p.95), so `jkzd` must never test a QI mask. `while_ult` QI writes `m ≤ 0xff`, so bits 15:8 are clean.
- **Empty mask:** the epilogue may run with `rem = 0`. The guard stays in the expander (imci.md:663-672), and a T1 counts `jkzd`/`testb` before each masked move.
- At `unlimited` the suggestion is ignored (tree-vect-loop.cc:3094), so Part A cannot be tested there.

## Part B: S4-05b, misaligned masked access

**6. Split design**, replacing the element-wise `else` arm (imci.md:680-702) for `MEM_ALIGN ≥ element size`; keep element-wise below that.
- GPR: `A = addr`, `L0 = A & -64`, `L1 = L0 + 64`, `s = (A & 63) >> log2(e)`.
- `kk = kmov r32, k`; for QI also `kk &= 0xff` (hazard above).
- `m0 = (kk << s) & lanes` and `m1 = kk >> (L - s)`, where `lanes` = 0xffff or 0xff. When `s = 0`, `m1 = 0`.
- **Load:**
  1. `t = 0` (vpxord).
  2. If `m0`: `kmov k',m0; vmovaps (L0), t{k'}`.
  3. If `m1`: `kmov k'',m1; vmovaps (L1), t{k''}`.
  4. The lane sets are disjoint, so both merge into `t`.
  5. `dst = vpermd (idx_s, t)` with `idx[n] = (n + s') & 15`.
- **Store:** `r = vpermd (idx_-s, data)`, then the same two guarded masked stores of `r`.
- Each guard is a GPR `test`/`jz`, which is cheaper than jkzd because `m0`/`m1` are already in GPRs.
- **Permute:** `vpermd` (p.480), because its index vector is a register. `valignd` needs an immediate shift (p.124: `SHIFT = imm8[3:0]`), so it only fits a compile-time-known `s`. For 8-lane modes, rotate dwords by `s' = 2s`.
- Build `idx` as `iota + broadcast (s')` then `vpandd` with `{1to16}` 15, or with an aligned 1 KB table of 16 index rows indexed by `s'·64`.
- **Why every touched line holds an active element:** L0 is accessed only when `m0 ≠ 0`, i.e. some active `j` has `j + s < L`, so `A + j·e < L1`. L1 is accessed only when `m1 ≠ 0`, i.e. some active `j ≥ L − s`. Each aligned `vmov{k}` names exactly one line: F3 `high-end` and F5 `aligned-end` (knc-unaligned-probe.md:213-214). It is never issued with an empty mask, avoiding F4 `aligned-guard` (:215). An active element is one the scalar loop accesses, so its line is mapped. Store lanes outside the mask are never written, so no race is added. No pair under a non-prefix mask is used (F2, :211-212).

**7. Tests.**
- `-O3 -fvect-cost-model=unlimited` skips the ×1000 term.
  - (a) Main-loop masked accesses: if-converted `if (c[i]) p[i] = v` and `sel` loads on `float *p`. Prevent alignment through peeling with `--param vect-max-peeling-for-alignment=0` (params.opt:1274).
  - (b) Masked epilogue on misaligned refs: add `--param vect-partial-vector-usage=1`. When set, it overrides `masked_p` (tree-vect-loop.cc:3118-3119), and the epilogue uses partial vectors (2104-2110).
- T1 scans per mode: `vpermd`, two masked `vmovaps` with `(` addresses, two `jz`/`je` guards, and no `vloadunpack|vpackstore` under `{%k`. The element-wise fallback is kept only for addresses that are not element-aligned. Add one `__attribute__((packed))` T1 that scans it: per-lane `test`/`jz` and no `vpermd`.
- s4_masks: every `o` in 0..L-1 and `n` in 0..65, with a guard page on both sides (ticket), built with those flags.

**Lead decision (I):** after Part B, a runtime-aligned address costs one guarded `vmov` plus `vpermd` and GPR work. Lowering the ×1000 term would let peeled loops get masked epilogues too.
