/* S9-08 host test: what config/linux/knc/spincount.h uses of libgomp.h, so that the k1om
   runtime's spin-count header compiles into delay.c on the host (Cygwin x86_64).  The names
   and types follow libgomp/libgomp.h; gomp_error is delay.c's, which counts the reports.  */
#ifndef S9_08_LIBGOMP_H
#define S9_08_LIBGOMP_H 1

/* card.h, which spincount.h includes after this file, needs the GNU extensions of
   <sched.h>; they must be on before the first system header.  */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#include <stdbool.h>
#include <stdio.h>

#define attribute_hidden

extern unsigned long long gomp_spin_count_var;
extern void gomp_error (const char *, ...)
  __attribute__ ((format (printf, 1, 2)));

#endif
