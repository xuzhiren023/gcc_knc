/* Compiled for baseline x86-64 before executing the native AVX2 experiment. */
#include <stdio.h>
#include <fenv.h>
#include <immintrin.h>
int main(void) {
  __builtin_cpu_init();
  printf("{\"avx2\":%s,\"fma\":%s,\"avx512f\":%s,\"roundingMode\":%d,\"feTonearest\":%d,\"mxcsr\":%u,\"compiler\":\"%s\"}\n",
    __builtin_cpu_supports("avx2")?"true":"false",
    __builtin_cpu_supports("fma")?"true":"false",
    __builtin_cpu_supports("avx512f")?"true":"false",
    fegetround(),FE_TONEAREST,_mm_getcsr(),__VERSION__);
  return 0;
}
