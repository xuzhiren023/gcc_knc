/* S2-06: exercise scalar atomics and the out-of-line TI fallbacks. */
#define PROBE(N, T) \
T atomic_load_##N(T *p) { return __atomic_load_n(p, __ATOMIC_SEQ_CST); } \
void atomic_store_##N(T *p, T v) { __atomic_store_n(p, v, __ATOMIC_SEQ_CST); } \
T atomic_exchange_##N(T *p, T v) { return __atomic_exchange_n(p, v, __ATOMIC_SEQ_CST); } \
T atomic_add_##N(T *p, T v) { return __atomic_fetch_add(p, v, __ATOMIC_SEQ_CST); } \
int atomic_cas_##N(T *p, T *e, T v) { return __atomic_compare_exchange_n(p, e, v, 0, __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST); } \
T sync_add_##N(T *p, T v) { return __sync_fetch_and_add(p, v); } \
T sync_cas_##N(T *p, T e, T v) { return __sync_val_compare_and_swap(p, e, v); } \
T sync_lock_##N(T *p, T v) { return __sync_lock_test_and_set(p, v); } \
void sync_unlock_##N(T *p) { __sync_lock_release(p); }
PROBE(1, unsigned char)
PROBE(2, unsigned short)
PROBE(4, unsigned int)
PROBE(8, unsigned long long)
PROBE(16, unsigned __int128)
void fences(void)
{
  __atomic_thread_fence(__ATOMIC_ACQUIRE);
  __atomic_thread_fence(__ATOMIC_RELEASE);
  __atomic_thread_fence(__ATOMIC_SEQ_CST);
  __sync_synchronize();
}
