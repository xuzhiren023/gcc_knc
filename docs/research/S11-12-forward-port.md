## PR128640 interaction review

Reviewed upstream gcc-16 commit `0be7752b59a` (master original
`19c7fe8874c`) against KNC `619e14b479a`, in
`gcc/config/i386/i386.cc` and `gcc/config/i386/i386-knc.cc`.
The change replaces vector-mode lists with classification in
`function_arg_advance_64`, `function_arg_64` and `ix86_gimplify_va_arg`,
and adds a checking assertion in the classifier wrapper. This also catches
aggregates containing a wide vector when deciding unnamed-argument transport.

The gcc-16 drill has no textual conflict in `i386.cc`; this does not by itself
validate its ABI behavior. Preserve KNC's early classifier rejection, including
the V16HI memory rule, and the argument/va_arg rejection hooks when porting.
KNC's `ix86_knc_check_abi_arg` rejects packed vector arguments in variadic
functions, including named arguments; `ix86_knc_check_va_arg_type` rejects
packed vector extraction. The recursive unsupported-type check rejects
aggregates containing packed vectors. Those restrictions must remain ahead of
the new generic classification logic. V16HI classification returns zero before
the wrapper's new assertion and before the unnamed-argument class-count check;
its existing memory transport must remain intact.

Master conflicts in `i386.cc` include the `ix86_pass_by_reference` KNC check
and KNC vector costs. A future resolution must retain the KNC argument check
alongside upstream's argument-hook changes and preserve the va_arg guard.
This is source inspection only: no merged compiler was built or tested, and
no upstream change was installed into either prefix for this batch check.

## 2026-11-14T16:56:24+00:00

Base: `releases/gcc-16.2.0`; KNC: `619e14b479a952edff32e94f22573710d0b8ac17`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `fceddda853fa2543b6d3ddbbe75f7e2468521a91`; date: 2026-11-14T12:21:36+01:00.

Conflicts: 14

#### `gcc/config/i386/i386-c.cc`

```diff
<<<<<<< upstream/master
  /* For some of the k6/pentium variants there weren't separate ISA bits to
=======
  if (isa_flag & OPTION_MASK_ISA_KNC)
    arch = ix86_knc_target_macros (parse_in, def_or_undef);

  /* For some of the k6/pentium varients there weren't separate ISA bits to
>>>>>>> knc
```

#### `gcc/config/i386/i386-options.cc`

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
      case ix86_veclibabi_type_hvml:
	ix86_veclib_handler = &ix86_veclibabi_hvml;
=======
      case ix86_veclibabi_type_knc:
	ix86_veclib_handler = &ix86_knc_veclibabi;
>>>>>>> knc
```

#### `gcc/config/i386/i386-options.h`

```diff
<<<<<<< upstream/master
extern tree ix86_veclibabi_hvml (combined_fn, tree, tree);
=======
extern tree ix86_knc_veclibabi (combined_fn, tree, tree);
>>>>>>> knc
```

#### `gcc/config/i386/i386-opts.h`

```diff
<<<<<<< upstream/master
  ix86_veclibabi_type_hvml
=======
  ix86_veclibabi_type_knc
>>>>>>> knc
```

#### `gcc/config/i386/i386.cc`

```diff
<<<<<<< upstream/master
=======
  if (TARGET_KNC && !ix86_knc_check_abi_arg (get_cumulative_args (cum_v), arg))
    return true;
  CUMULATIVE_ARGS *cum = get_cumulative_args (cum_v);

>>>>>>> knc
```

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* Only gather/scatter needs statement-specific KNC costs here.  Other
     KNC defaults have already received the x86 lowering adjustments.  */
  if (TARGET_KNC
      && (kind == vector_gather_load || kind == vector_scatter_store))
    {
      int cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
      if (cost >= 0)
        stmt_cost = cost;
    }
  /* ADR-0009 amendment 1 point 9: a KNC masked access of unknown
     alignment is a gather or scatter.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
  /* ADR-0008 point 1: a two-input KNC permute is vpermd plus vpermd.  */
  if (TARGET_KNC && kind == vec_perm
      && ix86_knc_two_input_perm_p (mode, stmt_info, node))
    stmt_cost *= 2;
>>>>>>> knc
```

#### `gcc/config/i386/i386.opt`

