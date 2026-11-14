# KNC libgomp: E6-03 implementation input (S9-01)

**S12-13 status update (2026-11-14).** This document retains the original
design. Current-source checks at GCC `619e14b479a9` supersede the waiting,
barrier and allocator proposals at their sections below. They do not certify
the deployed runtime. Sources use [knc-references.md](knc-references.md).

Read-only research, 2026-11-08. Nothing was built and nothing ran on the card. Sources are the
GCC checkout `.work/_shared/gcc` (branch `knc`, head `497bbe8bedf`, file:line below), the card
sysroot `.work/_shared/toolchain/sysroot`, the Intel KNC ISA text
`.work/_shared/intel-327364-001-xeon-phi-isa.txt`, and the repo's own records. Every answer is
marked **proven** (read in a file named here), **inferred** (follows from proven facts plus
documented upstream behaviour) or **unknown** (needs a configure run or a card job).

Settled before this note (ticket): native TLS works (S3-14); `libgcc_s.so.1` and
`libgfortran.so.5` live in GCC-KNC's private prefix (S7-06, S7-09); the card runs kernel 2.6.38 with
glibc 2.21; `pause` does not exist on KNC and `delay` does (S2-06); two threads saturate the VPU
and a spinning sibling steals issue slots on the round-robin core; WRF spends 54-58% of thread time
in barrier wait; glibc gives each thread that mallocs its own 64 MB arena reservation (S8-01 job 19).

## 1. Build: what `--enable-libgomp` needs for `k1om-mpss-linux`

**Current state.** The shared build is configured with `--disable-libgomp`
(`.work/_shared/gcc-build/config.status`, `ac_cs_config`). **Proven.** The top level would build
libgomp for any `*-*-linux*` target once that flag is dropped (`configure.ac:538-552`: the
`noconfigdirs` exclusion applies only to targets outside the listed OS families). **Proven.**

**Runtime selection.** `libgomp/configure.tgt:37` sets `config_path="posix"`; the futex block
(`configure.tgt:40-127`) replaces it only for listed targets, and the x86 case is
`i[456]86-*-linux* | x86_64-*-linux*` (`configure.tgt:88`). `k1om-mpss-linux` matches nothing
there, so even with futex enabled the build gets the pthread-mutex and semaphore runtime
(`config/posix/mutex.h:34`, `config/posix/sem.h`, `config/posix/bar.h`: a barrier of two
semaphores). **Proven.** The TLS block at `configure.tgt:25-27` does match (`*-*-linux*`) and
adds `-ftls-model=initial-exec -DUSING_INITIAL_EXEC_TLS` when `gcc_cv_have_tls` is yes; after
S3-14 the assembler TLS probe covers `k1om-*-linux*` (`gcc/configure.ac:3995`), so this is
expected to hold. **Inferred.** With `HAVE_TLS`, `__GLIBC__` and `USING_INITIAL_EXEC_TLS` set,
`struct gomp_thread` drops the `pthread_t handle` field (`libgomp.h:899-909`).

The sibling runtimes already route k1om as `cpu_type=i386` (`libgcc/config.host:134-136`,
`libgfortran/configure.host:45-48`). The same one-case addition is needed here:

```
k1om-*-linux*)
    config_path="linux/knc linux/x86 linux posix"
    ;;
```

placed inside the futex block. `Makefile.am:10-19` turns `config_path` into a `vpath` and `-I`
list in that order, so a `config/linux/knc/` directory overrides single files (`futex.h`,
`spincount.h`, later `bar.h`/`bar.c`) without copying the rest. **Proven.**

**Futex decision.** `enable_linux_futex` comes from `config/futex.m4:8-66` (included at
`libgomp/configure.ac:256`): for `*-linux*` the default is a link test of `syscall (SYS_gettid)`,
`syscall (SYS_futex, ...)` and `pthread_tryjoin_np` against the sysroot. The sysroot headers have
`__NR_gettid 186` and `__NR_futex 202` (`usr/include/asm/unistd_64.h:459,492`) and
`FUTEX_PRIVATE_FLAG 128` (`usr/include/linux/futex.h:24`); the kernel header reports
`LINUX_VERSION_CODE 132646` = 2.6.38 (`usr/include/linux/version.h:1`), glibc is 2.21
(`usr/include/features.h:356-357`). **Proven.** `FUTEX_PRIVATE_FLAG` entered Linux in 2.6.22, so
2.6.38 honours it and the `ENOSYS` fallback in `futex_wait`/`futex_wake`
(`config/linux/x86/futex.h:95-118`) will not trigger. **Inferred.** Whether the configure link
test passes with our cross compiler is **unknown** until it runs; PhiWeather's GCC 5 KNC libgomp
was built with `--disable-linux-futex --disable-shared`
(`PhiWeather/.tools/knc-bootstrap/build-knc-libgomp/config.log:7`, `Makefile:316`
`config_path = posix`), which shows the posix path builds for k1om but says nothing about futex.

**The x86 directory on KNC.** `config/linux/x86/futex.h` has two halves. The syscall half
(`:28-58`) is selected by `__x86_64__`, which `-march=knc` defines (`gcc/config/i386/i386-c.cc:919`
defines it for every 64-bit x86 target; `i386-knc.cc:897-898` adds `__KNC__` and `__k1om__`); the
`syscall` instruction is in the KNC supported GPR list (ISA text line 25833) and CPUID reports it
(line 26540). **Proven.** The `cpu_relax` half (`:120-124`) calls `__builtin_ia32_pause`. On KNC the
`pause` expander (`gcc/config/i386/i386.md:30320-30331`) emits `knc_pause`, which is `delay %1`
with the constant 32 forced into a register (`gcc/config/i386/imci.md:485-495`). So an unmodified
libgomp would not emit `pause` on KNC, but the delay count is fixed at 32 and not tunable. **Proven.**
`pause` itself is in the ISA's "not supported" table together with `cmpxchg16b` (ISA text line
25857 and 25853). **Proven.** `config/linux/x86/spincount.h:29-41` includes `cpuid.h` under
`__x86_64__` and queries CPUID leaf 7 for the hybrid bit; what KNC returns for leaf 7 is **unknown**
(harmless if zero, but a KNC `spincount.h` should set KNC defaults instead).

