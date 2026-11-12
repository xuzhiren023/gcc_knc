# S11-05 memory bandwidth experiment

Lead execution only. `membw.c` is original C with IMCI inline assembly; the host
path emulates vector operations and store hints for correctness, not performance.
No ICC headers or implementations are used. Research and decision criteria are in
`docs/research/knc-memory-bandwidth.md`.

## Build and test

From the ticket worktree, on the host:

```text
python tools/run.py --name S11-05-host --inputs tests/bench/membw -- python tests/bench/membw/test_membw.py
python tools/run.py --name S11-05-k1om-final --inputs tests/bench/membw tools/knc_lint -- python tests/bench/membw/build.py
```

The build script uses this lane's existing GCC-KNC `xgcc` with its `-B` prefix and
card sysroot. It never builds GCC. Auto-vectorization and automatic software
prefetch are disabled so they cannot override the explicit kernels/hints; vector
arithmetic remains IMCI. Staging is `.work/_shared/S11-05/{membw.mic,sweep.sh}`.
The binary is dynamically linked to the existing card C/pthread/rt runtime.

## Exact lead commands

These commands are from a worktree under `.work`, hence `../_shared`:

```text
python tools/card_run --benchmark --threads 240 --timeout 120 --file ../_shared/S11-05/membw.mic ../_shared/S11-05/sweep.sh probe
python tools/card_run --benchmark --threads 240 --timeout 6600 --file ../_shared/S11-05/membw.mic ../_shared/S11-05/sweep.sh first
python tools/card_run --benchmark --threads 240 --timeout 600 --file ../_shared/S11-05/membw.mic ../_shared/S11-05/sweep.sh confirm --threads 60 --pages huge --pf0 8 --pf1 64 --offset-lines 62
python tools/card_run --benchmark --threads 240 --timeout 5340 --file ../_shared/S11-05/membw.mic ../_shared/S11-05/sweep.sh second
python tools/card_run --benchmark --threads 240 --timeout 5340 --file ../_shared/S11-05/membw.mic ../_shared/S11-05/sweep.sh third
```

The confirmation configuration is an example: replace it with the winning
combination, separately by workload if winners differ. `probe` is read-only and
prints PMU availability and metadata. It must not be mistaken for a timing run.
Each native invocation has a 90-second alarm including initialization/validation;
it covers all requested workloads together. The two serial first-touch cases
run triad only (five initializations each, rather than thirty across six classes).
They retain 256 MiB per array, eight timed passes and the 90-second process bound.
the runner stops on failure, timeout, or invalid output. `card_run` supplies the
exclusive window and outer timeout. The sweep chmods only its staged binary.

## Controls

Every option takes a value; last occurrence wins.

