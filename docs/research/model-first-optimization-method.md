# Model-first optimization: existing methods and a draft skill

Research note for the lead, 2026-11-15. Plan stage only: web reading, a local skill
listing and a repository grep. Nothing was downloaded, installed, cloned, built or run
on the card, and no skill was created.

Question: the owner prefers a "first principles" method. Before optimizing, write a
mathematical model of the hot region (operation counts per resource, bytes per memory
level, dependency chains, parallel span, latency x bandwidth products), derive a lower
bound on run time, then choose optimizations by the dominant bound term and by the gap
between measurement and bound. Does a skill, tool or method already do this, and should
we reuse it, extend it or build our own?

## 1. Answer

**Build our own thin Claude Code skill, on an existing method, with a project-owned KNC
machine file. Do not adopt an existing tool as the engine.**

- The *method* exists and is mature: Roofline (with its hierarchical and instruction
  variants), the ECM model, and Hager and Wellein's model-driven performance engineering
  process with "performance patterns". ECM was already extended to KNC by its authors
  (Hofmann et al. 2016). The skill should follow that process and use its vocabulary.
- No existing *tool* models KNC. IACA is dead and never covered KNC. LLVM has no
  K1OM/IMCI target, so llvm-mca cannot read our code. OSACA and uiCA cover recent
  out-of-order x86 and AArch64 cores only, and OSACA assumes optimal port scheduling,
  which does not describe an in-order, dual-pipe core that issues from a thread every
  other cycle. Kerncraft ships no KNC or KNL machine file and needs one of those in-core
  analyzers. Intel Advisor's roofline targets KNL, not KNC. MAQAO CQA's 2014 paper names
  Xeon Phi, but current documentation lists KNL only; KNC support is unconfirmed.
