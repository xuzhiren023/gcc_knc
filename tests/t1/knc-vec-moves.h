/* S3-04 fixtures selected independently at -O0 and -O2 by --vector.
   Pointers inherit 64-byte alignment from packed; no function attribute
   supplies stack realignment. All calls use the ordinary scalar ABI. */
#ifndef CASE
#define CASE 1
#endif
extern void packed_clobber(void);

#if CASE >= 11 && CASE <= 15
/* Only element alignment is known, independently for input and output.
   Keep the vector type local: the ordinary scalar ABI carries the pointers. */
typedef __typeof__ (((packed){0})[0]) element;
typedef packed unaligned __attribute__((aligned(__alignof__(element)), may_alias));
struct __attribute__((packed, aligned(__alignof__(element)))) underaligned
{
  element pad;
  packed value;
};

#if CASE == 11
void packed_unknown(const unaligned *input, unaligned *output)
{
  *output = *input;
}
#elif CASE == 12
void packed_unknown_load(const unaligned *input, packed *output)
{
  *output = *input;
}
#elif CASE == 13
void packed_unknown_store(const packed *input, unaligned *output)
{
  *output = *input;
}
#elif CASE == 14
void packed_under_member(const struct underaligned *input,
                         struct underaligned *output)
{
  output->value = input->value;
}
#elif CASE == 15
void packed_unknown_live(const unaligned *input, unaligned *output)
{
  packed saved = *input;
  __asm__ volatile("# packed-live %g0" : "+YJ"(saved));
  packed_clobber();
  __asm__ volatile("# packed-reload %g0" : "+YJ"(saved));
  *output = saved;
}
#endif
#endif

