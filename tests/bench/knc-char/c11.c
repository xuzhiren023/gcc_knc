/* S8-10 C11: what a line costs when it crosses the ring (E5-16).
   l2.local: one thread chases a random cycle of 2048 lines (128 KiB, above L1
   and inside L2) that it has just written; l2.remote.near/far: the same
   chase, but the lines were just written by a thread on another core, so
   every load is a cache-to-cache transfer from that core's L2.  Before each
   chase the reader reads a 64 KiB evict buffer, so no chased line is in its
   L1.  pingpong.shared/padded: threads on cores 0 and 1 increment their own
   counter, 8 bytes apart in one line or 64 bytes apart.  barrier.counter/
   tree: every worker (60x4 in the job) runs back-to-back barriers, a
   sense-reversing barrier on one shared counter versus a combining tree of
   fan-in 4 (one node per core, then per four nodes), one node per line,
   each waiter spinning on its own node.  Included by driver.c to reuse its
   pinning, barrier and policy helpers.  Remote "far" is core cores/2 by
   logical id; the logical id does not give the ring position. */

enum { C11_LINES = 2048, C11_EVICT = 64*1024, C11_EPISODES = 64,
       C11_INCREMENTS = 1 << 18, C11_BARRIERS = 2000, C11_CASES = 7 };
static const char *const c11_names[C11_CASES] = {
    "c11.l2.local", "c11.l2.remote.near", "c11.l2.remote.far",
    "c11.pingpong.shared", "c11.pingpong.padded",
    "c11.barrier.counter", "c11.barrier.tree"};
static const char *const c11_units[C11_CASES] = {
    "ns_per_load", "ns_per_load", "ns_per_load",
    "ns_per_increment", "ns_per_increment", "ns_per_barrier", "ns_per_barrier"};
static int c11_case;
static unsigned char *c11_lines, *c11_evict;
static size_t c11_order[C11_LINES];
/* One line per flag; the ping-pong counters sit in c11_pong. */
static struct { volatile int value; char pad[60]; } c11_flag[2] __attribute__((aligned(64)));
static volatile uint64_t c11_pong[16] __attribute__((aligned(64)));
static struct { int count, sense; char pad[56]; } c11_central __attribute__((aligned(64)));
static struct c11_node { int count, sense, fanin, parent; char pad[48]; }
    c11_tree[128] __attribute__((aligned(64)));
static int c11_leaf_of_core[61], c11_nodes;
static double c11_result[C11_EPISODES];

