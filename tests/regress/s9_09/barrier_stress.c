/* S9-09 host stress test of the KNC team barrier (libgomp/config/linux/knc/bar.h, bar.c), which
   compile into this file unchanged on the host (Cygwin x86_64, tools/s9_09_checks.py host).

       barrier_stress MODE [BARRIERS [NCORES [THREADS]]]

   THREADS (240) pthreads pass BARRIERS (100000) barriers in gomp_knc_ncores = NCORES (60) groups.
   A thread that leaves barrier K checks that the root generation is K * BAR_INCR and that every
   thread arrived K times.  MODE:
     plain       gomp_barrier_wait, gomp_team_barrier_wait and gomp_team_barrier_wait_final in
                 turn; a third of the threads sleep at once, the others after a short spin.
     tasks-park  every waiter sleeps in futex_wait on its group word.  A late thread waits for all
                 of them to sleep, queues a task the way task.c does (set_task_pending under the
                 task lock, then gomp_team_barrier_wake (bar, 1)) and waits for a sleeper to run
                 it; then it queues a second one and arrives, so the barrier completes through
                 gomp_barrier_handle_tasks once the queue has drained.
     tasks-spin  the same with waiters that spin and never sleep.
     cancel      all threads pass a gomp_team_barrier_wait_cancel barrier (false); then all but one
                 wait in the next, odd threads asleep and even ones spinning, the last one calls
                 gomp_team_barrier_cancel and all must return true; then the final barrier.
     order       every waiter is held between its read of the root and futex_wait until the release
                 of its barrier, wakes included, is over: the wake is lost unless the release left
                 a changed group word behind.
   A watchdog fails the run when no thread moves for 30 seconds.

   Cygwin has no futex: futex_wait and futex_wake are a queue of condition variables per address.
   The spin hint is sched_yield, since 240 threads share the host's few cores.  */
#include <limits.h>
#include <pthread.h>
#include <sched.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* What bar.h and bar.c use of libgomp.h, mutex.h, wait.h and futex.h.  */
#define GOMP_MUTEX_H 1
#define GOMP_WAIT_H 1
enum memmodel { MEMMODEL_RELAXED, MEMMODEL_CONSUME, MEMMODEL_ACQUIRE, MEMMODEL_RELEASE,
                MEMMODEL_ACQ_REL, MEMMODEL_SEQ_CST };
typedef pthread_mutex_t gomp_mutex_t;
#define gomp_mutex_lock pthread_mutex_lock
#define gomp_mutex_unlock pthread_mutex_unlock
unsigned int gomp_knc_ncores;
#include "simple-bar.h"

struct gomp_team
{
  gomp_barrier_t barrier;
  gomp_mutex_t task_lock;
  unsigned task_count;
  int work_share_cancelled;
};

struct waiter { int *addr; struct waiter *next; pthread_cond_t cond; bool woken; };

struct gomp_thread
{
  struct { struct gomp_team *team; unsigned team_id; } ts;
  long done;		/* Barriers this thread has left.  */
  long spins;		/* Spin iterations before futex_wait; -1 never sleeps.  */
  struct waiter waiter;
};

static __thread struct gomp_thread *self;
static inline struct gomp_thread *gomp_thread (void) { return self; }
void gomp_barrier_handle_tasks (gomp_barrier_state_t);
static int do_spin (int *, int);
static void futex_wait (int *, int);
static void futex_wake (int *, int);
static inline void do_wait (int *addr, int val) { if (do_spin (addr, val)) futex_wait (addr, val); }
#include "bar.c"

enum { PLAIN, TASKS_PARK, TASKS_SPIN, CANCEL, ORDER };
static const char *const mode_names[] = { "plain", "tasks-park", "tasks-spin", "cancel", "order" };
static int mode, nthreads = 240;
static long barriers = 100000;
static struct gomp_team team;
static unsigned queued;				/* Under task_lock: team->task_queued_count.  */
static long arrived, releases, tasks_run, moves;	/* Atomic.  */
static int parked, spinning;			/* Atomic: threads in futex_wait, in do_spin.  */

#define LOAD(x) __atomic_load_n (&(x), MEMMODEL_SEQ_CST)
#define ADD(x, n) __atomic_add_fetch (&(x), n, MEMMODEL_SEQ_CST)

static void
fail (const char *what)
{
  printf ("FAIL %s: %s: generation %u, %ld arrivals, %ld tasks run, %d asleep, %d spinning\n",
          mode_names[mode], what, LOAD (team.barrier.generation), LOAD (arrived), LOAD (tasks_run),
          LOAD (parked), LOAD (spinning));
  fflush (stdout);
  _exit (1);
}

