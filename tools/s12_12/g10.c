#include "common.h"
#include <malloc.h>
#define BLOCKS 128
#define BYTES 16384
static unsigned char *blocks[CPU_SETSIZE][BLOCKS];
static pthread_barrier_t gate;
static double times[CPU_SETSIZE][3];
static int serial_touch;
static void touch(int i) {
    for(int b=0;b<BLOCKS;b++) memset(blocks[i][b],(i+b)%251+1,BYTES);
}
static void barrier(void) {
    int rc=pthread_barrier_wait(&gate); require(!rc||rc==PTHREAD_BARRIER_SERIAL_THREAD,"barrier");
}
static void *worker(void *arg) {
    int i=(int)(intptr_t)arg; pin(cpus[i]);
    barrier(); double t=now();
    for(int b=0;b<BLOCKS;b++) { blocks[i][b]=malloc(BYTES); require(blocks[i][b]!=NULL,"malloc"); }
    times[i][0]=now()-t; barrier(); barrier();
    t=now(); if(!serial_touch) touch(i); times[i][1]=now()-t;
    barrier(); barrier();
    /* A different worker checks and frees: includes cross-thread lifetime. */
    int other=(i+1)%ncpu;
    for(int b=0;b<BLOCKS;b++) for(int j=0;j<BYTES;j++)
        require(blocks[other][b][j]==(other+b)%251+1,"allocator contents");
    barrier(); t=now();
    for(int b=0;b<BLOCKS;b++) free(blocks[other][b]);
    times[i][2]=now()-t; barrier(); return NULL;
}
int main(int argc,char **argv) {
    require(argc==4,"args: arena cap (0=ambient), touch mode (0=parallel 1=serial), workers (1 or all)");
    int cap=atoi(argv[1]); serial_touch=atoi(argv[2]);
    require((cap==0||cap==1||cap==8)&&(serial_touch==0||serial_touch==1),"cap/mode");
    start("G10",0);
    if(!strcmp(argv[3],"1")) { pin(cpus[0]); ncpu=1; }
    else require(!strcmp(argv[3],"all"),"worker mode");
    printf("ALLOCATOR online=%ld configured=%ld affinity_count=%d cap=%d serial_touch=%d env_arena=%s env_mmap=%s\n",
           sysconf(_SC_NPROCESSORS_ONLN),sysconf(_SC_NPROCESSORS_CONF),ncpu,cap,serial_touch,
           getenv("MALLOC_ARENA_MAX")?getenv("MALLOC_ARENA_MAX"):"unset",
           getenv("MALLOC_MMAP_THRESHOLD_")?getenv("MALLOC_MMAP_THRESHOLD_"):"unset");
    if(cap) require(mallopt(M_ARENA_MAX,cap)!=0,"mallopt arena cap");
    pthread_t th[CPU_SETSIZE]; pthread_attr_t attr;
    require(!pthread_attr_init(&attr),"attr init"); require(!pthread_attr_setstacksize(&attr,256*1024),"stack size");
    require(!pthread_barrier_init(&gate,NULL,ncpu+1),"barrier init");
    double startup=now();
    for(int i=0;i<ncpu;i++) require(!pthread_create(&th[i],&attr,worker,(void*)(intptr_t)i),"thread create");
    barrier(); printf("TIME thread_setup workers=%d seconds=%.9f\n",ncpu,now()-startup);
    barrier(); snapshot("allocated_before_touch");
    double t=now(); if(serial_touch) { pin(cpus[0]); for(int i=0;i<ncpu;i++) touch(i); }
    double serial_seconds=now()-t;
    barrier(); barrier(); snapshot("touched_before_free");
    for(int i=0;i<ncpu;i++) printf("MAPPING worker=%d first_block=%p total_bytes=%d\n",i,blocks[i][0],BLOCKS*BYTES);
    barrier(); barrier(); barrier();
    for(int i=0;i<ncpu;i++) { require(!pthread_join(th[i],NULL),"join"); printf("TIME allocator worker=%d cpu=%d alloc_seconds=%.9f touch_seconds=%.9f free_seconds=%.9f\n",i,cpus[i],times[i][0],times[i][1],times[i][2]); }
    printf("TIME serial_touch seconds=%.9f active=%d\n",serial_seconds,serial_touch);
    puts("MALLOC_INFO_BEGIN"); malloc_info(0,stdout); puts("MALLOC_INFO_END");
    pthread_attr_destroy(&attr); pthread_barrier_destroy(&gate);
    result("G10","PASS"); return 0;
}
