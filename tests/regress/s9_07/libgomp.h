/* S9-07 host test: what libgomp's affinity.c and proc.c use of libgomp.h, so that the k1om
   runtime's own two files compile into places.c on the host (Cygwin x86_64).  The names and
   types follow libgomp/libgomp.h.  The affinity calls and fopen are redirected to places.c,
   which stands in for the card: its mask is the inherited one and its files are the fixture
   tree's.  */
#ifndef S9_07_LIBGOMP_H
#define S9_07_LIBGOMP_H 1

#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#include <pthread.h>
#include <sched.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define HAVE_PTHREAD_AFFINITY_NP 1
#define attribute_hidden
#define ialias(fn)
#define gomp_alloca(x) __builtin_alloca (x)

struct gomp_task_icv
{
  unsigned long nthreads_var;
};

struct gomp_team_state
{
  unsigned place_partition_off;
  unsigned place_partition_len;
};

struct gomp_thread
{
  struct gomp_team_state ts;
  unsigned int place;
};

/* Which environment variables were given: OMP_NUM_THREADS sets GOMP_ICV_NTHREADS on the
   no-suffix item.  */
enum gomp_icvs
{
  GOMP_ICV_NTHREADS = 7
};

enum gomp_device_num
{
  GOMP_DEVICE_NUM_FOR_ALL = -2,
  GOMP_DEVICE_NUM_FOR_NO_SUFFIX = -3
};

struct gomp_icv_list
{
  uint32_t flags;
};

extern struct gomp_task_icv gomp_global_icv;
extern unsigned long gomp_available_cpus;
extern void **gomp_places_list;
extern unsigned long gomp_places_list_len;

extern struct gomp_thread *gomp_thread (void);
extern struct gomp_task_icv *gomp_icv (bool);
extern struct gomp_icv_list *gomp_get_initial_icv_item (int);
extern bool gomp_get_icv_flag (uint32_t, enum gomp_icvs);
extern void *gomp_malloc (size_t);
extern void *gomp_realloc (void *, size_t);
extern void gomp_error (const char *, ...);
extern void gomp_display_string (char *, size_t, size_t *, const char *, size_t);

extern void gomp_init_num_threads (void);
extern void gomp_init_affinity (void);
extern void gomp_init_thread_affinity (pthread_attr_t *, unsigned int);
extern void **gomp_affinity_alloc (unsigned long, bool);
extern void gomp_affinity_init_place (void *);
extern bool gomp_affinity_add_cpus (void *, unsigned long, unsigned long,
				    long, bool);
extern bool gomp_affinity_remove_cpu (void *, unsigned long);
extern bool gomp_affinity_copy_place (void *, void *, long);
extern bool gomp_affinity_same_place (void *, void *);
extern bool gomp_affinity_finalize_place_list (bool);
extern bool gomp_affinity_init_level (int, unsigned long, bool);
extern void gomp_affinity_print_place (void *);
extern void gomp_get_place_proc_ids_8 (int, int64_t *);
extern void gomp_display_affinity_place (char *, size_t, size_t *, int);
extern unsigned gomp_dynamic_max_threads (void);
extern int omp_get_num_procs (void);
extern int omp_get_place_num_procs (int);

extern int test_getaffinity (size_t, cpu_set_t *);
extern int test_setaffinity (size_t, const cpu_set_t *);
extern FILE *test_fopen (const char *, const char *);

#define pthread_getaffinity_np(thread, size, set) test_getaffinity (size, set)
#define pthread_setaffinity_np(thread, size, set) test_setaffinity (size, set)
#define pthread_attr_setaffinity_np(attr, size, set) test_setaffinity (size, set)
#define fopen(name, mode) test_fopen (name, mode)

#endif /* S9_07_LIBGOMP_H */
