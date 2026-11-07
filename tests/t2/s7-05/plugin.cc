/* No PT_GNU_EH_FRAME: explicitly register/deregister the plugin frame table.
   Source: libgcc/unwind-dw2-fde.c public __register_frame interface. */
#include <signal.h>
#include <unwind.h>
__asm__(".section .eh_frame,\"a\",@progbits\n"
        ".hidden plugin_eh_start\nplugin_eh_start:\n.previous");
extern "C" char plugin_eh_start[];
extern "C" void __register_frame(void *), __deregister_frame(void *);
__attribute__((constructor)) static void register_frames()
{ __register_frame(plugin_eh_start); }
__attribute__((destructor)) static void deregister_frames()
{ __deregister_frame(plugin_eh_start); }
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
