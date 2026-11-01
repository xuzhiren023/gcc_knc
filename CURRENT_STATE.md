# GCC-KNC: current state

Single source of truth. Replace lines when facts change; history lives in git.
Last updated: 2026-11-01, kickoff.

## Status

| Area | State |
|---|---|
| Phase | M0 Foundation, Sprint 0 ready to start |
| Compiler | Nothing built yet. Donor GCC 5.1.1 is the reference |
| Acceptance | `m1_affine`: logic validated on host; donor expected red at T1. Not yet run on the card |
| Next gate | Gate A, at the end of Sprint 1 |
| Next step | GPT starts S0-01 (`docs/handoff/GPT_KICKOFF.md`) |

## Metrics

| Metric | Value |
|---|---|
| Tests T0 / T1 / T2 / T3 | None automated yet |
| Incremental rebuild + T1 | Not measured (S0-06) |
| Card minutes this sprint | 0 |
| Shared i386 lines changed | 0 |

## Card

Shared with PhiWeather, which has priority. This project has not used it. Rules are in
`docs/DEVELOPMENT_CYCLE.md` section 9, and no access is allowed before S0-04 is approved.

## Open owner decisions

See `docs/PROJECT_PLAN.md` section 10.

## Known limits

- Upstream binutils has no K1OM support, so LTO is out of scope.
- Sysroot redistribution review is open, so no release package may contain it.
