# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-03 11:47.

**Next: GPT-6.1, on S2-11 (card_run follows the shared card rules and runs hello on the card).** Run `python tools/dispatch.py`, or ask the tech lead to.

Current tickets: `[################----]` 23 of 28

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 17 of 17 tickets |
| M1 | Mixed native code | In progress | 6 of 11 tickets |
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
| S2-06 | Atomics without cmpxchg16b, spin hint by delay | Done | Atomics on KNC now compile at every width with 16-byte operations routed to libatomic (no cmpxchg16b, fence... |
| S2-07 | GCC 16 builds its own static libgcc for k1om | Not started | Owner approved Sprint 2 on 2026-11-03; ticket set to ready. |
| S2-08 | hello, scalar FP and printf on the card | draft | Owner approved Sprint 2 on 2026-11-03; this ticket stays draft until the card hold ends. |
| S2-09 | GCC 16 builds gfortran, and the secondary-reload reproducer passes | Not started | Reconfiguring means one full rebuild: use `make -j8` with `CFLAGS=-O2 -g1 CXXFLAGS=-O2 -g1` as `tools/toolc... |
| S2-10 | First card runs for the queued native checks | Not started | Owner's decision of 2026-11-03: the interactive lead runs every card job; engineer sessions have no card ac... |
| S2-11 | card_run follows the shared card rules and runs hello on the card | Changes requested | Lead, under the owner's 2026-11-03 delegation: allow a sixth round for the cpuinfo snapshot cost found on t... |

## Recent activity

- 2026-11-03 11:47 **S2-11** owner decide: Lead, under the owner's 2026-11-03 delegation: allow a sixth round for the cpuinfo snapshot cost found on the card.
- 2026-11-03 11:47 **S2-11** lead escalate: over 2 review rounds: Native run of 5ede60d by the lead at the default 10 s (job claude-e5d2c8fb..., 11 s, receipt in the lead's scratchpad): the f...
- 2026-11-03 11:47 **S2-11** owner decide: Lead, under the owner's 2026-11-03 delegation: lead's native run follows as review changes.
- 2026-11-03 11:46 **S2-11** lead escalate: Review of 5ede60d is clean: owned_pid skips PID 2 and PPid-2 kernel threads by shell read before any readlink (T0 counts commands with 300 dangling...
- 2026-11-03 11:44 **S2-11** engineer submit: GREEN 5ede60d; RED bc5da64. Fixed kernel-thread forks in owned_pid and false faults after successful reconnect. Added dangling-link/300-thread comm...
- 2026-11-03 11:39 **S2-11** owner decide: Lead, under the owner's 2026-11-03 delegation: allow a fifth round for the two 11:38 findings (kernel-thread forks in owned_pid/stop_owned/reap, an...
- 2026-11-03 11:38 **S2-11** lead escalate: over 2 review rounds: Review of 24cefc3. The one-pass snapshot, named steps with stderr, the guarded reaper and the no-replay reconnect are sound. ...
- 2026-11-03 11:34 **S2-11** engineer submit: GREEN 24cefc3/27ef954; RED e1e5cf8/8ef9669. Snapshot command counts, named stderr diagnostics, confirmed faults, one guarded cleanup reconnect and ...

## Cost

- From the script, engineer: 96 sessions, 183.4M input tokens
- From the script, lead: 95 sessions, 34.7M input tokens
- Started by hand, Claude: 3 sessions, 259.7M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 7.8 GiB of 100 GiB. 332 GiB free on the drive.
