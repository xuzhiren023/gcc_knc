# GCC-KNC: current state

The handoff between sessions. `STATUS.md` holds tickets, cost and disk, and updates itself. This
file holds what only a person or an agent can know. Replace lines when facts change, and do not
trust anything here that a quick command can check instead.

Last updated: 2026-11-01, during Sprint 0.

## Proven, and how

| Claim | Evidence | Rerun with |
|---|---|---|
| The lint rejects the listed instructions and passes legal code | Rerun on `main`; four deliberate breaks to the lint were all caught by its tests | `python -m unittest tests.tools.test_knc_lint` |
| The harness enforces its limits | 51 tests in temporary repositories passed on `main` on 2026-11-01, after the lead fixed a test fixture that S0-03's merge broke | `python -m unittest discover -s tests/tools -p "test_*.py"` |
| Script sessions can write logs and shared builds | Two real Codex sessions, before and after the fix | Read `tools/dispatch.py`, `engineer_command` |
| S0-03 is merged: on the donor, T0 and T2 pass, T1 assembly and lint pass, T1 scans are red for "no packed `zmm` arithmetic", in 15 s; the T2 link traces libc and the loader under the shared sysroot | Lead rerun on `main` on 2026-11-01. The merged files match the commit the lead verified | `python tools/check t0 t1 t2` |
| The T1 and T2 scans can fail: `vsubrps` on `zmm`, an empty requirement list, a missing symbol and an unknown version all go red | Red commit `e6cb86a` fails and `9b04025` passes. Four deliberate breaks to `tools/check.py` in exported copies were all caught | `python tools/check t0` |
| S0-05's change count against the donor's recorded base: 85 files, 1498 insertions, 278 deletions | Lead reran the same diff in the donor checkout | `git diff --shortstat cfd753e87 af7cc04` in the donor checkout |
| GCC 16.2 is at `.work/_shared/gcc`, at tag `releases/gcc-16.2.0` (`78d4ac7`), with a clean status, autocrlf and fileMode off, and permissions the sandbox can write | Lead checks on 2026-11-01 after the clone. `origin` and `knc` are not set up yet; S0-06 does that | `git -C .work/_shared/gcc describe --tags --exact-match`, `icacls` on a file |
| GCC 16's secondary-move path only runs when both operands are registers, so the donor's memory-store failure cannot happen there unmodified | Lead read `gcc/lra-constraints.cc:1442-1443` and `4512-4514`. Source reading only, nothing compiled | Read those lines |
| The donor T2 symbol scan really checks something | On a real binary from the same objects it finds 8 required symbols at GLIBC_2.14 from `libc.so.6` | `readelf --dyn-syms` and `--version-info` on the linked program |
| The shared sysroot has five startup files byte-identical to the bootstrap copies, and its libc and loader differ from them | Lead byte comparison on 2026-11-01 | Compare `usr/lib64/crt1.o` and `lib64/libc-2.21.so` against the bootstrap sysroot |
| Empty `lib` and `usr/lib` fix the donor link failure | Applied to the shared sysroot by S0-03, and the link passes in the lead's rerun | `gcc --sysroot=<sysroot> -print-file-name=crt1.o` |

## Not proven yet

- **No GCC 16 has been built yet.** This project has produced tools, not compiler code. Milestone M0 is the first compiler result. The source is here, but S0-06 has not started, so there is no build, no measured time and nothing to push.
- **Nothing has run on the card.** S0-04 is the first native result. `tools/card_run` does not exist. Card minutes so far: 0.
- **S0-05 is unmerged and has no review.** Its branch answers everything except the `0002` reproducer. The lead checked the change count and spot-checked the LRA lines and five runtime citations, all correct, but did not review the port, rewrite or drop calls.
- **The `0002` reproducer does not exist.** Two reduction attempts lost the donor and reference difference, and nothing shows yet whether that difference is a bug. Nothing about it has been shown on GCC 16. E2-02 already requires the reproducer.
- **T1 cannot yet recognise a real KNC vector loop.** A correct loop closed by `jknzd` or `jkzd` fails the scan. S0-09 fixes this.
- **The toolchain still depends on PhiWeather's folder.** On 2026-11-01, `as`, `ld` and the default sysroot all still resolved there, and every link runs PhiWeather's `ld`. They are compiled in, and `-B` does not override them. S0-08 fixes this, and S0-04 waits for it.
- **The startup files from S0-03** come from the bootstrap sysroot. Only a run on the card will prove they suit the card's libc.

