// S8-16: -mphinix, one flag for -O3 and the measured GCC-KNC defaults.
// tools/phinix.py drives this file: the -### expansion, .s identity with the
// expansion in docs/gcc-knc-flags.md, the banner and the progress bar.
// options: -mphinix

void
phinix_triad (float *restrict a, const float *restrict b,
              const float *restrict c, float s, int n)
{
  for (int i = 0; i < n; i++)
    a[i] = b[i] + s * c[i];
}

#ifdef KNC_PHINIX_WARN
#warning "phinix diagnostic"
#endif
#ifdef KNC_PHINIX_ERROR
#error "phinix error"
#endif
