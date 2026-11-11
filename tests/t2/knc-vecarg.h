/* S10-01: 64-byte vector arguments and results across translation units. */
typedef float v16sf __attribute__((vector_size(64)));
typedef double v8df __attribute__((vector_size(64)));
typedef int v16si __attribute__((vector_size(64)));
typedef long long v8di __attribute__((vector_size(64)));
v16sf vecarg_sf(v16sf, v16sf);
v8df vecarg_df(v8df, v8df);
v16si vecarg_si(v16si, v16si);
v8di vecarg_di(v8di, v8di);
v8df vecarg_mixed(int, float, v8df, double, v16si, long, v8df);
v16sf vecarg_ten(v16sf, v16sf, v16sf, v16sf, v16sf, v16sf, v16sf, v16sf,
                 v16sf, v16sf);
/* Eight doubles fill zmm0-zmm7 and the seventh long is on the stack, so both
   vectors need padding to reach their 64-byte aligned stack slots. */
v8di vecarg_stack(double, double, double, double, double, double, double,
                  double, long, long, long, long, long, long, long, v8di,
                  char, v8di);
