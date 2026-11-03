// S1-05: the torture runner must apply both option directives.
// options: -march=knc -O0 -std=gnu89 -DKNC_TORTURE_OPTIONS=7
/* { dg-options "-std=gnu89" } */
/* { dg-additional-options "-DKNC_TORTURE_OPTIONS=7" } */
#if KNC_TORTURE_OPTIONS != 7
#error torture additional options were ignored
#endif
knc_torture_options(x) { return x + KNC_TORTURE_OPTIONS; }
