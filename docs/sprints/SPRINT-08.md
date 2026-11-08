# Sprint 8: tuning block - the M2 weak spots

**Status:** started by the lead on 2026-11-08 under the owner's overnight blanket approval ("I will
give you a blanket approval with perferred option of what you recommand"; Sprints 8 and 9 in
progress by morning). Runs need no per-run approval, card jobs and timed benchmark windows
included, under the WRF announced-block rule. Engineers: Claude Code through `tools/dispatch.py`,
model by ticket depth. The gcc tickets form one chain (one GCC checkout and build) and start after
Sprint 7's batch check (S7-10).

**Why a tuning block between the runtime sprints:** the lead recommended it on 2026-11-07
(`docs/BACKLOG.md`, "Proposed for Sprint 8"); its card checks (S8-01) are already built and mostly
run. Milestone M3 (runtimes) continues in Sprint 9 and 10.

**Goal:** close the M2 weak spots without losing any M2 kernel: short and odd lengths stop falling
back to x87, streaming and short-row loops get two-level software prefetch, mat8/mat16 reach a fair
share of the hand-IMCI gain, and the cheap code-shape wins (memory operands, `vpmadd231d`, tune
flags, `-O2` defaults, 64-byte padding) land. Every change is judged by the paired, interleaved
measurement of ADR-0010 point 7 (S6-15 fixture).

Order (ADR-0009 amendment 1):
1. Card checks C1-C10 (S8-01; results in `docs/research/knc-characterization.md`).
2. Masked tails (S8-02), software prefetch (S8-03), small matrices (S8-04), the per-loop scalar-add
   cost (S8-05).
3. Memory-operand forms (S8-06), `vpmadd231d` (S8-07), tune flags (S8-08), `-O2` defaults (S8-09),
   ring traffic and check C11 (S8-10).
4. Batch check and paired M2 re-measure (S8-11).

**Decided by the lead:** `-ftrapping-math` stays the KNC default (ADR-0003: flags are observable).

**Out of scope:** libgomp (E6-03, Sprint 9), vector math (E7), up-converting memory operands (E4-07).

**Cap:** two weeks from start. Unfinished tickets return to the backlog.

**Rules carried from Sprint 7:** shared i386 changes take ADR-0006 forms only; x86 assembly stays
identical; only the lead runs card jobs; engineers stage binaries under `.work/_shared/<ticket>/`;
ADR-0010 applies to any timing; claims under 3% need a link-order check.
