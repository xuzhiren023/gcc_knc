# M4 corpus harness v2 (S11-18)

Stage with the shared Cygwin Python through the run wrapper. Prepend the shared
`toolchain/cross/bin` and `toolchain/cygwin/bin` to PATH:

```
python tools/run.py --name S11-18-stage --inputs tools/corpus.py tools/corpus -- ../_shared/toolchain/cygwin/bin/python3.12.exe tools/corpus.py stage
```

The default stage is `.work/_shared/S11-18/`. Its `lead.ps1` invokes the explicit
`lead` subcommand with Windows Python, needed by card_run's transport. The lead
alone runs it, through `tools/run.py`. `stage` and `collect` never start card jobs
or GCC builds. Binaries are compiled and linted on the host; readiness is not a
native correctness result. `--only` rebuilds selected programs while retaining
settings and other build records.

Every program runs on the full 7120 and card_run profiles `3100` and `5100`.
The latter grant 56 and 59 compute cores; the full core count comes from a native
probe. Profiles constrain CPU availability and memory, not clock speed. Serial
launches pin one worker. OpenMP selects one, two or four logical CPUs per core,
with GOMP affinity and fixed teams. Timed launches reserve the card exclusively.

The owner's S11-18 rule makes serial builds of STREAM, NPB CG/EP/MG/IS and HPCG
primary for both compilers, without `-fopenmp`. GCC-KNC OpenMP builds run at all
three densities in a separate panel labelled
`the donor toolchain has no OpenMP runtime`. Donor OpenMP attempts and their
failures remain visible in builds.json but are not voting launches. Serial HPCG
also uses HPCG_NO_OPENMP. The sole corpus source change adds `n` to the
ComputeResidual.cpp default(none) shared list, identically for both compilers,
in build copies only. The package source tree is never modified.

SQLite retains the donor baseline failure and tries optimization levels in
descending order, selecting the highest that builds and passes binary lint.
Its primary row records actual flags, optimization-fallback variant and the
original failure reason. Failed alternatives remain visible. Baselines elsewhere
are `-O2` and `-O2 -march=knc`; extra flag sets remain supported.

Each successful build carries runtime-prefix.json: installed driver version,
binary and selected runtime ELF revision strings, selected library paths and
recursive DT_NEEDED graph. Missing revision strings are explicitly unavailable,
never inferred from the current source checkout. Card-supplied glibc's version
is captured at execution. Each compiler's driver selects its own runtimes.

The pilot defaults to three pairs; `lead --pairs 6` selects ADR-0015's gate
count without rebuilding. `--repetitions` remains an alias. The staged script
accepts `-Pairs 6`; its default is three. Orders alternate AB, BA, AB (A is the
donor), with adjacent members. Complete primary rounds traverse full/3100/5100
and the program order above before the OpenMP panels. Those panels contain only
GCC-KNC launches, with no fictitious donor pair. Records include pair_id,
start_order, launch_order, profile, variant, actual flags, input and run.
The pilot's baseline has 468 timed launches plus the probe; six pairs yield 936.
The original 4-7 hour estimate is provisional: serial NPB EP/CG/MG class A can
exceed 120 seconds on one KNC core. The pilot now allows 3600 seconds per launch,
configurable with `lead --timeout` or the script's `-TimeoutSeconds`. Record the
measured duration; the lead uses neutral feasibility, never speedup, to freeze
the gate's class. Timed-out attempts remain failures. Extra flags and long serial
runs extend the estimate; no native calibration has run.

PB-adi, PB-durbin and bzip2 are sealed by program name, ignoring caller labels.
Their builds, logs, plans, runtime records, captures, card transport records and
result rows live only under `.work/_shared/m4-sealed/S11-18/`. Public staging
reports readiness/failure, and collection reports per-program pass/fail for
these programs. Keep sealed storage accessible only to the lead/reviewer;
the harness routes access but does not administer host accounts or ACLs.

Frozen workloads and checks:

| Program | Input | Check |
| --- | --- | --- |
| PB-gemm | NI=NJ=NK=512, double | complete live-outs against donor |
| PB-atax | M=N=4096, double | complete live-outs against donor |
| PB-cholesky, PB-ludcmp | N=512, double | complete live-outs against donor |
| PB-jacobi-2d | N=512, TSTEPS=100, double | complete live-outs against donor |
| PB-heat-3d | N=64, TSTEPS=40, double | complete live-outs against donor |
| PB-adi | N=256, TSTEPS=40, double | complete live-outs; sealed |
| PB-durbin | N=8192, double | complete live-outs; sealed |
| STREAM | 3 x 16,777,216 doubles, 20 iterations | upstream reference validation |
| NPB CG/EP/MG/IS | class A | upstream reference verification |
| HPCG | reference 104 cubed, requested 60 seconds | upstream VALID report |
| zlib, bzip2 | fixed 8 MiB input, levels 6 and 9 | full round trip and other compiler decoding |
| SQLite | input.sql, 100,000 rows | independent integer reference for all query outputs |

PolyBench emits every unrounded live-out double with 17 significant digits,
after the timing boundary described below.
Array names, order and lengths must agree. Every finite element must satisfy
`abs(a-b) <= max(1e-10, 1e-8*max(abs(a),abs(b)))`; missing or nonfinite output
fails. The host corruption control permutes values while preserving all five
old reductions and must fail. Clean and within-tolerance controls pass.

