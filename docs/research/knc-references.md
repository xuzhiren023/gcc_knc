# KNC reference index

S12-13, 2026-11-14. Stable source numbers extend those assigned by
[S12-10](knc-reference-gaps.md). Use this index for new citations. The digest is
[knc-digest-2026-11.md](knc-digest-2026-11.md). Sources were read locally;
there was no new retrieval or card experiment.

Paths in the main table are relative to `.work/_shared/knc-refs/` in the
project's shared area, not this disposable worktree. A PDF and its `.txt`
extraction are **one source**. The PDF controls pagination, symbols and table
columns. R11, R24, R25 and R26 retain their original group numbers; suffixes
identify their distinct files. A bare group number means the group, not an
unspecified edition. Hardware status is explicit where established; an
unknown stepping or production status is not filled in from a model-like name.

“Authoritative for” describes the source's scope. A paper establishes what its
authors measured, not a measurement on our card. A specification establishes
an interface subject to errata, not instruction timing. A source snapshot
establishes its implementation, not the installed MPSS binary.

| ID | Source and edition | Hardware / production status | Authoritative for; useful locator | Must not be used for | Local file(s) |
| --- | --- | --- | --- | --- | --- |
| R01 | Intel, *Xeon Phi Coprocessor System Software Developers Guide*, 328207-001EN, November 2012, 201 pages | KNC architecture; early guide, not a stepping-qualified production experiment | Core/decoder, cache and translation structure, threading: §§2.1.1–5, pp.18–24 | The unidentified 163-page guide's pagination; a complete pairing/timing model; resolving its own inconsistent L2 bank/duty-cycle descriptions; its p.24 counter-count overview over R10/R11 | `ssdg-2012.pdf`, `ssdg-2012.txt` |
| R02 | Rezaur Rahman, *Intel Xeon Phi Coprocessor Architecture and Tools*, Apress, 2013 | KNC; descriptive material and examples, no single qualified production stepping | Operand forwarding and eligible V-pipe classes, pp.32–34; encoding/pair restrictions, p.56 | Copying example code; treating historical mnemonics as current encodings; unconditional pairing or a complete production timing table | `rahman-2013.pdf`, `rahman-2013.txt` |
| R03 | H.J. Lu et al., *System V ABI: K1OM Architecture Processor Supplement*, v1.0, April 26, 2012 | K1OM ABI, independent of card model/stepping | Register arguments/returns, stack and preserved state, §§3.2.1–3, pp.15–22, especially Fig.3.4 p.21 | SSE instruction availability from the ABI's class names; bridge latency; proof that a compiler, DSO or kernel implements the ABI | `k1om-psabi-1.0.pdf`, `k1om-psabi-1.0.txt` |
| R04 | Marius Cornea, *Numerical Computation on Intel Xeon Phi Coprocessors Using the Intel Compilers and Math Libraries*, October 15, 2013 | KNC FP architecture and Intel compiler behavior; no local production validation | Gradual underflow, flags versus traps, x87/IMCI distinction, slides 9, 18 | GCC numerical proofs, installed libc behavior, permission to substitute fast math, or vendor math implementations | `cornea-2013.pdf`, `cornea-2013.txt` |
| R05 | Hofmann, Treibig, Hager, Wellein, *Performance Engineering for a Medical Imaging Application on the Intel Xeon Phi Accelerator*, arXiv:1401.3615, 2014 | Production-model 5110P, 60 cores, 1.05 GHz; stepping unspecified | Gather completion experiment, §V.D/Table II p.4; prefetch/application qualifications and machine, p.5 | Scatter costs; equating a gather instruction with its completion loop; transplanting approximate arithmetic or application speedups | `hofmann-gather-2014.pdf`, `hofmann-gather-2014.txt` |
| R06 | Zhenman Fang et al., *Measuring Microarchitectural Details of Multi- and Many-Core Memory Systems through Microbenchmarking*, TACO 11(4), article 55, December 2014 | Explicit **pre-production engineering sample**, 1 GHz, Linux 2.6.38.8, ICC 13.0.1 (§4, p.55:10) | Experimental methods and that sample's memory capacities, §§5–6, Table V p.55:19 | Production queue constants; equating L1 MSHRs, L2 MSHRs and combined requests; publication year inferred from filename | `fang-taco2015.pdf`, `fang-taco2015.txt` |
| R07 | Jianbin Fang et al., *Test-Driving Intel Xeon Phi*, ICPE 2014, pp.137–148 | 5100-series, 60 cores, 1.05 GHz (p.139); exact model/stepping and production qualification unspecified | Dependent latency versus aggregate throughput, §3.1 pp.139–140; memory experiments §3.2 | Substituting for R06's different system; timing our x87/ABI paths or assuming a named series proves our stepping | `fang-icpe2014.pdf`, `fang-icpe2014.txt` |
| R08 | John D. McCalpin, *Native Computing and Optimization on the Intel Xeon Phi Coprocessor*, IXPUG 2014 | SE10P; exact stepping/production qualification not supplied in the cited slides | Concurrency, loaded latency, density and prefetch in that configuration, slides 23–25, 28 | Universal serial prefetch distances, a production 7120 ceiling, or treating idle latency as loaded latency | `mccalpin-ixpug2014.pdf`, `mccalpin-ixpug2014.txt` |
| R09 | Karthik Raman, *Stream on Intel Xeon Phi Coprocessors*, updated October 22, 2013 | All results explicitly **pre-production**, on 2.6.x uOS: p.4 5110P/7110P, MPSS 2.1.4346-16; p.5 7110P, MPSS 2.1.4982-15, and 7120P, MPSS 2.1.6720-15 | Historical STREAM settings pp.2–4; card-side THP support in KNC_gold_update_1-2.1.4982-15 or later, p.4; libhugetlbfs results p.4 and THP-stack results without libhugetlbfs p.5 | **Superseded:** ~~Claiming its performance table tested that later THP stack~~ — p.5 does report THP-stack results. Neither page proves present MPSS 3.7 malloc promotion/backing (S12-12 G08 remains needed); no universal 64/8-line defaults or ECC changes | `raman-stream-2013.pdf`, `raman-stream-2013.txt` |
| R10 | Intel, *Xeon Phi Coprocessor Performance Monitoring Units*, 327357-001, rev.1.01, July 10, 2012 | KNC architectural PMU; some event definitions explicitly reference **A0**, not blanket production validation | Two 40-bit counters per hardware thread, pp.5–7,11; filtering and event units, pp.12–16 | Proof of perf/RDPMC permission, unbiased sampling, GBOX access, or a modern Xeon/KNL event map | `pmu-327357-001.pdf`, `pmu-327357-001.txt` |
| R11a | Linux contributors, upstream Linux v3.10, 2013, KNC perf driver | KNC PMU implementation; not installed 2.6.38-based MPSS | `knc_pmu`, `knc_event_constraints`, `knc_perfmon_event_map`: widths, event mapping and scheduling restrictions | Installed-kernel registration/backports or usable user access | `linux-v3.10-perf_event_knc.c` |
| R11b | Mpss-vt Linux fork, revision `b76c20`, KNC perf driver; snapshot date unestablished | KNC; kernel family 3.2.14 per R11c, not installed MPSS | That fork's event/constraint implementation and two-counter declaration | Treating this fork as our MPSS 3.7 kernel source | `mpssvt-perf_event_knc.c` |
| R11c | Mpss-vt revision `b76c20`, top-level Makefile | No hardware experiment | Version fields: 3.2.14, lines 1–4 | Driver correctness, installed binary identity or a release date | `mpssvt-Makefile` |
| R12 | Intel, *Xeon Phi Coprocessor x100 Product Family Specification Update*, 328205-016, March 2015 | Production x100; B0/B1/C0 applicability matrix pp.17–19; model and firmware identification earlier in document | Erratum triggers, specified workarounds and release/stepping scope; CD14/19/26/28 pp.22–25 | Assuming every erratum affects every image, “fixed/planned” means deployed, or ordinary WB stores trigger the UC-only CD26 condition | `errata-328205.pdf`, `errata-328205.txt` |
| R13 | Xinmin Tian et al., *Practical SIMD Vectorization Techniques for Intel Xeon Phi Coprocessors*, IPDPSW 2013, pp.1149–1158 | Intro names 5110P; actual Table 6.1 p.1155 is 61 cores/1 GHz/7936 MB, model and production status unspecified | Compiler techniques and memory-safety assumptions, §§III–V pp.1151–1154; configuration p.1155 | Calling the experiments 5110P solely from the introduction; safe padding in ordinary programs; copying examples or importing speedups | `tian-vectorization-2013.pdf`, `tian-vectorization-2013.txt` |
| R14 | Saule, Kaya, Catalyurek, *Performance Evaluation of Sparse Matrix Multiplication Kernels on Intel Xeon Phi*, arXiv:1302.1078, 2013 work; local rendering dated November 27, 2024 | Explicit **pre-release SE10P**, §2 p.2 | Useful-line density, private-cache replication and sparse locality, §§4.2–4.3 pp.7–10 | A 2024 experiment from the generated date; production constants; legal reassociation/reordering of a fixed strict benchmark | `saulea-spmv-2013.pdf`, `saulea-spmv-2013.txt` |
| R15 | Mingfei Ma et al., *Optimizing Non-Contiguous Memory Access on Intel Xeon Phi Coprocessors*, HPCC 2015, pp.1615–1620 | Production-model **7120P**, 61 cores/1.238 GHz/16 GB, Table I p.1619; stepping unspecified | Alternative lane/layout choices and their application-specific assumptions, §§III–IV pp.1616–1618 | Automatic legality of layout/padding changes; generic gather speedups; exact semantics from informal pack/unpack descriptions | `ma-noncontiguous-2015.pdf`, `ma-noncontiguous-2015.txt` |
| R16 | Michael Klemm, *Optimization Strategies for Intel Xeon Phi Coprocessors*, 2013 deck, 58 slides | KNC guidance; no one stepping-qualified model | Density, threading, vectorization diagnostics and memory advice, slides 51–54 | R17 slide numbering; Intel runtime variables as libgomp controls; experimental ICC hints as supported GCC options | `klemm-optimization-2013.pdf`, `klemm-optimization-2013.txt` |
| R17 | Michael Klemm, *The Intel Xeon Phi Coprocessor*, LMU seminar, December 11, 2014, 40 slides | KNC architectural overview, not a complete production timing experiment | Alternate-cycle single-context issue, registers, typical vector latency and cache geometry, slides 10–14 | Every vector latency being four; complete pairing; resolving slide 13/14's differing L1-latency wording | `klemm-microarch-2014.pdf`, `klemm-microarch-2014.txt` |
| R18 | Atanassov et al., editor Volker Weinberg, *Best Practice Guide Intel Xeon Phi*, PRACE/LRZ v2.0, January 31, 2017 | Mixed **KNC and KNL**; KNC OpenMP example uses 7110, p.60, stepping unspecified | KNC Intel-runtime blocktime and persistent-region/barrier distinction, §§13.2.4–5 pp.59–61 | KNL facts for KNC; Intel-library policy as proof of libgomp defaults or performance | `prace-bpg-v2.pdf`, `prace-bpg-v2.txt` |
| R19 | Vladimirov, Asai, Karpusenko, *Parallel Programming and Optimization with Intel Xeon Phi Coprocessors*, second edition, copyright 2013–2015 | Xeon hosts and KNC cards; examples differ; §4.5.4 is explicitly a multi-socket **Xeon host** | Workload-dependent placement, §4.4.5 p.341; first-touch NUMA scope, §4.5.4 pp.376–377 | Socket-style NUMA allocation on KNC; publication year from the later free-download announcement; universal density/arena settings | `colfax-2ed.pdf`, `colfax-2ed.txt` |
| R20 | Cramer, Schmidl, Klemm, an Mey, *OpenMP Programming on Intel Xeon Phi Coprocessors: An Early Performance Comparison*, MARC 2012 | Explicit **pre-production KNC**, p.2; commercial model/stepping not established | Early OpenMP/kernel experiments and grain/placement sensitivity, pp.3–6 | Present libgomp barrier costs or production timing constants; confusing KNC with the Knights Ferry work discussed as background | `cramer-openmp-2012.pdf`, `cramer-openmp-2012.txt` |
| R21 | Saini et al., *An Early Performance Evaluation of Many Integrated Core Architecture Based SGI Rackable Computing System*, NAS-2015-04 | Production-model **5110P**, Table 1 p.3 | Laboratory EPCC synchronization and loop-scheduling measurements, §6.5 pp.7–8 | A measured gain for our grouped barrier, or raw application time from the overhead statistic | `nasa-2015-04.pdf`, `nasa-2015-04.txt` |
| R22 | Romain Dolbeau, *Address Selection for Efficient Barriers on the Intel Xeon Phi*, rev.1.40, April 8, 2014 | Production-model **7120P**, 61 cores/1.238 GHz, p.2; stepping unspecified | Controlled physical-address communication and barrier experiments, §§II–III pp.1–7 | A portable DTD hash; our withdrawn M2 page-color attribution; copying its reboot/page-reservation procedure into scoring | `dolbeau-barriers-2014.pdf`, `dolbeau-barriers-2014.txt` |
| R23 | Thomas Lang, *An Intel Xeon Phi Backend for the ExaStencils Code Generator*, bachelor thesis, April 27, 2016 | 57 cores/1.1 GHz, ICC 16.0.1.150 (§4.1 p.29); exact model/production status unspecified | That application's perf attribution (~57% in OpenMP), §4.3 p.33 | Our perf availability, a transferable wait fraction, or a model number inferred from core count; damaged extracted numerals | `lang-thesis-2016.pdf`, `lang-thesis-2016.txt` |
| R24a | GNU C Library, tag glibc-2.21, 2015, `malloc/arena.c` | Upstream allocator, architecture-dependent; not a KNC deployment | `new_heap` and `arena_get2`: virtual reservation and CPU-derived arena limit | Equating reserved bytes with RSS, CPU count with inherited affinity, or upstream source with MPSS patches | `glibc-2.21-arena.c` |
| R24b | GNU C Library, tag glibc-2.21, `malloc/malloc.c` | Upstream; word-size-dependent | Threshold definitions and `mallopt`/`M_ARENA_MAX` handling | A universal fastest arena cap or installed behavior | `glibc-2.21-malloc.c` |
| R24c | GNU C Library, tag glibc-2.21, `sysdeps/i386/fpu/e_log.S` | **i386 x87**, not a K1OM implementation identity | Upstream log mechanism, including near-one path, `__ieee754_log` | Identifying our mapped log, its accuracy, or its timing | `glibc-2.21-e_log.S` |
| R25a | MPSS modules 3.6.1-1 mirror, revision `2850ead25b5c81ece2006d7ae06c2b3149175565`, `include/scif.h`; calendar date unestablished | MPSS host/card API, not verified installed 3.7 | Registration/lifetime and synchronous/CPU/ordered RMA interface, `scif_readfrom` and `scif_unregister` | Initiation as completion; general native huge-page policy; proof a deployed driver meets the API | `scif-3.6.1.h` |
| R25b | Same MPSS snapshot, `micscif/micscif_rma.c` | Host/card paths, with build-condition differences | `micscif_rma_copy`: final synchronous chunk polling, CPU path and registration-cache conditions | Matching 3.7 driver behavior or full DMA-erratum coverage from this one file | `scif-3.6.1-rma.c` |
| R26a | Intel MKL 11.3 Update 4 Developer Guide, 2016, KNC performance page, GUID-7F67CA7F-0B2D-4584-AE90-63A64A58F0EC | KNC native/offload library guidance; model unspecified | Scope of `MIC_USE_2MB_BUFFERS`: pointer-based offload transfers; memory section (HTML, no page) | A GCC native malloc control or observed current page backing | `mkl-11.3-knc-tuning.html` |
| R26b | Intel C++ Compiler 18.0 Linux release notes, Parallel Studio XE 2018, initial release 2017 | Explicit removal of x100/KNC support | “Support Removed” / 18.0 change list (HTML, no page) | Treating post-KNC Intel compiler/AVX-512 advice as IMCI support | `icc18-release-notes.html` |
| R27 | Intel, *Xeon Phi Coprocessor Instruction Set Architecture Reference Manual*, 327364-001, September 2012, 725 pages | KNC architectural interface; early specification, apply R12 for production errata | Instruction semantics/encoding; MXCSR §2.4 p.39 and §4.1 pp.55–56; NGO pp.393–398; prefetch pp.641–656 | Full timings, pairing, OS policy, or an algorithm's correct-rounding proof | **Shared-root paths:** `.work/_shared/intel-327364-001-xeon-phi-isa.pdf`, `.work/_shared/intel-327364-001-xeon-phi-isa.txt` |

