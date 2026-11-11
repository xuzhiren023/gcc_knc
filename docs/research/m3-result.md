# Milestone M3 (runtimes): result, 2026-11-11

**Question (PROJECT_PLAN section 6):** can the runtimes coexist on the card's old system?
**Go if:** Fortran, OpenMP and C++ integration tests pass natively, and required symbols and
system calls are all accounted for.
**Decision:** **go**, recommended by the lead and accepted under the owner's blanket approval of
2026-11-11 ("Tonight I want see s9 closed ... blanket approval for recommended action").

## Evidence

| Runtime | Native evidence on the card | Where |
|---|---|---|
| libgcc (static and shared) | GCC execute suite 1,681/1,681 at the Sprint 9 head (2026-11-11) | S9-11, S7 |
| libgfortran | Fortran slice and links (Sprint 7) | S7-09, `card-runs-s7.md` |
| libstdc++, libatomic | 56-program C++ batch (exceptions, RTTI, threads, tz, 16-byte atomics, cross-DSO with GCC 5 libraries both ways) all as expected; link guard against the card's GCC 5 libstdc++ | S9-03, S9-04, S9-05 |
| libgomp | the eight OpenMP programs at 60 and 240 threads with no memory limit; barrier, task, cancel, single and ordered testsuite slice (34 programs); KNC defaults measured on the card: spread places, `delay` 128, 200 ms spin, flat barrier, arena cap from the card's memory | S9-06 to S9-10, S9-12, S9-15, S9-24, S9-25 |

**Symbols and system calls.** The card has glibc 2.21 and the MPSS 2.6.38 kernel. The runtime
plans account for what they need from them: `docs/research/knc-libstdcxx.md` (timed waits through
`pthread_cond_timedwait`, no `pthread_cond_clockwait`; `from_chars(_Float128)` at long-double
precision), `docs/research/knc-libgomp.md` (futex, affinity, `delay` spin, no `getrandom`), and the
card checks above, which ran those paths natively.

## Known limits carried forward

- The card's `/dev/random` blocks (random_device token test, documented deviation, S9-05).
- The old linker finds a shared library's own dependencies only through `-rpath-link` (S9-06
  works around it for libgomp).
- The per-core OpenMP barrier is slower than the flat one on this card and stays behind a build
  switch (E6-09).
- One S9-07 test job builds an invalid `OMP_PLACES` string (runner defect; libgomp behaves as designed).
- The card's glibc `powl` returns NaN for negative bases with huge integer exponents; our vector
  math gives the C99 Annex F value (S10-06). Card libm is not a reference for special cases.
