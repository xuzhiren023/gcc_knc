# HP Z840: dual E5-2690 v3 and a Knights Corner coprocessor

Research for S12-11, 2026-11-14. The intended host has two 12-core E5-2690 v3 processors, DDR4 ECC RDIMMs, an x100 Xeon Phi of unknown SKU, and an RX 6700 XT. GPU compute is outside this note. No firmware, OS, compiler, or machine configuration was changed; no benchmark or card job was run.

## Recommendations, in priority order

1. **Resolve physical compatibility first:** identify the Phi, cooling assembly, PSU and harness. Prefer the CPU-connected x16 slots; a passive Phi needs a demonstrated air path through both sides of the card. Sources: HP platform documents, Intel card datasheet, then owner reports [H1–H5].
2. **Populate all eight host memory channels symmetrically.** Prefer one suitably sized RDIMM per channel when capacity permits; verify the actual clock before buying more DIMMs [H1, H6, H7].
3. **Use the host as the initial LLM baseline.** Measure one socket, both sockets, and SMT separately. A Phi experiment should keep weights resident and establish correct quantized kernels before claiming acceleration [L1–L3].
4. **Treat MPSS as a versioned legacy stack.** A documented Intel-era installation is a historical baseline; AlmaLinux 8.10 is a community candidate requiring a complete boot/SCIF qualification. Neither is a promise about an arbitrary current kernel [M1–M5].
5. **Place the offload process and its buffers beside the Phi's PCIe root.** Reuse registered buffers and measure transfer costs explicitly [M1, P1–P3].
6. **Choose work by measured end-to-end time.** Dense reusable kernels and sufficiently parallel streaming work are promising; sparse, branch-heavy and latency-sensitive work need separate evidence. Preserve floating-point requirements [P4–P10, T1–T4].

### Reading the evidence

**Verified (read)** means the cited primary document or data was inspected; it does not mean its results were reproduced here. **Reported** identifies an author's measurement or an owner/community claim, with its original hardware and software limits. **Derived** marks arithmetic or an engineering inference. Suggestions at the end are future measurements, not completed tests.

