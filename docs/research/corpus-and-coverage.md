# S0-07: public corpus and compile-side coverage

This is a compile-only baseline from 2026-11-02. No corpus program was executed,
on the host or on the card. The result supports a small, mixed public corpus;
it does not estimate speedup. **Loop counts do not equal time.** Runtime share
per region must come from card profiles in S6.

## Corpus proposal and licensing

Use the following frozen versions. The local primary sources are the lead's
read-only `.work/_shared/corpus/` packages, extracted into
`.work/_shared/tmp/S0-07/`. Source notices, rather than an external license
catalogue, were checked. No additional sources were fetched. Existing acquisition
information is in the lead's `corpus/SOURCES.txt`; no checksums were calculated or
copied into this deliverable, following AGENTS.md's prohibition on checksums.

| Package used | Language and workload | License evidence and conditions | Proposed status |
| --- | --- | --- | --- |
| `polybench-c-4.2.1-beta.tar.gz` | C; dense linear algebra, reductions, recurrences, stencils | `LICENSE.txt`: Ohio State University software distribution license; retain notices and disclaimer, reproduce them for binaries, no endorsement. Permissive, with indemnification language; retain the actual license rather than relabel it as BSD. | gemm, atax, cholesky, ludcmp, jacobi-2d, heat-3d for development; adi and durbin held out |
| `stream.c` revision 5.10 | C/OpenMP; copy, scale, add, triad, memory bandwidth | File lines 14–46: use, redistribution and modification permitted; publication naming and run-rule restrictions. These are compiler coverage counts, not published STREAM performance results. | Development baseline |
| `NPB3.4.2.tar.gz` | Fortran/OpenMP CG, EP, MG; C/OpenMP IS; sparse CG, random Gaussian generation, multigrid, integer sorting | Notices at the start of benchmark sources grant use, copying, distribution and modification for any purpose with or without fee; request reference to NPB 3.4; no warranty. | CG, EP, MG, IS for development; FT evaluated but deferred after setup failure |
| `hpcg-3.1.tar.gz` | C++/OpenMP; sparse matrix, symmetric Gauss–Seidel, multigrid, dot products | Root `COPYRIGHT`: three-clause BSD-style terms. Some setup makefiles retain an additional advertising acknowledgement; preserve those file notices too. | Conditional inclusion: fix upstream OpenMP build compatibility before full-program card use |
| `zlib-1.3.1.tar.gz` | C; DEFLATE, Huffman coding, checksums, branches and byte processing | `zlib.h` opening notice: zlib license; preserve notice, identify altered versions, do not misrepresent origin. | Compression library core for development; gzip file wrappers conditional on configuration |
| `sqlite-amalgamation-3460100.zip` (3.46.1) | C; SQL parsing, bytecode VM, B-trees and branch-heavy data management | `sqlite3.c` embedded source notices disclaim copyright (public domain). No separate restrictive license was found in the amalgamation. | Development; later card driver should include parsing plus in-memory SQL transactions |
| `bzip2-1.0.8.tar.gz` | C; block sorting, Huffman coding, integer compression/decompression | `LICENSE`: permissive bzip2 terms; retain notices, do not misrepresent origin, mark changes, no endorsement. | Entire library held out |

The held-out partition is fixed by program, not by input size: PolyBench adi and
durbin, and the entire bzip2 library. Their one baseline compile here is permitted;
their diagnostic details, source patterns and future profiles must never guide
tuning. Preserve this baseline and evaluate them only at a release gate after
freezing implementation choices. No compiler tuning was performed in this ticket.
The remaining PolyBench kernels and NPB BT, LU, SP, UA and DC are outside this
initial inexpensive sample, not additional claimed measurements.

For S6, propose deterministic rectangular arrays for the numeric kernels, the
upstream NPB class appropriate to card memory, HPCG's reference sparse problem,
and fixed text/binary compression inputs. Freeze inputs and correctness checks
before tuning. This ticket supplies compile coverage, not runtime drivers or
runtime results.

## Compilation and counting method

Compiler: shared Cygwin `gcc (GCC) 14.4.0`, with matching `gfortran` and `g++`.
All measured translation units used:

```
-O3 -march=skylake-avx512 -mprefer-vector-width=512
-fopt-info-vec-all -fdump-tree-vect-details -fdump-tree-cfg-lineno -c
```

