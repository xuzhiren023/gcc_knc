/* Additive full64B integer-storage DP pow variant. Original tables and
 * compensated FP expressions/conversions/event arithmetic remain unchanged.
 * Integer observation/selection lines inside large_neg change explicitly:
 * qword snapshots, +/-1 sign-bit selection and signed-zero bit repair.
 * Those deltas await fresh source/target qualification; no prior evidence
 * or zero-unsupported/zero-narrow-emission claim is inherited. */
/* Additive source-only DP pow register-table/i64-lane candidate.
 * Original source/export and host evidence remain unchanged. No compiler,
 * numerical, target ISA, ABI or G5 qualification is inherited.
 * Original Arm algorithm and table copyrights/licenses apply. */
/* Eight-DP GCC-vector adaptation of Arm optimized-routines v26.01 pow.c/data,
 * commit649ccc8411e7c4862965710f25c570d854a1483f.
 * Copyright(c)2018-2025 Arm Limited. SPDX-License-Identifier: MIT
 * Preserve compensated log/product/exp and signed subnormal rounding. Host
 * source experiment; no scalar pow delegation or target qualification. */
#include "pow_e8_register_i64_wide.h"
#include "math_config.h"
#include <string.h>
#if defined(__FAST_MATH__) || HAVE_FAST_FMA || HAVE_FAST_ROUND
#error "pow_e8 requires strict non-FMA/non-toint source configuration"
#endif
_Static_assert(POW_LOG_TABLE_BITS==7&&POW_LOG_POLY_ORDER==8&&EXP_TABLE_BITS==7&&EXP_POLY_ORDER==5&&EXP_USE_TOINT_NARROW==0,"unsupported pinned data configuration");
typedef double dv __attribute__((vector_size(64)));
typedef unsigned long long uv __attribute__((vector_size(64)));
typedef long long iv __attribute__((vector_size(64)));