| Option | Values/default | Meaning |
|---|---|---|
| `--workload` | all/read/write/copy/triad/rmw/stencil; all | Run separately; never aggregate classes |
| `--threads` | 0 (all allowed), or positive subset | One worker per selected allowed CPU; never escape `sched_getaffinity` |
| `--placement` | compact/spread/reverse; spread | Ascending CPU IDs, first sibling on each core before next siblings, descending IDs; native topology from sysfs |
| `--mib` | 1..2048; 256 | MiB **per array**; three arrays plus halos/padding |
| `--passes` | 1..1024; 8 | Full-array passes per timed sample |
| `--repeats` | odd 5..101; 5 | Independent initialized/validated samples |
| `--prefetch` | none/shared/exclusive/l2; shared | No hints; shared 0/1; exclusive on RMW and normal-store output; shared 0/2 |
| `--pf0`, `--pf1` | 0..4096; 16,32 | Distances in cache lines; 0 disables that level; hints stay inside arrays |
| `--store` | normal/nr/ngo; ngo | `vmovaps`/`vmovnraps`/`vmovnrngoaps`; read-only unaffected |
| `--fence` | end/chunk/line; end | Always a locked-add completion fence per pass; optional extra fences per chunk or line |
| `--evict` | none/l1/l2/both; none | `clevict0/1` after output stores; no effect on read-only |
| `--pages` | small/huge; small | Anonymous pages with THP disabled when supported, or verified hugetlbfs mount at `/mnt/huge` |
| `--offset-lines` | 0..32768; 0 | Extra relative displacement between consecutive arrays |
| `--padding-lines` | 0..32768; 0 | Extra gap after each array's halo; distinguish base displacement from logical length |
| `--chunk-lines` | 1..1048576; 4096 | Chunk/block size; stencil retains contiguous traversal within chunks |
| `--schedule` | block/cyclic; block | Contiguous worker partitions, or round-robin chunks |
| `--unroll` | 1/2/4/8; 4 | Explicit source expansion; operation/store/prefetch/fence/eviction modes dispatched outside the line loop |
| `--split` | 0/1; 0 | Split triad within each chunk using output as a temporary; other classes unchanged |
| `--first-touch` | parallel/serial; parallel | Workers or worker zero initialize arrays outside timing |
| `--pass-fence` | each/final; each | Completion per pass, or only after the last pass; RMW and split triad always retain per-pass completion; chunk/line fences still apply |
| `--read-chains` | 0/1/4; 0 | Original read kernel, private single accumulator, or four independent accumulators; private paths group four lines regardless of `--unroll` |
| `--probe` | 1 | Standalone perf syscall capability probe; no memory benchmark |

On Linux, huge allocation checks the filesystem type and faults one byte per
huge page before workers exist, catching allocation SIGBUS and falling back to
small pages. This supports old hugetlbfs without `fallocate`. The config record
reports the actual allocation choice. A fallback is a small-page result, never a
huge-page result. Huge physical-page prefault is serial, so `--first-touch` there
changes cache initialization ownership, not which CPU initially faults the page.
The small-page case measures actual parallel/serial first touch on the first
sample. Later samples retain the mappings; they measure steady state.

## Kernels, timing, validation and counting

Float arrays are cache-line aligned. Distinct index-dependent integer-valued
initial data makes the reference computations exact. The fixed-point reduction
in the read case sums float bit patterns modulo 2^32 per lane; it validates all
loaded lines without float reduction precision loss. All other kernels check
every output and check that input arrays were preserved. RMW changes its input
by one per pass, so validation detects omitted passes. No sampling-only checks.

| Class | Operation | Logical bytes per element per pass |
|---|---|---:|
| read | Read input into a validated register reduction | 4 |
| write | Fill output with 7 | 4 |
| copy | Copy input into output | 8 |
| triad | Output = input A + 2 * input B | 12 |
| rmw | A += 1 | 8 |
| stencil | Output = A[i-16] + A[i] + A[i+16], with fixed halo lines | 16 |

The stencil is a three-row, 16-float-wide vertical stencil-like pattern. It
counts the three logical reads, including reuse; it is not a claim of four
distinct DRAM transfers. Split triad still reports 12 useful bytes but also
reports five implementation streams (20 bytes) rather than three. Do not call
either logical result a memory-controller measurement.

Five or more synchronized samples include all passes, completion fences and the
last finishing worker. S11-06 measures the envelope from the earliest worker
start to the latest worker completion, after the completion fence and before the
ending barrier. It includes worker start skew, chunk dispatch and loop overhead.
Initialization and full validation are outside that envelope. The old worker-zero
wall interval is retained in each sample's `timings.wall_seconds` for comparison;
it includes both timed barriers and may include other workers starting validation
before worker zero obtains its timestamp. `timings.seconds` is the envelope used
for bandwidth; `start_skew_seconds` is latest minus earliest worker start. Raw
samples remain in acquisition order; min/median/max rates are sorted separately.
A final barrier prevents validation overlapping the next sample.
Output is JSON Lines with median/min/max decimal GB/s and the selected CPU list.
`sweep.sh` adds `CASE` command lines and `METADATA` blocks. Filter JSON result
records when analyzing; keep surrounding case/config records to retain context.
These are STREAM-style byte counts, not a submission to the official STREAM list.

## S11-05 native inner-loop instruction budget

