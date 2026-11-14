# Xeon Phi literature survey for GCC-KNC and PhiNix

S12-15 research, 2026-11-14. Ranked by likely usefulness to this project's
compiler, runtime, system, and application work, rather than citation count.

## Scope and reading conventions

The starting bibliography was Part 2 of
[knc-reference-gaps.md](knc-reference-gaps.md); `knc-references.md` was not present.
Its R01-R26 and G01-G16 identifiers below retain their meanings there. This
survey adds work beyond that bibliography. "Overlooked" means absent from that
starting bibliography, not proof that nobody in the project has used it.

**All page numbers are one-based PDF pages**, including covers, unless explicitly
called printed pages. This matters particularly for theses, preprints, and ZIB
reports. Web-only artifacts have named section locators instead of invented page
numbers. Author manuscripts can differ from the published edition; the local
edition is identified below. Performance numbers are authors' results or authors'
self-reports, never results measured in this ticket.

Downloaded PDFs and page-marked text extracts live outside git at
`.work/_shared/phi-literature/`, relative to the main GCC-KNC repository.
Each `Local:` filename below is relative to that directory. Text extracts have
the same basename and `.txt` extension. The collection contains 30 PDFs and
their text extracts, totaling 45.55 MiB, below the ticket's 2 GB limit.
This is a reading collection, not a
toolchain, source-code import, or set of runnable benchmark artifacts.

Three distinctions govern the recommendations:

* KNC uses IMCI; KNL uses AVX-512. Similar vector widths do not make their
  instructions, kernels, cost models, or binaries interchangeable.
* A host driver that recognizes a PCIe card is different evidence from a kernel
  booting on the card, and both are different from an application running there.
* Application layout changes, solver reorderings, quantization, and approximate
  math need their own correctness contracts. They do not authorize changes to
  ordinary C/C++ floating-point semantics in GCC.

## Ranked annotated sources

### 01. Indirect prefetch generation, with a later microarchitecture study