/* Exact readonly words from pinned Arm pow_log_data.c/exp_data.c. */
typedef long long v8di __attribute__((vector_size(64)));
static const uv pw_pow_log_invc_0 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff6a00000000000), UINT64_C(0x3ff6800000000000), UINT64_C(0x3ff6600000000000), UINT64_C(0x3ff6400000000000), UINT64_C(0x3ff6200000000000), UINT64_C(0x3ff6000000000000), UINT64_C(0x3ff5e00000000000), UINT64_C(0x3ff5c00000000000)
};
static const uv pw_pow_log_invc_1 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff5a00000000000), UINT64_C(0x3ff5800000000000), UINT64_C(0x3ff5600000000000), UINT64_C(0x3ff5600000000000), UINT64_C(0x3ff5400000000000), UINT64_C(0x3ff5200000000000), UINT64_C(0x3ff5000000000000), UINT64_C(0x3ff4e00000000000)
};
static const uv pw_pow_log_invc_2 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff4c00000000000), UINT64_C(0x3ff4a00000000000), UINT64_C(0x3ff4a00000000000), UINT64_C(0x3ff4800000000000), UINT64_C(0x3ff4600000000000), UINT64_C(0x3ff4400000000000), UINT64_C(0x3ff4200000000000), UINT64_C(0x3ff4000000000000)
};
static const uv pw_pow_log_invc_3 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff4000000000000), UINT64_C(0x3ff3e00000000000), UINT64_C(0x3ff3c00000000000), UINT64_C(0x3ff3a00000000000), UINT64_C(0x3ff3a00000000000), UINT64_C(0x3ff3800000000000), UINT64_C(0x3ff3600000000000), UINT64_C(0x3ff3400000000000)
};
static const uv pw_pow_log_invc_4 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff3400000000000), UINT64_C(0x3ff3200000000000), UINT64_C(0x3ff3000000000000), UINT64_C(0x3ff3000000000000), UINT64_C(0x3ff2e00000000000), UINT64_C(0x3ff2c00000000000), UINT64_C(0x3ff2c00000000000), UINT64_C(0x3ff2a00000000000)
};
static const uv pw_pow_log_invc_5 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff2800000000000), UINT64_C(0x3ff2600000000000), UINT64_C(0x3ff2600000000000), UINT64_C(0x3ff2400000000000), UINT64_C(0x3ff2400000000000), UINT64_C(0x3ff2200000000000), UINT64_C(0x3ff2000000000000), UINT64_C(0x3ff2000000000000)
};
static const uv pw_pow_log_invc_6 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff1e00000000000), UINT64_C(0x3ff1c00000000000), UINT64_C(0x3ff1c00000000000), UINT64_C(0x3ff1a00000000000), UINT64_C(0x3ff1a00000000000), UINT64_C(0x3ff1800000000000), UINT64_C(0x3ff1600000000000), UINT64_C(0x3ff1600000000000)
};
static const uv pw_pow_log_invc_7 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff1400000000000), UINT64_C(0x3ff1400000000000), UINT64_C(0x3ff1200000000000), UINT64_C(0x3ff1000000000000), UINT64_C(0x3ff1000000000000), UINT64_C(0x3ff0e00000000000), UINT64_C(0x3ff0e00000000000), UINT64_C(0x3ff0c00000000000)
};
static const uv pw_pow_log_invc_8 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff0c00000000000), UINT64_C(0x3ff0a00000000000), UINT64_C(0x3ff0a00000000000), UINT64_C(0x3ff0800000000000), UINT64_C(0x3ff0800000000000), UINT64_C(0x3ff0600000000000), UINT64_C(0x3ff0400000000000), UINT64_C(0x3ff0400000000000)
};
static const uv pw_pow_log_invc_9 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff0200000000000), UINT64_C(0x3ff0200000000000), UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000), UINT64_C(0x3fefc00000000000), UINT64_C(0x3fef800000000000), UINT64_C(0x3fef400000000000), UINT64_C(0x3fef000000000000)
};
static const uv pw_pow_log_invc_10 __attribute__((aligned(64))) = {
  UINT64_C(0x3feec00000000000), UINT64_C(0x3fee800000000000), UINT64_C(0x3fee400000000000), UINT64_C(0x3fee200000000000), UINT64_C(0x3fede00000000000), UINT64_C(0x3feda00000000000), UINT64_C(0x3fed600000000000), UINT64_C(0x3fed400000000000)
};
static const uv pw_pow_log_invc_11 __attribute__((aligned(64))) = {
  UINT64_C(0x3fed000000000000), UINT64_C(0x3fecc00000000000), UINT64_C(0x3feca00000000000), UINT64_C(0x3fec600000000000), UINT64_C(0x3fec400000000000), UINT64_C(0x3fec000000000000), UINT64_C(0x3febe00000000000), UINT64_C(0x3feba00000000000)
};
static const uv pw_pow_log_invc_12 __attribute__((aligned(64))) = {
  UINT64_C(0x3feb800000000000), UINT64_C(0x3feb400000000000), UINT64_C(0x3feb200000000000), UINT64_C(0x3feae00000000000), UINT64_C(0x3feac00000000000), UINT64_C(0x3feaa00000000000), UINT64_C(0x3fea600000000000), UINT64_C(0x3fea400000000000)
};
static const uv pw_pow_log_invc_13 __attribute__((aligned(64))) = {
  UINT64_C(0x3fea000000000000), UINT64_C(0x3fe9e00000000000), UINT64_C(0x3fe9c00000000000), UINT64_C(0x3fe9a00000000000), UINT64_C(0x3fe9600000000000), UINT64_C(0x3fe9400000000000), UINT64_C(0x3fe9200000000000), UINT64_C(0x3fe9000000000000)
};
static const uv pw_pow_log_invc_14 __attribute__((aligned(64))) = {
  UINT64_C(0x3fe8c00000000000), UINT64_C(0x3fe8a00000000000), UINT64_C(0x3fe8800000000000), UINT64_C(0x3fe8600000000000), UINT64_C(0x3fe8400000000000), UINT64_C(0x3fe8200000000000), UINT64_C(0x3fe7e00000000000), UINT64_C(0x3fe7c00000000000)
};
static const uv pw_pow_log_invc_15 __attribute__((aligned(64))) = {
  UINT64_C(0x3fe7a00000000000), UINT64_C(0x3fe7800000000000), UINT64_C(0x3fe7600000000000), UINT64_C(0x3fe7400000000000), UINT64_C(0x3fe7200000000000), UINT64_C(0x3fe7000000000000), UINT64_C(0x3fe6e00000000000), UINT64_C(0x3fe6c00000000000)
};
static const uv pw_pow_log_logc_0 __attribute__((aligned(64))) = {
  UINT64_C(0xbfd62c82f2b9c800), UINT64_C(0xbfd5d1bdbf580800), UINT64_C(0xbfd5767717455800), UINT64_C(0xbfd51aad872df800), UINT64_C(0xbfd4be5f95777800), UINT64_C(0xbfd4618bc21c6000), UINT64_C(0xbfd404308686a800), UINT64_C(0xbfd3a64c55694800)
};
static const uv pw_pow_log_logc_1 __attribute__((aligned(64))) = {
  UINT64_C(0xbfd347dd9a988000), UINT64_C(0xbfd2e8e2bae12000), UINT64_C(0xbfd2895a13de8800), UINT64_C(0xbfd2895a13de8800), UINT64_C(0xbfd22941fbcf7800), UINT64_C(0xbfd1c898c1699800), UINT64_C(0xbfd1675cababa800), UINT64_C(0xbfd1058bf9ae4800)
};
static const uv pw_pow_log_logc_2 __attribute__((aligned(64))) = {
  UINT64_C(0xbfd0a324e2739000), UINT64_C(0xbfd0402594b4d000), UINT64_C(0xbfd0402594b4d000), UINT64_C(0xbfcfb9186d5e4000), UINT64_C(0xbfcef0adcbdc6000), UINT64_C(0xbfce27076e2af000), UINT64_C(0xbfcd5c216b4fc000), UINT64_C(0xbfcc8ff7c79aa000)
};
static const uv pw_pow_log_logc_3 __attribute__((aligned(64))) = {
  UINT64_C(0xbfcc8ff7c79aa000), UINT64_C(0xbfcbc286742d9000), UINT64_C(0xbfcaf3c94e80c000), UINT64_C(0xbfca23bc1fe2b000), UINT64_C(0xbfca23bc1fe2b000), UINT64_C(0xbfc9525a9cf45000), UINT64_C(0xbfc87fa06520d000), UINT64_C(0xbfc7ab890210e000)
};
static const uv pw_pow_log_logc_4 __attribute__((aligned(64))) = {
  UINT64_C(0xbfc7ab890210e000), UINT64_C(0xbfc6d60fe719d000), UINT64_C(0xbfc5ff3070a79000), UINT64_C(0xbfc5ff3070a79000), UINT64_C(0xbfc526e5e3a1b000), UINT64_C(0xbfc44d2b6ccb8000), UINT64_C(0xbfc44d2b6ccb8000), UINT64_C(0xbfc371fc201e9000)
};
static const uv pw_pow_log_logc_5 __attribute__((aligned(64))) = {
  UINT64_C(0xbfc29552f81ff000), UINT64_C(0xbfc1b72ad52f6000), UINT64_C(0xbfc1b72ad52f6000), UINT64_C(0xbfc0d77e7cd09000), UINT64_C(0xbfc0d77e7cd09000), UINT64_C(0xbfbfec9131dbe000), UINT64_C(0xbfbe27076e2b0000), UINT64_C(0xbfbe27076e2b0000)
};
static const uv pw_pow_log_logc_6 __attribute__((aligned(64))) = {
  UINT64_C(0xbfbc5e548f5bc000), UINT64_C(0xbfba926d3a4ae000), UINT64_C(0xbfba926d3a4ae000), UINT64_C(0xbfb8c345d631a000), UINT64_C(0xbfb8c345d631a000), UINT64_C(0xbfb6f0d28ae56000), UINT64_C(0xbfb51b073f062000), UINT64_C(0xbfb51b073f062000)
};
static const uv pw_pow_log_logc_7 __attribute__((aligned(64))) = {
  UINT64_C(0xbfb341d7961be000), UINT64_C(0xbfb341d7961be000), UINT64_C(0xbfb16536eea38000), UINT64_C(0xbfaf0a30c0118000), UINT64_C(0xbfaf0a30c0118000), UINT64_C(0xbfab42dd71198000), UINT64_C(0xbfab42dd71198000), UINT64_C(0xbfa77458f632c000)
};
static const uv pw_pow_log_logc_8 __attribute__((aligned(64))) = {
  UINT64_C(0xbfa77458f632c000), UINT64_C(0xbfa39e87b9fec000), UINT64_C(0xbfa39e87b9fec000), UINT64_C(0xbf9f829b0e780000), UINT64_C(0xbf9f829b0e780000), UINT64_C(0xbf97b91b07d58000), UINT64_C(0xbf8fc0a8b0fc0000), UINT64_C(0xbf8fc0a8b0fc0000)
};
static const uv pw_pow_log_logc_9 __attribute__((aligned(64))) = {
  UINT64_C(0xbf7fe02a6b100000), UINT64_C(0xbf7fe02a6b100000), UINT64_C(0x0000000000000000), UINT64_C(0x0000000000000000), UINT64_C(0x3f80101575890000), UINT64_C(0x3f90205658938000), UINT64_C(0x3f98492528c90000), UINT64_C(0x3fa0415d89e74000)
};
static const uv pw_pow_log_logc_10 __attribute__((aligned(64))) = {
  UINT64_C(0x3fa466aed42e0000), UINT64_C(0x3fa894aa149fc000), UINT64_C(0x3faccb73cdddc000), UINT64_C(0x3faeea31c006c000), UINT64_C(0x3fb1973bd1466000), UINT64_C(0x3fb3bdf5a7d1e000), UINT64_C(0x3fb5e95a4d97a000), UINT64_C(0x3fb700d30aeac000)
};
static const uv pw_pow_log_logc_11 __attribute__((aligned(64))) = {
  UINT64_C(0x3fb9335e5d594000), UINT64_C(0x3fbb6ac88dad6000), UINT64_C(0x3fbc885801bc4000), UINT64_C(0x3fbec739830a2000), UINT64_C(0x3fbfe89139dbe000), UINT64_C(0x3fc1178e8227e000), UINT64_C(0x3fc1aa2b7e23f000), UINT64_C(0x3fc2d1610c868000)
};
static const uv pw_pow_log_logc_12 __attribute__((aligned(64))) = {
  UINT64_C(0x3fc365fcb0159000), UINT64_C(0x3fc4913d8333b000), UINT64_C(0x3fc527e5e4a1b000), UINT64_C(0x3fc6574ebe8c1000), UINT64_C(0x3fc6f0128b757000), UINT64_C(0x3fc7898d85445000), UINT64_C(0x3fc8beafeb390000), UINT64_C(0x3fc95a5adcf70000)
};
static const uv pw_pow_log_logc_13 __attribute__((aligned(64))) = {
  UINT64_C(0x3fca93ed3c8ae000), UINT64_C(0x3fcb31d8575bd000), UINT64_C(0x3fcbd087383be000), UINT64_C(0x3fcc6ffbc6f01000), UINT64_C(0x3fcdb13db0d49000), UINT64_C(0x3fce530effe71000), UINT64_C(0x3fcef5ade4dd0000), UINT64_C(0x3fcf991c6cb3b000)
};
static const uv pw_pow_log_logc_14 __attribute__((aligned(64))) = {
  UINT64_C(0x3fd07138604d5800), UINT64_C(0x3fd0c42d67616000), UINT64_C(0x3fd1178e8227e800), UINT64_C(0x3fd16b5ccbacf800), UINT64_C(0x3fd1bf99635a6800), UINT64_C(0x3fd214456d0eb800), UINT64_C(0x3fd2bef07cdc9000), UINT64_C(0x3fd314f1e1d36000)
};
static const uv pw_pow_log_logc_15 __attribute__((aligned(64))) = {
  UINT64_C(0x3fd36b6776be1000), UINT64_C(0x3fd3c25277333000), UINT64_C(0x3fd419b423d5e800), UINT64_C(0x3fd4718dc271c800), UINT64_C(0x3fd4c9e09e173000), UINT64_C(0x3fd522ae0738a000), UINT64_C(0x3fd57bf753c8d000), UINT64_C(0x3fd5d5bddf596000)
};
static const uv pw_pow_log_logtail_0 __attribute__((aligned(64))) = {
  UINT64_C(0x3cfab42428375680), UINT64_C(0xbd1ca508d8e0f720), UINT64_C(0xbd2362a4d5b6506d), UINT64_C(0xbce684e49eb067d5), UINT64_C(0xbd041b6993293ee0), UINT64_C(0x3d13d82f484c84cc), UINT64_C(0x3cdc42f3ed820b3a), UINT64_C(0x3d20b1c686519460)
};
static const uv pw_pow_log_logtail_1 __attribute__((aligned(64))) = {
  UINT64_C(0x3d25594dd4c58092), UINT64_C(0x3d267b1e99b72bd8), UINT64_C(0x3d15ca14b6cfb03f), UINT64_C(0x3d15ca14b6cfb03f), UINT64_C(0xbd165a242853da76), UINT64_C(0xbd1fafbc68e75404), UINT64_C(0x3d1f1fc63382a8f0), UINT64_C(0xbd26a8c4fd055a66)
};
static const uv pw_pow_log_logtail_2 __attribute__((aligned(64))) = {
  UINT64_C(0xbd0c6bee7ef4030e), UINT64_C(0xbcf036b89ef42d7f), UINT64_C(0xbcf036b89ef42d7f), UINT64_C(0x3d0d572aab993c87), UINT64_C(0x3d2b26b79c86af24), UINT64_C(0xbd172f4f543fff10), UINT64_C(0x3d21ba91bbca681b), UINT64_C(0x3d27794f689f8434)
};
static const uv pw_pow_log_logtail_3 __attribute__((aligned(64))) = {
  UINT64_C(0x3d27794f689f8434), UINT64_C(0x3d194eb0318bb78f), UINT64_C(0x3cba4e633fcd9066), UINT64_C(0xbd258c64dc46c1ea), UINT64_C(0xbd258c64dc46c1ea), UINT64_C(0xbd2ad1d904c1d4e3), UINT64_C(0x3d2bbdbf7fdbfa09), UINT64_C(0x3d2bdb9072534a58)
};
static const uv pw_pow_log_logtail_4 __attribute__((aligned(64))) = {
  UINT64_C(0x3d2bdb9072534a58), UINT64_C(0xbd10e46aa3b2e266), UINT64_C(0xbd1e9e439f105039), UINT64_C(0xbd1e9e439f105039), UINT64_C(0xbd20de8b90075b8f), UINT64_C(0x3d170cc16135783c), UINT64_C(0x3d170cc16135783c), UINT64_C(0x3cf178864d27543a)
};
static const uv pw_pow_log_logtail_5 __attribute__((aligned(64))) = {
  UINT64_C(0xbd248d301771c408), UINT64_C(0xbd2e80a41811a396), UINT64_C(0xbd2e80a41811a396), UINT64_C(0x3d0a699688e85bf4), UINT64_C(0x3d0a699688e85bf4), UINT64_C(0xbd2575545ca333f2), UINT64_C(0x3d2a342c2af0003c), UINT64_C(0x3d2a342c2af0003c)
};
static const uv pw_pow_log_logtail_6 __attribute__((aligned(64))) = {
  UINT64_C(0xbd1d0c57585fbe06), UINT64_C(0x3d253935e85baac8), UINT64_C(0x3d253935e85baac8), UINT64_C(0x3d137c294d2f5668), UINT64_C(0x3d137c294d2f5668), UINT64_C(0xbd269737c93373da), UINT64_C(0x3d1f025b61c65e57), UINT64_C(0x3d1f025b61c65e57)
};
static const uv pw_pow_log_logtail_7 __attribute__((aligned(64))) = {
  UINT64_C(0x3d2c5edaccf913df), UINT64_C(0x3d2c5edaccf913df), UINT64_C(0x3d147c5e768fa309), UINT64_C(0x3d2d599e83368e91), UINT64_C(0x3d2d599e83368e91), UINT64_C(0x3d1c827ae5d6704c), UINT64_C(0x3d1c827ae5d6704c), UINT64_C(0xbd2cfc4634f2a1ee)
};
static const uv pw_pow_log_logtail_8 __attribute__((aligned(64))) = {
  UINT64_C(0xbd2cfc4634f2a1ee), UINT64_C(0x3cf502b7f526feaa), UINT64_C(0x3cf502b7f526feaa), UINT64_C(0xbd2980267c7e09e4), UINT64_C(0xbd2980267c7e09e4), UINT64_C(0xbd288d5493faa639), UINT64_C(0xbcdf1e7cf6d3a69c), UINT64_C(0xbcdf1e7cf6d3a69c)
};
static const uv pw_pow_log_logtail_9 __attribute__((aligned(64))) = {
  UINT64_C(0xbd19e23f0dda40e4), UINT64_C(0xbd19e23f0dda40e4), UINT64_C(0x0000000000000000), UINT64_C(0x0000000000000000), UINT64_C(0xbd10c76b999d2be8), UINT64_C(0xbd23dc5b06e2f7d2), UINT64_C(0xbd2aa0ba325a0c34), UINT64_C(0x3d0111c05cf1d753)
};
static const uv pw_pow_log_logtail_10 __attribute__((aligned(64))) = {
  UINT64_C(0xbd2c167375bdfd28), UINT64_C(0xbd197995d05a267d), UINT64_C(0xbd1a68f247d82807), UINT64_C(0xbd0e113e4fc93b7b), UINT64_C(0xbd25325d560d9e9b), UINT64_C(0x3d2cc85ea5db4ed7), UINT64_C(0xbd2c69063c5d1d1e), UINT64_C(0x3cec1e8da99ded32)
};
static const uv pw_pow_log_logtail_11 __attribute__((aligned(64))) = {
  UINT64_C(0x3d23115c3abd47da), UINT64_C(0xbd1390802bf768e5), UINT64_C(0x3d2646d1c65aacd3), UINT64_C(0xbd2dc068afe645e0), UINT64_C(0xbd2534d64fa10afd), UINT64_C(0x3d21ef78ce2d07f2), UINT64_C(0x3d2ca78e44389934), UINT64_C(0x3d039d6ccb81b4a1)
};
static const uv pw_pow_log_logtail_12 __attribute__((aligned(64))) = {
  UINT64_C(0x3cc62fa8234b7289), UINT64_C(0x3d25837954fdb678), UINT64_C(0x3d2633e8e5697dc7), UINT64_C(0x3d19cf8b2c3c2e78), UINT64_C(0xbd25118de59c21e1), UINT64_C(0xbd1c661070914305), UINT64_C(0xbd073d54aae92cd1), UINT64_C(0x3d07f22858a0ff6f)
};
static const uv pw_pow_log_logtail_13 __attribute__((aligned(64))) = {
  UINT64_C(0xbd28724350562169), UINT64_C(0xbd0c358d4eace1aa), UINT64_C(0xbd2d4bc4595412b6), UINT64_C(0xbcf1ec72c5962bd2), UINT64_C(0xbd2aff2af715b035), UINT64_C(0x3cc212276041f430), UINT64_C(0xbcca211565bb8e11), UINT64_C(0x3d1bcbecca0cdf30)
};
static const uv pw_pow_log_logtail_14 __attribute__((aligned(64))) = {
  UINT64_C(0x3cf89cdb16ed4e91), UINT64_C(0x3d27188b163ceae9), UINT64_C(0xbd2c210e63a5f01c), UINT64_C(0x3d2b9acdf7a51681), UINT64_C(0x3d2ca6ed5147bdb7), UINT64_C(0x3d0a87deba46baea), UINT64_C(0x3d2a9cfa4a5004f4), UINT64_C(0xbd28e27ad3213cb8)
};
static const uv pw_pow_log_logtail_15 __attribute__((aligned(64))) = {
  UINT64_C(0x3d116ecdb0f177c8), UINT64_C(0x3d183b54b606bd5c), UINT64_C(0x3d08e436ec90e09d), UINT64_C(0xbd2f27ce0967d675), UINT64_C(0xbd2e20891b0ad8a4), UINT64_C(0x3d2ebe708164c759), UINT64_C(0x3d1fadedee5d40ef), UINT64_C(0xbd0a0b2a08a465dc)
};
static const uv pw_pow_exp_tail_0 __attribute__((aligned(64))) = {
  UINT64_C(0x0000000000000000), UINT64_C(0x3c9b3b4f1a88bf6e), UINT64_C(0xbc7160139cd8dc5d), UINT64_C(0xbc905e7a108766d1), UINT64_C(0x3c8cd2523567f613), UINT64_C(0xbc8bce8023f98efa), UINT64_C(0x3c60f74e61e6c861), UINT64_C(0x3c90a3e45b33d399)
};
static const uv pw_pow_exp_tail_1 __attribute__((aligned(64))) = {
  UINT64_C(0x3c979aa65d837b6d), UINT64_C(0x3c8eb51a92fdeffc), UINT64_C(0x3c3ebe3d702f9cd1), UINT64_C(0xbc6a033489906e0b), UINT64_C(0xbc9556522a2fbd0e), UINT64_C(0xbc5080ef8c4eea55), UINT64_C(0xbc91c923b9d5f416), UINT64_C(0x3c80d3e3e95c55af)
};
static const uv pw_pow_exp_tail_2 __attribute__((aligned(64))) = {
  UINT64_C(0xbc801b15eaa59348), UINT64_C(0xbc8f1ff055de323d), UINT64_C(0x3c8b898c3f1353bf), UINT64_C(0xbc96d99c7611eb26), UINT64_C(0x3c9aecf73e3a2f60), UINT64_C(0xbc8fe782cb86389d), UINT64_C(0x3c8a6f4144a6c38d), UINT64_C(0x3c807a05b0e4047d)
};
static const uv pw_pow_exp_tail_3 __attribute__((aligned(64))) = {
  UINT64_C(0x3c968efde3a8a894), UINT64_C(0x3c875e18f274487d), UINT64_C(0x3c80472b981fe7f2), UINT64_C(0xbc96b87b3f71085e), UINT64_C(0x3c82f7e16d09ab31), UINT64_C(0xbc3d219b1a6fbffa), UINT64_C(0x3c8b3782720c0ab4), UINT64_C(0x3c6e149289cecb8f)
};
static const uv pw_pow_exp_tail_4 __attribute__((aligned(64))) = {
  UINT64_C(0x3c834d754db0abb6), UINT64_C(0x3c864201e2ac744c), UINT64_C(0x3c8fdd395dd3f84a), UINT64_C(0xbc86a3803b8e5b04), UINT64_C(0xbc924aedcc4b5068), UINT64_C(0xbc9907f81b512d8e), UINT64_C(0xbc71d1e83e9436d2), UINT64_C(0xbc991919b3ce1b15)
};
static const uv pw_pow_exp_tail_5 __attribute__((aligned(64))) = {
  UINT64_C(0x3c859f48a72a4c6d), UINT64_C(0xbc9312607a28698a), UINT64_C(0xbc58a78f4817895b), UINT64_C(0xbc7c2c9b67499a1b), UINT64_C(0x3c4363ed60c2ac11), UINT64_C(0x3c9666093b0664ef), UINT64_C(0x3c6ecce1daa10379), UINT64_C(0x3c93ff8e3f0f1230)
};
static const uv pw_pow_exp_tail_6 __attribute__((aligned(64))) = {
  UINT64_C(0x3c7690cebb7aafb0), UINT64_C(0x3c931dbdeb54e077), UINT64_C(0xbc8f94340071a38e), UINT64_C(0xbc87deccdc93a349), UINT64_C(0xbc78dec6bd0f385f), UINT64_C(0xbc861246ec7b5cf6), UINT64_C(0x3c93350518fdd78e), UINT64_C(0x3c7b98b72f8a9b05)
};
static const uv pw_pow_exp_tail_7 __attribute__((aligned(64))) = {
  UINT64_C(0x3c9063e1e21c5409), UINT64_C(0x3c34c7855019c6ea), UINT64_C(0x3c9432e62b64c035), UINT64_C(0xbc8ce44a6199769f), UINT64_C(0xbc8c33c53bef4da8), UINT64_C(0xbc845378892be9ae), UINT64_C(0xbc93cedd78565858), UINT64_C(0x3c5710aa807e1964)
};
static const uv pw_pow_exp_tail_8 __attribute__((aligned(64))) = {
  UINT64_C(0xbc93b3efbf5e2228), UINT64_C(0xbc6a12ad8734b982), UINT64_C(0xbc6367efb86da9ee), UINT64_C(0xbc80dc3d54e08851), UINT64_C(0xbc781f647e5a3ecf), UINT64_C(0xbc86ee4ac08b7db0), UINT64_C(0xbc8619321e55e68a), UINT64_C(0x3c909ccb5e09d4d3)
};
static const uv pw_pow_exp_tail_9 __attribute__((aligned(64))) = {
  UINT64_C(0xbc7b32dcb94da51d), UINT64_C(0x3c94ecfd5467c06b), UINT64_C(0x3c65ebe1abd66c55), UINT64_C(0xbc88a1c52fb3cf42), UINT64_C(0xbc9369b6f13b3734), UINT64_C(0xbc805e843a19ff1e), UINT64_C(0xbc94d450d872576e), UINT64_C(0x3c90ad675b0e8a00)
};
static const uv pw_pow_exp_tail_10 __attribute__((aligned(64))) = {
  UINT64_C(0x3c8db72fc1f0eab4), UINT64_C(0xbc65b6609cc5e7ff), UINT64_C(0x3c7bf68359f35f44), UINT64_C(0xbc93091fa71e3d83), UINT64_C(0xbc5da9b88b6c1e29), UINT64_C(0xbc6c23f97c90b959), UINT64_C(0xbc92434322f4f9aa), UINT64_C(0xbc85ca6cd7668e4b)
};
static const uv pw_pow_exp_tail_11 __attribute__((aligned(64))) = {
  UINT64_C(0x3c71affc2b91ce27), UINT64_C(0x3c6dd235e10a73bb), UINT64_C(0xbc87c50422622263), UINT64_C(0x3c8b1c86e3e231d5), UINT64_C(0xbc91bbd1d3bcbb15), UINT64_C(0x3c90cc319cee31d2), UINT64_C(0x3c8469846e735ab3), UINT64_C(0xbc82dfcd978e9db4)
};
static const uv pw_pow_exp_tail_12 __attribute__((aligned(64))) = {
  UINT64_C(0x3c8c1a7792cb3387), UINT64_C(0xbc907b8f4ad1d9fa), UINT64_C(0xbc55c3d956dcaeba), UINT64_C(0xbc90a40e3da6f640), UINT64_C(0xbc68d6f438ad9334), UINT64_C(0xbc91eee26b588a35), UINT64_C(0x3c74ffd70a5fddcd), UINT64_C(0xbc91bdfbfa9298ac)
};
static const uv pw_pow_exp_tail_13 __attribute__((aligned(64))) = {
  UINT64_C(0x3c736eae30af0cb3), UINT64_C(0x3c8ee3325c9ffd94), UINT64_C(0x3c84e08fd10959ac), UINT64_C(0x3c63cdaf384e1a67), UINT64_C(0x3c676b2c6c921968), UINT64_C(0xbc808a1883ccb5d2), UINT64_C(0xbc8fad5d3ffffa6f), UINT64_C(0xbc900dae3875a949)
};
static const uv pw_pow_exp_tail_14 __attribute__((aligned(64))) = {
  UINT64_C(0x3c74a385a63d07a7), UINT64_C(0xbc82919e2040220f), UINT64_C(0x3c8e5a50d5c192ac), UINT64_C(0x3c843a59ac016b4b), UINT64_C(0xbc82d52107b43e1f), UINT64_C(0xbc892ab93b470dc9), UINT64_C(0x3c74b604603a88d3), UINT64_C(0x3c83c5ec519d7271)
};
static const uv pw_pow_exp_tail_15 __attribute__((aligned(64))) = {
  UINT64_C(0xbc8ff7128fd391f0), UINT64_C(0xbc8dae98e223747d), UINT64_C(0x3c8ec3bc41aa2008), UINT64_C(0x3c842b94c3a9eb32), UINT64_C(0x3c8a64a931d185ee), UINT64_C(0xbc8e37bae43be3ed), UINT64_C(0x3c77893b4d91cd9d), UINT64_C(0x3c5305c14160cc89)
};
static const uv pw_pow_exp_scale_0 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff0000000000000), UINT64_C(0x3feff63da9fb3335), UINT64_C(0x3fefec9a3e778061), UINT64_C(0x3fefe315e86e7f85), UINT64_C(0x3fefd9b0d3158574), UINT64_C(0x3fefd06b29ddf6de), UINT64_C(0x3fefc74518759bc8), UINT64_C(0x3fefbe3ecac6f383)
};
static const uv pw_pow_exp_scale_1 __attribute__((aligned(64))) = {
  UINT64_C(0x3fefb5586cf9890f), UINT64_C(0x3fefac922b7247f7), UINT64_C(0x3fefa3ec32d3d1a2), UINT64_C(0x3fef9b66affed31b), UINT64_C(0x3fef9301d0125b51), UINT64_C(0x3fef8abdc06c31cc), UINT64_C(0x3fef829aaea92de0), UINT64_C(0x3fef7a98c8a58e51)
};
static const uv pw_pow_exp_scale_2 __attribute__((aligned(64))) = {
  UINT64_C(0x3fef72b83c7d517b), UINT64_C(0x3fef6af9388c8dea), UINT64_C(0x3fef635beb6fcb75), UINT64_C(0x3fef5be084045cd4), UINT64_C(0x3fef54873168b9aa), UINT64_C(0x3fef4d5022fcd91d), UINT64_C(0x3fef463b88628cd6), UINT64_C(0x3fef3f49917ddc96)
};
static const uv pw_pow_exp_scale_3 __attribute__((aligned(64))) = {
  UINT64_C(0x3fef387a6e756238), UINT64_C(0x3fef31ce4fb2a63f), UINT64_C(0x3fef2b4565e27cdd), UINT64_C(0x3fef24dfe1f56381), UINT64_C(0x3fef1e9df51fdee1), UINT64_C(0x3fef187fd0dad990), UINT64_C(0x3fef1285a6e4030b), UINT64_C(0x3fef0cafa93e2f56)
};
static const uv pw_pow_exp_scale_4 __attribute__((aligned(64))) = {
  UINT64_C(0x3fef06fe0a31b715), UINT64_C(0x3fef0170fc4cd831), UINT64_C(0x3feefc08b26416ff), UINT64_C(0x3feef6c55f929ff1), UINT64_C(0x3feef1a7373aa9cb), UINT64_C(0x3feeecae6d05d866), UINT64_C(0x3feee7db34e59ff7), UINT64_C(0x3feee32dc313a8e5)
};
static const uv pw_pow_exp_scale_5 __attribute__((aligned(64))) = {
  UINT64_C(0x3feedea64c123422), UINT64_C(0x3feeda4504ac801c), UINT64_C(0x3feed60a21f72e2a), UINT64_C(0x3feed1f5d950a897), UINT64_C(0x3feece086061892d), UINT64_C(0x3feeca41ed1d0057), UINT64_C(0x3feec6a2b5c13cd0), UINT64_C(0x3feec32af0d7d3de)
};
static const uv pw_pow_exp_scale_6 __attribute__((aligned(64))) = {
  UINT64_C(0x3feebfdad5362a27), UINT64_C(0x3feebcb299fddd0d), UINT64_C(0x3feeb9b2769d2ca7), UINT64_C(0x3feeb6daa2cf6642), UINT64_C(0x3feeb42b569d4f82), UINT64_C(0x3feeb1a4ca5d920f), UINT64_C(0x3feeaf4736b527da), UINT64_C(0x3feead12d497c7fd)
};
static const uv pw_pow_exp_scale_7 __attribute__((aligned(64))) = {
  UINT64_C(0x3feeab07dd485429), UINT64_C(0x3feea9268a5946b7), UINT64_C(0x3feea76f15ad2148), UINT64_C(0x3feea5e1b976dc09), UINT64_C(0x3feea47eb03a5585), UINT64_C(0x3feea34634ccc320), UINT64_C(0x3feea23882552225), UINT64_C(0x3feea155d44ca973)
};
static const uv pw_pow_exp_scale_8 __attribute__((aligned(64))) = {
  UINT64_C(0x3feea09e667f3bcd), UINT64_C(0x3feea012750bdabf), UINT64_C(0x3fee9fb23c651a2f), UINT64_C(0x3fee9f7df9519484), UINT64_C(0x3fee9f75e8ec5f74), UINT64_C(0x3fee9f9a48a58174), UINT64_C(0x3fee9feb564267c9), UINT64_C(0x3feea0694fde5d3f)
};
static const uv pw_pow_exp_scale_9 __attribute__((aligned(64))) = {
  UINT64_C(0x3feea11473eb0187), UINT64_C(0x3feea1ed0130c132), UINT64_C(0x3feea2f336cf4e62), UINT64_C(0x3feea427543e1a12), UINT64_C(0x3feea589994cce13), UINT64_C(0x3feea71a4623c7ad), UINT64_C(0x3feea8d99b4492ed), UINT64_C(0x3feeaac7d98a6699)
};
static const uv pw_pow_exp_scale_10 __attribute__((aligned(64))) = {
  UINT64_C(0x3feeace5422aa0db), UINT64_C(0x3feeaf3216b5448c), UINT64_C(0x3feeb1ae99157736), UINT64_C(0x3feeb45b0b91ffc6), UINT64_C(0x3feeb737b0cdc5e5), UINT64_C(0x3feeba44cbc8520f), UINT64_C(0x3feebd829fde4e50), UINT64_C(0x3feec0f170ca07ba)
};
static const uv pw_pow_exp_scale_11 __attribute__((aligned(64))) = {
  UINT64_C(0x3feec49182a3f090), UINT64_C(0x3feec86319e32323), UINT64_C(0x3feecc667b5de565), UINT64_C(0x3feed09bec4a2d33), UINT64_C(0x3feed503b23e255d), UINT64_C(0x3feed99e1330b358), UINT64_C(0x3feede6b5579fdbf), UINT64_C(0x3feee36bbfd3f37a)
};
static const uv pw_pow_exp_scale_12 __attribute__((aligned(64))) = {
  UINT64_C(0x3feee89f995ad3ad), UINT64_C(0x3feeee07298db666), UINT64_C(0x3feef3a2b84f15fb), UINT64_C(0x3feef9728de5593a), UINT64_C(0x3feeff76f2fb5e47), UINT64_C(0x3fef05b030a1064a), UINT64_C(0x3fef0c1e904bc1d2), UINT64_C(0x3fef12c25bd71e09)
};
static const uv pw_pow_exp_scale_13 __attribute__((aligned(64))) = {
  UINT64_C(0x3fef199bdd85529c), UINT64_C(0x3fef20ab5fffd07a), UINT64_C(0x3fef27f12e57d14b), UINT64_C(0x3fef2f6d9406e7b5), UINT64_C(0x3fef3720dcef9069), UINT64_C(0x3fef3f0b555dc3fa), UINT64_C(0x3fef472d4a07897c), UINT64_C(0x3fef4f87080d89f2)
};
static const uv pw_pow_exp_scale_14 __attribute__((aligned(64))) = {
  UINT64_C(0x3fef5818dcfba487), UINT64_C(0x3fef60e316c98398), UINT64_C(0x3fef69e603db3285), UINT64_C(0x3fef7321f301b460), UINT64_C(0x3fef7c97337b9b5f), UINT64_C(0x3fef864614f5a129), UINT64_C(0x3fef902ee78b3ff6), UINT64_C(0x3fef9a51fbc74c83)
};
static const uv pw_pow_exp_scale_15 __attribute__((aligned(64))) = {
  UINT64_C(0x3fefa4afa2a490da), UINT64_C(0x3fefaf482d8e67f1), UINT64_C(0x3fefba1bee615a27), UINT64_C(0x3fefc52b376bba97), UINT64_C(0x3fefd0765b6e4540), UINT64_C(0x3fefdbfdad9cbe14), UINT64_C(0x3fefe7c1819e90d8), UINT64_C(0x3feff3c22b8f71f1)
};

