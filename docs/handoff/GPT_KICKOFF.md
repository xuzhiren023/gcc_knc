# GPT kickoff prompts

Paste these into Codex from the repository root. `AGENTS.md` carries the standing rules,
so the prompts stay short.

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