No fast-math or reassociation flags were added. This stock x86 compiler is a
proxy, not the KNC compiler; its AVX/SSE target flags do not imply any change to
KNC's target flags. The vector-width preference requests 512 bits but permits
narrower vectors. Count all reported widths and show 64-byte vector loops
separately. A 64-byte success may also have a narrower vector remainder.

`tools/corpus_coverage.py` records each compiler command and stderr in the fixed
shared `coverage/<program>/` directory. STREAM, NPB and HPCG use `-fopenmp`;
HPCG additionally uses `-DHPCG_NO_MPI`. PolyBench uses `-DSMALL_DATASET` and its
utilities include directory. NPB's `setparams` configuration helper was built and
executed to generate class S parameters; **no NPB benchmark was executed**.
There was no linking, runtime validation, card use, native KNC compile, or
benchmark timing. Object compilation alone does not establish library/runtime
availability on the card.

Scope: PolyBench benchmark translation units include initialization and printing,
but not `utilities/polybench.c`. NPB includes each selected benchmark directory's
Fortran or C sources, including its data module and verification source where
present; common RNG, timers and result-reporting translation units are excluded.
HPCG includes all `src/*.cpp`, including reference routines, setup and tests.
zlib includes root `*.c`; SQLite includes only `sqlite3.c`, not the shell; bzip2
includes blocksort, huffman, crctable, randtable, compress, decompress and bzlib.
These are compile-side program/library samples, not isolated timed kernels.

`tools/corpus_summary.py` searches diagnostic records for `loop vectorized using`
and `couldn't vectorize loop`. The denominator is the union of reported
file:line:column locations, and the numerator is locations with at least one
successful loop-vectorization report. Repeated vector modes, clones and
epilogues at one location count once; basic-block SLP successes do not count.
Locations reported both successful and unsuccessful count successful. This is a
**diagnostic-location coverage estimate**, not a census of all source loops:
early elimination, unrolling, inlining and shared source locations affect it.
Unreported source loops are not silently classified as failures.

Rejection categories use the first subsequent missed diagnostic for each missed
loop report, deduplicated by location, and are tabulated only for locations with
no success. Categories can overlap when compiler clones give different reasons.
They summarize GCC's immediate explanation, not independently proved causes.
Control/form includes nested loops, multiple exits and unanalyzable trip counts;
operation/type includes unsupported statements, reductions and absent vector
types; calls/effects includes memory-clobbering calls; dependence includes
aliasing and recurrences. Other means the immediate message did not classify.

Division and math use a separate, earlier representation to avoid interpreting
repeated vectorizer diagnostics as operations. The summary reconstructs natural
loops from the early GIMPLE CFG's successor graph using dominators and backedges,
merging multiple latches at a common header. It counts loops whose blocks contain
explicit `/` GIMPLE operations (integer or floating point), and direct standard
math calls/builtins, including lowered `ABS_EXPR`. Enclosing loops count a nested
operation too. These **CFG counts have a different denominator** from diagnostic
locations. Constant divisions in initialization are included even if later
folded; indirect or out-of-line calls to user helpers are not followed. Counts
describe visible operations, not dynamic calls, precision, or required vector
divide support. OpenMP lowering and C++ template instances also affect counts.

## Results

The CFG columns give all reconstructed loops, loops with division, and loops with direct math, respectively. Reasons show numbers of rejected diagnostic locations, not statements or dynamic executions.