/* The futex: a thread sleeps on its own condition variable in the queue of its address.  */
static struct bucket { pthread_mutex_t lock; struct waiter *list; } buckets[64];
#define BUCKET(addr) (&buckets[((uintptr_t) (addr) >> 6) % 64])

static void
futex_wait (int *addr, int val)
{
  struct bucket *b = BUCKET (addr);
  struct waiter *w = &self->waiter;

  pthread_mutex_lock (&b->lock);
  if (LOAD (*addr) == val)
    {
      w->addr = addr;
      w->woken = false;
      w->next = b->list;
      b->list = w;
      ADD (parked, 1);
      while (!w->woken)
        pthread_cond_wait (&w->cond, &b->lock);
      ADD (parked, -1);
    }
  pthread_mutex_unlock (&b->lock);
}

static void
futex_wake (int *addr, int count)
{
  struct bucket *b = BUCKET (addr);
  struct waiter **p, *w;

  pthread_mutex_lock (&b->lock);
  for (p = &b->list; (w = *p) != NULL && count > 0; )
    if (w->addr == addr)
      {
        *p = w->next;
        w->woken = true;
        pthread_cond_signal (&w->cond);
        count--;
      }
    else
      p = &w->next;
  pthread_mutex_unlock (&b->lock);
}

/* wait.h's do_spin: 0 when *ADDR changed, 1 to go on to futex_wait.  */
static int
do_spin (int *addr, int val)
{
  struct gomp_thread *thr = self;
  long i;

  if (mode == ORDER)
    {
      /* bar.c has read the root.  Hold the thread until its barrier is released and woken.  */
      while (LOAD (releases) <= thr->done)
        sched_yield ();
      return 1;
    }
  ADD (spinning, 1);
  for (i = 0; thr->spins < 0 || i < thr->spins; i++)
    {
      if (__atomic_load_n (addr, MEMMODEL_RELAXED) != val)
        break;
      sched_yield ();
    }
  ADD (spinning, -1);
  return thr->spins >= 0 && i == thr->spins;
}

/* task.c's gomp_barrier_handle_tasks, with a counter for the task queue.  */
void
gomp_barrier_handle_tasks (gomp_barrier_state_t state)
{
  gomp_barrier_t *bar = &team.barrier;

  gomp_mutex_lock (&team.task_lock);
  if (team.task_count != 0 && gomp_barrier_has_completed (state, bar))
    {
      gomp_mutex_unlock (&team.task_lock);
      return;
    }
  if (gomp_barrier_last_thread (state))
    {
      if (team.task_count == 0)
        {
          gomp_team_barrier_done (bar, state);
          gomp_mutex_unlock (&team.task_lock);
          gomp_team_barrier_wake (bar, 0);
          return;
        }
      gomp_team_barrier_set_waiting_for_tasks (bar);
    }
  for (;;)
    {
      bool run = queued != 0;

      if (run)
        {
          if (--queued == 0)
            gomp_team_barrier_clear_task_pending (bar);
        }
      else if (team.task_count == 0 && gomp_team_barrier_waiting_for_tasks (bar))
        {
          gomp_team_barrier_done (bar, state);
          gomp_mutex_unlock (&team.task_lock);
          gomp_team_barrier_wake (bar, 0);
          return;
        }
      gomp_mutex_unlock (&team.task_lock);
      if (!run)
        return;
      ADD (tasks_run, 1);
      sched_yield ();
      gomp_mutex_lock (&team.task_lock);
      __atomic_store_n (&team.task_count, team.task_count - 1, MEMMODEL_RELEASE);
    }
}

/* GOMP_task's queueing of one task, from a thread outside the barrier.  */
static void
queue_task (void)
{
  gomp_mutex_lock (&team.task_lock);
  __atomic_store_n (&team.task_count, team.task_count + 1, MEMMODEL_RELEASE);
  queued++;
  gomp_team_barrier_set_task_pending (&team.barrier);
  gomp_mutex_unlock (&team.task_lock);
  gomp_team_barrier_wake (&team.barrier, 1);
}

/* The thread has left a barrier that all threads passed.  */
static void
left (struct gomp_thread *thr)
{
  unsigned gen = LOAD (team.barrier.generation) & -BAR_INCR;

  thr->done++;
  if (gen != (unsigned) thr->done * BAR_INCR)
    fail ("a thread left a barrier at the wrong generation");
  if (LOAD (arrived) < thr->done * nthreads)
    fail ("a thread left a barrier before all had arrived");
  ADD (moves, 1);
}

