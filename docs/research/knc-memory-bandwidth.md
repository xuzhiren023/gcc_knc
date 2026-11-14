# S11-05: a measured route to higher KNC memory bandwidth

**Reference update, S12-13 (2026-11-14).** Existing numbered bibliography
entries remain historical; new notes use [the R-number index](knc-references.md).
Entry [2]'s 488596 transcription is not recovered R01 (328207-001EN,
November 2012, 201 pages), nor the unidentified 163-page SSDG cited elsewhere.
For cache/TLB facts use R01 pp.19,22–23; for PMU counts/units use R10
pp.5–7,11–16. R06 is explicitly an engineering sample (p.55:10), R08 is
SE10P, and R09 p.4 labels its performance results pre-production even though
the table names 5110P/7110P. Keep those configurations with their results.

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

**S12-13 qualification:** the zero-promotion observation is a snapshot, not
“huge pages cannot be allocated.” Sweep 2 below reports 48 actual huge-page
configurations. R09 p.4 documents THP in KNC_gold_update_1-2.1.4982-15 or later.
**Superseded:** ~~but its result table uses an older stack; neither proves
current malloc backing.~~ The p.4 libhugetlbfs table uses MPSS 2.1.4346-16;
R09 p.5 also reports THP-stack results without libhugetlbfs: 7110P on MPSS
2.1.4982-15 at 174/181 GB/s (ECC on/off), and 7120P on MPSS 2.1.6720-15 at
177 GB/s with ECC on. All are pre-production on MPSS 2.1 and 2.6.x uOS;
none establishes today's MPSS 3.7 malloc promotion or backing.
R26a's `MIC_USE_2MB_BUFFERS` concerns offload transfers. The MPSS-guide setting
in [12] remains a **reported** later-edition source, not a verified native
allocation control. S12-12 G08 separates these cases.

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

**The core-document gap is superseded (S12-13):** R10 is now local. It and
R11a `knc_pmu` establish **two 40-bit counters per hardware thread**, overriding
R01 p.24's conflicting overview. R10 pp.12–16 distinguishes event units:
active elements are not FLOPS; L2 misses can double-count a demand and prefetch;
some events lack thread context. R11a's generic cache map uses L1 events and
restricts several CRI events to counter 0. Core access still needs S12-12 G06.
The GBOX interface/source gap remains; R12 CD37 p.27 additionally constrains
driver writes during heavy memory traffic. No raw register access is proposed.

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

## S11-06: first-sweep audit and staged long-sample calibration

Evidence is the lead's 2026-11-12 16:56-17:05Z run, boot da3144f1,
`.work/_shared/tmp/claude-next22/membw-first.out`: 38 cases, 218 valid class
records, actual small and huge allocations. The following are completed wall-time
results from that binary, not new native results or corrected long-run baselines.

| Class | Best case | Min / median / max GB/s | Median sample ms | Interpretation |
|---|---:|---|---:|---|
| read | 4 | 73.48 / 107.73 / 115.86 | 19.93 | 60 spread, small pages; reduction overhead is a hypothesis tested in sweep 2 below |
| write | 33 | 102.92 / 124.83 / 126.30 | 17.20 | Huge/60 with chunk fences; case 10's 8/32 is effectively tied, not evidence that extra fences help |
| copy | 11 | 117.89 / 137.76 / 143.37 | 31.18 | Huge/60, prefetch 8/64 is a candidate; large within-case variation |
| triad | 16 | 143.54 / 143.70 / 144.17 | 44.83 | Offset 62 is tied with 8/64 case 11 at 143.5; no established offset gain |
| RMW | 32 | 127.40 / 151.02 / 155.68 | 28.44 | Both evictions; L2-only 149.3 is tied; base case 6 is 99.3 |
| stencil | 11 | 246.62 / 265.69 / 280.28 | 32.33 | Logical reuse-inclusive throughput reaches the lower target; channel throughput is unknown |

Durations are inferred from the reported bytes/rate, not separately recorded
timestamps. At small pages, 60/120/240 spread threads give read
107.7/70.1/58.5 and triad 138.0/82.2/96.7 GB/s (cases 4/5/3).
The density effect is substantial but not yet established for long samples.
Sixty compact or reverse threads occupy only 15 physical cores on the supplied
CPU numbering, versus 60 cores for spread: this comparison confounds sibling
density and core count; it is not proof of a ring-direction effect.
Huge-page triad 135.4 versus small-page 138.0 does not establish a page win.
Closing case 38 versus identical case 6 changes write 101.7 to 124.2 (+22%),
read 88.5 to 92.1, triad 135.4 to 137.0 and RMW 99.3 to 103.5.
Write drift alone prevents accepting its small single-case improvements.

