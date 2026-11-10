# GCC-KNC flags

ADR-0009 point 8. What to pass, what `-march=knc` already does, and how ICC's `-mmic` flags map.
Card checks C1-C12 are in [knc-characterization.md](research/knc-characterization.md); tickets
are in [work/tickets](../work/tickets/).

## Recommended flags

| Flag | Why |
|---|---|
| `-O2 -march=knc` | The defaults below; `-march=knc` also sets `-mtune=knc`. |
| `-O3` | Adds the dynamic vectorizer cost model (alignment peeling and versioning) and predictive commoning. |
| `-fopenmp` | 4 threads per core is the tuned case (ADR-0009 point 2). |
| `--param knc-threads-per-core=N` | Running 1-3 threads per core: more reduction chains (C7, [knc-costs.md](research/knc-costs.md)) and a longer L1 prefetch distance (C5). |
| `-ffast-math` | Only to match ICC's default FP model; see the last table. |

Do not pass SSE, AVX or MMX options: `-march=knc` rejects them (ADR-0002).

## What `-march=knc` implies

Each default yields to an explicit user setting.

| Default | Evidence |
|---|---|
| Short loops and remainders are masked vector code that never touches an unmapped page (`vect-partial-vector-usage=1`) | C6; [S8-02](../work/tickets/S8-02.md) |
| `-fprefetch-loop-arrays` at `-O2` and above: `vprefetch1` 32 lines ahead (`knc-prefetch-l2-distance`), `vprefetch0` 16 (`knc-prefetch-l1-distance`, halved for many streams) | C2, C5; [S8-03](../work/tickets/S8-03.md), [S8-12](../work/tickets/S8-12.md) |
| No-read streaming stores for write-only loops larger than L2, with a fence after the loop | C1; [S8-13](../work/tickets/S8-13.md) |
| `-O2` vectorizes with the cheap cost model and `-fversion-loops-for-strides` | [S8-09](../work/tickets/S8-09.md) (corpus loops vectorized at `-O2`: 17 to 64) |
| `-malign-data=cacheline`; local arrays of 64 bytes or more start a line | [S8-14](../work/tickets/S8-14.md) |
| Cache parameters: L1 32 KB, line 64 B, L2 256 KB (the DTLB reach, not the 512 KB cache) | C4; [S8-14](../work/tickets/S8-14.md) |
| OpenMP shared blocks and per-thread arrays start their own 64-byte line | C11; [S8-10](../work/tickets/S8-10.md) |
| Vector reduction chains from the thread density: one at the default 4 threads per core, two at 1-3 (`knc-threads-per-core`) | C7; [knc-costs.md](research/knc-costs.md) |
| Unroll a vector loop of at most 16 insns 4 times at `-O2` (`-munroll-only-small-loops`); larger loops and scalar loops as x86 | C9; [S8-15](../work/tickets/S8-15.md) |

`-mtune=knc` (tune flags, all listed in [knc-costs.md](research/knc-costs.md)):

| Default | Evidence |
|---|---|
| No 0x66/0x67-prefixed register forms where a 32-bit form gives the same result | SSDG p.16 (2-cycle decode); [S8-08](../work/tickets/S8-08.md) |
| Functions start on a 64-byte line; loops keep the generic alignment | M2 A/A pairs; [S8-08](../work/tickets/S8-08.md) |
| No tight-loop alignment pass (its nops ran on every outer trip) | m2_mat8 1.105x; [S8-19](../work/tickets/S8-19.md) |

Code shape, not a flag: vector add, sub, mul and FMA read aligned memory and `{1to16}`/`{1to8}`
broadcasts directly ([S8-06](../work/tickets/S8-06.md)); integer multiply-add is `vpmadd231d`
([S8-07](../work/tickets/S8-07.md)). [S8-04](../work/tickets/S8-04.md) and
[S8-05](../work/tickets/S8-05.md) changed no default. C10 (branch mispredict) has not changed the
branch cost yet.

## ICC `-mmic` equivalents

| ICC | GCC-KNC |
|---|---|
| `-mmic` | `k1om-mpss-linux-gcc -march=knc` |
| `-O2` (vectorizes) | `-O2 -march=knc` (cheap model, S8-09); `-O3` for the dynamic model |
| `-qopt-prefetch`, prefetch distances | on by default; `--param knc-prefetch-l2-distance=`, `knc-prefetch-l1-distance=` |
| `-qopt-streaming-stores auto` | automatic beyond L2 (S8-13); off with `-fno-prefetch-loop-arrays` |
| `-qopt-threads-per-core=N` | `--param knc-threads-per-core=N` |
| `-align array64byte` (Fortran) | default (`-malign-data=cacheline`, S8-14) |
| `-unroll=N` | `-funroll-loops`, `#pragma GCC unroll N` |
| `-qopenmp` | `-fopenmp` |
| `-qopt-assume-safe-padding` | not provided (masked tails use aligned masks or gather/scatter) |

**Where GCC-KNC deliberately differs: floating point** (ADR-0003, ADR-0009 point 7). ICC defaults
to `-fp-model fast=1`, which reassociates, contracts and approximates. GCC-KNC keeps IEEE
semantics at every `-O` level: vector division and square root are correctly rounded (FP32; FP64
division stays scalar x87), and no approximation is used without an opt-in. `-ffast-math` is the
nearest match to ICC's default; it also links `crtfastmath`, which flushes subnormals. ICC's
`-no-prec-div` / `-fimf-precision=low` approximate forms are not built yet (ADR-0003 point 5).
`-ffp-contract` is GCC's default (`fast` in GNU C modes, `off` with `-std=c11`).
