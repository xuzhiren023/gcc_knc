# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-03 13:10.

**Next: the tech lead, on S2-14.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[############--------]` 27 of 42

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 17 of 17 tickets |
| M1 | Mixed native code | In progress | 10 of 25 tickets |
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
| S0-04 | Card runner | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
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
| S2-02 | Float and double arguments and results in zmm lane 0 | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
| S2-03 | Varargs with the donor's register save area | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
| S2-04 | Scalar transfers through memory and mask scratch | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
| S2-05 | x87 compares and zmm spill alignment | Done | gcc16 now has tests proving it picks the IEEE-correct x87 compare for every float, double and long double c... |
| S2-06 | Atomics without cmpxchg16b, spin hint by delay | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
| S2-07 | GCC 16 builds its own static libgcc for k1om | In progress | Owner approved Sprint 2 on 2026-11-03; ticket set to ready. |
| S2-08 | hello, scalar FP and printf on the card | Not started | Rewritten now that the card is available: the engineer prepares, the lead runs (as in S2-10). Set ready by ... |
| S2-09 | GCC 16 builds gfortran, and the secondary-reload reproducer passes | Not started | Reconfiguring means one full rebuild: use `make -j8` with `CFLAGS=-O2 -g1 CXXFLAGS=-O2 -g1` as `tools/toolc... |
| S2-10 | First card runs for the queued native checks | Done | Ten programs ran on the shared Xeon Phi with output identical to their references: hello, the m1_affine fix... |
| S2-11 | card_run follows the shared card rules and runs hello on the card | Done | tools/card_run now runs programs on the shared Xeon Phi under the owner's card rules (ledger lines, cores 3... |
| S2-12 | card_run polls the card gently and reports what it reaped | Done | card_run now checks job status on its existing SSH session with backoff to 5 s and opens output connections... |
| S2-13 | Card tests pass again, and approve runs them | Done | All card tests in tests/tools pass again under Cygwin Python, and pm.py approve now refuses to merge any br... |
| S2-14 | card_run stages extra files, so one job can run a batch | Question for the tech lead | Applied 13:05 fixture-only translation: both fake shells use cwd=directory; only stage mkdir -p is relative... |
| S3-01 | Packed modes and IMCI patterns in GCC 16: entry points, audit and line estimate | draft |  |
| S3-02 | One helper for optional tools/check selections | draft |  |
| S3-03 | Native probe of unaligned pairs and masked aligned forms at page boundaries | draft |  |
| S3-04 | Packed modes legal under -march=knc, with aligned moves, spills and constants | draft |  |
| S3-05 | Unaligned packed moves through load and store pairs | draft |  |
| S3-06 | Packed FP add, sub, mul, FMA and broadcasts for V16SF and V8DF | draft |  |
| S3-07 | Auto-vectorization on zmm, with x87 peel and remainder; m1_affine T1 and T2 green | draft |  |
| S3-08 | Fortran twin of m1_affine vectorizes and links | draft |  |
| S3-09 | Packed integer add, sub, mul, logic and broadcast for V16SI; logic for V8DI | draft |  |
| S3-10 | Card batch for Sprint 3 and m1_affine | draft |  |
| S3-11 | Milestone M1 note: fixture, line counts, ICE classes and backend cost comparison | draft |  |

## Recent activity

- 2026-11-03 13:10 **S2-14** engineer ask: Applied 13:05 fixture-only translation: both fake shells use cwd=directory; only stage mkdir -p is relative, guards and /proc remain absolute. Cygw...
- 2026-11-03 13:07 **S2-14** owner decide: Lead, under the owner's 2026-11-03 delegation: input budget raised to 6M as well (the 13:06 decision raised only sessions). Continue per the 13:05 ...
- 2026-11-03 13:07 **S2-14** engineer escalate: budget: 2612700 input tokens used; the budget is 2000000
- 2026-11-03 13:06 **S2-14** owner decide: Lead, under the owner's 2026-11-03 delegation: 4 engineer sessions in total (2.6M tokens used). Follow the 13:05 answer: fixture-only change, keep ...
- 2026-11-03 13:05 **S2-14** lead escalate: budget: 2 engineer sessions used; the budget is 2
- 2026-11-03 13:05 **S2-14** lead answer: Yes, fixture only: keep the guard and /proc paths absolute and make only the stage mkdir -p relative (cwd=directory), so the stage step still lands...
- 2026-11-03 13:04 **S2-14** engineer ask: Both approved fixture attempts failed under Cygwin; no card access. cwd=directory plus /tmp->tmp and /proc/->proc/: 57/58 pass. ./tmp fallback: foc...
- 2026-11-03 13:01 **S2-14** lead answer: Test-fixture fix, no card_run change: in this test, run both fake shells (rpc's subprocess.run and the fake-ssh Popen) with cwd=directory, and make...

## Cost

- From the script, engineer: 107 sessions, 196.2M input tokens
- From the script, lead: 105 sessions, 37.3M input tokens
- Started by hand, Claude: 3 sessions, 317.6M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 7.8 GiB of 100 GiB. 329 GiB free on the drive.
