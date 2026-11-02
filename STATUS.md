# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-01 23:51.

**Next: the tech lead, on S0-05.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[######--------------]` 3 of 9

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 3 of 9 tickets |
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
| S0-03 | Test runner and red baseline | Done | tools/check now runs t0, t1 and t2 on the donor in about 16 seconds and records the expected baseline, with... |
| S0-04 | Card runner | Not started |  |
| S0-05 | Donor inventory | Question for the tech lead | Committed 3fec5cc: fixed GCC 16 citations; complete-flag full-source donor/reference compiles exit 0 with d... |
| S0-06 | GCC 16.2 fork and timing | Not started | Engineer sessions have no network, so do not clone. The owner or lead creates .work/_shared/gcc outside the... |
| S0-07 | Benchmark corpus and coverage estimate | Not started |  |
| S0-08 | Toolchain independent of PhiWeather | Not started | Also in scope, from the S0-03 review: nothing recreates the hand-made sysroot files (crt1.o, crti.o, crtn.o... |
| S0-09 | T1 scan sees KNC mask-branch loops | Not started |  |

## Recent activity

- 2026-11-01 23:51 **S0-05** engineer ask: Committed 3fec5cc: fixed GCC 16 citations; complete-flag full-source donor/reference compiles exit 0 with differing assembly. Extracted SUBMUSKINGC...
- 2026-11-01 23:46 **S0-05** lead answer: Do not wait on the owner: everything you asked for is on disk, read-only. Exact original compile command is recorded in C:/Users/xuzhi/Documents/Ph...
- 2026-11-01 23:44 **S0-05** engineer ask: Committed b04e492: GCC 16.2 F6 and LRA source audit complete; register-only guard excludes donor memory case. Reproducer unticked: two donor -O1 -S...
- 2026-11-01 23:39 **S0-05** lead answer: Unblocked: finish both open items on this branch. (1) Source: GCC 16.2 is at .work/_shared/gcc, read-only for you; do the F6 audit from it with fil...
- 2026-11-01 23:37 **S0-05** owner decide: Owner approved on 2026-11-01. GCC 16.2 is now at .work/_shared/gcc, at tag releases/gcc-16.2.0 (78d4ac7), with a clean status. The lead cloned it w...
- 2026-11-01 23:03 **S0-08** lead note: Also in scope, from the S0-03 review: nothing recreates the hand-made sysroot files (crt1.o, crti.o, crtn.o, libc.so and libc_nonshared.a in usr/li...
- 2026-11-01 23:03 **S0-06** lead note: Engineer sessions have no network, so do not clone. The owner or lead creates .work/_shared/gcc outside the sandbox with Git for Windows, which kee...
- 2026-11-01 22:57 **S0-05** lead escalate: Owner action: the engineer sandbox has no network, so S0-05 and S0-06 cannot get GCC 16.2. Keeping it closed, run once from the repo root, then pm....

## Cost

- From the script, engineer: 14 sessions, 8.1M input tokens
- From the script, lead: 14 sessions, 7.5M input tokens
- Started by hand, Claude: 2 sessions, 56.8M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 4.0 GiB of 100 GiB. 369 GiB free on the drive.