**Timing and instruction evidence.** `worker()` has one fence after each pass
and no per-pass barrier. Allocation, thread creation, initialization and ordinary
validation work are outside the intended interval. However, the old start time
precedes a barrier, and its stop time follows another barrier: faster workers
can begin validation before worker zero records that stop time. Thus it measures
more than completed streaming, with a potentially variable final scheduling delay.
The S11-06 binary reports earliest-start/latest-completed-worker envelope timing
and preserves the old wall interval and worker start skew for every sample.
It retains final completion in both fence modes and per-pass completion for RMW
and split triad, which reuse streamed output. README gives the exact overhead
ratios and matched-size/pass comparisons; no overhead is guessed or subtracted.

The original `kernel_READ_2_1_0_0` unroll-four bulk back edge was
0x414dbd -> 0x414ca0, taking 0x414d34 -> 0x414db0. It executes 31 instructions
per four lines: eight prefetches, four input loads, four integer adds, three
accumulator stores and twelve scalar/control instructions. One add reloads the
accumulator from memory each group; all four adds share a dependency chain.
This is 7.75 instructions per useful 64-byte line plus extra L1 accumulator
traffic, not a pure demand-load benchmark. New selectable private single/four
accumulators isolate that cost while retaining the original algorithm as control
and validating every line with the same modulo-2^32 result. Chunk dispatch and
all executed instructions remain timed. Counts are not cycle or bandwidth claims.
The private-four bulk path in the rebuilt binary executes 21 instructions per
four lines (eight prefetches, four loads, four independent adds, five control),
with no accumulator memory traffic inside that loop. The generated disassembly
is staged as `.work/_shared/S11-05/membw-read.dis`; addresses can change on build.

The triad's prior count is 13.25 instructions/line (README), including four
prefetches and two adds per line. Its completed best is 18.8% below Intel's
177 GB/s ECC-on comparator [5]; neither this gap nor the read reduction proves a
hardware bandwidth ceiling. The earlier write comparison must use C1's **204.5**
slowest-worker completed rate, not its 226.1 median-worker aggregate. The present
124.8 is 39.0% below that completed comparator; their workloads/timing differ.

**At sweep-2 staging (superseded by the results below).** The audit establishes the timed
boundaries, absence of per-pass barriers, short sample durations, and read-loop
overhead. It cannot establish the numerical timing penalty or which density,
page, prefetch and eviction observations survive longer native runs. The corrected
baseline is **pending**; no host result supplies it. Sweep 2 begins with triad
256 MiB x 8, 2048 MiB x 8, then 2048 MiB x 32, all 60 spread/huge/NGO/8/64.
The last should last about 1.18 seconds at 175 GB/s. If it remains below 175,
report that gap first, together with wall/envelope timing, skew, pages and drift.
Repeat the same size/pass calibration separately for the other five classes.

`sweep.sh second` stages 58 single-class cases, 87 minutes of summed 90-second
process bounds plus two minutes reserve, with an 89-minute outer timeout. It then
pairs 60/120 density with 8/64 and 32/128 prefetch, tests completed final-only
fences, private read reductions, 240-thread writes, store alternatives, and class
combinations of eviction/chunking/splitting/offset/unroll. Closing references use
new mappings for every class. Exact lead commands and numbered cases are in
`tests/bench/membw/README.md`; `second-plan` prints all commands without execution.

| Class | Short-run anchor GB/s | Provisional software scenario GB/s | Target GB/s | Gain to lower target from anchor | Long baseline / winner |
|---|---:|---:|---:|---:|---|
| read | 107.73 | 107.7-140.0 | 264-299.2 | 145.1% | pending / pending |
| write | 124.83 | 124.8-162.3 | 264-299.2 | 111.5% | pending / pending |
| copy | 137.76 | 137.8-179.1 | 264-299.2 | 91.6% | pending / pending |
| triad | 143.70 | 143.7-186.8; calibration must reach 175+ | 264-299.2 | 83.7% | pending / pending |
| RMW | 151.02 | 151.0-196.3 | 264-299.2 | 74.8% | pending / pending |
| stencil | 265.69 logical | 265.7-345.4 logical | 264-299.2 logical; channels separate | lower logical target reached | pending / pending |

These scenarios reuse the earlier explicitly conditional 1.3x prefetch opportunity
from [8], not a measured gain or an upper bound. Replace them with long baseline
and winner results; timing correction may change the anchor itself. No software
lever is yet shown to reach the physical target, and no measured hardware limit
has been isolated for any class. Current limits are the above short completed
kernel rates under those specific settings. The staged duration/fence/read-chain
experiments test benchmark limits; density/prefetch tests test latency hiding;
store/eviction/chunk tests test mixed-traffic costs. If those plateau, the next
discriminating evidence is channel traffic using the verified PMU route described
above, or an owner-approved ECC on/off/on comparison [5]. Do not prescribe ECC-off
as sufficient: even transferring 192/177 to today's best triad gives only 155.9
GB/s. Neither ECC, clocks, MPSS nor system configuration was changed here.

