/* S2-08: one card job, bounded child process groups, one result per test.
   POSIX fork/exec/wait/alarm; children inherit card_run's affinity and limits. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static volatile sig_atomic_t child_pid, expired;
static void deadline(int signal_number)
{
  (void)signal_number;
  expired = 1;
  if (child_pid > 0) kill(-(pid_t)child_pid, SIGKILL);
}

int main(int argc, char **argv)
{
  FILE *list;
  char file[256], name[256], path[260];
  struct sigaction action;
  struct rlimit core = {0, 0};
  int details, failures = 0, count = 0;
  if (argc != 2 || !(list = fopen(argv[1], "r"))) return 125;
  details = open("claude-torture.details", O_RDWR | O_CREAT | O_TRUNC, 0600);
  if (details < 0) return 125;
  setrlimit(RLIMIT_CORE, &core);
  memset(&action, 0, sizeof action);
  action.sa_handler = deadline;
  sigemptyset(&action.sa_mask);
  if (sigaction(SIGALRM, &action, 0)) return 125;
  while (fscanf(list, "%255s %255s", file, name) == 2)
    {
      pid_t pid, waited;
      int status = 0, ok;
      off_t start = lseek(details, 0, SEEK_CUR);
      if (strncmp(file, "claude-t-", 9) || strchr(file, '/')
          || strchr(file, '\\') || strstr(file, "..")) return 125;
      snprintf(path, sizeof path, "./%s", file);
      dprintf(details, "TEST %s\n", name);
      expired = 0;
      pid = fork();
      if (pid < 0) return 125;
      if (pid == 0)
        {
          if (setpgid(0, 0) || dup2(details, 1) < 0 || dup2(details, 2) < 0)
            _exit(126);
          close(details);
          fclose(list);
          execl(path, path, (char *)0);
          perror("exec");
          _exit(127);
        }
      /* Either parent or child establishes the group before its deadline. */
      if (setpgid(pid, pid) && errno != EACCES && errno != ESRCH) return 125;
      child_pid = pid;
      alarm(2);
      do waited = waitpid(pid, &status, 0); while (waited < 0 && errno == EINTR);
      alarm(0);
      kill(-pid, SIGKILL); /* Clean up only this test's descendants. */
      child_pid = 0;
      if (waited != pid) return 125;
      ok = !expired && WIFEXITED(status) && WEXITSTATUS(status) == 0;
      printf("%s %s\n", expired ? "TIMEOUT" : ok ? "PASS" : "FAIL", name);
      fflush(stdout);
      dprintf(details, "STATUS %s raw=%d timeout=%d\n", name, status, (int)expired);
      if (!ok)
        {
          char buffer[4096];
          ssize_t bytes;
          /* Preserve failing diagnostics before card_run removes the job dir. */
          while ((bytes = pread(details, buffer, sizeof buffer, start)) > 0)
            {
              ssize_t offset = 0, written;
              while (offset < bytes)
                {
                  written = write(2, buffer + offset, bytes - offset);
                  if (written < 0 && errno == EINTR) continue;
                  if (written <= 0) return 125;
                  offset += written;
                }
              start += bytes;
            }
          if (bytes < 0) return 125;
        }
      failures += !ok;
      ++count;
    }
  if (ferror(list) || !count) return 125;
  fclose(list);
  close(details);
  return failures != 0;
}
