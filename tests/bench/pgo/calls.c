/* S9-18 kernel "calls": a generic open-addressing hash table whose hash and key compare are
   called through function pointers, then a lookup pass. Speed depends on whether the calls are
   inlined (after PGO's indirect-call promotion) and on keeping the rare grow path cold. Mix 0
   uses hash_a and 90% lookup hits; mix 1 (mismatched training only) uses hash_b and 10% hits.

   Built by tools/s9_18_pgo.py like skewed.c. */
#include <stdlib.h>
#include <string.h>
#include "pgo.h"

#define KEYS 2048
#define QUERIES 4096

struct key { unsigned w[4]; };
struct slot { struct key k; unsigned value, used; };
struct calls {
    int hash; /* 0: hash_a, 1: hash_b */
    struct key keys[KEYS], queries[QUERIES];
    struct slot *table; /* scratch, reset by every call */
    unsigned cap;
};

#ifdef SETUP
void *setup(int mix, unsigned seed)
{
    struct calls *c = malloc(sizeof *c);
    unsigned x = seed * 2654435761u + 1;
    if (!c)
        abort();
    c->hash = mix;
    for (int i = 0; i < KEYS + QUERIES; i++) {
        struct key *k = i < KEYS ? &c->keys[i] : &c->queries[i - KEYS];
        for (int j = 0; j < 4; j++) {
            x ^= x << 13, x ^= x >> 17, x ^= x << 5;
            k->w[j] = x;
        }
        if (i >= KEYS && x % 100 < (mix ? 10u : 90u))
            *k = c->keys[x % KEYS];
    }
    c->cap = 4 * KEYS;
    c->table = malloc(c->cap * sizeof *c->table);
    if (!c->table)
        abort();
    return c;
}
#else
typedef unsigned (*hash_fn)(const struct key *);
typedef int (*eq_fn)(const struct key *, const struct key *);

static unsigned hash_a(const struct key *k)
{
    unsigned h = 0x811c9dc5u;
    for (int j = 0; j < 4; j++)
        h = (h ^ k->w[j]) * 0x01000193u;
    return h ^ (h >> 15);
}

static unsigned hash_b(const struct key *k)
{
    unsigned h = k->w[0] * 0x9e3779b1u;
    h ^= k->w[1] + (h << 6) + (h >> 2);
    h ^= k->w[2] + (h << 6) + (h >> 2);
    h ^= k->w[3] + (h << 6) + (h >> 2);
    return h;
}

static int key_eq(const struct key *a, const struct key *b)
{
    return a->w[0] == b->w[0] && a->w[1] == b->w[1] && a->w[2] == b->w[2] && a->w[3] == b->w[3];
}

static hash_fn const hashes[2] = { hash_a, hash_b };
static eq_fn volatile eq_ptr = key_eq; /* keeps the compare an indirect call */

/* Rare: re-mark the occupied slots when the table looks too full (never at KEYS = cap / 4, but
   the compiler cannot know that). */
static void grow(struct slot *t, unsigned cap, hash_fn hash)
{
    for (unsigned i = 0; i < cap; i++)
        if (t[i].used == 2)
            t[i].used = 1, t[i].value ^= hash(&t[i].k);
}

static struct slot *find(struct slot *t, unsigned cap, const struct key *k, hash_fn hash, eq_fn eq)
{
    for (unsigned i = hash(k) & (cap - 1);; i = (i + 1) & (cap - 1))
        if (!t[i].used || eq(&t[i].k, k))
            return &t[i];
}

unsigned long NAME(const void *in)
{
    struct calls *c = (struct calls *)in;
    hash_fn hash = hashes[c->hash];
    eq_fn eq = eq_ptr;
    unsigned used = 0;
    unsigned long sum = 0;
    memset(c->table, 0, c->cap * sizeof *c->table);
    for (unsigned i = 0; i < KEYS; i++) {
        if (UNLIKELY(used * 2 > c->cap))
            grow(c->table, c->cap, hash);
        struct slot *s = find(c->table, c->cap, &c->keys[i], hash, eq);
        if (!s->used)
            s->k = c->keys[i], s->used = 1, used++;
        s->value = i;
    }
    for (unsigned i = 0; i < QUERIES; i++) {
        struct slot *s = find(c->table, c->cap, &c->queries[i], hash, eq);
        sum = sum * 31 + (LIKELY(s->used) ? s->value : 0xffffu);
    }
    return sum + used;
}
#endif