```diff
<<<<<<< upstream/master
Enum(ix86_veclibabi) String(hvml) Value(ix86_veclibabi_type_hvml)
=======
Enum(ix86_veclibabi) String(knc) Value(ix86_veclibabi_type_knc)
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
mavx10v2aux
Target Mask(ISA2_AVX10V2AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V2AUX built-in functions and code generation.

macev1
Target Mask(ISA2_ACEV1) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and ACEV1 built-in functions and code generation.

mavx10v1aux
Target Mask(ISA2_AVX10V1AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V1AUX built-in functions and code generation.
=======
-param=knc-threads-per-core=
Target Joined UInteger Var(knc_threads_per_core) Init(4) IntegerRange(1, 4) Param Optimization
Assumed active KNC threads per core for latency hiding (1 to 4, default 4).

-param=knc-prefetch-l1-distance=
Target Joined UInteger Var(knc_prefetch_l1_distance) Init(16) IntegerRange(1, 4096) Param Optimization
KNC L1 software prefetch distance in cache lines (default 16; halved when distance x streams x threads per core exceeds a quarter of L1; kept below the L2 distance).

-param=knc-prefetch-l2-distance=
Target Joined UInteger Var(knc_prefetch_l2_distance) Init(32) IntegerRange(1, 4096) Param Optimization
KNC L2 software prefetch distance in cache lines (default 32).

mphinix
Target Driver RejectNegative Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: -O3 and the measured GCC-KNC defaults in one flag, with a banner and a progress bar on a terminal; IEEE semantics stay.

mphinix-banner
Target Driver Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: print the -mphinix banner on a terminal (default on).

mknc-card=
Target Driver Joined RejectNegative Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: tune for a card model: generic (default), 3100, 5100, 7100, a card name such as 7120P, or native.

mprogress
Target Driver Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: draw a progress bar, one step per driver job, on a terminal (default with -mphinix).

Wknc-unsafe-cbrtl
Common Var(warn_knc_unsafe_cbrtl) Init(1) Warning
Warn when KNC replaces an unsafe MPSS long double cube root call.
>>>>>>> knc
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
   (V16SF "TARGET_AVX512F") (V8SF "TARGET_AVX") V4SF
   (V8DF "TARGET_AVX512F") (V4DF "TARGET_AVX") (V2DF "TARGET_SSE2")
   (V8DI "TARGET_AVX512F") (V4DI "TARGET_AVX") (V2DI "TARGET_SSE2")
   (V16SI "TARGET_AVX512F") (V8SI "TARGET_AVX") (V4SI "TARGET_SSE2")
   (V32HI "TARGET_AVX512F") (V16HI "TARGET_AVX") (V8HI "TARGET_SSE2")
   (V64QI "TARGET_AVX512F") (V32QI "TARGET_AVX") (V16QI "TARGET_SSE2")])
=======
   (V8DI "TARGET_AVX512F || TARGET_KNC") (V4DI "TARGET_AVX") (V2DI "TARGET_SSE2")
   (V16SF "TARGET_AVX512F || TARGET_KNC") (V8SF "TARGET_AVX") V4SF
   (V8DF "TARGET_AVX512F || TARGET_KNC") (V4DF "TARGET_AVX") (V2DF "TARGET_SSE2")
   (V16SI "TARGET_KNC")])
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_expand_cond_fma (operands, false, false);
=======
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_cond_fma (<MODE>mode, operands[0], operands[1],
				   operands[2], operands[3], operands[4],
				   operands[5]));
      DONE;
    }
  rtx tmp = gen_reg_rtx (<MODE>mode);
  emit_insn (gen_fma<mode>4 (tmp,
			     operands[2],
			     operands[3],
			     operands[4]));
  emit_move_insn (operands[0], gen_rtx_VEC_MERGE (<MODE>mode,
						  tmp,
						  operands[5],
						  operands[1]));
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
{
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_plusminus (<CODE>, <MODE>mode, operands[0],
				    operands[1], operands[2]));
      DONE;
    }
>>>>>>> knc
```

#### `gcc/configure`

```diff
<<<<<<< upstream/master
  i?86-*-* | x86_64-*-*)
    if test x$as_flavor = xsolaris; then
      tls_section_flag=t
=======
  i?86-*-* | x86_64-*-* | k1om-*-linux*)
    case "$target:$gas" in
      i?86-*-solaris2*:no | x86_64-*-solaris2*:no)
	tls_section_flag=t
>>>>>>> knc
```

