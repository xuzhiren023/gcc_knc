/* Correctness gate shared by standalone correctness and every timing launch. */
#include "kernels.h"
#include <malloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

unsigned short_length = 17;
const char *build_names[3] = {"gcc", "x87", "imci"};
#define ROW(k,i,b) {#k, {m2_##k##_gcc,m2_##k##_x87,m2_##k##_imci},i,b}
const struct kernel kernels[7] = {
  ROW(affine_f32,0,4), ROW(affine_f64,1,8), ROW(stencil1,2,4),
  ROW(stencil2,3,4), ROW(short,4,4), ROW(mat8,5,4), ROW(mat16,6,4)
};
void die(const char *s) { fprintf(stderr,"ERROR %s\n",s); exit(2); }
static void *aligned(size_t n) {
  void *p;
  if (posix_memalign(&p,64,n)) die("allocation");
  return p;
}
/* Page-aligned, so a buffer's cache-set placement is the same in every launch (lead, 2026-11-06:
   with 64-byte alignment, M2 times moved up to 20% between launches). */
static void *page_aligned(size_t n) {
  void *p;
  if (posix_memalign(&p,4096,n)) die("allocation");
  return p;
}
void allocate_buffers(struct buffers *b, int k, unsigned long n, unsigned seed) {
  size_t nx = n+48, offset = 16;
  int size = kernels[k].bytes;
  size_t np = k == 6 ? 256 : k == 5 ? 128 : 16;
  if (k == 3) { nx = ((n+WIDTH-1)/WIDTH+2)*PITCH; offset = PITCH+16; }
  if (k >= 5) { unsigned d = k == 5 ? 8 : 16; nx = ((n+d-1)/d)*16+32; offset = 0; }
  b->nx = nx; b->ny = n+32;
  /* A fixed stagger per sibling thread (worker ids run c*density+t) and between x and y keeps the
     four siblings' and the two arrays' 4 KiB set offsets distinct and identical across launches.
     Multiples of 64 bytes keep every kernel's alignment. */
  size_t stagger = (seed%4)*1024;
  b->raw_x = page_aligned(nx*size+stagger);
  b->raw_y = page_aligned(b->ny*size+stagger+512);
  b->allocation = (char *)b->raw_x+stagger;
  b->storage = (char *)b->raw_y+stagger+512;
  b->x = (char *)b->allocation+offset*size;
  b->y = (char *)b->storage+16*size;
  b->p = aligned(np*size);
  if (size == 8) {
    double *x = b->allocation, *y = b->storage, *p = b->p;
    for (size_t i = 0; i < nx; ++i) x[i] = ((int)((i*17+seed*13)%127)-63)*0.25;
    for (size_t i = 0; i < b->ny; ++i) y[i] = -12345;
    for (size_t i = 0; i < np; ++i) p[i] = 0;
    p[0] = 2; p[1] = 0.5;
  } else {
    float *x = b->allocation, *y = b->storage, *p = b->p;
    for (size_t i = 0; i < nx; ++i) x[i] = ((int)((i*17+seed*13)%127)-63)*0.25f;
    for (size_t i = 0; i < b->ny; ++i) y[i] = -12345;
    for (size_t i = 0; i < np; ++i) p[i] = ((int)((i*7+seed*3)%17)-8)*0.25f;
    if (k < 5) { p[0] = 2; p[1] = 0.5f; }
  }
}
void free_buffers(struct buffers *b) { free(b->raw_x); free(b->raw_y); free(b->p); }
void invoke(int k, int build, struct buffers *b, unsigned long n) {
  kernel_fn fn = kernels[k].fn[build];
#ifdef NEGATIVE_CONTROL
  if (k == 0 && build == 2) fn = m2_affine_f32_imci_negative;
#endif
  if (k == 4) {
    for (unsigned long i = 0; i < n; i += short_length) {
      unsigned long count = n-i < short_length ? n-i : short_length;
      fn((float *)b->y+i,(float *)b->x+i,b->p,count);
    }
  } else fn(b->y,b->x,b->p,n);
}
/* Independent scalar oracle, compiled without vectorization/contraction.
   Quarter-integer inputs make every intermediate exactly representable, even
   with x87 extended evaluation: no tolerance or implicit FP-mode change. */
