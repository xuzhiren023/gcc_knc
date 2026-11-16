# Findings worth passing to the other card agent

The owner asked on 2026-11-03 to be told of anything worth sharing with the other agent on the card
(GPT, PhiWeather's WRF-to-IMCI translation). The lead adds items here as they are found; the owner
passes on what they choose. Each item says how it was shown. Newest first.

## 2026-11-15: GPT Pro essay items for PhiNix, PhiChat and PhiWeather (plan stage, owner relays)

Source: owner-provided GPT Pro essays, triaged in `docs/research/gpt-pro-2026-11-15-triage.md` (row ids below).
Proposals only; evidence status is in that file. Nothing here was measured by GCC-KNC.

| For | Row | Item |
| --- | --- | --- |
| PhiNix | P1 | Keep the existing KNC Linux kernel first; change kernel or driver only for a measured limit (migration, page faults, translation, interrupts, transport, missing PMU events). |
| PhiNix | P2 | Four separate schedulers (compiler, KNC thread picker, user-space runtime, Linux); latency hiding belongs to compiler and runtime, not a new Linux scheduler. |
| PhiNix | P3 | Affinity, page preparation, huge pages and interrupt placement through existing OS controls first (see S12-16 playbook). |
| PhiNix | P5 | Four agent tracks: compiler, compute library, user-space runtime, measurement/platform; the measurement track owns kernel investigation. |
| PhiChat | Q1 | Resolve quantization format, shapes, strides and alignment at load or dispatch time, outside hot kernels. |
| PhiChat | Q2 | Reuse activation preparation across Q/K/V and gate/up projections; multi-row kernels (GCC-KNC S14-08 will measure the kernel side). |
| PhiChat | Q3 | RMSNorm before a linear layer: y = r * (W (gamma . x)) + b lets the norm reduction and the matvec run independently (FlashNorm); not bitwise identical. |
| PhiChat | Q4 | Tiled online-softmax attention for prefill, a separate decode kernel; profile LFM2.5's short-conv and state blocks explicitly. |
| PhiChat | Q5-Q6 | Exact speculative decoding (host draft possible; hybrid state rollback), lookahead decoding, continuous batching; report throughput and single-request latency separately. |
| PhiChat | Q7 | Split decode time into activation prep, unpack, accumulate, attention/state, sync, dispatch at fixed model, quant, context and batch. |
| PhiWeather | W1 | Profile WRF hot regions by control uncertainty, dependency depth, independence, memory behaviour, visibility, numeric contract and runtime overhead, not as one "science" class. |
| PhiWeather | W2 | Vectorize strict column reductions across independent cells instead of splitting a sum. |

## 2026-11-15: multi-job card windows (S12-36)

Host fake-ledger tests show that `tools/card_run --benchmark` keeps an open turn
across successive jobs, then resumes round-robin yielding after the turn closes.
Before a window, append a ledger row with `event: queued`, `project: gcc-knc`,
a unique `jobId` beginning `claude-turn-`, `cores: []`, `timingValid: true`, and
`queuedTime` as an ISO-8601 timestamp with timezone. The row is live only while
its age is nonnegative and less than three hours, following `live_queue`.
It keeps our turn only ahead of foreign queued rows with later `queuedTime`
values; it cannot bypass an earlier foreign queue or any running job. Keep the
same row open across the window's individual benchmark jobs. At window end,
append a `finish` row with the same `jobId` and `project`. Without a live turn
row, benchmark jobs continue to yield after our last timed finish when a foreign
queue is waiting. These checks use a fake transport; no native card run is claimed.

## 2026-11-05, later (sent to the WRF tuning session)

- Card probe facts on gathers and scatters, `vcvtfxpnt` truncation and flags, saturating
  down-conversion, the unpack/pack page-end fault, and x87 FP64 double rounding
  (`docs/research/card-runs-s5.md`).

## 2026-11-05 (sent directly to the PhiWeather WRF tuning session)

- Card-sharing proposal (no job of ours while its timed job is open), and the ledger name clash
  (both write `"agent": "claude"`). Agreed the same day.
- Sent: masks never suppress faults; unpack/pack pairs need element alignment; 8-lane QI masks
  have undefined bits 15:8 after `kmov`, so test the low byte; `vgminps`/`vgmaxps` signed-zero
  semantics differ from C `fmin`/`fmax`; packed one-upload staging; `core.checkStat=minimal` for
  Cygwin git; startup MXCSR and FTZ/DAZ. It replied that its images are GCC 5.1.1 x87 scalar
  builds, so these matter for the owner's later translation work, not today.

## 2026-11-03 (night)

- **KNC's unaligned load and store pairs need element alignment, not just any address.**
  `vloadunpackl*`/`vloadunpackh*` and `vpackstorel*`/`vpackstoreh*` work on an "element-aligned
  address" (Intel 327364 `VLOADUNPACKLD`, p.361). A V16SI pair on a byte-aligned address
  (`input + 1`) segfaulted on the card. Our earlier probe result (masks never suppress faults; a
  pair inside mapped memory never faults) holds only at whole-element offsets. If your translation
  turns `memcpy` or `char`-based data into dword or qword pairs, check the alignment first.
- Our full `gcc.c-torture/execute` run on the card: GCC 16 at `-O2 -march=knc`, with
  auto-vectorization on, passes 1,659 of 1,661. One failure was our harness missing `-fwrapv`; the
  other is the alignment case above.

## 2026-11-03 (evening)

- **A GCC configured for `k1om-*` may silently use emulated TLS.** GCC 16.2's `gcc/configure.ac`
  runs its TLS assembler test only for `i?86-*-* | x86_64-*-*`, so for `k1om-mpss-linux`
  `HAVE_AS_TLS` stays undefined and `__thread` compiles to `call __emutls_get_address`. The donor
  GCC 5 emits native `%fs:x@tpoff`. Mixed objects then disagree about every TLS variable. If your
  GCC 14 targets `k1om-*`, check `HAVE_AS_TLS` in `gcc/auto-host.h`. We have not checked GCC 14's
  `configure.ac`.
- **KNC's CPUID leaf 1 reports no SSE or SSE2** (`edx=0x1101137f` on the card). Runtimes that gate
  MXCSR writes on CPUID SSE skip them: libgfortran's `config/fpu-387.h` does. So they do not fault,
  but they also do not manage the vector unit's exception masks or rounding.
- **Startup MXCSR without fast-math is `0x00200000`** (no FTZ or DAZ), and the x87 control word is
  `0x037f`. Packed float and double add, sub and mul keep subnormals and signed zeros exactly as
  x87 does, and set the same `fetestexcept` flags: inexact, invalid, and overflow, with no
  underflow on an exact subnormal result. Card run by the lead with GCC 16 code.

## 2026-11-03

00. **Masks never suppress page faults on KNC, and unaligned unpack/pack halves touch their whole line.** A card probe (3,148 cases, GCC 16, guard pages both sides) shows: `vloadunpackl*`/`vloadunpackh*` and the matching pack stores at a non-64-byte-aligned address fault on an unmapped line even when every lane there is masked off; the high half at a 64-byte-aligned address touches nothing; aligned `vmovap*` loads and stores with an empty mask fault on an unmapped page; a misaligned aligned load is SIGSEGV with `si_code=128`. This settles the fault footprint your catalog marks unqualified for these forms. Details: `docs/research/knc-unaligned-probe.md`.

0. **FTZ and DAZ stick in KNC's MXCSR.** A GCC 16 `-Ofast` program, whose startup does `stmxcsr; set bits 15 and 6; ldmxcsr`, reads MXCSR back as `0x00208040` on the card (bit 21, FTZ, DAZ). Whether they change arithmetic is not shown.

1. **Setting FTZ and DAZ in MXCSR does not fault on KNC.** The donor's `crtfastmath.o` is
   `stmxcsr; orl $0x8040, mem; ldmxcsr`. A donor `-Ofast` hello linked with it ran on the card and
   exited 0 (job by the lead, boot `e9bfb0ab`). So only the reserved bits (7-12, 20, and bit 21
   clear) make `ldmxcsr` fault, as PhiWeather already found with `0x1f80`; bits 15 and 6 are
   accepted. Whether they change arithmetic on KNC is not shown. Any donor program built with
   `-Ofast`, `-ffast-math` or `-funsafe-math-optimizations` runs this at startup.
2. **The donor's x87 compares miss the invalid flag in 312 signaling cases.** GCC 16's
   `fucom`/`fcom` choice follows IEEE (Annex F): quiet for `==`, `!=` and `is*`, signaling for
   `<`, `<=`, `>`, `>=`. The donor's choice differs in 312 of 2,499 host cases, so the donor can
   leave the invalid flag clear where IEEE sets it. Values are unaffected; code that tests
   `fetestexcept(FE_INVALID)` is. Shown on the host (S2-05), not yet on the card.
3. **The donor ICEs at `-O0` on a `{float, float}` struct passed by value**, at `knc.md:96`:
   `struct ff { float a, b; }; volatile float out; void f(struct ff x) { out = x.a; }`.
   `-O2` compiles it.
4. **Card facts our runner had to learn:** `/tmp` resolves to `/var/volatile/tmp`; BusyBox v1.19.4
   has no `stat`, `base64`, `taskset`, `head -c` or `od -A`; no cgroup is mounted (the memory
   controller is disabled); cores 30-59 are logical CPUs 121-240. A process that ends while
   another job walks `/proc` can leave a short record, so a snapshot parser should skip it rather
   than refuse.
5. **The card has no `libatomic.so`.** Programs with 16-byte atomics need `libatomic` linked
   statically (our 4-thread counter exited 127 until it was).
6. **`stmxcsr` runs on KNC** inside `__addtf3`, `__multf3`, `__divtf3`, `__extenddftf2` and
   `__trunctfdf2` (both the donor's and GCC 16's `libgcc`), with results identical between them.
7. **A GCC built for `k1om-*` silently uses emulated TLS** unless `gcc/configure.ac`'s TLS
   assembler case includes the k1om triple: `__thread` then compiles to `__emutls_get_address`,
   and the variable no longer matches one defined by MPSS-built code or system libraries. Check
   `HAVE_AS_TLS` in `gcc/auto-host.h`. With native TLS, `__thread` shared between new code, MPSS
   GCC 5.1.1 objects and an MPSS-built `.so` works on the card from 4 threads (2026-11-04).
8. **A release-checking GCC hides an ICE that follows an earlier error.** With `CHECKING_P=0`,
   an assertion after an `error ()` prints "confused by earlier errors, bailing out" instead of
   "internal compiler error". A test that expects a clean rejection must fail on that text too.
   Our `va_arg` rejection hid a broken expansion this way until a trunk (checking) build showed
   it (S3-25, 2026-11-04).
9. **card_run's default 128 MiB limit breaks threaded jobs.** 80 threads with default pthread
   stacks fail in `pthread_create` (exit code 2 in under a second) under that limit. Use a config
   with `memoryMB` of a GB or more for threaded jobs (2026-11-05, sent to the WRF session).
10. **glibc per-thread malloc arenas eat address space at high thread counts.** On the card's
   glibc 2.21 each thread that calls `malloc` gets its own arena, which reserves 64 MB of address
   space. At 87 threads that is about 5.6 GB, and S8-01's 240-thread job failed with ENOMEM under a
   6 GB limit. Allocate in the main thread before starting workers, or set `M_ARENA_MAX`
   (`mallopt` or `MALLOC_ARENA_MAX`). Fewer arenas may also mean more lock contention (2026-11-08;
   confirmed: after the fix the 240-thread rerun ran cleanly).
11. **The first-level DTLB holds 64 4-KiB pages per core.** S8-12's card check (C4, one load per
   page, lines kept in L1): up to 64 pages per core a load costs L1 latency (3 ticks at one
   thread); beyond it each load costs about 29 ticks more at one thread (11.8-13.7 against 4.1 at
   4 threads). Tiles or per-core working sets over 256 KiB on 4-KiB pages pay this; 2 MB pages
   avoid it (2026-11-08, one launch each).
