#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <dlfcn.h>
#include <link.h>
#include <pthread.h>
#include <signal.h>
#include <unistd.h>
#include <unwind.h>
struct Guard { int *p; explicit Guard(int *n):p(n){} ~Guard(){++*p;} };
static void check(bool ok,const char *s)
{ if(!ok) { fprintf(stderr,"FAIL %s\n",s); exit(1); } }
extern "C" void host_throw(int *n) { Guard guard(n); throw 91; }
struct Trace { uintptr_t lo[2], hi[2]; unsigned seen,depth; };
static _Unwind_Reason_Code trace(struct _Unwind_Context *ctx,void *arg)
{
  Trace *t=(Trace *)arg;
  uintptr_t ip=_Unwind_GetIP(ctx);
  ++t->depth;
  for(unsigned i=0;i<2;i++) if(ip>=t->lo[i] && ip<t->hi[i]) t->seen|=1U<<i;
  return _URC_NO_REASON;
}
/* Resolve function extents before raising the signal; the handler only
   collects unwind IPs and compares integer ranges. */
static Trace signal_trace;
static void handler(int,siginfo_t *,void *)
{ _Unwind_Backtrace(trace,&signal_trace); }
extern "C" __attribute__((noinline)) void signal_bridge(void (*fn)(void))
{ fn(); __asm__ volatile("" ::: "memory"); }
extern "C" __attribute__((noinline)) void backtrace_bridge(void (*fn)(_Unwind_Trace_Fn,void *),Trace *t)
{ fn(trace,t); __asm__ volatile("" ::: "memory"); }
static int ready_pipe[2], block_pipe[2], cancelled;
static void (*cancel_fn)(void (*)(int *),int *);
extern "C" void cancellation_point(int *n)
{
  Guard guard(n); char c='R';
  if(write(ready_pipe[1],&c,1)!=1) abort();
  if(read(block_pipe[0],&c,1)!=1) abort();
}
static void *worker(void *) { cancel_fn(cancellation_point,&cancelled); return 0; }
static void range(Trace *t,int i,void *fn)
{
  Dl_info info;
  const ElfW(Sym) *sym=0;
  check(dladdr1(fn,&info,(void **)&sym,RTLD_DL_SYMENT)!=0 && sym,"trace symbol lookup");
  t->lo[i]=(uintptr_t)fn; t->hi[i]=t->lo[i]+sym->st_size;
  check(t->hi[i]>t->lo[i],"trace function size");
}
int main(int argc,char **argv)
{
  check(argc==2,"explicit plugin path required");
  for(int pass=0;pass<3;pass++) {
    void *h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    check(h!=0,"dlopen plugin");
    void (*throws)(int *)=(void (*)(int *))dlsym(h,"plugin_throw");
    int (*catches)(void (*)(int *),int *)=(int (*)(void (*)(int *),int *))dlsym(h,"plugin_catch");
    void (*bt)(_Unwind_Trace_Fn,void *)=(void (*)(_Unwind_Trace_Fn,void *))dlsym(h,"plugin_backtrace");
    void (*sig)(void)=(void (*)(void))dlsym(h,"plugin_signal");
    cancel_fn=(void (*)(void (*)(int *),int *))dlsym(h,"plugin_cancel");
    check(throws && catches && bt && sig && cancel_fn,"plugin symbols");
    int n=0,caught=0;
    try { throws(&n); } catch(int x) { caught=x; }
    check(caught==73 && n==1,"DSO throw to host catch and cleanup");
    n=0; check(catches(host_throw,&n)==91 && n==2,"host throw to DSO catch and cleanups");
    if(!pass) puts("PASS cross DSO throw catch both directions");
    Trace t={};
    range(&t,0,(void *)bt); range(&t,1,(void *)backtrace_bridge);
    backtrace_bridge(bt,&t);
    check(t.seen==3 && t.depth>=4,"backtrace across DSO and host");
    if(!pass) puts("PASS backtrace across DSO");
    memset(&signal_trace,0,sizeof(signal_trace));
    range(&signal_trace,0,(void *)sig); range(&signal_trace,1,(void *)signal_bridge);
    struct sigaction sa={},old;
    sa.sa_sigaction=handler; sa.sa_flags=SA_SIGINFO; sigemptyset(&sa.sa_mask);
    check(sigaction(SIGUSR1,&sa,&old)==0,"signal install");
    signal_bridge(sig);
    check(sigaction(SIGUSR1,&old,0)==0,"signal restore");
    check(signal_trace.seen==3 && signal_trace.depth>=5,"signal trampoline unwind");
    if(!pass) puts("PASS signal unwind across trampoline and DSO");
    check(pipe(ready_pipe)==0 && pipe(block_pipe)==0,"cancellation pipes");
    pthread_t thread; void *result=0; char c;
    cancelled=0;
    check(pthread_create(&thread,0,worker,0)==0,"pthread create");
    check(read(ready_pipe[0],&c,1)==1,"worker ready");
    check(pthread_cancel(thread)==0 && pthread_join(thread,&result)==0,"cancel join");
    check(result==PTHREAD_CANCELED && cancelled==2,"forced unwind destructors across DSO");
    for(int i=0;i<2;i++) { close(ready_pipe[i]); close(block_pipe[i]); }
    if(!pass) puts("PASS pthread cancellation and two cleanups");
    check(dlclose(h)==0,"dlclose deregister frames");
  }
  puts("PASS three dlopen dlclose frame registration cycles");
  return 0;
}
