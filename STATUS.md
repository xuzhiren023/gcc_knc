# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 10:24.

**Next: the tech lead, on S0-08.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[#############-------]` 6 of 9

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 6 of 9 tickets |
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
| S0-04 | Card runner | Not started |  |
| S0-05 | Donor inventory | Done | The donor inventory now covers the whole tree with port/rewrite/drop decisions, the GCC 16.2 runtime audit ... |
| S0-06 | GCC 16.2 fork and timing | Done | GCC 16.2 is checked out on branch knc in the shared build area and builds stock x86_64 C+Fortran on Cygwin ... |
| S0-07 | Benchmark corpus and coverage estimate | Done | We now have a proposed public benchmark corpus (PolyBench, STREAM, NPB, HPCG, zlib, SQLite, with bzip2 and ... |
| S0-08 | Toolchain independent of PhiWeather | Question for the tech lead | all-gcc passed with authorized dup3=no and host C++98 (7cf5e89, 23d445f). install-gcc failed: fixincludes m... |
| S0-09 | T1 scan sees KNC mask-branch loops | Not started |  |

## Recent activity

- 2026-11-02 10:24 **S0-08** engineer ask: all-gcc passed with authorized dup3=no and host C++98 (7cf5e89, 23d445f). install-gcc failed: fixincludes mkinstalldirs runs mkdir -p for shared cr...
- 2026-11-02 09:33 **S0-08** lead answer: Authorized, no source edits: in the rebuild step, export ac_cv_func_dup3=no (libiberty then uses its dup2 fallback). This is host-only code and doe...
- 2026-11-02 09:32 **S0-08** engineer ask: Rebuild configured, but make -j8 all-gcc failed: libiberty/pex-unix.c:478 implicit declaration of dup3 under host GCC14. install-gcc not reached; s...
- 2026-11-02 09:12 **S0-08** lead answer: Source: .work/_shared/gcc-donor, branch donor at 93871d7 (public apc-llc/gcc-5.1.1-knc master af7cc04 plus the wide-int.h host fix). Read-only. Bud...
- 2026-11-02 09:12 **S0-08** owner decide: Owner on 2026-11-02: option (a). One-time exception to the never-copy rule: the lead copies the donor GCC source into .work/_shared/gcc-donor; afte...
- 2026-11-02 08:58 **S0-08** lead note: Checked: the donor source at PhiWeather/.tools/knc-bootstrap/gcc-source is af7cc04 plus one uncommitted change. Ignoring line endings, the only dif...
- 2026-11-02 08:42 **S0-08** lead escalate: The k1om gcc 5.1.1 must be rebuilt to drop compiled-in PhiWeather paths, and its patched source exists only in PhiWeather/gcc-source. AGENTS forbid...
- 2026-11-02 08:42 **S0-08** engineer ask: Source blocker: shared GCC is 16.2.0; installed donor is 5.1.1. Matching source exists only under PhiWeather/gcc-source. Configuring there retains ...

## Cost

- From the script, engineer: 23 sessions, 20.4M input tokens
- From the script, lead: 24 sessions, 11.0M input tokens
- Started by hand, Claude: 3 sessions, 80.7M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 8.2 GiB of 100 GiB. 356 GiB free on the drive.
