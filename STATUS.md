# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-01 23:03.

**Waiting for you:** S0-05. Run `python tools/pm.py inbox`.

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
| S0-05 | Donor inventory | **Waiting for you** | Owner action: the engineer sandbox has no network, so S0-05 and S0-06 cannot get GCC 16.2. Keeping it close... |
| S0-06 | GCC 16.2 fork and timing | Not started | Engineer sessions have no network, so do not clone. The owner or lead creates .work/_shared/gcc outside the... |
| S0-07 | Benchmark corpus and coverage estimate | Not started |  |
| S0-08 | Toolchain independent of PhiWeather | Not started | Also in scope, from the S0-03 review: nothing recreates the hand-made sysroot files (crt1.o, crti.o, crtn.o... |
| S0-09 | T1 scan sees KNC mask-branch loops | Not started |  |

## Recent activity

- 2026-11-01 23:03 **S0-08** lead note: Also in scope, from the S0-03 review: nothing recreates the hand-made sysroot files (crt1.o, crti.o, crtn.o, libc.so and libc_nonshared.a in usr/li...
- 2026-11-01 23:03 **S0-06** lead note: Engineer sessions have no network, so do not clone. The owner or lead creates .work/_shared/gcc outside the sandbox with Git for Windows, which kee...
- 2026-11-01 22:57 **S0-05** lead escalate: Owner action: the engineer sandbox has no network, so S0-05 and S0-06 cannot get GCC 16.2. Keeping it closed, run once from the repo root, then pm....
- 2026-11-01 22:54 **S0-05** engineer ask: Committed partial inventory d8d073c: docs/research/donor-inventory.md (85 changed paths against recorded gcc-5 r222343 base). Blocked: direct relea...
- 2026-11-01 22:49 **S0-03** lead approve: tools/check now runs t0, t1 and t2 on the donor in about 16 seconds and records the expected baseline, with T0, assembly, lint and T2 passing and o...
- 2026-11-01 22:47 **S0-03** engineer submit: Review fixes complete: red e6cb86a, fix 9b04025. Donor run 15.85s: 14 T0 tests, assembly/lint/T2 PASS, only expected T1 vectorization red; baseline...
- 2026-11-01 22:47 **S0-03** owner decide: Owner raised sessions to 8 on 2026-11-01 and approved the remaining 10 sessions of the 12-session run. Change no code: submit with --override, as t...
- 2026-11-01 22:24 **S0-03** lead recommend: Owner: raise `sessions` to 8. Both review fixes are verified by the lead: red e6cb86a fails, 9b04025 passes, and four deliberate breaks were caught...

## Cost

- From the script, engineer: 12 sessions, 5.8M input tokens
- From the script, lead: 12 sessions, 6.4M input tokens
- Started by hand, Claude: 2 sessions, 54.6M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 1.8 GiB of 100 GiB. 368 GiB free on the drive.
