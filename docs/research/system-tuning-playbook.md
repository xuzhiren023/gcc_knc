# Whole-system tuning: dual E5-2690 v3 Z840 and one Knights Corner card

S12-16, 2026-11-14. This starts after slot choice, memory population, power,
cooling and a working MPSS installation have been established. It extends
[the workstation study](host-phi-workstation.md) and
[the reference-gap study](knc-reference-gaps.md). No host settings were changed,
and no benchmark, compiler build or card job was run for this research.

## 1. Playbook, in application order

**Evidence labels:** **V** = the primary source was inspected; this verifies what
it documents, not operation on our machine. **R** = a measurement or deployment
reported by its authors, not reproduced here. **I** = our inference or proposed
policy. All recommended settings below are **I** unless explicitly identified
as a documented interface/default (**V**) or a centre's setting (**R**).
PDF pages are viewer pages unless specified otherwise. Links such as [B1]
resolve to the sources described in section 3.

Use two job policies: **throughput** for sustained scientific jobs and batched
inference; **latency** for interactive inference and short, frequent offloads.
They share the same correctness and memory-protection requirements. Start with
throughput, then change only settings relevant to measured latency. There is no
published Z840/KNC configuration that establishes a universal optimum.

### Step 1. Capture the working configuration and a comparable baseline

- **Set and why:** keep the working firmware/OS/MPSS combination fixed. Record
  HP BIOS revision; Phi SKU, stepping, flash/SMC versions, ECC and Turbo state;
  host and card kernel versions; runtime/library versions; and current policy
  values. Keep ordinary configuration backups outside the disposable worktree.
  Identify the Phi PCI address and its actual NUMA node. The target host has
  24 physical cores and, with HT enabled, 48 logical CPUs; this is not the
  engineering session's 12-thread machine. Sources: [B1] pp.8-10, [C2]
  §§3.4.5, 4.1 (pp.42, 63-68), [B5] specification fields.
- **Verify/effect:** inspect `lscpu -e`, `numactl --hardware`, the device's
  `/sys/bus/pci/devices/<BDF>/numa_node`, `lspci -s <BDF> -vv`, `micinfo`,
  `micctrl -s`, and host/card `/proc/cmdline`. A `numa_node` value of `-1` is
  unknown, not node zero. Map through the PCI root and topology before binding.
  This step establishes comparability; it has no claimed speedup.
- **Risk/rollback:** upgrading a functioning stack during tuning confounds the
  experiment. Keep the known boot entry and matched MPSS packages. Do not flash
  firmware as a performance experiment. Restore saved settings and boot the
  original kernel if a later configuration prevents normal operation.

### Step 2. Establish host frequency and memory-policy baselines

- **Set and why:** enable Turbo, retain NUMA with node interleaving disabled,
  use the supported memory clock, and start with a performance CPU governor
  during measurements. Let the installed cpufreq driver implement it; inspect
  `scaling_driver` before selecting controls. Retain HT in firmware initially,
  but use one worker per physical core. Do not invent a Dell-style profile name
  in HP F10: HP documents Runtime Power Management and Idle Power Savings.
  Sources: [B2] PDF pp.39-41, [B3] pp.1-3, 7-13, [C1] printed pp.14-16.
- **Verify/effect:** check each policy's governor, effective busy frequency with
  compatible `turbostat`/PCM, temperatures and throttling under the same work.
  A governor setting is not proof of sustained Turbo or AVX frequency. Dell's
  Haswell prototype study found DAPC and Performance usually within a few
  percent, with more power used by Performance; WRF favoured DAPC [B3] p.7.
  No Z840 uplift is established. For a latency policy, separately test Normal
  rather than Extended idle saving, and C1E/deep-state restrictions if exposed.
- **Risk/rollback:** higher idle power can reduce shared thermal headroom; HT
  can help some codes and hurt others. Restore the prior governor/F10 settings.
  Test 12 versus 24 physical workers, then 48 logical workers, before deciding
  whether firmware HT should be disabled for a dedicated scientific host.

### Step 3. Fix CPU, memory and interrupt locality before changing snoop mode

- **Set and why:** bind the host offload/control process and reusable DMA
  buffers to the Phi's NUMA node. An owner-run Linux launch can use
  `numactl --cpunodebind=<N> --membind=<N> <program>`; `<N>` must be discovered.
  Initialize buffers in the bound process before registration. For a host-only
  two-socket job, first-touch each partition on its owning workers; binding
  every byte to the Phi socket would waste the other socket's bandwidth.
  Sources: [C1] printed pp.15-16, [T1] pp.3-4, [O1] PDF pp.7-10, 27-28.
- **Verify/effect:** inspect `/proc/<pid>/numa_maps`, `numastat -p <pid>`, worker
  affinity and the Phi interrupt counters in `/proc/interrupts`. Initially keep
  NUMA-aware `irqbalance`. If it places Phi interrupts on busy or remote cores,
  reserve a local physical core for service work and configure exclusions or
  targeted IRQ affinity; check `/proc/irq/<IRQ>/smp_affinity_list` and actual
  counter movement. Expect fewer remote accesses and less jitter, not a fixed
  bandwidth percentage. ZIB deliberately put Phi and HCA on the same root [T1].
- **Risk/rollback:** an overly narrow service mask can bottleneck completions;
  irqbalance can overwrite manual masks. Save its service state and masks,
  use one authority for affinity, and restore both. Never stop it globally
  without assigning the remaining device interrupts. Reset NUMA binding by
  launching a fresh process with the original policy.

### Step 4. Choose Home Snoop or Early Snoop using the actual workload

- **Set and why:** after placement is correct, compare Home Snoop against the
  existing Early Snoop setting. Prefer Home Snoop as the candidate for high
  memory traffic, especially remote traffic. Keep Early Snoop as a latency
  comparison. **Do not prescribe Cluster-on-Die on the Z840:** HP's M60 document
  establishes only Early and Home Snoop [B1] p.28. If the installed firmware
  actually exposes CoD, test it separately with NUMA-aware partitions and a
  newly discovered topology [B3] pp.2, 4-7; [B4] pp.4, 9.
- **Verify/effect:** verify the BIOS selection after reboot, then run the same
  host STREAM and application case. CoD should expose two domains per socket,
  four total; ES versus HS need not change the domain count. **R:** on dual
  E5-2680 v3, disabling ES raised saturated remote read bandwidth from 16.8 to
  30.6 GB/s, while saturated local reads stayed near 63 GB/s [B4] table VII,
  p.9. This is a microbenchmark, not an 82% application-speedup prediction.
- **Risk/rollback:** CoD reduces each domain's cache/memory scope and can worsen
  cross-domain sharing; [B4] reports an approximately 23% runtime increase in
  one SPEC OpenMP case. Restore the previous snoop setting and placement map.
  Do not compare runs that silently changed both mapping and snoop mode.

### Step 5. Leave reliability controls intact; tune PCIe only from evidence

- **Set and why:** retain ECC, supported refresh timing and normal patrol
  scrubbing. Keep PCIe speed on Auto and confirm Gen2 x16 under transfer load.
  Record negotiated MaxPayload on the endpoint and upstream path. KNC DMA can
  use up to 256-byte transactions if the root supports them [C6] PDF p.28;
  this is not permission to force 256/512 bytes with `setpci`. Treat ASPM
  disabling as a reversible latency experiment only if idle-to-transfer delays
  remain after steps 2-3. Sources: [B1] pp.8-10; [B3] p.1; [C5] §§2.1.4, 5;
  [C6] §2.1.6.
- **Verify/effect:** inspect `LnkSta`, `DevCtl` and link-power control at both
  ends, kernel PCIe errors, transfer bandwidth and wake-up latency. A wider
  slot cannot make KNC a Gen3 endpoint. No inspected centre source establishes
  an optimal Z840 ASPM, refresh, patrol-scrub or payload setting, nor an
  isolated gain for changing them.
- **Risk/rollback:** unsupported payload/timing changes can cause errors;
  disabling protection changes the reliability envelope. Leave these controls
  out of the initial experiment. If an owner later changes an exposed ASPM
  policy, restore the exact saved firmware/kernel policy and reboot as needed.
  A firmware restore is preferable to ad hoc PCI configuration writes.

### Step 6. Use targeted Linux memory policy; postpone CPU isolation

- **Set and why:** on a dedicated, explicitly pinned benchmark host, compare
  `kernel.numa_balancing=0` with the original value. Keep the original value
  for an unpinned mixed-use baseline. For large anonymous buffers, start with
  THP `madvise` plus application advice when supported; retain an existing
  successful `always` policy as a measured comparator. Pre-fault before timing.
  If deterministic latency/page backing is needed, reserve only the required
  explicit huge pages on the intended node. Keep swap as a recovery facility,
  but require zero swapping in the timed working set; `vm.swappiness=10` is an
  RHEL7 latency-profile candidate, not a no-swap guarantee [O1] PDF pp.8, 14,
  26-28. Start without `isolcpus`, `nohz_full`, clocksource changes or extra
  timer options [O2].
