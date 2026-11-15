# S12-32: reload ICE on the byte/word extension (pr32243.c)

## Status at red (2026-11-14)

- S12-29 does not change it. The shared build is knc `71e9b2d00fc`, which contains
  `2e70e4115e2`, and `gcc.dg/vect/O3-vect-pr32243.c` still ICEs at plain `-O3 -march=knc`.
- Red test: `tests/t1/knc-convert-byte-register.c`, run by the existing `--byte-word`
  selection. Log: `.work/_state/logs/check_gcc16_t1-20261114-230935.log`.
- Not run at red: GCC build, T0-T2, ICE sweeps, x86. See "Green" below.

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

## Fix

One line in `imci.md`: operand 1's constraint `Bm` becomes `Ba`, S12-29's ordinary
memory constraint with the same alignment test. LRA then copies the register to an
aligned `NO_REGS` slot through `knc_transport_move`'s store alternative, so the store,
its GPR and its mask scratch stay visible.

A survey of `imci.md` found no other operand with a register-capable predicate and a
special-memory-only constraint.

## Green (2026-11-14)

GCC branch `s12/S12-32` on `knc` `71e9b2d00fc`: `f559e49271c` (imci.md, `Bm` -> `Ba`)
and `6b79c6f0566` (sse.md, the two extend expanders). Shared build stamp `6b79c6f0566`.

### Each red case alone, before the fix (lead's point 1)

`cc1` stops at the first ICE, so each function was compiled in its own file at `-O3`
with the pre-fix build (`71e9b2d00fc`). All three abort the same way:

| Function | Insn | ICE |
| --- | --- | --- |
| `cold_u8` | `*knc_zero_extendv16qiv16si2`, source `(reg:V16QI 104)` | `curr_insn_transform`, lra-constraints.cc:4553 |
| `cold_s16` | `*knc_sign_extendv16hiv16si2`, source `(reg:V16HI 104)` | same |
| `masked_local_s8` | `*knc_sign_extendv16qiv16si2`, source `(reg:V16QI 171)` | same |

With `f559e49271c` each compiles and converts from a stack slot
(`-16(%rsp){uint8}`, `-32(%rsp){sint16}`, `48(%rsp){sint8}` and `16(%rsp){sint8}`), and
the red test passes unchanged: `.work/_state/logs/check_gcc16_t1-20261114-232138.log`.

### Under-aligned sources (lead's point 2)

The claim at red, that no single set from under-aligned memory exists, was wrong for
one path, and that path was a second ICE. It does not depend on `Bm` or `Ba`: it fails
in `vregs`, before any constraint is read.

- The shared expanders `extendv16qiv16si2` and `extendv16hiv16si2` (sse.md) took any
  `nonimmediate_operand`. When the load is folded into the conversion
  (`__builtin_convertvector (*p, dwords)` with `p` to an `aligned(1)` vector or a packed
  member), expand emitted `(zero_extend:V16SI (mem:V16QI ... A8))`. The insn condition
  `!misaligned_operand` rejects that, so it was an unrecognizable insn
  (`extract_insn`, recog.cc:2892) at `-O1` and above. `-fno-tree-ter` hid it.
- Red for this: test commit `f422e236`, `under_u8` and `cold_packed_s16`,
  `.work/_state/logs/check_gcc16_t1-20261114-232147.log`.
- Fix `6b79c6f0566`: on KNC the expander forces a misaligned source into a register.
  The move expander then copies it to an aligned slot with exact-size `DImode` moves
  (visible to the optimizer) and combine folds the slot into the extension, so the code
  is one copy and one converting load. Green:
  `.work/_state/logs/check_gcc16_t1-20261114-232741.log`.

Nine probe functions, each compiled alone at `-O3` after both fixes
(`.work/_shared/S12-32/under.c`, one `-DF_<name>` each). Every converting load reads a stack slot:

| Source | Shape | Converting load |
| --- | --- | --- |
| `aligned(1)` V16QI | loop definitions, cold extension | `-64(%rsp){uint8}` |
| packed V16HI member | loop definitions, cold extension | `-120(%rsp){sint16}` |
| `aligned(1)` V16QI | one definition, cold extension | `-16(%rsp){uint8}` |
| packed V16HI member | one definition, cold extension | `-32(%rsp){sint16}` |
| `aligned(1)` V16QI | folded load, hot | `-16(%rsp){uint8}` |
| packed V16HI member | folded load, hot | `-32(%rsp){sint16}` |
| `aligned(1)` V16QI | one definition, call before the cold extension | `16(%rsp){uint8}` |
| packed V16HI member | one definition, call before the cold extension | `32(%rsp){sint16}` |
| `aligned(1)` V16HI by value | stack argument, cold extension | `16(%rbp){sint16}` (the `A256` argument slot) |

In the IRA dumps of the one-definition cases the only `REG_EQUIV` notes are on the
`DImode` copies (`mem:DI ... A8` and the frame slot); no V16QI/V16HI pseudo has a memory
equivalence, and after reload the extension's operand is `mem/c` off `sp` or `bp`. So
there is still no reproducer for extending `ix86_knc_cannot_substitute_mem_equiv_p`, and
it is unchanged. A by-value V16QI argument is not a case: KNC rejects it
("unsupported KNC register ABI mode").

The test keeps two of these (`under_u8`, `cold_packed_s16`) and one file-wide
`scan-asm-not` that no converting load uses a base other than `rsp`/`rbp`.

### Not fixed here: truncating store to under-aligned memory

The mirror expander `truncv16si<mode>2` has the same gap for its destination.
`void f (ubytes *p, dwords v) { *p = __builtin_convertvector (v, bytes); }` with
`ubytes` an `aligned(1)` V16QI is an unrecognizable insn at `-O3`
(`.work/_shared/S12-32/trunc.c -DA`). The packed V16HI member store compiles and goes
through an aligned slot. It is a different pattern from this ticket's and needs its own
red test, so it is left for the lead to ticket.

### Checks

All on the shared build at knc `6b79c6f0566`, host only.

- T0-T2 (`check.py t0 t1 t2 --compiler gcc16`): pass, no FAIL or ERROR line.
  `.work/_state/logs/check_gcc16_t0_t2-20261114-232804.log`.
- Vector sweep (`vect_suite.py --compile-only`): 2001 sources, 1346 compiled, 632
  skipped, 23 compile errors, 0 ICEs. `O3-vect-pr32243.c` compiles. The 23 errors are
  the same files as S12-21's sweep and are all among the 24 compile errors in
  `tests/baseline/gcc16-vect.txt`; the 24th, `pr123525.c`, now compiles. The baseline's
  16 ICE files all compile, and no file that the baseline compiled or linked fails.
  `.work/_state/logs/s12_32_vect-20261114-234048.log`, table in
  `.work/_shared/S12-32/vect.txt`.
- Torture compile sweep (`torture_compile.py`, O0/O2/O2-g/O3): 2003 files, 8012
  configurations, 0 ICEs, hangs, assembler rejections, lint or infrastructure failures.
  Compiler errors 33/32/32/32; against `tests/baseline/gcc16-torture-compile.txt` the
  only difference at every level is `pr108892.c`, which now compiles.
  `.work/_state/logs/s12_32_torture-20261114-234047.log`, lists in
  `.work/_shared/S12-32/torture.txt`.

Not run: x86 identity (sse.md changed; lead), card.

## Open point at red (answered above)

`ix86_knc_cannot_substitute_mem_equiv_p` covers only the scalar transport modes. At red
I argued that no under-aligned V16QI/V16HI equivalence could be built. That holds for
equivalences, but the reasoning missed the folded load in the extend expander; see
"Under-aligned sources".