**Citation:** Sam Ainsworth and Timothy M. Jones, *Software Prefetching for
Indirect Memory Accesses*, CGO 2017, pp. 305-317
([author PDF](https://www.cl.cam.ac.uk/~tmj32/papers/docs/ainsworth17-cgo.pdf));
extended as *Software Prefetching for Indirect Memory Accesses: A
Microarchitectural Perspective*, ACM TOCS 36(3), article 8, 2019,
[DOI 10.1145/3319393](https://doi.org/10.1145/3319393)
([author PDF](https://www.cl.cam.ac.uk/~tmj32/papers/docs/ainsworth19-tocs.pdf)).
**Local:** `ainsworth-cgo2017.pdf`, `ainsworth-tocs2019.pdf`.
**Goals:** GCC indirect accesses, prefetch costs, sparse kernels, G03/G04/G16.

* CGO pp. 4-5 derive future addresses by walking load dependencies back to loop
  induction variables; dependent loads need staggered prefetch distances.
* TOCS pp. 7-9 give sufficient bounds conditions for speculative address
  computation. A non-faulting prefetch does not make preceding ordinary loads safe.
* TOCS pp. 17-21 distinguish latency hiding from instruction overhead, bandwidth
  saturation, and address-translation limits; pp. 22-28 vary access complexity
  rather than relying solely on benchmark averages.

**Limits / relation to notes:** KNC is a 3120P; KNL 7210 is separately labeled
(TOCS p. 13). Both editions used manually inserted equivalent prefetches plus ICC
for KNC because Clang lacked that target (CGO p. 6; TOCS p. 11). This is a
transformation design, not an available LLVM IMCI backend. CGO's abstract and
introduction disagree on its headline KNC average; use the detailed experiments.
Extends R05/R14 beyond measuring gathers. Suggested work: a legality-first
indirect-prefetch prototype with address-load overhead visible in costing.

### 02. Choose SMT density per parallel region, not once per program

**Citation:** Wim Heirman, Trevor E. Carlson, Kenzo Van Craeynest, Ibrahim Hur,
Aamer Jaleel, Lieven Eeckhout, *Automatic SMT Threading for OpenMP Applications
on the Intel Xeon Phi Co-processor*, ROSS 2014, article 7,
[DOI 10.1145/2612262.2612268](https://doi.org/10.1145/2612262.2612268)
([author PDF](https://heirman.net/papers/ross2014.pdf)).
**Local:** `heirman-smt2014.pdf`. **Goals:** libgomp, affinity, G09, profile policy.

* Pp. 2-3 show that input size and parallel region change the preferred number of
  hardware threads per core; the controller samples successive invocations after
  a warmup invocation.
* Pp. 3-4 combine region timing with IPC and L2 misses to detect phases and
  revisit the choice. The implementation hooks Intel's OpenMP runtime.
* P. 5 shows that short workloads can fail to amortize calibration; the same CG
  application can prefer different densities for different NAS classes.

**Limits / relation to notes:** 7120A, 60 compute cores, controlled placement;
this is not a measured libgomp patch. Its timing approach must be reconciled with
R11's counter caveats. It qualifies any blanket four-threads-per-core rule and
adds a concrete policy to R20/R22. Suggested work: opt-in region-level density
selection with calibration charged to total runtime.

### 03. Popcorn actually ported a newer Linux to KNC

**Citation:** Antonio Barbalace et al., *Popcorn: Bridging the Programmability
Gap in Heterogeneous-ISA Platforms*, EuroSys 2015, article 29
([author PDF](https://www.ssrg.ece.vt.edu/papers/eurosys15.pdf)); Christopher S.
Jelesnianski, *A Compiler Framework to Support and Exploit Heterogeneous
Overlapping-ISA Multiprocessor Platforms*, Virginia Tech MS thesis, 2015
([institutional PDF](https://vtechworks.lib.vt.edu/bitstream/handle/10919/78177/etd-11202015-173824_Jelesnianski_CS_T_2015.pdf)).
**Local:** `popcorn-eurosys2015.pdf`, `jelesnianski-thesis2015.pdf`.
**Goals:** PhiNix, heterogeneous scheduling, compiler/runtime ABI boundaries.

* Paper pp. 7-10 describe page-based distributed shared memory, function-boundary
  migration, and partitioning that charges transfers and execution separately.
* Thesis pp. 40-41 records a useful cost-model defect: libm calls received a
  constant estimated cost. Page-access instrumentation drives a minimum-cut
  placement model; profiles do not cover functions never executed in training.
* Thesis p. 71 documents a 3120A and Linux 3.2.14, porting MPSS 3.2.3 support from
  2.6.38.8; pp. 71-72 specify mixed LLVM/GCC/ICC and modified runtime libraries.
* Thesis p. 80 measures instrumentation overhead separately from native runtime.

**Limits / relation to notes:** The evaluation restricts the host to eight cores
and uses 228 KNC hardware threads, not 228 physical cores (thesis p. 71).
This is historical kernel-port evidence, not current Linux support or a free
IMCI compiler. Extends G14/G15 and reinforces G01/G05's need to price library
calls. Suggested work: recover the published port's subsystem changes and
compare migration costs with explicit SCIF offload before choosing a PhiNix model.

### 04. A direct KNC LLM inference revival exists

**Citation:** Julia Longtin, *Xeon Phi (Knights Corner) Support*,
[llama.cpp pull request 6440](https://github.com/ggml-org/llama.cpp/pull/6440),
opened April 2024; web status inspected 2026-11-14.
**Local:** none; PR conversation and commit summaries only, no source import.
**Goals:** quantized GEMV/dot products, weight traffic, scalar/vector boundaries.

* The PR description attributes most gains to an IMCI assembly implementation of
  the Q5_K by Q8_K dot product. This is an unusually direct match to our LLM goal.
* It self-reports Mistral 7B Instruct Q5_K going from 0.18 to 1.2 tokens/s; the
  description does not establish a reproducible cross-machine benchmark.
* The conversation identifies cross-compiler detection, scalar runtime support,
  and an added benchmark binary as integration work, not just arithmetic changes.

**Limits / relation to notes:** The inspected PR is open, not evidence of support
in an upstream release. Hardware, prompt/decode split, correctness coverage, and
memory residency need independent recovery. Commit summaries mention importing
and subsequently removing intrinsics; no such headers or diffs were read here.
This adds direct application evidence beyond G03/G04/G12. Suggested work:
independently specify and benchmark one quantized dot contract, including unpack,
scale, reduction, tails, and bytes moved, without importing vendor-derived code.

### 05. SELL-C-sigma separates useful work from padding and RHS traffic

**Citation:** Moritz Kreutzer, Georg Hager, Gerhard Wellein, Holger Fehske,
Alan R. Bishop, *A Unified Sparse Matrix Data Format for Efficient General
Sparse Matrix-Vector Multiply on Modern Processors with Wide SIMD Units*,
SIAM J. Scientific Computing 36(5), 2014,
[DOI 10.1137/130930352](https://doi.org/10.1137/130930352)
([preprint](https://arxiv.org/abs/1307.6209)).
**Local:** `sell-c-sigma2014.pdf` (23-page preprint).
**Goals:** S12-07, gathers, layout, bandwidth models.

* Pp. 6-10 separate chunk height from the row-sorting window, making SIMD
  occupancy and reordering scope independently tunable.
* Pp. 13-14 model padding and right-hand-side access traffic explicitly rather
  than assigning every useful flop the same byte cost.
* P. 15 uses chunk height 16 on KNC for vectorization/alignment and reports three
  threads per core as best for these cases; pp. 18-19 discuss sorting/locality
  tradeoffs instead of assuming maximal sorting is optimal.

**Limits / relation to notes:** 5110P (p. 4), MIC intrinsics rather than evidence
of successful generic auto-vectorization (p. 15). Sorting and preprocessing costs
belong in complete solves; altered accumulation needs a numerical contract.
Extends R14's sparse survey with a portable format and inspectable cost model.
Suggested work: compare CSR with bounded-sorting SELL under matched useful
nonzeros, preprocessing amortization, and convergence checks.

### 06. CSR5 provides a concrete KNC artifact and conversion accounting

**Citation:** Weifeng Liu and Brian Vinter, *CSR5: An Efficient Storage Format
for Cross-Platform Sparse Matrix-Vector Multiplication*, ICS 2015, pp. 339-350,
[DOI 10.1145/2751205.2751209](https://doi.org/10.1145/2751205.2751209)
([preprint](https://arxiv.org/abs/1503.05032));
[authors' repository](https://github.com/weifengliu-ssslab/Benchmark_SpMV_using_CSR5).
**Local:** `csr5-ics2015.pdf`. **Goals:** S12-07, sparse load balance and masks.

* Pp. 4-6 distribute nonzeros into regular tiles and use metadata plus segmented
  reductions to handle row boundaries and uneven row lengths.
* P. 8 specifies 5110P, ICC/MIC intrinsics, MKL 11.2 Update 1, and MPSS-era
  software, making the comparison's environment recoverable.
* P. 10 counts allocation, tile descriptors, and transposition in conversion
  overhead; repeated SpMV is the amortization opportunity.

**Limits / relation to notes:** The repository README explicitly separates
`phi` KNC from the January 2017 AVX-512 KNL addition; its KNC implementation
supports double precision. Those directories are not interchangeable donors.
Extends R14/G03, without proving that an isolated faster SpMV improves HPCG.
Suggested work: compare end-to-end conversion plus repeated multiplies and
identify which segmented-reduction operations GCC lacks. No source was copied.

### 07. HAM exposes the software part of offload latency

**Citation:** Matthias Noack, *HAM - Heterogenous Active Messages for Efficient
Offloading on the Intel Xeon Phi*, ZIB Report 14-23, 2014
([institutional PDF](https://webdoc.sub.gwdg.de/ebook/serien/ah/ZIB/14_23.pdf)).
**Local:** `ham2014.pdf` (two cover pages). **Goals:** G15, host-card transfers,
offload runtime, symmetric execution.

* Pp. 5-6 separate dispatch/runtime overhead from accelerated kernel execution;
  the interface uses ordinary C++ rather than new language offload syntax.
* Pp. 10-11 implement both SCIF and MPI transports. Registered buffers, RMA
  completion, notification ordering, and buffer reuse are part of the protocol.
* P. 12 measures empty-call overhead, including roughly 2.2 microseconds for
  HAM/SCIF versus 39.1 for the compared Intel offload path.

**Limits / relation to notes:** Two 7120P cards, historical compiler/runtime
versions (p. 11). Empty-call latency is not application speedup or transfer
bandwidth. It does not remove the need for a compiler for device code.
Extends R25 from API semantics to a small protocol design. Suggested work:
design a persistent worker and buffer lifecycle, measuring dispatch, payload,
completion, and reuse separately before introducing automatic offload decisions.

### 08. Splotch makes allocation a measured application bottleneck

**Citation:** Timothy Dykes, Claudio Gheller, Marzia Rivi, Mel Krokos,
*Splotch: Porting and Optimizing for the Xeon Phi*, IJHPCA 31(6), 550-563,
2017, [DOI 10.1177/1094342016652713](https://doi.org/10.1177/1094342016652713)
([2016 preprint](https://arxiv.org/abs/1606.04427)).
**Local:** `splotch2016.pdf` (11-page preprint, provisional journal header).
**Goals:** malloc, reusable buffers, vector layout, G10/G15.

* Pp. 4-5 identify offload-time allocation and data lifetime as separate
  optimization targets; retaining buffers avoids repeating setup work.
* P. 5 describes thread-local pools that preserve alignment and coalesce free
  space, compared with ordinary library allocation alternatives.
* P. 10 reports cases where allocation consumes at least half the execution
  time, giving a workload-level reason to inspect allocators.

**Limits / relation to notes:** 5110-series test systems (p. 7); rendering has
specific allocation sizes and lifetimes. The study does not establish that
glibc arena locks cause our workloads' stalls. This fills G10 with application
evidence beyond R24's allocator-source inspection. Suggested work: recover
allocation-size/lifetime distributions and compare reuse, per-thread pools, and
allocator settings before changing the general allocator.

### 09. Quantized neural-network work already encountered KNC's narrow-data costs

**Citation:** Gaurav Raina, *Deep Convolutional Network Evaluation on the Intel
Xeon Phi: Where Subword Parallelism Meets Many-Core*, TU Eindhoven master's
thesis, 2016
([institutional PDF](https://pure.tue.nl/ws/files/46932913/844256-1.pdf)).
**Local:** `raina-thesis2016.pdf`. **Goals:** quantized inference, scalar cost,
conversion and SIMD utilization, G01/G12.

* Pp. 52-55 explain the cost of widening narrow integer operands for KNC
  arithmetic and the remaining scalar activation/index work.
* P. 55 discusses interleaving loads with arithmetic to reduce dependency stalls.
* P. 58 explicitly extrapolates a measured single-core result to 57 cores;
  p. 61 identifies serial sections and subword limitations as obstacles.

**Limits / relation to notes:** 31S1P, an image-recognition CNN, not an LLM.
The projected 43 frames/s is not a measured whole-card result. The text's broad
"32-bit only" wording must be confined to its narrow-integer discussion: KNC
also has 64-bit arithmetic. Its four-thread scheduling explanation is not a
replacement for R01 or S12-08 measurements. Suggested work: include widening,
unpacking, activation/scaling, and scalar reductions in quantized kernel costs.

### 10. BLIS explains how packing and thread placement interact

**Citation:** Tyler M. Smith, Robert van de Geijn, Mikhail Smelyanskiy,
Jeff R. Hammond, Field G. Van Zee, *Anatomy of High-Performance Many-Threaded
Matrix Multiplication*, IPDPS 2014, pp. 1049-1059,
[DOI 10.1109/IPDPS.2014.110](https://doi.org/10.1109/IPDPS.2014.110)
([author PDF](https://www.cs.utexas.edu/~flame/pubs/blis3_ipdps14.pdf)).
**Local:** none; author PDF read through web extraction after direct-download
timeouts. Page numbers refer to that 11-page PDF.
**Goals:** dense BLAS, GEMM, cache sharing, libgomp, G11.

* Pp. 2-3 expose five loops around a small microkernel, separating reusable
  algorithm structure from architecture-specific arithmetic.
* Pp. 4-5 explain that the selected parallel loop determines sharing of packed
  operands and replication across private caches; parallelizing the reduction
  dimension introduces extra synchronization or output reduction.
* P. 6 maps inner-loop work to siblings sharing a KNC core and outer-loop work
  across cores, accounting for the absence of a shared last-level cache.

**Limits / relation to notes:** 60-core KNC and Blue Gene/Q are distinct cases.
GEMM's reuse does not establish GEMV or token-decoding throughput. Extends
R08/G11 with constructive thread/data mapping. Suggested work: a portable BLAS
kernel boundary and packing policy, with GEMV and small-batch GEMM measured
separately; inspect historical BLIS artifacts only under a later code-use ticket.

### 11. QCD combines local working sets with reduced storage precision

**Citation:** Simon Heybrock, Balint Joo, Dhiraj D. Kalamkar, Mikhail
Smelyanskiy, Karthikeyan Vaidyanathan, Tilo Wettig, Pradeep Dubey,
*Lattice QCD with Domain Decomposition on Intel Xeon Phi Co-Processors*,
SC 2014, pp. 69-80, [DOI 10.1109/SC.2014.11](https://doi.org/10.1109/SC.2014.11)
([preprint](https://arxiv.org/abs/1412.2629)).
**Local:** `qcd-domain2014.pdf`. **Goals:** stencils, cache blocking,
compressed matrix/weight streaming, MPI.

* Pp. 3-4 use local domain solves and structure-of-arrays site fusion to reduce
  communication and avoid gathers in the main stencil.
* P. 5 sizes each domain for one core's L2 and stores selected constant matrices
  in half precision while keeping iteration vectors in single precision.
* P. 7 checks convergence behavior for this mixed-precision preconditioner;
  communication savings and arithmetic speed are not the sole success criteria.

**Limits / relation to notes:** The Stampede configuration is described as
7110P (p. 6); do not silently relabel it from other Stampede papers. Half-storage
conversion is not general half-precision arithmetic, and QCD convergence does
not validate LLM quantization or strict libm. Extends G04/G11/G13. Suggested
work: investigate compressed read-mostly data with explicit accuracy contracts
and cache-residency accounting. [QPhiX](https://github.com/JeffersonLab/qphix)
is a related inspectable artifact, not necessarily this exact solver revision.

### 12. A later LWK comparison makes tuned Linux the necessary baseline

**Citation:** Balazs Gerofi et al., *Linux vs. Lightweight Multi-kernels for
High Performance Computing: Experiences at Pre-Exascale*, SC 2021
([author PDF](https://bgerofi.github.io/papers/bgerofi-SC21.pdf)).
**Local:** `mckernel-sc2021.pdf`. **Goals:** PhiNix scheduling, memory management,
OS noise, honest Linux/LWK comparison.

* P. 3 distinguishes KNL 7250 Oakforest-PACS from A64FX Fugaku and documents
  different starting levels of Linux tuning.
* Pp. 4-5 discuss interrupt, kernel-worker, and memory-management interference;
  isolation must include these paths, not just pin application threads.
* P. 9 explains limits on large-scale comparisons and connects some KNL gains
  to heap management. Kernel names alone do not explain the result.

**Limits / relation to notes:** No KNC measurements. The transferable part is
the comparison method and service isolation, not KNL instruction behavior,
A64FX page/cache features, or a ready K1OM port. Extends G08/G10/G14 and guards
against attributing untuned Linux overhead to an unavoidable monolithic-kernel
cost. Suggested work: establish a tuned Linux baseline before judging a PhiNix
LWK experiment, reporting reserved cores and memory as consumed resources.

### 13. IHK/McKernel supplies a concrete compatibility mechanism

**Citation:** Balazs Gerofi, Masamichi Takagi, Atsushi Hori, Gou Nakamura,
Tomoki Shirasawa, Yutaka Ishikawa, *On the Scalability, Performance Isolation
and Device Driver Transparency of the IHK/McKernel Hybrid Lightweight Kernel*,
IPDPS 2016, pp. 1041-1050,
[DOI 10.1109/IPDPS.2016.80](https://doi.org/10.1109/IPDPS.2016.80)
([author PDF](https://bgerofi.github.io/papers/bgerofi-ipdps16.pdf)).
**Local:** `mckernel-ipdps2016.pdf`. **Goals:** PhiNix, POSIX compatibility,
drivers, memory partitioning.

* Pp. 2-3 split resources between Linux and a separate lightweight kernel;
  IHK can assign cores and physical memory without rebooting the machine.
* P. 3 describes selective syscall offload and a Linux proxy whose address-space
  relationship lets Linux services access application data.
* P. 4 extends that relationship to driver mappings, avoiding a separate LWK
  implementation of every device driver.

**Limits / relation to notes:** This paper's evaluation uses a dual E5-2680
cluster (p. 4), not KNC. KNC history is evidenced separately by entry 26.
The [current repository](https://github.com/RIKEN-SysSoft/mckernel) describes
Linux/POSIX compatibility as a design goal, not proof that every syscall works
on our card. Extends G14/G15. Suggested work: map SCIF, mmap, signals, futexes,
and thread creation to explicit local versus delegated services before coding.

### 14. HPCG requires convergence-aware scheduling and a traffic model

**Citation:** Jongsoo Park et al., *HPCG Results on IA: What Does It Tell about
Architecture?*, SC14 HPCG BoF, 2014
([presentation PDF](https://www.hpcg-benchmark.org/downloads/sc14/sc14-hpcg-bof-ver2.pdf)).
Related full paper: Park et al., *Efficient Shared-Memory Implementation of
High-Performance Conjugate Gradient Benchmark and Its Application to
Unstructured Matrices*, SC 2014,
pp. 945-955, [DOI 10.1109/SC.2014.82](https://doi.org/10.1109/SC.2014.82).
**Local:** `hpcg-sc2014-slides.pdf`; full-paper download unavailable.
**Goals:** S12-07, HPCG, sparse synchronization, symmetric MPI.

* Slide 7 explains why fused Gauss-Seidel/SpMV work can exceed a throughput
  estimate based on separate streaming passes: bytes were removed.
* Slide 9 contrasts level scheduling with block coloring, including differing
  iteration counts; the preferred strategy changes with multigrid level.
* Slides 5 and 8 distinguish Phi-only Tianhe-2 measurements from symmetric
  Stampede measurements and their bandwidth denominators.

**Limits / relation to notes:** Slides are not the full algorithm or current
HPCG rules. Do not combine SC14, later journal, and later benchmark-version
results. Complements R14 and qualifies a single STREAM-based roofline.
Suggested work: measure fine/coarse levels, synchronization, bytes, and complete
convergence separately; keep benchmark transformations out of general GCC rules.

### 15. WRF tile geometry can dominate the extra hardware threads

**Citation:** Samuel Elliott, *Performance Analysis and Optimization of the
Weather Research and Forecasting Model (WRF) on Intel Multicore and Manycore
Architectures*, SC15 student research poster extended abstract, 2015
([PDF](https://sc15.supercomputing.org/sites/all/themes/SC15images/src_poster/poster_files/spost161s2-file2.pdf)).
**Local:** `wrf-elliott2015.pdf`. **Goals:** WRF, MPI/OpenMP decomposition,
symmetric execution, G09/G15.

* P. 1 connects fewer MPI patches with less halo communication, while showing
  that placement is necessary to realize hybrid benefits.
* P. 1 separates history-output methods from compute timing; I/O can dominate
  apparent scaling.
* P. 2 ties OpenMP load imbalance to patch rows and tile geometry, and reports
  symmetric execution only for sufficiently large work per processor.

**Limits / relation to notes:** Stampede SE10P and E5-2660; this is a two-page
poster abstract, not a controlled general compiler comparison. P. 2's wording
about the workload threshold is awkward, so no universal crossover is adopted.
Extends G09 from runtime mechanisms to application decomposition. Suggested
work: capture per-thread tile sizes and compute/I/O/halo time before interpreting
WRF scaling as a compiler defect.

### 16. Climate radiation speedups include changes in numerical meaning

**Citation:** Amlesh Kashyap, Sathish S. Vadhiyar, Ravi S. Nanjundiah,
P. N. Vinayachandran, *Asynchronous and Synchronous Models of Executions on
Intel Xeon Phi Coprocessor Systems for High Performance of Long Wave Radiation
Calculations in Atmosphere Models*, JPDC 102, 199-212, 2017
([author PDF](https://cds.iisc.ac.in/faculty/vss/publications/amlesh-asyncsyncPhi-jpdc2017.pdf)).
**Local:** `wrf-radiation2017.pdf`. **Goals:** climate/WRF-adjacent workloads,
math costs, batching, host/card overlap.

* P. 4 aggregates small column chunks before offload, exposing enough parallel
  work and amortizing dispatch.
* Pp. 4-5 separate synchronous overlap from a model that consumes radiation
  results in a later timestep.
* Pp. 5-7 identify transcendental costs, use interpolation/table replacements,
  and vary floating-point compiler options; p. 10 discusses accuracy tradeoffs.

**Limits / relation to notes:** Two 7120 PX cards per node (p. 8). This is an
atmosphere-model radiation study, not a whole-WRF benchmark. Delaying results
and replacing math functions are scientific-model choices; its precision-flag
observations do not define GCC semantics. Reinforces G01/G05 while contradicting
any interpretation of the headline speedups as strict-math codegen alone.
Suggested work: profile strict radiation kernels first; put approximate math
and timestep changes in separately authorized application experiments.

### 17. Post-2018 work learns stream partitions and task granularity

**Citation:** Peng Zhang, Jianbin Fang, Tao Tang, Canqun Yang, Zheng Wang,
*Tuning Streamed Applications on Intel Xeon Phi: A Machine Learning Based
Approach*, 2018 [preprint arXiv:1802.02760](https://arxiv.org/abs/1802.02760).
**Local:** `stream-tuning2018.pdf`. **Goals:** host/card overlap, PGO-like
selection, task scheduling, G15/G16.

* Pp. 3-4 treat core partition count and queued task count as separate tuning
  decisions in an hStreams-based execution model.
* Pp. 5-6 combine static features and a short profiling run to select a learned
  configuration, rather than searching the full space at every launch.
* P. 7 uses held-out programs and keeps related convolution variants together
  when excluding training data, a useful protection against misleading results.

**Limits / relation to notes:** P. 6 identifies a 57-core KNC as "31SP", with
MPSS and a 2.6.38.8 device OS. This is library stream tuning, not GCC PGO, and
requires programs already expressed as streams. Extends G15/G16 with a concrete
training/evaluation design. Suggested work: use measured transfer and task
features to test simple policies before adopting a learned model; report
profiling and dispatch time in the comparison.

### 18. Vector Pascal is a compiler study with stronger language guarantees

**Citation:** Paul Cockshott, Susanne Oehler, Tian Xu, *Developing a Compiler
for the XeonPhi*, University of Glasgow Technical Report TR-2014-341, 2014
([institutional PDF](https://eprints.gla.ac.uk/93597/1/93597.pdf)).
**Local:** `vector-pascal2014.pdf`. **Goals:** vectorization design, compiler
costs, scalar remainder handling, OpenMP alternatives.

* Pp. 4-5 exploit array-language independence: outer dimensions can use cores
  while an inner dimension becomes SIMD work.
* Pp. 6-7 describe target pattern matching, gathers, vector loops, and scalar
  leftovers as explicit compiler transformations.
* Pp. 9-10 evaluate a 5110P and compare threading mechanisms and affinity choices.

**Limits / relation to notes:** Array-assignment semantics and frontend
restrictions are stronger than general C alias/dependency guarantees. The
report's affinity-disabled result is specific to its runtime and placement,
not a refutation of controlled affinity in R20/R22. This is the 2014 report,
not the expanded 2015 journal edition. Suggested work: use its separation of
thread-level and vector-level decisions as a design comparison, without importing
language assumptions into GCC legality checks.

### 19. BAAR used LLVM infrastructure without an LLVM KNC backend

**Citation:** Marvin Damschen and Christian Plessl, *Easy-to-Use On-the-Fly
Binary Program Acceleration on Many-Cores*, 2014 preprint / ADAPT 2015
([arXiv:1412.3906](https://arxiv.org/abs/1412.3906)).
**Local:** `baar2014.pdf`. **Goals:** compiler history, offload costing,
LLVM/ISPC search, G15.

* Pp. 2-3 show an LLVM-IR analysis/optimization route followed by generated C
  through the ISPC C backend and Intel compilation for the Phi.
* P. 3 makes offload suitability depend on parallelizable computation relative
  to communicated data, not just detecting a loop.
* Pp. 5-6 distinguish accelerated computation from communication costs and
  identify limitations of runtime acceleration and binary recovery.

**Limits / relation to notes:** 5110P, historical LLVM/Polly/ISPC/ICC stack.
"Binary acceleration" is not evidence that arbitrary native binaries can be
safely transformed, nor that LLVM contained an IMCI machine backend. Adds a
specific negative finding to the compiler search and reinforces G15's visible
transfer costs. Suggested work: recover transformation and profitability
concepts, not an assumed ready-to-port LLVM backend. No ISPC source was read.

### 20. MACVEC connects missed-vectorization reports to selective profiling

**Citation:** Antonio Gomez-Iglesias et al., *PerfExpert: Workflow for
Vectorization and Parallel Scalability*, SC15 MIC Tuning BoF, 2015, including
Ashay Rane et al.'s MACVEC segment
([IXPUG PDF](https://www.ixpug.org/docs/PerfExpert_SC15_MIC_Tuning.pdf)).
Related publication: Rane et al., *Unification of Static and Dynamic Analyses
to Enable Vectorization*, LCPC 2014 proceedings, 2015,
[DOI 10.1007/978-3-319-17473-0_24](https://doi.org/10.1007/978-3-319-17473-0_24).
**Local:** `perfexpert2015-slides.pdf`; original chapter not recovered.
**Goals:** PGO, optimization diagnostics, G16.

* Slides 10-12 combine hotspot profiles with reasons from compiler reports,
  instrumenting the hot loops for missing information.
* Slide 14 distinguishes recommendations that are safe independently from
  those requiring runtime checks. Observed input behavior alone is not proof.
* Slides 18-19 apply the same measurement-to-recommendation workflow to MPI
  protocols, collective algorithms, and process mapping.

**Limits / relation to notes:** A combined presentation, not a KNC-only
speedup dataset; MPI results later in the deck must not be attributed to the
vectorizer. Extends G16's causal method. Suggested work: correlate GCC missed
optimization reasons with real hotspots, then emit guarded recommendations or
versioning opportunities instead of treating a profile as a legality guarantee.

### 21. Hybrid BFS is a useful masked-gather workload

**Citation:** Mireya Paredes, Graham Riley, Mikel Lujan, *Vectorization of Hybrid
Breadth First Search on the Intel Xeon Phi*, Computing Frontiers 2017
([preprint arXiv:1704.02259](https://arxiv.org/abs/1704.02259)).
Companion: Paredes Lopez, *Exploring Vectorisation for Parallel Breadth-First
Search on an Advanced Vector Processor*, Manchester thesis, repository edition
2017 ([PDF](https://pure.manchester.ac.uk/ws/portalfiles/portal/60828897/FULL_TEXT.PDF)).
**Local:** `bfs-hybrid2017.pdf`, `paredes-thesis2017.pdf`.
**Goals:** masks, irregular control flow, gathers, G03/G12.

* Paper pp. 3-4 use different traversal/vectorization strategies for top-down
  and bottom-up search; one mapping is not optimal for every frontier.
* Pp. 4-5 maintain per-lane visited/parent state while gathering neighbors and
  limit the vectorized search depth before handling remaining work.
* P. 5 chooses a depth threshold from the studied graph behavior; p. 8 examines
  graph-size and degree effects.

**Limits / relation to notes:** 5110P, ICC 14, manually written intrinsics.
The paper calls them AVX-512 intrinsics, but the actual KNC target is IMCI;
do not enable `TARGET_AVX512F`. Thresholds from these graphs are not generic
compiler constants. The thesis is retained as a longer companion, not a second
independent experiment. Suggested work: add mask-density and early-exit shapes
to future representative irregular-kernel studies.

### 22. SCIF transfer policy depends on direction and PCIe topology

**Citation:** Bryant C. Lam, *Lightweight, Scalable, Shared-Memory Computing on
Many-Core Processors*, University of Florida PhD dissertation, 2015
([institutional PDF](https://ufdcimages.uflib.ufl.edu/UF/E0/04/94/01/00001/LAM_B.pdf)).
**Local:** `lam-thesis2015.pdf`. **Goals:** G15, multi-card execution,
small-message versus bulk transfer.

* Pp. 73-75 distinguish two-sided SCIF messaging, registered-memory DMA, and
  direct access through mapped remote regions, including completion handling.
* Pp. 77-80 compare nearby versus cross-socket card paths and distinguish remote
  reads from writes; transfer size alone is insufficient to pick a mechanism.
* P. 80 places latency and bandwidth measurements on a physical topology
  diagram, preventing intra-device bandwidth from being reported as PCIe speed.

**Limits / relation to notes:** Chapter 4's four-card 5110P system (p. 71),
not the TILE-Gx platform in earlier chapters. Thresholds are specific to that
host, MPSS, and topology. Adds measurable transport choices to R25. Suggested
work: record physical host/card paths and directional crossover curves before
building a transfer scheduler or interpreting a symmetric MPI result.

### 23. A numerical-kernel thesis records unsuccessful offload as well as wins

**Citation:** Samuel Khuvis, *Porting and Tuning Numerical Kernels in Real-World
Applications to Many-Core Intel Xeon Phi Accelerators*, UMBC PhD dissertation,
2016 ([institutional PDF](https://hpcf-files.umbc.edu/research/papers/Khuvis_PhDThesis2016.pdf)).
**Local:** `khuvis-thesis2016.pdf`. **Goals:** stencils, MPI/OpenMP, scalar
limitations, symmetric workload balance.

* Pp. 193-194 summarize matrix-free elliptic and biological-model studies:
  hybrid MPI/OpenMP and manual unrolling can matter beyond simply recompiling.
* P. 193 explains poor offload results for its elliptic problem through
  communication and the chosen execution model; native and symmetric execution
  have different costs.
* P. 194 contrasts independent-cell work with coupled ODE-solver work, for which
  parallelism and serial execution limits change the platform comparison.

**Limits / relation to notes:** Distinct maya 5110P and Stampede SE10P systems;
do not merge their columns or treat one Phi versus one CPU as an equal-node
comparison. Its offload restriction is an implementation choice, not a physical
ban on richer device runtimes. Extends R23 beyond one stencil generator.
Suggested work: preserve a failing-to-scale representative case alongside
optimized kernels when evaluating S12-08 and future runtime work.

### 24. FFT planning and application integration can dominate FFT arithmetic

**Citation:** Florian Wende, Martijn Marsman, Thomas Steinke, *On Enhancing
3D-FFT Performance in VASP*, CUG 2016
([proceedings PDF](https://cug.org/proceedings/cug2016_proceedings.orig/includes/files/pap111.pdf)).
**Local:** `vasp-fft2016.pdf`. **Goals:** FFT libraries, allocation/planning,
thread density, application-level measurement.

* Pp. 2-3 distinguish FFT plan creation, execution, and destruction, comparing
  FFTW and MKL interfaces rather than timing arithmetic alone.
* P. 4 finds limited benefit from expensive FFTW planning on the tested Phi
  grids and scaling only over a restricted thread range.
* Pp. 6-7 cache compatible plans in a wrapper and measure recurring planner
  costs separately from transform execution.

**Limits / relation to notes:** Phi 5120D, 59 cores (p. 2); several integration
plots are Haswell results. A wrapper gain is not proof of a better IMCI FFT
backend, and a small-grid optimum is not a whole-card throughput limit.
Extends G09/G10 to a concrete library workload. Suggested work: separate plan
lifetime, outer transform concurrency, and inner FFT threading in any FFT ticket.

### 25. AMG coarse solvers challenge a single STREAM roofline

**Citation:** Alex Druinsky, Pieter Ghysels, Xiaoye S. Li, Osni Marques,
Samuel Williams, Andrew Barker, Delyan Kalchev, Panayot Vassilevski,
*Comparative Performance Analysis of Coarse Solvers for Algebraic Multigrid on
Multicore and Manycore Architectures*, PPAM 2015 proceedings
([NERSC author PDF](https://portal.nersc.gov/project/sparse/xiaoye-web/ppam2015.pdf)).
**Local:** `amg-ppam2015.pdf`. **Goals:** sparse solvers, HPCG-adjacent reasoning,
memory-traffic models.

* Pp. 4-7 compare iterative coarse solves with HSS-compressed sparse
  factorization, including ordering and factorization work.
* P. 9 builds operation and byte counts for separate multigrid phases rather
  than assigning the whole algorithm one arithmetic intensity.
* P. 10 explains that AMG memory-access patterns differ substantially from
  STREAM and changes the coarse-solver traffic model accordingly.

**Limits / relation to notes:** The study labels its Phi platform Knights
Corner; a commercial SKU was not established from the inspected text, so none
is inferred. HSS is a solver change with setup and accuracy consequences, not
an interchangeable HPCG optimization. Extends R14/G03/G11. Suggested work:
build phase-specific measured-byte models before deciding whether gathers,
synchronization, or scalar execution limit a sparse solve.

### 26. Segmentation research is evidence about translation cost, with a hard ABI limit

**Citation:** Yuki Soma, Balazs Gerofi, Yutaka Ishikawa, *Revisiting Virtual
Memory for High Performance Computing on Manycore Architectures: A Hybrid
Segmentation Kernel Approach*, ROSS 2014,
[DOI 10.1145/2612262.2612264](https://doi.org/10.1145/2612262.2612264)
([author PDF](https://bgerofi.github.io/papers/ysoma-ross14.pdf)).
**Local:** `soma-segmentation2014.pdf`. **Goals:** PhiNix memory management,
TLB effects, G08/G14.

* P. 3 identifies the obstacle to disabling paging in x86-64 long mode; the
  experiment instead uses 32-bit segmentation.
* Pp. 4-5 combine segmentation cores with a paging kernel and require a modified
  linker layout for application loading.
* Pp. 6-7 compare translation regimes on KNC, including a single-thread Graph500
  prototype and both ordinary and large-page Linux baselines.

**Limits / relation to notes:** The 32-bit segmented application and 64-bit
paged baseline are not identical ABIs; the prototype is not a general 64-bit
Linux replacement. Headline improvement over 4 KiB pages must not be presented
as improvement over tuned huge pages. Complements R09/G08. Suggested work:
first quantify translation costs under existing page sizes; retain segmentation
as a bounded research counterexample, not PhiNix's default memory model.

### 27. mOS provides a design alternative, not a finished KNC OS claim

**Citation:** Robert W. Wisniewski, Todd Inglett, Pardo Keppel, Ravi Murty,
Rolf Riesen, *mOS: An Architecture for Extreme-scale Operating Systems*,
ROSS 2014 ([presentation](https://htor.inf.ethz.ch/ross2014/slides/ross2014-wisniewski.pdf));
[project wiki](https://github.com/intel/mos/wiki).
**Local:** `mos-ross2014-slides.pdf`; a presentation, not the full paper.
**Goals:** PhiNix service placement, Linux compatibility, OS noise.

* Slide 10 proposes combining Linux API/ABI compatibility with a lightweight
  execution environment on compute cores.
* Slide 11 separates application I/O from service execution to reduce noise and
  cache interference, while acknowledging aggregation needs at scale.
* The wiki's publication history explicitly says parts of the initial design
  changed or disappeared during implementation; the 2014 architecture is not
  a specification of the later code.

**Limits / relation to notes:** These are system-design materials, not a KNC
boot/performance evaluation. Later mOS/KNL work transfers only the service and
resource-management ideas until an actual K1OM implementation is established.
Extends G14 alongside, rather than conflating with, IHK/McKernel. Suggested work:
compare a small set of required services under integrated-kernel and split-kernel
designs, charging service-core and communication overhead explicitly.

### 28. YASK's folding is a useful stencil idea, not a verified current KNC target

**Citation:** Chuck Yount, *YASK Tutorial*, April 8, 2024, for YASK 4.05.00
and later ([project PDF](https://intel.github.io/yask/YASK-tutorial.pdf));
[YASK repository](https://github.com/intel/yask).
Related original: Charles Yount, *Vector Folding: Improving Stencil Performance
via Multi-dimensional SIMD-vector Representation*, HPCC 2015,
[DOI 10.1109/HPCC-CSS-ICESS.2015.27](https://doi.org/10.1109/HPCC-CSS-ICESS.2015.27).
**Local:** `yask-tutorial.pdf`; original paper not recovered.
**Goals:** stencils, layout, prefetching, cost-model experiments.

* Pp. 60-63 arrange a small multidimensional block inside a vector, changing
  neighbor reuse and the memory layout together.
* P. 64 exposes independent software-prefetch distances for cache levels.
* Pp. 65-66 connect dimension ordering and grouping of stencil equations to
  generated loops and shared-expression opportunities.

**Limits / relation to notes:** This is a later tutorial, not the 2015 KNC
experiment. Current compiler requirements and targets do not prove a supported
KNC build. Only layout/reuse and tuning methodology transfer; IMCI permutations
and generated-code costs require separate implementation and measurement.
Adds a distinct layout approach beyond R23. Suggested work: compare one folded
and one ordinary stencil layout, including shuffle cost and boundary handling.

### 29. Portable vector libm methodology remains relevant after Phi

**Citation:** Naoki Shibata and Francesco Petrogalli, *SLEEF: A Portable Vectorized
Library of C Standard Mathematical Functions*, IEEE TPDS 31(6), 1316-1327,
2020, [DOI 10.1109/TPDS.2019.2960333](https://doi.org/10.1109/TPDS.2019.2960333)
([preprint](https://arxiv.org/abs/2001.09258)).
**Local:** `sleef2020.pdf`. **Goals:** vector math design and verification,
G05/G13; adjacent methodology, not Phi performance evidence.

* Pp. 2-4 separate vector-operation abstraction from math algorithms and discuss
  FMA-dependent versus consistent-result implementations.
* Pp. 5-8 distinguish accuracy variants and range-reduction work, relevant to
  divergent lanes and strict rounding requirements.
* P. 9 describes reference-based testing; function throughput and numerical
  validation are separate concerns.

**Limits / relation to notes:** No KNC support or benchmark is established by
this source. ULP targets do not by themselves establish errno, exceptions,
rounding-mode, NaN, or signed-zero contracts required by a libm replacement.
Extends G05 with a modern portable design to study independently. Suggested
work: define a vector-math contract and reference-testing plan before selecting
algorithms. No implementation or vendor math code was copied.

### 30. A current KNC OS revival has a narrowly stated hardware baseline

**Citation:** Xeon Phi Revival Project,
[xeon-phi-revival repository README](https://github.com/Xeon-Phi-Revival-Project/xeon-phi-revival),
inspected 2026-11-14, section "Current Prerelease: XPR-OS 0.1.0-rc7".
**Local:** none; README only. **Goals:** PhiNix, current userland/toolchain
revivals, avoid duplicating existing preservation work.

* The README reports a project-built K1OM kernel, MIC modules, and bootstrap/final
  device operating environments, rather than merely card enumeration.
* It reports a CPython 3.12.13 core and deployment/recovery tooling.
* Its stated tested target is a 5110P using an already working CentOS 7.4 and
  MPSS 3.4.10 host; fresh host installation and other cards are not validated.

**Limits / relation to notes:** Repository self-report, not an independently
reproduced result in this ticket. The README explicitly calls it an experimental
prerelease, not a modern production distribution. No inference is made about
upstream kernel version, SIMD compiler completeness, or compatibility with our
card. Adds a concrete 2026 lead beyond R11/R25. Suggested work: compare documented
boot, kernel, and libc boundaries with PhiNix's requirements before duplicating
the effort; inspect licensing and component history in any subsequent code-use
ticket. No software was installed or run.

## Repository and revival cross-checks

These are discovery pointers and inspected documentation, not code approved for
import. Web locators replace page numbers. None was cloned, built, or run here.

| Artifact and primary source | Findings and limits relevant to our goals |
| --- | --- |
| [Ainsworth TOCS 2019 artifact](https://github.com/SamAinsworth/reproduce-tocs2019-paper), README | Identifies itself as the experimental artifact for entry 01 and uses Collective Knowledge. Recover benchmark variants and parameters before claiming a modern LLVM pass will compile unchanged. |
| [CSR5](https://github.com/weifengliu-ssslab/Benchmark_SpMV_using_CSR5), README, KNC and KNL sections | KNC 5110P/double-precision path is separate from the added KNL AVX-512 path. This is a concrete sparse artifact; small-matrix fixes in its history matter when choosing a future baseline. |
| [QPhiX](https://github.com/JeffersonLab/qphix), README, build configuration | Documents a MIC target and structure-of-arrays choices alongside other architectures. Useful stencil/BLAS-like kernel boundary; repository presence is not a current successful GCC-KNC build. |
| [apc-llc/gcc-5.1.1-knc](https://github.com/apc-llc/gcc-5.1.1-knc), repository overview | Historical KNC GCC fork to identify against existing donor history, not a newly discovered modern vector compiler. This survey did not establish complete IMCI coverage or build it. |
| [ISPC 1.9.0 release](https://github.com/ispc/ispc/releases/tag/v1.9.0), release record; entry 19's pp. 2-3 | Historical ISPC/LLVM involvement must be separated from final native code generation. BAAR's generated-C/ICC route is verified; no complete standalone LLVM IMCI backend was recovered. No ISPC implementation or KNC vendor headers were opened. |
| [IHK/McKernel](https://github.com/RIKEN-SysSoft/mckernel), README; [release history](https://www.pccluster.org/en/hpc/mckernel.html) | README describes selective syscall delegation and isolation. The release history's KNL/HFI configurations are not KNC deployment evidence; entry 26 supplies the separate historical KNC experiment. |
| [mOS wiki](https://github.com/intel/mos/wiki), publications and versioned guides | Later implementation differs from the ROSS14 architecture. Versioned memory-management/scheduler documentation is a useful design lead, but target generation must be established before treating it as a K1OM donor. |
| [Popcorn Linux](https://popcornlinux.org/), project site; entry 03 | Later heterogeneous-ISA work spans other CPUs. Use the EuroSys15/thesis evidence for KNC specifically; later ARM/x86 results do not validate a current Phi port. |
| [Philix](https://users.eecs.northwestern.edu/~kch479/philix/documentation.html), Prerequisites / Using philix | Documents KNC, MPSS 3.4.2, and a k1om GCC toolchain; a Multiboot2 route and minimal example kernel help boot experiments. It is boot infrastructure, not a modern Linux kernel or POSIX runtime. |
| [devcapcap/XeonPhi](https://github.com/devcapcap/XeonPhi), README, results | Describes MPSS 4.4.1/x200 modules with a 5.6-rc host and mixed card experiments. Enumeration and management output with no device OS version do not establish a booted modern KNC kernel; KNL/KNC wording in the README is inconsistent. |
| [mpss-centos7-uefi](https://github.com/dvokhmintsev/mpss-centos7-uefi), README, problem and reference hardware | Reports a host module-signature/UEFI obstacle and a 7120A on a specific CentOS setup. This is host-side compatibility work, not proof of a new card kernel. Its security-policy change is not a deployment recommendation for PhiNix. |
| [llama.cpp PR 6440](https://github.com/ggml-org/llama.cpp/pull/6440), description; [XPR revival](https://github.com/Xeon-Phi-Revival-Project/xeon-phi-revival), prerelease section | Highest-priority recent leads for LLM and OS work respectively; entries 04 and 30 separate claims from validation. Neither was imported. |
| [CVR](https://github.com/puckbee/CVR), repository description | CGO 2018 sparse-vector work is a potential comparison, but its KNL/AVX-512 implementation is not KNC machine code. Use only portable format/load-balance ideas after examining applicability. |
| [DeepBench](https://github.com/baidu-research/DeepBench), platform/results documentation | Xeon Phi 7250 results concern KNL. Dense/conv training-style measurements do not establish KNC quantized GEMV or autoregressive decoding performance. |

## Breadth, editions, and sources still worth recovering

The search covered ACM/IEEE proceedings and author copies, Springer, arXiv,
SC/ISC/IPDPS/ICS/PACT/CGO/CC/LCTES/ROSS/HPDC terms, Intel/IXPUG material,
institutional theses, and public repositories. It used KNC, Knights Corner,
K1OM, Xeon Phi, and system names as well as the compiler/runtime/OS/application
terms. Positive results include CGO, ICS, IPDPS, SC, ROSS, EuroSys, CF, PPAM,
HPCC, and LCPC. CC/LCTES/PACT/HPDC searches did not yield an additional
page-verified, directly useful KNC compiler source; that is a search outcome,
not evidence that none exists.

| Coverage area | Recovered evidence / remaining limitation |
| --- | --- |
| TACC / NERSC / US laboratories | MACVEC/PerfExpert (20), HPCG (14), NERSC/LBNL/LLNL AMG (25), and the Jefferson Lab/Regensburg QCD study (11) supply primary evidence. ORNL/Beacon application-porting material was encountered through the climate paper's related work, not reclassified as independently read experiments. |
| LRZ / PRACE | The starting bibliography already has PRACE Best Practice Guide v2, R18. Its broad advice was not counted as a new discovery. |
| Juelich / DEEP | The institutional [DEEP PRACEdays15 presentation](https://juser.fz-juelich.de/record/202671/files/DEEP_PRACEdays15_Suarez.pdf?subformat=pdfa) is a lead for cluster/booster MPI and load balance. Direct acquisition failed certificate validation; no local copy or page-level claim is made. |
| CSCS / CINECA | CSCS participates in Splotch (08); historical [CSCS cluster-manager report](https://www.cscs.ch/fileadmin/user_upload/contents_publications/technical_reports/bright-cluster-manager-2013-final.pdf) and [CINECA Phi training](https://hpc-forge.cineca.it/files/ScuolaCalcoloParallelo_WebDAV/public/anno-2015/24_Summer_School/IntelXeonPhi_Rome.pdf) were discovery leads, not additional ranked papers. Later CSCS/CINECA KNL/Caffe material was not presented as KNC evidence. |
| China / Tianhe-2 / NSCC | NUDT's stream-tuning study (17) and the Tianhe-2 versus Stampede distinction (14) are concrete results. NSCC-specific searches did not produce an additional full-text source. Li et al., *Parallelizing and Optimizing Large-Scale 3D Multi-Phase Flow Simulations on Tianhe-2*, CPE 28 (2016), 1678-1692, [DOI 10.1002/cpe.3717](https://doi.org/10.1002/cpe.3717), remains an abstract-level lead for cache blocking and heterogeneous balance; no page claims are inferred. |
| Theses across countries | Glasgow (18), Manchester (21), Virginia Tech (03), UMBC (23), Florida (22), and Eindhoven (09) were downloaded. A Karlsruhe Damschen thesis download timed out; the BAAR paper (19) supplies the accessible core result. Spanish-language Uruguay work below extends the search beyond English-language proceedings. |
| Japan / later system research | RIKEN's KNC segmentation experiment (26), IHK/McKernel (13), and the SC21 KNL/A64FX comparison (12) preserve the hardware distinctions. Later Japanese KNL FFT/scheduling results were not substituted for KNC data. |

The following are **acquisition leads, not fully read annotations**. They are
excluded from page-supported recommendations where full text was unavailable:

* Anh-Tu Ngoc Tran et al., *pyMIC-DL: A Library for Deep Learning Frameworks
  Run on the Intel Xeon Phi Coprocessor*, HPCC/SmartCity/DSS 2018,
  [DOI 10.1109/HPCC/SmartCity/DSS.2018.00061](https://doi.org/10.1109/HPCC/SmartCity/DSS.2018.00061),
  [author institution record](https://research.aalto.fi/en/publications/pymic-dl-a-library-for-deep-learning-frameworks-run-on-the-intel-/).
  The abstract describes a NumPy-like extension to pyMIC. Recover full text and
  artifact before treating it as a deployable modern inference library.
* Thanh-Dang Diep et al., *Chainer-XP: A Flexible Framework for ANNs Run on the
  Intel Xeon Phi Coprocessor*, HPSC 2018 proceedings, pp. 133-147,
  [Springer chapter](https://link.springer.com/chapter/10.1007/978-3-030-55240-4_7),
  first online **December 2, 2020**. A 2019 upload is not its publication date.
  The abstract explicitly targets KNC through pyMIC; it is GEMM/offload evidence,
  not quantized LLM decoding. Its claim that the device can only interpret
  C/C++/Fortran describes the assumed software route, not an architectural ban
  on other languages. Full chapter was subscription-only.
* Matias Carro and Pablo Da Costa Porto, *Computacion cientifica de alto
  desempeno en sistemas Xeon Phi*, Universidad de la Republica, 2023,
  [institutional record](https://www.colibri.udelar.edu.uy/jspui/handle/20.500.12008/43442).
  The record describes a TBB-based scientific application and unresolved
  vectorization/locality work. Retrieval returned HTTP 403; hardware edition,
  exact methods, and page-specific results remain unverified.
* The original HPCG SC14 paper, MACVEC LCPC chapter, and Yount HPCC15 paper merit
  recovery before implementation. Their available presentations/tutorial are
  labeled as such in entries 14, 20, and 28. The BLIS paper was readable through
  web extraction but direct downloads timed out; no missing local file is
  represented as downloaded.

## What we overlooked: proposed follow-up tickets

These are suggested scopes, not newly assigned ticket IDs. Existing S12-06,
S12-07, and S12-08 are named only where the starting bibliography already points
to them. Each proposal needs its own acceptance and any required card time.

| Priority | Suggested ticket | Why it adds something beyond the starting notes |
| --- | --- | --- |
| 1 | **Indirect-prefetch legality and cost study** (01; relevant to S12-07) | Go beyond gather throughput: include dependent address loads, bounds safety, look-ahead, and instruction overhead. Compare useful latency reduction with bandwidth saturation. |
| 2 | **Region-dependent libgomp SMT policy** (02) | Measure total runtime including calibration and short regions; compare densities under controlled affinity, with an explicit fallback policy. |
| 3 | **KNC Linux port archaeology and current revival comparison** (03, 30) | Recover the concrete 2.6.38.8-to-3.2.14 subsystem changes and compare XPR's documented boundaries with PhiNix requirements. Do not mistake a new userland for an upstream-modern card kernel. |
| 4 | **One independently specified quantized KNC dot product** (04, 09, 11) | A direct LLM precursor exists. Charge unpack, scales, widening, tails, reductions, and memory traffic; distinguish prompt processing from token decoding and validate numeric output. |
| 5 | **Sparse format and complete-solver comparison** (05, 06, 14, 25; S12-07) | Compare CSR/SELL/CSR5 only with preprocessing, actual bytes, synchronization, and convergence accounted for. Faster isolated kernels can lose complete solves. |
| 6 | **Persistent SCIF dispatch and buffer lifecycle** (07, 22) | Separate small control messages, payload transfer, registration, completion, and reuse; make topology and direction explicit. |
| 7 | **Allocation lifetime diagnosis before malloc tuning** (08, 24) | Application allocation and FFT planning can dwarf kernels. Distinguish unnecessary repetition from allocator contention and remote first-touch effects. |
| 8 | **Scalar and libm costs in mixed-placement models** (03, 09, 16; S12-06/S12-08) | Published profilers used crude library-call costs, and numerical workloads expose expensive scalar work. Use measured call/bridge costs without enabling implicit fast math. |
| 9 | **Tuned Linux versus LWK service budget** (12, 13, 26, 27) | Include interrupts, worker threads, heap/page behavior, delegated calls, reserved resources, and a compatibility matrix before claiming OS-design gains. |
| 10 | **WRF decomposition and symmetric balance diagnosis** (15, 16, 23) | Record patch/tile occupancy, halo and I/O time, rank/thread placement, and host/card work ratios before attributing scaling to GCC. |
| 11 | **Dense kernel packing and sibling-cache mapping** (10, 11) | BLIS and QCD give constructive data/thread layouts. Keep GEMM reuse, GEMV streaming, and low-precision storage experiments separate. |
| 12 | **Profile-guided missed-vectorization triage** (17, 20, 21) | Combine hotness with compiler reasons and observed mask/stride behavior. Require guards or static proof; hold out related workloads during tuning. |
| 13 | **Folded stencil layout experiment** (28) | Compare reuse gains with IMCI shuffle cost, boundaries, and layout-conversion cost; do not assume a later AVX-512 generator is a KNC backend. |
| 14 | **Vector math contract and independent validation design** (29) | Specify accuracy, exceptions, rounding modes, special values, and scalar fallback before implementing a portable vector-math library. |

No GCC builds, x86 checks, or card jobs were run for this research ticket.
No native performance claim was validated locally. No vendor headers, SVML,
libimf, Intrinsics Guide XML, or third-party implementation code was imported.
