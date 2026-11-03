// S1-05: the torture runner must apply both option directives.
// options: -march=knc -O0 -std=gnu89 -DKNC_TORTURE_OPTIONS=7
/* { dg-options "-std=gnu89" } */
/* { dg-additional-options "-DKNC_TORTURE_OPTIONS=7" } */
/* { dg-options "-DKNC_OFF_TARGET=1" { target x86_64*-*-* i?86-*-* } } */
/* { dg-additional-options "-DKNC_OFF_TARGET=2" { target { x86_64*-*-* i?86-*-* } } } */
#ifdef KNC_OFF_TARGET
#error target-selected torture options must be skipped
#endif
#if KNC_TORTURE_OPTIONS != 7
#error torture additional options were ignored
#endif
knc_torture_options(x) { return x + KNC_TORTURE_OPTIONS; }
