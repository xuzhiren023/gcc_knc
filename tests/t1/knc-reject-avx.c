// S1-04 / ADR-0002: AVX is not IMCI.
// options: -O2 -march=knc -mavx
// error: (?i)error:[^\n]*(?:avx[^\n]*knc|knc[^\n]*avx)
int knc_reject_avx(void) { return 0; }
