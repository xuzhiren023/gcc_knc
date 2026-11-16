# Multi-core unit and full-ring simulation: design for review

S14-13, Phase 1. **Pending lead review; Phase 2 has not started.** This is an
implementation contract and validation plan, not a simulation result. No native
measurement, new parameter fit, or multi-core prediction was made in this phase.
The scope is brief `codex-briefs/03-multicore-unit.md`; brief 02 owns `--jobs`.

## Evidence and geometry

Source numbers refer to `docs/research/knc-references.md` in GCC-KNC. Facts below
were verified in the local text extractions at the stated printed pages (R01)
or PDF slides (R08). R01 is the November 2012 architecture guide, not a
stepping-qualified production experiment. R08 describes SE10P; its production
qualification and stepping are unspecified. Project measurements below are
reported from the named rows on the production project card, stepping unspecified;
the original native logs were not reanalyzed here.

| Evidence | Consequence for this design |
|---|---|
| R01 p.13: up to 61 cores, eight controllers with two channels each | Model eight controllers and sixteen channel queues, with all controllers reachable by every tile. |
| R01 pp.17,19: core/L2 interface, directory and ring stop; controllers and system agent also attach to the interconnect | A tile contains the existing core, private caches, ring endpoint and directory attachment. A 61-position model is a contracted geometry, not a verified count of all physical ring agents. |
| R01 pp.19,22: 512 KiB private L2, 64-byte lines, eight ways, inclusive of L1; distributed directories | Preserve each core's existing cache geometry and LRU approximation; do not turn the L2s into one shared capacity pool. |
| R01 p.22: **64 directory slices**; R08 PDF slide 46 corroborates directory routing | Keep all 64 directory tables, even though there are 61 modeled core positions. Co-location of the three extra slices is assumed. |
| R01 pp.20-21: private and global coherence states; R08 PDF slide 46: directory-mediated source selection | Track owners and sharers, dirty data, and in-flight requests. Do not equate a remote cache access with a DRAM access. |
| R08 PDF slides 27-28: remote-cache latency and latency/concurrency interaction | The reported roughly 275 ns is an SE10P comparison, not a 7120 parameter. Queuing and outstanding requests must be explicit. |
| R22 section II pp.2-3, **reported** by the correction to S8-10 C11 in `knc-characterization.md`; production-model 7120P, stepping unspecified | Core number alone does not establish physical distance; unknown address mapping must be varied. The C11 near/far rows cannot identify a per-hop delay. |

Use 61 abstract bidirectional ring positions, numbered 0 through 60. This honors
the approved geometry without claiming that the real chip has only 61 ring stops.
Default eight detailed positions are `floor(i * 61 / 8)`:
`0, 7, 15, 22, 30, 38, 45, 53`. For isolated scaling runs use the corresponding
formula for N = 1, 2, 4 or 8, or an explicit placement. Logical CPU IDs do not
automatically map to these positions.

Attach controller j at `floor(j * 61 / 8)` and directory d at
`floor(d * 61 / 64)`. These placements are **assumed**, with rotated, clustered
and user-specified maps as alternatives. Every slice exists independently of
whether its position has a detailed core. Controllers and extra directories
share a modeled position without introducing hidden extra hop costs. The effect
of the contraction is part of the geometry sensitivity report.

## Unit, state, and request protocol

Each detailed tile has one `CoreSim`, one private `MemoryModel` (including DTLB,
prefetch streams and miss slots), its L2 contents, and a ring injection endpoint.
Contexts remain 0-3 within each core. The scheduler and instruction latencies
remain those of the existing single-core engine; multi-core changes concern
stepping and the backing memory service. The global TD holds line-address keys,
sharer sets, an optional dirty owner, and pending transaction queues. It must
also learn about private-cache evictions and invalidations.

Use the following reduced states, explicitly a model rather than a complete
implementation of the hardware coherence protocol:

