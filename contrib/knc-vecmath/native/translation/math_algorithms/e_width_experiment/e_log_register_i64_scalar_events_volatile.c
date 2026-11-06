/* Additive64-bit-lane source candidate; original source/header preserved.
 * No inherited host accuracy, target ABI/ISA or G5 qualification.
 * Arm table copyrights/licenses in the original algorithm comments apply. */
/* New gather-free DP8 log candidate; original FP expressions unchanged. */
/* Fresh parameterized host e-width adaptation; old source SHA256 67c29bad8761baa04e5c17a40a1854dabd6acc29768c210295e12d6ac98ba446.
 * Private pointer ABI only; software mask is not a GNU masked-vector ABI. */
#define PW_LANES 8
#define PW_ALL ((1u<<PW_LANES)-1u)
/* Adapted from Arm optimized-routines v26.01 log.c/log_data.c/math_err.c.
 * Copyright (c) 2018-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Commit649ccc8411e7c4862965710f25c570d854a1483f, exact data/license retained.
 * GCC four-lane adaptation, exact subnormal normalization and branch-lane
 * sanitization. No scalar log delegation, _ZGV exports or target qualification.
 */
#include "e_algorithms.h"
#include "math_config.h"
#include <string.h>
typedef double pw_f64v __attribute__((vector_size(PW_LANES*8)));
typedef unsigned long long pw_u64v __attribute__((vector_size(PW_LANES*8)));
typedef long long pw_i64v __attribute__((vector_size(PW_LANES*8)));
_Static_assert(LOG_TABLE_BITS==7 && LOG_POLY_ORDER==6 && LOG_POLY1_ORDER==12 && HAVE_FAST_FMA==0,"unsupported upstream configuration");
/* Exact original table words reconstructed as64-bit constants; no integer narrowing. */
typedef long long v8di __attribute__((vector_size(64)));
static const pw_u64v pw_log_invc_0 __attribute__((aligned(64))) = {
  0x3ff734f0c3e0de9fULL, 0x3ff713786a2ce91fULL, 0x3ff6f26008fab5a0ULL, 0x3ff6d1a61f138c7dULL, 0x3ff6b1490bc5b4d1ULL, 0x3ff69147332f0cbaULL, 0x3ff6719f18224223ULL, 0x3ff6524f99a51ed9ULL
};
static const pw_u64v pw_log_invc_1 __attribute__((aligned(64))) = {
  0x3ff63356aa8f24c4ULL, 0x3ff614b36b9ddc14ULL, 0x3ff5f66452c65c4cULL, 0x3ff5d867b5912c4fULL, 0x3ff5babccb5b90deULL, 0x3ff59d61f2d91a78ULL, 0x3ff5805612465687ULL, 0x3ff56397cee76bd3ULL
};
static const pw_u64v pw_log_invc_2 __attribute__((aligned(64))) = {
  0x3ff54725e2a77f93ULL, 0x3ff52aff42064583ULL, 0x3ff50f22dbb2bddfULL, 0x3ff4f38f4734ded7ULL, 0x3ff4d843cfde2840ULL, 0x3ff4bd3ec078a3c8ULL, 0x3ff4a27fc3e0258aULL, 0x3ff4880524d48434ULL
};
static const pw_u64v pw_log_invc_3 __attribute__((aligned(64))) = {
  0x3ff46dce1b192d0bULL, 0x3ff453d9d3391854ULL, 0x3ff43a2744b4845aULL, 0x3ff420b54115f8fbULL, 0x3ff40782da3ef4b1ULL, 0x3ff3ee8f5d57fe8fULL, 0x3ff3d5d9a00b4ce9ULL, 0x3ff3bd60c010c12bULL
};
static const pw_u64v pw_log_invc_4 __attribute__((aligned(64))) = {
  0x3ff3a5242b75dab8ULL, 0x3ff38d22cd9fd002ULL, 0x3ff3755bc5847a1cULL, 0x3ff35dce49ad36e2ULL, 0x3ff34679984dd440ULL, 0x3ff32f5cceffcb24ULL, 0x3ff3187775a10d49ULL, 0x3ff301c8373e3990ULL
};
static const pw_u64v pw_log_invc_5 __attribute__((aligned(64))) = {
  0x3ff2eb4ebb95f841ULL, 0x3ff2d50a0219a9d1ULL, 0x3ff2bef9a8b7fd2aULL, 0x3ff2a91c7a0c1babULL, 0x3ff293726014b530ULL, 0x3ff27dfa5757a1f5ULL, 0x3ff268b39b1d3bbfULL, 0x3ff2539d838ff5bdULL
};
static const pw_u64v pw_log_invc_6 __attribute__((aligned(64))) = {
  0x3ff23eb7aac9083bULL, 0x3ff22a012ba940b6ULL, 0x3ff2157996cc4132ULL, 0x3ff201201dd2fc9bULL, 0x3ff1ecf4494d480bULL, 0x3ff1d8f5528f6569ULL, 0x3ff1c52311577e7cULL, 0x3ff1b17c74cb26e9ULL
};
static const pw_u64v pw_log_invc_7 __attribute__((aligned(64))) = {
  0x3ff19e010c2c1ab6ULL, 0x3ff18ab07bb670bdULL, 0x3ff1778a25efbcb6ULL, 0x3ff1648d354c31daULL, 0x3ff151b990275fddULL, 0x3ff13f0ea432d24cULL, 0x3ff12c8b7210f9daULL, 0x3ff11a3028ecb531ULL
};
static const pw_u64v pw_log_invc_8 __attribute__((aligned(64))) = {
  0x3ff107fbda8434afULL, 0x3ff0f5ee0f4e6bb3ULL, 0x3ff0e4065d2a9fceULL, 0x3ff0d244632ca521ULL, 0x3ff0c0a77ce2981aULL, 0x3ff0af2f83c636d1ULL, 0x3ff09ddb98a01339ULL, 0x3ff08cabaf52e7dfULL
};
static const pw_u64v pw_log_invc_9 __attribute__((aligned(64))) = {
  0x3ff07b9f2f4e28fbULL, 0x3ff06ab58c358f19ULL, 0x3ff059eea5ecf92cULL, 0x3ff04949cdd12c90ULL, 0x3ff038c6c6f0ada9ULL, 0x3ff02865137932a9ULL, 0x3ff0182427ea7348ULL, 0x3ff008040614b195ULL
};
static const pw_u64v pw_log_invc_10 __attribute__((aligned(64))) = {
  0x3fefe01ff726fa1aULL, 0x3fefa11cc261ea74ULL, 0x3fef6310b081992eULL, 0x3fef25f63ceeadcdULL, 0x3feee9c8039113e7ULL, 0x3feeae8078cbb1abULL, 0x3fee741aa29d0c9bULL, 0x3fee3a91830a99b5ULL
};
static const pw_u64v pw_log_invc_11 __attribute__((aligned(64))) = {
  0x3fee01e009609a56ULL, 0x3fedca01e577bb98ULL, 0x3fed92f20b7c9103ULL, 0x3fed5cac66fb5cceULL, 0x3fed272caa5ede9dULL, 0x3fecf26e3e6b2ccdULL, 0x3fecbe6da2a77902ULL, 0x3fec8b266d37086dULL
};
static const pw_u64v pw_log_invc_12 __attribute__((aligned(64))) = {
  0x3fec5894bd5d5804ULL, 0x3fec26b533bb9f8cULL, 0x3febf583eeece73fULL, 0x3febc4fd75db96c1ULL, 0x3feb951e0c864a28ULL, 0x3feb65e2c5ef3e2cULL, 0x3feb374867c9888bULL, 0x3feb094b211d304aULL
};
static const pw_u64v pw_log_invc_13 __attribute__((aligned(64))) = {
  0x3feadbe885f2ef7eULL, 0x3feaaf1d31603da2ULL, 0x3fea82e63fd358a7ULL, 0x3fea5740ef09738bULL, 0x3fea2c2a90ab4b27ULL, 0x3fea01a01393f2d1ULL, 0x3fe9d79f24db3c1bULL, 0x3fe9ae2505c7b190ULL
};
static const pw_u64v pw_log_invc_14 __attribute__((aligned(64))) = {
  0x3fe9852ef297ce2fULL, 0x3fe95cbaeea44b75ULL, 0x3fe934c69de74838ULL, 0x3fe90d4f2f6752e6ULL, 0x3fe8e6528effd79dULL, 0x3fe8bfce9fcc007cULL, 0x3fe899c0dabec30eULL, 0x3fe87427aa2317fbULL
};
static const pw_u64v pw_log_invc_15 __attribute__((aligned(64))) = {
  0x3fe84f00acb39a08ULL, 0x3fe82a49e8653e55ULL, 0x3fe8060195f40260ULL, 0x3fe7e22563e0a329ULL, 0x3fe7beb377dcb5adULL, 0x3fe79baa679725c2ULL, 0x3fe77907f2170657ULL, 0x3fe756cadbd6130cULL
};
static const pw_u64v pw_log_logc_0 __attribute__((aligned(64))) = {
  0xbfd7cc7f79e69000ULL, 0xbfd76feec20d0000ULL, 0xbfd713e31351e000ULL, 0xbfd6b85b38287800ULL, 0xbfd65d5590807800ULL, 0xbfd602d076180000ULL, 0xbfd5a8ca86909000ULL, 0xbfd54f4356035000ULL
};
static const pw_u64v pw_log_logc_1 __attribute__((aligned(64))) = {
  0xbfd4f637c36b4000ULL, 0xbfd49da7fda85000ULL, 0xbfd445923989a800ULL, 0xbfd3edf439b0b800ULL, 0xbfd396ce448f7000ULL, 0xbfd3401e17bda000ULL, 0xbfd2e9e2ef468000ULL, 0xbfd2941b3830e000ULL
};
static const pw_u64v pw_log_logc_2 __attribute__((aligned(64))) = {
  0xbfd23ec58cda8800ULL, 0xbfd1e9e129279000ULL, 0xbfd1956d2b48f800ULL, 0xbfd141679ab9f800ULL, 0xbfd0edd094ef9800ULL, 0xbfd09aa518db1000ULL, 0xbfd047e65263b800ULL, 0xbfcfeb224586f000ULL
};
static const pw_u64v pw_log_logc_3 __attribute__((aligned(64))) = {
  0xbfcf474a7517b000ULL, 0xbfcea4443d103000ULL, 0xbfce020d44e9b000ULL, 0xbfcd60a22977f000ULL, 0xbfccc00104959000ULL, 0xbfcc202956891000ULL, 0xbfcb81178d811000ULL, 0xbfcae2c9ccd3d000ULL
};
static const pw_u64v pw_log_logc_4 __attribute__((aligned(64))) = {
  0xbfca45402e129000ULL, 0xbfc9a877681df000ULL, 0xbfc90c6d69483000ULL, 0xbfc87120a645c000ULL, 0xbfc7d68fb4143000ULL, 0xbfc73cb83c627000ULL, 0xbfc6a39a9b376000ULL, 0xbfc60b3154b7a000ULL
};
static const pw_u64v pw_log_logc_5 __attribute__((aligned(64))) = {
  0xbfc5737d76243000ULL, 0xbfc4dc7b8fc23000ULL, 0xbfc4462c51d20000ULL, 0xbfc3b08abc830000ULL, 0xbfc31b996b490000ULL, 0xbfc2875490a44000ULL, 0xbfc1f3b9f879a000ULL, 0xbfc160c8252ca000ULL
};
static const pw_u64v pw_log_logc_6 __attribute__((aligned(64))) = {
  0xbfc0ce7f57f72000ULL, 0xbfc03cdc49fea000ULL, 0xbfbf57bdbc4b8000ULL, 0xbfbe370896404000ULL, 0xbfbd17983ef94000ULL, 0xbfbbf9674ed8a000ULL, 0xbfbadc79202f6000ULL, 0xbfb9c0c3e7288000ULL
};
static const pw_u64v pw_log_logc_7 __attribute__((aligned(64))) = {
  0xbfb8a646b372c000ULL, 0xbfb78d01b3ac0000ULL, 0xbfb674f145380000ULL, 0xbfb55e0e6d878000ULL, 0xbfb4485cdea1e000ULL, 0xbfb333d94d6aa000ULL, 0xbfb22079f8c56000ULL, 0xbfb10e4698622000ULL
};
static const pw_u64v pw_log_logc_8 __attribute__((aligned(64))) = {
  0xbfaffa6c6ad20000ULL, 0xbfadda8d4a774000ULL, 0xbfabbcece4850000ULL, 0xbfa9a1894012c000ULL, 0xbfa788583302c000ULL, 0xbfa5715e67d68000ULL, 0xbfa35c8a49658000ULL, 0xbfa149e364154000ULL
};
static const pw_u64v pw_log_logc_9 __attribute__((aligned(64))) = {
  0xbf9e72c082eb8000ULL, 0xbf9a55f152528000ULL, 0xbf963d62cf818000ULL, 0xbf9228fb8caa0000ULL, 0xbf8c317b20f90000ULL, 0xbf8419355daa0000ULL, 0xbf781203c2ec0000ULL, 0xbf60040979240000ULL
};
static const pw_u64v pw_log_logc_10 __attribute__((aligned(64))) = {
  0x3f6feff384900000ULL, 0x3f87dc41353d0000ULL, 0x3f93cea3c4c28000ULL, 0x3f9b9fc114890000ULL, 0x3fa1b0d8ce110000ULL, 0x3fa58a5bd001c000ULL, 0x3fa95c8340d88000ULL, 0x3fad276aef578000ULL
};
static const pw_u64v pw_log_logc_11 __attribute__((aligned(64))) = {
  0x3fb07598e598c000ULL, 0x3fb253f5e30d2000ULL, 0x3fb42edd8b380000ULL, 0x3fb606598757c000ULL, 0x3fb7da76356a0000ULL, 0x3fb9ab434e1c6000ULL, 0x3fbb78c7bb0d6000ULL, 0x3fbd431332e72000ULL
};
static const pw_u64v pw_log_logc_12 __attribute__((aligned(64))) = {
  0x3fbf0a3171de6000ULL, 0x3fc067152b914000ULL, 0x3fc147858292b000ULL, 0x3fc2266ecdca3000ULL, 0x3fc303d7a6c55000ULL, 0x3fc3dfc33c331000ULL, 0x3fc4ba366b7a8000ULL, 0x3fc5933928d1f000ULL
};
static const pw_u64v pw_log_logc_13 __attribute__((aligned(64))) = {
  0x3fc66acd2418f000ULL, 0x3fc740f8ec669000ULL, 0x3fc815c0f51af000ULL, 0x3fc8e92954f68000ULL, 0x3fc9bb3602f84000ULL, 0x3fca8bed1c2c0000ULL, 0x3fcb5b515c01d000ULL, 0x3fcc2967ccbcc000ULL
};
static const pw_u64v pw_log_logc_14 __attribute__((aligned(64))) = {
  0x3fccf635d5486000ULL, 0x3fcdc1bd3446c000ULL, 0x3fce8c01b8cfe000ULL, 0x3fcf5509c0179000ULL, 0x3fd00e6c121fb800ULL, 0x3fd071b80e93d000ULL, 0x3fd0d46b9e867000ULL, 0x3fd13687334bd000ULL
};
static const pw_u64v pw_log_logc_15 __attribute__((aligned(64))) = {
  0x3fd1980d67234800ULL, 0x3fd1f8ffe0cc8000ULL, 0x3fd2595fd7636800ULL, 0x3fd2b9300914a800ULL, 0x3fd3187210436000ULL, 0x3fd377266dec1800ULL, 0x3fd3d54ffbaf3000ULL, 0x3fd432eee32fe000ULL
};
static const pw_u64v pw_log_chi_0 __attribute__((aligned(64))) = {
  0x3fe61000014fb66bULL, 0x3fe63000034db495ULL, 0x3fe650000d94d478ULL, 0x3fe67000074e6fadULL, 0x3fe68ffffedf0faeULL, 0x3fe6b0000763c5bcULL, 0x3fe6d0001e5cc1f6ULL, 0x3fe6efffeb05f63eULL
};
static const pw_u64v pw_log_chi_1 __attribute__((aligned(64))) = {
  0x3fe710000e869780ULL, 0x3fe72ffffc67e912ULL, 0x3fe74fffdf81116aULL, 0x3fe770000f679c90ULL, 0x3fe78ffffa7ec835ULL, 0x3fe7affffe20c2e6ULL, 0x3fe7cfffed3fc900ULL, 0x3fe7efffe9261a76ULL
};
static const pw_u64v pw_log_chi_2 __attribute__((aligned(64))) = {
  0x3fe81000049ca3e8ULL, 0x3fe8300017932c8fULL, 0x3fe850000633739cULL, 0x3fe87000204289c6ULL, 0x3fe88fffebf57904ULL, 0x3fe8b00022bc04dfULL, 0x3fe8cfffe50c1b8aULL, 0x3fe8effffc918e43ULL
};
static const pw_u64v pw_log_chi_3 __attribute__((aligned(64))) = {
  0x3fe910001efa5fc7ULL, 0x3fe9300013467bb9ULL, 0x3fe94fffe6ee076fULL, 0x3fe96fffde3c12d1ULL, 0x3fe98ffff4458a0dULL, 0x3fe9afffdd982e3eULL, 0x3fe9cfffed49fb66ULL, 0x3fe9f00020f19c51ULL
};
static const pw_u64v pw_log_chi_4 __attribute__((aligned(64))) = {
  0x3fea10001145b006ULL, 0x3fea300007bbf6faULL, 0x3fea500010971d79ULL, 0x3fea70001df52e48ULL, 0x3fea90001c593352ULL, 0x3feab0002a4f3e4bULL, 0x3feacfffd7ae1ed1ULL, 0x3feaefffee510478ULL
};
static const pw_u64v pw_log_chi_5 __attribute__((aligned(64))) = {
  0x3feb0fffdb650d5bULL, 0x3feb2ffffeaaca57ULL, 0x3feb4fffd995badcULL, 0x3feb7000249e659cULL, 0x3feb8ffff9871640ULL, 0x3febafffd204cb4fULL, 0x3febcfffd2415c45ULL, 0x3febeffff86309dfULL
};
static const pw_u64v pw_log_chi_6 __attribute__((aligned(64))) = {
  0x3fec0fffe1b57653ULL, 0x3fec2ffff1fa57e3ULL, 0x3fec4fffdcbfe424ULL, 0x3fec6fffed54b9f7ULL, 0x3fec8fffeb998fd5ULL, 0x3fecb0002125219aULL, 0x3feccfffdd94469cULL, 0x3fecefffeafdc476ULL
};
static const pw_u64v pw_log_chi_7 __attribute__((aligned(64))) = {
  0x3fed1000169af82bULL, 0x3fed30000d0ff71dULL, 0x3fed4fffea790fc4ULL, 0x3fed70002edc87e5ULL, 0x3fed900021dc82aaULL, 0x3fedafffd86b0283ULL, 0x3fedd000296c4739ULL, 0x3fedefffe54490f5ULL
};
static const pw_u64v pw_log_chi_8 __attribute__((aligned(64))) = {
  0x3fee0fffcdabf694ULL, 0x3fee2fffdb52c8ddULL, 0x3fee4ffff24216efULL, 0x3fee6fffe88a5e11ULL, 0x3fee9000119eff0dULL, 0x3feeafffdfa51744ULL, 0x3feed0001a127fa1ULL, 0x3feef00007babcc4ULL
};
static const pw_u64v pw_log_chi_9 __attribute__((aligned(64))) = {
  0x3fef0ffff57a8d02ULL, 0x3fef30001ee58ac7ULL, 0x3fef4ffff5823494ULL, 0x3fef6ffffca94c6bULL, 0x3fef8fffe1f9c441ULL, 0x3fefafffd2e0e37eULL, 0x3fefd0001c77e49eULL, 0x3fefeffff7e0c331ULL
};
static const pw_u64v pw_log_chi_10 __attribute__((aligned(64))) = {
  0x3ff00ffff465606eULL, 0x3ff02ffff3867a58ULL, 0x3ff04ffffdfc0d17ULL, 0x3ff0700003cd4d82ULL, 0x3ff08ffff9f2cbe8ULL, 0x3ff0b000010cda65ULL, 0x3ff0d00001a4d338ULL, 0x3ff0effffadafdfdULL
};
static const pw_u64v pw_log_chi_11 __attribute__((aligned(64))) = {
  0x3ff110000bbafd96ULL, 0x3ff12ffffae5f45dULL, 0x3ff150000dd59ad9ULL, 0x3ff170000f21559aULL, 0x3ff18ffffc275426ULL, 0x3ff1b000123d3c59ULL, 0x3ff1cffff8299eb7ULL, 0x3ff1effff48ad400ULL
};
static const pw_u64v pw_log_chi_12 __attribute__((aligned(64))) = {
  0x3ff210000c8b86a4ULL, 0x3ff2300003854303ULL, 0x3ff24fffffbcf684ULL, 0x3ff26ffff52921d9ULL, 0x3ff2900014933a3cULL, 0x3ff2b00014556313ULL, 0x3ff2cfffebfe523bULL, 0x3ff2f0000bb8ad96ULL
};
static const pw_u64v pw_log_chi_13 __attribute__((aligned(64))) = {
  0x3ff30ffffb7ae2afULL, 0x3ff32ffffeac5f7fULL, 0x3ff350000ca66756ULL, 0x3ff3700011fbf721ULL, 0x3ff38ffff9592fb9ULL, 0x3ff3b00004ddd242ULL, 0x3ff3cffff5b2c957ULL, 0x3ff3efffeab0b418ULL
};
static const pw_u64v pw_log_chi_14 __attribute__((aligned(64))) = {
  0x3ff410001532aff4ULL, 0x3ff4300017478b29ULL, 0x3ff44fffe795b463ULL, 0x3ff46fffe80475e0ULL, 0x3ff48fffef6fc1e7ULL, 0x3ff4afffe5bea704ULL, 0x3ff4d000171027deULL, 0x3ff4f0000ff03ee2ULL
};
static const pw_u64v pw_log_chi_15 __attribute__((aligned(64))) = {
  0x3ff5100012dc4bd1ULL, 0x3ff530001605277aULL, 0x3ff54fffecdb704cULL, 0x3ff56fffef5f54a9ULL, 0x3ff5900017e61012ULL, 0x3ff5b00003c93e92ULL, 0x3ff5d0001d4919bcULL, 0x3ff5efffe7b87a89ULL
};
static const pw_u64v pw_log_clo_0 __attribute__((aligned(64))) = {
  0x3c7e026c91425b3cULL, 0x3c8dbfea48005d41ULL, 0x3c8e7fa786d6a5b7ULL, 0x3c61fcea6b54254cULL, 0xbc7c7e274c590efdULL, 0xbc8ac16848dcda01ULL, 0x3c833f1c9d499311ULL, 0xbc7e80041ae22d53ULL
};
static const pw_u64v pw_log_clo_1 __attribute__((aligned(64))) = {
  0x3c7bff6671097952ULL, 0x3c8c00e226bd8724ULL, 0xbc6e02916ef101d2ULL, 0xbc67fc71cd549c74ULL, 0x3c81bec19ef50483ULL, 0xbc707e1729cc6465ULL, 0xbc808072087b8b1cULL, 0x3c8dc0286d9df9aeULL
};
static const pw_u64v pw_log_clo_2 __attribute__((aligned(64))) = {
  0x3c897fd251e54c33ULL, 0xbc8afee9b630f381ULL, 0x3c89bfbf6b6535bcULL, 0xbc8bbf65f3117b75ULL, 0xbc89006ea23dcb57ULL, 0xbc7d00df38e04b0aULL, 0xbc88007146ff9f05ULL, 0x3c83817bd07a7038ULL
};
static const pw_u64v pw_log_clo_3 __attribute__((aligned(64))) = {
  0x3c893e9176dfb403ULL, 0x3c7f804e4b980276ULL, 0xbc8f7ef0d9ff622eULL, 0xbc7082aa962638baULL, 0xbc87801b9164a8efULL, 0xbc8740e08a5a9337ULL, 0x3c3fce08c19be000ULL, 0xbc8a3faa27885b0aULL
};
static const pw_u64v pw_log_clo_4 __attribute__((aligned(64))) = {
  0x3c74ff489958da56ULL, 0x3c8cbeab8a2b6d18ULL, 0x3c88fecadd787930ULL, 0xbc8f41763dd8abdbULL, 0xbc8ebf0284c27612ULL, 0xbc69fd043cff3f5fULL, 0xbc823ee7129070b4ULL, 0x3c6a063ee00edea3ULL
};
static const pw_u64v pw_log_clo_5 __attribute__((aligned(64))) = {
  0x3c5a06c8381f0ab9ULL, 0xbc79011e74233c1dULL, 0xbc79ff1068862a9fULL, 0x3c8aff45d0864f3eULL, 0x3c7cfe7796c2c3f9ULL, 0xbc63ff27eef22bc4ULL, 0xbc6cffb7ee3bea21ULL, 0xbc814103972e0b5cULL
};
static const pw_u64v pw_log_clo_6 __attribute__((aligned(64))) = {
  0x3c8bc16494b76a19ULL, 0xbc64feef8d30c6edULL, 0xbc843f68bcec4775ULL, 0x3c847ea3f053e0ecULL, 0x3c7383068df992f1ULL, 0xbc68fd8e64180e04ULL, 0x3c8e7ebe1cc7ea72ULL, 0x3c8ebe39ad9f88feULL
};
static const pw_u64v pw_log_clo_7 __attribute__((aligned(64))) = {
  0x3c757d91a8b95a71ULL, 0x3c89c1906970c7daULL, 0xbc580e37c558fe0cULL, 0xbc7f80d64dc10f44ULL, 0xbc747c8f94fd5c5cULL, 0x3c8c7f1dc521617eULL, 0x3c88019eb2ffb153ULL, 0x3c6e00d2c652cc89ULL
};
static const pw_u64v pw_log_clo_8 __attribute__((aligned(64))) = {
  0xbc7f8340202d69d2ULL, 0x3c7b00c1ca1b0864ULL, 0x3c72ffa8b094ab51ULL, 0xbc57f673b1efbe59ULL, 0xbc84808d5e0bc801ULL, 0x3c780006d54320b5ULL, 0xbc5002f860565c92ULL, 0xbc8540445d35e611ULL
};
static const pw_u64v pw_log_clo_9 __attribute__((aligned(64))) = {
  0xbc4ffb3139ef9105ULL, 0x3c8a81acf2731155ULL, 0x3c8a3f41d4d7c743ULL, 0xbc6202f41c987875ULL, 0x3c777dd1f477e74bULL, 0xbc6f01199a7ca331ULL, 0x3c7181ee4bceacb1ULL, 0xbc6e05370170875aULL
};
static const pw_u64v pw_log_clo_10 __attribute__((aligned(64))) = {
  0xbc8a7ead491c0adaULL, 0xbc977f69c3fcb2e0ULL, 0x3c97bffe34cb945bULL, 0x3c820083c0e456cbULL, 0xbc6dffdfbe37751aULL, 0xbc913f7faee626ebULL, 0x3c807dfa79489ff7ULL, 0xbc77040570d66bc0ULL
};
static const pw_u64v pw_log_clo_11 __attribute__((aligned(64))) = {
  0x3c8e80d4846d0b62ULL, 0x3c9dbffa64fd36efULL, 0x3c9a0077701250aeULL, 0x3c8dfdf9e2e3deeeULL, 0x3c910030dc3b7273ULL, 0x3c997f7980030188ULL, 0xbc65f932ab9f8c67ULL, 0x3c937fbf9da75bebULL
};
static const pw_u64v pw_log_clo_12 __attribute__((aligned(64))) = {
  0x3c9f806b91fd5b22ULL, 0x3c93ffc2eb9fbf33ULL, 0x3c7601e77e2e2e72ULL, 0x3c7ffcbb767f0c61ULL, 0xbc7202ca3c02412bULL, 0xbc92808233f21f02ULL, 0xbc88ff7e384fdcf2ULL, 0xbc85ff51503041c5ULL
};
static const pw_u64v pw_log_clo_13 __attribute__((aligned(64))) = {
  0xbc810071885e289dULL, 0xbc91ff5d3fb7b715ULL, 0x3c957f82228b82bdULL, 0x3c8000bac40dd5ccULL, 0xbc943f9d2db2a751ULL, 0x3c857f6b707638e1ULL, 0x3c7a023a10bf1231ULL, 0x3c987f6d66b152b0ULL
};
static const pw_u64v pw_log_clo_14 __attribute__((aligned(64))) = {
  0x3c67f8375f198524ULL, 0x3c8301e672dc5143ULL, 0x3c89ff69b8b2895aULL, 0xbc95c0b19bc2f254ULL, 0x3c9b4009f23a2a72ULL, 0xbc94ffb7bf0d7d45ULL, 0xbc99c06471dc6a3dULL, 0x3c977f890b85531cULL
};
static const pw_u64v pw_log_clo_15 __attribute__((aligned(64))) = {
  0x3c6004657166a436ULL, 0xbc96bfcece233209ULL, 0xbc8902720505a1d7ULL, 0x3c9bbfe60ec96412ULL, 0x3c887ec581afef90ULL, 0xbc9f41080abf0cc0ULL, 0xbc98812afb254729ULL, 0xbc947eb780ed6904ULL
};

