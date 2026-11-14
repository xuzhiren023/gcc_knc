# Sprint 11 batch check

GCC `knc`: `619e14b479a952edff32e94f22573710d0b8ac17`.
Project sources: `4669ddadfd9559fc8c3c15e8c89ee51be9f0491a` (includes the ready-ticket commit).
Lane 1's clean build stamp names `e0bc456a11e9`; its Git tree equals the final
`knc` tree, `08911b33207d841a0adcb91209764291d6a7a81d`.
No GCC source changes or GCC builds were made by this engineer.

## Host results

- T0 passed: 36 regression, 8 doctor, 6 portability and 6 lint unit tests.
  T1 passed all 327 reported checks. The engineer's combined run stopped in T2
  on permission denied replacing `_shared/S5-21/short-vector-O2-0.mic`.
  The lead subsequently ran
  `python tools/check.py t2 --compiler gcc16 --short-vector-abi`: 7/7 PASS,
  recorded in `_state/logs/check_gcc16_t2-20261114-115203.log` and confirmed
  on this ticket. That run covers the hidden result pointer, both caller/callee
  directions, ELF/interpreter and symbol versions. The engineer did not rerun
  the lead-owned outputs. These are host ABI checks, not native execution.
- ICE sweeps: O2 with `-ftree-vectorize` and O3 each examined 2,003 sources:
  1,969 pass, 32 compiler errors, 2 user-inline-assembly rejections; zero ICEs,
  hangs, assembler rejections outside user asm, lint or infrastructure failures.
  The runs took 9.8 and 8.7 minutes respectively. Detailed summaries are
  `_shared/S11-12/sweep-vect.txt` and `_shared/S11-12/sweep-O3.txt`.
- Execute corpus: 1,692 sources; 1,681 linked, including 118 with packed zmm
  instructions; 11 compile errors, zero ICEs, zero compile timeouts, zero link
  errors. All 1,681 binaries and the parallel suite driver passed instruction lint.
  Compile failures remain recorded in `_shared/S11-12/execute/build.tsv`.
- Vector math: host and KNC libraries and all three qualification programs built;
  KNC objects and executables passed lint. Benchmark built and passed lint;
  vector objects call all six expected library entry points, scalar objects none.
- Final prefix collection succeeded: both lanes have 26 vmath archive members
  and resolve libgcc, libgfortran, libstdc++, libatomic, libgomp and libknc_vmath.
  Both `--version` banners are `k1om-mpss-linux-gcc (GCC) 16.2.0`.
  Both compiler banners say GCC 16.2.0; they do not embed a Git revision.
  See `tests/baseline/S11-12-prefixes.txt` for source/runtime/library revisions,
  compiler configuration, library resolution and installed contents. Lane 2 was
  recorded last, after its final install. The lead's ticket answer identifies
  both installs as GCC `619e14b479a`; this revision attribution comes from the
  lead, not the compiler banner. Collection ran at project `fe2a3682`, which
  adds only this ticket's staging/report work to the source head above.

## Staged, not validated natively

`.work/_shared/S11-12/README.md` lists 107 separate `run.sh` entries with
scheduling estimates: execute (60 serial children over 60 physical cores), 97
qualification/control/compare jobs at 240 threads, and nine exclusive benchmark
jobs (three launches each at full/3100/5100, four workers/core).
The profiles use 240/224/236 workers; they do not emulate another card's clocks
or bandwidth. All binaries and entries are in the shared ticket directory.
Raw qualification dumps need the existing host/MPFR assessment before claiming
a numerical pass. No card job or x86 identity check was run by the engineer.

## Forward-port drill

After the lead refreshed upstream refs, the merge-tree drill completed against
master `fceddda853fa2543b6d3ddbbe75f7e2468521a91` (14 conflicting files)
and gcc-16 `0be7752b59a68e42415826e2632719ffbfe350c8` (four conflicting files).
`docs/research/S11-12-forward-port.md` records each conflict and upstream churn
in KNC-modified files. This is a conflict inventory, not a completed port or build.
Both refs contain PR128640; its ABI interaction is reviewed in that report.
The earlier engineer fetch failed on network access; the completed drill uses
the lead's refreshed refs. The lead runs the final-head x86 identity check.

All run logs are under `.work/_state/logs/`, with names beginning `S11_12_`.
The combined log is `S11_12_t0_t2-20261114-112050.log`; its detailed worker log
is `check_gcc16_t0_t1_t2-20261114-112051.log`. The sweep logs are
`S11_12_vector_ice_sweep-20261114-113432.log` and
`S11_12_O3_ice_sweep-20261114-113756.log`. Build/lint logs are
`S11_12_execute_build-20261114-112246.log`,
`S11_12_execute_lint-20261114-113214.log`,
`S11_12_vmath_build-20261114-112344.log`, and
`S11_12_vmath_timing_build-20261114-112852.log`.
Completion logs are `S11_12_drill-20261114-115624.log` and
`S11_12_final_prefixes-20261114-115624.log`.
The first sweep invocation was stopped: its Windows trampoline lost the imported
level override and selected default O0/O2/O2-g/O3. It has no sweep verdict.
The corrected invocations call Cygwin Python directly on
`_shared/S11-12/sweep.py`, selecting O2 and O3 separately, four workers each.
