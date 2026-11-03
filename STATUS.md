# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 20:03.

**Next: the tech lead, on S1-04.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[###############-----]` 13 of 17

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 13 of 17 tickets |
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
| S0-04 | Card runner | Done | The card runner now safely runs one program on the card with a shared lock, refuses if anything foreign is ... |
| S0-05 | Donor inventory | Done | The donor inventory now covers the whole tree with port/rewrite/drop decisions, the GCC 16.2 runtime audit ... |
| S0-06 | GCC 16.2 fork and timing | Done | GCC 16.2 is checked out on branch knc in the shared build area and builds stock x86_64 C+Fortran on Cygwin ... |
| S0-07 | Benchmark corpus and coverage estimate | Done | We now have a proposed public benchmark corpus (PolyBench, STREAM, NPB, HPCG, zlib, SQLite, with bzip2 and ... |
| S0-08 | Toolchain independent of PhiWeather | Done | The shared k1om gcc, g++ and gfortran were rebuilt so their assembler, linker and sysroot all resolve insid... |
| S0-09 | T1 scan sees KNC mask-branch loops | Done | The T1 check now recognises KNC vector loops that close with the mask branches jknzd and jkzd, so correct G... |
| S0-10 | Card sysroot links Fortran, libm and pthreads | Done | Fortran programs and C programs using -lm, -lpthread, -ldl or -lrt now link with default flags against the ... |
| S1-01 | Tickets can change the GCC fork | Done | Tickets marked gcc: yes now get their own branch in the GCC fork, count its changes in the size budget, sho... |
| S1-02 | GCC 16.2 builds for k1om-mpss-linux | Done | GCC 16.2 now configures and builds its C compiler for k1om-mpss-linux, using the shared KNC assembler, link... |
| S1-03 | tools/check runs source-level tests against GCC 16 | Done | tools/check t1 --compiler gcc16 now compiles each tests/t1/*.c test and checks its scan, scan-not, per-func... |
| S1-04 | -march=knc with no SSE, AVX, MMX, CMOV, FCOMI or MFENCE | Waiting for review | 2545639 fixes scan-failure assembly/lint regression. tools/check t0 PASS (26 tests); gcc16 T1: all 12 sourc... |
| S1-05 | Integer C assembles with as 2.22 and lints clean | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |
| S1-06 | K1OM link defaults | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |
| S1-07 | Milestone M0 evidence note | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |

## Recent activity

- 2026-11-02 20:03 **S1-04** engineer submit: 2545639 fixes scan-failure assembly/lint regression. tools/check t0 PASS (26 tests); gcc16 T1: all 12 sources incl smoke PASS; affine scans remain ...
- 2026-11-02 19:59 **S1-04** lead changes: 1. tools/check.py:249 regresses t0: tests/regress/test_check.py:211 (test_scan_asm) fails because 'if not failures' now skips as --march=k1om and k...
- 2026-11-02 19:57 **S1-04** engineer submit: tools/check t1 --compiler gcc16: all 12 sources incl smoke PASS; affine scans are expected pre-E2 failures. CMOV seed caught cmovge; removed, rebui...
- 2026-11-02 19:35 **S1-04** lead note: new_test_files is now 11 in the front matter; the 19:23 answer said so, but a review session cannot edit files, so it was not set until now. Submit...
- 2026-11-02 19:23 **S1-04** lead answer: Yes: new_test_files is now 11 on the ticket, the approved red suite (defaults, two macro tests, five option rejections, three code tests); one file...
- 2026-11-02 19:23 **S1-04** engineer ask: Submit blocked: 11 new test files; budget 8, although all 11 red tests were approved at 16:00. May the budget be raised for this approved suite? 6a...
- 2026-11-02 19:09 **S1-04** lead answer: Accept equivalent KNC-safe forms; do not force donor forms in GCC. Branch direction is block layout, and GCC 16 may use the signalling fcompp for '...
- 2026-11-02 19:08 **S1-04** engineer ask: GCC fixes committed 04e646b1348; rebuild passed (35.6 min). Fixed filename false positives in instruction scans: 7bb554a. Two acceptance attempts f...

## Cost

- From the script, engineer: 52 sessions, 65.0M input tokens
- From the script, lead: 52 sessions, 19.4M input tokens
- Started by hand, Claude: 3 sessions, 174.8M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 9.3 GiB of 100 GiB. 327 GiB free on the drive.
