# KNC two-level software prefetch (S8-03, E5-07)

Status: red tests committed 2026-11-08; the green steps below are the plan, not results.

## Rules the T1 scans encode (`tests/t1/knc-prefetch-*.c`)

Source: `docs/research/knc-characterization.md` C2, C4, C5 and the S8-12 rerun.

- `-march=knc` turns `-fprefetch-loop-arrays` on at `-O2` and `-O3` (not `-Os`).
- Every prefetched stream gets `vprefetch1` (L2) at the L2 distance and `vprefetch0` (L1)
  at the L1 distance, L2 ahead of L1. Never L1 without L2 (C5: 1.7-2.3x slower than none).
- Distances are in 64-byte lines of the stream, the unit C5 swept (one line per row
  iteration). For a loop whose iteration moves one line this is C5's iteration count; a
  scalar loop over floats gets 16 x 16 iterations ahead for 16 lines, so a line's prefetch
  is still issued once (the pass's `prefetch_mod`).
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
- Written streams use the read-hint forms `vprefetch0/1`, as C5's kernels did for their
  output array. `vprefetche*` is unmeasured and not emitted.

## Green plan

- `imci.md`: one `(prefetch ...)` insn under `TARGET_KNC`, locality 3/2/1/0 to
  `vprefetch0/1/2/nta` (Intel 327364-001 pp. 641-656); write hint dropped like the SSE path.
  `knc.md`: prefetches take a scalar slot (C2: `vprefetch0` pairs free with a vector op).
- `i386.md` `prefetch` expander: `|| TARGET_KNC` in the condition and an early KNC emit
  (ADR-0006 forms). This also makes `__builtin_prefetch` work on KNC.
- `tree-ssa-loop-prefetch.cc`: a target hook `TARGET_PREFETCH_DISTANCES (nstreams, &near,
  &far)` in lines, consulted after reuse pruning; when it answers, `ahead` comes from it and
  a second prefetch at the far distance is issued with locality 2 (1 for nontemporal). With
  the hook unset (every other target) the pass is unchanged. `target.def`, `tm.texi.in`,
  `tm.texi`: one hook entry.
- `i386.cc`: one hook table entry to `ix86_knc_prefetch_distances` (`i386-knc.cc`).
- `i386.opt`: the two `-param=knc-prefetch-*-distance=` params, `Param Optimization`.
- `i386-options.cc`: the existing `-mtune=knc` block calls `ix86_knc_prefetch_params`, which
  sets `-fprefetch-loop-arrays` at `-O2`+, `min-insn-to-prefetch-ratio` and
  `prefetch-min-insn-to-mem-ratio` to 1 (an eight-stream loop is two instructions per
  reference; C2 prices `vprefetch0` at zero and `vprefetch1` at about 2 core cycles), and
  `simultaneous-prefetches` so eight streams at 16 lines are not refused.
