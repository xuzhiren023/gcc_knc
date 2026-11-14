# S12-12: combined residual-gap diagnostic batch

This stages rows 4, 5, 6, 7, 9 and 10 of S12-10's **Ranked residual gaps and
bounded closure experiments** in `docs/research/knc-reference-gaps.md`.
Rows 1–3 belong to S12-06/07/08; row 8 belongs to their theme A/B work.
No compiler/runtime defaults change here. No card jobs have been run by the
engineer. Host build/lint success is not native correctness or performance.

The durable sources are `tools/s12_12/`, the staging/reading tool is
`tools/s12_12_stage.py`, and its host tests are `tests/tools/test_s12_12.py`.
The installed `.work/_shared/gcc-knc-16.2.0` driver builds each program with
`-O2 -march=knc -std=gnu11 -pthread`, warnings as errors, and the card sysroot's
libm/libdl/librt. No GCC rebuild, vendor headers, raw instruction bytes,
fast-math, or private library implementation is used. G04's explicit legal
store instructions and G07's generated assembly are diagnostic controls.

## Delivery and lead commands

Everything the lead runs is under `.work/_shared/S12-12/`: `README.md`
(this plan), `batch.sh`, `g06/run.sh`, `g04/run.sh`, `g08/run.sh`, `g05/run.sh`,
`g07/run.sh`, `g10/run.sh`, their six `diag.mic` binaries, and `src/`.
These artifacts survive deletion of the engineer worktree. The scripts use
the main repository's `tools/card_run`; set `KNC_ROOT` only if another checkout
of that runner is needed. Run from the shared Cygwin shell, with its `python3`
and cross tools on PATH. All scripts are invoked with `sh`, so Windows file
mode is immaterial.

```sh
sh .work/_shared/S12-12/batch.sh full
# Optional, only when allocator CPU-count/memory sensitivity is wanted:
sh .work/_shared/S12-12/batch.sh profiles
```

`profiles` runs the full batch and adds G10 on 3100 and 5100. To add only the
capacity checks after a completed full batch, use:

```sh
sh .work/_shared/S12-12/g10/run.sh 3100 timed
sh .work/_shared/S12-12/g10/run.sh 5100 timed
```

Do not run both batch forms for the same evidence. Jobs run sequentially;
the lead can put the separate S12-06/07/08 phase-1 commands before or after
these in its coordinated Sprint 12 window. Their time is outside this budget.

| Job | Expected card time | Execution deadline | Timing / placement |
| --- | --- | --- | --- |
| G06 inventory | <30 s | 45 s | Answer-only; one serial job/core, packable |
| G06 counter and sampling calibration | <1 min | 90 s | Exclusive benchmark; one logical CPU |
| G04 prefetch/store matrix | 1–3 min | 180 s | Exclusive benchmark; one logical CPU |
| G08 page/stride matrix | 1–3 min | 180 s | Exclusive benchmark; one logical CPU |
| G05 loaded math/string routes | <2 min | 180 s | Exclusive benchmark; one logical CPU |
| G07 controlled branch family | <1 min | 180 s | Exclusive benchmark; one logical CPU |
| G10 fresh-process allocation matrix | 3–12 min | 12 × 90 s | Exclusive; one worker, then all granted CPUs |
| G10 each optional capacity profile | 3–12 min | 12 × 90 s | Exclusive; 3100 or 5100 affinity/memory limits |

Full execution deadlines sum to 32.25 min; with both capacity profiles,
68.25 min. Allow roughly 15 min for staging/collection and metadata: target
under two hours, excluding admission waits. These are estimates, not measured
card times. A timeout is an infrastructure/incomplete-run result, never a
request to silently increase work or label it passing. Single-core cases
remain single-core even if the matrix takes over a minute. G10 creates one
worker per granted CPU for its parallel case; no long independent validation
loop is left serial there. Serial first touch is an explicitly timed control.

The exact commands are embedded in each `run.sh`. Equivalently, with `S` the
absolute staged directory and `R` the main repository:

