# S11-05: a measured route to higher KNC memory bandwidth

The next experiment should combine completed NGO stores, the right thread
density, explicit huge pages and coordinated prefetch, then attack mixed-stream
conflicts with relative array placement and chunking. The deliverable is a
validated six-class benchmark and a staged, bounded first sweep. No new card
measurement is claimed here. The lead replaces the conditional forecasts below
with the sweep results, retaining a separate winner for each workload.

## Peak and target

The **7120P raw interface peak is 352 decimal GB/s**. Intel's product specification
lists 16 channels and that bandwidth [1, Memory Specifications]. The system guide
describes eight controllers, two 32-bit channels per controller [2, section
2.1.8.2, p. 27]. Intel's model-specific presentation gives 5.5 GT/s for the 7120P
[3, slide 10]. Thus:

`8 controllers * 2 channels * 32 bits / 8 * 5.5 GT/s = 352 GB/s`.

The requested 75–85% target is **264–299.2 GB/s**, independently for read, write,
copy, triad and RMW. For the stencil we must publish both logical throughput and
actual DRAM traffic if counters become available; cache reuse can lift logical
throughput without lifting channel utilization. All percentages in this document
use 352, without silently changing the denominator when ECC changes.

ECC consumes capacity and traffic, but the capacity fraction is not a universal
bandwidth penalty. McCalpin's measured address mapping found blocks of 62 data
lines plus two ECC lines, spread over controllers/channels [4, first reply,
August 24, 2015]. That implies 31/32 payload capacity and an ideal sequential
storage-ratio illustration of `352 * 31/32 = 341 GB/s`; **341 is not a verified
sustained ECC-on ceiling**. ECC access locality, controller scheduling, refresh
and turnarounds are additional effects.

There is stronger same-model performance evidence than a generic ECC estimate:
Intel measured **177 GB/s ECC-on and 192 GB/s ECC-off STREAM triad on a 7120P**
[5, p. 5, lower results table], an 8.47% gain. Fang et al. report 20–27% in their
ECC experiment [6, section 3.3.1, p. 142]; that is a different system/experiment,
not a forecast for this card. The lead records current ECC state before testing.
Changing it is an owner decision and is absent from the runner.

## Existing evidence and traffic accounting