- No existing *skill* does this for CPUs. The skills found are GPU-only and work from
  profiler output (AMD's Magpie, community roofline-classification skills); none derives
  an analytic bound from sourced machine parameters.
- The repository already applies parts of the method by hand (Little's law, traffic
  bounds, removable-time bounds), but each note invents its own format and the machine
  parameters are spread over five documents. A skill plus one machine file makes the
  practice uniform and reviewable.

Optional later trial (not proposed for M4): Kerncraft's layer-condition and cache
simulator part predicts per-level traffic for C loop kernels independently of the in-core
model. A hand-written KNC machine file might let us use only that part for stencil or
PolyBench traffic. It is AGPL-3.0 and would be run as a separate tool, never linked into
GCC. It needs an owner-approved install and a separate ticket.

## 2. Survey of methods and tools

"KNC fit" says whether the thing can be used on KNC as is. In-order KNC facts used below:
one issue slot per thread every other cycle, U and V pipes with vector and x87 work on U,
4-cycle vector latency with 1-cycle throughput, 3-cycle address-generation interlock,
no L1 hardware prefetcher (R01 SSDG §2.1, p.17; R17 Klemm slide 12; ADR-0009).

### Methods

| Method | What it models; inputs; outputs | KNC fit | Source |
| --- | --- | --- | --- |
| Roofline | Attainable FLOP/s = min(peak, intensity x bandwidth). Inputs: op count, bytes, measured ceilings. Output: bound and which roof binds | Yes as a method, with KNC-specific ceilings: per-thread-count compute roofs (1, 2, 4 threads/core), gather and x87 roofs, measured STREAM roof. A single STREAM roof is known to mislead on KNC (`phi-literature-survey.md` §25) | Williams, Waterman, Patterson, CACM 2009, https://doi.org/10.1145/1498765.1498785 |
| Hierarchical roofline | One roof per memory level (L1, L2, memory) in one chart | Yes; KNC's per-core L2 and ring make the L2 roof matter | Yang, Kurth, Williams, CCPE 2020, https://www.osti.gov/pages/biblio/1574050 |
| Instruction roofline | Instructions/s against instructions per memory transaction; for integer and control-heavy code | Yes, and the right roof for bzip2, zlib, SQLite and scalar paths, where FLOPs say nothing | Ding, Williams, PMBS 2019, https://www.dcs.warwick.ac.uk/pmbs/pmbs19/PMBS19/abstracts/paper2.html |
| ECM (Execution-Cache-Memory) | Single-core time = in-core overlapping part combined with per-level transfer times (Intel: transfers do not overlap each other); multicore scaling until the memory term saturates. Inputs: in-core cycles, bytes per level, per-level transfer cycles | **Best fit.** Its authors extended it to KNC for the Kahan dot product, adding ring-bus latency effects and prefetch instruction cycles | Stengel et al., arXiv:1410.5010, https://arxiv.org/abs/1410.5010 ; Hofmann et al., CCPE 29:e3921, arXiv:1604.01890, https://arxiv.org/abs/1604.01890 ; ProPE poster on KNC: https://blogs.fau.de/prope/files/2018/09/ISC-ProPE-Poster-2018.pdf |
| Hager-Wellein performance engineering process, performance patterns | Iterate: model, measure, compare; a discrepancy is diagnosed by a named pattern (bottleneck, hazard, parallelism) and refines the model | Yes; it is the owner's method almost word for word. Use it as the skill's backbone | Treibig, Hager, Wellein, arXiv:1206.3738, https://arxiv.org/abs/1206.3738 ; https://hpc-wiki.info/hpc/Performance_Patterns ; ProPE: https://www.vi-hps.org/projects/prope/prope.html |
| Little's law (memory-level parallelism) | Outstanding requests = bandwidth x latency | Yes; already used in `knc-memory-bandwidth.md` (about 20-23 lines per core at 60 cores). Loaded latency exceeds idle latency, so idle-latency results understate demand | McCalpin, https://sites.utexas.edu/jdm4372/2025/02/17/single-core-memory-bandwidth-latency-bandwidth-and-concurrency ; R08 slides 23-28 |
| Work-span (Brent) | T_P >= max(T_1/P, T_inf); greedy schedule within 2x | Yes, for the OpenMP panels and 240-thread runs; add barrier cost (R22) to the span | https://www.csd.uwo.ca/~mmorenom/HPC-Slides/Multithreaded_Parallelism_and_Performance_Measures.pdf |
| Modulo-scheduling MII | II >= max(ResMII, RecMII) | Yes per thread; on KNC ResMII must count issue slots per thread (2 cycles each), U-only classes, and VPU occupancy shared by the core's threads. GCC's SMS (`gcc/modulo-sched.cc`) already computes an MII | Rau, HPL-94-115, 1994, https://www.hpl.hp.com/techreports/94/HPL-94-115.pdf |
| "Speed of light" (Nsight Compute) | Per-unit achieved throughput as % of peak; unit SOL is the max over sub-units; duration, not SOL %, is ground truth | Format only: a per-resource utilization table is a good report shape. GPU tool | https://docs.nvidia.com/nsight-compute/ComputeTriage/index.html ; https://docs.nvidia.com/nsight-compute/2022.1/ProfilingGuide |
| Facile (component-wise bound) | Basic-block throughput = max over separately computed bottleneck components (front end, ports, dependencies); interpretable because the max names the bottleneck | Design pattern only (models recent Intel cores). Our bound T = max(terms) has the same shape | Abel, Sharma, Reineke, IISWC 2023, https://arxiv.org/abs/2310.13212 |

### Tools

| Tool | Models / inputs / outputs | KNC support | Machine model user-definable | License; maturity | Source |
| --- | --- | --- | --- | --- | --- |
| Kerncraft | ECM, Roofline, layer conditions, benchmark mode; input is a C loop kernel plus YAML machine file; in-core model chosen with `--incore-model`/`-i` (default OSACA; IACA or LLVM-MCA otherwise) | No. 17 example machine files (SNB to Cascade Lake, Zen 1-2, ThunderX2, A64FX); none KNC or KNL. In-core analyzers cannot read IMCI | Yes (YAML) | AGPL-3.0; active (pushed 2026-07) | https://github.com/RRZE-HPC/kerncraft |
| OSACA | Port pressure, critical path, loop-carried dependencies, DOT graph, from assembly; assumes optimal scheduling (`--fixed` alternative) | No. Supports Intel SNB-GNR, AMD Zen 1-5, several AArch64 cores. No in-order model; MVEX/IMCI parsing not listed | Partly: ISA/arch DB extensible by importing ibench/asmbench results, hand edits for irregular operands | AGPL-3.0; active (pushed 2026-10); SC-W 2024 added Zen 4, Golden Cove, Neoverse V2 | https://github.com/RRZE-HPC/OSACA ; https://arxiv.org/abs/1809.00912 |
| llvm-mca | Simulates LLVM scheduling models on assembly; in-order pipeline support since 2021 | No. LLVM has no K1OM/IMCI target; Intel said in 2013 it did not plan open-source KNC support | Only by writing an LLVM scheduling model in TableGen, which needs an MC layer for the ISA | Apache-2.0 with LLVM exception; mature | https://llvm.org/docs/CommandGuide/llvm-mca.html ; https://lists.llvm.org/pipermail/llvm-dev/2013-July/063734.html ; https://lists.llvm.org/pipermail/llvm-dev/2021-March/149068.html |
| uiCA | Cycle-level pipeline simulator for basic blocks from uops.info data; about 1% error on recent Intel cores; assumes cache hits | No (recent Intel big cores only) | No practical path | AGPL-3.0; last push 2024-01 | https://github.com/andreas-abel/uiCA ; https://arxiv.org/abs/2107.14210 |
| IACA | Static throughput/latency of a marked block | No; end of life April 2019; Intel points to llvm-mca | No (closed) | Proprietary, retired | https://www.intel.com/content/www/us/en/develop/articles/intel-architecture-code-analyzer.html |
| PALMED / PMEvo | Builds an abstract-resource throughput model automatically from microbenchmark timings only | Not packaged for KNC. Could in principle run its microbenchmarks on the card, but the model targets superscalar out-of-order cores and is a research prototype | Generated | Research code; CGO 2022 | https://arxiv.org/abs/2012.11473 |
| MAQAO CQA | Static loop analyzer; lower bound in cycles assuming L1-resident data, infinite trip count, no dynamic hazards; names the bottleneck | Unconfirmed. The 2014 paper names Xeon Phi; current tutorial lists KNL among supported cores, not KNC | No | Free binary distribution; check terms before use | https://maqao.liparad.uvsq.fr/ ; https://maqao.liparad.uvsq.fr/documentation/MAQAO.Tutorial.CQA.pdf |
| Intel Advisor / VTune roofline | Measured cache-aware roofline | No KNC evidence; documented for KNL. ICC 18 removed x100 support (R26b) | No | Proprietary | https://www.osti.gov/biblio/1398491 ; https://cdrdv2-public.intel.com/671165/roofline-analysis-with-intel-advisor.pdf |
| Timeloop / Accelergy | Analytic performance and energy of tensor loop nests mapped onto accelerator buffer hierarchies; mapper searches tilings | Not as is. Conceptually one could describe KNC's L1/L2 as buffer levels for GEMM/GEMV tiling, but it models accelerators, not an in-order CPU's issue rules. Too heavy for our tickets | Yes (YAML architecture specs) | BSD-3-Clause; active | https://github.com/NVlabs/timeloop ; https://timeloop.csail.mit.edu/ |

### LLM-agent skills and agent systems

| Item | What it does | Fit |
| --- | --- | --- |
| AMD Magpie kernel evaluator (Claude Code skill) | Benchmark, profile, TraceLens roofline per kernel (`pct_roofline_mean`, `roofline_bound`), compare candidates, rerun benchmark | AMD GPUs, profiler-driven; a good workflow shape (baseline, bound, candidates, compare), not an analytic model. https://rocm.docs.amd.com/projects/amd-skills/en/latest/walkthroughs/magpie-kernel-evaluator.html |
| Community roofline-classification skills (for example agent-almanac "analyze-kernel-bottleneck" on skill indexes) | Classify memory- vs compute-bound by intensity against machine balance, with hard-coded GPU numbers | GPU-only; the indexed page is now gone (HTTP 410). Not reusable |
| Atrex-Bench and related LLM GPU-kernel benchmarks | Per-problem roofline ceiling as the score for agent-written kernels | Confirms the idea of a bound as the stopping rule; GPU-only. https://arxiv.org/abs/2607.14541 |

Nothing found derives a lower bound for a CPU loop from sourced machine parameters and
steers an agent by its dominant term; nothing handles an in-order core.

## 3. What exists locally

- **Skills.** `~/.claude/skills/` holds `agent-team-project` and `synced` (no
  SKILL.md). Plugin `skills` folders under `~/.claude/plugins/` (official marketplace:
  champion-kit, plugin-dev, math-proof, skill-creator and others) contain no performance
  modeling skill; the one grep hit (`champion-kit/maturity`) uses "lower bound" about
  commit counts.
- **Already applied in the repository, by hand:**
  - Little's law and traffic-model bounds: `docs/research/knc-memory-bandwidth.md`
    (concurrency calculation near line 85; per-pattern compulsory-traffic bounds; headroom
    `H(B) = 352/B - 1` explicitly "room to investigate, not expected attainment").
  - Removable-time bounds on profiled regions: `docs/research/m4-baseline.md`
    (`A = T * (U/L) * p`, `D(s) = A * (1 - 1/s)`) and `docs/research/s12-06-scalar-fp.md`
    (demonstrated removable lower bound 0 s). This is the Amdahl term of the method.
  - Latency x throughput for independent chains: `docs/research/knc-costs.md`
    (`--param=knc-threads-per-core`, two chains at 1-3 threads, one at 4), measured in
    `knc-characterization.md` C7 and C9.
  - Prefetch distance as latency over cycles per iteration: characterization C5 sweep,
    `knc-prefetch.md`.
  - ECM is cited only for the host (`host-phi-workstation.md` T1,
    `system-tuning-playbook.md` [B6]); roofline only as a caution
    (`phi-literature-survey.md` §25). No note uses roofline or ECM terms for KNC work.
- **Machine parameters** are spread over `knc-characterization.md` (measured, card and
  date per table), `knc-microarch.md`, `knc-costs.md`, ADR-0009 and `knc-references.md`
  (R-numbers with editions, pages, hardware status). The S12-14 audit's V/R/E evidence
  labels are the right provenance scheme for a machine file.
- **Gaps:** no common model artifact per ticket, no "distance from bound" in tickets or
  approval notes, no stated stop rule when a program is near its bound, and no single
  parameter table with per-model (7120/5110P/3120) values.

## 4. KNC bound terms the skill should use

Per core, for a hot loop run by t threads on that core (t = 1..4), per iteration:

| Term | Formula (cycles) | Inputs and where they come from |
| --- | --- | --- |
| Thread issue | `T_issue_thr = 2 * B` per thread, B = issue bundles per iteration (a U+V pair counts once) | Bundle count from the assembly; every-other-cycle issue R01 p.17, characterization point 1 |
| Core issue | `T_issue_core = sum over threads of B / 1` | One bundle per core cycle (R01) |
| U-pipe | `T_U = N_U` (vector, x87, U-only classes) | Pairing classes R02 pp.32-34, 56; S12-13 V-pipe vector store exceptions |
| VPU | `T_VPU = N_vec` per core, shared by threads | 1/cycle throughput (R17 slide 12, characterization) |
| Recurrence | `T_rec = latency sum of the loop-carried chain / (independent chains per thread)`; with t threads the core hides up to t chains | 4-cycle vector latency; scalar add 1 cycle at 4 threads (`knc-costs.md`) |
| AGI | 3 cycles where an address depends on a just-computed register | ADR-0009; R02 |
| L1-L2 transfer | lines from L2 x cycles per line | characterization; ECM KNC extension (Hofmann 2016) |
| Memory | `bytes / sustainable bandwidth`, card-wide, split per core | measured STREAM classes in `knc-memory-bandwidth.md`; not raw 352 GB/s |
| Concurrency | outstanding lines needed = `BW x latency / 64` vs available L1 misses + L2 prefetch streams | Little's law; R08 slides 23, 28; R06 Table V (pre-production) |
| Gather/scatter | per distinct cache line touched, not per element | R05 Table II |
| Prefetch distance | `d_L1 = ceil(L2 latency / cycles per iteration)`, `d_L2 = ceil(memory latency / cycles per iteration)` | characterization C5; loaded, not idle, latency |
| Span (OpenMP) | `T_inf` plus barriers x barrier cost | R22; work-span law |

Bound: `T_lb = max(all terms)` is a valid lower bound only if each term is itself a lower
bound for that resource. A *prediction* adds an overlap assumption: on an in-order core a
demand miss stalls the thread and overlaps only with other threads' work, so an
ECM-style sum (`T_in-core + transfers`) per thread, then the max with the shared-resource
terms per core, is the natural prediction. The skill must report both and never present
the prediction as a bound. Whole-program effect goes through the profile share p
(Amdahl), as `m4-baseline.md` already does.

## 5. Draft skill design (not created)

**Name:** `model-first` (generic method). The KNC specifics live in project files that
the skill reads, so the same skill can ship in the agent-team-project kit.

**Location:** project skill in the repository (`.claude/skills/model-first/SKILL.md`), so
engineer sessions started by `tools/dispatch.py` load it; a copy without KNC references
goes into `agent-team-project/kit` later.

**Trigger description (draft):** "Use before changing code or compiler heuristics to make
a program or loop faster, and when reviewing such a change: build an operation, byte and
dependency model of the hot region, derive a run-time lower bound and a prediction from
the project's machine file, compare with measurement, and pick the transformation by the
dominant term. Not for correctness, ABI or build tickets."

**Tier, chosen from the ticket's existing `depth` field (light/standard/deep):**

| Tier | Required | Limit |
| --- | --- | --- |
| light | One line in the ticket note: dominant term, its value, measured time, ratio | No new measurements |
| standard | Model table (section 4 terms that apply), `T_lb`, `T_pred`, measured, utilization per term, prediction of the change | About 10% of the ticket's session budget |
| deep | As standard, plus a microbenchmark for any input whose uncertainty changes the decision, and model validation on a second program or profile | Inputs only measured when the decision depends on them |

**Steps the skill makes the agent follow:**

1. *Scope.* Name the hot region and its share p of program time from an existing
   profile; skip regions below about 5% unless the ticket says otherwise. Compute the
   Amdahl cap `1 / (1 - p + p/s)` for a plausible s before any modeling.
2. *Characterize.* Trip counts, data sizes per level, working set, threads per core,
   profile (7120, `--profile 3100`, `--profile 5100`).
3. *Model.* Count operations by resource from the assembly (bundles, U-only, VPU,
   loads/stores, gathers, prefetches, branches), bytes per level, loop-carried chains,
   parallel span. Every input row carries a source: counted (file and line), machine file
   key, or measured on this ticket (run ID).
4. *Bound and predict.* `T_lb = max(terms)`; `T_pred` with the stated overlap
   assumption; both per profile.
5. *Compare.* Measure under ADR-0010/ADR-0015 rules. Report `T_lb / T_meas`,
   `T_pred / T_meas` and per-term utilization (a speed-of-light table).
6. *Diagnose.* If measured is close to `T_lb` (say within 15%), the code is at its limit
   for this algorithm and layout: only fewer operations or bytes help; say so and stop.
   If measured greatly exceeds `T_pred`, the model misses a term (AGI, bank conflict,
   TLB, ring, x87 bridge): name the suspected performance pattern and check it before
   transforming. If `T_pred` greatly exceeds `T_lb`, the problem is overlap: chains,
   threads, prefetch distance.
7. *Choose.* Map the dominant term to levers: issue (unrolling, fewer overhead
   instructions, pairing), VPU (fewer operations, FMA), recurrence (more accumulators
   only where strict FP allows; no reassociation without legality), memory (NGO stores,
   blocking, layout, prefetch), concurrency (prefetch distance and density, threads), span
   (schedule, barrier placement).
8. *Predict.* Write the new `T_lb`, `T_pred` and whole-program gain before measuring.
9. *Measure and update.* Record predicted against measured on the ticket, keep negative
   results, and update the model. A newly measured parameter goes into the machine file
   with the ticket ID, card, date and compiler commit.

**Artifacts:** a "Model" section in the ticket note or research note with a fixed table
(term, formula, inputs, source, value per profile), the bound, the prediction, the
measurement and the decision. A small evaluator (`tools/bound.py` reading a model YAML
and the machine file) is a possible later engineer ticket; the skill must work without
it.

**Machine file:** one file, proposed `docs/research/knc-machine.yaml` (lead-owned, like
`harness/`). Each key has value, unit, scope (thread/core/card), model column
(7120/5110P/3120 and the `--profile` restrictions), evidence label V/R/E as in S12-14,
and a source: an R-number with page or slide from `knc-references.md`, or a
characterization table and row with card date. Pre-production sources (R06, R09, R20)
keep that status. Idle and loaded latency are separate keys. The file is filled from
the existing documents, not from memory; values without a source stay empty.

**Fit with the ticket flow and agent-team-project:**
- The lead writes optimization tickets with the tier implied by `depth`; acceptance names
  the model artifact, as it names tests.
- For deep tickets the model with its prediction is reviewed before implementation, the
  way `pm.py red` gates red tests.
- Review (DEVELOPMENT_CYCLE §7) checks that inputs are sourced and that the
  chosen transformation targets the dominant term; over-modeling is a finding, as
  over-testing is.
- `pm.py approve --note` states the distance from bound in one sentence, for example
  "now 1.1x its memory bound on 7120".
- Findings that change a parameter go to `CURRENT_STATE.md` and the machine file.

**Avoiding over-modeling:** tiers tied to depth; skip regions below about 5%; no
microbenchmark unless the decision changes with the input; reuse an existing model by
link; stop when measurement is within the stated band of the bound; never model
correctness, ABI or build tickets.

## 6. Risks

- False precision: KNC parameters from pre-production parts and idle latencies; the
  bound is only as good as its weakest input. Each term keeps its evidence label.
- A bound is not an expected result (the bandwidth note already says this); tickets must
  not book predicted gains.
- Per-model differences (cores, clock, memory) change which term dominates; a 7120-only
  model can mislead under `--profile 3100` or `5100`.
- Strict FP: the model must not recommend reassociation or fast-math transformations as
  levers without the usual legality case.
- Integer and control-heavy programs (bzip2, zlib, SQLite) need the instruction-roofline
  form; FLOP-based terms are empty there.
