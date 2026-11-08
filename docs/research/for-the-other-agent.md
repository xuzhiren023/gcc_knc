# Findings worth passing to the other card agent

The owner asked on 2026-11-03 to be told of anything worth sharing with the other agent on the card
(GPT, PhiWeather's WRF-to-IMCI translation). The lead adds items here as they are found; the owner
passes on what they choose. Each item says how it was shown. Newest first.

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

00. **Masks never suppress page faults on KNC, and unaligned unpack/pack halves touch their whole line.** A card probe (3,148 cases, GCC 16, guard pages both sides) shows: `vloadunpackl*`/`vloadunpackh*` and the matching pack stores at a non-64-byte-aligned address fault on an unmapped line even when every lane there is masked off; the high half at a 64-byte-aligned address touches nothing; aligned `vmovap*` loads and stores with an empty mask fault on an unmapped page; a misaligned aligned load is SIGSEGV with `si_code=128`. This settles the fault footprint your catalog marks unqualified for these forms. Details: `C:/Users/xuzhi/Documents/gcc_knc/docs/research/knc-unaligned-probe.md`.

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
   (`mallopt` or `MALLOC_ARENA_MAX`). Fewer arenas may also mean more lock contention (2026-11-08,
   lead's diagnosis, not yet confirmed by the S8-01 rerun).
