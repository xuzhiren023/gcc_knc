/* Harness wrapper; the packaged STREAM source and license remain unchanged. */
#define main corpus_stream_main
#include "stream.c"
#undef main
#include <stdint.h>
extern void corpus_environment(const char *) __attribute__((weak));
int main(void) {
  int rc = corpus_stream_main();
  FILE *f;
  int which;
  STREAM_TYPE *values[3] = {a,b,c};
  if (rc) return rc;
  if (corpus_environment) corpus_environment("materialize");
  f = fopen("arrays.bin", "wb");
  if (!f) return 2;
  for (which=0; which<3; ++which) {
    char name[80] = {0};
    uint64_t count = STREAM_ARRAY_SIZE;
    name[0] = 'a'+which;
    if (fwrite(name,1,sizeof name,f)!=sizeof name ||
        fwrite(&count,sizeof count,1,f)!=1 ||
        fwrite(values[which],sizeof(double),count,f)!=count) return 2;
  }
  return fclose(f) ? 2 : 0;
}
