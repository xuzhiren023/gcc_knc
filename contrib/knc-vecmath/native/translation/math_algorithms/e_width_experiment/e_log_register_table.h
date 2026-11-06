/* Exact Arm optimized-routines v26.01 N128 log data, commit649ccc8411e7c4862965710f25c570d854a1483f.
 * Copyright(c)2018 Arm Limited. SPDX-License-Identifier: MIT OR Apache-2.0 WITH LLVM-exception
 * Fixed paired-DWORD shards only; no target qualification. */
#ifndef PW_LOG_REGISTER_TABLE_H
#define PW_LOG_REGISTER_TABLE_H
#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "DP8 log register tables require little-endian words"
#endif
typedef uint32_t pw_log_u32v __attribute__((vector_size(64)));
static const pw_log_u32v pw_log_invc_0 __attribute__((aligned(64))) = {
  UINT32_C(0xc3e0de9f), UINT32_C(0x3ff734f0), UINT32_C(0x6a2ce91f), UINT32_C(0x3ff71378), UINT32_C(0x08fab5a0), UINT32_C(0x3ff6f260), UINT32_C(0x1f138c7d), UINT32_C(0x3ff6d1a6), UINT32_C(0x0bc5b4d1), UINT32_C(0x3ff6b149), UINT32_C(0x332f0cba), UINT32_C(0x3ff69147), UINT32_C(0x18224223), UINT32_C(0x3ff6719f), UINT32_C(0x99a51ed9), UINT32_C(0x3ff6524f)
};
static const pw_log_u32v pw_log_invc_1 __attribute__((aligned(64))) = {
  UINT32_C(0xaa8f24c4), UINT32_C(0x3ff63356), UINT32_C(0x6b9ddc14), UINT32_C(0x3ff614b3), UINT32_C(0x52c65c4c), UINT32_C(0x3ff5f664), UINT32_C(0xb5912c4f), UINT32_C(0x3ff5d867), UINT32_C(0xcb5b90de), UINT32_C(0x3ff5babc), UINT32_C(0xf2d91a78), UINT32_C(0x3ff59d61), UINT32_C(0x12465687), UINT32_C(0x3ff58056), UINT32_C(0xcee76bd3), UINT32_C(0x3ff56397)
};
static const pw_log_u32v pw_log_invc_2 __attribute__((aligned(64))) = {
  UINT32_C(0xe2a77f93), UINT32_C(0x3ff54725), UINT32_C(0x42064583), UINT32_C(0x3ff52aff), UINT32_C(0xdbb2bddf), UINT32_C(0x3ff50f22), UINT32_C(0x4734ded7), UINT32_C(0x3ff4f38f), UINT32_C(0xcfde2840), UINT32_C(0x3ff4d843), UINT32_C(0xc078a3c8), UINT32_C(0x3ff4bd3e), UINT32_C(0xc3e0258a), UINT32_C(0x3ff4a27f), UINT32_C(0x24d48434), UINT32_C(0x3ff48805)
};
static const pw_log_u32v pw_log_invc_3 __attribute__((aligned(64))) = {
  UINT32_C(0x1b192d0b), UINT32_C(0x3ff46dce), UINT32_C(0xd3391854), UINT32_C(0x3ff453d9), UINT32_C(0x44b4845a), UINT32_C(0x3ff43a27), UINT32_C(0x4115f8fb), UINT32_C(0x3ff420b5), UINT32_C(0xda3ef4b1), UINT32_C(0x3ff40782), UINT32_C(0x5d57fe8f), UINT32_C(0x3ff3ee8f), UINT32_C(0xa00b4ce9), UINT32_C(0x3ff3d5d9), UINT32_C(0xc010c12b), UINT32_C(0x3ff3bd60)
};
static const pw_log_u32v pw_log_invc_4 __attribute__((aligned(64))) = {
  UINT32_C(0x2b75dab8), UINT32_C(0x3ff3a524), UINT32_C(0xcd9fd002), UINT32_C(0x3ff38d22), UINT32_C(0xc5847a1c), UINT32_C(0x3ff3755b), UINT32_C(0x49ad36e2), UINT32_C(0x3ff35dce), UINT32_C(0x984dd440), UINT32_C(0x3ff34679), UINT32_C(0xceffcb24), UINT32_C(0x3ff32f5c), UINT32_C(0x75a10d49), UINT32_C(0x3ff31877), UINT32_C(0x373e3990), UINT32_C(0x3ff301c8)
};
static const pw_log_u32v pw_log_invc_5 __attribute__((aligned(64))) = {
  UINT32_C(0xbb95f841), UINT32_C(0x3ff2eb4e), UINT32_C(0x0219a9d1), UINT32_C(0x3ff2d50a), UINT32_C(0xa8b7fd2a), UINT32_C(0x3ff2bef9), UINT32_C(0x7a0c1bab), UINT32_C(0x3ff2a91c), UINT32_C(0x6014b530), UINT32_C(0x3ff29372), UINT32_C(0x5757a1f5), UINT32_C(0x3ff27dfa), UINT32_C(0x9b1d3bbf), UINT32_C(0x3ff268b3), UINT32_C(0x838ff5bd), UINT32_C(0x3ff2539d)
};
static const pw_log_u32v pw_log_invc_6 __attribute__((aligned(64))) = {
  UINT32_C(0xaac9083b), UINT32_C(0x3ff23eb7), UINT32_C(0x2ba940b6), UINT32_C(0x3ff22a01), UINT32_C(0x96cc4132), UINT32_C(0x3ff21579), UINT32_C(0x1dd2fc9b), UINT32_C(0x3ff20120), UINT32_C(0x494d480b), UINT32_C(0x3ff1ecf4), UINT32_C(0x528f6569), UINT32_C(0x3ff1d8f5), UINT32_C(0x11577e7c), UINT32_C(0x3ff1c523), UINT32_C(0x74cb26e9), UINT32_C(0x3ff1b17c)
};
static const pw_log_u32v pw_log_invc_7 __attribute__((aligned(64))) = {
  UINT32_C(0x0c2c1ab6), UINT32_C(0x3ff19e01), UINT32_C(0x7bb670bd), UINT32_C(0x3ff18ab0), UINT32_C(0x25efbcb6), UINT32_C(0x3ff1778a), UINT32_C(0x354c31da), UINT32_C(0x3ff1648d), UINT32_C(0x90275fdd), UINT32_C(0x3ff151b9), UINT32_C(0xa432d24c), UINT32_C(0x3ff13f0e), UINT32_C(0x7210f9da), UINT32_C(0x3ff12c8b), UINT32_C(0x28ecb531), UINT32_C(0x3ff11a30)
};
static const pw_log_u32v pw_log_invc_8 __attribute__((aligned(64))) = {
  UINT32_C(0xda8434af), UINT32_C(0x3ff107fb), UINT32_C(0x0f4e6bb3), UINT32_C(0x3ff0f5ee), UINT32_C(0x5d2a9fce), UINT32_C(0x3ff0e406), UINT32_C(0x632ca521), UINT32_C(0x3ff0d244), UINT32_C(0x7ce2981a), UINT32_C(0x3ff0c0a7), UINT32_C(0x83c636d1), UINT32_C(0x3ff0af2f), UINT32_C(0x98a01339), UINT32_C(0x3ff09ddb), UINT32_C(0xaf52e7df), UINT32_C(0x3ff08cab)
};
static const pw_log_u32v pw_log_invc_9 __attribute__((aligned(64))) = {
  UINT32_C(0x2f4e28fb), UINT32_C(0x3ff07b9f), UINT32_C(0x8c358f19), UINT32_C(0x3ff06ab5), UINT32_C(0xa5ecf92c), UINT32_C(0x3ff059ee), UINT32_C(0xcdd12c90), UINT32_C(0x3ff04949), UINT32_C(0xc6f0ada9), UINT32_C(0x3ff038c6), UINT32_C(0x137932a9), UINT32_C(0x3ff02865), UINT32_C(0x27ea7348), UINT32_C(0x3ff01824), UINT32_C(0x0614b195), UINT32_C(0x3ff00804)
};
static const pw_log_u32v pw_log_invc_10 __attribute__((aligned(64))) = {
  UINT32_C(0xf726fa1a), UINT32_C(0x3fefe01f), UINT32_C(0xc261ea74), UINT32_C(0x3fefa11c), UINT32_C(0xb081992e), UINT32_C(0x3fef6310), UINT32_C(0x3ceeadcd), UINT32_C(0x3fef25f6), UINT32_C(0x039113e7), UINT32_C(0x3feee9c8), UINT32_C(0x78cbb1ab), UINT32_C(0x3feeae80), UINT32_C(0xa29d0c9b), UINT32_C(0x3fee741a), UINT32_C(0x830a99b5), UINT32_C(0x3fee3a91)
};
static const pw_log_u32v pw_log_invc_11 __attribute__((aligned(64))) = {
  UINT32_C(0x09609a56), UINT32_C(0x3fee01e0), UINT32_C(0xe577bb98), UINT32_C(0x3fedca01), UINT32_C(0x0b7c9103), UINT32_C(0x3fed92f2), UINT32_C(0x66fb5cce), UINT32_C(0x3fed5cac), UINT32_C(0xaa5ede9d), UINT32_C(0x3fed272c), UINT32_C(0x3e6b2ccd), UINT32_C(0x3fecf26e), UINT32_C(0xa2a77902), UINT32_C(0x3fecbe6d), UINT32_C(0x6d37086d), UINT32_C(0x3fec8b26)
};
static const pw_log_u32v pw_log_invc_12 __attribute__((aligned(64))) = {
  UINT32_C(0xbd5d5804), UINT32_C(0x3fec5894), UINT32_C(0x33bb9f8c), UINT32_C(0x3fec26b5), UINT32_C(0xeeece73f), UINT32_C(0x3febf583), UINT32_C(0x75db96c1), UINT32_C(0x3febc4fd), UINT32_C(0x0c864a28), UINT32_C(0x3feb951e), UINT32_C(0xc5ef3e2c), UINT32_C(0x3feb65e2), UINT32_C(0x67c9888b), UINT32_C(0x3feb3748), UINT32_C(0x211d304a), UINT32_C(0x3feb094b)
};
static const pw_log_u32v pw_log_invc_13 __attribute__((aligned(64))) = {
  UINT32_C(0x85f2ef7e), UINT32_C(0x3feadbe8), UINT32_C(0x31603da2), UINT32_C(0x3feaaf1d), UINT32_C(0x3fd358a7), UINT32_C(0x3fea82e6), UINT32_C(0xef09738b), UINT32_C(0x3fea5740), UINT32_C(0x90ab4b27), UINT32_C(0x3fea2c2a), UINT32_C(0x1393f2d1), UINT32_C(0x3fea01a0), UINT32_C(0x24db3c1b), UINT32_C(0x3fe9d79f), UINT32_C(0x05c7b190), UINT32_C(0x3fe9ae25)
};
static const pw_log_u32v pw_log_invc_14 __attribute__((aligned(64))) = {
  UINT32_C(0xf297ce2f), UINT32_C(0x3fe9852e), UINT32_C(0xeea44b75), UINT32_C(0x3fe95cba), UINT32_C(0x9de74838), UINT32_C(0x3fe934c6), UINT32_C(0x2f6752e6), UINT32_C(0x3fe90d4f), UINT32_C(0x8effd79d), UINT32_C(0x3fe8e652), UINT32_C(0x9fcc007c), UINT32_C(0x3fe8bfce), UINT32_C(0xdabec30e), UINT32_C(0x3fe899c0), UINT32_C(0xaa2317fb), UINT32_C(0x3fe87427)
};
static const pw_log_u32v pw_log_invc_15 __attribute__((aligned(64))) = {
  UINT32_C(0xacb39a08), UINT32_C(0x3fe84f00), UINT32_C(0xe8653e55), UINT32_C(0x3fe82a49), UINT32_C(0x95f40260), UINT32_C(0x3fe80601), UINT32_C(0x63e0a329), UINT32_C(0x3fe7e225), UINT32_C(0x77dcb5ad), UINT32_C(0x3fe7beb3), UINT32_C(0x679725c2), UINT32_C(0x3fe79baa), UINT32_C(0xf2170657), UINT32_C(0x3fe77907), UINT32_C(0xdbd6130c), UINT32_C(0x3fe756ca)
};
static const pw_log_u32v pw_log_logc_0 __attribute__((aligned(64))) = {
  UINT32_C(0x79e69000), UINT32_C(0xbfd7cc7f), UINT32_C(0xc20d0000), UINT32_C(0xbfd76fee), UINT32_C(0x1351e000), UINT32_C(0xbfd713e3), UINT32_C(0x38287800), UINT32_C(0xbfd6b85b), UINT32_C(0x90807800), UINT32_C(0xbfd65d55), UINT32_C(0x76180000), UINT32_C(0xbfd602d0), UINT32_C(0x86909000), UINT32_C(0xbfd5a8ca), UINT32_C(0x56035000), UINT32_C(0xbfd54f43)
};
static const pw_log_u32v pw_log_logc_1 __attribute__((aligned(64))) = {
  UINT32_C(0xc36b4000), UINT32_C(0xbfd4f637), UINT32_C(0xfda85000), UINT32_C(0xbfd49da7), UINT32_C(0x3989a800), UINT32_C(0xbfd44592), UINT32_C(0x39b0b800), UINT32_C(0xbfd3edf4), UINT32_C(0x448f7000), UINT32_C(0xbfd396ce), UINT32_C(0x17bda000), UINT32_C(0xbfd3401e), UINT32_C(0xef468000), UINT32_C(0xbfd2e9e2), UINT32_C(0x3830e000), UINT32_C(0xbfd2941b)
};
static const pw_log_u32v pw_log_logc_2 __attribute__((aligned(64))) = {
  UINT32_C(0x8cda8800), UINT32_C(0xbfd23ec5), UINT32_C(0x29279000), UINT32_C(0xbfd1e9e1), UINT32_C(0x2b48f800), UINT32_C(0xbfd1956d), UINT32_C(0x9ab9f800), UINT32_C(0xbfd14167), UINT32_C(0x94ef9800), UINT32_C(0xbfd0edd0), UINT32_C(0x18db1000), UINT32_C(0xbfd09aa5), UINT32_C(0x5263b800), UINT32_C(0xbfd047e6), UINT32_C(0x4586f000), UINT32_C(0xbfcfeb22)
};
static const pw_log_u32v pw_log_logc_3 __attribute__((aligned(64))) = {
  UINT32_C(0x7517b000), UINT32_C(0xbfcf474a), UINT32_C(0x3d103000), UINT32_C(0xbfcea444), UINT32_C(0x44e9b000), UINT32_C(0xbfce020d), UINT32_C(0x2977f000), UINT32_C(0xbfcd60a2), UINT32_C(0x04959000), UINT32_C(0xbfccc001), UINT32_C(0x56891000), UINT32_C(0xbfcc2029), UINT32_C(0x8d811000), UINT32_C(0xbfcb8117), UINT32_C(0xccd3d000), UINT32_C(0xbfcae2c9)
};
static const pw_log_u32v pw_log_logc_4 __attribute__((aligned(64))) = {
  UINT32_C(0x2e129000), UINT32_C(0xbfca4540), UINT32_C(0x681df000), UINT32_C(0xbfc9a877), UINT32_C(0x69483000), UINT32_C(0xbfc90c6d), UINT32_C(0xa645c000), UINT32_C(0xbfc87120), UINT32_C(0xb4143000), UINT32_C(0xbfc7d68f), UINT32_C(0x3c627000), UINT32_C(0xbfc73cb8), UINT32_C(0x9b376000), UINT32_C(0xbfc6a39a), UINT32_C(0x54b7a000), UINT32_C(0xbfc60b31)
};
static const pw_log_u32v pw_log_logc_5 __attribute__((aligned(64))) = {
  UINT32_C(0x76243000), UINT32_C(0xbfc5737d), UINT32_C(0x8fc23000), UINT32_C(0xbfc4dc7b), UINT32_C(0x51d20000), UINT32_C(0xbfc4462c), UINT32_C(0xbc830000), UINT32_C(0xbfc3b08a), UINT32_C(0x6b490000), UINT32_C(0xbfc31b99), UINT32_C(0x90a44000), UINT32_C(0xbfc28754), UINT32_C(0xf879a000), UINT32_C(0xbfc1f3b9), UINT32_C(0x252ca000), UINT32_C(0xbfc160c8)
};
static const pw_log_u32v pw_log_logc_6 __attribute__((aligned(64))) = {
  UINT32_C(0x57f72000), UINT32_C(0xbfc0ce7f), UINT32_C(0x49fea000), UINT32_C(0xbfc03cdc), UINT32_C(0xbc4b8000), UINT32_C(0xbfbf57bd), UINT32_C(0x96404000), UINT32_C(0xbfbe3708), UINT32_C(0x3ef94000), UINT32_C(0xbfbd1798), UINT32_C(0x4ed8a000), UINT32_C(0xbfbbf967), UINT32_C(0x202f6000), UINT32_C(0xbfbadc79), UINT32_C(0xe7288000), UINT32_C(0xbfb9c0c3)
};
static const pw_log_u32v pw_log_logc_7 __attribute__((aligned(64))) = {
  UINT32_C(0xb372c000), UINT32_C(0xbfb8a646), UINT32_C(0xb3ac0000), UINT32_C(0xbfb78d01), UINT32_C(0x45380000), UINT32_C(0xbfb674f1), UINT32_C(0x6d878000), UINT32_C(0xbfb55e0e), UINT32_C(0xdea1e000), UINT32_C(0xbfb4485c), UINT32_C(0x4d6aa000), UINT32_C(0xbfb333d9), UINT32_C(0xf8c56000), UINT32_C(0xbfb22079), UINT32_C(0x98622000), UINT32_C(0xbfb10e46)
};
static const pw_log_u32v pw_log_logc_8 __attribute__((aligned(64))) = {
  UINT32_C(0x6ad20000), UINT32_C(0xbfaffa6c), UINT32_C(0x4a774000), UINT32_C(0xbfadda8d), UINT32_C(0xe4850000), UINT32_C(0xbfabbcec), UINT32_C(0x4012c000), UINT32_C(0xbfa9a189), UINT32_C(0x3302c000), UINT32_C(0xbfa78858), UINT32_C(0x67d68000), UINT32_C(0xbfa5715e), UINT32_C(0x49658000), UINT32_C(0xbfa35c8a), UINT32_C(0x64154000), UINT32_C(0xbfa149e3)
};
static const pw_log_u32v pw_log_logc_9 __attribute__((aligned(64))) = {
  UINT32_C(0x82eb8000), UINT32_C(0xbf9e72c0), UINT32_C(0x52528000), UINT32_C(0xbf9a55f1), UINT32_C(0xcf818000), UINT32_C(0xbf963d62), UINT32_C(0x8caa0000), UINT32_C(0xbf9228fb), UINT32_C(0x20f90000), UINT32_C(0xbf8c317b), UINT32_C(0x5daa0000), UINT32_C(0xbf841935), UINT32_C(0xc2ec0000), UINT32_C(0xbf781203), UINT32_C(0x79240000), UINT32_C(0xbf600409)
};
static const pw_log_u32v pw_log_logc_10 __attribute__((aligned(64))) = {
  UINT32_C(0x84900000), UINT32_C(0x3f6feff3), UINT32_C(0x353d0000), UINT32_C(0x3f87dc41), UINT32_C(0xc4c28000), UINT32_C(0x3f93cea3), UINT32_C(0x14890000), UINT32_C(0x3f9b9fc1), UINT32_C(0xce110000), UINT32_C(0x3fa1b0d8), UINT32_C(0xd001c000), UINT32_C(0x3fa58a5b), UINT32_C(0x40d88000), UINT32_C(0x3fa95c83), UINT32_C(0xef578000), UINT32_C(0x3fad276a)
};
static const pw_log_u32v pw_log_logc_11 __attribute__((aligned(64))) = {
  UINT32_C(0xe598c000), UINT32_C(0x3fb07598), UINT32_C(0xe30d2000), UINT32_C(0x3fb253f5), UINT32_C(0x8b380000), UINT32_C(0x3fb42edd), UINT32_C(0x8757c000), UINT32_C(0x3fb60659), UINT32_C(0x356a0000), UINT32_C(0x3fb7da76), UINT32_C(0x4e1c6000), UINT32_C(0x3fb9ab43), UINT32_C(0xbb0d6000), UINT32_C(0x3fbb78c7), UINT32_C(0x32e72000), UINT32_C(0x3fbd4313)
};
static const pw_log_u32v pw_log_logc_12 __attribute__((aligned(64))) = {
  UINT32_C(0x71de6000), UINT32_C(0x3fbf0a31), UINT32_C(0x2b914000), UINT32_C(0x3fc06715), UINT32_C(0x8292b000), UINT32_C(0x3fc14785), UINT32_C(0xcdca3000), UINT32_C(0x3fc2266e), UINT32_C(0xa6c55000), UINT32_C(0x3fc303d7), UINT32_C(0x3c331000), UINT32_C(0x3fc3dfc3), UINT32_C(0x6b7a8000), UINT32_C(0x3fc4ba36), UINT32_C(0x28d1f000), UINT32_C(0x3fc59339)
};
static const pw_log_u32v pw_log_logc_13 __attribute__((aligned(64))) = {
  UINT32_C(0x2418f000), UINT32_C(0x3fc66acd), UINT32_C(0xec669000), UINT32_C(0x3fc740f8), UINT32_C(0xf51af000), UINT32_C(0x3fc815c0), UINT32_C(0x54f68000), UINT32_C(0x3fc8e929), UINT32_C(0x02f84000), UINT32_C(0x3fc9bb36), UINT32_C(0x1c2c0000), UINT32_C(0x3fca8bed), UINT32_C(0x5c01d000), UINT32_C(0x3fcb5b51), UINT32_C(0xccbcc000), UINT32_C(0x3fcc2967)
};
static const pw_log_u32v pw_log_logc_14 __attribute__((aligned(64))) = {
  UINT32_C(0xd5486000), UINT32_C(0x3fccf635), UINT32_C(0x3446c000), UINT32_C(0x3fcdc1bd), UINT32_C(0xb8cfe000), UINT32_C(0x3fce8c01), UINT32_C(0xc0179000), UINT32_C(0x3fcf5509), UINT32_C(0x121fb800), UINT32_C(0x3fd00e6c), UINT32_C(0x0e93d000), UINT32_C(0x3fd071b8), UINT32_C(0x9e867000), UINT32_C(0x3fd0d46b), UINT32_C(0x334bd000), UINT32_C(0x3fd13687)
};
static const pw_log_u32v pw_log_logc_15 __attribute__((aligned(64))) = {
  UINT32_C(0x67234800), UINT32_C(0x3fd1980d), UINT32_C(0xe0cc8000), UINT32_C(0x3fd1f8ff), UINT32_C(0xd7636800), UINT32_C(0x3fd2595f), UINT32_C(0x0914a800), UINT32_C(0x3fd2b930), UINT32_C(0x10436000), UINT32_C(0x3fd31872), UINT32_C(0x6dec1800), UINT32_C(0x3fd37726), UINT32_C(0xfbaf3000), UINT32_C(0x3fd3d54f), UINT32_C(0xe32fe000), UINT32_C(0x3fd432ee)
};
static const pw_log_u32v pw_log_chi_0 __attribute__((aligned(64))) = {
  UINT32_C(0x014fb66b), UINT32_C(0x3fe61000), UINT32_C(0x034db495), UINT32_C(0x3fe63000), UINT32_C(0x0d94d478), UINT32_C(0x3fe65000), UINT32_C(0x074e6fad), UINT32_C(0x3fe67000), UINT32_C(0xfedf0fae), UINT32_C(0x3fe68fff), UINT32_C(0x0763c5bc), UINT32_C(0x3fe6b000), UINT32_C(0x1e5cc1f6), UINT32_C(0x3fe6d000), UINT32_C(0xeb05f63e), UINT32_C(0x3fe6efff)
};
static const pw_log_u32v pw_log_chi_1 __attribute__((aligned(64))) = {
  UINT32_C(0x0e869780), UINT32_C(0x3fe71000), UINT32_C(0xfc67e912), UINT32_C(0x3fe72fff), UINT32_C(0xdf81116a), UINT32_C(0x3fe74fff), UINT32_C(0x0f679c90), UINT32_C(0x3fe77000), UINT32_C(0xfa7ec835), UINT32_C(0x3fe78fff), UINT32_C(0xfe20c2e6), UINT32_C(0x3fe7afff), UINT32_C(0xed3fc900), UINT32_C(0x3fe7cfff), UINT32_C(0xe9261a76), UINT32_C(0x3fe7efff)
};
static const pw_log_u32v pw_log_chi_2 __attribute__((aligned(64))) = {
  UINT32_C(0x049ca3e8), UINT32_C(0x3fe81000), UINT32_C(0x17932c8f), UINT32_C(0x3fe83000), UINT32_C(0x0633739c), UINT32_C(0x3fe85000), UINT32_C(0x204289c6), UINT32_C(0x3fe87000), UINT32_C(0xebf57904), UINT32_C(0x3fe88fff), UINT32_C(0x22bc04df), UINT32_C(0x3fe8b000), UINT32_C(0xe50c1b8a), UINT32_C(0x3fe8cfff), UINT32_C(0xfc918e43), UINT32_C(0x3fe8efff)
};
static const pw_log_u32v pw_log_chi_3 __attribute__((aligned(64))) = {
  UINT32_C(0x1efa5fc7), UINT32_C(0x3fe91000), UINT32_C(0x13467bb9), UINT32_C(0x3fe93000), UINT32_C(0xe6ee076f), UINT32_C(0x3fe94fff), UINT32_C(0xde3c12d1), UINT32_C(0x3fe96fff), UINT32_C(0xf4458a0d), UINT32_C(0x3fe98fff), UINT32_C(0xdd982e3e), UINT32_C(0x3fe9afff), UINT32_C(0xed49fb66), UINT32_C(0x3fe9cfff), UINT32_C(0x20f19c51), UINT32_C(0x3fe9f000)
};
static const pw_log_u32v pw_log_chi_4 __attribute__((aligned(64))) = {
  UINT32_C(0x1145b006), UINT32_C(0x3fea1000), UINT32_C(0x07bbf6fa), UINT32_C(0x3fea3000), UINT32_C(0x10971d79), UINT32_C(0x3fea5000), UINT32_C(0x1df52e48), UINT32_C(0x3fea7000), UINT32_C(0x1c593352), UINT32_C(0x3fea9000), UINT32_C(0x2a4f3e4b), UINT32_C(0x3feab000), UINT32_C(0xd7ae1ed1), UINT32_C(0x3feacfff), UINT32_C(0xee510478), UINT32_C(0x3feaefff)
};
static const pw_log_u32v pw_log_chi_5 __attribute__((aligned(64))) = {
  UINT32_C(0xdb650d5b), UINT32_C(0x3feb0fff), UINT32_C(0xfeaaca57), UINT32_C(0x3feb2fff), UINT32_C(0xd995badc), UINT32_C(0x3feb4fff), UINT32_C(0x249e659c), UINT32_C(0x3feb7000), UINT32_C(0xf9871640), UINT32_C(0x3feb8fff), UINT32_C(0xd204cb4f), UINT32_C(0x3febafff), UINT32_C(0xd2415c45), UINT32_C(0x3febcfff), UINT32_C(0xf86309df), UINT32_C(0x3febefff)
};
static const pw_log_u32v pw_log_chi_6 __attribute__((aligned(64))) = {
  UINT32_C(0xe1b57653), UINT32_C(0x3fec0fff), UINT32_C(0xf1fa57e3), UINT32_C(0x3fec2fff), UINT32_C(0xdcbfe424), UINT32_C(0x3fec4fff), UINT32_C(0xed54b9f7), UINT32_C(0x3fec6fff), UINT32_C(0xeb998fd5), UINT32_C(0x3fec8fff), UINT32_C(0x2125219a), UINT32_C(0x3fecb000), UINT32_C(0xdd94469c), UINT32_C(0x3feccfff), UINT32_C(0xeafdc476), UINT32_C(0x3fecefff)
};
static const pw_log_u32v pw_log_chi_7 __attribute__((aligned(64))) = {
  UINT32_C(0x169af82b), UINT32_C(0x3fed1000), UINT32_C(0x0d0ff71d), UINT32_C(0x3fed3000), UINT32_C(0xea790fc4), UINT32_C(0x3fed4fff), UINT32_C(0x2edc87e5), UINT32_C(0x3fed7000), UINT32_C(0x21dc82aa), UINT32_C(0x3fed9000), UINT32_C(0xd86b0283), UINT32_C(0x3fedafff), UINT32_C(0x296c4739), UINT32_C(0x3fedd000), UINT32_C(0xe54490f5), UINT32_C(0x3fedefff)
};
static const pw_log_u32v pw_log_chi_8 __attribute__((aligned(64))) = {
  UINT32_C(0xcdabf694), UINT32_C(0x3fee0fff), UINT32_C(0xdb52c8dd), UINT32_C(0x3fee2fff), UINT32_C(0xf24216ef), UINT32_C(0x3fee4fff), UINT32_C(0xe88a5e11), UINT32_C(0x3fee6fff), UINT32_C(0x119eff0d), UINT32_C(0x3fee9000), UINT32_C(0xdfa51744), UINT32_C(0x3feeafff), UINT32_C(0x1a127fa1), UINT32_C(0x3feed000), UINT32_C(0x07babcc4), UINT32_C(0x3feef000)
};
static const pw_log_u32v pw_log_chi_9 __attribute__((aligned(64))) = {
  UINT32_C(0xf57a8d02), UINT32_C(0x3fef0fff), UINT32_C(0x1ee58ac7), UINT32_C(0x3fef3000), UINT32_C(0xf5823494), UINT32_C(0x3fef4fff), UINT32_C(0xfca94c6b), UINT32_C(0x3fef6fff), UINT32_C(0xe1f9c441), UINT32_C(0x3fef8fff), UINT32_C(0xd2e0e37e), UINT32_C(0x3fefafff), UINT32_C(0x1c77e49e), UINT32_C(0x3fefd000), UINT32_C(0xf7e0c331), UINT32_C(0x3fefefff)
};
static const pw_log_u32v pw_log_chi_10 __attribute__((aligned(64))) = {
  UINT32_C(0xf465606e), UINT32_C(0x3ff00fff), UINT32_C(0xf3867a58), UINT32_C(0x3ff02fff), UINT32_C(0xfdfc0d17), UINT32_C(0x3ff04fff), UINT32_C(0x03cd4d82), UINT32_C(0x3ff07000), UINT32_C(0xf9f2cbe8), UINT32_C(0x3ff08fff), UINT32_C(0x010cda65), UINT32_C(0x3ff0b000), UINT32_C(0x01a4d338), UINT32_C(0x3ff0d000), UINT32_C(0xfadafdfd), UINT32_C(0x3ff0efff)
};
static const pw_log_u32v pw_log_chi_11 __attribute__((aligned(64))) = {
  UINT32_C(0x0bbafd96), UINT32_C(0x3ff11000), UINT32_C(0xfae5f45d), UINT32_C(0x3ff12fff), UINT32_C(0x0dd59ad9), UINT32_C(0x3ff15000), UINT32_C(0x0f21559a), UINT32_C(0x3ff17000), UINT32_C(0xfc275426), UINT32_C(0x3ff18fff), UINT32_C(0x123d3c59), UINT32_C(0x3ff1b000), UINT32_C(0xf8299eb7), UINT32_C(0x3ff1cfff), UINT32_C(0xf48ad400), UINT32_C(0x3ff1efff)
};
static const pw_log_u32v pw_log_chi_12 __attribute__((aligned(64))) = {
  UINT32_C(0x0c8b86a4), UINT32_C(0x3ff21000), UINT32_C(0x03854303), UINT32_C(0x3ff23000), UINT32_C(0xffbcf684), UINT32_C(0x3ff24fff), UINT32_C(0xf52921d9), UINT32_C(0x3ff26fff), UINT32_C(0x14933a3c), UINT32_C(0x3ff29000), UINT32_C(0x14556313), UINT32_C(0x3ff2b000), UINT32_C(0xebfe523b), UINT32_C(0x3ff2cfff), UINT32_C(0x0bb8ad96), UINT32_C(0x3ff2f000)
};
static const pw_log_u32v pw_log_chi_13 __attribute__((aligned(64))) = {
  UINT32_C(0xfb7ae2af), UINT32_C(0x3ff30fff), UINT32_C(0xfeac5f7f), UINT32_C(0x3ff32fff), UINT32_C(0x0ca66756), UINT32_C(0x3ff35000), UINT32_C(0x11fbf721), UINT32_C(0x3ff37000), UINT32_C(0xf9592fb9), UINT32_C(0x3ff38fff), UINT32_C(0x04ddd242), UINT32_C(0x3ff3b000), UINT32_C(0xf5b2c957), UINT32_C(0x3ff3cfff), UINT32_C(0xeab0b418), UINT32_C(0x3ff3efff)
};
static const pw_log_u32v pw_log_chi_14 __attribute__((aligned(64))) = {
  UINT32_C(0x1532aff4), UINT32_C(0x3ff41000), UINT32_C(0x17478b29), UINT32_C(0x3ff43000), UINT32_C(0xe795b463), UINT32_C(0x3ff44fff), UINT32_C(0xe80475e0), UINT32_C(0x3ff46fff), UINT32_C(0xef6fc1e7), UINT32_C(0x3ff48fff), UINT32_C(0xe5bea704), UINT32_C(0x3ff4afff), UINT32_C(0x171027de), UINT32_C(0x3ff4d000), UINT32_C(0x0ff03ee2), UINT32_C(0x3ff4f000)
};
static const pw_log_u32v pw_log_chi_15 __attribute__((aligned(64))) = {
  UINT32_C(0x12dc4bd1), UINT32_C(0x3ff51000), UINT32_C(0x1605277a), UINT32_C(0x3ff53000), UINT32_C(0xecdb704c), UINT32_C(0x3ff54fff), UINT32_C(0xef5f54a9), UINT32_C(0x3ff56fff), UINT32_C(0x17e61012), UINT32_C(0x3ff59000), UINT32_C(0x03c93e92), UINT32_C(0x3ff5b000), UINT32_C(0x1d4919bc), UINT32_C(0x3ff5d000), UINT32_C(0xe7b87a89), UINT32_C(0x3ff5efff)
};
static const pw_log_u32v pw_log_clo_0 __attribute__((aligned(64))) = {
  UINT32_C(0x91425b3c), UINT32_C(0x3c7e026c), UINT32_C(0x48005d41), UINT32_C(0x3c8dbfea), UINT32_C(0x86d6a5b7), UINT32_C(0x3c8e7fa7), UINT32_C(0x6b54254c), UINT32_C(0x3c61fcea), UINT32_C(0x4c590efd), UINT32_C(0xbc7c7e27), UINT32_C(0x48dcda01), UINT32_C(0xbc8ac168), UINT32_C(0x9d499311), UINT32_C(0x3c833f1c), UINT32_C(0x1ae22d53), UINT32_C(0xbc7e8004)
};
static const pw_log_u32v pw_log_clo_1 __attribute__((aligned(64))) = {
  UINT32_C(0x71097952), UINT32_C(0x3c7bff66), UINT32_C(0x26bd8724), UINT32_C(0x3c8c00e2), UINT32_C(0x6ef101d2), UINT32_C(0xbc6e0291), UINT32_C(0xcd549c74), UINT32_C(0xbc67fc71), UINT32_C(0x9ef50483), UINT32_C(0x3c81bec1), UINT32_C(0x29cc6465), UINT32_C(0xbc707e17), UINT32_C(0x087b8b1c), UINT32_C(0xbc808072), UINT32_C(0x6d9df9ae), UINT32_C(0x3c8dc028)
};
static const pw_log_u32v pw_log_clo_2 __attribute__((aligned(64))) = {
  UINT32_C(0x51e54c33), UINT32_C(0x3c897fd2), UINT32_C(0xb630f381), UINT32_C(0xbc8afee9), UINT32_C(0x6b6535bc), UINT32_C(0x3c89bfbf), UINT32_C(0xf3117b75), UINT32_C(0xbc8bbf65), UINT32_C(0xa23dcb57), UINT32_C(0xbc89006e), UINT32_C(0x38e04b0a), UINT32_C(0xbc7d00df), UINT32_C(0x46ff9f05), UINT32_C(0xbc880071), UINT32_C(0xd07a7038), UINT32_C(0x3c83817b)
};
static const pw_log_u32v pw_log_clo_3 __attribute__((aligned(64))) = {
  UINT32_C(0x76dfb403), UINT32_C(0x3c893e91), UINT32_C(0x4b980276), UINT32_C(0x3c7f804e), UINT32_C(0xd9ff622e), UINT32_C(0xbc8f7ef0), UINT32_C(0x962638ba), UINT32_C(0xbc7082aa), UINT32_C(0x9164a8ef), UINT32_C(0xbc87801b), UINT32_C(0x8a5a9337), UINT32_C(0xbc8740e0), UINT32_C(0xc19be000), UINT32_C(0x3c3fce08), UINT32_C(0x27885b0a), UINT32_C(0xbc8a3faa)
};
static const pw_log_u32v pw_log_clo_4 __attribute__((aligned(64))) = {
  UINT32_C(0x9958da56), UINT32_C(0x3c74ff48), UINT32_C(0x8a2b6d18), UINT32_C(0x3c8cbeab), UINT32_C(0xdd787930), UINT32_C(0x3c88feca), UINT32_C(0x3dd8abdb), UINT32_C(0xbc8f4176), UINT32_C(0x84c27612), UINT32_C(0xbc8ebf02), UINT32_C(0x3cff3f5f), UINT32_C(0xbc69fd04), UINT32_C(0x129070b4), UINT32_C(0xbc823ee7), UINT32_C(0xe00edea3), UINT32_C(0x3c6a063e)
};
static const pw_log_u32v pw_log_clo_5 __attribute__((aligned(64))) = {
  UINT32_C(0x381f0ab9), UINT32_C(0x3c5a06c8), UINT32_C(0x74233c1d), UINT32_C(0xbc79011e), UINT32_C(0x68862a9f), UINT32_C(0xbc79ff10), UINT32_C(0xd0864f3e), UINT32_C(0x3c8aff45), UINT32_C(0x96c2c3f9), UINT32_C(0x3c7cfe77), UINT32_C(0xeef22bc4), UINT32_C(0xbc63ff27), UINT32_C(0xee3bea21), UINT32_C(0xbc6cffb7), UINT32_C(0x972e0b5c), UINT32_C(0xbc814103)
};
static const pw_log_u32v pw_log_clo_6 __attribute__((aligned(64))) = {
  UINT32_C(0x94b76a19), UINT32_C(0x3c8bc164), UINT32_C(0x8d30c6ed), UINT32_C(0xbc64feef), UINT32_C(0xbcec4775), UINT32_C(0xbc843f68), UINT32_C(0xf053e0ec), UINT32_C(0x3c847ea3), UINT32_C(0x8df992f1), UINT32_C(0x3c738306), UINT32_C(0x64180e04), UINT32_C(0xbc68fd8e), UINT32_C(0x1cc7ea72), UINT32_C(0x3c8e7ebe), UINT32_C(0xad9f88fe), UINT32_C(0x3c8ebe39)
};
static const pw_log_u32v pw_log_clo_7 __attribute__((aligned(64))) = {
  UINT32_C(0xa8b95a71), UINT32_C(0x3c757d91), UINT32_C(0x6970c7da), UINT32_C(0x3c89c190), UINT32_C(0xc558fe0c), UINT32_C(0xbc580e37), UINT32_C(0x4dc10f44), UINT32_C(0xbc7f80d6), UINT32_C(0x94fd5c5c), UINT32_C(0xbc747c8f), UINT32_C(0xc521617e), UINT32_C(0x3c8c7f1d), UINT32_C(0xb2ffb153), UINT32_C(0x3c88019e), UINT32_C(0xc652cc89), UINT32_C(0x3c6e00d2)
};
static const pw_log_u32v pw_log_clo_8 __attribute__((aligned(64))) = {
  UINT32_C(0x202d69d2), UINT32_C(0xbc7f8340), UINT32_C(0xca1b0864), UINT32_C(0x3c7b00c1), UINT32_C(0xb094ab51), UINT32_C(0x3c72ffa8), UINT32_C(0xb1efbe59), UINT32_C(0xbc57f673), UINT32_C(0x5e0bc801), UINT32_C(0xbc84808d), UINT32_C(0xd54320b5), UINT32_C(0x3c780006), UINT32_C(0x60565c92), UINT32_C(0xbc5002f8), UINT32_C(0x5d35e611), UINT32_C(0xbc854044)
};
static const pw_log_u32v pw_log_clo_9 __attribute__((aligned(64))) = {
  UINT32_C(0x39ef9105), UINT32_C(0xbc4ffb31), UINT32_C(0xf2731155), UINT32_C(0x3c8a81ac), UINT32_C(0xd4d7c743), UINT32_C(0x3c8a3f41), UINT32_C(0x1c987875), UINT32_C(0xbc6202f4), UINT32_C(0xf477e74b), UINT32_C(0x3c777dd1), UINT32_C(0x9a7ca331), UINT32_C(0xbc6f0119), UINT32_C(0x4bceacb1), UINT32_C(0x3c7181ee), UINT32_C(0x0170875a), UINT32_C(0xbc6e0537)
};
static const pw_log_u32v pw_log_clo_10 __attribute__((aligned(64))) = {
  UINT32_C(0x491c0ada), UINT32_C(0xbc8a7ead), UINT32_C(0xc3fcb2e0), UINT32_C(0xbc977f69), UINT32_C(0x34cb945b), UINT32_C(0x3c97bffe), UINT32_C(0xc0e456cb), UINT32_C(0x3c820083), UINT32_C(0xbe37751a), UINT32_C(0xbc6dffdf), UINT32_C(0xaee626eb), UINT32_C(0xbc913f7f), UINT32_C(0x79489ff7), UINT32_C(0x3c807dfa), UINT32_C(0x70d66bc0), UINT32_C(0xbc770405)
};
static const pw_log_u32v pw_log_clo_11 __attribute__((aligned(64))) = {
  UINT32_C(0x846d0b62), UINT32_C(0x3c8e80d4), UINT32_C(0x64fd36ef), UINT32_C(0x3c9dbffa), UINT32_C(0x701250ae), UINT32_C(0x3c9a0077), UINT32_C(0xe2e3deee), UINT32_C(0x3c8dfdf9), UINT32_C(0xdc3b7273), UINT32_C(0x3c910030), UINT32_C(0x80030188), UINT32_C(0x3c997f79), UINT32_C(0xab9f8c67), UINT32_C(0xbc65f932), UINT32_C(0x9da75beb), UINT32_C(0x3c937fbf)
};
static const pw_log_u32v pw_log_clo_12 __attribute__((aligned(64))) = {
  UINT32_C(0x91fd5b22), UINT32_C(0x3c9f806b), UINT32_C(0xeb9fbf33), UINT32_C(0x3c93ffc2), UINT32_C(0x7e2e2e72), UINT32_C(0x3c7601e7), UINT32_C(0x767f0c61), UINT32_C(0x3c7ffcbb), UINT32_C(0x3c02412b), UINT32_C(0xbc7202ca), UINT32_C(0x33f21f02), UINT32_C(0xbc928082), UINT32_C(0x384fdcf2), UINT32_C(0xbc88ff7e), UINT32_C(0x503041c5), UINT32_C(0xbc85ff51)
};
static const pw_log_u32v pw_log_clo_13 __attribute__((aligned(64))) = {
  UINT32_C(0x885e289d), UINT32_C(0xbc810071), UINT32_C(0x3fb7b715), UINT32_C(0xbc91ff5d), UINT32_C(0x228b82bd), UINT32_C(0x3c957f82), UINT32_C(0xc40dd5cc), UINT32_C(0x3c8000ba), UINT32_C(0x2db2a751), UINT32_C(0xbc943f9d), UINT32_C(0x707638e1), UINT32_C(0x3c857f6b), UINT32_C(0x10bf1231), UINT32_C(0x3c7a023a), UINT32_C(0x66b152b0), UINT32_C(0x3c987f6d)
};
static const pw_log_u32v pw_log_clo_14 __attribute__((aligned(64))) = {
  UINT32_C(0x5f198524), UINT32_C(0x3c67f837), UINT32_C(0x72dc5143), UINT32_C(0x3c8301e6), UINT32_C(0xb8b2895a), UINT32_C(0x3c89ff69), UINT32_C(0x9bc2f254), UINT32_C(0xbc95c0b1), UINT32_C(0xf23a2a72), UINT32_C(0x3c9b4009), UINT32_C(0xbf0d7d45), UINT32_C(0xbc94ffb7), UINT32_C(0x71dc6a3d), UINT32_C(0xbc99c064), UINT32_C(0x0b85531c), UINT32_C(0x3c977f89)
};
static const pw_log_u32v pw_log_clo_15 __attribute__((aligned(64))) = {
  UINT32_C(0x7166a436), UINT32_C(0x3c600465), UINT32_C(0xce233209), UINT32_C(0xbc96bfce), UINT32_C(0x0505a1d7), UINT32_C(0xbc890272), UINT32_C(0x0ec96412), UINT32_C(0x3c9bbfe6), UINT32_C(0x81afef90), UINT32_C(0x3c887ec5), UINT32_C(0x0abf0cc0), UINT32_C(0xbc9f4108), UINT32_C(0xfb254729), UINT32_C(0xbc98812a), UINT32_C(0x80ed6904), UINT32_C(0xbc947eb7)
};
static __attribute__((always_inline)) inline void
pw_log_register_lookup(pw_u64v keys,pw_f64v *invc,pw_f64v *logc,pw_f64v *chi,pw_f64v *clo) {
  keys&=127;
  const pw_u64v paired=keys|(keys<<32);
  pw_log_u32v key;memcpy(&key,&paired,sizeof key);
  const pw_log_u32v selector=((key&7)<<1)+(pw_log_u32v){0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1};
  const pw_log_u32v group=key>>3;
  pw_log_u32v invcs={0},logcs={0},chis={0},clos={0};
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==0);
    invcs|=__builtin_shuffle(pw_log_invc_0,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_0,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_0,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_0,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==1);
    invcs|=__builtin_shuffle(pw_log_invc_1,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_1,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_1,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_1,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==2);
    invcs|=__builtin_shuffle(pw_log_invc_2,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_2,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_2,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_2,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==3);
    invcs|=__builtin_shuffle(pw_log_invc_3,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_3,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_3,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_3,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==4);
    invcs|=__builtin_shuffle(pw_log_invc_4,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_4,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_4,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_4,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==5);
    invcs|=__builtin_shuffle(pw_log_invc_5,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_5,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_5,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_5,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==6);
    invcs|=__builtin_shuffle(pw_log_invc_6,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_6,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_6,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_6,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==7);
    invcs|=__builtin_shuffle(pw_log_invc_7,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_7,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_7,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_7,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==8);
    invcs|=__builtin_shuffle(pw_log_invc_8,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_8,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_8,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_8,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==9);
    invcs|=__builtin_shuffle(pw_log_invc_9,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_9,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_9,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_9,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==10);
    invcs|=__builtin_shuffle(pw_log_invc_10,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_10,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_10,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_10,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==11);
    invcs|=__builtin_shuffle(pw_log_invc_11,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_11,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_11,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_11,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==12);
    invcs|=__builtin_shuffle(pw_log_invc_12,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_12,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_12,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_12,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==13);
    invcs|=__builtin_shuffle(pw_log_invc_13,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_13,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_13,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_13,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==14);
    invcs|=__builtin_shuffle(pw_log_invc_14,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_14,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_14,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_14,selector)&keep;
  }
  {
    const pw_log_u32v keep=(pw_log_u32v)(group==15);
    invcs|=__builtin_shuffle(pw_log_invc_15,selector)&keep;
    logcs|=__builtin_shuffle(pw_log_logc_15,selector)&keep;
    chis|=__builtin_shuffle(pw_log_chi_15,selector)&keep;
    clos|=__builtin_shuffle(pw_log_clo_15,selector)&keep;
  }
  memcpy(invc,&invcs,sizeof invcs);
  memcpy(logc,&logcs,sizeof logcs);
  memcpy(chi,&chis,sizeof chis);
  memcpy(clo,&clos,sizeof clos);
}
#endif
