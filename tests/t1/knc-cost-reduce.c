// S6-05: docs/research/knc-characterization.md, vaddpd.rt,
// vpermf32x4.rt and swizzle_*.rt: one core cycle each at four threads.
// A single vector load and the reduction tree should beat eight scalar
// loads/x87 adds (l1.load_rt and x87_add.rt).  Reassociation is explicitly
// permitted here; the cost change must not imply fast math for other code.
// options: -O3 -march=knc -ffast-math -fvect-cost-model=dynamic -fno-tree-slp-vectorize -fopt-info-vec-all
// scan-asm-func cheap_reduction: \bvaddpd\s
// scan-output: vectorized 1 loops in function
double
cheap_reduction (const double *input)
{
  input = __builtin_assume_aligned (input, 64);
  double sum = 0;
  for (int i = 0; i < 8; ++i)
    sum += input[i];
  return sum;
}
