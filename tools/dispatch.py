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
import status  # noqa: E402
import storage  # noqa: E402

ENGINEER_PROMPT = """You are an engineer on GCC-KNC, working on ticket {id} only, in this worktree.
Run: python tools/pm.py show {id}
You are the engineer, not the tech lead: ignore CLAUDE.md's lead role. Do only what that ticket asks. Rules are in AGENTS.md. Read other documents only if the ticket points to them.
Work without narration: no plans, progress reports or summaries between steps, only the tool calls the work needs.
End the session with one pm.py command: submit, red, ask or escalate. Your final message is only the "PM update:" line it prints."""

LEAD_PROMPT = """You are the tech lead on GCC-KNC. Ticket {id} is in state {state}, on branch {branch}.
Run: python tools/pm.py show {id}
{task}
Read only what you need: the ticket, git log and git diff main...{branch}. Rerun something only if you doubt it.
For gcc: yes tickets also review git -C .work/_shared/gcc diff knc...{branch} and git -C .work/_shared/gcc log knc..{branch}.
You cannot edit files or run tools/check, so never promise either. A soft budget (size, test files, test ratio) is passed with submit --override '<reason>'. A ticket field, a protected file or a check you cannot run needs the interactive lead: say so, or escalate.
Finish with one pm.py command, run as plain `python tools/pm.py ...`: PM_ROLE is already set, and a prefix is refused. On approve, the --note is read by the project manager: say in one plain sentence what now works. Your final message is only the "PM update:" line it prints."""

LEAD_TASKS = {
    "review": "Review per docs/DEVELOPMENT_CYCLE.md section 7, then run pm.py approve, or pm.py changes with numbered findings, each with file:line. "
              "If an acceptance line names a step the interactive lead runs (an x86 check by the lead, a card run before approval) "
              "and the ticket does not yet record its result, do not approve: run pm.py escalate saying which result is missing.",
    "red-review": "Check that the failing tests prove the acceptance criteria and fail for the right reason, then run pm.py approve or pm.py changes.",
    "blocked": "Answer the question with pm.py answer, or send it to the owner with pm.py escalate if it is the owner's decision.",
}


def newest(*patterns):
    found = [path for pattern in patterns for path in glob.glob(os.path.expandvars(pattern))]
    return max(found, key=os.path.getmtime) if found else None


def claude_binary():
    # A Microsoft Store install keeps %APPDATA% in its package folder, which only the app sees as %APPDATA%.
    return newest(r"%LOCALAPPDATA%\Packages\*Claude*\LocalCache\Roaming\Claude\claude-code\*\*\claude.exe",
                  r"%APPDATA%\Claude\claude-code\*\*\claude.exe") or "claude"


def engineer_command(board, ticket, worktree):
    # Owner, 2026-11-07: engineers are Claude Code sessions from now on; "codex" stays selectable.
    # A ticket's own backend field wins (owner, 2026-11-08: Codex gpt-6.1 as the fallback for a stuck ticket).
    if (ticket.fields.get("backend") or board.policy.get("engineer_backend", "codex")) == "claude":
        effort = board.policy.get("engineer_effort") or board.budget(ticket)["effort"]
        model = ticket.fields.get("model") or board.budget(ticket).get("claude_model") or "opus"
        os.makedirs(storage.shared_area(board.root), exist_ok=True)
        dirs = [storage.state_dir(board.root), storage.shared_area(board.root)]
        try:
            with open(os.path.join(board.root, "config", "card.local.json"), encoding="utf8") as f:
                ledger = json.load(f).get("ledger")
        except (OSError, ValueError):
            ledger = None
        if ledger:
            dirs.append(os.path.dirname(os.path.abspath(ledger)))
        command = [claude_binary(), "-p", ENGINEER_PROMPT.format(id=ticket.id), "--output-format", "json",
                   "--no-session-persistence", "--model", model, "--effort", effort,
                   "--allowedTools", "Read,Edit,Write,Grep,Glob,Bash"]
        for d in dirs:
            command += ["--add-dir", d]
        return command
    codex = newest(r"%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe") or "codex"
    # The policy can fix effort and service tier ("priority" is Codex's fast mode) for every engineer session.
    effort = board.policy.get("engineer_effort") or board.budget(ticket)["effort"]
    tier = board.policy.get("engineer_service_tier")
    trust ='projects."%s".trust_level="trusted"' % worktree.replace("\\", "\\\\")
    os.makedirs(storage.shared_area(board.root), exist_ok=True)
    # A ticket's own model field wins, then its depth's budget, then the policy default (owner, 2026-11-05).
    model = ticket.fields.get("model") or board.budget(ticket).get("model") or board.policy.get("engineer_model")
    # Logs and the shared build area sit beside the worktree, outside what workspace-write allows by itself.
    roots = [storage.state_dir(board.root), storage.shared_area(board.root)]
    # The card job ledger is shared with another project's agent, so it lives outside both (owner, 2026-11-03).
    try:
        with open(os.path.join(board.root, "config", "card.local.json"), encoding="utf8") as f:
            ledger = json.load(f).get("ledger")
    except (OSError, ValueError):
        ledger = None
    if ledger:
        roots.append(os.path.dirname(os.path.abspath(ledger)))
    writable = "sandbox_workspace_write.writable_roots=" + json.dumps(roots)
    return [codex, "exec"] + (["-m", model] if model else []) + ["--json", "--ephemeral", "-C", worktree, "--sandbox", "workspace-write",
            "--dangerously-bypass-hook-trust", "-c", trust, "-c", writable, "-c", 'approval_policy="never"',
            "-c", 'model_reasoning_effort="%s"' % effort] + (["-c", 'service_tier="%s"' % tier] if tier else []) + [
            ENGINEER_PROMPT.format(id=ticket.id)]


