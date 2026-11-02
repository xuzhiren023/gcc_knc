# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-01 20:20.

**Next: the tech lead, on S0-03.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[#####---------------]` 2 of 7

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 2 of 7 tickets |
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
| S0-03 | Test runner and red baseline | Question for the tech lead | Blocked by the lead's explicit sysroot comparison gate: direct byte comparisons (Path.read_bytes equality, ... |
| S0-04 | Card runner | Not started |  |
| S0-05 | Donor inventory | Not started |  |
| S0-06 | GCC 16.2 fork and timing | Not started |  |
| S0-07 | Benchmark corpus and coverage estimate | Not started |  |

## Recent activity

- 2026-11-01 20:20 **S0-03** engineer ask: Blocked by the lead's explicit sysroot comparison gate: direct byte comparisons (Path.read_bytes equality, no hashes) of PhiWeather/.tools/knc-boot...
- 2026-11-01 20:19 **S0-03** lead answer: Sysroot: yes, and the fault is in S0-01, which named the wrong source. project-host/sysroot has no development files. PhiWeather/.tools/knc-bootstr...
- 2026-11-01 20:16 **S0-03** engineer ask: Two attempts; commits b1ba718/035f80a. Cygwin run 62.38s: scanner seeds PASS, assembly/lint PASS, T1 expected red (no packed zmm arithmetic); tests...
- 2026-11-01 20:11 **S0-02** lead approve: knc_lint now rejects the listed non-KNC instructions in .s, .o, archives, shared objects and executables, and correctly flags 2 pause sites in libc...
- 2026-11-01 20:09 **S0-02** engineer submit: Parser regressions failed then passed; encoded rules and inline source/linked cases pass. Log: .work/_state/logs/S0_02_parser_green-20261101-200843...
- 2026-11-01 19:44 **S0-02** lead changes: Good work: all 21 fixtures, the binary path for every listed rule, error exits and the library scan all hold up on my rerun. Four fixes, all reprod...
- 2026-11-01 12:57 **S0-02** engineer submit: Prior T0 passed seeded rules and donor loops -O2 (host only); no reruns. Logs: .work/_state/logs/S0_02_t0-20261101-125051.log, S0_02_card_libraries...
- 2026-11-01 12:56 **S0-02** lead answer: Keep all the fixtures: 'one seeded file per rule' is my acceptance criterion, so the budget is the wrong limit here. Do not merge or drop any to ge...

## Cost

- From the script, engineer: 5 sessions, 2.1M input tokens
- From the script, lead: 5 sessions, 2.2M input tokens
- Started by hand, Claude: 1 sessions, 43.7M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 1.8 GiB of 100 GiB. 375 GiB free on the drive.
