# ADR-0008: KNC permutes, reductions, conversions, gather/scatter, FP min/max and byte data

**Status:** Accepted 2026-11-05, from S5-01 (`docs/research/knc-gather-reduce.md`) and S5-02
(`docs/research/knc-conversions.md`). Points 5 and 6 are conditional on the card probes those
tickets wrote (`tests/regress/knc-gather-probe.c`, `tests/regress/knc-convert-probe.c`). The
lead amends this ADR with their results before the gather, scatter, fix_trunc and FP min/max
tickets start.
**Decider:** Claude (lead), within Sprint 5 as the owner started it on 2026-11-05. Citations are
in the two research documents, at `knc` `c759f17f1b9`, and refer to printed pages of
Intel 327364-001.

## Context

Sprint 5 vectorizes the loop shapes that Sprint 4 leaves scalar. Each was confirmed at the
Sprint 4 head:
- conversions ("conversion not supported by target");
- reversed and stride-2 access: `ix86_vectorize_vec_perm_const` returns false for every 512-bit
  mode without AVX-512F;
- indexed access: `ix86_knc_support_vector_misalignment` refuses every gather and scatter;
- byte and word data (no usable vector type).

Integer reductions do vectorize today, but through "reduce using scalar code", which keeps the
vector accumulator in a stack slot for the whole loop. Without `-fassociative-math`, an FP sum
is an in-order fold. It is legal, but costly (the `s5_ops` baseline).

## Decision

1. **Permutes.**
   - KNC gets its own `vec_perm_const`: `ix86_knc_vectorize_vec_perm_const` in `i386-knc.cc`,
     reached by a first-statement `if (TARGET_KNC)` return in `ix86_vectorize_vec_perm_const`
     (ADR-0006 rule 2).
   - The AVX-512 paths stay off. Removing their guard would reach `gcc_unreachable` in
     `expand_vec_perm_even_odd_1` and `expand_vec_perm_broadcast_1`.
   - The classifier tries the cheapest form first: identity, a register swizzle, `vpermf32x4`,
     `vpshufd`, `valignd`, one `vpermd`, and finally `vpermd` plus a write-masked `vpermd` for
     two inputs. Every one-input and two-input selector is covered.
   - `testing_p` must give the same answer the expansion does.
   - For 8-lane modes, `vpermd` uses dword-pair indices (it reads index bits 3:0 only).
   - No swizzled insn carries a rounding override: they share the EH bits.
   - A KNC cost term in `ix86_vector_costs` prices the two-`vpermd` form, so that SLP does not
     pick permute-heavy plans for free.
2. **Reductions.**
   - `reduc_plus_scal`, `reduc_smax/smin/umax/umin_scal` and `reduc_and/ior/xor_scal` are enabled
     for the KNC modes in `sse.md` with a KNC condition term and an entry dispatch to a tree
     builder in `i386-knc.cc`. The tree is `vpermf32x4` plus swizzled-operand adds: 4 steps for
     16 lanes, 3 for 8.
   - V8DI plus uses S4-04's carry sequence.
   - **FP ordering contract (ADR-0003 point 2):** an FP sum is reassociated only where GCC itself
     allows it (`-fassociative-math`). KNC adds no `fold_left_plus`. The in-order fold GCC emits
     otherwise is correct, and its cost is a Sprint 6 cost-model question.
3. **FP min/max.**
   - `MIN_EXPR`/`MAX_EXPR` on V16SF/V8DF map to `vgminps`/`vgmaxps` (`pd`). GCC forms them only
     when NaNs and signed zeros need not be honoured, so the mapping is exact.
   - `fmin`/`fmax` and their reductions are enabled under `!flag_signaling_nans`, with the zero
     sign unspecified as C allows (Annex F.10.9.2 only recommends it), provided the probe's
     `minmax` lines confirm the manual's quiet-NaN rules. The `s4_masks` checks already accept
     either zero sign.
4. **Conversions within 32- and 64-bit elements.**
   - `(float) int32`, `(float) uint32`, `(int) float`, `(unsigned) float`, `(double) float`,
     `(float) double`, and int32 to and from double map to single IMCI instructions. Float-to-int
     uses the `rz` immediate, so no control-word save and restore is needed.
   - Widening reads lanes 0-7, and the high half comes down with `vpermf32x4 $0xee`. Narrowing
     merges two halves with a masked `vpermf32x4 $0x44`.
   - 64-bit integer conversions, and int32/int64 extension and truncation, stay scalar. IMCI has
     no form for them.
   - Under `-ftrapping-math`, vector float-to-int is enabled only if the probe shows that IE is
     raised for finite out-of-range inputs. Otherwise it is gated on `!flag_trapping_math`.
