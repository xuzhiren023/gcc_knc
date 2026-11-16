// S14-16: synthetic byte decoder, inspired by the scalar register pressure
// in development-corpus zlib inflate_fast. No application code is copied.
// Callers provide valid table widths and enough readable input.
// options: -O2 -march=knc
// scan-asm-func byte_decode: \bmovzbl\b
// scan-asm-loop-not byte_decode: %k[0-7]\b
// scan-asm-not: %k[0-7]\b

struct entry {
  unsigned char width, extra;
  unsigned short base;
};

unsigned long
byte_decode (const unsigned char *input, const unsigned char *end,
             unsigned int *output, unsigned int *limit,
             const struct entry *first, const struct entry *second,
             unsigned long bits, unsigned int available,
             unsigned int first_mask, unsigned int second_mask)
{
  while (input < end && output < limit)
    {
      if (available < 16)
        {
          bits += (unsigned long) *input++ << available;
          available += 8;
          bits += (unsigned long) *input++ << available;
          available += 8;
        }
      const struct entry *a = first + (bits & first_mask);
      unsigned int width = a->width & 15;
      bits >>= width;
      available -= width;
      unsigned int value = a->base;
      unsigned int extra = a->extra & 15;
      if (available < extra)
        {
          bits += (unsigned long) *input++ << available;
          available += 8;
        }
      value += (unsigned int) bits & ((1U << extra) - 1);
      bits >>= extra;
      available -= extra;
      const struct entry *b = second + (bits & second_mask);
      width = b->width & 15;
      bits >>= width;
      available -= width;
      extra = b->extra & 15;
      unsigned int other = b->base;
      if (available < extra)
        {
          bits += (unsigned long) *input++ << available;
          available += 8;
          if (available < extra)
            {
              bits += (unsigned long) *input++ << available;
              available += 8;
            }
        }
      other += (unsigned int) bits & ((1U << extra) - 1);
      bits >>= extra;
      available -= extra;
      *output++ = value + other;
    }
  return bits;
}
