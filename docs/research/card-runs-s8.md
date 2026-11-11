# Sprint 8 card results (S8-11 batch check, 2026-11-10)

Lead card run 23:39Z, frozen set `.work/_shared/tmp/claude-s8-11` (SHA beside it), Sprint 8 head
`fe7ed380f149` against Sprint 7 `497bbe8bedf0` (ADR-0010 amendment 2 and point 7; `gcc` over
`gcc_before`, lower is faster).

- Full GCC execute suite at `-O2 -march=knc`: 1,681 of 1,681 pass. M2 negative 1, positive 0.

| Kernel | L2 d1 | L2 d4 | memory d1 | memory d4 |
|---|---|---|---|---|
| mat8 | 0.171 / 0.172 | 0.178 / 0.178 | 0.177 / 0.179 | 0.178 / 0.178 |
| mat16 | 0.333 / 0.337 | 0.312 / 0.315 | 0.351 / 0.352 | 0.358 / 0.350 |
| affine_f32 | 0.272 / 0.336 | 0.770 / 0.775 | 0.599 / 0.596 | 0.687 / 0.685 |
| affine_f64 | 0.334 / 0.297 | 0.728 / 0.721 | 0.600 / 0.601 | 0.688 / 0.690 |
| stencil1 | 0.463 / 0.453 | 0.952 / 0.979 | 0.583 / 0.583 | 0.686 / 0.684 |
| stencil2 | 1.007 / 1.016 | 0.958 / 1.020 | 1.004 / 1.002 | 1.008 / 0.999 |
| short | **1.094 / 1.097** | **1.065 / 1.069** | **1.085 / 1.082** | **1.064 / 1.050** |

Launch 1 / launch 2. Sprint 8 is 1.3x to 5.8x faster on five kernels, flat on stencil2, and 5-10%
slower on short: S8-23. The head measured predates S8-20 (unroll by density), S8-21 (masked-load
prefetch) and S8-22 (`-mphinix` fix); their own pairs are on their tickets.
