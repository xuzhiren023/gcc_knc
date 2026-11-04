# Sprint 4: masks, compares, if-conversion and safe masked tails (Milestone M2, part 1)

**Status:** approved by the owner on 2026-11-04 ("Approve Sprint 4"), with runs without per-run
approval. Proposed by the lead the same day, after M1 was accepted.

**Who implements (owner, 2026-11-04: "we are tight on GPT usage, use claude code subagent with
proper model and level for sprint 4"):** Sprint 4's engineer work runs as Claude Code subagents
started by the lead, not GPT through `tools/dispatch.py`. Deep compiler tickets and S4-01 use
Opus at high effort; light tickets use Sonnet at medium. Each subagent works as the engineer under
`AGENTS.md` (`PM_ROLE=engineer`, `pm.py start/commit/submit`, red first). The lead reviews and
merges as before, and never reviews its own subagent's work less strictly. Subagent tokens do not
reach `STATUS.md`; the lead records them per ticket in a note.

**Goal:** loops with conditions vectorize on `zmm` under `-march=knc`. Compares produce `k` masks,
`if`, `?:`, `fabs`, `min` and `max` become masked operations or blends instead of scalar code, and
the native results are exact. 32-bit integer loops vectorize (S3-09), and 64-bit integer add and
sub get the IMCI carry form. A loop's remainder may use a masked vector access only where every
64-byte line it touches is known to be mapped (S3-03's probe: masks never suppress a fault).
Otherwise the x87 remainder stays. Roadmap row S4 in `docs/PROJECT_PLAN.md`; backlog E4-01,
E4-04 and the integer part of E3-04.

**Out of scope (Sprint 5):** gather and scatter, conversions, permutes, reductions, and correctly
rounded division and square root (E4-02, E4-03, E4-05 to E4-07). Performance and the cost model
are Sprint 6 and decide M2.

**Cap:** two weeks from approval. Unfinished tickets return to the backlog.

**Rules carried from Sprint 3:**
- Shared i386 changes take ADR-0006 forms only, and lines and hunks are reported (no cap).
- x86 assembly stays identical.
- Per-head checks run as batch checks after every 2-3 gcc merges (`docs/DEVELOPMENT_CYCLE.md`
  section 4).
- The card is for validating built programs only, on cores 40-59.

## Tickets

| Ticket | What it delivers | Depth | Lane | Needs |
|---|---|---|---|---|
| S4-01 | Research and ADR-0007: mask design for KNC. `k0`-`k7` are already allocatable as HI (ADR-0004); this adds the vector boolean mode, `ix86_get_mask_mode` for the four packed modes, `vec_cmp`/`vcond_mask` names, IMCI compare predicates, `kand`/`kor`/`knot`/`kortest`, mask spills, and which AVX-512 mask code in `i386`/`sse.md` can be reused behind ADR-0006 hooks versus written in `imci.md`. Shared-line estimate. Masked-tail design from S3-03's fault table | deep | tools | |
| S4-02 | Mask registers in vector code: `vec_cmp` for V16SF, V8DF and V16SI into `k` masks, mask logic, mask spills and reloads; T1 per compare predicate (E4-01, part 1) | deep | gcc | S4-01, ADR-0007 accepted |
| S3-09 | V16SI add, sub, mul, logic and broadcast; V8DI logic (moved here by the owner) | standard | gcc | |
| S4-03 | Blends and if-conversion: `vcond_mask` to IMCI masked moves and blends, so `if`, `?:`, `fabs`, `min` and `max` loops vectorize; NaN and signed-zero cases exact (E4-01, part 2) | deep | gcc | S4-02 |
| S4-04 | V8DI add and sub with the IMCI carry form (`vpaddsetcd`/`vpadcd`), so `long` add loops vectorize | standard | gcc | S4-02, S3-09 |
| S4-05 | Safe masked tails (E4-04): use a masked vector remainder only where the loop's peel makes every touched 64-byte line part of the array; otherwise keep x87. Lengths 0-65, every element offset, arrays flush against a guard page | deep | gcc | S4-03 |
| S4-06 | Batch check after S4-02, S3-09 and S4-03 merge: x86 identical, drill, ICE sweeps at `-O2 -ftree-vectorize` and `-O3`; the lead then runs the card suite | standard | gcc | those three |
| S4-07 | Final batch check at the sprint head, after S4-04 and S4-05 | standard | gcc | all above |
| S4-09 | **First in the gcc lane.** Wrong code from S3-06: LRA folds a misaligned load into `vaddps`/`vsubps`/`vmulps` (constraint `m` instead of `Bm`), which faults on the card. Found by `s4_masks` on 2026-11-04 | standard | gcc | |
| S4-08 | Small fixes from M1: S3-22's V4SF varargs assert also requires 128-bit alignment (and `TARGET_64BIT`); S3-10's ABI expected files use the card's `%La` spelling | light | gcc | |

The lead writes `tests/acceptance/s4_masks/` before S4-02 starts: conditional FP and integer loops
with exact references, NaN and signed zero, and masked-tail cases at a guard page. Each gcc ticket
gets its own card check after merge.

S3-25 (the `va_arg` error path) finishes in Sprint 3; if it is still open at approval, it carries
over unchanged.

## Sprint exit

- [ ] S4-01 to S4-08 and S3-09 merged, or returned to the backlog with a reason
- [ ] ADR-0007 accepted
- [ ] `tests/acceptance/s4_masks` passes on the card at `-O2 -ftree-vectorize` and `-O3`
- [ ] Final batch check green: x86 identical, every drill conflict textual, 0 ICE in both sweeps,
  full execute suite all pass on the card
- [ ] Shared lines and hunks reported at the sprint head, with the KNC-only files beside them
- [ ] `CURRENT_STATE.md` updated; three-line retro below

## Retro

*(at close)*
