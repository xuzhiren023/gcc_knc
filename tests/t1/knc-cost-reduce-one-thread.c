// S6-05: docs/research/knc-characterization.md point 1, vaddpd.lat/rt:
// one thread issues every other cycle with latency 4; at least two
// independent accumulators hide the latency.  Use the existing x86
// reduc_lat_mult_thr / vect_unroll_limit path, not forced loop unrolling.
// --param=knc-threads-per-core is the proposed density parameter (default 4).
// options: -O3 -march=knc -ffast-math -fvect-cost-model=dynamic --param=knc-threads-per-core=1 -fopt-info-vec-all
// scan-asm-loop-accumulators cheap_reduction: 2+
// scan-output: vectorized 1 loops in function
#include "knc-cost-reduce.c"
