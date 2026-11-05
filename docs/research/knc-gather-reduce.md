# S5-01: gather, scatter, permutes, reductions and FP min/max on KNC

Research for backlog E4-02 and E4-06 (`docs/BACKLOG.md:65,69`), input to ADR-0008.
Read only: no GCC build and no card job. The probe in item 6 has not run on the card,
so every hardware statement below is what the manual says, not what the card does.

Sources:

- Intel 327364-001, *Xeon Phi Coprocessor ISA Reference Manual* (Sept. 2012), text at
  `.work/_shared/intel-327364-001-xeon-phi-isa.txt`. Page numbers are printed pages.
- GCC 16 at `.work/_shared/gcc`, branch `knc` (head `c759f17f1b9`, the S4-14 merge). Paths
  below are relative to `gcc/`.
- What GCC 16 does today: host compiles with the shared `xgcc -march=knc` at `-O2` and `-O3`
  with `-fopt-info-vec` and `-fdump-tree-vect-details`, on the loops quoted in 2.3. This
  runs the compiler only; nothing was built.

## Summary

1. All eight gather/scatter forms take **signed 32-bit indices**. The 8-lane forms read the
   **low 8 dwords** of the index register (pp.298, 487, 533, 596). There is no 64-bit index
   form and no 8-element 32-bit vector mode on KNC (ADR-0005).
2. Every form may finish only **a subset** of the active lanes per execution and clears their
   mask bits, so it must run in a `jknzd` loop (p.297). The 8-lane forms zero `k[15:8]`
   themselves (p.298), so `jknzd` is exact for QI masks inside that loop.
3. The manual says a masked-off element never faults (exception tables, pp.299, 302, 597).
   S3-03 found that masks do *not* suppress faults on ordinary moves, so this must be proved on
   the card. The manual says nothing about the state left by a fault on element k.
4. p.301 prints the address as `BASE + SignExtend(VINDEX * SCALE)`. GCC's `gather_load`
   extends first and then scales (`doc/md.texi:7455-7471`). If the card multiplies in 32 bits,
   an `int` index with scale 4 or 8 is not exact. The probe tests this.
5. GCC 16 i386 uses `TARGET_VECTORIZE_BUILTIN_GATHER`/`_SCATTER` (`config/i386/i386.cc:28311-28315`),
   not the optabs. The vectorizer prefers the optabs per data mode when they exist
   (`tree-vect-data-refs.cc:4864`). The AVX-512 patterns cannot be reused: they are single
   instructions with no retry loop, need `TARGET_AVX512F`, and their 8-lane forms use V8SI.
6. **V16SF and V16SI gathers/scatters need no shared change**: the `mask_gather_load*` and
   `*scatter_store*` optab names are free in i386, and the alignment hook is KNC-only.
   **V8DF and V8DI** cannot use the optabs exactly, because the optab needs an offset vector with
   as many lanes as the data (`internal-fn.cc:5484`), and that means V8DI. The exact route is the
   legacy builtin hook, which already handles a V16SI index for 8-lane data
   (`tree-vect-stmts.cc:11126-11150`).
7. Today `a[i] = b[idx[i]]` is refused before any of that: `ix86_knc_support_vector_misalignment`
   returns false for every gather/scatter (`config/i386/i386-knc.cc:97`), which blocks even the
   emulated gather.
8. KNC has no `vec_perm_const` today: `ix86_vectorize_vec_perm_const` returns false for all four
   512-bit modes without AVX-512F (`config/i386/i386-expand.cc:25422-25427`). Reversed loops,
   stride-2 loads and even/odd extraction all stay scalar (2.3). Removing that guard is not safe.
   `expand_vec_perm_even_odd_1` and `expand_vec_perm_broadcast_1` reach `gcc_unreachable`
   for these modes (`i386-expand.cc:24791, 24995`). KNC needs its own hook behind an entry dispatch.
9. Any one-input permute is one `vpermd`, and any two-input permute is `vpermd` plus a masked
   `vpermd`. Swizzles, `vpermf32x4`, `vpshufd` and `valignd` are cheaper special cases.
10. Reductions: no `reduc_*` optab works for KNC, so `int` and `long` sums use "Reduce using
    scalar code". Worse, that keeps the **vector accumulator in a stack slot for the whole loop**
    (2.3). The cheapest 16-lane tree is 2 `vpermf32x4` plus 4 adds with swizzled operands; the
    8-lane tree is 1 `vpermf32x4` plus 3 adds.
11. `float s += a[i]` without fast-math: GCC 16 uses an in-order fold-left reduction at `-O2` and
    at `-O3`. KNC has no `fold_left_plus`, so this becomes an unrolled in-order x87 sum. That is
    correct and keeps ADR-0003. `double` does the same at `-O3`; at `-O2` the cheap cost model
    rejects it.
12. `vgminps` and `vgmaxps` follow GCC's documented `fmin`/`fmax` contract for quiet NaNs. GCC's own
    constant folding (`mpfr_min`/`mpfr_max`) gives the signed zeros that the pseudocode gives. Only
    libm differs (S4-03). `MIN_EXPR`/`MAX_EXPR` map exactly in every case, because GCC forms them
    only when NaNs and signed zeros need not be honoured (`fold-const.cc:6186, 6215, 6230`).

---

## 1. Gather and scatter forms

### 1.1 The forms

| Form | Pages | Lanes | Index dwords read | Conversion | Notes |
| --- | --- | --- | --- | --- | --- |
| `vgatherdps zmm{k}, Uf32(mvt)` | 300-302 | 16 | 15:0 | up-conversion (float16, u/s int8/16) | "SIMD FP exceptions: Invalid" (p.301) |
| `vgatherdpd zmm{k}, Uf64(mvt)` | 297-299 | 8 | 7:0 (`j = 32*n`, p.298) | none | `k1[15:8] = 0` (p.298) |
| `vpgatherdd zmm{k}, Ui32(mvt)` | 484-486 | 16 | 15:0 | up-conversion | |
| `vpgatherdq zmm{k}, Ui64(mvt)` | 487-489 | 8 | 7:0 | none | `k1[15:8] = 0` |
| `vscatterdps mvt{k}, Df32(zmm)` | 598-600 | 16 | 15:0 | down-conversion | |
| `vscatterdpd mvt{k}, Df64(zmm)` | 595-597 | 8 | 7:0 (p.596) | none | `k1[15:8] = 0` (p.596) |
| `vpscatterdd mvt{k}, Di32(zmm)` | 530-532 | 16 | 15:0 | down-conversion | |
| `vpscatterdq mvt{k}, Di64(zmm)` | 533-535 | 8 | 7:0 | none | `k1[15:8] = 0` |
| `vgatherpf0dps Uf32(mvt){k}` | 303-305 | 16 | 15:0 | | prefetch to L1; faults ignored, lane counted done; mask updated, so loop (p.303) |
| `vgatherpf1dps` | 310 | 16 | | | the same into L2 |
| `vgatherpf0hintdps`, `vgatherpf0hintdpd` | 308, 306 | 16, 8 | | | pure hint: may be dropped, never faults, changes no state, not even the mask (p.306) |
| `vscatterpf0dps`, `vscatterpf1dps` | 601, 608 | 16 | | | prefetch with RFO; sets A, not D (p.303) |
| `vscatterpf0hintdps`, `vscatterpf0hintdpd` | 606, 604 | 16, 8 | | | pure hints |

There is no 64-bit-index (`q`) form at all, and no non-hint prefetch for 64-bit elements.
GCC's software prefetching never asks for gather prefetches, so E4-02 does not need the
prefetch forms.

