# GCC-KNC: current state

The handoff between sessions. `STATUS.md` holds tickets, cost and disk, and updates itself. This
file holds what only a person or an agent can know. Replace lines when facts change, and do not
trust anything here that a quick command can check instead.

Last updated: 2026-11-01, during Sprint 0.

## Proven, and how

| Claim | Evidence | Rerun with |
|---|---|---|
| The lint rejects the listed instructions and passes legal code | Rerun on `main`; four deliberate breaks to the lint were all caught by its tests | `python -m unittest tests.tools.test_knc_lint` |
| The harness enforces its limits | 49 tests in temporary repositories passed on the 2026-11-01 handoff, including the approve check | `python -m unittest discover -s tests/tools -p "test_*.py"` |
| Script sessions can write logs and shared builds | Two real Codex sessions, before and after the fix | Read `tools/dispatch.py`, `engineer_command` |
| S0-03 branch, not merged: T0 passes, T1 assembly and lint pass, T1 scans are red for "no packed `zmm` arithmetic", in 17 s | Lead rerun on 2026-11-01. The branch is not reviewed yet, and T2 fails | In `.work/S0-03`: `python tools/check t0 t1 t2` |
| The shared sysroot has five startup files byte-identical to the bootstrap copies, and its libc and loader differ from them | Lead byte comparison on 2026-11-01 | Compare `usr/lib64/crt1.o` and `lib64/libc-2.21.so` against the bootstrap sysroot |
| Empty `lib` and `usr/lib` fix the donor link failure | Lead link in a throwaway sysroot exited 0, with a K1OM binary and the right interpreter. Not applied to the shared sysroot yet | `gcc --sysroot=<sysroot> -print-file-name=crt1.o` |

## Not proven yet

- **No GCC 16 exists yet.** This project has produced tools, not compiler code. Milestone M0 is the first compiler result. S0-06 has not started, so there is no checkout and no measured build time.
- **Nothing has run on the card.** S0-04 is the first native result. `tools/card_run` does not exist. Card minutes so far: 0.
- **T2 does not pass on the donor.** The shared sysroot lacks `lib` and `usr/lib`, and the trace parser needs a fix. Both are on S0-03.
- **The toolchain still depends on PhiWeather's folder.** On 2026-11-01, `as`, `ld` and the default sysroot all still resolved there, and every link runs PhiWeather's `ld`. They are compiled in, and `-B` does not override them. S0-08 fixes this, and S0-04 waits for it.
- **The startup files from S0-03** come from the bootstrap sysroot. Only a run on the card will prove they suit the card's libc.
- **The tests on the S0-03 branch** have run, but no review has checked their strength yet.

## Open items not on a ticket

- `tools/doctor` reports the sysroot OK while the compiler cannot find `crt1.o`, because it only checks that the file exists. S0-03 adds the two directories to that check.
- The dispatcher stops all work when any ticket needs the owner, by design. On 2026-11-01 this left 4 of 6 sessions unused while S0-05, S0-06 and S0-07 were free to run. `pm.py board` still says "Next: engineer on S0-05", which the dispatcher will not do.
- `pm.py decide` on a ticket over its session budget does not free it: the next dispatch sends it straight back. Raise `sessions` on the ticket as well.
- `dispatch.py --dry-run` can change the board: the over-budget branch escalates and saves before the dry-run check (`tools/dispatch.py:133`). Found by reading, not run. Its test covers only a ticket under budget.
- An escalation made by the dispatcher is logged as "lead escalate", because `PM_ROLE` stays set from the previous session.

- `ldmxcsr` and `stmxcsr` pass the lint, because Intel manual 327364 is not on this machine. Decide once someone has Appendix B.
- `f3 2e 90`, a `pause` with a stray prefix in the middle, passes the lint. Hand-written code only.
- Script reviews cannot run tests, by design. `pm.py approve` now runs the branch's `tools/check t0` itself, once that tool exists on the branch.
- Claude's script sessions read more tokens than GPT's: 3.7M against 2.9M after 14 sessions. Review this at the Sprint 0 retro.
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
