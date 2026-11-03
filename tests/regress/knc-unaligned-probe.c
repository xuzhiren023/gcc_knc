/* S3-03: Intel 327364-001, ch.6 VLOADUNPACK*/
/* Build with -DHOST_LOGIC for T0; only the KNC build accepts --native.
   A is the logical stream base; every high instruction uses A+64.
   Offsets are ELEMENT offsets, 0..63, not byte offsets. */
#define _GNU_SOURCE 1
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { PAIR, LOW, HIGH, ALIGNED };
enum { INSIDE_START, INSIDE_END, CROSS_START, CROSS_END, MASK_START,
       MASK_END, HIGH_END, ALIGN_END, ALIGN_GUARD, MISALIGNED, GROUPS };
struct probe_case {
  int type, store, form, group, offset, address;
  unsigned mask;
};
#ifndef HOST_LOGIC
static const char *const types[] = { "ps", "pd", "d", "q" };
static const char *const forms[] = { "pair", "low", "high", "aligned" };
static const char *const groups[] = {
  "inside-start", "inside-end", "cross-start", "cross-end", "mask-start",
  "mask-end", "high-end", "aligned-end", "aligned-guard", "misaligned"
};
#endif
static struct probe_case cases[4096];
static int count;
static int width(int type) { return (type & 1) ? 8 : 4; }
static unsigned full_mask(int type) { return (1u << (64 / width(type))) - 1; }
#ifndef HOST_LOGIC
static unsigned char memory_byte(int i) { return (unsigned char)(1 + i % 127); }
#endif

static void add(int t, int st, int f, int g, int o, int a, unsigned m)
{
  struct probe_case c = { t, st, f, g, o, a, m };
  if (count == (int)(sizeof cases / sizeof cases[0])) abort();
  cases[count++] = c;
}

static unsigned mapped_mask(int a, int size, int page)
{
  unsigned m = 0;
  int lane;
  for (lane = 0; lane < 64 / size; ++lane)
    if (a + lane * size >= 0 && a + (lane + 1) * size <= page)
      m |= 1u << lane;
  return m;
}

static void make_cases(int page)
{
  int t, st, o, g, f, empty;
  count = 0;
  for (t = 0; t < 4; ++t) {
    int size = width(t), lanes = 64 / size;
    unsigned all = full_mask(t);
    for (st = 0; st < 2; ++st) {
      for (o = 0; o < 64; ++o) {
        add(t, st, PAIR, INSIDE_START, o, o * size, all);
        add(t, st, PAIR, INSIDE_END, o, page - 64 - o * size, all);
        add(t, st, PAIR, CROSS_START, o, -o * size, all);
        add(t, st, PAIR, CROSS_END, o, page - 64 + o * size, all);
      }
      for (o = 1; o < lanes; ++o)
        for (g = MASK_START; g <= MASK_END; ++g) {
          int a = g == MASK_START ? -o * size : page - 64 + o * size;
          for (f = PAIR; f <= HIGH; ++f)
            for (empty = 0; empty < 2; ++empty)
              add(t, st, f, g, o, a, empty ? 0 : mapped_mask(a, size, page));
        }
      add(t, st, HIGH, HIGH_END, 0, page - 64, all);
      add(t, st, ALIGNED, ALIGN_END, 0, page - 64, all);
      add(t, st, ALIGNED, ALIGN_END, 0, page - 64, 0);
      add(t, st, ALIGNED, ALIGN_GUARD, 0, page, 1);
      add(t, st, ALIGNED, ALIGN_GUARD, 0, page, 0);
    }
    /* One crossing alignment control per type (load only). */
    add(t, 0, ALIGNED, MISALIGNED, 1, page - 32, all);
  }
}

struct transfer { int lane, address; };
/* Enumerate actual packed/expanded stream positions, NOT lane*size positions.
   step=0: low, step=1: high, step=2: ordinary aligned move. */
static int transfers(const struct probe_case *c, int step, struct transfer *out)
{
  int lane, rank = 0, n = 0, size = width(c->type);
  int boundary = (c->address + 64) & ~63;
  for (lane = 0; lane < 64 / size; ++lane) if (c->mask & (1u << lane)) {
    int a = c->address + (step == 2 ? lane : rank) * size;
    if (step == 2 || (step == 0 ? a < boundary : a >= boundary)) {
      out[n].lane = lane;
      out[n++].address = a;
    }
    ++rank;
  }
  return n;
}

static void source_bytes(int type, unsigned char *src)
{
  int lane;
  /* Finite, normal, exact IEEE values; the integer forms use the same bits. */
  for (lane = 0; lane < 64 / width(type); ++lane) {
    if (width(type) == 4) {
      uint32_t bits = 0x3f800000u + (unsigned)lane * 0x10000u;
      memcpy(src + lane * 4, &bits, 4);
    } else {
      uint64_t bits = UINT64_C(0x3ff0000000000000) + (uint64_t)lane * UINT64_C(0x10000000000);
      memcpy(src + lane * 8, &bits, 8);
    }
  }
}

