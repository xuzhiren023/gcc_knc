// S1-04 / ADR-0002: KNC does not implement MMX.
// options: -O2 -march=knc -mmmx
// error: (?i)error:[^\n]*(?:mmx[^\n]*knc|knc[^\n]*mmx)
int knc_reject_mmx(void) { return 0; }
