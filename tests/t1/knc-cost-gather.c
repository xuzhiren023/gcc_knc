// S6-05: docs/research/knc-characterization.md, gather_scattered.rt:
// 126.70 core cycles for 16 lines at four threads.  A gather-only copy
// cannot amortize that against scalar loads/stores (l1.load_rt and
// l1.store_normal: 1.10 each); unknown indices need a conservative estimate.
// Keep a positive scalar load check so an empty function cannot pass.
// options: -O3 -march=knc -fvect-cost-model=dynamic -fno-tree-slp-vectorize -fopt-info-vec-all
// scan-asm-not: \bvgatherdps\b
// scan-asm-func costly_gather: \b(?:flds|movl)\s+[^\n]*\(
// scan-output: vectorized 0 loops in function
float cost_gather_out[1024] __attribute__((aligned(64)));
int cost_gather_index[1024] __attribute__((aligned(64)));

void
costly_gather (const float *restrict input)
{
  for (int i = 0; i < 1024; ++i)
    cost_gather_out[i] = input[cost_gather_index[i]];
}
