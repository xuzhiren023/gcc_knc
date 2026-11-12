/* Fixed file input, one compression/decompression, full byte comparison. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef CORPUS_ZLIB
#include <zlib.h>
#else
#include <bzlib.h>
#endif

int main(int argc, char **argv)
{
  const unsigned int size = 8 * 1024 * 1024;
  unsigned char *input = malloc(size), *packed = malloc(size * 2 + 4096), *output = malloc(size);
  FILE *f = fopen("input.bin", "rb");
  int good = 0;
  unsigned int packed_size = 0;
  int decode = argc == 2 && !strcmp(argv[1], "decode");
  if (!input || !packed || !output || !f) return 2;
  if (fread(input, 1, size, f) != size || fgetc(f) != EOF) return 2;
  fclose(f);
  if (decode) {
    f = fopen("packed.bin", "rb");
    if (!f) return 2;
    packed_size = fread(packed, 1, size * 2 + 4096, f);
    if (!feof(f) || ferror(f)) return 2;
    fclose(f);
  }
#ifdef CORPUS_ZLIB
  {
    uLongf compressed = size * 2 + 4096, restored = size;
    if (decode) compressed = packed_size;
    if ((decode || compress2(packed, &compressed, input, size, 6) == Z_OK) &&
        uncompress(output, &restored, packed, compressed) == Z_OK)
      good = restored == size && !memcmp(input, output, size);
    packed_size = compressed;
  }
#else
  {
    unsigned int compressed = size * 2 + 4096, restored = size;
    if (decode) compressed = packed_size;
    if ((decode || BZ2_bzBuffToBuffCompress((char *)packed, &compressed, (char *)input, size, 9, 0, 30) == BZ_OK) &&
        BZ2_bzBuffToBuffDecompress((char *)output, &restored, (char *)packed, compressed, 0, 0) == BZ_OK)
      good = restored == size && !memcmp(input, output, size);
    packed_size = compressed;
  }
#endif
  if (good && !decode) {
    f = fopen("packed.bin", "wb");
    if (!f || fwrite(packed, 1, packed_size, f) != packed_size || fclose(f)) return 2;
  }
  if (good) {
    output[size / 2] ^= 1;
    if (!memcmp(input, output, size)) return 1;
    puts("CORPUS_CONTROL rejected");
  }
  free(input); free(packed); free(output);
  puts(decode ? (good ? "CORPUS_CROSS pass" : "CORPUS_CROSS fail") :
               (good ? "CORPUS_CHECK pass" : "CORPUS_CHECK fail"));
  return good ? 0 : 1;
}
