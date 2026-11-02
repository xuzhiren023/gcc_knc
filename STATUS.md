# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-01 22:47.

**Next: the tech lead, on S0-03.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[#####---------------]` 2 of 8

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 2 of 8 tickets |
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
| S0-02 | ISA lint | Done | knc_lint now rejects the listed non-KNC instructions in .s, .o, archives, shared objects and executables, a... |
| S0-03 | Test runner and red baseline | Waiting for review | Review fixes complete: red e6cb86a, fix 9b04025. Donor run 15.85s: 14 T0 tests, assembly/lint/T2 PASS, only... |
| S0-04 | Card runner | Not started |  |
| S0-05 | Donor inventory | Not started |  |
| S0-06 | GCC 16.2 fork and timing | Not started |  |
| S0-07 | Benchmark corpus and coverage estimate | Not started |  |
| S0-08 | Toolchain independent of PhiWeather | Not started | Tested: `gcc -v` shows `--with-as`, `--with-ld` and `--with-sysroot` compiled in with PhiWeather paths, and... |

## Recent activity

- 2026-11-01 22:47 **S0-03** engineer submit: Review fixes complete: red e6cb86a, fix 9b04025. Donor run 15.85s: 14 T0 tests, assembly/lint/T2 PASS, only expected T1 vectorization red; baseline...
- 2026-11-01 22:47 **S0-03** owner decide: Owner raised sessions to 8 on 2026-11-01 and approved the remaining 10 sessions of the 12-session run. Change no code: submit with --override, as t...
- 2026-11-01 22:24 **S0-03** lead recommend: Owner: raise `sessions` to 8. Both review fixes are verified by the lead: red e6cb86a fails, 9b04025 passes, and four deliberate breaks were caught...
- 2026-11-01 22:21 **S0-03** lead escalate: budget: 6 engineer sessions used; the budget is 6
- 2026-11-01 22:21 **S0-03** lead answer: No budget raise. The 500-line budget is a soft limit that the override is built for: tools/pm.py:300 lets it through when you pass --override, and ...
- 2026-11-01 22:20 **S0-03** engineer ask: Both review fixes complete: red e6cb86a, fix 9b04025. Donor run 15.85s: 14 T0 tests, assembly/lint/T2 PASS, only expected T1 vectorization red; bas...
- 2026-11-01 22:19 **S0-03** lead note: Correction: the lead misread the owner. 12 is the cap on the dispatch run, not this ticket's limit, so the 'sessions to 12' decision entry above is...
- 2026-11-01 22:18 **S0-03** owner decide: Owner set sessions to 12 on 2026-11-01 and approved one more run. Make the two 22:01 review fixes, per the 22:03 lead note. This replaces the 22:03...

## Cost

- From the script, engineer: 10 sessions, 4.7M input tokens
- From the script, lead: 10 sessions, 5.3M input tokens
- Started by hand, Claude: 2 sessions, 52.8M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 1.8 GiB of 100 GiB. 366 GiB free on the drive.
