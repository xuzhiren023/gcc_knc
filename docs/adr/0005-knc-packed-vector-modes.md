# ADR-0005: KNC packed vector modes

**Status:** Accepted 2026-11-03, after S3-01 (`docs/research/knc-packed-modes.md`) and S3-03's card
probe (`docs/research/knc-unaligned-probe.md`). **Decider:** Claude; the owner chose on 2026-11-03
to go past M1's 300 shared lines (point 8). Citations are `file:line` in the
GCC fork `.work/_shared/gcc` at `knc` `80bc88d9f9e`, or the donor `.work/_shared/gcc-donor` at
`93871d7` (prefixed "donor"). Instruction availability was checked by assembling each mnemonic
with the shared `as --march=k1om` on 2026-11-03.

## Context

ADR-0002 point 3 names V16SF, V8DF, V16SI and V8DI as KNC's vector modes; ADR-0004 point 2 keeps
them unadvertised until E3 adds them with their moves. Today:

- GCC 16 admits 512-bit modes only under AVX-512F: `ix86_vector_mode_supported_p`
  (`i386.cc:25177-25199`), the generic part of `ix86_hard_regno_mode_ok` (`i386.cc:21915-21928`),
  and `ix86_preferred_simd_mode`, which returns `word_mode` without SSE (`i386.cc:26001-26002`).
  KNC's early return admits only scalars and XI in `zmm` (`i386.cc:21898-21901`).
- The donor never vectorized: its mode hooks have no KNC case (donor `i386.c:45961-45975`,
  `51711-51714`), and `knc.md` has only scalar modes (donor `knc.md:21-30`). Its one reusable idea
  is the unaligned scalar move through a stack bridge (donor `knc.md:220-264`,
  `i386.c:17801-17857`), which uses a hard-coded `k2` (`i386.c:17819-17822`) that ADR-0004
  point 6 rejects. The donor does not shorten this work.
- `sse.md` already instantiates the standard names for these modes: `mov<mode>`
  (`sse.md:1462-1469`) and `movmisalign<mode>` (`sse.md:1950-1956`) over `VMOVE`
  (`sse.md:286-295`), add/sub (`sse.md:2667-2673`) and mul (`sse.md:2756-2762`) over `VF_BHSD`
  (`sse.md:400-411`), `fma<mode>4` over `FMAMODEM` (`sse.md:6188-6205`), `vec_init` over
  `VEC_INIT_MODE` (`sse.md:29732-29762`), integer `vec_duplicate` (`sse.md:32372-32384`) and
  integer add/sub over `VI_AVX2` (`sse.md:16585-16591`). The generators have no duplicate-name
  check (none in `gensupport.cc`), so a second `movv16sf` in `imci.md` would collide in the
  generated code. There is no FP `vec_duplicate` for these modes, so that name is free.
- `-O2 -ftree-vectorize`, the fixture's flags, selects the cheap cost model (`opts.cc:1440-1446`),
  which does not version loops for alignment. With `x` and `y` misaligned differently, the affine
  loops vectorize only if `movmisalign` exists. M1 therefore depends on the unaligned pair and so
  on the E3-01 probe.
- k1om has no `vmovups`, `vdivps`, `vpaddq`, `vpsubq`, `vpmullq` or `vpsllq`. It has
  `vloadunpack{l,h}{ps,pd,d,q}`, `vpackstore{l,h}{ps,pd,d,q}`, broadcasts from memory and `{1toN}`
  memory operands, `vpermf32x4`, and register swizzles such as `{aaaa}`.
- Shared i386 files carry 251 changed lines (added plus deleted, against `releases/gcc-16.2.0`,
  excluding `imci.md` and `linux-k1om.h`), so 49 of M1's 300 remain. S2-06 added 54.

## Decision

1. **Modes.** Under 64-bit `TARGET_KNC`, exactly V16SF, V8DF, V16SI and V8DI are supported, through
   one predicate used by `ix86_vector_mode_supported_p` and the KNC branch of
   `ix86_hard_regno_mode_ok`. They live in `zmm0`-`zmm31` only, never in mask or general
   registers. No other vector mode is enabled: no 128- or 256-bit modes, no byte, word, HF, BF or
   V4TI modes. XI stays transport-only.
