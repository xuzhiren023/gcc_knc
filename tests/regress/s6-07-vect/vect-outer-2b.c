/* Reduced from gcc.dg/vect/vect-outer-2b.c; S6-07 baseline ICE. */
#define N 40
float image[2*N][N][N] __attribute__ ((__aligned__(__BIGGEST_ALIGNMENT__)));
__attribute__ ((noinline)) void
foo (){
  int i,j,k;
 for (k=0; k<N; k++) {
  for (i = 0; i < N; i++) {
    for (j = 0; j < N; j++) {
      image[k+i][j][i] = j+i+k;
    }
  }
 }
}
