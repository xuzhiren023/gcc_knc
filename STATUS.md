# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 11:28.

**Next: the tech lead, on S0-04.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[##############------]` 7 of 10

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 7 of 10 tickets |
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
| S0-04 | Card runner | Waiting for review | RED 07590f2 failed as expected: card_timeout 35.0 was not an int. GREEN ade6efe: nine T0 tests passed once ... |
| S0-05 | Donor inventory | Done | The donor inventory now covers the whole tree with port/rewrite/drop decisions, the GCC 16.2 runtime audit ... |
| S0-06 | GCC 16.2 fork and timing | Done | GCC 16.2 is checked out on branch knc in the shared build area and builds stock x86_64 C+Fortran on Cygwin ... |
| S0-07 | Benchmark corpus and coverage estimate | Done | We now have a proposed public benchmark corpus (PolyBench, STREAM, NPB, HPCG, zlib, SQLite, with bzip2 and ... |
| S0-08 | Toolchain independent of PhiWeather | Done | The shared k1om gcc, g++ and gfortran were rebuilt so their assembler, linker and sysroot all resolve insid... |
| S0-09 | T1 scan sees KNC mask-branch loops | Not started |  |
| S0-10 | Card sysroot links Fortran, libm and pthreads | Not started |  |

## Recent activity

- 2026-11-02 11:28 **S0-04** engineer submit: RED 07590f2 failed as expected: card_timeout 35.0 was not an int. GREEN ade6efe: nine T0 tests passed once through bootstrap Cygwin python3.12.exe ...
- 2026-11-02 11:27 **S0-04** lead changes: Lock, idle policy, boot guards, kernel-thread rule and the seven cases are sound. Two card-side fixes, both small, same test file, red then green: ...
- 2026-11-02 11:24 **S0-04** engineer submit: RED 8787e21 failed as expected for missing shared lock resolver, kernel classification and card-side limit. GREEN 9c96b5e: nine T0 cases passed onc...
- 2026-11-02 11:14 **S0-04** lead answer: Both answered. (1) The two ignore lines are approved, but .gitignore is protected and an engineer cannot submit a change to it. Drop the .gitignore...
- 2026-11-02 11:13 **S0-04** engineer ask: GREEN commit 9fa9ab4: seven T0 cases passed once via s0-04-green; log .work/_state/logs/s0_04_green-20261102-111228.log. Native acceptance remains ...
- 2026-11-02 11:06 **S0-04** lead approve-red: The card runner's safety contract and seven fake-card tests are approved, including the check that a process just outside our private run directory...
- 2026-11-02 11:05 **S0-04** engineer red: Review before GREEN: 476e656 adds requested cwd=run_dir+0 and other-run exe subcases, built from self.run_dir in the fake. Both require refused wit...
- 2026-11-02 11:03 **S0-04** lead changes: Spec and seven cases are sound and fail for the right reason. Both questions approved: creating the empty control dir before the first process chec...

## Cost

- From the script, engineer: 31 sessions, 28.4M input tokens
- From the script, lead: 32 sessions, 13.3M input tokens
- Started by hand, Claude: 3 sessions, 94.4M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 8.7 GiB of 100 GiB. 355 GiB free on the drive.
