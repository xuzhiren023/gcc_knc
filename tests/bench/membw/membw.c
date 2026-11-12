/* S11-05. Original benchmark; instruction interfaces: Intel 327364,
   VMOVNRNGOAPS, VMOVNRAPS, VPREFETCH*, CLEVICT*. No vendor implementation. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#if defined(__linux__)
#include <linux/perf_event.h>
#include <sys/syscall.h>
#include <sys/vfs.h>
#include <setjmp.h>
#include <signal.h>
#endif

#if defined(__KNC__) || defined(__k1om__)
#define NATIVE 1
typedef float Vec __attribute__((vector_size(64)));
typedef uint32_t Uvec __attribute__((vector_size(64)));
#else
#define NATIVE 0
typedef struct { float v[16]; } Vec;
typedef struct { uint32_t v[16]; } Uvec;
#endif
#define INLINE static inline __attribute__((always_inline))
enum { READ, WRITE, COPY, TRIAD, RMW, STENCIL };
static const char *names[] = {"read", "write", "copy", "triad", "rmw", "stencil"};
static struct {
    size_t lines, chunk, offset, padding;
    int threads, repeats, passes, placement, pf0, pf1, prefetch;
    int store, fence, evict, huge, cyclic, unroll, split, workload, serial_touch;
} cfg = {4194304, 4096, 0, 0, 0, 5, 8, 1, 16, 32, 1,
         2, 0, 0, 0, 0, 4, 0, -1, 0};
static float *a, *b, *c;
static pthread_barrier_t barrier;
static int allowed, cpus[CPU_SETSIZE], actual_huge, current_workload;
static double elapsed[101], start_time;
static size_t map_bytes;
static void *mapping;
typedef struct __attribute__((aligned(64))) {
    int id, cpu, valid;
    Uvec sum;
} Worker;
static Worker workers[CPU_SETSIZE];

static void die(const char *why) { fprintf(stderr, "membw: %s (%s)\n", why, strerror(errno)); exit(2); }
static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) die("clock_gettime");
    return t.tv_sec + t.tv_nsec * 1e-9;
}
INLINE void fence(void) {
    int local = 0;
    __asm__ volatile("lock; addl $0,%0" : "+m"(local) : : "memory", "cc");
}
INLINE Vec load(const float *p) {
    Vec v;
#if NATIVE
    __asm__ volatile("vmovaps %1,%g0" : "=YJ"(v) : "m"(*(const Vec *)p));
#else
    memcpy(&v, p, 64);
    __asm__ volatile("" : "+m"(v));
#endif
    return v;
}
INLINE Vec add(Vec x, Vec y) {
#if NATIVE
    return x + y;
#else
    for (int j=0;j<16;j++) x.v[j] += y.v[j];
    return x;
#endif
}
INLINE Vec constant(float f) {
#if NATIVE
    return (Vec){f,f,f,f,f,f,f,f,f,f,f,f,f,f,f,f};
#else
    Vec v;
    for (int j=0;j<16;j++) ((float *)&v)[j] = f;
    return v;
#endif
}
INLINE void accumulate(Uvec *sum, Vec x) {
    Uvec u;
    memcpy(&u, &x, 64);
#if NATIVE
    *sum += u;
#else
    for (int j=0;j<16;j++) sum->v[j] += u.v[j];
#endif
}
INLINE void store(float *p, Vec v, int kind) {
#if NATIVE
    if (kind == 2) __asm__ volatile("vmovnrngoaps %g1,%0" : "=m"(*(Vec *)p) : "YJ"(v));
    else if (kind == 1) __asm__ volatile("vmovnraps %g1,%0" : "=m"(*(Vec *)p) : "YJ"(v));
    else __asm__ volatile("vmovaps %g1,%0" : "=m"(*(Vec *)p) : "YJ"(v));
#else
    (void)kind;
    memcpy(p, &v, 64);
    __asm__ volatile("" : "+m"(*(float (*)[16])p));
#endif
}
INLINE void prefetch(const float *p, int level, int exclusive) {
#if NATIVE
    if (exclusive) {
        if (level==0) __asm__ volatile("vprefetche0 %0" : : "m"(*(const Vec *)p));
        else if (level==1) __asm__ volatile("vprefetche1 %0" : : "m"(*(const Vec *)p));
        else __asm__ volatile("vprefetche2 %0" : : "m"(*(const Vec *)p));
    } else {
        if (level==0) __asm__ volatile("vprefetch0 %0" : : "m"(*(const Vec *)p));
        else if (level==1) __asm__ volatile("vprefetch1 %0" : : "m"(*(const Vec *)p));
        else __asm__ volatile("vprefetch2 %0" : : "m"(*(const Vec *)p));
    }
#else
    (void)p; (void)level; (void)exclusive;
#endif
}
/* A private snapshot: no configuration or global-pointer reads in line loops. */
typedef struct {
    float *a, *b, *c;
    size_t lines;
    int pf0, pf1, unroll, split;
} Kernel;
INLINE void hints(size_t i, int op, int sk, int pf, int checked, const Kernel *k) {
    if (!pf) return;
    for (int level=0;level<2;level++) {
        size_t distance = level ? k->pf1 : k->pf0;
        if (checked && (!distance || i + distance >= k->lines)) continue;
        size_t j = (i + distance)*16;
        int hint = pf == 3 && level ? 2 : level;
        if (op != WRITE) prefetch(k->a+j, hint, op==RMW && pf==2);
        if (op==TRIAD) prefetch(k->b+j, hint, 0);
        if (op!=READ && op!=RMW && sk==0 && pf==2)
            prefetch(k->c+j, hint, 1);
    }
}
INLINE void evict(float *p, int mode) {
#if NATIVE
    if (mode & 1) __asm__ volatile("clevict0 %0" : "+m"(*(Vec *)p));
    if (mode & 2) __asm__ volatile("clevict1 %0" : "+m"(*(Vec *)p));
#else
    (void)p; (void)mode;
#endif
}
enum { SPLIT_START=6, SPLIT_END };
INLINE void line(size_t i, int op, int sk, int pf, int lf, int ev, int checked,
                 Uvec *sum, const Kernel *k) {
    size_t j = i*16;
    Vec v;
    hints(i, op==SPLIT_START ? TRIAD : op, sk, pf, checked, k);
    if (op==READ) { accumulate(sum, load(k->a+j)); return; }
    if (op==WRITE) v = constant(7);
    else if (op==COPY) v = load(k->a+j);
    else if (op==TRIAD) { Vec y = load(k->b+j); v = add(load(k->a+j), add(y,y)); }
    else if (op==RMW) v = add(load(k->a+j),constant(1));
    else if (op==SPLIT_START) { Vec y=load(k->b+j); v=add(y,y); }
    else if (op==SPLIT_END) v=add(load(k->a+j),load(k->c+j));
    else v = add(add(load(k->a+j-16),load(k->a+j)),load(k->a+j+16));
    float *out = (op==RMW ? k->a : k->c) + j;
    store(out,v,sk);
    if (lf) fence();
    evict(out,ev);
}