**Other static blockers found: none.** Across `libgomp/` (excluding testsuite, plugins and the
accelerator configs) the only `__builtin_ia32_*` use is the `pause` above; `__int128` and
`__sync_val_compare_and_swap_16` occur only in `config/accel/target-indirect.c` and
`config/nvptx/atomic.c`, which are not built for a host runtime; there is no SSE or `immintrin.h`
include. **Proven** (grep). The host runtime needs: 4-byte `__sync` CAS for `HAVE_SYNC_BUILTINS`
(`acinclude.m4:5-14`), which KNC has (S2-06 kept `__GCC_HAVE_SYNC_COMPARE_AND_SWAP_8` and below);
`pthread_{get,set}affinity_np` and `pthread_attr_setaffinity_np` (`configure.ac:258-275`, glibc
2.21 has them, and PhiWeather's GCC 5 config shows `HAVE_PTHREAD_AFFINITY_NP 1`,
`HAVE_SYNC_BUILTINS 1`, `HAVE_TLS 1`, `HAVE_AS_SYMVER_DIRECTIVE 1` for this sysroot and
assembler); `SYS_gettid` for `omp_nest_lock` owners (`config/linux/lock.c:67,80`); `mlock` for
pinned allocations (`config/linux/allocator.c:124`); lazy `dlopen` of `libnuma.so.1` and
`libmemkind.so.0` that fails gracefully (`allocator.c:288,343`); `aligned_alloc`/`posix_memalign`/
`memalign` (`alloc.c:63-80`), present in glibc 2.21, which turns on
`GOMP_USE_ALIGNED_WORK_SHARES` (`libgomp.h:95-106`). The Fortran parts (`openacc.f90`, `omp_lib`)
need the k1om gfortran, which S7-09 installed. **Proven/inferred as marked.**

**Link spec.** `gcc/gcc.cc:1198` includes `libgomp.spec` for `-fopenmp`; the template is one line,
`*link_gomp: @link_gomp@` (`libgomp/libgomp.spec.in`), filled with `-lgomp` plus `$LIBS` and
`-ldl` (`libgomp/configure.ac:406-408`). The SONAME is `libgomp.so.1` (`libtool_VERSION=1:0:0`,
`libgomp/configure.ac:177`, applied at `Makefile.am:55-60`). **Proven.**

## 2. Coexistence with the card's other OpenMP runtimes

**What is on hand.** The sysroot has no `libgomp.so*` and no `libiomp5*`; neither does the cross
toolchain nor PhiWeather's bootstrap tree (find over all three). The only other KNC libgomp here is
PhiWeather's static GCC 5 build (`build-knc-libgomp/.libs/libgomp.la`, no shared object).
**Proven for local copies.** What the card's `/lib64` and the MPSS tree hold is **unknown** from
here; the lead's first card check lists them (plan, ticket A).

**Symbol versions.** Our `libgomp.map` defines the version nodes `OMP_1.0` to `OMP_5.2`,
`GOMP_1.0` to `GOMP_6.0.1`, `OACC_2.0` to `OACC_2.6.1`, `GOACC_2.0` to `GOACC_2.0.2` and
`GOMP_PLUGIN_1.0` to `1.4` (`libgomp/libgomp.map:1-676`). `GOMP_6.0` adds
`omp_get_device_from_uid` and `omp_get_uid_from_device` (`libgomp.map:447-454`), `GOMP_6.0.1` adds
`omp_target_memset` (`:456-460`); no GCC 5 runtime has these. **Proven.** A GCC 5 `libgomp.so.1`
carries the same SONAME with nodes up to `OMP_4.0`/`GOMP_4.0.1`, and Intel's `libiomp5.so` exports
the `GOMP_*` entry points under versioned `GOMP_1.0`-`GOMP_4.0` nodes for GCC compatibility.
**Inferred** (upstream history and Intel's documented GCC-compat layer; verify with `readelf -V`
on the card copies).

**Consequence.** Three failure shapes: (1) a program linked with `-fopenmp` against our driver but
with a `-L` directory holding the GCC 5 `libgomp.so.1` first links against the old runtime and
fails at load on any `GOMP_5.*`/`GOMP_6.*` symbol, or silently runs the old barrier; (2) a program
whose dependency (an Intel-built library) pulls `libiomp5.so`, which also satisfies `GOMP_*`
references, ends with two thread pools; (3) a GCC 5 static libgomp inside an object archive plus our
shared one gives duplicate definitions.