static int c11_owner(void) {
    return c11_case == 0 ? 0 : c11_case == 1 ? density : (cores/2)*density;
}
/* Write every line of the cycle: the owner's L2 then holds them modified. */
static void c11_write_cycle(void) {
    for (size_t i = 0; i < C11_LINES; ++i)
        *(unsigned char *volatile *)(c11_lines + 64*c11_order[i]) =
            c11_lines + 64*c11_order[(i+1) % C11_LINES];
}
static double c11_chase(void) {
    unsigned char *volatile *e = (unsigned char *volatile *)c11_evict;
    for (size_t i = 0; i < C11_EVICT/sizeof(*e); i += 64/sizeof(*e)) (void)e[i];
    unsigned char *p = c11_lines;
    uint64_t t0 = now();
    for (size_t i = 0; i < C11_LINES; ++i) p = *(unsigned char *volatile *)p;
    uint64_t t1 = now();
    if (p != c11_lines) fail("C11 cycle broken");
    return (double)(t1 - t0) / C11_LINES;
}
static void c11_wait_flag(int k, int value) {
    while (__atomic_load_n(&c11_flag[k].value, __ATOMIC_ACQUIRE) != value) {}
}
static void c11_l2(int id) {
    int owner = c11_owner(), reader = 0;
    for (int e = 0; e < C11_EPISODES; ++e) {
        if (id == owner) {
            if (e) c11_wait_flag(1, e);
            c11_write_cycle();
            __atomic_store_n(&c11_flag[0].value, e+1, __ATOMIC_RELEASE);
        }
        if (id == reader) {
            c11_wait_flag(0, e+1);
            c11_result[e] = c11_chase();
            __atomic_store_n(&c11_flag[1].value, e+1, __ATOMIC_RELEASE);
        }
    }
}
static void c11_pingpong(int id) {
    int slot = id == 0 ? 0 : id == density ? (c11_case == 3 ? 1 : 8) : -1;
    if (slot < 0) return;
    volatile uint64_t *counter = &c11_pong[slot];
    /* Both start together: each raises its flag and waits for the other. */
    __atomic_store_n(&c11_flag[slot != 0].value, 1, __ATOMIC_RELEASE);
    c11_wait_flag(slot == 0, 1);
    uint64_t t0 = now();
    for (unsigned i = 0; i < C11_INCREMENTS; ++i) ++*counter;
    uint64_t t1 = now();
    if (*counter != C11_INCREMENTS) fail("C11 counter lost an increment");
    c11_result[slot != 0] = (double)(t1 - t0) / C11_INCREMENTS;
}
static void c11_central_wait(int *local_sense) {
    *local_sense = !*local_sense;
    if (__atomic_fetch_add(&c11_central.count, 1, __ATOMIC_ACQ_REL) == cores*density - 1) {
        __atomic_store_n(&c11_central.count, 0, __ATOMIC_RELAXED);
        __atomic_store_n(&c11_central.sense, *local_sense, __ATOMIC_RELEASE);
    } else
        while (__atomic_load_n(&c11_central.sense, __ATOMIC_ACQUIRE) != *local_sense) {}
}
static void c11_tree_arrive(int n, int sense) {
    struct c11_node *node = &c11_tree[n];
    if (__atomic_fetch_add(&node->count, 1, __ATOMIC_ACQ_REL) == node->fanin - 1) {
        if (node->parent >= 0) c11_tree_arrive(node->parent, sense);
        __atomic_store_n(&node->count, 0, __ATOMIC_RELAXED);
        __atomic_store_n(&node->sense, sense, __ATOMIC_RELEASE);
    } else
        while (__atomic_load_n(&node->sense, __ATOMIC_ACQUIRE) != sense) {}
}
/* Leaves are cores (fan-in = siblings); each level groups four nodes. */
static void c11_tree_build(void) {
    int first = 0, count = cores;
    c11_nodes = cores;
    for (int c = 0; c < cores; ++c) {
        c11_leaf_of_core[c] = c;
        c11_tree[c] = (struct c11_node){0, 0, density, -1, {0}};
    }
    while (count > 1) {
        int parents = (count + 3) / 4;
        for (int i = 0; i < parents; ++i) {
            int fanin = count - 4*i < 4 ? count - 4*i : 4;
            c11_tree[c11_nodes + i] = (struct c11_node){0, 0, fanin, -1, {0}};
        }
        for (int i = 0; i < count; ++i) c11_tree[first + i].parent = c11_nodes + i/4;
        first = c11_nodes; c11_nodes += parents; count = parents;
    }
}
static void c11_barrier(int id) {
    int sense = 0;
    uint64_t t0 = now();
    for (int b = 0; b < C11_BARRIERS; ++b) {
        if (c11_case == 5) c11_central_wait(&sense);
        else { sense = !sense; c11_tree_arrive(c11_leaf_of_core[id/density], sense); }
    }
    uint64_t t1 = now();
    if (id == 0) c11_result[0] = (double)(t1 - t0) / C11_BARRIERS;
}
static void *c11_worker(void *arg) {
    struct worker *w = arg;
    pin(w->cpu);
    for (;;) {
        wait_all();
        if (stop) break;
        if (c11_case <= 2) c11_l2(w->id);
        else if (c11_case <= 4) c11_pingpong(w->id);
        else c11_barrier(w->id);
        wait_all();
    }
    return NULL;
}
static int c11_compare(const void *p, const void *q) {
    double a = *(const double *)p, b = *(const double *)q;
    return (a > b) - (a < b);
}