Counted from the staged k1om binary's disassembly after the review fixes, with
the default `--unroll 4 --prefetch shared --pf0 16 --pf1 32 --store ngo
--fence end --evict none --split 0`. Counts follow the executed steady-state
path, including branches and loop control, excluding entry/exit and array tails.
`../_shared/S11-05/membw.dis` contains the two inspected functions.

| Workload / symbol | Executed instructions per four lines | Per line | Logical bytes per four lines |
|---|---:|---:|---:|
| write / `kernel_WRITE_2_1_0_0` | 14: 4 stores + 10 scalar/control | 3.5 | 256 |
| triad / `kernel_TRIAD_2_1_0_0` | 53: 16 prefetches + 8 loads + 8 adds + 4 stores + 17 scalar/control | 13.25 | 768 |

For this binary, the write back edge is `0x426c06 -> 0x426bd0`; all 14
instructions on that path execute at unroll four. The triad back edge is
`0x48e8ee -> 0x48e6d0`: follow through `0x48e7cf`, whose taken branch skips
the unroll-eight body to `0x48e8d0`. That path executes 53 instructions.
Addresses can change on rebuild; the symbols and branch paths identify the
loops. These are static instruction counts, not measured cycles or bandwidth.

Configuration and array pointers are snapshotted at chunk entry. The generated
variants select operation, store, prefetch mode, line fence and eviction before
the line loop. Load/store/prefetch/eviction assembly names its exact 64-byte
memory operand; only the completion fence has a full memory clobber. The write
constant is loaded into a vector register before the loop, with no scalar
construction or stack traffic per line. The triad loop has one stack-resident
end-bound comparison per four lines, but no global configuration/pointer loads,
vector spills, or per-line mode tests. Unroll selection costs remain included.

With both prefetch distances nonzero, a separate bulk loop omits bounds checks;
the tail checks each hint, preserving the in-array rule. Disabling either
distance uses the checked path. Short chunks, tails, split triad, fences and
eviction variants have different costs. Compare those results using their own
paths rather than assigning these default counts to them. The completion fences
and chunk dispatch remain inside the measured interval. S11-06 reports barrier
overhead separately, as described above.

## First-pass budget and interpretation

| Step | Cases | Conservative bound, 90 seconds/case |
|---|---:|---:|
| Store kind, density, pages | 8 | 12 min |
| Prefetch | 6 | 9 min |
| Relative offsets and placement | 7 | 10.5 min |
| Splitting/chunking (all classes), first touch (triad only) | 4 + 2 | 6 + 3 min |
| Unroll, eviction, fences, far hint | 7 | 10.5 min |
| Core scaling and closing reference | 4 | 6 min |
| Total first sweep | 38 | 57 min |

Add two minutes for the probe, six for four confirmation cases, and a planned
15-minute staging/metadata allowance: 80 minutes. The 110-minute outer timeout
also prevents an unexpectedly slow first sweep exceeding the two-hour budget.
These are planned budgets, not measured card durations. A case that hits its
alarm is incomplete, not slow-but-valid performance data.

Only the first section establishes baselines; subsequent rows start from 60
threads/huge pages to screen the space cheaply. If that base loses, use `confirm`
to retest a proposed winner against the actual best base before accepting it.
The initial sweep does not claim a full Cartesian search. Compare medians and
ranges, retain regressions, and reject comparisons contaminated by fallback,
thermal drift, a changed affinity mask or overlapping jobs.

## S11-06 second sweep: calibration before tuning

Run the `second` command above only through the lead's card allocation. It runs
58 single-workload invocations, each bounded by the existing 90-second alarm:
87 minutes maximum summed process time, plus a two-minute metadata/launch reserve.
The outer 5340-second timeout caps the job at 89 minutes; an incomplete or timed
out case is a failure, never a valid slow sample. No hardware setting changes.
Every invocation uses five fully initialized and validated samples. Long cases
use 2048 MiB per array (about 6 GiB total), 32 passes, spread placement and NGO
stores unless the CASE line overrides them. Allocation fallback remains visible.

