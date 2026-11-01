# Sprint 0: The loop works

**Goal:** the test loop runs end to end against the donor compiler, `m1_affine` is
recorded red for the right reason, and we know the donor's real contents, GCC 16's real
build cost and the project's likely value.

**Cap:** two weeks. **Implementer:** GPT. **Reviewer:** Claude.

No GCC 16 target code is written in this sprint. All tools follow TDD: T0 tests first.

## Suggested order

S0-01 → S0-02 → S0-03 → S0-04. S0-05, S0-06 and S0-07 can run in parallel with these or
afterwards, and they do not depend on each other.

## Stories

### S0-01 Toolchain manifest and doctor (Light)

Read-only reuse of existing tools. Inputs from PhiWeather (never modified):

- Cross tools: `C:\Users\xuzhi\Documents\PhiWeather\.tools\knc-bootstrap\cross\bin` (donor GCC 5.1.1, `as` 2.22)
- Private Cygwin: `...\knc-bootstrap\cygwin\bin` (GCC 14.4). Must be on `PATH`, or `cc1` fails looking for `cygmpc-3.dll`
- Sysroot: `...\.tools\project-host\sysroot`

Acceptance:

- [ ] `toolchain/manifest.json` names each tool, path, version and role
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

**Spec and red tests are reviewed before GREEN.** Read how PhiWeather's card access and
lock work first (`scripts/AppScientificExecution.py` and `K1OM_REMOTE` are the starting
points) and post the proposed behaviour as a consult.

Acceptance:

- [ ] `tools/card_run` implements section 9 of the development cycle: lock and process checks, private directory, time limit, cleanup, boot ID, card minutes
- [ ] T0 tests with a fake transport cover: lock present, foreign process, timeout, card unreachable, reboot during a run, nonzero exit, and cleanup after failure
- [ ] It never takes action on a foreign process. It reports and refuses
- [ ] **Decision raised to the owner:** whether our runner should also hold PhiWeather's lock while running, so the app's dispatcher waits. Check what the app does if the lock appears, and do not write to that path until the owner agrees
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

### S0-07 Coverage estimate (Standard, research)

A cheap answer to "how much could this help?" before heavy investment. **Compile-only on
the host; no WRF execution on the host.**

Use the existing GCC 14 build (`.tools/project-host/compiler.json`), with AVX-512 flags as
a *proxy* for what a 512-bit target could vectorize, and `-fopt-info-vec-all` on WRF hot
files. Combine with whatever sampled profile is retained in PhiWeather. Some evidence was
cleaned up on 2026-11-01, so check what exists, and if nothing usable remains say so and
request a sampling run from the owner rather than guessing. Do the same at smaller scale
for a PhiChat region.

Deliverable: `docs/research/coverage-estimate.md`

Acceptance:

- [ ] For the top hot regions: share of step time, whether GCC vectorizes the loops, reason if not, whether the loops divide or call math functions, and typical trip counts where known
- [ ] An estimate of `f`, the accelerable fraction, as a range with assumptions spelled out, then run through the report's §13 model at plausible `S`
- [ ] Clear limits: AVX-512 vectorizes operations IMCI lacks, so this is an upper bound for legality and says nothing about profitability
- [ ] One-paragraph conclusion the owner can act on

## Sprint exit

- [ ] All stories approved and merged, or explicitly returned to the backlog
- [ ] `CURRENT_STATE.md` updated
- [ ] Sprint 1 refined from E1, using S0-05 and S0-06 findings
- [ ] Three-line retro below
- [ ] Owner has read the S0-07 conclusion, and confirms proceeding to S1

## Log

Evidence notes, consults and review verdicts are appended here, newest last.

*(empty)*

## Retro

*(at close)*