#### `gcc/configure.ac`

```diff
<<<<<<< upstream/master
  i?86-*-* | x86_64-*-*)
    if test x$as_flavor = xsolaris; then
      tls_section_flag=t
=======
  i?86-*-* | x86_64-*-* | k1om-*-linux*)
    case "$target:$gas" in
      i?86-*-solaris2*:no | x86_64-*-solaris2*:no)
	tls_section_flag=t
>>>>>>> knc
```

#### `libgfortran/configure`

```diff
<<<<<<< upstream/master
#line 13240 "configure"
=======
#line 13250 "configure"
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 13346 "configure"
=======
#line 13356 "configure"
>>>>>>> knc
```

#### `libgomp/configure`

```diff
<<<<<<< upstream/master
=======
USE_FORTRAN_FALSE
USE_FORTRAN_TRUE
LIBGOMP_RUNTIME_GUARD_FILE
>>>>>>> knc
```

#### `libgomp/env.c`

```diff
<<<<<<< upstream/master
      fputs ("  [all] GOMP_RUNTIME_USM = '", stderr);
      switch (gomp_runtime_usm_var)
	{
	case GOMP_RUNTIME_USM_DISABLED:
	  fputs ("DISABLED", stderr);
	  break;
	case GOMP_RUNTIME_USM_AUTO:
	  fputs ("AUTO", stderr);
	  break;
	case GOMP_RUNTIME_USM_ENABLED:
	  fputs ("ENABLED", stderr);
	  break;
	}
      fputs ("'\n", stderr);
      fprintf (stderr, "  [host] GOMP_BARRIER_TYPE = '%s'\n",
	       gomp_barrier_request == GOMP_FLAT_BARRIER   ? "flat"
	       : gomp_barrier_request == GOMP_TREE_BARRIER ? "tree"
	       : gomp_barrier_request == GOMP_CENTRALIZED_BARRIER
		 ? "centralized"
		 : "auto");
      fprintf (stderr, "  [host] GOMP_FORKJOIN_BARRIER_TYPE = '%s'\n",
	       gomp_forkjoin_barrier_request == GOMP_FLAT_BARRIER   ? "flat"
	       : gomp_forkjoin_barrier_request == GOMP_TREE_BARRIER ? "tree"
	       : gomp_forkjoin_barrier_request == GOMP_CENTRALIZED_BARRIER
		 ? "centralized"
		 : "auto");
=======
#ifdef __k1om__
      gomp_knc_display_delay (stderr);
      gomp_knc_display_malloc (stderr);
#endif
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  parse_barrier_choice ("GOMP_BARRIER_TYPE", &gomp_barrier_request);
  gomp_forkjoin_barrier_request = gomp_barrier_request;
  parse_barrier_choice ("GOMP_FORKJOIN_BARRIER_TYPE",
			&gomp_forkjoin_barrier_request);
=======
#ifdef __k1om__
  gomp_knc_init_arenas ((none != NULL
			 && gomp_get_icv_flag (none->flags, GOMP_ICV_STACKSIZE))
			|| (all != NULL
			    && gomp_get_icv_flag (all->flags,
						  GOMP_ICV_STACKSIZE)));
#endif
>>>>>>> knc
```

#### `libgomp/libgomp.h`

```diff
<<<<<<< upstream/master
#ifdef __AMDGCN__
/* Parameters needed to kick off new threads on AMD GCN.  They correspond to
   various fields in gomp_thread.  This struct, and all its contents, should
   only be modified by gomp_team_start, and stay untouched until the threads
   of a team reach the final barrier.  */

struct gomp_thread_start_data
{
  /* Team the new thread is part of.  */
  struct gomp_team *team;
  /* Active nesting level.  */
  unsigned level, active_level;
  /* Parent task.  */
  struct gomp_task *parent_task;
  /* Previous ICVs.  */
  struct gomp_task_icv prev_icvs;
  /* Task group for the new threads implicit task.  */
  struct gomp_taskgroup *taskgroup;
};
=======
#ifdef __k1om__
/* KNC: a member that starts a cache line of its own.  */
#define GOMP_KNC_LINE __attribute__((aligned (64)))
#else
#define GOMP_KNC_LINE
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#ifdef __AMDGCN__
  /* Used on AMD GCN to inform threads how to launch in a team.  */
  struct gomp_thread_start_data thr_start_data;
#elif LIBGOMP_USE_PTHREADS
  /* Cache to help initialise each secondary threads `task` when re-using a
     team very many times.  This allows each secondary thread to perform the
     re-initialisation instead of having the primary thread need to perform
     that initialisation.  */
  struct thread_init {
    struct gomp_task_icv task_icv_init;
    struct gomp_task *task_parent_init;
    struct gomp_taskgroup *task_taskgroup;
    uintptr_t def_allocator;
    unsigned int num_teams;
    unsigned int team_num;
    void (*fn) (void *data);
    void *data;
  } ti;
  struct prev_place_vars {
    unsigned int place_partition_off;
    unsigned int place_partition_len;
    char bind;
  } ppv;
#endif
  bool reused;

  /* This array contains structures for implicit tasks.  */
  struct gomp_task implicit_task[];
=======
  /* This array contains structures for implicit tasks.  Use
     gomp_implicit_task to index it.  */
  struct gomp_task implicit_task[] GOMP_KNC_LINE;
>>>>>>> knc
```

