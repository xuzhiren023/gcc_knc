#!/usr/bin/env python3
"""The project board. Tickets in work/tickets/ are the only channel between agents.

Engineer:  start ID | commit ID -m M | red ID --note N | submit ID --note N [--override WHY] | ask ID TEXT
Lead:      approve ID [--note N] | changes ID TEXT | answer ID TEXT
Owner:     decide ID TEXT
Anyone:    board | status | show ID | inbox | usage | escalate ID TEXT
"""
import argparse
import contextlib
import datetime
import json
import os
import re
import subprocess
import sys
import time

import status
import storage

STATES_ACTIVE = ("doing", "red-review", "review", "changes", "blocked")
ROLES = {"engineer", "lead", "owner"}


class Refused(Exception):
    pass


_lock_depth = 0


@contextlib.contextmanager
def board_lock(root):
    """One board change at a time, so two dispatcher lanes never race in git. Re-entrant per process."""
    global _lock_depth
    if _lock_depth:
        _lock_depth += 1
        try:
            yield
        finally:
            _lock_depth -= 1
        return
    path = os.path.join(storage.state_dir(root), "board.lock")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # An approve runs tools/check t0 under the lock, so the other lane may wait minutes.
    deadline = time.monotonic() + float(os.environ.get("PM_LOCK_WAIT", "900"))
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise Refused("the board is busy: %s is held by another pm or dispatcher process. "
                              "If none is running, it was left by a crash; remove it." % path)
            time.sleep(0.2)
    os.write(fd, str(os.getpid()).encode("ascii"))
    os.close(fd)
    _lock_depth = 1
    try:
        yield
    finally:
        _lock_depth = 0
        os.remove(path)


def lane_of(ticket):
    """gcc tickets share one GCC checkout and build; a ticket that only uses the build says lane: gcc."""
    return ticket.fields.get("lane") or ("gcc" if ticket.fields.get("gcc") == "yes" else "tools")


def run_git(*args, cwd=None, check=True):
    result = subprocess.run(("git",) + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True)
    if check and result.returncode != 0:
        raise Refused("git %s failed:\n%s" % (" ".join(args), result.stdout.strip()[:800]))
    return result.stdout.strip()


def main_checkout():
    """The first worktree is the main checkout, wherever this runs from."""
    for line in run_git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            return line[len("worktree "):]
    raise Refused("not in a git repository")


class Board:
    def __init__(self):
        self.root = main_checkout()
        self.dir = os.path.join(self.root, "work", "tickets")
        with open(os.path.join(self.root, "harness", "policy.json"), encoding="utf8") as f:
            self.policy = json.load(f)

    def ids(self):
        if not os.path.isdir(self.dir):
            return []
        return sorted(name[:-3] for name in os.listdir(self.dir) if name.endswith(".md"))

    def tickets(self):
        return [self.load(ticket_id) for ticket_id in self.ids()]

    def load(self, ticket_id):
        path = os.path.join(self.dir, ticket_id + ".md")
        if not os.path.exists(path):
            raise Refused("no ticket " + ticket_id)
        with open(path, encoding="utf8") as f:
            text = f.read()
        match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
        if not match:
            raise Refused(ticket_id + " has no front matter")
        fields = dict(line.split(": ", 1) if ": " in line else (line.rstrip(":"), "")
                      for line in match.group(1).splitlines())
        return Ticket(self, ticket_id, fields, match.group(2))

    def budget(self, ticket):
        budget = dict(self.policy["budgets"][ticket.fields.get("depth", "standard")])
        # The lead can raise these on a ticket: many small test files, sessions lost to harness faults, or owner-granted room.
        for limit in ("new_test_files", "sessions", "input_tokens"):
            if ticket.fields.get(limit):
                budget[limit] = int(ticket.fields[limit])
        return budget

    def worktree(self, ticket):
        return storage.worktree(self.root, ticket.id)

    def state_dir(self):
        path = storage.state_dir(self.root)
        os.makedirs(path, exist_ok=True)
        return path


