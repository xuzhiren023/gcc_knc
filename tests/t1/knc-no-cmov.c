// S1-04: exact donor reproducer and branch form, measured 2026-11-02.
// options: -O2
// scan-asm-not: ^[ \t]*(?:cmov\w*|fcomi\w*|fucomi\w*|mfence)\b
// scan-asm-func knc_select: \bjl\b
int knc_select(int a, int b, int c) { return a < b ? c : a; }