| Program | Compiled TUs / attempted | Vectorized / reported loop locations | 64-byte successes | CFG loops / divide / math | Top rejection categories (locations) |
| --- | ---: | ---: | ---: | ---: | --- |
| bzip2 (held out) | 7/7 | 18/192 (9.4%) | 15 | 216 / 8 / 0 | control/loop form: 129; dependence/alias: 20; operation/type/reduction: 16 |
| HPCG (partial) | 39/40 | 13/92 (14.1%) | 13 | 116 / 13 / 2 | control/loop form: 54; operation/type/reduction: 11; calls/memory effects: 7 |
| NPB-CG | 2/2 | 18/47 (38.3%) | 18 | 49 / 4 / 2 | control/loop form: 21; dependence/alias: 5; operation/type/reduction: 4 |
| NPB-EP | 3/3 | 2/9 (22.2%) | 2 | 10 / 3 / 2 | control/loop form: 4; calls/memory effects: 2; operation/type/reduction: 1 |
| NPB-FT (deferred) | 0/2 | unavailable | unavailable | unavailable | configuration failure |
| NPB-IS | 1/1 | 1/25 (4.0%) | 1 | 26 / 1 / 0 | control/loop form: 16; dependence/alias: 3; calls/memory effects: 3 |
| NPB-MG | 2/2 | 23/54 (42.6%) | 23 | 66 / 4 / 2 | control/loop form: 18; operation/type/reduction: 7; dependence/alias: 3 |
| PB-adi (held out) | 1/1 | 1/11 (9.1%) | 1 | 11 / 7 / 0 | control/loop form: 6; operation/type/reduction: 4 |
| PB-atax | 1/1 | 3/7 (42.9%) | 3 | 8 / 3 / 0 | control/loop form: 4 |
| PB-cholesky | 1/1 | 4/13 (30.8%) | 4 | 16 / 4 / 1 | control/loop form: 7; other/unspecified: 2 |
| PB-durbin (held out) | 1/1 | 3/5 (60.0%) | 3 | 6 / 1 / 0 | control/loop form: 2 |
| PB-gemm | 1/1 | 5/12 (41.7%) | 5 | 12 / 6 / 0 | control/loop form: 7 |
| PB-heat-3d | 1/1 | 3/13 (23.1%) | 3 | 13 / 3 / 0 | control/loop form: 7; other/unspecified: 3 |
| PB-jacobi-2d | 1/1 | 3/9 (33.3%) | 3 | 9 / 2 / 0 | control/loop form: 6 |
| PB-ludcmp | 1/1 | 9/18 (50.0%) | 9 | 21 / 6 / 0 | control/loop form: 6; other/unspecified: 3 |
| SQLite | 1/1 | 28/1505 (1.9%) | 25 | 1523 / 40 / 1 | control/loop form: 1254; operation/type/reduction: 111; dependence/alias: 70 |
| STREAM | 1/1 | 11/17 (64.7%) | 11 | 18 / 4 / 0 | control/loop form: 3; operation/type/reduction: 2; calls/memory effects: 1 |
| zlib (partial) | 12/15 | 13/134 (9.7%) | 12 | 140 / 0 / 0 | control/loop form: 74; operation/type/reduction: 38; dependence/alias: 6 |

FT is deferred rather than assigned zero coverage: `ft_data.f90` cannot find
the upstream-generated `blk_par.h`, and `ft.f90` consequently lacks `ft_data.mod`.
No FT loop diagnostics or division/math counts are available. This is a setup
failure, not evidence that FFT loops cannot vectorize.

HPCG is partial: `ComputeResidual.cpp:59` fails because `n` is absent from the
enclosing OpenMP `parallel default(none)` data-sharing clauses. zlib is partial:
`gzlib.c`, `gzread.c` and `gzwrite.c` fail GCC 14's implicit-function-declaration
checks for POSIX `lseek`, `read`, `write` and `close`; this direct compilation
did not run zlib configure or enable its unistd configuration. Do not treat this
as a zlib algorithm or KNC ISA failure. Their failed translation units are
excluded from the reported coverage. Per the ticket, failures were recorded and
the pass continued without source patches, warning suppression or repeated builds.

## Intrinsic and OS suitability

| Program(s) | Source inspection and build limitations |
| --- | --- |
| All eight selected PolyBench kernels | No modern x86 intrinsic requirement found. Standard C and libm; runtime utility timer uses `gettimeofday`. Host object success does not validate its allocation/timing support on the card. |
| STREAM | No modern x86 intrinsics found; uses OpenMP, `unistd.h`, `sys/time.h`, `gettimeofday`, standard math. Requires card OpenMP runtime and ordinary POSIX timing, not a new Linux-specific feature in the inspected source. |
| NPB CG, EP, MG, IS; FT candidate | No modern x86 intrinsics found in the OpenMP source. Requires Fortran runtime, OpenMP, IEEE arithmetic support and libm; the common default timer uses `gettimeofday`. The alternative SGI mmap timer was not selected. MPI sources were not selected. FT's missing generated header remains a configuration blocker. |
| HPCG | No x86 intrinsic requirement found in `src`. MPI is compiled out with `HPCG_NO_MPI`; OpenMP and C++ library support remain required. The existing default(none) source failure prevents claiming a complete build. MPI/multinode behavior has no coverage here. |
| zlib | Portable C path requires no x86 SIMD intrinsics. `crc32.c` contains guarded AArch64 CRC inline assembly, not an active x86 requirement. gzip wrappers need POSIX I/O declarations/configuration; core compression units compiled. Do not enable platform accelerator paths for KNC by inference. |
| SQLite | MSVC `intrin.h`/byte-swap intrinsics are guarded and inactive under GCC. Debug hardware timing has guarded x86 `rdtsc` inline assembly; this is not AVX-512 and is not evidence of KNC compatibility. POSIX VFS/thread code references pthreads, locking, mmap, dynamic loading and timers, including a guarded `clock_gettime` path with `gettimeofday` fallback. Card libc/VFS support remains unvalidated. A later in-memory driver can avoid filesystem workload dependence; select optional facilities explicitly against the card sysroot. |
| bzip2 library | No modern x86 intrinsics or new OS feature requirement found in the seven library sources. Uses standard C allocation and I/O; CLI/platform-specific front-end code was excluded. Card linking and correctness remain untested. |

