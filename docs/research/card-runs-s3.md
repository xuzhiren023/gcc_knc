# Card runs, Sprint 3

All jobs were run by the lead through `tools/card_run`, under the shared card rules. They used
cores 30-59 (logical CPUs 121-240), and boot ID `e9bfb0ab-e90a-4a5e-9df4-2899a9fd93a4` was
unchanged. No timing figures are given: the ledger shows another agent's jobs overlapping.

## 2026-11-03 evening (UTC 00:15-00:30 on 11-04)

The compiler was the shared GCC 16 build. The vector copy checks used S3-06's branch build (it
contains S3-04 and S3-05); the FP checks used the merged `knc` at `0da1f525ed2` (S3-06's merge).
The sources are in `tests/acceptance/s3_vec_card/`.

| Program | Flags | Result on the card |
|---|---|---|
| `vec_card.c`: S3-04/S3-05 packed copies, 4 types (aligned, zero, pool constant; unaligned pairs at every element offset of source and destination, with sentinels; pairs flush against unmapped guard pages; vectors live across calls at four stack alignments) | `-O0` | `S3-VEC PASS cases=780 failures=0` |
| same | `-O2` | `S3-VEC PASS cases=780 failures=0` |
| same, `-DBROKEN_ALIGN` (negative control: aligned moves on unaligned addresses) | `-O2` | Segmentation fault, as it must |
| `fp_card.c`: S3-06 V16SF/V8DF add, sub, mul and broadcast-multiply, exact values | `-O0` | `S3-FP PASS cases=8 failures=0` |
| same, plus FMA where fused and unfused differ (`vfmadd` present) | `-O2` | `S3-FP PASS cases=10 failures=0` |
| S2-08's 256 `gcc.c-torture/execute` programs, rebuilt with S3-06's branch build at `-O2 -march=knc` | `-O2`, `-j 30` | 256 of 256 PASS |

Card minutes: about 0.18 in total.

Runner issue: two attempts at the torture job were refused with `unknown process identity in
snapshot: b'PROC\t242373\t\tkworker/u:7\t\t'` while a `gpt61` job ran. The third attempt passed.
S3-17 fixes the cause.

After S3-17 merged (runner fix): `hello` matched, and the same 256 torture programs passed 256 of 256 while a `gpt61` job overlapped.
