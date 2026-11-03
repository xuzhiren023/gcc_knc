// S1-04: donor x87 comparison; long double uses the stack ABI.
// options: -O2
// scan-asm-not: ^[ \t]*(?:cmov\w*|fcomi\w*|fucomi\w*|mfence|sahf)\b
// scan-asm-func knc_less: ^[ \t]*fu?comp{0,2}\b
// scan-asm-func knc_less: \bfnstsw\b
// scan-asm-func knc_less: ^[ \t]*(?:testb|andb)\b
// scan-asm-func knc_less: ^[ \t]*set[a-z]+\b
int knc_less(long double a, long double b) { return a < b; }
