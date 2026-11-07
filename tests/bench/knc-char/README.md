# S6-03 machine characterization

## S8-01 tuning checks (lead job list, not run by the engineer)

Build the extended corpus with:

```text
python tools/run.py --name S8-01-acceptance --inputs tests/bench/knc-char -- python tests/bench/knc-char/build.py
```

The current build writes `knc-char.mic`, `knc-char-host.exe`, `driver.s`,
`kernels.s` and `kernels.h` to `.work/_shared/S8-01/`. It reads the existing
compiler without rebuilding or modifying GCC. `check_s8.py` checks all 254 S8
point names and the output keys on the host, with inert kernels; it first
failed on the missing catalog. Host output is explicitly unmeasured.

`--check cN` selects a family; `--case NAME` selects a single point. The list
below covers the required placements. Run each line in five independent
launches, retain every sample and chronological group, and report launch
ranges in `docs/research/knc-characterization.md`. Large family selections
need long exclusive windows; the lead can split them with `--case` using the
names from `--dry-run --check cN`. No card results are supplied by this ticket.
The lead coordinates windows with PhiWeather. C3 is optional and omitted.

```text
python tools/card_run --benchmark --threads 1 --timeout 120 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 1 --check c1
python tools/card_run --benchmark --threads 4 --timeout 120 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 4 --check c1
python tools/card_run --benchmark --threads 240 --timeout 120 ../_shared/S8-01/knc-char.mic --native --cores 60 --threads 4 --check c1
python tools/card_run --benchmark --threads 1 --timeout 180 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 1 --check c2
python tools/card_run --benchmark --threads 2 --timeout 180 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 2 --check c2
python tools/card_run --benchmark --threads 4 --timeout 180 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 4 --check c2
python tools/card_run --benchmark --threads 1 --timeout 120 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 1 --check c4
python tools/card_run --benchmark --threads 4 --timeout 120 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 4 --check c4
python tools/card_run --benchmark --threads 2 --timeout 3600 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 2 --check c5
python tools/card_run --benchmark --threads 4 --timeout 3600 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 4 --check c5
python tools/card_run --benchmark --threads 1 --timeout 3600 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 1 --check c6
python tools/card_run --benchmark --threads 4 --timeout 3600 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 4 --check c6
python tools/card_run --benchmark --threads 4 --timeout 120 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 4 --check c7
python tools/card_run --benchmark --threads 1 --timeout 180 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 1 --check c9
python tools/card_run --benchmark --threads 2 --timeout 180 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 2 --check c9
python tools/card_run --benchmark --threads 1 --timeout 120 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 1 --check c10
python tools/card_run --benchmark --threads 4 --timeout 120 ../_shared/S8-01/knc-char.mic --native --cores 1 --threads 4 --check c10
```

Point names and units (each round contains 32 units):

| Check | Point names | Unit and controls |
|---|---|---|
| C1 | `c1.store.{normal,nr,ngo}` | 64-byte line; 16 MiB per core divided among siblings, write-only full unmasked lines. All variants include a final `lock addl` drain before timing ends. |
| C2 | `c2.{vector,prefetch0,prefetch1,vector_prefetch0,vector_prefetch1}` | One instruction or adjacent pair; compare the paired cost with both isolated controls, with eight independent vector chains and hot prefetch targets. |
| C4 | `c4.pages.{128,256,384,448}` | Dependent load, randomized 4 KiB page cycle; KiB per core divided exactly among siblings, including the non-power-of-two points. |
| C5 | `c5.{stream,stencil,row7,row8,row9}.l1_D.l2_D` | One 64-byte row iteration. Full Cartesian sweep L1={0,8,16,32,64}, L2={0,32,64,128}; 0 disables the hint. Distances count iterations, not bytes. |
| C6 | `c6.{x87,aligned,peel,gather}.nN` | One complete `y=x+1` invocation of N=1..33 elements. Peel starts one float off alignment and scalar-peels up to alignment; aligned and gather start aligned. Gather only handles a partial final vector, with mask replay. Include the peel alignment difference in interpretation. |
| C7 | `c7.reduce.a{1,2}` | One 16-lane reduction update, identical 32-vector input and operation counts; two-accumulator finish combines the results. |
| C9 | `c9.{vector,memory}.u{1,2,4}` | One dependent vector add update; U independent recurrence registers with U instructions per actual loop branch. Round scaling preserves 32 updates per reported round. Memory operands read the same hot line. |
| C10 | `c10.branch.{fixed,random}` | One conditional branch with balanced instruction counts on its two paths (including a common jump); fixed all-taken-direction bits versus precomputed pseudorandom bits, same load/index overhead. RNG is outside timing. Delta per branch is an effective random-branch cost, not a direct hardware miss count. |