- **Verify/effect:** inspect THP sysfs, `/proc/<pid>/smaps` (`AnonHugePages`,
  page sizes), `meminfo`, fault counts, `vmstat` swap-in/out and per-node
  huge-page pools. On a legacy host, mmap-backed model files do not become
  anonymous THP merely because THP is enabled. Explicit allocation must
  actually consume its pool. Benefits depend on TLB pressure and fault timing;
  no measured Z840/LLM percentage is available.
- **Risk/rollback:** THP compaction can create latency spikes; static huge-page
  reservations reduce ordinary memory; a single initializing thread can place
  all pages remotely. Restore sysctl/sysfs values, terminate the test process,
  and release only the pages reserved for it. Changing THP policy does not
  necessarily split existing huge mappings; compare fresh processes. If using
  `tuned`, save `tuned-adm active`, inspect the installed profile and restore
  that profile after the test. Do not combine a profile change with silent
  hand edits it will overwrite.

### Step 7. Set a card power/timer policy appropriate to the job

- **Set and why:** retain ECC. Keep frequency management and supported Turbo
  available for sustained throughput; the x100 datasheet explicitly identifies
  7120P/7120X Turbo support [C5] pp.13, 57-59. Inspect the actual SKU instead of
  assuming every 7100 card is identical. For batch jobs, allow PC3/PC6 and
  warm the card before timing. For a persistent interactive service, compare
  PC3/PC6 off during the service allocation, with other values held fixed.
  `PowerManagement` in `/etc/mpss/micN.conf` controls `cpufreq`, `corec6`,
  `pc3`, `pc6`; edit the desired flags, then use the release-matched clean
  shutdown/boot procedure and verify the effective state. The 3.8 `--pm`
  suboption selects stepping defaults, not arbitrary flag combinations.
  Keep card TSC as the starting clocksource [C2] pp.123, 135-136, 154-155.
- **Verify/effect:** inspect the effective card command line, available/current
  clocksource and `micsmc` status. Time both first request after idle and warm
  requests. **R:** CSC describes roughly 0.5 s wake-up from deep sleep [C3]
  p.4. That matters for interactive latency but is usually amortized by a long
  job. Do not poll `micsmc` to measure deep-idle power: CSC found the query
  itself wakes the card; use an external meter for that comparison.
- **Risk/rollback:** disabling sleep increases idle energy/heat. Reloading the
  card loses jobs and volatile files. Restore the recorded configuration and
  runtime state during a coordinated idle window. Preserve the shipped
  `ExtraCommandLine` baseline, including `highres=off` if present; do not copy
  host `nohz_full` or Intel-idle options into a 2.6.38 card kernel.

### Step 8. Reserve card service capacity and establish real page backing

- **Set and why:** initially exclude the physical BSP/OS core and its four
  hardware contexts from workers. Discover core/sibling mapping; Linux CPU 0
  and CPU IDs 1-3 are not necessarily one physical core on KNC. Retain MPSS,
  SCIF, health and required MPI/offload services. Reduce optional monitoring
  frequency and unnecessary filesystem activity, rather than indiscriminately
  killing daemons. For native large arrays, test card THP and, only if needed,
  explicit 2-MiB pages; align/prefault and reuse allocations [C1] printed
  pp.4-9; [C4] pp.2-5; [R1] pp.56-62.
- **Verify/effect:** read each worker's allowed CPUs, card `smaps`, fault counts,
  free memory and filesystem usage. **R:** Stampede's 2013 SE10P STREAM report
  says THP matched its previous explicit-huge-page performance, reaching
  174.663 GB/s Triad with 60 threads [H1]. This combines a tuned compiler,
  store/prefetch policy and page backing; it does not isolate a THP speedup.
- **Risk/rollback:** code/data staged into the RAM filesystem consumes the same
  card capacity as the application; large stacks and many malloc arenas add
  pressure. Keep a measured margin for OS, transport and temporary buffers.
  Restore page settings and service policy, release test allocations, and
  remove only the job's staged files. Use MPSS overlays for deliberate persistent
  card changes; editing only the live card filesystem may be lost on reboot.

### Step 9. Make transfers persistent, aligned and observable

- **Set and why:** allocate page-aligned host/card transfer buffers, keep data
  offsets and lengths cache-line aligned, register once, reuse, and wait for
  the documented completion/fence before reuse. Compare small-message CPU
  transfer with DMA; batch small requests. Separate registration, enqueue,
  completed transfer and simultaneous two-way transfer timings. Keep SCIF
  defaults unless a specific failure requires a change. Source interfaces:
  [C1] printed pp.10-16, [C2] §§9.3.3-9.3.6, [T3] printed pp.8-9.
- **Verify/effect:** check registration errors, pinned-memory limits, NUMA
  placement, bytes transferred, completion and data validation. **R:** ZIB's
  host/Phi MPI measurements rose from 5.7 GB/s at two ranks to 6.9 GB/s at
  sixteen, while latency rose from 9.2 to 62 microseconds [T1] table I, p.3.
  This demonstrates a bandwidth/latency tradeoff, not a reason to use sixteen
  transfer ranks. SSH transfer is a control/staging path, not a SCIF bandwidth
  test. Inference weights should remain resident if card capacity permits.
- **Risk/rollback:** excess pinned memory harms host/card capacity; unbounded
  caching and mistaken asynchronous completion can corrupt results. Close
  endpoints and unregister buffers on normal and error exits. Restore any
  changed SCIF cache limit. `reg_cache` for virtual-address transfer calls,
  explicit `scif_register`, and native heap allocation are separate mechanisms.

### Step 10. Verify MPI transport, then partition symmetric work

- **Set and why:** for host/card MPI, use a KNC-era compatible library on both
  architectures and verify the SCIF DAPL provider. In the documented Intel MPI
  stacks the starting interface is `I_MPI_MIC=enable`,
  `I_MPI_FABRICS=shm:dapl`, with a provider list chosen from the installed
  providers. LRZ documents `ofa-v2-scif0` alongside its Mellanox provider
  [R1] p.115. A single-card workstation needs no external HCA for raw SCIF;
  CCL-proxy is an HCA/network mechanism, not an extra local-DMA accelerator.
  Start with one host rank per socket and one card rank, OpenMP within each;
  reduce host workers to leave service capacity when the measured workload
  needs it. Source: [T1] pp.3-4; [T2] pp.4-6; [C2] pp.55-60.
- **Verify/effect:** use release-matched MPI debug output, hostname/rank/CPU
  reports and ping-pong to verify the provider and pinning. Map disjoint
  physical-core domains (`I_MPI_PIN_DOMAIN`/processor lists in Intel MPI), then
  bind OpenMP workers inside each domain. Pass host and MIC environment values
  separately. **R:** NASA's updated MPI/SCIF path delivered about 6 GB/s for
  4-MB host/Phi messages versus approximately 1.6 GB/s and 0.455 GB/s on its
  two cards before the update [T2] pp.5-6. This was a combined stack/path
  change, not an isolated fabric-variable experiment.
- **Risk/rollback:** a launch can silently fall back to TCP, oversubscribe a
  socket or allocate too much per-rank memory. First compare host-only and
  card-only rates, then size unequal work partitions so phases finish together.
  Restore the original launcher/environment/provider list to roll back. Do
  not install unrelated OFED packages or copy cluster-specific provider names
  onto a host where they do not exist.

### Step 11. Tune the runtime that actually executes the application

- **Set and why:** for GNU OpenMP on the host, start with
  `OMP_PLACES=cores`, `OMP_PROC_BIND=spread`, `OMP_DYNAMIC=false`, and a
  physical-core thread count; compare `close` for shared-cache workloads.
  For Intel OpenMP on KNC, start with `KMP_AFFINITY=granularity=fine,balanced`
  restricted to the allocated cores. Compare 1, 2, 3 and 4 workers per usable
  core, keeping the core set fixed. With GNU KNC libgomp, use supported
  `OMP_PLACES`/`OMP_PROC_BIND` or explicit `GOMP_CPU_AFFINITY`; KMP variables
  do not configure libgomp [R1] pp.27-28, 56-62; [R4].
- **Verify/effect:** inspect the loaded runtime, requested/actual team size and
  every thread's CPU mask. Do not infer placement from aggregate CPU usage.
  **R:** Tianhe-2's atmospheric solver used 224 threads on 56 KNC cores;
  explicitly compact host affinity reduced mean step times from 0.2718 to
  0.1538 s and from 0.2623 to 0.1567 s in two layouts [H2] pp.6-7.
  These are that solver's results, not universal affinity gains. Use fewer
  MPI ranks plus threads if rank replication exceeds card memory.
