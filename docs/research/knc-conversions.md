# S5-02: conversions, and byte and word data, on KNC (ADR-0008 input)

Ticket S5-02 (backlog E4-05 and E4-07). This is a read-only study. GCC was not built, and no
card job was run.

**Sources.** `file:line` refers to the GCC fork `.work/_shared/gcc` at `knc` `c759f17f1b9`.
"p.N" is a printed page of Intel 327364-001 (`.work/_shared/intel-327364-001-xeon-phi-isa.txt`).
On 2026-11-05 the shared K1OM `as --march=k1om` assembled every mnemonic named here, and the
shared GCC 16 `xgcc` produced the vectorizer reports in section 2.3. The probe is
`tests/regress/knc-convert-probe.c` (section 5). Its card results are **not run yet**, so every
"open" item below is still open.

## 1. IMCI conversion forms

### 1.1 The ten forms

IMCI has exactly ten conversion instructions (table of contents, lines 231-240; pp.154-189).
None of them has a 64-bit integer side. Every rounding conversion takes its rounding mode from
the immediate when it has one, otherwise from the `{rn,rd,ru,rz}` register swizzle (EH=1), and
otherwise from MXCSR.RC (precedence on p.63, section 4.6.1; also p.35).

| Form (pages) | Reads | Writes | Rounding | Exp. adjust | Special inputs | MXCSR flags | DAZ / FZ |
|---|---|---|---|---|---|---|---|
| `vcvtdq2pd` (154-156) | int32 lanes 0-7 (register lower half), or 8 from memory (32 B) | 8 doubles | exact | none | none | none | n/a |
| `vcvtudq2pd` (187-189) | uint32 lanes 0-7, as above | 8 doubles | exact | none | none | none | n/a |
| `vcvtps2pd` (184-186) | float lanes 0-7, as above | 8 doubles | exact | none | SNaN quieted (Table 4.1, p.57) | IE, DE | DAZ |
| `vcvtpd2ps` (180-183) | 8 doubles | float lanes 0-7, **lanes 8-15 zeroed** | MXCSR.RC, or `{rX}` swizzle | none | NaN quieted, keeps leading payload bits (Table 6.9) | OE UE IE PE DE | DAZ, FZ |
| `vcvtfxpntdq2ps` (157-160) | 16 int32 | 16 floats | MXCSR.RC, or `{rX}` swizzle | imm8 bits 6:4, divides by 2^0 .. 2^32 | none | PE | n/a |
| `vcvtfxpntudq2ps` (177-179) | 16 uint32 | 16 floats | as above | as above | none | PE | n/a |
| `vcvtfxpntps2dq` (169-172) | 16 floats | 16 int32 | **imm8 bits 1:0** (rn 00, rd 01, ru 10, rz 11) | imm8 bits 6:4, multiplies before rounding | NaN gives 0. Out of range gives "the nearest representable value" (Table 6.7) | IE PE | DAZ |
| `vcvtfxpntps2udq` (173-176) | 16 floats | 16 uint32 | imm8 bits 1:0 | as above | as above (Table 6.8) | IE PE | DAZ |
| `vcvtfxpntpd2dq` (161-164) | 8 doubles | int32 lanes 0-7, **lanes 8-15 zeroed** | imm8 bits 1:0 | none | as above (Table 6.5) | IE PE | DAZ |
| `vcvtfxpntpd2udq` (165-168) | 8 doubles | uint32 lanes 0-7, lanes 8-15 zeroed | imm8 bits 1:0 | none | as above (Table 6.6) | IE PE | DAZ |

Notes, each from the cited page:

- **Lanes.** The widening forms read only the lower 256 bits of a register source
  (`tmpSrc2[255:0] = zmm2[255:0]`, pp.154, 184, 187). Register swizzles permute only within
  128-bit groups (Table 2.2, p.29), so the high 8 lanes reach a widening form only after
  `vpermf32x4 $0xee` (p.482) or `valignd $8` (p.124). The narrowing forms write lanes 0-7 under
  the write-mask, then set `zmm1[511:256] = 0` unconditionally, outside the mask loop (pp.162,
  166, 181). A merge of two narrowed halves is therefore one masked `vpermf32x4 $0x44` (mask
  0xff00) of the second result into the first.