Upstream reference tolerances are unchanged: STREAM's double validation uses
1e-13 relative average error; NPB CG uses 1e-10, EP and MG use 1e-8, and IS uses
exact integer verification. HPCG TestCG uses 1e-12 convergence tolerance and
TestSymmetry allows scaled departures up to 1 (normalized by DBL_EPSILON and
the vector/matrix norms). The upstream report must declare validity; all its
other validity conditions still apply. Sources: stream.c, NPB CG/cg.f90,
EP/verify.f90, MG/mg.f90, and HPCG TestCG.cpp/TestSymmetry.cpp. SQLite and
compression use exact comparisons, with no numeric tolerance.

Compression input is the frozen unsigned 32-bit LCG seed 11, multiplier 1664525,
increment 1013904223, using the fixed block pattern and literal in corpus.py.
After timing, the launcher runs the other compiler's decoder in an isolated
runtime directory on the actual compressed output. Both decoders compare every
byte with the original. The launcher then copies packed.bin to corrupt.bin,
flipping its first byte, and invokes that same peer decoder in control mode.
Only a decoder error or a full-output mismatch counts as rejection; file errors
do not. A clean control stream must be accepted by the decoder and therefore
fail the negative control. Cross-decoding and the corruption control must both pass.
The other compiler's first successful flag set supplies the reference decoder.

ADR-0015's raw score is launch-to-exit wall latency on CLOCK_MONOTONIC_RAW.
The resident launcher timestamps immediately before fork and immediately after
waitpid reaps the child. Startup, input reads, allocation, initialization, work,
local built-in checks, required output materialization, cleanup and exit all count.
There is no SIGSTOP boundary and no subtraction of built-in validation costs.
The child writes stdout/stderr to local files. PolyBench's interceptor writes
array names, counts and every raw double to arrays.bin. Compression writes both
packed.bin and restored.bin before exit. After CORPUS_TIME is recorded, the
supervisor transfers text and formats arrays as CORPUS_ARRAY lines. Cross-decoding
and corruption checks follow timing. Thus output is complete without timing
per-double decimal conversion or SSH transfer. No corpus source changes are needed.

Each row's time_seconds is the raw wall latency, with timing carrying the clock,
boundary, monotonic start/end nanoseconds, UTC start nanoseconds and clocksource.
Missing, inconsistent or legacy partial clock records fail. A child failure retains
its measured duration when timing metadata exists. Recognizable package-internal
timer lines are retained verbatim in secondary_timing_output, also preserved in
the original capture; they never replace time_seconds. No program timer is enabled
or synthesized where the package does not emit one.
This is not an official HPCG submission or published STREAM rating.

Each launch produces one raw JSON line, including build and transport failures.
`collect` writes checked results.jsonl and public status.json. Missing, duplicate
or incorrect launches fail. Scoring belongs to S11-14 / ADR-0015;
v2 collection emits no scores. The old summary helper remains a legacy API only.

Independent references before the gate (follow-up owned by the lead, per the
17:35 S11-18 answer; these are proposed checks, not implemented native passes):

| Program | Independent reference to freeze and validate |
| --- | --- |
| PB-gemm | Independently initialized matrices and high-precision direct matrix multiplication; every C element |
| PB-atax | Independent dense A*x and transpose(A)*temporary; every y element |
| PB-cholesky | High-precision scalar Cholesky; compare the live-out array and reconstruction residual |
| PB-ludcmp | High-precision independent LU and triangular solves; complete live-outs and solve residual |
| PB-jacobi-2d | Scalar reference with independent ping-pong grids, exact frozen boundaries and step count |
| PB-heat-3d | Scalar three-dimensional stencil reference with independent initialization and boundaries |
| PB-adi | Independent directional tridiagonal solves and boundary updates for every frozen step |
| PB-durbin | High-precision independent recurrence from the declared input; every live-out element |
| STREAM | Analytic recurrence for each array element after the exact warm-up and iteration count, replacing average-only validation |
| NPB-CG | NPB 3.4.2 class A packaged zeta reference and verification |
| NPB-EP | NPB 3.4.2 class A packaged Gaussian-sum references and verification |
| NPB-MG | NPB 3.4.2 class A packaged residual-norm reference and verification |
| NPB-IS | NPB 3.4.2 class A rank references and full integer verification |
| HPCG | HPCG 3.1 full TestCG/TestSymmetry and validity conditions; record actual iterations and require equal work |
| zlib | Original bytes as exact oracle; both peer decoding and an independent host zlib decoder |
| SQLite | Independent integer computation of every ordered query result, row count and transaction effect |
| bzip2 | Original bytes as exact oracle; peer decoding and independent host bzip2 decoder, all artifacts sealed |

The independent PolyBench and STREAM checks must use ADR-0015's frozen
`abs(actual-reference) <= 1e-8 + 1e-6*abs(reference)` with finiteness checked
first. The current pilot's stricter donor-comparison tolerance above is retained;
donor agreement alone is not independent-reference readiness. Packaged NPB/HPCG
tolerances stay unchanged and integer/byte results are exact. The follow-up must
exercise corruption through each checker family. HPCG's duration-driven work is
pilot-only until equal completed work can be established; six pairs alone do not
make this harness gate-ready. The lead must also freeze environment/inputs and
verify held-out ACLs before any gate run. Pilot timings cannot become gate samples.

Host acceptance (fixtures and host builds of harness C code; use shared Cygwin
Python and gcc, with the staged codec sources available):

```
python tools/run.py --name S11-18-green --inputs tests/tools/test_corpus_v2.py tools/corpus.py tools/corpus -- ../_shared/toolchain/cygwin/bin/python3.12.exe -m unittest discover -s tests/tools -p test_corpus_v2.py
```

Large outputs remain in fixed shared directories, overwriting prior versions.
Package licence notices remain intact. Host tests and staging claim no native pass.
