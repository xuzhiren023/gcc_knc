/* S5-02: native probe of IMCI conversions and memory up/down-conversion.
   Intel 327364-001: VCVT* pp.154-189, VMOVAPS/VMOVDQA32 pp.379-384,
   VBROADCAST* pp.132-145, VLOADUNPACKHD p.349, VPACKSTORELD p.417,
   sections 2.2.2-2.2.3 (pp.30-34), tables 3.3/3.4 (pp.49-50), 4.6.1 (p.63).
   It records what the manual leaves open (docs/research/knc-conversions.md,
   section 5): NaN, infinity and out-of-range results of the fxpnt forms,
   what imm8 bits 2-3 do, the MXCSR flags raised, whether integer
   down-conversion saturates, and the fault footprint of converted accesses
   at a page end.

   Build on the host (Git Bash, from the repository root; -O0, inline asm):
     T=$PWD/.work/_shared/toolchain; B=$PWD/.work/_shared/gcc-build/gcc
     PATH=$T/cygwin/bin:$T/cross/bin:$PATH $B/xgcc -B$B/ -march=knc -O0 \
       -Wall -Wextra -Wa,--march=k1om tests/regress/knc-convert-probe.c \
       -o knc-convert-probe.mic
   Run on the card only:  ./knc-convert-probe.mic --native
   Every line starts "S5-02".  Values are hex bit patterns.  flags= is
   MXCSR bits 5:0 (PE UE OE ZE DE IE) after the instruction, cleared before.
   check= appears only where the manual states the result.
   tools/knc_lint rejects both the .s and the binary (it decodes both): K1OM
   objdump spells the register source of vcvtdq2pd/vcvtudq2pd/vcvtps2pd as
   %ymm1, the same encoding as %zmm1.  A lint false positive (see the doc).  */
#define _GNU_SOURCE 1
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

typedef union {
  uint32_t u[16]; int32_t i[16]; float f[16];
  uint64_t q[8]; double d[8]; uint16_t h[32]; uint8_t b[64];
} vec;
static vec vin __attribute__((aligned(64)));
static vec vout __attribute__((aligned(64)));
static vec vsrc __attribute__((aligned(64)));

static unsigned get_mxcsr(void)
{
  unsigned m;
  __asm__ volatile ("stmxcsr %0" : "=m"(m));
  return m;
}
static void set_mxcsr(unsigned m) { __asm__ volatile ("ldmxcsr %0" : : "m"(m)); }
static unsigned base_mxcsr;
/* Clear the six status flags, set RC (0 rn, 1 rd, 2 ru, 3 rz). */
static void arm_flags(unsigned rc) { set_mxcsr((base_mxcsr & ~0x603fu) | (rc << 13)); }
static unsigned read_flags(void)
{
  unsigned f = get_mxcsr() & 0x3fu;
  set_mxcsr(base_mxcsr);
  return f;
}

/* ---- Register conversions ---------------------------------------------- */
enum { PS2DQ, PS2UDQ, PD2DQ, PD2UDQ, DQ2PS, DQ2PS_ADJ16, UDQ2PS, DQ2PD,
       UDQ2PD, PS2PD, PD2PS };
static const char *const op_names[] = {
  "vcvtfxpntps2dq", "vcvtfxpntps2udq", "vcvtfxpntpd2dq", "vcvtfxpntpd2udq",
  "vcvtfxpntdq2ps", "vcvtfxpntdq2ps-imm0x40", "vcvtfxpntudq2ps", "vcvtdq2pd",
  "vcvtudq2pd", "vcvtps2pd", "vcvtpd2ps"
};

#define CVT_PRE "vmovdqa32 (%[i]), %%zmm1\n\tvmovdqa32 (%[o]), %%zmm0\n\t" \
                "kmov %[k], %%k1\n\t"
#define CVT_POST "\n\tvmovdqa32 %%zmm0, (%[o])"
#define CVT_ASM(TEXT) __asm__ volatile (CVT_PRE TEXT CVT_POST \
  : : [i] "r"(vin.u), [o] "r"(vout.u), [k] "r"(k) : "zmm0", "zmm1", "k1", "memory")
