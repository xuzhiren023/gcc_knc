/* Fixed file input, one compression/decompression, full byte comparison. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef CORPUS_ZLIB
#include <zlib.h>
#else
#include <bzlib.h>
#endif

int main(void)
{
  const unsigned int size = 8 * 1024 * 1024;
  unsigned char *input = malloc(size), *packed = malloc(size * 2 + 4096), *output = malloc(size);
  FILE *f = fopen("input.bin", "rb");
  int good = 0;
  if (!input || !packed || !output || !f) return 2;
  if (fread(input, 1, size, f) != size || fgetc(f) != EOF) return 2;
  fclose(f);
#ifdef CORPUS_ZLIB
  {
    uLongf compressed = size * 2 + 4096, restored = size;
    if (compress2(packed, &compressed, input, size, 6) == Z_OK &&
        uncompress(output, &restored, packed, compressed) == Z_OK)
      good = restored == size && !memcmp(input, output, size);
  }
#else
  {
    unsigned int compressed = size * 2 + 4096, restored = size;
    if (BZ2_bzBuffToBuffCompress((char *)packed, &compressed, (char *)input, size, 9, 0, 30) == BZ_OK &&
        BZ2_bzBuffToBuffDecompress((char *)output, &restored, (char *)packed, compressed, 0, 0) == BZ_OK)
      good = restored == size && !memcmp(input, output, size);
  }
#endif
  free(input); free(packed); free(output);
  puts(good ? "CORPUS_CHECK pass" : "CORPUS_CHECK fail");
  return good ? 0 : 1;
}