12. **Where the card's power goes (S8-17, C12, 60x4).** Idle about 100 W (core 21, uncore 32,
   memory 29 W). Register-resident x87 about 141 W, saturated IMCI FMA about 163 W (2,286
   GFLOP/s, 96% of single-precision peak), a memory stream about 192 W (memory rail 55 W, uncore
   40 W, 156.5 GB/s). Memory traffic, not the vector unit, drives the draw; the clock stayed at
   1.238 GHz and the die peaked at 72 C, no throttling (2026-11-08, one launch).

## 2026-11-11: settings shared with PhiWeather's lead on request (owner)

Sent directly: flat barrier wins (per-core 1.5-2.5x slower); DELAY 128 spin hint (siblings 1.01x vs up to 1.80x
without a hint); 200 ms spin (region entry 0.30 vs 3.75 ms after 10 ms gaps); our libgomp.so.1 should load
under GCC 5 objects (untested); prefetch L2 32 / L1 16 lines, 8-float rows 34%/20% faster; streaming stores
beyond 256 KB 15-31%; placement one place per core, OS core excluded; no AutoFDO path (no LBR, no perf); PGO
19-21% on branchy code; arena cap matters only for one process with many threads; subnormals free;
unaligned scalar x87 stores 8x slower.

**2026-11-11, answer to PhiWeather's prefetch-cost question (sent directly).** Our prefetch data is all
memory-bound; none covers instruction-bound, L2-resident loops. vprefetch0 pairs with a vector op for free
(C2), vprefetch1 costs about 2 core cycles; prefetch lost time on short loops (1.30x, now versioned), L1-only
prefetch, and aliased many-stream rows. Advised: one prefetch per line per stream, no clamps (versioned short
trips instead), L1 distance 4 lines at about 20 streams and 2 threads/core, then A/B none / both / vprefetch0-only per kernel.