#define CVT_I(INSN, IMM) CVT_ASM(INSN " $" #IMM ", %%zmm1, %%zmm0%{%%k1%}")
#define CVT_R(INSN) CVT_ASM(INSN " %%zmm1, %%zmm0%{%%k1%}")
#define EIGHT(OP, INSN) \
  case OP * 8 + 0: CVT_I(INSN, 0); break; case OP * 8 + 1: CVT_I(INSN, 1); break; \
  case OP * 8 + 2: CVT_I(INSN, 2); break; case OP * 8 + 3: CVT_I(INSN, 3); break; \
  case OP * 8 + 4: CVT_I(INSN, 4); break; case OP * 8 + 5: CVT_I(INSN, 5); break; \
  case OP * 8 + 6: CVT_I(INSN, 6); break; case OP * 8 + 7: CVT_I(INSN, 7); break;

/* vin -> vout under mask k; vout keeps its previous contents elsewhere. */
static void convert(int op, int imm, unsigned k)
{
  switch (op < DQ2PS ? op * 8 + imm : 100 + op) {
    EIGHT(PS2DQ, "vcvtfxpntps2dq")
    EIGHT(PS2UDQ, "vcvtfxpntps2udq")
    EIGHT(PD2DQ, "vcvtfxpntpd2dq")
    EIGHT(PD2UDQ, "vcvtfxpntpd2udq")
    case 100 + DQ2PS: CVT_I("vcvtfxpntdq2ps", 0); break;
    case 100 + DQ2PS_ADJ16: CVT_I("vcvtfxpntdq2ps", 0x40); break;
    case 100 + UDQ2PS: CVT_I("vcvtfxpntudq2ps", 0); break;
    case 100 + DQ2PD: CVT_R("vcvtdq2pd"); break;
    case 100 + UDQ2PD: CVT_R("vcvtudq2pd"); break;
    case 100 + PS2PD: CVT_R("vcvtps2pd"); break;
    case 100 + PD2PS: CVT_R("vcvtpd2ps"); break;
    default: abort();
  }
}

static int is_pd_source(int op) { return op == PD2DQ || op == PD2UDQ || op == PD2PS; }

/* Special and out-of-range inputs, one value broadcast to every lane so
   the sticky flags belong to that input.  imm 3 is rz, C's (int) cast. */
static const uint32_t f_special[] = {
  0x7fc00000, 0xffc00000, 0x7fa00000, 0x7f800000, 0xff800000, 0x00000000,
  0x80000000, 0x3f800000, 0xbf400000, 0xbf800000, 0x00000001, 0x4effffff,
  0x4f000000, 0xcf000000, 0xcf000001, 0x4f7fffff, 0x4f800000, 0x501502f9,
  0xd01502f9
};
static const uint64_t d_special[] = {
  0x7ff8000000000000ull, 0xfff8000000000000ull, 0x7ff4000000000000ull,
  0x7ff0000000000000ull, 0xfff0000000000000ull, 0x0000000000000000ull,
  0x8000000000000000ull, 0x3ff0000000000000ull, 0xbfe8000000000000ull,
  0xbff0000000000000ull, 0x0000000000000001ull, 0x41dfffffffc00000ull,
  0x41dfffffffe00000ull, 0x41e0000000000000ull, 0xc1e0000000000000ull,
  0xc1e0000000200000ull, 0x41efffffffe00000ull, 0x41f0000000000000ull,
  0x4202a05f20000000ull, 0xc202a05f20000000ull
};
/* +-2.5, +-1.5, +-0.5 in lanes 0-5. */
static const uint32_t f_round[] = {
  0x40200000, 0xc0200000, 0x3fc00000, 0xbfc00000, 0x3f000000, 0xbf000000 };
static const uint64_t d_round[] = {
  0x4004000000000000ull, 0xc004000000000000ull, 0x3ff8000000000000ull,
  0xbff8000000000000ull, 0x3fe0000000000000ull, 0xbfe0000000000000ull };

