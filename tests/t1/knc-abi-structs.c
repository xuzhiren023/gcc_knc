/* SysV eightbytes, including aggregate rollback when only one zmm is free. */
struct df { double d; float f; };
struct ff { float a, b; };
volatile double abi_sink_d;
volatile float abi_sink_f;
void abi_in_df_d(struct df x) { abi_sink_d = x.d; }
void abi_in_df_f(struct df x) { abi_sink_f = x.f; }
void abi_in_ff_a(struct ff x) { abi_sink_f = x.a; }
void abi_in_ff_b(struct ff x) { abi_sink_f = x.b; }
struct df abi_out_df(void) { struct df x = { 2.5, 1.25f }; return x; }
struct ff abi_out_ff(void) { struct ff x = { 1.25f, 3.5f }; return x; }
#define ARGS double a,double b,double c,double d,double e,double f,double g,struct df x,double tail
void abi_in_stack_df_d(ARGS) { abi_sink_d = x.d; }
void abi_in_stack_df_f(ARGS) { abi_sink_f = x.f; }
void abi_in_stack_tail(ARGS) { abi_sink_d = tail; }