C5 uses eight 1 MiB arrays per worker. Stream reads one array and writes an
affine result to the eighth; stencil reads a forward three-point FP32 stencil
with unaligned load-unpack pairs and a two-element initialized halo; short
rows sum seven arrays into the eighth with masks for 7, 8 or 9 active elements
and 64-byte row pitch. Only the arrays used by each kernel are prefetched.
These fixed memory-sized per-worker arrays deliberately differ from C4's
fixed per-core capacity experiment. The one-core jobs touch at most 32 MiB.

The extended driver uses pinned first touch with page-aligned allocations and
a fixed 1 KiB sibling stagger. A native one-round gate checks C1 stores, C5
outputs, C6 outputs and untouched tail elements, and C7 sums before the pilot.
Batch sizing is checked and adjusted to 50-200 ms; each result is the median
of five group medians (3 warm-ups and 21 samples per group). Same-worker TSC
ticks remain auxiliary; wall makespan is the primary result. Chronological
`group` lines preserve the unsorted group medians. Under ADR-0010 amendment 2,
spread >=2% prints `regime_step ... flagged=1` and does not reject a launch.
`accepted` reflects density and median batch duration; use the process exit
status too, since end-policy changes fail the launch after result emission.
Start/end source, governor and policy limits are compared; current frequency
is recorded as telemetry. No host test establishes native correctness or speed.

## Original S6-03 corpus and historical protocol

The following describes the original corpus. Its S6-03 artifact paths and
spread-based acceptance text are historical; the S8 build location and
ADR-0010 amendment-2 behavior above supersede them for the extended binary.

`knc-char.mic` is one driver with small hand-written assembly programs, one
selectable kernel per measurement below. GCC cannot schedule the timed bodies.
Source of instruction syntax/semantics: Intel 327364-001 (local shared text),
especially KAND pp.79-80, KXOR pp.105-106, gathers pp.297-302, no-read stores
pp.390-392, permutations pp.480-483, and move conversion tables; existing
`tests/regress/knc-{convert,gather}-probe.c` provide assembler examples.
ADR-0009 points 1-5 motivate the corpus; S6-01 and ADR-0010 define timing.
This delivers programs for the lead to run, with no native timing claims.

Build and acceptance, from this worktree:

```text
python tools/run.py --name S6-03-acceptance --inputs tests/bench/knc-char -- python tests/bench/knc-char/build.py
```

This uses the shared GCC 16, assembles every kernel, links the card ELF, lints
both assembly files and the ELF, then builds a Cygwin host driver and checks its
arguments at densities 1-4. The host build substitutes inert functions and
refuses `--native`; its `--dry-run` does not measure or execute IMCI. Outputs,
including generated assembly/header, stay in `.work/_shared/S6-03/`:
`knc-char.mic`, `knc-char-host.exe`, `driver.s`, `kernels.s`, `kernels.h`.
`build.py build|lint|host` can finish an uncompleted phase after a failure.

Lead-only example (not executed by the engineer), from a ticket worktree:

```text
python tools/card_run --benchmark --threads 4 --timeout 120 ../_shared/S6-03/knc-char.mic --native --cores 1 --threads 4 --case vaddps.lat
python tools/card_run --benchmark --threads 240 --timeout 120 ../_shared/S6-03/knc-char.mic --native --cores 60 --threads 4 --case memory.store_stream
```