`sh tests/bench/membw/sweep.sh second-plan` prints the exact 58 CASE commands
without touching a binary or reading card metadata. Duplicate options are
intentional: the final value wins. The host test checks expansion and the budget.

| Cases | Purpose |
|---|---|
| 1-3 | STREAM-equivalent triad: 60 threads, huge, NGO, prefetch 8/64; 256 MiB x 8, 2048 MiB x 8, 2048 MiB x 32 |
| 4-18 | Same three-size/pass calibration for read, write, copy, RMW and stencil, in that order |
| 19-24 | Long triad/read/write/copy/RMW/stencil with only the final completion fence |
| 25-42 | Per class read/write/copy/triad/RMW/stencil: 120 threads at 8/64, 120 at 32/128, 60 at 32/128 |
| 43-44 | Read: private single accumulator and four independent accumulators |
| 45-47 | Write: 240 threads NGO, 60 NR, 60 normal with exclusive prefetch |
| 48 | Copy: cyclic 1024-line chunks and L2 eviction |
| 49-50 | Triad: offset 62 plus unroll 8; split with 1024-line chunks |
| 51 | RMW: both evictions plus cyclic 1024-line chunks |
| 52 | Stencil: 128-line chunks and L1 eviction |
| 53-58 | Closing long references, fresh mappings, same order as cases 19-24 |

The per-class references retain promising first-sweep configurations: read uses
small pages and prefetch 16/32; write uses huge pages and 8/32; RMW uses huge,
16/32 and both evictions; copy/triad/stencil use huge and 8/64. Case 43/44 keep
the same read reference configuration. Private reductions preserve full modulo
2^32 validation; neither result is accepted on instruction counts alone.

Final-only fencing retains publication after all passes. Each worker owns its
written lines; stencil reads immutable input. RMW consumes its own prior output,
and split triad reuses streamed output as a normal-store temporary, so both
always retain per-pass completion even when `final` is requested. Case 23 is
therefore a repeated RMW control. No worker consumes another worker's streamed
output during the timed loop. The experiment measures intermediate completion
cost only where output is not reused, and never omits final NGO completion.

Compare the triad size/pass ladder (cases 1-3) using both
envelope and old wall rates. At 175 GB/s the longest triad sample should last
about 1.18 seconds, versus 37 ms for the shortest. Require at least 175 GB/s
completed triad before describing calibration as reproduced. If it falls short,
report the measured gap, timing/skew fraction, actual pages and reference drift;
prioritize that diagnosis over promoting small tuning gains. Do not adjust counts
or remove completion to match STREAM. This is an equivalent useful-byte kernel,
not the official STREAM implementation or a matched compiler/system experiment.

For each sample calculate `logical_bytes / wall_seconds / 1e9` and compare with
the envelope rate. Report `(wall_seconds-seconds)/wall_seconds` and
`start_skew_seconds/seconds`; no guessed overhead subtraction. Compare 2048 x 8
against 2048 x 32 to test duration at fixed footprint, and 256 x 8 against
2048 x 8 to expose size/cache/page effects. Only longer native runs can tell which
first-sweep observations survive. Keep differences below 10% provisional; wider
overlapping ranges or closing-reference drift require paired repeats even above
10%. The predicted-vs-target table and current evidence are in the research note.

## S11-06 third sweep: close the long-sample gap

Sweep 2's measured baseline and per-class results are in the research note's
final section. The benchmark binary is unchanged from the validated sweep-2
build; only the runner needs restaging. Run `third` with the exact lead command
above. `sh tests/bench/membw/sweep.sh third-plan` prints all commands without
reading metadata, touching the binary or executing a card case. The host test
checks case count, long samples, paired controls and identical closing references.

Every case uses 2048 MiB per array, 32 passes, five samples and spread placement.
Defaults remain NGO, block scheduling, 4096-line chunks, unroll four, both
prefetch levels, no output eviction and per-pass completion. Class references:
triad 60/huge/8/64, read 120/small/8/64, write 60/huge/8/32,
copy and stencil 60/huge/32/128, RMW 60/huge/16/32 with both evictions.
Distances in write's configuration do not issue prefetch with NGO stores.
Requested huge pages must be verified from each config record as before.