| State/event | Modeled behavior |
|---|---|
| Absent | No private copy; the next read routes through the TD to a channel. |
| Clean shared | One or more L2 copies, memory current. TD selects a present source by shortest modeled return path, ties by tile ID (assumed; alternative: lowest tile ID). |
| Dirty owned | One owner has current data. Ownership transfers or sharing must retrieve that data; memory cannot supply a stale copy. |
| Dirty shared | A designated owner supplies current data, with additional read sharers; owner eviction writes back before losing ownership. This retains the distinction exposed by R01 p.21 without claiming full GOLS timing. |
| Pending | Serialize conflicting operations for a line at its TD. Merge compatible reads; no cache hit is visible before its fill completes. |
| Local hit | Existing local hit cost; a store to a shared line still needs an ownership upgrade. |
| Remote read | Requester -> TD; TD lookup -> owner; owner response -> requester; completion acknowledgement -> TD. Charge every hop, lookup, endpoint service and occupied link. |
| Memory read | Requester -> TD -> controller channel; service -> requester; completion -> TD. Update sharers only at the appropriate completion event. |
| Ordinary store miss | RFO obtains the old line, invalidates other sharers and waits for acknowledgements before ownership; partial stores retain unaffected bytes. |
| Full-line no-read store | Obtain ownership and invalidate sharers but omit the old-data read. Charge the outgoing data and eventual memory write. Do not treat no-read as no-coherence or zero traffic. |
| Eviction | Clean copies leave the sharer set; a dirty last owner sends a 64-byte writeback through the ring and channel queue. Inclusive L2 eviction invalidates local L1 copies. |

The first implementation supports disjoint writable streams and shared read-only
data, plus explicit line-transaction tests of ownership/invalidation. The existing
functional trace generator runs contexts independently; it cannot correctly
execute races, spin loops or value-dependent inter-core communication. Such
kernels return `unsupported`, not a successful functional check. Locked operations,
fences without measured costs, arbitrary atomics and executable barrier protocols
are not silently approximated. Full-line no-read eligibility must be proven from
the instruction and coverage; unsupported partial combinations are rejected.

## Ring and controller events

Route each message in the shortest direction on the 61-position ring; route
requests, responses and acknowledgements independently. Represent separate
logical address, data and acknowledgement fabrics, with independent occupancy
for each directed link and finite injection credits. This separation is an
**assumed modeling choice from the brief**, not a verified three-ring bandwidth
fact from the R01 passages inspected here. An alternative shares one link budget
among all message types; report sensitivity to it. No unverified physical ring
width is asserted.

A hop-arrival event competes for its next directed link at the current global
time; it must not reserve an entire future route and displace requests that have
not yet been generated. Non-preemptive FIFO link service uses stable transaction
sequence numbers for ties. A 64-byte data packet occupies `ceil(64 / slot_bytes)`
slots; control packets use one slot. Link release and downstream arrival are
separate events, allowing pipelining. Count occupancy, waiting time, hop count,
bytes and queue depth by direction and fabric. Finite endpoint credits bound
outstanding traffic; internal queues may be represented sparsely, with explicit
event and storage budgets rather than an invented hardware queue depth.

Each of sixteen channels is a FIFO pipelined server: service interval controls
admission throughput, and a separate unloaded delay controls completion latency.
Independent channels overlap. At this stage DRAM banks, refresh, ECC wires and
read/write turnaround are not simulated; their aggregate effect is an assumed
effective service interval, not an asserted physical bus rate. Channel saturation
must arise from queued transactions, never by capping a reported GB/s afterwards.

The read-only starting interval per channel is derived as

`service_cycles = 16 * 64 * card.clock_hz / (read_only_GBs * 1e9)`.

Use `card.clock_hz = 1.238e9` and `read_only_GBs = 186.1` from the measured card
profile. The aggregate observation is measured; equal channel sharing and its
use as a service parameter are **assumed/derived**. Keep fractional time as
integer subcycle ticks or rational credit accumulation, not independent ceiling
rounding per request. Choosing one tick = 1/1024 core cycle is a numerical design
choice; test that service accumulation does not introduce persistent bias.

The profile's 179.4 RMW, 82.4 normal-store and 169.7 NGO GB/s values are useful-byte
rates from different configurations. They are calibration comparisons, not three
independent physical channel roofs. Account explicitly for RFO reads, dirty
writebacks and useful bytes; do not apply both a useful-byte reduction and the
same traffic penalty a second time. Use one traffic-independent read-derived
interval initially, with an assumed write/read interval ratio (below). Any change
to that ratio using an observed store row makes that row calibration evidence.

## Parameter contract and uncertainty

No profile changes are made in Phase 1. Phase 2 adds parameters with the same
status/source/alternatives conventions as existing profiles and regenerates
`parameters.md`. Every assumed value below is a starting sensitivity point, not
a fit or a hardware claim. Unlisted required parameters give `missing_parameter`.

