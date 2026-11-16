# Qualifications and toolchain traps

Source IDs use the [edition register](practices.md#source-editions). Vendor
statements below are verified in those editions. Local card results are
reported from the named documents, not newly measured by this skill.

## Density, overlap and memory

- **Four siblings are a capacity, not a universal optimum.** R01 pp.19,23-24
  describes issue spacing. R16 slide 51 suggests trying intermediate densities;
  R08 slide 24 finds a lower STREAM density useful. Our production card's
  S11-06 sweep-2 triad drops from 163.70 to 74.71 GB/s between 60 and 120
  workers at matched hints (`knc-memory-bandwidth.md`, cases 3/34). Its
  S11-09 int8 GEMV instead benefits from more siblings (density table).
  Neither observation identifies a universal cache or queue cause.
- **Prefetch is work.** R08 slide 29 warns about hot-cache issue overhead;
  R27 pp.641-656 defines hints, not their latency. C2 in
  `knc-characterization.md` separates near and far hot-target costs. C5's
  original many-stream same-offset sweep aliased cache sets; use the corrected
  padded S8-12 table. Compiler pass bookkeeping is not a hardware queue size
  (`knc-digest-2026-11.md`, M4-5). Keep units of lines, source iterations and
  post-vectorization iterations distinct.
- **Longer lookahead can lose.** `knc-memory-bandwidth.md`, S11-09 hint table,
  reports 32/256 losing to 8/64 for all measured GEMV formats, while plain read
  improves. These are near/far distances in physical weight lines. R09 p.4
  names its option far-first, in cache lines; R02 p.161 discusses vectorized
  iterations. Inspect the installed compiler's output before translating units.
- **Huge pages are possible, not guaranteed or always faster.** R09 pp.4-5
  distinguishes explicit pages from a later THP stack; all its reported cards
  are pre-production. Our production card obtained actual huge mappings in
  S11-06, but ordinary malloc promotion remains unknown. The S11-09 matched
  GEMV page cases show no large gain (`knc-memory-bandwidth.md`). Check mappings
  at the measurement boundary. `MIC_USE_2MB_BUFFERS` is an offload control,
  not a native GCC allocator setting (R26a, Memory Allocation).
- **Physical cache size is not a safe tile size.** `knc-machine.yaml` records
  physical L2 = 512 KiB and a small-page data-TLB reach of 256 KiB per core;
  R01 pp.22-23 and corrected C4 in `knc-characterization.md` supply the evidence.
  Count touched pages and sibling footprints. No socket-style local allocation
  policy follows for KNC from R19 pp.376-377; that example is a Xeon host.
- **Do not turn an idle latency into a saturated-memory latency.** R08 slides
  23,28 explicitly distinguish them. `knc-machine.yaml` leaves loaded memory
  latency and production usable outstanding lines unknown. Counts reported
  for R06's pre-production sample are not production limits.
- **Keep store variants and completion separate.** The old NR-only result
  does not reject NGO. C1 in `knc-characterization.md` gives a completed-worker
  NGO estimate of 204.5 GB/s; its 226.1 GB/s median-worker aggregate is not
  completion throughput. S11-06's later envelope result differs and must not
  be silently substituted. R27 pp.388-398 requires eligibility and ordering.
  A mask or down-conversion prevents the intended no-read benefit. Preserve
  the compiler's ordering operation before publication, calls and returns.
- **Eviction advice conflicts.** R16 slide 54 presents early eviction as a
  streaming tool; R09 p.4 disables it for its STREAM recipe. Local S11-06
  RMW both-eviction results lack a matched long no-eviction control. Therefore
  neither always-evict nor never-evict is established on our card
  (`knc-memory-bandwidth.md`, sweep-2 tuning observations).
- **Gather hints are not a promised speedup.** R27 pp.303-310 defines their
  interface. R05 p.5 reports an ineffective hint and a blocking gather-prefetch
  form on a production-model 5110P. Our measured endpoint costs are full
  completions (`knc-characterization.md`, gather rows). They do not establish
  scatter timing or arbitrary-mask costs.

## Arithmetic and compiled paths

- **KNC is IMCI, not AVX-512F.** Use a K1OM compiler and its KNC target options;
  SSE/AVX/MMX flags are rejected (`gcc-knc-flags.md`, Recommended flags).
  R26b, Support Removed, removes KNC from ICC 18.0. A later compiler's MIC or
  Xeon Phi documentation may concern KNL and does not establish KNC support.
- **Do not copy ICC's FP defaults as a performance fix.** R04 slides 9,18
  separates IMCI flags and gradual underflow from x87 trapping behavior.
  `gcc-knc-flags.md`, ICC equivalents, documents GCC-KNC's opt-in fast math
  and the errno change made by `-mphinix`. The tiny-output observation in
  `knc-digest-2026-11.md`, FP gate, remains distinct from input-subnormal
  success. No measured universal speed case for flushing follows.
- **FP64 vector divide and square root already exist.** The project's
  correctness contract is correctly rounded FP32/FP64 divide and square root
  in every rounding mode, FP64 since S10-09 (`gcc-knc-flags.md`, ICC
  equivalents). Their internal FMAs implement those operations. Do not revive
  an old proposal to replace them with unqualified approximations. The source
  contract is not a new native qualification result for the caller's binary.
- **x87 is not a universal FP64 oracle.** Its intermediate precision can
  double-round. Match the operation's specified precision with an independent
  reference (`knc-digest-2026-11.md`, FP gate; R04 slide 9; R27 pp.55-56).
  Preserve exceptional values, rounding, flags, traps and errno as required.
- **MPSS libm cbrtl can fault.** `gcc-knc-flags.md`, Safe long double cube root,
  records finite-input failures and the compiler's `__knc_cbrtl` replacement.
  Direct recognized calls are covered; indirect calls, old objects and `dlsym`
  are not. Rebuild direct callers or explicitly call the replacement as that
  document specifies. Its host MPFR result is not a native pass: the cited
  note says native validation is staged.
- **Unrolling is not a new recurrence chain.** In C9's corrected memory-chain
  experiment, moving recurrence state matters more than adding unroll.
  In C7, the measured accumulator variants tie at four siblings
  (`knc-characterization.md`). More accumulators also require legal FP
  reassociation and may spill. No measured lower-density gain follows from C7.
- **Packing weights changes work per byte.** S11-09's int8 GEMV has lower
  weight GB/s but greater weights/s than fp32 (`knc-memory-bandwidth.md`).
  Include conversions, row scales, copies and reductions. This does not prove
  a particular quantized model meets the application's accuracy target.
- **Instruction count alone misses issue restrictions.** R02 pp.34,56 admits
  selected vector stores on V and restricts eligible encodings. R01 p.19's
  address-setup interval is not a penalty on every load. The local spill/reload
  pair is not every ABI bridge (`knc-characterization.md`, Full table;
  `knc-digest-2026-11.md`, M4-1 to M4-3). Preserve visible call and spill costs.

## Runtime and evidence

- **Runtime variables are not interchangeable.** `KMP_*` controls Intel's
  runtime, not libgomp. Select supported OpenMP/GOMP controls and verify actual
  placement (`system-tuning-playbook.md`, step 11; R18 pp.56-62). A persistent
  parallel region can still contain more barriers; R18 pp.59-61 separates team
  reuse from synchronization. Our optional grouped barrier lost in the reported
  test (`knc-digest-2026-11.md`, runtime table); retain the established runtime
  until matching evidence justifies another.
- **Arenas reserve address space; they do not all become resident.** R24a/b
  are upstream allocator snapshots, not the installed MPSS implementation.
  `knc-digest-2026-11.md`, allocator row, distinguishes affinity, memory limits
  and current libgomp policy. Fix a measured capacity/contention problem;
  do not make an arbitrary arena cap universal.
- **PMU documentation is not access permission.** R10 pp.5-7,11-16 and R11a
  identify counter structure and event restrictions, not the caller's kernel.
  R16 slide 52 prints a total-instruction denominator under a lane-use label;
  use the VPU-instruction denominator for average active lanes, with calibrated
  events (R10 pp.15-16; inference from event definitions). Neither ratio is
  FLOPs. Unavailable counters do not mean zero stalls.
- **Errata have exact triggers.** R12 pp.17-19,22-26 governs production
  stepping scope. UC packstore pairing, mask context state, fault-handler
  MXCSR and x87 exception clearing need their specific workarounds. Do not
  generalize the UC-only condition to ordinary WB output. Do not change kernel,
  firmware, ECC or power policy as a side effect of code tuning.
- **Evidence can be invalid or provisional.** `practice-lessons.md` records
  invalid vector-math batches and a faulty accuracy-screen reference. A staged
  program, host test or predicted rate is not a native pass. Report invalid
  timing, infrastructure failure and missing evidence explicitly. Restore
  only the accepted result after the caller's validation.
