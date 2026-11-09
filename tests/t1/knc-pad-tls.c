/* S8-10 (E5-16): per-thread arrays start a 64-byte line, as static data of
   a line or more already does (prefetch_block 64).  Generic varasm caps TLS
   alignment at a word, so a thread's array would straddle two lines.
   __thread and OpenMP threadprivate alike; scalars and external
   declarations keep their ABI alignment.  */
// options: -O2 -march=knc -fopenmp
// scan-asm: \.align 64\s+\.type\s+tls_hist, @object
// scan-asm: \.align 64\s+\.type\s+tp_part, @object
// scan-asm: \.align 4\s+\.type\s+tls_count, @object
__thread int tls_hist[16];
__thread int tls_count;
static double tp_part[8];
#pragma omp threadprivate(tp_part)
extern __thread double tls_ext[8];

double *part (void) { return tp_part; }
double ext (int i) { return tls_ext[i]; }
