/* S11-01. Original endpoint/protocol code. Interface facts: installed MPSS
   sdk/include/scif.h (3.7); no vendor code or library is distributed here. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <arpa/inet.h>
#include <netinet/tcp.h>
#include <pthread.h>
#include <sched.h>
#ifdef __CYGWIN__
#include <windows.h>
typedef void *endpoint;
#define WALL_CLOCK CLOCK_MONOTONIC
static int *(*native_errno)(void);
#else
#include <dlfcn.h>
typedef int endpoint;
#define WALL_CLOCK CLOCK_MONOTONIC_RAW
#endif
#include "transfer_sha256.h"

/* ABI declarations are interface facts, written independently of the header. */
typedef struct { uint16_t node, port; } node_port;
static struct {
  endpoint (*open)(void);
  int (*close)(endpoint);
  int (*bind)(endpoint,uint16_t);
  int (*listen)(endpoint,int);
  int (*accept)(endpoint,node_port*,endpoint*,int);
  int (*connect)(endpoint,node_port*);
  int (*send)(endpoint,void*,int,int);
  int (*recv)(endpoint,void*,int,int);
  int64_t (*reg)(endpoint,void*,size_t,int64_t,int,int);
  int (*unreg)(endpoint,int64_t,size_t);
  int (*write)(endpoint,int64_t,size_t,int64_t,int);
  int (*read)(endpoint,int64_t,size_t,int64_t,int);
  int (*vwrite)(endpoint,void*,size_t,int64_t,int);
  void *(*map)(void*,size_t,int,int,endpoint,int64_t);
  int (*unmap)(void*,size_t);
  int (*nodes)(uint16_t*,int,uint16_t*);
} sc;
static int is_scif, fdin=0, fdout=1, opened, registered;
static endpoint ep;
static int64_t local_offset;
static size_t window_size;
static void *window;
static volatile sig_atomic_t cancelled;
static void stop(int n) { (void)n;cancelled=1; }
static void die(const char *s) { cancelled=1;fprintf(stderr,"ERROR %s (errno=%d)\n",s,errno);exit(2); }
static double now(clockid_t c)
{ struct timespec t;if(clock_gettime(c,&t))die("clock");return t.tv_sec+t.tv_nsec*1e-9; }
static void cleanup(void)
{
  /* All locally issued RMA is synchronous. Normal exit additionally exchanges
     DONE before unregistering. On error close the endpoint before releasing VA. */
  if(opened) {
    if(registered && !cancelled) {
      if(sc.unreg(ep,local_offset,window_size)) {
        fprintf(stderr,"ERROR unregister; cleanup uncertain\n");
        cancelled=1;sc.close(ep);_Exit(2);
      }
    }
    if(sc.close(ep)){fprintf(stderr,"ERROR close; cleanup uncertain\n");_Exit(2);}
    opened=0;
    if(cancelled)fprintf(stderr,"{\"endpoint_closed\":true}\n");
  }
  /* On abnormal shutdown leave the pages allocated until process teardown. */
  if(!cancelled) {
#ifdef __CYGWIN__
    if(window)VirtualFree(window,0,MEM_RELEASE);
#else
    free(window);
#endif
  }
}
static void scif_load(void)
{
#ifdef __CYGWIN__
  HMODULE lib=LoadLibraryExW(L"C:\\Windows\\System32\\uSCIF.dll",NULL,0);
#define RESOLVE(field,name) do { *(void **)(&sc.field)=(void *)GetProcAddress(lib,name); if(!sc.field)die(name); } while(0)
#else
  void *lib=dlopen("libscif.so.0",RTLD_NOW|RTLD_LOCAL);
#define RESOLVE(field,name) do { *(void **)(&sc.field)=dlsym(lib,name); if(!sc.field)die(name); } while(0)
#endif
  if(!lib)die("installed SCIF library unavailable");
#ifdef __CYGWIN__
  /* uSCIF imports MSVCR110: its errno is distinct from Cygwin's TLS errno. */
  *(void **)(&native_errno)=(void *)GetProcAddress(GetModuleHandleW(L"MSVCR110.dll"),"_errno");
  if(!native_errno)die("SCIF runtime errno unavailable");
#endif
  RESOLVE(open,"scif_open");RESOLVE(close,"scif_close");RESOLVE(bind,"scif_bind");
  RESOLVE(listen,"scif_listen");RESOLVE(accept,"scif_accept");RESOLVE(connect,"scif_connect");
  RESOLVE(send,"scif_send");RESOLVE(recv,"scif_recv");RESOLVE(reg,"scif_register");
  RESOLVE(unreg,"scif_unregister");RESOLVE(write,"scif_writeto");RESOLVE(read,"scif_readfrom");
  RESOLVE(vwrite,"scif_vwriteto");RESOLVE(map,"scif_mmap");RESOLVE(unmap,"scif_munmap");
  RESOLVE(nodes,"scif_get_nodeIDs");
#undef RESOLVE
}
static void exact(void *data,size_t n,int sending)
{
  unsigned char *p=data;double deadline=now(WALL_CLOCK)+120;
  while(n) {
    ssize_t done;
    if(cancelled)die("cancelled");
    if(is_scif) {
      int take=n>65536?65536:(int)n;
      /* Nonblocking messages permit a deadline and cooperative cancellation. */
      done=sending?sc.send(ep,p,take,0):sc.recv(ep,p,take,0);
#ifdef __CYGWIN__
      if(done<0)errno=*native_errno();
#endif
      if(done==0 || (done<0 && (errno==EAGAIN || errno==EWOULDBLOCK))) {
        if(now(WALL_CLOCK)>deadline){cancelled=1;die("SCIF message deadline");}
        usleep(100);continue;
      }
    } else done=sending?write(fdout,p,n):read(fdin,p,n);
    if(done<0 && errno==EINTR)continue;
    if(done<=0){cancelled=1;die("short/disconnected transport");}
    p+=done;n-=(size_t)done;
  }
}
static void token(char expected,int sending)
{ char x=expected;exact(&x,1,sending);if(x!=expected){cancelled=1;die("protocol token");} }
static uint64_t number(const char *s,uint64_t max)
{ char *end;errno=0;unsigned long long n=strtoull(s,&end,10);if(errno||!*s||*end||n>max)die("argument range");return n; }
static int tcp(const char *address,unsigned port,int server)
{
  struct sockaddr_in a;int s=socket(AF_INET,SOCK_STREAM,0),one=1;
  if(s<0)die("socket");
  memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons((uint16_t)port);
  if(inet_pton(AF_INET,address,&a.sin_addr)!=1)die("IPv4 address");
  if(server) {
    socklen_t n=sizeof(a);
    if(bind(s,(struct sockaddr*)&a,sizeof(a))||listen(s,1)||getsockname(s,(struct sockaddr*)&a,&n))die("listen");
    fprintf(stderr,"{\"ready\":true,\"port\":%u,\"node\":0}\n",ntohs(a.sin_port));fflush(stderr);
    int t=accept(s,NULL,NULL);close(s);s=t;if(s<0)die("accept");
  } else if(connect(s,(struct sockaddr*)&a,sizeof(a)))die("connect");
  struct timeval timeout={120,0};
  setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
  setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
  setsockopt(s,IPPROTO_TCP,TCP_NODELAY,&one,sizeof(one));return s;
}
static void connect_transport(const char *method,const char *address,unsigned port,int host)
{
  is_scif=!strncmp(method,"scif-",5);
  if(is_scif) {
    scif_load();ep=sc.open();
    if((intptr_t)ep==-1)die("scif_open");
    opened=1;
    if(host) {
      node_port peer;endpoint accepted;uint16_t self,nodes[32];
      int bound=sc.bind(ep,0);if(bound<0||sc.listen(ep,1))die("scif listen");
      if(sc.nodes(nodes,32,&self)<0)die("node enumeration");
      fprintf(stderr,"{\"ready\":true,\"port\":%d,\"node\":%u}\n",bound,self);fflush(stderr);
      if(sc.accept(ep,&peer,&accepted,1))die("scif accept");
      if(sc.close(ep))die("listener close; cleanup uncertain");
      ep=accepted;
      fprintf(stderr,"SCIF peer node=%u port=%u\n",peer.node,peer.port);
    } else {
      node_port target={(uint16_t)number(address,65535),(uint16_t)port};
      if(sc.connect(ep,&target)<0)die("scif connect");
    }
  } else if(strcmp(method,"pipe")) fdin=fdout=tcp(address,port,host);
}
static void affinity(const char *list)
{
#ifndef __CYGWIN__
  cpu_set_t set;char *copy=strdup(list),*p,*save=NULL;CPU_ZERO(&set);
  if(!copy)die("affinity allocation");
  for(p=strtok_r(copy,",",&save);p;p=strtok_r(NULL,",",&save))CPU_SET(number(p,CPU_SETSIZE-1),&set);
  free(copy);if(sched_setaffinity(0,sizeof(set),&set))die("affinity");
#else
  (void)list;
#endif
}
static void fill(unsigned char *p,size_t n,uint64_t offset,unsigned rep)
{
  /* Position-derived words: identical input regardless of transport chunk size. */
  for(size_t i=0;i<n;) {
    uint64_t x=((offset+i)>>3)+((uint64_t)rep<<32)+0x123456789abcdefULL;
    x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;x^=x>>31;
    for(unsigned j=0;j<8 && i<n;j++,i++)p[i]=(unsigned char)(x>>(8*j));
  }
}
static int trial(int host,const char *method,const char *direction,uint64_t size,unsigned reps,int corrupt)
{
  int sender=(!strcmp(direction,"up"))==host;
  int dma=is_scif && strcmp(method,"scif-msg");
  int read_mode=!strcmp(method,"scif-read"),map_mode=!strcmp(method,"scif-mmap");
  int vwrite=!strcmp(method,"scif-vwrite");
  uint64_t peer_offset=0;unsigned rep;
  window_size=size<64*1024*1024?size:64*1024*1024;
  window_size=(window_size+4095)&~(size_t)4095;
#ifdef __CYGWIN__
  window=VirtualAlloc(NULL,window_size,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
  if(!window)die("VirtualAlloc");
#else
  if(posix_memalign(&window,4096,window_size))die("aligned allocation");
#endif
  memset(window,0,window_size);
  if(dma) {
    local_offset=sc.reg(ep,window,window_size,0,3,0);
    if(local_offset<0)die("register");
    registered=1;
    uint64_t mine=(uint64_t)local_offset;
    if(host){exact(&mine,8,1);exact(&peer_offset,8,0);}
    else{exact(&peer_offset,8,0);exact(&mine,8,1);}
    if(peer_offset>INT64_MAX || (peer_offset&4095))die("remote window offset");
  }
  for(rep=0;rep<reps;rep++) {
    sha256 hash;unsigned char digest[32],peer_digest[32];char hex[65];
    uint64_t off;double elapsed=0,cpu=0,hash_seconds=0,started=now(WALL_CLOCK);
    sha_init(&hash);
    for(off=0;off<size;) {
      size_t n=size-off>window_size?window_size:(size_t)(size-off);
      if(sender) {
        fill(window,n,off,rep);double ht=now(WALL_CLOCK);sha_add(&hash,window,n);hash_seconds+=now(WALL_CLOCK)-ht;
        token('S',1);token('R',0);
      } else {memset(window,0xa5,n);token('S',0);token('R',1);}
      double ct=now(CLOCK_PROCESS_CPUTIME_ID),t=now(WALL_CLOCK);
      if(!dma)exact(window,n,sender);
      else if(read_mode || map_mode) {
        if(!sender) {
          if(read_mode) {if(sc.read(ep,local_offset,n,(int64_t)peer_offset,4))die("synchronous read");}
          else {
            void *mapped=sc.map(NULL,window_size,1,0,ep,(int64_t)peer_offset);
            if(mapped==(void*)-1 || !mapped)die("remote mmap");
            memcpy(window,mapped,n);if(sc.unmap(mapped,window_size))die("remote unmap");
          }
          token('D',1);
        } else token('D',0);
      } else {
        if(sender) {
          int result=vwrite?sc.vwrite(ep,window,n,(int64_t)peer_offset,4):sc.write(ep,local_offset,n,(int64_t)peer_offset,4);
          if(result)die("synchronous write");
          token('D',1);
        } else token('D',0);
      }
      /* Receiver completion is acknowledged before either hashes/reuses pages. */
      token('A',!sender);
      elapsed+=now(WALL_CLOCK)-t;cpu+=now(CLOCK_PROCESS_CPUTIME_ID)-ct;
      if(!sender) {
        if(corrupt && !off)((unsigned char*)window)[0]^=1;
        double ht=now(WALL_CLOCK);sha_add(&hash,window,n);hash_seconds+=now(WALL_CLOCK)-ht;
      }
      off+=n;
    }
    sha_end(&hash,digest);sha_hex(digest,hex);
    if(host){exact(digest,32,1);exact(peer_digest,32,0);}
    else{exact(peer_digest,32,0);exact(digest,32,1);}
    double remote_cpu,remote_seconds;
    if(host){exact(&remote_cpu,sizeof(double),0);exact(&remote_seconds,sizeof(double),0);}
    else{exact(&cpu,sizeof(double),1);exact(&elapsed,sizeof(double),1);remote_cpu=remote_seconds=0;}
    int match=!memcmp(digest,peer_digest,32);
    if(host) {
      fprintf(stderr,"{\"method\":\"%s\",\"direction\":\"%s\",\"bytes\":%"PRIu64",\"repeat\":%u,\"seconds\":%.9f,\"MiB_s\":%.6f,\"latency_us\":%.3f,\"host_cpu_seconds\":%.9f,\"card_cpu_seconds\":%.9f,\"card_seconds\":%.9f,\"host_hash_seconds\":%.9f,\"wall_seconds\":%.9f,\"sha256\":\"%s\",\"integrity\":\"%s\"}\n",
        method,direction,size,rep,elapsed,size/1048576.0/elapsed,elapsed*1e6,cpu,remote_cpu,remote_seconds,hash_seconds,now(WALL_CLOCK)-started,hex,match?"match":"mismatch");fflush(stderr);
    }
    if(!match){cancelled=1;fprintf(stderr,"ERROR integrity mismatch\n");return 3;}
  }
  /* Digest exchange proves both sides have stopped touching the windows.
     Release registrations before the endpoint-close handshake. */
  if(registered) {
    if(sc.unreg(ep,local_offset,window_size))die("unregister");
    registered=0;
  }
  if(host){
    token('Q',1);token('Q',0);token('Z',1);
    /* The peer exits only after consuming Z. No registered memory remains. */
    if(is_scif) {
      char c;double deadline=now(WALL_CLOCK)+120;
      for(;;) {
        int r=sc.recv(ep,&c,1,0);
#ifdef __CYGWIN__
        if(r<0)errno=*native_errno();
#endif
        if(r<0 && errno!=EAGAIN && errno!=EWOULDBLOCK)break;
        if(r>0||now(WALL_CLOCK)>deadline)die("close handshake");
        usleep(1000);
      }
    }
  }else{token('Q',0);token('Q',1);token('Z',0);}
  return 0;
}

/* Production files use the same bounded allocation and receiver-pull handshake
   as the S11-01 trial. The card listens; Windows only connects out. Neither
   endpoint publishes a pathname: the guarded Python policy does that after
   comparing both reports. Interface source: MPSS 3.7 scif.h RMA contracts. */
static void file_io(int fd,void *data,size_t size,int writing)
{
  unsigned char *p=data;
  while(size) {
    ssize_t n=writing?write(fd,p,size):read(fd,p,size);
    if(n<0 && errno==EINTR && !cancelled)continue;
    if(n<=0)die("integrity: short file IO");
    p+=n;size-=(size_t)n;
  }
}
static int transfer_file(int host,const char *method,const char *address,unsigned port,
                         const char *nonce,uint64_t size,const char *direction,const char *path)
{
  double started=now(WALL_CLOCK),elapsed=0,io_seconds=0;
  int sender=(!strcmp(direction,"up"))==host,dma=!strcmp(method,"scif-read");
  int fd=open(path,sender?(O_RDONLY|O_NOFOLLOW):(O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW),0600);
  struct stat st;
  if(fd<0 || fstat(fd,&st) || !S_ISREG(st.st_mode))die("regular transfer file");
  if(sender && (uint64_t)st.st_size!=size)die("integrity: source length");
  /* Reverse the benchmark's server role for production: the card listens. */
  connect_transport(method,address,port,!host);
  char auth[32];
  if(host){exact((void*)nonce,32,1);token('N',0);}
  else {exact(auth,32,0);if(memcmp(auth,nonce,32))die("nonce mismatch");token('N',1);}
  uint64_t agreed=size,peer_offset=0;
  if(host){exact(&agreed,8,1);token('L',0);}
  else {exact(&agreed,8,0);if(agreed!=size)die("integrity: declared length");token('L',1);}
  window_size=size<64*1024*1024?(size_t)size:64*1024*1024;
  if(!window_size)window_size=4096;
  window_size=(window_size+4095)&~(size_t)4095;
#ifdef __CYGWIN__
  window=VirtualAlloc(NULL,window_size,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
  if(!window)die("VirtualAlloc");
#else
  if(posix_memalign(&window,4096,window_size))die("aligned allocation");
#endif
  if(dma) {
    local_offset=sc.reg(ep,window,window_size,0,sender?1:2,0);
    if(local_offset<0)die("register");
    registered=1;
    uint64_t mine=(uint64_t)local_offset;
    if(host){exact(&mine,8,1);exact(&peer_offset,8,0);}
    else{exact(&peer_offset,8,0);exact(&mine,8,1);}
    /* MPSS 3.7 scif.h, scif_register: 2^62 bounds FIXED requests only.
       Driver-assigned windows may be higher; bound the final byte, not the
       file length. Every chunk reuses these same registered base offsets. */
    if(peer_offset>(uint64_t)INT64_MAX-(window_size-1) || (peer_offset&4095)) {
      fprintf(stderr,"SCIF remote offset=%"PRIu64" window=%zu\n",peer_offset,window_size);
      die("remote offset range");
    }
  }
  for(uint64_t off=0;off<size;) {
    size_t n=size-off>window_size?window_size:(size_t)(size-off);
    if(sender) {
      double io_started=now(WALL_CLOCK);
      file_io(fd,window,n,0);io_seconds+=now(WALL_CLOCK)-io_started;
      if(dma && (n&63))memset((unsigned char*)window+n,0,64-(n&63));
      token('S',1);token('R',0);
    } else {token('S',0);token('R',1);}
    double t=now(WALL_CLOCK);
    if(dma) {
      if(!sender) {
        /* RMA tails are cache-line aligned inside the page-rounded window;
           only the exact file bytes enter the destination file. */
        size_t dma_bytes=(n+63)&~(size_t)63;
        if(sc.read(ep,local_offset,dma_bytes,(int64_t)peer_offset,4))die("synchronous read");
        token('D',1);
      } else token('D',0);
    } else exact(window,n,sender);
    token('A',!sender);
    elapsed+=now(WALL_CLOCK)-t;
    if(!sender) {
      double io_started=now(WALL_CLOCK);
      file_io(fd,window,n,1);io_seconds+=now(WALL_CLOCK)-io_started;
    }
    off+=n;
  }
  if(sender) {
    unsigned char extra;ssize_t n=read(fd,&extra,1);
    if(n!=0 || fstat(fd,&st) || (uint64_t)st.st_size!=size)die("integrity: source length changed");
  } else if(fstat(fd,&st) || (uint64_t)st.st_size!=size)die("integrity: destination length");
  if(close(fd))die("file close");
  /* Both endpoints confirm exact length and completed file IO before unregister. */
  if(host){token('V',1);token('V',0);}else{token('V',0);token('V',1);}
  if(registered) {
    if(sc.unreg(ep,local_offset,window_size))die("unregister; cleanup uncertain");
    registered=0;
  }
  if(host){token('Q',1);token('Q',0);token('Z',1);}
  else{token('Q',0);token('Q',1);token('Z',0);}
  if(opened) {
    /* The client waits for the server's orderly close, as in S11-01. */
    if(host) {
      double deadline=now(WALL_CLOCK)+120;char c;
      for(;;) {
        int r=sc.recv(ep,&c,1,0);
#ifdef __CYGWIN__
        if(r<0)errno=*native_errno();
#endif
        if(r<0 && errno!=EAGAIN && errno!=EWOULDBLOCK)break;
        if(r>0 || now(WALL_CLOCK)>deadline)die("close handshake");
        usleep(1000);
      }
    }
    if(sc.close(ep))die("close; cleanup uncertain");
    opened=0;
  }
  fprintf(stderr,"{\"file_complete\":true,\"bytes\":%"PRIu64","
          "\"cleanup_confirmed\":true,\"seconds\":%.9f,\"wall_seconds\":%.9f,\"io_seconds\":%.9f}\n",
          size,elapsed,now(WALL_CLOCK)-started,io_seconds);
  return 0;
}

static int file_payload(int generate,const char *path,uint64_t size,unsigned seed)
{
  unsigned char *data=malloc(1048576),digest[32];char hex[65];sha256 hash;
  if(!data)die("file buffer");
  int fd=open(path,generate?(O_WRONLY|O_CREAT|O_TRUNC|O_NOFOLLOW):(O_RDONLY|O_NOFOLLOW),0600);
  if(fd<0)die("payload open");
  sha_init(&hash);
  for(uint64_t off=0;off<size;) {
    size_t n=size-off>1048576?1048576:(size_t)(size-off),done=0;
    if(generate)fill(data,n,off,seed);
    while(done<n) {
      ssize_t k=generate?write(fd,data+done,n-done):read(fd,data+done,n-done);
      if(k<0 && errno==EINTR)continue;
      if(k<=0)die("payload length");
      done+=(size_t)k;
    }
    sha_add(&hash,data,n);off+=n;
  }
  if(!generate){char extra;if(read(fd,&extra,1)!=0)die("excess payload");}
  if(close(fd))die("payload close");
  sha_end(&hash,digest);sha_hex(digest,hex);free(data);
  printf("{\"sha256\":\"%s\",\"bytes\":%"PRIu64"}\n",hex,size);return 0;
}
static int measure(char **args,const char *side)
{
  struct rusage usage;int status;double start=now(WALL_CLOCK);pid_t child=fork();
  if(child<0)die("fork");
  if(!child){execvp(args[0],args);_Exit(127);}
  if(wait4(child,&status,0,&usage)<0)die("wait4");
  double cpu=usage.ru_utime.tv_sec+usage.ru_utime.tv_usec*1e-6+usage.ru_stime.tv_sec+usage.ru_stime.tv_usec*1e-6;
  fprintf(stderr,"{\"event\":\"process-time\",\"side\":\"%s\",\"seconds\":%.9f,\"cpu_seconds\":%.9f}\n",side,now(WALL_CLOCK)-start,cpu);
  return WIFEXITED(status)?WEXITSTATUS(status):2;
}

#ifndef __CYGWIN__
static int busy,quit,active;
static pthread_mutex_t load_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t load_cond=PTHREAD_COND_INITIALIZER;
static void *burn(void *arg)
{
  cpu_set_t set;CPU_ZERO(&set);CPU_SET((intptr_t)arg,&set);
  if(pthread_setaffinity_np(pthread_self(),sizeof(set),&set))die("worker affinity");
  cpu_set_t actual;
  if(pthread_getaffinity_np(pthread_self(),sizeof(actual),&actual)||!CPU_EQUAL(&set,&actual))die("worker pin readback");
  volatile uint64_t x=1;
  while(!__atomic_load_n(&quit,__ATOMIC_RELAXED)) {
    pthread_mutex_lock(&load_mutex);
    while(!__atomic_load_n(&busy,__ATOMIC_RELAXED)&&!__atomic_load_n(&quit,__ATOMIC_RELAXED))pthread_cond_wait(&load_cond,&load_mutex);
    pthread_mutex_unlock(&load_mutex);
    __atomic_add_fetch(&active,1,__ATOMIC_RELAXED);
    while(__atomic_load_n(&busy,__ATOMIC_RELAXED)&&!__atomic_load_n(&quit,__ATOMIC_RELAXED)) {
      unsigned i;for(i=0;i<10000;i++)x=x*6364136223846793005ULL+1;
    }
    __atomic_sub_fetch(&active,1,__ATOMIC_RELAXED);
  }
  return NULL;
}
static int lease(const char *address,unsigned port,const char *nonce)
{
  cpu_set_t set;pthread_t threads[CPU_SETSIZE];unsigned n=0;int cpu;
  char cpus[4096]="",cwd[4096],line[9000];size_t used=0;
  if(sched_getaffinity(0,sizeof(set),&set)||!getcwd(cwd,sizeof(cwd)))die("lease affinity/cwd");
  /* The current guarded card_run directory has a simple ASCII name. */
  if(strncmp(cwd,"/tmp/claude/claude-",19)||strchr(cwd,'"'))die("not a card_run directory");
  for(cpu=0;cpu<CPU_SETSIZE;cpu++)if(CPU_ISSET(cpu,&set)) {
    used+=(size_t)snprintf(cpus+used,sizeof(cpus)-used,"%s%d",n?",":"",cpu);
    if(pthread_create(&threads[n++],NULL,burn,(void*)(intptr_t)cpu))die("busy worker");
  }
  if(n!=240)die("exclusive 240 CPU lease required");
  fdin=fdout=tcp(address,port,0);
  int len=snprintf(line,sizeof(line),"{\"nonce\":\"%s\",\"directory\":\"%s\",\"cpus\":\"%s\"}\n",nonce,cwd,cpus);
  exact(line,(size_t)len,1);
  for(;;){
    char c;exact(&c,1,0);if(c=='Q')break;
    if(c=='K'){exact(&c,1,1);continue;}
    if(c!='B'&&c!='I')die("lease command");
    pthread_mutex_lock(&load_mutex);
    __atomic_store_n(&busy,c=='B',__ATOMIC_RELAXED);pthread_cond_broadcast(&load_cond);
    pthread_mutex_unlock(&load_mutex);
    double deadline=now(WALL_CLOCK)+30;
    while(__atomic_load_n(&active,__ATOMIC_RELAXED)!=(c=='B'?240:0)) {
      if(now(WALL_CLOCK)>deadline)die("load state deadline");
      usleep(1000);
    }
    exact(&c,1,1);
  }
  pthread_mutex_lock(&load_mutex);
  __atomic_store_n(&quit,1,__ATOMIC_RELAXED);pthread_cond_broadcast(&load_cond);
  pthread_mutex_unlock(&load_mutex);
  for(unsigned j=0;j<n;j++)pthread_join(threads[j],NULL);
  token('Q',1);return 0;
}
#endif
int main(int argc,char **argv)
{
  signal(SIGPIPE,SIG_IGN);signal(SIGINT,stop);signal(SIGTERM,stop);atexit(cleanup);
  /* Availability probe deliberately opens no endpoint and registers no pages. */
  if(argc==2 && !strcmp(argv[1],"scif-probe")){scif_load();return 0;}
  if(argc==10 && !strcmp(argv[1],"file")) {
    int host=!strcmp(argv[2],"host");
    if(!host && strcmp(argv[2],"card"))die("file role");
    if(strcmp(argv[3],"pipe") && strcmp(argv[3],"scif-read"))die("file method");
    if(strlen(argv[6])!=32 || strspn(argv[6],"0123456789abcdef")!=32)die("nonce");
    if(strcmp(argv[8],"up") && strcmp(argv[8],"down"))die("direction");
    return transfer_file(host,argv[3],argv[4],(unsigned)number(argv[5],65535),argv[6],
                         number(argv[7],INT64_MAX),argv[8],argv[9]);
  }
#ifdef __CYGWIN__
  /* Native scp -S invokes this executable as its SSH client. The runner supplies
     a guarded, validated prefix, keeping the remote scp process measurable. */
  if(argc>2 && argv[1][0]=='-' && getenv("S11_SCP_PREFIX")) {
    const char *prefix=getenv("S11_SCP_PREFIX"),*original=argv[argc-1];
    if(strncmp(original,"scp ",4))die("unexpected SCP remote command");
    char **args=calloc((size_t)argc+1,sizeof(char*));
    char *remote=malloc(strlen(prefix)+strlen(original)+1);
    if(!args||!remote)die("SCP wrapper allocation");
    strcpy(remote,prefix);strcat(remote,original);
    args[0]="C:/Windows/System32/OpenSSH/ssh.exe";
    for(int i=1;i<argc;i++)args[i]=argv[i];
    args[argc-1]=remote;
    execv(args[0],args);die("exec SSH");
  }
#endif
  if(argc>=6 && !strcmp(argv[1],"measure")) {
    if(strcmp(argv[2],"host")&&strcmp(argv[2],"card"))die("measure side");
    if(strcmp(argv[3],"-"))affinity(argv[3]);
    if(strcmp(argv[4],"--"))die("measure separator");
    return measure(argv+5,argv[2]);
  }
  if(argc==6 && (!strcmp(argv[1],"generate")||!strcmp(argv[1],"inspect"))) {
    if(strcmp(argv[5],"-"))affinity(argv[5]);
    return file_payload(!strcmp(argv[1],"generate"),argv[2],number(argv[3],1073741824),(unsigned)number(argv[4],20));
  }
  if(argc==2 && !strcmp(argv[1],"selftest")) {
    sha256 s;unsigned char d[32];char h[65];sha_init(&s);sha_add(&s,"abc",3);sha_end(&s,d);sha_hex(d,h);
    if(strcmp(h,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"))return 1;
    puts("abc: match");return 0;
  }
#ifndef __CYGWIN__
  if(argc==5 && !strcmp(argv[1],"lease"))return lease(argv[2],(unsigned)number(argv[3],65535),argv[4]);
#endif
  if(argc<10 || argc>12)die("usage: host|card METHOD ADDRESS PORT NONCE BYTES REPEATS up|down [CPU_LIST] [corrupt]");
  int host=!strcmp(argv[1],"host");
  if(!host && strcmp(argv[1],"card"))die("role");
  const char *method=argv[2],*nonce=argv[5];
  if(strcmp(method,"tcp")&&strcmp(method,"pipe")&&strcmp(method,"scif-msg")&&strcmp(method,"scif-write")&&strcmp(method,"scif-read")&&strcmp(method,"scif-vwrite")&&strcmp(method,"scif-mmap")&&strncmp(method,"fake-",5))die("method");
  if(strlen(nonce)!=32||strspn(nonce,"0123456789abcdef")!=32)die("nonce");
  if(strcmp(argv[8],"up")&&strcmp(argv[8],"down"))die("direction");
  uint64_t size=number(argv[6],1073741824);unsigned reps=(unsigned)number(argv[7],20);
  if(!size||!reps)die("empty trial");
  if(!host && strcmp(argv[9],"-"))affinity(argv[9]);
  connect_transport(method,argv[3],(unsigned)number(argv[4],65535),host);
  char auth[32];
  if(host){exact(auth,32,0);if(memcmp(auth,nonce,32)){cancelled=1;die("nonce mismatch");}token('N',1);}
  else{exact((void*)nonce,32,1);token('N',0);}
  return trial(host,method,argv[8],size,reps,argc>10 && !strcmp(argv[10],"corrupt"));
}
