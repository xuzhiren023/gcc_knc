#include <pthread.h>
#include <stdio.h>
static unsigned long long atomic_count, sync_count;
static void *worker(void *unused)
{
  unsigned int i;
  (void) unused;
  for (i = 0; i < 100000; ++i)
    {
      __atomic_fetch_add(&atomic_count, 1, __ATOMIC_SEQ_CST);
      __sync_fetch_and_add(&sync_count, 1);
    }
  return 0;
}
int main(void)
{
  pthread_t threads[4];
  unsigned int i;
  for (i = 0; i < 4; ++i)
    if (pthread_create(&threads[i], 0, worker, 0)) return 2;
  for (i = 0; i < 4; ++i)
    if (pthread_join(threads[i], 0)) return 3;
  printf("atomic=%llu sync=%llu expected=400000\n", atomic_count, sync_count);
  return atomic_count != 400000 || sync_count != 400000;
}
