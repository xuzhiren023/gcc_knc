# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 07:50.

**Next: GPT-6.1, on S0-07 (Benchmark corpus and coverage estimate).** Run `python tools/dispatch.py`, or ask the tech lead to.

Current tickets: `[###########---------]` 5 of 9

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 5 of 9 tickets |
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
| S0-05 | Donor inventory | Done | The donor inventory now covers the whole tree with port/rewrite/drop decisions, the GCC 16.2 runtime audit ... |
| S0-06 | GCC 16.2 fork and timing | Done | GCC 16.2 is checked out on branch knc in the shared build area and builds stock x86_64 C+Fortran on Cygwin ... |
| S0-07 | Benchmark corpus and coverage estimate | Not started |  |
| S0-08 | Toolchain independent of PhiWeather | Not started | Also in scope, from the S0-03 review: nothing recreates the hand-made sysroot files (crt1.o, crti.o, crtn.o... |
| S0-09 | T1 scan sees KNC mask-branch loops | Not started |  |

## Recent activity

- 2026-11-02 07:50 **S0-06** lead approve: GCC 16.2 is checked out on branch knc in the shared build area and builds stock x86_64 C+Fortran on Cygwin (full 45 min, i386.cc rebuild 2.8 min, i...
- 2026-11-02 07:49 **S0-06** engineer submit: Acceptance met; commit aba96eb. GCC tag on knc, remotes configured, clean status, no case collisions or push. Cygwin GCC 14.4 C+Fortran all-gcc pas...
- 2026-11-02 06:52 **S0-05** lead approve: The donor inventory now covers the whole tree with port/rewrite/drop decisions, the GCC 16.2 runtime audit for SSE, pause, 16-byte atomics, __float...
- 2026-11-02 06:50 **S0-05** engineer submit: 09ba98c: inventory and self-contained drive_channel reproducer complete. Both compile-only checks exit 0; donor drops 4 address setups on 3 stores,...
- 2026-11-02 06:50 **S0-05** lead answer: No split and no budget change. The 979 lines are one research document plus the reduced reproducer, which I approved at any size. Submit 09ba98c wi...
- 2026-11-02 06:50 **S0-05** engineer ask: 09ba98c completes inventory and self-contained drive_channel reproducer. Both compilers exit 0; donor drops 4 address setups on 3 stores, reference...
- 2026-11-02 06:44 **S0-05** lead changes: (1) docs/research/donor-inventory.md: the benign conclusion is wrong. drive_channel_rsl is benign, but the donor drops the address reload on 4 dele...
- 2026-11-02 06:44 **S0-05** owner decide: Owner on 2026-11-02: yes, send S0-05 back for changes per the lead note at 00:20, and run the remaining 10 of the 12 sessions.

## Cost

- From the script, engineer: 18 sessions, 16.3M input tokens
- From the script, lead: 18 sessions, 10.0M input tokens
- Started by hand, Claude: 2 sessions, 64.1M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 6.3 GiB of 100 GiB. 363 GiB free on the drive.
