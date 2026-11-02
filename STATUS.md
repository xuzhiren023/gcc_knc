# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 15:54.

**Next: GPT-6.1, on S1-04 (-march=knc with no SSE, AVX, MMX, CMOV, FCOMI or MFENCE).** Run `python tools/dispatch.py`, or ask the tech lead to.

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
| S1-04 | -march=knc with no SSE, AVX, MMX, CMOV, FCOMI or MFENCE | In progress | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |
| S1-05 | Integer C assembles with as 2.22 and lints clean | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |
| S1-06 | K1OM link defaults | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |
| S1-07 | Milestone M0 evidence note | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |

## Recent activity

- 2026-11-02 15:50 **S1-03** lead approve: tools/check t1 --compiler gcc16 now compiles each tests/t1/*.c test and checks its scan, scan-not, per-function and expected-error directives, and ...
- 2026-11-02 15:50 **S1-03** owner decide: Owner on 2026-11-02: approve and merge S1-03 on the lead verification at 15:45 (smoke.c passes with GCC 16, donor matches baseline). No further eng...
- 2026-11-02 15:45 **S1-07** lead note: Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a timeout of at least 75 minutes, never in ...
- 2026-11-02 15:45 **S1-06** lead note: Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a timeout of at least 75 minutes, never in ...
- 2026-11-02 15:45 **S1-05** lead note: Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a timeout of at least 75 minutes, never in ...
- 2026-11-02 15:45 **S1-04** lead note: Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a timeout of at least 75 minutes, never in ...
- 2026-11-02 15:44 **S1-03** lead escalate: budget: 2 engineer sessions used; the budget is 2
- 2026-11-02 15:44 **S1-03** lead changes: 1. tests/t1/smoke.c:1 - gcc16 smoke acceptance is unverified: the lead's run of 'python tools/check t1 --compiler gcc16' was refused by the session...

## Cost

- From the script, engineer: 43 sessions, 53.3M input tokens
- From the script, lead: 44 sessions, 16.3M input tokens
- Started by hand, Claude: 3 sessions, 141.0M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 9.3 GiB of 100 GiB. 335 GiB free on the drive.
