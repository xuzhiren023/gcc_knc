#!/usr/bin/env python3
"""Move the board forward without anyone relaying context.

Reads the board with no model involved, starts one fresh agent session for the
next action, records its token use, and repeats. It stops when nothing can move,
when a ticket needs the owner, or at --max-sessions.

    python tools/dispatch.py --dry-run
    python tools/dispatch.py --max-sessions 6
"""
import argparse
import datetime
import glob
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pm  # noqa: E402
import storage  # noqa: E402

ENGINEER_PROMPT = """You are an engineer on GCC-KNC, working on ticket {id} only, in this worktree.
Run: python tools/pm.py show {id}
Do only what that ticket asks. Rules are in AGENTS.md. Read other documents only if the ticket points to them.
End the session with one pm.py command: submit, red, ask or escalate. Do not write a summary."""

LEAD_PROMPT = """You are the tech lead on GCC-KNC. Ticket {id} is in state {state}, on branch {branch}.
Run: python tools/pm.py show {id}
{task}
Read only what you need: the ticket, git log and git diff main...{branch}. Rerun something only if you doubt it.
Finish with one pm.py command. Do not write a summary."""

LEAD_TASKS = {
    "review": "Review per docs/DEVELOPMENT_CYCLE.md section 7, then run pm.py approve, or pm.py changes with numbered findings, each with file:line.",
    "red-review": "Check that the failing tests prove the acceptance criteria and fail for the right reason, then run pm.py approve or pm.py changes.",
    "blocked": "Answer the question with pm.py answer, or send it to the owner with pm.py escalate if it is the owner's decision.",
}


def newest(pattern):
    found = glob.glob(os.path.expandvars(pattern))
    return max(found, key=os.path.getmtime) if found else None


def engineer_command(board, ticket, worktree):
    codex = newest(r"%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe") or "codex"
    effort = board.budget(ticket)["effort"]
    trust = 'projects."%s".trust_level="trusted"' % worktree.replace("\\", "\\\\")
    shared = storage.shared_area(board.root)
    os.makedirs(shared, exist_ok=True)
    roots = 'sandbox_workspace_write.writable_roots=["%s"]' % shared.replace("\\", "\\\\")
    return [codex, "exec", "--json", "--ephemeral", "-C", worktree, "--sandbox", "workspace-write",
            "--dangerously-bypass-hook-trust", "-c", trust, "-c", roots, "-c", 'approval_policy="never"',
            "-c", 'model_reasoning_effort="%s"' % effort,
            ENGINEER_PROMPT.format(id=ticket.id)]


def lead_command(board, ticket):
    claude = newest(r"%APPDATA%\Claude\claude-code\*\*\claude.exe") or "claude"
    state = ticket.state
    prompt = LEAD_PROMPT.format(id=ticket.id, state=state, branch=ticket.fields.get("branch", ""),
                                task=LEAD_TASKS[state])
    return [claude, "-p", prompt, "--output-format", "json", "--no-session-persistence",
            "--model", "opus", "--effort", board.budget(ticket)["effort"],
            "--allowedTools", "Read,Grep,Glob,Bash(git log*),Bash(git diff*),Bash(git show*),Bash(python tools/pm.py*)"]


def session_env(board, ticket, role):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env.update(PM_ROLE=role, PM_TICKET=ticket.id, PM_DEPTH=ticket.fields.get("depth", "standard"),
               PM_ALLOW_TIERS=ticket.fields.get("allow_tiers", ""), PM_ALLOW_BULK=ticket.fields.get("allow_bulk", ""),
               PM_SHARED=storage.shared_area(board.root))
    return env


def parse_usage(role, output):
    """Token totals from an agent's JSON output."""
    usage = {"input_tokens": 0, "output_tokens": 0}
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        found = event.get("usage") if isinstance(event, dict) else None
        if not isinstance(found, dict):
            continue
        usage["input_tokens"] += found.get("input_tokens", 0) + found.get("cache_read_input_tokens", 0)
        usage["output_tokens"] += found.get("output_tokens", 0)
    return usage


def ledger_totals(board, ticket_id, role):
    path = os.path.join(board.state_dir(), "ledger.jsonl")
    sessions = tokens = 0
    if os.path.exists(path):
        with open(path, encoding="utf8") as f:
            for line in f:
                entry = json.loads(line)
                if entry["ticket"] == ticket_id and entry["role"] == role:
                    sessions += 1
                    tokens += entry.get("input_tokens", 0)
    return sessions, tokens