def lead_command(board, ticket):
    # A Microsoft Store install keeps %APPDATA% in its package folder, which only the app sees as %APPDATA%.
    claude = newest(r"%LOCALAPPDATA%\Packages\*Claude*\LocalCache\Roaming\Claude\claude-code\*\*\claude.exe",
                    r"%APPDATA%\Claude\claude-code\*\*\claude.exe") or "claude"
    state = ticket.state
    prompt = LEAD_PROMPT.format(id=ticket.id, state=state, branch=ticket.fields.get("branch", ""),
                                task=LEAD_TASKS[state])
    return [claude, "-p", prompt, "--output-format", "json", "--no-session-persistence",
            "--model", "opus", "--effort", board.budget(ticket)["effort"],
            "--allowedTools", "Read,Grep,Glob,Bash(git log*),Bash(git diff*),Bash(git show*),"
            "Bash(git -C .work/_shared/gcc log*),Bash(git -C .work/_shared/gcc diff*),"
            "Bash(git -C .work/_shared/gcc show*),Bash(python tools/pm.py*)"]


def session_env(board, ticket, role):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env.update(PM_ROLE=role, PM_TICKET=ticket.id, PM_DEPTH=ticket.fields.get("depth", "standard"),
               PM_ALLOW_TIERS=ticket.fields.get("allow_tiers", ""), PM_ALLOW_BULK=ticket.fields.get("allow_bulk", ""))
    if role == "engineer":
        # The sandbox user does not own the shared GCC checkout, so git calls it dubious. Command-line
        # scope is trusted for safe.directory; Codex would drop GIT_CONFIG_KEY_0 because it contains KEY.
        # Git for Windows and Cygwin git spell the same path differently, so trust both.
        gcc = os.path.join(storage.shared_area(board.root), "gcc").replace("\\", "/")
        cygwin = "/cygdrive/%s%s" % (gcc[0].lower(), gcc[2:])
        env["GIT_CONFIG_PARAMETERS"] = "'safe.directory'='%s' 'safe.directory'='%s'" % (gcc, cygwin)
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
        usage["input_tokens"] += (found.get("input_tokens", 0) + found.get("cache_read_input_tokens", 0)
                                  + found.get("cache_creation_input_tokens", 0))
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


def refresh_status(board):
    """The session's last ticket change came before its tokens were recorded, so show them now."""
    try:
        with pm.board_lock(board.root):
            path = status.write(board, pm.next_action(board))
            pm.run_git("add", "--", path, cwd=board.root)
            pm.run_git("commit", "-q", "-m", "pm: status after session", "--", path, cwd=board.root)
    except Exception as problem:  # The status page must never stop the work.
        print("  Status page not updated: %s" % problem)


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
        try:
            pm.cmd_start(board, argparse.Namespace(id=ticket.id))
        except pm.Refused as refused:
            print("  %s could not start, so no session ran: %s" % (ticket.id, refused))
            return False
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
    except FileNotFoundError:
        print("  Could not find the %s command line, so no session ran and the ticket is unchanged.\n"
              "  Ask a Claude or Codex session to take this ticket instead (see KICKOFF.md)." % role)
        return False
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
    refresh_status(board)
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
    # One dispatcher per lane may run at once: gcc tickets share the GCC checkout, tools tickets do not.
    parser.add_argument("--lane", help="gcc, tools, or any research lane named on tickets")
    args = parser.parse_args(argv)
    board = pm.Board()
    for _ in range(args.max_sessions):
        if any(t.state == "owner" and args.lane in (None, pm.lane_of(t)) for t in board.tickets()):
            break
        level, message = storage.check(board.root, board.policy)
        if level != "ok":
            print(message)
        if level == "hard":
            print("No session started. See: python tools/storage.py")
            break
        action = pm.next_action(board, args.lane)
        if action is None or not run_session(board, action[1], action[0], args.dry_run):
            break
    pm.cmd_board(board, None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
