# Kickoff

## Start the work

Nothing needs pasting into an agent. See what would happen, at no cost:

```bash
python tools/dispatch.py --dry-run
```

Then run a few sessions. Each one is a fresh Codex or Claude session on one ticket:

```bash
python tools/dispatch.py --max-sessions 6
```

It stops when a ticket needs you, when nothing can move, or at the limit. Then:

```bash
python tools/pm.py inbox
```

`docs/COLLABORATION.md` has the full picture. Sessions you start yourself in the Codex app also
work: ask one to take a ticket with `python tools/pm.py show <ID>`.

## Optional: independent review of the kickoff

Paste this into a Codex session at the repository root.

```text
You are an independent senior compiler engineer reviewing the kickoff of GCC-KNC. Do not
implement anything, and do not edit, commit or push. Only report findings. Keep this
efficient: do not read files you do not need, and do not re-verify what you have checked.

Scope, from the owner: this is a brand new, general-purpose project. It aims to provide
broad optimization for any program that needs GCC to compile, on Intel Xeon Phi Knights
Corner. It is not part of PhiWeather or PhiChat. The research report discusses those
applications heavily; treat that only as background evidence about the hardware. Flag
anything in the plan that still ties goals, priorities or tuning to one application.

Read: README.md, docs/PROJECT_PLAN.md, docs/DEVELOPMENT_CYCLE.md, docs/COLLABORATION.md,
docs/HARNESS.md, docs/BACKLOG.md, work/tickets/, docs/adr/, tools/pm.py, tools/dispatch.py,
harness/, docs/reviews/2026-11-01-research-review.md, tests/acceptance/, and AGENTS.md.
Use GCC_KNC_TECHNICAL_RESEARCH_REPORT_20261101.md as background.

The plan was written by Claude, which is also the tech lead on the project. Check its work
independently, and do not assume its claims are right. Where you can, verify them:
- The donor GCC is at PhiWeather\.tools\knc-bootstrap\gcc-source, its compiled tools are in
  ..\cross\bin, and that folder's cygwin\bin must be on PATH. These folders are read-only.
- Do not use the Xeon Phi card or run anything on it. Do not run tools/dispatch.py except
  with --dry-run.
- Use the Intel ISA reference 327364 and GCC 16 sources or docs for ISA and GCC claims.

Answer these:
1. Technical: is a KNC subtarget in GCC 16's i386 backend the right base, compared with a
   separate backend or GCC 14? What does ADR-0002 underestimate? Are the review's findings
   on the donor, division, unaligned access, gather and x86 baseline gaps correct? What
   major KNC or GCC risk is missing?
2. Breadth: will this plan deliver gains for typical programs, including integer and
   branch-heavy code, or is it too focused on floating-point loops? Is the proposed corpus
   and Milestone M4 measure sound? Is ~1.25x over GCC 5.1.1 a sensible threshold?
3. Plan: is the sprint order right, and are tickets small enough? Are the milestones and the
   forecast realistic? What should be cut or moved earlier?
4. Agile and TDD: will this cycle work with one card and no emulator? Can tests pass while
   the compiler is wrong? Is the m1_affine fixture strong enough, and what would it miss?
5. Collaboration and cost: will the ticket-and-dispatcher structure work without a person
   relaying context? Where will it deadlock or lose information? Are the harness budgets
   sensible, and will they stop real work or miss real waste?
6. Sprint 0: is it ready to start? Name anything ambiguous or blocked.

Report format:
- Verdict first: READY, READY WITH CHANGES, or NOT READY, with one paragraph of reasoning.
- Then findings, most severe first. For each: severity (Critical, High, Medium, Low), file
  and line, the problem, your evidence, whether you verified it or are inferring it, and a
  specific recommended change.
- Then what you checked and found correct, and what you could not check.

Report only real problems, and say so if an area is fine. Do not rewrite the plan.
```