### 1.2 Index width, scale, element order, duplicates

- **Index width.** Indices are signed dwords: the titles say "Signed Dword Indices", and the
  pseudocode sign-extends (`SignExtend(...)`, pp.298, 301). For the 8-lane forms the index is
  `VINDEX[j+31:j]` with `j = 32*n`, n < 8, so the 8-lane forms read the **low 8 dwords** and
  ignore dwords 15:8 (pp.298, 487, 596, 533). So yes: an 8-lane double gather takes 32-bit
  indices.
- **Scale.** The VSIB scale field, SIB bits 7:6, gives 1, 2, 4 or 8 (3.3.1, p.44). Disp8 is
  scaled by the element size before conversion for gathers and after conversion for scatters
  (pp.297, 595).
- **Address arithmetic, which the manual leaves ambiguous.** Every form prints
  `mvt[n] = BASE_ADDR + SignExtend(VINDEX[i+31:i] * SCALE)` (for example p.301). Read literally,
  the product is formed in 32 bits and then extended. GCC's optab contract is the opposite order:
  "extend the offset element to address width … multiply the extended offset by operand 4"
  (`doc/md.texi:7461-7465`, and the same for scatters at `7521-7525`). The two differ whenever
  `|index × scale| >= 2^31`, for example `double` with `int` indices at or above 2^28. The
  probe's `index` group measures it. If the product is 32-bit, a gather is exact only when the
  compiler can prove `|idx × scale| < 2^31`, and item 7 lists that as the top risk.
- **Element order.** The order of gather loads is not specified. The order of scatter stores is
  specified only for overlap: "Writes to overlapping destination memory locations are
  guaranteed to be ordered with respect to each other (from LSB to MSB of the source registers)
  … Writes that are not overlapped may happen in any order … this does not account for
  non-overlapping indices that map into the same physical address" (pp.530, 533, 595, 598).
  Elements must be element-aligned (below), so overlap here means equal addresses.
- **Duplicate indices.** Within one execution the highest lane wins. Across re-executions the
  manual is silent: guarantee (b) only promises that the lowest enabled lane is in each subset
  (p.595). The rule matters to GCC: the vectorizer never checks a scatter against itself
  (`tree-vect-data-refs.cc:451`, `dra == drb`), so `a[idx[i]] = b[i]` with repeated `idx`
  is correct only if the highest lane wins. The probe's `dup-*` cases check it, including
  duplicates spread over several cache lines and around a fault.

### 1.3 Partial completion

Quoted for every gather and scatter (p.297 and its copies): "only a subset of the active
elements of write mask k1 are actually operated on (as denoted by function SELECT_SUBSET).
There are only two guarantees … (a) the destination mask is a subset of the source mask … and
(b) on a given invocation … at least one element (the least significant enabled mask bit) will
be selected", and "Programmers should always enforce the execution of a gather/scatter
instruction to be re-executed (via a loop) until … the write-mask bits all are zero". The
pseudocode clears `k1[n]` for each lane it completes (pp.298, 301).

So the lowering is:

```
    kmov    mask, %k1               ; never k0: "#UD … if … selected write-mask is k0" (p.299)
1:  vgatherdps (%base,%zmmI,4), %zmmD{%k1}
    jknzd   1b, %k1
```

Other rules from the manual:

- The destination must not be the index register: "#GP fault if the destination vector zmm1 is
  the same as index vector VINDEX" (p.297). In GCC terms, an earlyclobber destination tied to
  the else value.
- The mask is consumed and ends at zero, so it is an in/out operand. A caller that needs the
  mask again must copy it first.
- `k1[15:8] = 0` at the end of every 8-lane form (p.298), even when the mask came in with bits
  15:8 undefined (ADR-0007), because the loop runs only n < 8. The loop therefore needs no byte
  test, unlike the empty-mask guard in `@knc_maskmove` (`config/i386/imci.md:681`).
- What an execution with an all-zero mask does is not stated, since guarantee (b) assumes an
  enabled lane. The loop runs it once. The probe covers it (`empty-mask-all-guard`).

### 1.4 Fault footprint

- **Masked-off lanes.** The manual says they never fault: every exception row has "and
  corresponding write-mask bit is not zero": non-canonical, misaligned and page fault
  (pp.299, 302, 486, 489, 532, 535, 597, 600). Section 2.1.3.2 says the same for alignment:
  "a #GP fault will result if the related write-mask bit is not disabled" (p.26). This differs
  from the ordinary moves, where S3-03 found that masks never suppress a fault on the card. It
  is therefore **not** settled until the probe confirms it.
- **What an active lane reads.** Each gathered element "will always access 64 bytes of memory",
  namely its whole 64-byte line, `element & ~63` up to `+63` (pp.297, 300, 484, 487; also 4.5.3,
  p.62). The text prints `& (0x3F)`; as S3-03 found for unpack loads, this means rounding down.
  A line never crosses a page, so this cannot fault where the element itself would not. It
  matters only for uncached or MMIO memory (4.5, p.62). Scatters have no such sentence; stores
  write only the masked elements at their converted size (4.5.4, p.62).
- **Alignment.** Each element must be aligned to its own size before conversion (p.26;
  "aligned to element-wise data granularity", p.299). GCC already promises element alignment
  for a `float`/`double` access unless it is packed.
- **A fault on active lane k.** The manual is silent. It does not say whether lanes completed
  before the fault keep their results and have their mask bits cleared, whether the faulting
  instruction can be restarted, or what `si_addr` reports. The code GCC emits needs only one
  property: after the kernel handles a fault (demand paging, stack growth) and returns, the
  re-executed instruction must still give the full correct result. The probe tests that
  (`fault-lane*-resume`) and records the partial memory state of an abandoned scatter
  (`fault-lane*-abandon`). The partial register state of a gather is not visible from user
  space without the MPSS signal-frame layout for zmm and k registers, which this probe does not
  rely on.

### 1.5 What the manual does not say, and how each gap is covered

| Gap | Matters for GCC because | Probe group |
| --- | --- | --- |
| Masked-off lanes really do not fault | `IFN_MASK_GATHER_LOAD` and conditional gathers rely on it | `masked-off-*`, `empty-mask-all-guard` |
| Restart after a handled fault | demand paging inside a vectorized loop | `fault-lane*-resume` |
| State after an abandoned scatter | diagnosis only; nothing in GCC depends on it | `fault-lane*-abandon` (INFO) |
| Duplicate order across re-executions | `a[idx[i]] = b[i]`; `tree-vect-data-refs.cc:451` | `dup-*` |
| 32-bit or address-width index × scale | the optab contract, `md.texi:7461` | `index scaled-index-2^31` (INFO) |
| Dwords 15:8 ignored by the 8-lane forms | the legacy V16SI-index path (2.4) | every 8-lane case points them at the guard page |
| Signed-zero results of `vgmin`/`vgmax` | `fmin`/`fmax` mapping (item 5) | `minmax` (INFO on zero lanes) |

---

## 2. GCC 16 entry points for indexed access

### 2.1 What i386 uses today

i386 uses the target builtins, not the optabs:

- `TARGET_VECTORIZE_BUILTIN_GATHER` → `ix86_vectorize_builtin_gather` and `_SCATTER` →
  `ix86_vectorize_builtin_scatter` (`config/i386/i386.cc:28311-28315`).
- sse.md defines no `gather_load`, `mask_gather_load`, `scatter_store` or `mask_scatter_store`
  pattern; a grep finds none. The only gather expanders are `avx2_gathersi<mode>` and
  `avx2_gatherdi<mode>` (`config/i386/sse.md:30213, 30276`) and the AVX-512 ones.
