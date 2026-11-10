# GCC-KNC flags

ADR-0009 point 8. What to pass, what `-march=knc` already does, and how ICC's `-mmic` flags map.
Card checks C1-C12 are in [knc-characterization.md](research/knc-characterization.md); tickets
are in [work/tickets](../work/tickets/).

## Recommended flags

| Flag | Why |
|---|---|
| `-O2 -march=knc` | The defaults below; `-march=knc` also sets `-mtune=knc`. |
| `-O3` | Adds the dynamic vectorizer cost model (alignment peeling and versioning) and predictive commoning. |
| `-fopenmp` | 4 threads per core is the tuned case (ADR-0009 point 2). |
| `--param knc-threads-per-core=N` | Running 1-3 threads per core: more reduction chains (C7, [knc-costs.md](research/knc-costs.md)) and a longer L1 prefetch distance (C5). |
| `-ffast-math` | Only to match ICC's default FP model; see the last table. |

Do not pass SSE, AVX or MMX options: `-march=knc` rejects them (ADR-0002).

## What `-march=knc` implies

Each default yields to an explicit user setting.

| Default | Evidence |
|---|---|
| Short loops and remainders are masked vector code that never touches an unmapped page (`vect-partial-vector-usage=1`) | C6; [S8-02](../work/tickets/S8-02.md) |
| `-fprefetch-loop-arrays` at `-O2` and above: `vprefetch1` 32 lines ahead (`knc-prefetch-l2-distance`), `vprefetch0` 16 (`knc-prefetch-l1-distance`, halved for many streams) | C2, C5; [S8-03](../work/tickets/S8-03.md), [S8-12](../work/tickets/S8-12.md) |
| No-read streaming stores for write-only loops larger than L2, with a fence after the loop | C1; [S8-13](../work/tickets/S8-13.md) |
| `-O2` vectorizes with the cheap cost model and `-fversion-loops-for-strides` | [S8-09](../work/tickets/S8-09.md) (corpus loops vectorized at `-O2`: 17 to 64) |
| `-malign-data=cacheline`; local arrays of 64 bytes or more start a line | [S8-14](../work/tickets/S8-14.md) |
| Cache parameters: L1 32 KB, line 64 B, L2 256 KB (the DTLB reach, not the 512 KB cache) | C4; [S8-14](../work/tickets/S8-14.md) |
| OpenMP shared blocks and per-thread arrays start their own 64-byte line | C11; [S8-10](../work/tickets/S8-10.md) |
| Vector reduction chains from the thread density: one at the default 4 threads per core, two at 1-3 (`knc-threads-per-core`) | C7; [knc-costs.md](research/knc-costs.md) |
| Unroll a vector loop of at most 16 insns 4 times at `-O2` (`-munroll-only-small-loops`); a stream (at most one vector op per vector store) 2 times at `knc-threads-per-core` 1-2 and not at 3-4; larger loops and scalar loops as x86 | C9; [S8-15](../work/tickets/S8-15.md), [S8-20](../work/tickets/S8-20.md) |

`-mtune=knc` (tune flags, all listed in [knc-costs.md](research/knc-costs.md)):

| Default | Evidence |
|---|---|
| No 0x66/0x67-prefixed register forms where a 32-bit form gives the same result | SSDG p.16 (2-cycle decode); [S8-08](../work/tickets/S8-08.md) |
| Functions start on a 64-byte line; loops keep the generic alignment | M2 A/A pairs; [S8-08](../work/tickets/S8-08.md) |
| No tight-loop alignment pass (its nops ran on every outer trip) | m2_mat8 1.105x; [S8-19](../work/tickets/S8-19.md) |

Code shape, not a flag: vector add, sub, mul and FMA read aligned memory and `{1to16}`/`{1to8}`
broadcasts directly ([S8-06](../work/tickets/S8-06.md)); integer multiply-add is `vpmadd231d`
([S8-07](../work/tickets/S8-07.md)). [S8-04](../work/tickets/S8-04.md) and
[S8-05](../work/tickets/S8-05.md) changed no default. C10 (branch mispredict) has not changed the
branch cost yet.

## ICC `-mmic` equivalents