**Guarantee of one runtime per process, S7-06/S7-09 pattern.** Install `libgomp.so.1` in the
private prefix beside `libgcc_s.so.1` and `libgfortran.so.5`
(`.work/_shared/gcc-knc-16.2.0/k1om-mpss-linux/lib64/`), found by `DT_RPATH $ORIGIN/../lib`
(`tools/s7_09_checks.py:14,42`). Add the same guard as `libgfortran.spec` and
`libgfortran-knc.ld` (installed copies in that lib64 directory): the k1om `libgomp.spec` becomes
`*link_gomp: -lgomp libgomp-knc.ld%s ...`, where the implicit linker script does
`EXTERN(omp_get_device_from_uid)` and `ASSERT(DEFINED(omp_get_device_from_uid), "GCC-KNC: the
libgomp found first is older than this compiler's libgomp.so.1")`, so shape (1) fails at link time
with a clear message in static and shared links alike. Shape (2) is a load-time property: the card
check runs the program with `LD_DEBUG=libs` (glibc 2.21 supports it) or reads `/proc/self/maps` and
requires exactly one `libgomp` mapping from the private prefix and no `libiomp5`; `OMP_DISPLAY_ENV=
verbose` (`env.c:1971-1975` prints `GOMP_SPINCOUNT`, which libiomp5 does not) identifies ours at
run time. Shape (3) is a documentation rule (rebuild everything with GCC-KNC, as E8-01 already
states). **Inferred design on proven mechanisms.**

## 3. Affinity on KNC's CPU numbering

**Numbering.** `tools/card_run` maps CPUs to cores from `/proc/cpuinfo` `core id` and only accepts
cores 0-59 with exactly four CPUs each (`tools/card_run:188-199,327`); cores 30-59 are logical CPUs
121-240 (`CURRENT_STATE.md`, S2-11 card fact). So core c = CPUs 4c+1..4c+4 for c = 0..59
(**proven** for 30-59, **inferred** for 0-29 by the same formula), and CPU 0 with CPUs 241-243 form
core 60, the OS core (**inferred**; the ticket states it). `claude-pin` sets the job's affinity mask
with `sched_setaffinity` before `exec` (`tools/claude-pin.c:46`), so under `card_run` the process
mask already excludes CPU 0 and the other project's cores. **Proven.**

**What GCC 16 does by default.** `bind_var` defaults to `omp_proc_bind_false` (`env.c:76`) and
`gomp_init_affinity` runs only when it is not false (`env.c:2418-2419`), so by default nothing is
pinned and the 2.6.38 scheduler places 240 threads. **Proven.** With `OMP_PROC_BIND=true` and no
`OMP_PLACES`, `gomp_init_affinity` builds `threads` places (`config/linux/affinity.c:52-55` calls
`gomp_affinity_init_level (1, ULONG_MAX, true)`): one place per CPU in the process mask, in CPU
number order (`affinity.c:277-359`), from the mask read by `pthread_getaffinity_np`
(`config/linux/proc.c:94`). Threads are then assigned to places in order (`team.c:752-832`,
`gomp_init_thread_affinity` at `:832`, `pthread_attr_setaffinity_np` at `affinity.c:67-71`).
On KNC numbering that puts threads 0-3 on core 0, 4-7 on core 1, and so on: a 60-thread team
occupies 15 cores four deep, and outside `card_run` it includes CPU 0. **Proven mechanism,
inferred outcome.**

**`cores` places need sysfs.** `OMP_PLACES=cores` (level 2, `env.c:773-777`) reads
`/sys/devices/system/cpu/cpuN/topology/thread_siblings_list` (`affinity.c:296-297`), `sockets`
reads `core_siblings_list`, `ll_caches` reads `cache/index*/shared_cpu_list` (`affinity.c:284-292`),
`numa_domains` reads `/sys/devices/system/node/online` (`affinity.c:375`). If a file is missing the
CPU is dropped and the place list may come out empty with "Error reading core/socket topology"
(`affinity.c:493-500`). Whether the card's kernel exposes these sysfs files is **unknown** (card
check A3). `/proc/cpuinfo` `core id` is proven present.

**Explicit settings that work with today's code** (`env.c:754-800` for `OMP_PLACES`,
`env.c:1134-1230` for `GOMP_CPU_AFFINITY`):

| Goal | Setting |
| --- | --- |
| one place per core, 60 places of 4 CPUs, OS core excluded | `OMP_PLACES="{1:4}:60:4"` |
| one thread per core | `OMP_PLACES="{1:4}:60:4" OMP_PROC_BIND=spread OMP_NUM_THREADS=60` |
| two siblings per core | same places, `OMP_PROC_BIND=close OMP_NUM_THREADS=120` |
| pin to one CPU per core, no place list | `GOMP_CPU_AFFINITY="1-237:4"` |

**Design for the KNC default.** When none of `OMP_PLACES`, `GOMP_CPU_AFFINITY` and
`OMP_PROC_BIND` is set, a KNC `gomp_init_affinity` (new `config/linux/knc/affinity.c`, or a KNC
branch in the linux one) should: build core places from sysfs when present, else from
`/proc/cpuinfo` `core id` (the card_run method); intersect with the inherited mask
(`gomp_affinity_finalize_place_list`, `affinity.c:188-224`, already does this); drop the core that
contains CPU 0 unless the mask leaves nothing else; set `bind_var` to `omp_proc_bind_spread` so a
60-thread team gets one thread per core, 120 two, 240 four (`team.c:418,531,707,792` are the
spread cases over the place partition). `omp_get_num_procs` then counts the usable CPUs (`proc.c:147-178`). Keep
`OMP_PROC_BIND=false` as the explicit opt-out. **Design, to be proven by ticket B.**

## 4. Barrier and spin