Host validation passed all three tests (kernel/control correctness, invalid
options, and second-sweep expansion/budget). The expected initial failure was
missing timing diagnostics, committed as b57eca55. Final host and native
GCC-KNC prefix build/instruction-lint logs are
`.work/_state/logs/S11_06_host-20261112-121926.log` and
`.work/_state/logs/S11_06_k1om-20261112-121926.log`.
The rebuilt binary and runner are staged in `.work/_shared/S11-05/`.
At that staging point, native correctness/performance and the corrected baseline
awaited the lead. No card job, GCC rebuild or x86 batch check was run by this engineer.

## S11-06: sweep-2 results, corrected baseline and sweep 3

Evidence: `.work/_shared/tmp/claude-next23/membw-second.out`, lead-run
2026-11-12 18:32-18:52Z, boot da3144f1, benchmark mode with 240 CPUs granted.
All 58 native result records validate all five samples; 48 configurations used
actual huge pages and ten used small pages, with no huge-page fallback. These
are observed card results, superseding the pending baseline above. The timing
fix and optional private reductions are in 18a2713c; this follow-up changes the
runner and analysis, not the measured kernels or byte counts.

### Calibration and measured overhead

Each row holds its configuration fixed while increasing footprint and passes.
All use 60 spread threads, NGO and per-pass completion. Read uses small pages
and 16/32 prefetch; write huge and 8/32; RMW huge, 16/32 and both evictions;
the other classes huge and 8/64. Rates are median decimal GB/s.

| Class / cases | 256 MiB x 8 | 2048 MiB x 8 | 2048 MiB x 32: corrected baseline | Median wall-time penalty, short -> long | Long start skew / envelope |
|---|---:|---:|---:|---:|---:|
| triad / 1-3 | 153.12 | 163.85 | 163.70 | 13.68% -> 0.70% | 0.17% |
| read / 4-6 | 136.25 | 146.33 | 147.24 | 30.67% -> 1.58% | 0.50% |
| write / 7-9 | 144.15 | 167.32 | 169.23 | 51.14% -> 1.79% | 0.51% |
| copy / 10-12 | 152.83 | 160.89 | 161.65 | 28.62% -> 0.86% | 0.24% |
| RMW / 13-15 | 166.50 | 177.93 | 179.11 | 23.91% -> 0.81% | 0.26% |
| stencil, logical / 16-18 | 293.16 | 316.36 | 323.10 | 30.01% -> 0.80% | 0.28% |

The penalty is the median of `(wall_seconds-seconds)/wall_seconds`, not a
subtracted estimate. Long baseline sample envelopes last 0.406-1.259 seconds;
their `(max-min)/median` rate spreads are 0.43-0.83%. Closing references 53-58
change those medians by -0.68% to +0.39%, so the earlier large write drift does
not persist. This stability statement concerns the six baselines, not every
tuning case: read case 27 spans 2.79%, and triad case 35 spans 5.79%.

The corrected envelope rate rises 5.77-17.39% from short to long, or equivalently
the short rate is 5.46-14.82% below the long rate. Most recovery occurs when
increasing footprint at eight passes; increasing passes at fixed 2048 MiB adds
-0.09% to +2.13%. Thus size, startup amortization and cache/page effects remain
confounded in the first step; it would be incorrect to attribute all recovery
to sample duration alone. The separate wall/envelope comparison demonstrates
substantial old timing overhead directly. It cannot retroactively correct the
first sweep's samples, which did not record both clocks.

There is no per-pass barrier. Final-only completion (19-24) changes the matched
long envelope medians by less than 0.6%; RMW retains per-pass completion and is
a repeat control. Fences are therefore not the dominant measured loss in these
settings. Start skew stays included in the envelope. Private read chains one
and four give 148.857 and 148.864 GB/s (43/44), only about 1.1% above the
147.24 reference: neither the memory accumulator nor the dependency chain is
shown to be the limiting factor at 60 threads and 16/32. This corrects the
first-sweep hypothesis rather than assuming fewer instructions imply more GB/s.

**STREAM calibration still misses 175 GB/s.** Plain long triad is 163.70,
6.46% below that criterion; its old-wall median is 162.58. Timing overhead and
0.17% start skew cannot account for the remaining gap. The best combined
offset/unroll case reaches 168.23, still 3.87% below 175. These are equivalent
logical operations, not a matched reproduction of Intel's compiler/system [5].