#### `libgomp/team.c`

```diff
<<<<<<< upstream/master
		     + sizeof (team->implicit_task[0]);
      size_t team_extra = nthreads * extra;
      size_t barrier_padding = 0;
      if (barrier_extra_alloc.size)
	{
	  /* `offsetof` in case the structure is padded and `implicit_task` is
	     not at the end of `sizeof (*team)`.  */
	  size_t barrier_offset
	    = offsetof (struct gomp_team, implicit_task) + team_extra;
	  gomp_assert (barrier_extra_alloc.align
			 <= __alignof (struct gomp_team),
		       "barrier extra alignment too large: %lu > %lu",
		       (unsigned long) barrier_extra_alloc.align,
		       (unsigned long) __alignof (struct gomp_team));
	  barrier_padding = ((barrier_offset + barrier_extra_alloc.align - 1)
			     & ~(barrier_extra_alloc.align - 1))
			    - barrier_offset;
	}
      size_t alloc_extra
	= team_extra + barrier_padding + barrier_extra_alloc.size;
=======
		     + GOMP_IMPLICIT_TASK_STRIDE;
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
	  nthr->place = place;
=======
	  nthr->ts.def_allocator = thr->ts.def_allocator;
#ifdef HAVE_SYNC_BUILTINS
	  nthr->ts.single_count = 0;
#endif
	  nthr->ts.static_trip = 0;
	  nthr->num_teams = thr->num_teams;
	  nthr->team_num = thr->team_num;
	  nthr->task = gomp_implicit_task (team, i);
	  nthr->place = place;
	  gomp_init_task (nthr->task, task, icv);
	  gomp_implicit_task (team, i)->icv.nthreads_var = nthreads_var;
	  gomp_implicit_task (team, i)->icv.bind_var = bind_var;
	  nthr->task->taskgroup = taskgroup;
	  nthr->fn = fn;
	  nthr->data = data;
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
      start_data->team = team;
      start_data->team_id = i;

      start_data->active_level = thr->ts.active_level;
=======
      start_data->fn = fn;
      start_data->fn_data = data;
      start_data->ts.team = team;
      start_data->ts.work_share = &team->work_shares[0];
      start_data->ts.last_work_share = NULL;
      start_data->ts.team_id = i;
      start_data->ts.level = team->prev_ts.level + 1;
      start_data->ts.active_level = thr->ts.active_level;
      start_data->ts.def_allocator = thr->ts.def_allocator;
#ifdef HAVE_SYNC_BUILTINS
      start_data->ts.single_count = 0;
#endif
      start_data->ts.static_trip = 0;
      start_data->num_teams = thr->num_teams;
      start_data->team_num = thr->team_num;
      start_data->task = gomp_implicit_task (team, i);
      gomp_init_task (start_data->task, task, icv);
      gomp_implicit_task (team, i)->icv.nthreads_var = nthreads_var;
      gomp_implicit_task (team, i)->icv.bind_var = bind_var;
      start_data->task->taskgroup = taskgroup;
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +67 | -22 |
| `gcc/config.gcc` | +93 | -158 |
| `gcc/config.host` | +10 | -2 |
| `gcc/config/i386/i386-builtins.cc` | +46 | -6 |
| `gcc/config/i386/i386-c.cc` | +10 | -5 |
| `gcc/config/i386/i386-expand.cc` | +3467 | -512 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +142 | -91 |
| `gcc/config/i386/i386-options.h` | +1 | -0 |
| `gcc/config/i386/i386-opts.h` | +2 | -1 |
| `gcc/config/i386/i386-passes.def` | +0 | -0 |
| `gcc/config/i386/i386-protos.h` | +21 | -16 |
| `gcc/config/i386/i386.cc` | +1461 | -566 |
| `gcc/config/i386/i386.h` | +75 | -51 |
| `gcc/config/i386/i386.md` | +2634 | -1549 |
| `gcc/config/i386/i386.opt` | +24 | -6 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/knc-driver.cc` | +0 | -0 |
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +2025 | -695 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/t-knc` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +1 | -1 |
| `gcc/configure` | +1052 | -923 |
| `gcc/configure.ac` | +368 | -379 |
| `gcc/cp/g++spec.cc` | +7 | -1 |
| `gcc/doc/tm.texi` | +200 | -69 |
| `gcc/doc/tm.texi.in` | +73 | -39 |
| `gcc/gcc.cc` | +160 | -59 |
| `gcc/params.opt` | +23 | -5 |
| `gcc/target.def` | +170 | -39 |
| `gcc/testsuite/g++.target/i386/knc-unsafe-cbrtl-pragma.C` | +0 | -0 |
| `gcc/testsuite/gcc.target/i386/knc-slp-width.c` | +0 | -0 |
| `gcc/testsuite/gcc.target/i386/knc-unsafe-cbrtl-pragma.c` | +0 | -0 |
| `gcc/testsuite/gfortran.dg/knc-ltgt-mask.f90` | +0 | -0 |
| `gcc/testsuite/gfortran.dg/knc-rrtm-reload.LICENSE` | +0 | -0 |
| `gcc/testsuite/gfortran.dg/knc-rrtm-reload.f90` | +0 | -0 |
| `gcc/tree-ssa-loop-ivcanon.cc` | +9 | -11 |
| `gcc/tree-ssa-loop-ivopts.cc` | +290 | -97 |
| `gcc/tree-ssa-loop-prefetch.cc` | +20 | -12 |
| `libgcc/config.host` | +14 | -23 |
| `libgcc/config/i386/knc-cbrtl.c` | +0 | -0 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +2 | -1 |
| `libgfortran/Makefile.in` | +7 | -2 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +206 | -23 |
| `libgfortran/configure.ac` | +18 | -11 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |
| `libgomp/Makefile.am` | +7 | -5 |
| `libgomp/Makefile.in` | +32 | -25 |
| `libgomp/config/linux/knc/affinity.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/card.h` | +0 | -0 |
| `libgomp/config/linux/knc/futex.h` | +0 | -0 |
| `libgomp/config/linux/knc/guard.ld` | +0 | -0 |
| `libgomp/config/linux/knc/mutex.c` | +0 | -0 |
| `libgomp/config/linux/knc/simple-bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/spincount.h` | +0 | -0 |
| `libgomp/configure` | +134 | -274 |
| `libgomp/configure.ac` | +86 | -33 |
| `libgomp/configure.tgt` | +19 | -16 |
| `libgomp/env.c` | +146 | -6 |
| `libgomp/libgomp.h` | +159 | -11 |
| `libgomp/libgomp.texi` | +1099 | -153 |
| `libgomp/team.c` | +462 | -101 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/baseline_symbols.txt` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc-static.ld` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc.ld` | +0 | -0 |
| `libstdc++-v3/src/Makefile.am` | +20 | -0 |
| `libstdc++-v3/src/Makefile.in` | +22 | -1 |