class Ticket:
    def __init__(self, board, ticket_id, fields, body):
        self.board, self.id, self.fields, self.body = board, ticket_id, fields, body

    @property
    def state(self):
        return self.fields["state"]

    def deps(self):
        return [d.strip() for d in self.fields.get("deps", "").split(",") if d.strip()]

    def save(self, verb, entry=None):
        with board_lock(self.board.root):
            self._save(verb, entry)

    def _save(self, verb, entry):
        if entry:
            today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            role = os.environ.get("PM_ROLE", "engineer")
            self.body = self.body.rstrip("\n") + "\n\n- %s %s %s: %s\n" % (today, role, verb, entry)
        path = os.path.join(self.board.dir, self.id + ".md")
        front = "\n".join("%s: %s" % item for item in self.fields.items())
        with open(path, "w", encoding="utf8", newline="\n") as f:
            f.write("---\n%s\n---\n%s" % (front, self.body))
        root = self.board.root
        paths = [path]
        try:
            paths.append(status.write(self.board, next_action(self.board)))
        except Exception as problem:  # The status page must never stop the work.
            print("Status page not updated: %s" % problem)
        run_git("add", "--", *paths, cwd=root)
        run_git("commit", "-q", "-m", "pm: %s %s -> %s" % (self.id, verb, self.state), "--", *paths, cwd=root)
        line = status.update_line(self)
        print("PM update: " + line)
        if self.state in status.NOTIFY_STATES:
            try:
                status.notify("GCC-KNC", line)
            except OSError:
                pass


def require_role(*allowed):
    role = os.environ.get("PM_ROLE", "engineer")
    if role not in ROLES:
        raise Refused("unknown PM_ROLE " + role)
    if role not in allowed:
        raise Refused("this action belongs to the %s, not the %s" % (" or ".join(allowed), role))


def require_state(ticket, *allowed):
    if ticket.state not in allowed:
        raise Refused("%s is in state %s; expected %s" % (ticket.id, ticket.state, " or ".join(allowed)))


def limit_text(board, text):
    limit = board.policy["note_max_chars"]
    if len(text) > limit:
        raise Refused("note is %d characters; the limit is %d. Point to the log path instead of quoting it."
                      % (len(text), limit))
    return " ".join(text.split())


def next_action(board, lane=None):
    """Who should act next, and on what: (role, ticket) or None. Finish before starting.
    With a lane, only that lane's tickets count, and the WIP limit applies per lane."""
    tickets = board.tickets()
    done = {t.id for t in tickets if t.state == "done"}
    if lane:
        tickets = [t for t in tickets if lane_of(t) == lane]
    for states, role in ((("review", "red-review", "blocked"), "lead"), (("changes", "doing"), "engineer")):
        for ticket in tickets:
            if ticket.state in states:
                return role, ticket
    active = sum(t.state in STATES_ACTIVE for t in tickets)
    if active >= board.policy["wip_limit"]:
        return None
    for ticket in tickets:
        if ticket.state == "ready" and all(d in done for d in ticket.deps()):
            return "engineer", ticket
    return None


def added_lines(diff):
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and current:
            yield current, line[1:]


def gcc_current_branch(board, ticket):
    path = os.path.join(storage.shared_area(board.root), "gcc")
    if ticket.fields.get("gcc") != "yes" or not os.path.isdir(os.path.join(path, ".git")):
        return None
    return run_git("branch", "--show-current", cwd=path)


def gcc_checkout(board, ticket, allow_dirty=False):
    """WIP is one: the shared checkout may belong only to this ticket or knc."""
    if ticket.fields.get("gcc") != "yes":
        return None
    path = os.path.join(storage.shared_area(board.root), "gcc")
    if not os.path.isdir(os.path.join(path, ".git")):
        raise Refused("GCC checkout missing: " + path)
    if not allow_dirty and run_git("status", "--porcelain", cwd=path):
        raise Refused("uncommitted changes in the GCC checkout")
    branch = run_git("branch", "--show-current", cwd=path)
    if branch not in ("knc", ticket.fields["branch"]):
        raise Refused("GCC checkout is on another branch: " + branch)
    return path