2. **Entry points.** A standard name that `sse.md` already instantiates for these modes stays
   there. KNC enables it by adding `|| TARGET_KNC` to the four modes' entries in that name's
   iterator and to the expander's condition, plus a first-statement KNC dispatch where the body
   would call SSE-only helpers. This is the `movxi` precedent (`i386.md:2388-2397`) and the
   `sync.md` one (`sync.md:424-426`). No `sse.md` `define_insn` condition is widened. S3-01 showed that widening `VMOVE` enables
   `*vmov<mode>_constm1_pternlog_false_dep` without AVX-512 (`sse.md:1536-1546`) and that `VI` exposes
   ternary-logic insns and splits (`sse.md:19036-19064`, `19350-19440`), so moves and integer logic
   use expander-only iterators. Every
   instruction pattern for these modes is a `*knc_` insn in `imci.md` under `TARGET_KNC`, with
   KNC constraints (`YJ`), printing `zmm` with `%g`. A name `sse.md` does not instantiate for these
   modes (FP `vec_duplicate`) goes only in `imci.md`. If widening an iterator entry would enable
   any `sse.md` insn under KNC, that name gets an expander-only iterator instead.
3. **Instruction mapping.**

   | Operation | V16SF | V8DF | V16SI | V8DI |
   |---|---|---|---|---|
   | aligned load, store, copy | `vmovaps` | `vmovapd` | `vmovdqa32` | `vmovdqa64` |
   | unaligned load (pair) | `vloadunpacklps` + `hps` | `lpd` + `hpd` | `ld` + `hd` | `lq` + `hq` |
   | unaligned store (pair) | `vpackstorelps` + `hps` | `lpd` + `hpd` | `ld` + `hd` | `lq` + `hq` |
   | zero | `vpxord` | `vpxord` | `vpxord` | `vpxord` |
   | broadcast from memory | `vbroadcastss` | `vbroadcastsd` | `vpbroadcastd` | `vpbroadcastq` |
   | add, sub | `vaddps`, `vsubps` | `vaddpd`, `vsubpd` | `vpaddd`, `vpsubd` | none (carry sequence, E4) |
   | mul | `vmulps` | `vmulpd` | `vpmulld` | none |
   | fma (contraction only) | `vfmadd{132,213,231}ps` | `...pd` | none | none |
   | and, or, xor | | | `vpandd`, `vpord`, `vpxord` | `vpandq`, `vporq`, `vpxorq` |
   | divide, square root | none (ADR-0003) | none | none | none |

   A pair is `l` at the address and `h` at the address plus 64. Other constants load from a
   64-byte aligned pool entry with `vmovaps`. A broadcast takes its scalar from memory. A scalar
   in a register is broadcast with `vpermf32x4 $0` and a swizzled `vmovaps`/`vmovapd` (S3-01:
   327364-001 section 2.2.1, tables 2.2/2.3; checked with the assembler, to be checked on the card
   in S3-06).
4. **Unaligned access and tails.** `movmisalign` uses the pair, **but only on element-aligned
   addresses** (amended 2026-11-03). Intel 327364 `VLOADUNPACKLD` (p.361) defines the pair for a
   stream at an "element-aligned address", that is, loads "only element-wise, not vector-wise,
   aligned". A byte-aligned V16SI load segfaulted on the card (`pr65369`, S3-21). Byte-aligned packed
   accesses must not vectorize, and explicit ones take a byte-granular path. S3-03 showed on the
   card that a pair wholly inside mapped memory never faults at any element offset, and that the
   `h` half at a 64-byte
   aligned address touches nothing. It also showed that masks never suppress a page fault and that
   an unaligned half touches its whole line whatever its mask, so masked tails (E4-04) must stay
   inside lines known to be mapped. Peel and remainder iterations are scalar x87
   (E3-05). Partial vectors stay off (`i386-options.cc:3187`), and `ix86_get_mask_mode` is not
   changed in S3 (`i386.cc:26126-26150`). Masked tails are E4-04, designed from E3-01's results.
