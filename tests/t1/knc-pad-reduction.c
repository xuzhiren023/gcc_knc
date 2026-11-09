/* S8-10 (E5-16): every thread of the team reads the encountering thread's
   .omp_data_o block and combines its reduction into it with a locked add,
   while the encountering thread's own frames (GOMP_parallel, the outlined
   body) grow just below it.  The block starts a 64-byte line so those
   writes never share its line: the function realigns its frame to 64.  */
// options: -O2 -march=knc -fopenmp
// scan-asm-func reduce_sum: andq\s+\$-64,\s*%rsp
// scan-asm-func reduce_sum: GOMP_parallel
// scan-asm-func reduce_sum._omp_fn.0: lock;?\s*addl
// scan-asm-loop-not reduce_sum._omp_fn.0: %rsp
int
reduce_sum (const int *a, int n)
{
  int s = 0;
#pragma omp parallel for reduction(+:s)
  for (int i = 0; i < n; i++)
    s += a[i];
  return s;
}
