# The cost harness

Rules in a prompt can be ignored, so the limits on waste are enforced by tools. All the
numbers are in [`harness/policy.json`](../harness/policy.json), and the lead tunes them at retros.

## What the data showed

From the 40 largest Codex sessions on this machine. The categories are a rough keyword match
on each command, so treat them as indicative.

| Finding | Number | Response |
|---|---|---|
| Long sessions dominate cost, because each turn re-sends the context | Top 5 sessions: about 390M of 535M input tokens; largest: 121M | One ticket per fresh session, with token and call budgets |
| Test commands are the largest share of calls | 885 of 2,354 calls (38%) | Test-run budgets, and skipping repeats |
| Reading and searching return the most text | 23.6M of 44.4M output characters (53%) | Short output from tools, and no whole-log reads |
| Hashing is common but small | 125 calls (5%) | Blocked anyway, as it adds nothing here |

So hashing is the most visible habit, but session length is the most expensive one.

## Four layers

| Layer | Where | What it stops | Can it be bypassed? |
|---|---|---|---|
| **Session limits** | `tools/dispatch.py` | Long sessions, and effort above what the ticket needs. A ticket over its session or token budget goes to you | Only by not using the dispatcher |
| **Live hook** | `.codex/hooks.json`, `harness/hook_policy.py` | Hashing, direct card access, raw builds and tests, whole-log reads, push and merge. Also ends a session's tool calls and test runs at budget | A guardrail. An inventive command might slip past, and layer 4 catches much of that |
| **Short, cached runs** | `tools/run.py` | Long output in context, and re-running what already passed on the same committed content | `--force`, which needs a reason |
| **Submit checks** | `tools/pm.py submit` | Protected paths, hashing or receipt files in the diff, missing `[red]` commit, oversized changes, too many tests | Size and test budgets can be overridden with a stated reason, shown to the reviewer. The others cannot |

The review adds a fifth, human-style check: over-testing and needless validation count as
review findings, and the fix is to delete them.

## Keeping the disk small

PhiWeather reached 375.9 GiB and is 115 GiB now. Git history was never the problem: it is only
155 MiB. Today's space is in git-ignored output that accumulates:

| Pattern | Size today |
|---|---|
| Per-campaign test folders, kept after use | 29 GiB in `artifacts/test-state` |
| Full copies of every release | 12 GiB in `artifacts/release`, about 0.3 GiB each |
| Near-identical build trees | Five `wrf-*-real` folders, 0.7 GiB each |
| Retained reference runs and data | 33 GiB in `reference`, 29 GiB in `wps-geography` |

Git cannot see any of it, so the limits measure the disk itself:

| Control | What it does |
|---|---|
| **Disposable by design** | A ticket's worktree is deleted when it merges, with everything in it. Output only survives by being committed, and files over 1 MiB cannot be committed |
| **One shared build area** | One GCC checkout, toolchain and build tree in `.work/_shared`, never one per ticket |
| **Project limit** | Warns at 60 GiB. At 100 GiB, or under 100 GiB free on the drive, no session starts, and running sessions can only delete and hand over |
| **Ticket limit** | 2, 10 or 20 GiB per worktree by depth. Going over sends the ticket to you, and blocks submit |
| **No bulk copies** | Tree copies, archives, clones and downloads are refused unless the ticket allows them |
| **Commit limits** | 1 MiB per file and 5 MiB per change. `.gitignore` is protected, so it cannot be widened to hide output |
| **Logs capped** | Agent logs stay under 500 MiB, oldest removed first |
| **Leak warning** | Flags a session if the drive shrinks by over 5 GiB more than the project grew, which catches writes elsewhere |

The limits are my starting judgment, sized for one GCC checkout and build. Check where the space is,
or clear old logs and finished worktrees:

```bash
python tools/storage.py
```

```bash
python tools/storage.py --prune
```

## Budgets per ticket depth

| | Light | Standard | Deep |
|---|---|---|---|
| Tool calls per session | 60 | 150 | 300 |
| Test runs per session | 6 | 15 | 25 |
| Engineer sessions per ticket | 2 | 3 | 4 |
| Input tokens per ticket | 2M | 6M | 12M |
| Changed lines | 300 | 500 | 800 |
| New test files | 2 | 4 | 8 |
| Disk per worktree | 2 GiB | 10 GiB | 20 GiB |
| Reasoning effort | low | medium | high |

These are starting judgments, set against the session data above. Check `tools/pm.py usage`
at each retro and adjust them.

When a session hits a budget, commits and `tools/pm.py` still work, so it can always hand
over what it has. A session never loses work to a budget.

## What the harness does not forbid

Tests the ticket asks for; any test that found a real bug; reruns after code changes; deep
checks on ABI and floating-point semantics. The aim is to spend effort on verification that can
change a decision, not to reduce testing as such.

## Setup and limits

- **Codex loads a project's hooks and rules only when the project is trusted.** The dispatcher handles this for each of its sessions, without changing your settings. For sessions you start yourself, trust this folder once when asked, or the limits do not apply.
- **Sessions you start yourself** get the same limits from the board, but the token and session budgets are only counted by the dispatcher.
- **`.git` is protected inside the Codex sandbox,** so `.codex/rules/default.rules` lets `git add`, `git commit` and `tools/pm.py` run outside it. Nothing else gets that exception.
- **Compiler changes will need one extension.** Submit checks read this repository's diff, so S1 must also apply them to `compiler/gcc`, which is a separate repository.
- **Disk is checked every 25 tool calls and between sessions,** so one very large build could overshoot before it is stopped. `tools/run.py` also refuses to start on a nearly full drive.
- **Token budgets are checked between sessions.** The tool-call budget is what stops a session partway through.
