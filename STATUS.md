# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 17:19.

**Waiting for you:** S1-04. Run `python tools/pm.py inbox`.

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
| S1-04 | -march=knc with no SSE, AVX, MMX, CMOV, FCOMI or MFENCE | **Waiting for you** | GPT's only shell (exec_command) returns within 30 s and needs write_stdin polling, so the 1-hour GCC rebuil... |
| S1-05 | Integer C assembles with as 2.22 and lints clean | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |
| S1-06 | K1OM link defaults | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |
| S1-07 | Milestone M0 evidence note | Not started | Rebuild GCC with the logged gcc16 step of tools/toolchain.py as ONE blocking foreground shell call with a t... |

## Recent activity

- 2026-11-02 17:19 **S1-04** lead escalate: GPT's only shell (exec_command) returns within 30 s and needs write_stdin polling, so the 1-hour GCC rebuild means about 120 polls, the pattern tha...
- 2026-11-02 17:18 **S1-04** engineer ask: Current shell is exec_command: no execution-timeout argument, Windows yield_time_ms capped at 30000 ms; long commands return session_id and require...
- 2026-11-02 17:17 **S1-04** owner decide: Owner on 2026-11-02: send S1-04 back to GPT with 6 sessions. Build with the shell tool and seed in i386-options.cc, per the lead notes at 16:25 and...
- 2026-11-02 16:35 **S1-04** lead note: Read ee7278c9dac and 7d860fac47a before any build: no defects found. The sync.md change is needed, not optional: on x86-64 GCC emits mfence wheneve...
- 2026-11-02 16:25 **S1-04** lead note: The 300 s limit is the node_repl MCP tool you used (spawnSync), not your shell. S1-02 ran its 59-minute build as an ordinary shell command: powersh...
- 2026-11-02 16:16 **S1-04** lead escalate: The engineer's shell tool stops every call at 300 s, so the required single blocking GCC rebuild (up to 75 min) cannot finish there; S1_04_gcc16_se...
- 2026-11-02 16:10 **S1-04** engineer ask: GCC implementation: ee7278c9dac; shared CMOV/MFENCE guards: 7d860fac47a. Foreground logged gcc16 --resume via spawnSync(timeout=4500000), tool time...
- 2026-11-02 16:00 **S1-04** lead approve-red: The S1-04 red tests are approved: they fail today because -march=knc does not exist yet, and they check its defaults, its macros, the five rejected...

## Cost

- From the script, engineer: 47 sessions, 57.5M input tokens
- From the script, lead: 48 sessions, 17.4M input tokens
- Started by hand, Claude: 3 sessions, 147.8M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 9.3 GiB of 100 GiB. 330 GiB free on the drive.