### Which tuning observations survive

- Read reaches 186.14 at 120 threads, small pages, 8/64 (25). At matched
  32/128 it is 183.37 with 60 threads and 185.21 with 120 (27/26): the 1.0%
  difference does not establish a density win. The large increase over 147.24
  demonstrates a useful prefetch/density combination, not a density-only gain.
- Write NGO is nearly flat at 60/120/240 threads: 169.23, 167.74 and 165.86
  (9/28/45). NR 28.65 and normal plus exclusive prefetch 51.49 (46/47) lose
  strongly under the tested settings. In `hints()`/`lines()`, NGO write emits
  no prefetch, so the earlier attribution to write distances 8/32 was spurious.
  The best 169.74 remains 17.0% below C1's completed-worker 204.5 comparator;
  dispatch/issue, allocation and completion-method differences remain open.
- Copy's 60-thread 32/128 result is 163.90 (33), versus 158.83 at 120 with
  those distances (32). Cyclic 1024 plus L2 eviction gives 147.42 (48), a
  combined change that does not isolate either lever. No sub-10% gain is accepted.
- Triad collapses to 74.71/76.91 at 120 threads with 8/64 and 32/128 (34/35),
  versus 163.70/166.33 at 60 (3/36). Its roughly 0.35% wall penalty and
  0.11-0.19% skew at 120 rule out barrier/start timing as an explanation of
  the roughly halved throughput. This class-specific effect needs controls for
  two input streams, prefetch pressure, output stores and address scheduling;
  the data do not identify which resource is responsible. Offset 62 plus
  unroll eight gives 168.23 (49), a provisional 2.8% combination gain. Split
  triad gives 83.56 useful GB/s (50), with five implementation streams rather
  than three; splitting at 1024 lines is rejected for this configuration only.
- RMW's both-eviction reference is stable at 179.11-179.39 (15/23/57).
  Deeper 32/128 at 60 threads drops to 157.28 (39); 120-thread 8/64 gives
  171.36 (37). Cyclic 1024 with both evictions gives 170.37 (51). Sweep 2
  lacks a matched no-eviction control, so it confirms the candidate's rate,
  not the first sweep's claimed eviction gain independently of other changes.
- Stencil reaches 326.22 logical GB/s (42); 120 threads at 32/128 give
  316.66 (41). The logical target is exceeded, but input reuse prevents
  claiming 92.7% physical channel utilization. Long-run page-size and
  compact/reverse comparisons were not repeated, so neither is established.

### Gap and staged next experiment

No measured hardware ceiling has been isolated. Using the best read and write
endpoints in the earlier traffic model predicts only
`3/(2/186.14 + 1/169.74) = 180.34 GB/s` for triad. This is an illustrative
mixed-traffic model using different configurations, not a bound. It shows why
closing a small mixed-stream gap alone would not demonstrate 264 GB/s: the
endpoints also need improvement. Even applying the historical ECC ratio [5]
to 168.23 gives about 182.49, not the target; no ECC change was performed.

The forecast below is deliberately the measured winner carried forward (the
null forecast), not an assumed gain from an untested lever. The required
improvement remains explicit; fill the last column from sweep 3's raw output.

| Class | Sweep-2 winner / case, GB/s | Forecast GB/s | Target GB/s | Gain required to lower / upper target | Sweep-3 result |
|---|---:|---:|---:|---:|---|
| read | 186.14 / 25 | 186.14 | 264-299.2 | 41.8% / 60.7% | pending |
| write | 169.74 / 55 | 169.74 | 264-299.2 | 55.5% / 76.3% | pending |
| copy | 163.90 / 33 | 163.90 | 264-299.2 | 61.1% / 82.6% | pending |
| triad | 168.23 / 49 | 168.23 | 264-299.2 | 56.9% / 77.9% | pending |
| RMW | 179.39 / 23 | 179.39 | 264-299.2 | 47.2% / 66.8% | pending |
| stencil, logical | 326.22 / 42 | 326.22 logical | 264-299.2 logical | already exceeded; DRAM unknown | pending |

`sweep.sh third` stages 58 cases at **2048 MiB x 32 passes**, five samples each.
Calibration/reference cases come first; then matched 60/120-thread 16/128 and
32/256 tests per reading class, isolated controls for the 120-thread triad
collapse, write dispatch/unroll/density tests, and matched RMW eviction controls.
The collapse reference and all six opening configurations are repeated at the
end with fresh mappings. Exact commands and numbered cases are in the README;
`third-plan` prints the expansion. The 90-second process alarms sum to 87
minutes; a two-minute reserve and 5340-second outer timeout cap the job at 89.

