# GPT Pro essays, 2026-11-15: structured outline (owner-provided, untrusted until checked)

Source: two responses the owner obtained from GPT Pro on 2026-11-15 and pasted to the GCC-KNC lead. This is a
faithful outline of every proposal, formula and claim, one line each, not a verbatim copy. Nothing here is a project
fact until checked; the evidence status of each item is in `docs/research/gpt-pro-2026-11-15-triage.md`.

## Essay 1: broad optimization for gcc-knc (classes, latency hiding, LLM kernels)

### Framing
- E1.0a Use H/S/N/C/G/B as coverage labels; optimize each hot region by what actually stalls it.
- E1.0b Goal broader than fast numerical loops: recover parallelism hidden by source structure, schedule it for KNC, adapt at run time when compile-time knowledge is missing.
- E1.0c Four mechanisms: (1) remove avoidable control decisions before the hot loop; (2) arrange independent instructions in advance for the in-order core; (3) asynchronous prefetch, hardware threads and coarse task scheduling for variable latency; (4) change the dependency structure where algebra or verified speculation permits. (4) is the largest conceptual opportunity.
- E1.0d gcc-knc already vectorizes; next target is how well vector kernels use issue slots, registers, caches and independent work.

### 1. Taxonomy refinement
- E1.1a Classes describe different dimensions (H/S domain, N/C source style, G origin, B behaviour); keep as overlapping labels.
- E1.1b PolyBench is evidence for regular static-control kernels, not for already-tuned libraries (BLAS-style).
- E1.1c Split G into generated arithmetic and generated control flow.
- E1.1d C++ syntax is not runtime abstraction overhead; templates/iterators may vanish; unresolved virtual calls and opaque boundaries are the real problem (GCC has inlining, devirtualization, guarded indirect-target promotion).
- E1.1e Per-class opportunity table (H scheduling/register blocking/prefetch; S expose independent cells/rows, library calls, specialization; N recover structure via alias analysis, scalar replacement, loop transforms, inlining, guarded specialization; C remove/specialize abstractions; G arithmetic: scheduling and registers, state machines: path specialization, compact dispatch, transition fusion; B profile-guided control flow, traversal overlap, layout, batching).
- E1.1f NPB members differ (CG irregular memory/communication, IS random memory, EP embarrassingly parallel); one "science policy" misses this.
- E1.1g Per hot region measure seven properties: control uncertainty, dependency depth, available independence, memory behaviour, compiler visibility, numerical contract, runtime overhead. Properties drive optimization; classes drive coverage.

### 2. KNC facts and the objective
- E1.2a Four hardware contexts per core; one context cannot issue in consecutive cycles, so two contexts are needed for full issue.
- E1.2b Dual issue with U/V pairing restrictions; at most one vector instruction per core cycle, shared by four threads.
- E1.2c 32 vector registers per context; shared per-core L1 and 512 KiB L2, so more threads compete for cache.
- E1.2d KNL out-of-order/AVX-512 behaviour must not enter the cost model.
- E1.2e A demand miss can block the issuing thread's in-order pipeline; other contexts continue; software prefetches overlap later work and can complete out of order.
- E1.2f Moving a demand load earlier helps only that load; an early prefetch prevents the later demand load blocking; a software scheduler on a stalled thread cannot run; switch work before the stall or rely on sibling contexts.
- E1.2g Lower bound: T >= max(T_dependency_path, bytes/sustainable_bandwidth, max_r work_r/capacity_r); resource work includes unpacking, conversions, permutations, address arithmetic, reductions (Roofline extension).
- E1.2h A transformation wins by shortening the dependency path, reducing work/traffic, or raising utilization toward capacity.

