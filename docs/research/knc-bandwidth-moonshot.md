# S14-68: getting beyond the 7120P bandwidth plateau

2026-11-17. Research and proposed experiments only. No card job, GCC build,
firmware change, or new native performance result belongs to this ticket.

**The best large bet is to reduce the time each useful memory request occupies
the delivery path, while keeping more useful requests in flight.** Address-aware
work assignment and deliberately staggered streams deserve the next experiment.
Another sweep of larger prefetch distances does not. ECC-off is a useful
controlled intervention, but its historical gain cannot bridge 185 to 264 GB/s
by itself. A minimal kernel is valuable if it gives us physical-address control
and observability; merely removing Linux does not enlarge the memory interface.

There is a substantial clue hidden behind the third sweep's unchanged winners:
at 120 threads, cyclic triad recovered **73.64 to 147.87 GB/s**. It still lost to
60-thread triad, but a nearly twofold scheduling response is incompatible with
calling that collapse an unavoidable pin-bandwidth limit. The experiment changed
work ownership during initialization too, so it has not identified a controller
hash or proved that timing-phase staggering caused the recovery.

My planning estimate for a successful software investigation is **205-240 GB/s
read with ECC on**, with low-to-moderate confidence. **264-299 GB/s remains a
credible experiment target, not a forecast:** it requires a major improvement in
productive concurrency or loaded latency, probably combined with an owner-chosen
system configuration. I assign low confidence to sustained 299 GB/s of useful
ECC-on reads and still lower confidence to that rate for mixed traffic. Packed
GEMV also needs a separate instruction-delivery improvement.

## Evidence and accounting

Labels throughout: **V** = verified in the cited original during this review;
**R** = reported measurement, including historical local card runs inspected here;
**E** = inference or conditional estimate, never a measurement. Every proposed
gain below is E. A zero outcome and regressions remain possible. Confidence words
are engineering judgments, not statistical intervals. R-number identities and
hardware qualifications are in [the reference index](knc-references.md).

The ticket identifies the current system as a production-model 7120P, 61 cores,
16 GB, ECC on, MPSS 3.8.6, 2.6.38 uOS, Windows host, PCIe Gen2 x4. **The four
historical raw logs instead identify their kernel as
`2.6.38.8+mpss3.7.1`.** This may reflect an older image or host/card component
version differences. It is not evidence of a performance change from MPSS 3.8.6.
The next baseline must record both component versions and boot identity.

R: inspection of the supplied JSON result records found 218 valid first-sweep,
58 second-sweep, 58 third-sweep, and 55 GEMV records. Here “valid” means the
record's validation flag; it does not rehabilitate the first sweep's old timing
method. Source root for the following paths is
`C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/`:

| Evidence | Useful result and qualification |
| --- | --- |
| `tmp/claude-next23/membw-second.out`, cases 25/55/33/49/23 | Read 186.14, write 169.74, copy 163.90, triad 168.23, RMW 179.39 GB/s. Different winning configurations. |
| `tmp/claude-next28/membw-third.out`, cases 2/40/4/15/48 | Read 185.14, write 170.97, copy 166.11, triad 167.12, RMW 179.66. Five samples, 2 GiB per array, 32 passes. |
| Third sweep, cases 27/31/32/37/38 | 120-thread triad: baseline 73.64; small pages 99.91; cyclic 147.87; normal stores 99.72; offset 62 lines 71.75. These isolate different changes, not combinations. |
| `tmp/claude-next28/membw-gemv.out`, cases 8/14/46/18 | Actual huge-page read 189.06; fp32/fp16/int8 weight rates 125.30/87.25/70.04 GB/s. GEMV winners use small pages; thread counts 120/120/240. |
| [Characterization C1](knc-characterization.md), S8-01 | NGO 226.1 is a worker-median aggregate; 204.5 is derived from the slowest worker. Neither is the later earliest-start/latest-finish envelope. One launch, 4 MiB per worker, 240 workers. |

The implementation in `tests/bench/membw/membw.c:487` timestamps workers around
all passes and completion fences, including chunk dispatch. Validation is outside
the envelope. `ranges()` at line 459 uses 4096-line chunks by default: the cyclic
case above is **256 KiB chunks**, not the previously unsuccessful cyclic
1024-line-plus-eviction combination. Block ownership and cyclic ownership produce
different starting-address phases, translation working sets and initialization
ownership. New tests must separate these effects in the same resident allocation.

Use decimal GB/s throughout. Read counts input bytes; write counts output bytes;
copy counts both. Thus 166 GB/s copy means about 83 GB/s delivered to the
destination. GEMV counts weight bytes only, and stencil's 328 logical GB/s counts
reused input: neither is a measured GDDR traffic counter. Keep pin transfers,
compulsory payload, extra traffic and useful application work as separate columns.

## Model: where 352 GB/s can go

Region: completed, resident streaming work; fixed read work
`W = 2^31 * 32 = 68,719,476,736 bytes`. Full profile: 60 compute cores, explicit
affinity, normally two siblings/core for read and one for mixed streams. Overall
LLM decode share `p` is unknown; no end-to-end token-speed claim follows. If the
weight-streaming phase speeds up by `s`, whole-program speedup is
`1 / ((1-p) + p/s)`. For illustration only, `p=0.8-0.95` and `s=264/185` give
1.31-1.40x, compared with the 1.43x regional gain.

Inputs come from [knc-machine.yaml](knc-machine.yaml):
`runner_compute_cores`, `nominal_core_clock`, `core_bundle_rate`,
`thread_issue_interval`, `memory_load_latency_idle`,
`production_usable_outstanding_lines`, `memory_load_latency_loaded`, the stream/GEMV
bandwidth records, and the prefetch records. The two unknown concurrency/loaded
latency inputs must remain unknown. The pin geometry below is also supplied by
the ticket and verified architecturally in R01 section 2.1.8.2, p.27.

### Pin and service budget

The pin ceiling is `8 * 2 * 4 bytes * 5.5 GT/s = 352 GB/s` (V: R01 p.27,
early architectural guide; 7120P configuration R: ticket). Each channel contributes
22 GB/s and each two-channel controller 44 GB/s before overhead. Reads and writes
share that transfer capacity; 352 read plus 352 write simultaneously is not the
copy ceiling.

