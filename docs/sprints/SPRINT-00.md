# Sprint 0: The loop works

**Goal:** the test loop runs end to end against the donor compiler, `m1_affine` is
recorded red for the right reason, and we know the donor's real contents, GCC 16's real
build cost and the likely value across a general program corpus.

**Cap:** two weeks. **Implementer:** GPT. **Reviewer:** Claude.

No GCC 16 target code is written in this sprint. All tools follow TDD: T0 tests first.

## Suggested order

S0-01 → S0-02 → S0-03 → S0-04. S0-05, S0-06 and S0-07 can run in parallel with these or
afterwards, and they do not depend on each other.

## Stories

### S0-01 Toolchain manifest and doctor (Light)

This project is independent of PhiWeather, but the only local builds of these tools
happen to live in its folder. Use them read-only to bootstrap:

- Cross tools: `C:\Users\xuzhi\Documents\PhiWeather\.tools\knc-bootstrap\cross\bin` (donor GCC 5.1.1, `as` 2.22)
- Private Cygwin: `...\knc-bootstrap\cygwin\bin` (GCC 14.4). Must be on `PATH`, or `cc1` fails looking for `cygmpc-3.dll`
- Sysroot: `...\.tools\project-host\sysroot`

Acceptance:

- [ ] `toolchain/manifest.json` names each tool, path, version and role
- [ ] By sprint exit, the tools and sysroot are copied or rebuilt into this project's git-ignored `.tools/`, so nothing depends on the PhiWeather folder
- [ ] `tools/doctor` runs each tool, reports versions, and fails with a useful message on anything missing
- [ ] Also checks for `dejagnu` and `expect` availability; reports them as absent if so, and it is not a Sprint 0 failure
- [ ] Confirms in a sentence whether any usable KNC emulator exists (Intel SDE is the one to check), for `docs/research/`

### S0-02 ISA lint (Standard)

`tools/knc_lint` takes `.s`, `.o`, archives, shared objects or executables, and fails on
anything not legal on KNC.

Clean assembly is not sufficient, because `as --march=k1om` accepts `pause` although
the ISA manual lists it as unsupported. So the lint disassembles with the k1om `objdump`,
and applies a deny list derived from ISA reference 327364 Appendix B.

Acceptance:

- [ ] Rejects: any `xmm` or `ymm` register use; MMX; `cmov*`; `fcmov*`; `fcomi`, `fcomip`, `fucomi`, `fucomip`; `cmpxchg16b`; `pause` (encoded `f3 90`); `mfence`, `lfence`, `sfence`; `monitor`, `mwait`; `sysenter`, `sysexit`; `(bad)` decodes
- [ ] Reports file, symbol, address and instruction for each violation
- [ ] T0 tests: one seeded bad assembly file per rule, and known-good donor output passing (donor `loops.c` at `-O2`)
- [ ] **Run it over the card-derived `libc`, `libm`, `libgcc_s`, `libstdc++` and report results.** Anything flagged there needs explaining (the deny list or the library may be wrong). `rep; nop` in those libraries is a likely hit: find out what the lint should do with it, and raise it in a consult rather than deciding alone

### S0-03 Test runner and red baseline (Standard)

`tools/check` runs tiers `t0`, `t1`, `t2` (and later `t3`) over the acceptance fixtures and
`tests/regress/`, for a selectable compiler (`--compiler donor` now, `--compiler gcc16` later).

Acceptance:

- [ ] Implements every T1 and T2 check in `tests/acceptance/README.md`, with precise per-function scans
- [ ] Run against the donor: `m1_affine` T1 fails on the vectorization checks, for the reason "no packed `zmm` arithmetic"; assembly, lint and T2 pass
- [ ] Result recorded in `tests/baseline/donor-gcc5.txt`
- [ ] A seeded fake "passing" assembly file proves the T1 scan can go green, and a mutated one proves it can go red
- [ ] `tools/check t0 t1 t2` on the donor finishes in under 2 minutes

### S0-04 Card runner (Deep)

