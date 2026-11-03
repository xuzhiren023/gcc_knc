# Sprint 3: ordinary loops vectorize on `zmm` (Milestone M1)

**Status:** draft, for the owner's approval. No ticket runs before that.

**Goal:** GCC 16 auto-vectorizes ordinary FP loops onto `zmm` with IMCI under `-march=knc`, and
`m1_affine` (`tests/acceptance/m1_affine/`) passes every check in its README: T1 and T2 on the host,
and T3 on the card at every length 0-65, every element offset in a cache line, and with both arrays
flush against a guard page, with the donor-built driver (ABI cross-check) and the Fortran twin.
Then Milestone M1: is the i386 subtarget still cheaper than a separate backend?

**Cap:** two weeks from the owner's approval. Unfinished tickets return to the backlog, and M1 is
decided on what exists.

**Before it starts:** Sprint 2 closes (S2-07, S2-09 and S2-10 done or returned), because S3-08
needs `gfortran` and S3-10 needs the runner proven on S2-10's batch. The owner or lead places Intel
manual 327364 under `.work/_shared/` for S3-01 and S3-03 (engineer sessions cannot fetch).

**Design:** `docs/adr/0005-knc-packed-vector-modes.md` (Proposed). The lead accepts it after
S3-01, and S3-04 waits for that.

## Shared i386 line budget

Measured 2026-11-03 at `knc` `80bc88d9f9e`: **251 of 300 used, 49 left** (S1 45, S2 206; S2-06 added
54). Measure: added plus deleted lines in `gcc/config/i386` and `gcc/common/config/i386` against
`releases/gcc-16.2.0`, excluding `imci.md`, `linux-k1om.h` and the new KNC-only `i386-knc.*`:

```bash
git -C .work/_shared/gcc diff --numstat releases/gcc-16.2.0 knc -- gcc/config/i386 gcc/common/config/i386
```

| Ticket | Allocation | Where the lines go |
|---|---|---|
| S3-04 | 24 | four `VMOVE` entries, `mov` condition and dispatch, one-line hook calls |
| S3-05 | 6 | `movmisalign` condition and dispatch |
| S3-06 | 12 | `VF_BHSD` and `FMAMODEM` entries, add/sub and mul conditions |
| S3-07 | 4 | the `preferred_simd_mode` call |
| S3-09 | none | about 20 estimated; runs only with the owner's choice below |

46 of 49. A ticket that would pass its allocation stops and asks on the ticket. S2-07 and S2-09 are
expected to add none; if they do, the lead re-plans before S3-04. Integer vector arithmetic (S3-09)
would take M1 to about 315. The owner chooses, when S3-07 is merged: run S3-09 and let M1's
comparison count it, or move it to Sprint 4.

## Card

Only the interactive lead runs card jobs, through `tools/card_run`, under the shared-card rules in
`CURRENT_STATE.md` (cores 30-59, at most 7 GB, the ledger, `claude-` names, no timing figures).
Engineer tickets prepare a batch and submit; the lead runs it and writes the results file. Two card
sessions are planned: S3-03's probe, early, and S3-10's batch, at the end.

## Tickets

| Ticket | What it delivers | Depth | Needs |
|---|---|---|---|
| S3-01 | Research: standard names, iterators, hooks and IMCI forms for the four modes; the `sse.md` audit; line estimates (ADR-0005 questions 2 and 3) | deep | |
| S3-02 | `tools/check.py`: one helper for optional check selections, so new flags stop breaking `test_check.py` | light | |
| S3-03 | Native probe of unaligned pairs and masked aligned forms at page boundaries (E3-01); lead runs it | deep | 327364 placed |
| S3-04 | The four modes legal, KNC-only C++ file, aligned moves, spills, zero and pool constants, ABI guard (E3-02, E3-03) | deep | S3-01, ADR accepted, S3-02 |
| S3-05 | Unaligned moves through load and store pairs (E3-03) | deep | S3-03, S3-04 |
| S3-06 | V16SF and V8DF add, sub, mul, FMA, and broadcasts (E3-04, FP part) | standard | S3-04 |
| S3-07 | Auto-vectorization on, x87 peel and remainder, `m1_affine` T1 and T2 green with GCC 16 (E3-05) | deep | S3-05, S3-06 |
| S3-08 | Fortran twin of `m1_affine` vectorizes and links | standard | S2-09, S3-07 |
| S3-09 | V16SI add, sub, mul, logic and broadcast; V8DI logic (E3-04, integer part) | standard | S3-07, owner's choice |
| S3-10 | Native batch for S3: `m1_affine` in all its builds, and the S3 tickets' native lines; lead runs it | standard | S3-07, S3-08 |
| S3-11 | Milestone M1 note: fixture results, line counts, ICE classes, cost comparison with a separate backend (E3-06) | deep | all above |

The dispatcher runs two lanes, one ticket in progress in each: `--lane gcc` for tickets with
`gcc: yes` or `lane: gcc`, which share the GCC checkout and build, and `--lane tools` for the rest.
S3-01 and S3-02 run in the tools lane, so they can overlap with the gcc lane's work. Every ticket
that builds or compiles with the shared GCC build is in the gcc lane.

## Sprint exit

- [ ] S3-01 to S3-08, S3-10 and S3-11 approved and merged, or returned to the backlog with a reason
- [ ] S3-09 merged, or moved to Sprint 4 by the owner's choice
- [ ] ADR-0005 accepted, with S3-03's answer recorded in it
- [ ] `m1_affine`: every row of its README green with GCC 16, including the donor-driver run and
  the Fortran twin, from S3-10's card run; the lead ticks the native lines from it
- [ ] Shared i386 line count measured at the final `knc` head, with the KNC-only files' size beside it
- [ ] **M1 cost comparison** (S3-11): the subtarget's real cost so far against a separate backend
  estimated from the donor inventory and our own tickets, with any open SSE-assumption ICE class.
  The lead recommends go, adjust or stop; the owner decides
- [ ] `CURRENT_STATE.md` updated, `work/milestones.json` updated if M1 is accepted, and the GCC
  `knc` branch ready for the owner to push
- [ ] Three-line retro below

## Retro

*(at close)*
