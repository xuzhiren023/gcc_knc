# S9-19: auto-parallelization and AutoFDO on KNC (dumps and sources; card numbers pending)

Sources `tests/bench/autopar/loops.c`, `tests/bench/autofdo/perf_probe.c`; tool `tools/s9_19_auto.py`; `-O2 -march=knc`.

## 1. Auto-parallelization (`-ftree-parallelize-loops=N`)

Three `restrict` loops, no OpenMP: triad (run-time n), five-point stencil (fixed 4096 x 4096), double
dot product. One program holds par1 (off), par60, par120, par240 and omp60/120/240 (`#pragma omp
parallel for num_threads(T)`, `reduction(+:s)` for the dot product).

Opt-info (`.work/_shared/S9-19/optinfo.txt`, same at 60, 120, 240):

| loop | parallelized | why (`-fdump-tree-parloops-details`) |
|---|---|---|
| triad | yes, inner loop | independent iterations; restrict rules out overlap |
| stencil | yes, outer (row) loop | rows independent; the inner loop stays serial per thread and is vectorized |
| reduce | **no** | "detected reduction ... FAILED: it is not a part of reduction": `tree-parloops.cc` classes FP `+` as an in-order `FOLD_LEFT_REDUCTION` unless `-fassociative-math`, and will not reassociate it. With `-fassociative-math -fno-signed-zeros -fno-trapping-math` it is parallelized; that changes precision, so not a default. |

Outlined bodies lose `restrict`, so the vectorizer versions them for aliasing (cheap run-time check).

Timing (lead, several launches): `card_run --benchmark --timeout 1800 --file-list
.work/_shared/S9-19/autopar-files.txt .work/_shared/S9-19/autopar.sh`. Per kernel 11 rounds of all
seven variants shuffled: a checked warm-up call (settles the team size), then a ~100 ms batch.
`SUMMARY ratio_median` = ms/call(variant) / ms/call(par1). Passes: default placement, then
`OMP_PROC_BIND=spread OMP_PLACES=threads`. N=240 oversubscribes a 3120. Host x86: all variants
match the serial checksum (`.work/_state/logs/s9_19_host-20261110-193447.log`).

## 2. AutoFDO (`-fauto-profile`)

Our `k1om-mpss-linux-gcc` accepts `-fauto-profile=FILE`. The question is the profile.

**Card probe** (lead, read-only): `card_run --timeout 300 --file-list
.work/_shared/S9-19/probe-files.txt .work/_shared/S9-19/probe.sh`. It prints the perf sysctls,
event sources and any `perf` binary, then tries, as our user, counting, cycles sampling, cpu-clock
timer sampling and branch-stack sampling (errno, or count, samples and first IP).

**Branch records**, from ISA manual 327364-001 (the other sources in
`docs/research/knc-intrinsics-sources.md` do not cover the PMU):

- No last-branch-record facility is documented: "LBR", "last branch", "branch record" and
  `DEBUGCTL` do not occur in the manual.
- CPUID.01H:EDX bit 21 DS (the Debug Store buffer behind BTS and PEBS) returns 0 (Table B.9, p. 681);
  CPUID.01H:ECX DS-CPL and PDCM return 0 (Table B.10, p. 682). No BTS, no precise sampling.
- Two 40-bit counters per hardware thread, RDPMC (p. 667); SPFLT (p. 634) only gates them per thread.
- Kernel ABI: the MPSS sysroot is Linux 2.6.38 (`LINUX_VERSION_CODE` 132646); its
  `linux/perf_event.h` has no `PERF_SAMPLE_BRANCH_STACK` (Linux 3.4). The probe's last event checks it.

**Verdict: LBR-based AutoFDO is blocked** (hardware and kernel ABI). Left is **IP-only sampling**,
only if the probe shows cycles or cpu-clock samples reaching our user. It is weak: sample IPs give
approximate block counts but no edges or call targets (so no indirect-call promotion, S9-18's
`calls` case); no PEBS, so interrupt skid smears counts across blocks; sparse with two counters per
thread. There is probably no `perf` on the card, so we would need our own recorder (`perf_probe.c`
reads the ring) and a converter to `.afdo`; whether `create_gcov` accepts IP-only input was not
checked. Instrumented PGO (S9-18) remains the practical route. Fill in the probe lines when run.
