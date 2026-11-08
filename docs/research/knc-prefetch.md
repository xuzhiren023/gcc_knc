# KNC two-level software prefetch (S8-03, E5-07)

Status: green 2026-11-08 (GCC s8/S8-03 at 8c18be9; T1 scans pass). Card results are the
lead's: the paired M2 run and s4_masks / s5_ops are staged under `.work/_shared/S8-03/`.

## Rules the T1 scans encode (`tests/t1/knc-prefetch-*.c`)

Source: `docs/research/knc-characterization.md` C2, C4, C5 and the S8-12 rerun.

- `-march=knc` turns `-fprefetch-loop-arrays` on at `-O2` and `-O3` (not `-Os`).
- Every prefetched stream gets `vprefetch1` (L2) at the L2 distance and `vprefetch0` (L1)
  at the L1 distance, L2 ahead of L1. Never L1 without L2 (C5: 1.7-2.3x slower than none).
- Distances are in 64-byte lines of the stream, the unit C5 swept (one line per row
  iteration). For a loop whose iteration moves one line this is C5's iteration count; a
  scalar loop over floats gets 16 x 16 iterations ahead for 16 lines, so a line's prefetch
  is still issued once (the pass's `prefetch_mod`). When the loop's largest step exceeds a
  line the distance stays in bytes: iterations = ceil(lines x 64 / step), at least 1, so
  WRF's k loop (51 trips, 1092-byte step; lead note 2026-11-08) gets `vprefetch1` 2 and
  `vprefetch0` 1 iterations ahead (2184 and 1092 bytes) and a 4 KiB-step loop 1 and 1.
  The four-distance trip check below uses that iteration count (4 x 2 = 8 for WRF's loop,
  not 128), so the loop is prefetched. `tests/t1/knc-prefetch-O2.c` `column_f32`.
- Defaults: `--param=knc-prefetch-l2-distance=32`, `--param=knc-prefetch-l1-distance=16`.
  The L2 distance never changes with density (C5: 32 best at 2 and 4 threads; 64 within 6%).
- L1 footprint rule: when `L1 distance x prefetched streams x knc-threads-per-core` exceeds
  a quarter of L1 (128 lines), the L1 distance halves. This reproduces every measured point:
  16 for one or two streams at 2 and 4 threads, 8 for eight streams at 2 and 4 threads
  (S8-12: 8 beats 16 by 12% at 2 threads). Unmeasured in between; halving costs at most 2%
  on stream and stencil (C5 L1 8 against 16), so the rule errs toward the smaller footprint.
- The L1 distance is kept below the L2 distance if a user sets them the other way round.
- A loop is prefetched only if it runs at least four L2 distances (the pass's trip-count
  ratio, applied to the far distance), so a 2 KiB-per-stream fixed loop gets none.
- A loop whose trip count is known only at run time is versioned on it (lead changes
  2026-11-08: on the card, M2 `short` at length 17 ran one vector iteration with four
  prefetches and their address updates, 1.30-1.33x slower). The prefetched copy runs only
  when the loop runs at least four L2 distances in iterations (128 vector iterations, 2048
  floats, for a unit-step loop); the other copy is the loop as S8-02 compiled it, with no
  prefetch. The guard is one compare and branch before the loop. A loop whose single exit
  gives no trip count (several exits, or none the niter analysis can express) gets no
  prefetch, since the guard cannot be built. `tests/t1/knc-prefetch-O2.c` `stream_f32`.
- Written streams use the read-hint forms `vprefetch0/1`, as C5's kernels did for their
  output array. `vprefetche*` is unmeasured and not emitted.

## What was built (GCC s8/S8-03, 836a0e2..2fb2498)

- `imci.md`: `knc_prefetch`, one `(prefetch ...)` insn under `TARGET_KNC`, locality 3/2/1/0 to
  `vprefetch0/1/2/nta` (Intel 327364-001 pp. 641-656); write hint dropped like the SSE path.
  `knc.md`: `knc_special` value `prefetch` puts it in a scalar slot (C2).
- `i386.md` `prefetch` expander: `|| TARGET_KNC` in the condition and an early
  `gen_knc_prefetch` emit at entry (ADR-0006 forms). `__builtin_prefetch` now works on KNC.
- `tree-ssa-loop-prefetch.cc`: target hook `TARGET_PREFETCH_DISTANCES (nstreams, &near, &far)`
  in lines (`target.def`, `tm.texi.in`, `tm.texi`; default `NULL`). When it answers, the
  pass skips its latency-derived `ahead`, counts the streams after reuse pruning, converts
  lines to iterations by the loop's largest step (smallest `prefetch_mod` below a line,
  ceil(lines x line / step) above one), checks the trip count against the far distance,
  and issues the far prefetch (locality 2, or 1 when nontemporal) before the near one for
  every stream. `i386.cc` points the hook at
  `ix86_knc_prefetch_distances`, which returns false unless `TARGET_KNC`.
- `i386-knc.cc`: the distance rule above; `-fprefetch-loop-arrays` at `-O2`+ (not `-Os`),
  `min-insn-to-prefetch-ratio` and `prefetch-min-insn-to-mem-ratio` 1, from the existing
  `ix86_knc_vectorizer_params` call (no `i386-options.cc` change); `simultaneous_prefetches`
  1024 in the KNC cost table (the pass's slot count, not a hardware queue: eight streams at
  16 + 32 lines hold 384 slots). `i386.opt`: the two params.
- Two generic fixes the scans needed. Round 2 (lead, 2026-11-08) gated both on the two-level
  hook answering (`targetm.prefetch_distances` present and returning true, an own line in each
  condition; GCC 2fb2498): on every other target `__builtin_prefetch` in `ivopts` and the
  pass's grouping are exactly upstream's, and the KNC assembly of the T1 files and the M2
  kernels is byte-identical to 440d4a9.
  - The pass groups references whose addresses differ by a constant once expanded through
    their definitions (`tree-affine`). The vectorizer gives `x[i-1]`, `x[i]` and `x[i+1]`
    separate pointers, initialized before the loop as `x` plus separately computed offsets
    (at `-O3` with alignment peeling: prolog count, +1, +2), so the stencil counted four
    streams, halved its L1 distance and prefetched the same line three times.
  - `ivopts` treats the pointer of `__builtin_prefetch` as an address use
    (`USE_PTR_ADDRESS`, as for the masked load/store internal functions). As a generic use
    the prefetch IV was the cheapest to keep, so the loop pointer was anchored on the far
    prefetch and the accesses became `-2048(%rcx)`; the assembly was equivalent but the
    distances were unreadable in it.
- Stencil scans accept a displacement within 8 bytes of the line: the one prefetched x
  reference is the leading `x[i+1]`, and the loop pointer may be anchored on any of the
  three x accesses.
- Round 3 (lead changes after the card run, 2026-11-08; GCC 8c18be9): the pass's
  `version_loop_for_prefetch`, run only for the two-level target once every check has
  passed and before the loop is unrolled or prefetched. `number_of_iterations_exit` on
  the single exit gives `niter` (one less than the body count); a constant keeps the
  existing trip check, otherwise `loop_version` on `niter >= 4 x far_ahead - 1`, likely
  branch to the prefetched original, the copy untouched (KNC has no `storent` pattern, so
  no store in it was marked nontemporal either). The pass then resets SCEV and asks for
  a CFG cleanup as after unrolling.