For every measurement, use density 1, 2, 3 and 4, setting the launch thread
reservation to `cores*density`. Use one core to isolate per-core behavior, then
60 cores for production memory/ring contention. Select one `--case` per job to
keep exclusive windows short; omission runs the whole catalog (allow at least
1800 seconds). Repeat each accepted configuration in three independent windows.
Use a card configuration with `memoryMB >= 2048` at 60 cores; there is no CLI
memory override. The lead records results in
`docs/research/knc-characterization.md`. Density 3 is collected as diagnostic
data and always marked unaccepted, as ADR-0010 requires.

Each worker discovers core IDs in `/proc/cpuinfo`, sorts the four siblings and
pins itself to sibling `t` of core `c`, for `c=0..cores-1`, `t=0..density-1`.
The worker checks singleton affinity against the inherited allowed mask. Core
60 is excluded. Workers perform first touch and initialization after pinning.
Every launch prints start/end clocksource and power policy, and worker CPU IDs.

Each case has a pilot targeting 100 ms, then five groups of three warm-ups and
21 timed samples. All samples are printed. `--rounds 1..100000000` is a debug
override that bypasses the pilot; omit it for protocol measurements. A kernel
round executes 32 units with a single decrement/branch tail. The assembly has
64-byte aligned loop entries and uses 1 chain for `.lat`, 8 for vector `.rt`,
7 for x87 `.rt`, 6 for mask `.rt`, and 3 for scalar `.rt`. Setup and ABI
prologue/epilogue remain inside the long batch and are amortized, not subtracted.
RDTSC has CPUID serialization on both sides. Samples include boundary costs.

Output (whitespace separated):

```text
DRY vaddps.lat 4 cycles=unmeasured cores=1 bytes=4096
pin WORKER LOGICAL_CPU
policy PHASE SYSFS_PATH VALUE
sample NAME THREADS_PER_CORE GROUP REP WORKER ROUNDS MAKESPAN_NS WORKER_TSC_TICKS
group NAME THREADS_PER_CORE GROUP MEDIAN_NS MIN_NS MAX_NS
result NAME THREADS_PER_CORE cycles=TICKS_PER_UNIT cycle_unit=tsc_ticks worker=ID ns_per_unit=NS spread=FRACTION accepted=BOOL cores=N bytes=BYTES_PER_WORKER units=UNITS instructions=BODY_INSTRUCTIONS_PER_UNIT
```

There is one `result` line per measurement per worker. `cycles` is explicitly
**serialized same-worker TSC ticks per unit**, not proven physical core cycles:
S6-01 found about 1232.2 MHz but no invariant-TSC guarantee. The primary
comparison is `ns_per_unit`, the median of five group makespan medians divided
by `32*rounds`. The cycles figure independently takes the median of that
worker's five tick medians. No TSC subtraction across workers or cores occurs.
`accepted=1` means the five wall group medians have full spread below 2% and
density is not 3; the lead must additionally check <2% spread across the three
independent launch medians. Exit 0 means that within-launch check passes for
every selected case; 3 means noisy/diagnostic data, 2 means invalid arguments
or infrastructure failure. Missing sysfs paths are printed with errno.

`.lat` is a dependency-chain experiment and `.rt` a reciprocal-throughput
experiment.
Figures are effective per-worker costs at the selected density, including
shared issue resources, rather than density-independent architectural latency.
For one-core throughput with balanced workers, aggregate units/ns is density
divided by `ns_per_unit`; retain the measured per-worker figures alongside it.
Memory stores have no independently observable register result;
their `.lat` numbers are expressly store-to-load round trips. Do not assign
those entire numbers to isolated load or store scheduler latency. Unpack `.rt`
counts the low/high pair as one unit; unpack `.lat` counts its store pair plus
load pair as one unit. Spill/reload counts a 64-byte stack round trip as one
unit. Half converting moves use `{float16}`; their `.lat` unit also contains
the reverse move. Masked moves run with full masks and alternating eight-lane
masks; inactive lanes merge. `instructions` excludes the common loop tail;
0 denotes variable-length gather replay. Gather completes all requested lanes
using the ISA mask-replay loop; its costs include mask reset, replay branches,
and (for `.lat`) dependent index OR. All gather data is zero so OR restores
the chosen indices. The all-lane case hits one line; scattered hits 16 lines.
These are complete gathers, not a claim about one partial gather issue.