- **Risk/rollback:** nested BLAS/OpenMP teams and simultaneous runtimes can
  oversubscribe. Set library thread counts deliberately; when outer workers
  each call a BLAS, start with one BLAS thread. Leave allocator defaults until
  RSS or contention identifies a problem; then compare a bounded
  `MALLOC_ARENA_MAX` (for example 4 versus the default) per process, checking
  contention and peak memory [R5]. Restore/unset the per-job variables to undo
  the experiment. Avoid globally preloading an allocator.

### Step 12. Enable offload only where it improves the complete workload

- **Set and why:** preserve separate host-only, native-card and transfer-inclusive
  results. For legacy MKL, keep automatic offload off for the host baseline;
  enable `MKL_MIC_ENABLE=1` only in its comparison. **V:** the published
  MKL **11.0.2** thresholds include GEMM with M,N > 2048 and K > 256;
  TRSM/TRMM M,N > 3072; SYMM M,N > 2048; LU M,N > 8192 [R1] p.38.
  They are historical library decisions, not universal break-even sizes.
  Keep long-lived weights/arrays on the card, and retain host serial/I/O work.
- **Verify/effect:** use the installed MKL/offload diagnostics to prove where
  work ran and measure both startup and steady state. **R:** a 7120P study
  reported 984 GF/s resident DGEMM versus 485 GF/s on dual Ivy Bridge hosts,
  but its STREAM figures were 176 versus 85 GB/s [R2] pp.2-3. Neither is a
  transfer-inclusive Z840 or quantized-LLM result. LLM comparison must separate
  prompt processing, token generation, first-token latency and memory use [L1].
- **Risk/rollback:** repeated transfers, small kernels, conversion and launch
  costs can eliminate the kernel gain. MKL 11.3's `MIC_USE_2MB_BUFFERS` applies
  to pointer-based offload buffers, not native GCC malloc; cap
  `MKL_MIC_MAX_MEMORY` only within an explicit capacity budget [R3]. Restore
  the original offload/environment settings and host execution path. Keep
  precision, convergence and output validation unchanged.

### Step 13. Accept a policy with workload results, not peak counters

- **Set and why:** collect a low-frequency host/card telemetry trace during the
  benchmark ladder: STREAM, completed SCIF transfers, MPI ping-pong if used,
  DGEMM, short HPL/HPCG diagnostics, then the actual WRF/LLM/sparse case.
  Validate results before comparing speed. Sources: [H1], [T1] table I,
  [R2], [M1] slide 8, [M2] pp.1-2, [C2] Appendix F.2 pp.193-195.
- **Verify/effect:** watch effective frequencies, sustained temperatures,
  thermal/power throttling, ECC/PCIe errors, page faults, swap, CPU migrations,
  memory bandwidth and MPI imbalance. Use host perf/PCM versions that support
  Haswell; do not assume a host perf event exists on the card. A short HPL
  stress pass establishes neither sparse efficiency nor LLM latency. No
  absolute acceptance score for this owner is established by the sources.
- **Risk/rollback:** intrusive sampling perturbs short jobs; power queries can
  prevent card sleep. Restore monitoring frequency and retain the previous
  accepted job policy if throughput, tail latency, correctness or energy per
  completed work unit regresses. Section 6 bounds the experiments and times.

## 2. Evidence by layer

### 2.1 Host firmware: what is established and what is not

| Item | Evidence and applicability | Decision for this Z840 |
| --- | --- | --- |
| Power profile, P-states, Turbo | **V:** HP exposes runtime/idle controls [B2]. **R:** Dell's September 2014 R730xd **prototype**, RHEL 6.5 kernel 2.6.32-431, Intel 14.0.3/MKL 11.1.3, compares its DAPC and Performance policies [B3] pp.1, 3, 7-13. **V:** Haswell has workload-dependent frequency behaviour [B6] §§2.3-2.4. | **I:** performance governor is a repeatable starting control; measure effective clocks. Do not promise nominal/all-core Turbo under sustained AVX2. Do not describe DAPC as an HP option or a centre-wide policy. |
| C-states/C1E | **V:** MPSS 3.1 performance guidance discusses host C1E/governor interaction with transfers specifically on **Romley**, RHEL6/SLES11 [C1] pp.14-16. **R:** a 2013 TACC author describes a driver latency limit permitting C1, plus `intel_idle.max_cstate=0` to select ACPI idle [H3]. | **I:** diagnose idle-to-transfer delay first. Haswell uncore management differs from Romley, so busy waiting or disabling all idle states is not an automatic port of that recipe. Modern `intel_idle.max_cstate=0` disables that driver; it does not itself mean "disable all C-states" [O3]. |
| HT | **R:** Dell recommends HT off for generic HPC but observes workload-dependent benefits; its HPL comparison uses physical-core worker counts even with HT enabled [B3] pp.9-13. **R:** ZIB's deployed E5-2690 nodes had HT enabled [T1] p.3. | **I:** keep capability available while comparing 24/48 workers. For host inference also compare 12 workers and one-socket memory. Do not apply the host HT recommendation to KNC's four-way threading. |
| ES/HS/CoD, NUMA | **V:** HP M60 permits ES/HS [B1] p.28. **R:** Bull dual E5-2680 v3, Ubuntu 14.04.2/kernel 3.19.1, BIOS 1.0, gives remote-read 16.8/30.6 GB/s ES/HS and workload-specific CoD regressions [B4] pp.4, 9. It is a commercial-model study, not identified as pre-production. | **I:** HS is the first alternative to test after correct placement. CoD remains unavailable unless the owner's actual firmware proves otherwise. NUMA interleaving is not a substitute for first touch. |
| Patrol scrub/refresh | **V:** Dell's dense-memory profile changes scrub, refresh and Turbo together [B3] p.1. It does not measure each change in isolation. No inspected HP/centre source supplies a Z840-specific numeric tuning target. | **I:** normal vendor defaults; retain scrub/ECC. A lower-refresh or no-scrub benchmark score would not establish an acceptable scientific-computing setting. |
| ASPM, payload, link | **V:** KNC PCIe is Gen2; original 2012 system-software guide specifies 64-byte DMA alignment/granularity and up to 256-byte transactions with a capable root [C5, C6]. That guide is early architectural documentation, not a production Z840 measurement. | **I:** Auto speed, verify 5 GT/s x16 under traffic. Keep negotiated payload. An ASPM-off experiment requires a measured symptom; no centre BIOS dump found supports making it universal. |

The Dell document has a model-label inconsistency: table 2 says **E5-2693 v3**
for its 14-core case, while plots/discussion say **E5-2697 v3**. Visual inspection
confirmed the mismatch. Use its qualitative controlled comparisons, retain the
prototype qualification, and do not present it as exact E5-2690 v3 validation.

### 2.2 Host Linux policy and the limits of centre evidence

**V:** Red Hat's low-latency brief, revision 2.1 for **RHEL 7.4** (2017), shows
`latency-performance` using a performance governor and low-latency controls;
`network-latency` additionally disables THP and automatic NUMA balancing
([O1], PDF p.14, printed p.10). These profiles include multiple changes. Their
names do not imply they maximize native card STREAM, resident LLM decoding,
or dense linear algebra. **I:** use the installed `throughput-performance`
profile as an optional throughput starting point only after inspecting its
actual settings; construct a narrow measured override rather than assuming
profile contents are identical across RHEL6/7/8 or community MPSS ports.

**V:** the same Red Hat brief says irqbalance gained PCI affinity handling in
RHEL6.4 and remains useful in RHEL7 ([O1], PDF pp.27-28). **I:** retain it for
the initial throughput policy; move only offending Phi interrupts when traces
show interference. `/proc/irq/*/smp_affinity` is a CPU bitmask;
`smp_affinity_list`, where available, is a CPU list [O4]. Do not confuse
physical core IDs with logical CPU bits or assume every IRQ permits steering.

**V:** Linux 3.10 documents `nohz_full` for CPUs with one runnable task and
requires housekeeping capacity [O2]. **I:** for the 24-core Haswell host, use
ordinary affinity/cpusets first. Only a remaining tail-latency problem justifies
a bounded experiment with CPU isolation, IRQ placement and housekeeping
together. A kernel rebuild, `idle=poll`, blanket mitigation disabling or
system-wide timer changes is outside the initial playbook. `isolcpus` alone
does not move interrupts, kernel workers, application helper threads and RCU
work into a coherent service allocation. The legacy card kernel does not gain
modern host isolation features by receiving their boot arguments.

**I:** preserve usable swap on a mixed-use host, but treat sustained swapping or
major faults after warm-up as a failed capacity/placement configuration. Do not
use `swapoff` on a full machine as a tuning shortcut. Pre-faulting and an
application memory budget address this directly. THP policy, explicit HugeTLB
allocation, allocation locality and swapping are four different controls.

The following is the recovered deployment evidence, rather than a fabricated
list of identical settings at every centre. **Unspecified means not established
by these sources**, not that the centre used the OS default. None of the six
named sites yielded a complete public BIOS, boot-argument, IRQ, tuned, THP and
allocator configuration for all its KNC nodes in this review.