- For KNC both hooks return `NULL_TREE`: `!TARGET_AVX512F && GET_MODE_SIZE (mode) == 64`, then
  `!TARGET_AVX2` (`config/i386/i386-builtins.cc:1684-1693`), and `!TARGET_AVX512F`
  (`config/i386/i386.cc:20729`).
- Upstream master at `7eb405c3d11` (2026-11-01) still has the same hooks
  (`i386.cc:29115`) and the legacy path in `tree-vect-stmts.cc`.

### 2.2 How the vectorizer chooses

1. `vect_check_gather_scatter` (`tree-vect-data-refs.cc:4824`) sets
   `use_ifn_p = supports_vec_gather_load_p (TYPE_MODE (vectype))`, or the scatter equivalent
   (`:4864-4867`). That is true when any `mask_gather_load`, `mask_len_gather_load` or
   `gather_load` optab exists for the **data mode**, with any offset mode
   (`optabs-query.cc:747-770`). The choice is therefore made per data mode, and different
   modes may use different mechanisms.
2. On the IFN path it tries offset types from the index precision up to `POINTER_SIZE`,
   signed and unsigned, with scales `{scale, 1, 2, 4, 8}`, and asks
   `internal_gather_scatter_fn_supported_p` for each (`tree-vect-data-refs.cc:4527-4630`). The
   priorities are an exact scale with the same sign, then a sign swap, then a smaller scale with
   at least twice the precision (`:4691-4795`).
3. `internal_gather_scatter_fn_supported_p` **requires the offset vector to have as many lanes as
   the data** (`internal-fn.cc:5484-5486`). It checks the optab for (data mode, offset mode), with
   operand 3 (or 2 for scatters) as the offset sign and operand 4 (3) as the scale, against the
   pattern's predicates (`:5488-5494`).
4. Off the IFN path it calls `targetm.vectorize.builtin_gather (vectype, offtype, scale)`
   (`tree-vect-data-refs.cc:5118-5130`). The offset vector type then comes from the decl's
   argument type. This path is `VMAT_GATHER_SCATTER_LEGACY` ("legacy, x86 only",
   `tree-vect-stmts.cc:11038-11040`). It accepts an offset vector with **twice** the data's lanes
   and, for the second data vector, moves the offsets' high half down with a `VEC_PERM_EXPR`
   whose selector is `i | nelt/2` (`:11126-11150`; scatter `:9160-9190`). That is exactly KNC's
   "8 lanes from the low dwords of a V16SI".
5. Alignment: for IFN and emulated gathers, `vect_supportable_dr_alignment` calls
   `support_vector_misalignment (mode, misalignment, is_packed, is_gather_scatter = true)`, with
   the misalignment taken from the object alignment modulo the element size
   (`tree-vect-data-refs.cc:6914-6923`, called from `tree-vect-stmts.cc:2518`). The legacy path
   skips this check (`tree-vect-stmts.cc:2502-2508`).

### 2.3 What GCC 16 does on KNC today

Host compile with `xgcc -march=knc`, read from `-fopt-info-vec` and the vect dump. All loops use
`restrict` pointers and an `int n`.

| Loop | `-O2` | `-O3` | Reason in the dump |
| --- | --- | --- | --- |
| `float s += a[i]` | vectorized | vectorized | "using an in-order (fold-left) reduction" (`tree-vect-loop.cc:7863`); body is 16 `fadds` per iteration |
| `double s += a[i]` | not vectorized | vectorized | same; very-cheap model rejects it at `-O2` |
| `int s += a[i]`, `int max`, `long s +=` | not vectorized | vectorized | "reduc op not supported by target", then "Reduce using scalar code" (`tree-vect-loop.cc:6103`) |
| `float max` via `?:`, no fast-math | no | no | "unsupported use in stmt": no `MAX_EXPR` is formed (item 5) |
| `a[i] = b[idx[i]]`, float | no | no | "unsupported unaligned access" (`tree-vect-stmts.cc:2675`), from `i386-knc.cc:97` |
| `a[idx[i]] = b[i]`, float | no | no | same |
| `if (m[i]) a[i] = b[idx[i]]` | no | no | same, on `.MASK_LOAD` |
| `a[i] = b[idx[i]]`, double | no | no | "conversion not supported by target" on `(long) idx` |
| `a[i] = b[n-1-i]` | no | no | "negative step and reversing not supported" (`tree-vect-stmts.cc:1935`) |
| complex `b[2i]`, `b[2i+1]` | no | no | "unsupported vect permute { 1 0 3 2 … }", "no array mode for V16SF[2]" |
| `a[i] = b[2i] + b[2i+1]` | no | no | "unsupported vect permute { 0 2 4 … 30 }" |

The `int` sum at `-O3` shows a real cost beyond the epilogue. The scalar epilogue reads the
accumulator lanes through memory, and RA keeps the accumulator in a stack slot for the whole
loop: `vpaddd -64(%rsp), %zmm1, %zmm0` followed by `vmovdqa32 %zmm0, -64(%rsp)` on every
iteration, then sixteen `movq`/`shrq`/`addl` steps. A `reduc_plus_scal_v16si` removes both.

### 2.4 What KNC must provide

| Loop | V16SF, V16SI (int index) | V8DF, V8DI (int index) |
| --- | --- | --- |
| `a[i] = b[idx[i]]` | `gather_load<m>v16si` or `mask_gather_load<m>v16si` (an all-ones mask is fine), plus the alignment hook change | legacy hook: a KNC decl taking a V16SI index (low 8 dwords) and `vec_perm_const` for V16SI `{8..15,8..15}` (`vpermf32x4 $0xee`) |
| `a[idx[i]] = b[i]` | `scatter_store<m>v16si` or `mask_scatter_store<m>v16si` | legacy scatter hook, as above |
| `if (m[i]) a[i] = b[idx[i]]` | `mask_gather_load<m>v16si` **and** a masked store of `a[i]`. S4-14's cost term makes a masked access that is not known 64-byte aligned 1000 times dearer (`config/i386/i386.cc:26803-26806`), so the loop vectorizes only when `a` is known aligned | the same, through the legacy masked builtin |

In every case `ix86_knc_support_vector_misalignment` must accept `is_gather_scatter` when
`misalignment % element_size == 0`. That is the element alignment the hardware requires
(p.26), and it is the misalignment GCC passes (`tree-vect-data-refs.cc:6914-6918`). The
`!is_packed` rule stays.

**Why the optabs do not fit 8-lane data.** The offset vector must have 8 lanes
(`internal-fn.cc:5484`). For an `int` index the 32-bit offset vectype is V16SI, because
`get_vectype_for_scalar_type` follows the loop's 64-byte vector mode (`tree-vect-data-refs.cc:4560`),
so the only 8-lane candidate is V8DI. A `mask_gather_loadv8dfv8di` pattern then receives 64-bit
offsets and must be correct for any of them, for example a genuine `long` index. `vgatherdpd`
reads 32 bits. Exactness would need a run-time check that all eight offsets fit in 32 bits,
with a scalar fallback inside the expander, plus V16SI→V8DI index widening, which KNC lacks
today ("conversion not supported", 2.3). The legacy hook avoids both. It also matches what
x86 AVX-512 uses every day (`*ALTSIV8DF` builtins, `i386-builtins.cc:1766`), so the vectorizer
code behind it is well exercised.

### 2.5 Offset type rules