**Spec and red tests are reviewed before GREEN.** Existing card access on this machine is
a useful reference for connection details (`K1OM_REMOTE` in PhiWeather's scripts). Post the
proposed behaviour as a consult.

Acceptance:

- [ ] `tools/card_run` implements section 9 of the development cycle: lock and process checks, private directory, time limit, cleanup, boot ID, card minutes
- [ ] T0 tests with a fake transport cover: lock present, foreign process, timeout, card unreachable, reboot during a run, nonzero exit, and cleanup after failure
- [ ] It never takes action on a foreign process. It reports and refuses
- [ ] External locks are configuration, and the runner only reads them. It never writes to another project's lock path
- [ ] Once approved and the card is free: run the donor-built `m1_affine` at T3 and a `hello`. The expected output for `m1_affine` is `ACCEPT-PASS`, because scalar x87 loops should compute correctly. **That result validates the fixture and runner on real hardware, including guard pages**

### S0-05 Donor inventory (Standard)

Replaces guesswork with a list. The donor checkout has real history; find the FSF base
for `af7cc04` (or the nearest `gcc-5` branch point) and diff against it. If the history
does not make that possible, compare with the GCC 5.1.0 release tarball.

Deliverable: `docs/research/donor-inventory.md`

Acceptance:

- [ ] Covers **the entire tree**, not only `gcc/config/i386`: libgcc, libgomp, libstdc++, libgfortran, libatomic, libquadmath, libitm, top-level config
- [ ] Each KNC change is marked **port**, **rewrite** or **drop**, with a one-line reason and the GCC 16 location where it would land
- [ ] Separately lists runtime dependencies on SSE, `pause`, 16-byte atomics, `__float128` and MXCSR in GCC 16.2's own runtime sources (the review's F6)
- [ ] States how much vector code generation the donor has. Expected: none. Evidence if different
- [ ] States whether the secondary-reload mechanism from patch `0002` still exists in GCC 16's `lra-constraints.cc`, with the reproducer preserved in `tests/regress/`
- [ ] Records the `kmov` naming, `knc_cost`, stringop tables and other donor tuning worth keeping

### S0-06 GCC 16.2 fork and timing (Standard)

Follow ADR-0001. If the owner has not created the fork repository yet, use a local-only
clone and note it.

Acceptance:

- [ ] Tag `releases/gcc-16.2.0` checked out at `compiler/gcc` with `core.autocrlf=false` and `core.fileMode=false`, and a clean `git status`; case-collision check done
- [ ] Stock `x86_64` target `all-gcc` built under `build/` (git-ignored), C and Fortran front ends, with GCC 14.4 on Cygwin
- [ ] **Measured and recorded:** configure time, full `all-gcc` time, incremental rebuild after touching `i386.cc`, and a one-file `.md` change. Peak memory if practical
- [ ] Recommendation: does the T1 budget (≤ 5 min) look reachable on Cygwin? This feeds Gate A
- [ ] Does `config.sub` in GCC 16.2 still accept `k1om-mpss-linux`? Note the result without patching

### S0-07 Benchmark corpus and coverage estimate (Standard, research)

A cheap answer to "what would help most programs?" before heavy investment. Propose a
public corpus, then estimate compile-side coverage on the host. **Compile-only; corpus
programs are not benchmarked on the host.**

Candidates to evaluate, not yet chosen: PolyBench/C, STREAM, NAS Parallel Benchmarks, HPCG
(numeric, C, Fortran, C++, OpenMP), and zlib, SQLite and a compression or parsing workload
(integer and branch-heavy). Check each license and whether it builds without modern x86
intrinsics or newer OS features.

Use a stock modern GCC with AVX-512 flags as a *proxy* for what a 512-bit target could
vectorize, with `-fopt-info-vec-all`.

Deliverable: `docs/research/corpus-and-coverage.md`

Acceptance:

- [ ] Proposed corpus with license, language, workload type, and a held-out part never used for tuning
- [ ] For each program: share of loops vectorized, top reasons for rejection, how many loops divide or call math functions, and use of unsupported intrinsics or OS features
- [ ] Runtime share per region is taken from card profiles later, in S6. Until then, say plainly that loop counts do not equal time
- [ ] Clear limits: AVX-512 vectorizes operations IMCI lacks, so this is an upper bound for legality and says nothing about profitability
- [ ] One-paragraph conclusion on where broad gains are likely to come from, vector or scalar

## Sprint exit

- [ ] All stories approved and merged, or explicitly returned to the backlog
- [ ] `CURRENT_STATE.md` updated
- [ ] Sprint 1 refined from E1, using S0-05 and S0-06 findings
- [ ] Three-line retro below
- [ ] Owner has approved the corpus and read the S0-07 conclusion, and confirms proceeding to S1

## Log

Evidence notes, consults and review verdicts are appended here, newest last.

*(empty)*

## Retro

*(at close)*