def over_budget(board, ticket):
    budget = board.budget(ticket)
    sessions, tokens = ledger_totals(board, ticket.id, "engineer")
    if sessions >= budget["sessions"]:
        return "%d engineer sessions used; the budget is %d" % (sessions, budget["sessions"])
    if tokens >= budget["input_tokens"]:
        return "%d input tokens used; the budget is %d" % (tokens, budget["input_tokens"])
    return None


def run_session(board, ticket, role, dry_run):
    if role == "engineer":
        reason = over_budget(board, ticket)
        if reason:
            print("%s: over budget (%s), sending to the owner" % (ticket.id, reason))
            ticket.fields.update(state="owner", resume=ticket.state)
            ticket.save("escalate", "budget: " + reason)
            return True
    print("%s %s: %s session" % (ticket.id, ticket.state, role))
    if dry_run:
        return False
    os.environ["PM_ROLE"] = role
    if role == "engineer":
        pm.cmd_start(board, argparse.Namespace(id=ticket.id))
        ticket = board.load(ticket.id)
        command, cwd = engineer_command(board, ticket, board.worktree(ticket)), board.worktree(ticket)
    else:
        command, cwd = lead_command(board, ticket), board.root
    timeout = board.policy["session_timeout_minutes"] * 60
    project_before = storage.project_bytes(board.root)
    free_before = shutil.disk_usage(board.root).free
    before = (ticket.state, ticket.fields.get("head"))
    try:
        # codex exec waits for end of input on an inherited stdin.
        done = subprocess.run(command, cwd=cwd, env=session_env(board, ticket, role), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf8",
                              errors="replace", timeout=timeout)
        output, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as expired:
        output, code = str(expired.stdout or ""), "timeout"
    entry = {"at": datetime.datetime.now().isoformat(timespec="seconds"), "ticket": ticket.id, "role": role,
             "exit": code}
    entry.update(parse_usage(role, output))
    logs = os.path.join(board.state_dir(), "logs")
    os.makedirs(logs, exist_ok=True)
    log_path = os.path.join(logs, "%s-%s-%s.jsonl" % (ticket.id, role, entry["at"].replace(":", "")))
    with open(log_path, "w", encoding="utf8") as f:
        f.write(output)
    if role == "lead" and "Not logged in" in output:
        print("  Claude's command line is not logged in, so no review ran and the ticket is unchanged.\n"
              "  Log in once (docs/COLLABORATION.md), or open a Claude session and ask it to act as tech lead.")
        return False
    with open(os.path.join(board.state_dir(), "ledger.jsonl"), "a", encoding="utf8") as f:
        f.write(json.dumps(entry) + "\n")
    print("  exit %s, %d input tokens, %d output; log: %s" % (code, entry["input_tokens"], entry["output_tokens"], log_path))
    storage.prune_logs(board.state_dir(), board.policy["storage"]["logs_keep_mb"])
    project_growth = storage.project_bytes(board.root) - project_before
    elsewhere = (free_before - shutil.disk_usage(board.root).free - project_growth) / storage.GIB
    if elsewhere > board.policy["storage"]["leak_warn_gib"]:
        print("  WARNING: the drive lost %.1f GiB outside this project during the session. "
              "Something else may be running, or files were written elsewhere." % elsewhere)
    after = board.load(ticket.id)
    if role == "engineer" and after.state in ("doing", "review", "changes", "blocked"):
        worktree_gib = storage.tree_size(board.worktree(after)) / storage.GIB
        if worktree_gib > board.budget(after)["disk_gib"]:
            print("  worktree over its disk budget, sending to the owner")
            after.fields.update(state="owner", resume=after.state)
            after.save("escalate", "worktree uses %.1f GiB; the budget is %d GiB"
                       % (worktree_gib, board.budget(after)["disk_gib"]))
            return True
    if (after.state, after.fields.get("head")) == before and role == "lead":
        print("  the lead did not change the ticket, sending to the owner")
        after.fields.update(state="owner", resume=after.state)
        after.save("escalate", "lead session ended without a decision (exit %s)" % code)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-sessions", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    board = pm.Board()
    for _ in range(args.max_sessions):
        if any(t.state == "owner" for t in board.tickets()):
            break
        level, message = storage.check(board.root, board.policy)
        if level != "ok":
            print(message)
        if level == "hard":
            print("No session started. See: python tools/storage.py")
            break
        action = pm.next_action(board)
        if action is None or not run_session(board, action[1], action[0], args.dry_run):
            break
    pm.cmd_board(board, None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