def submit_problems(board, ticket, cwd):
    """Return (hard problems, budget problems) for this branch against main."""
    policy = board.policy
    budget = board.budget(ticket)
    hard, soft = [], []
    if run_git("status", "--porcelain", cwd=cwd):
        hard.append("uncommitted changes in the worktree")
    base = run_git("merge-base", "main", "HEAD", cwd=cwd)
    subjects = run_git("log", "--format=%s", base + "..HEAD", cwd=cwd).splitlines()
    gcc = gcc_checkout(board, ticket)
    gcc_diff = "knc..." + ticket.fields["branch"] if gcc else None
    if gcc:
        subjects += run_git("log", "--format=%s", "knc.." + ticket.fields["branch"], cwd=gcc).splitlines()
    if not subjects:
        hard.append("no commits on this branch")
    if ticket.fields.get("type", "code") == "code" and not any("[red]" in s for s in subjects):
        hard.append("no [red] test commit: this is test-driven work")

    names = run_git("diff", "--name-status", base + "...HEAD", cwd=cwd).splitlines()
    new_tests = 0
    for line in names:
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        if any(path.startswith(p) or path == p for p in policy["protected_paths"]):
            hard.append("protected path changed: %s (raise it with ask)" % path)
        is_new = status.startswith("A")
        if is_new and re.search(policy["receipt_files"], path):
            hard.append("receipt-style file added: %s (put one short note on the ticket instead)" % path)
        if is_new and any(path.startswith(p) for p in policy["test_paths"]):
            new_tests += 1

    limits = policy["storage"]
    total_bytes = 0
    for line in names:
        parts = line.split("\t")
        if parts[0].startswith(("A", "M", "R", "C")):
            size = int(run_git("cat-file", "-s", "HEAD:" + parts[-1], cwd=cwd))
            total_bytes += size
            if size > limits["max_file_mb"] * storage.MIB:
                hard.append("%s is %.1f MiB; the limit is %d MiB. Large data stays out of git."
                            % (parts[-1], size / storage.MIB, limits["max_file_mb"]))
    if total_bytes > limits["max_diff_mb"] * storage.MIB:
        hard.append("this change adds %.1f MiB of files; the limit is %d MiB"
                    % (total_bytes / storage.MIB, limits["max_diff_mb"]))
    worktree_gib = storage.tree_size(cwd) / storage.GIB
    if worktree_gib > budget["disk_gib"]:
        hard.append("the worktree uses %.1f GiB; the budget is %d GiB. Delete build outputs first."
                    % (worktree_gib, budget["disk_gib"]))

    test_added = code_added = 0
    for line in run_git("diff", "--numstat", base + "...HEAD", cwd=cwd).splitlines():
        added, removed, path = line.split("\t", 2)
        if added == "-":
            continue
        if any(path.startswith(p) for p in policy["test_paths"]):
            test_added += int(added)
        else:
            code_added += int(added) + int(removed)
    if gcc:
        for line in run_git("diff", "--numstat", gcc_diff, cwd=gcc).splitlines():
            added, removed, _ = line.split("\t", 2)
            if added != "-":
                code_added += int(added) + int(removed)
    if test_added + code_added > budget["changed_lines"]:
        soft.append("%d changed lines; the budget is %d, so split the ticket"
                    % (test_added + code_added, budget["changed_lines"]))
    if new_tests > budget["new_test_files"]:
        soft.append("%d new test files; the budget is %d" % (new_tests, budget["new_test_files"]))
    if test_added >= policy["test_ratio_min_lines"] and test_added > policy["test_to_code_ratio"] * max(code_added, 1):
        soft.append("%d test lines for %d code lines; test the acceptance criteria, not every path"
                    % (test_added, code_added))

    hash_rx = re.compile(policy["hash_in_diff"], re.I)
    for path, text in added_lines(run_git("diff", "-U0", base + "...HEAD", cwd=cwd)):
        if hash_rx.search(text):
            hard.append("hashing added in %s: %s" % (path, text.strip()[:80]))
            break
    return hard, soft