### 3. Branches
- E1.3a Specialize first: loop unswitching, function specialization, guarded fast paths (alignment, non-overlap, stride, dynamic type), direct-call promotion, full-block/tail separation, work bucketing, hot-path layout.
- E1.3b For LLMs resolve quantization format, dimensions, strides, alignment, activation type at load/dispatch time.
- E1.3c PGO should choose likely paths; __builtin_expect only informs the compiler.
- E1.3d If-conversion rule: extra instructions + dependencies + traffic < avoided branch overhead + recovery; hyperblock-style selective predication.
- E1.3e IMCI masking preserves inactive lanes (merge), creating a destination dependency; no zero-masking; gather/scatter completion loops must stay correct.
- E1.3f Produce branch conditions earlier where legal; never read invalid memory or move side effects.
- E1.3g No dependable universal KNC mispredict penalty found; measure per context count; separate branch count from branch loss (5% recovery time caps speedup at 1.053x).

### 4. Compile-time out-of-order
- E1.4a Hardware OoO features map to software: renaming -> SSA/regalloc; ready selection -> list scheduling; cross-iteration -> modulo pipelining; chains -> independent accumulators/tiles; alias speculation -> runtime checks/versioning; across branches -> trace/superblock and selective if-conversion; memory-level parallelism -> prefetch and stream interleaving.
- E1.4b Itanium lessons portable: scheduling, register expansion, larger regions, controlled speculation; rotating registers/ALAT not available on KNC.
- E1.4c Independent chains needed: N >= ceil(L*R); KNC study measured 4-cycle vector latency incl. FMA and reached peak with 4 threads x 1 chain or 2 threads x 2 chains.
- E1.4d Quantized-kernel steady state: L2 prefetch far, L1 prefetch near, load prefetched block, unpack earlier block, accumulate another, advance addresses; compiler emits prologue/epilogue.
- E1.4e Modulo scheduling: II >= max(ResMII, RecMII); more unrolling helps only if it exposes independence without spills/code growth.
- E1.4f Strict reductions: no silent partial sums; interleave independent sums, vectorize across independent rows/cells/outputs, prefetch, prepare addresses; GEMM across output columns preserves each reduction's order; GEMV may need packing.
- E1.4g Cost model must know pairing, AGI, operand forms, encodings (pairing restricted by instruction length/addressing form); a folded memory operand can be slower than load + later register op.

### 5. Memory window
- E1.5a Coordinated two-distance prefetch (far to L2, near L2->L1, then demand load); L1 prefetch slots far fewer than L2 on a research chip; remeasure on 3120A/7120P.
- E1.5b Prefetch distance ~ latency / cycles per iteration; outstanding bytes ~ bandwidth x latency; tune with tile size and context count.
- E1.5c McCalpin: streaming may peak with fewer than four contexts; "always four threads" is wrong.
- E1.5d Access-helper threads (3+1, 2+1 per core, or another core building work lists); must save more than it costs; another core does not fill the consumer's L1; dense LLM weights do not need helpers.
- E1.5e AMAC: interleave several independent pointer chains with prefetch; no help inside one chain; no "prefetch completed" signal.
- E1.5f No instruction-level software dispatch; schedule tiles/traversals/record groups/attention blocks/requests; static ownership for regular work, local queues and stealing only for imbalance.

### 6. N, C, G, B
- E1.6a N: inline small visible functions, scalar replacement, invariant hoisting, IV simplification, interchange/tiling, guarded versions for runtime strides/non-overlap, tail recursion to iteration; never invent restrict; AoS transform only when layout/pointers are controlled.
- E1.6b C: expose callees/types -> simplify abstractions -> recover loops -> KNC scheduling; LTO and guarded specialization; benchmark one algorithm as raw arrays, containers/iterators, function objects, function pointers, virtual dispatch.
- E1.6c G arithmetic: CSE, constant propagation, independent-subexpression scheduling, register lifetimes, code-size control; G state machines: specialization, transition fusion, outline rare states, remove redundant tests, branch vs table dispatch, batch records; parallel prefix of s_{i+1}=F(s_i,x_i) when composable (research).
- E1.6d B: find the truly serial part; SQLite mixes parser, bytecode VM, storage; dispatch specialization, prepared reuse, batched lookups, compact metadata, fewer allocations; IMCI lacks AVX-512BW byte ops, widen/pack with counted cost.

