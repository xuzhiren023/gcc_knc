/* S11-27 serial MG card batch. Each child prints its own NPB verification.
   The lead invokes this through card_run --threads 1. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static const char *cases[] = { /* CASES */ };

static double now(void)
{
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(126);
  return t.tv_sec + t.tv_nsec * 1e-9;
}

int main(void)
{
  double deadline = now() + 540;
  unsigned i;
  int incomplete = 0;
  setvbuf(stdout, NULL, _IONBF, 0);
  if (setenv("LD_LIBRARY_PATH", ".", 1)) return 126;
  for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
    {
      pid_t child, result;
      int status, timed_out = 0;
      double start = now();
      if (start >= deadline)
        {
          printf("CASE %s NOT_RUN total budget exhausted\n", cases[i]);
          incomplete = 1;
          continue;
        }
      printf("CASE %s BEGIN\n", cases[i]);
      child = fork();
      if (child < 0) return 126;
      if (!child)
        {
          char path[128];
          snprintf(path, sizeof(path), "./%s", cases[i]);
          execl(path, path, (char *) NULL);
          perror(path);
          _exit(126);
        }
      for (;;)
        {
          struct timespec pause = {0, 100000000};
          result = waitpid(child, &status, WNOHANG);
          if (result == child) break;
          if (result < 0 && errno != EINTR) return 126;
          if (now() >= deadline || now() - start >= 120)
            {
              kill(child, SIGKILL);
              while (waitpid(child, &status, 0) < 0)
                if (errno != EINTR) return 126;
              timed_out = incomplete = 1;
              break;
            }
          nanosleep(&pause, NULL);
        }
      printf("CASE %s END exit=%d signal=%d timeout=%d seconds=%.3f\n",
             cases[i], WIFEXITED(status) ? WEXITSTATUS(status) : -1,
             WIFSIGNALED(status) ? WTERMSIG(status) : 0, timed_out, now() - start);
    }
  /* NPB often exits zero on wrong answers: inspect each verification line. */
  return incomplete ? 124 : 0;
}