5. **The named-insn exception (amends ADR-0005 point 2).**
   - The scope: `floatv16siv16sf2`, `fix_truncv16sfv16si2`, `fixuns_truncv16sfv16si2` and
     `vec_unpacks_lo_v16sf` are `define_insn`s in `sse.md`. Their names cannot be defined again in
     `imci.md`, and no ADR-0006 form fits an insn.
   - These four insns, and only these, may each get one mode-tested KNC condition term, under
     four rules:
     - (a) an `imci.md` `*knc_` insn matching the same RTL comes earlier in the machine
       description, so it is the one recog uses;
     - (b) its predicates accept a superset of the `sse.md` insn's predicates;
     - (c) the `_mask` and `_round` copies stay off, which they do because `subst.md` ANDs in
       their own `TARGET_AVX512F`;
     - (d) a T1 scan shows that none of `vcvtdq2ps`, `vcvttps2dq`, `vcvttps2udq` or `vcvtps2pd`
       is emitted with an x86 spelling under KNC.
   - Any further insn needs an ADR amendment.
6. **Gather and scatter.**
   - **16-lane** (V16SF, V16SI):
     - `imci.md` defines `mask_gather_load`, `gather_load`, `mask_scatter_store` and
       `scatter_store` with a V16SI offset. These names are free in i386, so there are no shared
       lines.
     - Each expands to one insn whose output is the `vgather…`/`vscatter…` loop closed by
       `jknzd`, with a mask that is not `k0` and is consumed, and an unspec BLK memory reference.
     - `ix86_knc_support_vector_misalignment` accepts gathers and scatters at element alignment.
   - **8-lane** (V8DF, V8DI): through the legacy builtin hooks (`TARGET_VECTORIZE_BUILTIN_GATHER`
     and `_SCATTER`), with entry dispatches in `ix86_vectorize_builtin_gather` and
     `ix86_vectorize_builtin_scatter`. These read the low 8 dwords of a V16SI index, which the
     vectorizer already supports. If upstream removes that path, the fallback is a V8DI-offset
     optab.
   - **Conditions, all from the card probe:**
     - masked-off lanes must neither fault nor touch memory, or only all-ones masks are offered;
     - the index must be scaled at address width, or only scale 1 is offered;
     - with duplicate scatter indices, the highest active lane must win across re-executions, or
       `scatter_store` is left out;
     - a gather or scatter resumed after a page fault must complete correctly, or none of this is
       used.
7. **Byte and word data (amends ADR-0005 point 1).**
   - V16QI and V16HI become supported **transport-only** modes under KNC, through a separate
     predicate, never `ix86_knc_packed_mode_p`. They have no arithmetic, compares or
     `movmisalign`, and their register home is the low 128 bits of `zmm`, like TI.
   - A KNC `TARGET_VECTORIZE_RELATED_MODE` pairs 16-lane modes.
   - Widening loads and narrowing stores use IMCI up- and down-conversion on 16- or 32-byte
     aligned memory. A narrowing store ANDs first, so C's modular truncation holds whether the
     hardware saturates or truncates.
   - `char` compares stay scalar. `ix86_get_mask_mode` is unchanged.
   - The ABI hook rejects the new modes for arguments.

## Order

These are the gcc tickets, one at a time:
- permutes (1);
- reductions (2);
- same-width conversions (4, 5), after S5-05's lint fix;
- float/double-width conversions (4);
- 16-lane gather/scatter (6);
- 8-lane gather/scatter (6);
- FP min/max (3);
- byte and word data (7).

Division and square root follow ADR-0003 and S5-03. Batch checks run after every 2-3 merges.

## Consequences

- Shared i386 lines grow by an estimated 80: about 32 for permutes and reductions, 37 for
  conversions, 12 for 8-lane gather/scatter and 6 for byte data. All are ADR-0006 forms, except the
  four named-insn terms in point 5.
- `s5_ops` is the acceptance fixture for every ticket. Its baseline at the Sprint 4 head is in
  its README.
- The probes must run on the card before the conditional points 3, 4 (flags) and 6 are built.
