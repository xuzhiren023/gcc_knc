# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-01 20:09.

**Next: the tech lead, on S0-02.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

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
| S0-02 | ISA lint | Waiting for review | Parser regressions failed then passed; encoded rules and inline source/linked cases pass. Log: .work/_state... |
| S0-03 | Test runner and red baseline | Not started |  |
| S0-04 | Card runner | Not started |  |
| S0-05 | Donor inventory | Not started |  |
| S0-06 | GCC 16.2 fork and timing | Not started |  |
| S0-07 | Benchmark corpus and coverage estimate | Not started |  |

## Recent activity

- 2026-11-01 20:09 **S0-02** engineer submit: Parser regressions failed then passed; encoded rules and inline source/linked cases pass. Log: .work/_state/logs/S0_02_parser_green-20261101-200843...
- 2026-11-01 19:44 **S0-02** lead changes: Good work: all 21 fixtures, the binary path for every listed rule, error exits and the library scan all hold up on my rerun. Four fixes, all reprod...
- 2026-11-01 12:57 **S0-02** engineer submit: Prior T0 passed seeded rules and donor loops -O2 (host only); no reruns. Logs: .work/_state/logs/S0_02_t0-20261101-125051.log, S0_02_card_libraries...
- 2026-11-01 12:56 **S0-02** lead answer: Keep all the fixtures: 'one seeded file per rule' is my acceptance criterion, so the budget is the wrong limit here. Do not merge or drop any to ge...
- 2026-11-01 12:55 **S0-02** engineer ask: Submit refused: 22 new test files; budget is 4. Existing implementation b89a224 and red 233481a were retained; only S0-02-report.txt added in 80ed3...
- 2026-11-01 12:55 **S0-02** lead answer: No sandbox change: the owner would have to decide on widening it, and this step does not need it. run.py is for builds and tests, and this is a sin...
- 2026-11-01 12:53 **S0-02** engineer ask: Required runner blocked before objdump: python tools/run.py --name S0_02_pause_second_site --inputs tools/knc_lint -- ../_shared/toolchain/cross/bi...
- 2026-11-01 12:53 **S0-02** lead answer: Keep f3 90 a hard error: no libc exception, allowlist or flag in the tool. The manual lists PAUSE as unsupported, and a donor library containing it...

## Cost

- From the script, engineer: 4 sessions, 1.0M input tokens
- From the script, lead: 3 sessions, 1.0M input tokens
- Started by hand, Claude: 1 sessions, 43.0M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 1.8 GiB of 100 GiB. 376 GiB free on the drive.
