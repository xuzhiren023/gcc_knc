# Sprint 12: optimization ranked by corpus profiles, and the bandwidth winners in the compiler (Milestone M4, part 2)

**Status:** planned 2026-11-12. Tickets are written when Sprint 11's corpus harness and bandwidth sweeps land;
the order below is by expected benefit across the corpus, and the profiles may reorder it.

**Goal:** the corpus programs run faster under GCC-KNC than under GCC 5.1.1 for reasons we can name, with the top
corpus-wide hot spots carried through GIMPLE, RTL and assembly, and the memory-bandwidth winners from Sprint 11
applied by the compiler and runtimes by default where they help.

Order:
1. **Corpus profiles (E7-03).** Card time per program under both compilers, hot functions and loops per program,
   and a ranked list of missed optimizations across the corpus (held-out programs excluded from every decision).
2. **Bandwidth winners in the compiler (from S11-05/06/09).** Software prefetch distances per loop class (L2 far /
   L1 near, E7-06), NGO streaming stores and eviction for write and read-modify-write streams, the GEMV loop shape
   for weight streaming (several independent row streams, vector kept in L1), and thread-density guidance; each
   a ticket with a T1 shape test and a card A/B on the bandwidth benchmark and on the corpus program it helps.
3. **Scalar and integer code quality for the in-order core (E7-04, E7-15, E7-13).** Scheduling where it helps
   (vector loops) and not where it hurts (x87), inlining and branch shape, no unaligned scalar stores.
4. **Loop-level items the profiles confirm:** unroll for long streams at low thread density (E7-12), a cheaper short
   remainder (E7-19), indirect-access prefetch (E7-09), alignment peeling for long loops (E7-10).
5. **Runtime:** retune the per-core OpenMP barrier (E6-09) if the corpus's OpenMP programs show barrier time.
6. Batch check.

Every optimization ticket: a red T1/T3 test for the shape, a paired card A/B (ADR-0010) on the programs it targets
and on two it should not change, and no program more than 5% slower without a known cause.

**Out of scope:** `-mphinix` final contents and PGO (Sprint 13); IMCI intrinsics (E6-05) unless a corpus program
needs them.

**Cap:** two weeks from the first implementation ticket.