| Cases | Exact variation from the class reference |
|---|---|
| 1-6 | Calibration/references: triad, read, write, copy, RMW, stencil |
| 7-10, 11-14, 15-18, 19-22, 23-26 | Read, copy, triad, RMW, stencil respectively: 60 at 16/128; 60 at 32/256; 120 at 16/128; 120 at 32/256 |
| 27 | Triad 120 threads, 8/64: repeat the collapse reference |
| 28-30 | Triad 120: no prefetch; far-only 0/128; near-only 16/0 |
| 31-33 | Triad 120: small pages; cyclic scheduling at 4096; block chunks 65536 |
| 34-38 | Triad 120: L2 eviction; far T2 hint; NR stores; normal stores; offset 62 |
| 39-42 | Write 60 unroll 8; 60 chunk 65536; 240 unroll 8; 240 chunk 65536 |
| 43-46 | Write 120 unroll 8; 60 L2 eviction; 60 chunk fences; 60 cyclic chunks 1024 |
| 47-51 | RMW at 16/32: 60 no eviction; 60 L2; 120 no eviction; 120 L2; 120 both |
| 52 | Repeat case 27's triad 120-thread collapse reference |
| 53-58 | Repeat cases 1-6 exactly, with fresh allocations |

All 58 process alarms include initialization and validation: `58 * 90 = 5220`
seconds (87 minutes), plus a 120-second metadata/launch reserve. The 5340-second
outer timeout enforces an 89-minute cap; a timeout or validation failure is
incomplete, not accepted performance. The prior sweep took about 20 minutes,
but that observation does not replace the conservative bound.

Read/density comparisons use matched distances; RMW eviction comparisons hold
16/32 fixed. Compare each triad diagnostic to 27/52 and the 60-thread 1/53
references. Single-level prefetch changes both hints and checked-loop overhead;
NR/normal tests retain shared input prefetch and change only store kind. Write
unroll/chunk changes are separate, except the explicitly combined cyclic-1024
candidate. Interpret gains below 10% as provisional and check min/max, overhead,
skew, closing drift and actual pages before selecting a candidate. Sweep 3 does
not reproduce the small combined offset/unroll winner or split triad; it spends
those cases on identifying the large class-specific loss. No native gain is
claimed until the lead returns raw output.

## S11-09: weight-streaming GEMV

`--workload gemv --format fp32|int8|fp16` selects a separate workload;
`all` retains the six original streaming classes. `--columns 4096|11008`
selects the row length. `--mib` is the weight payload budget, rounded **up**
to whole rows, so `--mib 2048` always streams at least 2 GiB. The mapping
also holds the shared immutable fp32 input vector, per-row scale storage and
one fp32 output per row. It does not allocate the three STREAM arrays.

The workers, affinity, placement, page allocation/fallback, first touch,
sample envelope and completion fences are shared with the existing harness.
Block/cyclic scheduling operates on whole rows; `--chunk-lines` is rounded up
to a whole-row tile with at least `--row-streams` rows. `--row-streams 1|2|4|8`
(default 4) interleaves that many
rows, reusing each vector load across their independent accumulators. A partial
group uses single-row cleanup. `--column-block 0|N` (default 1024, positive N
must be a multiple of 16) traverses that vector window across the row tile
before the next window; zero means the full row. Smaller windows aim to retain
the vector in L1, including the 43 KiB vector at 11008 columns. `--unroll`
controls 1/2/4/8 groups of 16 columns per loop iteration.

Weights expand directly to registers using IMCI `vmovaps` with signed-byte or
half conversion, then explicit fp32 fused multiply-adds. The int8 scale is a
per-row fp32 power of two, applied after each partial reduction. The generator
includes both signs, zero, all signed-byte values and fractional normal half
values. Products and sums are exact for these inputs, permitting exact scalar
reference comparison across reduction orders. This is a finite-value bandwidth
validation, not a NaN/subnormal or arbitrary-model numerical qualification.
Every sample checks all outputs and immutable weights, scales and vector.
Initialization and the scalar reference run on the same selected workers,
outside timing. Host execution emulates conversion and vector arithmetic.

