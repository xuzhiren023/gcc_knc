/* S9-19: can our user sample with perf_event_open on the card (what AutoFDO needs)?
   For each event: open it on this thread, run a busy loop, then report the count and how many
   PERF_RECORD_SAMPLE records reached the ring buffer, with the first sampled IP.  Changes nothing:
   no sysctl, no root.  Exit 0 when the probe ran, whatever the answers. */
#define _GNU_SOURCE
#include <errno.h>
#include <linux/perf_event.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>

#define SAMPLE_BRANCH_STACK (1U << 11) /* not in this kernel's header; added in Linux 3.4 */
#define PAGES 8                        /* data pages of the ring buffer, a power of two */

static volatile unsigned long sink;

static void busy(void)
{
    for (unsigned long i = 0; i < 200000000UL; i++)
        sink += i & 7 ? i : 1;
}

static void probe(const char *name, uint32_t type, uint64_t config, uint64_t period,
                  uint64_t sample_type, int exclude_kernel)
{
    struct perf_event_attr a;
    memset(&a, 0, sizeof a);
    a.size = sizeof a;
    a.type = type;
    a.config = config;
    a.sample_period = period;
    a.sample_type = sample_type;
    a.disabled = 1;
    a.exclude_kernel = exclude_kernel;
    a.exclude_hv = 1;
    a.wakeup_events = 1;
    int fd = syscall(__NR_perf_event_open, &a, 0, -1, -1, 0);
    if (fd < 0) {
        printf("EVENT %s open=FAIL errno=%d (%s)\n", name, errno, strerror(errno));
        return;
    }
    long page = sysconf(_SC_PAGESIZE);
    void *ring = period ? mmap(0, page * (PAGES + 1), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)
                        : MAP_FAILED;
    ioctl(fd, PERF_EVENT_IOC_RESET, 0);
    ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
    busy();
    ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
    uint64_t count = 0;
    if (read(fd, &count, sizeof count) != sizeof count)
        count = 0;
    long samples = 0, other = 0;
    uint64_t ip = 0;
    if (ring != MAP_FAILED) {
        struct perf_event_mmap_page *m = ring;
        uint64_t head = m->data_head, tail = 0, size = page * PAGES;
        __sync_synchronize();
        const char *data = (const char *)ring + page;
        /* Only the first PAGES pages' worth survive; records may wrap, so stop at a wrap. */
        while (tail + sizeof(struct perf_event_header) <= head && head - tail <= size) {
            const struct perf_event_header *h = (const void *)(data + tail % size);
            if (h->size == 0 || tail % size + h->size > size)
                break;
            if (h->type == PERF_RECORD_SAMPLE) {
                if (!samples++ && (sample_type & PERF_SAMPLE_IP))
                    memcpy(&ip, h + 1, sizeof ip);
            } else {
                other++;
            }
            tail += h->size;
        }
        printf("EVENT %s open=ok count=%llu ring=ok bytes=%llu samples=%ld other_records=%ld "
               "first_ip=%#llx\n", name, (unsigned long long)count, (unsigned long long)head,
               samples, other, (unsigned long long)ip);
        munmap(ring, page * (PAGES + 1));
    } else {
        printf("EVENT %s open=ok count=%llu ring=%s\n", name, (unsigned long long)count,
               period ? "FAIL" : "none");
    }
    close(fd);
}

int main(void)
{
    uint64_t ip = PERF_SAMPLE_IP | PERF_SAMPLE_TID;
    probe("hw-cycles-count", PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES, 0, 0, 1);
    probe("hw-instructions-count", PERF_TYPE_HARDWARE, PERF_COUNT_HW_INSTRUCTIONS, 0, 0, 1);
    probe("hw-branches-count", PERF_TYPE_HARDWARE, PERF_COUNT_HW_BRANCH_INSTRUCTIONS, 0, 0, 1);
    probe("hw-cycles-sample-user", PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES, 1000003, ip, 1);
    probe("hw-cycles-sample-all", PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES, 1000003, ip, 0);
    probe("sw-cpu-clock-sample-user", PERF_TYPE_SOFTWARE, PERF_COUNT_SW_CPU_CLOCK, 100000, ip, 1);
    probe("hw-cycles-sample-branch-stack", PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES, 1000003,
          ip | SAMPLE_BRANCH_STACK, 1);
    printf("RESULT perf_probe ran\n");
    return 0;
}