Use `knc-characterization.md`, C1, as the write-only starting evidence:
normal/NR/NGO stores achieved 83.5/114.1/226.1 GB/s at 60 cores, four threads/core.
Those values aggregate the median worker. The corresponding slowest-worker
figures are 82.4/110.8/**204.5 GB/s**. The new synchronized wall-time benchmark
must be compared to the completion-based figures, not credited a regression
merely because it does not reproduce 226.1. That study used a completion fence
and had one launch. Its energy section reports 156.5 GB/s for stream RMW.

No local class-specific baseline for read, copy, triad or this stencil is supplied
by those measurements. The ticket's roughly 175 GB/s is a planning anchor for
mixed streaming, not a measured baseline for all four classes. Intel's 192 GB/s
triad result [5] and our completed write stream already justify experiments above
180; neither establishes a fixed bound for a different class.

The benchmark reports logical reads plus writes, excludes RFO/ECC, and explicitly
reports implementation streams for splitting. With a cold, no-reuse output, the
RFO-only upper improvement from avoiding an output read is:

| Class | Useful transfers per element | With one extra output RFO | RFO-only speedup bound |
|---|---:|---:|---:|
| write | 1 | 2 | 2x |
| copy | 2 | 3 | 1.5x |
| triad | 3 | 4 | 4/3x |
| RMW | 2 | Already reads that line | 1x from eliminating an extra RFO alone |
| read | 1 | No output | 1x |
| stencil | 4 logical, about 2 compulsory with reuse | About 3 compulsory | 1.5x compulsory-traffic bound |

These are traffic-model bounds, not total speedup bounds: queueing/order effects
can also change, explaining why C1's NGO/normal ratio exceeds 2. Split triad has
five implementation transfers rather than three; its temporary must stay in
cache, or its arithmetic bandwidth bound worsens by 3/5. This cost remains visible.

## Concurrency calculation for this card

The characterization's memory latency is 357–366 TSC ticks, with its measured TSC
about 1232 MHz: roughly 290–297 ns. From Little's law, the target requires
`bandwidth * latency / 64` outstanding lines, or approximately **1196–1389 lines
card-wide, 20–23.2 per active core at 60 cores**. At full raw peak it becomes
roughly 26.6–27.2 lines/core. These are calculations using idle latency, so they
understate the requirement if latency grows under load.

McCalpin reports eight L1 misses/core and L2 hardware prefetch tracking of sixteen
streams, with about 24 prefetched lines/core [7, slides 23 and 28]. Fang et al.
measured 56–60 L2 MSHRs on their preproduction KNC [8, Table V, p. 55:19]. Neither
number is a proven usable limit on this 7120P under mixed traffic. The target
requires productive L2 prefetch concurrency beyond the demand-miss slots; adding
threads alone does not multiply resources shared by a core. Screen software
distance together with density, then use the winning pair in placement tests.

## Ranked levers and their experiments

`B` means the newly measured, completed baseline for that class. For unknown
mechanisms, `H(B)=352/B-1` is a deliberately loose raw-traffic headroom bound;
there is no claimed positive minimum. For stencil logical throughput the
compulsory-traffic upper illustration is 704/B-1 if each input line is fetched
once and output does not RFO. These bounds describe room to investigate, not
expected attainment. A negative result is retained and only excludes the exact
tested setting and allocation, never the entire mechanism.

| Rank / lever | Layer, mechanism and evidence | Expected gain or bound | Staged experiment / cost | Risk | Owner approval |
|---|---|---|---|---|---|
| 1. NGO versus NR/normal, end fence | Software/order: C1 and [9, pp. 396–398]; avoid output reads and permit more write concurrency | C1 completion gain 204.5/82.4 = 2.48x over normal; mixed-class RFO bounds above | First cases 1–3, all classes; budget 4.5 min | NGO on reused output may lose; ordering must be preserved | No |
| 2. Density and placement | On-die/DRAM queues: shared miss resources; compare siblings versus additional cores | Historical STREAM recovery up to 1/0.9 = 1.11x from four to one thread/core [7, slide 24]; card gain unknown | Cases 4–5, then compact/spread/reverse and 16/32/48-core screen; budget in runner | A low-density win for triad need not win writes | No |
| 3. Explicit 2 MB pages | OS/TLB and channel locality | Historical 175/162 = 1.080x [7, slide 24]; local gain bounded by H(B) | Cases 6–8; compare actual allocation mode, not requested mode | Fragmentation/fallback; huge prefault is serial | No, using existing mount |
| 4. Coordinated near/far prefetch | Software/L2 streamer: overlap latency without flooding queues | [8, section 6] reports 1.3x over ICC for its study; use as a test opportunity, not a transferable guarantee; H(B) bounds raw gain | None; 8/32, 8/64, 16/64, 32/128; density pairing; six-case budget 9 min | Early eviction, too many outstanding lines, instruction overhead | No |
| 5. Relative array offsets and padding | Memory/hash: avoid coincident controller/bank phases | No measured local gain; 0..H(B). [4] motivates 62-line-based offsets, without asserting a complete hash | Offset 1/62/124/992 lines, pad 17; keep logical data size fixed | Virtual offsets do not fix physical color across allocations | No |
| 6. Chunking, batching, loop splitting | Software/controller turnaround: fewer concurrent streams or longer same-direction bursts | Copy/triad traffic bounds above; split triad can lose up to the 5/3 traffic factor if intermediate spills | Chunks 128/1024/4096 lines, block/cyclic, split triad; six-case budget 9 min | Extra loads/stores and synchronization can erase controller gain | No |
| 7. Exclusive prefetch; T2 hint | Software/coherence: request ownership before RMW/normal stores; T2 is an L2 non-temporal hint [9, pp. 641–652] | Exclusive cannot remove the necessary RMW read; latency opportunity 0..H(B) | Normal-store exclusive control; shared 0/2 control; NGO outputs deliberately not prefetched | Ownership too early can evict useful data | No |
| 8. Eviction and unroll | Software/issue: compare eviction pressure against extra instructions | Our default already omits eviction; no free historical gain to count twice. Unroll bound is recovery of measured instruction time, at most H(B) | Unroll 1/4/8; none/l1/l2/both; chunk versus end fences | Larger code, spills, premature eviction | No |
| 9. First touch / interleaved chunks / page color | OS/cache placement: separate ownership and access order from physical channel mapping | 0..H(B), no promised NUMA-local gain | Serial versus parallel initialization, cyclic versus blocks, plus offset screen | Huge prefault changes the meaning of first touch; see README | No |
| 10. ECC-off crossover | Memory configuration | Same-model historical triad 8.47% [5]; 20–27% is only a separate-system sensitivity [6] | Owner-controlled on/off/on, identical winning configuration, record usable RAM and clocks; outside first pass | Reduced error protection; state change/reboot may alter page placement | **Yes** |
| 11. Clocks, governor, thermal state | Power: distinguish channel clock, core issue clock and throttling | If currently throttled, frequency-only ceiling scales as restored/current frequency; no measured positive gain if already stable | Before/after metadata plus reference/candidate/candidate/reference confirmation | Host/card clock fields may differ; do not infer MHz from throughput | **Yes** for changes; reads no |
| 12. 61st core and controller policy | Ring/OS or firmware scheduling | At equal per-core delivery 61/60 = 1.0167 is the ideal extra-core capacity illustration; actual effect can be negative. Row-policy gain remains 0..H(B) | Lead follow-up only after queue/placement screen; current runner reserves 60 compute cores | OS interference; undocumented row controls; no safe policy write identified | **Yes** |

## Answers at each layer and how to decide

**Memory system.** [2, section 2.1.8.2] assigns scheduling and refresh to MBOX;
it does not provide enough evidence to claim a fixed row-buffer policy or a
particular turnaround-cycle penalty on this board. The offset/chunk sweep is the
first experiment, holding the workload constant. Split triad is a stream-count
and temporary-reuse test, not a guarantee that all channels switch direction
together. If it wins, follow with register-tiled copy/triad bursts and count the
temporary traffic explicitly. Compare read-only and write-only achieved rates to
the mixed rate: for weights R,W, `Bmix_ideal=(R+W)/(R/Bread+W/Bwrite)` is a
measured endpoint model. A mixed shortfall suggests additional interference; it
does not identify bank conflicts without counters. Repeat winning offsets with
new mappings before proposing an allocator policy.

**Ring and directories.** [4, second reply, points 1–2] describes private L2s,
distributed directory destinations and address-dependent latency. Therefore
adjacent logical CPU numbers are not proof of adjacent directory destinations.
Our affinity list comes from the actual mask and sysfs topology. Compact versus
spread distinguishes sibling pressure from core count; reverse changes which
cores participate at a fixed count. The default runner cannot allocate the OS
core: `tools/card_run` permits physical cores 0–59. A 61-core result needs a lead
allocation decision; this experiment neither escapes affinity nor modifies the
harness. No ring ceiling is inferred from a plateau before density, offset and
prefetch controls are considered.

**Software and ICC.** Intel's tuned STREAM recipe uses explicit streaming stores,
64-line far / 8-line near prefetch, no streaming-cache eviction, and 60 spread
workers [5, pp. 2 and 4]. Its 7120P ECC-off measurement is above 180 GB/s, with
the method and configuration stated. GCC-KNC already has two-level prefetch and
NGO write streams; winning the same switch again is evidence for a workload
selection rule, not evidence of a missing instruction. [8] supplies a second
route: coordinate cache levels instead of blindly increasing distance. We do not
read ICC headers, SVML or libimf. No compiler source change or rebuild is needed
to perform this screen. The benchmark's control branches and any spills are real
costs; if all configurations underperform existing C1, inspect loop overhead
before attributing the result to hardware.

**OS/pages.** Local C4 measured a first-level DTLB threshold of 64 small pages
per core, shared among siblings: 256 KiB/core, or an equal-share illustration of
64 KiB per thread at four threads/core. At 60 cores the nominal aggregate reach
is 15 MiB, not 240 independent TLBs. Do not assume the same entry count for huge
pages. The local card-state note says THP is enabled but AnonHugePages remains
zero; `/mnt/huge` and overcommit are available. Intel's older STREAM report [5,
p. 4] expected automatic promotion on its stack; that is not proof of promotion
on MPSS 3.7 here. Linux documents explicit HugeTLB versus THP separately [10,
sections “Using Huge Pages” and “HugeTLB Pages”; 11, introduction]. MPSS's SCIF
huge-page setting is a transfer-layer control [12, section 9.3.6, p. 128], not
permission to alter this native benchmark's kernel. Keep small-page and actual
huge-page results separate. Page coloring remains an experiment, not a promised
allocator fix: establishing physical color requires a verified channel map and
access to physical page identities. No `/proc/pagemap` privileges are requested.

**Power and clocks.** Record firmware/MPSS/kernel versions, ECC state, GDDR
transfer rate, core governor, turbo policy, current/min/max core frequencies,
temperatures, throttling flags, free/huge memory, affinity, load and competing jobs.
The runner reads available card sysfs/proc fields at the boundaries and preserves
unavailable markers. The lead should use the existing host management sampler
for GDDR/ECC/power/throttle fields unavailable inside the card, at a consistent
cadence throughout confirmation. Record the cadence and tool version. No clock
or power limit is changed. A declining closing reference calls for a cooled,
paired repeat, not a new tuning claim. `CLOCK_MONOTONIC` avoids assuming TSC equals
current core frequency; [2, section 2.1.7.1, p. 26] documents TSC caveats.

## Counters: what is available, and what is missing

No new counter access has been attempted on the card by the engineer. The
existing CURRENT_STATE S9-19 note reports no usable `perf` path. That does not
prove a direct `perf_event_open` call is unavailable, so `sweep.sh probe` stages
one unprivileged core-cycle open plus the registered PMU type/format/event files
and `perf_event_paranoid`. It prints the exact errno when access fails. Core
cycles or cache misses are not reported as memory-channel bytes.

The missing ingredients for channel utilization are a **readable KNC GBOX/FBOX
interface, verified per-channel read/write event definitions and transfer units,
and permission to open those events**. McCalpin did use GBOX/FBOX counters for
mapping [4]; this is evidence the hardware can answer the question, not that
MPSS exposes it to this user. Intel's PMU manual 327357-001 is identified by [2,
section 2.1.7] and [13]; its old downloadable attachment returned 404 during this
research. No KNL or Xeon-server event encoding is substituted. This is a source
and installed-interface gap, not a claim that GBOX counters cannot work.

The probe inventory distinguishes ENOSYS (syscall), EACCES/EPERM (permission),
and absent GBOX PMU registration/event aliases. If GBOX events are exposed,
return that inventory through the ticket so a counter reader can use the actual
ABI without configuration changes. Collect channel read/write transfer deltas,
elapsed time, time-enabled/time-running and the event's documented byte unit.
For a 32-bit channel at 5.5 GT/s, `utilization=(read_bytes+write_bytes)/time/22e9`;
for an aggregated two-channel controller the denominator is 44e9. Count each
channel once, reject zero running time, and keep multiplexing visible. Compare
total traffic with the logical/RFO model before interpreting read/write mix.
No module, kernel, MSR/MMIO, perf permission or `/etc` change is in this ticket.

## What we expect: conditional forecasts to replace with card results

These are **testable scenarios, not measurements or confidence intervals**.
The common 1.3x opportunity multiplier below comes from [8, section 6], applied
as a deliberately provisional transfer of its coordinated-prefetch result.
It must not be multiplied again by page/density gains that may explain it.
For write-only, use the historical 175/162 huge-page factor from [7] as a smaller
opportunity scenario; page status in C1 is not established. Unchanged performance
is included in every interval. Unknown-class baselines remain explicitly
estimated until the first three cases replace them.

| Class | Today's GB/s and status | After top software levers, scenario GB/s | % of raw peak | 75–85% target GB/s | Lead result |
|---|---|---:|---:|---:|---|
| read | 180.4 estimate: 164 on 5110P [6, p. 141] times data-rate ratio 5.5/5.0; ideal scaling assumption | 180.4–234.5 | 51.3–66.6% | 264–299.2 | pending |
| write | 204.5 completed proxy; 226.1 worker-median aggregate, local C1 | 204.5–220.9 completed basis | 58.1–62.8% | 264–299.2 | pending |
| copy | 175 estimate from ticket mixed-stream anchor, not local copy data | 175–227.5 | 49.7–64.6% | 264–299.2 | pending |
| triad | 177 external same-model result [5, p. 5]; not our card measurement | 177–230.1 | 50.3–65.4% | 264–299.2 | pending |
| RMW | 156.5 local energy-phase measurement; method differs from this benchmark | 156.5–203.5 | 44.5–57.8% | 264–299.2 | pending |
| stencil-like | 175 planning placeholder, no matching measured kernel | 175–227.5 logical | 49.7–64.6% logical | 264–299.2 logical **and separate channel target** | pending |

The table makes the remaining experiment explicit. For example, a 230.1 triad
result needs a further **14.7–30.0%** to meet the target. If the same-model ECC
factor transfers, it becomes `230.1 * 192/177 = 249.6`; then placement/turnaround
must recover **5.8–19.9%**. Those are required gains calculated from the target,
not predictions. At a completed write rate of 220.9, the target needs another
19.5–35.4%; prioritize core/density/prefetch combinations for writes instead of
assuming the triad ECC factor applies. Retain ECC-on results as their own class
of configuration. For stencil, blocking that increases reuse must also show
reduced elapsed time and modeled/counted physical bytes, not only a larger
logical GB/s number.

## Staged plan and candidate backlog stories

The executable, runner, exact `card_run --benchmark --threads 240` commands,
option semantics and timing budgets are in `tests/bench/membw/README.md`.
The first pass has 38 cases, five samples per class, and a 57-minute summed
per-case timeout bound. Including probe, confirmation and a staging allowance
gives an 80-minute plan; the first sweep also has a 110-minute outer timeout.
All new native results are pending the lead. Host correctness and k1om
build/instruction lint are complete; no x86 batch check or GCC rebuild was run.

Promote a candidate only after paired confirmation of correctness, page mode,
affinity and stable closing reference. Require separation larger than the
observed run ranges; retain all six classes so tuning one cannot hide another's
regression. Offset winners must survive another allocation. The first sweep
screens single changes; confirmation combines the winning density, page mode,
prefetch, offset and chunk size, followed by ablation to identify contributors.

Candidate stories, conditional on those results:

1. **Choose store form by output reuse and completed-loop gain.** Extend the
   GCC-KNC store-cost decision only for loops with full-line writes and proven
   safe publication. Acceptance: copy/triad as well as write-only wins; no RMW
   regression; fences remain explicit in generated code and costs.
2. **Make software prefetch depend on stream count and runtime density.** Tune
   near/far distance and ownership hint together, with a no-prefetch version for
   cache-resident tiles. Acceptance: paired multi-class winners at both sparse
   and dense masks; source and destination bounds preserved.
3. **Offer explicit huge-page allocation with honest fallback.** Runtime helper
   reuses the existing hugetlbfs mount, reports actual mode, and does not alter
   system policy. Acceptance: allocation/fallback correctness and matched-size
   bandwidth gain, including allocation overhead for real applications.
4. **Select libgomp density for bandwidth-dominated regions.** Use actual allowed
   topology and user overrides; retain worker capacity for compute regions.
   Acceptance: density sweep plus region-entry cost shows a net application win.
5. **Cost loop splitting and tiling with the extra transfers.** Add a candidate
   vectorizer/runtime version only when the saved stall time exceeds the new
   temporary traffic and synchronization. Acceptance: fused/split correctness,
   full byte accounting and gains across independent sizes/placements.
6. **Add configurable relative array placement.** Runtime padding/color hint,
   only after channel measurements or repeat-allocation evidence. Acceptance:
   a useful gain across allocations, no hardcoded undocumented address hash.
7. **Expose counter-backed diagnostics.** Once the probe identifies an accessible
   ABI, read each channel once and correlate mix/utilization with class results.
   Acceptance: correct units, permission failures explicit, no configuration
   writes and no core-event proxy labeled as DRAM traffic.

No performance lever is ruled out by this report. Unsafe omission of a required
NGO publication fence is excluded by instruction semantics [9, p. 396]; the
experiment instead moves fences to valid boundaries. Next actions are ranked
above and staged: establish six completed baselines, combine the best software
controls, then decide the ECC and counter follow-ups using the measured gap.

## Primary references (facts only; no copied code)

1. [Intel 7120P specifications](https://www.intel.com/content/www/us/en/products/sku/75799/intel-xeon-phi-coprocessor-7120p-16gb-1-238-ghz-61-core/specifications.html), Memory Specifications.
2. [Intel System Software Developers Guide, revision 2.03, document 488596](https://doczz.net/doc/21375/intel%C2%AE-xeon-phi%E2%84%A2-coprocessor-system-software-developers-g...), sections 2.1.7–2.1.8.2, pp. 24–27; mirror of Intel's document.
3. [Marius Cornea, Intel, Numerical Computation on Intel Xeon Phi Coprocessors](https://www.lip6.fr/public/2013-10-15_Cornea.pdf), October 2013, slide 10.
4. [John McCalpin, address mapping measurements](https://community.intel.com/t5/Software-Archive/How-Xeon-Phi-divides-address-space-with-distributed-L2/m-p/1059763), August 24, 2015, first reply and “A few more comments,” points 1–2. Primary investigator's reported experiment; not a vendor-guaranteed hash specification.
5. [Karthik Raman, Intel, Stream on Intel Xeon Phi Coprocessors](https://www.intel.com/content/dam/develop/external/us/en/documents/streamtriad-xeonphi-3.pdf), updated October 22, 2013, pp. 2, 4–5.
6. [Jianbin Fang et al., Test-Driving Intel Xeon Phi](https://research.spec.org/icpe_proceedings/2014/proceedings/p137.pdf), ICPE 2014, section 3.3.1, pp. 141–142.
7. [John McCalpin, Native Computing and Optimization on the Intel Xeon Phi Coprocessor](https://www.ixpug.org/docs/IXPUG_2014_MIC_Native-new.pdf), IXPUG 2014, slides 23–25, 28 (one-based PDF pages).
8. [Zhenman Fang et al., Measuring Microarchitectural Details of Multi- and Many-Core Memory Systems through Microbenchmarking](https://zhenman.github.io/files/J1-TACO2015-uBench-XeonPhi.pdf), ACM TACO 11(4), article 55, Table V p. 55:19 and section 6. No source code imported.
9. [Intel Instruction Set Architecture Reference, 327364-001](https://dtsheet.com/doc/1263380/intel-xeon-phi-coprocessor-instruction-set-architecture-r...), VMOVNRNGOAPS pp. 396–398, CLEVICT0/1 pp. 624–627, prefetch pp. 641–656; mirror of Intel's document.
10. [Linux HugeTLB documentation](https://docs.kernel.org/admin-guide/mm/hugetlbpage.html), “Using Huge Pages” and allocation/pool sections. Current documentation is interface guidance, not evidence of MPSS kernel version support.
11. [Linux transparent huge-page documentation](https://docs.kernel.org/admin-guide/mm/transhuge.html), introduction and application behavior.
12. [Intel MPSS User's Guide, April 2017](https://manualzz.com/doc/48993479/intel%C2%AE-manycore-platform-software-stack--intel%C2%AE-mpss-), section 9.3.6, p. 128. Later MPSS edition; local 3.7 behavior comes from CURRENT_STATE, not extrapolation from this guide.
13. [Intel resource index: PMU 327357-001](https://community.intel.com/t5/Software-Archive/RESOURCES-including-downloads/m-p/816579/thread-id/5984?attachment-id=57653). Attachment unavailable when checked; no unverified raw event numbers used.
