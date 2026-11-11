/* S9-18 kernel "skewed": a hot loop with a data-dependent branch that goes one way 95% of the
   time (mix 0) and a heavier rare path. Mix 1, used only to train the mismatched profile, makes
   the rare path the common one.

   Built by tools/s9_18_pgo.py: with -DSETUP for the input generator (once, plain -O2), otherwise
   as the kernel NAME with LIKELY/UNLIKELY from pgo.h (HINT=0 none, 1 right, -1 wrong). */
#include <stdlib.h>
#include "pgo.h"

#define N 16384
#define RARE 1000000u /* values at or above this take the rare path */

struct skewed { unsigned a[N]; };

#ifdef SETUP
void *setup(int mix, unsigned seed)
{
    struct skewed *s = malloc(sizeof *s);
    unsigned x = seed * 2654435761u + 1;
    if (!s)
        abort();
    for (int i = 0; i < N; i++) {
        x ^= x << 13, x ^= x >> 17, x ^= x << 5;
        int rare = x % 100 < (mix ? 95u : 5u);
        s->a[i] = rare ? RARE + (x >> 8) % 4096 : (x >> 8) % 1000;
    }
    return s;
}
#else
/* The rare path: a short dependent loop, big enough that inlining it into the hot loop costs
   code size and register pressure. */
static unsigned rare(unsigned v, unsigned h)
{
    for (unsigned k = 0; k < 8 + (v & 7); k++)
        h = (h ^ (v >> (k & 15))) * 0x01000193u + k;
    return h;
}

unsigned long NAME(const void *in)
{
    const struct skewed *s = in;
    unsigned h = 0x811c9dc5u;
    unsigned long sum = 0;
    for (int i = 0; i < N; i++) {
        unsigned v = s->a[i];
        if (UNLIKELY(v >= RARE))
            h = rare(v, h);
        else
            h = (h ^ v) * 3 + (h >> 5);
        sum += h;
    }
    return sum;
}
#endif