static __attribute__((always_inline)) inline void pw_pow_log_register_lookup(uv key, uv *log_invc, uv *log_logc, uv *log_logtail) {
  const uv keys=key&UINT64_C(127),group=keys>>3;
  const v8di selector=(v8di)(keys&UINT64_C(7));
  uv log_invc_bits={0};
  uv log_logc_bits={0};
  uv log_logtail_bits={0};
  {
    const uv keep=(uv)(group==UINT64_C(0));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_0,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_0,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_0,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(1));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_1,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_1,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_1,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(2));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_2,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_2,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_2,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(3));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_3,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_3,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_3,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(4));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_4,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_4,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_4,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(5));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_5,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_5,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_5,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(6));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_6,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_6,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_6,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(7));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_7,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_7,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_7,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(8));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_8,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_8,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_8,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(9));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_9,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_9,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_9,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(10));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_10,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_10,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_10,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(11));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_11,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_11,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_11,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(12));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_12,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_12,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_12,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(13));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_13,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_13,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_13,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(14));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_14,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_14,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_14,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(15));
    log_invc_bits|=__builtin_shuffle(pw_pow_log_invc_15,selector)&keep;
    log_logc_bits|=__builtin_shuffle(pw_pow_log_logc_15,selector)&keep;
    log_logtail_bits|=__builtin_shuffle(pw_pow_log_logtail_15,selector)&keep;
  }
  *log_invc=log_invc_bits;
  *log_logc=log_logc_bits;
  *log_logtail=log_logtail_bits;
}