| ICC | GCC-KNC |
|---|---|
| `-mmic` | `k1om-mpss-linux-gcc -march=knc` |
| `-O2` (vectorizes) | `-O2 -march=knc` (cheap model, S8-09); `-O3` for the dynamic model |
| `-qopt-prefetch`, prefetch distances | on by default; `--param knc-prefetch-l2-distance=`, `knc-prefetch-l1-distance=` |
| `-qopt-streaming-stores auto` | automatic beyond L2 (S8-13); off with `-fno-prefetch-loop-arrays` |
| `-qopt-threads-per-core=N` | `--param knc-threads-per-core=N` |
| `-align array64byte` (Fortran) | default (`-malign-data=cacheline`, S8-14) |
| `-unroll=N` | `-funroll-loops`, `#pragma GCC unroll N` |
| `-qopenmp` | `-fopenmp` |
| `-qopt-assume-safe-padding` | not provided (masked tails use aligned masks or gather/scatter) |

**Where GCC-KNC deliberately differs: floating point** (ADR-0003, ADR-0009 point 7). ICC defaults
to `-fp-model fast=1`, which reassociates, contracts and approximates. GCC-KNC keeps IEEE
semantics at every `-O` level: vector division and square root are correctly rounded (FP32; FP64
division stays scalar x87), and no approximation is used without an opt-in. `-ffast-math` is the
nearest match to ICC's default; it also links `crtfastmath`, which flushes subnormals. ICC's
`-no-prec-div` / `-fimf-precision=low` approximate forms are not built yet (ADR-0003 point 5).
`-ffp-contract` is GCC's default (`fast` in GNU C modes, `off` with `-std=c11`).

## `-mphinix`

One flag for the measured best set ([S8-16](../work/tickets/S8-16.md)): Phi plus phoenix.
The driver expands it before `cc1` runs, so `-###` shows exactly what it means:

Expansion: `-O3 -march=knc -mtune=knc -fprefetch-loop-arrays -munroll-only-small-loops -malign-data=cacheline`

- `-O3` adds the dynamic vectorizer cost model and predictive commoning to the `-march=knc`
  defaults above; the other flags are those defaults, written out.
- Each part yields to an explicit user setting of the same option, given before or after
  `-mphinix` (`-O2`, `-mtune=`, `-fno-prefetch-loop-arrays`, `-funroll-loops`, `-malign-data=`).
- IEEE semantics stay: no `-ffast-math` or any part of it.
- KNC only: with another `-march=` it is an error, and an x86 compiler does not accept it.

On a terminal, `-mphinix` also prints the rising-phoenix banner once, and draws an apt-style
progress bar, one step per driver job (`[####......] 40%  compiling foo.c (2/5)`). The bar
sits on the terminal's last line, below a scroll region, so warnings and errors scroll above it
unchanged, and it is cleared on exit.

| Switch | Effect |
|---|---|
| `-mno-phinix-banner` | No banner. |
| `-mprogress` | The progress bar without `-mphinix`. |
| `-mno-progress` | No progress bar. |

Neither ever appears when stderr is not a terminal, under `-E` or `-o -`, with `-###`, `-v` or
`--version`, or under make's `-j` or jobserver (`MAKEFLAGS`). They write only to stderr and never
change the exit status, the diagnostics or an output file.

`-mphinix` without `-mknc-card=` also detects the card (`-mknc-card=native`, next section).

## `-mknc-card=`

Every KNC card has the same core (ISA, L1, L2, TLB), so a card model changes tuning, never the
instruction set ([S9-13](../work/tickets/S9-13.md)). `-mknc-card=MODEL` sets the model's values
for the parameters that follow the memory system; each yields to an explicit `--param`, given
before or after it. The driver expands it, so `-###` shows the `--param`s. KNC only: with another
`-march=` it is an error, and an x86 compiler does not accept it.

| Model | Cards (accepted as names, `-mknc-card=7120` is `7100`) | Cores | Clock | GB/s per core | `knc-prefetch-l2-distance` | `knc-prefetch-l1-distance` |
|---|---|---|---|---|---|---|
| `generic` (default) | any | | | | 32 | 16 |
| `3100` | 3110P, 3115A, 3120A, 3120P | 57 | 1.1 GHz | 4.2 | 23, derived, not measured | 16 |
| `5100` | 5110P, 5120D | 60 | 1.053 GHz | 5.3 | 29, derived, not measured | 16 |
| `7100` | 7110P, 7110X, 7120P, 7120X, 7120A, 7120D | 61 | 1.238 GHz | 5.8 | 32, measured on a 7120P ([S8-03](../work/tickets/S8-03.md)) | 16 |

- The model: the L2 prefetch distance (lines) must cover memory latency x bandwidth per core.
  Latency in ns is about the same on the three (GDDR5 on the same ring), and a stream that waits
  on memory consumes lines at the bandwidth, not the clock, so the distance scales with bandwidth
  per core: 32 x 4.2 / 5.8 = 23 and 32 x 5.3 / 5.8 = 29.
