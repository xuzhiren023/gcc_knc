# S6-02 M2 kernels

This lead-reviewed acceptance fixture supplies seven kernels, three implementations
of each, a bitwise correctness gate, and the ADR-0010 timing driver. Native results
are pending the lead's card jobs. Host compilation is not native correctness.
The original red commit is `70bcf0a`; its host copy stand-in was approved in S6-02.
Only this ticket's new fixture is changed.

## Build and correctness

From the worktree root, run:

```text
python tools/run.py --name S6-02-suite-build --inputs tests/acceptance/m2_kernels -- python tests/acceptance/m2_kernels/build.py all
```

The script uses the shared GCC 16 compiler and sysroot, compiles the C sources
with `-O2 -march=knc -ffp-contract=fast -Wall -Wextra -Werror`, assembles **every**
object with donor binutils 2.22 `--march=k1om`, links with pthreads/librt, and
runs `tools/knc_lint` on both complete executables. It overwrites outputs in
`.work/_shared/S6-02/`; it neither rebuilds GCC nor runs a card program.

- `m2-kernels.mic`: the real suite. `--correctness` (also the default) must exit 0.
- `m2-negative.mic`: the identical suite with the driver compiled using
  `-DNEGATIVE_CONTROL`. Only the FP32 affine IMCI function is replaced by
  `negative.s`, which copies x and omits multiply/add. Expected exit 1,
  `correctness kernel=affine_f32 builds=3 failing_cases=154`; the other six
  kernels must report zero. No benchmark proceeds when the gate fails.

The lead stages these binaries, runs negative then positive correctness, and
only after those results are as expected schedules exclusive `card_run
--benchmark` jobs. Engineers do not start card jobs. Exit codes are 0 for
successful correctness/within-launch timing, 1 for a numerical/guard mismatch,
2 for invalid arguments or infrastructure errors, and 3 for timing noise or
excluded density 3. Timing exit 0 does **not** establish cross-launch stability.

## Implementations and data

All entry points have separate symbols, restrict-qualified pointer arguments,
and no scalar FP argument ABI dependency. Array allocations, initial input and
output pointers, and parameter blocks are 64-byte aligned. The `.s` references
are hand-written IMCI, with no intrinsics or opaque bytes. Affine (including
short) and matrix multiply-adds use `vfmadd213ps/pd` and `vfmadd231ps`, respectively,
matching the GCC kernel build's permitted contraction (`-ffp-contract=fast`,
GCC's default). The independent oracle retains `-ffp-contract=off`.
`kernels.c` is compiled twice: `BUILD=gcc` enables `-ftree-vectorize`, while
`BUILD=x87` disables both loop and SLP vectorization. The scalar checker and
timing code also disable both. The name `gcc` denotes this vector-enabled build;
it does not assert that GCC successfully vectorizes every loop.

Affine and stencil main loops process four independent vectors per iteration
to expose four arithmetic chains for one thread (ADR-0009 point 3). Full aligned
vectors use unmasked aligned moves; the remainder mask is computed once per
function call, and only the final partial vector uses it. Short calls use
unpack/pack moves because chunk starts need not be aligned. Stencil neighbor
loads likewise need unpack moves. The 8x8 matrix uses a constant eight-lane
store mask for complete outputs (each is half a vector), plus the once-computed
remainder mask for its final partial output; 16x16 full stores are unmasked.

The affine and 1-D stencil bulk loops prefetch each of four input cache lines
256 bytes ahead with `vprefetch0` (L1) and 2048 bytes ahead with `vprefetch1`
(L2). Short calls and matrix input-vector iterations prefetch one line at those
same distances. The 2-D stencil prefetches the next output row's center/south
lines at +384/+768 bytes to L1, and row +8 with its north/south neighbors at
+2688/+3072/+3456 bytes to L2, for each of the four column-vector offsets.
These fixed distances also apply to cache-sized inputs; they are initial
reference choices, not card-tuned performance claims. Prefetch hints near the
end can extend past the allocation, but all demand loads stay within the
initialized padding. No output prefetch or streaming-store assumption is used.