Downloaded references are outside git at `C:\Users\xuzhi\Documents\gcc_knc\.work\_shared\host-phi-refs\` (called `refs/` below). PDF page numbers are viewer pages unless a printed page is specified. Extracted `.txt` companions aid searching; the PDFs govern ambiguous tables. Web-only entries are identified explicitly. No vendor header, Intrinsics Guide XML, or ISPC implementation was consulted.

## 1. Slots, firmware, memory, power and cooling

### PCIe topology and firmware

**Verified, H1.** With both processors installed, HP's electrical slot map is:

| Slot | Electrical link | Root |
| --- | --- | --- |
| 1 | PCIe 3.0 x4 | CPU0 |
| 2 | PCIe 3.0 x16 | CPU0 |
| 3 | PCIe 3.0 x8 | CPU1 |
| 4 | PCIe 3.0 x16 | CPU1 |
| 5 | PCIe 3.0 x8 | CPU1; switches to a PCH Gen2 x4 path without CPU1 |
| 6 | PCIe 3.0 x16 | CPU0 |
| 7 | PCIe 2.0 x1 | PCH |

**Recommendation/derived:** consider Phi in slot 4 and GPU in slot 2, subject to physical clearance, intake space and cable reach. This gives independent CPU roots. Slots 2 and 6 are alternatives for placing both devices beside CPU0. Mechanical connector length alone does not establish electrical width. The Phi negotiates Gen2; expect 5 GT/s x16 under load, not Gen3 just because the slot supports it [H1, H4]. Linux NUMA node numbers must be discovered, not equated blindly with HP's CPU labels.

**Verified, M1/M2:** KNC requires a large, above-4-GB PCIe MMIO allocation; the Linux guide describes an 8-GB-or-larger aperture. This is address space, not an instruction to reserve eight GB of ordinary host RAM. **Unresolved:** the inspected HP F10 documentation does not establish a Z840 menu named “Above 4G Decoding.” Firmware may allocate it automatically. Check BAR assignment and driver diagnostics before changing anything. GPU Resizable BAR/SAM is a different feature and is not the KNC requirement.

**Verified, H3:** F10 exposes slot enablement, runtime power management, idle power saving and thermal controls. H1 p.28 documents Early Snoop and Home Snoop in M60 BIOS. **Recommendation:** retain NUMA locality (node interleaving off), leave PCIe speed on Auto, enable Turbo, and begin with a repeatable OS performance policy. Record temperatures and effective clock. Do not prescribe disabling every C-state: idle power and sustained AVX frequency are separate issues. Compare Home Snoop if remote traffic is significant; Cluster-on-Die is an experiment only if this firmware actually exposes it [T1, T2].

### Memory population

**Verified, H1/H6:** four channels per processor, two DIMM positions per channel; E5-2690 v3 supports up to DDR4-2133. HP's balanced four-DIMM-per-CPU placement uses that CPU's black positions 1, 3, 6 and 8. Eight equal-capacity RDIMMs across both processors give one DIMM per channel; for example, 8 x 16 GB gives 128 GB. Follow HP's population drawing, and do not mix RDIMMs and LRDIMMs.

**Verified with scope limit, H7:** Intel's E5-v3 server-board validation lists SRx4, SRx8, DRx8 and DRx4 RDIMMs at 2133 MT/s with 1 DPC and 1866 MT/s with 2 DPC. Its QR LRDIMM row differs. This is strong evidence for the v3 loading tradeoff, not a Z840-specific speed guarantee. Rank and DPC are different: a dual-rank RDIMM still occupies one slot. Match supported modules, capacities and ranks across channels; the sources do not establish that buying a particular rank count alone maximizes this workstation's performance.

**Derived:** four 64-bit channels at 2133 MT/s give 68.3 GB/s per socket, or 136.5 GB/s across two independently served sockets. At 1866, those ceilings become 59.7 and 119.4 GB/s, a 12.5% reduction. These are transfer-rate ceilings, not STREAM measurements. Filling a missing channel can matter more than DIMM speed; extra capacity can nevertheless be worth the 2-DPC penalty if it prevents paging. Remote allocations cannot simply claim the sum of both sockets' local bandwidth [H6, H7, T2].

### PSU, connectors and simultaneous heat

**Verified, H2:** HP requires the high-power 1125-W PSU option for the E5-2690 v3 configuration and lists three six-pin auxiliary graphics leads. Its available output varies with AC input; the tables give different high-line thresholds in different sections. Use the installed PSU label and actual mains voltage, with 1125 W as the conservative planning figure. The high-power configuration has two front fans. Keep the intended fan assemblies, guides and shrouds installed.

**Verified, H4/H5:** a reference RX 6700 XT is 230 W, 267 mm, two slots, with one eight-pin and one six-pin supply. Partner boards may differ. KNC model ratings differ: 5110P is nominally 225 W; 3120A/P and 7120P are 300 W; 7120A is 270 W. For a 300-W card Intel specifies both supplemental connectors; its 225-W configuration permits an eight-pin or two six-pin connections. Identify the actual card's connector specification rather than treating any eight-pin cable as interchangeable.

**Derived:** two 135-W processors plus a 225–300-W Phi and the reference GPU total 725–800 W before memory, disks and fans. This sum is neither wall consumption nor a transient rating. Three PSU leads versus four possible card plugs makes the harness a separate constraint. Establish rail/current limits, correct pinout, wire rating and an appropriate HP-compatible harness before simultaneous operation; total wattage alone does not approve a splitter. HP's graphics budget is not qualification of this exact Phi/GPU pairing.

**Reported, H8/H9:** a Z840 owner says a 3120A worked with the larger PSU; the post calls it “1175 W,” inconsistent with HP's 1125-W designation. An HP forum contributor reports 18 A/216 W capability per Z840 six-pin lead and use of six-to-eight-pin adapters. These are useful leads, not manufacturer approval of this machine's wiring or a passive-card thermal result.

### Active versus passive Phi

**Verified, H4:** active A models have an on-card blower; passive P models rely on system airflow through the primary heatsink and backside path. Figure 3-7 requires about 16 CFM total at 25 C inlet and 32.8 CFM at 45 C for its 270/300-W passive group, with approximately 0.16/0.54 inches of water pressure drop respectively. The 5110P has separate curves.

**Recommendation/derived:** a fan's free-air CFM does not prove delivered flow against the heatsink. A passive installation needs a fitted duct, inlet clearance, backside flow and measured thermal margin with the side panel fitted. An active card reduces dependence on a custom duct but still needs intake clearance. The inspected sources do not establish successful passive Phi plus RX 6700 XT cooling in a Z840. Resolve this before interpreting throttled performance.

### Hardware sources

- **H1 — HP, _HP Z840 Workstation Technical White Paper_, v3/v4-era revision, undated copy.** [PDF](https://zworkstations.com/site/assets/files/1044/hp-z840-technical-white-paper.pdf); `refs/hp-z840-technical.pdf`. Verified: pp.8–10 topology/link training; pp.23–25 memory and population drawing; p.28 snoop modes. The CPU labels in the slot table come from the dual-processor diagram.
- **H2 — HP, _QuickSpecs: HP Z840 Workstation_, DA-15098 v34, 2017-06-05.** [PDF](https://pcserverandparts.com/content/Spec%20Sheets/Workstations/HP/HP%20Z840/HP%20Z840%20Workstation%20QuickSpecs.pdf); `refs/hp-z840-quickspecs.pdf`. Verified: pp.3–6 processor/PSU/options, p.25 power, p.31 fans. Manufacturer document hosted by a reseller.
- **H3 — HP, _Z440, Z640, and Z840 Workstation Series Maintenance and Service Guide_, 2014/2016.** [PDF](https://h10032.www1.hp.com/ctg/Manual/c04823811.pdf); `refs/hp-z840-service.pdf`. Verified: printed pp.29–31, PDF pp.39–41, F10 settings. No verified numeric MMIO control in the inspected settings.
- **H4 — Intel, _Xeon Phi Coprocessor x100 Product Family Datasheet_, April 2015, 328209-004EN.** [PDF](https://www.intel.com/content/dam/www/public/us/en/documents/datasheets/xeon-phi-coprocessor-datasheet.pdf); `refs/intel-knc-datasheet.pdf`. Verified: §§2.1.4, 3.3, 4.2; pp.9, 13, 20–25, 47; figures 3-6/3-7. Intel interface/specification facts are paraphrased here; no vendor code is reproduced.
- **H5 — AMD, _Radeon RX 6700 XT Graphics Card_, current product page read 2026-11-14.** [Specifications](https://www.amd.com/en/products/graphics/desktops/radeon/6000-series/amd-radeon-rx-6700-xt.html), sections General, Requirements and Dimensions. Verified web-only; local HTML download timed out. Applies to the reference design.
- **H6 — Intel, _Xeon Processor E5-2690 v3 Specifications_, SKU 81713, read 2026-11-14.** [Specifications](https://www.intel.com/content/www/us/en/products/sku/81713/intel-xeon-processor-e52690-v3-30m-cache-2-60-ghz/specifications.html); `refs/intel-e52690v3.html`. Verified: CPU, memory and expansion fields; 12 cores/24 threads per socket, AVX2, four channels, 40 PCIe 3.0 lanes, 135 W.
- **H7 — Intel, _Server Board S2600CW Technical Product Specification_, rev.2.61.** [PDF](https://cdrdv2-public.intel.com/840480/S2600CW_TPS.pdf); `refs/intel-s2600cw.pdf`. Verified: printed p.36, PDF p.38, table 3, inspected visually. This is a different motherboard's validation matrix.
- **H8 — MWind2, Intel Community, _Samples from 2017 Fortran and C mic phi_, 2021-09-12.** [Thread](https://community.intel.com/t/samples-from-2017-fortran-and-c-mic-phi/102383); `refs/mpss-z840-owner.html`. Reported Z840/3120A ownership experience; not an electrical or cooling qualification.
- **H9 — NonSequitur777, HP Support Community, _Power out for video card_, 2024-03-24/25.** [Thread](https://h30434.www3.hp.com/t5/Desktop-Software-and-How-To-Questions/Power-out-for-video-card/td-p/9026775). Reported; web-only, direct download returned 403. The author's firsthand adapter example is a Z440; the Z840 current rating is an assertion in that reply.

## 2. MPSS, OS and transport choices

### Historical support versus community operation

**Verified, M1:** the April 2017 MPSS 3.8 Linux guide's table 2 specifies these combinations. They describe that release, not a blanket 3.8.6 certification:

| Distribution | Kernel in the 3.8 table |
| --- | --- |
| RHEL 6.7 / 6.8 / 6.9 | 2.6.32-573 / -642 / -696 |
| RHEL 7.1 / 7.2 / 7.3 | 3.10.0-229 / -327 / -500 |
| SLES 11 SP4 | 3.0.101-63-default |
| SLES 12 / 12 SP1 / 12 SP2 | 3.12.28-4 / 3.12.49-11 / 4.4.16-56-default |

**Verified, M2:** the Windows 3.8 readme lists 64-bit Windows 8.1 Enterprise, Windows 10, Server 2012 and 2012 R2. That October 2016 statement does not validate Windows 11 or every subsequent Windows 10 update. A Windows host still manages a separate Linux-based coprocessor environment. The host driver, card image, host/card runtimes and application toolchain all need compatible versions; installing a modern compiler alone does not restore legacy offload support.

**Verified source, reported operation, M3:** Jan Just Keijser documents MPSS 3.8.6 ports through CentOS 7.9 and CentOS 8.5, including 4.18.0-348.2.1. His guide explicitly reports boot, SSH and offload working. It addresses timer API changes, network scripts and daemon/sysfs ordering, showing why merely compiling `mic.ko` is insufficient. His listed Intel-era endpoint is RHEL 7.4 / 3.10.0-693. MPSS 4.4 targets the later Knights Landing PCIe products; it is not a KNC upgrade.

**Verified recipe, reported compatibility, M4:** the AlmaLinux project supplies an alpha MPSS 3.8.6-8 recipe/module for AlmaLinux 8.10, kernel `4.18.0-553.40.1.el8_10`, and a 5110P. This is a concrete newer candidate, not demonstrated support for all Alma/Rocky/RHEL 8 kernels or Linux 6.x. Its AI motivation is not a measured LLM result. No independent reproduction was performed here.

**Recommendation:** use a dedicated, recoverable host installation for MPSS qualification, with the exact kernel and module recipe recorded; keep a known bootable kernel. Prefer Linux for this project because the concrete community ports and NUMA/SCIF diagnostics are available there. Do not disable security services indiscriminately to imitate old recipes. Intel's 2020 advisory recommends 3.8.6 for an installer-permissions issue [M5]; that fixes a specific issue, not the maintenance status of the entire stack. Current host OS and acceptable maintenance tradeoffs remain owner decisions.

### SCIF and NUMA

**Verified, M1:** place the offload process on the NUMA node attached to the card. **Derived recommendation:** also first-touch or explicitly allocate its transfer buffers there; pinning a thread does not relocate already allocated memory. On this host, slot 4 suggests CPU1 locality, but confirm sysfs topology.

**Verified, P3:** SCIF offers registered-memory DMA/RMA and mapped remote buffers; HAM uses fences to order small control messages. **Recommendation:** allocate aligned reusable buffers, register once, batch transfers and separate initialization from steady-state timing. Double-buffer only with explicit completion/ownership rules. Measure host-to-card and card-to-host independently, and compare local versus remote host memory. Prefer SSH/virtual Ethernet for control and file setup; do not assume their performance represents SCIF [M6].

### Stack sources

- **M1 — Intel, _MPSS User's Guide for Linux_, rev.3.8, April 2017.** [Guide mirror](https://manualzz.com/doc/34876361/intel-mpss-software-stack-user-s-guide); `refs/mpss-3.8-linux-guide-extract.txt` is a partial web extraction, not the full guide. Verified: §§3.1.2–3.1.3, pp.31–32 (MMIO and OS table), §3.2.1.1 p.36 (NUMA); §3.4.3 (matching kernel driver). The direct Intel download was unavailable.
- **M2 — Intel, _MPSS for Windows Readme_, rev.3.8, October 2016, 328510-001.** [Lenovo-hosted PDF](https://download.lenovo.com/servers/mig/2017/02/13/6440/intc_dd_mic_3.8_windows_x86-64.pdf); `refs/mpss-3.8-windows-readme.pdf`. Verified: §2.1 p.6, host OS and BIOS requirements.
- **M3 — Jan Just Keijser, _MPSS_ and _Xeon Phi: MPSS on CentOS 8_, community notes through 8.5, read 2026-11-14.** [Index](https://jjkeijser.github.io/mpss/), [CentOS 8 guide](https://jjkeijser.github.io/mpss/xeon-phi-mpss-centos8.html); `refs/mpss-community.html`, `refs/mpss-centos8.html`. Author-reported successful operation; exact patch/kernel lists inspected.
- **M4 — ruribe17, _Xeon Phi 5110P KNC Drivers/Utilities for AlmaLinux_, 2025-era README.** [Repository](https://github.com/ruribe17/Xeon-Phi-5110P-KNC-Drivers-Utilities-for-AlmaLinux-8.1); `refs/mpss-alma8-readme.md`. Installation/rebuild sections and v0.1.0-alpha module URL inspected; compatibility remains reported.
- **M5 — Intel, _INTEL-SA-00340: MPSS Advisory_, 2020-02-11.** [Advisory](https://www.intel.com/content/www/us/en/security-center/advisory/intel-sa-00340.html); `refs/intel-mpss-advisory.html`. Verified: affected versions, CVE-2020-0563 and 3.8.6 recommendation.
- **M6 — Olli-Pekka Lehto, CSC/PRACE, _Practical Experiences with Intel Xeon Phi_, 2013–2014-era note.** [PDF](https://prace-ri.eu/wp-content/uploads/WP147.pdf); `refs/prace-knc-practice.pdf`. Verified: pp.2–3, MPSS generations, card filesystem and networking. Avoid filling a RAM-backed card filesystem with datasets; shared filesystems help capacity but introduce I/O costs.

## 3. Measured scientific results and their limits

All numerical results in this section are **reported measurements verified by reading**, not local passes. Older Sandy Bridge/Ivy Bridge comparisons cannot establish speedup over two Haswell E5-2690 v3 processors.

| Workload and source | Hardware/software and reported result | Decision supported |
| --- | --- | --- |
| MPI transport, NASA Maia [P1] | Dual E5-2670 Sandy Bridge, two production 5110P cards. For 4-MB messages, MPI update/SCIF improvements changed approximately 1.6 GB/s and 455 MB/s to about 6 GB/s for each card. | Transport selection and runtime version can dominate apparent hardware performance. |
| Symmetric OVERFLOW, NASA [P1] | Host plus two cards reached about 1.9x host-only; communication and imbalance still made it worse than using two host nodes. | Partition by measured rates and communication, not equal core counts. This is not a one-card Z840 result. |
| STREAM, Rupp [P4] | Dual Haswell: 88.9 GB/s at 24 threads; KNC: 142.7 GB/s at 240 threads, 64-million-double arrays. Below roughly 30 threads the host curves are stronger. | Phi needs broad parallelism; use sustainable traffic rates, not advertised pin bandwidth. Exact SKU is not established by the saved article text. |
| DGEMM and STREAM, Colfax [P5] | 7120P versus dual E5-2697 v2, ICC 15.0.1 / MPSS 3.4.1: DGEMM 984 versus 485 GF/s; STREAM 176 versus 85 GB/s. | Large resident dense kernels can benefit. Native DGEMM excludes offload transfer cost; the host is Ivy Bridge. |
| HPCG, SC14 [P6] | Stampede's combined Xeon/Phi result lists 29.9 GF/s single-node and 43,959 GF/s aggregate, versus 20.8 single-node in the earlier ISC configuration. | Sparse solver performance is far below dense peak; the slide's STREAM-normalized efficiency is not FLOP-peak efficiency. This is a center-scale result, not Haswell evidence. |
| Sparse kernels, Saule et al. [P7] | Explicitly **pre-release SE10P**, 61 cores: optimized SpMV up to about 22 GF/s; multiple RHS SpMM up to about 128 GF/s. | Reusing matrix/index data changes arithmetic intensity. Do not treat a pre-production board as a retail-card guarantee. |
| Sparse autotuning, PRACE [P8] | Production 3120P, 56 active cores/224 threads, ICC 15: profiling-based selection averages 2.2x MKL across the paper's matrix set. | This is algorithm selection versus MKL on the card, not Phi versus host. Include preprocessing cost. |
| CP2K, EPCC/PRACE [P9] | 5110P versus dual E5-2670: native CP2K was roughly four times slower than the 16-core host in the study. Some regression tests failed. | Portability is not speed or correctness. Small-matrix, serial and communication costs matter. |
| WRF Goddard microphysics [P10] | 7120P tuning improved the kernel 4.7x; the same changes improved E5-2670 code 2.8x. Kernel share fell from 20% to 7.5%. | These are each platform's before/after gains, not a 4.7x Phi-over-host comparison or whole-WRF speedup. |

WRF qualification matters: **P10 is a discussion preprint; the publisher says review stopped and a revision was not submitted.** Its conclusion's phrase about a 1.15x change in total processing time is ambiguous. The component shares and kernel result are clearer evidence. **Derived Amdahl check:** improving only a 20% component by 4.7 gives `1 / (0.8 + 0.2/4.7) = 1.19` at most under unchanged-other-work assumptions. This explains why a kernel headline cannot promise a comparable application gain; it is not a measured WRF result.

**Additional Haswell comparison, P11:** Xcelerit measured native 7120P at about 1.8x double-precision and 1.2x single-precision performance of **one** 14-core E5-2697 v3 for its Monte Carlo LIBOR case. The author's dual-socket prediction is an extrapolation. It supplies no measured Phi-versus-24-core-E5-2690-v3 result.

### Execution mode choice

- **Native card execution:** compile for KNC, load data once, run on the card. Good for resident, parallel workloads; limited by card RAM and weak serial performance. A host AVX2 executable cannot serve as the KNC executable.
- **Offload:** host retains control, I/O and latency-sensitive work; send substantial kernels with reusable data. Time transfers, launches, synchronization and output conversion as well as the kernel. Modern oneAPI/AVX-512 support must not be mistaken for this legacy target [M1–M3, P3].
- **Symmetric MPI:** host and card both compute, with separately targeted binaries/runtimes and a working SCIF-capable communication path. Use unequal partitions calibrated to the actual workload. OVERFLOW and HPCG establish feasibility, not a universal speedup [P1, P6].

The ticket-linked [local characterization](knc-characterization.md) reports one-core/1–4-thread measurements on 2026-11-06, including about 4 GB/s single-core reads and roughly 357–366 core-cycle memory latency. Its approximately 1.238-GHz core clock does not identify the board model or establish whole-card bandwidth. The example card configuration's job memory setting also does not establish physical GDDR capacity.

### Performance sources

- **P1 — S. Saini et al., NASA, _An Early Performance Evaluation of Many Integrated Core Architecture Based SGI Rackable Computing System_, SC2013 / NAS-2015-04.** [PDF](https://www.nas.nasa.gov/assets/nas/pdf/papers/NAS_Technical_Report_NAS-2015-04.pdf); `refs/nasa-maia.pdf`. Table 1 p.3; §6.3 pp.5–6 transport; §6.9.1.3 p.10 OVERFLOW. Verified production 5110P context.
- **P2 — Florian Wende, Guido Laubender, Thomas Steinke, ZIB/HLRN, _Integration of Intel Xeon Phi Servers into the HLRN-III Complex: Experiences, Performance and Lessons Learned_, CUG 2014.** [PDF](https://cug.org/proceedings/cug2014_proceedings/includes/files/pap194.pdf); `refs/zib-scif.pdf`. Verified: pp.3–4, SCIF/MPI comparisons and stack configuration. Supports measuring rank-count and transport tradeoffs rather than assuming more ranks always help.
- **P3 — Matthias Noack, ZIB, _HAM — Heterogenous Active Messages for Efficient Offloading on the Intel Xeon Phi_, report 14-23, 2014.** [PDF](https://webdoc.sub.gwdg.de/ebook/serien/ah/ZIB/14_23.pdf); `refs/ham-scif.pdf`. Verified: §3.3, printed pp.8–9, PDF pp.10–11, SCIF registration/RMA and ordering; no implementation copied.
- **P4 — Karl Rupp, _STREAM Benchmark Results on Intel Xeon and Xeon Phi_, 2015-02.** [Article](https://www.karlrupp.net/2015/02/stream-benchmark-results-on-intel-xeon-and-xeon-phi/), [author's data archive](https://www.karlrupp.net/wp-content/uploads/2015/02/stream-bench-intel-2015.zip); `refs/stream-rupp.html`, `refs/rupp-haswell-stream64M.dat`, `refs/rupp-mic-stream64M.dat`, `refs/rupp-LICENSE.txt`. Verified raw rows and article methodology; numbers converted from STREAM MB/s to decimal GB/s. The raw column label says GB/sec despite values in the MB/s scale. Only data and its license were retained from the archive.
- **P5 — Andrey Vladimirov, Colfax, _Performance-to-Power and Performance-to-Cost Ratios with Intel Xeon Phi Coprocessors_, 2015-01-27.** [PDF](https://colfaxresearch.com/download/352/); `refs/colfax-power.pdf`. Verified: pp.2–3, configurations, table 2 and benchmark setup. Historical prices do not answer today's economics; measure wall energy per completed job.
- **P6 — Jongsoo Park et al., Intel/TACC/LBNL, _HPCG Results on IA: What Does It Tell about the Architecture?_, SC14.** [Slides](https://www.hpcg-benchmark.org/downloads/sc14/sc14-hpcg-bof-ver2.pdf); `refs/hpcg-sc14.pdf`. Verified: slide 8, including explicit use of both Xeon and Phi and assumed STREAM rates. Special Stampede-era hardware is not evidence for this owner's SKU.
- **P7 — Erik Saule, Kamer Kaya, Umit V. Catalyurek, _Performance Evaluation of Sparse Matrix Multiplication Kernels on Intel Xeon Phi_, 2013.** [Paper](https://arxiv.org/pdf/1302.1078); `refs/knc-sparse.pdf`. Verified: p.2 pre-release hardware, pp.6 and 12–13 kernel results. Pre-production status is explicit.
- **P8 — A. Elafrou, G. Goumas, NTUA/PRACE, _Characterization and Optimization of Sparse Computations on Intel Xeon Phi_, undated PDF, PRACE WP238.** [PDF](https://prace-ri.eu/wp-content/uploads/WP238.pdf); `refs/prace-knc-sparse.pdf`. Verified: §4A–C pp.10–13, production 3120P experiment and preprocessing costs.
- **P9 — Fiona Reid, Iain Bethune, EPCC/PRACE, _Evaluating CP2K on Exascale Hardware: Intel Xeon Phi_, 2013-era study.** [PDF](https://prace-ri.eu/wp-content/uploads/wp152.pdf); `refs/prace-cp2k.pdf`. Verified: pp.2, 9–12 and 17, platform, affinity and performance/correctness limits.
- **P10 — J. Mielikainen, B. Huang, A. H.-L. Huang, _Intel Xeon Phi Accelerated WRF Goddard Microphysics Scheme_, GMDD 7, 8941–8973, 2014.** [PDF](https://gmd.copernicus.org/preprints/7/8941/2014/gmdd-7-8941-2014.pdf), [publication status](https://gmd.copernicus.org/preprints/gmd-2014-211/); `refs/wrf-goddard-discussion.pdf`. Verified: abstract p.8942, results/conclusion pp.8951–8953; status read online 2026-11-14. Uncompleted peer review limits evidential weight.
- **P11 — Xcelerit, _Benchmarks: Intel Haswell vs. Intel Xeon Phi_, 2014-09-24.** [Report](https://benchmarks.xcelerit.com/benchmarks-intel-haswell-vs-xeon-phi/); `refs/xcelerit-haswell.html`. Verified: test setup and result discussion; vendor-authored, one-host-socket comparison using ICC 15 and Xcelerit SDK 3.

## 4. Host compiler, threads, NUMA and huge pages

**Verified interfaces, T4; recommendation:** start host GCC builds with `-O3 -march=haswell -mtune=haswell`, adding `-fopenmp` where the program uses OpenMP. Inspect `-fopt-info-vec-optimized` and `-fopt-info-vec-missed`. These processors have AVX2/FMA, not AVX-512. These flags target the host only. Do not add `-Ofast`/`-ffast-math` implicitly; if comparison requires unfused rounding, make the FMA-contraction policy explicit, for example `-ffp-contract=off`. Use a library build compatible with Haswell and the intended precision.

**Recommendation:** first compare 12 physical cores on one socket, 24 across both, then 48 logical threads. For a well-partitioned OpenMP loop, `OMP_PLACES=cores`, `OMP_PROC_BIND=spread`, `OMP_NUM_THREADS=24` is a starting point with parallel first-touch. For independent partitions, two MPI processes with 12 threads each and local allocation can make locality clearer. Ensure library thread counts do not multiply the application thread count unintentionally. Reserve transport/control capacity when overlap actually requires it; measure that cost. `close`/compact placement can suit shared-cache work, so no affinity policy is universal [P9, T4].

**Measured evidence, T2:** on dual 12-core E5-2680 v3, switching Early Snoop off raised saturated remote reads from roughly 16.8 to 30.6 GB/s while local throughput remained around 63 GB/s. Cluster-on-Die helped some cases but slowed some OpenMP workloads by up to 23%. The useful default is local placement and a recorded BIOS mode; topology changes need workload-specific evidence.

**Measured evidence, T1:** the ECM study's dual E5-2695 v3 experiments show that uncore frequency changes affect cache bandwidth and power; its full-chip streaming-store experiment improved from 1636 to 2298 million updates/s. Non-temporal stores can reduce write-allocate traffic for large unreused outputs, but that is not a reason to use them for every store or for read-only LLM weights. The paper adjusts some STREAM rates for read-for-ownership traffic; do not compare those directly with ordinary payload-only STREAM figures. Track effective AVX clocks under sustained load rather than assuming nominal or maximum Turbo frequency.

**Measured evidence, T3:** HawkEye evaluates a dual E5-2690 v3 system. Its research huge-page policy improved `cg.D` from 1952 to 1202 seconds against 4-KB pages, but a sequential test did not improve (517 versus 535 seconds). This is evidence that TLB behavior matters, not a 1.62x guarantee from stock Linux THP. **Recommendation:** compare 4-KB versus controlled huge-page backing only for the actual memory access pattern, preserve NUMA placement, inspect real backing and TLB counters, and include allocation/compaction latency. Begin with application-scoped advice or explicit reservation when supported, rather than a global “always” change.

### Host-tuning sources

- **T1 — Johannes Hofmann, Dietmar Fey, Jan Eitzinger, Georg Hager, Gerhard Wellein, _Analysis of Intel's Haswell Microarchitecture Using the ECM Model and Microbenchmarks_, 2015.** [Paper](https://arxiv.org/pdf/1511.03639); `refs/haswell-ecm.pdf`. Verified: §§2.3–2.4 pp.4–5, setup p.8, §4.5 p.11.
- **T2 — Daniel Molka, Daniel Hackenberg, Robert Schone, Wolfgang E. Nagel, _Cache Coherence Protocol and Memory Performance of the Intel Haswell-EP Architecture_, ICPP 2015.** [Author PDF](https://tu-dresden.de/zih/forschung/ressourcen/dateien/abgeschlossene-projekte/benchit/2015_ICPP_authors_version.pdf); `refs/haswell-memory-analysis.pdf`. Verified: configuration table p.4, table VII and §8 p.9. Retained for local research, not redistributed in git.
- **T3 — Ashish Panwar, Sorav Bansal, K. Gopinath, _HawkEye: Efficient Fine-grained OS Support for Huge Pages_, ASPLOS 2019.** [Paper](https://www.cse.iitd.ac.in/~sbansal/pubs/hawkeye.pdf); `refs/hawkeye-asplos2019.pdf`. Verified: §4 setup p.7, table 9 p.12. The quoted speedup is the prototype HawkEye-PMU policy against base pages.
- **T4 — PRACE authors, edited by Volker Weinberg/LRZ, _Best Practice Guide: Intel Xeon Haswell/Broadwell_, 2017-01-31.** [PDF](https://www.prace-ri.eu/wp-content/uploads/Best-Practice-Guide_Haswell.pdf); `refs/prace-haswell-broadwell.pdf`. Verified: compiler pp.15–18, OpenMP p.22, affinity p.46, huge pages p.64. Current interface checks: GNU [x86 options](https://gcc.gnu.org/onlinedocs/gcc/x86-Options.html) and [OpenMP binding](https://gcc.gnu.org/onlinedocs/libgomp/OMP_005fPROC_005fBIND.html), `refs/gcc-x86-options.html`, `refs/gcc-openmp-binding.html`, read 2026-11-14. Settings above are proposed baselines, not a benchmark result.

## 5. LLM inference: capacity, bandwidth and partitioning

### Establish the host result first

**Verified, L1:** current llama.cpp documents CPU quantization, AVX2 support, thread controls and NUMA modes. Its inspected backend documentation does not establish a KNC backend. KNC's IMCI ISA is not Haswell AVX2 or AVX-512; a useful Phi port needs explicit kernel and runtime work. No inspected source supplies a measured modern quantized-LLM inference result on KNC. The AlmaLinux repository's AI objective does not fill that gap.

**Recommendation:** measure the same model/quantization and context with GPU layers disabled. Separate prompt processing from token generation; compare 12/24/48 host threads and NUMA distribution. Keep model placement under control: CPU affinity alone does not move existing file-cache/mmap pages. Inspect `numastat` and mappings before attributing a change to socket count. Quantization changes model accuracy as well as storage; compare quality and output validity before choosing a smaller format.

### Explicit bandwidth arithmetic

**Derived model, not measured LLM performance:** for dense batch-one decoding that reads roughly `W` bytes of weights each token, weight-read time is at least `W / B` if `B` is an applicable bandwidth ceiling. Compute, dequantization, KV traffic and synchronization add cost. MoE activation patterns, cache reuse and batching change this model.

For an **illustrative 4.0-GB weight payload** (not a claim about a particular model file):

| Bandwidth assumption | `B / 4.0 GB` | Meaning |
| --- | --- | --- |
| Two sockets, DDR4-2133 theoretical 136.5 GB/s | 34.1 tokens/s | Ideal weight-only ceiling if both sockets serve local portions effectively |
| Two sockets, DDR4-1866 theoretical 119.4 GB/s | 29.9 tokens/s | Same idealized model at reduced DIMM clock |
| Rupp's measured dual-Haswell STREAM 88.9 GB/s | 22.2 tokens/s | Illustrative ratio; STREAM traffic is not a validated LLM read-bandwidth ceiling |
| Rupp's measured KNC STREAM 142.7 GB/s | 35.7 tokens/s | Same caveat; excludes dequantization/compute and says nothing about this card's SKU |
| NASA's measured host–Phi payload rate, about 6 GB/s | 1.5 tokens/s | Illustrates the cost if all 4 GB are transferred every decoded token |

PCIe Gen2 x16 has an 8-GB/s-per-direction ceiling after 8b/10b encoding, before transaction overhead; 6 GB/s is a measured payload example, not an entitlement on this machine. Host DDR and card GDDR bandwidths cannot simply be added for serially dependent stages [H4, P1, P4].

### Which split could make sense?

**Recommendation/derived:** keep a persistent subset of layers and their weights on the card, transferring activations across a small number of boundaries. For a single sequence, host stage time plus card stage time plus transfer time remains on the critical path. Divide by measured stage time, not parameter count alone. A pipeline can increase throughput with multiple independent sequences, provided stages balance and pipeline bubbles are amortized; it need not improve interactive latency.

Splitting independent requests/batches between host and Phi avoids per-layer synchronization, but requires a working card inference implementation and sufficient memory for each model copy. Tensor-parallel splits introduce reductions at many layers and are a poor first experiment over this link. Streaming weights from host each token is especially unattractive for interactive decode; batching can amortize weight movement across useful work, with latency and KV-memory costs.

**Verified external example, L2:** FlexGen demonstrates that scheduling, compression and large batches can make offloaded inference useful on a 16-GB NVIDIA T4 with substantial host RAM/SSD. This supports the batching/reuse principle only. It is not KNC evidence, an RX 6700 XT recommendation, or a prediction of this system's tokens/s.

Capacity is a hard prerequisite: account for weights, quantization metadata, KV cache, temporary buffers, card OS and any RAM-backed filesystem. The 5110P/3120P/7120P studies illustrate different card capacities; determine this board's actual free GDDR before selecting a partition. Quantized storage does not automatically imply efficient KNC quantized arithmetic. Establish correctness against a host reference, then measure the actual matrix-vector/matrix-matrix kernels and complete inference path [P1, P5, P8, M6].

### LLM sources

- **L1 — ggml-org contributors, _llama.cpp_ README, build documentation, `llama-bench` and completion documentation, master read 2026-11-14.** [Project](https://github.com/ggml-org/llama.cpp), [build](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md), [benchmark](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md), [completion](https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md). Local: `refs/llamacpp-readme.md`, `refs/llamacpp-build.md`, `refs/llamacpp-bench.md`, `refs/llamacpp-completion.md`. Verified interface sections: CPU/quantization, `--threads`, `--numa`, `--n-prompt`, `--n-gen`, GPU layer control. Defaults and flags are version-sensitive.
- **L2 — Ying Sheng et al., _FlexGen: High-Throughput Generative Inference of Large Language Models with a Single GPU_, ICML/PMLR 202, 2023.** [Paper](https://proceedings.mlr.press/v202/sheng23a/sheng23a.pdf); `refs/flexgen.pdf`. Verified: §§4–6 scheduling, compression and evaluation, particularly hardware assumptions. Used for the offload/batching mechanism, not cross-device speed extrapolation.
- **L3 — This note's arithmetic**, using H6/H7 channel rates and P1/P4 bandwidth measurements. Decimal GB throughout; explicitly hypothetical weight payload. No empirical LLM result is claimed.

## 6. Open questions and cheap measurements for the owner/lead

These are proposed next checks. Engineers do not start card jobs; any card execution must be scheduled by the lead through `tools/card_run`. Checks exceeding about one minute must use all CPUs assigned to that native program, following the project affinity rule.

| Question | Cheap check and decision it resolves |
| --- | --- |
| Which Phi, cooler, PSU and GPU board are installed? | Read labels/part numbers and obtain `micinfo` inventory; photograph/inspect the harness and airflow path. Record actual card RAM, active/passive cooler, PSU input/output rating and GPU dimensions before approving a load test. |
| Are both sockets' channels populated and running at the intended speed? | Read BIOS DIMM inventory and `dmidecode` configured speed; map ranks/capacity to HP's population diagram. Distinguish 1-DPC from 2-DPC and verify 2133/1866 rather than inferring from DIMM labels. |
| Is the Phi on the intended PCIe root with a full link and BARs? | Inspect `lspci -tv`, `lspci -vv -s <BDF>`, `/sys/bus/pci/devices/<BDF>/numa_node`, `numactl -H` and driver diagnostics. Record Gen2 x16 under load and above-4-GB BAR allocation. A reduced link requires placement/contact/firmware investigation before performance tuning. |
| Which OS/kernel/MPSS combination actually works? | Record host kernel, module build, card image and runtime versions. Qualify boot, SSH, two-way SCIF transfer and one correct native/offload result, then repeat boot once. Package installation alone is insufficient. Keep the earlier working kernel recoverable. |
| Is bandwidth local and balanced? | Run short host STREAM-sized workloads larger than LLC: one socket locally, the other locally, then both with parallel first-touch; compare physical threads versus SMT. A 5–10-second sample per case should reveal large placement errors. Record configured clock and page policy. |
| Is the transport performing as expected? | Lead-run small/medium/large SCIF messages, e.g. 1 KB, 1 MB and 64 MB, with reused registered buffers; compare local/remote host allocation and both directions. Report latency, sustained payload rate and setup cost separately. |
| Is the cooling path adequate with both cards present? | After harness/duct inspection, use a short staged lead-controlled load and monitor Phi/host clocks, power, temperatures and throttling, first with GPU idle and then representative concurrent GPU activity. Record ambient/inlet conditions and side-panel state. Stop on cooling or power faults; do not use a performance run to discover missing cooling hardware. |
| Does this LLM benefit from the second socket or SMT? | Fix model, quantization and context; use CPU-only `llama-bench` with prompt/generation phases (for example `-p 512 -n 128 -ngl 0`) and 12/24/48 threads. Inspect NUMA placement and report prompt rate, decode rate and latency separately. Establish this baseline before a Phi port. |
| Would huge pages, Home Snoop or a different affinity policy help? | Change one exposed setting at a time with the same working set; check page backing, local/remote traffic, TLB misses and effective clocks. Retain only a repeatable improvement consistent with correctness and latency requirements. |
| What work should move to Phi? | Once kernels exist, compare a resident dense kernel, a representative sparse operation and the actual WRF/LLM component against the host. Include transfer/setup costs and validate numerical results. Fit a weighted partition from measured times; reject splits whose communication consumes the saved compute time. |

The immediate decisions are therefore hardware identification and an honest host baseline. A measured Phi advantage remains workload-, placement-, runtime- and capacity-dependent.