/* Constant modes are selected once per chunk, never once per line. Keep named
   variants in the disassembly so the instruction budget can be inspected.
   Bound checks live in the array tail; unroll grouping remains runtime. */
#define ONE(J) line(i+(J),op,sk,pf,lf,ev,checked,sum,k)
INLINE void lines_loop(size_t lo, size_t hi, int op, int sk, int pf, int lf, int ev,
                       int checked, Uvec *sum, const Kernel *k) {
    size_t i=lo;
    const size_t unroll=k->unroll;
    for (; i+unroll<=hi; i+=unroll) {
        ONE(0); if (unroll>=2) { ONE(1); }
        if (unroll>=4) { ONE(2); ONE(3); }
        if (unroll==8) { ONE(4); ONE(5); ONE(6); ONE(7); }
    }
    for (;i<hi;i++) { ONE(0); }
}
#undef ONE
INLINE void lines(size_t lo, size_t hi, int op, int sk, int pf, int lf, int ev,
                  Uvec *sum, const Kernel *k) {
    if (!pf || (op==WRITE && !(sk==0 && pf==2))) {
        lines_loop(lo,hi,op,sk,pf,lf,ev,0,sum,k);
        return;
    }
    size_t end=lo;
    if (k->pf0 && k->pf1) {
        size_t distance=k->pf0>k->pf1 ? k->pf0 : k->pf1;
        end=k->lines>distance ? k->lines-distance : 0;
        if (end>hi) end=hi;
        if (end<lo) end=lo;
        lines_loop(lo,end,op,sk,pf,lf,ev,0,sum,k);
    }
    lines_loop(end,hi,op,sk,pf,lf,ev,1,sum,k);
}
#define VARIANT(OP,SK,PF,LF,EV) \
static __attribute__((noinline)) void kernel_##OP##_##SK##_##PF##_##LF##_##EV( \
    size_t lo, size_t hi, Uvec *sum, const Kernel *options) { \
    const Kernel k=*options; \
    if (OP==TRIAD && k.split) { \
        lines(lo,hi,SPLIT_START,0,PF,0,0,sum,&k); \
        lines(lo,hi,SPLIT_END,SK,0,LF,EV,sum,&k); \
    } else lines(lo,hi,OP,SK,PF,LF,EV,sum,&k); \
}
#define EVICTIONS(M,OP,SK,PF,LF) \
    M(OP,SK,PF,LF,0) M(OP,SK,PF,LF,1) M(OP,SK,PF,LF,2) M(OP,SK,PF,LF,3)