| Kernel | Operation / layout |
|---|---|
| `affine_f32`, `affine_f64` | M1 shapes: `y[i] = a*x[i]+b`, with runtime a/b loaded through a parameter pointer. |
| `stencil1` | FP32 `(x[i-1]+x[i])+x[i+1]`, initialized halos, n output points. |
| `stencil2` | FP32 `(((north+west)+center)+east)+south`, 64 output columns, input pitch 96, 16 floats of padding on each side and a top/bottom halo row. Final output row may be partial. |
| `short` | FP32 affine in separate variable-length calls of 1..64 elements. `--short-length` defaults to 17. The driver walks the complete n-element working set in chunks, with a shorter final call. Subcalls may be unaligned; every build gets identical chunks and dispatch overhead. |
| `mat8`, `mat16` | Fixed 8x8 / 16x16 FP32 matrix times a stream of input vectors, n output elements. Matrix storage is column-major with leading dimension 16; each input vector occupies 16 floats. The fixed matrix is reused. A final incomplete output vector computes just its requested rows. |

The matrix kernels sum columns from 0 upwards, starting at +0. IMCI parallelizes
independent rows without reassociation. The stencils are one out-of-place sweep,
not an iterative PDE solver. Inputs and coefficients are read-only; outputs do
not feed the next repetition. One element of work means one scalar output,
including for matrix kernels; their operation counts differ from affine.

Correctness uses an independent scalar oracle, two deterministic signed datasets,
all lengths 0..64, and 255, 256, 257, 336, 512, 1023, 1024, 1025, 4096, 5456,
8192, 16384 and 262144. Each output is compared bit-for-bit, and 16 sentinel
elements on either side are checked after **each** build. Outputs are reset
between builds. Short checks exercise every call length 1..64 and the selected
chunk length over the larger working sets. Large padded input regions and halo
values are initialized, including inactive IMCI tail lanes.

Inputs are quarter integers in [-15.75,15.75], affine a=2 and b=0.5, and matrix
coefficients are quarter integers in [-2,2]. Every intermediate and final value
is exactly representable in FP32 (and FP64): matrix partial sums have at most
16 terms, each a multiple of 1/16, with absolute sum <=504. No tolerance is
used. Separate multiply/add and fused multiply-add are bitwise equal for these
exactly representable inputs and intermediate results. This deliberately
establishes identical FP results despite contraction and x87 extended
precision; it is not a claim about arbitrary inexact/exceptional inputs or
changed FP modes. No fast-math flags are enabled.

## Timing jobs

A single job measures all three builds for one kernel/configuration. These are
**program arguments for the lead's exclusive benchmark job**, not permission to
run them directly:

```text
m2-kernels.mic --benchmark --kernel affine_f32 --working-set L2 --density 4 --cores 60 --launch 1
m2-kernels.mic --benchmark --kernel affine_f32 --length 17 --density 4 --cores 60 --launch 2
m2-kernels.mic --benchmark --kernel short --working-set memory --density 2 --cores 1 --launch 3 --short-length 17
```

Use five independent launches numbered 1..5 for each identical configuration
(ADR-0010 amendment 1). Since 2026-11-06 the three builds are **interleaved**: every
round of a group runs each build once, the starting build rotates with the round,
and even launches rotate the other way. The driver checks the entire correctness suite before measuring. The lead must
still run the separate correctness jobs first. Stage files before the benchmark
window, retain complete stdout/stderr and job exit status, and coordinate windows
with PhiWeather through the lead, as required by ADR-0010.

The comparison matrix uses all seven kernels, 1 and 60 cores, densities 1, 2,
and 4, and the explicit ADR boundary lengths:

```text
15 16 17 255 256 257 1023 1024 1025 4096 16384 262144
```

Also run `--working-set L1`, `L2`, and `memory` for each configuration. For short
loops, additionally sweep `--length N --short-length N` for N=1..64; the larger
working sets use the declared chunk length (17 by default). Density 3 is supported
for diagnostic jobs but is always marked noncomparable and exits 3, per ADR-0010.

Working-set selection starts with S6-01's per-worker rows:

| Density | L1 | L2 | Memory |
|---|---:|---:|---:|
| 1 | 1024 | 16384 | 262144 |
| 2 | 512 | 8192 | 262144 |
| 3 (diagnostic) | 336 | 5456 | 262144 |
| 4 | 256 | 4096 | 262144 |

For L1/L2, reduce length in multiples of 16 as needed to fit 12 KiB / 192 KiB
**per core**, counting all siblings, input padding/halos, output guards and
coefficients. This matters for FP64 and matrices. The driver prints the resulting
length and exact allocated data bytes per worker/core. These are conservative
capacity budgets, not proven cache residency; allocator/thread/stack overhead
is not included. Memory length stays 262144: even the 1-core case exceeds that
core's L2, and 60-core jobs exceed aggregate card L2. Explicit `--length` rows
are labelled `boundary`, without a cache-residency claim.