```sh
# Packable access inventory: deliberately no --profile (that reserves all cores).
python3 "$R/tools/card_run" --threads 1 --timeout 45 "$S/g06/diag.mic" inventory
# Timed calibration; collect the raw ring for the host decoder.
python3 "$R/tools/card_run" --benchmark --profile full --threads 1 --timeout 90 \
  --collect claude-pmu-samples.bin --collect-dir "$S/results/g06/full" "$S/g06/diag.mic"
# Each serial timed family:
for job in g04 g08 g05 g07; do
  python3 "$R/tools/card_run" --benchmark --profile full --threads 1 --timeout 180 "$S/$job/diag.mic"
done
# Fresh process for EVERY cell. all uses sched_getaffinity, not a hard-coded CPU count.
for workers in 1 all; do
 for cap in 0 1 8; do
  for touch in 0 1; do
   python3 "$R/tools/card_run" --benchmark --profile full --threads 240 --timeout 90 \
     "$S/g10/diag.mic" "$cap" "$touch" "$workers"
  done
 done
done
```

The wrappers overwrite fixed `results/<gap>/<profile>/` logs and stop on
runner failure, failed correctness, missing/duplicate results or malformed
samples. `UNAVAILABLE` is retained distinctly and does not prevent unrelated
experiments. G06's native PASS means known-work/count readback succeeded;
it does **not** authorize profiling until sampling loss and perturbation are
reviewed. No summary computes a purported speedup or changes policy.

## Measurement and qualification

`card_run --benchmark` provides exclusive scheduling and rejects foreign
workloads. Its granted mask still spans the reserved cores: each serial
program narrows itself to the first granted logical CPU before measurement.
G10's `1` control does likewise, while `all` creates and pins a worker for
every granted CPU (normally 240/224/236 for full/3100/5100). The other three
siblings of a serial worker receive no benchmark work.

Every program prints original and effective affinity, topology sibling lists,
`/proc/stat` before/after, kernel, limits, memory, `CLOCK_MONOTONIC_RAW` and
the exposed clocksource. CPU frequency, governor, idle-state residency, and
the micras power interface are read when available; absent/denied files are
explicitly marked. Review per-sibling CPU-time deltas against the topology;
interrupts and OS tasks can invalidate an otherwise exclusive sample.
Missing frequency/power observability leaves a power-state qualification gap;
the lead should attach its existing card telemetry or withhold cross-run
timing conclusions. Never infer a constant clock from the model name.

Each allocation family prints addresses, byte extents, faults and raw
`/proc/self/smaps` while the relevant memory is alive. Attribute mappings by
address interval; compare `KernelPageSize`, `MMUPageSize`, `AnonHugePages`,
and available huge-page flags. A successful madvise or a requested huge page
is not proof of backing. Missing fields/ambiguous backing mean unqualified
page comparisons. Snapshots and correctness scans are outside the reported
kernel intervals; their wall cost remains in the card-run launch-to-exit time.
Keep every repetition and its ordering; three rotations expose order effects,
but are a screening diagnostic, not a statistical default-change campaign.

## G06 — access and calibration

Question: does this installed kernel expose a usable instruction/cycle pair,
and can it sample without loss or severe perturbation? Inventory records
registered PMU types, modules, permissions and exact `perf_event_open` errors.
The counting job requests generic instructions and cycles as a group, user
space only, without guessing raw event mappings. It retains ioctl/read errors,
counts, time enabled/running and elapsed wall time. Known assembly loops at
100k/200k/400k iterations execute three instructions per iteration plus setup;
the independent arithmetic result must be `3*n`. Counts must be positive,
unmultiplexed, close to `3*n` (30k setup allowance), and scale within 10%.
Failure stops PMU-dependent work, not the rest of this batch.

If counting qualifies, compare three uninstrumented loops to an instruction
sampling run, period 100k, retaining a bounded 256 KiB ring and the original
IP/lost records in `claude-pmu-samples.bin`. The host decoder rejects malformed or
unexpected layouts, reports sample/lost counts and rejects zero samples or
any recorded loss. Review roughly 12 expected samples against the counted
work and sampled/uninstrumented wall time. Treat fewer than 10 or more than
15 samples, significant unexplained count differences, or >10% perturbation
as unqualified attribution; the short three-baseline calibration may itself
be inconclusive at that threshold. No hot-PC attribution is attempted here.

