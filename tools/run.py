#!/usr/bin/env python3
"""Run a build or test with short output, and skip it if nothing it depends on changed.

    python tools/run.py --name t1 --inputs tests tools -- python tools/check.py t1

Output goes to a log file; only a short summary reaches the agent's context.
With --inputs, a command that already passed on the same committed content
prints CACHED and does not run again. --force reruns it, and needs a reason.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time

import storage

TAIL_LINES = 12
ERROR_LINES = 8
ERROR_RX = re.compile(r"\b(error|fail(ed|ure)?|fatal|internal compiler error|segmentation fault)\b", re.I)


def git(*args):
    out = subprocess.run(("git",) + args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
    return out.stdout.strip() if out.returncode == 0 else None


def state_dir():
    path = storage.state_dir(storage.main_root())
    os.makedirs(os.path.join(path, "logs"), exist_ok=True)
    return path


def input_key(name, inputs, command):
    """Identify the committed content of INPUTS, or None if it is uncommitted."""
    if git("status", "--porcelain", "--", *inputs):
        return None
    ids = [git("rev-parse", "HEAD:" + path) or path for path in inputs]
    return "|".join([name] + ids + [" ".join(command)])


def load_cache(path):
    try:
        with open(path, encoding="utf8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def summarize(log_path):
    with open(log_path, encoding="utf8", errors="replace") as f:
        lines = f.read().splitlines()
    tail = lines[-TAIL_LINES:]
    head = lines[:-TAIL_LINES]
    errors = [line for line in head if ERROR_RX.search(line)][-ERROR_LINES:]
    return errors, tail, len(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--inputs", nargs="*", default=[], help="paths whose committed content decides the result")
    parser.add_argument("--force", metavar="REASON", help="rerun despite a cached pass")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("no command given")

    root = storage.main_root()
    limits = storage.load_policy(root)["storage"]
    free = shutil.disk_usage(root).free / storage.GIB
    if free < limits["min_drive_free_gib"]:
        print("REFUSED: the drive has %.0f GiB free; the project stops below %d GiB." % (free, limits["min_drive_free_gib"]))
        return 3

    state = state_dir()
    cache_path = os.path.join(state, "run-cache.json")
    cache = load_cache(cache_path)
    key = input_key(args.name, args.inputs, command) if args.inputs else None
    if key and key in cache and not args.force:
        print("CACHED %s: passed at %s on this same content. Not rerun." % (args.name, cache[key]))
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(state, "logs", "%s-%s.log" % (re.sub(r"\W", "_", args.name), stamp))
    start = time.time()
    with open(log_path, "wb") as log:
        code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
    minutes = (time.time() - start) / 60

    errors, tail, total = summarize(log_path)
    print("%s %s: exit %d, %.1f min, %d log lines" % ("PASS" if code == 0 else "FAIL", args.name, code, minutes, total))
    if code != 0 and errors:
        print("--- error lines")
        print("\n".join(line[:200] for line in errors))
    print("--- last lines")
    print("\n".join(line[:200] for line in tail))
    print("--- log: " + log_path)

    storage.prune_logs(state, limits["logs_keep_mb"])
    if key and code == 0:
        cache[key] = stamp
        with open(cache_path, "w", encoding="utf8") as f:
            json.dump(cache, f)
    return code


if __name__ == "__main__":
    sys.exit(main())
