# GPT kickoff prompts

Paste these into Codex from the repository root. `AGENTS.md` carries the standing rules,
so the prompts stay short.

## Independent review of the kickoff

```text
You are an independent senior compiler engineer reviewing the kickoff of GCC-KNC. Do not
implement anything, and do not edit, commit or push. Only report findings. Include
uncommitted changes in the working tree in your review.

Scope, from the owner: this is a brand new, general-purpose project. It aims to provide
broad optimization for any program that needs GCC to compile, on Intel Xeon Phi Knights
Corner. It is not part of PhiWeather or PhiChat. The research report discusses those
applications heavily; treat that only as background evidence about the hardware. Flag
anything in the plan that still ties goals, priorities or tuning to one application.

Read: README.md, docs/PROJECT_PLAN.md, docs/DEVELOPMENT_CYCLE.md, docs/BACKLOG.md,
docs/sprints/SPRINT-00.md, docs/adr/, docs/reviews/2026-11-01-research-review.md,
tests/acceptance/, AGENTS.md, and GCC_KNC_TECHNICAL_RESEARCH_REPORT_20261101.md.

The plan was written by Claude, which will also be the reviewer on the project. Check its
work independently, and do not assume its claims are right. Where you can, verify them:
- The donor GCC is at PhiWeather\.tools\knc-bootstrap\gcc-source, its compiled tools are in
  ..\cross\bin, and that folder's cygwin\bin must be on PATH. These folders are read-only.
- Do not use the Xeon Phi card or run anything on it.
- Use the Intel ISA reference 327364 and GCC 16 sources or docs for ISA and GCC claims.

Answer these:
1. Technical: is a KNC subtarget in GCC 16's i386 backend the right base, compared with a
   separate backend or GCC 14? What does ADR-0002 underestimate? Are the review's findings
   on the donor, division, unaligned access, gather and x86 baseline gaps correct? What
   major KNC or GCC risk is missing?
2. Breadth: will this plan deliver gains for typical programs, including integer and
   branch-heavy code, or is it too focused on floating-point loops? Is the proposed corpus
   and Gate E measure sound? Is ~1.25x over GCC 5.1.1 a sensible threshold?
3. Plan: is the sprint order right, and are stories small enough? Are the gates and the
   forecast realistic? What should be cut or moved earlier?
4. Agile and TDD: will this cycle work with one card and no emulator? Can tests pass while
   the compiler is wrong? Is the m1_affine fixture strong enough, and what would it miss?
   Is the process too heavy or too light?
5. Sprint 0: is it ready to start? Name anything ambiguous or blocked.

Report format:
- Verdict first: READY, READY WITH CHANGES, or NOT READY, with one paragraph of reasoning.
- Then findings, most severe first. For each: severity (Critical, High, Medium, Low), file
  and line, the problem, your evidence, whether you verified it or are inferring it, and a
  specific recommended change.
- Then what you checked and found correct, and what you could not check.

Report only real problems, and say so if an area is fine. Do not rewrite the plan.
```

## First session

```text
You are the implementer on GCC-KNC, a modern GCC toolchain for Intel Xeon Phi Knights
Corner. Claude is tech lead and reviewer. The owner makes decisions.

Read, in this order: AGENTS.md, CURRENT_STATE.md, docs/sprints/SPRINT-00.md,
docs/DEVELOPMENT_CYCLE.md, docs/reviews/2026-11-01-research-review.md. Use
GCC_KNC_TECHNICAL_RESEARCH_REPORT_20261101.md as background reading; where it conflicts
with the review or an ADR, the review and ADR win.

Start Sprint 0 with story S0-01. Then continue through S0-02 and S0-03 in order, one
branch per story, following RED, GREEN, REFACTOR with an evidence note in the sprint log
for each. Stop after S0-03 for review, or sooner if an escalation rule applies. Do not
start S0-04 card work or use the card in this session. Do not push or merge.

At the end, tell me: which stories are ready for review, their branches and head commits,
test results, and any open questions.
```

## Later sessions

```text
Continue GCC-KNC as implementer. Read AGENTS.md and CURRENT_STATE.md, then the current
sprint file including its log. Apply any review findings first. Then take the next story
in order. Stop when a story needs review, an escalation rule applies, or the sprint goal
is met. Report stories, branches, head commits, test results and open questions.
```

## Asking Claude for a review

```text
Review story <ID> on branch <branch> (depth per the sprint file). Check the red-green
history and evidence note, then record your verdict in the sprint log.
```
