# KNC intrinsics: verified sources (2026-11-10)

Input: a GPT deep-research report on Intel IMCI intrinsics, supplied by the owner, checked
source by source by a lead subagent (web, 2026-11-10). This note keeps what was verified. It
records facts and pointers only, no Intel text. How we may use them is ADR-0013.

## What exists

| Source | URL | Status | Use |
|---|---|---|---|
| Intel C++ Compiler 16.0 guide, KNC intrinsics (mirror at UFRJ NACAD) | https://portal.nacad.ufrj.br/online/intel/compiler_c/common/core/index.htm (TOC `hh_toc.htm`; MIC root `GUID-FC13EE09-8555-414B-8FF2-D7D66CD3975C.htm`) | Verified | The family list: 390 MIC TOC entries, 348 family pages, about 633 base and mask names before `[ext]`/`[_round]` expansion; SVML 97 pages, scalar 6 |
| Intel Xeon Phi ISA manual 327364-001 (Sept 2012) | https://www.intel.com/content/dam/develop/external/us/en/documents/327364001en.pdf; mirror https://www.ece.lsu.edu/gp/refs/xeon-phi-isa-ref-manual.pdf; local `.work/_shared/intel-327364-001-xeon-phi-isa.{pdf,txt}` | Verified | Authority for semantics and encodings: chapter 3 format (3.3 MVEX), chapter 6 instructions, appendix A scalar. 200 "Intrinsic Equivalent" blocks naming 348 distinct `_mm512_` intrinsics |
| Intel Intrinsics Guide data XML, version 3.4.6 (Wayback) | http://web.archive.org/web/20200316191432id_/https://software.intel.com/sites/landingpage/IntrinsicsGuide/files/data-3.4.6.xml (also 3.4.2, 3.4.5, 3.5.x, 3.6.0) | Verified | Machine-readable list: 255 entries tagged KNC, 338 AVX-512/KNC, 2 SVML/KNC (about 595). Has errors: `addsets_ps` sign pseudo-code wrong; `mask2int` mapped to `kmov` though the guide says no instruction |
| Intrinsics Guide release notes | https://www.intel.com/content/www/us/en/developer/articles/release-notes/intrinsics-guide-release-notes.html | Verified | KNC added v3.1 (2013-12-18), removed v3.6.6 (2023-05-10) and v3.6.7 |
| ISPC v1.8.2 `examples/intrinsics/knc.h` (and `knc-i1x16.h`, `knc-i1x8.h`, `knc2x.h`) | https://github.com/ispc/ispc/blob/v1.8.2/examples/intrinsics/knc.h | Verified; BSD-3, (c) 2010-2015 Intel | Real usage: knc.h has 769 uses of 227 distinct `_mm512_*` names; unaligned access through `extloadunpacklo/hi` and `extpackstorelo/hi`; 64-bit gathers grouped by upper 32 bits |
| CERN talk, K.-D. Oertel, "Intel Xeon Phi Programming Models" (2013-04-11) | https://indico.cern.ch/event/238763/attachments/401939/558856/KDO-IntelWorkshopCERN-XeonPhiProgrammingModels.pdf | Verified (slides 63-69 = PDF pages 38-43) | Slide 64: ICC treated intrinsics as bypassing optimization except register allocation. Slide 69's example has bugs |
| binutils K1OM: H.J. Lu 2011 patch; removal in 2.39 | https://sourceware.org/ml/binutils/2011-07/msg00193.html; 2.39 `gas/NEWS` | Verified | Our MPSS binutils 2.22 is the only assembler; current binutils cannot assemble k1om |
| Agner Fog objconv | https://www.agner.org/optimize/objconv-instructions.pdf (section 8.4) | Verified | Independent disassembler for KNC encodings: a cross-check |
| Rahman, "Intel Xeon Phi Coprocessor Architecture and Tools" (Apress 2013, open access) | https://link.springer.com/book/10.1007/978-1-4302-5927-5 | Verified | Chapter 3: vector ISA background |

Of little use for intrinsics: the Colfax boot camp (3 names), Lang's Passau thesis (about 5),
PRACE BPG v2.0 (none; working copy on Zenodo), LRZ 2017 proceedings (10), the UvA SAC paper (none).

## Corrections to the GPT report

- The CERN title is "Programming Models"; slide 69's example is buggy.
- ISA instruction descriptions are chapter 6, not 3.
- ISPC stores use `extpackstorelo/hi`, not plain `packstore`.
- The GCC 5.1.1 KNC fork (our donor) has no KNC intrinsics: stock AVX-512F headers plus three
  inline-asm helpers (`_mm512_swizzle_pd`, `_mm512_reverse_pd`, `_mm512_reduce_mul_pd`). Its
  README's "AVX512 builtins" claim says nothing about IMCI. Confirmed in our local donor tree.
- ICC's prototypes are reached through `immintrin.h`; `zmmintrin.h` is ICC's internal file.

## Facts that shape the design

- Most intrinsics map to one instruction; masked forms merge into the destination's old value.
- Some have no instruction (`_mm512_mask2int` and kin): compiler-generated transfers.
- Some have two results (`_mm512_addsets_ps(v2, v3, &sign)`, VADDSETSPS).
- Some are sequences (unaligned load/store pairs, 64-bit gathers).
- SVML intrinsics are library calls, not instructions; GCC-KNC writes its own vector math (E7-01,
  ADR-0011), never Intel SVML.
- Demand order for a first subset: ISPC's top names (permutevar, extload/extstore, gather/scatter,
  mask ops `kmovlhb`/`kxor`/`kswapb`, compares, swizzles, `extloadunpack*`/`extpackstore*`), and
  what FFTW's KCVI backend calls (not yet counted).

Working files from the check (lead scratchpad, not in git): the guide's TOC with GUIDs, the
decompressed 3.4.6 XML, ISPC counts, PDF text extracts.
