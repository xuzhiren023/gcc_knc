#!/usr/bin/env python3
"""Measure and limit this project's disk use. Hard links count once.

    python tools/storage.py          where the space is, against the limits
    python tools/storage.py --prune  remove old logs and worktrees of finished tickets

Limits are in harness/policy.json. Pruning touches only those two things.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

GIB = 2 ** 30
MIB = 2 ** 20


def tree_size(path, seen=None):
    """Bytes under PATH. Only large files are checked for hard links, which keeps this fast."""
    seen = set() if seen is None else seen
    total = 0
    stack = [path]
    while stack:
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                    continue
                size = entry.stat(follow_symlinks=False).st_size
                if size >= MIB:
                    # DirEntry.stat does not fill these fields on Windows.
                    info = os.lstat(entry.path)
                    if info.st_nlink > 1:
                        key = (info.st_dev, info.st_ino)
                        if key in seen:
                            continue
                        seen.add(key)
                total += size
            except OSError:
                pass
    return total


def main_root(cwd=None):
    out = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=cwd, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, universal_newlines=True).stdout
    for line in out.splitlines():
        if line.startswith("worktree "):
            return os.path.normpath(line[len("worktree "):])
    return os.path.normpath(cwd or os.getcwd())


def work_area(root):
    """Ticket worktrees, the shared build area and agent state. Git-ignored, and inside the
    project folder so that Codex's sandbox can write to it."""
    return os.path.join(root, ".work")


def state_dir(root):
    return os.path.join(work_area(root), "_state")


def worktree(root, ticket_id):
    return os.path.join(work_area(root), ticket_id)


def active_ticket(root):
    """Fields of the ticket being worked on, for sessions the dispatcher did not start."""
    tickets = os.path.join(root, "work", "tickets")
    if not os.path.isdir(tickets):
        return {}
    for name in sorted(os.listdir(tickets)):
        with open(os.path.join(tickets, name), encoding="utf8") as f:
            front = f.read().split("---\n")[1] if name.endswith(".md") else ""
        fields = dict(line.split(": ", 1) for line in front.splitlines() if ": " in line)
        if fields.get("state") == "doing":
            return fields
    return {}


def shared_area(root):
    return os.path.join(work_area(root), "_shared")


def project_bytes(root):
    return tree_size(root)


def load_policy(root):
    with open(os.path.join(root, "harness", "policy.json"), encoding="utf8") as f:
        return json.load(f)


def check(root, policy):
    """Return (level, message), where level is ok, soft or hard."""
    limits = policy["storage"]
    used = project_bytes(root) / GIB
    free = shutil.disk_usage(root).free / GIB
    if free < limits["min_drive_free_gib"]:
        return "hard", "The drive has %.0f GiB free; the project stops below %d GiB." % (free, limits["min_drive_free_gib"])
    if used >= limits["project_hard_gib"]:
        return "hard", "The project uses %.1f GiB; the limit is %d GiB." % (used, limits["project_hard_gib"])
    if used >= limits["project_soft_gib"]:
        return "soft", "The project uses %.1f GiB; it stops at %d GiB." % (used, limits["project_hard_gib"])
    return "ok", "The project uses %.1f GiB of %d GiB." % (used, limits["project_hard_gib"])


def prune_logs(state_dir, keep_mb):
    """Delete the oldest logs until they fit in KEEP_MB. Return bytes freed."""
    logs = os.path.join(state_dir, "logs")
    if not os.path.isdir(logs):
        return 0
    files = sorted((e for e in os.scandir(logs) if e.is_file()), key=lambda e: e.stat().st_mtime, reverse=True)
    kept = freed = 0
    for entry in files:
        size = entry.stat().st_size
        if kept + size <= keep_mb * MIB:
            kept += size
        else:
            os.remove(entry.path)
            freed += size
    return freed


def finished_worktrees(root):
    """Worktrees whose ticket is done. These should already be gone."""
    tickets = os.path.join(root, "work", "tickets")
    area = work_area(root)
    if not os.path.isdir(area):
        return []
    found = []
    for name in os.listdir(area):
        ticket = os.path.join(tickets, name + ".md")
        if not name.startswith("_") and os.path.exists(ticket):
            with open(ticket, encoding="utf8") as f:
                if re.search(r"^state: done$", f.read(), re.M):
                    found.append(os.path.join(area, name))
    return found


def report(root, policy):
    seen = set()
    rows = [("Git history", tree_size(os.path.join(root, ".git"), seen))]
    tracked = sum(tree_size(e.path, seen) if e.is_dir(follow_symlinks=False) else e.stat().st_size
                  for e in os.scandir(root) if e.name not in (".git", ".work"))
    rows.append(("Main checkout", tracked))
    area = work_area(root)
    if os.path.isdir(area):
        for entry in os.scandir(area):
            labels = {"_shared": "Shared build area", "_state": "Agent logs"}
            label = labels.get(entry.name, "Worktree " + entry.name)
            rows.append((label, tree_size(entry.path, seen)))
    for label, size in sorted(rows, key=lambda r: -r[1]):
        print("%8.2f GiB  %s" % (size / GIB, label))
    print("Free on this drive: %.0f GiB" % (shutil.disk_usage(root).free / GIB))
    print(check(root, policy)[1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prune", action="store_true")
    args = parser.parse_args(argv)
    root = main_root()
    policy = load_policy(root)
    if args.prune:
        freed = prune_logs(state_dir(root), policy["storage"]["logs_keep_mb"])
        print("Old logs removed: %.1f MiB" % (freed / MIB))
        for path in finished_worktrees(root):
            subprocess.run(["git", "worktree", "remove", "--force", path], cwd=root)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            print("Removed finished worktree: " + path)
    report(root, policy)
    return 0


if __name__ == "__main__":
    sys.exit(main())
