# Sprint 0: The loop works

**Goal:** the test loop runs end to end against the donor compiler, `m1_affine` is
recorded red for the right reason, and we know the donor's real contents, GCC 16's real
build cost and the likely value across a general program corpus.

**Cap:** two weeks. No GCC 16 target code is written in this sprint.

The work is in tickets, in `work/tickets/S0-*.md`. Run `python tools/pm.py board` to see
where they stand. Tickets carry their own status and notes, so this file holds only the
goal and the exit conditions.

## Sprint exit

- [x] All stories approved and merged, or explicitly returned to the backlog (S0-01 to S0-10; S0-04's card run waits for the owner's card hold)
- [x] `CURRENT_STATE.md` updated
- [x] Sprint 1 refined from E1, using S0-05 and S0-06 findings (`SPRINT-01.md`, tickets in draft)
- [x] Three-line retro below
- [ ] Owner has approved the corpus and read the S0-07 conclusion, and confirms proceeding to S1

## Retro

- **Worked:** red-then-green held on every code ticket, and the lead's own reruns caught what reviews missed: the real `0002` failure, the Fortran link regression, and a card job that could outlive its connection.
- **Hurt:** sessions spent asking about things the lead could have settled in the ticket (no network, PhiWeather paths, Cygwin permissions), and a lead recommendation to drop the reproducer that the owner rightly overruled.
- **Change:** before a ticket goes ready, the lead checks its inputs exist where the sandbox can read them, and every acceptance names a check the lead can rerun.
