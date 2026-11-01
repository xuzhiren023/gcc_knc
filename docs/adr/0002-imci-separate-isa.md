# ADR-0002: IMCI is a separate ISA, not a flavour of AVX-512

**Status:** Accepted. **Date:** 2026-11-01. **Decider:** Claude.

## Context

IMCI and AVX-512F both have 512-bit registers and masks, and many mnemonics match.
It is tempting to enable `TARGET_AVX512F` and patch the differences. The donor shows
where that leads: its `-mavx512f` output on an ordinary loop uses `vfmadd132ss`,
`vdivsd` and `vmovups`, which the `k1om` assembler rejects. IMCI also differs in kind:

- `zmm` is the only vector width; there are no `xmm`, `ymm` or scalar FP forms.
- No vector divide or square root.
- Unaligned access needs load and store pairs.
- Gather and scatter must loop until the mask is empty.
- No byte or word vector elements.
- Memory operands have swizzle and up/down conversion forms.
- No direct moves between general and vector registers.

## Decision

1. KNC keeps its own flag, `TARGET_ISA_KNC`. **It never sets `TARGET_AVX512F`, or any
   SSE or AVX flag**, and `-mavx512f` and similar options are rejected on this target.
2. Vector patterns go in a new `gcc/config/i386/imci.md`, gated on `TARGET_KNC`. Patterns
   in `sse.md` are not reused by widening their conditions.
3. V16SF, V8DF, V16SI and V8DI are the vector modes. A KNC-specific predicate makes them
   valid; no AVX-512 check is relaxed to allow them.
4. Shared i386 code changes only where the feature is truly common. Each change is a
   small, separately reviewable commit. S3 starts counting these changes for Gate B.

## Consequences

- The vector backend is new work, written from the ISA manual. The donor does not
  shorten it.
- Mode-generic i386 code that assumes SSE or AVX will show up as ICEs and wrong
  alternatives. That is the cost being measured for Gate B, which decides whether a
  separate backend would have been cheaper.
- Existing `_mm512_*` intrinsics are not inherited. An IMCI intrinsics header is its
  own backlog item (E6-05), driven by real use.
