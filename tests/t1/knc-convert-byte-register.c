// S12-32, ADR-0008 point 7; Intel 327364-001 pp.379-384.
// A byte/word vector that keeps a register (its extension is colder than its
// definitions) must reload through an aligned stack slot: the up-conversion
// reads memory only.  masked_local_s8 is reduced from gcc.dg/vect/O3-vect-pr32243.c.
// options: -O3
// scan-asm-not: %[xy]mm\d+
// scan-asm-func cold_u8: \bvmovdqa32\s+-?\d*\(%r[sb]p\)\{uint8\},\s*%zmm\d+
// scan-asm-func cold_s16: \bvmovdqa32\s+-?\d*\(%r[sb]p\)\{sint16\},\s*%zmm\d+
// scan-asm-func masked_local_s8: \bvmovdqa32\s+-?\d*\(%r[sb]p\)\{sint8\},\s*%zmm\d+
typedef unsigned char bytes __attribute__((vector_size(16)));
typedef short words __attribute__((vector_size(32)));
typedef int dwords __attribute__((vector_size(64)));

dwords cold_u8 (bytes *p, int n, int c)
{
  bytes b = p[0];
  for (int i = 1; i < n; i++)
    if (p[i][0])
      b = p[i];
  if (__builtin_expect (c, 0))
    return __builtin_convertvector (b, dwords);
  return (dwords) {};
}

dwords cold_s16 (words *p, int n, int c)
{
  words w = p[0];
  for (int i = 1; i < n; i++)
    if (p[i][0])
      w = p[i];
  if (__builtin_expect (c, 0))
    return __builtin_convertvector (w, dwords);
  return (dwords) {};
}

void sink (int *);
void masked_local_s8 (int count, const char *value, const char *mask)
{
  int temp[4096], i;
  const char val = *value;
  for (i = 0; i < count; i++)
    if (!mask || mask[i])
      temp[i] = (temp[i] & 0xffffff) | val;
  sink (temp);
}
