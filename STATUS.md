# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 08:41.

**Next: GPT-6.1, on S0-08 (Toolchain independent of PhiWeather).** Run `python tools/dispatch.py`, or ask the tech lead to.

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
| S0-08 | Toolchain independent of PhiWeather | In progress | Rebuild authorized; do not intercept print queries in a wrapper, since that fakes the check without changin... |
| S0-09 | T1 scan sees KNC mask-branch loops | Not started |  |

## Recent activity

- 2026-11-02 08:41 **S0-08** lead answer: Rebuild authorized; do not intercept print queries in a wrapper, since that fakes the check without changing what the driver runs. Rebuild only the...
- 2026-11-02 08:40 **S0-08** engineer ask: Reserved specs attempt failed: ../_shared/s0_08_specs_probe.py overrides *linker and *invoke_as to shared paths and passes --sysroot. Both print-pr...
- 2026-11-02 08:34 **S0-07** lead approve: We now have a proposed public benchmark corpus (PolyBench, STREAM, NPB, HPCG, zlib, SQLite, with bzip2 and two PolyBench kernels held out) and a co...
- 2026-11-02 08:32 **S0-07** engineer submit: d620e4a: corpus report and measurement scripts. GCC 14.4 compile-only proxy via tools/run.py: STREAM, 8 PolyBench, NPB CG/EP/MG/IS, SQLite, bzip2 c...
- 2026-11-02 08:14 **S0-07** lead answer: Sources are in .work/_shared/corpus/, read-only, with SHA-256, size and URL for each in SOURCES.txt: polybench-c-4.2.1-beta.tar.gz, stream.c (5.10)...
- 2026-11-02 08:14 **S0-07** owner decide: Owner on 2026-11-02: yes, the lead downloads the benchmark sources into .work/_shared/corpus/.
- 2026-11-02 07:52 **S0-07** lead escalate: Engineer sandbox has no network, so S0-07 cannot fetch the corpus; nothing is on the branch yet. Owner choice: either place versioned source archiv...
- 2026-11-02 07:51 **S0-07** engineer ask: Blocked by sandbox network permissions: Python urllib.request.urlopen on https://www.cs.virginia.edu/stream/FTP/Code/stream.c fails with URLError /...

## Cost

- From the script, engineer: 21 sessions, 18.8M input tokens
- From the script, lead: 22 sessions, 10.7M input tokens
- Started by hand, Claude: 2 sessions, 71.0M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 6.4 GiB of 100 GiB. 361 GiB free on the drive.