### 7. LLM-specific
- E1.7a Reuse preparation across outputs (activation quantization, correction sums, Q/K/V and gate/up shared input, scale decode); multi-row kernels; compare lanes-across-reduction vs lanes-across-output-rows; keep weights compressed, expand in registers/tiles.
- E1.7b VPMADD231D: 16 int32 multiply-add lanes with memory up-conversion (not VNNI); identity sum w x = s_w s_x (sum q r - z_w sum r); int32 exact if K max|q| max|r| < 2^31; benchmark vs FP path.
- E1.7c T-MAC style LUT kernel: 16 subset sums of 4 activations in one zmm, prepacked weight bitplanes, VPERMD selects for 16 rows; count table build, index prep, permutes, pressure, scales.
- E1.7d RMSNorm then linear: y = r[W(gamma.x)] + b removes the reduction-before-matvec dependency (FlashNorm); bitwise equivalence not implied.
- E1.7e FlashAttention-style tiled attention with online softmax for prefill; decode needs a different kernel; LFM2.5 hybrid (22 short-conv + 8 GQA blocks) needs conv/state profiling.

### 8. Speculation
- E1.8a Exact speculative decoding: verify several positions together, turning GEMV into small GEMM; T_token = (T_draft + T_verify + T_comm + T_commit)/E[tokens per round]; host could draft; hybrid models need state rollback.
- E1.8b Lookahead decoding as a draft-free alternative (experiment).
- E1.8c Continuous batching (ORCA iteration-level); report throughput and single-request latency separately.
- E1.8d Software TLS (MUTLS) possible; priorities: address prediction + prefetch (high), guarded assumption checks (high), task speculation (experimental), value prediction (low), dynamic instruction reordering (low).

### 9. Concrete gcc-knc and runtime changes
- E1.9a Middle end must keep types, bounds, aliases, side effects, loop structure long enough for specialization/dependence analysis.
- E1.9b Backend: describe KNC with define_insn_reservation, define_bypass, TARGET_SCHED_ISSUE_RATE, TARGET_SCHED_VARIABLE_ISSUE; compiler schedules one thread and cannot control the thread picker; never insert NOPs for cache latency.
- E1.9c SMS needs a counted-loop (doloop) form and bails when targetm.code_for_doloop_end is absent; accepting -fmodulo-sched proves nothing; inspect -fdump-passes, -fdump-rtl-sms, sched1, sched2, -fopt-info and final post-RA assembly.
- E1.9d Runtime stages: load (resolve config, prepack, plans), calibration (variants, tiles, contexts, prefetch distance), regular execution (persistent pinned workers), irregular (local queues), adaptation (outside inner loops).

### 10. M4 expansion and measurement
- E1.10a Add targeted N/C/G cases: ordered reduction with runtime bounds and uncertain aliases; AoS escaping vs non-escaping; bad traversal order; same algorithm via pointers/iterators/functors; runtime heterogeneous virtual-call loop; generated arithmetic of growing size; generated state machine with varied traces; one vs many independent traversals. LLVM test-suite as a material source.
- E1.10b Report four outcomes separately: unmodified-source compiler gain; runtime-assisted gain; algorithm/layout redesign; relaxed numerics/model behaviour.
- E1.10c Measure one context, one core multi-context, whole card, whole application; record correctness, cycles, instructions, branch misses, memory behaviour, code size, spills, scheduling overhead; confirm which KNC PMU events MPSS exposes.
- E1.10d LLM: split activation prep, unpack, accumulate, attention/state, sync, dispatch; fixed work/model/quant/context/batch.
- E1.10e Priority order: (1) profile H/S/N/C/G/B regions and LLM path; (2) fix KNC scheduling, verify software pipelining; (3) tune accumulators, tiles, prefetch, contexts jointly; (4) guarded specialization, abstraction elimination; (5) compare multi-row FP, int-MAC, LUT LLM kernels; (6) remove graph dependencies/redundant prep; (7) batching, speculation, irregular scheduling.
- E1.10f Compare against an optimized dual E5-2690 v3 path with equal algorithms and numerical contracts; apply host-benefiting improvements to the host first.
- E1.10g First deliverable: KNC scheduling model + H/S/N/C/G/B benchmark matrix, then competing LLM kernels. Keep the existing KNC Linux kernel; give kernel work a measured problem.