## Open items not on a ticket

- Cygwin tools run outside the Codex sandbox write their own permissions, which a sandboxed engineer cannot replace. `icacls` on `.work/_shared/check/donor/loops-off.o` shows this, and it cost one engineer session on 2026-11-01. Files with inherited permissions are fine, so create shared files outside the sandbox with native tools such as Git for Windows. `.work/_shared/check/donor` is stale and unused.
- The merge check misses harness tests. `pm.py approve` runs only `tools/check t0`, which leaves out `tests/tools/test_harness.py` by the lead's own scoping, so S0-03 merged with 2 harness tests failing. Lead-run sessions should run the whole `tests/tools` suite after a merge, or the check should include it.
- `tests/regress` needs Python 3.10 or later, because of `ignore_cleanup_errors`. It passes through `tools/check`, which uses Cygwin's 3.12, and errors under this machine's native Python 3.8. Run it through `tools/check`.
- A session limit raised on a ticket gets used up by questions as well as review rounds: each `pm.py ask` ends a session. S0-03 took 7 sessions against a limit that started at 3, and S0-05 used all 3 with an extra pass still asked for.
- Lead answers can keep a ticket going past what it needs. On 2026-11-01, script answers sent S0-05 back twice for a reproducer that the GCC 16 guard makes irrelevant until E2-02, which used 5 of the 12 approved sessions. Close optional items early, and bound them to one attempt.
- `pm.py submit` refuses an over-budget branch without saying `--override` exists (`tools/pm.py:303`). S0-03's engineer spent a session asking, despite two earlier answers telling it to use the flag. Have the refusal name the flag.
- The board takes tickets in ID order: S0-05, S0-06, S0-07, S0-08, S0-09, then S0-04, which waits for S0-08. With two sessions per ticket, reaching the card takes about 10 sessions.
- The dispatcher stops all work when any ticket needs the owner, by design. On 2026-11-01 this blocked S0-06 and S0-07 while they were free to run. `pm.py board` still names a next ticket, which the dispatcher will not start.
- `pm.py decide` on a ticket over its session budget does not free it: the next dispatch sends it straight back. Raise `sessions` on the ticket as well.
- `dispatch.py --dry-run` can change the board: the over-budget branch escalates and saves before the dry-run check (`tools/dispatch.py:133`). Found by reading, not run. Its test covers only a ticket under budget.
- An escalation made by the dispatcher is logged as "lead escalate", because `PM_ROLE` stays set from the previous session.

- `ldmxcsr` and `stmxcsr` pass the lint, because Intel manual 327364 is not on this machine. Decide once someone has Appendix B.
- `f3 2e 90`, a `pause` with a stray prefix in the middle, passes the lint. Hand-written code only.
- Script reviews cannot run tests, by design. `pm.py approve` now runs the branch's `tools/check t0` itself, once that tool exists on the branch.
- Script sessions have read 8.1M input tokens for GPT and 7.8M for Claude after 29 sessions. Review the balance at the Sprint 0 retro.
- Submit checks do not see `compiler/gcc`, which is a separate repository. Extend them in Sprint 1.

## Repositories

- This one: `xuzhiren023/gcc_knc`, private per the owner.
- GCC: `xuzhiren023/gcc_16_knc`, private per the owner, and empty until the owner pushes after S0-06.
- Only the owner pushes.

## Card

Approved by the owner on 2026-11-01. Native jobs run only when the card is idle, and only through
`tools/card_run` once S0-04 has reached that step. Rules are in `docs/DEVELOPMENT_CYCLE.md` section 9.

## Known limits

- Upstream binutils has no K1OM support, so LTO is out of scope.
- Sysroot redistribution review is open, so no release package may contain it.