- The L1 distance covers an L2 hit, which costs the same core cycles on every model: 16 for all.
- `generic` is the longest distance, 32: a distance too short stalls on every line, one too
  long only keeps a few more lines in the 512 KB L2. So plain `-march=knc` (no `-mknc-card=`)
  adds no `--param` and gives the same code on every machine.
- Not card-dependent, so unchanged by the model: `knc-threads-per-core`, the S8-13
  streaming-store threshold (cache size), the cache parameters, unrolling and vector costs.

`-mknc-card=native` picks the model before `cc1` runs:

- On a card (a native compiler, `cpu family` 11 in `/proc/cpuinfo`): the number of distinct
  `core id` values, which includes the core MPSS keeps for the OS: 61 is `7100`, 59-60 `5100`,
  56-57 `3100`. A `MemTotal` in `/proc/meminfo` over 12 GiB is a `7100` (the only 16 GB model)
  even if a kernel hides the OS core.
- On a Linux host with MPSS 3.x: each `/sys/class/mic/micN` whose `family` is `x100`, by the
  first digit after the dash in its `sku` (`C0-7120 P/A/X/D`, `B1PRQ-5110P/5120D`; the names are
  from mpss-modules `host/linsysfs.c`). One model: that model. Different models: an error that
  names them and asks for `-mknc-card=MODEL`.
- Nothing found (a Windows host, a host without MPSS): `generic`, with a one-line note on stderr.

## Writing fast code for KNC

Guidance for programs on the Intel® Xeon Phi™ x100 coprocessor, in our own words. Sources are
named per claim; none of this is Intel text (ADR-0013).

**Threads per core.**
- Use 4 per core for compute-bound loops: one thread cannot issue back to back on this in-order
  core, so the compiler assumes 4 (`knc-threads-per-core`, [best-practice review](research/knc-best-practice-review.md) item 3).
- Pure streaming code may run faster at 1-2 per core: McCalpin's STREAM loses about 10% at 4
  (review item 10); our own prefetch and unroll measurements are C5 and S8-15 ([knc-costs.md](research/knc-costs.md)).
- Tell the compiler what you run: `--param knc-threads-per-core=N` (ICC `-qopt-threads-per-core=N`).
  At 1-3 it uses two reduction chains and a longer L1 prefetch distance (C7, C5).

**First touch and parallel regions.**
- Initialize data in the thread that will use it (the same `schedule(static)` loop shape), so
  pages are first written, and cached, where they are used (PRACE §13.2.2-13.2.8, review item 10).
- Prefer fewer, larger `parallel` regions over many small ones: each fork and join costs a barrier
  across up to 240 threads. Use `nowait` on a worksharing loop when the next loop does not read
  what it wrote. libgomp's static-schedule and spin choices are in S9-08 and S9-10.

**Heap.**
- Allocate large blocks once and reuse them across time steps. Each `malloc` above glibc's mmap
  threshold is an `mmap` plus page zeroing, and freeing it is an `munmap` (review item 4).
- glibc knobs, set in the environment (ICC's `-qopt-malloc-options` did this at link time):
  `MALLOC_MMAP_THRESHOLD_=<bytes>` (large, for example 1073741824, keeps big blocks on the heap)
  with `MALLOC_TRIM_THRESHOLD_=<bytes>` (large, so freed memory is not returned each step).
  Not adopted as a compiler or libgomp default; measure on your program.
- Arenas and stacks: libgomp sets `MALLOC_ARENA_MAX` from the card's memory unless you set it
  (ADR-0012, S9-12; WRF runs at 64). Thread stacks reserve address space too: set
  `OMP_STACKSIZE` for 240 threads ([knc-libgomp.md](research/knc-libgomp.md) section 6).

**Differences from ICC `-mmic` defaults.**
- ICC flushed subnormals to zero (`-ftz`) and used faster, less accurate divide and
  transcendentals by default. GCC-KNC keeps IEEE at every `-O` level (ADR-0003): subnormals are
  kept, divide and square root are correctly rounded.
- Opt in with `-ffast-math`, which links `crtfastmath` and flushes subnormals, and also
  reassociates and approximates. There is no separate ICC-style `-no-prec-div` yet (ADR-0003
  point 5). The VPU cost of subnormal operands is the subject of
  [S9-16](../work/tickets/S9-16.md); do not assume flushing is needed for speed until it reports.

Intel and Xeon Phi are trademarks of Intel Corporation or its subsidiaries.