static __attribute__((always_inline)) inline void pw_pow_exp_register_lookup(uv key, uv *exp_tail, uv *exp_scale) {
  const uv keys=key&UINT64_C(127),group=keys>>3;
  const v8di selector=(v8di)(keys&UINT64_C(7));
  uv exp_tail_bits={0};
  uv exp_scale_bits={0};
  {
    const uv keep=(uv)(group==UINT64_C(0));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_0,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_0,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(1));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_1,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_1,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(2));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_2,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_2,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(3));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_3,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_3,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(4));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_4,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_4,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(5));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_5,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_5,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(6));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_6,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_6,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(7));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_7,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_7,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(8));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_8,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_8,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(9));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_9,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_9,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(10));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_10,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_10,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(11));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_11,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_11,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(12));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_12,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_12,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(13));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_13,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_13,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(14));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_14,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_14,selector)&keep;
  }
  {
    const uv keep=(uv)(group==UINT64_C(15));
    exp_tail_bits|=__builtin_shuffle(pw_pow_exp_tail_15,selector)&keep;
    exp_scale_bits|=__builtin_shuffle(pw_pow_exp_scale_15,selector)&keep;
  }
  *exp_tail=exp_tail_bits;
  *exp_scale=exp_scale_bits;
}

/* Complete64B integer observability prevents a narrow predicate-pack
 * expression at this boundary. Emission still needs its own compiler proof. */