| Parameter | Proposed value, source/status, alternatives |
|---|---|
| Line/L2 geometry | 64 B, 512 KiB, eight ways; documented, verified R01 pp.19,22, early architecture guide. Keep existing cache replacement approximation. |
| Ring positions / detailed tiles | 61 / 8; owner design; contracted placement assumption. N = 1,2,4 for scaling tests; explicit placements allowed. |
| TD slices / controllers / channels | 64 / 8 / 16; documented, verified R01 pp.13,22, early guide. Attachments assumed as above. |
| TD address map | Assumed `(line_number xor (line_number >> 6)) mod 64`; alternatives sequential modulo, fixed-seed permutation, explicit physical-line map and single-slice stress. Not the undisclosed hardware hash. |
| Channel address map | Assumed `line_number mod 16`, controller = channel // 2; alternatives XOR-folded lines, page interleave, explicit map and single-channel stress. Model virtual addresses as physical surrogates only with an explicit assumption. |
| Hop delay | Assumed 1 core cycle; alternatives 2 and 4. C11 does not isolate it. |
| Data slot / control service | Assumed 32 bytes per cycle per direction / one control packet per cycle; data alternatives 16 and 64 B, control alternatives 2 and 4 cycles. Effective slot capacity, not verified wire width. |
| Injection credits | Assumed 32 per tile; alternatives 16 and 64. Separate from inherited L1 miss limits. |
| TD lookup / initiation interval | Assumed 8 / 1 core cycles; alternatives lookup 4,16,32 and interval 2,4. Separate latency from throughput. |
| Remote source service | Existing local-L2 latency plus assumed 0 endpoint cycles; endpoint alternatives 16,64. Does not add the full measured remote latency to a separately modeled route. |
| Remote endpoint residual | If using 192 ns from `latency.remote_l2_line_ns`, derive a nonnegative residual after modeled unloaded route/TD/source costs, averaged over the declared map. S8-10 C11 then becomes calibration, not held out. Negative residual rejects the parameter combination. Alternative: leave unset and request measurement. |
| Memory unloaded delay | Profile `latency.memory = 328` cycles, derived from S6-03 `memory.load_lat` minus its separately charged DTLB penalty. Decompose the total into path plus nonnegative channel residual under the declared map; do not add another 328 cycles to the path. Alternative inherited 357 is reported, not silently selected. |
| Per-core fill interval | Existing 20 cycles, reported S6-03 `memory.load_rt`, 19.48 ticks per line per core at four threads (`knc-machine.yaml: memory_effective_load_reciprocal_throughput`); alternative 37. In the new backend this limits injection once, rather than adding a second independent completion throttle. |
| Channel interval | Above read-derived formula; assumed equal sharing, derived from measured S11-06 sweep-2 read winner. Sensitivity uses profile read alternatives 147.2 and 189.1 GB/s; those rows cease to be independent validation if used to choose parameters. |
| Write/read service ratio | Assumed 1; alternatives 1.25 and 2. Expose read/write queue statistics and open misses; do not select by held-out GEMV or triad. |
| Background active cores | 60 total by default (`card.usable_cores`, project placement); alternative 61 with OS interference explicitly excluded. Thus eight detailed tiles imply 52 background cores, or 53 in the explicit 61-active scenario. |
| Background epoch | Assumed 256 cycles; alternatives 64 and 1024, with startup/drain policy below. Deterministic seed 0, alternative seeds recorded. |

The C11 rows are 194.4-195.0 ns near and 190.6-190.9 ns far, with an own-L2
outlier of 44.5 ns in launch 2 (`knc-characterization.md`, C11). Preserve every
launch; do not explain the outlier as a verified page-placement effect. Sampling
mapping alternatives reports sensitivity, not a confidence interval or proof of
the undisclosed hash. Controlled physical-address experiments are needed to bound
that uncertainty.

## Composition, execution and background traffic

`simulate --scale unit` runs 1-8 detailed tiles in the same full geometry with
background disabled by default; `--scale ring` enables the explicit total-active
core count and symmetric background. Each stream declares `core` and a local
`context`; reject duplicates, out-of-range contexts and more than eight detailed
cores. Missing `core` retains existing core-scale behavior. Placement and memory
maps belong to the scenario so comparisons reject mismatched maps or load levels.

One process owns a heap of `(time, phase, sequence, event)` entries and all core
and memory state. At a cycle boundary, apply completions first, step each detailed
core in stable ID order, then arbitrate new requests; this order must be specified
and tested. Each core executes its existing issue decision once per cycle.
Extract that step from `CoreSim.run` while retaining its original core-only path.
Do not run each core to completion and merge timestamps: later contention changes
when the next instruction can issue.

The current cache API returns future ready times synchronously. A contended
backend instead needs transaction handles and completion callbacks: dependent
instructions and contexts wait on the handle, while nonblocking prefetches and
other contexts proceed. Do not guess a completion timestamp and later silently
change it. Keep existing pairing, decode and scoreboard rules intact; complete
handles before testing issue eligibility. Future fills are not installed as
resident data early. Dirty writeback and fence-visible completion count toward
the result's completion envelope, not merely the last instruction's issue time.

