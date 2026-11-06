/* Exact N128 tail/scale words from Arm optimized-routines v26.01.
 * Copyright (c) 2018-2023, Arm Limited. SPDX-License-Identifier: MIT
 * Commit649ccc8411e7c4862965710f25c570d854a1483f.
 * Original exp_data.c SHA256 a5e84677e7693c7d22195f86faac5fdc6f92bff7ea2e54c0e7888203a78ffc24.
 * Each vector is eight uint64 entries stored low-dword,high-dword.
 * Source-only table selection; no native qualification. */
#ifndef PW_EXP_REGISTER_TABLE_H
#define PW_EXP_REGISTER_TABLE_H
#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "DP8 exp paired word-half table requires little-endian x86"
#endif
typedef uint32_t pw_exp_u32v __attribute__((vector_size(64)));
static const pw_exp_u32v pw_exp_tail_0 __attribute__((aligned(64))) = {
  UINT32_C(0x00000000), UINT32_C(0x00000000), UINT32_C(0x1a88bf6e), UINT32_C(0x3c9b3b4f), UINT32_C(0x9cd8dc5d), UINT32_C(0xbc716013), UINT32_C(0x108766d1), UINT32_C(0xbc905e7a), UINT32_C(0x3567f613), UINT32_C(0x3c8cd252), UINT32_C(0x23f98efa), UINT32_C(0xbc8bce80), UINT32_C(0x61e6c861), UINT32_C(0x3c60f74e), UINT32_C(0x5b33d399), UINT32_C(0x3c90a3e4)
};
static const pw_exp_u32v pw_exp_scale_0 __attribute__((aligned(64))) = {
  UINT32_C(0x00000000), UINT32_C(0x3ff00000), UINT32_C(0xa9fb3335), UINT32_C(0x3feff63d), UINT32_C(0x3e778061), UINT32_C(0x3fefec9a), UINT32_C(0xe86e7f85), UINT32_C(0x3fefe315), UINT32_C(0xd3158574), UINT32_C(0x3fefd9b0), UINT32_C(0x29ddf6de), UINT32_C(0x3fefd06b), UINT32_C(0x18759bc8), UINT32_C(0x3fefc745), UINT32_C(0xcac6f383), UINT32_C(0x3fefbe3e)
};
static const pw_exp_u32v pw_exp_tail_1 __attribute__((aligned(64))) = {
  UINT32_C(0x5d837b6d), UINT32_C(0x3c979aa6), UINT32_C(0x92fdeffc), UINT32_C(0x3c8eb51a), UINT32_C(0x702f9cd1), UINT32_C(0x3c3ebe3d), UINT32_C(0x89906e0b), UINT32_C(0xbc6a0334), UINT32_C(0x2a2fbd0e), UINT32_C(0xbc955652), UINT32_C(0x8c4eea55), UINT32_C(0xbc5080ef), UINT32_C(0xb9d5f416), UINT32_C(0xbc91c923), UINT32_C(0xe95c55af), UINT32_C(0x3c80d3e3)
};
static const pw_exp_u32v pw_exp_scale_1 __attribute__((aligned(64))) = {
  UINT32_C(0x6cf9890f), UINT32_C(0x3fefb558), UINT32_C(0x2b7247f7), UINT32_C(0x3fefac92), UINT32_C(0x32d3d1a2), UINT32_C(0x3fefa3ec), UINT32_C(0xaffed31b), UINT32_C(0x3fef9b66), UINT32_C(0xd0125b51), UINT32_C(0x3fef9301), UINT32_C(0xc06c31cc), UINT32_C(0x3fef8abd), UINT32_C(0xaea92de0), UINT32_C(0x3fef829a), UINT32_C(0xc8a58e51), UINT32_C(0x3fef7a98)
};
static const pw_exp_u32v pw_exp_tail_2 __attribute__((aligned(64))) = {
  UINT32_C(0xeaa59348), UINT32_C(0xbc801b15), UINT32_C(0x55de323d), UINT32_C(0xbc8f1ff0), UINT32_C(0x3f1353bf), UINT32_C(0x3c8b898c), UINT32_C(0x7611eb26), UINT32_C(0xbc96d99c), UINT32_C(0x3e3a2f60), UINT32_C(0x3c9aecf7), UINT32_C(0xcb86389d), UINT32_C(0xbc8fe782), UINT32_C(0x44a6c38d), UINT32_C(0x3c8a6f41), UINT32_C(0xb0e4047d), UINT32_C(0x3c807a05)
};
static const pw_exp_u32v pw_exp_scale_2 __attribute__((aligned(64))) = {
  UINT32_C(0x3c7d517b), UINT32_C(0x3fef72b8), UINT32_C(0x388c8dea), UINT32_C(0x3fef6af9), UINT32_C(0xeb6fcb75), UINT32_C(0x3fef635b), UINT32_C(0x84045cd4), UINT32_C(0x3fef5be0), UINT32_C(0x3168b9aa), UINT32_C(0x3fef5487), UINT32_C(0x22fcd91d), UINT32_C(0x3fef4d50), UINT32_C(0x88628cd6), UINT32_C(0x3fef463b), UINT32_C(0x917ddc96), UINT32_C(0x3fef3f49)
};
static const pw_exp_u32v pw_exp_tail_3 __attribute__((aligned(64))) = {
  UINT32_C(0xe3a8a894), UINT32_C(0x3c968efd), UINT32_C(0xf274487d), UINT32_C(0x3c875e18), UINT32_C(0x981fe7f2), UINT32_C(0x3c80472b), UINT32_C(0x3f71085e), UINT32_C(0xbc96b87b), UINT32_C(0x6d09ab31), UINT32_C(0x3c82f7e1), UINT32_C(0x1a6fbffa), UINT32_C(0xbc3d219b), UINT32_C(0x720c0ab4), UINT32_C(0x3c8b3782), UINT32_C(0x89cecb8f), UINT32_C(0x3c6e1492)
};
static const pw_exp_u32v pw_exp_scale_3 __attribute__((aligned(64))) = {
  UINT32_C(0x6e756238), UINT32_C(0x3fef387a), UINT32_C(0x4fb2a63f), UINT32_C(0x3fef31ce), UINT32_C(0x65e27cdd), UINT32_C(0x3fef2b45), UINT32_C(0xe1f56381), UINT32_C(0x3fef24df), UINT32_C(0xf51fdee1), UINT32_C(0x3fef1e9d), UINT32_C(0xd0dad990), UINT32_C(0x3fef187f), UINT32_C(0xa6e4030b), UINT32_C(0x3fef1285), UINT32_C(0xa93e2f56), UINT32_C(0x3fef0caf)
};
static const pw_exp_u32v pw_exp_tail_4 __attribute__((aligned(64))) = {
  UINT32_C(0x4db0abb6), UINT32_C(0x3c834d75), UINT32_C(0xe2ac744c), UINT32_C(0x3c864201), UINT32_C(0x5dd3f84a), UINT32_C(0x3c8fdd39), UINT32_C(0x3b8e5b04), UINT32_C(0xbc86a380), UINT32_C(0xcc4b5068), UINT32_C(0xbc924aed), UINT32_C(0x1b512d8e), UINT32_C(0xbc9907f8), UINT32_C(0x3e9436d2), UINT32_C(0xbc71d1e8), UINT32_C(0xb3ce1b15), UINT32_C(0xbc991919)
};
static const pw_exp_u32v pw_exp_scale_4 __attribute__((aligned(64))) = {
  UINT32_C(0x0a31b715), UINT32_C(0x3fef06fe), UINT32_C(0xfc4cd831), UINT32_C(0x3fef0170), UINT32_C(0xb26416ff), UINT32_C(0x3feefc08), UINT32_C(0x5f929ff1), UINT32_C(0x3feef6c5), UINT32_C(0x373aa9cb), UINT32_C(0x3feef1a7), UINT32_C(0x6d05d866), UINT32_C(0x3feeecae), UINT32_C(0x34e59ff7), UINT32_C(0x3feee7db), UINT32_C(0xc313a8e5), UINT32_C(0x3feee32d)
};
static const pw_exp_u32v pw_exp_tail_5 __attribute__((aligned(64))) = {
  UINT32_C(0xa72a4c6d), UINT32_C(0x3c859f48), UINT32_C(0x7a28698a), UINT32_C(0xbc931260), UINT32_C(0x4817895b), UINT32_C(0xbc58a78f), UINT32_C(0x67499a1b), UINT32_C(0xbc7c2c9b), UINT32_C(0x60c2ac11), UINT32_C(0x3c4363ed), UINT32_C(0x3b0664ef), UINT32_C(0x3c966609), UINT32_C(0xdaa10379), UINT32_C(0x3c6ecce1), UINT32_C(0x3f0f1230), UINT32_C(0x3c93ff8e)
};
static const pw_exp_u32v pw_exp_scale_5 __attribute__((aligned(64))) = {
  UINT32_C(0x4c123422), UINT32_C(0x3feedea6), UINT32_C(0x04ac801c), UINT32_C(0x3feeda45), UINT32_C(0x21f72e2a), UINT32_C(0x3feed60a), UINT32_C(0xd950a897), UINT32_C(0x3feed1f5), UINT32_C(0x6061892d), UINT32_C(0x3feece08), UINT32_C(0xed1d0057), UINT32_C(0x3feeca41), UINT32_C(0xb5c13cd0), UINT32_C(0x3feec6a2), UINT32_C(0xf0d7d3de), UINT32_C(0x3feec32a)
};
static const pw_exp_u32v pw_exp_tail_6 __attribute__((aligned(64))) = {
  UINT32_C(0xbb7aafb0), UINT32_C(0x3c7690ce), UINT32_C(0xeb54e077), UINT32_C(0x3c931dbd), UINT32_C(0x0071a38e), UINT32_C(0xbc8f9434), UINT32_C(0xdc93a349), UINT32_C(0xbc87decc), UINT32_C(0xbd0f385f), UINT32_C(0xbc78dec6), UINT32_C(0xec7b5cf6), UINT32_C(0xbc861246), UINT32_C(0x18fdd78e), UINT32_C(0x3c933505), UINT32_C(0x2f8a9b05), UINT32_C(0x3c7b98b7)
};
static const pw_exp_u32v pw_exp_scale_6 __attribute__((aligned(64))) = {
  UINT32_C(0xd5362a27), UINT32_C(0x3feebfda), UINT32_C(0x99fddd0d), UINT32_C(0x3feebcb2), UINT32_C(0x769d2ca7), UINT32_C(0x3feeb9b2), UINT32_C(0xa2cf6642), UINT32_C(0x3feeb6da), UINT32_C(0x569d4f82), UINT32_C(0x3feeb42b), UINT32_C(0xca5d920f), UINT32_C(0x3feeb1a4), UINT32_C(0x36b527da), UINT32_C(0x3feeaf47), UINT32_C(0xd497c7fd), UINT32_C(0x3feead12)
};
static const pw_exp_u32v pw_exp_tail_7 __attribute__((aligned(64))) = {
  UINT32_C(0xe21c5409), UINT32_C(0x3c9063e1), UINT32_C(0x5019c6ea), UINT32_C(0x3c34c785), UINT32_C(0x2b64c035), UINT32_C(0x3c9432e6), UINT32_C(0x6199769f), UINT32_C(0xbc8ce44a), UINT32_C(0x3bef4da8), UINT32_C(0xbc8c33c5), UINT32_C(0x892be9ae), UINT32_C(0xbc845378), UINT32_C(0x78565858), UINT32_C(0xbc93cedd), UINT32_C(0x807e1964), UINT32_C(0x3c5710aa)
};
static const pw_exp_u32v pw_exp_scale_7 __attribute__((aligned(64))) = {
  UINT32_C(0xdd485429), UINT32_C(0x3feeab07), UINT32_C(0x8a5946b7), UINT32_C(0x3feea926), UINT32_C(0x15ad2148), UINT32_C(0x3feea76f), UINT32_C(0xb976dc09), UINT32_C(0x3feea5e1), UINT32_C(0xb03a5585), UINT32_C(0x3feea47e), UINT32_C(0x34ccc320), UINT32_C(0x3feea346), UINT32_C(0x82552225), UINT32_C(0x3feea238), UINT32_C(0xd44ca973), UINT32_C(0x3feea155)
};
static const pw_exp_u32v pw_exp_tail_8 __attribute__((aligned(64))) = {
  UINT32_C(0xbf5e2228), UINT32_C(0xbc93b3ef), UINT32_C(0x8734b982), UINT32_C(0xbc6a12ad), UINT32_C(0xb86da9ee), UINT32_C(0xbc6367ef), UINT32_C(0x54e08851), UINT32_C(0xbc80dc3d), UINT32_C(0x7e5a3ecf), UINT32_C(0xbc781f64), UINT32_C(0xc08b7db0), UINT32_C(0xbc86ee4a), UINT32_C(0x1e55e68a), UINT32_C(0xbc861932), UINT32_C(0x5e09d4d3), UINT32_C(0x3c909ccb)
};
static const pw_exp_u32v pw_exp_scale_8 __attribute__((aligned(64))) = {
  UINT32_C(0x667f3bcd), UINT32_C(0x3feea09e), UINT32_C(0x750bdabf), UINT32_C(0x3feea012), UINT32_C(0x3c651a2f), UINT32_C(0x3fee9fb2), UINT32_C(0xf9519484), UINT32_C(0x3fee9f7d), UINT32_C(0xe8ec5f74), UINT32_C(0x3fee9f75), UINT32_C(0x48a58174), UINT32_C(0x3fee9f9a), UINT32_C(0x564267c9), UINT32_C(0x3fee9feb), UINT32_C(0x4fde5d3f), UINT32_C(0x3feea069)
};
static const pw_exp_u32v pw_exp_tail_9 __attribute__((aligned(64))) = {
  UINT32_C(0xb94da51d), UINT32_C(0xbc7b32dc), UINT32_C(0x5467c06b), UINT32_C(0x3c94ecfd), UINT32_C(0xabd66c55), UINT32_C(0x3c65ebe1), UINT32_C(0x2fb3cf42), UINT32_C(0xbc88a1c5), UINT32_C(0xf13b3734), UINT32_C(0xbc9369b6), UINT32_C(0x3a19ff1e), UINT32_C(0xbc805e84), UINT32_C(0xd872576e), UINT32_C(0xbc94d450), UINT32_C(0x5b0e8a00), UINT32_C(0x3c90ad67)
};
static const pw_exp_u32v pw_exp_scale_9 __attribute__((aligned(64))) = {
  UINT32_C(0x73eb0187), UINT32_C(0x3feea114), UINT32_C(0x0130c132), UINT32_C(0x3feea1ed), UINT32_C(0x36cf4e62), UINT32_C(0x3feea2f3), UINT32_C(0x543e1a12), UINT32_C(0x3feea427), UINT32_C(0x994cce13), UINT32_C(0x3feea589), UINT32_C(0x4623c7ad), UINT32_C(0x3feea71a), UINT32_C(0x9b4492ed), UINT32_C(0x3feea8d9), UINT32_C(0xd98a6699), UINT32_C(0x3feeaac7)
};
static const pw_exp_u32v pw_exp_tail_10 __attribute__((aligned(64))) = {
  UINT32_C(0xc1f0eab4), UINT32_C(0x3c8db72f), UINT32_C(0x9cc5e7ff), UINT32_C(0xbc65b660), UINT32_C(0x59f35f44), UINT32_C(0x3c7bf683), UINT32_C(0xa71e3d83), UINT32_C(0xbc93091f), UINT32_C(0x8b6c1e29), UINT32_C(0xbc5da9b8), UINT32_C(0x7c90b959), UINT32_C(0xbc6c23f9), UINT32_C(0x22f4f9aa), UINT32_C(0xbc924343), UINT32_C(0xd7668e4b), UINT32_C(0xbc85ca6c)
};
static const pw_exp_u32v pw_exp_scale_10 __attribute__((aligned(64))) = {
  UINT32_C(0x422aa0db), UINT32_C(0x3feeace5), UINT32_C(0x16b5448c), UINT32_C(0x3feeaf32), UINT32_C(0x99157736), UINT32_C(0x3feeb1ae), UINT32_C(0x0b91ffc6), UINT32_C(0x3feeb45b), UINT32_C(0xb0cdc5e5), UINT32_C(0x3feeb737), UINT32_C(0xcbc8520f), UINT32_C(0x3feeba44), UINT32_C(0x9fde4e50), UINT32_C(0x3feebd82), UINT32_C(0x70ca07ba), UINT32_C(0x3feec0f1)
};
static const pw_exp_u32v pw_exp_tail_11 __attribute__((aligned(64))) = {
  UINT32_C(0x2b91ce27), UINT32_C(0x3c71affc), UINT32_C(0xe10a73bb), UINT32_C(0x3c6dd235), UINT32_C(0x22622263), UINT32_C(0xbc87c504), UINT32_C(0xe3e231d5), UINT32_C(0x3c8b1c86), UINT32_C(0xd3bcbb15), UINT32_C(0xbc91bbd1), UINT32_C(0x9cee31d2), UINT32_C(0x3c90cc31), UINT32_C(0x6e735ab3), UINT32_C(0x3c846984), UINT32_C(0x978e9db4), UINT32_C(0xbc82dfcd)
};
static const pw_exp_u32v pw_exp_scale_11 __attribute__((aligned(64))) = {
  UINT32_C(0x82a3f090), UINT32_C(0x3feec491), UINT32_C(0x19e32323), UINT32_C(0x3feec863), UINT32_C(0x7b5de565), UINT32_C(0x3feecc66), UINT32_C(0xec4a2d33), UINT32_C(0x3feed09b), UINT32_C(0xb23e255d), UINT32_C(0x3feed503), UINT32_C(0x1330b358), UINT32_C(0x3feed99e), UINT32_C(0x5579fdbf), UINT32_C(0x3feede6b), UINT32_C(0xbfd3f37a), UINT32_C(0x3feee36b)
};
static const pw_exp_u32v pw_exp_tail_12 __attribute__((aligned(64))) = {
  UINT32_C(0x92cb3387), UINT32_C(0x3c8c1a77), UINT32_C(0x4ad1d9fa), UINT32_C(0xbc907b8f), UINT32_C(0x56dcaeba), UINT32_C(0xbc55c3d9), UINT32_C(0x3da6f640), UINT32_C(0xbc90a40e), UINT32_C(0x38ad9334), UINT32_C(0xbc68d6f4), UINT32_C(0x6b588a35), UINT32_C(0xbc91eee2), UINT32_C(0x0a5fddcd), UINT32_C(0x3c74ffd7), UINT32_C(0xfa9298ac), UINT32_C(0xbc91bdfb)
};
static const pw_exp_u32v pw_exp_scale_12 __attribute__((aligned(64))) = {
  UINT32_C(0x995ad3ad), UINT32_C(0x3feee89f), UINT32_C(0x298db666), UINT32_C(0x3feeee07), UINT32_C(0xb84f15fb), UINT32_C(0x3feef3a2), UINT32_C(0x8de5593a), UINT32_C(0x3feef972), UINT32_C(0xf2fb5e47), UINT32_C(0x3feeff76), UINT32_C(0x30a1064a), UINT32_C(0x3fef05b0), UINT32_C(0x904bc1d2), UINT32_C(0x3fef0c1e), UINT32_C(0x5bd71e09), UINT32_C(0x3fef12c2)
};
static const pw_exp_u32v pw_exp_tail_13 __attribute__((aligned(64))) = {
  UINT32_C(0x30af0cb3), UINT32_C(0x3c736eae), UINT32_C(0x5c9ffd94), UINT32_C(0x3c8ee332), UINT32_C(0xd10959ac), UINT32_C(0x3c84e08f), UINT32_C(0x384e1a67), UINT32_C(0x3c63cdaf), UINT32_C(0x6c921968), UINT32_C(0x3c676b2c), UINT32_C(0x83ccb5d2), UINT32_C(0xbc808a18), UINT32_C(0x3ffffa6f), UINT32_C(0xbc8fad5d), UINT32_C(0x3875a949), UINT32_C(0xbc900dae)
};
static const pw_exp_u32v pw_exp_scale_13 __attribute__((aligned(64))) = {
  UINT32_C(0xdd85529c), UINT32_C(0x3fef199b), UINT32_C(0x5fffd07a), UINT32_C(0x3fef20ab), UINT32_C(0x2e57d14b), UINT32_C(0x3fef27f1), UINT32_C(0x9406e7b5), UINT32_C(0x3fef2f6d), UINT32_C(0xdcef9069), UINT32_C(0x3fef3720), UINT32_C(0x555dc3fa), UINT32_C(0x3fef3f0b), UINT32_C(0x4a07897c), UINT32_C(0x3fef472d), UINT32_C(0x080d89f2), UINT32_C(0x3fef4f87)
};
static const pw_exp_u32v pw_exp_tail_14 __attribute__((aligned(64))) = {
  UINT32_C(0xa63d07a7), UINT32_C(0x3c74a385), UINT32_C(0x2040220f), UINT32_C(0xbc82919e), UINT32_C(0xd5c192ac), UINT32_C(0x3c8e5a50), UINT32_C(0xac016b4b), UINT32_C(0x3c843a59), UINT32_C(0x07b43e1f), UINT32_C(0xbc82d521), UINT32_C(0x3b470dc9), UINT32_C(0xbc892ab9), UINT32_C(0x603a88d3), UINT32_C(0x3c74b604), UINT32_C(0x519d7271), UINT32_C(0x3c83c5ec)
};
static const pw_exp_u32v pw_exp_scale_14 __attribute__((aligned(64))) = {
  UINT32_C(0xdcfba487), UINT32_C(0x3fef5818), UINT32_C(0x16c98398), UINT32_C(0x3fef60e3), UINT32_C(0x03db3285), UINT32_C(0x3fef69e6), UINT32_C(0xf301b460), UINT32_C(0x3fef7321), UINT32_C(0x337b9b5f), UINT32_C(0x3fef7c97), UINT32_C(0x14f5a129), UINT32_C(0x3fef8646), UINT32_C(0xe78b3ff6), UINT32_C(0x3fef902e), UINT32_C(0xfbc74c83), UINT32_C(0x3fef9a51)
};
static const pw_exp_u32v pw_exp_tail_15 __attribute__((aligned(64))) = {
  UINT32_C(0x8fd391f0), UINT32_C(0xbc8ff712), UINT32_C(0xe223747d), UINT32_C(0xbc8dae98), UINT32_C(0x41aa2008), UINT32_C(0x3c8ec3bc), UINT32_C(0xc3a9eb32), UINT32_C(0x3c842b94), UINT32_C(0x31d185ee), UINT32_C(0x3c8a64a9), UINT32_C(0xe43be3ed), UINT32_C(0xbc8e37ba), UINT32_C(0x4d91cd9d), UINT32_C(0x3c77893b), UINT32_C(0x4160cc89), UINT32_C(0x3c5305c1)
};
static const pw_exp_u32v pw_exp_scale_15 __attribute__((aligned(64))) = {
  UINT32_C(0xa2a490da), UINT32_C(0x3fefa4af), UINT32_C(0x2d8e67f1), UINT32_C(0x3fefaf48), UINT32_C(0xee615a27), UINT32_C(0x3fefba1b), UINT32_C(0x376bba97), UINT32_C(0x3fefc52b), UINT32_C(0x5b6e4540), UINT32_C(0x3fefd076), UINT32_C(0xad9cbe14), UINT32_C(0x3fefdbfd), UINT32_C(0x819e90d8), UINT32_C(0x3fefe7c1), UINT32_C(0x2b8f71f1), UINT32_C(0x3feff3c2)
};