The inspection searched source for SIMD intrinsics, intrinsic headers, inline
assembly and representative timing/thread/mapping APIs, then examined relevant
guards. It is not an exhaustive API audit or a card build. None of the measured
portable algorithms inherently requires AVX-512 intrinsics; host compiler
success with AVX-512 flags cannot prove absence of unsupported generated KNC
instructions or resolve card OS dependencies.

## Interpretation and limits

**AVX-512 vectorizes operations that IMCI lacks. This proxy is an optimistic
upper bound for legality and says nothing about KNC profitability.** It is not
a mathematical upper bound on every future compiler: target-independent
transformations and costing can also miss legal opportunities. In particular,
AVX-512 masks, integer operations, gathers, permutations, reductions and
divide/square-root support do not transfer automatically. A stock x86 cost model
does not model KNC spills, helper calls, memory traffic or instruction latencies.
Keep divide and square root scalar until their exact mode is proved correct;
these measurements justify neither implicit fast-math nor precision changes.

The sample is deliberately small and unweighted. Initializers, verification,
printing and template/library code can contribute loops but little runtime;
large scalar functions and eliminated loops can disappear from diagnostics.
Conversely a single sparse loop may dominate execution. No total loop percentage
is used as a claim about most programs, native correctness or speed. S6 must
measure card runtime share per region and visible scalar/vector costs before
prioritizing optimizations by time.

The broadest vector opportunity is regular numeric work: contiguous loads and
stores, simple arithmetic, stencils and independent inner loops. Sparse indexing,
recurrences, strict floating-point reductions, branches and calls reduce that
opportunity; integer compression and SQL favor scalar control flow, addressing,
register allocation and call quality in this compile sample. A small, correct
vector subset is therefore plausible for broad numeric gains, while scalar
quality has the widest applicability across this mixed corpus. Runtime evidence
is needed to choose their investment order or attach any speedup estimate.

## Run evidence

The compile pass was invoked through `tools/run.py`, once for STREAM to establish
the diagnostic format and once for the remaining sources. It continued through
candidate failures; its wrapper success means the survey finished, not that every
translation unit compiled. Raw compiler diagnostics and CFGs are outside git in
`.work/_shared/tmp/S0-07/coverage/`; commands are in each translation-unit log.
The report and the two small measurement scripts are the retained artifacts.

- STREAM wrapper: `PASS`, GCC 14.4.0, 1/1 translation unit compiled; log
  `.work/_state/logs/S0_07_stream-20261102-082510.log`.
- Remaining corpus wrapper: `PASS` survey completion in 5.2 minutes;
  FT 0/2, HPCG 39/40, zlib 12/15, all other attempted units compiled; log
  `.work/_state/logs/S0_07_corpus-20261102-082534.log`.
- Commands used the shared `toolchain/cygwin/bin/python3.12.exe` to run
  `tools/corpus_coverage.py ../_shared/tmp/S0-07 --only STREAM`, then the
  same script without `--only` (the script deliberately omits STREAM from that
  second pass). The native Windows Python invoked each through
  `python tools/run.py --name S0-07-stream|S0-07-corpus --inputs
  tools/corpus_coverage.py ../_shared/corpus -- <Cygwin Python command>`.
  The STREAM invocation's source input was specifically `corpus/stream.c`.
- `python tools/corpus_summary.py ../_shared/tmp/S0-07/coverage` searched
  diagnostics and CFGs after compilation. Failed units are excluded even when
  GCC emitted an early CFG before failing. This analysis does not execute code
  from the corpus. No compile pass was repeated.