static void fill_broadcast(int op, uint64_t bits)
{
  int n;
  for (n = 0; n < 16; ++n)
    if (is_pd_source(op)) { if (n < 8) vin.q[n] = bits; }
    else vin.u[n] = (uint32_t)bits;
}

static void special_values(void)
{
  int op, n, v;
  for (op = PS2DQ; op <= PD2UDQ; ++op) {
    int pd = is_pd_source(op), count = pd ? 20 : 19, lanes = pd ? 8 : 16;
    for (v = 0; v < count; ++v) {
      uint64_t bits = pd ? d_special[v] : f_special[v];
      int uniform = 1, upper_zero = 1;
      unsigned flags;
      fill_broadcast(op, bits);
      memset(&vout, 0x5a, sizeof vout);
      arm_flags(0);
      convert(op, 3, 0xffff);
      flags = read_flags();
      for (n = 1; n < lanes; ++n) uniform &= vout.u[n] == vout.u[0];
      for (n = 8; pd && n < 16; ++n) upper_zero &= vout.u[n] == 0;
      printf("S5-02 group=special op=%s imm=3 rc=rn input=%0*llx result=%08x "
             "uniform=%s%s flags=%02x\n", op_names[op], pd ? 16 : 8,
             (unsigned long long)bits, vout.u[0], uniform ? "yes" : "no",
             pd ? (upper_zero ? " upper=zero" : " upper=NONZERO") : "", flags);
    }
  }
}

/* imm8 bits 1:0 select rn/rd/ru/rz (pp.161-173); bit 2 is undocumented.
   Each imm 0-7 runs under each MXCSR.RC, so a result that follows RC when
   bit 2 is set shows bit 2 means "use MXCSR". */
static void rounding(void)
{
  static const char *const rc_names[] = { "rn", "rd", "ru", "rz" };
  int op, imm, rc, n;
  for (op = PS2DQ; op <= PD2DQ; op += 2)
    for (imm = 0; imm < 8; ++imm)
      for (rc = 0; rc < 4; ++rc) {
        unsigned flags;
        memset(&vin, 0, sizeof vin);
        for (n = 0; n < 6; ++n)
          if (op == PD2DQ) vin.q[n] = d_round[n]; else vin.u[n] = f_round[n];
        arm_flags((unsigned)rc);
        convert(op, imm, 0xffff);
        flags = read_flags();
        printf("S5-02 group=rounding op=%s imm=%d rc=%s inputs=+2.5,-2.5,+1.5,-1.5,+0.5,-0.5"
               " results=%d,%d,%d,%d,%d,%d flags=%02x\n", op_names[op], imm,
               rc_names[rc], vout.i[0], vout.i[1], vout.i[2], vout.i[3],
               vout.i[4], vout.i[5], flags);
      }
}

static void print_lanes(const char *group, int op, const char *rc, unsigned k,
                        int words, unsigned flags)
{
  int n;
  printf("S5-02 group=%s op=%s rc=%s mask=%04x out=", group, op_names[op], rc, k);
  for (n = 0; n < words; ++n) printf("%s%08x", n ? "," : "", vout.u[n]);
  printf(" flags=%02x\n", flags);
}

/* Int to FP follows MXCSR.RC (pp.157, 177); FP widening and the 8-lane
   forms read only the low half (pp.154, 184, 187); pd2ps rounds by
   MXCSR.RC and zeroes the high half (p.181). */