Interpret single-level prefetch controls with care: disabling one distance also
selects the bounds-checked loop, so a loss alone does not establish that both
cache-level hints are necessary. A recovery at 120 threads identifies a useful
configuration, then needs a paired confirmation before attributing a mechanism.
The same caution applies to offsets without known physical page colors.
If deeper prefetch and the isolated controls plateau, the missing discriminant
is actual channel traffic/latency and the documented GBOX interface described
above, followed by an owner-approved ECC crossover if warranted. Present rates
are measured limits of these kernels/configurations, not proof that software
cannot reach the target. No clock, ECC, MPSS or system configuration change is
part of sweep 3, and its native results await the lead.

Validation: all four host tests pass, including third-sweep expansion, controls
and budget; log `.work/_state/logs/S11_06_third_host-20261112-135711.log`.
The new runner is restaged at `.work/_shared/S11-05/sweep.sh`, alongside the
unchanged `membw.mic` used in sweep 2. The existing GCC-KNC build/lint evidence
above remains applicable because `membw.c` and the build flags were not changed;
no repeat compiler build or native execution was needed for this runner update.

## S11-09: GEMV weight bandwidth for decode

The validated native screen reaches **125.30 GB/s fp32, 87.25 GB/s fp16 and
70.04 GB/s int8 weight bytes**. In decode work these are **31.33, 43.63 and
70.04 billion weights/s**, respectively. Packed weights improve work/s despite
lower byte rates. None reaches the 264-299.2 GB/s weight-byte target. The next
compiler work should reduce scalar address/prefetch control and accumulator
copies; the runtime choice must be format-specific. More threads, more row
streams and smaller vector windows do not improve every format.

The workload consumes a row-major matrix with fp32, signed int8 plus a per-row
fp32 scale, or fp16 weights, and a shared fp32 vector. Each pass computes one
dot product per row. The controls, accounting, validation and exact lead
command are in `tests/bench/membw/README.md`.

### Native evidence and calibration

Evidence is the lead's 2026-11-12 21:41-21:57Z run, boot
`da3144f1-552e-4305-bd17-84a3835da020`, in
`.work/_shared/tmp/claude-next28/membw-gemv.out`. All **55 result records are
valid**, each with five samples; the job and program exit codes are zero, and
the runner reports no overlapping jobs. The run took 15.72 card minutes within
the 89-minute outer cap. Every case uses 2048 MiB (GEMV rounds upward to whole
rows), 32 passes, and spread placement within 240 granted CPUs on 60 cores.
Validation checks every output against the scalar reference and verifies
immutable inputs outside timing. This establishes correctness for the generated
exact finite inputs, not arbitrary-model accuracy or special-value behavior.

Sweep 2's corrected read reference was 186.143664 GB/s, range
185.489341-186.701635, at 120 threads, small pages and prefetch 8/64
(`.work/_shared/tmp/claude-next23/membw-second.out`, case 25). The new read
opening/closing pair is 183.502622/185.563886 GB/s at those same settings.
The fastest new read median is **189.061677 GB/s, case 8, actual 2 MiB pages**,
range 187.893589-190.170735. The raw config and CASE records correct two details
in the ticket's lead summary: read case 8 uses huge pages, and int8 case 18
uses **240 threads**, not 120. All three GEMV winners use actual 4096-byte pages.

| Workload | Case | Columns / window | Threads | Min / median / max weight GB/s | Gweights/s | Effective GFLOP/s | Median envelope ms | Start-skew range ms |
|---|---:|---|---:|---|---:|---:|---:|---|
| fp32 | 14 | 11008 / 1024 | 120 | 112.38 / 125.30 / 128.08 | 31.33 | 62.65 | 548.43 | 2.23-3.85 |
| fp16 | 46 | 11008 / full | 120 | 85.89 / 87.25 / 88.26 | 43.63 | 87.25 | 787.60 | 2.43-3.39 |
| int8 + row scale | 18 | 4096 / 1024 | 240 | 69.15 / 70.04 / 70.71 | 70.04 | 140.08 | 981.17 | 3.90-5.01 |

All winners use four row streams, unroll four and shared `vprefetch0/1` at
8/64 weight lines. Timing is earliest worker start to latest completed worker,
including start skew and completion fences. The plain-read controls matched on
threads/pages/prefetch/unroll are case 1 for fp32/fp16 and case 4 for int8;
GEMV attains 68.3%, 47.5% and 37.7% of their respective read byte rates.
Read allocates three arrays whereas GEMV allocates the weight matrix plus small
metadata/vector/output regions; these controls do not fix physical page mapping.

