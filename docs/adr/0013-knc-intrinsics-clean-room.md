# ADR-0013: KNC intrinsics are written clean-room from interface facts

**Status:** Accepted 2026-11-10 (owner: "find a way to implement it in our gcc without violating
any license and intel's own copyright ... update the project guides"). The four points marked
**owner** were the lead's defaults; the owner accepted them the same day ("Yes").
**Input:** `docs/research/knc-intrinsics-sources.md`; a lead subagent's source check and
clean-room guidance (2026-11-10, engineering guidance, not legal advice); backlog E6-05; ADR-0002;
ADR-0011.

## Context

GCC-KNC will offer Intel's KNC (IMCI) `_mm512_*` intrinsics so that existing KNC code (FFTW's
KCVI backend, ISPC-style code, tuned science kernels) builds. Intel's material describes them: the
Intel C++ Compiler 16.0 guide, the ISA manual 327364-001 and the Intrinsics Guide data XML. All are
© Intel. The guide and the manual grant no licence. Intel's website terms of use (§4.1.16, §4.1.17,
§8.1(b), §9.2(b)) forbid text and data mining of its materials, systematic downloading, and
reverse engineering of its software, and they limit documents to informational, non-commercial use.
ISPC's `knc*.h` is BSD-3 (© Intel). GCC's own x86 headers set the precedent: written from Intel's
published specification, under GPL-3.0+ with the GCC Runtime Library Exception.

## Decision

1. **Interface facts may be used; Intel's expression may not.**
   - Usable: intrinsic, type and constant names and values, prototypes (parameter order and
     types, return type), mask and merge behaviour, the mapped instruction, and instruction
     semantics as the ISA manual defines them, written in our own words and code.
   - Never copied anywhere (code, comments, tests, tickets, commit messages, docs): Intel's
     descriptions, parameter text, "Operation" pseudo-code, tables, examples, or the layout and
     comments of ICC's `zmmintrin.h`/`immintrin.h`.
   - Never used: ICC headers, `libsvml` or `libimf` binaries, or their disassembly.
2. **Two roles, kept apart.**
   - An **inventory** ticket records facts only, one row per intrinsic: name, return and
     parameter types, masked or unmasked, merge or zero behaviour, the mnemonic or "sequence" or
     "no instruction", and a provenance reference (ISA manual section and page, ICC guide GUID).
     No sentence or pseudo-code from any source, nothing longer than an identifier.
   - **Implementation** tickets get the inventory and the ISA manual only. They do not read ICC
     headers, ISPC code, or the Intrinsics Guide XML.
3. **Provenance is a reference, never a quote.** Every intrinsic's row and test names its source
   page. Review runs a verbatim check (long word n-grams against the source PDFs and pages) on
   new header text and comments.
4. **Tests are our own and the card decides.** Tests come from the engineer's reading of the ISA
   semantics, including masks, NaN, rounding and unaligned lo/hi pairs, and run on the card. When
   documents disagree (the XML's `addsets` sign, `mask2int` mapped to `kmov`), the ISA manual and
   the card settle it.
5. **The Intrinsics Guide XML is at most an internal checklist** (**owner**; lead default).
   - Allowed: an uncommitted, local name list to check coverage, fetched once.
   - Not allowed: committing any extract of it, or generating headers, docs or tests from its
     text. Its terms forbid mining, and its pseudo-code has errors. Committing an extract needs a
     lawyer.
6. **ISPC is a usage reference.** Its `knc*.h` (BSD-3) tells us which intrinsics real code uses
   and suggests test scenarios. We do not copy its code. If a snippet must ever be copied, it goes
   in its own file under `tests/third_party/ispc/` with Intel's BSD notice intact.
7. **Naming** (**owner**; lead default).
   - The header is `imciintrin.h` in GCC style, included from `immintrin.h` only under
     `-march=knc`, with a one-line `zmmintrin.h` that only includes `<immintrin.h>`, so code
     written for ICC finds it.
   - Under `-march=knc` the AVX-512 headers stay unavailable (ADR-0002), because AVX-512 and KNC
     share names with different meanings.
8. **Licence on new files** (**owner**; lead default): GPL-3.0-or-later with GCC Runtime Library
   Exception 3.1, the same text as GCC's `*intrin.h`. The copyright line is "Copyright (C) 2026
   GCC-KNC contributors", not the FSF's, because nothing is assigned to the FSF.
9. **Trademarks.**
   - Referential and factual only: "provides `_mm512_*` intrinsics for the Intel® Xeon Phi™ x100
     coprocessor (IMCI), source-compatible with code written for the Intel C++ Compiler".
   - Never "Intel ..." as a component name, never "official", "certified" or "Intel-approved", no
     logos.
   - Docs that name Intel carry: "Intel and Xeon Phi are trademarks of Intel Corporation or its
     subsidiaries."
10. **Math stays its own lane.** SVML-like vector math follows ADR-0011: our own code, plus
    permissive sources (MIT, Apache-2.0, BSD) copied with their licences. Never derive anything
    from Intel SVML or `libimf`.
11. **Before any public binary release** (**owner**): a lawyer checks the trademark wording and the
    third-party notices once.

12. **Known answers come from the card, not from Intel examples** (owner question 2026-11-10).
    - Intel's documentation examples are not test sources. They grant no licence, are not
      committed, and do not state results; the reference was ICC's output, which we cannot run.
    - Primary check, per intrinsic: the builtin and the same instruction written as inline
      assembly (encoded by the MPSS assembler, independent of our patterns) must agree bit for
      bit on the card, over random inputs and masks.
    - Second check: a scalar C model written from the ISA manual's definition, compared lane by
      lane, including NaN, rounding and edge cases.
    - Corpus: ISPC v1.8.2's self-checking tests through its `knc.h` target (BSD-3) may be used, in
      `tests/third_party/ispc/` with Intel's notice kept and our changes marked. FFTW's own test
      suite (GPL) is the end-to-end check for E6-05d.

## Consequences

- The intrinsics work is an inventory first, then implementation, the same order the source check
  recommended. It costs more than mechanically generating a header from the XML, and it avoids
  shipping Intel's expression.
- Engineers follow the short form of this ADR in `AGENTS.md` ("Third-party material").