Expected decisions: access denied/unsupported -> infrastructure/driver work;
bad calibration -> no trustworthy attribution; clean counts and sampling ->
a separately authorized profiling step. None changes a compiler default.
The raw-event/uncore mapping remains unqualified, so G04 never pretends its
useful bytes are measured traffic. References: S12-10 R10 (PMU 327357-001),
R11 (public Linux perf interfaces, explicitly not deployed-kernel identity).

## G04 — hints, stores, reuse

Question: are fixed-distance read hints beneficial in scalar read and update
streams, and does reduced store traffic survive immediate reuse/publication?
Sweep 0/8/16/32/64 cache-line lookahead at 32 KiB and 32 MiB, read versus
read-modify-write, three rotated repetitions. The same mapping/alignment and
initialization are reused within a size. Bounds suppress out-of-range hints.
The no-hint path retains the shared loop's runtime dispatch, so address and
hint issue costs stay visible. This tests warm initialization, not a claimed
cold-cache regime or the independent far-hint heuristic.

Matched full-line zero stores compare temporal `vmovaps`, ordered no-read
`vmovnraps`, and weakly ordered no-read `vmovnrngoaps`. All variants include
the KNC locked-add publication fence; report fenced write time and immediate
readback separately. These aligned, disjoint, whole-line destinations make
the no-read variants legal. No cross-core publication claim is made.
Independent sum/element checks validate stream outputs and every stored word.
Instruction interface reference: ISA 327364, VMOVNRAPS/VMOVNRNGOAPS;
existing `tools/storent.py` supplies the repository's fencing convention.

Expected decisions: a robust distance/reuse-dependent benefit motivates a
broader compiler-prefetch/store profitability experiment; a flat or reversed
result leaves defaults unchanged. Store throughput without reuse benefit
does not justify a universal streaming-store default. Without qualified PMU
traffic events, this is latency/useful-work evidence only. No extra profiles:
one core and <=32 MiB do not exercise capacity limits.

## G08 — actual backing and translation versus cache conflicts

Question: does a latency knee follow page count/backing rather than same-set
cache pressure? Request anonymous memory with NOHUGEPAGE advice and explicit
MAP_HUGETLB, retaining errno and mapping evidence. Touch each 4 MiB mapping
before timing. Sweep 16/32/64/128/256/512 nodes independently of 4/8 KiB stride;
each cell has either fixed page offset or a distributed `(i*17)%64` cache-line
offset. A 73-step permutation forms one full cycle, independently checked
against node addresses. Timed dependent pointer chasing returns to its start.
Three repetitions retain the same mapping. Failures to allocate explicit
huge pages are `UNAVAILABLE`, never silently replaced with small pages.

Only compare small/large timings after confirming actual 4 KiB/2 MiB backing
for the address ranges in smaps. Distributed offsets remove the known fixed
offset L1-conflict mistake; they do not prove physical coloring or isolate
all cache effects. A knee that persists with distributed offsets and shifts
with verified backing supports translation work; a fixed-offset-only effect
supports cache-set investigation. Neither alone changes the 256 KiB compiler
heuristic. A runtime huge-page recommendation needs representative programs
and memory cost evidence. This is row 6 only; no S12-08 pairing/pressure work
is duplicated. Small absolute memory and one worker need no capacity profile.

## G05 — installed log/copy/set paths

Question: which objects/symbol addresses are actually used, and how much
steady cost is inside those calls versus a same-ABI identity-call control?
Print glibc version, dladdr resolution and loaded mappings before timing;
retain function and object-base addresses for later object-relative analysis.
Use volatile function pointers so no builtin expansion substitutes another
path. Sweep log inputs over [0.5,1.5), and copy/set 16 B through 4 MiB with
aligned and +1 byte offsets, three repetitions. Each copy/set has a bounded
total byte budget. Process setup/metadata stays outside steady intervals;
runner wall time includes it. The identity bridge is a diagnostic lower-cost
control, not an exact removable fraction of EP's cost.

Independent checks: analytic `log(2^k)=k*ln(2)` for k=-20..20 with an explicit
eight-epsilon absolute/relative bound, domain/zero/infinity/NaN classification,
and finite minimum-normal/subnormal/maximum/near-one outputs. Log errno and
exception flags are retained without claiming a full rounding/accuracy suite.
Copies are compared to a deterministic index formula and sets to a constant,
with before/after sentinels. No replacement is proposed or qualified.

