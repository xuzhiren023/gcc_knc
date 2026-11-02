// S1-04: donor seq_cst fence uses a locked stack operation.
// options: -O2
// scan-asm-not: \b(?:cmov\w*|fcomi\w*|fucomi\w*|mfence)\b
// scan-asm-func knc_fence: \block\b[ \t]*;?\s*or[lq][ \t]+\$0,[ \t]*\(%rsp\)
void knc_fence(void) { __atomic_thread_fence(__ATOMIC_SEQ_CST); }