Closing references 52-55 versus opening 1/10/15/20 change read by +1.12%, fp32
by +2.79%, int8 by +5.19%, and fp16 by -0.24%. The largest winner spread is
fp32 case 14: (max-min)/median = 12.5%. Treat these as best medians in a screen,
not independently confirmed optima. In particular, modest int8 changes must
survive the observed reference drift before becoming defaults. Start skew is
small compared with these long envelopes; it does not explain the GEMV/read gap.
No PMU measurements isolate conversion stalls, cache misses or instruction issue.

### Prediction versus target

Retain the pre-run prediction as an **optimistic equal-byte-rate scenario**:
186.14 GB/s for each format, transferring sweep 2's read rate without charging
GEMV overhead. The measurements are 32.7%, 53.1% and 62.4% below that scenario
for fp32, fp16 and int8. It was neither a lower bound nor a measured ceiling.

| Format | Predicted scenario weight GB/s (effective GFLOP/s) | Measured best weight GB/s | Target weight GB/s (effective GFLOP/s) | Gain needed from measured best to lower / upper target |
|---|---:|---:|---|---:|
| fp32 | 186.14 (93.07) | 125.30 | 264-299.2 (132-149.6) | 110.7% / 138.8% |
| fp16 | 186.14 (186.14) | 87.25 | 264-299.2 (264-299.2) | 202.6% / 242.9% |
| int8 + row scale | 186.14 (372.29) | 70.04 | 264-299.2 (528-598.4) | 276.9% / 327.2% |

Effective FLOPs are two per weight. Weight GB/s excludes vector loads, scale
reads, partial-output traffic, reduction stack transfers, RFO and ECC; it is
not measured channel utilization. For P billion streamed parameters, the
illustrative weight-only rate is Gweights/s divided by P tokens/s. Thus the
best int8 kernel consumes 2.24 times as many weights/s as the best fp32 kernel,
and fp16 1.39 times, across the configurations/shapes in the table. These are
not matched-model speedups: quantization accuracy, metadata format, attention,
other operators and synchronization still require end-to-end measurement.

Even recovery to the matched read controls would require +46.4% fp32, +110.3%
fp16 and +165.0% int8. Reaching 264-299.2 then also requires memory-delivery
improvements beyond the measured read cases. Neither step is established here;
there is no conclusion that the requested target cannot be reached.

### Executed instruction cost and accumulator chains

IMCI `vmovaps` expands signed bytes and binary16 to fp32 on the load path
[9, section 2.2.2, pp. 30-33; VMOVAPS, pp. 379-382]. The kernels use precise
16-byte/32-byte operands and feed explicit fp32 FMAs, without a dequantized
matrix buffer. There is no separate AVX/F16C conversion instruction here.
Conversion latency/throughput itself was not measured independently.

The staged binary's disassembly is `.work/_shared/S11-05/membw-gemv.dis`.
Followed paths for `gemv_0_4`, `gemv_1_4`, `gemv_2_4` use four rows, unroll
four, shared prefetch 8/64, aligned column starts, and interior matrix addresses
where both hints are in bounds. One iteration covers 64 columns in each of
four rows (256 weights). Counts include executed branches and padding NOPs;
they exclude entry, column tails, horizontal reductions and output updates.
They are static path counts, not measured retired instructions or cycles.

| Format / symbol | Weight lines / iteration | Weight loads | Shared vector loads | FMAs | Register copies | Near + far hints | Scalar/control/NOP | Total instructions | Instructions / weight line |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fp32 / `gemv_0_4` | 16 | 16 | 4 | 16 | 20 | 32 | 279 | 367 | 22.94 |
| fp16 / `gemv_2_4` | 8 | 16 | 4 | 16 | 20 | 16 | 200 | 272 | 34.00 |
| int8 / `gemv_1_4` | 4 | 16 | 4 | 16 | 20 | 8 | 135 | 199 | 49.75 |

The back edges are `0x53fe14 -> 0x53f710`, `0x556184 -> 0x5559d0`, and
`0x54ab61 -> 0x54ab64`, respectively. The last is a jump to a loop header laid
out after its body. Runtime hint-mode/distance tests, bounds comparisons,
address formation and unroll selection remain inside these loops. Scalar
stack operands hold addresses/bounds; the inspected inner paths keep vector
accumulators in registers, but execute 20 register-to-register vector moves
per iteration. This provides a concrete optimization target beyond FMA count.
The earlier read audit counted 7.75 instructions/line for its original bulk
path; that is context from the earlier binary, not a fresh read disassembly.

