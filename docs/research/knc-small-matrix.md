# Small-matrix kernels: mat8 and mat16 diagnosis (S8-04, E5-11 part 2)

Compiler: GCC `knc` 028f9f3 (after S8-03) for the diagnosis, 800ef2e for the result. Fixture: `tests/acceptance/m2_kernels/kernels.c`
with the `build.py` flags (`-O2 -march=knc -ffp-contract=fast -ftree-vectorize`). Evidence in
`.work/_shared/S8-04/kernels-diag.{s,vect,optinfo}` (assembly, `-fdump-tree-vect-details`,
`-fopt-info-vec-all`), produced by `diag.sh` there.

## What the per-loop reports say

| Kernel | Vectorized loop | Shape | Costs (vector inside / scalar iteration / threshold) |
|---|---|---|---|
| mat8 | row loop `r < count` (count <= 8), V16SF, factor 16 | outer-loop vectorization, whole-loop mask (partial vectors), "alignment unknown, a gather or scatter per access" | 264 / 164 / 2 |
| mat16 | row loop `r < count` (count <= 16), V16SF, factor 16 | outer-loop vectorization, full vectors; x87 scalar loop for count < 16 | 520 / 324 / 16 |

In both, the `j` loop stays inside the vector loop; `x[(base/D)*16+j]` has "zero step in outer
loop", so each inner iteration loads one scalar and broadcasts it.

## What the assembly says (inner `j` loop, one FMA per iteration)

GCC mat16, 12 instructions:

```text
flds (%rdx) ; fstps -4(%rsp) ; vbroadcastss -4(%rsp), %zmm2 ; vpermf32x4 $0, %zmm2, %zmm0
vmovaps %zmm0{aaaa}, %zmm0 ; vloadunpacklps/vloadunpackhps ; vfmadd231ps ; addq ; addq ; cmpq ; jne
```

Hand-written IMCI (`imci.s`, `.Ldot`), 6 instructions:

```text
vbroadcastss (%r9), %zmm1 ; vfmadd231ps (%r8), %zmm1, %zmm0 ; addq ; addq ; subl ; jne
```

GCC mat8, 16 instructions: the same five-instruction broadcast, plus `kmov %k1,%k2`, `vpxord`,
`vgatherdps` with its `jknzd` retry, `vblendmps` (the `.COND_ADD` else-zero), the masked FMA
and the loop control; the store is a `vscatterdps`.

So the broadcast of `x[j]` costs five instructions and a store-to-load round trip
(`fstps` then a dependent `vbroadcastss` from the same slot: spill_reload.lat 12 on the
in-order core) where IMCI uses one memory broadcast. That is half of mat16's loop and a
third of mat8's.

## Why: the lane-use hypothesis does not hold

- M2-final's mat8 was not vectorized at all (the row loop has at most 8 trips, below the
  factor 16, and there was no whole-loop mask yet): GCC ran x87 code, hence 2% of the IMCI
  gain, and S6-06's 10% is the scheduler on that x87 code. S8-02's whole-loop mask vectorized
  it: the lead's paired run measured mat8 at 0.29 of its time before S8-02
  (`CURRENT_STATE.md`, card 2026-11-08 19:04-19:10Z).
- IMCI uses the same 8 of 16 lanes for mat8 (its 16-lane load reads the padded leading
  dimension; the store is 8-lane masked). Lane use is 50%, not the 25% of Tian Fig. 6.4, and a
  rejection would hand mat8 back to x87. Full unroll plus SLP is not available: `count` is a
  run-time value and KNC has no 8-lane FP32 mode.

## Root cause of the broadcast

