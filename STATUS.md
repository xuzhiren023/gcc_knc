# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 06:50.

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
| S0-05 | Donor inventory | Question for the tech lead | 09ba98c completes inventory and self-contained drive_channel reproducer. Both compilers exit 0; donor drops... |
| S0-06 | GCC 16.2 fork and timing | Not started | Engineer sessions have no network, so do not clone. The owner or lead creates .work/_shared/gcc outside the... |
| S0-07 | Benchmark corpus and coverage estimate | Not started |  |
| S0-08 | Toolchain independent of PhiWeather | Not started | Also in scope, from the S0-03 review: nothing recreates the hand-made sysroot files (crt1.o, crti.o, crtn.o... |
| S0-09 | T1 scan sees KNC mask-branch loops | Not started |  |

## Recent activity

- 2026-11-02 06:50 **S0-05** engineer ask: 09ba98c completes inventory and self-contained drive_channel reproducer. Both compilers exit 0; donor drops 4 address setups on 3 stores, reference...
- 2026-11-02 06:44 **S0-05** lead changes: (1) docs/research/donor-inventory.md: the benign conclusion is wrong. drive_channel_rsl is benign, but the donor drops the address reload on 4 dele...
- 2026-11-02 06:44 **S0-05** owner decide: Owner on 2026-11-02: yes, send S0-05 back for changes per the lead note at 00:20, and run the remaining 10 of the 12 sessions.
- 2026-11-02 00:20 **S0-05** lead note: Verdict: changes requested, once this leaves the inbox. The 00:16 review reached this but could not record it. The lead compiled the full source wi...
- 2026-11-02 00:16 **S0-05** lead escalate: lead session ended without a decision (exit 0)
- 2026-11-02 00:13 **S0-05** engineer submit: aa2a98f: both full-source -O1 -mknc -S reload-dump compiles exit 0; compared all 18 functions. Missing prologue load is in drive_channel_rsl: donor...
- 2026-11-02 00:10 **S0-05** owner decide: Owner on 2026-11-02: gave 12 more sessions to solve S0-05 first. The 0002 reproducer stays in scope and is not moved to E2-02, so the lead recommen...
- 2026-11-01 23:54 **S0-05** lead recommend: Owner: raise `sessions` to 4 for one submit-only session, and drop the extra pass in the 23:52 answer. The lead read gcc/lra-constraints.cc:1442-14...

## Cost

- From the script, engineer: 15 sessions, 8.8M input tokens
- From the script, lead: 16 sessions, 9.3M input tokens
- Started by hand, Claude: 2 sessions, 64.1M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 4.0 GiB of 100 GiB. 367 GiB free on the drive.
