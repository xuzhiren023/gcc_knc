# GCC-KNC: current state

The handoff between sessions. `STATUS.md` holds tickets, cost and disk, and updates itself. This
file holds what only a person or an agent can know. Replace lines when facts change, and do not
trust anything here that a quick command can check instead.

Last updated: 2026-11-01, during Sprint 0.

## Proven, and how

| Claim | Evidence | Rerun with |
|---|---|---|
| The lint rejects the listed instructions and passes legal code | Rerun on `main`; four deliberate breaks to the lint were all caught by its tests | `python -m unittest tests.tools.test_knc_lint` |
| The harness enforces its limits | 40+ tests in temporary repositories | `python -m unittest discover -s tests/tools -p "test_*.py"` |
| Script sessions can write logs and shared builds | Two real Codex sessions, before and after the fix | Read `tools/dispatch.py`, `engineer_command` |

## Not proven yet

- **No GCC 16 exists yet.** This project has produced tools, not compiler code. Milestone M0 is the first compiler result.
- **Nothing has run on the card.** S0-04 is the first native result. Card minutes so far: 0.
- **The toolchain still depends on PhiWeather's folder.** S0-08 fixes this, and S0-04 waits for it.
- **The startup files from S0-03** come from the bootstrap sysroot. Only a run on the card will prove they suit the card's libc.

## Open items not on a ticket

- `ldmxcsr` and `stmxcsr` pass the lint, because Intel manual 327364 is not on this machine. Decide once someone has Appendix B.
- `f3 2e 90`, a `pause` with a stray prefix in the middle, passes the lint. Hand-written code only.
- Script reviews cannot run tests, by design. `pm.py approve` now runs the branch's `tools/check t0` itself, once that tool exists on the branch.
- Claude's script sessions read more tokens than GPT's: 3.1M against 2.3M after 12 sessions. Review this at the Sprint 0 retro.
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