**GCC 16's barrier.** `gomp_barrier_t` is two cache lines: `total`+`generation` (read-mostly)
and `awaited`+`awaited_final` (`config/linux/bar.h:35-43`). Every arriving thread does one
`__atomic_add_fetch (&bar->awaited, -1, ACQ_REL)` (`bar.h:98`): 240 read-modify-writes on a
single line, each a ring transfer between cores. The last arriver resets `awaited`, bumps
`generation` by `BAR_INCR` and calls `futex_wake (INT_MAX)` (`bar.c:39-43`, team variant
`bar.c:91-106`). Waiters loop `do_wait` on `generation` (`bar.c:47-49`, `:112-123`):
`do_spin` reads the word up to `gomp_spin_count_var` times with `cpu_relax` between reads, or only
`gomp_throttled_spin_count_var` times when `gomp_managed_threads > gomp_available_cpus`
(`config/linux/wait.h:48-68`), then `futex_wait`. All 240 spinners poll the same `generation` line;
when it changes, every core refetches it over the ring. The team variant also handles
`BAR_TASK_PENDING`, `BAR_WAITING_FOR_TASK` and `BAR_CANCELLED` flags in the low bits of
`generation` (`bar.h:47-54`, `bar.c:80-215`); `gomp_team_barrier_done` stores to `generation` under
`task_lock` (`bar.h:162-169`); `gomp_barrier_handle_tasks` in `task.c` depends on these.
The thread pool's dock is a `gomp_simple_barrier_t` wrapping the same type
(`config/posix/simple-bar.h:34-36`; `team.c:123-133,873`), so fork/join pays the same cost twice
per region (dock release and final team barrier). **Proven.**

**Historical generic spin defaults (superseded for KNC, S12-13).** Without `GOMP_SPINCOUNT`: 300,000 spins when `OMP_WAIT_POLICY` is unset
(a 3 ms estimate at 100,000 spins per ms, `env.c:2432-2447`), 30,000,000,000 for `active`, 0 for
`passive`; throttled 100 or 1,000 (`env.c:2448-2454`); `do_adjust_default_spincount` is the only
target hook and sets 1 on x86 hybrid parts (`config/linux/x86/spincount.h:34-41`). `cpu_relax` is
`__builtin_ia32_pause` (x86) or an empty asm (generic `config/linux/futex.h:66-70`). **Proven.**
On KNC each spin iteration is instructions issued by a thread that shares the in-order core's
round-robin issue with the working sibling; `delay r32` is the ISA's answer: "the processor should
not fetch/issue instructions for the current thread for the specified number of clock cycles",
exits early on interrupts and may be a NOP on some implementations (ISA text lines 24644-24668).
**Proven.**

**Current KNC correction:** `config/linux/knc/card.h` defines delay 128 and
`GOMP_KNC_SPIN_MSEC=200`; `spincount.h` applies it with user overrides. R18
pp.59–61 describes Intel's 200 ms policy and distinguishes barriers from
region formation; it does not independently validate ours. R27 p.628 allows
interrupt-related early exit from DELAY, so its operand is not exact elapsed
sleep time. The 3 ms conversion below is a **superseded design**, not today's default.

**Historical design: `delay`-based spin.** In `config/linux/knc/futex.h` define
`cpu_relax ()` as `__asm volatile ("delay %0" :: "r" (gomp_knc_delay) : "memory")` with
`gomp_knc_delay` a runtime variable (default from the one-core measurement, candidates 32, 128,
512; env `GOMP_KNC_DELAY` for tuning), and keep `do_spin`'s structure: the spin count then counts
delay periods, so the KNC default `gomp_spin_count_var` in `knc/spincount.h` becomes about
3 ms / (delay cycles / 1.1 GHz), for example 25,000 at `delay 128`. `GOMP_SPINCOUNT` and
`OMP_WAIT_POLICY` keep their meaning. Since `__builtin_ia32_pause` already emits `delay 32` on KNC,
the inline asm is only needed for a variable count. **Design.**

**S12-13 barrier correction:** `config/linux/knc/bar.h` keeps the grouped
implementation behind `GOMP_KNC_GROUP_BARRIER`; its comment reports a
1.5–1.7× slowdown against the default Linux barrier. C11's synthetic tree
versus one-counter result does not establish a real libgomp win. R18 pp.59–61,
R21 §6.5 pp.7–8 and R22 pp.4–7 require the algorithm, useful work, placement
and synchronization denominator to stay explicit. The following proposal is
**superseded as the default recommendation**, retained as design history.

**Historical design: hierarchical barrier.** Two levels, in `config/linux/knc/bar.h` and `bar.c`, keeping
the `gomp_barrier_t` API and the `BAR_*` flag protocol so `team.c`, `task.c`, `work.c` and
`single.c` need no change:

- **Scope: the team barrier only.** `gomp_barrier_init` is called on `team->barrier` once, in
  `gomp_new_team` with the final `nthreads` (`team.c:190`), and a team is only reused for the same
  `nthreads` (`get_last_team`, `team.c:175`). `gomp_barrier_reinit` is never applied to a team
  barrier: its only callers are the pool dock's `gomp_simple_barrier_reinit` (`team.c:482,722,891`
  through `config/posix/simple-bar.h:48`), which grows the count while old threads are already
  parked. **Proven** (grep over `libgomp/*.c`). The hierarchical barrier therefore has a fixed
  member count for its whole life, and the dock keeps the flat `gomp_barrier_t` (a KNC
  `simple-bar.h` wrapping the flat type, since `simple-bar.h` is the posix one). Making the dock
  hierarchical is a follow-up decided by measurement 3.
