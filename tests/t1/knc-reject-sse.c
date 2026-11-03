// S1-04 / ADR-0002: require a feature conflict, not an unknown -march.
// options: -O2 -march=knc -msse
// error: (?i)error:[^\n]*(?:sse[^\n]*knc|knc[^\n]*sse)
int knc_reject_sse(void) { return 0; }
