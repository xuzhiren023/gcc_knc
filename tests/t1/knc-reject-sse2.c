// S1-04 / ADR-0002: unlike the donor, reject explicit SSE2.
// options: -O2 -march=knc -msse2
// error: (?i)error:[^\n]*(?:sse[^\n]*knc|knc[^\n]*sse)
int knc_reject_sse2(void) { return 0; }