/* A store fault may leave a subset of the permitted bytes written. Every
   changed byte must still have the right value at the right position.
   Scan the ENTIRE mapped page, not just the nominal vector range. */
static int check_store(const unsigned char *actual, const unsigned char *want,
                       const unsigned char *allowed, int page, int fault,
                       int *changed, int *sentinel)
{
  int i, bad = 0;
  *changed = *sentinel = 0;
  for (i = 0; i < page; ++i) {
    if (actual[i] != 0xa5) {
      ++*changed;
      if (!allowed[i]) { ++*sentinel; ++bad; }
      else if (actual[i] != want[i]) ++bad;
    } else if (!fault && allowed[i] && want[i] != 0xa5) ++bad;
  }
  return bad;
}

static void store_model(const struct probe_case *c, int page,
                        const unsigned char *src, unsigned char *want,
                        unsigned char *allowed)
{
  int step, n, i, b, size = width(c->type);
  struct transfer tr[16];
  memset(want, 0xa5, page);
  memset(allowed, 0, page);
  for (step = 0; step < 3; ++step) {
    if (c->form == PAIR ? step == 2 :
        step != (c->form == ALIGNED ? 2 : c->form == HIGH)) continue;
    n = transfers(c, step, tr);
    for (i = 0; i < n; ++i)
      for (b = 0; b < size; ++b) {
        int a = tr[i].address + b;
        if (a >= 0 && a < page) {
          allowed[a] = 1;
          want[a] = src[tr[i].lane * size + b];
        }
      }
  }
}

