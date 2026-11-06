// S5-16: reduced vector constructor from pr82052.c's vec_initv16qiqi ICE.
// Transport-mode constructors must not enter SSE duplicate expansion.
// options: -O2
typedef unsigned char bytes __attribute__((vector_size(16)));
void byte_init (bytes *p, unsigned char c)
{
  *p = (bytes) {c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c};
}
