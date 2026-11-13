/* S11-28 correctness-only supervisor. Never used for primary timing. */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

int main(void)
{
  pid_t child;
  int status, tick = 0, rc;
  FILE *flag = fopen("arena.flag", "r");
  if (flag) { fclose(flag); setenv("MALLOC_ARENA_MAX", "2", 1); }
  child = fork();
  if (child < 0) return 2;
  if (!child) {
    execl("./hpcg", "hpcg", (char *)0);
    _exit(127);
  }
  for (;;) {
    char path[80], line[256];
    FILE *input;
    struct timespec delay = {0, 500000000};
    snprintf(path, sizeof path, "/proc/%ld/status", (long)child);
    input = fopen(path, "r");
    if (input) {
      while (fgets(line, sizeof line, input))
        if (!strncmp(line, "VmPeak:", 7) || !strncmp(line, "VmHWM:", 6) ||
            !strncmp(line, "VmSize:", 7))
          printf("HPCG_MEMORY %d %s", tick, line);
      fclose(input);
      fflush(stdout);
    }
    rc = waitpid(child, &status, WNOHANG);
    if (rc == child) break;
    if (rc < 0 && errno != EINTR) return 2;
    /* Keep the sampling round bounded; partial measurements are lower bounds. */
    if (++tick == 120) {
      kill(child, SIGTERM);
      while (waitpid(child, &status, 0) < 0) if (errno != EINTR) return 2;
      puts("HPCG_MEMORY_INCOMPLETE 60-second diagnostic limit");
      return 124;
    }
    while (nanosleep(&delay, &delay) && errno == EINTR) {}
  }
  return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