| Centre/system | Hardware/status and dated software scope | What the source actually establishes | What remains unspecified |
| --- | --- | --- | --- |
| TACC Stampede | Operational SE10P system, special KNC SKU, Sandy Bridge hosts. September 2013 STREAM uses ICC 13.1.1; exact MPSS build is absent in that report [H1]. | **R:** card THP replaced explicit hugetlbfs without losing the previous performance; 60-thread Triad 174.663 GB/s. **R, weaker:** TACC author's indexed 2013 discussion describes host C1 latency limiting [H3]. | Full BIOS/IRQ/governor/tuned state; complete card boot line. The 2013 configuration must not be filled in from today's Stampede3 or KNL Stampede2 documentation. |
| Tianhe-2 / NSCC Guangzhou | Deployed dual E5-2692 + three 31S1P nodes, 57 cores/card; Kylin, Intel 14.0, customized MPICH 3.1 and MPSS 3.1.2 in an accepted 2014 paper [H2] pp.3-4. Production installation, special OEM card. | **R:** 224 workers/56 cores per card, explicit compact **host** affinity, asynchronous transfers and communication tuning; table I gives large timing/jitter reductions. | BIOS, host kernel build, IRQ policy, card clocksource and idle-state configuration. TH Express-2 transport knobs are not Intel MPI/SCIF controls for our workstation. |
| NERSC Babbage | Operational **testbed**, 45 nodes, Sandy Bridge hosts plus two 60-core/8-GB KNC cards; 2013 annual report [H4]. NWChem study uses Intel Fortran 14.0.1 [H5] §3, PDF p.2. | **R:** mounted production filesystems, modules and prearranged runtime libraries; native-mode study uses balanced affinity. Native runs intentionally exclude host computation and PCIe from timing. | Full OS/MPSS revisions in these two sources, BIOS and kernel tuning. Cori's later KNL configuration is not evidence for Babbage. |
| LRZ SuperMIC | Operational research cluster with 32 nodes, two 5110P/node; PRACE v2.0 (2017) §17.4 pp.110-115; Linux on both sides, Mellanox OFED 2.2. Separate introductory diagnostic shows MPSS 3.4/card 2.6.38.8; separate library example shows Intel MPI 5.1.3.181 [R1] pp.10, 13. | **R/V:** directly reachable cards through a virtual bridge; host and MIC binaries; per-site defaults `I_MPI_MIC=enable`, `shm:dapl`; Mellanox and SCIF provider selection. | Do not combine the introductory sample and later job examples into a single synchronized fleet software inventory. Exact host kernel/BIOS/IRQ/page policy is absent. |
| Jülich DEEP | **Prototype system**, 128 Xeon cluster nodes plus a 384-card 7120X booster and EXTOLL FPGA network [H6]. This is a different system topology from one host plus one PCIe card. | **V/R:** OmpSs and ParaStation Global MPI integrate the modules. Centres also explored system-level work distribution instead of treating every card as identical to a host rank. | An applicable Z840/KNC MPSS, BIOS, card-OS or IRQ recipe. Modern JURECA Booster/DEEP-ER KNL and current DEEP GPU descriptions are excluded. |
| ZIB / HLRN-III Phi subcluster | Operational four-node integration, production 7120 cards; dual E5-2690, HT on; CentOS6.3, 2.6.32-279, MPSS 2.1.6720-19, Intel MPI 4.1.1/4.1.3, True Scale driver 7.2.0.0.42 [T1] pp.3-4. | **R:** Phi/HCA share PCI root; central libraries and filesystems, batch integration, SCIF for simultaneous host+card operation. Its then-current TMI path cannot use host and attached card together; MPSS3.3 support was prospective. | Complete BIOS and scheduler/IRQ/page tunables. Their absence is not a claim of default policy. |
| CSC / PRACE | Practical operational guidance spanning MPSS 2.x/3.x, including 3.2/3.3 features; precise test SKU/build not supplied [C3]. | **R:** deep-sleep energy policy for long HPC active periods; persistent MPSS configuration and filesystem management; external idle-power measurement. | A universally safe frequency/idle combination for every stepping or latency-sensitive service. |
| NASA Maia | Production 5110P cards, dual Sandy Bridge hosts; MPSS Gold then Gold Update 3, Intel MPI 4.1.0.030 then 4.1.1.036 [T2] pp.3-6. | **R:** transport/runtime changes can dominate host/card bandwidth; application results distinguish native, host and hybrid modes. | A Z840 BIOS recipe or proof that every newer MPSS release automatically improves every transport. |

### 2.3 Card and MPSS

**V:** MPSS 3.8 documents an initial power configuration of frequency management
on, core C6 off, PC3 on and PC6 on; stepping-sensitive `micctrl --pm` defaults
also exist ([C2] Appendix A.3.3 p.136, Appendix B.3.2.11 p.154). This is the documented
configuration of that release, not an observation of our MPSS3.7 card.
**I:** preserve the deployed stepping-compatible `corec6` choice while comparing
PC3/PC6. Do not force all power states on because an older example does so.
Host Turbo/C-states and card Turbo/PC states need separate records.

**V:** the 3.8 guide's `ExtraCommandLine` initial value includes `highres=off`
(p.135); its TSC description says the power-management software maintains
calibration (p.123). The 3.1 performance guide says calibration was added in
MPSS Gold Update 3, whereas earlier systems had stronger timing caveats [C1]
printed pp.2-3. **I:** prefer the installed OS monotonic clock for elapsed time,
batch tiny operations, pin timing threads, and check across sleep/throttle
transitions. Raw cycle counts across cores/frequencies are not elapsed seconds.
Keep `micetc` for a diagnosed calibration problem, not as an automatic upgrade.

**V:** card THP is documented from Gold Update 1,
`KNC_gold_update_1-2.1.4982-15`, with the 2.6.38 kernel [C4] pp.4-5.
**I:** the current THP switch alone proves neither promotion nor native malloc
backing. Inspect mappings after warm-up. Use explicit `MAP_HUGETLB` when
guaranteed backing is a test requirement, with allocation failure handled
explicitly; do not silently report a fallback as a huge-page result. Static
huge pages consume capacity even when idle. A library preload requires a
compatible dynamic allocator path and cannot transparently rewrite a static
binary's calls. Alignment and first touch are still necessary for useful
measurements.

**V:** MPSS supports host-side filesystem overlays for persistent changes and
RAM/NFS root alternatives [C2] §§4.2, 7, Appendix A.4; CSC warns about limited
card storage/memory [C3] pp.2-3. **I:** native jobs need only their code,
libraries, input and required services staged; symmetric jobs additionally
need matching MPI paths and reachable endpoints. Retain watchdog and RAS
reporting. Keep compilation and heavy I/O on the host where practicable. A
successful `micctrl` setting is not evidence until the rebooted card's actual
state agrees. Changes to `/etc/mpss/default.conf` may affect every card;
prefer a card-specific override when deliberately testing one card.

No inspected centre source establishes a universal card-daemon shutdown list,
the best native malloc arena count, or a benefit from changing `highres`.
These remain bounded experiments, not baseline requirements.

### 2.4 Transfers and MPI

| Mechanism | Verified scope | Consequence |
| --- | --- | --- |
| Raw SCIF RMA/DMA | [T3] printed pp.8-9 and [C1] pp.10-16 describe registered/mapped buffers, completion and alignment. **V:** the 3.1 guide's misaligned 8-KiB example loses about half the aligned bandwidth; the mutually misaligned case has extra copying. | **I:** optimize reuse and alignment before queue knobs. A one-MiB crossover in a historical example is not a universal DMA threshold. Measure both directions and initiators. |
| SCIF registration cache | **V:** MPSS3.8 `reg_cache` defaults enabled for `scif_vreadfrom`/`scif_vwriteto`; `reg_cache_limit` is in 4-KiB pages per endpoint; explicit huge-page support is controlled separately by `huge_page`, and THP support is distinct [C2] pp.127-128. | **I:** inspect the installed module/version and current limit. Do not increase limits blindly or treat these host-driver settings as native card page allocation. Raw registration and MPI's own caching may have different lifetimes. |
| SCIF peer-to-peer | **V:** MPSS3.8 `p2p`/`p2p_proxy` concern transfers between cards [C2] pp.126-127. | **I:** no useful tuning target for this one-card system. P2P proxy and CCL-proxy are different features. |
| Local host/card MPI | **R:** LRZ uses DAPL provider selection and ZIB requires SCIF for its symmetric case [R1] p.115, [T1] p.4. | **I:** verify that host/card traffic selects the SCIF provider. A virtual Ethernet interface can make MPI functional while hiding a much slower path. Keep TCP as a diagnostic fallback, not an assumed performance baseline. |
| CCL-direct / CCL-proxy and OFED | **V:** MPSS3.8 describes `ofed-mic` and, for Mellanox HCA use, `mpxyd` with `/etc/mpxyd.conf`; True Scale PSM-direct is a different path [C2] §§3.7.1-3.7.8 pp.55-60. Intel's 2014 slides distinguish direct and host-proxy paths [T4] slides 24-25. | **I:** without an HCA, do not install a proxy to speed local DMA. With a future HCA, use a matched MPSS/OFED/MPI combination and give the host proxy CPU capacity near the relevant PCI root. Same-root topology particularly matters for direct access; proxy mode can have different cross-socket tradeoffs. |
| Symmetric balance | **R:** Stampede's SC14 HPCG result used both host Xeons and Phi [M1] slide 8. **R:** Tianhe's solver explicitly overlaps transfers and host/card computation [H2] pp.5-8. | **I:** use measured kernel throughput and halo size to distribute work, then inspect the slowest rank. One rank on each device does not imply equal work. A faster sum of device peaks does not guarantee a faster synchronized job. |