- **Group membership is a pure function of `team_id` and `total`, computed once by the master.**
  `gomp_barrier_init (bar, count)` sets `ngroups = min (count, gomp_knc_ncores)` (60 by default,
  the core count from section 3's place builder, or from the mask) and `gsize = ceil (count /
  ngroups)`; thread `team_id` belongs to group `team_id / gsize`, and the last group's size is
  `count - (ngroups - 1) * gsize`. Each group's arrival counter is stored with its size before the
  team is released, so no counter is ever read before its member count exists. `team_id` is the
  thread's index in the team and does not change while the team exists (`libgomp.h:412-445`).
  This matches the bound layouts without a second mapping: with `close` and `T > P`,
  `s = nthreads / place_partition_len` consecutive `team_id`s share one place (`team.c:697-700,
  777-781`), and `spread` with `T > P` does the same (`team.c:707-715`), so with section 3's 60
  core places, threads `4c..4c+3` are the siblings of core `c` at 240 threads and `2c, 2c+1` at
  120. **Proven** for the assignment order. Unbound threads keep the same deterministic groups:
  only locality is lost when they migrate, never correctness. `sched_getcpu ()`
  (`sysroot/usr/include/bits/sched.h:88`; getcpu is a vsyscall on this kernel,
  `asm/unistd_64.h:650`) is not used for membership; at most it can later choose between two
  precomputed mappings, and the first ticket does not use it at all.
- Arrival: decrement the group counter (an L1/L2-local RMW among siblings, no ring traffic); the
  sibling that brings it to zero resets it to the group size and decrements the root `awaited`,
  which sits in its own line and sees at most 60 RMWs instead of 240. The thread that brings the
  root to zero gets `BAR_WAS_LAST`, exactly as `gomp_barrier_wait_start` does today (`bar.h:98`).
  `awaited_final` (`bar.h:112-121`) gets the same group treatment with a second per-group counter.
  A second tree level (fan-in 8: 60 to 8 to 1) is a later option; measure first.
- **One rule for every thread of a barrier instance: always arrive through the groups, and only
  the root owns the flags.** The root `generation` word stays the one and only place where
  `BAR_TASK_PENDING`, `BAR_WAITING_FOR_TASK` and `BAR_CANCELLED` live (`bar.h:47-54,129-169`), so
  `task.c` works unchanged under `task_lock`. Each group's release word is a *mirror* of the root
  generation: it is rewritten with the root's current value (flags included) by every operation
  that changes the root and must wake someone, namely the root release (`bar.c:104-105,168-170`,
  ours), `gomp_team_barrier_wake` (`bar.c:74-78`, ours) and `gomp_team_barrier_cancel`
  (`bar.c:203-215`, ours). Every `task.c` writer of the flags that needs a wake already calls
  `gomp_team_barrier_wake` after it (`task.c:729-734`, `833-839`, `1089-1094`, `1583-1585`,
  `1620-1622`, `1633`, `1798`, `2116`, `2320`, `2770-2790`); `clear_task_pending` (`task.c:1306`)
  and `set_waiting_for_tasks` (`task.c:1588`) need no wake today and get none. **Proven** for the
  call sites. A waiter uses the group word exactly as the flat code uses `bar->generation` for
  waiting (`do_wait (&group->word, generation)`, `bar.c:114,181`) and reads the root with ACQUIRE
  for every decision (`bar.c:115-123,182-192`), so the task and cancel loops stay as written: when
  `TASK_PENDING` is mirrored the waiter wakes, runs `gomp_barrier_handle_tasks`, and loops; when
  `BAR_CANCELLED` is mirrored the cancel variant returns true. The root releaser writes the new
  generation into the root first, then into the 60 group words, then futex-wakes each group word:
  60 line writes by one thread instead of 240 polls of one line. For `gomp_team_barrier_wake (bar,
  n)` with `n < INT_MAX` (one task to run): mirror into all group words so spinners see it, then
  `futex_wake (1)` on the group words in order until `n` sleepers have been woken or all groups are
  tried, bounding the syscalls at 60 in the worst case. Because a thread's expected value is
  derived from the root generation it read at arrival and the mirror always holds the latest
  root value, a mirror written before the waiter parks makes `futex_wait` return `EAGAIN` at once,
  so no wake is lost whichever order arrival, task queueing and release happen in. Siblings spin
  with `delay` on their group word, then `futex_wait` on it.
- The plain `gomp_barrier_wait`/`gomp_barrier_wait_last` pair used on `team->barrier` at thread
  exit and team end (`team.c:112,117,871,988`) goes through the same groups and root; there are no
  flags on that path, so the mirror is the bare generation.

**What to measure (lead, card; C11 corpus from S8-10 plus one source file).**
1. One core: a worker loop alone, then with 1, 2 and 3 siblings spinning on a local word with no
   hint, with `delay 32`, `128`, `512`; report worker time ratio (knc-optimization-gaps G3 named this
   check). This fixes `gomp_knc_delay` and shows whether `delay` is a NOP on this stepping.
2. Barrier: 100,000 empty `#pragma omp barrier` at 60x1, 60x2, 60x4 (60, 120, 240 threads) with
   the flat GCC 16 barrier, the two-level barrier, and a tree-of-8 variant; microseconds per barrier.
3. Fork/join: 100,000 empty `#pragma omp parallel` regions at 60x4 (WRF: about 9,850 regions per
   step, fork about 17 us, `docs/research/wrf-input-2026-11-06.md`); with `OMP_WAIT_POLICY`
   unset, `active`, `passive`.
4. Release fan-out: time from the last arrival to the last thread leaving, 60x4.
5. A WRF-shaped case: 240 threads, imbalanced region where one thread does 2x work, which is where
   spinning siblings slow the critical thread.
Timing figures stay out of the ledger per the shared-card rules; they go to
`docs/research/knc-characterization.md`.

## 5. Per-thread data

**What is padded today.** `gomp_barrier_t` fields are `aligned (64)` (`bar.h:39,41`).
`struct gomp_work_share` puts `lock`, `threads_completed`, `next`, `next_ws` and `task_reductions`
on a second line (`libgomp.h:359-399`, compile-time check that `lock` is at offset 64 at
`libgomp.h:405-406`), enabled by `GOMP_USE_ALIGNED_WORK_SHARES` (`libgomp.h:95-106`), and the
team and work-share blocks are allocated with `gomp_aligned_alloc (__alignof (struct gomp_team))`
(`team.c:181-182`, `work.c:82-83,197-198`), which is 64 because of the barrier. **Proven.**

