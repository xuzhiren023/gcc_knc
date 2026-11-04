/* S3-21: selected by --vector-byte-aligned for all four modes at O2/O3.
   The S3-05 --vector-unaligned probes retain the element-aligned pair counts.
   No vector values cross the ABI. */
#ifndef SCALAR
#define SCALAR int
#define ELEMENT_BYTES 4
#endif
typedef SCALAR scalar;
typedef scalar vector __attribute__((vector_size(64)));
typedef vector byte_vector __attribute__((aligned(1), may_alias));
extern void consume(const void *);

/* pr65369's unrolled small memcpy shape, with only byte source alignment.
   Four-byte elements reproduce its sixteen pieces exactly. */
void byte_slp(const unsigned char *block)
{
  scalar buf[64 / ELEMENT_BYTES];
#define PIECE(N) __builtin_memcpy(buf + (N), block + (N) * ELEMENT_BYTES, ELEMENT_BYTES)
  PIECE(0); PIECE(1); PIECE(2); PIECE(3);
  PIECE(4); PIECE(5); PIECE(6); PIECE(7);
#if ELEMENT_BYTES == 4
  PIECE(8); PIECE(9); PIECE(10); PIECE(11);
  PIECE(12); PIECE(13); PIECE(14); PIECE(15);
#endif
#undef PIECE
  consume(buf);
}

/* Exercise the loop vectorizer with the same byte-aligned memory type.
   A fixed full-vector count also exercises O2's very-cheap cost model. */
void byte_loop(vector *output, const unsigned char *input)
{
  scalar *dest = (scalar *) output;
  for (unsigned i = 0; i < 64 / ELEMENT_BYTES; ++i)
    __builtin_memcpy(dest + i, input + i * ELEMENT_BYTES, ELEMENT_BYTES);
}

void byte_load(const byte_vector *input, vector *output)
{
  vector value = *input;
  __asm__ volatile("# byte-value %g0" : "+YJ"(value));
  *output = value;
}

void byte_store(const vector *input, byte_vector *output)
{
  vector value = *input;
  __asm__ volatile("# byte-value %g0" : "+YJ"(value));
  *output = value;
}

/* All sub-element offsets, with known vector alignment on the other side.
   Force a vector register so the explicit move expander must handle the MEM. */
#define MEMBER(N)                                                        \
  struct __attribute__((packed)) member_##N                              \
  { unsigned char pad[N]; vector value; };                               \
  void load_member_##N(const struct member_##N *input, vector *output)    \
  {                                                                     \
    vector value = input->value;                                        \
    __asm__ volatile("# member-value %g0" : "+YJ"(value));               \
    *output = value;                                                     \
  }                                                                     \
  void store_member_##N(const vector *input, struct member_##N *output)   \
  {                                                                     \
    vector value = *input;                                              \
    __asm__ volatile("# member-value %g0" : "+YJ"(value));               \
    output->value = value;                                               \
  }
MEMBER(1)
MEMBER(2)
MEMBER(3)
#if ELEMENT_BYTES == 8
MEMBER(4)
MEMBER(5)
MEMBER(6)
MEMBER(7)
#endif
