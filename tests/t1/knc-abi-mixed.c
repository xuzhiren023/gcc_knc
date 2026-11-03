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