| Term | Formula / range | Evidence and interpretation |
| --- | --- | --- |
| Raw transfer time | `W/352e9 = 0.19523 s` | Conditional physical lower bound at the ticket's transfer rate, assuming every counted input byte crosses GDDR. |
| Inline ECC traffic/scheduling | Payload factor **0.90-0.97**, sensitivity range | E, not a measured ECC-bit fraction. R01 p.27 verifies optional memory ECC, but not this factor. R09 p.5 reports 177 on / 192 off on a pre-production 7120P: an 8.47% throughput gain, not an ECC capacity ratio. |
| Refresh/unavailable DRAM time | Factor **0.94-0.99** after ECC | E: a deliberately broad 1-6% service-time loss. R01 p.27 assigns refresh to the controller; installed device timings, refresh mode and temperature dependence are unknown. Measure or source them before narrowing this range. |
| Payload service after those two terms | `352 * (0.90-0.97) * (0.94-0.99)` = **297.8-338.0 GB/s** | E conditional envelope for ideal scheduling, not a sustainable-rate prediction. Equivalent time **0.2033-0.2308 s**. ECC and refresh assumptions are not independently measured. |
| Remaining delivery efficiency at 185 | `185/(297.8-338.0)` = **54.7-62.1%** | Arithmetic inference: **112.8-153.0 GB/s** of this conditional payload capacity is still unexplained. It is not all lost in one component. |
| Observed completed time | `W/185e9 = 0.37146 s` | R rate rounded from the repeated stream plateau. Large-array residency is required for interpreting this as compulsory DRAM work. |
| Target times | **0.26030-0.22968 s** at 264-299.2 | E targets: remove **29.9-38.2%** of present time. At 299.2, the pessimistic ECC/refresh envelope is already insufficient. |

