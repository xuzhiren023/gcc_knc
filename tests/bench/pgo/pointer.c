/* S9-18 kernel "pointer": a walk over a singly linked list scattered through a node pool, checking
   each node's tag and taking an error path (a recovery that formats a message) when the tag is
   bad. Mix 0 has one bad node in 1000; mix 1 (mismatched training only) one in three.

   Built by tools/s9_18_pgo.py like skewed.c. */
#include <stdio.h>
#include <stdlib.h>
#include "pgo.h"

#define NODES 8192
#define TAG 0x4b4e43u

struct node { struct node *next; unsigned tag, value; };
struct pointer { struct node *head; char log[64]; struct node pool[NODES]; };

#ifdef SETUP
void *setup(int mix, unsigned seed)
{
    struct pointer *p = malloc(sizeof *p);
    static unsigned order[NODES];
    unsigned x = seed * 2654435761u + 1;
    if (!p)
        abort();
    for (unsigned i = 0; i < NODES; i++)
        order[i] = i;
    for (unsigned i = NODES - 1; i > 0; i--) {
        x ^= x << 13, x ^= x >> 17, x ^= x << 5;
        unsigned j = x % (i + 1), t = order[i];
        order[i] = order[j], order[j] = t;
    }
    for (unsigned i = 0; i < NODES; i++) {
        struct node *n = &p->pool[order[i]];
        x ^= x << 13, x ^= x >> 17, x ^= x << 5;
        n->next = i + 1 < NODES ? &p->pool[order[i + 1]] : NULL;
        n->tag = x % (mix ? 3u : 1000u) ? TAG : x >> 8;
        n->value = x >> 4;
    }
    p->head = &p->pool[order[0]];
    return p;
}
#else
/* The error path: format the bad node into the log and derive a replacement value. */
static unsigned recover(struct pointer *p, const struct node *n, unsigned long seen)
{
    int len = snprintf(p->log, sizeof p->log, "bad tag %#x at node %lu", n->tag, seen);
    return (unsigned)len + (unsigned char)p->log[len - 1];
}

unsigned long NAME(const void *in)
{
    struct pointer *p = (struct pointer *)in;
    unsigned long sum = 0, seen = 0;
    for (const struct node *n = p->head; n; n = n->next, seen++) {
        if (UNLIKELY(n->tag != TAG))
            sum += recover(p, n, seen);
        else
            sum = sum * 33 + n->value;
    }
    return sum + seen;
}
#endif
