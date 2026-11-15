# S12-32: reload ICE on the byte/word extension (pr32243.c)

## Status at red (2026-11-14)

- S12-29 does not change it. The shared build is knc `71e9b2d00fc`, which contains
  `2e70e4115e2`, and `gcc.dg/vect/O3-vect-pr32243.c` still ICEs at plain `-O3 -march=knc`.
- Red test: `tests/t1/knc-convert-byte-register.c`, run by the existing `--byte-word`
  selection. Log: `.work/_state/logs/check_gcc16_t1-20261114-230935.log`.
- Not run yet: GCC build, T0-T2, ICE sweeps, x86.

## Root cause

`*knc_<code><mode>v16si2` (`imci.md`) takes its source with predicate
`nonimmediate_operand` but only the special-memory constraint `Bm`. In
`lra-constraints.cc:process_alt_operands` the `CT_SPECIAL_MEMORY` case wins for a
matching MEM or an already spilled pseudo and never clears `badop` for a register,
unlike `CT_MEMORY`. When IRA keeps the V16QI/V16HI pseudo in a zmm register, the only
alternative is refused (reload dump: `Considering alt=0 of insn 169: (0) =YJ (1) Bm`,
`Bad operand -- refuse`) and `curr_insn_transform` aborts at line 4553.

IRA keeps the register whenever the extension is colder than the pseudo's definitions.
In pr32243.c the vector is a constructor of `val` loaded from a stack slot in one block
and extended in a later, colder block of the masked epilogue (r177 costs
`ALL_SSE_REGS:54 MEM:81`). Earlier cases passed only because IRA chose memory.

## Reproducers

- `cold_u8`, `cold_s16`: vectorizer-independent. A loop defines the narrow vector and
  the extension sits under `__builtin_expect (c, 0)`. ICE at `-O1`, `-O2` and `-O3`.
- `masked_local_s8`: reduced from pr32243.c, needs `-O3` (unswitching on `!mask`).

## Planned fix

One line in `imci.md`: operand 1's constraint `Bm` becomes `Ba`, S12-29's ordinary
memory constraint with the same alignment test. LRA then copies the register to an
aligned `NO_REGS` slot through `knc_transport_move`'s store alternative, so the store,
its GPR and its mask scratch stay visible.

A survey of `imci.md` found no other operand with a register-capable predicate and a
special-memory-only constraint.

## Open point for review

`ix86_knc_cannot_substitute_mem_equiv_p` covers only the scalar transport modes. I do
not plan to extend it to V16QI/V16HI: `ix86_knc_expand_vector_move` sends an
under-aligned narrow load through an aligned slot, so no single set from under-aligned
memory exists, and a stack-passed V16HI argument is `A256`. No under-aligned
equivalence could be built, so the guard would be untested.