Conversions use scale 0 and rounding control 0; repeated register conversions
consume the previous result's bits. FP32/FP64 arithmetic uses normal one-valued
inputs (FMA/add grow slowly; multiply/divide/reciprocal remain one). x87 uses
eight initialized stack registers with st0 as a constant and pops them on exit.
No compiler floating-point optimizations affect the assembly.

Pairing units contain two instructions and rotate through independent vector
chains. Compare vector/scalar, vector/vector and scalar/scalar results at the
same density; include loop overhead and avoid inferring pairing from a single
recurrence. AGI units have an `add $0` pointer update, 0-4 scalar NOPs, and
its dependent address use. Gaps count instructions, **not assumed cycles**:
issue spacing depends on density and pairing. Compare the five curves at each
density to locate the interlock; do not label a NOP one core cycle.

Hierarchy budgets count siblings: total live data is at most 16 KiB/core for
L1, 256 KiB/core for L2, and 16 MiB/core for memory. Each per-worker allocation
uses the largest power of two not exceeding that budget divided by density
(density 3 rounds down). Arrays are 64-byte aligned. These are capacity targets,
not proven residency. Pointer latency visits a deterministic Fisher-Yates
random permutation of **every 64-byte line** in a single dependent cycle,
avoiding regular streaming prefetch. Load/store bandwidth visits sequential
full lines, 2048 bytes/round; calculate aggregate GB/s as
`64*cores*density / ns_per_unit`. Compare `store_normal` and `store_stream`
at identical footprints: the latter uses globally ordered `vmovnraps` no-read
stores (not non-globally-ordered stores), including serialized completion at
the batch boundary. Cache/ring effects, first-touch ownership and warming are
part of the observed behavior; no silent overhead subtraction is made.

Every catalog row below has the expected `result NAME D cycles=...` line
given above, where D is 1, 2, 3 or 4. Units and qualifications above apply.

