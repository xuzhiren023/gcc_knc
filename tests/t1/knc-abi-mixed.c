/* XImode transport does not advertise a packed vector ABI in Sprint 2. */
#if defined(ABI_VECTOR32_PARAMETER)
typedef int abi_vector32 __attribute__((vector_size(32)));
int abi_vector32_parameter(abi_vector32 x) { return x[0]; }
#elif defined(ABI_VECTOR1_PARAMETER) || defined(ABI_VECTOR1_RESULT)
typedef signed char abi_vector1 __attribute__((vector_size(1)));
#if defined(ABI_VECTOR1_PARAMETER)
int abi_vector1_parameter(abi_vector1 x) { return x[0]; }
#else
extern abi_vector1 abi_vector1_value;
abi_vector1 abi_vector1_result(void) { return abi_vector1_value; }
#endif
#elif defined(ABI_VECTOR_PARAMETER) || defined(ABI_VECTOR_RESULT) || defined(ABI_VECTOR_FIELD)
typedef int abi_vector __attribute__((vector_size(64)));
#if defined(ABI_VECTOR_PARAMETER)
int abi_vector_parameter(abi_vector x) { return x[0]; }
#elif defined(ABI_VECTOR_RESULT)
extern abi_vector abi_vector_value;
abi_vector abi_vector_result(void) { return abi_vector_value; }
#else
struct abi_vector_record { abi_vector x; };
int abi_vector_field(struct abi_vector_record x) { return x.x[0]; }
#endif
#else
/* Each probe makes one incoming location observable without conflating args. */
volatile long abi_sink_i;
volatile float abi_sink_f;
volatile double abi_sink_d;
#define ARGS int i, float f, long j, double d, int k, float g
void abi_in_mix_i(ARGS) { abi_sink_i = i; }
void abi_in_mix_f(ARGS) { abi_sink_f = f; }
void abi_in_mix_j(ARGS) { abi_sink_i = j; }
void abi_in_mix_d(ARGS) { abi_sink_d = d; }
void abi_in_mix_k(ARGS) { abi_sink_i = k; }
void abi_in_mix_g(ARGS) { abi_sink_f = g; }
#endif