static void int_and_fp(void)
{
  static const char *const rc_names[] = { "rn", "rd", "ru", "rz" };
  static const int32_t di[16] = { 16777217, -16777217, 16777219, 0x7fffffff,
    -2147483647, 1, 0, -1, 33554435, 196608, 0, 0, 0, 0, 0, 0 };
  static const uint32_t ui[16] = { 0xffffffffu, 0x80000001u, 16777217u,
    0x80000080u, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };
  /* 1+2^-24+2^-40, -(same), 2^1000, 2^-1000, 2^-140 (exact float denormal),
     2^-140*(1+2^-30), sNaN, qNaN with payload. */
  static const uint64_t pd[8] = { 0x3ff0000010001000ull, 0xbff0000010001000ull,
    0x7e70000000000000ull, 0x0170000000000000ull, 0x3730000000000000ull,
    0x3730000000400000ull, 0x7ff4000000000000ull, 0x7ff8000012345678ull };
  static const uint32_t ps[4] = { 0x7fa00000, 0x7fc12345, 0x00000001, 0x3f800000 };
  int rc, n, v;
  unsigned flags;
  for (rc = 0; rc < 4; ++rc) {
    memcpy(vin.i, di, sizeof di);
    arm_flags((unsigned)rc); convert(DQ2PS, 0, 0xffff); flags = read_flags();
    print_lanes("int2fp", DQ2PS, rc_names[rc], 0xffff, 10, flags);
    memcpy(vin.u, ui, sizeof ui);
    arm_flags((unsigned)rc); convert(UDQ2PS, 0, 0xffff); flags = read_flags();
    print_lanes("int2fp", UDQ2PS, rc_names[rc], 0xffff, 4, flags);
    memset(&vin, 0, sizeof vin); vin.q[0] = pd[0]; vin.q[1] = pd[1];
    arm_flags((unsigned)rc); convert(PD2PS, 0, 0xffff); flags = read_flags();
    print_lanes("fp2fp-round", PD2PS, rc_names[rc], 0xffff, 2, flags);
  }
  memcpy(vin.i, di, sizeof di);
  arm_flags(0); convert(DQ2PS_ADJ16, 0, 0xffff); flags = read_flags();
  print_lanes("int2fp-expadj", DQ2PS_ADJ16, "rn", 0xffff, 10, flags);
  /* One value per run, broadcast, for flag attribution. */
  for (v = 2; v < 8; ++v) {
    fill_broadcast(PD2PS, pd[v]);
    arm_flags(0); convert(PD2PS, 0, 0xffff); flags = read_flags();
    printf("S5-02 group=fp2fp-special op=vcvtpd2ps input=%016llx result=%08x flags=%02x\n",
           (unsigned long long)pd[v], vout.u[0], flags);
  }
  for (v = 0; v < 4; ++v) {
    fill_broadcast(PS2PD, ps[v]);
    arm_flags(0); convert(PS2PD, 0, 0xffff); flags = read_flags();
    printf("S5-02 group=fp2fp-special op=vcvtps2pd input=%08x result=%016llx flags=%02x\n",
           ps[v], (unsigned long long)vout.q[0], flags);
  }
  /* Low-half reads: lanes 8-15 hold garbage that must not appear. */
  for (n = 0; n < 16; ++n) vin.u[n] = n < 8 ? (uint32_t)(n * 1000 - 3000) : 0x7fa00000u;
  vin.u[7] = 0xffffffffu;
  arm_flags(0); convert(DQ2PD, 0, 0xffff); flags = read_flags();
  print_lanes("low-half", DQ2PD, "rn", 0xffff, 16, flags);
  arm_flags(0); convert(UDQ2PD, 0, 0xffff); flags = read_flags();
  print_lanes("low-half", UDQ2PD, "rn", 0xffff, 16, flags);
  for (n = 0; n < 16; ++n) vin.u[n] = n < 8 ? 0x3f800000u + ((uint32_t)n << 20) : 0x7fa00000u;
  arm_flags(0); convert(PS2PD, 0, 0xffff); flags = read_flags();
  print_lanes("low-half", PS2PD, "rn", 0xffff, 16, flags);
  /* Write-mask 0x0f: lanes 4-7 should keep 0xdeadbeef, lanes 8-15 become 0. */
  for (n = 0; n < 8; ++n) vin.d[n] = n + 1;
  for (n = 0; n < 16; ++n) vout.u[n] = 0xdeadbeefu;
  convert(PD2DQ, 3, 0x0f);
  print_lanes("mask-upper", PD2DQ, "imm3", 0x0f, 16, 0);
  for (n = 0; n < 16; ++n) vout.u[n] = 0xdeadbeefu;
  convert(PD2PS, 0, 0x0f);
  print_lanes("mask-upper", PD2PS, "rn", 0x0f, 16, 0);
}

