// S1-04: donor defaults measured by the lead on 2026-11-02.
// options: -O2 -Q --help=target
// scan-output: ^\s*-march=\s+knc\s*$
// scan-output: ^\s*-mtune=\s+knc\s*$
// scan-output: ^\s*-mfpmath=\s+387\s*$
// scan-output: ^\s*-mmmx\s+\[disabled\]\s*$
// scan-output: ^\s*-mcx16\s+\[disabled\]\s*$
// scan-output: ^\s*-mfxsr\s+\[disabled\]\s*$
// scan-output: ^\s*-msahf\s+\[disabled\]\s*$
// scan-output: ^\s*-msse\s+\[disabled\]\s*$
// scan-output: ^\s*-msse2\s+\[disabled\]\s*$
// scan-output: ^\s*-mavx\s+\[disabled\]\s*$
// scan-output: ^\s*-mavx512f\s+\[disabled\]\s*$
int knc_defaults(void) { return 0; }
