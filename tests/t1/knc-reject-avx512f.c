// S1-04 / ADR-0002: AVX-512F is not IMCI.
// options: -O2 -march=knc -mavx512f
// error: (?i)error:[^\n]*(?:avx[^\n]*knc|knc[^\n]*avx)
int knc_reject_avx512f(void) { return 0; }
