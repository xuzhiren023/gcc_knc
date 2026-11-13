/* S11-27 class-S correctness round: one serial case per physical core.
   The lead runs this through card_run --threads 240. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static const char *cases[] = { /* CASES */ };

int main(void)
{
  cpu_set_t allowed;
  int cpus[CPU_SETSIZE], cores = 0, ordinal = 0, cpu, failed = 0;
  unsigned first, i, total = sizeof(cases) / sizeof(cases[0]);
  setvbuf(stdout, NULL, _IONBF, 0);
  if (sched_getaffinity(0, sizeof(allowed), &allowed)) return 126;
  /* card_run allocates complete four-thread KNC cores in CPU order. */
  for (cpu = 0; cpu < CPU_SETSIZE; ++cpu)
    if (CPU_ISSET(cpu, &allowed) && ordinal++ % 4 == 0)
      cpus[cores++] = cpu;
  if (!cores || setenv("LD_LIBRARY_PATH", ".", 1)
      || setenv("OMP_NUM_THREADS", "1", 1)
      || setenv("OMP_DYNAMIC", "FALSE", 1)) return 126;
  for (first = 0; first < total; first += cores)
    {
      pid_t children[CPU_SETSIZE];
      unsigned count = total - first;
      if (count > (unsigned) cores) count = cores;
      for (i = 0; i < count; ++i)
        {
          children[i] = fork();
          if (children[i] < 0) return 126;
          if (!children[i])
            {
              cpu_set_t one;
              char path[128], log[128];
              int fd;
              CPU_ZERO(&one);
              CPU_SET(cpus[i], &one);
              if (sched_setaffinity(0, sizeof(one), &one)) _exit(126);
              snprintf(log, sizeof(log), "%s.log", cases[first + i]);
              fd = open(log, O_WRONLY | O_CREAT | O_TRUNC, 0600);
              if (fd < 0 || dup2(fd, 1) < 0 || dup2(fd, 2) < 0) _exit(126);
              close(fd);
              alarm(60);
              snprintf(path, sizeof(path), "./%s", cases[first + i]);
              execl(path, path, (char *) NULL);
              _exit(126);
            }
        }
      for (i = 0; i < count; ++i)
        {
          int status;
          char log[128], buffer[1024];
          FILE *file;
          while (waitpid(children[i], &status, 0) < 0)
            if (errno != EINTR) return 126;
          printf("CASE %s BEGIN cpu=%d\n", cases[first + i], cpus[i]);
          snprintf(log, sizeof(log), "%s.log", cases[first + i]);
          file = fopen(log, "r");
          if (file)
            {
              while (fgets(buffer, sizeof(buffer), file)) fputs(buffer, stdout);
              fclose(file);
            }
          else failed = 1;
          printf("CASE %s END exit=%d signal=%d\n", cases[first + i],
                 WIFEXITED(status) ? WEXITSTATUS(status) : -1,
                 WIFSIGNALED(status) ? WTERMSIG(status) : 0);
          if (!WIFEXITED(status) || WEXITSTATUS(status)) failed = 1;
        }
    }
  /* NPB exits zero for verification failures; the lead reads each CASE log. */
  return failed ? 1 : 0;
}
