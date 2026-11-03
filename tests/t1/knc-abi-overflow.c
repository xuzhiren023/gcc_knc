/* Probe every argument: an incorrect register budget or stack order must fail. */
volatile float abi_sink_f;
volatile double abi_sink_d;
#define ARGS(T) T a0,T a1,T a2,T a3,T a4,T a5,T a6,T a7,T a8,T a9
#define PROBE(T,S,N) void abi_in_##S##N(ARGS(T)) { abi_sink_##S = a##N; }
#define ALL(T,S) PROBE(T,S,0) PROBE(T,S,1) PROBE(T,S,2) PROBE(T,S,3) \
  PROBE(T,S,4) PROBE(T,S,5) PROBE(T,S,6) PROBE(T,S,7) PROBE(T,S,8) PROBE(T,S,9)
ALL(float,f)
ALL(double,d)
