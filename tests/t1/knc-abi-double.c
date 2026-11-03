/* S2-02: scalar results must cross the ABI even with x87 bodies. */
volatile double abi_sink_f64;
void abi_in_f64(double x) { abi_sink_f64 = x; }
double abi_out_f64(void) { return 2.5; }
double abi_identity_f64(double x) { return x; }
double abi_body_f64(double x, double y) { return x * y + 2.5; }
/* A lane-store mask can survive across a call and require an HI reload. */
double abi_callback_f64(double (*p)(double), double x) { return p(x) + 0.5; }
/* long double retains its memory argument and st(0) result. */
volatile long double abi_sink_ld;
void abi_in_ld(long double x) { abi_sink_ld = x; }
long double abi_out_ld(void) { return 3.75L; }
