# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 21:49.

**Next: GPT-6.1, on S1-05 (Integer C assembles with as 2.22 and lints clean).** Run `python tools/dispatch.py`, or ask the tech lead to.

Current tickets: `[################----]` 14 of 17

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 14 of 17 tickets |
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
| S1-04 | -march=knc with no SSE, AVX, MMX, CMOV, FCOMI or MFENCE | Done | GCC 16 now accepts -march=knc (the k1om default): it predefines __KNC__ and no SSE/MMX/AVX macros, rejects ... |
| S1-05 | Integer C assembles with as 2.22 and lints clean | In progress | 1. tools/torture_compile.py:123 ignores the corpus's own dg-options/dg-additional-options, so 386-387 files... |
| S1-06 | K1OM link defaults | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |
| S1-07 | Milestone M0 evidence note | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |

## Recent activity

- 2026-11-02 21:48 **S1-05** lead changes: 1. tools/torture_compile.py:123 ignores the corpus's own dg-options/dg-additional-options, so 386-387 files per level (19% of the corpus) stop at f...
- 2026-11-02 21:47 **S1-05** engineer submit: Acceptance met in commits 393c13d / GCC a6f28997967: DWARF 4 red/green; GCC rebuild 2056.884s; full torture sweep 6009 measurements in 584.499s, ze...
- 2026-11-02 21:46 **S1-05** lead answer: Size is soft and the acceptance itself requires the full file lists, so keep the summary as is and submit with --override 'tests/baseline/gcc16-tor...
- 2026-11-02 21:46 **S1-05** engineer ask: Acceptance met: DWARF 4 red/green, rebuild 2056.884s, sweep 6009 measurements/584.499s with zero hang/ICE/as/lint/infra. Submit refused: 1743 lines...
- 2026-11-02 21:15 **S1-05** lead note: Owner chose DWARF 4 as the k1om -g default. Set it in linux-k1om.h (DWARF_VERSION_DEFAULT 4), red first with a tests/t1 case that reads the .debug_...
- 2026-11-02 21:05 **S1-05** lead note: Measured: the donor's -g default is DWARF 4; GCC 16's is DWARF 5, already without .file 0 (configure saw as 2.22), and it assembles, so the choice ...
- 2026-11-02 20:59 **S1-05** owner decide: Owner on 2026-11-02: DWARF 4 is the default for k1om, matching the donor; continue S1-05 per the lead note at 21:15.
- 2026-11-02 20:55 **S1-05** lead escalate: Owner: which debugger/version runs on the card (MPSS gdb 7.x, or none)? It sets the k1om default DWARF: GCC 16 uses DWARF 5 (.file 0, rejected by a...

## Cost

- From the script, engineer: 55 sessions, 72.2M input tokens
- From the script, lead: 56 sessions, 20.8M input tokens
- Started by hand, Claude: 3 sessions, 188.6M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 9.3 GiB of 100 GiB. 325 GiB free on the drive.