## Essay 2: which layer owns what (compiler, runtime, Linux)

- E2.0a The missing layer is the user-space runtime (workers, implementation selection, scheduling); much "autonomous" behaviour belongs there.
- E2.0b "Kernel" means either a compute kernel (user-space function) or the Linux kernel; new IMCI compute kernels need no Linux change.
- E2.1a Four schedulers: compiler instruction scheduler (compile time), KNC hardware thread picker (cycle level), user-space task scheduler (runtime), Linux thread scheduler (OS). Changing one does not replace another.
- E2.1b A cache miss stalls only that hardware context, no OS switch; page faults and blocking syscalls involve Linux; branch mispredicts are handled in hardware.
- E2.1c A new Linux scheduler is not the mechanism for hiding instruction latency.
- E2.2a Ownership rule: compiler knows dependencies, runtime knows current work and inputs, Linux controls privileged resources. Ownership map: instruction scheduling, SMS, branch layout/if-conversion/devirtualization/specialization -> compiler; prefetch placement -> compiler or library; packing/blocking/quantized arithmetic -> compute library; tensor fusion/model algebra -> graph optimizer; workers/queues/batching/variant selection -> runtime; pointer-traversal interleaving/helpers -> compiler/library + runtime; affinity, page preparation, huge pages -> runtime using OS facilities; DMA, interrupts, transport, missing MM facilities -> driver/Linux.
- E2.3a Software OoO path A (compiler): schedule vector code, overlap iterations, unroll for independence without spills, hoist address math and safe prefetches, specialize on runtime checks; enabling an option is not proof it fired.
- E2.3b Path B (runtime/library): AMAC-style interleaving of independent lookups, persistent workers, ready tiles, batching, variant choice; must get ahead of demand misses.
- E2.4a Agent track 1, compiler scheduling and transformations: audit latency/resource model, inspect pre/post-RA schedules, find needless chains and spills, check which loops get SMS, judge branch changes by cycles, add guarded transformations; output compiler change + assembly + correctness + measurement; classes as coverage, not six policies.
- E2.4b Agent track 2, compute libraries and model transformations: quantized dot/GEMV, packing/layout, activation-prep reuse, fusion, model algebra under an explicit numeric contract; turn library-vs-compiler gaps into compiler improvements where general.
- E2.4c Agent track 3, user-space runtime: persistent pools, placement on cores/contexts, granularity and queue overhead, variant selection, resident buffers, interleaving, transfer/compute overlap; this track owns worker creation, libraries cooperate.
- E2.4d Agent track 4, measurement and platform integration: latency/throughput, kernel vs prep time, counters, cache/memory, worker utilization, context switches, migrations, page faults, interrupts, transport; owns kernel investigation and proposes Linux/driver patches only on evidence.
- E2.5a Linux/driver changes are justified only by measured limits: migration (first affinity), page faults (preallocate), translation overhead (page sizes), interrupts (placement), driver transfer overhead, missing PMU events. Check what the MPSS kernel actually supports.
- E2.6a Unchanged source can still use a runtime: compiler emits checks, fallbacks, and calls into a linked runtime (libgomp precedent).
- E2.6b PGO of the application helps that application; building GCC itself with PGO only speeds the compiler.
- E2.6c Main effort: gcc-knc scheduling, compute libraries, user-space runtime; platform work starts with measurement and existing OS controls.
