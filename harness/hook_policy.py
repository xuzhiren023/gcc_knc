#!/usr/bin/env python3
"""Codex PreToolUse hook: refuse wasteful commands and enforce session budgets.

Printing a deny decision as JSON refuses the call. This is a guardrail, not a
security boundary; tools/pm.py checks the result again at submit.
"""
import json
import os
import re
import sys
import tempfile

POLICY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "policy.json")
COMMAND_POSITION = r"(?:^|[;&|(]\s*|-Command\s+[\"']?)"


def load_policy():
    with open(POLICY, encoding="utf8") as f:
        return json.load(f)


def budget_for(policy, env):
    return policy["budgets"].get(env.get("PM_DEPTH", "standard"), policy["budgets"]["standard"])


def command_text(tool_input):
    """The shell command, wherever this Codex version puts it."""
    tool_input = tool_input or {}
    if not isinstance(tool_input, dict):
        return str(tool_input)
    for key in ("command", "cmd", "script"):
        if tool_input.get(key):
            command = tool_input[key]
            return " ".join(command) if isinstance(command, list) else str(command)
    return ""


def check_command(command, policy, env):
    """Return a denial reason, or None to allow."""
    if re.search(policy["exempt"], command):
        return None
    full = re.search(policy["full_tier_pattern"], command)
    if full and full.group(1) not in env.get("PM_ALLOW_TIERS", "").split(","):
        return "Tier %s is not allowed on this ticket. It runs at sprint close or when the ticket says so." % full.group(1)
    if re.search(policy["wrappers"], command):
        return None
    for rule in policy["hook_rules"]:
        if re.search(COMMAND_POSITION + "(?:" + rule["command"] + ")", command):
            return rule["reason"]
        if rule.get("anywhere") and re.search(rule["anywhere"], command):
            return rule["reason"]
    return None


def check_budget(command, counts, policy, env):
    """Update COUNTS for this call and return a denial reason, or None."""
    budget = budget_for(policy, env)
    if re.search(policy["exempt"], command):
        return None
    counts["tool_calls"] = counts.get("tool_calls", 0) + 1
    if counts["tool_calls"] > budget["tool_calls"]:
        return ("Session budget of %d tool calls reached. Commit what works, then run "
                "tools/pm.py submit, or tools/pm.py ask with a specific question." % budget["tool_calls"])
    if re.search(policy["test_run_pattern"], command):
        counts["test_runs"] = counts.get("test_runs", 0) + 1
        if counts["test_runs"] > budget["test_runs"]:
            return ("Budget of %d test runs reached. Do not re-verify passing work. Submit it, "
                    "or ask with the failure." % budget["test_runs"])
    return None


def main():
    # Windows hosts may add a byte-order mark. A crash here would silently allow the call.
    event = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    policy = load_policy()
    # apply_patch also uses tool_input.command, but that text is file content.
    is_shell = event.get("tool_name", "Bash") != "apply_patch"
    command = command_text(event.get("tool_input")) if is_shell else ""
    reason = check_command(command, policy, os.environ)
    if reason is None:
        state_dir = os.path.join(tempfile.gettempdir(), "gcc_knc_hook")
        path = os.path.join(state_dir, re.sub(r"\W", "_", str(event.get("session_id", "none"))) + ".json")
        try:
            with open(path, encoding="utf8") as f:
                counts = json.load(f)
        except (OSError, ValueError):
            counts = {}
        reason = check_budget(command, counts, policy, os.environ)
        try:
            os.makedirs(state_dir, exist_ok=True)
            with open(path, "w", encoding="utf8") as f:
                json.dump(counts, f)
        except OSError:
            pass  # Losing a count must not stop the work or hide a denial.
    if reason:
        # Verified live on Windows: Codex 0.163 honours this form and ignores exit code 2.
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
