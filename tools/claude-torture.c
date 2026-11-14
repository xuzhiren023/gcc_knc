/* S2-18: bounded parallel process groups, ordered results, per-child limits.
   POSIX fork/exec/wait, clock_gettime(2), getrlimit(2)/setrlimit(2).
   Children inherit card_run's affinity; its RLIMIT_AS is the job budget. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

struct test
{
  char file[256], name[256];
  pid_t pid;
  int status, expired, done;
  double deadline;
  FILE *output;
};

static volatile sig_atomic_t stopped;
static void stop(int signal_number) { stopped = signal_number; }

static double now(void)
{
  struct timespec value;
  if (clock_gettime(CLOCK_MONOTONIC, &value)) return -1;
  return value.tv_sec + value.tv_nsec / 1e9;
}

static int number(const char *text, unsigned long *value)
{
  char *end;
  if (*text < '0' || *text > '9') return 0;
  errno = 0;
  *value = strtoul(text, &end, 10);
  return !errno && !*end && *value;
}

static int report(struct test *test, FILE *details)
{
  char buffer[4096];
  size_t bytes;
  int ok = !test->expired && WIFEXITED(test->status)
           && WEXITSTATUS(test->status) == 0;
  if (fseek(test->output, 0, SEEK_SET)) return -1;
  fprintf(details, "TEST %s\n", test->name);
  if (!ok) fprintf(stderr, "TEST %s\n", test->name);
  while ((bytes = fread(buffer, 1, sizeof buffer, test->output)) != 0)
    if (fwrite(buffer, 1, bytes, details) != bytes
        || (!ok && fwrite(buffer, 1, bytes, stderr) != bytes)) return -1;
  if (ferror(test->output)) return -1;
  fprintf(details, "STATUS %s raw=%d timeout=%d\n",
          test->name, test->status, test->expired);
  if (!ok) fprintf(stderr, "STATUS %s raw=%d timeout=%d\n",
                   test->name, test->status, test->expired);
  if (ferror(details) || ferror(stderr)) return -1;
  fclose(test->output);
  test->output = NULL;
  printf("%s %s\n", test->expired ? "TIMEOUT" : ok ? "PASS" : "FAIL",
         test->name);
  if (fflush(stdout)) return -1;
  return !ok;
}

int main(int argc, char **argv)
{
  FILE *list = NULL, *details = NULL;
  struct test *tests = NULL;
  struct sigaction action;
  struct rlimit core = {0, 0}, budget, child_limit;
  unsigned long jobs = 1, mib = 0;
  size_t count = 0, launched = 0, emitted = 0, running = 0, i;
  int arg = 1, failures = 0, result = 125, fields;
  char file[256], name[256];
  while (arg < argc - 1)
    {
      unsigned long value;
      if (arg + 1 >= argc - 1 || !number(argv[arg + 1], &value)) goto cleanup;
      if (!strcmp(argv[arg], "-j") && value <= INT_MAX) jobs = value;
      else if (!strcmp(argv[arg], "--limit-mb") && value <= 7168) mib = value;
      else goto cleanup;
      arg += 2;
    }
  if (arg != argc - 1 || getrlimit(RLIMIT_AS, &budget)) goto cleanup;
  child_limit = budget;
  if (mib) child_limit.rlim_cur = child_limit.rlim_max = (rlim_t)mib * 1024 * 1024;
  else if (jobs > 1 && budget.rlim_cur != RLIM_INFINITY)
    child_limit.rlim_cur = child_limit.rlim_max = budget.rlim_cur / jobs;
  /* Division avoids overflow, and uses the actual inherited reservation,
     never a caller's assertion of the ledger's memoryMB. Serial runs with no
     explicit limit retain their existing inherited limits, even if unlimited. */
  if ((jobs > 1 && !mib && budget.rlim_cur == RLIM_INFINITY)
      || child_limit.rlim_cur == 0
      || (budget.rlim_cur != RLIM_INFINITY
          && child_limit.rlim_cur > budget.rlim_cur / jobs))
    {
      fputs("claude-torture: memory budget cannot cover N times the per-program limit; "
            "set --limit-mb and sufficient job memoryMB\n", stderr);
      goto cleanup;
    }
  list = fopen(argv[arg], "r");
  if (!list) goto cleanup;
  /* Validate the complete list and memory budget before starting any child. */
  while ((fields = fscanf(list, "%255s %255s", file, name)) == 2)
    {
      struct test *more;
      if (strncmp(file, "claude-t-", 9) || strchr(file, '/')
          || strchr(file, '\\') || strstr(file, "..")) goto cleanup;
      more = realloc(tests, (count + 1) * sizeof *tests);
      if (!more) goto cleanup;
      tests = more;
      memset(&tests[count], 0, sizeof *tests);
      strcpy(tests[count].file, file);
      strcpy(tests[count].name, name);
      ++count;
    }
  if (fields != EOF || ferror(list) || !count) goto cleanup;
  fclose(list);
  list = NULL;
  details = fopen("claude-torture.details", "w");
  if (!details || setrlimit(RLIMIT_CORE, &core)) goto cleanup;
  memset(&action, 0, sizeof action);
  action.sa_handler = stop;
  sigemptyset(&action.sa_mask);
  if (sigaction(SIGTERM, &action, 0) || sigaction(SIGINT, &action, 0)
      || sigaction(SIGHUP, &action, 0)) goto cleanup;
  while (emitted < count && !stopped)
    {
      /* Bound buffered results as well as live children: a slow early test
         must not leave one open temporary file per remaining suite entry. */
      while (launched < count && running < jobs && launched - emitted < jobs
             && !stopped)
        {
          struct test *test = &tests[launched];
          char path[260];
          double start = now();
          if (start < 0 || !(test->output = tmpfile())) goto cleanup;
          snprintf(path, sizeof path, "./%s", test->file);
          test->pid = fork();
          if (test->pid < 0) { test->pid = 0; goto cleanup; }
          if (test->pid == 0)
            {
              if (setpgid(0, 0)
                  || ((mib || jobs > 1) && setrlimit(RLIMIT_AS, &child_limit))
                  || dup2(fileno(test->output), 1) < 0
                  || dup2(fileno(test->output), 2) < 0) _exit(126);
              for (i = 0; i <= launched; ++i)
                if (tests[i].output) close(fileno(tests[i].output));
              close(fileno(details));
              /* Restore normal program signal semantics after fork. */
              signal(SIGTERM, SIG_DFL);
              signal(SIGINT, SIG_DFL);
              signal(SIGHUP, SIG_DFL);
              execl(path, path, (char *)0);
              perror("exec");
              _exit(127);
            }
          ++launched;
          ++running;
          /* Either parent or child establishes the group before its deadline. */
          if (setpgid(test->pid, test->pid) && errno != EACCES && errno != ESRCH)
            goto cleanup;
          test->deadline = start + 2;
        }
      for (i = 0; i < launched; ++i)
        if (tests[i].pid > 0)
          {
            struct test *test = &tests[i];
            pid_t waited = waitpid(test->pid, &test->status, WNOHANG);
            double current;
            if (waited < 0 && errno == EINTR) continue;
            if (waited < 0) goto cleanup;
            if (waited == test->pid)
              {
                kill(-test->pid, SIGKILL); /* Only this test's descendants. */
                test->pid = 0;
                test->done = 1;
                --running;
              }
            else
              {
                current = now();
                if (current < 0) goto cleanup;
                if (current >= test->deadline)
                  {
                    test->expired = 1;
                    kill(-test->pid, SIGKILL);
                  }
              }
          }
      while (emitted < launched && tests[emitted].done)
        {
          int failed = report(&tests[emitted], details);
          if (failed < 0) goto cleanup;
          failures += failed;
          ++emitted;
        }
      if (running)
        {
          struct timespec pause = {0, 10000000};
          nanosleep(&pause, NULL);
        }
    }
  result = stopped ? 128 + stopped : failures != 0;
cleanup:
  /* Also cover driver errors and job TERM/HUP/INT, without orphaned groups. */
  for (i = 0; i < count; ++i)
    if (tests[i].pid > 0)
      {
        kill(-tests[i].pid, SIGKILL);
        kill(tests[i].pid, SIGKILL); /* Covers a failure before setpgid. */
      }
  for (i = 0; i < count; ++i)
    {
      if (tests[i].pid > 0)
        while (waitpid(tests[i].pid, NULL, 0) < 0 && errno == EINTR) {}
      if (tests[i].output) fclose(tests[i].output);
    }
  if (list) fclose(list);
  if (details && fclose(details)) result = 125;
  free(tests);
  return result;
}
