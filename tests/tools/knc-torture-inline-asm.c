// S1-05: invalid user assembly is classified by its #APP block.
// Fixture for test_torture_compile.py; expected to fail assembly.
void knc_torture_inline_asm(void) { __asm__("knc_invalid_instruction"); }
