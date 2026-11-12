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
last finishing worker. Initialization and full validation are outside the timed
region. A final barrier prevents validation overlapping the next sample.
Output is JSON Lines with median/min/max decimal GB/s and the selected CPU list.
`sweep.sh` adds `CASE` command lines and `METADATA` blocks. Filter JSON result
records when analyzing; keep surrounding case/config records to retain context.
These are STREAM-style byte counts, not a submission to the official STREAM list.

## Native inner-loop instruction budget

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
paths rather than assigning these default counts to them. The per-pass fence,
chunk dispatch and thread synchronization remain inside the measured interval.

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