static __attribute__((always_inline)) inline void
pw_log_register_lookup(pw_u64v keys,pw_f64v *invc,pw_f64v *logc,pw_f64v *chi,pw_f64v *clo) {
  keys&=127ULL;
  const pw_u64v group=keys>>3;
  const v8di selector=(v8di)(keys&7ULL);
  pw_u64v invcs={0},logcs={0},chis={0},clos={0};
  {
    const pw_u64v keep=(pw_u64v)(group==0ULL);
    invcs|=__builtin_shuffle(pw_log_invc_0,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_0,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_0,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_0,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==1ULL);
    invcs|=__builtin_shuffle(pw_log_invc_1,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_1,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_1,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_1,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==2ULL);
    invcs|=__builtin_shuffle(pw_log_invc_2,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_2,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_2,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_2,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==3ULL);
    invcs|=__builtin_shuffle(pw_log_invc_3,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_3,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_3,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_3,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==4ULL);
    invcs|=__builtin_shuffle(pw_log_invc_4,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_4,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_4,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_4,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==5ULL);
    invcs|=__builtin_shuffle(pw_log_invc_5,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_5,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_5,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_5,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==6ULL);
    invcs|=__builtin_shuffle(pw_log_invc_6,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_6,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_6,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_6,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==7ULL);
    invcs|=__builtin_shuffle(pw_log_invc_7,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_7,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_7,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_7,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==8ULL);
    invcs|=__builtin_shuffle(pw_log_invc_8,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_8,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_8,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_8,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==9ULL);
    invcs|=__builtin_shuffle(pw_log_invc_9,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_9,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_9,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_9,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==10ULL);
    invcs|=__builtin_shuffle(pw_log_invc_10,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_10,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_10,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_10,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==11ULL);
    invcs|=__builtin_shuffle(pw_log_invc_11,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_11,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_11,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_11,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==12ULL);
    invcs|=__builtin_shuffle(pw_log_invc_12,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_12,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_12,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_12,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==13ULL);
    invcs|=__builtin_shuffle(pw_log_invc_13,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_13,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_13,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_13,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==14ULL);
    invcs|=__builtin_shuffle(pw_log_invc_14,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_14,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_14,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_14,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==15ULL);
    invcs|=__builtin_shuffle(pw_log_invc_15,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_15,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_15,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_15,selector)&keep;
  }
  memcpy(invc,&invcs,sizeof invcs);memcpy(logc,&logcs,sizeof logcs);
  memcpy(chi,&chis,sizeof chis);memcpy(clo,&clos,sizeof clos);
}