For a 61-core KNC with one service core reserved, an initial symmetric setup is
two host ranks, each using up to 12 physical cores, plus one card rank using
120 workers over 60 compute cores. Reduce one host domain to 11 workers if its
service core must be dedicated; compare rather than reserve arbitrarily. On a
5110P the corresponding card starting count is 118 workers over 59 cores.
**I:** these are starting experiments, not published optimal configurations.
Use separate binaries and rank-local environment blocks. Host
`I_MPI_PIN_DOMAIN=socket` cannot be assumed to partition a card in the desired
way; inspect actual rank masks. For multiple card ranks, partition the physical
cores explicitly and ensure threads, MPI helpers and library teams fit.

### 2.5 Runtimes, allocators and workload-specific choices

**V:** Intel KNC OpenMP offers compact, scatter and balanced affinity;
balanced spreads load while keeping adjacent thread IDs together more than
scatter does [R1] pp.56-58. **R:** NERSC's NWChem study chose balanced [H5].
**I:** scatter-like spreading is useful for testing memory concurrency;
compact placement may help a cache-sharing team. More threads hide latency but
also divide L1/L2 space and add barriers. Do not elevate a STREAM winner into a
dense, sparse or LLM-wide recommendation.

**V:** Intel compiler offload has a separate environment-forwarding mechanism:
`MIC_ENV_PREFIX=MIC` selects the prefix used for card-side settings such as
`MIC_OMP_NUM_THREADS` and `MIC_KMP_AFFINITY` [R1] pp.27-28. **I:** use that
mechanism only with the matching offload runtime. A native card process receives
ordinary `OMP_NUM_THREADS`/affinity variables through its launcher; a host
shell's prefixed variable is not sufficient evidence that an MPI-launched
native process received it. Verify values inside each target process.

| Usable physical card cores C | 1 thread/core | 2/core | 3/core | 4/core |
| --- | ---: | ---: | ---: | ---: |
| 56 (57-core part, one core reserved) | 56 | 112 | 168 | 224 |
| 59 (60-core part, one core reserved) | 59 | 118 | 177 | 236 |
| 60 (61-core part, one core reserved) | 60 | 120 | 180 | 240 |

These are **I, derived counts**. The allocation must contain the same C cores
at every density. A 60-worker job packed onto 15 cores is not a one-thread-per-
core comparison. At one worker/core, a conventional KNC instruction stream can
underutilize issue opportunities; nonetheless the tuned 60-thread STREAM
result [H1] demonstrates that four workers/core is not always the winner.

**V:** Intel OpenMP's documented 200-ms blocktime and behaviour around parallel
regions are discussed in [R1] pp.59-61. GNU's busy-wait control is
`GOMP_SPINCOUNT`, with `OMP_WAIT_POLICY` also relevant [R4]. **I:** retain a
persistent team where the algorithm allows it. For intermittent offload or
outer MPI phases, compare passive waiting/short blocktime against active
waiting, measuring both power and wake-up cost. A barrier inside one persistent
region does not behave like repeatedly creating and ending regions. Intel
`KMP_BLOCKTIME=0` does not configure GCC-KNC libgomp.

**V:** glibc2.21's allocator source handles `MALLOC_ARENA_MAX`; its manual
documents mmap/trim controls but still marks arena documentation as TODO [R5].
Installed MPSS patches remain unverified. **I:** first remove
allocation/zeroing from timed iterations and reuse workspaces. Only then test
a reduced arena count when many-thread RSS is excessive. Fewer arenas can
serialize allocation, and disabling trim or raising mmap thresholds can retain
memory. Report peak RSS and allocation time as well as kernel speed. There is
no evidence for an across-the-board jemalloc/tcmalloc preload on this card.

| Workload | First useful policy | Required end-to-end distinction |
| --- | --- | --- |
| LLM interactive decode | **I:** host AVX2 baseline; 12 local physical cores versus 24 across sockets, then HT. Keep weights and KV state resident; test placement using the application's supported NUMA controls. Card use requires an actual KNC implementation and enough capacity. | Prompt tokens/s, generation tokens/s, first-token and per-token tail latency, context length, batch, quantization, KV format and RSS. Separate cold model load from a warm request; host cached/file-backed weights have different page behaviour from anonymous buffers. |
| LLM prompt/batched inference | **I:** compare larger physical-core teams and dense kernels; consider card-resident execution only after transfer costs are measured. | Batched throughput can improve while single-user latency worsens. Legacy MKL GEMM offload thresholds do not establish support for quantized operators or small-batch matrix-vector decode. |
| WRF/atmospheric work | **I:** pin MPI+OpenMP per socket, parallel first touch, and measure a complete timestep including communication and physics. Explore Phi for sufficiently large persistent kernels. | [H2] is a custom Euler atmospheric solver, not WRF. The WRF Goddard discussion paper in S12-11 [A1] concerns a physics component and did not complete peer review; it cannot establish full-model speedup. |
| STREAM / bandwidth kernels | **I:** spread across all allocated cores, pre-fault pages, vary density, and hold stores/prefetch settings fixed when comparing OS settings. | STREAM reports useful algorithm bytes; hardware memory traffic may include write allocation/ECC and must not be compared as identical byte counts. Cache-resident arrays do not measure GDDR5 bandwidth. |
| Dense BLAS/HPL | **I:** use a matched KNC-capable library, avoid nested teams and benchmark both resident and transfer-inclusive operation. Keep ECC on. | DGEMM peak throughput, HPL solution residuals and full application time answer different questions. Dense success does not qualify sparse work. |
| HPCG/SpMV/sparse solvers | **I:** test pages, memory locality, ordering and density with representative matrices; compare host-only before adding symmetric ranks. | Include setup/reordering costs and convergence; strict reductions and precision cannot be relaxed to make a system setting appear faster. MPI collectives and the slowest device can dominate. |

### 2.6 Monitoring and node qualification

**V/R:** TACC Stats collected job-level CPU, memory, paging, interconnect and
hardware-counter data on production Stampede and Lonestar [M2] pp.1-2.
This supports correlating multiple resource signals rather than watching CPU
utilization alone. **I:** use compatible PCM memory/QPI measurements and
`perf stat` on Haswell, plus `turbostat` for effective clocks/C-state residency
where supported. Inspect tool support before enabling PMU access; a missing
counter is missing evidence, not zero events.

On the card use installed `micsmc`/`micinfo` capabilities for temperatures,
frequency, power and throttling, and OS counters for faults, migrations and
memory. Card PMU/perf support depends on the MPSS kernel; the reference-gap
study's G06 remains relevant. Preserve ECC/RAS diagnostics. The best polling
rate is the lowest that can distinguish steady throttling and phase changes;
for short kernels gather telemetry outside the tight loop. For idle energy,
use the external meter as noted in step 7.

The following ladder is **our synthesis**, not a recovered common acceptance
contract at TACC, LRZ and NERSC. The evidence establishes that these tests were
used for characterization; it does not establish that every centre ran them
in this order to accept each KNC node.

| Test | What it isolates and what to record | Historical anchor |
| --- | --- | --- |
| STREAM on host and native card | Sustainable large-array bandwidth, mapping, pages, density; validate arrays and state MB/s versus GB/s convention. | TACC [H1], 174.663 GB/s Triad on SE10P; commercial 7120P/dual Ivy study [R2], 176/85 GB/s. Neither is the owner's target score. |
| Completed SCIF transfers | Registration versus steady-state transfer, both directions, small-message latency and large-message throughput; include content validation. | MPSS [C1], ZIB [T1], NASA [T2]. MPI over SCIF figures are not raw SCIF API guarantees. |
| MPI ping-pong/collective | Provider, rank masks, latency/bandwidth and imbalance under native/symmetric launch. | ZIB Intel MPI Benchmark 3.2.4 [T1] table I; NASA [T2] §6.3. |
| DGEMM and short HPL | Vector/library throughput, thermal steadiness, dense solve correctness. | [R2] 984 GF/s 7120P DGEMM; Dell [B3] p.3 uses HPL as a system stress benchmark. MPSS micperf bundles comparative performance workflows [C2] Appendix F.2. |
| Short HPCG / representative SpMV | Sparse memory traffic, reductions and communication with correctness/convergence. | [M1] slide 8 reports Stampede combined host+Phi 29.9 GF/s/node versus an earlier 20.8, using assumed STREAM rates for its efficiency calculation. It is not a Phi-only score or a Z840 forecast. |
| WRF timestep / LLM requests | The owner-visible objective and any regression in startup, tail latency, numerical result or memory. | [H2] supplies atmospheric affinity evidence; [L1] defines prompt/generation measurements. No retrieved centre measured this owner's modern LLM on KNC. |

