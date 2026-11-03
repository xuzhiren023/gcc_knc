# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-03 10:14.

**Next: the tech lead, on S2-06.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[###############-----]` 22 of 28

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 17 of 17 tickets |
| M1 | Mixed native code | In progress | 5 of 11 tickets |
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
| S1-07 | Milestone M0 evidence note | Done | M0 is settled as adjust: GCC 16.2 builds a k1om cc1 whose assembly the 2.22 assembler accepts, an options-f... |
| S2-01 | Design for zmm and mask registers under -march=knc | Done | The register design for KNC is settled on paper: all 32 zmm and 8 mask registers become usable under -march... |
| S2-02 | Float and double arguments and results in zmm lane 0 | Done | GCC 16 for KNC now passes float and double arguments and results in zmm lane 0, puts them on the stack afte... |
| S2-03 | Varargs with the donor's register save area | Done | GCC 16 varargs functions now check %al and save the FP argument registers to the SysV save area at fp_offse... |
| S2-04 | Scalar transfers through memory and mask scratch | Done | Scalar values now move between general and vector registers through memory with an allocated mask scratch, ... |
| S2-05 | x87 compares and zmm spill alignment | Done | gcc16 now has tests proving it picks the IEEE-correct x87 compare for every float, double and long double c... |
| S2-06 | Atomics without cmpxchg16b, spin hint by delay | Question for the tech lead | Build and scoped T1/T2 pass; red 3fc86d7. Logs: .work/_state/logs/S2_06_*.log. Native via tools/card_run ex... |
| S2-07 | GCC 16 builds its own static libgcc for k1om | Not started | Owner approved Sprint 2 on 2026-11-03; ticket set to ready. |
| S2-08 | hello, scalar FP and printf on the card | draft | Owner approved Sprint 2 on 2026-11-03; this ticket stays draft until the card hold ends. |
| S2-09 | GCC 16 builds gfortran, and the secondary-reload reproducer passes | Not started | Reconfiguring means one full rebuild: use `make -j8` with `CFLAGS=-O2 -g1 CXXFLAGS=-O2 -g1` as `tools/toolc... |
| S2-10 | First card runs for the queued native checks | Not started | The owner supplied `config/card.local.json` on 2026-11-03 (git-ignored; the `knownHosts` file is read from ... |
| S2-11 | card_run works on the card's BusyBox and shares the card | Not started | Supersedes the 10:00 to 10:06 lock notes. The owner said card runs need no exclusive window, since the card... |

## Recent activity

- 2026-11-03 10:14 **S2-06** engineer ask: Build and scoped T1/T2 pass; red 3fc86d7. Logs: .work/_state/logs/S2_06_*.log. Native via tools/card_run exits 126: config/card.local.json missing;...
- 2026-11-03 10:10 **S2-11** lead note: Supersedes the 10:00 to 10:06 lock notes. The owner said card runs need no exclusive window, since the card runs Linux and our tests are small, so ...
- 2026-11-03 10:06 **S2-11** lead note: Correction to 10:02: if `flock` is missing on the card, nothing on the card can hold this lock by `flock` either, so take it by atomic create alone...
- 2026-11-03 10:02 **S2-11** lead note: The owner has no preference on the protocol, so the runner must be safe under both. Take: create the file atomically only if it is absent (`set -C`...
- 2026-11-03 10:02 **S2-10** lead note: The owner supplied `config/card.local.json` on 2026-11-03 (git-ignored; the `knownHosts` file is read from PhiWeather's folder, read only). It runs...
- 2026-11-03 10:00 **S2-11** lead note: Draft until the owner confirms how the WRF side holds this lock (by the file existing, or by `flock` on it); the lead sets it ready with that proto...
- 2026-11-03 09:40 **S2-10** lead note: Draft until the owner has filled in `config/card.local.json` (host, identity, knownHosts, and the WRF run's lock in `externalLocks`); the lead sets...
- 2026-11-03 09:38 **S2-05** lead approve: gcc16 now has tests proving it picks the IEEE-correct x87 compare for every float, double and long double comparison (quiet fucom for ==, != and is...

## Cost

- From the script, engineer: 84 sessions, 169.3M input tokens
- From the script, lead: 82 sessions, 30.6M input tokens
- Started by hand, Claude: 3 sessions, 232.6M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 7.7 GiB of 100 GiB. 306 GiB free on the drive.