static __attribute__((noinline)) void pw_core_log(const uint64_t input[PW_LANES],uint64_t output[PW_LANES]) {
  uint64_t active[PW_LANES],norm_input[PW_LANES]={0};for(unsigned pw_lane=0;pw_lane<PW_LANES;++pw_lane)norm_input[pw_lane]=0x3ff0000000000000;
  uint64_t invalid_input[PW_LANES]={0,0,0,0},nearbits[PW_LANES],farbits[PW_LANES];
  unsigned valid=0,zeros=0,invalid=0,subnormal=0,infinity=0,far=0,ones=0;
  for(unsigned i=0;i<PW_LANES;++i) {
    const uint64_t bits=input[i],mag=bits&UINT64_C(0x7fffffffffffffff);
    active[i]=UINT64_C(0x3ff0000000000000);
    if(!mag)zeros|=1u<<i;
    else if(mag>UINT64_C(0x7ff0000000000000) || (bits>>63)) {invalid|=1u<<i;invalid_input[i]=bits;}
    else if(bits==UINT64_C(0x7ff0000000000000))infinity|=1u<<i;
    else {
      valid|=1u<<i;active[i]=bits;
      if(bits<UINT64_C(0x0010000000000000)){subnormal|=1u<<i;norm_input[i]=bits;}
      if(bits==UINT64_C(0x3ff0000000000000))ones|=1u<<i;
    }
  }
  if(subnormal) {
    pw_f64v n;memcpy(&n,norm_input,sizeof n);
    const pw_f64v scaled=n*0x1p52;uint64_t words[PW_LANES];memcpy(words,&scaled,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(subnormal&(1u<<i))active[i]=words[i]-(UINT64_C(52)<<52);
  }
  for(unsigned i=0;i<PW_LANES;++i) {
    const int near=(valid&(1u<<i)) && input[i]-UINT64_C(0x3fee000000000000)<UINT64_C(0x3ff1090000000000)-UINT64_C(0x3fee000000000000);
    nearbits[i]=near?input[i]:UINT64_C(0x3ff0000000000000);
    farbits[i]=active[i];if((valid&(1u<<i)) && !near)far|=1u<<i;
  }
  pw_f64v x;memcpy(&x,nearbits,sizeof x);
  pw_f64v r=x-1,r2=r*r,r3=r*r2;
  const double *B=__log_data.poly1;
  pw_f64v y=r3*(B[1]+r*B[2]+r2*B[3]+r3*(B[4]+r*B[5]+r2*B[6]+r3*(B[7]+r*B[8]+r2*B[9]+r3*B[10])));
  pw_f64v w=r*0x1p27;
  const pw_f64v rhi=r+w-w,rlo=r-rhi;
  w=rhi*rhi*B[0];pw_f64v hi=r+w,lo=r-hi+w;
  lo=lo+B[0]*rlo*(rhi+r);y=y+lo;y=y+hi;
  memcpy(output,&y,sizeof y);
  if(far) {
    /* Do not evaluate the table path on1 when it is discarded: its reduction
     * need not be exact and could spuriously raise inexact for log(1)/qNaN.
     * Inactive lanes duplicate a real far input, whose inexact is required. */
    unsigned donor=0;while(!(far&(1u<<donor)))++donor;
    for(unsigned i=0;i<PW_LANES;++i)if(!(far&(1u<<i)))farbits[i]=farbits[donor];
    pw_u64v ix;memcpy(&ix,farbits,sizeof ix);
    const pw_u64v tmp=ix-UINT64_C(0x3fe6000000000000),index=(tmp>>45)&127;
    pw_i64v stmp;memcpy(&stmp,&tmp,sizeof tmp);const pw_i64v k=stmp>>52;
    const pw_u64v iz=ix-(tmp&UINT64_C(0xfff0000000000000));
    pw_f64v z;memcpy(&z,&iz,sizeof z);
    pw_f64v invc,logc,chi,clo;
    pw_log_register_lookup(index,&invc,&logc,&chi,&clo);
    r=(z-chi-clo)*invc;
    /* k is the signed exponent in[-1075,1024]. Adding its two's-complement
     * representation to the bits of1.5*2^52 changes the double by exactly k
     * (all remain in the same binade, spacing1). The final subtraction is
     * exact under every RC, matching the original exact integer conversion.
     * All integer operations stay in64-bit lanes; no int32 pack/unpack. */
    pw_u64v ku;memcpy(&ku,&k,sizeof ku);
    const pw_u64v biased=ku+0x4338000000000000ULL;
    pw_f64v biased_fp;memcpy(&biased_fp,&biased,sizeof biased_fp);
    const pw_f64v kd=biased_fp-0x1.8p52;
    w=kd*__log_data.ln2hi+logc;hi=w+r;lo=w-hi+r+kd*__log_data.ln2lo;
    r2=r*r;const double *A=__log_data.poly;
    y=lo+r2*A[0]+r*r2*(A[1]+r*A[2]+r2*(A[3]+r*A[4]))+hi;
    uint64_t words[PW_LANES];memcpy(words,&y,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(far&(1u<<i))output[i]=words[i];
  }
  if(invalid) {
    /* Retain the original vector subtraction as an observable FP event:
     * signaling NaNs quiet with IE, and negative subnormals retain DE. */
    pw_f64v v;memcpy(&v,invalid_input,sizeof v);
    volatile pw_f64v subtraction_event=v-v;
    (void)subtraction_event;
    /* Exception output/control is deliberately scalar and observable.
     * Keep the finite path and its ordinary vector storage unchanged. */
    volatile unsigned domain_negative=0;
    volatile uint64_t *exception_output=output;
    for(unsigned i=0;i<PW_LANES;++i)if(invalid&(1u<<i)) {
      volatile uint64_t input_word=invalid_input[i];
      const uint64_t bits=input_word,mag=bits&UINT64_C(0x7fffffffffffffff);
      if(mag>UINT64_C(0x7ff0000000000000))
        exception_output[i]=bits|UINT64_C(0x0008000000000000);
      else {
        exception_output[i]=UINT64_C(0xfff8000000000000);
        domain_negative=1;
      }
    }
    if(domain_negative) {
      /* Volatile operands/result require a real scalar invalid event.
       * Its emission and sticky/control behavior require fresh qualification. */
      volatile float numerator=0.0f,denominator=0.0f;
      volatile float invalid_event=numerator/denominator;
      (void)invalid_event;
    }
  }
  if(zeros) {
    /* +/-0 return the same negative infinity; the scalar pole event supplies ZD. */
    volatile float negative_one=-1.0f,positive_zero=0.0f;
    volatile float pole_event=negative_one/positive_zero;
    (void)pole_event;
    volatile uint64_t *exception_output=output;
    for(unsigned i=0;i<PW_LANES;++i)if(zeros&(1u<<i))
      exception_output[i]=UINT64_C(0xfff0000000000000);
  }
  for(unsigned i=0;i<PW_LANES;++i){if(infinity&(1u<<i))output[i]=UINT64_C(0x7ff0000000000000);if(ones&(1u<<i))output[i]=0;}
}

/* Bit snapshots support exact input/output or merge/output aliasing only.
 * Every full64B input/merge buffer is readable, even when inactive. */
static int pw_apply_log(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES],int unsafe) {
  if(active&~PW_ALL)return 1;
  uint64_t saved[PW_LANES],pass[PW_LANES],neutral[PW_LANES],value[PW_LANES];
  memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!active && !unsafe){memcpy(output,pass,64);return 0;}
  /* Keep software predicates in the same64-bit lanes as the payload.
   * This is exact integer selection; no floating arithmetic or side effects. */
  const pw_u64v lane_bits={1ULL,2ULL,4ULL,8ULL,16ULL,32ULL,64ULL,128ULL};
  const pw_u64v requested=(pw_u64v){0}+(unsigned long long)active;
  const pw_u64v result_mask=(pw_u64v)((requested&lane_bits)!=0ULL);
  const pw_u64v evaluated=(pw_u64v){0}+(unsigned long long)(unsafe?PW_ALL:active);
  const pw_u64v evaluate_mask=(pw_u64v)((evaluated&lane_bits)!=0ULL);
  pw_u64v saved_bits,pass_bits;memcpy(&saved_bits,saved,sizeof saved_bits);memcpy(&pass_bits,pass,sizeof pass_bits);
  const pw_u64v neutral_bits=(saved_bits&evaluate_mask)|(((pw_u64v){0}+0x3ff0000000000000ULL)&~evaluate_mask);
  memcpy(neutral,&neutral_bits,sizeof neutral_bits);
  pw_core_log(neutral,value);
  pw_u64v computed;memcpy(&computed,value,sizeof computed);
  const pw_u64v selected=(computed&result_mask)|(pass_bits&~result_mask);
  memcpy(value,&selected,sizeof selected);
  memcpy(output,value,64);return 0;
}
int phi_host_log_register_e8(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES]) {
  return pw_apply_log(input,active,merge,output,0);
}
#ifdef PW_ENABLE_NEGATIVE_CONTROL
int phi_host_log_register_e8_unsafe_negative(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES]) {
  return pw_apply_log(input,active,merge,output,1);
}
#endif
