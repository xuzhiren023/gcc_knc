/* No PT_GNU_EH_FRAME: donor crtbeginS/crtendS register and deregister frames. */
#include <signal.h>
#include <unwind.h>
struct Guard { int *p; explicit Guard(int *n):p(n){} ~Guard(){++*p;} };
extern "C" void plugin_throw(int *n)
{ Guard guard(n); throw 73; }
extern "C" int plugin_catch(void (*call)(int *),int *n)
{ Guard guard(n); try { call(n); } catch(int x) { return x; } return -1; }
extern "C" void plugin_cancel(void (*call)(int *),int *n)
{ Guard guard(n); call(n); }
extern "C" __attribute__((noinline)) void plugin_signal(void)
{ raise(SIGUSR1); __asm__ volatile("" ::: "memory"); }
extern "C" __attribute__((noinline)) void plugin_backtrace(_Unwind_Trace_Fn cb,void *p)
{ _Unwind_Backtrace(cb,p); __asm__ volatile("" ::: "memory"); }
