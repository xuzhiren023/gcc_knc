// S1-04: donor x87 comparison; long double uses the stack ABI.
// options: -O2
// scan-asm-not: \b(?:cmov\w*|fcomi\w*|fucomi\w*|mfence|sahf)\b
// scan-asm-func knc_less: \bfucompp\b
// scan-asm-func knc_less: \bfnstsw\b
// scan-asm-func knc_less: \btestb\b
// scan-asm-func knc_less: \bsete\b
int knc_less(long double a, long double b) { return a < b; }
