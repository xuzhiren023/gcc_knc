// S1-04: donor reproducer; accept either conditional-branch direction.
// options: -O2
// scan-asm-not: ^[ \t]*(?:cmov\w*|fcomi\w*|fucomi\w*|mfence)\b
// scan-asm-func knc_select: ^[ \t]*j(?!mp\b)[a-z]+\b
int knc_select(int a, int b, int c) { return a < b ? c : a; }
