#define _POSIX_C_SOURCE 200809L
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>

int main(int argc, char **argv)
{
  struct rlimit limit;
  struct timespec delay = {0, 0};
  const char *sleep = strstr(argv[0], "sleep-");
  (void)argc;
  if (sleep)
    {
      /* Reverse completion order, with all eight within one second. */
      delay.tv_nsec = (900 - (sleep[6] - '0') * 40) * 1000000L;
      if (getrlimit(RLIMIT_AS, &limit) || limit.rlim_cur != 64 * 1024 * 1024)
        return 3;
    }
  else if (strstr(argv[0], "timeout")) delay.tv_sec = 10;
  else if (strstr(argv[0], "crash")) raise(SIGSEGV);
  else if (strstr(argv[0], "fail")) { puts("failure diagnostic"); return 7; }
  while (nanosleep(&delay, &delay)) {}
  return 0;
}
