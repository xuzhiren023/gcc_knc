# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-03 07:20.

**Next: GPT-6.1, on S2-03 (Varargs with the donor's register save area).** Run `python tools/dispatch.py`, or ask the tech lead to.

Current tickets: `[###############-----]` 19 of 25

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 17 of 17 tickets |
| M1 | Mixed native code | In progress | 2 of 8 tickets |
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
| S2-03 | Varargs with the donor's register save area | In progress | Red proven: the new test shows GCC 16 varargs functions skip the AL check, the FP register saves and fp_off... |
| S2-04 | Scalar transfers through memory and mask scratch | Not started | Follow docs/adr/0004-knc-registers-and-scalar-abi.md, point 6: an allocated GPR scratch and an HI mask pseu... |
| S2-05 | x87 compares and zmm spill alignment | Not started | Follow docs/adr/0004-knc-registers-and-scalar-abi.md, point 2: XI spills need 64-byte storage. This ticket ... |
| S2-06 | Atomics without cmpxchg16b, spin hint by delay | Not started | Owner approved Sprint 2 on 2026-11-03; ticket set to ready. |
| S2-07 | GCC 16 builds its own static libgcc for k1om | Not started | Owner approved Sprint 2 on 2026-11-03; ticket set to ready. |
| S2-08 | hello, scalar FP and printf on the card | draft | Owner approved Sprint 2 on 2026-11-03; this ticket stays draft until the card hold ends. |

## Recent activity

- 2026-11-03 07:20 **S2-03** lead approve-red: Red proven: the new test shows GCC 16 varargs functions skip the AL check, the FP register saves and fp_offset=48 that the donor does, while AL at ...
- 2026-11-03 07:19 **S2-03** engineer red: 6ceebb8 [red]. Corrected T1 rerun: donor callers/callees pass at O0/O2, including AL=0/1/8 and overflow stack values; GCC16 callers pass. GCC16 cal...
- 2026-11-03 07:18 **S2-03** lead answer: Yes. T1 red is the red proof for this ticket. A link cannot see the save-area layout or %al, so passing T2 links before the change is expected and ...
- 2026-11-03 07:17 **S2-03** engineer ask: 6ceebb8 [red]. Reproducer: escaping va_list after va_start omits AL guard, all FP saves and fp_offset=48 on GCC16 -O0/-O2; donor passes. Both T2 cr...
- 2026-11-03 07:12 **S2-02** lead approve: GCC 16 for KNC now passes float and double arguments and results in zmm lane 0, puts them on the stack after eight, and passes double-float and flo...
- 2026-11-03 07:09 **S2-02** engineer submit: Red 5bbf4ca. Build PASS. Scalar T1/T2 all passed across full run plus focused 32-byte warning fix (final GCC 498234009a3). 6009 sweep on f9ce0e14db...
- 2026-11-03 06:50 **S2-02** lead changes: 1. gcc/config/i386/i386.cc:2262 (GCC cd59775df0a): the check rejects every VECTOR_TYPE with a non-vector mode, not only the XImode case S2-02 made ...
- 2026-11-03 06:47 **S2-02** engineer submit: Build PASS. All S2-02 scalar T1/T2 checks PASS; broader runner fails packed-vector scans and unbridged runtime link. 6009 sweep PASS: FP ABI/ICE/as...

## Cost

- From the script, engineer: 71 sessions, 129.4M input tokens
- From the script, lead: 70 sessions, 25.9M input tokens
- Started by hand, Claude: 3 sessions, 209.4M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 7.7 GiB of 100 GiB. 314 GiB free on the drive.
