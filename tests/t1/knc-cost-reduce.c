// S6-05: characterization point 1, vaddpd.lat/rt: latency 4, issue
// interval 4 at the default four threads per core, so one chain suffices.
// Runtime n keeps the main loop; fast math explicitly permits reassociation.
// The low-density companion compiles this same loop with one thread per core.
// options: -O3 -march=knc -ffast-math -fvect-cost-model=dynamic -fopt-info-vec-all
// scan-asm-loop-accumulators cheap_reduction: 1
// scan-output: vectorized 1 loops in function
double
cheap_reduction (const double *input, int n)
{
  input = __builtin_assume_aligned (input, 64);
  double sum = 0;
  for (int i = 0; i < n; ++i)
    sum += input[i];
  return sum;
}
