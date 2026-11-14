# S12-21 phase-one density and IMUL diagnostic

The lead authorized recovery into `.work/_shared/S12-21/r2/` after stopping
the duplicate session. The old mixed outputs under `.work/_shared/S12-21/`
remain untouched and must not be run. Stage, package and collect share one
output-directory constant. Staging refuses any nonempty destination before
building, preventing stale assembly from entering the census.

The recovered stage uses gzip and one copy of each runtime DSO to stay within
the card runner's 64 MiB payload limit. All 28 fresh builds and lints passed. The compressed payload is
16,328,655 bytes; package size and shell syntax checks passed during staging.

This phase uses the installed `gcc-knc-16.2.0` prefix and the fourteen
development programs only. There is no GCC source or default change.
The comparison is serial `-O2 -march=knc` versus the same flags plus
`--param=knc-threads-per-core=1`. The lead corrected the ticket's nonexistent
`-mknc-density` spelling during red review.

## Code census

`tools/s12_21_stage.py` builds and lints each variant once, retaining compiler
assembly under `.work/_shared/S12-21/r2/{default,density1}/PROGRAM/`.
`code-summary.json` records instruction counts, IMUL counts, backward loops,
and static loop-carried register counts. `code/PROGRAM.json` contains the
normalized instruction sequence per function, each IMUL's zero-based
instruction position, backward-loop intervals and their register sets, and
the changed instruction ranges for each variant.

Normalization removes assembler directives/comments and canonicalizes local
numeric labels by first use within each function. Function and data-symbol
names, instructions and operands remain. A sequence diff is computed per
function; each changed block contributes the larger of its two instruction
counts. The four programs with the largest totals are selected, with program
name as the deterministic tie-breaker. These are static code differences,
not hot-path weights or predictions of performance.

The chain count is explicitly a static recurrence census: within each
backward-branch interval, count registers read before their first write that
are also written in the interval. General-register width aliases are merged;
stack/frame pointers, flags, memory dependencies and implicit x87 stack state
are excluded. Nested loop intervals are counted separately. Vector-register
and IMUL-destination subsets are also recorded. This approximation does not
claim to recover GCC's chosen unroll factor, dynamic critical paths, or
path-sensitive data flow.

Recovered static census (each count pair is default / density 1):

| Program | Changed instructions | Instructions | IMUL | Register chains |
| --- | ---: | ---: | ---: | ---: |
| PB-gemm | 282 | 796 / 820 | 2 / 2 | 65 / 65 |
| PB-atax | 471 | 804 / 838 | 2 / 2 | 168 / 168 |
| PB-cholesky | 60 | 631 / 635 | 2 / 2 | 75 / 75 |
| PB-ludcmp | 778 | 1419 / 1088 | 2 / 2 | 268 / 163 |
| PB-jacobi-2d | 96 | 870 / 870 | 2 / 2 | 98 / 98 |
| PB-heat-3d | 157 | 796 / 796 | 2 / 2 | 198 / 198 |
| STREAM | 449 | 885 / 851 | 0 / 0 | 81 / 81 |
| NPB-CG | 3470 | 5155 / 5135 | 11 / 11 | 1663 / 1519 |
| NPB-EP | 147 | 1382 / 1387 | 11 / 11 | 95 / 95 |
| NPB-MG | 4249 | 9086 / 9011 | 64 / 65 | 2173 / 2147 |
| NPB-IS | 216 | 1310 / 1267 | 2 / 2 | 142 / 142 |
| HPCG | 1333 | 6701 / 6437 | 35 / 35 | 831 / 809 |
| zlib | 1041 | 11419 / 11419 | 19 / 19 | 2738 / 2738 |
| SQLite | 15191 | 171426 / 171601 | 529 / 529 | 37997 / 38078 |

## Staged card experiment

The lead entry point is `.work/_shared/S12-21/r2/batch.sh`, with `payload.tar.gz`
listed in `files.txt`. It uses one exclusive `full` reservation, a 1740-second
outer deadline, a 120-second IMUL deadline, and 24 workload deadlines of
60 seconds each (1560 seconds total inner deadlines). A timeout or nonzero
exit stops the batch. Fixed corpus sizes are retained; a workload that
cannot complete within its deadline requires lead review, not smaller input.

The IMUL executable pins itself to one granted CPU and reports actual
affinity, core/sibling topology, available frequency before/after, and timer
overhead. Its eight assembly kernels cover 32/64-bit register and hot-memory
operands, each with one dependent chain or eight independent chains. Each
iteration contains 64 multiplies; each case runs 200000 iterations after a
short warm-up, for three samples. Results are checked against modular
exponentiation outside the timed region. The disassembly is `imul.asm`.

Samples report serialized TSC ticks and `CLOCK_MONOTONIC_RAW` elapsed time.
Ticks/op include loop overhead; the back-to-back timer cost is reported and
not subtracted. Independent-stream ticks/op measure throughput, not latency.
TSC ticks must not be called core cycles without reviewing actual clock
conditions. Memory forms reuse one warmed operand and do not measure cache
miss latency. R02 p.56 motivates this experiment; no published ten-cycle
number is asserted as a native result.

The selected programs run three adjacent pairs, alternating default/density1,
density1/default, default/density1. The existing corpus launcher pins the
serial child to the first granted CPU, records launch-to-exit timing, and
preserves each program's correctness output. Both variants use the same
fixed input and runtime prefix. zlib additionally cross-decodes with the
opposite density build and rejects a corrupted stream.

After the lead saves combined stdout/stderr as `native.log`, the `collect`
subcommand rejects missing, duplicate, reordered or incomplete pairs and
IMUL samples, validates corpus correctness output, compares full PolyBench
arrays and HPCG work where applicable, and checks paired affinity. It writes
the three default/density1 time ratios and their median to
`native-analysis.json`. The lead must also review reservation/environment
evidence and variation before deciding whether phase two is justified.

From the project root, lead only:

```text
python tools/card_run --benchmark --profile full --threads 240 --timeout 1740 --file-list .work/_shared/S12-21/r2/files.txt .work/_shared/S12-21/r2/batch.sh
python tools/s12_21_stage.py collect .work/_shared/S12-21/r2/native.log
```

The four staging-contract tests passed, including rejection of an existing
assembly tree before building:
`.work/_state/logs/s12_21_r2_contracts-20261114-160635.log`.
The complete fresh stage passed in 5.7 minutes, building/linting all 28 serial
variants, the launcher and the eight-form IMUL executable, and generating the
census and compressed package:
`.work/_state/logs/s12_21_r2_stage-20261114-160641.log`.
The measured code-difference selection is SQLite, NPB-MG, NPB-CG and HPCG.
No card execution, native latency, speedup, or phase-two eligibility is
claimed. x86 identity and ICE sweeps are not phase-one checks.
