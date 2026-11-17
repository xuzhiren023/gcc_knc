/* Fixed Q1/Q2 work is one corpus vote, with both exit statuses checked. */
#include <errno.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    const char *programs[] = {"./Q1-workload", "./Q2-workload"};
    for (unsigned i = 0; i < 2; ++i) {
        pid_t child = fork();
        int status;
        if (child < 0) return 2;
        if (child == 0) {
            execl(programs[i], programs[i], (char *)0);
            perror(programs[i]);
            _exit(127);
        }
        while (waitpid(child, &status, 0) < 0) {
            if (errno != EINTR) return 2;
        }
        if (!WIFEXITED(status)) return 2;
        if (WEXITSTATUS(status)) return WEXITSTATUS(status);
    }
    return 0;
}