#define FENCES(M,OP,SK,PF) EVICTIONS(M,OP,SK,PF,0) EVICTIONS(M,OP,SK,PF,1)
#define PREFETCHES(M,OP,SK) \
    FENCES(M,OP,SK,0) FENCES(M,OP,SK,1) FENCES(M,OP,SK,2) FENCES(M,OP,SK,3)
#define STORES(M,OP) PREFETCHES(M,OP,0) PREFETCHES(M,OP,1) PREFETCHES(M,OP,2)
#define OPERATIONS(M) \
    STORES(M,READ) STORES(M,WRITE) STORES(M,COPY) \
    STORES(M,TRIAD) STORES(M,RMW) STORES(M,STENCIL)
OPERATIONS(VARIANT)
#define ENTRY(OP,SK,PF,LF,EV) kernel_##OP##_##SK##_##PF##_##LF##_##EV,
typedef void (*KernelFn)(size_t, size_t, Uvec *, const Kernel *);
static const KernelFn kernels[] = { OPERATIONS(ENTRY) };
#undef ENTRY
#undef VARIANT
#undef OPERATIONS
#undef STORES
#undef PREFETCHES
#undef FENCES
#undef EVICTIONS
static void kernel(size_t lo, size_t hi, int op, Uvec *sum) {
    const Kernel k={a,b,c,cfg.lines,cfg.pf0,cfg.pf1,cfg.unroll,cfg.split};
    const int store_kind=cfg.store, pf=cfg.prefetch, fm=cfg.fence, ev=cfg.evict;
    kernels[((((op*3+store_kind)*4+pf)*2+(fm==2))*4+ev)](lo,hi,sum,&k);
    if (fm==1) fence();
}
static float init_a(size_t k) { return (float)(1 + (k % 251)); }
static float init_b(size_t k) { return (float)(1 + (k % 127)); }
static void initialize(size_t lo, size_t hi) {
    for (size_t k=lo*16;k<hi*16;k++) { a[k]=init_a(k); b[k]=init_b(k); c[k]=-999; }
}
static int validate(size_t lo, size_t hi, int op, uint32_t expected[16]) {
    int valid=1;
    for (size_t k=lo*16;k<hi*16;k++) {
        float x=init_a(k), y=init_b(k), want=0;
        if (op==READ) { uint32_t bits; memcpy(&bits,&x,4); expected[k%16]+=bits*(uint32_t)cfg.passes; }
        if (op==WRITE) want=7;
        if (op==COPY) want=x;
        if (op==TRIAD) want=x+2*y;
        if (op==RMW) want=x+cfg.passes;
        if (op==STENCIL) want=(k<16?3:init_a(k-16))+x+(k+16>=cfg.lines*16?5:init_a(k+16));
        if (a[k] != (op==RMW?want:x) || b[k]!=y) valid=0;
        if (op!=RMW && op!=READ && c[k]!=want) valid=0;
        if ((op==RMW || op==READ) && c[k]!=-999) valid=0;
    }
    return valid;
}
static void ranges(Worker *w, int action) {
    size_t lo, end, step;
    if (cfg.cyclic) { lo=(size_t)w->id*cfg.chunk; end=cfg.lines; step=cfg.chunk*cfg.threads; }
    else { lo=cfg.lines*w->id/cfg.threads; end=cfg.lines*(w->id+1)/cfg.threads; step=cfg.chunk; }
    uint32_t expected[16]={0};
    for (;lo<end;lo+=step) {
        size_t hi=lo+cfg.chunk; if(hi>end) hi=end;
        if (action==0) initialize(lo,hi);
        else if (action==1) kernel(lo,hi,current_workload,&w->sum);
        else w->valid &= validate(lo,hi,current_workload,expected);
    }
    if (action==2 && current_workload==READ) {
        uint32_t sums[16]; memcpy(sums,&w->sum,64);
        for(int j=0;j<16;j++) if(sums[j]!=expected[j]) w->valid=0;
    }
}
static void *worker(void *arg) {
    Worker *w=arg;
    cpu_set_t set; CPU_ZERO(&set); CPU_SET(w->cpu,&set);
    int err=pthread_setaffinity_np(pthread_self(),sizeof(set),&set);
    if(err) { errno=err; die("pthread_setaffinity_np"); }
    for (int r=0;r<cfg.repeats;r++) {
        memset(&w->sum,0,64); w->valid=1;
        if (!cfg.serial_touch) ranges(w,0);
        else if(w->id==0) initialize(0,cfg.lines);
        pthread_barrier_wait(&barrier);
        if(w->id==0) start_time=now();
        pthread_barrier_wait(&barrier);
        for(int pass=0;pass<cfg.passes;pass++) { ranges(w,1); fence(); }
        pthread_barrier_wait(&barrier);
        if(w->id==0) elapsed[r]=now()-start_time;
        ranges(w,2);
        pthread_barrier_wait(&barrier);
        if(!w->valid) die("result validation failed; no bandwidth accepted");
    }
    return NULL;
}
static int number(const char *s, int max) {
    char *end; errno=0; long n=strtol(s,&end,10);
    if(errno || !*s || *end || n<0 || n>max) die("invalid numeric option");
    return (int)n;
}
static int choice(const char *s, const char *list) {
    int n=0; const char *p=list;
    while(*p) { const char *q=strchr(p,','); size_t len=q?(size_t)(q-p):strlen(p);
        if(strlen(s)==len && !strncmp(s,p,len)) return n;
        if(!q) break;
        p=q+1; n++;
    }
    die("invalid option value"); return -1;
}
static void parse(int argc,char **argv) {
    for(int i=1;i<argc;i+=2) {
        if(i+1>=argc) die("options require values; see README");
        const char *k=argv[i], *v=argv[i+1];
        if(!strcmp(k,"--workload")) cfg.workload=!strcmp(v,"all")?-1:choice(v,"read,write,copy,triad,rmw,stencil");
        else if(!strcmp(k,"--mib")) cfg.lines=(size_t)number(v,2048)*16384;
        else if(!strcmp(k,"--threads")) cfg.threads=number(v,CPU_SETSIZE);
        else if(!strcmp(k,"--repeats")) cfg.repeats=number(v,101);
        else if(!strcmp(k,"--passes")) cfg.passes=number(v,1024);
        else if(!strcmp(k,"--placement")) cfg.placement=choice(v,"compact,spread,reverse");
        else if(!strcmp(k,"--pf0")) cfg.pf0=number(v,4096);
        else if(!strcmp(k,"--pf1")) cfg.pf1=number(v,4096);
        else if(!strcmp(k,"--prefetch")) cfg.prefetch=choice(v,"none,shared,exclusive,l2");
        else if(!strcmp(k,"--store")) cfg.store=choice(v,"normal,nr,ngo");
        else if(!strcmp(k,"--fence")) cfg.fence=choice(v,"end,chunk,line");
        else if(!strcmp(k,"--evict")) cfg.evict=choice(v,"none,l1,l2,both");
        else if(!strcmp(k,"--pages")) cfg.huge=choice(v,"small,huge");
        else if(!strcmp(k,"--offset-lines")) cfg.offset=number(v,32768);
        else if(!strcmp(k,"--padding-lines")) cfg.padding=number(v,32768);
        else if(!strcmp(k,"--chunk-lines")) cfg.chunk=number(v,1048576);
        else if(!strcmp(k,"--schedule")) cfg.cyclic=choice(v,"block,cyclic");
        else if(!strcmp(k,"--unroll")) cfg.unroll=number(v,8);
        else if(!strcmp(k,"--split")) cfg.split=number(v,1);
        else if(!strcmp(k,"--first-touch")) cfg.serial_touch=choice(v,"parallel,serial");
        else die("unknown option");
    }
    if(!cfg.lines || !cfg.chunk || !cfg.passes || cfg.repeats<5 || !(cfg.repeats&1)
       || (cfg.unroll!=1 && cfg.unroll!=2 && cfg.unroll!=4 && cfg.unroll!=8)) die("invalid size/repeats/unroll");
}
static int topology(int cpu) {
    char path[160]; int id=-1;
    snprintf(path,sizeof(path),"/sys/devices/system/cpu/cpu%d/topology/core_id",cpu);
    FILE *f=fopen(path,"r");
    if(f) { if(fscanf(f,"%d",&id)!=1) id=-1; fclose(f); }
#if NATIVE
    if(id<0) die("core topology unavailable; cannot label placement");
#else
    if(id<0) id=cpu;
#endif
    return id;
}
static void affinity(void) {
    cpu_set_t mask; CPU_ZERO(&mask);
    if(sched_getaffinity(0,sizeof(mask),&mask)) die("sched_getaffinity");
    int ids[CPU_SETSIZE], core[CPU_SETSIZE], rank[CPU_SETSIZE];
    for(int i=0;i<CPU_SETSIZE;i++) if(CPU_ISSET(i,&mask)) {
        ids[allowed]=i; core[allowed]=topology(i); rank[allowed]=0;
        for(int j=0;j<allowed;j++) if(core[j]==core[allowed]) rank[allowed]++;
        allowed++;
    }
    if(!allowed || cfg.threads>allowed) die("thread count exceeds affinity");
    if(!cfg.threads) cfg.threads=allowed;
    for(int i=0;i<allowed;i++) cpus[i]=ids[i];
    if(cfg.placement==1) {
        int out=0;
        for(int r=0;r<allowed;r++) for(int i=0;i<allowed;i++) if(rank[i]==r) cpus[out++]=ids[i];
    } else if(cfg.placement==2) for(int i=0;i<allowed;i++) cpus[i]=ids[allowed-1-i];
}
#if defined(__linux__)
static sigjmp_buf huge_fault;
static void huge_bus_error(int signo) { (void)signo; siglongjmp(huge_fault,1); }
static int commit_huge_pages(void) {
    struct sigaction action, old;
    memset(&action,0,sizeof(action)); action.sa_handler=huge_bus_error;
    sigemptyset(&action.sa_mask);
    if(sigaction(SIGBUS,&action,&old)) die("SIGBUS handler");
    int okay=0;
    if(!sigsetjmp(huge_fault,1)) {
        for(size_t i=0;i<map_bytes;i+=2097152) ((volatile char *)mapping)[i]=0;
        okay=1;
    }
    if(sigaction(SIGBUS,&old,NULL)) die("restore SIGBUS handler");
    return okay;
}
#endif
static void allocate(void) {
    size_t stride=(cfg.lines+2+cfg.padding)*64;
    map_bytes=3*stride+2*cfg.offset*64+2097152;
    map_bytes=(map_bytes+2097151)&~(size_t)2097151;
    mapping=MAP_FAILED;
    if(cfg.huge) {
        char path[]="/mnt/huge/membw-XXXXXX";
        int fd=mkstemp(path);
        if(fd>=0) {
            unlink(path);
#if defined(__linux__)
            struct statfs fs;
            /* Old MPSS hugetlbfs need not implement fallocate. Check the mount,
               reserve with mmap, then fault one byte per huge page under a
               temporary SIGBUS handler before any threads exist. */
            if(!fstatfs(fd,&fs) && (unsigned long)fs.f_type==0x958458f6UL
               && !ftruncate(fd,map_bytes)) {
                mapping=mmap(NULL,map_bytes,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
                if(mapping!=MAP_FAILED) {
                    if(commit_huge_pages()) actual_huge=1;
                    else { munmap(mapping,map_bytes); mapping=MAP_FAILED; }
                }
            }
#endif
            close(fd);
        }
        if(!actual_huge) fprintf(stderr,"hugetlbfs allocation unavailable; using small pages\n");
    }
    if(mapping==MAP_FAILED) {
        mapping=mmap(NULL,map_bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        if(mapping==MAP_FAILED) die("mmap");
#ifdef MADV_NOHUGEPAGE
        if(madvise(mapping,map_bytes,MADV_NOHUGEPAGE) && errno!=EINVAL) die("MADV_NOHUGEPAGE");
#endif
    }
    a=(float *)((char *)mapping+64);
    b=(float *)((char *)a+stride+cfg.offset*64);
    c=(float *)((char *)b+stride+cfg.offset*64);
    for(int j=0;j<16;j++) { a[j-16]=3; a[cfg.lines*16+j]=5; }
}
static int cmp(const void *x,const void *y) {
    double a0=*(const double *)x,b0=*(const double *)y;
    return (a0>b0)-(a0<b0);
}
int main(int argc,char **argv) {
    if(argc==3 && !strcmp(argv[1],"--probe") && !strcmp(argv[2],"1")) {
#if defined(__linux__) && defined(__NR_perf_event_open)
        struct perf_event_attr attr;
        memset(&attr,0,sizeof(attr)); attr.size=sizeof(attr);
        attr.type=PERF_TYPE_HARDWARE; attr.config=PERF_COUNT_HW_CPU_CYCLES;
        attr.exclude_kernel=1; attr.exclude_hv=1;
        int fd=syscall(__NR_perf_event_open,&attr,0,-1,-1,0);
        if(fd<0) printf("core perf_event_open unavailable: errno=%d (%s)\n",errno,strerror(errno));
        else { printf("core cycles perf_event_open accessible; this does not measure GDDR bytes\n"); close(fd); }
#else
        puts("core perf_event_open probe unavailable in this build");
#endif
        puts("GBOX channel utilization/read-write mix requires registered GBOX PMUs, event encodings, transfer units and permission; see sweep probe PMU inventory. No core-miss proxy is reported as channel traffic.");
        return 0;
    }
    alarm(90); /* Whole invocation, including allocation and every workload. */
    parse(argc,argv); affinity(); allocate();
    printf("{\"kind\":\"config\",\"native\":%s,\"page_bytes\":%d,\"requested_huge\":%s,\"mapping_bytes\":%zu,\"counting\":\"decimal GB/s; logical reads+writes, excludes RFO and ECC; stencil counts 3 reads+1 write\"}\n",NATIVE?"true":"false",actual_huge?2097152:4096,cfg.huge?"true":"false",map_bytes);
    pthread_t threads[CPU_SETSIZE];
    if(pthread_barrier_init(&barrier,NULL,cfg.threads)) die("barrier init");
    for(int op=0;op<6;op++) {
        if(cfg.workload!=-1 && cfg.workload!=op) continue;
        current_workload=op;
        for(int t=0;t<cfg.threads;t++) {
            workers[t].id=t; workers[t].cpu=cpus[t];
            int err=pthread_create(&threads[t],NULL,worker,&workers[t]);
            if(err) { errno=err; die("pthread_create"); }
        }
        for(int t=0;t<cfg.threads;t++) if(pthread_join(threads[t],NULL)) die("pthread_join");
        const int streams[]={1,1,2,3,2,4};
        double bytes=(double)cfg.lines*64*cfg.passes*streams[op], rates[101];
        for(int r=0;r<cfg.repeats;r++) { if(elapsed[r]<=0) die("invalid timer"); rates[r]=bytes/elapsed[r]/1e9; }
        qsort(rates,cfg.repeats,sizeof(double),cmp);
        printf("{\"kind\":\"result\",\"workload\":\"%s\",\"valid\":true,\"samples\":%d,\"threads\":%d,\"allowed_cpus\":%d,\"min_GBs\":%.6f,\"median_GBs\":%.6f,\"max_GBs\":%.6f,\"logical_bytes\":%.0f,\"implementation_streams\":%d,\"cpus\":[",names[op],cfg.repeats,cfg.threads,allowed,rates[0],rates[cfg.repeats/2],rates[cfg.repeats-1],bytes,op==TRIAD&&cfg.split?5:streams[op]);
        for(int t=0;t<cfg.threads;t++) printf("%s%d",t?",":"",cpus[t]);
        puts("]}"); fflush(stdout);
    }
    pthread_barrier_destroy(&barrier); munmap(mapping,map_bytes);
    return 0;
}
