/* S8-11 WRF-shaped column: see column.c.  */
#define COLUMN_NK 51     /* k trips */
#define COLUMN_LD 273    /* floats per k level: a 1092-byte step */
#define COLUMN_NI 8      /* floats per row */
#define COLUMN_NIN 28    /* read arrays; one more is written */

#define COLUMN_ARGS(f)                                                                     \
  float *restrict, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f, f,   \
  f, f, f, f, float
#define COLUMN_IN const float *restrict
void column_pf (COLUMN_ARGS (COLUMN_IN));
void column_nopf (COLUMN_ARGS (COLUMN_IN));
void column_ref (COLUMN_ARGS (COLUMN_IN));