static __attribute__((always_inline)) inline uv pw_pow_wide_boundary_i64(uv value) {
  volatile uv wide;
  wide=value;
  return wide;
}

/* Alias-safe qword snapshot for scalar integer classification. The pointer
 * observes object bytes; no double/uint64_t pointer punning is used. Volatile
 * qword destinations and the existing noinline policy keep the reads real.
 * No FP expression, environment API or status operation occurs here. */
static __attribute__((noinline)) void pw_pow_snapshot_i64(const void *source,
    volatile uint64_t output[8]) {
  const unsigned char *bytes=source;
  for(unsigned i=0;i<8;++i) {
    uint64_t word;memcpy(&word,bytes+8*i,8);output[i]=word;
  }
}

static uv pw_pow_lane_mask(unsigned active) {
  const uv lanes={1ULL,2ULL,4ULL,8ULL,16ULL,32ULL,64ULL,128ULL};
  const uv requested=(uv){0}+(uint64_t)active;
  return pw_pow_wide_boundary_i64((uv)((requested&lanes)!=UINT64_C(0)));
}

/* The signed reduction exponent k is in[-1075,1024]. Adding its modulo2^64
 * representation to the bits of1.5*2^52 changes that binary64 by exactly k;
 * subtracting1.5*2^52 is exact in every RC. Actual target event proof remains
 * required; no float-control write or int32 pack/unpack is introduced. */