Expected decisions: expensive call bodies with confirmed routes motivate
runtime-source/accuracy investigation; a substantial ABI-control cost refers
back to S12-06; a repeatable size crossover could motivate a compiler stringop
threshold experiment. Mapping paths/version strings do not prove source
revision or resolve internal IFUNC/helper dispatch; that correspondence stays
open. No blanket libc/libm quality claim, extra profile, or default change.

## G07 — direct-branch family, layout and footprint

Question: how do predictability and code spread affect a fixed hot branch
family? Generated assembly gives 64 direct conditional branch sites with the
same test/increment work and one unconditional next-site jump each. Vary
target spacing (compact, 64-byte, 1024-byte) and entry offset (0/16 bytes from
a 64-byte boundary); unreachable alignment padding is never executed. The
largest function spans about 64 KiB. All variants see identical constant,
alternating and deterministic pseudo-random input arrays; three rotations
retain the fixed 256 KiB data footprint. An independent population count
checks the arithmetic result. No compiler if-conversion erases the branch.

Expected decisions: stable footprint/predictability sensitivity motivates
general layout/inlining follow-up, with controls in real programs; no clear
effect leaves heuristics unchanged. Padding can alter branch encoding length
and fetch placement together; this is a footprint/placement comparison, not
an isolated decode-width measurement. Timing alone cannot separate BTB,
direction-prediction and instruction-cache misses or assign a misprediction
penalty. No use of the incomplete KNC misprediction event. One core and fixed
small memory do not justify smaller-card profiles.

## G10 — allocation lifetimes, first touch, caps

Question: for a bounded allocation-heavy lifetime, do ambient/1/8 arena caps
change allocation/free time, page-zeroing work or retained memory? Every
cell is a fresh process. Compare one worker and all affinity CPUs, parallel
versus serial first touch, for each cap. This is a pthread-only runtime probe,
not a rerun or validation of libgomp's existing arena sweep/policy. Cap zero
preserves environment/defaults; 1 and 8 explicitly call mallopt before worker
creation. Record original arena/mmap environment, configured/online versus
allowed CPUs, limits and allocator XML. There is no libgomp override here.

Each worker allocates 128 × 16 KiB blocks (2 MiB/worker); total payload <=480
MiB plus 256 KiB stacks/worker. Record per-worker allocation, first-touch and
cross-thread-free intervals. Snapshot allocated-but-untouched, touched, and
post-free RSS/mappings/faults. Serial first touch covers the same bytes in
the same process; its explicit wall time is separate from parallel intervals.
Before cross-thread free, the receiving worker independently checks every
byte against the producer/block formula. Snapshot overhead is excluded from
the reported phases. Arenas may allocate/touch metadata during malloc; do not
claim all pre-touch pages are untouched or virtual reservations are RSS.

Expected decisions: material allocation contention versus retention trades
could justify a runtime arena-setting trial; first-touch-dominated costs
suggest initialization/locality work; small differences leave settings alone.
3100/5100 add value here because CPU count changes arena demand and enforced
memory limits differ. They emulate capacity/affinity, not those products'
clock/bandwidth. The bounded footprint does not establish maximum feasible
heap size, OOM behavior, or an optimal cap for arbitrary workloads.

## Host verification and interpretation

Host reader tests deliberately fail without the implementation, and reject
missing/duplicate/wrong/failed result markers plus truncated/malformed sample
records. Native independent checks execute only when the lead runs the jobs.
One staging pass builds and lints all six binaries and syntax-checks the
seven shell scripts. Generated G07 source and explicit G04 controls remain
in the shared directory for inspection. Do not rerun passed host checks merely
to get a second form of evidence. No native result or projected gain is
reported by staging.

Host build (shared Cygwin environment; no card launch):

```sh
python3 tools/run.py --name S12-12-stage --inputs tools/s12_12 tools/s12_12_stage.py \
  docs/research/s12-12-experiments.md -- python3 tools/s12_12_stage.py stage
python3 tools/run.py --name S12-12-reader --inputs tools/s12_12_stage.py \
  tests/tools/test_s12_12.py -- python3 tests/tools/test_s12_12.py
```
