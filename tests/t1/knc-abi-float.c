/* S2-02: compared with donor assembly by tools/check --scalar-abi. */
#if defined(__SSE__) || defined(__SSE2__) || defined(__AVX__) || defined(__AVX512F__)
#error KNC must not enable SSE or AVX
#endif
volatile float abi_sink_f32;
void abi_in_f32(float x) { abi_sink_f32 = x; }
float abi_out_f32(void) { return 1.25f; }
float abi_identity_f32(float x) { return x; }
float abi_body_f32(float x, float y) { return x * y + 1.25f; }
