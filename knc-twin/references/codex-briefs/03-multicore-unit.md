# Codex ticket brief: knc-twin, from one core to the smallest card unit (design first)

For the GCC-KNC lead to dispatch on a Codex lane (backend codex, depth deep, model per
`harness/policy.json`, today gpt-6-astra; the owner ruled out a Fable subagent for this).
Branch `twin/0.3` of gcc_knc, folder `knc-twin/`. Owner request 2026-11-16: grow the twin past one
core to the smallest repeating card unit, simulated (not formulas), and compose units on the ring; the
owner approved the target design below on the same day.

## What exists

One core is simulated (`scripts/knc_model/timing.py`, `cache.py`): four contexts, pairing, decode,
private L1 and L2 as set-associative LRU line tracking, DTLB, a streaming L2 prefetcher, a per-core
memory service rate (`memory.core_service_cycles_per_line`, 20 cycles per line, a four-thread
measurement). Pair and card scales (`analytic.py`, `references/analytic-scales.md`) are formulas on
measured bandwidths. Result classes: `conditional_bound`, `unvalidated_scenario_estimate`,
`calibrated_forecast`; the rules for held-out validation are in `references/calibration.md`.

## Target design (owner-approved, 2026-11-16, relayed by the GCC-KNC lead)

- **8 tiles simulated in detail, cycle by cycle.** A tile is a core (today's validated model,
  unchanged), its L1, its 512 KiB L2 slice, its ring stop and its tag-directory slice. Why 8: the
  7120 has about 60 compute cores and 8 memory controllers, about 7.5 cores per controller, so 8 busy
  tiles load each controller at the full-card ratio; 2 or 4 tiles miss the memory contention, 16 or 61
  add cost and no new effect.
- **Full 61-stop ring geometry.** The 8 tiles are placed spread around the ring so hop distances
  match the real average; shortest direction; per-hop delay and slot contention as events.
- **All 8 memory controllers (2 channels each) and all directory slices** as cheap queues and
  tables, addresses interleaved across all of them as on the card. Service rate and latency
  calibrated to the project's measured values, not the theoretical peak.
- **The other ~53 cores as statistical background traffic** on the ring and the controllers, at
  the rate of the simulated tiles (symmetry), so the full-card load is present.
- **One process per scenario** with a global event queue keeping the tiles in lockstep; `--jobs`
  parallelism across scenarios only (see brief 02); it must run under PyPy too.

Validation (held-out rules as for 0.3):
- Detailed 1/2/4/8-core runs reproduce the measured bandwidth scaling (S11-05/S11-06 sweeps).
- The extrapolated full card reproduces the measured full-card STREAM (about 186 GB/s read, 168
  triad) and the S11-09 GEMV (fp32 about 125 GB/s).
- Remote-L2 and ring latencies against the C-rows (S8-10 C11 and the S6-03/S8 rows).
- Until both bandwidth checks hold, every multi-core result is `unvalidated_scenario_estimate`.
- Parameters not yet measured or cited (hop delay, directory lookup, ring slot width, per-channel
  saturation) start as labelled estimates (`status: assumed`, with alternatives) and become
  `prepare-native` requests for after M4.

## Phase 1: the design note (`references/multicore-design.md`), before any code

The note instantiates the target design above; the points below are what it must settle.

Define the unit and the composition, each parameter sourced (R-number and page from
`docs/research/knc-references.md`, or a measured row from `docs/research/knc-machine.yaml` or
`docs/research/knc-characterization.md`; ADR-0013: facts and pages, never copied text):

1. **Unit**: a core with its L2 slice and ring stop; the distributed tag directory (TD) slice that
   owns a set of addresses (the hash is not public: state what is assumed and how a measurement can
   bound its effect); the path from the ring to a GDDR5 memory-controller channel (R01 ring and TD
   description; R08 remote-L2 latency and concurrency; the S8-10 C11 remote-L2 line time 190-195 ns
   and barrier costs in `knc-machine.yaml`).
2. **Protocol states** the unit tracks per line: local L2 hit; remote L2 hit through the TD (hop
   count both ways on the bidirectional ring, the TD lookup, the remote slice's response); memory
   fill through the TD and a controller queue; the write path (RFO vs no-read stores). Keep MESI to
   the states the project's measurements can distinguish; name what stays a formula.
3. **Ring**: bidirectional, hops counted from ring-stop positions, a per-stop occupancy and a data
   block transfer time; whether the three rings (data, address, acknowledgement) are modeled
   separately (R01) or as one bandwidth budget, and why.
4. **Memory controllers**: channels, queue per channel, service time per line derived from the
   measured sustained bandwidths (`card.sustained_bandwidth_gbs` in `profiles/card-7120-measured.json`
   and the S11-05/S11-06 sweeps); the address-to-channel interleave as an assumption with
   alternatives.
5. **Composition**: N units on the ring; each unit runs the existing core model; shared state is the
   TD slices, the ring and the controller queues; a global cycle loop or an event queue, and the cost
   model of each (Python speed matters: the one-core engine runs about 20,000 instructions per
   second).
6. **Result classes**: every multi-core number is `unvalidated_scenario_estimate` until a held-out
   case covers its shape; the formula-based `pair`/`card` scales stay as they are and are compared
   with the simulation on the same inputs.
7. **Validation plan with existing data** (held-out rules as in 0.3: predict first, never tune on a
   held-out row): remote-L2 and ring latencies (S8-10 C11 rows), single-core to multi-core bandwidth
   scaling (S11-05/S11-06 STREAM sweeps, S11-09 GEMV, `tests/heldout_native/stream-*-card`,
   `gemv-fp32-card`), libgomp barrier and spin costs (S9 tickets, S8-10 C11 barrier rows), the M4
   OpenMP builds' thread-scaling rows if usable.
8. **Missing microbenchmarks** as `prepare-native` requests for after M4: ring-distance latency
   (same line from stops at distance 1, 15, 30), controller saturation per channel (one channel's
   addresses from 1 to 60 cores), TD contention (many cores missing on lines owned by one slice),
   remote write/RFO cost, and whatever the design needs that no row gives.

The lead reviews the note before Phase 2 starts.

## Phase 2: implementation on the branch

`scripts/knc_model/multicore.py` (units, ring, TD, controllers), a `--scale unit|ring` on
`simulate` with a kernel format that places streams on cores (`streams[].core`), `capabilities`
listing what is simulated and what is a formula, tests that run 2, 4 and 8 units on the
characterization stream kernels and reproduce the documented latency and bandwidth facts, and the
held-out cases of Phase 1 step 7 under `tests/heldout_native/` with recorded predictions.

## Done when

- The design note is reviewed and its parameters are all sourced or marked assumed with alternatives.
- The simulation reproduces the held-out rows of step 7 within stated bands, with the misses listed
  as open misses in `references/validation.md`, and every multi-core result carries its class.
- The missing-microbenchmark requests are written under `.work/_shared/<ticket>/` with
  `prepare-native` and listed in `references/calibration-plan.json`.
- Host rule until the lead says M4 is done: two single-threaded processes at most, no builds, no card.
