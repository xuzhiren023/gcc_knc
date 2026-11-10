/* S8-14 (E5-13, ADR-0009 point 5): arrays of a 64-byte line or more start
   a line, so vector loops see aligned full lines and masked tails.  Static,
   global and function-scope static arrays get .align 64; a local array
   gets a 64-byte aligned frame slot.  Smaller objects keep their alignment,
   and struct layout (member offset, size) does not change.  */
// options: -O2 -march=knc
// scan-asm: \.align 64\s+\.type\s+g_vec, @object
// scan-asm: \.local\s+s_vec\s+\.comm\s+s_vec,64,64
// scan-asm: \.local\s+f_vec\.\d+\s+\.comm\s+f_vec\.\d+,256,64
// scan-asm: \.align 16\s+\.type\s+g_small, @object
// scan-asm-func local_vec: \bandq\s+\$-64, %rsp
// scan-asm-func local_small: ^\s*subq\s+\$24, %rsp
// scan-asm-func member_offset: \bmovl\s+\$4, %eax
// scan-asm-func member_size: \bmovl\s+\$68, %eax
float g_vec[16];
static double s_vec[8];
float g_small[4];
struct rec { char tag; float v[16]; };

extern void use (void *);

double *s_ptr (void) { return s_vec; }
float *f_ptr (void) { static float f_vec[64]; return f_vec; }
void local_vec (void) { float l[16]; use (l); }
void local_small (void) { int l[4]; use (l); }
int member_offset (void) { return __builtin_offsetof (struct rec, v); }
int member_size (void) { return sizeof (struct rec); }