**What is not.** `struct gomp_thread` is one plain `__thread` object, `gomp_tls_data`
(`team.c:43`, declared `libgomp.h:970`), with no alignment: it holds the thread's hot `ts`
(`team`, `work_share`, `team_id`, `libgomp.h:412-445`) next to `release`, a futex word that other
threads write for ordered loops (`libgomp.h:881`), and it shares TLS lines with whatever the
program and other libraries place in TLS. `struct gomp_team.implicit_task[]` is one `struct
gomp_task` per thread laid out contiguously (`libgomp.h:861`), each written by its own thread
(`icv`, `kind`, `children_queue`, `libgomp.h:678-780`), unpadded. `ordered_release[]` is a
pointer array written once (`team.c:102`). `gomp_managed_threads` is a global written at every
fork (`team.c:289,740,894,980`) and loaded once per `do_spin` call, before the spin loop
(`wait.h:50-55`); the loop itself (`wait.h:56-60`) touches only the waited address. So each waiter
reads that line once per wait episode, not once per spin iteration: at most 240 reads per barrier
of a line that was written once at the fork, which is 60 ring transfers per region at the first
barrier and none afterwards until the next fork. Not worth moving. Linux `gomp_sem_t`, `gomp_mutex_t`
and `omp_lock_t` are bare `int`s (`config/linux/sem.h:36`, `mutex.h:33`, `omp-lock.h:9`), so
user locks pad as the user places them. **Proven.**

**Design.** `__thread struct gomp_thread gomp_tls_data __attribute__((aligned (64)))` with the
struct padded to a multiple of 64 (static assert), `release` on its own line; `struct gomp_task`
padded to a 64-byte multiple or `implicit_task` allocated as 64-byte strided slots (the `extra`
size in `team.c:179-184`); the 60 group lines of the barrier allocated at 64-byte stride.
`gomp_managed_threads` and `gomp_available_cpus` stay where they are (see above). Sizes change
nothing in the ABI: these structures are private
to `libgomp.so.1` (`libgomp.h` is not installed). **Design.**

**Reductions are a compiler matter.** `lower_reduction_clauses` (`gcc/omp-low.cc:7663-7960`)
uses one `OMP_ATOMIC` update on the shared variable when there is exactly one scalar reduction
(`:7755-7772`): 240 atomic RMWs on one line, serialized over the ring. With two or more clauses,
array sections or user-defined reductions it wraps plain updates in `GOMP_atomic_start`/`_end`
(`:7944-7958`), which take one global `default_lock` (`libgomp/critical.c:32-45`): every thread
in turn, each handoff a futex or a ring transfer. **Proven.** A tree combine therefore belongs in
omp-low.cc, not in the runtime: emit a per-team array of 64-byte-strided partials (S8-10 already
pads the private temporaries), store the private value, then a barrier and either a log2(N)
pairwise combine or a single-thread sweep of 240 lines (240 reads by one core, no RMW contention).
Which wins at 240 threads is measurement item 6 below; until then the runtime tickets only pad.

**Static schedule default.** For `omp for` with no `schedule` clause the compiler uses static
(`gcc/omp-general.cc:238`) and maps `schedule(auto)` to static (`:346-354`); only
`schedule(runtime)` consults the runtime's `run_sched_var`, whose default is `GFS_DYNAMIC` with
chunk 1 (`env.c:71-72`, `loop.c:218-240`). Dynamic chunk 1 at 240 threads is one RMW on the
work-share lock line per iteration. **Proven.** Recommendation: the KNC runtime default for
`run_sched_var` becomes `GFS_STATIC` (def-sched-var is implementation defined in the OpenMP
specification; `OMP_SCHEDULE` still overrides), and `omp_display_env` shows it. The compiler default
needs no change.

Measurement item 6 (lead): `reduction(+:sum)` over 240 threads, one clause (atomic path) and two
clauses (lock path), 10,000 regions, against a hand-written padded-partials version.

## 6. malloc at 60-240 threads

**Facts.** S8-01 job 19 (C1 at 60x4) failed with ENOMEM at thread 87 of 240 under `card_run`'s
6 GB limit (`work/tickets/S8-01.md:55-57`). `card_run` applies the limit as `RLIMIT_AS`, which
bounds reserved virtual address space, not resident memory (`tools/claude-pin.c:50-55`), with a
budget of at most 10,240 MiB (`tools/card_run:24`). **Proven.** glibc 2.21's malloc gives a
thread that calls malloc while the main arena is busy its own arena, whose heap is an `mmap`
reservation of `HEAP_MAX_SIZE` = 64 MB on 64-bit; the default arena cap is 8 x cores
(`NARENAS_FROM_NCORES`), about 1,900 on a 244-CPU card, so up to 240 threads each get one:
87 x 64 MB is about 5.6 GB, which matches the failure point. **Inferred** from glibc 2.21 source
behaviour and the job 19 arithmetic. `malloc.h` exposes `M_ARENA_MAX` (-8) and `M_ARENA_TEST` (-7)
(`sysroot/usr/include/malloc.h:117-118`), and glibc 2.21 reads `MALLOC_ARENA_MAX` from the
environment. **Proven** header, **inferred** env support. Thread stacks reserve address space too:
the pthread default is the `RLIMIT_STACK` soft limit (commonly 8 MB), so 240 threads reserve
about 1.9 GB more unless `OMP_STACKSIZE`/`GOMP_STACKSIZE` is set (`env.c:2458-2492`;
`PTHREAD_STACK_MIN` is 16 KB, `bits/local_lim.h:81`). **Inferred.**