static void reference(int k, struct buffers *b, void *output, unsigned long n) {
  if (k == 1) {
    const double *x = b->x, *p = b->p;
    double *y = output;
    for (unsigned long i = 0; i < n; ++i) y[i] = p[0]*x[i]+p[1];
    return;
  }
  const float *x = b->x, *p = b->p;
  float *y = output;
  for (unsigned long i = 0; i < n; ++i) {
    if (k == 0 || k == 4) y[i] = p[0]*x[i]+p[1];
    else if (k == 2) y[i] = (x[(long)i-1]+x[i])+x[i+1];
    else if (k == 3) {
      long q = (i/WIDTH)*PITCH+i%WIDTH;
      y[i] = (((x[q-PITCH]+x[q-1])+x[q])+x[q+1])+x[q+PITCH];
    } else {
      unsigned d = k == 5 ? 8 : 16;
      float sum = 0;
      for (unsigned j = 0; j < d; ++j)
        sum = sum+p[j*16+i%d]*x[(i/d)*16+j];
      y[i] = sum;
    }
  }
}
static int check(int k, unsigned long n, unsigned seed) {
  struct buffers b;
  allocate_buffers(&b,k,n,seed);
  size_t size = kernels[k].bytes;
  void *want = aligned((n+32)*size);
  reference(k,&b,want,n);
  int failures = 0;
  for (int build = 0; build < 3; ++build) {
    /* Reset output and guards: a missed store must not pass. */
    if (size == 8) for (size_t i = 0; i < b.ny; ++i) ((double *)b.storage)[i] = -12345;
    else for (size_t i = 0; i < b.ny; ++i) ((float *)b.storage)[i] = -12345;
    invoke(k,build,&b,n);
    int bad = 0;
    for (unsigned long i = 0; i < n; ++i)
      if (memcmp((char *)b.y+i*size,(char *)want+i*size,size)) {
        printf("FAIL kernel=%s build=%s length=%lu seed=%u index=%lu\n",
               kernels[k].name,build_names[build],n,seed,i);
        bad = 1; break;
      }
    for (unsigned i = 0; i < 16; ++i) {
      int guard = size == 8
        ? ((double *)b.storage)[i] != -12345 || ((double *)b.y)[n+i] != -12345
        : ((float *)b.storage)[i] != -12345 || ((float *)b.y)[n+i] != -12345;
      if (guard) { printf("FAIL guard kernel=%s build=%s length=%lu\n",
                         kernels[k].name,build_names[build],n); bad = 1; break; }
    }
    failures += bad;
  }
  free(want); free_buffers(&b);
  return failures;
}
int correctness(void) {
  static const unsigned long lengths[] = {
    255,256,257,336,512,1023,1024,1025,4096,5456,8192,16384,262144
  };
  int failures = 0;
  unsigned saved = short_length;
  for (int k = 0; k < 7; ++k) {
    int bad = 0;
    for (unsigned seed = 0; seed < 2; ++seed) {
      for (unsigned n = 0; n <= 64; ++n) {
        if (k == 4) short_length = n ? n : 1;
        bad += check(k,n,seed);
      }
      short_length = saved;
      for (unsigned i = 0; i < sizeof(lengths)/sizeof(*lengths); ++i)
        bad += check(k,lengths[i],seed);
    }
    printf("correctness kernel=%s builds=3 failing_cases=%d\n",kernels[k].name,bad);
    failures += bad;
  }
  short_length = saved;
  return failures ? 1 : 0;
}
int main(int argc, char **argv) {
  /* Workers allocate in their own threads; glibc would give each a 64 MiB arena reservation, and
     240 of them exceed card_run's address-space limit (lead, 2026-11-06). */
  mallopt(M_ARENA_MAX, 2);
  if (argc == 1 || (argc == 2 && !strcmp(argv[1],"--correctness"))) return correctness();
  if (!strcmp(argv[1],"--benchmark")) return benchmark(argc,argv);
  fprintf(stderr,"Use --correctness or --benchmark --kernel NAME --length N "
          "--density 1|2|3|4 --cores 1|60 --launch 1..5 [--short-length 1..64] "
          "[--warmup-seconds 0..60]\n");
  return 2;
}
