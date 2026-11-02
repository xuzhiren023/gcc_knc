// S1-04: k1om must default to the independent KNC ISA (ADR-0002).
// options: -O2
#if !defined(__KNC__) || !defined(__k1om__) || !defined(__k1om) || !defined(__x86_64__)
#error KNC default target macros are missing
#endif
#if defined(__SSE__) || defined(__SSE2__) || defined(__MMX__) || defined(__AVX__) || defined(__AVX512F__)
#error KNC default target must not enable SSE, MMX or AVX
#endif
int knc_macros_default(void) { return 0; }