5. **Vectorizer.** Under KNC `ix86_preferred_simd_mode` returns the 64-byte mode for SF, DF, SI and
   DI, and `word_mode` otherwise. `ix86_autovectorize_vector_modes` stays empty, so one vector size
   is tried (`i386.cc:26087-26121`). Costs stay the generic tables (`knc` is `PROCESSOR_GENERIC`,
   `common/config/i386/i386-common.cc:2221`) until S6. S3 makes no profitability claim.
6. **ABI.** Vector-typed arguments, results and struct members stay an error. The guard in
   `classify_argument` (`i386.cc:2260-2268`) extends from XI to the four modes, and must also run
   before the large-aggregate return (`i386.cc:2286-2295`), which otherwise skips the fields of a
   large struct (S3-01), so a type whose mode becomes V16SF does not start passing in registers. The vector ABI is its own ADR (E7).
7. **Spills.** Packed spills use the 64-byte slots S2-05 proved for XI; `BIGGEST_ALIGNMENT` is
   already 512 for KNC (`i386.h:850-851`).
8. **Code location and budget.** C++ logic for these hooks goes in a new KNC-only file,
   `gcc/config/i386/i386-knc.cc`, with prototypes in `i386-knc.h` included once from
   `i386-protos.h`. Shared files get one-line calls. The M1 count stays the measure above; the
   KNC-only files' size is reported beside it, so M1's comparison sees the whole cost. Allocations
   in shared lines, from S3-01's sketch: S3-04 37, S3-05 11, S3-06 35, S3-07 8, total 91, taking
   the measure from 251 to about 342. The owner chose on 2026-11-03 to go past 300 and let M1
   compare real costs. A ticket that would pass its allocation stops and asks. Integer arithmetic
   (S3-09, about 50 more) has no allocation.

## How they stay out of SSE and AVX patterns

- No SSE, AVX or AVX-512 flag is set (ADR-0002); `-msse*` and `-mavx*` stay rejected.
- `x`, `v`, `k` and `Yk` stay `NO_REGS` on KNC (ADR-0004 point 3), so an `sse.md` insn could not
  allocate even if its condition were true.
- S3-01 audits every insn that uses a widened iterator.
- T1 checks every output against an allowlist: IMCI mnemonics from the table, S2's transfers, x87
  and integer. They reject `xmm`, `ymm`, `vmovups`, `{z}`, suffixed `kmov` and EVEX-only forms, and
  `tools/knc_lint` runs on all of it.

## Consequences

- Turning on `preferred_simd_mode` changes default `-O2` output, where the very-cheap model
  vectorizes loops whose trip count is a multiple of the vector length (`opts.cc:676-677`). That
  ticket is deep and runs the torture sweep.
- M1's shared-line count will be about 342, over its 300 limit by the owner's choice; M1's
  comparison weighs that against a separate backend's estimated cost.
- V8DI is a storage and logic mode in S3. Loops with 64-bit integer add, sub or multiply do not
  vectorize until E4.

## Open questions

1. E3-01: does the `h` half at an aligned address plus 64 touch the next line or page? Do masked
   aligned forms fault on masked-off lanes in an unmapped page?
   **Answered on the card by S3-03 (2026-11-03, `docs/research/knc-unaligned-probe.md`):** at an
   aligned address the high half touches nothing; at an unaligned address each half touches its
   whole line whatever the mask; and masks, even empty ones, never suppress a page fault, for loads
   or stores. Masked tails must stay within lines known to be mapped.
2. S3-01: does widening the `VMOVE`, `VF_BHSD` and `FMAMODEM` entries enable any `sse.md` insn
   under KNC? Does a duplicate standard name fail to build as described?
3. S3-01: is `vpermf32x4 $0` plus the `{aaaa}` swizzle a correct register broadcast for V8DF, given
   that 64-bit swizzles act on 256-bit groups? Until then, broadcasts go through memory.
4. E4: ADR-0004 allows only HI in mask registers. Eight-lane modes need an 8-bit mask held in HI
   with a rule for the high bits.
5. S6: the generic tables price x87 scalar statements with SSE costs (`i386.cc:25714-25730`), so
   S3's vectorization decisions are not tuned.
