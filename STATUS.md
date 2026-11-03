# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 22:59.

**Next: GPT-6.1, on S1-07 (Milestone M0 evidence note).** Run `python tools/dispatch.py`, or ask the tech lead to.

Current tickets: `[##################--]` 16 of 17

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 16 of 17 tickets |
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
| S1-05 | Integer C assembles with as 2.22 and lints clean | Done | All 2003 GCC torture compile files now build for KNC at -O0, -O2 and -O2 -g and assemble with the card's ol... |
| S1-06 | K1OM link defaults | Done | GCC 16 now targets the K1OM ABI by default: it passes --march=k1om to as and -m elf_k1om to ld, uses the /l... |
| S1-07 | Milestone M0 evidence note | Not started | The 15:45 note is wrong and replaced: your shell returns after 30 s, so start each build in the background ... |

## Recent activity

- 2026-11-02 22:59 **S1-06** lead approve: GCC 16 now targets the K1OM ABI by default: it passes --march=k1om to as and -m elf_k1om to ld, uses the /lib64/ld-linux-k1om.so.2 loader and 16-by...
- 2026-11-02 22:57 **S1-06** engineer submit: Red first and build-command harness red/green recorded. T1 PASS (prior session); T2 PASS now: ELF181, K1OM loader, glibc <=2.21, as/ld flags, only ...
- 2026-11-02 22:56 **S1-06** lead answer: Do not change the fork's link specs: -lgcc_s_asneeded and -latomic_asneeded are mainstream GCC 16 behavior (gcc.cc:1004 and init_gcc_specs), and th...
- 2026-11-02 22:55 **S1-06** engineer ask: Repro: tools/check t2 --compiler gcc16 --link-defaults. Two links fail on absent -lgcc_s_asneeded/-latomic_asneeded despite donor -B. K1OM as/ld/lo...
- 2026-11-02 22:35 **S1-07** lead note: The 15:45 note is wrong and replaced: your shell returns after 30 s, so start each build in the background and poll it quietly with write_stdin, do...
- 2026-11-02 22:26 **S1-05** lead approve: All 2003 GCC torture compile files now build for KNC at -O0, -O2 and -O2 -g and assemble with the card's old assembler with no crashes, hangs, asse...
- 2026-11-02 22:25 **S1-05** engineer submit: 75e803f: red/green; 6009 cases/808.426s; ICE/hang/as/lint/infra=0; user asm=2/level. Target diagnostics: pr106433,pr110386-2,pr89235,pr97576 (SSE f...
- 2026-11-02 22:20 **S1-06** lead note: The 15:45 note is wrong and replaced: your shell returns after 30 s, so a blocking call cannot work. Start the rebuild in the background and poll i...

## Cost

- From the script, engineer: 59 sessions, 81.9M input tokens
- From the script, lead: 59 sessions, 21.3M input tokens
- Started by hand, Claude: 3 sessions, 195.5M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 7.7 GiB of 100 GiB. 325 GiB free on the drive.
