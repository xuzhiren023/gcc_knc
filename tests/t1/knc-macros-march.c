// S1-04: explicit -march=knc has the same ISA macros (ADR-0002).
// options: -O2 -march=knc
#if !defined(__KNC__) || !defined(__k1om__) || !defined(__k1om) || !defined(__x86_64__)
#error KNC explicit target macros are missing
#endif
#if defined(__SSE__) || defined(__SSE2__) || defined(__MMX__) || defined(__AVX__) || defined(__AVX512F__)
#error KNC explicit target must not enable SSE, MMX or AVX
#endif
int knc_macros_march(void) { return 0; }
