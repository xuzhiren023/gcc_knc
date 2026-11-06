/* Reduced from gcc.dg/vect/vect-outer-2d.c; S6-07 baseline ICE. */
#define N 40
float image[N][N][N+1] __attribute__ ((__aligned__(__BIGGEST_ALIGNMENT__)));
__attribute__ ((noinline)) void
foo (){
  int i,j,k;
 for (k=0; k<N; k++) {
  for (i = 0; i < N; i++) {
    for (j = 0; j < i+1; j++) {
      image[k][j][i] = j+i+k;
    }
  }
 }
}