- **Write-mask.** A masked-off lane is neither computed nor written (every form, "Elements in
  zmm1 with the corresponding bit clear in k1 retain their previous values").
- **Memory sources.** The `fxpnt` int-to-float forms accept the full Si32 load-op conversions
  `{uint8}`, `{sint8}`, `{uint16}` and `{sint16}` (p.158). The float-to-int forms accept Sf32,
  which has `{float16}`, `{uint8}`, `{uint16}` and `{sint16}` but **no `{sint8}`** (p.171;
  Table 2.4, p.30). `vcvtdq2pd`, `vcvtudq2pd` and `vcvtps2pd` raise #UD for any memory
  conversion other than `{1to8}` or `{4to8}` (pp.156, 186, 189). The assembler rejects
  `vcvtps2pd (%rax){uint8}` ("invalid vector swizzle"), which agrees.
- **The immediate.** The float-to-int forms document only bits 1:0 (rounding) and bits 6:4
  (exponent adjustment). Bit 7 set "must UD". **Bits 2 and 3 are not described.** The manual
  defines no "use MXCSR" encoding, and `RoundingMode = IMM8[1:0]` is unconditional in all four
  operation sections (pp.162, 166, 170, 174). The assembler accepts `$7`. The probe tests imm
  0-7 under each MXCSR.RC (section 5).
- **Saturation.** The text of all four float-to-int forms says out-of-range values convert "to
  the nearest representable value" and NaN converts to 0. The tables say NaN to 0, +inf to
  INT_MAX, -inf to INT_MIN, and ±0 to 0. The **unsigned** tables 6.6 and 6.8 repeat INT_MAX and
  INT_MIN, which contradicts the text (0 and UINT_MAX would be "nearest"). The manual is
  inconsistent here. `vexp223ps` relies on this saturation (p.190).
- **Flags.** Table 4.1 (p.57) lists the `fxpnt` float-to-int forms with "a NaN operand" as the
  invalid case. **It does not say whether a finite out-of-range input raises IE.** All
  exceptions are masked on KNC, and the flags are sticky and are the OR over all lanes (p.57;
  p.63, "do not trap").
- **Exponent adjustment.** It is exact scaling by a power of two (divide after rounding for
  int-to-float, multiply before rounding for float-to-int, pp.158, 170). With imm8 bits 6:4 = 0
  it is the identity. It is not needed for C casts. A later combine pattern could fold
  `(float) i * 0x1p-16f` into `vcvtfxpntdq2ps $0x40`, but that is out of scope here.

### 1.2 Mapping to C

| C operation | IMCI form | Same as C? |
|---|---|---|
| `(float) int32` | `vcvtfxpntdq2ps $0` (register or aligned memory, EH=0) | Yes. One rounding by MXCSR.RC (p.157). PE as in IEEE. |
| `(float) uint32` | `vcvtfxpntudq2ps $0` | Yes (p.177). x86 without AVX512VL needs a sequence (`sse.md:9046-9056`); KNC needs one instruction. |
| `(double) int32` / `(double) uint32` | `vcvtdq2pd` / `vcvtudq2pd` on lanes 0-7 | Yes. Exact, no flags. |
| `(double) float` | `vcvtps2pd` on lanes 0-7 | Yes. Exact. An SNaN is quieted and raises IE, as an IEEE conversion should. |
| `(float) double` | `vcvtpd2ps` | Yes if MXCSR.FZ and DAZ are clear. They are clear unless `crtfastmath` sets them (S2-15, `-ffast-math` only). |
| `(int) float`, `(int) double` | `vcvtfxpnt{ps,pd}2dq $3` (rz) | Yes for every input C defines. The immediate fixes truncation whatever MXCSR.RC is, so no control-word save and restore is needed. |
| `(unsigned) float`, `(unsigned) double` | `vcvtfxpnt{ps,pd}2udq $3` | Same as above, inputs in (-1, 2^32) included. |

**What a program can observe.**

1. **Undefined casts.** Today's scalar code converts float to int with x87 `fistpl` under a
   forced-truncation control word (the KNC GCC 16 at `-O2`: `fnstcw`, `orb $12`, `fldcw`,
   `fistpl`). For NaN and out-of-range inputs, x87 stores the integer indefinite 0x80000000
   and raises IE in the x87 status word. IMCI stores 0 for NaN and saturates the rest. C11
   6.3.1.4p1 makes these casts undefined, and Annex F.4 leaves the value unspecified (but
   requires "invalid"). So results may differ between the vector body and a scalar peel or
   epilogue of the same loop, which is allowed. **The open fact that matters is the flag:**
   if a finite out-of-range input does not raise IE, then under the default `-ftrapping-math`
   a program testing `fetestexcept (FE_INVALID)` sees a difference. In that case, vector
   fix_trunc should be enabled only under `-fno-trapping-math`, as
   `supportable_indirect_convert_operation` already does for its two-step float-to-int
   (`tree-vect-stmts.cc:14531-14533`).
   `(unsigned) f` is computed scalar as `fistpq` plus the low 32 bits. It wraps negatives at or
   below -1 where IMCI saturates, which is also undefined.
2. **Rounding-mode source.** Scalar int-to-float and double-to-float use x87 `fildl`/`fstps` and
   `fldl`/`fstps`, which round by the x87 control word. The vector forms round by MXCSR.RC.
   glibc's `fesetround` sets both, so only a program that changes one of them directly with
   asm sees a difference.
3. **Flush to zero.** x87 never flushes, while `vcvtpd2ps` honours FZ and DAZ (p.181). This
   differs only under `crtfastmath`, which `-ffast-math` permits.

### 1.3 What has no IMCI form and stays scalar

- int64 or uint64 to float or double, and float or double to int64 or uint64: IMCI has no
  `vcvtqq2pd` and the like, and there is no Si64 or Ui64 conversion (Tables 2.7, 2.11, 2.13,
  pp.31-34). `long` and `long long` casts stay scalar, and so do `vec_pack_float` (V8DI to
  V16SF, `sse.md:9627`) and `vec_unpack_sfix_trunc` (V16SF to V8DI, `sse.md:10181-10227`,
  AVX512DQ).
- int32 to int64 sign or zero extension and int64 to int32 truncation: IMCI has no `vpmov*`.
  These could be built from `vpermd` and shifts, but this ticket does not design them.
  `vec_unpacks_lo/hi_v16si` (`sse.md:22236-22285`) and `vec_pack_trunc_v8di`
  (`sse.md:19566-19576`) stay off.
- Conversions from or to `long double` (x87 only), and `_Float16` and `__bf16` arithmetic. `{float16}`
  exists only as a memory format (section 3), and ADR-0005 has no HF modes.
- A rounding float-to-int that follows MXCSR (`lrint`), unless probe item 2 shows imm bit 2
  selects MXCSR.RC. It is not needed for C casts.

## 2. GCC 16 entry points

### 2.1 What the vectorizer asks for

- **Same lane count.** `vectorizable_conversion` uses modifier NONE when both vector types
  have the same number of lanes (`tree-vect-stmts.cc:5476-5486`), and calls
  `supportable_indirect_convert_operation` (`14505`). That calls
  `supportable_convert_operation` (`optabs-tree.cc:369-411`), which requires both modes to be
  vector modes (`381`) and asks `can_fix_p`, `can_float_p`, `can_extend_p` or `trunc_optab`
  (`385-408`). If that fails, it tries an intermediate integer type, but for FIX_TRUNC only
  under `!flag_trapping_math` (`tree-vect-stmts.cc:14531-14533`).
- **Twice the lanes (WIDEN).** `supportable_widening_operation` maps CONVERT to
  `VEC_UNPACK_LO/HI_EXPR`, FLOAT to `VEC_UNPACK_FLOAT_LO/HI_EXPR`, and FIX_TRUNC to
  `VEC_UNPACK_FIX_TRUNC_LO/HI_EXPR` (`14110-14122`).
- **Half the lanes (NARROW_DST).** `supportable_narrowing_operation` maps CONVERT to
  `VEC_PACK_TRUNC_EXPR`, FIX_TRUNC to `VEC_PACK_FIX_TRUNC_EXPR`, and FLOAT to
  `VEC_PACK_FLOAT_EXPR` (`14355-14376`).
- **Vectorization factor.** With one vector size (ADR-0005 point 5), the factor is the lane
  count of the narrowest element type: 16 for any loop that touches a 4-byte type, and 8 for a
  loop that touches only 8-byte types.

| Case | Modifier | Optabs needed (KNC modes) | VF |
|---|---|---|---|
| (a) `f[i] = i32[i]` | NONE | `floatv16siv16sf2` (`floatunsv16siv16sf2` for unsigned) | 16 |
| (b) `i32[i] = f[i]` | NONE | `fix_truncv16sfv16si2` (`fixuns_truncv16sfv16si2`) | 16 |
| (c) `d[i] = f[i]` | WIDEN | `vec_unpacks_lo_v16sf` and `vec_unpacks_hi_v16sf` | 16 (two V8DF per V16SF) |
| (c) `f[i] = d[i]` | NARROW_DST | `vec_pack_trunc_v8df` | 16 |
| `d[i] = i32[i]` | WIDEN | `vec_unpacks_float_lo/hi_v16si` (`vec_unpacku_float_lo/hi_v16si`) | 16 |
| `i32[i] = d[i]` | NARROW_DST | `vec_pack_sfix_trunc_v8df` (`vec_pack_ufix_trunc_v8df`) | 16 |
| (d) mixed `float` and `double` | WIDEN and/or NARROW | the (c) names, plus mask unpack/pack for if-converted bodies: `vec_unpacks_lo_hi` (`sse.md:22266`), `vec_unpacks_hi_hi` (`22310`), `vec_pack_trunc_qi` (`19578`), all `TARGET_AVX512F` | 16 |

`fix_trunc<v8df><v8si>2`, `float<v8si><v8df>2`, `extendv8sfv8df2` and `truncv8dfv8sf2`
(`sse.md:9548`, `9953`, `10591-10601`) need V8SI or V8SF, which ADR-0005 point 1 forbids. KNC
must therefore reach double through the unpack and pack names, never through the direct
half-width names.

### 2.2 What `sse.md` already defines, and the ADR-0006 handling for each

| Name (KNC mode) | `sse.md` | Kind and condition | Handling under ADR-0006 |
|---|---|---|---|
| `floatv16siv16sf2` | 9023-9034 | **define_insn**, VF1, `TARGET_SSE2 && <mask..> && <round..>` | Named insn, see 2.4 |
| `floatunsv16siv16sf2` | 9046-9056 (insn `*floatuns…` 9036) | expander, VF1 (V16SF `TARGET_AVX512F`, `436-437`) | Expander-only iterator copy plus condition term. The V16SF body is empty, so the RTL is left for an `imci.md` insn |
| `fix_truncv16sfv16si2`, `fixuns_truncv16sfv16si2` | 9159-9168 | **define_insn**, `any_fix`, `TARGET_AVX512F` | Named insn, see 2.4 |
| `vec_unpacks_lo_v16sf` | 10626-10638 | **define_insn**, `TARGET_AVX512F` | Named insn, see 2.4 |
| `vec_unpacks_hi_v16sf` | 10830-10842 | expander with a V8SF temporary | Condition term plus entry dispatch (`vpermf32x4 $0xee` + `vcvtps2pd`) |
| `vec_pack_trunc_v8df` | 11156-11171 | expander, VF2_512_256 (V8DF `TARGET_AVX512F`, `465-466`), V8SF temporaries | Expander-only iterator copy, condition term, entry dispatch. The iterator cannot be widened: `<sse2_avx_avx512f>_cvtps2pd…` (`10603`) and `float<si2dfmodelower>…` (`9548`) are insns over it |
| `vec_unpacks_float_lo_v16si` | 10982-10991 | expander, pattern only: `(float:V8DF (vec_select:V8SI V16SI [0..7]))`, `TARGET_AVX512F` | Condition term only. An `imci.md` `*knc_` insn matches the same RTL (`vcvtdq2pd`). `avx512f_cvtdq2pd512_2` (`9743`) stays under AVX512F |
| `vec_unpacks_float_hi_v16si` | 10968-10980 | expander, V8SI temporary | Condition term plus dispatch (`vpermf32x4 $0xee` then the lo insn) |
| `vec_unpacku_float_lo/hi_v16si` | 11133-11154 / 11084-11107 | expander, x86 bias sequence, `TARGET_AVX512F` | Condition term plus dispatch to `vcvtudq2pd` |
| `vec_pack_sfix_trunc_v8df` | 11226-11241 | expander, V8SI temporaries, `TARGET_AVX512F` | Condition term plus dispatch (two `vcvtfxpntpd2dq $3`, masked `vpermf32x4 $0x44`) |
| `vec_pack_ufix_trunc_v8df` | 11295- | expander, VF2 (V8DF `TARGET_AVX512F`, `450-451`), `TARGET_SSE2` | Expander-only iterator copy, condition, dispatch (`…pd2udq $3`) |
| `<insn>v16qiv16si2`, `<insn>v16hiv16si2` | 24912-24916, 25116-25120 | expander, pattern only, `TARGET_AVX512F` | E4-07 only (section 4). Mode-tested condition term |
| `truncv16siv16qi2`, `truncv16siv16hi2` | 15374-15378 | expander, PMOV_DST_MODE_1 (`15366`, no per-mode condition), `TARGET_AVX512F` | E4-07 only. Mode-tested condition term |
| `vec_unpacks_lo/hi_hi`, `vec_pack_trunc_qi` | 22266, 22310, 19578 | expanders on masks (`kshiftrw`, `kunpckbw` forms), `TARGET_AVX512F` | Only for if-converted mixed-width loops. Defer (section 6) |

The `mask` and `round` substitutions AND their own `TARGET_AVX512F` into every generated
variant (`subst.md:81-84`, and `subst.md:218-221` for `round`). So a
condition term on a base pattern never enables its `_mask` or `_round` copies.

### 2.3 What the KNC GCC 16 does today

`xgcc -march=knc -O2 -ftree-vectorize -fdump-tree-vect-details` on 64-byte aligned global
arrays (`float f[]`, `double d[]`, `int i32[]`, `unsigned u32[]`, `unsigned char u8[]`,
`short s16[]`, N=1024, one loop per function):

| Loop | Result | Vector types chosen |
|---|---|---|
| `f = i32`, `f = u32`, `i32 = f` | "conversion not supported by target" | V16SF and V16SI |
| `d = f`, `f = d`, `d = i32`, `i32 = d`, `d = d * f + 1.0` | "conversion not supported by target" | V16SF or V16SI, and V8DF |
| `i32 = u8` | "conversion not supported by target" | **8-byte** `vector(8) unsigned char` and `vector(2) int` |
| `u8 = i32 & 255` | "conversion not supported by target" | V16SI and `vector(64) unsigned char` (XImode) |
| `f = u8` | "no vectype for stmt" | n/a |
| `s16 = s16 + 1` | **vectorized "using 8 byte vectors"**: SWAR arithmetic in GPRs (`movabsq` masks, `andq`/`xorq`/`addq`) | `vector(4) short` in DImode |
| `i32 = u8 > 7` | not vectorized (unsupported SLP) | 8-byte types |

The byte cases depend on which data reference is analysed first. When the vector size comes
from `unsigned char`, `ix86_knc_preferred_simd_mode` returns `word_mode`
(`i386-knc.cc:71-81`), and `get_related_vectype_for_scalar_type` turns that into 8-byte
"vectors" (`tree-vect-stmts.cc:13588-13603`). When it comes from `int`, the char type gets V64QI
from `mode_for_vector` (`stor-layout.cc:529-536`), and that falls back to XImode. Neither is
usable. The `short` SWAR loop is correct generic code, but it is not IMCI vectorization.

### 2.4 The four named insns

`floatv16siv16sf2`, `fix_truncv16sfv16si2`, `fixuns_truncv16sfv16si2` and
`vec_unpacks_lo_v16sf` are `define_insn`s in `sse.md`, so their names are taken.
`gentarget-def` rejects a second definition (`gentarget-def.cc:276`, seen in S3-11's trunk
build), so `imci.md` cannot define them. Their conditions are false under KNC, so the optabs are
missing, and these are exactly cases (a), (b) and half of (c). ADR-0005 point 2 says "No
`sse.md` `define_insn` condition is widened", and no ADR-0006 form fits an insn: an insn has no
body to dispatch from. Options:

1. **Recommended: a mode-tested KNC term in each of the four insn conditions** (one line each),
   as a narrow exception recorded in ADR-0008, under four rules:
   - an `imci.md` `*knc_` insn matching the same RTL comes first in the file
     (`i386.md:2385` against `30916`). md.texi says "the pattern that appears first in the
     machine description is the one used" (`doc/md.texi:8801-8802`);
   - the `imci.md` predicate accepts a superset of the `sse.md` predicate (`vector_operand` /
     `nonimmediate_operand`), so recog never falls through to the `sse.md` insn;
   - the `_mask` and `_round` variants stay off (2.2);
   - a T1 scan rejects `vcvtdq2ps`, `vcvttps2dq`, `vcvttps2udq` and `vcvtps2pd` with a `%ymm`
     source in compiler *source* output.

   If an `sse.md` insn were ever matched under KNC, its `x`/`v` constraints are `NO_REGS` (ADR-0005,
   "How they stay out"). The result would be an ICE, not AVX code.
2. Turn each named insn into an expander plus a `*` insn upstream-style. That rewrites
   upstream patterns, which ADR-0006 rules 2 and 3 forbid.
3. Enable only the expander names. That leaves (a), (b) and (c) scalar, which defeats E4-05.

## 3. Up and down conversion in memory forms

The rule is section 2.2.2 (p.32) for loads and 2.2.3 (pp.33-34) for stores: "Each source memory
operand must have an address that is aligned to the number of bytes of memory actually accessed
... otherwise, a #GP fault will result". The sizes come from Table 3.3 (p.49) and Table 3.4
(p.50). S3-03 measured a #GP as SIGSEGV with `si_code=128`
(`docs/research/knc-unaligned-probe.md:216`). The write-mask never suppresses a fault (S3-03).

| Form | Conversions | Bytes accessed and required alignment | Semantics |
|---|---|---|---|
| `vmovdqa32 zmm{k}, m{c}` (p.382) | `{uint8}`, `{sint8}` / `{uint16}`, `{sint16}` | 16 / 32 | zero- or sign-extend to int32 (Table 2.9, p.33). No `{1to16}`/`{4to16}` (assembler: "operand size mismatch") |
| `vmovaps zmm{k}, m{c}` (p.379) | `{uint8}`, `{sint8}`, `{uint16}`, `{sint16}` / `{float16}` | 16 / 32 | int to float32. Exact, since \|value\| < 2^24 and no flag is listed. float16 to float32 is exact, ignores DAZ, sets no DE (p.59) |
| `vpbroadcastd`, `vbroadcastss` `{1to16}` (pp.459, 142) | as for the 16-element loads | 1, 2 or 4 (element size) | one element converted and replicated |
| `vbroadcasti32x4`, `vbroadcastf32x4` `{4to16}` (pp.136, 132) | as above | 4, 8 or 16 | four elements converted and replicated ×4 |
| `vloadunpackl/hd m{c}` (pp.349, 361) | `{uint8}` etc. | element size before conversion (Table 3.3, "element level"), **but each half touches its whole 64-byte line** (p.349) | stream at A. The h half is always issued at A+64 (`pointer = mt - 64`) |
| `vmovdqa32 m{k}, zmm{c}` (p.382) | `{uint8}`, `{sint8}` / `{uint16}`, `{sint16}` | 16 / 32 | uint32/sint32 to 8/16 bits. **Saturate or truncate: not stated** |
| `vmovaps m{k}, zmm{c}` (p.379) | `{uint8}`, `{sint8}`, `{uint16}`, `{sint16}` / `{float16}` | 16 / 32 | float to int by MXCSR.RC (Table 2.12 note, p.34). Saturation not stated. float16 keeps denormals and ignores FZ (p.60). Flags O U I P D (p.380) |
| `vpackstorel/hd m{k}, zmm{c}` (pp.405, 417) | as `vmovdqa32` | element size after conversion. A fault reports the line base (p.417) | packed stream at A, h at A+64 |

Answers:

- **Footprint.** An up-converting load of 16 bytes reads only those 16 bytes, which must be
  16-byte aligned, so it can never cross a page. `vmovdqa32 (A){uint8}` at A = page end - 16 is
  therefore safe on paper. The same goes for down-converting stores, so 16 bytes at a 16-byte
  aligned address are page-safe. The probe confirms this at the page end (section 5).
- **Unaligned converted streams** (`vloadunpack`/`vpackstore`). The h half at A+64 touches the
  line after A's line even when the 16-byte stream ends inside A's line. The manual's "will
  always access 64 bytes" (p.349) and S3-03's line rule both predict a fault when that line is
  unmapped, as at A = page end - 16. The probe checks this. A compiler use must issue the h
  half only when `(A & 63) + bytes > 64`, behind a GPR test, as S4-14 does for masked moves.
- **Saturate or truncate.** The manual is silent (pp.33-34, 383, 418), so the probe decides.
  The design below does not depend on the answer: `vpandd` with 0xff (0xffff) before a
  `{uint8}` (`{uint16}`) store gives C's modular truncation under either behaviour, and only
  the AND becomes removable if the stores truncate.
- **Float down-conversion** rounds by MXCSR.RC, not toward zero, so it does not implement C's
  `(unsigned char) f`. Do not use it for C casts.

## 4. Byte and word data in GCC

### 4.1 Candidates

1. **Memory-only V16QI and V16HI modes** (the ticket's `zero_extend:V16SI (mem:V16QI)`).
   `vector(16) unsigned char` then has a vector mode with the same lane count as V16SI, so
   `u8` to `int32` is a NONE conversion through `can_extend_p` (`optabs-tree.cc:396-401`), and
   `<insn>v16qiv16si2` becomes one `vmovdqa32 {uint8}`. `int32` to `u8` is `trunc_optab`
   (`403-408`), which becomes `vpandd` plus `vmovdqa32 {uint8}` when the destination is
   memory. `f = u8` is FLOAT_EXPR of different sizes, so it becomes two steps, extend and float
   (`tree-vect-stmts.cc:14530-14560`). An `imci.md` insn
   `(float:V16SF (any_extend:V16SI (mem:V16QI)))` makes that one `vmovaps {uint8}`, exactly.
2. **`vec_unpacku_lo/hi` on V64QI or V32HI.** These need register byte modes, which IMCI cannot
   operate on: it has no byte or word arithmetic, compares or shuffles (Appendix A list). They
   would be rejected by ADR-0005 point 1 for nothing.
3. **Not at all.** `char` and `short` loops stay scalar, apart from today's accidental SWAR.

### 4.2 What candidate 1 costs against ADR-0005

- **`ix86_vector_mode_supported_p`.** The KNC branch returns `ix86_knc_packed_mode_p`
  (`i386.cc:25122-25123`). It must accept V16QI and V16HI through a **separate** predicate:
  `ix86_knc_packed_mode_p` also gates the shared expanders' conditions
  (`sse.md:1958, 5289, 16615, 17283, 19120`, through `VI_AVX2_KNC` and `VI_KNC`, which list
  V16QI and V16HI unconditionally, `imci.md:34-48`). Widening it would enable byte add, logic
  and compare expanders. Cost: 1 shared line (call `ix86_knc_vector_mode_supported_p`).
- **Register home.** A supported mode needs some register that holds it, or a V16QI pseudo that
  combine fails to fold has nowhere to go: LRA cannot spill a memory-to-memory move with no
  class. The cheapest home is `zmm`'s low 128 bits, with 16-byte aligned transfers like TI's
  (`knc_load_pair`, `knc_store`, `imci.md:160-205`): `ix86_knc_hard_regno_mode_ok`
  (`i386-knc.cc:504-511`) and `ix86_knc_vector_move_mode_p` (`62-66`, which already admits
  V4SF as transport only). No shared lines. A register operand of the extend is then reloaded
  to a 16-byte aligned stack slot. That cost is visible, as AGENTS.md requires.
- **Lane-count pairing.** The default `related_mode` picks the same *size*
  (`targhooks.cc:1611-1625`), which gives V64QI. KNC needs a `TARGET_VECTORIZE_RELATED_MODE`
  that pairs 16-lane modes with each other (aarch64 does the same for unpacked SVE modes). i386
  defines no such hook today, so it costs 2 shared lines (`#undef`/`#define`), and the function
  goes in `i386-knc.cc`, returning `default_vectorize_related_mode` when `!TARGET_KNC`.
  `ix86_knc_preferred_simd_mode` returns V16QI/V16HI for QI/HI (no shared lines). Without
  both, the order effect in 2.3 remains.
- **Hooks that then fire.**
  - `ix86_get_mask_mode` gives V16QI a vector mask, not HI, because only 64-byte data takes the
    scalar-mask path under KNC (`i386.cc:26080-26091`). Char comparisons would therefore mix
    mask kinds. **Keep `char` and `short` compares scalar** and leave the hook alone.
  - `movmisalign` for V16QI/V16HI: leave it off. The vectorizer then peels for alignment or
    stays scalar, which avoids the h-half footprint hazard (section 3).
  - ABI: `ix86_knc_unsupported_abi_type_p` (`i386-knc.cc:154-177`) must reject the new modes, or
    a user `vector_size(16)` char type starts passing in an SSE class. No shared lines.
  - `ix86_set_reg_reg_cost` (`i386.cc:22109-22110`) and the generic cost tables price V16QI
    like a 16-byte SSE mode. This is acceptable until S6.
  - The expanders `<insn>v16qiv16si2`, `<insn>v16hiv16si2` and `trunc<v16si><mode>2` get
    mode-tested KNC terms (3 lines), plus `imci.md` insns.
- **ADR-0005 point 1** ("no byte, word ... modes") must be amended for memory-and-transport
  modes. That is an ADR-0008 decision.

### 4.3 Recommendation

Do E4-05 first, on its own (section 6). Then do E4-07 as **candidate 1, restricted to
widening loads and narrowing stores**: V16QI and V16HI as supported, transport-only modes,
the related-mode hook, extension and truncation through memory forms, and no byte arithmetic,
compares or `movmisalign`. `u8`/`s8`/`u16`/`s16` to int32 and float, int32 to `u8`/`u16`, and
`short` loops whose arithmetic happens in `int` after promotion would then vectorize at VF 16.
`char` compares and `short` arithmetic in `short` (the vectorizer's over-widening pattern
narrows it) would stay scalar or SWAR. That is the smallest design that buys the common
image and sensor loops. If the owner will not amend ADR-0005 point 1 this sprint, keep `char`
and `short` scalar. Nothing in E4-05 depends on E4-07.

## 5. Probe

`tests/regress/knc-convert-probe.c`, about 520 lines, is in the style of S3-03: guard pages
from `mmap` and `mprotect`, `sigsetjmp`/`siglongjmp`, raw `si_code` and `si_addr`, and inline
asm only. The build command is in its header (`-march=knc -O0`). It compiled cleanly on the host
with the shared GCC 16 on 2026-11-05 (`-Wall -Wextra`, no warnings). The lead runs
`knc-convert-probe.mic --native` on the card. Every output line starts with `S5-02`.

| Group | What it settles | Manual |
|---|---|---|
| `special` | `ps2dq`, `ps2udq`, `pd2dq`, `pd2udq` at imm 3 on ±qNaN, sNaN, ±inf, ±0, ±1, -0.75, the min denormal, the INT_MAX/INT_MIN/2^32 boundaries and ±1e10, one value per run (broadcast), so the flags belong to that input. Also checks that the pd forms zero lanes 8-15 | NaN gives 0. Saturation stated, with the unsigned tables inconsistent. **IE for finite out-of-range: open** |
| `rounding` | imm 0-7 × MXCSR.RC rn/rd/ru/rz on ±2.5, ±1.5, ±0.5 for `ps2dq` and `pd2dq` | bits 1:0 stated; **bit 2 ("current"?) open** |
| `int2fp`, `int2fp-expadj` | `dq2ps`, `udq2ps` on ties and inexact values under each RC; imm 0x40 scaling | MXCSR.RC stated; flags stated (PE) |
| `fp2fp-round`, `fp2fp-special` | `pd2ps` rounding under each RC; overflow (2^1000), underflow (2^-1000), exact and inexact float denormals, sNaN, payload qNaN; `ps2pd` on sNaN, payload qNaN, denormal | flags listed; when UE is raised for an exact denormal is not stated |
| `low-half`, `mask-upper` | `dq2pd`, `udq2pd`, `ps2pd` ignore lanes 8-15; `pd2dq`/`pd2ps` under mask 0x0f keep lanes 4-7 and zero lanes 8-15 | stated (pp.162, 181); the pack sequences rely on it |
| `memory` loads | 14 up-converting forms (table in the source) at mid-page (value check), page end - bytes (no fault expected), the guard page with mask 0xffff and 0, and half-misaligned (#GP expected). The `vloadunpackl/hd {uint8}` pair at A = page end - 16 (h at A+64 is in the guard page) and across a line | footprint and alignment stated; **h-half fault for a short stream: open** |
| `memory` stores | 10 down-converting forms, same placements; prints every stored element; `model=saturate/truncate/both/neither` for integer sources; counts bytes changed outside [A, A+bytes) | **saturation open**; float rounding by RC stated |

**Lint finding (tools).** `tools/knc_lint` rejects both the probe's `.s` and its binary. It
assembles the `.s` and decodes it too, and the K1OM `objdump` spells the register source of
`vcvtdq2pd`, `vcvtudq2pd` and `vcvtps2pd` as `%ymm1`. The lint's register rule
(`tools/knc_lint:24, 37`) denies any `%ymm`. The encoding `62 f1 7a 08 e6 c1` is the same
whether the source is written `%zmm1` or `%ymm1`. This is a false positive on correct KNC code,
and E4-05 output will hit it as soon as `vcvtdq2pd` or `vcvtps2pd` is emitted. Before E4-05's
checks, the lint needs an exception for the decoded source operand of these three mnemonics.
For this probe, the lead can accept exactly these three reported lines.

## 6. Recommendation and estimate

### E4-05: int and FP conversions within 32/64-bit elements

**`imci.md` patterns** (about 180 lines):

- `*knc_floatv16siv16sf2`, `*knc_floatunsv16siv16sf2`: `vcvtfxpnt{,u}dq2ps $0`. Memory operand
  aligned and full-width only (`Bm`).
- `*knc_fix{,uns}_truncv16sfv16si2`: `vcvtfxpntps2{,u}dq $3`.
- `*knc_vec_unpacks_lo_v16sf` (RTL as `sse.md:10627-10633`): `vcvtps2pd`.
  `*knc_vec_unpacks_float_lo_v16si` (as `10983-10990`): `vcvtdq2pd`. A uint variant:
  `vcvtudq2pd`.
- `knc_cvtpd2ps_lo`, `knc_cvtpd2{,u}dq_lo`: a V16 result whose lanes 8-15 are zero, described as
  `vec_concat` with a zero V8 half. This is exact (pp.162, 181) and lets the combiner know
  the high half is zero.
- `knc_permf32x4<mode>` with an immediate and a merge mask: `vpermf32x4 $0xee` to move the high
  half down, and a masked `vpermf32x4 $0x44` (mask 0xff00) to merge two packed halves.
- Expanders called by the dispatches below. Their C bodies go in `i386-knc.cc`, about 80
  lines.

**Shared hunks** (`sse.md`, about 37 lines in 11 hunks):

| Name | Lines | ADR-0006 form |
|---|---|---|
| `floatv16siv16sf2`, `fix<u>_truncv16sfv16si2` (one insn), `vec_unpacks_lo_v16sf` | 3 | mode-tested condition term on a named insn: **needs the ADR-0008 exception** (2.4) |
| `floatuns<…>2` | 3 | expander-only iterator copy (`VF1_KNC` in `imci.md`) plus condition |
| `vec_unpacks_hi_v16sf`, `vec_unpacks_float_hi_v16si` | 8 | condition plus entry dispatch |
| `vec_unpacks_float_lo_v16si` | 1 | condition only (an `imci.md` insn matches) |
| `vec_unpacku_float_lo/hi_v16si`, `vec_pack_sfix_trunc_v8df` | 12 | condition plus entry dispatch |
| `vec_pack_trunc_<mode>`, `vec_pack_ufix_trunc_<mode>` (V8DF) | 10 | expander-only iterator copy, condition, dispatch |

**Risks:**

- The named-insn exception is the only new kind of shared change. Review it against x86 with the
  usual x86 check (ADR-0006 rule 5).
- IE on finite out-of-range inputs (probe). If it is not raised, gate fix_trunc on
  `!flag_trapping_math` in the KNC dispatch or condition.
- Scalar and vector results differ for undefined casts (1.2). This is allowed, but a test must
  not compare the two outside the defined range.
- The `vpermf32x4` merge needs a k register for 0xff00. It is visible as a `knc_mask` insn and
  can be hoisted.
- `knc_lint` false positive (section 5).

**Tickets:**

1. **S5-gcc-A: same-width conversions** (a, b and unsigned). The ADR-0008 clause, the four
   insn terms (or two, if `vec_unpacks_lo` waits for B), and `floatuns`.
   - T1 scan: `-O2 -ftree-vectorize` loops `f=i32`, `f=u32`, `i32=f`, `u32=f` each contain
     `vcvtfxpnt…` with `$0x3` for float-to-int, and contain no `fnstcw`, `fistp` or `%ymm` in
     the `.s`.
   - Native: compare every lane against the scalar x87 result for in-range inputs, including
     ties under each `fesetround` mode for int to float. Out-of-range inputs: no comparison,
     only the probe's IE fact, checked once.
2. **S5-gcc-B: float and double widths** (c, d, and int and double). The unpack and pack names,
   `vpermf32x4`, and the zero-high-half insns.
   - T1 scan: `d=f`, `f=d`, `d=i32`, `i32=d`, `d=d*f+1.0` vectorize ("loop vectorized using
     64 byte vectors"). Each has one `vpermf32x4 $0xee` per unpack-hi and one masked
     `$0x44` per pack, and no V8SF/V8SI moves.
   - Native: bit-exact against scalar for (c). For `f=d`, check directed rounding through
     `fesetround`.
3. Mask unpack and pack for if-converted mixed loops (`vec_unpacks_lo/hi_hi`,
   `vec_pack_trunc_qi`) wait for a loop that needs them. Their bodies need KNC mask moves
   through a GPR, because KNC has no `kshiftrw`.

Budget: A plus B together are about 37 shared lines and about 260 KNC-only lines.

### E4-07: byte and word data

**`imci.md` patterns** (about 120 lines): V16QI/V16HI transport (16-byte aligned, low 128 bits
of `zmm`, like TI); `*knc_<any_extend>v16qiv16si2` and `…v16hiv16si2` with memory operand →
`vmovdqa32 {s,u}int8/16`; `*knc_float_extend` `(float:V16SF (any_extend:V16SI (mem)))` →
`vmovaps {…}`; `*knc_truncv16siv16qi2_store` → `vpandd` + `vmovdqa32 {uint8}` (and 16-bit),
the AND dropped only if the probe shows truncation.

**Shared hunks:** about 6 lines in 5 hunks. They are the
`ix86_vector_mode_supported_p` call (1, hook form), `TARGET_VECTORIZE_RELATED_MODE` (2, table
entry), and the three expander condition terms (3, mode-tested condition term). Everything
else goes in `i386-knc.cc`, about 70 lines.

**Risks:**

- The ADR-0005 point 1 amendment.
- Order-dependent vector size until the related-mode hook lands (2.3).
- Unaligned byte streams. Keeping `movmisalign` off makes these loops peel or stay scalar.
- Saturating DownConv (handled by the AND).
- V16QI pseudos that combine leaves unfolded go through a stack slot, which is visible but slow.

**Ticket:**

- **S5-gcc-C: widening byte and word loads and narrowing stores**, after A.
  - T1 scan: `i32=u8`, `i32=s8`, `i32=u16`, `f=u8`, `f=s16`, `u8=i32&255` and `s16=i32`
    vectorize at 64 bytes with one `vmovdqa32`/`vmovaps` `{…}` per 16 elements. `i32 = u8 > 7`
    stays scalar, and no `{uint8}` access is misaligned for its size.
  - Native: values against scalar. One loop with `u8` ending exactly at a page end, under the
    guard-page harness, to prove the footprint in compiled code.