/* ---- Memory forms ------------------------------------------------------- */
static sigjmp_buf recovery;
static volatile sig_atomic_t armed, signal_number, signal_code, phase;
static void *volatile signal_address;

static void handler(int sig, siginfo_t *info, void *context)
{
  (void)context;
  if (!armed) _exit(128 + sig);
  signal_number = sig;
  signal_code = info->si_code;
  signal_address = info->si_addr;
  siglongjmp(recovery, 1);
}

typedef void (*memop)(unsigned char *a, unsigned k);
#define LOAD_OP(NAME, INSN) static void NAME(unsigned char *a, unsigned k) { \
  __asm__ volatile ("vmovdqa32 (%[o]), %%zmm0\n\tkmov %[k], %%k1\n\t" INSN \
                    "\n\tvmovdqa32 %%zmm0, (%[o])" \
    : : [o] "r"(vout.u), [a] "r"(a), [k] "r"(k) : "zmm0", "k1", "memory"); }
#define STORE_OP(NAME, INSN) static void NAME(unsigned char *a, unsigned k) { \
  __asm__ volatile ("vmovdqa32 (%[s]), %%zmm0\n\tkmov %[k], %%k1\n\t" INSN \
    : : [s] "r"(vsrc.u), [a] "r"(a), [k] "r"(k) : "zmm0", "k1", "memory"); }