static dv pw_pow_exact_small_i64_to_dp(iv k) {
  uv bits;memcpy(&bits,&k,64);
  const uv biased=bits+UINT64_C(0x4338000000000000);
  dv value;memcpy(&value,&biased,64);
  return value-0x1.8p52;
}

static unsigned kind(uint64_t x) {
  unsigned e=(x>>52)&2047;
  if(e<1023)return 0;if(e>1075)return 2;
  unsigned shift=1075-e;
  if(x&((UINT64_C(1)<<shift)-1))return 0;
  return (x&(UINT64_C(1)<<shift))?1:2;
}
static unsigned snan(uint64_t x){return (x&UINT64_C(0x7fffffffffffffff))>UINT64_C(0x7ff0000000000000)&&!(x&UINT64_C(0x0008000000000000));}
static dv frombits(uv bits){dv result;memcpy(&result,&bits,64);return result;}
static uv tobits(dv value){uv result;memcpy(&result,&value,64);return result;}
static __attribute__((noinline)) void core(const uint64_t x[8],const uint64_t y[8],uint64_t output[8]) {
  uint64_t ax[8],ay[8],norm[8],sign[8]={0},special[8]={0};
  unsigned direct=0,nans=0,invalid=0,divzero=0,subnormal=0,tiny_y=0,overflow=0,underflow=0;
  for(unsigned i=0;i<8;++i) {
    uint64_t xb=x[i],yb=y[i],xm=xb&UINT64_C(0x7fffffffffffffff),ym=yb&UINT64_C(0x7fffffffffffffff);
    ax[i]=norm[i]=UINT64_C(0x3ff0000000000000);ay[i]=0;
    if(!ym){if(snan(xb))nans|=1u<<i;else{direct|=1u<<i;special[i]=UINT64_C(0x3ff0000000000000);}continue;}
    if(xb==UINT64_C(0x3ff0000000000000)){if(snan(yb))nans|=1u<<i;else{direct|=1u<<i;special[i]=UINT64_C(0x3ff0000000000000);}continue;}
    if(xm>UINT64_C(0x7ff0000000000000)||ym>UINT64_C(0x7ff0000000000000)){nans|=1u<<i;continue;}
    if(ym==UINT64_C(0x7ff0000000000000)) {
      direct|=1u<<i;special[i]=xm==UINT64_C(0x3ff0000000000000)?UINT64_C(0x3ff0000000000000):
        ((xm<UINT64_C(0x3ff0000000000000))==!(yb>>63)?0:UINT64_C(0x7ff0000000000000));continue;
    }
    unsigned integer=kind(yb);sign[i]=(xb>>63)&&integer==1?UINT64_C(0x8000000000000000):0;
    if(!xm||xm==UINT64_C(0x7ff0000000000000)) {
      direct|=1u<<i;special[i]=sign[i]|((!xm)==!(yb>>63)?0:UINT64_C(0x7ff0000000000000));
      if(!xm&&(yb>>63))divzero|=1u<<i;continue;
    }
    if((xb>>63)&&!integer){invalid|=1u<<i;continue;}
    if(ym<UINT64_C(0x3be0000000000000)){tiny_y|=1u<<i;continue;}
    if(ym>=UINT64_C(0x43e0000000000000)) {
      if(xm==UINT64_C(0x3ff0000000000000)){direct|=1u<<i;special[i]=UINT64_C(0x3ff0000000000000);}
      else if((xm>UINT64_C(0x3ff0000000000000))==!(yb>>63))overflow|=1u<<i;
      else underflow|=1u<<i;
      continue;
    }
    ax[i]=xm;ay[i]=yb;
    if(xm<UINT64_C(0x0010000000000000)){subnormal|=1u<<i;norm[i]=xm;}
  }
  if(subnormal) {
    dv v;memcpy(&v,norm,64);v*=0x1p52;uint64_t bits[8];memcpy(bits,&v,64);
    for(unsigned i=0;i<8;++i)if(subnormal&(1u<<i))ax[i]=bits[i]-(UINT64_C(52)<<52);
  }
  uv ix;memcpy(&ix,ax,64);
  const uv offset=ix-UINT64_C(0x3fe6955500000000),index=(offset>>45)&127,iz=ix-(offset&UINT64_C(0xfff0000000000000));
  iv signed_offset;memcpy(&signed_offset,&offset,64);const dv kd=pw_pow_exact_small_i64_to_dp(signed_offset>>52),z=frombits(iz);
  dv invc,logc,logtail;
  uv invc_words,logc_words,logtail_words;
  pw_pow_log_register_lookup(index,&invc_words,&logc_words,&logtail_words);
  memcpy(&invc,&invc_words,64);memcpy(&logc,&logc_words,64);memcpy(&logtail,&logtail_words,64);
  const dv zhi=frombits((iz+(UINT64_C(1)<<31))&UINT64_C(0xffffffff00000000)),zlo=z-zhi;
  const dv rhi=zhi*invc-1,rlo=zlo*invc,r=rhi+rlo;
  const dv t1=kd*__pow_log_data.ln2hi+logc,t2=t1+r,lo1=kd*__pow_log_data.ln2lo+logtail,lo2=t1-t2+r;
  const dv ar=__pow_log_data.poly[0]*r,ar2=r*ar,ar3=r*ar2,arhi=__pow_log_data.poly[0]*rhi,arhi2=rhi*arhi;
  const dv hi=t2+arhi2,lo3=rlo*(ar+arhi),lo4=t2-hi+arhi2;
  const dv p=ar3*(__pow_log_data.poly[1]+r*__pow_log_data.poly[2]+ar2*(__pow_log_data.poly[3]+r*__pow_log_data.poly[4]+ar2*(__pow_log_data.poly[5]+r*__pow_log_data.poly[6])));
  const dv lo=lo1+lo2+lo3+lo4+p,loghi=hi+lo,loglo=hi-loghi+lo;
  dv yd;memcpy(&yd,ay,64);
  const dv yhi=frombits(tobits(yd)&UINT64_C(0xfffffffff8000000)),ylo=yd-yhi;
  const dv lhi=frombits(tobits(loghi)&UINT64_C(0xfffffffff8000000)),llo=loghi-lhi+loglo;
  dv ehi=yhi*lhi,elo=ylo*lhi+yd*llo;
  uint64_t ewords[8];pw_pow_snapshot_i64(&ehi,ewords);
  unsigned tiny_exp=0,large_pos=0,large_neg=0;
  for(unsigned i=0;i<8;++i) {
    unsigned top=(ewords[i]>>52)&2047;
    if(top<969){tiny_exp|=1u<<i;ehi[i]=0;elo[i]=0;}
    else if(top>=1033){if(ewords[i]>>63)underflow|=1u<<i;else overflow|=1u<<i;ehi[i]=0;elo[i]=0;}
    else if(top>=1032){if(ewords[i]>>63)large_neg|=1u<<i;else large_pos|=1u<<i;}
  }
  dv eround=ehi*__exp_data.invln2N+__exp_data.shift;uv ki=tobits(eround);eround-=__exp_data.shift;
  const dv er=ehi+eround*__exp_data.negln2hiN+eround*__exp_data.negln2loN+elo,er2=er*er;
  uv sbits;dv tail;
  uv tail_words,scale_words,sign_words;memcpy(&sign_words,sign,64);
  pw_pow_exp_register_lookup(ki,&tail_words,&scale_words);memcpy(&tail,&tail_words,64);
  const uv signed_bias=(uv)(sign_words!=UINT64_C(0))&UINT64_C(262144);
  sbits=scale_words+((ki+signed_bias)<<45);
  const dv tmp=tail+er+er2*(__exp_data.poly[0]+er*__exp_data.poly[1])+er2*er2*(__exp_data.poly[2]+er*__exp_data.poly[3]);
  uv normal=sbits;for(unsigned i=0;i<8;++i)if((large_pos|large_neg)&(1u<<i))normal[i]=UINT64_C(0x3ff0000000000000);
  const dv scale=frombits(normal),approx=scale+scale*tmp;memcpy(output,&approx,64);
  if(large_pos) {
    uv bits=(uv){0}+UINT64_C(0x3ff0000000000000);dv t=(dv){0};
    for(unsigned i=0;i<8;++i)if(large_pos&(1u<<i)){bits[i]=sbits[i]-(UINT64_C(1009)<<52);t[i]=tmp[i];}
    const dv s=frombits(bits),v=(s+s*t)*0x1p1009;uint64_t out[8];memcpy(out,&v,64);
    for(unsigned i=0;i<8;++i)if(large_pos&(1u<<i))output[i]=out[i];
  }
  if(large_neg) {
    uv bits=(uv){0}+UINT64_C(0x3ff0000000000000);dv t=(dv){0};
    for(unsigned i=0;i<8;++i)if(large_neg&(1u<<i)){bits[i]=sbits[i]+(UINT64_C(1022)<<52);t[i]=tmp[i];}
    const dv s=frombits(bits);dv v=s+s*t;unsigned sub=0;
    uint64_t vwords[8];pw_pow_snapshot_i64(&v,vwords);
    for(unsigned i=0;i<8;++i)if((large_neg&(1u<<i))&&(vwords[i]&UINT64_C(0x7fffffffffffffff))<UINT64_C(0x3ff0000000000000))sub|=1u<<i;
    if(sub) {
      dv one=(dv){0}+1;
    const uv sub_mask=pw_pow_lane_mask(sub);
    uv repair_sign;memcpy(&repair_sign,sign,64);
    const uv one_bits=tobits(one)|(repair_sign&sub_mask);
    one=frombits(pw_pow_wide_boundary_i64(one_bits));
      dv low=s-v+s*t;const dv high=one+v;low=one-high+v+low;const dv rounded=(high+low)-one;
      for(unsigned i=0;i<8;++i)if(sub&(1u<<i))v[i]=rounded[i];
      uv vb=tobits(v);
      const uv zero_mask=pw_pow_wide_boundary_i64((uv)((vb&UINT64_C(0x7fffffffffffffff))==UINT64_C(0)));
      const uv repair_mask=zero_mask&sub_mask;
      vb=pw_pow_wide_boundary_i64((vb&~repair_mask)|(repair_sign&repair_mask));
      v=frombits(vb);
      volatile double factor=0x1p-1022;volatile double force=factor*factor;(void)force;
    }
    const dv vout=0x1p-1022*v;uint64_t out[8];memcpy(out,&vout,64);
    for(unsigned i=0;i<8;++i)if(large_neg&(1u<<i))output[i]=out[i];
  }
  if(tiny_exp) {
    dv a=(dv){0};for(unsigned i=0;i<8;++i)if(tiny_exp&(1u<<i))memcpy(&a[i],&ewords[i],8);
    const dv v=1+a;uint64_t out[8];memcpy(out,&v,64);for(unsigned i=0;i<8;++i)if(tiny_exp&(1u<<i))output[i]=out[i]^sign[i];
  }
  if(tiny_y) {
    dv a=(dv){0};for(unsigned i=0;i<8;++i)if(tiny_y&(1u<<i)){memcpy(&a[i],&y[i],8);if((x[i]&UINT64_C(0x7fffffffffffffff))<UINT64_C(0x3ff0000000000000))a[i]=-a[i];}
    const dv v=1+a;uint64_t out[8];memcpy(out,&v,64);for(unsigned i=0;i<8;++i)if(tiny_y&(1u<<i))output[i]=out[i];
  }
  if(nans) {
    dv a=(dv){0},b=(dv){0};for(unsigned i=0;i<8;++i)if(nans&(1u<<i)){memcpy(&a[i],&x[i],8);memcpy(&b[i],&y[i],8);}
    const dv v=a+b;uint64_t out[8];memcpy(out,&v,64);for(unsigned i=0;i<8;++i)if(nans&(1u<<i))output[i]=out[i];
  }
  if(invalid||divzero) {
    volatile double one=1;dv a=(dv){0}+1,b=(dv){0}+1;
    for(unsigned i=0;i<8;++i){if(invalid&(1u<<i)){a[i]=0;b[i]=0;}if(divzero&(1u<<i)){a[i]=sign[i]?-one:one;b[i]=0;}}
    const dv v=a/b;uint64_t out[8];memcpy(out,&v,64);
    for(unsigned i=0;i<8;++i){if(invalid&(1u<<i))output[i]=out[i];if(divzero&(1u<<i))special[i]=out[i];}
  }
  if(overflow||underflow) {
    volatile double big=0x1p769,small=0x1p-767;dv a=(dv){0}+1,b=(dv){0}+1;
    for(unsigned i=0;i<8;++i){if(overflow&(1u<<i)){a[i]=sign[i]?-big:big;b[i]=big;}if(underflow&(1u<<i)){a[i]=sign[i]?-small:small;b[i]=small;}}
    const dv v=a*b;uint64_t out[8];memcpy(out,&v,64);for(unsigned i=0;i<8;++i)if((overflow|underflow)&(1u<<i))output[i]=out[i];
  }
  for(unsigned i=0;i<8;++i)if(direct&(1u<<i))output[i]=special[i];
}
int phi_host_pow_register_i64_wide_e8(const uint64_t x[8],const uint64_t y[8],unsigned active,const uint64_t merge[8],uint64_t output[8]) {
  if(active&~255u)return 1;
  uint64_t ax[8],ay[8],pass[8],result[8];memcpy(ax,x,64);memcpy(ay,y,64);memcpy(pass,merge,64);
  if(!active){memcpy(output,pass,64);return 0;}
  const uv mask=pw_pow_lane_mask(active);uv xb,yb,mb;
  memcpy(&xb,ax,64);memcpy(&yb,ay,64);memcpy(&mb,pass,64);
  xb=(xb&mask)|(((uv){0}+UINT64_C(0x3ff0000000000000))&~mask);yb&=mask;
  memcpy(ax,&xb,64);memcpy(ay,&yb,64);core(ax,ay,result);
  uv computed;memcpy(&computed,result,64);computed=(computed&mask)|(mb&~mask);
  memcpy(output,&computed,64);return 0;
}
