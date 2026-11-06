#ifndef M2_KERNELS_H
#define M2_KERNELS_H
#include <stddef.h>
#include <stdint.h>

/* Integer/pointer ABI shared by C and hand-written assembly. n counts outputs.
   p holds affine a,b or a column-major matrix with leading dimension 16. */
typedef void (*kernel_fn)(void *restrict, const void *restrict,
                          const void *restrict, unsigned long);
#define DECLARE(k, b) void m2_##k##_##b(void *restrict, const void *restrict, \
                                      const void *restrict, unsigned long);
#define BUILDS(k) DECLARE(k, gcc) DECLARE(k, x87) DECLARE(k, imci)
BUILDS(affine_f32)
BUILDS(affine_f64)
BUILDS(stencil1)
BUILDS(stencil2)
BUILDS(short)
BUILDS(mat8)
BUILDS(mat16)
DECLARE(affine_f32, imci_negative)

enum { WIDTH = 64, PITCH = 96, MAX_WORKERS = 240 };
struct kernel { const char *name; kernel_fn fn[3]; int kind, bytes; };
extern const struct kernel kernels[7];
extern const char *build_names[3];
extern unsigned short_length;
struct buffers { void *allocation, *x, *storage, *y, *p, *raw_x, *raw_y; size_t nx, ny; };
void allocate_buffers(struct buffers *, int, unsigned long, unsigned);
void free_buffers(struct buffers *);
void invoke(int, int, struct buffers *, unsigned long);
int correctness(void);
int benchmark(int, char **);
void die(const char *);
#endif