static __attribute__((always_inline)) inline void
pw_exp_register_lookup(pw_u64v ki,pw_u64v *tailbits,pw_u64v *sbits) {
  const pw_u64v keys=ki&127;
  const pw_u64v paired=keys|(keys<<32);
  pw_exp_u32v key;memcpy(&key,&paired,sizeof key);
  const pw_exp_u32v selector=((key&7)<<1)
    +(pw_exp_u32v){0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1};
  const pw_exp_u32v group=key>>3;
  pw_exp_u32v tails={0},scales={0};
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==0);
    tails|=__builtin_shuffle(pw_exp_tail_0,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_0,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==1);
    tails|=__builtin_shuffle(pw_exp_tail_1,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_1,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==2);
    tails|=__builtin_shuffle(pw_exp_tail_2,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_2,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==3);
    tails|=__builtin_shuffle(pw_exp_tail_3,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_3,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==4);
    tails|=__builtin_shuffle(pw_exp_tail_4,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_4,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==5);
    tails|=__builtin_shuffle(pw_exp_tail_5,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_5,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==6);
    tails|=__builtin_shuffle(pw_exp_tail_6,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_6,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==7);
    tails|=__builtin_shuffle(pw_exp_tail_7,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_7,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==8);
    tails|=__builtin_shuffle(pw_exp_tail_8,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_8,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==9);
    tails|=__builtin_shuffle(pw_exp_tail_9,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_9,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==10);
    tails|=__builtin_shuffle(pw_exp_tail_10,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_10,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==11);
    tails|=__builtin_shuffle(pw_exp_tail_11,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_11,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==12);
    tails|=__builtin_shuffle(pw_exp_tail_12,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_12,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==13);
    tails|=__builtin_shuffle(pw_exp_tail_13,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_13,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==14);
    tails|=__builtin_shuffle(pw_exp_tail_14,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_14,selector)&keep;
  }
  {
    const pw_exp_u32v keep=(pw_exp_u32v)(group==15);
    tails|=__builtin_shuffle(pw_exp_tail_15,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_15,selector)&keep;
  }
  memcpy(tailbits,&tails,sizeof tails);
  memcpy(sbits,&scales,sizeof scales);
}
#endif