Per physical weight line the kernels need 1/2/4 load expansions and 1/2/4
FMAs for fp32/fp16/int8, plus 0.25/0.5/1 shared vector loads. Four independent
row sums hide some dependency latency, but unrolling columns continues the
same four accumulator chains. More unroll does not create more independent
sums. Packed formats execute more arithmetic, conversion and copies per byte;
int8 additionally scales each partial row sum. Consequently lower packed-weight
GB/s is compatible with greater useful work/s and does not by itself measure
the conversion unit's limit.

Horizontal reduction is another visible cost: a vector store to the stack,
then 16 x87 scalar additions (eight iterations of two `fadds` plus loop control),
followed by a scalar output update, per row per column window. At 4096 columns,
window 1024 performs four such reductions per row; at 11008 it performs eleven,
window 256 performs 43, and full-row performs one. Int8 reads/applies its scale
per window. A vector-register reduction and fewer partial updates are specific
candidates, subject to the required FP ordering contract.

### What the lever measurements support

The following medians are weight GB/s. Density cases retain 4096 columns,
window 1024, four streams, unroll four, small pages and prefetch 8/64.

| Threads (siblings/core) | Read, cases 2/1/3/4 | fp32, cases 11/10/12/13 | fp16, cases 21/20/22/23 | int8, cases 16/15/17/18 |
|---|---:|---:|---:|---:|
| 60 (1) | 175.33 | 82.47 | 56.57 | 38.82 |
| 120 (2) | 183.50 | 98.55 | 72.63 | 53.58 |
| 180 (3) | 186.06 | 99.85 | 64.94 | 58.03 |
| 240 (4) | 185.59 | 90.93 | 66.28 | 70.04 |

Int8 improves 30.7% from two to four siblings while read improves only 1.1%:
this is evidence for hiding kernel latency/issue gaps, not a comparable rise
in available DRAM bandwidth. Three siblings barely improve fp32, within the
opening/closing drift; three/four lose for fp16 and four lose for fp32.
Retain 120 as the starting density for fp32/fp16 and 240 for int8, without
extrapolating the 4096-column density ladder to every shape or optimized kernel.

| Lever (120 threads unless stated) | fp32 | fp16 | int8 | Interpretation |
|---|---|---|---|---|
| Row streams 1 / 4 / 8, 4096 columns | 103.10 / 98.55 / 86.24 (25/10/26) | 65.67 / 72.63 / 72.65 (43/20/44) | 43.37 / 53.58 / 51.74 (34/15/35) | Four beats one for packed formats; eight supplies no established win. More streams remain a candidate only with reduced address/copy cost and register-pressure checks. |
| Window 256 / 1024 / full, 11008 columns | 99.12 / 125.30 / 117.24 (27/14/28) | 65.85 / 77.53 / 87.25 (45/24/46) | 39.73 / 53.13 / 58.49 (36/19/37) | Smaller vector footprint loses to added reductions/traversal. Full-row gains 12.5% fp16 and 10.1% int8 over 1024; fp32's 1024 winner has broad variation. |
| Hints 8/64 / 32/256, 4096 columns | 98.55 / 76.97 (10/29) | 72.63 / 60.87 (20/47) | 53.58 / 47.99 (15/38) | Deeper hints lose while matched read rises 183.50 to 186.27 (1/5); distance is kernel-dependent. |
| Far-only 0/128 / near-only 8/0 | 89.37 / 86.90 (30/31) | 77.23 / 78.41 (48/49) | 54.39 / 58.75 (39/40) | Read falls to 148.52 / 92.37 (6/7); packed kernels can benefit from less hint/control work, although int8 drift weakens small gains. |
| Small / actual huge pages | 98.55 / 96.71 (10/32) | 72.63 / 73.60 (20/50) | 53.58 / 55.09 (15/41) | Read improves to 189.06 (8), but no large GEMV gain. Small packed-format gains need paired confirmation. |
| Unroll 4 / 8 | 98.55 / 96.37 (10/33) | 72.63 / 72.07 (20/51) | 53.58 / 54.79 (15/42) | No robust gain over drift; the same accumulator chains remain. |

The 4096-column vector is 16 KiB and the 11008-column vector is 43 KiB;
windows 256/1024 reduce the active vector segment to 1/4 KiB. A smaller
working set is not proof of better L1 residency once sibling and weight traffic
are included. The full-row packed wins show that saving reduction and traversal
work can outweigh the intended vector-cache benefit. The fp32 shape comparison
also changes row stride, rows per tile and traversal locality, so its large
11008-column gain cannot be assigned solely to fewer reductions per weight.

Hints issue once per physical weight line, with distances in weight bytes.
A 4096-column int8 row spans 64 lines: far distance 64 reaches the next row.
Interleaving and column blocking change the time until those lines are used,
and can overlap coverage. The near-only packed wins and deeper-hint losses
support testing lower hint overhead/less premature coverage; they do not prove
which cache or queue caused the loss. The far-only comparison also changes
far distance from 64 to 128, so it is not a pure removal-of-near-hint test.