**2026-11-11 16:45 EST, for PhiWeather's next session (their session was offline after the host reboot).**
2 MB pages are now available on the card, on demand: the owner set `nr_overcommit_hugepages` = 4096 (up to
8 GB, allocated only when asked, freed on exit; nothing reserved) and mounted hugetlbfs at `/mnt/huge`; MPSS
also mounts one at `/var/volatile/tmp/COI2MB`. Only code using `MAP_HUGETLB` or those mounts gets them; THP is
unchanged (`always`, never used). Lost at the next card reboot. Owner's instruction to both projects: start no
new work until the owner says usage has been reset.

MPSS libm `cbrtl` (long double cube root) segfaults on the card for many arguments, for example `cbrtl(1e-5)`:
`s_cbrtl.S:178` zero-extends a negative table offset and reads 4 GiB past the table (found by GCC-KNC S10-12,
2026-11-12). Double `cbrt` and `cbrtf` are not affected as far as we know. Avoid `cbrtl` on the card.

Host-card DMA, measured 2026-11-12 (GCC-KNC S11-01, idle card, SHA-256 checked, no bugcheck): the card's link is PCIe
Gen2 x4 (about 1.6-1.7 GB/s data per direction). Card to host: host-initiated `scif_readfrom` 1.67 GB/s (link limit).
Host to card: card-initiated `scif_readfrom` 1.35 GB/s, `scif_writeto` 1.0 GB/s. SCIF messages (0.1-0.2 MiB/s,
disconnect at 64 MiB) and `scif_mmap` (2.5-9 MiB/s) are not for bulk data. Raw TCP 174/320 MiB/s, SSH 11/17 MiB/s; the
host firewall blocks inbound TCP from the card. Safe practice: reusable 64 MiB registered windows, synchronous RMA,
explicit completion before reuse or unregister, in-memory SHA-256, bugcheck check between groups, no force-kill or
auto-retry of DMA. Sent to the WRF lead 2026-11-12 15:45 EST.

## 2026-11-16 - WRF 1.21x vs Sirocco: cause status (lead answer to PhiWeather)

1. Sirocco hand IMCI kernels (~4% wall): by design; M6 intrinsics header would allow them in C.
2. Short tiles (6-10 in i), masked epilogue gathers/scatters, x87 scalar tails: planned, GitHub #32 (M5) and S12-27 (Sprint 15).
3. Heap automatic arrays: known, not planned on the compiler side; twin can price it (S14-11 heap stubs); -fstack-arrays untested (card/OMP stack limits). In S14-30.
4. IEEE-strict math: by design (owner); vector libm S12-18 done, S12-20 contract M6.
5. mp_thompson vcvtps2pd: twin side done (S14-11, 0.4.0).
Missing: a like-for-like baseline (same source, GCC 5.1.1 without hand kernels, same thread layout) and per-routine profiles; -mphinix prefetch/unroll on short tiles. Ticket S14-30 attributes the gap first. Asked PhiWeather for Sirocco's compiler, flags, runtimes, threads per core, and per-routine profiles from the 25 h runs.
