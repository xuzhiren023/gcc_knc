/* S2-11 native runner acceptance. Build with the donor and shared sysroot. */
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>

int main(void)
{
    cpu_set_t cpus;
    int cpu;
    if (sched_getaffinity(0, sizeof cpus, &cpus))
        return 1;
    puts("hello from KNC");
    fputs("allowed logical CPUs:", stdout);
    for (cpu = 0; cpu < CPU_SETSIZE; ++cpu)
        if (CPU_ISSET(cpu, &cpus))
            printf(" %d", cpu);
    putchar('\n');
    return 0;
}
