# Kickoff

GPT-6.1 implements one ticket per session. Claude reviews and merges. You decide, and you
are the only one who pushes. `python tools/pm.py board` shows where everything stands.

## Before the first session

1. **Optional: log Claude's command line in once,** so reviews can run unattended. Type `/login` in the session this opens:

   ```powershell
   & (Get-ChildItem "$env:LOCALAPPDATA\Packages\*Claude*\LocalCache\Roaming\Claude\claude-code\*\*\claude.exe" | Sort-Object LastWriteTime | Select-Object -Last 1).FullName
   ```

   Without this, ask a Claude session to review instead (see below).

2. **In Codex, open this folder and choose GPT-6.1.** If Codex asks you to review the project's hooks, approve them (`/hooks` in the command line). They are the limits on cost and disk use, and the prompt below checks they are active.

## Start GPT-6.1

Start a new session for each ticket and paste this. Short sessions are what keep the cost down.

```text
You are an engineer on GCC-KNC, a modern GCC toolchain for Intel Xeon Phi Knights Corner.
Claude is the tech lead. You talk to the lead only through your ticket.

1. Run exactly: make --version
   Project policy should refuse it. If it runs or reports "not recognized", the project's
   hooks are not active: tell me that and stop.
2. Run: python tools/pm.py board
   If the last lines do not say "Next: engineer on <ID>", tell me what they say and stop.
3. Run: python tools/pm.py start <ID>
   It prints your worktree. Use that folder as the working directory for every command
   from now on. Do not use "git -C" or "cd <path>;" in a command.
4. Run: python tools/pm.py show <ID>, and read AGENTS.md. Do only what the ticket asks.
   Read other documents only if the ticket points to them.
5. End with one tools/pm.py command: submit, red, ask or escalate. Then stop. Do not start
   another ticket. Your final message is only the "PM update:" line that command prints.
```

## After each session

GPT-6.1 ends with one `PM update:` line, and you get a desktop notification. The full picture
is in `STATUS.md`.

Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs." Or, if you
logged Claude's command line in, run this instead:

```bash
python tools/dispatch.py --max-sessions 1
```

Either way, the lead answers questions, or reviews and merges approved work to local `main`.
Then check the board. If it says `Next: engineer on ...`, start a new GPT-6.1 session with the
same prompt:

```bash
python tools/pm.py board
```

If a ticket needs you, this shows the question:

```bash
python tools/pm.py inbox
```

## Or let it run without you

The dispatcher can run both agents in turn, using GPT-6.1 for engineers, with no pasting at all.
It stops when a ticket needs you, or at the session limit. These sessions also get the token and
session budgets, which sessions you start by hand do not:

```bash
python tools/dispatch.py --dry-run
```

```bash
python tools/dispatch.py --max-sessions 6
```

Pick one way at a time. Do not run the dispatcher while a hand-started session is working.

## See how the project is going

**Open [`STATUS.md`](STATUS.md).** It updates itself at every ticket change: what happens next, whether
anything is waiting for you, milestones, tickets, recent activity, cost and disk. You also get a Windows
notification when a ticket is finished, approved, blocked, or needs you.

For more detail on cost and disk:

```bash
python tools/pm.py usage
```

```bash
python tools/storage.py
```

## Optional: independent review before Sprint 0

Paste this into a GPT-6.1 session once if you want a second opinion on the plan.

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
tools/storage.py, harness/, docs/reviews/2026-11-01-research-review.md, tests/acceptance/,
and AGENTS.md. Use GCC_KNC_TECHNICAL_RESEARCH_REPORT_20261101.md as background.

The plan was written by Claude, which is also the tech lead on the project. Check its work
independently, and do not assume its claims are right. Do not use the Xeon Phi card, and do
not run tools/dispatch.py except with --dry-run. The donor GCC is read-only, at
PhiWeather\.tools\knc-bootstrap\gcc-source.

Answer these:
1. Technical: is a KNC subtarget in GCC 16's i386 backend the right base? What does ADR-0002
   underestimate? What major KNC or GCC risk is missing?
2. Breadth: will this deliver gains for typical programs, including integer and branch-heavy
   code? Is the corpus and the Milestone M4 measure sound?
3. Plan: is the sprint order right? Are the milestones and the forecast realistic?
4. TDD: can tests pass while the compiler is wrong? What would m1_affine miss?
5. Collaboration, cost and disk: where will the ticket structure deadlock or lose information?
   Will the limits stop real work, or miss real waste?
6. Sprint 0: is it ready to start?

Give a verdict first: READY, READY WITH CHANGES, or NOT READY. Then findings, most severe
first, each with severity, file and line, evidence, whether you verified or inferred it, and
a specific change. Report only real problems. Do not rewrite the plan.
```