static int c11_main(int argc, char **argv) {
    int dry = 0, native = 0, only = -1;
    pthread_t threads[240];
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--dry-run")) dry = 1;
        else if (!strcmp(argv[i], "--native")) native = 1;
        else if ((!strcmp(argv[i], "--threads") || !strcmp(argv[i], "--cores") ||
                  !strcmp(argv[i], "--check") || !strcmp(argv[i], "--case")) && i+1 < argc) {
            const char *option = argv[i++], *value = argv[i];
            if (!strcmp(option, "--threads")) density = (int)number(value, 4);
            else if (!strcmp(option, "--cores")) cores = (int)number(value, 60);
            else if (!strcmp(option, "--case")) {
                for (int k = 0; k < C11_CASES; ++k)
                    if (!strcmp(value, c11_names[k])) only = k;
                if (only < 0) fail("unknown measurement name");
            }
            else if (strcmp(value, "c11")) fail("--check c11 takes no other check");
        } else fail("usage: --dry-run|--native --check c11 [--threads 1,2,4] [--cores 2..60] [--case NAME]");
    }
    if (dry == native) fail("choose exactly one execution mode");
    if (density == 3) fail("S8 excludes density 3");
    if (dry) {
        for (int k = 0; k < C11_CASES; ++k)
            if (only < 0 || only == k)
                printf("DRY %s cores=%d threads=%d unit=%s value=unmeasured\n",
                       c11_names[k], cores, density, c11_units[k]);
        return 0;
    }
#ifdef CHAR_HOST
    fail("host executable supports --dry-run only");
#endif
    if (cores < 2) fail("C11 needs --cores 2 or more");
    topology_read();
    policy(0);
    if (posix_memalign((void **)&c11_lines, 4096, 64*C11_LINES) ||
        posix_memalign((void **)&c11_evict, 4096, C11_EVICT)) fail("allocation");
    memset(c11_evict, 0, C11_EVICT);
    uint64_t state = 1234567;
    for (size_t i = 0; i < C11_LINES; ++i) c11_order[i] = i;
    for (size_t i = C11_LINES-1; i > 0; --i) {
        size_t j = random_next(&state) % (i+1), t = c11_order[i];
        c11_order[i] = c11_order[j]; c11_order[j] = t;
    }
    /* The cycle must start at line 0, which the chase starts from. */
    for (size_t i = 0; i < C11_LINES; ++i)
        if (!c11_order[i]) { c11_order[i] = c11_order[0]; c11_order[0] = 0; break; }
    c11_tree_build();
    if (pthread_barrier_init(&barrier, NULL, cores*density+1)) fail("barrier init");
    pthread_attr_t attr;
    if (pthread_attr_init(&attr) || pthread_attr_setstacksize(&attr, 256 * 1024)) fail("thread attributes");
    for (int i = 0; i < cores*density; ++i) {
        workers[i].id = i; workers[i].cpu = topology[i/density][i%density];
        printf("pin %d %d\n", i, workers[i].cpu);
        if (pthread_create(&threads[i], &attr, c11_worker, &workers[i])) fail("pthread_create");
    }
    for (int k = 0; k < C11_CASES; ++k) {
        double groups[GROUPS];
        if (only >= 0 && only != k) continue;
        c11_case = k;
        for (int g = 0; g < GROUPS; ++g) {
            c11_flag[0].value = c11_flag[1].value = 0;
            for (int s = 0; s < 16; ++s) c11_pong[s] = 0;
            wait_all(); wait_all();
            double value;
            if (k <= 2) {
                /* Median episode; the first episode is a warm-up. */
                qsort(c11_result + 1, C11_EPISODES - 1, sizeof(double), c11_compare);
                value = c11_result[C11_EPISODES/2];
            } else if (k <= 4) value = c11_result[0] > c11_result[1] ? c11_result[0] : c11_result[1];
            else value = c11_result[0];
            groups[g] = value;
            printf("c11_group name=%s group=%d value=%.3f unit=%s\n", c11_names[k], g, value, c11_units[k]);
        }
        qsort(groups, GROUPS, sizeof(double), c11_compare);
        int owner = k <= 2 ? c11_owner() : k <= 4 ? density : -1;
        printf("c11 name=%s cores=%d threads=%d reader_cpu=%d owner_cpu=%d value=%.3f unit=%s min=%.3f max=%.3f spread=%.6f\n",
               c11_names[k], cores, density, k <= 4 ? workers[0].cpu : -1,
               owner >= 0 ? workers[owner].cpu : -1, groups[GROUPS/2], c11_units[k],
               groups[0], groups[GROUPS-1], (groups[GROUPS-1] - groups[0]) / groups[GROUPS/2]);
        fflush(stdout);
    }
    stop = 1; wait_all();
    for (int i = 0; i < cores*density; ++i)
        if (pthread_join(threads[i], NULL)) fail("pthread_join");
    free(c11_lines); free(c11_evict);
    policy(1);
    return 0;
}