The remaining top-level local files are inspection derivatives, not independent
evidence: `ssdg-2012-page.png` (R01), `rahman-2013-page.png` (R02 p.34),
`abi-page.png` (R03 p.21), and `hofmann-gather-2014-page.png` (R05 p.4).
`_pdf_tools/` contains the local PDF reader and its dependencies, not KNC
reference material. It is outside the source corpus and must not be cited as
hardware evidence. No vendor file or tool dependency is committed here.

## Citation and edition rules

Use `R02, p.34, Table 3-1`, `R17, slide 11`, or
`R24a, arena_get2, lines 838–857`. Pages mean **printed pages** unless explicitly
marked PDF pages. R03 printed p.21 is PDF p.22; R02 printed p.34 is PDF p.38,
but printed p.56 is PDF p.59: do not apply a constant offset throughout that
book. R19 printed p.341 is PDF p.367. R23 printed p.33 is PDF p.41.
R13 printed p.1155 is PDF p.7; R15 printed p.1619 is PDF p.5.
HTML and code have no page number: cite their heading, GUID, symbol and/or
line range instead. Cite facts in our own words; do not reproduce vendor
tables, prose, examples or code (ADR-0013).

Three SSDG identities must remain separate. R01 is recovered and paginated.
**328207-002, June 2013**, is reported in R22's bibliography (reference 10,
p.8); its original is absent. **488596 rev.2.03, November 8, 2012**, was
identified from a transcription by S12-10, but has no local PDF. The older
163-page guide in `knc-optimization-sources.md` has no positively identified
edition. None is an alternate filename for R01. Its pp.16–22 must not be
silently reassigned to R01.

Other missing references stay **reported**, not verified: x100 registers
**330991-001** (TUNE_PREFQ and GBOX details in older notes); matching MPSS 3.7
kernel/glibc patches and original guide; the later MPSS 3.8 guide transcription;
complete production timing, predictor and uncore manuals. Local path: **none**.
S12-10 records the acquisition outcomes. R10 closes the core-PMU document gap
only. New notes should cite the recovered R-source when it supports the fact,
or cite S12-10's missing-source record explicitly rather than invent an R-source
page for an unavailable document.
