# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-01 12:55.

**Next: GPT-6.1, on S0-02 (ISA lint).** Start a new session and paste the prompt from `KICKOFF.md`.

Current tickets: `[##------------------]` 1 of 7

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 1 of 7 tickets |
| M1 | Mixed native code | Not started | Not planned in detail yet |
| M2 | Useful vector target | Not started | Not planned in detail yet |
| M3 | Runtimes | Not started | Not planned in detail yet |
| M4 | Broad optimization | Not started | Not planned in detail yet |
| M5 | Program corpus | Not started | Not planned in detail yet |
| M6 | Release | Not started | Not planned in detail yet |

## Tickets

| Ticket | What | State | Latest |
|---|---|---|---|
| S0-01 | Toolchain manifest and doctor | Done | Reviewed: red commit real; tests fail on the missing-tool cases; doctor rerun OK, required tools present, d... |
| S0-02 | ISA lint | In progress | No sandbox change: the owner would have to decide on widening it, and this step does not need it. run.py is... |
| S0-03 | Test runner and red baseline | Not started |  |
| S0-04 | Card runner | Not started |  |
| S0-05 | Donor inventory | Not started |  |
| S0-06 | GCC 16.2 fork and timing | Not started |  |
| S0-07 | Benchmark corpus and coverage estimate | Not started |  |

## Recent activity

- 2026-11-01 12:55 **S0-02** lead answer: No sandbox change: the owner would have to decide on widening it, and this step does not need it. run.py is for builds and tests, and this is a sin...
- 2026-11-01 12:53 **S0-02** engineer ask: Required runner blocked before objdump: python tools/run.py --name S0_02_pause_second_site --inputs tools/knc_lint -- ../_shared/toolchain/cross/bi...
- 2026-11-01 12:53 **S0-02** lead answer: Keep f3 90 a hard error: no libc exception, allowlist or flag in the tool. The manual lists PAUSE as unsupported, and a donor library containing it...
- 2026-11-01 12:52 **S0-02** engineer ask: Required consult: keep f3 90 (pause/rep; nop) a hard error, or allow a libc exception? Commits: red 233481a, implementation b89a224. T0 passed seed...
- 2026-11-01  **S0-01** lead approve: Reviewed: red commit real; tests fail on the missing-tool cases; doctor rerun OK, required tools present, dejagnu and expect absent as allowed; LTO...
- 2026-11-01  **S0-01** engineer submit: Submitted by the lead on the engineer's behalf, to save a session. Unit tests 2 pass; doctor rc 0 (run by the lead). | OVER BUDGET (211 changed lin...
- 2026-11-01  **S0-01** lead answer: Budget: do not split. 98 of the 211 lines are the manifest, which is data, so the limit is too tight rather than the ticket too big. Lead will subm...
- 2026-11-01  **S0-01** engineer ask: Commit d73fb9f implements the lead-approved manifest trim. Doctor passed once: .work/_state/logs/S0_01_doctor-20261101-123520.log in this worktree....

## Cost

- engineer: 1 sessions, 0.2M input tokens
- lead: 1 sessions, 0.3M input tokens
- Counts dispatcher sessions only, not sessions you start by hand.

## Disk

The project uses 1.8 GiB of 100 GiB. 376 GiB free on the drive.
