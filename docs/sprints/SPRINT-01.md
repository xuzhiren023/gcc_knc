# Sprint 1: GCC 16 speaks KNC

**Goal:** GCC 16.2 is configured for `k1om-mpss-linux`, and its `cc1` turns integer C into
assembly that the 2.22 assembler accepts and `tools/knc_lint` passes. This ends Milestone M0.

**Cap:** two weeks. Host tiers only (T0 to T2): no ticket here needs the card. Floating-point
arguments and returns stay out of scope until E2-01, so tests use integer C and `long double`.

The work is in tickets, in `work/tickets/S1-*.md`, in this order:

| Ticket | What it delivers |
|---|---|
| S1-01 | Tickets can change the GCC fork, with review and merge like this repository |
| S1-02 | GCC 16.2 builds for `k1om-mpss-linux` (E1-01) |
| S1-03 | `tools/check` runs source-level T1 and T2 tests against GCC 16 |
| S1-04 | `-march=knc` with no SSE, AVX, MMX, CMOV, FCOMI or MFENCE (E1-02) |
| S1-05 | Integer C assembles with `as` 2.22 and lints clean (E1-03, E1-04) |
| S1-06 | K1OM link defaults: loader, link and assembler specs (E1-05) |
| S1-07 | Milestone M0 evidence note and recommendation (E1-06) |

## Sprint exit

- [ ] All stories approved and merged, or explicitly returned to the backlog
- [ ] `CURRENT_STATE.md` updated, and the GCC `knc` branch is ready for the owner to push
- [ ] Milestone M0 review held: go, adjust or stop, decided by the owner
- [ ] On go, with every M0 requirement met and all tests passing in the lead's own rerun: a local
  milestone commit updating `work/milestones.json`, and a local `milestone/M0` tag here and on the
  GCC fork's `knc` branch. Nothing is pushed (owner, 2026-11-02)
- [ ] Sprint 2 refined from E2
- [ ] Three-line retro below

## Retro

*(at close)*
