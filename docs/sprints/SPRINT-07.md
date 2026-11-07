# Sprint 7: runtimes, part 1 - shared libgcc and the first libgfortran slice (Milestone M3)

**Status:** started by the owner on 2026-11-07 ("Can we start working on sprint 7 while waiting for
card window"; run authorization and engineers "Yes, same as S6"). Runs need no per-run approval,
card jobs and timed benchmark windows included. Engineers: Codex through `tools/dispatch.py`, model by
ticket depth, as in Sprint 6. The gcc tickets stay parked in `lane: lead` until Sprint 6's gcc
tickets (S6-06, S6-14, S6-08) are merged, because all gcc tickets share one GCC checkout and build;
then the lead moves them to `lane: gcc` in order. Sprint 6 closed 2026-11-07; tickets are released one chain at a time while Codex and Claude usage is low (owner, 2026-11-07), starting with S7-03.

**Goal (Milestone M3, part 1):** programs built by GCC-KNC can use a shared `libgcc_s` that is a
drop-in superset of the donor's on the card's glibc 2.21, and a first Fortran runtime slice
(descriptors, allocation, formatted I/O, modules) with correct KNC floating-point control. Inputs:
`docs/research/knc-libgcc-shared.md` (S7-01) and `docs/research/knc-libgfortran.md` (S7-02).

Order:
1. Shared libgcc: donor ABI objects and map (S7-03), shared build and driver (S7-04), card payloads
   (S7-05), lead native acceptance and the install decision (S7-06).
2. libgfortran: KNC floating-point backend (S7-07), the base runtime and descriptor/I/O slice
   (S7-08), runtime isolation and packaging (S7-09).
3. Batch check after S7-05 and S7-08 (S7-10).

**Out of scope:** binary128 / kind 16 and libquadmath (S7-02 option 4, backlog), libgomp (E6-03),
libstdc++ (E6-06), MPI (E6-04), anything installed over the card's system libraries.

**Cap:** two weeks from start. Unfinished tickets return to the backlog.

**Rules carried from Sprint 6:** shared i386 changes take ADR-0006 forms only; x86 assembly stays
identical; only the lead runs card jobs; engineers stage binaries under `.work/_shared/<ticket>/`;
ADR-0010 applies to any timing.
