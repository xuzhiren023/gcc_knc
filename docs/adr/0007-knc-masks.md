# ADR-0007: KNC masks, compares, blends and masked tails

**Status:** Accepted 2026-11-04, from S4-01 (`docs/research/knc-masks.md`, merged `875c4b0`).
**Decider:** Claude (lead), within Sprint 4 as the owner approved it on 2026-11-04. Citations are
`file:line` in `.work/_shared/gcc` at `knc` `0d3c0152fe3`, and printed pages of Intel 327364-001.

## Context

Sprint 4 makes loops with conditions vectorize (S4-02 to S4-05). GCC 16 needs `vec_cmp`,
`vcond_mask`, `maskload`/`maskstore` and, for masked epilogues, `cond_<op>`, all spelled with a
mask mode. Under KNC today `ix86_get_mask_mode` (`i386.cc:26073`) returns vector masks, because
its scalar-mask branch needs `TARGET_AVX512F`.
- **Hardware:** KNC has `k0`-`k7` (16 bits; 64-bit-element forms use the low 8, p.22), FP
  compares with 8 predicates (3-bit immediate, pp.144-151), integer compares for 32-bit lanes only,
  merge-only masking with no `{z}`, and 2-operand destructive mask logic.
- **S3-03's card probe:** masks never suppress a fault; an unaligned load or store half touches its
  whole line; an aligned access at a 64-byte boundary touches only its line.

## Decision

1. **Mask modes.** `get_mask_mode` returns HImode for V16SF and V16SI and QImode for V8DF and
   V8DI, through one condition term in the existing scalar-mask branch. This amends ADR-0004
   point 2: `k1`-`k7` hold QI as well as HI. Bits 15:8 of a QI mask are undefined. Every 16-bit
   consumer (`kortest`, `jkzd`/`jknzd`, `kmov r32,k`, `kconcat*`) masks or ignores them.
2. **Reuse behind hooks.** The `sse.md` expanders `vec_cmp`, `vec_cmpu`, `vcond_mask`, `maskload`,
   `maskstore`, `cond_fma*`, `cond_<plusminus>`/`cond_mul`, `abs`/`neg` and integer
   `smin`/`smax`/`umin`/`umax` serve KNC through ADR-0006 forms. Each widened condition tests the
   mode (`ix86_knc_packed_mode_p` or narrower), never a bare `|| TARGET_KNC`, because these
   iterators have ungated 128- and 256-bit entries. An iterator that insns also use gets an
   expander-only KNC copy (the `VMOVE_KNC` precedent), not a widened entry.
   `ix86_expand_mask_vec_cmp` takes a KNC entry delegation.
3. **New `imci.md` insns.** Compares, blends, masked arithmetic, masked aligned moves, mask logic,
   `kortest`/`jkzd`, `kmerge2l1*`, QI/HI `kmov`, `while_ult`, `fmin`/`fmax` and the V8DI carry
   split are new `*knc_` patterns, in KNC's MVEX encoding. Write-masks use `k1`-`k7` (`k0` means
   "no mask"). A zero else-value costs a `vpxord`.
4. **Memory operands use `Bm`, never `m`.** A packed-mode memory alternative must use the `Bm`
   constraint (`vector_memory_operand`). With `m`, LRA folds a misaligned load into an IMCI
   arithmetic instruction, which faults (S4-09).
5. **FP compares follow C.** EQ is eq, NE is neq, UNORDERED is unord and ORDERED is ord; these are
   quiet. LT and LE signal, as C `<` and `<=` do, and GT and GE are the same with the operands
   swapped. The quiet UNLT, UNLE, UNGT and UNGE are an `ord` compare, a masked `lt`/`le`, then
   `knot`. LTGT is `ord` followed by a masked `neq`. The card must show that a masked-off NaN lane
   raises no invalid flag before anything relies on it; until then those four take the scalar
   path. Under `-fno-trapping-math`, where no flag is observable, UNLT/UNLE/UNGT/UNGE map to
   `nle`/`nlt` with swaps (S4-03, lead-reviewed 2026-11-04); UNEQ and LTGT stay scalar.
6. **V8DI.** Add and sub use the 4-instruction carry sequence (`vmovdqa32 t,a{cdab}`,
   `vpaddsetcd t,kc,b{cdab}`, `vpaddd`, `vpadcd r{kodd},kc,zero`; sub uses the borrow forms).
   `addv8di3`/`subv8di3` already exist in `sse.md:16597` over `VI_AVX2`, so S4-04 uses an ADR-0006
   form there (S3-09's iterator approach), not a second definition. V8DI compares stay off in
   Sprint 4.
7. **Masked tails.** The safety rule: every 64-byte line a masked instruction names holds at least
   one element the scalar program accesses at that point. So:
   - no masked access with an empty mask;
   - no load or store pair under a non-prefix mask;
   - a misaligned masked access is split into guarded aligned halves;
   - a prefix-masked pair issues its high half only when the elements reach the next line.

   The rule lives in the `maskload`/`maskstore` expanders, so the cost model cannot break it.
   (2026-11-08: the profitability part below is superseded by ADR-0009 amendment 1 point 9 and S8-01's
   C6: gather/scatter tails for unknown alignment; the safety rule above stands.)
   Profitability: the KNC term in `finish_cost` asks for a masked epilogue only when every data
   reference is known 64-byte aligned after peeling; otherwise the x87 epilogue stays. Masks come
   from a scalar `while_ult`. `param_vect_partial_vector_usage` stays 0 (no fully masked main
   loops). Masked epilogues need `cond_<op>` for every FP operation (`-ftrapping-math`).
8. **Budget.** S4-01 estimates 47-75 shared lines in 16-20 hunks for S4-02 to S4-05. In the
   ADR-0006 measure (i386 files, S3-22's method) that takes 184 lines in 53 hunks to about
   231-259 lines in 69-73 hunks. S4-01's own figure of 234 measures all of `gcc/`. Lines are
   reported, with no cap (owner, 2026-11-03); ADR-0006 forms are required.

## Consequences

- One mask design serves all four modes, and most of the vectorizer's mask machinery comes from
  `sse.md` without copying it.
- QI masks add a hazard (undefined high byte) that every new mask consumer must handle; reviews
  check it.
- Four quiet FP relations wait for a card check, so some `isgreater`-style loops stay scalar in
  Sprint 4.
- Masked tails appear only for aligned loops. Misaligned loops keep the x87 remainder until the
  split expansion is shown on the card.