- The index is a signed dword in every form (1.2). The KNC optab patterns accept offset
  operand 3 (2 for scatters) = 0, signed, only. With unsigned 32-bit offsets the vectorizer then
  falls to the sign-swap pass, which requires `needed_precision = 2 × 32 = 64` bits
  (`tree-vect-data-refs.cc:4715-4738`). There is no 64-bit form, so `unsigned` indices do not
  vectorize. That is correct: `vgatherdps` cannot zero-extend.
- The scale is 1, 2, 4 or 8 if the probe shows address-width arithmetic. If it shows a 32-bit
  product, only scale 1 is exact for arbitrary `int` offsets. The vectorizer would then multiply
  the offsets itself, which needs twice the precision (`:4740-4760`), so `int`-indexed
  `float`/`double` gathers would not vectorize. ADR-0008 must wait for that probe line.
- For the legacy hook, mirror `ix86_vectorize_builtin_gather`'s rules (`i386-builtins.cc:1695-1712`):
  SImode signed index only (DImode has no KNC form), and a scale that is a power of two up to 8.
- Byte and short indices are widened to `int` by the vectorizer; that needs `vec_unpack` for
  V16SI, which is not in scope here.

### 2.6 Can the AVX-512 code be reached behind ADR-0006 forms?

No. KNC needs its own `imci.md` patterns:

- The AVX-512 gathers are one instruction that completes every lane: `*avx512f_gathersi<mode>`
  and the `avx512f_gathersi<mode>` expander, both under `TARGET_AVX512F`. KNC's contract needs
  the `jknzd` retry loop (1.3).
- The 8-lane AVX-512 forms take a V8SI index. Even the ALTSI builtins cut the V16SI index to V8SI
  with `gen_vec_extract_lo_v16si` (`config/i386/i386-expand.cc:16527-16532`). V8SI does not exist
  on KNC (ADR-0005).
- Their operand semantics (AVX-512 opmasks, EVEX encodings) are a different ISA (ADR-0002).

What can be reached through ADR-0006 forms is the **hooks**. Each of these is an early
`if (TARGET_KNC) return ix86_knc_…;` (rule 2): `ix86_vectorize_builtin_gather`,
`ix86_vectorize_builtin_scatter`, `ix86_builtin_decl` and `ix86_expand_builtin`, for builtin
codes in a KNC range above `IX86_BUILTIN_MAX` (`i386-builtins.cc:122, 226`).

---

## 3. Permutes

### 3.1 IMCI forms

