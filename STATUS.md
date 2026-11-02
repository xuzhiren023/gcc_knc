# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-02 09:12.

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
| S0-08 | Toolchain independent of PhiWeather | In progress | Source: .work/_shared/gcc-donor, branch donor at 93871d7 (public apc-llc/gcc-5.1.1-knc master af7cc04 plus ... |
| S0-09 | T1 scan sees KNC mask-branch loops | Not started |  |

## Recent activity

- 2026-11-02 09:12 **S0-08** lead answer: Source: .work/_shared/gcc-donor, branch donor at 93871d7 (public apc-llc/gcc-5.1.1-knc master af7cc04 plus the wide-int.h host fix). Read-only. Bud...
- 2026-11-02 09:12 **S0-08** owner decide: Owner on 2026-11-02: option (a). One-time exception to the never-copy rule: the lead copies the donor GCC source into .work/_shared/gcc-donor; afte...
- 2026-11-02 08:58 **S0-08** lead note: Checked: the donor source at PhiWeather/.tools/knc-bootstrap/gcc-source is af7cc04 plus one uncommitted change. Ignoring line endings, the only dif...
- 2026-11-02 08:42 **S0-08** lead escalate: The k1om gcc 5.1.1 must be rebuilt to drop compiled-in PhiWeather paths, and its patched source exists only in PhiWeather/gcc-source. AGENTS forbid...
- 2026-11-02 08:42 **S0-08** engineer ask: Source blocker: shared GCC is 16.2.0; installed donor is 5.1.1. Matching source exists only under PhiWeather/gcc-source. Configuring there retains ...
- 2026-11-02 08:41 **S0-08** lead answer: Rebuild authorized; do not intercept print queries in a wrapper, since that fakes the check without changing what the driver runs. Rebuild only the...
- 2026-11-02 08:40 **S0-08** engineer ask: Reserved specs attempt failed: ../_shared/s0_08_specs_probe.py overrides *linker and *invoke_as to shared paths and passes --sysroot. Both print-pr...
- 2026-11-02 08:34 **S0-07** lead approve: We now have a proposed public benchmark corpus (PolyBench, STREAM, NPB, HPCG, zlib, SQLite, with bzip2 and two PolyBench kernels held out) and a co...

## Cost

- From the script, engineer: 22 sessions, 19.1M input tokens
- From the script, lead: 23 sessions, 10.8M input tokens
- Started by hand, Claude: 2 sessions, 75.5M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 7.0 GiB of 100 GiB. 361 GiB free on the drive.
