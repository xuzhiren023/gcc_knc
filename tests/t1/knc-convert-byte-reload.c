// S5-16: reduced from gcc.c-torture/compile/pr60502.c.
// A scalarized byte operation must reload its transport-mode result.
// options: -O0
typedef signed char bytes __attribute__((vector_size(16)));
void byte_reload (bytes *p)
{
  bytes ones = {-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1};
  *p |= *p ^ ones;
}