Together, the disassembly and divergent read/GEMV responses support **kernel
instruction issue, dependent accumulation and conversion work per weight byte**
as the leading explanation for the gap. They do not exclude cache delivery or
prefetch effects, nor establish a hardware conversion-throughput ceiling.
Fp32 carries the heaviest hint/control burden per group; fp16 adds two expanded
vectors per line and benefits from fewer reductions; int8 adds four and row
scaling, and responds strongly to four siblings. This is more actionable than
attributing every format to a single DRAM plateau.

### Candidate compiler/runtime backlog and next experiment

- **Specialize GEMV bulk control:** dispatch hint mode, nonzero distances and
  unroll outside the inner loop; use advancing row pointers and a bounds-safe
  bulk region plus a checked tail. The 367/272/199-instruction paths provide
  the baseline. Preserve exact operand widths and allocation bounds; measure
  code size and scalar spills as well as instructions and weight throughput.
- **GEMV vectorizer and register allocation:** represent multiple row reductions
  sharing one vector load; cost load expansion, FMA dependencies, accumulator
  copies, horizontal reduction and cleanup. Investigate the 20 copies per
  iteration before simply doubling streams. Test independent partial sums
  within a row only with the appropriate reassociation contract; ordinary FP
  semantics must remain unchanged. Compare against the native four-stream
  baseline, since eight already failed to improve this implementation.
- **Packed loads and reduction lowering:** keep signed-byte/half expansion in
  registers and make its width/conversion cost visible. Replace stack/x87
  reduction only when a legal vector reduction is available, and amortize row
  scale/partial stores over longer windows. Validate general finite values,
  exceptional values and model-specific scaling separately from this exact
  synthetic validation. No GCC build or compiler patch is part of this ticket.
- **Prefetch policy:** use bytes per row stream and consume time, not one
  distance for every format. Start from 8/64 for fp32; test near-only packed
  kernels paired with full-row windows. Do not promote 32/256, huge pages or
  unroll eight on the basis of their plain-read behavior.
- **Runtime/libgomp placement:** preserve the granted affinity mask, spread
  across cores before adding siblings, and expose format/shape-specific team
  sizes. Compare persistent OpenMP teams at 120 for fp32/fp16 and 240 for int8
  against this pthread baseline, including first touch and scheduling overhead.
  Pthread results do not establish libgomp's current placement behavior.
- **llama.cpp-style integration:** provide KNC dispatch, aligned packed loads,
  row/block-scale metadata handling and tails, without dequantization buffers.
  Real block-quantized formats can require extra unpack, zero-point and scale
  operations absent here. Partition whole rows over a persistent team, tune
  vector windows and density per layer, preserve rounding conventions, and
  measure model accuracy plus complete token latency. Weights/s is the kernel
  comparison metric; metadata and all extra transfers remain visible.

A concrete next native experiment is the interaction of **full-row accumulation
and near-only hints for packed weights**, at 120 and 240 threads and both
column counts, with matching read controls and paired opening/closing GEMV
references. The individual gains above motivate this combination; their gains
must not be multiplied into a prediction. No additional sweep is staged in
this analysis-only continuation: first keep the completed 55-case screen as
the baseline, and put bulk-control/reduction changes in a separate code ticket
before spending another card turn on their comparison.

Owner-only options remain unchanged: historical same-model ECC off/on triad
gain 8.47% [5, p. 5], with unknown GEMV gain; restoring a throttled clock has
at most the restored/current-frequency illustration for issue-bound work,
with no demonstrated gain if already stable; MPSS and page-policy changes
have unknown gain and require matched experiments. No ECC, clock, MPSS or
`/etc` setting was changed. Existing hugetlbfs was measured as allocated.

### Acceptance evidence

Implementation `b0dd4243` follows failing contract commit `737e8ed5`; staging
and host evidence were recorded in `33de9541`. All six host tests passed,
including nine GEMV format/control combinations and the 55-case calibration/
budget contract. The corrected host runner names Cygwin's `.exe` explicitly;
an older extensionless binary had shadowed it during the initial test. Log:
`.work/_state/logs/S11_09_host_final-20261112-142447.log`.

The benchmark was rebuilt with the existing GCC-KNC prefix, linted and staged
as `.work/_shared/S11-05/{membw.mic,sweep.sh}`. Build/lint log:
`.work/_state/logs/S11_09_k1om_final-20261112-142447.log`. The lead's raw native
log above supplies all 55 validated results. This continuation changes analysis
only, so passing host tests and the build were not repeated. GCC itself was
not built; x86 was not run; the engineer launched no card job.