static void *
worker (void *arg)
{
  struct gomp_thread thr = { .ts = { &team, (uintptr_t) arg } };
  gomp_barrier_t *bar = &team.barrier;
  unsigned id = thr.ts.team_id;
  gomp_barrier_state_t state;
  long round, seen;

  self = &thr;
  pthread_cond_init (&thr.waiter.cond, NULL);
  thr.spins = (mode == TASKS_PARK ? 0 : mode == TASKS_SPIN ? -1
               : mode == CANCEL ? -(long) (id % 2 == 0) : id % 3 == 0 ? 0 : 20 * (id % 3));
  for (round = 0; thr.done < barriers; round++)
    {
      bool late = id == round % nthreads;

      ADD (arrived, 1);
      switch (mode)
        {
        case PLAIN:
          if (round % 3 == 0)
            gomp_barrier_wait (bar);
          else if (round % 3 == 1)
            gomp_team_barrier_wait (bar);
          else
            gomp_team_barrier_wait_final (bar);
          break;
        case ORDER:
          state = gomp_barrier_wait_start (bar);
          gomp_team_barrier_wait_end (bar, state);
          if (state & BAR_WAS_LAST)
            ADD (releases, 1);
          break;
        case TASKS_PARK:
        case TASKS_SPIN:
          if (late)
            {
              /* All the others have left the barrier before and wait in this one.  */
              while (LOAD (arrived) != (round + 1) * nthreads
                     || LOAD (*(mode == TASKS_PARK ? &parked : &spinning)) != nthreads - 1)
                sched_yield ();
              seen = LOAD (tasks_run);
              queue_task ();
              while (LOAD (tasks_run) == seen)
                sched_yield ();
              queue_task ();
            }
          gomp_team_barrier_wait (bar);
          break;
        case CANCEL:
          if (gomp_team_barrier_wait_cancel (bar))
            fail ("a barrier that nobody cancelled returned true");
          left (&thr);
          if (late)
            {
              while (LOAD (moves) != (3 * round + 1) * nthreads
                     || LOAD (parked) + LOAD (spinning) != nthreads - 1)
                sched_yield ();
              gomp_team_barrier_cancel (&team);
            }
          else if (!gomp_team_barrier_wait_cancel (bar))
            fail ("a cancelled barrier returned false");
          ADD (moves, 1);
          ADD (arrived, 1);
          gomp_team_barrier_wait_final (bar);
          break;
        }
      left (&thr);
    }
  return NULL;
}

int
main (int argc, char **argv)
{
  pthread_t *threads;
  pthread_attr_t attr;
  long last = -1, now;
  int i, quiet = 0;

  setvbuf (stdout, NULL, _IOLBF, 0);
  for (mode = 0; mode < 5 && (argc < 2 || strcmp (argv[1], mode_names[mode])); mode++)
    continue;
  if (mode == 5)
    return puts ("usage: barrier_stress plain|tasks-park|tasks-spin|cancel|order [BARRIERS [NCORES [THREADS]]]"), 2;
  if (argc > 2)
    barriers = atol (argv[2]);
  gomp_knc_ncores = argc > 3 ? atoi (argv[3]) : 60;
  if (argc > 4)
    nthreads = atoi (argv[4]);
  for (i = 0; i < 64; i++)
    pthread_mutex_init (&buckets[i].lock, NULL);
  pthread_mutex_init (&team.task_lock, NULL);
  gomp_barrier_init (&team.barrier, nthreads);
  threads = malloc (nthreads * sizeof *threads);
  pthread_attr_init (&attr);
  pthread_attr_setstacksize (&attr, 256 * 1024);
  for (i = 0; i < nthreads; i++)
    if (pthread_create (&threads[i], &attr, worker, (void *) (uintptr_t) i))
      return puts ("FAIL: pthread_create"), 2;
  while ((now = LOAD (moves)) < (mode == CANCEL ? 3 : 2) * barriers * nthreads / 2)
    {
      quiet = now == last ? quiet + 1 : 0;
      if (quiet == 30)
        fail ("no thread moved for 30 seconds");
      last = now;
      sleep (1);
    }
  for (i = 0; i < nthreads; i++)
    pthread_join (threads[i], NULL);
  if (LOAD (team.barrier.generation) != (unsigned) barriers * BAR_INCR)
    fail ("the final generation is wrong");
  printf ("PASS %s: %d threads in %u groups of %u, %ld barriers, generation %u, %ld tasks run\n",
          mode_names[mode], nthreads, team.barrier.ngroups, team.barrier.gsize, barriers,
          LOAD (team.barrier.generation), LOAD (tasks_run));
  return 0;
}
