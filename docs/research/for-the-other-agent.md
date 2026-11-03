# Findings worth passing to the other card agent

The owner asked on 2026-11-03 to be told of anything worth sharing with the other agent on the card
(GPT, PhiWeather's WRF-to-IMCI translation). The lead adds items here as they are found; the owner
passes on what they choose. Each item says how it was shown. Newest first.

## 2026-11-03

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