The vectorizer emits `_12 = *x; vect_cst = {_12, _12, ... x16}`. The CONSTRUCTOR uses the SSA
name sixteen times, so TER does not substitute the load, and `ix86_knc_expand_duplicate`
receives a register: it emits `knc_broadcast_block` (an unspec) and the swizzle.
Combine tries to fold the load into the block (`-fdump-rtl-combine-details`: "Trying 31 ->
33 ... Failed to match") but no pattern takes `(unspec [(mem:SF)] BROADCAST_BLOCK)`. The SF
pseudo is then allocated to x87 and reaches the YJ operand through the S2 reload bridge:
`flds`, `fstps`, `vbroadcastss` from the slot. The expander's memory path
(`*knc_broadcast_memory`, `vbroadcastss m32`) exists but is never reached from the vectorizer.

## Fix (green step)

Emit the register broadcast as one `(set (reg:V16SF) (vec_duplicate:V16SF (reg:SF)))` insn
(`define_insn_and_split`, split at split1 before register allocation into block and swizzle
so both stay independently allocated, as the imci.md comment requires). Combine then folds a
single-use load into the existing `*knc_broadcast_memory`. Expected inner loops: mat16 12 -> 8
instructions with no store-to-load round trip, mat8 16 -> 12; V8DF gets `vbroadcastsd m64`.
No shared i386 line; imci.md and i386-knc.cc only. The scalar_to_vec cost entry
(`CEIL (12, density)`, modelling the bridge) is left as it is in this ticket.

Red scan: `tests/t1/knc-broadcast-load.c` (mat8, mat16 and an FP64 mat8 shape). The positive
scan wants a `vbroadcasts[sd]` from a non-stack base (any displacement or index); the loop
scans forbid only the bridge (an x87 store to `(%rsp)`, a `vbroadcasts[sd]` from `(%rsp)`,
`vpermf32x4`), because mat16's count < 16 remainder (`fldz`, `flds (%rax)`,
`fstps (%r10,%rsi,4)`) and mat8_f64's `fldl`/`fstpl` remainder are legitimate scalar code that
the fix keeps. `check.py` stops at the first failing directive, so every directive was scored
separately (`.work/_shared/S8-04/directives.py`, output in `directives-red.txt` there):

| Directive | knc 028f9f3 | hand-edited .s (bridge replaced by `vbroadcastss (%rdx)`, x87 remainder kept) |
|---|---|---|
| scan-asm-func mat8_f32 | FAIL (not found) | PASS |
| scan-asm-loop-not mat8_f32 | FAIL (2 of 4 loops: `fstps -4(%rsp)`, `vbroadcastss -4(%rsp)`, `vpermf32x4`) | PASS (0 of 4) |
| scan-asm-func mat16_f32 | FAIL (not found) | PASS |
| scan-asm-loop-not mat16_f32 | FAIL (2 of 5 loops, same three) | PASS (0 of 5) |
| scan-asm-func mat8_f64 | FAIL (not found) | PASS |
| scan-asm-loop-not mat8_f64 | FAIL (2 of 5 loops: `fstpl -8(%rsp)`, `vbroadcastsd -8(%rsp)`, `vpermf32x4`) | PASS (0 of 5) |
| scan-asm-not xmm/ymm | PASS | PASS |

The two loops with a hit per function are the inner `j` loop and the enclosing row loop that
contains it.

## Result (GCC `knc` 800ef2e, `kernels-after.s` in `.work/_shared/S8-04`)

| Kernel | Inner `j` loop before | after | Function | Other kernels |
|---|---|---|---|---|
| mat16 | 12 instructions, store-to-load round trip | 8: `vloadunpackl/hps`, `vbroadcastss (%rdx)`, `addq`, `addq`, `cmpq`, `vfmadd231ps`, `jne` | 68 -> 62 | same mnemonic counts |
| mat8 | 16 | 12: the gather pair, `vbroadcastss (%rdx)`, `vblendmps`, masked FMA, loop control | 66 -> 59 | (register names only) |

mat16's x87 remainder for count < 16 is unchanged. The affine, short and stencil kernels keep
their entry broadcast through x87 and a slot: there the scalar has two uses (the vector
broadcast and the x87 remainder loop), so combine does not fold the load; the mnemonic counts
are identical and only register numbers move. The IMCI loop is still 6 instructions: it folds
the broadcast into the FMA's memory operand and needs no `vloadunpack` pair (below).

## What remains after the fix (not this ticket)

- mat8 loads `a[j*16+r]` with a gather: the fixture gives the matrices no alignment, so the
  masked load of unknown alignment is the gather form (S8-02). IMCI relies on the driver's
  64-byte alignment and the padded leading dimension, which the compiler cannot know.
- IMCI folds the broadcast into the FMA's memory operand (`{1to16}` swizzle); GCC keeps a
  separate `vbroadcastss`. A later pattern could take `(vec_duplicate (mem))` as an FMA operand.
- `vblendmps` per iteration from `.COND_ADD`'s else-zero in the whole-loop-masked chain.