Workers are `core*density+sibling`, pinned to sorted cpuinfo siblings of cores
0..cores-1, with OS CPUs 0,241,242,243 excluded. Each worker checks its own
singleton affinity and current CPU before/after every batch and performs its
own first touch. The controller shares core 0's first sibling and waits at
barriers during computation. Each worker records RAW wall start/end; global
makespan is latest end minus earliest start. TSC subtraction is **only within
worker 0**, serialized with CPUID, and is diagnostic. Clocksource and power
policy are recorded at both endpoints.

A growing pilot estimates repetitions for about 100 ms per batch (minimum one
sweep) for each build, re-sized until a check batch is 50-200 ms. A global warm-up
of `--warmup-seconds` (default 10, 0..60) interleaved rounds follows: the slow
regime seen in the first seconds after the threads start ended 6.2-6.9 s into the
first build in every large step of the 2026-11-06 blocks
(`docs/research/m2-noise-diagnosis.md`). Then five groups of three warm-up and 21
timed rounds, each round running every build once. Every pilot, warm-up and timed
sample is printed. The per-build figure is the median of its five group medians.
The launch is valid (`paired_ok=1`, exit 0) when every build's batches are sized
and the gain fraction computed from **same-group** medians agrees across the five
groups within 2% (when the IMCI denominator is not positive in some group, the
gcc/imci time ratio is used instead). Per-build group spreads are still printed
with `within_launch_ok` but no longer decide the exit code. No extra samples are
added to rescue a noisy result.

## Output and M2 arithmetic

Each measurement is one `sample` line with key=value fields:

```text
sample kernel=affine_f32 build=gcc length=N threads_per_core=D cores=C cycles_per_element=... repetitions=R wall_ns=... ns_per_element=... phase=timed group=G sample=S launch=L working_set=L2 short_length=17
```

`cycles_per_element` is serialized **worker-0 TSC ticks / (N*R)**, not verified
core cycles and not a cross-core time. It meets the requested diagnostic field;
M2 calculations use `wall_ns` and `ns_per_element = wall_ns/(N*C*D*R)` only.
Straggler diagnostics follow on the same line: `t_ms` (RAW time since program
start), `max_worker`/`max_ns` (the worker with the longest own start-to-end time),
`median_ns` (median worker time), `skew_ns` (last start minus first start), and
from `getrusage(RUSAGE_THREAD)` the involuntary context switches summed over
workers (`nivcsw`), the largest per worker (`nivcsw_max`, `nivcsw_worker`) and the
summed system time (`stime_us`). Global warm-up samples have `group=-1`. Each group
also prints a `pair` line (same-group `gcc_over_x87`, `imci_over_x87`,
`gcc_over_imci`, `gain_fraction`), and the launch ends with a `launch` line
(`gain_fraction` from the launch figures, `gain_fraction_spread`,
`gcc_over_imci_spread`, `gcc_over_x87_max` over groups, `sized`, `paired_ok`).
Placement, policy, configuration, correctness, group min/median/max and summary
records have distinct prefixes. No example above is measured evidence.

For each build/configuration take the normalized median-of-group-medians from
its `summary` line in each of five independent launches. Require `paired_ok=1`
on the `launch` line, density !=3, successful job exits and identical inputs/work;
M2's two conditions must hold in every launch (ADR-0010 amendment 1), and the
range across launches is reported. Retain all samples even when a gate fails.
T_build is the launch figure:

```text
speedup_build = T_x87 / T_build
gain_fraction = (T_x87/T_gcc - 1) / (T_x87/T_imci - 1)
```

A zero or negative IMCI gain denominator is not a valid M2 yardstick; report it
rather than treating a quotient as a pass. At L2, 60 cores, density 4, FP32 affine
needs `gain_fraction >= 0.5`. Also require `T_gcc <= 1.05*T_x87` at **every** tested
FP32 affine length, including boundary and working-set rows at 1 and 60 cores.
Do not pool lengths, short chunk sizes, densities, cores or working-set labels,
or compare raw batch times when repetitions differ. No M2 pass can be reported
until the complete required matrix and independent-launch noise gates exist.
