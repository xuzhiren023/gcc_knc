/* Both the explicit builtin and a spin-wait loop must use DELAY. */
void spin_hint(void) { __builtin_ia32_pause(); }
void spin_wait(unsigned int *p)
{
  while (__atomic_load_n(p, __ATOMIC_ACQUIRE) == 0)
    __builtin_ia32_pause();
}