The historical [Intel STREAM report, R09 p.5](https://www.intel.com/content/dam/develop/external/us/en/documents/streamtriad-xeonphi-3.pdf)
was checked against the original table: the 177/192 pair is explicitly
pre-production and uses MPSS 2.1.6720-15. Applying its ratio to 185 gives
200.7 GB/s, not 264. The earlier note's 31/32 ECC capacity illustration depends
on a source outside the indexed R-corpus; this note does not promote it into a
verified traffic fraction. ECC accesses can also change row locality, so do not
multiply an empirical ECC speedup by a second assumed ECC byte saving.

The unexplained budget has several *competing* explanations:

| Mechanism | E diagnostic range, not an allocated loss | What would distinguish it |
| --- | --- | --- |
| Read/write turnaround and write draining | **0-3%** for a clean read stream, **0-15%** for mixed payload | Pure-read demand has no compulsory write turnaround; dirty eviction/ECC activity can add some. At existing endpoints, the harmonic model gives copy **177.8** and triad **180.2 GB/s**. Their 166/167 results leave roughly 7-8% below that model, not 40%. This comparison is suggestive, because the endpoints use different settings. |
| Bank conflicts, row activation/precharge, channel imbalance | **0-30%** of available service | Compare contiguous traversal with permuted long contiguous runs at fixed bytes and allocation. Check per-channel traffic if a verified interface exists. Row hits and balanced channels are different conditions; a stride can improve one while damaging the other. No bank count, row size or address-bit map is assumed. |
| Ring/TD routing, injection and backpressure | **0-35%** of delivery time | Compare the same address sets under alternative core assignment; observe loaded latency and whether adding producers reduces per-producer service. TD lookups consume ring capacity/latency, not an extra compulsory 64-byte GDDR read. V: R01 pp.19-20; R02 pp.68-69. |
| Insufficient useful outstanding requests | **0-40%** of delivery time | Little's-law sensitivities below. Prefetch distance is not occupancy; a dropped, duplicate or too-early prefetch is not a useful line in flight. Shared core resources are not multiplied by sibling count. |
| Prefetch waste and cache pollution | **0-20%** extra transferred bytes; additional timing effects unknown | Match issued useful-line coverage, leading distance and stream count; compare retired work and completion. Core L2 events may double-count demand and prefetch, so they cannot simply be multiplied by 64 to claim pin bytes (R10 pp.12-16, R via the indexed audit, early PMU document). |
| Translation, instruction issue and OS interference | **0-10%** removable time for a mature plain-read loop; wider for other kernels | E prior, not an OS measurement. Read's huge-page result is only about 2% above 185-186. GEMV has much larger executed work per byte. Fault/interrupt counts, matched paths and a warm resident allocation separate these terms. |

At the device level, refresh loss starts with `tRFC/tREFI` over the banks it
blocks; turnaround loss starts with transitions times the required idle duration;
row-conflict loss starts with activation/precharge service not hidden behind
other banks. Their installed timings and overlap are missing, so the ranges
above are sensitivity inputs, not values reverse-engineered from 185. Likewise,
ring capacity depends on the sum of flow rates times the links each flow uses,
and on the hottest link, not just total delivered bytes. This is why an additive
waterfall assigning the remaining 113-153 GB/s to named blocks would be invented.

**Do not add these ranges.** Bank conflict raises latency, which reduces the
bandwidth a fixed request pool can sustain; counting both as independent losses
would charge the same stall twice. A useful card model is
`B_useful <= min(B_payload_service, B_ring_for_this_routing, 60*N*64/L,
B_issue_for_this_kernel) / traffic_amplification`.
Some resources overlap, others serialize; this is a bottleneck framework, not
a fitted prediction. Pin utilization 185/352 = 52.6% is inferred from useful
bytes, not measured bus activity. The ECC/refresh time term is 54.7-62.1% of the
observed time; the raw term is 52.6%. Other term utilizations are **unknown**.

### Outstanding lines and latency: the decision-changing uncertainty

R: the project's dependent-memory measurement is approximately **290-297 ns**
after conversion with its measured TSC rate. It includes its access/translation
conditions and is not loaded streaming latency. V: R01 p.19 describes roughly
38 combined requests/core; R08 slides 23 and 28 discuss eight L1 misses and
prefetch concurrency on an SE10P of unspecified production status. R06 Table V,
p.55:19 reports 56-60 L2 MSHRs on an explicitly pre-production sample. These are
different resources; none proves a usable production pool of 38, 60 or their sum.

Required **productive 64-byte lines per active core**,
`N = B_GBs * L_ns / (60*64)`:

| Loaded-latency scenario | 185 GB/s | 264 GB/s | 299.2 GB/s | 352 GB/s |
| --- | ---: | ---: | ---: | ---: |
| 295 ns, optimistic idle-like value | 14.2 | 20.3 | 23.0 | 27.0 |
| 450 ns, E | 21.7 | 30.9 | 35.1 | 41.3 |
| 600 ns, E | 28.9 | 41.3 | 46.8 | 55.0 |
| 750 ns, E | 36.1 | 51.6 | 58.4 | 68.8 |

At 600 ns, conditional pools of 24/32/38/48 productive lines/core imply
153.6/204.8/243.2/307.2 GB/s before other limits. Alternatively, 32 lines/core
at 450 ns permit 273.1 GB/s. This gives two distinct routes to the moonshot:
**roughly 40-50 productive requests at current-like loaded latency**, or
**roughly 30-35 at substantially shorter latency**. Neither route is established.
A latency probe mixed with stream traffic samples a different request class;
use it as a discriminator, not a direct measurement of every stream request's
residence time. Infer an *effective* occupancy only with that qualification.

The 180 GB/s annotation in R17 slide 13 (V, architectural deck, unqualified
stepping) is not a sufficient card-wide bound. R02 pp.68-69 distinguishes data,
address and acknowledgment rings, distributed controllers and address-dependent
destinations. Aggregate deliveries at different ring segments are not all bytes
crossing one link. The local 185-189 read results already exceed a literal
180-card-total interpretation. Conversely, this does not prove ring contention
is small: hottest-link load, injection and TD delays may still cap a particular
address/work assignment. No uniform hop map or “nearest numbered CPU” is assumed.

### RFO, stores and GEMV are different budgets

For cold whole-line output, normal write allocation can require an old-line read.
Traffic amplification is then **2x write, 1.5x copy, 4/3x triad**, relative to
their useful byte counts; RMW already needs the old line. NGO can avoid that
read when legal, but completion and ordering remain required (R27 pp.388-398,
reported architectural semantics via the cited benchmark/review; production
errata R12 apply). NGO already underlies the best write/copy/triad results, so
its RFO benefit cannot be booked again. The third sweep's normal-store triad
recovery at 120 threads suggests a pacing/ownership interaction; it does not make
normal stores the card-wide default.

The S11-09 disassembly audit in [the bandwidth note](knc-memory-bandwidth.md)
counts the actual bulk paths in `S11-05/membw-gemv.dis`. Per 256 weights:

| Format | Weight bytes | Executed instructions | Absolute aggregate issue-only roof at 60 x 1.238 GHz |
| --- | ---: | ---: | ---: |
| fp32 | 1024 | 367 | 414.5 GB/s, subsequently capped by memory and other resources |
| fp16 | 512 | 272 | 279.6 GB/s before loads, dependencies and other bottlenecks |
| int8 | 256 | 199 | **191.1 GB/s even with impossible-to-guarantee perfect dual issue** |

This is `60*1.238e9*2*weight_bytes/instructions`, an optimistic aggregate
resource bound, not a simulated per-core schedule or achievable rate. V: maximum
two instructions/bundle and one bundle/core-cycle, R01 p.19, R02 pp.34,56;
R: nominal configuration from the machine file, not a new clock measurement.
Remainders, reductions, pairing restrictions, expansion loads and stalls only
lower these roofs. At that clock, the current int8 bulk path cannot deliver
264 GB/s merely by making memory faster. Its 70 GB/s result is far below even
this partial bound, so the bound does not identify which instruction cost dominates.

Across formats the measured useful work is **31.33/43.63/70.04 Gweights/s**.
Expanded weight operands are consumed in registers; there is no pre-expanded
matrix in the benchmark (reported R27 section 2.2.2 pp.30-33 and VMOVAPS
pp.379-382). Improving weight GB/s and choosing the best representation for
tokens/s are separate decisions. A future int4 kernel adds unpack and scale
costs absent from this int8 experiment.

### Twin review and model limits

The installed knc-twin 0.4 skill, its `references/validation.md`,
`references/analytic-scales.md`, current profile and CLI capability declarations
were reviewed before assigning the ranges below. **No new twin simulation was
run and no new twin status or cycle result is claimed.** This note proposes
card-level experiments and uses explicit algebraic sensitivities, not a modeled
one-core optimized kernel. There is no candidate assembly to validate yet.

The twin's card calculation takes sustainable bandwidth as an input; it cannot
discover a higher bandwidth ceiling. Its unit/ring model assumes maps and service
parameters and is restricted by its skill to qualitative direction, never a
numerical bandwidth forecast. Core validation reports 3.1% median, 17.9% worst
error on 105 compiled HPCG/sparse loops and 39/39 rankings for pairs over 5%
apart; that breadth does not validate a GDDR controller, new streaming GEMV or
kernel/firmware policy. The installed analytic-scales prose also retains older
156.5/226.1 figures, while validation/profile material uses corrected envelope
rates: the project machine file and raw sweeps control this note's baselines.

Before implementing proposal P4 or P7, a separate ticket should run capabilities,
import the complete compiled baseline and candidate, and report actual `status`,
`assumptions`, `unsupported`, `limiting_constraints`, `calibration_status` and
`result_class`. Unsupported OS, DMA and controller behavior must remain outside
that core result. Missing fence timing is already identified in the installed
example results as `missing_parameter`; do not silently omit completion. Until
T1-03 lands, trace dependency-critical-path output is a cold-start estimate, not
a steady-state floor. Differences within about 20% need the card. Here
`T_pred` for an unchanged read is the empirical **0.363-0.371 s** band;
the **0.2297-0.2603 s** moonshot band is a target conditional on the missing
concurrency/service inputs. New predicted-versus-measured ratios are N/A.

## Ranked proposals

Rank reflects information gained and useful upside per card minute, not just
maximum imagined speedup. P1-P14 are proposals for the lead to stage later.
Minutes below are **caps on future card occupancy**, including reference runs;
engineering, source acquisition and reboot recovery are separate. “No” in an
approval statement means no new owner system-policy change, not permission for
an engineer to launch a job. All runs remain lead-coordinated.

### P1. Measure the delivery curve, not another distance winner

Mechanism: distinguish starving controllers from occupied controllers, loaded
latency from clock loss, and worker imbalance from useful traffic. R08 slides
23-25,28 motivates the concurrency test; R10 pp.5-7,12-16 constrains PMU
interpretation. Direct gain **0%**; it chooses between P2-P6 and P11-P12.

Experiment, **15 minutes**: read at 15/30/45/60 physical cores and one/two
siblings, plus a low-rate dependent chase at three background loads. Keep total
work large and fixed, return completed envelope, clocks, faults and per-worker
completion spread. Establish topology from the granted CPU set. If an already
verified GBOX interface exists, calibrate its read/write units and collect all
channels without multiplexing. Otherwise report unavailable; core misses are
not a substitute for memory bytes. A high-latency plateau with low documented
channel occupancy supports delivery work; busy balanced channels support a
service/traffic explanation. A chase alone cannot settle that distinction.

Kill the proposed interpretation if the probe changes stream throughput by over
**3%** or clocks/work differ; reduce sampling before spending more time. Risk:
measurement perturbation and misinterpreting counters. Owner approval: **no**
for existing read-only interfaces; **yes** for enabling privileged counter access.
Portability: method applies to 5110P/3120; curves must be remeasured.

### P2. Break synchronized address phases before reverse-engineering the map

Mechanism: block starts, sibling strides and coincident array phases can create
bursts toward the same bank/controller/TD even if long-run bytes are balanced.
Assign whole contiguous chunks in different orders, or give workers different
starting chunks and wrap once. Keep each byte visited exactly once. This changes
the request schedule without changing the numerical operation or adding traffic.
The third-sweep cyclic recovery is direct R evidence; R02 p.69 supplies only the
architectural mapping motivation, not the actual address function.

Prediction: **0-25% read** above 185, **0-15% mixed** above each class's winner;
a **25-45%** read upside is a low-confidence scenario only if it cuts loaded
latency by roughly 20-30% at the same effective occupancy. Regressions are
possible. The 101% recovery of a bad triad configuration is not a 101% forecast
over the best baseline.

Experiment, **20 minutes**: fixed resident allocation, block, cyclic 4096-line,
cyclic-with-worker-phase rotation, and permuted 2 MiB chunks; read at 120 threads
and triad at 60/120. Initialize all variants with the same ownership first;
separately reverse that ownership only for a surviving pair. A second mapping
and a different array size distinguish a repeatable schedule from a lucky page
set. Kill the broad-default proposal if gains stay below **5%**, disappear with
a fresh mapping, or trade read gains for large mixed-stream losses. Risk:
overlap/omitted chunks, tails, more TLB misses and lost spatial prefetch.
Approval: **no**. Carry-over: algorithm applies to all KNC; winning phase/chunk
sizes do not automatically carry over. Runtime route: explicit static ownership
for application-owned arrays; do not globally change OpenMP scheduling semantics.

### P3. Build an empirical memory map, then place work near its data path

Mechanism: choose page/core assignments that shorten core-to-directory-to-memory
paths and spread active banks. V: R22 sections II-III pp.1-7 demonstrates
physical-address-sensitive communication on a production-model 7120P, but its
barrier result is not a stream result or a portable DTD hash. Keep controller,
channel, bank, row, cache-set and directory identities separate. Whole-page
coloring may be too coarse if low bits stripe a page across destinations.

Prediction: **0-55% read**, low confidence, with **264-280 GB/s** an ambitious
favorable case rather than a guaranteed subrange. The quantitative reason is
the 32-request, 600-to-450 ns sensitivity (204.8 to 273.1), not extrapolation
from a barrier speedup. Capacity loss from selecting rare colors must be charged.

Experiment, **35 minutes after a source/privilege gate**: obtain physical page
identities through an owner-approved interface, measure pairwise interference
between disjoint contiguous streams, then test two hypotheses on held-out pages:
balanced destination groups and shorter-latency core/page assignments. Compare
identity, randomized and inferred assignments, equal bytes, two densities.
Fit an empirical classifier first; do not assume XOR address bits or a 62-line
period. Require it to predict held-out interference before choosing pages.
Kill the mapping-based optimization if its predictions fail or gain is below
**10%** after charging extra loads/indexing, lost capacity and allocation time
amortized over real tokens. Risk: privileged address exposure, fragmented memory,
or an allocator starving services. Approval: **yes** for physical mapping and
reservation. All KNC models are candidates; model/ECC/image-specific mapping is
expected until disproved. Runtime route: opt-in packed-weight allocator and
page-to-worker metadata, not a hidden compiler assumption about arbitrary pointers.

### P4. Prefetch a bounded number of useful lines; test page-boundary seeding

Mechanism: R01 p.19 (V, early guide) describes 16 L2 streams bounded by 4 KiB;
the machine file also reports the absence of L1 hardware prefetch under that
source's cache description. That boundary does not become 2 MiB merely
because translation uses huge pages. Seed the next region early, distribute
prefetch issue over time, and remove duplicate coverage. Test one/four streams
per worker with the **same total leading bytes**, not ever-larger lookahead.
Try non-temporal L2 hints and delayed `clevict` only as matched alternatives
(reported instruction semantics R27 pp.624-627,641-656).

Prediction: **0-20% read**, **0-15% GEMV**, with regression risk from extra issue
or eviction. If productive occupancy increases 10-20% at unchanged latency, the
Little's-law term rises by that amount; if it is already full, gain is zero.
This does not claim the old 16/128 or 32/256 losses will reverse.

Experiment, **14 minutes**: precompiled equal-control-path loops for ordinary
8/64, boundary seeding, budgeted burst hints, and budgeted hints plus delayed
eviction; two densities, fixed actual page backing. Record useful bytes per
hint. No-hint/tail branches must have comparable control overhead. Kill if gains
are below **5%** across fresh mappings, or apparent improvement is only fewer
runtime tests. Risk: premature eviction, overfetch, faulting/bounds assumptions,
and shared sibling pressure. Approval: **no** for instructions; **yes** for any
hardware-prefetch register change, which is not part of this test. GCC route:
stream-byte/density-aware hint scheduling and bulk/tail versioning after code
inspection and native confirmation. Applies architecturally to all KNC, retune
distances rather than transfer a 7120 value.

### P5. Separate core/ring clock sensitivity from memory clock sensitivity

Mechanism: raising a bottleneck's service clock can raise its ceiling; restoring
throttled operation can recover lost throughput. R01 pp.17,26 describes separate
frequency domains and TSC caveats (V, early guide). No installed clock state or
safe writable range is inferred from those descriptions.

Prediction: **0%** if clocks are already adequate; otherwise **0-20%** as a
planning sensitivity, with a conditional upper gain `f_restored/f_observed-1`
for a wholly frequency-bound term. For example, a 10% faster relevant domain
can provide at most 10% from that term alone; bottleneck switching lowers it.
There is no promise that a memory clock above the ticket's 5.5 GT/s is supported.

Experiment, **20 minutes plus separately allocated transition time**: first log
effective core/memory rates, temperature and throttle state under read, NGO
write and GEMV. If supported and approved, compare two documented core operating
points at fixed memory rate, then two documented memory points at fixed core
policy. A downward point is sufficient to measure sensitivity; overclocking is
unnecessary. Kill the core/ring-clock explanation if read is insensitive while
an issue-heavy control responds; kill a throttle explanation if no throttling
occurs. Risk: heat, resets, invalid TSC comparisons. Preserve thermal/power
protection and completion timing. Approval: **yes** for changes. Other SKUs need
their own supported operating points; no 7120 Turbo assumption transfers.

### P6. ECC on/off/on as a diagnostic as well as a possible gain

Mechanism: reduce ECC traffic and its scheduling interactions. V/R: R09 p.5's
pre-production 7120P pair gives an 8.47% historical gain; it is not a current
production read measurement. Prediction **0-15%** for current useful bandwidth,
with that historical ratio a central illustration; a larger effect remains a
test outcome, not budgeted upside.

Experiment, **20 minutes measurement plus 25 minutes reserved for transitions**:
owner-controlled on/off/on, identical read/write/copy/triad settings, clocks and
long work. Record new usable capacity and page mappings after each boot. Test
both the original and any P2 winner to expose an ECC/mapping interaction. The
return-to-on control must recover the earlier range. Kill ECC-off as a useful
speed policy if the gain is below **5%**, unstable, or unacceptable to the owner;
never count loss of protection as a free software improvement. Risk: undetected
memory errors and changed mappings; no durable/model-critical data during the
experiment. Approval: **yes**. Mechanism carries to ECC-capable KNC models, size
of gain does not. No compiler default can silently disable ECC.

### P7. Spend the saved memory time in a much smaller GEMV loop

Mechanism: move invariant hint-mode/bounds/unroll selection out of the bulk loop,
advance row pointers, keep independent rows in registers, reuse the vector load,
and remove avoidable accumulator copies. S11-09's 367/272/199-instruction paths
and 20 vector copies per 256 weights are the R evidence. This changes the issue
roof rather than pin rate. Keep exact-width packed loads and avoid a widened
memory buffer.

Prediction: **0-50% weight throughput** from specialization alone, conditional
on eliminating **20-40%** of the binding instruction time: `1/(1-r)` is
1.25-1.67 before memory/other limits. Planning ranges are **145-180 fp32,
100-140 fp16, 85-125 int8 GB/s** for a successful rewrite on present-like memory,
low confidence; these are neither twin forecasts nor guaranteed gains.

Experiment, **20 minutes after a separate implementation/twin ticket**: baseline
and specialized loop for all three formats, 4096/11008 columns, two/four siblings,
with best read control and held-out rectangular matrix. Inspect instruction
paths and spills before the card. Kill if lower instruction work does not improve
completed weights/s beyond noise, or gains require undeclared reassociation.
Risk: load widths, tails, exceptions, reduction order and quantization semantics.
Approval: **no** for semantics-preserving code; **yes** for a changed numerical
contract. GCC/runtime route: legal load-expansion/FMA scheduling and reduction
costing, plus persistent format/shape-specific teams. Same ISA mechanism across
KNC; actual team sizes and rates must be retuned.

### P8. Turn the C1 write discrepancy into a controlled experiment

Mechanism: isolate producer cadence, buffer extent and completed-work timing.
C1's 204.5 slowest-worker estimate motivates a gap; it does not prove a
missing 20% in the current harness. NGO-only straight-line bursts with fewer
dispatch transitions might change write draining even when issue is not saturated.

Prediction **0-20% write** (roughly 171-205 GB/s if successful); 226 is not a
completion-envelope target justified by C1. Experiment, **10 minutes**: C1-style
and current loop under one timing/completion protocol, 4 and 9 MiB per worker
at 240 workers, equal total written work, identical mappings when possible.
Only if a gap survives, compare short/long store bursts at 60/240 threads.
Kill the cadence hypothesis if matched envelopes agree within **5%**. Risk:
weakening completion or accidentally crediting cache-resident stores. Keep
verified ordering, cold output and full validation. Approval: **no**. Runtime
route: a measured large-fill implementation, size-dispatched, not NR-for-all.
Other SKUs can repeat the experiment; C1's rate is specific to this card.

### P9. Batch read and write phases without a temporary in memory

Mechanism: register-tiled copy/triad reads a short burst then emits whole-line
NGO output; stagger worker phases so all controllers do not alternate together.
This differs from split triad, which introduced five implementation streams.
It may improve turnarounds or reduce a pathological mixed request pattern.

Prediction **0-10% mixed bandwidth** with present endpoints; higher gains require
endpoint improvements too. The 177.8/180.2 endpoint estimates bound the size of
the *inferred mixed penalty*, not a physical maximum. Experiment, **12 minutes**:
interleaved baseline and register batches of 4/8/16 lines, synchronized versus
staggered worker start phases, copy and triad, best density. Include all phase
work in timing; no per-chunk global barrier. Kill if only a DRAM temporary wins
in a logical-byte metric, or native improvement is below **5%**. Risk: spills,
register pressure, output ordering, aliasing and FP changes. Approval: **no**
for a legal specialized path. GCC route: profitability only where alias/reuse
proof and measured store policy justify it; carry the method across KNC, not
batch size.

### P10. Use huge pages and a quieter persistent runtime as enabling tools

Mechanism: fewer translations, stable allocations, less startup and background
interference. Huge pages also make larger physical extents inspectable for P3.
R01 pp.22-23 documents translation structure; R09 pp.4-5 reports historical
page-backed STREAM configurations. Neither establishes current automatic
promotion. The present R read gain is about 2%, and GEMV had no large matched
page-size gain.

Prediction **0-8% steady-state bandwidth**, with potentially larger first-token
or tail-latency improvements not quantified here. Experiment, **15 minutes**:
small versus actual explicit huge pages, persistent prefaulted buffers versus
fresh allocation, and existing service policy versus approved quieter policy,
using read and GEMV with the same affinity. Kill as a plateau solution if
steady-state gain remains below **5%**, while retain any independently useful
tail-latency/capacity benefit. Risk: huge-page reservation, service starvation,
and confusing virtual reservation with resident memory. Approval: **no** for
available allocation modes and user-owned teams; **yes** for reservation, daemon,
IRQ or kernel policy changes. libgomp must honor the granted cpuset, expose actual
placement and avoid nested oversubscription. Same method across KNC.

### P11. Use on-card DMA as an independent injector and copy offload

Mechanism: a different request origin can distinguish core injection limits from
memory service limits. **Local GDDR-to-GDDR DMA exists architecturally** (V: R01
pp.27-28, early guide); it need not go through this host's PCIe x4 link. However,
eight DMA channels are not eight independent GDDR interfaces. R01 pp.19-20
describes 128 combined system-agent requests; p.27's 2 GB/s guarantee is a
guarantee, not a measured DMA maximum.

Prediction: no defensible current-board DMA rate. A deliberately conditional
64-byte/request, 128-outstanding, **300-750 ns** residence model gives
**10.9-27.3 GB/s aggregate traffic**, or **5.5-13.7 GB/s copy payload** if reads
and writes share that pool. Transfer size and installed implementation may
invalidate the model; do not treat it as a hardware bound. Possible useful gain
is **0-15% aggregate CPU-plus-DMA traffic** in an underfilled regime, not a
promise of faster GEMV.

Experiment, **15 minutes after driver review**: local DMA copy with 1/2/4/8
available channels, CPU-only copy, and CPU read plus disjoint DMA copy. Count
completed DMA bytes and CPU bytes separately; maintain a fixed useful workload
when reporting application speed. Kill DMA as a high-bandwidth engine if it
saturates well below CPU copy, or slows CPU read by at least the traffic it adds.
It may still be useful for CPU-time offload. Risk: address/lifetime mistakes,
incomplete transfers and driver hangs; R12 CD16/17 p.23 and CD39 p.27 document
relevant production ordering/lifecycle errata. Approval: **yes** for driver or
channel-allocation changes; never take a transport-owned channel. R25a/b
`scif_readfrom`/`micscif_rma_copy` are an older 3.6.1 implementation reference,
not proof of installed local-copy support. Applicability is architectural KNC;
available driver path must be established per image.

DMA staging of every weight into a second GDDR buffer is **not accepted as a
decode optimization without a contrary experiment**: it normally reads the
original, writes staging, and reads staging, versus one original read. Even
perfect overlap cannot erase that 3x payload accounting. A DMA engine cannot
directly populate application vector registers in the documented interface.

### P12. Boot a minimal diagnostic kernel, then grow only useful facilities

Mechanism: deterministic physical allocation and worker placement, minimal
interrupt noise, and a clean route to verified counters. This could expose the
P3 mapping and P13 policy opportunities even if removing OS overhead itself is
small. It does not remove the hardware coherence/directory path (R01 pp.19-20,
R02 pp.68-69, V, architectural sources).

Prediction for **OS removal alone: 0-10% throughput**, low confidence; mapping
benefits are charged to P3, not counted again. To explain 185-to-264 entirely
through OS removal would require at least **29.9%** of current elapsed time to
be removable OS interference. That is a falsifiable requirement, not shown by
the small wall/envelope difference or the 120-thread triad collapse.

Experiment, **30 minutes measurement plus a separate 30-minute boot/recovery
allocation**, after a prepared recoverable image: stock/minimal/stock, identical
user loop, frequency/ECC state, buffer backing/physical placements as far as
reproducible, no host transfer in timing. Preserve card service/health support
on the reserved core. If physical placement changes, classify that result as
the combined image+mapping intervention. Kill a minimal-OS *bandwidth* project
if matched read/write gains stay below **5%** and no needed observability is
unlocked. Risk: failure to boot, lost RAM state, health-service or interrupt
mistakes; recover using a known working host/boot image, with no flash change in
the first experiment. Approval: **yes**. The later modern-Linux project can
reuse interfaces, but a newer kernel is not itself a bandwidth mechanism.
All KNC models need image/driver/errata qualification.

### P13. Ask whether controller policy, not the ISA, is leaving bubbles

Mechanism: documented row scheduling, channel interleaving, prefetch-trigger or
refresh policy could change service efficiency. R01 p.27 establishes controller
scheduling/refresh duties; it supplies no sufficient production tuning recipe.
The index marks register manual 330991-001 and installed MPSS source coverage
as unresolved. This is a **source-gated proposal**, not permission to guess MMIO.

Prediction **0-45% read**, very low confidence, only if P1 demonstrates idle
service capacity and a verified supported policy can recover it. Raising
delivery efficiency from about 0.58 to 0.80 would yield about 38% at fixed
payload service; the arithmetic does not establish a writable policy.

Experiment, **20 minutes after source review and owner approval**: one documented
setting at a time, baseline/change/restore, read and mixed traffic, temperature,
ECC state and errors recorded. First establish that the setting is writable,
safe for the stepping, and actually takes effect. Stop this branch if no such
supported interface exists, if channels are already service-saturated, or if
the gain is below **10%** and cannot justify maintenance risk. Risk: corruption,
hangs and thermal effects; never disable refresh or health protections. R12
CD37 p.27 also constrains GBOX writes under traffic. Approval: **yes**, including
source acquisition/indexing before implementation. No cross-SKU register or
mapping assumptions. Runtime route is an explicit owner-selected platform
profile, never an invisible compiler action.

### P14. Raise effective decode bandwidth by moving fewer weight bytes

Mechanism: lossless packed blocks, exact zero/block elision where real data
supports it, or sharing one fetched weight block across independent requests.
These can exceed 352 GB/s of *uncompressed-equivalent work* without exceeding
the pins. Adjacent tokens in one autoregressive sequence cannot simply be
batched as independent inputs. Numerical format changes require a separate
accuracy contract; the existing fp16/int8 results do not authorize one.

Prediction: **0-50% single-request weights/s** if measured compression is
1.2-2.0x and saved memory time exceeds unpack/metadata cost; otherwise zero or
a loss. Batch 2-4 independent requests offers a weight-traffic amortization
factor of 2-4, not a promised latency/speedup factor. From total phase time,
`T_new >= max(compressed_bytes/B, decode_work/issue_rate)` plus dependencies and
non-overlapped overhead; that test must use actual weights, not synthetic zeros.

Experiment, **20 minutes after a real-format implementation**: original versus
lossless packed weights, exact reconstruction/output check, full layer including
scales/metadata; then batch 1/2/4 independent requests, report latency and
throughput separately. Kill if bits/weight do not fall enough, unpack becomes
dominant, or latency/accuracy violates the application contract. Risk:
decompression bounds, corrupted metadata and numerical drift in lossy variants.
Approval: **no** for exact user-owned layout changes; **yes** for numerical or
service-policy changes. KNC-specific load expansion is reported in R27
pp.30-33,379-382; no hardware decompressor is assumed. Carry-over to other KNC
is plausible, with independently measured instruction/memory balance.

## First card session: 90 minutes maximum

This is a **future lead-run diagnostic session**, not a staged executable or
authorization to start work on another ticket. Preparation must produce the
equal-path hint variants, fixed-allocation scheduling controls and low-rate
latency probe in their own tickets. Compile/lint and test correctness before
allocating card time. If preparation is incomplete, use existing controls for
the corresponding block or return unused card time; do not code live on the card.
No reboot, ECC change, clock change, privileged mapping or new driver is needed
in this first session.

| Minute window | Exact case families / maximum scope | Decision |
| --- | --- | --- |
| 0-8 | Record host MPSS and card image/boot, granted topology, actual pages, clocks/ECC/temperature using existing interfaces; warm buffers; read120, write60, copy60, triad60 references, five samples each | If references drift over 3% or the image differs from historical metadata, establish the new baseline and label historical comparisons accordingly. Diagnose instability before selecting a winner. |
| 8-23 | P1: read at 15/30/45/60 cores x 1/2 siblings (8 cases); chase alone and with 30-/60-core backgrounds (3 brief cases), reserving its core within the allocation | Early plateau plus rising latency prioritizes routing/occupancy; clock changes prioritize P5; lack of counters remains an explicit ambiguity. |
| 23-43 | P2: read120 and triad120 x block/cyclic4096/phase-rotated cyclic/permuted-2MiB (8 cases); triad60 block/cyclic controls (2) | If cyclic recovery reproduces in one fixed initialized allocation, investigate schedule/translation. If it needs changed initialization, investigate ownership/mapping. Neither observation alone identifies bank bits. |
| 43-57 | P4: baseline, boundary seed, budgeted hints, budgeted hints+delayed eviction, at 60/120 threads (8 read cases), equal control paths | If gain follows productive concurrency, retain that design. If no gain, stop deeper-distance tuning and prioritize P3/P5/P6. |
| 57-67 | P8: two loop bodies x two per-worker extents (4 matched NGO-write cases), same completed-byte work | If C1 gap vanishes, retire it as evidence of missing write headroom. If it persists, preserve the exact producer pattern for a separate ticket. |
| 67-82 | Best surviving read-delivery policy versus baseline on fp32/int8 GEMV, two shapes (8 cases), fixed existing arithmetic | Transfer of gain supports a general memory/runtime policy. No transfer prioritizes P7's instruction work; do not force the read policy into GEMV. If no read winner exists, omit this block. |
| 82-90 | One surviving configuration and baseline in ABBA order on fresh allocations; closing read/write references and cleanup | Accept only completed, correct work with stable references. Record no winner when results overlap or drift. Stop at 90 minutes even if candidates remain. |

Keep 2 GiB per streaming array and 32 passes for long-reference comparability,
five samples per scored case, and full correctness checks outside timing. Timing
includes tails, dispatch, mandatory fences and the last worker. New variants
must preserve those semantics. The windows are hard occupancy budgets, not
guarantees that every case will finish; cap individual cases and skip remaining
cases within a block rather than overrun. Use every granted CPU only where the
case calls for it; subsets are intentional for scaling, not accidental serial
validation. Validation lasting over a minute must distribute across the grant.

After this session: a stable **10% or greater** read win that transfers to GEMV
earns a runtime/compiler implementation ticket and another shape/model check.
A smaller **5-10%** repeatable win is useful but does not explain the moonshot
gap. A stable plateau with no such win earns P3 source/mapping work and an
owner decision on P5/P6. High measured channel utilization with excess bytes
prioritizes traffic reduction; low utilization with long waits prioritizes
injection/routing. Mixed-only wins go to P9. An ECC crossover or boot experiment
gets its own reserved session and rollback budget; neither is appended at minute 89.

## What the ceiling means for each workload

All ranges below are E, with present nominal clocks and enough resident work.
“Payload service” is the ECC/refresh-only sensitivity, deliberately omitting
bank/ring/queue losses. “Planning result” is a successful-investigation estimate,
not a new measurement. Different proposals consume the same headroom; their
percentage gains must not be multiplied blindly.

| Traffic | Physical/accounting ceiling | Successful-investigation planning result | Confidence and stretch |
| --- | --- | --- | --- |
| Read, one compulsory fetch per line | Raw **352**; ECC-on/refresh-only **298-338**; ECC-off with the same refresh sensitivity **331-348** GB/s | **205-240 on**, **220-260 off** | Low-to-moderate for the on range; low for off until crossed over. **264-299** needs a large delivery improvement. Very low confidence above 300 useful ECC-on. |
| NGO write, completed whole lines | Same raw 352 and conditional payload **298-338 on**, **331-348 off**; ownership/draining can reduce it | **180-215 on**, **195-235 off** | Low; C1 is a clue, not an envelope proof. **250-290** is an ambitious controller/producer success scenario. |
| Normal cold write with RFO | At most **176 raw useful GB/s**; **149-169 on** under the payload sensitivity | No new forecast; choose it only for reuse/legality or a measured pacing benefit | High confidence in the 2-transfer accounting when the RFO actually occurs, low in any sustained number. |
| NGO copy | Raw **352 summed** = **176 destination**; conditional on mixed loss **0-15%**, ECC-on **253-338 summed** = **127-169 destination** | **180-215 summed on**, **195-235 off**, or half those rates delivered | Low. **240-280 summed** is a stretch after endpoint gains. Never report it as 240-280 destination GB/s. Normal-copy RFO changes the raw useful ceiling to **234.7 summed**, **117.3 destination**. |
| GEMV weight bytes | `min(read_service/(1+extra_DRAM_bytes/weight_bytes), issue/expansion/reduction roof)`; cannot simply assign the read ceiling to each format | Successful code work at current-like memory: **145-180 fp32**, **100-140 fp16**, **85-125 int8** | Low; S11-09 fp32 spread reached 12.5%. Combined memory and code stretch: **210-270 / 150-220 / 110-180**, respectively, very low confidence. The current int8 instruction path has the 191.1 partial roof above. |

The expected advantage of 264 GB/s is not “another 79 for free”: it needs
**42.7%** more useful read bandwidth than 185. The raw-pins improvement bound
is **90.3%**, before mandatory overhead. Reaching 299.2 needs **61.7%**.
Eliminating just the inferred copy/triad mixed penalty cannot do this; neither
can adding the reserved core (61/60 is only a 1.67% ideal producer increase,
and it would compete with services).

For actual 5110P and 3120 cards, keep the mechanisms and redo the budgets from
their verified memory geometry, clocks, enabled controllers, usable cores and
capacity. `knc-machine.yaml` leaves several 3120 constants and all matched
smaller-model sustainable rates unknown; do not fill them from memory. A 56-
or 59-core runner restriction on this 7120P is not a smaller physical card.
The read-only latency/density experiment and one held-out GEMV shape are the
minimum transfer checks before a policy becomes a SKU default.

## Negative evidence and implementation gates

These exclusions are deliberately narrow and evidence-based:

| Claim not accepted | Evidence / scope |
| --- | --- |
| Larger distances or unroll eight will break the plateau | S11-06 sweeps 2-3 and S11-09 held the winners essentially flat; deeper GEMV hints lost. P4 changes coverage/issue policy, not just distance. |
| More siblings are always better | 120-thread triad collapses; NGO write is flat at 60/120/240. Conversely int8 GEMV's best screen used 240. Keep workload-specific teams. |
| Split triad is a free controller optimization | Sweep-2 case 50: 83.56 useful GB/s with five implementation streams. P9 excludes that temporary. |
| Removing completion fences explains the gap | Matched long per-pass versus final-only cases changed by less than 0.6% (S11-06 calibration); removing required final completion is invalid. |
| Huge pages alone buy 40% | Actual huge-page read is 189.06; matched GEMV changes are small. This does not reject physical mapping work or latency benefits in other shapes. |
| ECC-off alone reaches 264 | R09 p.5's same-named-model historical ratio gives 200.7 from 185, not 264; different configurations may differ but need the crossover. |
| PCIe/host DMA tuning solves resident GDDR streaming | R01 pp.26-28 separates host transport and on-card memory paths; these kernels already run on resident data. Host throughput affects loading/offload, not compulsory local weight bandwidth. |
| A helper thread creates another request pool on the same core | Shared-resource architecture in R01 pp.19,23-24 and the measured sibling plateaus. A remote helper can add a producer but also a cache-to-cache hop (R02 p.69); no rate is credited without a same-total-core experiment. |
| The ring has a proven 180 GB/s global maximum | R17's annotation lacks the needed traffic scope; R02's distributed topology and the measured read results rule out treating it as a universal useful-byte cap. |

For a winner, GCC-KNC should expose the true costs of hints, loads, conversions,
copies, spills and completion. Use `TARGET_KNC` IMCI paths and preserve strict
FP, masks, fault footprint and aliasing semantics. Runtime policy must respect
the allocated CPU set and actual page backing, retain per-format/density
choices, and keep a fallback when a mapping or allocation is unavailable.
Application-owned weight packing can exploit a measured map; arbitrary program
pointers cannot silently inherit it. Owner-controlled ECC, clocks and kernel
settings are explicit platform choices, not compiler optimizations.

## Source locators and review scope

Only indexed primary hardware sources are used for new architectural claims.
All vendor facts are paraphrased; no vendor code, tables or examples are copied.
Originals reside in the shared reference corpus, not this worktree.

| Source | Pages/sections used | Qualification |
| --- | --- | --- |
| R01, Intel SSDG 328207-001EN, November 2012 | pp.17-20,22-24,26-28; especially 2.1.8.2 and 2.1.8.2.1 | Clock, request, L2-stream and controller/DMA descriptions V original text; translation and absent-L1-prefetch details R via machine file. Early architecture, not a production timing/queue measurement. |
| R02, Rahman, 2013 | pp.34,56 and chapter 5 pp.67-69 | V architectural descriptions; no qualified production stepping. |
| R06, Zhenman Fang et al., TACO 2014 | p.55:10, Table V p.55:19 | R via machine file/reference audit; explicitly pre-production. No production queue constant imported. |
| R08, McCalpin, IXPUG 2014 | slides 23-25,28 | V original text; SE10P, production qualification unspecified. |
| R09, Raman, STREAM, updated October 2013 | pp.4-5, especially p.5 lower table | V original and live Intel PDF; published results R, explicitly pre-production. |
| R10, Intel PMU 327357-001 | pp.5-7,12-16 | R via indexed audit and bandwidth note; early event definitions, not verified installed access. |
| R12, Intel specification update 328205-016 | CD16/17 p.23, CD37/39 p.27; stepping applicability pp.17-19 | DMA ordering/lifecycle text V; CD37 R via indexed bandwidth review. Production x100 errata, applicability must match deployed stepping. |
| R17, Klemm, December 2014 deck | slides 10-14, especially 13 | V original text; architecture, no qualified timing experiment. |
| R22, Dolbeau rev.1.40, April 2014 | sections II-III pp.1-7 | V local original, production-model 7120P. Live author URL failed retrieval; no new online edition substituted. |
| R25a/b, MPSS 3.6.1 source snapshot | `scif_readfrom`, `scif_unregister`, `micscif_rma_copy` | R from indexed source/practice review; API reference, not the installed 3.8.6 implementation. |
| R27, ISA 327364-001 | 2.2.2 pp.30-33; pp.379-398,624-627,641-656 | R via supplied implementation audits and knc-optimize practice references; early interface, production errata still apply. |

Reviewed project context: the supplied bandwidth, characterization, microarch,
prefetch, machine, reference and optimization notes; the card-policy portions of
`system-tuning-playbook.md`; `CURRENT_STATE.md`; membw source/README/sweep cases;
and the three requested modeling skills. Their old or superseded statements
were not silently treated as current facts. The only repository deliverable is
this note; no new tests or binaries are needed for an analysis-only ticket.
