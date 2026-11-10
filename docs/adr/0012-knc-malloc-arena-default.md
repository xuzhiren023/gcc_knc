# ADR-0012: OpenMP programs on KNC size glibc's malloc arena cap from the card's memory

**Status:** Accepted 2026-11-10. The owner set the requirement ("this setting should be change
accordingly based on card model number and guarantee best performance across model"; WRF runs
with `MALLOC_ARENA_MAX=64` for speed); the lead set the details.
**Supersedes:** the recommendation in `docs/research/knc-libgomp.md` section 6 that libgomp must
not call `mallopt` and should only document `MALLOC_ARENA_MAX`.

## Context

glibc 2.21 gives each thread that mallocs while the main arena is busy its own arena, an `mmap`
reservation of 64 MiB, up to 8 x CPUs arenas. Reservations cost address space, not memory, so a
240-thread OpenMP program on a card without an address-space limit runs with up to 240 arenas.
Under an `RLIMIT_AS` it fails instead: S8-01 job 19 and the S9-06 `tasks` program at 240 threads
(2026-11-10) both ran out under `card_run`'s 6 GiB limit. Fewer arenas means more threads sharing
an arena lock; WRF measured 64 as fast on the 7120.

GCC-KNC must work on every KNC card, and their memory differs: 3120 (6 GB, 57 cores), 5110P
(8 GB, 60 cores), 7120 (16 GB, 61 cores). One fixed value is wrong for some of them.

## Decision

1. **libgomp on k1om sets the arena cap at load** (`mallopt (M_ARENA_MAX, n)`) when the
   environment has no `MALLOC_ARENA_MAX`. A user's `MALLOC_ARENA_MAX` always wins. Programs that
   do not use OpenMP are not affected.
2. **The cap comes from what the card and the process can reserve, not from a model table.** The
   inputs are `MemTotal`, the `RLIMIT_AS` soft limit, `CommitLimit` when `overcommit_memory` is 2,
   and the CPUs the process may run on. Memory is what decides the right value, and reading it
   covers every model and variant (3120, 5110P, 5120D, 7120) and any limit a batch system sets.
3. **The rule:** as many arenas as threads that can run (the CPUs of the mask), unless their
   reservations, plus the thread stacks, would not fit in the budget. Then the largest count that
   fits. The budget is `RLIMIT_AS` when it is finite (and `CommitLimit` under strict
   overcommit), otherwise a share of `MemTotal`. The share, and whether a cap below the thread
   count is faster, are set by measurement, not by this ADR.
4. **Measurement decides the numbers.** Measurement 7 of `knc-libgomp.md` (240 threads,
   malloc/free) runs with arena caps unset, 240, 120, 64, 60, 30 and 8, at job limits of 6, 8
   and 10 GiB as stand-ins for the 3120, the 5110P and the 7120 (10 GiB is our card budget;
   `tools/card_run:24`). The rule picks the fastest cap that fits at each size; ADR-0010 rules
   apply.
5. **It is visible.** `omp_display_env` (verbose) prints the cap and where it came from (user,
   or derived, with the budget it used).

## Consequences

- A library changes the program's allocator setting. This is a documented KNC default with an
  opt-out, like the default thread binding of S9-07.
- 240-thread programs no longer fail under an address-space limit that can hold their stacks.
- Card jobs that start 240 threads use the 10 GiB budget until this lands.