def cmd_start(board, args):
    require_role("engineer")
    ticket = board.load(args.id)
    require_state(ticket, "ready", "changes", "doing")
    if ticket.state == "ready":
        action = next_action(board, lane_of(ticket))
        if action is None or action[1].id != ticket.id:
            raise Refused("%s cannot start now: its dependencies or the WIP limit prevent it" % ticket.id)
    path = board.worktree(ticket)
    os.makedirs(storage.shared_area(board.root), exist_ok=True)
    branch = ticket.fields.setdefault("branch", "%s/%s" % (ticket.fields.get("sprint", "s0"), ticket.id))
    # Resuming keeps this ticket's own uncommitted GCC work; any other checkout must be clean.
    gcc = gcc_checkout(board, ticket, allow_dirty=gcc_current_branch(board, ticket) == branch)
    if gcc:
        exists = run_git("branch", "--list", branch, cwd=gcc)
        target = (branch,) if exists else ("-b", branch, "knc")
        run_git("checkout", "-q", *target, cwd=gcc)
    if not os.path.isdir(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        exists = run_git("branch", "--list", branch, cwd=board.root)
        target = (path, branch) if exists else ("-b", branch, path)
        run_git("worktree", "add", "-q", *target, cwd=board.root)
    if ticket.state != "doing":
        ticket.fields["state"] = "doing"
        ticket.save("start")
    print("worktree: " + path)


def cmd_commit(board, args):
    """Commit the worktree or shared GCC. Codex's sandbox protects .git and exempts only plain commands, so
    git add or git commit inside a longer script fails."""
    require_role("engineer")
    ticket = board.load(args.id)
    require_state(ticket, "doing")
    worktree = board.worktree(ticket)
    if args.gcc:
        worktree = gcc_checkout(board, ticket, allow_dirty=True)
        if worktree is None:
            raise Refused("--gcc requires a gcc: yes ticket")
        if not run_git("branch", "--list", "knc", cwd=worktree):
            run_git("branch", "knc", "releases/gcc-16.2.0", cwd=worktree)
        branch = ticket.fields["branch"]
        if run_git("branch", "--show-current", cwd=worktree) == "knc":
            exists = run_git("branch", "--list", branch, cwd=worktree)
            target = (branch,) if exists else ("-b", branch, "knc")
            run_git("checkout", "-q", *target, cwd=worktree)
    run_git("add", "-A", cwd=worktree)
    if not run_git("status", "--porcelain", cwd=worktree):
        raise Refused("nothing to commit")
    run_git("commit", "-q", "-m", args.message, cwd=worktree)
    print(run_git("log", "-1", "--format=%h %s", cwd=worktree))


def cmd_red(board, args):
    require_role("engineer")
    ticket = board.load(args.id)
    require_state(ticket, "doing")
    ticket.fields["state"] = "red-review"
    ticket.fields["head"] = run_git("rev-parse", "--short", "HEAD", cwd=board.worktree(ticket))
    ticket.save("red", limit_text(board, args.note))
    print("%s is waiting for the lead to approve the failing tests" % ticket.id)


def cmd_submit(board, args):
    require_role("engineer")
    ticket = board.load(args.id)
    require_state(ticket, "doing")
    note = limit_text(board, args.note)
    if ticket.fields.get("depth") == "deep" and ticket.fields.get("red_approved") != "yes" \
            and ticket.fields.get("type", "code") == "code":
        raise Refused("deep ticket: run pm.py red and wait for approval first")
    worktree = board.worktree(ticket)
    hard, soft = submit_problems(board, ticket, worktree)
    if soft and not args.override:
        hard += soft
    if hard:
        tail = ("\nBudget items are soft: if the lead has approved the size, resubmit with --override '<reason>'."
                if soft and not args.override else "")
        raise Refused("submit refused:\n  - " + "\n  - ".join(hard) + tail)
    if soft:
        note += " | OVER BUDGET (%s): %s" % ("; ".join(soft), args.override)
    ticket.fields["state"] = "review"
    ticket.fields["head"] = run_git("rev-parse", "--short", "HEAD", cwd=worktree)
    if ticket.fields.get("gcc") == "yes":
        ticket.fields["gcc_head"] = run_git("rev-parse", ticket.fields["branch"], cwd=gcc_checkout(board, ticket))
    ticket.save("submit", note)
    print("%s submitted at %s. End this session." % (ticket.id, ticket.fields["head"]))


def machine_check(worktree):
    """Run the branch's own T0 before it can merge, so approval never rests on a report alone."""
    if not os.path.exists(os.path.join(worktree, "tools", "check")):
        return ""
    try:
        done = subprocess.run([sys.executable, os.path.join("tools", "check"), "t0"], cwd=worktree, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                              errors="replace", timeout=600)
    except subprocess.TimeoutExpired:
        raise Refused("not merged: tools/check t0 ran past 10 minutes. Use pm.py changes.")
    if done.returncode != 0:
        raise Refused("not merged: tools/check t0 failed. Use pm.py changes.\n" + done.stdout[-1500:])
    return " Machine check: tools/check t0 passed."


def cmd_approve(board, args):
    require_role("lead", "owner")
    ticket = board.load(args.id)
    require_state(ticket, "review", "red-review")
    if ticket.state == "red-review":
        ticket.fields.update(state="doing", red_approved="yes")
        ticket.save("approve-red", limit_text(board, args.note or "tests approved"))
        print(ticket.id + ": failing tests approved")
        return
    branch = ticket.fields["branch"]
    worktree = board.worktree(ticket)
    note = limit_text(board, args.note or "merged") + machine_check(worktree)
    message = "Merge %s: %s" % (ticket.id, ticket.fields.get("title", ""))
    gcc = gcc_checkout(board, ticket)
    if gcc:
        if run_git("rev-parse", branch, cwd=gcc) != ticket.fields.get("gcc_head"):
            raise Refused("GCC branch moved since submit; submit again before approval")
        if run_git("status", "--porcelain", cwd=board.root) or \
                run_git("branch", "--show-current", cwd=board.root) != "main":
            raise Refused("main checkout must be clean and on main before merging a GCC ticket")
        main_head = run_git("rev-parse", "HEAD", cwd=board.root)
        knc_head = run_git("rev-parse", "knc", cwd=gcc)
        previous = run_git("branch", "--show-current", cwd=gcc)
        run_git("checkout", "-q", "knc", cwd=gcc)
        try:
            run_git("merge", "--no-ff", "-q", "-m", message, branch, cwd=gcc)
            run_git("merge", "--no-ff", "-q", "-m", message, branch, cwd=board.root)
        except Refused:
            # Both checkouts were clean. Restore both integration tips and clear conflicts.
            run_git("reset", "--hard", main_head, cwd=board.root)
            run_git("reset", "--hard", knc_head, cwd=gcc)
            run_git("checkout", "-q", previous, cwd=gcc)
            raise
    else:
        run_git("merge", "--no-ff", "-q", "-m", message, branch, cwd=board.root)
    if os.path.isdir(worktree):
        run_git("worktree", "remove", "--force", worktree, cwd=board.root)
    ticket.fields["state"] = "done"
    ticket.save("approve", note)
    print(ticket.id + ": approved and merged")


def cmd_changes(board, args):
    require_role("lead", "owner")
    ticket = board.load(args.id)
    require_state(ticket, "review", "red-review")
    rounds = int(ticket.fields.get("rounds", "0")) + 1
    ticket.fields["rounds"] = str(rounds)
    if rounds > board.policy["max_review_rounds"]:
        ticket.fields.update(state="owner", resume="changes")
        ticket.save("escalate", "over %d review rounds: %s" % (board.policy["max_review_rounds"], args.text))
        print(ticket.id + ": too many review rounds, sent to the owner")
        return
    ticket.fields["state"] = "changes"
    ticket.save("changes", args.text)
    print(ticket.id + ": changes requested")


def cmd_ask(board, args):
    require_role("engineer")
    ticket = board.load(args.id)
    require_state(ticket, "doing", "changes")
    ticket.fields["state"] = "blocked"
    ticket.save("ask", limit_text(board, args.text))
    print("%s is waiting for an answer. End this session." % ticket.id)


def cmd_answer(board, args):
    require_role("lead", "owner")
    ticket = board.load(args.id)
    require_state(ticket, "blocked")
    ticket.fields["state"] = "doing"
    ticket.save("answer", args.text)
    print(ticket.id + ": answered")


def cmd_escalate(board, args):
    ticket = board.load(args.id)
    if ticket.state in ("done", "owner"):
        raise Refused("%s is already %s" % (ticket.id, ticket.state))
    ticket.fields.update(state="owner", resume=ticket.state)
    ticket.save("escalate", limit_text(board, args.text))
    print(ticket.id + ": sent to the owner")


def cmd_decide(board, args):
    require_role("owner")
    ticket = board.load(args.id)
    require_state(ticket, "owner")
    ticket.fields["state"] = ticket.fields.pop("resume", "doing")
    ticket.save("decide", args.text)
    print("%s: decision recorded, back to %s" % (ticket.id, ticket.state))


def cmd_board(board, _args):
    tickets = board.tickets()
    action = next_action(board)
    for ticket in tickets:
        print("%-7s %-10s %-8s %s" % (ticket.id, ticket.state, ticket.fields.get("depth", ""),
                                      ticket.fields.get("title", "")))
    print("\nNext: " + ("%s on %s" % (action[0], action[1].id) if action else "nothing can move"))
    waiting = [t.id for t in tickets if t.state == "owner"]
    if waiting:
        print("Waiting for the owner: " + ", ".join(waiting))


def cmd_status(board, _args):
    print(status.write(board, next_action(board)))


def cmd_show(board, args):
    ticket = board.load(args.id)
    print("\n".join("%s: %s" % item for item in ticket.fields.items()))
    print(ticket.body)


def cmd_inbox(board, _args):
    waiting = [t for t in board.tickets() if t.state == "owner"]
    if not waiting:
        print("Nothing needs the owner.")
    for ticket in waiting:
        entries = [line for line in ticket.body.splitlines() if line.startswith("- 2")]
        print("%s %s\n  %s" % (ticket.id, ticket.fields.get("title", ""), entries[-1] if entries else ""))


def cmd_usage(board, _args):
    path = os.path.join(board.state_dir(), "ledger.jsonl")
    totals = {}
    if os.path.exists(path):
        with open(path, encoding="utf8") as f:
            for line in f:
                entry = json.loads(line)
                item = totals.setdefault((entry["ticket"], entry["role"]), [0, 0, 0])
                item[0] += 1
                item[1] += entry.get("input_tokens", 0)
                item[2] += entry.get("output_tokens", 0)
    print("%-7s %-9s %8s %14s %10s" % ("ticket", "role", "sessions", "input tokens", "output"))
    for (ticket, role), (count, tokens_in, tokens_out) in sorted(totals.items()):
        print("%-7s %-9s %8d %14d %10d" % (ticket, role, count, tokens_in, tokens_out))
    for agent, (count, tokens_in) in sorted(status.hand_usage(board.root).items()):
        print("%-7s %-9s %8d %14d" % ("by hand", agent, count, tokens_in))


def parser():
    top = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = top.add_subparsers(dest="action")
    sub.required = True

    def add(name, func, *params):
        cmd = sub.add_parser(name)
        cmd.set_defaults(func=func)
        for param, kwargs in params:
            cmd.add_argument(param, **kwargs)

    ident = ("id", {})
    add("board", cmd_board)
    add("inbox", cmd_inbox)
    add("usage", cmd_usage)
    add("status", cmd_status)
    add("show", cmd_show, ident)
    add("start", cmd_start, ident)
    add("commit", cmd_commit, ident, ("--gcc", {"action": "store_true"}),
        ("-m", {"dest": "message", "required": True}))
    add("red", cmd_red, ident, ("--note", {"required": True}))
    add("submit", cmd_submit, ident, ("--note", {"required": True}), ("--override", {}))
    add("approve", cmd_approve, ident, ("--note", {}))
    for name, func in (("changes", cmd_changes), ("ask", cmd_ask), ("answer", cmd_answer),
                       ("escalate", cmd_escalate), ("decide", cmd_decide)):
        add(name, func, ident, ("text", {}))
    return top


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        board = Board()
        if args.func in (cmd_board, cmd_inbox, cmd_show):
            args.func(board, args)
        else:
            with board_lock(board.root):
                args.func(board, args)
    except Refused as refusal:
        print("REFUSED: %s" % refusal, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