At each background epoch, measure detailed tiles' actual offered off-core traffic
by operation and destination, including blocked demand. Generate traffic for each
unmodeled active core using the previous epoch's per-tile rate and distribution,
with fractional credit carry and deterministic phase offsets. At startup use a
declared warmup of the same detailed workload; warmup is simulated and excluded
from the measured interval. End background injection at the measured region's
last detailed issue, then drain its previously admitted traffic together with
detailed writes. The stopping policy and remaining background work are reported.
Check epoch and warmup sensitivity before treating a run as steady state.

Background is synthetic offered traffic, not 52 instruction simulations or
computed extra completed work. Use disjoint addresses preserving the declared
TD/channel distribution; background changes contention but cannot supply or
overwrite detailed functional data. It consumes ring/TD/channel resources and
bounded injection credits just like detailed traffic. Feedback from the prior
epoch is an explicit approximation; it may oscillate or miss heterogeneous phases.
Return that limitation and stability diagnostics. Asymmetric communication,
locks, and barriers cannot use the symmetry extrapolation.

Report detailed useful bytes divided by the detailed completion envelope, plus
separately labeled full-card extrapolation from representative per-core useful
work. The latter is a symmetry estimate under simulated full load, not an isolated
one-core rate multiplied by 60. Also report physical controller bytes, queue waits,
source counts and synthetic background bytes so the extrapolation is auditable.

Cycle stepping costs O(N * cycles); ring/TD/channel events cost O(E log Q) and
memory O(Q + resident lines). Sparse queues avoid a card-size memory image. Skip
idle spans only when the next event/issue opportunity is known and skipped stall
counters remain equivalent. Set instruction, event, cycle and wall-time budgets;
exhaustion returns `budget_exhausted` with partial diagnostics, never a prediction.
Use standard-library Python 3.8-compatible code and `heapq`, suitable for PyPy.
No thread pool; scenario-level `--jobs` is brief 02's responsibility.

## Results and validation contract

Capabilities must distinguish simulated `unit`/`ring`, synthetic background and
analytical `pair`/`card`. Existing analytical scales and their numeric behavior
remain unchanged. `analytic-scales.md` currently contains older bandwidth prose;
use current profile entries, not that prose, for comparisons. Compare identical
work, traffic accounting, placement and context count; differences are findings,
not a reason to force the simulation to equal the formula.

Every new result is `unvalidated_scenario_estimate`, even if the core shape was
validated, and includes assumptions, unsupported forms, parameters used,
limiting constraints and calibration status. Promotion needs both scaling and
full-card bandwidth validation for the actual multi-core shape, plus resolved
assumed-parameter policy under `calibration.md`; a passing unit test is insufficient.

Freeze the model before comparisons, identify its commit, and retain ordinary
prediction results. Do not create extra hashes, receipts or provenance files.
Previously inspected historical targets are retrospective checks, not newly
blind predictions. Parameters and rules learned from any row exclude that row
from held-out statistics. In particular the S11-06 sweep winners already calibrate
the card profile; reproducing them cannot satisfy independent validation.

| Evidence group | Treatment and predeclared check |
|---|---|
| S6-03 local/memory latency and per-core service | Calibration anchors inherited unchanged. Core-only regression verifies no change of the existing model. |
| S8-10 C11 near/far remote-L2 | Calibration if the 192 ns residual is used. Otherwise retrospective comparison only after recording predictions. Target per-row error <=10%, retain launch ranges separately; no claim that logical near/far proves physical distance. New controlled rows are needed for independent latency validation. |
| S11-05/S11-06 1/2/4/8-core STREAM scaling | Locate exact logs, core placement, sibling count, page backing, prefetch and completion metric before importing. Run background off with matching detailed placements. Target each comparable row within 10%; missing rows stay pending, never interpolate a measured scaling curve. The brief names sweeps, but exact low-core-count rows have not been established in Phase 1. |
| S11-06 full-card read/RMW/NGO winners | Calibration regression only: 186.14/179.39/169.74 GB/s useful bytes, different winning configurations (`knc-machine.yaml: stream_sweep2_bandwidth`). Never count these as held out. |
| S11-06 triad | 168.23 GB/s winner, 163.70 baseline, same machine file's named rows. Retrospective target <=10% with matching store form and completion timing. Using either to adjust write cost removes it from independent validation. |
| `stream-*-card`, `gemv-fp32-card` | Keep current analytical cases and predictions intact. Add separately named simulated cases only with actual stream kernels and inputs. Their existing L1 stand-in `core.s` loops are not faithful multi-core validation kernels. Read baseline is 147.238707 GB/s at 60 threads/small pages, not the 186.14 sweep winner. |
| S11-09 fp32 GEMV | Reported 125.30 GB/s weight bytes only, 120 threads/small pages (`knc-machine.yaml: gemv_weight_bandwidth`). Preserve that byte definition, vector/reduction traffic and timed scope. Target <=10% median error; retain observed spread and reference drift separately, not as a widened tolerance. |
| C11 barriers, S9 libgomp, M4 OpenMP scaling | C11 tree 5521-6469 ns and counter 26810-28410 ns are custom barriers. They remain analytical synchronization inputs for matching protocols, not simulated libgomp validation. `knc-machine.yaml: openmp_barrier_cost` is null. Do not substitute 6 us for libgomp or infer its scaling. M4 rows need matching binaries, placement, timed regions and runtime before use. |

