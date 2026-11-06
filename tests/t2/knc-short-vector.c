/* S5-21: a 32-byte short vector result uses a hidden result pointer.
   Distinct constants keep the whole result observable without an argument
   whose ABI could conceal a mistaken register-return convention. */
typedef unsigned short __attribute__((__vector_size__ (32))) V;

V
short_vector_return (void)
{
  return (V) { 1, 2, 3, 4, 5, 6, 7, 8,
               9, 10, 11, 12, 13, 14, 15, 16 };
}