| NAME | What it isolates |
|---|---|
| `vaddps.lat` | FP32 vector add; one dependent chain |
| `vaddps.rt` | FP32 vector add; independent destinations/chains |
| `vmulps.lat` | FP32 vector multiply by one; one dependent chain |
| `vmulps.rt` | FP32 vector multiply by one; independent destinations/chains |
| `vfmadd213ps.lat` | FP32 fused multiply-add; one dependent chain |
| `vfmadd213ps.rt` | FP32 fused multiply-add; independent destinations/chains |
| `vpaddd.lat` | Vector integer add; one dependent chain |
| `vpaddd.rt` | Vector integer add; independent destinations/chains |
| `vpxord.lat` | Vector integer XOR, distinct operands; one dependent chain |
| `vpxord.rt` | Vector integer XOR, distinct operands; independent destinations/chains |
| `vpermd.lat` | Dword permutation, data dependency; one dependent chain |
| `vpermd.rt` | Dword permutation, data dependency; independent destinations/chains |
| `vpermf32x4.lat` | 128-bit block permutation; one dependent chain |
| `vpermf32x4.rt` | 128-bit block permutation; independent destinations/chains |
| `vrcp23ps.lat` | FP32 approximate reciprocal of one; one dependent chain |
| `vrcp23ps.rt` | FP32 approximate reciprocal of one; independent destinations/chains |
| `scalar_add.lat` | Scalar 64-bit integer add (three chains in rt); one dependent chain |
| `scalar_add.rt` | Scalar 64-bit integer add (three chains in rt); independent destinations/chains |
| `scalar_xor.lat` | Scalar integer XOR (three chains in rt); one dependent chain |
| `scalar_xor.rt` | Scalar integer XOR (three chains in rt); independent destinations/chains |
| `kmov.lat` | Mask register move (six destinations in rt); one dependent chain |
| `kmov.rt` | Mask register move (six destinations in rt); independent destinations/chains |
| `kand.lat` | Mask AND (six chains in rt); one dependent chain |
| `kand.rt` | Mask AND (six chains in rt); independent destinations/chains |
| `kxor.lat` | Mask XOR (six chains in rt); one dependent chain |
| `kxor.rt` | Mask XOR (six chains in rt); independent destinations/chains |
| `swizzle_cdab.lat` | 32-bit register swizzle cdab; one dependent chain |
| `swizzle_cdab.rt` | 32-bit register swizzle cdab; independent destinations/chains |
| `swizzle_badc.lat` | 32-bit register swizzle badc; one dependent chain |
| `swizzle_badc.rt` | 32-bit register swizzle badc; independent destinations/chains |
| `swizzle_dacb.lat` | 32-bit register swizzle dacb; one dependent chain |
| `swizzle_dacb.rt` | 32-bit register swizzle dacb; independent destinations/chains |
| `swizzle_aaaa.lat` | 32-bit register swizzle aaaa; one dependent chain |
| `swizzle_aaaa.rt` | 32-bit register swizzle aaaa; independent destinations/chains |
| `swizzle_bbbb.lat` | 32-bit register swizzle bbbb; one dependent chain |
| `swizzle_bbbb.rt` | 32-bit register swizzle bbbb; independent destinations/chains |
| `swizzle_cccc.lat` | 32-bit register swizzle cccc; one dependent chain |
| `swizzle_cccc.rt` | 32-bit register swizzle cccc; independent destinations/chains |
| `swizzle_dddd.lat` | 32-bit register swizzle dddd; one dependent chain |
| `swizzle_dddd.rt` | 32-bit register swizzle dddd; independent destinations/chains |
| `vaddpd.lat` | FP64 vector arithmetic; one dependent chain |
| `vaddpd.rt` | FP64 vector arithmetic; independent destinations/chains |
| `vmulpd.lat` | FP64 vector arithmetic; one dependent chain |
| `vmulpd.rt` | FP64 vector arithmetic; independent destinations/chains |
| `vfmadd213pd.lat` | FP64 vector arithmetic; one dependent chain |
| `vfmadd213pd.rt` | FP64 vector arithmetic; independent destinations/chains |
| `vcvtfxpntdq2ps.lat` | Fixed-point conversion scale zero; register bit-pattern recurrence; one dependent chain |
| `vcvtfxpntdq2ps.rt` | Fixed-point conversion scale zero; register bit-pattern recurrence; independent destinations/chains |
| `vcvtfxpntudq2ps.lat` | Fixed-point conversion scale zero; register bit-pattern recurrence; one dependent chain |
| `vcvtfxpntudq2ps.rt` | Fixed-point conversion scale zero; register bit-pattern recurrence; independent destinations/chains |
| `vcvtfxpntps2dq.lat` | Fixed-point conversion scale zero; register bit-pattern recurrence; one dependent chain |
| `vcvtfxpntps2dq.rt` | Fixed-point conversion scale zero; register bit-pattern recurrence; independent destinations/chains |
| `vcvtfxpntps2udq.lat` | Fixed-point conversion scale zero; register bit-pattern recurrence; one dependent chain |
| `vcvtfxpntps2udq.rt` | Fixed-point conversion scale zero; register bit-pattern recurrence; independent destinations/chains |
| `vcvtfxpntpd2dq.lat` | Fixed-point conversion scale zero; register bit-pattern recurrence; one dependent chain |
| `vcvtfxpntpd2dq.rt` | Fixed-point conversion scale zero; register bit-pattern recurrence; independent destinations/chains |
| `vcvtfxpntpd2udq.lat` | Fixed-point conversion scale zero; register bit-pattern recurrence; one dependent chain |
| `vcvtfxpntpd2udq.rt` | Fixed-point conversion scale zero; register bit-pattern recurrence; independent destinations/chains |
| `x87_add.lat` | x87 add; dependent st1 |
| `x87_add.rt` | x87 add; seven independent stack registers |
| `x87_mul.lat` | x87 mul; dependent st1 |
| `x87_mul.rt` | x87 mul; seven independent stack registers |
| `x87_div.lat` | x87 div; dependent st1 |
| `x87_div.rt` | x87 div; seven independent stack registers |
| `masked_load.lat` | masked_load; dependent store-to-load round trip, not isolated load/store latency |
| `masked_store.lat` | masked_store; dependent store-to-load round trip, not isolated load/store latency |
| `unpack.lat` | unpack; dependent store-to-load round trip, not isolated load/store latency |
| `convert_up.lat` | convert_up; dependent store-to-load round trip, not isolated load/store latency |
| `convert_down.lat` | convert_down; dependent store-to-load round trip, not isolated load/store latency |
| `spill_reload.lat` | spill_reload; dependent store-to-load round trip, not isolated load/store latency |
| `masked_load.rt` | masked_load; eight independent buffers; unpack counts L/H pair |
| `masked_store.rt` | masked_store; eight independent buffers; unpack counts L/H pair |
| `unpack.rt` | unpack; eight independent buffers; unpack counts L/H pair |
| `convert_up.rt` | convert_up; eight independent buffers; unpack counts L/H pair |
| `convert_down.rt` | convert_down; eight independent buffers; unpack counts L/H pair |
| `spill_reload.rt` | spill_reload; eight independent buffers; unpack counts L/H pair |
| `masked_load_sparse.lat` | masked_load; dependent store-to-load round trip, not isolated load/store latency; alternating eight active lanes |
| `masked_store_sparse.lat` | masked_store; dependent store-to-load round trip, not isolated load/store latency; alternating eight active lanes |
| `masked_load_sparse.rt` | masked_load; eight independent buffers; unpack counts L/H pair; alternating eight active lanes |
| `masked_store_sparse.rt` | masked_store; eight independent buffers; unpack counts L/H pair; alternating eight active lanes |
| `gather_all.lat` | Complete 16-lane gather with mask reset/replay; one cache line; result-to-index OR dependency on zero data |
| `gather_all.rt` | Complete 16-lane gather with mask reset/replay; one cache line; eight output registers |
| `gather_scattered.lat` | Complete 16-lane gather with mask reset/replay; 16 cache lines; result-to-index OR dependency on zero data |
| `gather_scattered.rt` | Complete 16-lane gather with mask reset/replay; 16 cache lines; eight output registers |
| `pair.vector_scalar` | U/V issue experiment; cycles per two-instruction pair; independent streams |
| `pair.vector_vector` | U/V issue experiment; cycles per two-instruction pair; independent streams |
| `pair.scalar_scalar` | U/V issue experiment; cycles per two-instruction pair; independent streams |
| `agi.gap0` | Pointer ALU update then load separated by 0 scalar NOP instructions (not assumed cycles) |
| `agi.gap1` | Pointer ALU update then load separated by 1 scalar NOP instructions (not assumed cycles) |
| `agi.gap2` | Pointer ALU update then load separated by 2 scalar NOP instructions (not assumed cycles) |
| `agi.gap3` | Pointer ALU update then load separated by 3 scalar NOP instructions (not assumed cycles) |
| `agi.gap4` | Pointer ALU update then load separated by 4 scalar NOP instructions (not assumed cycles) |
| `l1.load_lat` | Dependent randomized 64-byte-line pointer cycle; per-worker l1 budget |
| `l1.load_rt` | Sequential 64-byte lines; load_rt; bytes/ns derives bandwidth, includes loop/address overhead |
| `l1.store_normal` | Sequential 64-byte lines; store_normal; bytes/ns derives bandwidth, includes loop/address overhead |
| `l1.store_stream` | Sequential 64-byte lines; globally ordered no-read stores; bytes/ns derives bandwidth, includes loop/address overhead |
| `l2.load_lat` | Dependent randomized 64-byte-line pointer cycle; per-worker l2 budget |
| `l2.load_rt` | Sequential 64-byte lines; load_rt; bytes/ns derives bandwidth, includes loop/address overhead |
| `l2.store_normal` | Sequential 64-byte lines; store_normal; bytes/ns derives bandwidth, includes loop/address overhead |
| `l2.store_stream` | Sequential 64-byte lines; globally ordered no-read stores; bytes/ns derives bandwidth, includes loop/address overhead |
| `memory.load_lat` | Dependent randomized 64-byte-line pointer cycle; per-worker memory budget |
| `memory.load_rt` | Sequential 64-byte lines; load_rt; bytes/ns derives bandwidth, includes loop/address overhead |
| `memory.store_normal` | Sequential 64-byte lines; store_normal; bytes/ns derives bandwidth, includes loop/address overhead |
| `memory.store_stream` | Sequential 64-byte lines; globally ordered no-read stores; bytes/ns derives bandwidth, includes loop/address overhead |
