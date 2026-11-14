/* Build-time dump interception; the packaged benchmark remains unchanged. */
#include <stdio.h>
int corpus_fprintf(FILE *, const char *, ...);
#define fprintf corpus_fprintf
