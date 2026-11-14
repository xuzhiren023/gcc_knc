#include "common.h"
#include <linux/perf_event.h>
#include <sys/syscall.h>
#include <sys/ioctl.h>
#include <fcntl.h>

struct reading { uint64_t value,enabled,running; };
static int event(uint64_t config,int group,int sampling) {
    struct perf_event_attr a; memset(&a,0,sizeof a);
    a.size=sizeof a; a.type=PERF_TYPE_HARDWARE; a.config=config;
    a.disabled=1; a.exclude_kernel=1; a.exclude_hv=1;
    a.read_format=PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING;
    if(sampling) { a.sample_period=100000; a.sample_type=PERF_SAMPLE_IP; a.wakeup_events=1; }
    errno=0; int fd=syscall(__NR_perf_event_open,&a,0,-1,group,0);
    printf("PERF_OPEN config=%llu group=%d sample=%d size=%u fd=%d errno=%d %s\n",
           (unsigned long long)config,group,sampling,a.size,fd,errno,strerror(errno));
    return fd;
}
static __attribute__((noipa)) uint64_t work(unsigned n) {
    uint64_t x=0;
    /* Exactly n adds, n decrements, n conditional branches, plus setup. */
    __asm__ volatile("1: addq $3,%0; subl $1,%1; jnz 1b":"+r"(x),"+r"(n)::"cc");
    return x;
}
static int command(int fd,unsigned long request,unsigned long arg) {
    errno=0; int rc=ioctl(fd,request,arg);
    if(rc) printf("PERF_IOCTL request=%lu rc=%d errno=%d %s\n",request,rc,errno,strerror(errno));
    return rc==0;
}
static int reading(int fd,struct reading *r,const char *label,unsigned n,double sec) {
    errno=0; ssize_t size=read(fd,r,sizeof *r);
    printf("COUNT label=%s n=%u read_bytes=%ld errno=%d value=%llu enabled=%llu running=%llu seconds=%.9f\n",
           label,n,(long)size,errno,(unsigned long long)r->value,(unsigned long long)r->enabled,(unsigned long long)r->running,sec);
    return size==sizeof *r && r->enabled && r->running==r->enabled && r->value;
}
int main(int argc,char **argv) {
    start("G06",1); dump("/proc/sys/kernel/perf_event_paranoid"); dump("/proc/modules");
    globdump("/sys/bus/event_source/devices/*/type");
    FILE *raw=fopen("claude-pmu-samples.bin","wb"); require(raw!=NULL,"sample output");
    int ins=event(PERF_COUNT_HW_INSTRUCTIONS,-1,0),cyc=-1,good=1;
    if(ins>=0) cyc=event(PERF_COUNT_HW_CPU_CYCLES,ins,0);
    if(ins<0||cyc<0) { if(ins>=0)close(ins); fclose(raw); result("G06","UNAVAILABLE"); return 0; }
    if(argc==2 && !strcmp(argv[1],"inventory")) {
        close(cyc); close(ins); fclose(raw); result("G06","PASS"); return 0;
    }
    uint64_t previous=0; double baseline=0;
    for(unsigned n=100000;n<=400000;n*=2) {
        struct reading ir={0},cr={0};
        good &= command(ins,PERF_EVENT_IOC_RESET,PERF_IOC_FLAG_GROUP);
        good &= command(ins,PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP);
        double t=now(); uint64_t value=work(n); t=now()-t;
        good &= command(ins,PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP);
        require(value==3ULL*n,"PMU known-work value"); sink=value;
        good &= reading(ins,&ir,"instructions",n,t); good &= reading(cyc,&cr,"cycles",n,t);
        /* Allow measurement setup; do not silently scale multiplexed counts. */
        if(ir.value<3ULL*n||ir.value>3ULL*n+30000) good=0;
        if(previous && (ir.value<previous*18/10||ir.value>previous*22/10)) good=0;
        previous=ir.value;
    }
    close(cyc); close(ins);
    if(!good) { fclose(raw); puts("QUALIFICATION counting_failed stop=1"); result("G06","UNAVAILABLE"); return 0; }
    for(int i=0;i<3;i++) { double t=now(); sink=work(400000); baseline+=now()-t; }
    printf("CALIBRATION uninstrumented_mean_seconds=%.9f\n",baseline/3);
    int fd=event(PERF_COUNT_HW_INSTRUCTIONS,-1,1);
    if(fd<0) { fclose(raw); result("G06","UNAVAILABLE"); return 0; }
    size_t page=(size_t)sysconf(_SC_PAGESIZE),bytes=page*65;
    struct perf_event_mmap_page *meta=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
    if(meta==MAP_FAILED) { printf("PERF_MMAP errno=%d %s\n",errno,strerror(errno)); close(fd); fclose(raw); result("G06","UNAVAILABLE"); return 0; }
    good=command(fd,PERF_EVENT_IOC_RESET,0)&&command(fd,PERF_EVENT_IOC_ENABLE,0);
    double t=now(); uint64_t value=work(400000); t=now()-t;
    good &= command(fd,PERF_EVENT_IOC_DISABLE,0); require(value==1200000,"sampled work");
    struct reading r={0}; good &= reading(fd,&r,"sampled_instructions",400000,t);
    __sync_synchronize(); uint64_t head=meta->data_head,tail=meta->data_tail;
    printf("SAMPLES head=%llu tail=%llu capacity=%zu period=100000 expected_approx=12 seconds=%.9f baseline_seconds=%.9f\n",
           (unsigned long long)head,(unsigned long long)tail,page*64,t,baseline/3);
    if(head<tail||head-tail>page*64||head==tail) good=0;
    else { unsigned char *data=(unsigned char*)meta+page;
        for(uint64_t i=tail;i<head;i++) require(fputc(data[i%(page*64)],raw)!=EOF,"sample write"); }
    require(!fclose(raw),"sample close"); munmap(meta,bytes); close(fd);
    puts("QUALIFICATION sampling_requires_host_decode_loss_and_perturbation_review=1 no_profiles_launched=1");
    result("G06",good?"PASS":"UNAVAILABLE"); return 0;
}