HPL and HPCG do not replace application validation. A short diagnostic HPCG
run is not an official benchmark submission. A node can have good STREAM and
poor sparse gather performance, or good DGEMM and poor inference decode.

## 3. Source register and retrieval scope

Existing references in `.work/_shared/host-phi-refs/` (**host refs**) and
`.work/_shared/knc-refs/` (**KNC refs**) were reused before live searches.
New retrieved documents and extracts also reside in **host refs**, outside git.
Searches covered the six requested centres, additional NASA/ZIB/CSC deployments,
HP and Haswell firmware studies, MPSS3.x, Linux policy and KNC-era libraries.
No ICC header, SVML/libimf implementation, Intrinsics Guide XML or ISPC source
was consulted. All recommendations and explanations here are newly written;
Intel material is cited for interface/specification facts, without copied code,
examples, tables or prose.

| ID | Primary source, edition and exact locator | Local copy / qualification |
| --- | --- | --- |
| [B1] | HP, *Z840 Workstation Technical White Paper*, pp.8-10 and 28. | Host refs `hp-z840-technical.pdf`, reused. M60 firmware capability, not actual owner settings. |
| [B2] | HP, *Z440/Z640/Z840 Maintenance and Service Guide*, printed pp.29-31, PDF pp.39-41. | Host refs `hp-z840-service.pdf`, reused. |
| [B3] | Garima Kochhar/Dell, *BIOS tuning for HPC on 13th Generation Haswell servers*, September 2014, pp.1-3, 7-13. | **New:** `dell-haswell-bios.pdf`. R730xd prototype; table/plot CPU-label mismatch retained. Configuration page inspected visually. |
| [B4] | Molka et al., *Cache Coherence Protocol and Memory Performance of the Intel Haswell-EP Architecture*, ICPP2015, table II p.4, tables VII/VIII and §VIII p.9. | Host refs `haswell-memory-analysis.pdf`, reused; table VII visually checked. Commercial E5-2680 v3 systems, Ubuntu/kernel stated above. No MPSS involved. |
| [B5] | Intel, *E5-2690 v3 Specifications*, CPU/memory fields, read 2026-11-14 in S12-11. | Host refs `intel-e52690v3.html`, reused; specification, not performance result. |
| [B6] | Hofmann et al., *Analysis of Intel's Haswell Microarchitecture Using the ECM Model and Microbenchmarks*, 2015, §§2.3-2.4 pp.4-5, experimental setup p.8. | Host refs `haswell-ecm.pdf`, reused. |
| [C1] | Intel, *MPSS Performance Guide*, **3.1**, rev.1.0.0, October 2013, printed pp.2-16 (PDF pp.8-22). | **New partial web extraction:** `mpss-tuning-web-extract.txt`, `mpss-transfer-power-web-extract.txt`. Full PDF download failed; primary manual readable through mirror. Some extracted mapping tables have errors; do not copy their core-number labels. |
| [C2] | Intel, *MPSS User's Guide*, **3.8**, April 2017: §§3.4.5, 3.7, 4.2, 9.1-9.3, Appendices A.3-A.4/B.3.2.11/F.2; printed pp.42, 55-60, 76-79, 123-128, 135-140, 154-155, 193-195. | Same **new partial extracts** for tuning/power; other sections inspected live. Full mirror download returned 403. This is not a recovered MPSS3.7 kernel/configuration. |
| [C3] | Olli-Pekka Lehto/CSC, PRACE *Practical Experiences with Intel Xeon Phi*, WP147, pp.2-4. | Host refs `prace-knc-practice.pdf`, reused; MPSS2.x/3.x-era operational advice, exact SKU/build unspecified. |
| [C4] | Karthik Raman/Intel, *Stream on Intel Xeon Phi Coprocessors*, updated October 22, 2013, pp.2-5. | KNC refs `raman-stream-2013.pdf`, reused; Gold Update 1 and kernel version explicitly named. |
| [C5] | Intel, *Xeon Phi Coprocessor x100 Product Family Datasheet*, 328209-004EN, April 2015, pp.13, 47-59, §§2.1.4, 5. | Host refs `intel-knc-datasheet.pdf`, reused; production family specification, SKU-specific features. |
| [C6] | Intel, *Xeon Phi Coprocessor System Software Developers Guide*, 2012 edition, §2.1.6, PDF p.28. | KNC refs `ssdg-2012.pdf`, reused; early architecture edition, not a production platform qualification. |
| [O1] | Red Hat, *Low Latency Performance Tuning for Red Hat Enterprise Linux 7*, rev.2.1, November 8, 2017 (RHEL7.4), PDF pp.7-16, 26-32; revision p.34. | **New:** `redhat7-low-latency.pdf`. Filename contains 201501, but the inspected revision history says 2017; use the contents' edition. |
| [O2] | Linux **v3.10**, [kernel parameters](https://github.com/torvalds/linux/blob/v3.10/Documentation/kernel-parameters.txt) and `Documentation/timers/NO_HZ.txt`, entries `isolcpus`, `nohz_full`, `pcie_aspm`, and adaptive-tick sections. | **New:** `linux-v3.10-parameters.txt`, `linux-v3.10-nohz.txt`; unpaginated. Upstream capabilities, not proof of MPSS backports. |
| [O3] | Linux kernel documentation, *CPU Idle Time Management*, command-line parameter discussion, read 2026-11-14. | **New:** `linux-cpuidle.html`; unpaginated, current documentation used only to disambiguate control semantics. |
| [O4] | Linux **v3.10**, `Documentation/IRQ-affinity.txt`. | **New:** `linux-v3.10-irq-affinity.txt`; unpaginated. |
| [H1] | John McCalpin/TACC, *STREAM update for Intel Xeon Phi SE10P*, September 17, 2013, message body, configuration and result fields. | **New:** `tacc-stream-2013.html`; unpaginated firsthand author report. |
| [H2] | Xue et al., *Ultra-scalable CPU-MIC Acceleration of Mesoscale Atmospheric Modeling on Tianhe-2*, DOI 10.1109/TC.2014.2366754, accepted manuscript, pp.3-8, especially table I p.7. | **New:** `nscc-tianhe-stencil.pdf`; affinity table visually checked. Production Tianhe-2, custom Euler solver, MPSS3.1.2. |
| [H3] | John McCalpin/TACC, 2013 Intel Community discussion *Measuring data transferring bandwidth*, C-state/interrupt-latency reply. | **Search-index report only:** direct thread returned 404. Weaker than an inspected deployment document; no full local copy. Reported E5-2670 C1/C3 latencies 3/93 microseconds and 75-microsecond driver latency constraint. |
| [H4] | NERSC, *2013 Annual Report*, PDF pp.72-74, Babbage/application-readiness section. | **New:** `nersc-2013-report.pdf`. Operational testbed; MPSS build unspecified. |
| [H5] | LBNL/PNNL authors, *Thread-Level Parallelization and Optimization of NWChem for the Intel MIC Architecture*, PMAM2015, §3, PDF p.2. | **New:** `nersc-nwchem.pdf` from OSTI; LBNL direct endpoint returned 403. Native Babbage, Fortran14.0.1; no full MPSS/host OS inventory. |
| [H6] | DEEP project consortium, *DEEP* project description, original Cluster/Booster paragraph and software stack. | **New:** `juelich-deep-project.html`; unpaginated primary project account. Prototype architecture, not a KNC workstation OS recipe. |
| [T1] | Wende, Laubender, Steinke/ZIB, *Integration of Intel Xeon Phi Servers into the HLRN-III Complex*, CUG2014, pp.3-4, table I, appendices B/D/E. | Host refs `zib-scif.pdf`, reused; deployed CentOS6.3/MPSS2.1.6720-19. |
| [T2] | Saini et al./NASA, *An Early Performance Evaluation of Many Integrated Core Architecture Based SGI Rackable Computing System*, SC2013 / NAS-2015-04, table 1 p.3, §§5, 6.3 pp.4-6. | Host refs `nasa-maia.pdf`, reused. Production 5110P; changing MPSS, MPI version and provider confounds isolation of their individual effects. |
| [T3] | Noack/ZIB, *HAM - Heterogeneous Active Messages for Efficient Offloading on the Intel Xeon Phi*, report14-23, §3.3, printed pp.8-9/PDF pp.10-11. | Host refs `ham-scif.pdf`, reused. Mechanism/reference study; no implementation copied. |
| [T4] | Murty/Intel, IXPUG2014 MPSS presentation, slides 24-25 on CCL-direct/proxy. | **New:** `murty-ixpug-mpi2014.pdf`. B1/Sandy Bridge examples, not a Haswell production crossover rule; no chart-derived numerical claim used. |
| [R1] | Atanassov et al., editor Weinberg/LRZ, *Best Practice Guide Intel Xeon Phi*, **v2.0, January 31, 2017**, KNC pp.27-28, 38-39, 56-62, 110-116. | KNC refs `prace-bpg-v2.pdf`, reused. Contains KNL too; only KNC passages used here. Different examples have different software vintages. |
| [R2] | Vladimirov/Colfax, *Performance-to-Power and Performance-to-Cost Ratios with Intel Xeon Phi Coprocessors*, January 27, 2015, pp.2-3, table 2. | Host refs `colfax-power.pdf`, reused. Production 7120P versus dual E5-2697 v2; ICC15.0.1, MPSS3.4.1. |
| [R3] | Intel, *MKL 11.3 Update 4 Developer Guide*, section *Improving Performance on Intel Xeon Phi Coprocessors*, GUID-7F67CA7F-0B2D-4584-AE90-63A64A58F0EC. | KNC refs `mkl-11.3-knc-tuning.html`, reused; unpaginated interface reference. |
| [R4] | GNU libgomp manual, `OMP_PLACES`, [OMP_PROC_BIND](https://gcc.gnu.org/onlinedocs/libgomp/OMP_005fPROC_005fBIND.html), [GOMP_SPINCOUNT](https://gcc.gnu.org/onlinedocs/libgomp/GOMP_005fSPINCOUNT.html), read 2026-11-14. | **New:** `gcc-openmp-places.html`, `gcc-gomp-spincount.html`; existing `gcc-openmp-binding.html`. Unpaginated. Verify support in the deployed GCC-KNC runtime instead of presuming every current-manual feature. |
| [R5] | GNU glibc **2.21**, manual `memory.texi`, *Malloc Tunable Parameters*, and [malloc/arena.c](https://raw.githubusercontent.com/bminor/glibc/glibc-2.21/malloc/arena.c), `ptmalloc_init`/`arena_get2`. | **New:** `glibc-2.21-malloc-manual.texi`; reused KNC refs `glibc-2.21-arena.c`. Upstream versioned sources; MPSS patch correspondence unresolved; no implementation copied into the repository. |
| [M1] | Park et al., Intel/TACC/LBNL, *HPCG Results on IA: What Does It Tell about the Architecture?*, SC14, slide8. | Host refs `hpcg-sc14.pdf`, reused, visually inspected. Operational special Stampede hardware, mixed host/card result, MPSS revision unstated. |
| [M2] | Evans et al./TACC, *Comprehensive Resource Use Monitoring for HPC Systems with TACC Stats*, HUST2014, pp.1-2. | **New:** `tacc-stats-hust.pdf`. Production job monitoring, not a complete node-acceptance specification. |
| [L1] | ggml-org, `llama.cpp` benchmark/build documentation, snapshot read 2026-11-14 for S12-11. | Host refs `llamacpp-bench.md`, `llamacpp-build.md`, reused. Host tool interface only; no claim of KNC support. |
| [A1] | Mielikainen et al., *Intel Xeon Phi Accelerated WRF Goddard Microphysics Scheme*, GMDD7, 8941-8973, 2014, abstract and results/conclusion pp.8942, 8951-8953. | Host refs `wrf-goddard-discussion.pdf`, reused; uncompleted peer review, component result. |

Public-source gaps remain for each site's complete low-level settings and for
the exact installed MPSS3.7 libc/kernel patches. Fujitsu's Haswell memory paper
was found but direct retrieval returned 401; it is not used for numeric claims.
The newer Red Hat full performance-guide download also failed; the retrieved,
versioned low-latency brief supplies the relevant policy evidence instead.

[B1]: https://zworkstations.com/site/assets/files/1044/hp-z840-technical-white-paper.pdf
[B2]: https://h10032.www1.hp.com/ctg/Manual/c04823811.pdf
[B3]: https://dl.dell.com/manuals/all-products/esuprt_software/esuprt_it_ops_datcentr_mgmt/high-computing-solution-resources_White-Papers6_en-us.pdf
[B4]: https://tu-dresden.de/zih/forschung/ressourcen/dateien/abgeschlossene-projekte/benchit/2015_ICPP_authors_version.pdf
[B5]: https://www.intel.com/content/www/us/en/products/sku/81713/intel-xeon-processor-e52690-v3-30m-cache-2-60-ghz/specifications.html
[B6]: https://arxiv.org/pdf/1511.03639
[C1]: https://manuals.plus/m/480539d499d67ab1baec7b514547c5a6b160cf127a25427f0a267b042937be19.pdf
[C2]: https://manualzz.com/doc/48993479/intel%C2%AE-manycore-platform-software-stack--intel%C2%AE-mpss-
[C3]: https://prace-ri.eu/wp-content/uploads/WP147.pdf
[C4]: https://www.intel.com/content/dam/develop/external/us/en/documents/streamtriad-xeonphi-3.pdf
[C5]: https://www.intel.com/content/dam/www/public/us/en/documents/datasheets/xeon-phi-coprocessor-datasheet.pdf
[C6]: https://raw.githubusercontent.com/tpn/pdfs/master/Intel%20Xeon%20Phi%20-%20System%20Software%20Developers%20Guide%20%28Nov%202012%29.pdf
[O1]: https://access.redhat.com/sites/default/files/attachments/201501-perf-brief-low-latency-tuning-rhel7-v2.1.pdf
[O2]: https://github.com/torvalds/linux/blob/v3.10/Documentation/timers/NO_HZ.txt
[O3]: https://kernel.org/doc/html/latest/admin-guide/pm/cpuidle.html
[O4]: https://github.com/torvalds/linux/blob/v3.10/Documentation/IRQ-affinity.txt
[H1]: https://www.cs.virginia.edu/stream/stream_mail/2013/0015.html
[H2]: https://rajivranjan.net/wp-content/uploads/2015/02/tctianche.pdf
[H3]: https://community.intel.com/t5/Software-Archive/Measuring-data-transferring-bandwidth/m-p/951411/highlight/true
[H4]: https://www.nersc.gov/assets/Uploads/Elements/FileList/Annual-Reports/2013-NERSC-Annual-Report.pdf
[H5]: https://www.osti.gov/servlets/purl/1407275
[H6]: https://deep-projects.eu/project/deep/
[T1]: https://cug.org/proceedings/cug2014_proceedings/includes/files/pap194.pdf
[T2]: https://www.nas.nasa.gov/assets/nas/pdf/papers/NAS_Technical_Report_NAS-2015-04.pdf
[T3]: https://webdoc.sub.gwdg.de/ebook/serien/ah/ZIB/14_23.pdf
[T4]: https://www.ixpug.org/docs/Murty_IXPUG_2014.pdf
[R1]: https://prace-ri.eu/wp-content/uploads/Best-Practice-Guide_Intel-Xeon-Phi.pdf
[R2]: https://colfaxresearch.com/download/352/
[R3]: https://portal.nacad.ufrj.br/online/intel/mkl/common/mkl_userguide/GUID-7F67CA7F-0B2D-4584-AE90-63A64A58F0EC.htm
[R4]: https://gcc.gnu.org/onlinedocs/libgomp/OMP_005fPLACES.html
[R5]: https://github.com/bminor/glibc/blob/glibc-2.21/manual/memory.texi
[M1]: https://www.hpcg-benchmark.org/downloads/sc14/sc14-hpcg-bof-ver2.pdf
[M2]: https://tacc.utexas.edu/media/filer_public/35/b3/35b3a32a-3c48-4d4b-a803-f9aa30c92b52/tacc_stats_hust.pdf
[L1]: https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md
[A1]: https://gmd.copernicus.org/preprints/7/8941/2014/gmdd-7-8941-2014.pdf

## 4. Consequences for GCC-KNC card practice

This is a proposal, with **no change to `tools/card_run` or any machine**.
Inspection of `tools/card_run` establishes the following **V, repository**
behaviour: `--threads` defaults to 1; ordinary reservations take approximately
`ceil(threads/4)` physical cores; `--benchmark` takes exclusive whole-card
timing access and selects all 60 compute cores unless a profile restricts them.
Profiles select 56/59/60/60 cores for `3100`/`5100`/`7100`/`full`, with memory
limits of 5632/7680/unlimited/unlimited MiB respectively. The transfer default
is `auto`, with a 1-MiB DMA threshold. These are software policies, not findings
that all workloads perform best at those values.

- Keep the one-thread default for narrowly scoped diagnosis; require explicit
  counts for substantial tests. Lead-run timed comparisons should use
  `--benchmark` and the intended profile, with application workers distributed
  over the granted topology. `--threads 60` in an ordinary reservation does
  not allocate 60 physical cores. For the default full compute set, compare
  60/120/180/240 workers on the same 60 cores when the program supports it.
- A program that intentionally launches one worker for every CPU returned by
  `sched_getaffinity` will use all allowed logical CPUs. Setting a lower OpenMP
  thread count does not constrain such a pthread program. Density experiments
  require explicit application worker mapping/count controls; the scheduler
  reservation alone is not proof of team size. Long native checks must use
  the granted CPUs as required by the engineer rules.
- Preserve profiles as resource limits. They do not emulate a different
  SKU's frequency, memory channels/bandwidth, Turbo, thermals or ECC overhead.
  A `3100` result on a 7100-class device must be labelled a constrained run,
  not native validation on a 3100. Smaller profiles still need the common
  service-core exclusion and coordinated timing access.
- Leave default page and allocator policies unchanged pending measurement.
  Record observed huge-page backing, pre-fault/allocate outside tight timed
  loops and retain a memory margin. Per-job allocator or OpenMP variables are
  preferable to modifying MPSS globally. Intel MKL/KMP advice is not an
  implicit change to GCC's math precision or libgomp waiting policy.
- The wrapper's DMA threshold governs staging. It is not an MPI/SCIF
  crossover measurement and should not be changed from a historical figure.
  Record staging separately from native execution; include it in application
  end-to-end reports when deployment actually pays it each invocation.
- All card measurements remain owner/lead work through `tools/card_run` after
  card-time coordination. No binaries were requested or produced for this
  research ticket, and no result above is a native pass of GCC-KNC.

## 5. Contradictions and precedence

| Apparent conflict | Which evidence to use and why |
| --- | --- |
| Disable power saving for performance versus CSC's PC6 advice | Both can be right. CSC assumes long active intervals and measures energy; interactive inference pays wake-up delay repeatedly. Keep separate batch and latency policies, with first-request and warm timings. The Romley transfer explanation is not a measured Haswell uncore result. |
| TACC uses a C1 limit versus Dell DAPC can match Performance | TACC's claim concerns transfer interrupt latency on Sandy Bridge and is only index-recovered here; Dell measures whole applications on a Haswell prototype. Prefer the primary, versioned documents for mechanisms and the owner's before/after latency measurement for the actual choice. Neither proves that all C-states must be disabled. |
| CoD often helps Dell HPC cases versus it hurts SPEC OpenMP cases | The sharing patterns and topology differ. [B4] shows local/remote and application consequences. HP's supported menu [B1] takes precedence for what can actually be selected; do not prescribe a feature the firmware does not expose. |
| Enable THP for KNC bandwidth versus RHEL network-latency disables it | One optimizes resident throughput, the other tail latency from faults/compaction. TACC's same-site THP result is strong KNC evidence; it does not prove that a file-mapped LLM or a latency-sensitive host should use `always`. Compare real mappings and fresh processes. |
| Sixty STREAM threads versus four threads per KNC core | TACC's result combines explicit compiler prefetch/store choices and large pages. Tianhe's solver used 224 workers on 56 cores; NERSC tuned balanced placement for another code. Use the measured workload/density result, not a universal thread count. |
| ZIB saw little MPSS2.1-to-3.1 gain versus NASA's large transport improvement | Different transport/library versions and tests. NASA changed Intel MPI/provider behaviour; ZIB reports its own installation. Prove the active path and benchmark it instead of equating the larger version number with a guaranteed speedup. |
| TSC versus MICETC, and incompatible overhead claims | Early KNC TSC was not intrinsically invariant; later MPSS recalibrates it. The 3.1 guide gives measured examples, while 3.8 says roughly 100x access difference and has a questionable per-core MICETC description. Prefer version-matched timing behaviour and original hardware documentation; do not merge these into one precise overhead number. |
| LRZ's snapshot says Ivy Bridge/E5-2650 at 2.6 GHz | That paragraph mixes model/generation/frequency labels. Trust it for the explicit software/provider recipe; do not reuse its host identity as exact E5-v3 performance evidence. The documented 5110P pair and Linux/Mellanox setup suffice for the limited comparison here. |
| A recent oneMKL webpage still mentions automatic Phi offload | A current webpage can retain historical text. Use the explicitly versioned MKL11.x guide and a KNC-capable installed library/compiler. KNL AVX-512/MCDRAM/cluster modes and current oneAPI support do not establish KNC IMCI support. |
| Pre-production/prototype numbers versus deployed hardware | Prefer deployed matching-SKU evidence for performance expectations. Dell's platform is explicitly prototype, Jülich DEEP is a prototype architecture, and Stampede/Tianhe use special SKUs. None sets a guaranteed acceptance threshold for an unidentified owner's card. |

## 6. Owner's smallest useful before/after measurement plan

The estimates below are **I, operator wall-time budgets**, not measured runtimes;
they assume working binaries, input data and the existing Linux/MPSS install.
Provisioning a KNC application or building WRF/LLM support is not included.
The owner/lead coordinates all card access. No step below was executed here.

Use a fixed problem, precision, code/library build, input size and warm-up.
For each selected comparison collect one warm-up and three timed samples,
reporting median and range; collect repeated requests within each sample for
latency percentiles. Keep thermal conditions comparable. An A/B reversal is
only needed when drift or overlapping ranges make the result ambiguous; do
not launch an exhaustive cross-product. Retain a setting only if the intended
metric improves beyond observed run variation with validated output, no new
errors and an acceptable energy/capacity tradeoff.

| Order / budget | Minimum experiment | Decision and stop condition |
| --- | --- | --- |
| 1. Inventory and baseline, **10-15 min** | Record step1 state and current policies. Run one host STREAM and one native-card STREAM case plus the smallest representative application case under the existing configuration. Capture clocks, temperature and faults. | If mapping, clock, errors or capacity are wrong, repair that one issue before comparing tuning. No firmware/power sweep yet. |
| 2. Locality and team size, **15-25 min** | For the owner-priority workload, compare current placement with explicit binding/first touch. Host: 12 local physical workers, then 24 physical, then 48 logical only if plausible. Card: fixed compute-core set at 1/2/3/4 workers per core. Use STREAM as a short bandwidth check, not as a substitute for the application's result. | Keep the smallest team achieving the objective. Skip card LLM if no validated KNC implementation exists; record that gap instead of substituting DGEMM tokens/s. |
| 3. Transfer and MPI path, **10-15 min** | Test completed registered-buffer transfers at 4 KiB, 64 KiB, 1 MiB and 16 MiB, both directions, keeping registration separate. Compare Phi-local versus remote host memory only once. If symmetric MPI is intended, add two-rank host/card ping-pong with diagnostic provider/pinning output. | Unexpectedly low throughput or TCP fallback is a transport issue. Resolve it before more device work. Skip MPI entirely for a native-only workload. |
| 4. Pages and allocation, **10-15 min** | On the winning mapping/count, compare current backing with supported THP advice for a large-array or sparse case; use explicit huge pages only if backing or latency remains uncertain. Inspect actual pages, faults and peak RSS. Test one lower arena cap only if measured RSS/allocation contention justifies it. | Keep policy if the application benefits. A failed huge-page allocation or absent promotion is a failed configuration, not a negative huge-page benchmark. |
| 5. Dense/sparse qualification, **15-20 min** | One short resident DGEMM and one short HPL residual/stress check; one short HPCG or representative sparse solve with correctness/convergence. Compare the selected policy to the baseline only for the relevant workload. | Diagnose throttling/library failure or sparse regressions. Do not expand to full official HPL/HPCG submission runs. |
| 6. Conditional power/snoop test, **15-25 min**, plus **5-10 min per reboot** | Only if the application still shows latency/remote-bandwidth symptoms: compare one host idle/governor change or HS against ES; separately compare card PC3/PC6 for first request after idle. Hold all other choices fixed. | Reject a change that improves only a synthetic peak while worsening the objective. Leave CoD, patrol/refresh and payload alone unless a concrete remaining problem warrants a separate study. |
| 7. Application confirmation, **15-30 min** | LLM: fixed quantization/context, prompt processing (e.g. 512 tokens) and generation (e.g. 128 tokens), plus idle-to-first-response and warm repeated requests. Scientific: a short complete WRF interval or the actual dense/sparse solve; for symmetric runs compare best host-only with combined host/card and inspect rank wait time. | Report time-to-solution or prompt/decode/tail latency, memory and energy with validated outputs. Include cold load and transfer costs separately. A card-only kernel win does not meet an end-to-end acceleration claim. |

The first five stages plus application confirmation budget about **75-120
minutes**; optional power/snoop work adds **15-25 minutes plus reboots**. Shorter
initial runs can eliminate unpromising branches. If the chosen WRF/model case
cannot finish within its budget, use a documented smaller representative case
or schedule the full application separately; do not shorten away the phase
whose performance motivated the test.