**What libgomp itself allocates in workers.** Team, pool and work-share blocks are allocated by
the master (`team.c:181-184`, `work.c:82-86`); `gomp_thread_start` allocates nothing
(`team.c:70-135`); explicit tasks are allocated by the thread that creates them (`task.c`), and
`omp_alloc` by the caller. A libgomp program without tasks or user malloc in workers creates no
extra arenas; one `malloc` per worker is enough to reserve 64 MB each. **Proven for the code
paths named, inferred for the arena effect.**

**Historical recommendation, superseded by ADR-0012 (S12-13 annotation).** libgomp must not call `mallopt` on the program's behalf: it changes the
program's allocator behaviour globally and a library has no standing to do that. It should
document, in the KNC section of the libgomp manual page and in `omp_display_env` output, the two
knobs: `MALLOC_ARENA_MAX=60` (one arena per core, 3.75 GB reserved, no serialization across cores)
as the setting for 240 threads under `RLIMIT_AS`, and `OMP_STACKSIZE=2M` or similar for the stacks;
`MALLOC_ARENA_MAX=1` is the wrong fix because it funnels 240 threads through one arena mutex.
`card_run` jobs that start 240 threads should set both in the job line. **Design.**

**Current correction:** `card.h` `gomp_knc_arena_cap` derives a cap and startup
applies it unless `MALLOC_ARENA_MAX` is set. Finite address-space/strict-commit
budgets account for stacks and a 512 MiB reserve; without either budget it
uses one arena per allowed CPU. Its comment reports about 169 arenas faster
than 60–64 on a malloc-heavy case. Neither 60 nor 64 is universally fastest,
and one arena/core does not guarantee absence of lock contention. R24a
`new_heap`/`arena_get2` and R24b `mallopt` establish virtual reservation and
upstream allocator mechanisms, not installed MPSS behavior; code has no page
number. R19 pp.376–377's first-touch NUMA example is a Xeon host, not a KNC
placement proof. The digest lists the ADR-0012 unlimited-budget wording
discrepancy for the lead; no ADR or allocator change is made here.

Measurement item 7 (lead): 240 threads each doing 100,000 `malloc`/`free` of 1 KiB, with
`MALLOC_ARENA_MAX` unset, 60, 8 and 1; record `VmPeak` and `VmRSS` from `/proc/self/status` and
the wall time; and the same program at 60 and 120 threads.

## Recommended E6-03 implementation tickets

Five tickets in dependency order; A first and alone in the gcc lane (it changes `configure.tgt`
and the install), then B and C in parallel on the built runtime, then D, then E. Each lists its
acceptance (host, red first) and the card checks the lead runs. Engineers stage card binaries under
`.work/_shared/<ticket>/` and never run them.

