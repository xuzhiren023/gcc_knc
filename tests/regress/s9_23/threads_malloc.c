/* S9-23: 240 threads each malloc and touch 8 MiB, so glibc makes one arena per thread.
   Under an RLIMIT_AS this fails "out of memory"; with no limit it prints "ok 240". */
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { THREADS = 240, BYTES = 8 << 20 };
static pthread_barrier_t barrier;
static int failures;

static void *work(void *arg) {
    char *p = malloc(BYTES);
    (void)arg;
    if (p) memset(p, 1, BYTES);
    else __sync_fetch_and_add(&failures, 1);
    pthread_barrier_wait(&barrier); /* all arenas live at once */
    free(p);
    return NULL;
}

int main(void) {
    pthread_t t[THREADS];
    int i, started = 0;
    pthread_barrier_init(&barrier, NULL, THREADS);
    for (i = 0; i < THREADS; ++i) {
        if (pthread_create(&t[i], NULL, work, NULL)) { puts("pthread_create failed"); return 1; }
        ++started;
    }
    for (i = 0; i < started; ++i) pthread_join(t[i], NULL);
    if (failures) { printf("malloc failed in %d threads\n", failures); return 1; }
    printf("ok %d\n", THREADS);
    return 0;
}