#define REQUIRE(x) do { if (!(x)) { \
  fprintf(stderr, "T0 failed line %d: %s\n", __LINE__, #x); return 1; } } while (0)

static int self_test(void)
{
  int i, t, st, o, g, f, empty, changed, sentinel, seen[4][2][4][64] = {{{{0}}}};
  int masks[4][2][2][3][16][2] = {{{{{{0}}}}}};
  int totals[GROUPS] = {0};
  unsigned char actual[4096], want[4096], allowed[4096], src[64];
  struct transfer tr[16];
  struct probe_case c = { 0, 1, PAIR, MASK_END, 0, 4096 - 12, 7 };
  make_cases(4096);
  REQUIRE(count == 3148);
  for (i = 0; i < count; ++i) {
    const struct probe_case *p = cases + i;
    int size = width(p->type);
    REQUIRE(p->address >= -4096 && p->address + 128 <= 8192);
    REQUIRE(p->address % size == 0 && !(p->mask & ~full_mask(p->type)));
    ++totals[p->group];
    if (p->group <= CROSS_END) {
      int expected_address = p->group == INSIDE_START ? p->offset * size :
        p->group == INSIDE_END ? 4096 - 64 - p->offset * size :
        p->group == CROSS_START ? -p->offset * size : 4096 - 64 + p->offset * size;
      REQUIRE(p->address == expected_address && p->mask == full_mask(p->type) && p->form == PAIR);
      ++seen[p->type][p->store][p->group][p->offset];
    }
    if (p->group == MASK_START || p->group == MASK_END) {
      unsigned m = mapped_mask(p->address, size, 4096);
      REQUIRE(m && m != full_mask(p->type));
      REQUIRE(p->mask == 0 || p->mask == m);
      ++masks[p->type][p->store][p->group - MASK_START][p->form][p->offset][p->mask == 0];
    }
    if (p->group == HIGH_END) REQUIRE(p->form == HIGH && p->address + 64 == 4096);
    if (p->group == ALIGN_END) REQUIRE(p->address == 4032 && p->form == ALIGNED);
    if (p->group == ALIGN_GUARD) REQUIRE(p->address == 4096 && p->form == ALIGNED);
    if (p->group == MISALIGNED) REQUIRE(p->address % 64 == 32 && !p->store);
  }
  for (t = 0; t < 4; ++t) for (st = 0; st < 2; ++st) {
    for (g = 0; g < 4; ++g) for (o = 0; o < 64; ++o)
      REQUIRE(seen[t][st][g][o] == 1);
    for (g = 0; g < 2; ++g) for (f = 0; f < 3; ++f)
      for (o = 1; o < 64 / width(t); ++o) for (empty = 0; empty < 2; ++empty)
        REQUIRE(masks[t][st][g][f][o][empty] == 1);
  }
  REQUIRE(totals[HIGH_END] == 8 && totals[ALIGN_END] == 16);
  REQUIRE(totals[ALIGN_GUARD] == 16 && totals[MISALIGNED] == 4);
  /* Independent known answers: end-prefix fits exactly; start-suffix is
     compacted into the guard, NOT moved to the first mapped lane. */
  REQUIRE(transfers(&c, 0, tr) == 3 && tr[2].address == 4092);
  REQUIRE(transfers(&c, 1, tr) == 0);
  c.address = -12; c.mask = 0xfff8;
  REQUIRE(transfers(&c, 0, tr) == 3 && tr[0].lane == 3 && tr[0].address == -12);
  REQUIRE(transfers(&c, 1, tr) == 10 && tr[0].lane == 6 && tr[0].address == 0);
  c.address = 4032; c.mask = 0xffff;
  REQUIRE(transfers(&c, 1, tr) == 0);
  /* Sentinel checker must reject both-side overruns, wrong data and missing
     writes, while accepting valid full and partial faulted writes. */
  c.address = 128; c.mask = 7;
  source_bytes(0, src);
  store_model(&c, 4096, src, want, allowed);
  REQUIRE(allowed[128] && allowed[139] && !allowed[127] && !allowed[140]);
  memcpy(actual, want, sizeof actual);
  REQUIRE(!check_store(actual, want, allowed, 4096, 0, &changed, &sentinel) && changed == 12);
  actual[127] = 1; actual[140] = 2;
  REQUIRE(check_store(actual, want, allowed, 4096, 0, &changed, &sentinel) && sentinel == 2);
  memcpy(actual, want, sizeof actual); actual[128] ^= 1;
  REQUIRE(check_store(actual, want, allowed, 4096, 0, &changed, &sentinel));
  memset(actual, 0xa5, sizeof actual); actual[128] = want[128];
  REQUIRE(!check_store(actual, want, allowed, 4096, 1, &changed, &sentinel) && changed == 1);
  REQUIRE(check_store(actual, want, allowed, 4096, 0, &changed, &sentinel));
  puts("T0 PASS: 3148 cases; all type/direction/offset/mask/half controls; sentinel negative controls");
  return 0;
}

#ifndef HOST_LOGIC
#include <signal.h>
#include <setjmp.h>
#include <sys/mman.h>
#include <unistd.h>
static sigjmp_buf recovery;
static volatile sig_atomic_t armed, signal_number, signal_code, phase;
static void *volatile signal_address;
static unsigned char src[64] __attribute__((aligned(64)));
static unsigned char output[64] __attribute__((aligned(64)));

static void handler(int sig, siginfo_t *info, void *context)
{
  (void)context;
  if (!armed) _exit(128 + sig);
  signal_number = sig;
  signal_code = info->si_code;
  signal_address = info->si_addr;
  siglongjmp(recovery, 1);
}

/* Checkpoint the completed low load before high, so a fault leaves an honest
   count of committed load lanes. The faulting load's register state is NOT
   observable here. Stores are inspected directly after recovery. */
#define LOAD_ONE(op, displacement) \
  __asm__ volatile ("vmovdqa32 (%[out]), %%zmm0\n\t" \
                    "kmov %[mask], %%k1\n\t" \
                    op " " displacement "(%[a]), %%zmm0%{%%k1%}\n\t" \
                    "vmovdqa32 %%zmm0, (%[out])" \
    : : [out] "r"(output), [a] "r"(a), [mask] "r"(mask) : "zmm0", "k1", "memory")
#define STORE_ONE(op, displacement) \
  __asm__ volatile ("vmovdqa32 (%[src]), %%zmm0\n\t" \
                    "kmov %[mask], %%k1\n\t" \
                    op " %%zmm0, " displacement "(%[a])%{%%k1%}" \
    : : [src] "r"(src), [a] "r"(a), [mask] "r"(mask) : "zmm0", "k1", "memory")
#define OPS(suffix, aligned) \
  if (!c->store) { \
    if (c->form == ALIGNED) { LOAD_ONE(aligned, ""); } \
    else { \
      if (c->form != HIGH) { LOAD_ONE("vloadunpackl" suffix, ""); phase = 1; } \
      if (c->form != LOW) { LOAD_ONE("vloadunpackh" suffix, "64"); } \
    } \
  } else { \
    if (c->form == ALIGNED) { STORE_ONE(aligned, ""); } \
    else { \
      if (c->form != HIGH) { STORE_ONE("vpackstorel" suffix, ""); phase = 1; } \
      if (c->form != LOW) { STORE_ONE("vpackstoreh" suffix, "64"); } \
    } \
  }

__attribute__((noinline)) static void execute(const struct probe_case *c, unsigned char *a)
{
  unsigned mask = c->mask;
  switch (c->type) {
    case 0: OPS("ps", "vmovaps"); break;
    case 1: OPS("pd", "vmovapd"); break;
    /* Aligned controls test the requested floating move on identical bits. */
    case 2: OPS("d", "vmovaps"); break;
    case 3: OPS("q", "vmovapd"); break;
  }
  phase = 2;
}

__attribute__((noinline)) static void guarded_execute(const struct probe_case *c,
                                                    unsigned char *a)
{
  phase = signal_number = signal_code = 0; signal_address = NULL;
  if (sigsetjmp(recovery, 1) == 0) {
    armed = 1;
    execute(c, a);
  }
  armed = 0;
}

static int run_case(const struct probe_case *c, unsigned char *memory, int page)
{
  int i, b, step, n, bad = 0, bytes = 0, sentinel = 0;
  unsigned lanes = 0;
  unsigned char *want = malloc((size_t)page), *allowed = malloc((size_t)page);
  unsigned char expected[64];
  struct transfer tr[16];
  if (!want || !allowed) exit(2);
  for (i = 0; i < page; ++i) memory[i] = c->store ? 0xa5 : memory_byte(i);
  source_bytes(c->type, src);
  memset(output, 0xd7, sizeof output);
  guarded_execute(c, memory + c->address);
  if (c->store) {
    store_model(c, page, src, want, allowed);
    bad = check_store(memory, want, allowed, page, signal_number != 0, &bytes, &sentinel);
  } else {
    memset(expected, 0xd7, sizeof expected);
    for (step = 0; step < 3; ++step) {
      int completed = phase == 2 || (c->form == PAIR && phase == 1 && step == 0);
      if (!completed || (c->form == PAIR ? step == 2 :
          step != (c->form == ALIGNED ? 2 : c->form == HIGH))) continue;
      n = transfers(c, step, tr);
      for (i = 0; i < n; ++i) {
        if (tr[i].address < 0 || tr[i].address + width(c->type) > page) { ++bad; continue; }
        for (b = 0; b < width(c->type); ++b)
          expected[tr[i].lane * width(c->type) + b] = memory_byte(tr[i].address + b);
      }
    }
    for (i = 0; i < 64; ++i) {
      if (output[i] != expected[i]) ++bad;
      if (output[i] != 0xd7) { ++bytes; lanes |= 1u << (i / width(c->type)); }
    }
    for (i = 0; i < page; ++i) if (memory[i] != memory_byte(i)) { ++sentinel; ++bad; }
  }
  printf("form=%s-%s-%s case=%s offset=%d element_bytes=%d A=%+d mask=0x%04x "
         "fault=%s si_code=%d si_addr=%p phase=%d bytes=%d lanes=0x%04x sentinel_changed=%d check=%s\n",
         c->store ? "store" : "load", forms[c->form], types[c->type], groups[c->group],
         c->offset, width(c->type), c->address, c->mask,
         signal_number ? (signal_number == SIGSEGV ? "SIGSEGV" : "SIGBUS") : "none",
         (int)signal_code, signal_address, (int)phase, bytes, lanes, sentinel, bad ? "FAIL" : "ok");
  free(want); free(allowed);
  return bad != 0;
}

static int native(void)
{
  long page = sysconf(_SC_PAGESIZE);
  unsigned char *region, *memory;
  struct sigaction action;
  int i, bad = 0;
  if (page < 1024 || page > 1048576 || page % 64) return 2;
  region = mmap(NULL, (size_t)page * 3, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (region == MAP_FAILED) { perror("mmap"); return 2; }
  memory = region + page;
  if (mprotect(memory, (size_t)page, PROT_READ | PROT_WRITE)) { perror("mprotect"); return 2; }
  memset(&action, 0, sizeof action); action.sa_sigaction = handler;
  action.sa_flags = SA_SIGINFO; sigemptyset(&action.sa_mask);
  if (sigaction(SIGSEGV, &action, NULL) || sigaction(SIGBUS, &action, NULL)) { perror("sigaction"); return 2; }
  setvbuf(stdout, NULL, _IOLBF, 0);
  printf("S3-03 page=%ld mapped=%p end_guard=%p; bytes/lanes for faulted loads are completed checkpoints only\n",
         page, (void *)memory, (void *)(memory + page));
  make_cases((int)page);
  for (i = 0; i < count; ++i) bad += run_case(cases + i, memory, (int)page);
  munmap(region, (size_t)page * 3);
  printf("S3-03 cases=%d data_or_sentinel_failures=%d\n", count, bad);
  return bad != 0;
}
#endif

int main(int argc, char **argv)
{
  if (argc == 2 && !strcmp(argv[1], "--self-test")) return self_test();
#ifndef HOST_LOGIC
  if (argc == 2 && !strcmp(argv[1], "--native")) return native();
#endif
  fprintf(stderr, "usage: %s --self-test (host) or --native (KNC build, card only)\n", argv[0]);
  return 2;
}