#if CASE == 1
void packed_copy(const packed *input, packed *output)
{
  *output = *input;
}
#elif CASE == 2
void packed_live(const packed *input, packed *output)
{
  packed saved = *input;
  __asm__ volatile("# packed-live %g0" : "+YJ"(saved));
  packed_clobber();
  __asm__ volatile("# packed-reload %g0" : "+YJ"(saved));
  *output = saved;
}
#elif CASE == 3
void packed_zero(packed *output) { *output = (packed){0}; }
#elif CASE == 4
void packed_pool(packed *output) { *output = (packed){PACKED_VALUES}; }
#elif CASE == 5
void packed_arg(packed value, packed *output) { *output = value; }
#elif CASE == 6
packed packed_result(const packed *input) { return *input; }
#elif CASE == 7
struct member { packed value; };
void packed_member(struct member value, packed *output) { *output = value.value; }
#elif CASE == 8
/* The classifier used to return early before checking large struct fields. */
struct large_member { long pad; packed value; };
void packed_large_member(struct large_member value, packed *output)
{ *output = value.value; }
#elif CASE == 9
void packed_pressure(const packed *input, packed *output)
{
  packed v0 = input[0];
  packed v1 = input[1];
  packed v2 = input[2];
  packed v3 = input[3];
  packed v4 = input[4];
  packed v5 = input[5];
  packed v6 = input[6];
  packed v7 = input[7];
  packed v8 = input[8];
  packed v9 = input[9];
  packed v10 = input[10];
  packed v11 = input[11];
  packed v12 = input[12];
  packed v13 = input[13];
  packed v14 = input[14];
  packed v15 = input[15];
  packed v16 = input[16];
  packed v17 = input[17];
  packed v18 = input[18];
  packed v19 = input[19];
  packed v20 = input[20];
  packed v21 = input[21];
  packed v22 = input[22];
  packed v23 = input[23];
  packed v24 = input[24];
  packed v25 = input[25];
  packed v26 = input[26];
  packed v27 = input[27];
  packed v28 = input[28];
  packed v29 = input[29];
  packed v30 = input[30];
  packed v31 = input[31];
  __asm__ volatile("# packed-before %g0 %g1 %g2 %g3 %g4 %g5 %g6 %g7"
    : "+YJ"(v0), "+YJ"(v1), "+YJ"(v2), "+YJ"(v3), "+YJ"(v4), "+YJ"(v5), "+YJ"(v6), "+YJ"(v7) : : "memory");
  __asm__ volatile("# packed-before %g0 %g1 %g2 %g3 %g4 %g5 %g6 %g7"
    : "+YJ"(v8), "+YJ"(v9), "+YJ"(v10), "+YJ"(v11), "+YJ"(v12), "+YJ"(v13), "+YJ"(v14), "+YJ"(v15) : : "memory");
  __asm__ volatile("# packed-before %g0 %g1 %g2 %g3 %g4 %g5 %g6 %g7"
    : "+YJ"(v16), "+YJ"(v17), "+YJ"(v18), "+YJ"(v19), "+YJ"(v20), "+YJ"(v21), "+YJ"(v22), "+YJ"(v23) : : "memory");
  __asm__ volatile("# packed-before %g0 %g1 %g2 %g3 %g4 %g5 %g6 %g7"
    : "+YJ"(v24), "+YJ"(v25), "+YJ"(v26), "+YJ"(v27), "+YJ"(v28), "+YJ"(v29), "+YJ"(v30), "+YJ"(v31) : : "memory");
  packed_clobber();
  __asm__ volatile("# packed-after %g0 %g1 %g2 %g3 %g4 %g5 %g6 %g7"
    : "+YJ"(v0), "+YJ"(v1), "+YJ"(v2), "+YJ"(v3), "+YJ"(v4), "+YJ"(v5), "+YJ"(v6), "+YJ"(v7) : : "memory");
  __asm__ volatile("# packed-after %g0 %g1 %g2 %g3 %g4 %g5 %g6 %g7"
    : "+YJ"(v8), "+YJ"(v9), "+YJ"(v10), "+YJ"(v11), "+YJ"(v12), "+YJ"(v13), "+YJ"(v14), "+YJ"(v15) : : "memory");
  __asm__ volatile("# packed-after %g0 %g1 %g2 %g3 %g4 %g5 %g6 %g7"
    : "+YJ"(v16), "+YJ"(v17), "+YJ"(v18), "+YJ"(v19), "+YJ"(v20), "+YJ"(v21), "+YJ"(v22), "+YJ"(v23) : : "memory");
  __asm__ volatile("# packed-after %g0 %g1 %g2 %g3 %g4 %g5 %g6 %g7"
    : "+YJ"(v24), "+YJ"(v25), "+YJ"(v26), "+YJ"(v27), "+YJ"(v28), "+YJ"(v29), "+YJ"(v30), "+YJ"(v31) : : "memory");
  output[0] = v0;
  output[1] = v1;
  output[2] = v2;
  output[3] = v3;
  output[4] = v4;
  output[5] = v5;
  output[6] = v6;
  output[7] = v7;
  output[8] = v8;
  output[9] = v9;
  output[10] = v10;
  output[11] = v11;
  output[12] = v12;
  output[13] = v13;
  output[14] = v14;
  output[15] = v15;
  output[16] = v16;
  output[17] = v17;
  output[18] = v18;
  output[19] = v19;
  output[20] = v20;
  output[21] = v21;
  output[22] = v22;
  output[23] = v23;
  output[24] = v24;
  output[25] = v25;
  output[26] = v26;
  output[27] = v27;
  output[28] = v28;
  output[29] = v29;
  output[30] = v30;
  output[31] = v31;
}
#elif CASE == 10
void packed_regcopy(const packed *input, packed *output)
{
  register packed low __asm__("zmm0") = *input;
  __asm__ volatile("# packed-source %g0" : "+YJ"(low));
  register packed high __asm__("zmm31") = low;
  __asm__ volatile("# packed-destination %g0" : "+YJ"(high));
  *output = high;
}
#endif
