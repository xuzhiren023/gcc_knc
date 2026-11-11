# S9-19: auto-parallelization and AutoFDO on KNC (build, dumps and sources; card numbers pending)

Sources: `tests/bench/autopar/loops.c`, `tests/bench/autofdo/perf_probe.c`. Tool: `tools/s9_19_auto.py`.
Prefix `gcc-knc-16.2.0`, all `-O2 -march=knc`.

## 1. Auto-parallelization (`-ftree-parallelize-loops=N`)

Three loops with `restrict` pointers, no OpenMP: triad `a[i] = b[i] + q*c[i]` (length n at run
time), a five-point stencil on a fixed 4096 x 4096 grid, and a double dot-product reduction.
Variants in one program: par1 (N=1, off), par60, par120, par240, and omp60/120/240 (the same loops
with `#pragma omp parallel for num_threads(T)`, `reduction(+:s)` for the dot product).

What GCC did (`-fopt-info-loop-optimized`, `.work/_shared/S9-19/optinfo.txt`; the same at 60, 120
and 240):

| loop | parallelized | why (parloops dump, `-fdump-tree-parloops-details`) |
|---|---|---|
| triad | yes, "parallelizing inner loop" | independent iterations; restrict proves no overlap |
| stencil | yes, "parallelizing outer loop" (the row loop) | rows independent; the inner loop stays serial inside each thread and is vectorized |
| reduce | **no** | "detected reduction ... FAILED: it is not a part of reduction". `tree-parloops.cc` classes a floating-point `+` reduction as in-order (`FOLD_LEFT_REDUCTION`) unless `-fassociative-math`, and refuses to parallelize those because it would reassociate the sum. With `-fassociative-math -fno-signed-zeros -fno-trapping-math` it is parallelized ("parallelizing inner loop 1"); that is a precision change, so not a default (AGENTS.md). |

Side effects seen in the opt-info: the outlined loop bodies lose `restrict`, so the vectorizer
versions them for aliasing ("loop versioned for vectorization because of possible aliasing", a
cheap run-time overlap check). parloops keeps a serial copy for short trip counts, which is
vectorized as before.

Timing (lead): `card_run --benchmark --timeout 1800 --file-list .work/_shared/S9-19/autopar-files.txt
.work/_shared/S9-19/autopar.sh`, in several launches. `autopar.mic` links `libgomp.so.1` (staged
next to it, rpath `$ORIGIN`). Per kernel, 11 rounds; each round runs all seven variants in a
shuffled order, an untimed warm-up call (it also checks the checksum and settles the thread team
size, which changes between variants), then a batch of about 100 ms sized per variant. `SUMMARY
ratio_median` is ms/call(variant) / ms/call(par1) in the same round. Two passes: libgomp's default
placement, then `OMP_PROC_BIND=spread OMP_PLACES=threads`. Data: n = 8M doubles (three 64 MB
arrays), grid 2 x 128 MB. N=240 oversubscribes a 3120 (228 threads); the script prints `nproc`.

Host check (x86, Cygwin gcc): all seven variants give the serial checksum for the three loops
(data are small integers, so every sum is exact in any order). Log
`.work/_state/logs/s9_19_host-20261110-193040.log`; x86 times are not results.

## 2. AutoFDO (`-fauto-profile`)

Compiler side: our `k1om-mpss-linux-gcc` accepts `-fauto-profile=FILE` (it tries to open the file).
The question is the profile.

**Card probe** (lead): `card_run --timeout 300 --file-list .work/_shared/S9-19/probe-files.txt
.work/_shared/S9-19/probe.sh`. Read-only. It prints `uname -r`, whether a `perf` binary exists,
`perf_event_paranoid`, `perf_event_mlock_kb`, `perf_event_max_sample_rate`, the
`/sys/bus/event_source/devices/` entries with their `type`, PMU symbol names in `/proc/kallsyms`,
the cpuinfo flags, then `perf_probe.mic`. That program opens, on its own thread, as our user:
counting cycles, instructions and branches; cycles sampling user-only and user+kernel (period
1000003, IP + TID); software cpu-clock sampling (period 100 us, the timer fallback); and cycles
sampling with the branch-stack sample bit (1 << 11). For each: the errno, or the count and the
number of `PERF_RECORD_SAMPLE` records in the ring buffer with the first IP.

**Branch records** (facts from the ISA manual 327364-001; no other source in
`docs/research/knc-intrinsics-sources.md` covers the PMU):

- The manual documents no last-branch-record facility. "LBR", "last branch", "branch record" and
  `IA32_DEBUGCTL` do not appear anywhere in it.
- CPUID.01H:EDX bit 21 (DS, Debug Store, the buffer used by BTS and PEBS) returns 0 (Table B.9,
  p. 681). CPUID.01H:ECX DS-CPL and PDCM return 0 (Table B.10, p. 682). So no branch trace store
  and no precise event sampling.
- Two performance counters per hardware thread, 40 bits, read with RDPMC (p. 667). SPFLT
  (p. 634) only gates those counters per thread from user code; it records nothing.
- The card's kernel ABI: the MPSS sysroot is Linux 2.6.38 (`LINUX_VERSION_CODE` 132646), and its
  `linux/perf_event.h` has no `PERF_SAMPLE_BRANCH_STACK` or `branch_sample_type` (added in Linux
  3.4). Even with LBR hardware, this kernel could not hand branch stacks to user space. The probe's
  last event checks that on the card.

**Verdict: AutoFDO as designed (LBR branch stacks) is blocked on KNC**, by the hardware (no
documented branch records, no DS) and by the kernel ABI. What is left is **IP-only sampling**, and
only if the probe shows cycles sampling (or the cpu-clock timer) delivering samples to our user:

- IP samples give per-instruction hit counts, hence approximate basic-block counts. They give no
  edge or call-target information: branch probabilities only where flow conservation pins them,
  and no indirect-call promotion (the source of S9-18's `calls` gain, if the card shows one).
- No PEBS means interrupt skid: on an in-order core the sampled IP lands some instructions after
  the event, smearing counts across block boundaries.
- Two counters per thread, one cycles sample per ~1M cycles: sparse profiles that need long runs.
- No `perf` binary is expected on the card (the probe reports it); we would need our own recorder
  (`perf_probe.c` already reads the ring buffer) and a converter to `.afdo`. Whether Google's
  `create_gcov` accepts IP-only input was not checked here.

So the realistic options are: instrumented PGO (`-fprofile-generate`/`-use`, which works, S9-18),
or, if the probe passes, a weak IP-only AutoFDO that is unlikely to beat static heuristics. Fill
in the probe's lines and the verdict line when the card has run it.