List all misses in `validation.md` with their mechanism hypothesis and request;
do not widen the 10% engineering target after observing a miss. These targets
are proposed acceptance bands, not achieved accuracy. Independent held-out rows
and the lead's shape approval remain necessary for a calibrated result.

Phase 2 starts with a failing test commit and, for this deep ticket, the `red`
handoff required by AGENTS.md. At most two new test files: one for deterministic
ring/protocol/conservation tests and one for multi-core CLI/scaling integration.
Test shortest routes in both directions, link contention, independent channels,
all 64 TDs, invalidations, writeback/RFO/no-read accounting, delayed visibility,
request completion and budget failure. Include 2/4/8-tile stream runs and a
one-tile equivalence case. Hardware comparisons belong to the evidence harness,
with errors reported separately from model-invariant tests. Run the requested
selftest and `tests/regress/test_knc_twin.py` once after implementation; long
validation waits for lead confirmation that timed card work is idle.

## Native requests after M4

Phase 2 will add the following IDs to `calibration-plan.json` and generate
requests with `prepare-native` under `.work/_shared/S14-13/native/<id>/`.
These are planned destinations, **not staged or executed requests**.

| ID | Experiment and parameter isolated |
|---|---|
| `multicore-ring-distance` | Same physical line with controlled owners/requesters at candidate distances 1,15,30; repeated addresses/allocations and core pairs; report actual placement uncertainty. Measure loaded and unloaded latency to separate hop, TD and endpoint contributions. |
| `multicore-channel-saturation` | 1,2,4,8,16,30,60 active cores, fixed siblings and page mode; inferred single-channel address sets versus balanced sets. Record mapping uncertainty; measure queue growth and completed line rate, not a nominal per-channel roof. |
| `multicore-td-contention` | Disjoint missing lines mapped to a candidate common TD versus dispersed TDs, keeping channel load matched. Set membership is a hypothesis unless independently verified. Separates TD initiation interval from lookup latency. |
| `multicore-remote-write` | Exclusive, clean-shared and dirty-owner line handoffs; ordinary partial/full stores versus full-line no-read stores; publication timing included. Measures RFO, invalidate/ack and writeback cost. |
| `multicore-ring-mixed` | Matched read/write traffic and remote-only traffic, with independent destination placements; tests combined versus separate fabric budgets and write/read service ratio. |
| `multicore-symmetry` | Matched 1/2/4/8 and full-card STREAM configurations, plus fixed background-load levels; measures the feedback approximation and channel balance. Keep a separate prospective GEMV/STREAM run reserved for validation, never calibration. |

The present `prepare-native` driver supports at most four contexts and checks
them serially before timing (`scripts/knc_model/native.py`). It cannot yet express
60-core saturation or concurrent handoff correctness. Extend it in Phase 2 to
carry explicit placement, cooperative phases, a shared completion envelope and
all CPUs from `sched_getaffinity` for long checks. Do not stage a four-context
request and claim it measures 60-core saturation. Unsupported lock/fence costs
remain explicit. Requests retain calibration versus validation roles; the lead
builds/runs them in coordinated card time. No card launch is authorized here.

## Review required before implementation

Approve or revise the contracted 61-position ring with **64 TD slices**, the
52-background default for 60 usable cores (53 only for 61 active), the causal
asynchronous memory interface and symmetry policy, and the calibration/held-out
split. Identify available low-core scaling logs and independent full-card rows;
the existing calibration winners cannot satisfy both roles. Confirm the proposed
10% per-row engineering targets and when long host validation is allowed.
Native request generation and the implementation/tests remain Phase 2 work.