Near/far prefetch distances remain **weight cache lines per row stream**.
Hints issue once per 64 weight bytes, not once per converted vector, and may
cross into later rows but never leave the weight allocation. This matters for
int8: a 4096-column row is only 64 lines, so stopping hints at row boundaries
would disable the default far hint. Blocking can make those future lines less
immediately useful; compare full-row and blocked traversal. `shared` uses
`vprefetch0/1`; `l2` selects `vprefetch2` for the far hint. `exclusive` remains
shared for immutable weights. `store`, `evict`, `split`, `offset-lines`,
`padding-lines`, extra line/chunk fences and `read-chains` affect only the
original classes. GEMV uses ordinary scalar output stores and pass fences.

GEMV `logical_bytes` counts only `rows * columns * weight_width * passes`.
`median_GFLOPs` counts two operations per weight and equals
`median_GBs * 2 / weight_width`; conversion/scaling/reduction overhead is timed
but not counted as extra useful FLOPs. `scale_bytes` is the int8 scale footprint,
not timed DRAM traffic. Column blocking writes partial sums and reads them back:
`output_bytes_per_pass = rows * 4 * (2 * column_blocks - 1)` reports these logical
transfers. Scale reads occur per row per column block. Vector loads, scalar
horizontal-reduction stack transfers, RFO, ECC and cache reuse are excluded from
weight GB/s; this is never labelled measured GDDR controller bandwidth.

Build/test through the existing scripts:

```text
python tools/run.py --name S11-09-host --inputs tests/bench/membw -- python tests/bench/membw/test_membw.py
python tools/run.py --name S11-09-k1om --inputs tests/bench/membw tools/knc_lint -- python tests/bench/membw/build.py
```

The host test extends the existing file with format/shape validation, byte/FLOP
accounting and sweep expansion checks. It launches no card job. The lead runs:

```text
python tools/card_run --benchmark --threads 240 --timeout 5340 --file ../_shared/S11-05/membw.mic ../_shared/S11-05/sweep.sh gemv
```

`sh tests/bench/membw/sweep.sh gemv-plan` prints all 55 exact CASE commands,
without touching the binary or card metadata. Every case uses 2048 MiB of
weights (or read input), 32 passes, five samples and spread placement. Defaults
are 120 threads, small pages, 8/64 prefetch, four row streams, 1024-column blocks
and unroll four. The process alarms include initialization and validation:
`55 * 90 + 120 = 5070 seconds` (84.5 minutes including launch/metadata reserve).
The outer timeout caps the job at 89 minutes. A timeout is incomplete evidence.

| Cases | Purpose |
|---|---|
| 1-4 | Plain read at 120, 60, 180, 240 threads (2, 1, 3, 4 siblings/core on the granted 60 cores) |
| 5-9 | Read controls: 32/256, far-only 0/128, near-only 8/0, huge pages, unroll eight |
| 10-24 | Per format fp32/int8/fp16: same four densities, then 11008 columns at 120 threads |
| 25-51 | Per format: streams one/eight; 11008 columns with window 256/full; deeper, far-only and near-only hints; huge pages; unroll eight |
| 52-55 | Repeat opening read and each format's 120-thread/4096-column reference |

Every memory/prefetch/unroll setting has an earlier matched plain-read control.
Requested huge pages must be verified from `page_bytes`, and CPU lists checked
against topology. This is a screen, not a Cartesian search.

The lead completed all 55 cases with valid outputs on 2026-11-12. Raw results:
`.work/_shared/tmp/claude-next28/membw-gemv.out`. See the S11-09 section of
`docs/research/knc-memory-bandwidth.md` for measured format winners, instruction
counts, configuration corrections and candidate compiler/runtime work.
