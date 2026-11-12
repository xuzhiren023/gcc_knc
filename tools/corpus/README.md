# M4 corpus harness (S11-11)

Run `tools/corpus.py stage` with the shared Cygwin Python through `tools/run.py`.
Put `toolchain/cross/bin` and `toolchain/cygwin/bin` on PATH first. From a ticket
worktree, the Windows invocation is:

```
python.exe tools/run.py --name S11-11-stage --inputs tools/corpus.py tools/corpus -- ../_shared/toolchain/cygwin/bin/python3.12.exe tools/corpus.py stage
```

This extracts the read-only archives into `.work/_shared/corpus-build/sources`,
compiles each selected program with both installed compilers, lints each binary,
resolves its compiler runtimes with that compiler's driver, and stages under
`.work/_shared/S11-11`. Failures and diagnostic causes remain in `builds.json`;
the full commands and diagnostics are in the fixed per-build `build.log`.
Compilation stops at a failed program and continues with the rest of the corpus.
No source patches, warning suppression, compiler builds or target execution occur.
Use `stage --only NPB-IS` (or other program names) after a recipe correction to
rebuild just those programs and retain all other build records and frozen inputs.
The flag sets and repetitions must match the existing stage.

The **lead only** runs the staged `lead.ps1` through `tools/run.py` with Windows
Python and PowerShell. Windows Python is required by `card_run`'s Windows
OpenSSH transport and configuration paths. For example:

```
python.exe tools/run.py --name S11-11-card --inputs tools/corpus.py tools/corpus -- powershell -NoProfile -File ../_shared/S11-11/lead.ps1
```

It invokes `card_run --benchmark --threads 240` for an affinity probe, then for
every successful planned build. The native launcher counts physical cores in
the affinity granted by card_run using sysfs, and restricts the child to one
CPU per core, all 240 logical CPUs, or one CPU for serial programs. It sets
OpenMP's thread count, disables dynamic teams, and supplies `GOMP_CPU_AFFINITY`.
The actual CPU list, core count and requested threads are recorded per run.
The 240-thread case fails if fewer than 240 CPUs are available. There is no
hardcoded 60-core density. The runner currently reserves the whole card even
for serial launches so no concurrent timed job can spoil the comparison.

Only explicit `lead` launches card jobs. `stage` and `collect` never do.
The lead command needs this repository's `card_run` and connection configuration.
The staged script prefers the merged main checkout and falls back to the ticket
worktree before merge. Staged inputs and executables survive worktree deletion.

Baseline pair: `-O2`, and `-O2 -march=knc`. Extra sets are JSON, for example
`--extra-flags '{"gcc-5.1.1":[["-O3"]],"gcc-knc":[["-O3","-mphinix"]]}'`.
Each supplied set is a complete set; the baseline remains. Common workload
options such as `-fopenmp` and frozen dimension definitions are added equally.
Each compiler uses the libraries selected by its own installation, including
configured sysroot libraries; missing runtimes are recorded as build failures.
Nothing is borrowed from the other compiler prefix.

Three repetitions are the minimum. Each program/density is launched in pairs,
alternating donor-first and candidate-first. Extra sets are likewise interleaved.
The summary compares every donor/candidate flag combination within the same
program, input and density using the median of paired time ratios. Missing,
duplicate, unexpected, incorrect and failed launches remain failures. A failed
comparison has no speedup; an incomplete partition has no headline median.
The complete partition median weights every program/density/flag comparison
equally. Results from PB-adi, PB-durbin and all bzip2 variants are always held out
by program name, irrespective of labels supplied in result files.

Frozen workloads and checks:

| Program | Input | Correctness |
| --- | --- | --- |
| PB-gemm | NI=NJ=NK=512, double | numeric live-out checksums |
| PB-atax | M=N=4096, double | numeric live-out checksums |
| PB-cholesky, PB-ludcmp | N=512, double | numeric live-out checksums |
| PB-jacobi-2d | N=512, TSTEPS=100, double | numeric live-out checksums |
| PB-heat-3d | N=64, TSTEPS=40, double | numeric live-out checksums |
| PB-adi (held out) | N=256, TSTEPS=40, double | numeric live-out checksums |
| PB-durbin (held out) | N=8192, double | numeric live-out checksums |
| STREAM | three 16,777,216-element double arrays (384 MiB), 20 iterations | upstream validation |
| NPB CG, EP, MG, IS | class A, upstream deterministic input | upstream successful verification |
| HPCG | package reference 104 cubed, requested 60 seconds | upstream VALID report |
| zlib | 8 MiB fixed input, compression level 6 | full byte-for-byte round trip |
| bzip2 (held out) | same 8 MiB input, block size 9 | full byte-for-byte round trip |
| SQLite | staged `input.sql`, 100,000 rows, in-memory transaction | count and two integer sums independently checked |

PolyBench uses its deterministic initializer. Build-time dump interception reads
the unrounded live-out doubles, and emits per-array count, sum, sum of absolute
values, sum of squares and a position-weighted sum in long double. No packaged
source is edited. Between paired compilers, each finite checksum must satisfy
`abs(a-b) <= max(1e-10, 1e-8*max(abs(a),abs(b)))`; counts and array names must
match exactly. Missing/nonfinite output fails. A mismatch marks the candidate
JSONL row `fail` and prevents a speedup. These are numeric reductions, not file
hashes; no content hashes or provenance files are produced. They are a compact
correctness check, not a proof of elementwise equality.

The compression file is generated once on the host: unsigned 32-bit LCG seed 11,
multiplier 1664525, increment 1013904223. The first 1024 bytes of each 4096-byte
block use its high byte; the remainder repeats the literal in `corpus.py`.
No input is downloaded. Serial library drivers and unmodified PolyBench stay
on one CPU; the upstream OpenMP programs use both requested densities.

Timing uses native CLOCK_MONOTONIC around fork/exec/wait, excluding SSH and file
transfer and including whole-program initialization, computation and checks.
HPCG report copying is outside the timer. This is a short correctness/performance
comparison, not an official HPCG submission or a published STREAM rating.
NPB class A and HPCG reference allocations fit the 16 GiB card; STREAM's arrays
are several times its aggregate cache. Memory and runtime remain subject to the
lead's card execution, never inferred as passed from compilation.

The baseline has 138 launches plus one probe. Budget estimate: 70-110 minutes
including transfers, using 45-second per-program card limits and 180 seconds for
HPCG. This is an estimate, not a measured result; scheduler contention, staging
failures and unexpectedly slow programs are reported. PolyBench dimensions are
frozen here with a 1-10 second target; **native calibration is still needed**.
Do not change held-out inputs or tune from their timings. Larger extra flag sets
increase the budget. A native check that times out remains a failure.

`raw-results.jsonl` retains parsed individual observations. `collect` writes
`results.jsonl` with cross-compiler checks applied, `summary.json`, and a table
in `summary.md`. The fixed capture directory retains per-launch stdout/stderr,
including the HPCG validity report. Build failures generate a result for every
planned repetition; skipped builds are never silently dropped. Interrupted runs
can be collected, with every missing launch listed. All outputs overwrite their
previous locations, and no large input/output is committed.

Host acceptance (fake results only):

```
python tools/run.py --name S11-11-host --inputs tests/tools/test_corpus.py tools/corpus.py -- python -m unittest discover -s tests/tools -p test_corpus.py
```

Package source and licence notices remain intact in the shared extraction.
See `docs/research/corpus-and-coverage.md` for the frozen package versions and
licences. No held-out result may guide compiler tuning.
