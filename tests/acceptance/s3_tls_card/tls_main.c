/* Four threads each write their own values through one compiler's code and,
   after a barrier, read them back through the other's.  The main thread
   writes nothing and must still see the initial values at the end.  With
   shared storage (CONTROL_SHARED) the reads after the barrier see the last
   writer's values, so the check fails.  */
#include <pthread.h>
#include <stdio.h>
#include "tls.h"

#define THREADS 4

static pthread_barrier_t barrier;
static int failures[THREADS + 1];
static int checks;

static void
expect (int slot, const char *what, int got, int want)
{
  if (got != want)
    {
      failures[slot]++;
      printf ("FAIL thread=%d %s got=%d want=%d\n", slot, what, got, want);
    }
}

static void
initial (int slot)
{
  expect (slot, "new_get_d", new_get_d (), 7);
  expect (slot, "donor_get_d", donor_get_d (), 7);
  expect (slot, "donor_get_g", donor_get_g (), 9);
  expect (slot, "new_get_g", new_get_g (), 9);
  expect (slot, "tls_s", tls_s, 11);
  expect (slot, "lib_get_s", lib_get_s (), 11);
  expect (slot, "lib_get_ls", lib_get_ls (), 13);
}

static void *
worker (void *arg)
{
  int i = (int) (long) arg;
  initial (i);
  new_set_d (100 + i);		/* GCC 16 writes the donor's variable.  */
  donor_set_g (200 + i);	/* The donor writes GCC 16's variable.  */
  tls_s = 300 + i;		/* The executable writes the library's.  */
  lib_set_ls (400 + i);
  pthread_barrier_wait (&barrier);
  expect (i, "donor_get_d", donor_get_d (), 100 + i);
  expect (i, "tls_d", tls_d, 100 + i);
  expect (i, "new_get_g", new_get_g (), 200 + i);
  expect (i, "tls_g", tls_g, 200 + i);
  expect (i, "lib_get_s", lib_get_s (), 300 + i);
  expect (i, "lib_get_ls", lib_get_ls (), 400 + i);
  pthread_barrier_wait (&barrier);
  return 0;
}

int
main (void)
{
  pthread_t t[THREADS];
  int i, total = 0;

  pthread_barrier_init (&barrier, 0, THREADS);
  for (i = 0; i < THREADS; i++)
    if (pthread_create (&t[i], 0, worker, (void *) (long) i))
      {
	printf ("S3-TLS FAIL pthread_create\n");
	return 1;
      }
  for (i = 0; i < THREADS; i++)
    pthread_join (t[i], 0);
  initial (THREADS);
  checks = THREADS * 13 + 7;
  for (i = 0; i <= THREADS; i++)
    total += failures[i];
  printf ("S3-TLS %s checks=%d failures=%d\n", total ? "FAIL" : "PASS", checks, total);
  return total != 0;
}