### upstream/releases/gcc-16

Commit: `0be7752b59a68e42415826e2632719ffbfe350c8`; date: 2026-11-13T17:36:44-08:00.

Conflicts: 4

#### `gcc/config/i386/i386-options.cc`

```diff
<<<<<<< upstream/releases/gcc-16
      case ix86_veclibabi_type_hvml:
	ix86_veclib_handler = &ix86_veclibabi_hvml;
=======
      case ix86_veclibabi_type_knc:
	ix86_veclib_handler = &ix86_knc_veclibabi;
>>>>>>> knc
```

#### `gcc/config/i386/i386-options.h`

```diff
<<<<<<< upstream/releases/gcc-16
extern tree ix86_veclibabi_hvml (combined_fn, tree, tree);
=======
extern tree ix86_knc_veclibabi (combined_fn, tree, tree);
>>>>>>> knc
```

#### `gcc/config/i386/i386-opts.h`

```diff
<<<<<<< upstream/releases/gcc-16
  ix86_veclibabi_type_hvml
=======
  ix86_veclibabi_type_knc
>>>>>>> knc
```

#### `gcc/config/i386/i386.opt`

```diff
<<<<<<< upstream/releases/gcc-16
Enum(ix86_veclibabi) String(hvml) Value(ix86_veclibabi_type_hvml)
=======
Enum(ix86_veclibabi) String(knc) Value(ix86_veclibabi_type_knc)
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +3 | -1 |
| `gcc/config.gcc` | +0 | -0 |
| `gcc/config.host` | +0 | -0 |
| `gcc/config/i386/i386-builtins.cc` | +0 | -0 |
| `gcc/config/i386/i386-c.cc` | +3 | -2 |
| `gcc/config/i386/i386-expand.cc` | +23 | -10 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +4 | -0 |
| `gcc/config/i386/i386-options.h` | +1 | -0 |
| `gcc/config/i386/i386-opts.h` | +2 | -1 |
| `gcc/config/i386/i386-passes.def` | +0 | -0 |
| `gcc/config/i386/i386-protos.h` | +0 | -0 |
| `gcc/config/i386/i386.cc` | +260 | -111 |
| `gcc/config/i386/i386.h` | +0 | -0 |
| `gcc/config/i386/i386.md` | +73 | -28 |
| `gcc/config/i386/i386.opt` | +3 | -0 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/knc-driver.cc` | +0 | -0 |
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/t-knc` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `gcc/cp/g++spec.cc` | +0 | -0 |
| `gcc/doc/tm.texi` | +0 | -0 |
| `gcc/doc/tm.texi.in` | +0 | -0 |
| `gcc/gcc.cc` | +0 | -0 |
| `gcc/params.opt` | +0 | -0 |
| `gcc/target.def` | +0 | -0 |
| `gcc/testsuite/g++.target/i386/knc-unsafe-cbrtl-pragma.C` | +0 | -0 |
| `gcc/testsuite/gcc.target/i386/knc-slp-width.c` | +0 | -0 |
| `gcc/testsuite/gcc.target/i386/knc-unsafe-cbrtl-pragma.c` | +0 | -0 |
| `gcc/testsuite/gfortran.dg/knc-ltgt-mask.f90` | +0 | -0 |
| `gcc/testsuite/gfortran.dg/knc-rrtm-reload.LICENSE` | +0 | -0 |
| `gcc/testsuite/gfortran.dg/knc-rrtm-reload.f90` | +0 | -0 |
| `gcc/tree-ssa-loop-ivcanon.cc` | +0 | -0 |
| `gcc/tree-ssa-loop-ivopts.cc` | +8 | -3 |
| `gcc/tree-ssa-loop-prefetch.cc` | +0 | -0 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-cbrtl.c` | +0 | -0 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +0 | -0 |
| `libgfortran/Makefile.in` | +0 | -0 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +0 | -0 |
| `libgfortran/configure.ac` | +0 | -0 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |
| `libgomp/Makefile.am` | +0 | -0 |
| `libgomp/Makefile.in` | +0 | -0 |
| `libgomp/config/linux/knc/affinity.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/card.h` | +0 | -0 |
| `libgomp/config/linux/knc/futex.h` | +0 | -0 |
| `libgomp/config/linux/knc/guard.ld` | +0 | -0 |
| `libgomp/config/linux/knc/mutex.c` | +0 | -0 |
| `libgomp/config/linux/knc/simple-bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/spincount.h` | +0 | -0 |
| `libgomp/configure` | +0 | -0 |
| `libgomp/configure.ac` | +0 | -0 |
| `libgomp/configure.tgt` | +0 | -0 |
| `libgomp/env.c` | +0 | -0 |
| `libgomp/libgomp.h` | +0 | -0 |
| `libgomp/libgomp.texi` | +0 | -0 |
| `libgomp/team.c` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/baseline_symbols.txt` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc-static.ld` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc.ld` | +0 | -0 |
| `libstdc++-v3/src/Makefile.am` | +0 | -0 |
| `libstdc++-v3/src/Makefile.in` | +0 | -0 |