**A. Build, select and package libgomp for k1om** (deep, gcc lane). Add the `k1om-*-linux*`
case to `libgomp/configure.tgt` with `config_path="linux/knc linux/x86 linux posix"`; add
`config/linux/knc/futex.h` (x86 syscall asm, `cpu_relax` = `delay` with a runtime count) and
`config/linux/knc/spincount.h` (KNC default spin count, no CPUID probe); drop `--disable-libgomp`
from the shared build's configure; install `libgomp.so.1`, `libgomp.a`, `omp.h`, `omp_lib*` into
the private prefix; k1om `libgomp.spec` naming `libgomp-knc.ld` with the `GOMP_6.0` ASSERT guard.
Acceptance: `configure` reports futex yes and `config_path` as above (red: today's `posix`);
`readelf` shows SONAME `libgomp.so.1`, version nodes up to `GOMP_6.0.1`, `RPATH $ORIGIN/../lib` on a
linked program and `DT_NEEDED` only from the prefix; the disassembly lint finds `delay` and no
`pause`, `cmpxchg16b` or SSE; six staged programs (parallel for with static and dynamic schedule,
reduction, critical and atomic, single and ordered, tasks with taskwait, nested locks and
`omp_get_wtime`) in C and two in Fortran link statically and shared; the negative link against a
directory holding an older `libgomp.so.1` stub fails with the guard text. Card checks: the eight
programs at 60x1 and 60x4 with `OMP_DISPLAY_ENV=verbose`; `LD_DEBUG=libs` or `/proc/self/maps`
shows one libgomp from the prefix and no `libiomp5`; `ls /lib64 /opt/intel* 2>/dev/null | grep
-i 'gomp\|iomp'` and `readelf -d -V` on whatever it finds (answers section 2's unknown); `cat
/sys/devices/system/cpu/cpu1/topology/thread_siblings_list` and `core_siblings_list` (section 3's
unknown); `OMP_WAIT_POLICY=passive` shows low CPU time in `/proc/self/stat` (futex path live).

**B. KNC affinity defaults** (deep). `config/linux/knc/affinity.c` or a KNC branch: core places
from sysfs with the `/proc/cpuinfo` fallback, intersect with the inherited mask, drop the OS core,
default `spread`; `OMP_PROC_BIND=false` opts out; `OMP_PLACES`/`GOMP_CPU_AFFINITY` unchanged.
Acceptance: host unit tests of the place builder against a fixture tree (a captured card
`/proc/cpuinfo` and a synthetic sysfs) for 244 CPUs, for a 120-CPU mask, and for a mask that
contains only the OS core; `omp_get_num_procs`, `omp_get_num_places`, `omp_get_place_num_procs`
agree with the fixture. Card checks: `OMP_DISPLAY_AFFINITY=true` at 60, 120 and 240 threads prints
1, 2 and 4 threads per core with no thread on CPU 0 or 241-243; under a 30-core `card_run` mask all
threads stay inside it; `OMP_PLACES="{1:4}:60:4"` and `GOMP_CPU_AFFINITY="1-237:4"` give the
table in section 3.

**C. Spin with `delay` and the one-core measurement** (small). `gomp_knc_delay` with
`GOMP_KNC_DELAY`, the KNC spin-count default, `omp_display_env` lines for both. Acceptance: T1 scan
of the built `libgomp.so.1` for `delay` in `do_spin`'s inlined loop and no `pause`; env parsing
tests red then green. Card checks: measurement 1 (worker alone vs 1-3 spinning siblings, no hint
vs `delay` 32/128/512) and 3 (fork/join at 60x4 under the three wait policies); the lead sets the
default from the result and records it in `knc-characterization.md`.

**D. Hierarchical barrier** (deep). `config/linux/knc/bar.h`, `bar.c` and `simple-bar.h` per
section 4: groups fixed by the master in `gomp_barrier_init` from `team_id` and `total`, root
counter, per-group mirror words refreshed by the root release, `gomp_team_barrier_wake` and
`gomp_team_barrier_cancel`, the root alone holding the `BAR_*` flags, the dock on the flat type,
same `gomp_barrier_t` API. Acceptance: the barrier compiles into an x86_64 host unit test (same
sources, `gomp_knc_ncores` set from the test) that runs 240 pthreads through 100,000 barriers
with a generation check, in four variants: (a) plain; (b) tasks: with `GOMP_SPINCOUNT=0` so
waiters park in `futex_wait` on their group words, a late thread queues work through the
`gomp_team_barrier_set_task_pending` plus `gomp_team_barrier_wake (bar, 1)` sequence while the
others are parked, and the test checks that a parked thread wakes and that the barrier still
completes once the queue drains; the same with spinning waiters; (c) cancel: one thread calls
`gomp_team_barrier_cancel` while others are parked and spinning in `gomp_team_barrier_wait_cancel`,
and all must return true; (d) wake ordering: the release is forced between a thread's root read
and its `futex_wait` (a hook in the test build) and no thread hangs. Plus the libgomp testsuite's
barrier, task, taskwait, cancel and `single`/`ordered` tests cross-compiled and staged (red: the
host stress test fails on a deliberately broken mirror write); no change outside
`config/linux/knc/`. Card checks: measurements 2 (flat vs two-level at 60x1, 60x2, 60x4), 4 and 5;
the staged testsuite subset passes at 60x4 with `OMP_WAIT_POLICY` unset and `passive`; a tasks
program with 10,000 tasks and one with `cancel parallel` pass at 60x4.

**E. Padding, schedule default and the malloc documentation** (small). Section 5's padding of
`gomp_tls_data`, `implicit_task` and the group lines; `run_sched_var` default
`GFS_STATIC` for KNC; the manual text and `omp_display_env` hint for `MALLOC_ARENA_MAX` and
`OMP_STACKSIZE`; a staged reduction microbenchmark (atomic path, lock path, padded partials) and a
staged malloc microbenchmark. Acceptance: static asserts on sizes and offsets red then green; a
host test that `schedule(runtime)` with no `OMP_SCHEDULE` reports static; `omp_display_env` output
test. Card checks: measurements 6 and 7; the eight programs from A still pass at 60x4. The result of
6 decides whether a compiler ticket (omp-low.cc tree combine) is opened.

## Risks

- **Configure may still pick `posix`.** The futex link test (`config/futex.m4:22-46`) runs with
  our cross compiler against the sysroot; if it fails, `enable_linux_futex` is `no` and the whole
  futex block is skipped regardless of the new case. Ticket A's acceptance checks `config_path`
  explicitly, and `--enable-linux-futex` forces the test to error loudly instead (`futex.m4:48-56`).
- **`delay` may be a NOP or exit early.** The ISA allows both (lines 24655-24660). Measurement 1
  decides; if `delay` does not help, the fallback is a lower spin count plus earlier `futex_wait`.
- **sysfs topology may be missing on 2.6.38.** B's `/proc/cpuinfo` fallback covers it; the card
  check in A finds out before B starts.
- **Tasks and cancellation interact with the barrier generation word.** D keeps the flags on the
  root and mirrors them into the group words at every wake; the residual risk is a `task.c` path
  that changes the root without calling `gomp_team_barrier_wake` (none found in GCC 16, but a
  forward port must re-check the list in section 4). The host stress variants (b) to (d) run
  before the card run.
- **The dock stays flat in D.** Fork/join still pays 240 polls of one line at the dock release;
  measurement 3 decides whether a dock follow-up is worth a ticket.
- **Address space at 240 threads.** Even with our libgomp, a program that mallocs in workers
  reserves 64 MB per thread; the knobs in E are documentation, not enforcement. `card_run` job lines
  for 60x4 should set `MALLOC_ARENA_MAX` and `OMP_STACKSIZE` or raise the memory budget.
- **A second runtime from a foreign dependency.** The link guard catches an old `libgomp.so.1`
  but not `libiomp5.so` pulled by another library; the load-time check in A's card job is the only
  detection, and the rule is to build everything with GCC-KNC.
- **ABI exposure.** `omp.h`'s `omp_lock_t` is an `int` and `omp_nest_lock_t` a 16-byte struct
  (`config/linux/omp-lock.h:9-12`), identical to the x86_64 Linux layout a GCC 5 or Intel runtime
  uses; nothing in A-E changes installed headers or the exported symbol set, so the private-prefix
  rule, not the ABI, is what keeps the runtimes apart.