| Form | Page | Semantics | Cost |
| --- | --- | --- | --- |
| Register swizzle on a load-op source | Table 2.2 p.29 (32-bit), Table 2.3 p.30 (64-bit) | eight fixed patterns, the same in every 128-bit block (32-bit) or 256-bit block (64-bit): `{dcba}` identity, `{cdab}` swap pairs, `{badc}` swap two-away, `{dacb}` cross product (`dest[3:0] = d,a,c,b`), `{aaaa}`…`{dddd}` broadcast | free on the second source of any arithmetic, compare or `vmov*` (Load-Op SwizzUpConv, p.28); only one operand per instruction; not with a memory operand |
| `vpermd zmm1{k}, zmm2, zmm3/m` | 480-481 | `dest[n] = src[zmm2[n] bits 3:0]`, one source, 16 dwords, write-masked | one instruction plus an index register (a hoisted constant); no swizzle allowed (#UD) |
| `vpermf32x4 zmm1{k}, zmm2/m, imm8` | 482-483 | any of 4^4 permutations of the 128-bit blocks, one source | one instruction, no constant |
| `vpshufd zmm1{k}, zmm2/m, imm8` | 536-537 | any permutation within a 128-bit block, the same in all four blocks | one instruction, no constant |
| `valignd zmm1{k}, zmm2, zmm3/m, imm8` | 124-125 | `(zmm2:zmm3) >> 32*imm8[3:0]`, two sources, dword granularity | one instruction |
| `vblendmps/pd`, `vpblendmd/q` | (`imci.md:580`) | per-lane select | one instruction plus a mask |

KNC has no two-source table permute (no `vpermt2*`), no `vpermq` or `vpermpd`, and no
`unpck*` or `shufps`. A 64-bit permute is a `vpermd` on dword pairs `(2e, 2e+1)`, which
`knc_permvar<mode>` already does for rotations (`config/i386/imci.md:650-664`).

General recipes:

- **One input, any selector:** `vpermd I, src` with `I[n] = sel[n]`. One instruction plus a
  constant.
- **Two inputs, any selector:** `t = vpermd I, op0`, then `t{m} = vpermd I, op1`, with
  `I[n] = sel[n] mod nelt` and `m` the lanes that take op1. Two instructions, one index
  constant and one mask constant. The second `vpermd` merges because it is write-masked
  ("retain their previous values", p.480).

### 3.2 Which GCC hook covers what

| Hook | Status for KNC | What it would expand to |
| --- | --- | --- |
| `TARGET_VECTORIZE_VEC_PERM_CONST` (`i386-expand.cc:25380`) | returns false for V16SF, V16SI, V8DF, V8DI without AVX-512F (`:25422-25427`) | the KNC dispatcher (3.4) |
| `vec_perm<mode>` (variable) | `VEC_PERM_AVX2` puts these modes under `TARGET_AVX512F` (`sse.md:18742-18763`) | `vpermd` plus mask compare; low priority, the vectorizer rarely needs it |
| `vec_shr_<mode>` | only `V_128` (`sse.md:17825`), so the KNC names are free | `valignd dst, zero, src, k` (`2k` for 8-lane modes); used by the shift reduction epilogue only when no `reduc_*` optab exists, for example `*` reductions |
| `vec_extract<m><scalar>` | `VEC_EXTRACT_MODE` puts these modes under `TARGET_AVX512F` (`sse.md:13668-13687`) | lane 0 is the ADR-0004 transport; lane k is `valignd`/`vpermd`, then lane 0. Needs an ADR-0006 iterator term plus an entry dispatch in `ix86_expand_vector_extract` (`i386-expand.cc:19344`), as `vec_init` has at `:18653` |
| `vec_extract<m><half>` | V8SF and V4DF do not exist | not applicable: no half modes on KNC (ADR-0005) |
| `vec_init` | done: `VEC_INIT_MODE` (`sse.md:29781-29790`) → `ix86_knc_expand_vector_init` (`i386-knc.cc:292`) | |
| `vec_interleave*`, `vec_extract_even/odd`, `vec_reverse` | no such optabs in GCC 16 (`optabs.def`); the vectorizer asks `vec_perm_const` | through `vec_perm_const` |
| `vec_load_lanes` | "no array mode for V16SF[2]" (2.3) | not needed once `vec_perm_const` exists |

### 3.3 What the vectorizer needs, and the cheapest sequence

| Need | Selector (V16SF) | Cheapest IMCI |
| --- | --- | --- |
| Reversed loop `a[n-1-i]` (`perm_mask_for_reverse`, `tree-vect-stmts.cc:1866-1879`; else elementwise, `:1928-1935`) | `{15 … 0}` | `vpermd` with a hoisted index, 1 per vector. Without a constant: `vpshufd $0x1b` + `vpermf32x4 $0x1b`. V8DF: `vpermd` on pairs, or `vpermf32x4 $0x1b` + swizzle `{cdab}` (64-bit) |
| Complex swap re/im | `{1 0 3 2 …}` | swizzle `{cdab}`, free on the consuming operation (32-bit for float complex, 64-bit for double complex) |
| Even extraction (stride 2) | `{0 2 … 30}` | `vpermd I, op0`; `vpermd I, op1{0xff00}` with `I = {0,2,…,14,0,2,…,14}` |
| Odd extraction | `{1 3 … 31}` | the same with `I = {1,3,…}` |
| Interleave for stride-2 stores | `{0 16 1 17 …}` / `{8 24 …}` | `vpermd I, op0`; `vpermd I, op1{0xaaaa}`, with `I = {0,0,1,1,…,7,7}` or `{8,8,…}` |
| Offsets high half (legacy 8-lane gather) | `{8..15, 8..15}` | `vpermf32x4 $0xee` |
| Whole-vector shift (epilogue) | `{k … 15, 16 …}` with zero | `valignd $k` |
| Broadcast lane j | `{j j …}` | lane 0: `vpermf32x4 $0` + swizzle `{aaaa}` (`ix86_knc_expand_duplicate`, `i386-knc.cc:257`); lane j: `vpermd` |

The vector costs need a KNC term so that a two-`vpermd` permute is counted as two. Today a
`vec_perm` is charged once (`i386.cc:26808`).

### 3.4 Which `ix86_expand_vec_perm_const_1` paths would fire wrongly

Today none, because the function is never reached for KNC modes: the mode switch in
`ix86_vectorize_vec_perm_const` returns false first (`i386-expand.cc:25422-25427`). If that guard
were simply widened to `|| TARGET_KNC`, the walk in `ix86_expand_vec_perm_const_1`
(`:25210-25330`) would do this for 512-bit modes without AVX-512F:

- `expand_vec_perm_1` (`:22181`): the `vec_select` matchers (`expand_vselect`,
  `expand_vselect_vconcat`) only recog insns whose conditions hold, so they could match KNC's
  `knc_swap_pairsv16si` (`imci.md:970`) and the broadcast swizzles. They are safe, but the result
  depends on the order of insns in the md files. The other single-insn tries (blend, movs,
  insertps, vpermil, pshufb, palignr, `ix86_expand_vec_one_operand_perm_avx512`,
  `ix86_expand_vec_perm_vpermt2`) test SSE, AVX or AVX-512 flags and return false.
- `expand_vec_perm_even_odd` (`:24802`) accepts V16SF, V8DF, V16SI and V8DI selectors
  `{0,2,4,…}` and calls `expand_vec_perm_even_odd_1`, which has no case for them and hits
  **`gcc_unreachable` at `:24791`**: an ICE on the even/odd extraction of 2.3.
- `expand_vec_perm_broadcast` (`:25004`) passes any splat to `expand_vec_perm_broadcast_1`, whose
  switch also ends in **`gcc_unreachable` (`:24995`)** for these modes.
- `canonicalize_vector_int_perm` (`:21702`) recasts V16SI as V8DI and retries `expand_vec_perm_1`.
  That is harmless, since it finds nothing.
- The other two-, three- and four-insn helpers test `TARGET_SSE*`, `TARGET_AVX*` or sizes of 16
  or 32 bytes and return false (surveyed: `pshuflw_pshufhw`, `palignr`, `interleave2`,
  `vpermq_perm_1`, `vperm2f128`, `pblendv`, `2perm_*`, `shufps_shufps`, `punpckldq_pshuf`,
  `even_odd_pack`, `pslldq_psrldq_por`, `pand_pandn_por`, `even_odd_trunc`, `vpermt2_vpshub2`,
  `vpshufb4_vpermq2`).

So KNC takes ADR-0006 rule 2: `if (TARGET_KNC) return ix86_knc_vectorize_vec_perm_const (...)`
at the top of `ix86_vectorize_vec_perm_const`, and no shared helper runs. The KNC function must
return the same answer for `target == NULL` (testing) as it expands. With the two-`vpermd`
recipe, every selector on the four modes is supported, so testing is trivially true.

---

## 4. Reductions

### 4.1 Optabs and names

| Optab (`optabs.def:411-426`) | sse.md name for the KNC modes | KNC form |
| --- | --- | --- |
| `reduc_plus_scal_<m>` | defined for V16SF, V8DF, V16SI, V8DI under `TARGET_AVX512F`, through V8SF/V4DF halves (`sse.md:3994-4018`) | tree below; V8DI through the carry add (`imci.md:935-1060`) |
| `reduc_smax/smin_scal_<m>` | `REDUC_SMINMAX_MODE`, all four modes (`sse.md:4040-4064`) | V16SI `vpmaxsd`/`vpminsd`; V16SF/V8DF `vgmaxps/pd` (only reached for `MAX_EXPR`, item 5); V8DI none (no 64-bit compare) |
| `reduc_umax/umin_scal_<m>` | `VI_AVX512BW` (V16SI, V8DI unconditional) under `TARGET_AVX512F` (`sse.md:4066-4081`) | V16SI `vpmaxud`/`vpminud` (pp.497-506); V8DI none |
| `reduc_and/ior/xor_scal_<m>` | `REDUC_ANY_LOGIC_MODE`, V16SI and V8DI (`sse.md:4321-4340`) | `vpandd/vpord/vpxord` (`q` for V8DI) |
| `reduc_fmax/fmin_scal_<m>` | not defined by i386; free names | `vgmax`/`vgmin` tree, only if `fmax<m>3`/`fmin<m>3` are adopted (item 5) |
| `fold_left_plus_<m>` | not defined; free | not recommended (4.4) |

Each sse.md name that exists is a name `imci.md` may not reuse, since `imci.md` is read first.
Each of the four sse.md expanders therefore needs the ADR-0006 form already used for add/sub
(`sse.md:16611-16620`): an expander-only iterator copy with a `|| ix86_knc_packed_mode_p`
condition, defined in `imci.md` like `VI_AVX2_KNC` (`imci.md:34`), and an entry dispatch
`if (TARGET_KNC) { emit_insn (gen_knc_reduc_… ); DONE; }`. Note also that `ix86_split_reduction`
already returns `mode` for KNC (`i386-expand.cc:26833`), so no half-mode split is requested.

### 4.2 The vectorizer's epilogue when no `reduc_*` optab exists

`vect_create_epilog_for_reduction` (`tree-vect-loop.cc:5332`):

1. With `IFN_REDUC_*` supported, one call (`:5960-5968`).
2. Otherwise `targetm.vectorize.split_reduction` may halve first (`:5998-6025`). For KNC it returns
   the same mode, and there are no half modes to extract (`:5185-5245` needs `vec_extract` to a
   half mode or integer punning).
3. Otherwise **shift reduction**, if `have_whole_vector_shift`: either `vec_shr_<m>` or
   `vec_perm_const` for every shift selector (`:4672-4692`, used at `:6031-6036`). Shift by
   n/2, n/4 and so on, then extract lane 0.
4. Otherwise "Reduce using scalar code": extract each lane with `BIT_FIELD_REF` and combine in
   scalar (`:6103`). This is what KNC does today (2.3).

Once `vec_perm_const` exists, `MULT_EXPR` reductions, which have no `reduc_*` optab
(`tree-vect-loop.cc:3308-3310`), get step 3 with `valignd`.

### 4.3 The cheapest IMCI tree

Swizzles fold into the add, but only within 128-bit blocks for 32-bit elements and 256-bit
blocks for 64-bit elements. `vpermf32x4` moves 128-bit blocks.

```
V16SF / V16SI (16 lanes, 6 instructions):
  t = vpermf32x4 $0x4e, v        ; swap the 256-bit halves
  v = v + t
  t = vpermf32x4 $0xb1, v        ; swap adjacent 128-bit blocks
  v = v + t
  v = v + v{badc}                ; swizzled second source, free
  v = v + v{cdab}
  -> every lane holds the sum; take lane 0

V8DF (8 lanes, 4 instructions):
  t = vpermf32x4 $0x4e, v ; v = v + t
  v = v + v{badc}                ; 64-bit badc swaps the 128-bit halves of each 256 bits
  v = v + v{cdab}                ; 64-bit cdab swaps the qwords of each 128 bits
```

A `vpermd` tree needs four index constants and four `vpermd`, against two (or one) `vpermf32x4`
and free swizzles, so the swizzle tree is cheaper. `vpmaxsd`, `vpminsd`, the unsigned forms,
`vpandd`/`vpord`/`vpxord`, `vgmaxps` and `vgminps` all take the same swizzled operand
(SwizzUpConv, p.28; for example `Sf32(zmm3/mt)` in VGMAXPS, p.337). V8DI add has no swizzled
form of the carry sequence, so it uses `vpermf32x4 $0x4e`, `vpermf32x4 $0xb1` and `vpshufd $0x4e`
(swap qwords), each followed by the 4-instruction carry add (`imci.md:1033-1060`). That is 15
instructions. It is still better than the scalar epilogue's memory round trip, and it is the
last thing to do.

Lane 0 becomes the scalar result through ADR-0004's transport: a scalar SF/DF/SI/DI value may
sit in lane 0 of a zmm register (`knc_store<mode>`, `imci.md:160-169`), so the expander does not
add a hidden memory transfer. RA adds the bridge if the value must reach x87 or a GPR, and that
transfer is visible in RTL.

New insns: swizzled-operand forms of `*knc_<op><mode>3` with a `vec_select` second operand,
like `knc_<insn>_carry_outv16si` (`imci.md:984-1009`); and `knc_permf32x4<mode>` (an unspec
with an immediate, like `knc_broadcast_block<mode>`, `imci.md:489`).

### 4.4 FP ordering in GCC 16

- `needs_fold_left_reduction_p` returns `!flag_associative_math` for FP `+`
  (`tree-vect-loop.cc:3421-3445`). Then `vectorizable_reduction` sets `FOLD_LEFT_REDUCTION`
  (`:7472-7497`), and `fold_left_reduction_fn` asks for `IFN_FOLD_LEFT_PLUS` (`:3252-3263`).
  Without it, `reduc_fn = IFN_LAST`, and `vectorize_fold_left_reduction` (`:6431`) adds the lanes
  one at a time in order (`vect_expand_fold_left`, `:6340`).
- Observed, `float s += a[i]` with no fast-math flags:
  - `-O2`: vectorized, in-order. The dump says "reduc op not supported by target" and then "using
    an in-order (fold-left) reduction". After later passes the loop is 16 `fadds` from memory per
    iteration in source order. No vector add is used, so nothing is reassociated.
  - `-O3`: the same. `double` is the same at `-O3`; at `-O2` the very-cheap model leaves it scalar.
- `-ffast-math` (in fact `-fassociative-math`) is required for any tree; GCC asks for it itself.
  `MIN_EXPR`/`MAX_EXPR`, `fmin` and `fmax` never need fold-left (`:3428-3441`).

### 4.5 Contract recommendation (ADR-0003 point 2)

1. **No implicit reassociation.** `reduc_plus_scal_v16sf` and `_v8df` are exact only as a tree,
   so they may be used only where GCC has decided reassociation is allowed. The vectorizer already
   ensures that (4.4). The expander needs no flag test, but a T1 negative scan must show that
   `-O2` and `-O3` without `-fassociative-math` emit no `vaddps`/`vaddpd` reduction tree.
2. **No `fold_left_plus_<m>`.** An in-order sum in vector registers costs a lane move plus a
   masked add per element, about 32 instructions for 16 lanes. That is more than today's 16
   `fadds`, and it would move the arithmetic from x87 to zmm. GCC 16 already gives the in-order
   result.
3. The tree order is fixed (halves, then blocks, then pairs), so `-ffast-math` results are
   deterministic run to run.
4. Integer reductions are always exact: wrapping `+`, `min`/`max` and logic are associative.

---

## 5. FP min/max

### 5.1 The instructions

The pseudocode is transcribed in the probe's `model()`:

| | `vgmaxps`/`vgmaxpd` (pp.338, 334) | `vgminps`/`vgminpd` (pp.346, 342) | `vgmaxabsps` (p.330) |
| --- | --- | --- | --- |
| one NaN | returns the other operand | the same | `Abs(other)` |
| both NaN | the first source A, unchanged (an sNaN is not quietened) | the same | `Abs(A)` |
| `(-0,+0)`, `(+0,-0)` | `+0` both ways | `-0` both ways | `+0` |
| prose on zeros | "it is permissible for the result of comparing zeros to be dependent on the order of parameters, using a comparison that ignores the signs" (p.337) | the same (p.345) | the same (p.329) |
| sNaN alone | the other operand, no quietening (p.337 prose) | the same | |
| DAZ | input denormals are zero under MXCSR.DAZ; tiny results are not flushed | the same | the same |

First source A is the middle AT&T operand: `vgmaxps %zmmB, %zmmA, %zmmD`. Only `vgmaxabsps` has
an absolute form; there is no `vgmaxabspd`.

### 5.2 Against GCC's operations

- **`MIN_EXPR`/`MAX_EXPR` and RTL `smin`/`smax`**: "if both operands are zeros, or if either
  operand is NaN, then it is unspecified which of the two operands is returned"
  (`tree.def:784-786`, `rtl.def:507-509`, `md.texi:5139-5142`). Any result `vgmin`/`vgmax` gives is
  allowed, so the map is **exact by definition, whatever the probe shows**.
- **When C produces them.** `a < b ? a : b` becomes `MIN_EXPR` only when signed zeros are not
  honoured (`fold-const.cc:6186`) **and** NaNs are not honoured (`:6215`, `:6230`). So
  `-ffinite-math-only` alone is not enough; it takes `-ffinite-math-only -fno-signed-zeros`
  (both in `-ffast-math`). Without them the `?:` stays a compare and select (`float max`, 2.3).
- **`fmin`/`fmax` (`IFN_FMIN`/`FMAX`, `fmin<m>3`)**: "If one operand is a quiet NaN, then the
  other operand is returned. If both … quiet NaN, then a quiet NaN is returned. In the case
  when gcc supports signaling NaN (-fsignaling-nans) an invalid floating point exception is
  raised and a quiet NaN is returned" (`md.texi:5146-5151`). The text says nothing about signed
  zeros.
  - Quiet NaNs: the pseudocode matches exactly.
  - sNaN under `-fsignaling-nans`: `vgmaxps` returns the other operand, not a quiet NaN. So the
    pattern needs `!flag_signaling_nans`.
  - Signed zeros: GCC's own constant folding uses `mpfr_min`/`mpfr_max`
    (`fold-const-call.cc:1526-1532`). MPFR gives `min(±0) = -0` and `max(±0) = +0`, which is the
    pseudocode's answer. S4-03 recorded that k1om libm `fminf` returns its first argument for
    `(+0,-0)`, which is `+0` (`work/tickets/S4-03.md:45`), so libm is the odd one out. The probe
    prints libm next to the instruction for every pair.
- **`vgmaxabsps`** equals `fmax (fabsf (a), fabsf (b))` for quiet NaNs, and its zeros are always
  `+0`. No C form produces it directly; it would be a combine pattern on
  `IFN_FMAX (ABS, ABS)` or `MAX_EXPR (ABS, ABS)`. It has little value, so it is out of scope.

### 5.3 What can map, and the reductions that follow

| C source | GCC operation | Map | Condition |
| --- | --- | --- | --- |
| `a < b ? a : b`, `a > b ? a : b` and their `<=`/`>=` forms | `MIN_EXPR`/`MAX_EXPR` | `vgminps/pd`, `vgmaxps/pd` | formed only under `-ffinite-math-only -fno-signed-zeros`; exact then |
| `s = a[i] < s ? a[i] : s` | `MIN_EXPR` reduction → `reduc_smin_scal` | `vgmin` tree (4.3) | the same |
| `fminf`, `fmaxf`, `fmin`, `fmax` | `IFN_FMIN`/`FMAX` | `vgmin`/`vgmax` | `!flag_signaling_nans`, and an ADR-0008 decision on the libm zero mismatch |
| `fmaxf` reduction | `reduc_fmax_scal` (`md.texi:7907-7911`) | `vgmax` tree | the same as `fmaxf`; no fold-left needed |
| `int`/`unsigned` min/max | `MIN_EXPR` | `vpminsd`/`vpminud` and so on, already V16SI (`imci.md:803`) | always |
| `long` min/max | | none | no 64-bit compare on KNC |

`smin`/`smax` for V16SF/V8DF share a name with sse.md's `<code><mode>3<mask_name><round_saeonly_name>`
(`sse.md:3318-3335`). That expander needs `VFH_KNC` (which exists, `imci.md:816`), a
`|| TARGET_KNC` term, and an entry dispatch placed **before** its
`!flag_finite_math_only || flag_signed_zeros` branch, which would otherwise emit the SSE IEEE
pattern. `fmin<m>3`/`fmax<m>3` are free names, so they are `imci.md` only.

---

## 6. Probe: `tests/regress/knc-gather-probe.c`

Its style follows `tests/regress/knc-unaligned-probe.c`: one RW page between two `PROT_NONE`
pages, `sigsetjmp` recovery, and every instruction in inline asm. The build is `-O0`, so the
compiler adds no vector code. The build command is in the file header, and the program was
compiled, linked and passed `tools/knc_lint` on the host. It ran on no machine. Each case prints
one line ending in `check=ok`, `FAIL` (contradicts the manual or a fact GCC relies on) or `INFO`
(the manual is silent, so the line is the observation). The program exits 1 on any `FAIL`.

Groups, each run for all four gather forms and all four scatter forms:

| Group / case | What it settles | Check |
| --- | --- | --- |
| `all-active` | baseline; for 8-lane forms dwords 15:8 point into the guard, so a read of them faults | ok/FAIL |
| `masked-off-{upper,lower}-guard-lane{0,mid,last}` | a masked-off lane pointing into `PROT_NONE` neither faults nor writes; a gather keeps the old value | ok/FAIL |
| `empty-mask-all-guard` | an all-zero mask is a no-op and the loop runs once | ok/FAIL |
| `last-element-of-page` | the 64-byte line rule never reaches the next page | ok/FAIL |
| `fault-lane{0,mid,last}-resume` | the handler opens the page and returns: the result must be complete and correct; reports `faults`, the `si_addr` offset, iterations and the final mask | ok/FAIL |
| `fault-lane*-abandon` (scatter) | lanes stored before an abandoned fault; no byte outside an active element changed | INFO, FAIL on a stray byte |
| `dup-all-same`, `dup-all-same-mask-5555`, `dup-two-lines`, `dup-four-lines` | the highest active lane wins, including duplicates in different lines (likely separate re-executions) | ok/FAIL |
| `dup-around-fault-resume` / `-abandon` | lanes 0 and 2 share an element with a fault on lane 1 between them | ok/FAIL; INFO |
| `index scaled-index-2^31` | `semantics=address-width` (GCC's order), `32-bit-product`, or other | INFO, decisive for 2.5 |
| `index negative-index` | indices are sign-extended | ok/FAIL |
| `minmax` × `vgmaxps`, `vgminps`, `vgmaxpd`, `vgminpd`, `vgmaxabsps` | each lane against the pseudocode, with libm `fmin*`/`fmax*` alongside; NaN rules FAIL on a mismatch, `±0` lanes INFO | ok/FAIL/INFO |

Every line also prints the loop's execution count, as information about `SELECT_SUBSET`. It is
not a timing. Running it needs `tools/card_run` with about 64 MiB and the owner's agreement while
the card is on hold.

---

## 7. Recommendation and estimate

The estimates count changed lines. Shared lines are ADR-0006 forms. Rebuild cost follows
`AGENTS.md`: any `.md` or `i386-knc.h` edit means a near-full rebuild, so put every new prototype
in one `i386-knc.h` edit per ticket.

### E4-06: permutes, reductions, min/max (do first; E4-02's 8-lane route needs its permute)

**`imci.md` patterns:**

- `knc_permf32x4<mode>` (imm8), `knc_pshufd<mode>` (imm8), `knc_valignd<mode>` (two inputs and an
  imm), `knc_swizzle<mode>` (a `vmov*` with one of the 8 swizzles), and a write-masked
  `knc_permvar<mode>_mask` (`vec_merge` around the existing `knc_permvar`).
- Swizzled-second-operand variants of FP add, integer add, min/max and logic, used by the
  reduction trees. Mul, for product reductions, is optional.
- `vec_shr_<mode>` via `valignd`; optional once `vec_perm_const` handles shift selectors.
- Expanders `@knc_reduc_<op><mode>` for plus (four modes, V8DI through the carry),
  smax/smin/umax/umin (V16SI; V16SF/V8DF smax/smin), and and/ior/xor (V16SI, V8DI).
- `*knc_<maxmin>v16sf3`/`v8df3` (`vgmaxps/pd`, `vgminps/pd`), for `MIN_EXPR` only.
- If ADR-0008 accepts them: `fmin<m>3`, `fmax<m>3`, `reduc_fmin_scal_<m>` and
  `reduc_fmax_scal_<m>` under `!flag_signaling_nans`.
- Estimate: about 230 lines of `imci.md` and about 200 lines of `i386-knc.cc` (the permute
  dispatcher and selector classifier, and the reduction tree builder).

**Shared hunks:**

| Hunk | File | Form | Lines |
| --- | --- | --- | --- |
| `if (TARGET_KNC) return ix86_knc_vectorize_vec_perm_const (...)` | `i386-expand.cc:25380` | rule 2, early return | 3 |
| reduc plus, smaxmin, umaxmin, any_logic expanders: KNC iterator, condition term, entry dispatch | `sse.md:4004, 4051, 4067, 4327` | rule 2 + condition term | 4 × 5 = 20 |
| `<code><mode>3` smaxmin: `VFH_KNC`, `|| TARGET_KNC`, entry dispatch | `sse.md:3318` | the same | 5 |
| a `vec_perm` cost term for KNC two-`vpermd` permutes | `i386.cc:26803` (next to S4-14's term) | condition term | 4 |
| prototypes | `i386-knc.h` | KNC file (rebuild cost only) | 3 |

That is about 32 shared lines, all hooks.

**Risks:**

- `testing_p` must agree with the expansion, or the vectorizer asserts in
  `vect_gen_perm_mask_checked`.
- `vpermd` indices read only bits 3:0 (p.480). For 8-lane modes, build dword pairs, never qword
  indices.
- Swizzles exist only on the second source and only for register operands. With the rounding
  override, EH=1 reuses the same bits (p.28), so no swizzled insn may also carry a rounding
  override.
- The sse.md reduction expanders change upstream more often than most. Keep each hunk to the
  ADR-0006 shape so the forward-port drill sees only context changes.
- An under-costed two-input permute could make SLP pick permute-heavy plans; that is what the
  cost term is for.
- If `fmin`/`fmax` are adopted and the probe shows order-dependent zeros, the vector results
  depend on operand order, and libm already differs. ADR-0008 must state the zero contract.

**Proposed gcc tickets:**

1. **Permutes** (`vec_perm_const` dispatch and the five insns).
   - T1: at `-O3`, `a[i] = b[n-1-i]` emits `vpermd` for each of the four modes; `b[2i] + b[2i+1]`
     emits two `vpermd`, one with `{%k}`; complex re/im uses a `{cdab}` swizzle; and
     `__builtin_shuffle` with constant selectors covers every recipe kind (identity, swizzle,
     `vpermf32x4`, `vpshufd`, `valignd`, one and two `vpermd`), with a negative scan that no
     `vpermt2`/`vpermq` appears.
   - Native: reversed, stride-2 and interleaved loops compared with a scalar reference on the
     card, across all four modes and lengths 1-67.
2. **Reductions** (the four sse.md dispatches and the trees).
   - T1: the `int` sum at `-O3` has the `vpermf32x4 $0x4e`/`$0xb1` and swizzled `vpaddd` tree and
     no stack accumulator (no `vpaddd -64(%rsp)`); `long` sum, `int` max, `unsigned` min, and
     `&`/`|`/`^` all emit their trees; `float`/`double` sums with `-ffast-math` emit the
     `vaddps`/`vaddpd` tree; and a negative scan that `float` sums at `-O2` and `-O3` without fast
     math contain no `vaddps`.
   - Native: integer reductions are exact against scalar, including wrap-around. FP sums under
     `-ffast-math` use integer-valued inputs, so the exact sum is representable and any order
     gives the same answer.
3. **FP min/max** (`MIN_EXPR` patterns and `reduc_smin`/`smax` for V16SF/V8DF; `fmin`/`fmax` only
   if ADR-0008 says so).
   - T1: `?:` max with `-ffinite-math-only -fno-signed-zeros` gives `vgmaxps`, and without those
     flags gives no `vgmax`.
   - Native: values without NaN or zero ties compared with scalar. This ticket needs the probe's
     `minmax` lines first.

### E4-02: gather and scatter lowering

**`imci.md` patterns:**

- `knc_gather<mode>` for the four modes: a `define_insn` whose output is the `1: vgather…;
  jknzd 1b` loop (1.3).
  - Operands: the destination is an earlyclobber `=&YJ` tied to the else value; the index is
    `YJ` (V16SI); the base is a GPR; the mask is `+YL`, consumed to zero, never k0; the scale is
    a const operand; and the memory is `(mem:BLK (scratch))` in an unspec, as the AVX-512 gathers
    do, so alias analysis sees a read of unknown memory.
  - Mark the insn `type "multi"` with a length bound, as `*knc_packed_unaligned_load` does
    (`imci.md:345-357`).
- `knc_scatter<mode>`: the same loop with `vscatter…`, the mask consumed, and a BLK memory store.
- `mask_gather_load<m>v16si` and `gather_load<m>v16si` for V16SF and V16SI.
  - Operand 3 (offset sign) is accepted only as 0. Operand 4 (scale) is 1/2/4/8, or 1 only if the
    probe shows a 32-bit product.
  - Else values: support `MASK_LOAD_ELSE_ZERO` with a visible `vpxord` into the destination, and
    undefined.
  - The unmasked form sets the mask to all ones in a GPR, then `kmov`.
- `mask_scatter_store<m>v16si` and `scatter_store<m>v16si` for V16SF and V16SI.
- In `i386-knc.cc`: `ix86_knc_support_vector_misalignment` accepts `is_gather_scatter` when the
  misalignment is a multiple of the element size.
- Estimate for the 16-lane part: about 120 lines of `imci.md` and 10 of `i386-knc.cc`, with
  **zero shared lines**.
- The 8-lane part: KNC builtin decls and expanders for V8DF/V8DI gathers and scatters with a V16SI
  index, reading the low 8 dwords (about 120 lines of `i386-knc.cc`, about 40 of `imci.md`).

**Shared hunks, 8-lane part only:**

| Hunk | File | Form | Lines |
| --- | --- | --- | --- |
| `if (TARGET_KNC) return ix86_knc_vectorize_builtin_gather (...)` | `i386-builtins.cc:1677` | rule 2 | 3 |
| `if (TARGET_KNC) return ix86_knc_vectorize_builtin_scatter (...)` | `i386.cc:20723` | rule 2 | 3 |
| KNC builtin codes in `ix86_builtin_decl` | `i386-builtins.cc` | rule 2 | 3 |
| KNC builtin codes in `ix86_expand_builtin` | `i386-expand.cc` | rule 2 | 3 |
| prototypes | `i386-knc.h` | KNC file | 4 |

That is about 12 shared lines.

**Risks**, in order:

1. **Index × scale arithmetic** (1.2). If the card forms a 32-bit product, scales above 1 are
   not exact for `int` indices, and most `float`/`double` gathers stay scalar unless value-range
   information bounds the index. The probe decides this before any pattern is written.
2. **Masked-off fault suppression** (1.4) is unproven, and the analogous claim failed for
   ordinary moves in S3-03. If it fails, conditional gathers (`mask_gather_load` with a real
   mask) are unsafe, and only unmasked or all-ones forms may be offered.
3. **Duplicate order across re-executions** (1.2). If it fails, `scatter_store` is not exact for
   `a[idx[i]] = b[i]`, and scatters need a run-time conflict check (there is no `vpconflictd` on
   KNC) or must be left out.
4. **Restart after a fault.** If a resumed gather or scatter is wrong, nothing here is usable.
5. **A branch inside one insn.** Scheduling sees a single insn; that is acceptable because the
   loop is self-contained and runs at least once. The mask is clobbered, which is visible. Use
   local numeric labels.
6. **The 8-lane route depends on the legacy path** that upstream marks "legacy, x86 only". It is
   still on master (2.1). If upstream removes it, x86 AVX-512 must move first, and KNC would then
   need the guarded V8DI-offset optab (2.4), which can be kept as the fallback plan.
7. **Conditional gathers whose store is masked** vectorize only for 64-byte-aligned destinations
   while S4-14's cost term stands (2.4).

**Proposed gcc tickets** (each needs the probe's results first):

4. **16-lane gather/scatter** (the misalignment hook, `knc_gather`/`knc_scatter`, four optabs).
   - T1: at `-O3`, `a[i] = b[idx[i]]` and `a[idx[i]] = b[i]` for `float` and `int` contain
     `vgatherdps`/`vpgatherdd` (`vscatterdps`/`vpscatterdd`) inside a `jknzd` loop with a non-k0
     mask; `if (m[i]) a[i] = b[idx[i]]` with an aligned `a` uses the compare mask; an `unsigned`
     index produces no gather; and `long` data produces none until ticket 5.
   - Native, compared with scalar:
     - random and repeated indices (the highest lane wins);
     - an index to the last element of a page;
     - a conditional gather whose masked-off lanes point at a `PROT_NONE` page;
     - a gather over a freshly `mmap`ed, untouched region, so the loop takes demand-paging faults.
5. **8-lane gather/scatter through the builtin hook** (the four shared dispatches, KNC decls; after
   ticket 1, for `vpermf32x4 $0xee`).
   - T1: `double`/`long` with an `int` index emit `vgatherdpd`/`vpgatherdq` twice per 16 indices,
     with one `vpermf32x4 $0xee` on the index; scatters likewise; and an x86-64 build's code for
     the same file is unchanged (the hooks are inert off KNC).
   - Native: the same cases as ticket 4 for `double` and `long`.

Suggested order: probe on the card, then tickets 1, 2, 4, 3, 5. Ticket 3's `fmin`/`fmax` part and
ticket 5's route are lead decisions for ADR-0008.
