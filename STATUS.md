# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 10:37.

**Next: the tech lead, on S0-04.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[###############-----]` 7 of 9

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 7 of 9 tickets |
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
| S0-04 | Card runner | Question for the tech lead | Consult: approve exclusive own lock; read-only external locks; fail closed on foreign/unknown processes; re... |
| S0-05 | Donor inventory | Done | The donor inventory now covers the whole tree with port/rewrite/drop decisions, the GCC 16.2 runtime audit ... |
| S0-06 | GCC 16.2 fork and timing | Done | GCC 16.2 is checked out on branch knc in the shared build area and builds stock x86_64 C+Fortran on Cygwin ... |
| S0-07 | Benchmark corpus and coverage estimate | Done | We now have a proposed public benchmark corpus (PolyBench, STREAM, NPB, HPCG, zlib, SQLite, with bzip2 and ... |
| S0-08 | Toolchain independent of PhiWeather | Done | The shared k1om gcc, g++ and gfortran were rebuilt so their assembler, linker and sysroot all resolve insid... |
| S0-09 | T1 scan sees KNC mask-branch loops | Not started |  |

## Recent activity

- 2026-11-02 10:37 **S0-04** engineer ask: Consult: approve exclusive own lock; read-only external locks; fail closed on foreign/unknown processes; recheck idle before execution; private sta...
- 2026-11-02 10:36 **S0-08** lead approve: The shared k1om gcc, g++ and gfortran were rebuilt so their assembler, linker and sysroot all resolve inside our own toolchain, a C program now lin...
- 2026-11-02 10:34 **S0-08** engineer submit: 43f3643 scripts staged install-gcc, Windows overlay preserving target libs, and stage removal. Install PASS: .work/_state/logs/s0_08_install-202611...
- 2026-11-02 10:27 **S0-08** lead answer: Authorized: use /tmp/knc-stage in the shared Cygwin. My 'outside C:\Users' was imprecise; what matters is that the Cygwin path mkdir -p walks does ...
- 2026-11-02 10:26 **S0-08** engineer ask: Staging scope conflict: cygpath -w /tmp/knc-stage resolves to C:\Users\xuzhi\Documents\gcc_knc\.work\_shared\toolchain\cygwin\tmp\knc-stage. TEMP/T...
- 2026-11-02 10:24 **S0-08** lead answer: Not an environment problem to escalate: Cygwin mkdir -p walks every path component and gets EACCES on C:\Users\xuzhi, which already exists. Install...
- 2026-11-02 10:24 **S0-08** engineer ask: all-gcc passed with authorized dup3=no and host C++98 (7cf5e89, 23d445f). install-gcc failed: fixincludes mkinstalldirs runs mkdir -p for shared cr...
- 2026-11-02 09:33 **S0-08** lead answer: Authorized, no source edits: in the rebuild step, export ac_cv_func_dup3=no (libiberty then uses its dup2 fallback). This is host-only code and doe...

## Cost

- From the script, engineer: 26 sessions, 25.9M input tokens
- From the script, lead: 27 sessions, 11.6M input tokens
- Started by hand, Claude: 3 sessions, 84.8M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 8.7 GiB of 100 GiB. 355 GiB free on the drive.
