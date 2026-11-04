/* S3-21 card probe, run by the lead after building at -O2 and -O3:
   xgcc -B<build>/ -O2 -march=knc tests/t2/knc-vec-byte-aligned.c -o <shared>/byte-aligned
   tools/card_run <shared>/byte-aligned
   Four modes, all 64x64 source/destination offsets, both guard boundaries.
   Explicit byte vectors, pr65369-shaped SLP, element-aligned pairs and
   packed members share byte-exact payload and sentinel checks. */
#define _GNU_SOURCE
#include <sys/mman.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef void (*copy_fn)(unsigned char *, const unsigned char *);
#define NOIPA __attribute__((noipa))
#define COPY_PIECE(N) __builtin_memcpy(tmp + (N), src + (N) * sizeof(tmp[0]), sizeof(tmp[0]))
#define MEMBER(TAG, N)                                                    \
  struct __attribute__((packed)) TAG##_member_##N                         \
  { unsigned char pad[N]; TAG##_vec value; };                             \
  static NOIPA void TAG##_packed_##N(unsigned char *dst,                   \
                                     const unsigned char *src)           \
  {                                                                      \
    const struct TAG##_member_##N *s = (const void *)(src - N);            \
    struct TAG##_member_##N *d = (void *)(dst - N);                        \
    TAG##_vec v = s->value;                                               \
    __asm__ volatile ("" : "+YJ"(v));                                    \
    d->value = v;                                                        \
  }
#define MODE(TAG, T, COUNT)                                               \
  typedef T TAG##_vec __attribute__((vector_size(64)));                    \
  typedef TAG##_vec TAG##_byte __attribute__((aligned(1), may_alias));     \
  typedef TAG##_vec TAG##_elem __attribute__((aligned(sizeof(T)), may_alias)); \
  static NOIPA void TAG##_bytecopy(unsigned char *dst, const unsigned char *src) \
  {                                                                      \
    TAG##_vec v = *(const TAG##_byte *)src;                               \
    __asm__ volatile ("" : "+YJ"(v));                                    \
    *(TAG##_byte *)dst = v;                                               \
  }                                                                      \
  static NOIPA void TAG##_elemcopy(unsigned char *dst, const unsigned char *src) \
  {                                                                      \
    TAG##_vec v = *(const TAG##_elem *)src;                               \
    __asm__ volatile ("" : "+YJ"(v));                                    \
    *(TAG##_elem *)dst = v;                                               \
  }                                                                      \
  static NOIPA void TAG##_slp(unsigned char *dst, const unsigned char *src) \
  {                                                                      \
    T tmp[COUNT];                                                        \
    COPY_PIECE(0); COPY_PIECE(1); COPY_PIECE(2); COPY_PIECE(3);             \
    COPY_PIECE(4); COPY_PIECE(5); COPY_PIECE(6); COPY_PIECE(7);             \
    if (COUNT == 16)                                                      \
      {                                                                  \
        COPY_PIECE(8); COPY_PIECE(9); COPY_PIECE(10); COPY_PIECE(11);       \
        COPY_PIECE(12); COPY_PIECE(13); COPY_PIECE(14); COPY_PIECE(15);     \
      }                                                                  \
    __builtin_memcpy(dst, tmp, 64);                                       \
  }                                                                      \
  MEMBER(TAG, 1) MEMBER(TAG, 2) MEMBER(TAG, 3)
MODE(sf, float, 16)
MODE(df, double, 8)
MODE(si, int, 16)
MODE(di, long long, 8)
MEMBER(df, 4) MEMBER(df, 5) MEMBER(df, 6) MEMBER(df, 7)
MEMBER(di, 4) MEMBER(di, 5) MEMBER(di, 6) MEMBER(di, 7)

struct mode_case {
  const char *name;
  unsigned size;
  copy_fn bytecopy, slp, elemcopy, packed[7];
};
#define ROW(TAG, SIZE, ...) { #TAG, SIZE, TAG##_bytecopy, TAG##_slp, TAG##_elemcopy, \
  { TAG##_packed_1, TAG##_packed_2, TAG##_packed_3, __VA_ARGS__ } }
static const struct mode_case modes[] = {
  ROW(sf, 4, 0),
  ROW(df, 8, df_packed_4, df_packed_5, df_packed_6, df_packed_7),
  ROW(si, 4, 0),
  ROW(di, 8, di_packed_4, di_packed_5, di_packed_6, di_packed_7)
};

static unsigned char *map_guarded(size_t page)
{
  unsigned char *p = mmap(0, 3 * page, PROT_NONE,
                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (p == MAP_FAILED || mprotect(p + page, page, PROT_READ | PROT_WRITE))
    { perror("guard mapping"); exit(2); }
  return p + page;
}

static size_t position(size_t page, unsigned offset, unsigned end)
{
  /* At the end, residue zero ends exactly at the guard.  Residues 1-63
     leave 63-1 bytes of checked sentinels before it. */
  return end ? page - (offset ? 128 : 64) + offset : offset;
}

int main(void)
{
  long page_size = sysconf(_SC_PAGESIZE);
  if (page_size < 256 || page_size % 64) return 2;
  size_t page = page_size;
  unsigned char *source = map_guarded(page), *dest = map_guarded(page);
  for (unsigned m = 0; m < 4; ++m)
    for (unsigned ends = 0; ends < 4; ++ends)
      for (unsigned so = 0; so < 64; ++so)
        for (unsigned doff = 0; doff < 64; ++doff)
          {
            size_t sp = position(page, so, ends & 1);
            size_t dp = position(page, doff, ends & 2);
            const struct mode_case *mc = modes + m;
            for (unsigned kind = 0; kind < mc->size + 2; ++kind)
              {
                copy_fn fn = kind == 0 ? mc->bytecopy : kind == 1 ? mc->slp
                           : kind == 2 ? mc->elemcopy : mc->packed[kind - 3];
                if (kind == 2 && (so % mc->size || doff % mc->size)) continue;
                /* A packed base points N bytes before its member. */
                if (kind > 2 && (sp < kind - 2 || dp < kind - 2)) continue;
                memset(source, 0xa5, page);
                memset(dest, 0x5a, page);
                for (unsigned i = 0; i < 64; ++i)
                  source[sp + i] = (unsigned char)(37 * i + 13 * m);
                fn(dest + dp, source + sp);
                /* A full cache line of sentinels on either side catches
                   writes by either half of an illegal packed store.  */
                for (long rel = -64; rel < 128; ++rel)
                  {
                    long si = (long)sp + rel, di = (long)dp + rel;
                    unsigned char payload = (unsigned char)(37 * rel + 13 * m);
                    unsigned char expected_src = rel >= 0 && rel < 64 ? payload : 0xa5;
                    unsigned char expected_dst = rel >= 0 && rel < 64 ? payload : 0x5a;
                    if ((si >= 0 && si < (long)page
                         && ((volatile unsigned char *)source)[si] != expected_src)
                        || (di >= 0 && di < (long)page
                            && ((volatile unsigned char *)dest)[di] != expected_dst))
                      {
                        printf("FAIL %s ends=%u src=%u dst=%u kind=%u rel=%ld\n",
                               mc->name, ends, so, doff, kind, rel);
                        return 1;
                      }
                  }
              }
          }
  munmap(source - page, 3 * page);
  munmap(dest - page, 3 * page);
  puts("PASS S3-21 all four modes, source/destination offsets 0-63, sentinels and guards");
  return 0;
}