LOAD_OP(ld_d_u8, "vmovdqa32 (%[a])%{uint8%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_d_s8, "vmovdqa32 (%[a])%{sint8%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_d_u16, "vmovdqa32 (%[a])%{uint16%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_d_s16, "vmovdqa32 (%[a])%{sint16%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_ps_u8, "vmovaps (%[a])%{uint8%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_ps_s8, "vmovaps (%[a])%{sint8%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_ps_u16, "vmovaps (%[a])%{uint16%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_ps_s16, "vmovaps (%[a])%{sint16%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_ps_f16, "vmovaps (%[a])%{float16%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_b4_u8, "vbroadcasti32x4 (%[a])%{uint8%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_b4_s16, "vbroadcastf32x4 (%[a])%{sint16%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_b1_u8, "vpbroadcastd (%[a])%{uint8%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_b1_f16, "vbroadcastss (%[a])%{float16%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_l_u8, "vloadunpackld (%[a])%{uint8%}, %%zmm0%{%%k1%}")
LOAD_OP(ld_h_u8, "vloadunpackhd 64(%[a])%{uint8%}, %%zmm0%{%%k1%}")
STORE_OP(st_d_u8, "vmovdqa32 %%zmm0%{uint8%}, (%[a])%{%%k1%}")
STORE_OP(st_d_s8, "vmovdqa32 %%zmm0%{sint8%}, (%[a])%{%%k1%}")
STORE_OP(st_d_u16, "vmovdqa32 %%zmm0%{uint16%}, (%[a])%{%%k1%}")
STORE_OP(st_d_s16, "vmovdqa32 %%zmm0%{sint16%}, (%[a])%{%%k1%}")
STORE_OP(st_ps_u8, "vmovaps %%zmm0%{uint8%}, (%[a])%{%%k1%}")
STORE_OP(st_ps_s8, "vmovaps %%zmm0%{sint8%}, (%[a])%{%%k1%}")
STORE_OP(st_ps_u16, "vmovaps %%zmm0%{uint16%}, (%[a])%{%%k1%}")
STORE_OP(st_ps_s16, "vmovaps %%zmm0%{sint16%}, (%[a])%{%%k1%}")
STORE_OP(st_ps_f16, "vmovaps %%zmm0%{float16%}, (%[a])%{%%k1%}")
STORE_OP(st_l_u8, "vpackstoreld %%zmm0%{uint8%}, (%[a])%{%%k1%}")
STORE_OP(st_h_u8, "vpackstorehd %%zmm0%{uint8%}, 64(%[a])%{%%k1%}")

enum { U8, S8, U16, S16, F16 };
enum { INT, FP };
struct form {
  const char *name;
  memop first, second;      /* second: the h half of a pair, or NULL */
  int store, bytes, elem, conv, to, copies;  /* copies: 16, 4 ({4to16}) or 1 */
};
static const struct form forms[] = {
  { "vmovdqa32{uint8}", ld_d_u8, NULL, 0, 16, 1, U8, INT, 16 },
  { "vmovdqa32{sint8}", ld_d_s8, NULL, 0, 16, 1, S8, INT, 16 },
  { "vmovdqa32{uint16}", ld_d_u16, NULL, 0, 32, 2, U16, INT, 16 },
  { "vmovdqa32{sint16}", ld_d_s16, NULL, 0, 32, 2, S16, INT, 16 },
  { "vmovaps{uint8}", ld_ps_u8, NULL, 0, 16, 1, U8, FP, 16 },
  { "vmovaps{sint8}", ld_ps_s8, NULL, 0, 16, 1, S8, FP, 16 },
  { "vmovaps{uint16}", ld_ps_u16, NULL, 0, 32, 2, U16, FP, 16 },
  { "vmovaps{sint16}", ld_ps_s16, NULL, 0, 32, 2, S16, FP, 16 },
  { "vmovaps{float16}", ld_ps_f16, NULL, 0, 32, 2, F16, FP, 16 },
  { "vbroadcasti32x4{uint8}", ld_b4_u8, NULL, 0, 4, 1, U8, INT, 4 },
  { "vbroadcastf32x4{sint16}", ld_b4_s16, NULL, 0, 8, 2, S16, FP, 4 },
  { "vpbroadcastd{uint8}", ld_b1_u8, NULL, 0, 1, 1, U8, INT, 1 },
  { "vbroadcastss{float16}", ld_b1_f16, NULL, 0, 2, 2, F16, FP, 1 },
  { "vloadunpackl/hd{uint8}", ld_l_u8, ld_h_u8, 0, 16, 1, U8, INT, 16 },
  { "vmovdqa32-store{uint8}", st_d_u8, NULL, 1, 16, 1, U8, INT, 16 },
  { "vmovdqa32-store{sint8}", st_d_s8, NULL, 1, 16, 1, S8, INT, 16 },
  { "vmovdqa32-store{uint16}", st_d_u16, NULL, 1, 32, 2, U16, INT, 16 },
  { "vmovdqa32-store{sint16}", st_d_s16, NULL, 1, 32, 2, S16, INT, 16 },
  { "vmovaps-store{uint8}", st_ps_u8, NULL, 1, 16, 1, U8, FP, 16 },
  { "vmovaps-store{sint8}", st_ps_s8, NULL, 1, 16, 1, S8, FP, 16 },
  { "vmovaps-store{uint16}", st_ps_u16, NULL, 1, 32, 2, U16, FP, 16 },
  { "vmovaps-store{sint16}", st_ps_s16, NULL, 1, 32, 2, S16, FP, 16 },
  { "vmovaps-store{float16}", st_ps_f16, NULL, 1, 32, 2, F16, FP, 16 },
  { "vpackstorel/hd{uint8}", st_l_u8, st_h_u8, 1, 16, 1, U8, INT, 16 },
};

/* Placements; G is the first guard byte (end of the mapped page).
   mid: aligned, inside the page.  end: A = G - bytes (pairs: A & 63 = 48,
   so the stream ends exactly at G but A+64 is in the guard page).
   cross: pairs only, A & 63 = 56, both halves inside the page.
   guard: A = G.  guard-empty: A = G with mask 0.  misaligned: A = mid +
   bytes / 2, below the access-size alignment of p.32 / p.34. */
enum { MID, END, CROSS, GUARD, GUARD_EMPTY, MISALIGNED, PLACES };
static const char *const places[] = { "mid", "end", "cross", "guard",
                                      "guard-empty", "misaligned" };

static const uint16_t halves[16] = { 0x3c00, 0xc000, 0x0001, 0x03ff, 0x7bff,
  0x7c00, 0xfc00, 0x7e00, 0x7d00, 0x8000, 0x3555, 0x0400, 0x4248, 0xbc00,
  0x5640, 0x0200 };
static const int32_t int_src[16] = { 0, 1, 127, 128, 255, 256, 257, -1, -128,
  -129, 32767, 32768, 65535, 65536, 2147483647, -2147483647 - 1 };
static const uint32_t fp_src[16] = { 0x3f000000, 0x3fc00000, 0x40200000,
  0xbf000000, 0xbf800000, 0x437f8000, 0x43800000, 0x43960000, 0xc3010000,
  0x477fff80, 0x501502f9, 0xd01502f9, 0x7fc00000, 0x7f800000, 0xff800000,
  0x1a800000 };

static uint8_t pattern(int i) { return (uint8_t)(i * 37 + 11); }

static uint32_t half_bits(uint16_t h)
{
  uint32_t sign = (uint32_t)(h >> 15) << 31, e = (h >> 10) & 31, m = h & 1023;
  if (e == 31) return sign | 0x7f800000u | (m << 13) | (m ? 0x00400000u : 0);
  if (e) return sign | ((e + 112) << 23) | (m << 13);
  if (!m) return sign;
  for (e = 113; !(m & 1024); m <<= 1) --e;
  return sign | (e << 23) | ((m & 1023) << 13);
}

static uint32_t element(const struct form *f, const unsigned char *a, int n)
{
  int32_t v = 0;
  float x;
  uint32_t bits;
  a += (f->copies == 16 ? n : f->copies == 4 ? n % 4 : 0) * f->elem;
  switch (f->conv) {
    case U8: v = a[0]; break;
    case S8: v = (int8_t)a[0]; break;
    case U16: v = a[0] | a[1] << 8; break;
    case S16: v = (int16_t)(a[0] | a[1] << 8); break;
    case F16: return half_bits((uint16_t)(a[0] | a[1] << 8));
  }
  if (f->to == INT) return (uint32_t)v;
  x = (float)v;            /* exact: |v| < 2^24 */
  memcpy(&bits, &x, 4);
  return bits;
}

static unsigned char *g_memory;
static long g_page;

__attribute__((noinline)) static void guarded(const struct form *f, unsigned char *a,
                                              unsigned k)
{
  phase = signal_number = signal_code = 0;
  signal_address = NULL;
  if (sigsetjmp(recovery, 1) == 0) {
    armed = 1;
    f->first(a, k);
    phase = 1;
    if (f->second) f->second(a, k);
    phase = 2;
  }
  armed = 0;
}

static int address_of(const struct form *f, int place, long *offset)
{
  long mid = 1024, end = g_page - f->bytes;
  if (f->second) end = g_page - 16;       /* A & 63 = 48 */
  switch (place) {
    case MID: *offset = mid; return 1;
    case END: *offset = end; return 1;
    case CROSS: *offset = mid + 56; return f->second != NULL;
    case GUARD: case GUARD_EMPTY: *offset = g_page; return 1;
    case MISALIGNED: *offset = mid + f->bytes / 2;
      return f->bytes > 1 && f->second == NULL;
  }
  return 0;
}

static void memory_case(const struct form *f, int place)
{
  long offset, i;
  unsigned char *a;
  unsigned k = place == GUARD_EMPTY ? 0 : 0xffff, flags;
  int n, bad = 0, changed = 0, outside = 0, sat = 0, trunc = 0;
  if (!address_of(f, place, &offset)) return;
  a = g_memory + offset;
  for (i = 0; i < g_page; ++i) g_memory[i] = f->store ? 0xa5 : pattern((int)i);
  if (!f->store && f->conv == F16 && offset + 32 <= g_page)
    memcpy(a, halves, (size_t)(f->copies == 16 ? 32 : f->copies * 2));
  memset(&vout, 0xd7, sizeof vout);
  if (f->to == INT) memcpy(vsrc.i, int_src, sizeof int_src);
  else memcpy(vsrc.u, fp_src, sizeof fp_src);
  arm_flags(0);
  guarded(f, a, k);
  flags = read_flags();
  if (!signal_number && place != GUARD && place != GUARD_EMPTY) {
    if (!f->store) {
      for (n = 0; n < 16; ++n) bad += vout.u[n] != element(f, a, n);
    } else {
      for (i = 0; i < g_page; ++i)
        if (g_memory[i] != 0xa5) {
          ++changed;
          if (i < offset || i >= offset + f->bytes) ++outside;
        }
    }
  }
  printf("S5-02 group=memory form=%s place=%s A=page%+ld mask=%04x fault=%s si_code=%d "
         "si_addr=%s%+ld phase=%d flags=%02x", f->name, places[place], offset - g_page,
         k, signal_number ? (signal_number == SIGSEGV ? "SIGSEGV" : "SIGBUS") : "none",
         (int)signal_code, signal_address ? "page" : "null",
         signal_address ? (long)((unsigned char *)signal_address - (g_memory + g_page)) : 0L,
         (int)phase, flags);
  if (signal_number || place == GUARD || place == GUARD_EMPTY) {
    if (f->store) {
      for (i = 0; i < g_page; ++i) changed += g_memory[i] != 0xa5;
      printf(" bytes_changed=%d", changed);
    }
    printf("\n");
    return;
  }
  if (!f->store) {
    printf(" check=%s\n", bad ? "FAIL" : "ok");
    return;
  }
  printf(" bytes_changed=%d outside=%d stored=", changed, outside);
  for (n = 0; n < 16; ++n) {
    uint32_t got = f->elem == 1 ? a[n] : (uint32_t)(a[2 * n] | a[2 * n + 1] << 8);
    printf("%s%0*x", n ? "," : "", f->elem * 2, got);
    if (f->to == INT && f->conv != F16) {
      int64_t v = int_src[n], lo = f->conv == U8 ? 0 : f->conv == S8 ? -128 :
                  f->conv == U16 ? 0 : -32768;
      int64_t hi = f->conv == U8 ? 255 : f->conv == S8 ? 127 :
                   f->conv == U16 ? 65535 : 32767;
      uint32_t width = f->elem == 1 ? 0xffu : 0xffffu;
      int64_t s = (f->conv == U8 || f->conv == U16) ? (int64_t)(uint32_t)v : v;
      s = s < lo ? lo : s > hi ? hi : s;
      sat += got == ((uint32_t)s & width);
      trunc += got == ((uint32_t)v & width);
    }
  }
  if (f->to == INT)
    printf(" model=%s", sat == 16 && trunc == 16 ? "both" : sat == 16 ? "saturate" :
           trunc == 16 ? "truncate" : "neither");
  printf("\n");
}

static int native(void)
{
  unsigned char *region;
  struct sigaction action;
  size_t f;
  int place;
  g_page = sysconf(_SC_PAGESIZE);
  if (g_page < 4096 || g_page % 64) return 2;
  region = mmap(NULL, (size_t)g_page * 3, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (region == MAP_FAILED) { perror("mmap"); return 2; }
  g_memory = region + g_page;
  if (mprotect(g_memory, (size_t)g_page, PROT_READ | PROT_WRITE)) { perror("mprotect"); return 2; }
  memset(&action, 0, sizeof action);
  action.sa_sigaction = handler;
  action.sa_flags = SA_SIGINFO;
  sigemptyset(&action.sa_mask);
  if (sigaction(SIGSEGV, &action, NULL) || sigaction(SIGBUS, &action, NULL)) {
    perror("sigaction");
    return 2;
  }
  setvbuf(stdout, NULL, _IOLBF, 0);
  base_mxcsr = get_mxcsr();
  printf("S5-02 page=%ld mxcsr=%08x\n", g_page, base_mxcsr);
  special_values();
  rounding();
  int_and_fp();
  for (f = 0; f < sizeof forms / sizeof forms[0]; ++f)
    for (place = 0; place < PLACES; ++place) memory_case(&forms[f], place);
  set_mxcsr(base_mxcsr);
  munmap(region, (size_t)g_page * 3);
  printf("S5-02 done\n");
  return 0;
}

int main(int argc, char **argv)
{
  if (argc == 2 && !strcmp(argv[1], "--native")) return native();
  fprintf(stderr, "usage: %s --native (KNC card only)\n", argv[0]);
  return 2;
}
