"""Tests for the board, the hook and the run wrapper. Reviewer-owned, like the harness."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "harness"))
sys.path.insert(0, os.path.join(REPO, "tools"))
import hook_policy  # noqa: E402

POLICY = hook_policy.load_policy()


def deny(command, env=None):
    return hook_policy.check_command(command, POLICY, env or {})


class HookCommands(unittest.TestCase):
    def test_refuses_waste(self):
        for command in ("sha256sum file", "Get-FileHash x.bin", 'powershell.exe -Command "Get-FileHash x"',
                        "ls; md5sum a", "python -c 'import hashlib'", "git push origin main", "git merge s0/x",
                        "ssh mic0 ls", "make -j8", "cd build && make check", "./configure --target=x",
                        "pytest tests", "python -m unittest", "cat build/x.log", "Get-Content foo.sum"):
            self.assertIsNotNone(deny(command), command)

    def test_allows_normal_work(self):
        for command in ("rg make src", "git commit -m 'make it sha256 free'", "python tools/pm.py submit S0-01 --note x",
                        "python tools/run.py --name t1 -- make -j8", "tail -n 50 build/x.log", "ls",
                        "python tools/card_run.py ./a.out", "Get-Content foo.log -Tail 20", "git diff main...HEAD"):
            self.assertIsNone(deny(command), command)

    def test_full_tiers_need_the_ticket_to_allow_them(self):
        self.assertIsNotNone(deny("python tools/check.py t4"))
        self.assertIsNone(deny("python tools/check.py t4", {"PM_ALLOW_TIERS": "t3,t4"}))
        self.assertIsNone(deny("python tools/check.py t1"))


class HookBudgets(unittest.TestCase):
    def test_tool_calls_run_out_but_finishing_stays_possible(self):
        env = {"PM_DEPTH": "light"}
        limit = POLICY["budgets"]["light"]["tool_calls"]
        counts = {"tool_calls": limit}
        self.assertIn("budget", hook_policy.check_budget("ls", counts, POLICY, env))
        self.assertIsNone(hook_policy.check_budget("git commit -m done", counts, POLICY, env))
        self.assertIsNone(hook_policy.check_budget("python tools/pm.py submit X --note y", counts, POLICY, env))

    def test_test_runs_run_out(self):
        env = {"PM_DEPTH": "light"}
        counts = {"test_runs": POLICY["budgets"]["light"]["test_runs"]}
        self.assertIn("re-verify", hook_policy.check_budget("python tools/run.py --name t1 -- x", counts, POLICY, env))


class HookProcess(unittest.TestCase):
    def run_hook(self, raw):
        return subprocess.run([sys.executable, os.path.join(REPO, "harness", "hook_policy.py")], input=raw,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def decision(self, done):
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] if done.stdout.strip() else "allow"

    def test_denial_uses_the_json_form_codex_honours(self):
        event = {"session_id": "unit", "tool_name": "Bash", "tool_input": {"command": "sha256sum x"}}
        done = self.run_hook(json.dumps(event).encode())
        self.assertEqual(self.decision(done), "deny")
        self.assertIn(b"Hashing", done.stdout)

    def test_byte_order_mark_does_not_turn_a_denial_into_an_allow(self):
        event = {"session_id": "unit", "tool_name": "Bash", "tool_input": {"command": "make --version"}}
        self.assertEqual(self.decision(self.run_hook(b"\xef\xbb\xbf" + json.dumps(event).encode())), "deny")

    def test_patch_text_is_not_treated_as_a_command(self):
        event = {"session_id": "unit-patch", "tool_name": "apply_patch",
                 "tool_input": {"command": "*** Add File: a\n+make all; sha256sum x\n"}}
        self.assertEqual(self.decision(self.run_hook(json.dumps(event).encode())), "allow")


TICKET = """---
id: {id}
title: Demo
state: ready
depth: {depth}
type: code
sprint: s0
deps: {deps}
---
## Outcome

Demo.
"""


class Sandbox(unittest.TestCase):
    """A real temporary repository, with the real tools copied in."""

    def setUp(self):
        self.top = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.top, ignore_errors=True)
        self.root = os.path.join(self.top, "proj")
        for sub in ("tools", "harness"):
            shutil.copytree(os.path.join(REPO, sub), os.path.join(self.root, sub),
                            ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(self.root, "work", "tickets"))
        with open(os.path.join(self.root, ".gitignore"), "w", newline="\n") as f:
            f.write("/.work/\n__pycache__/\n")
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.git("config", "core.autocrlf", "false")
        self.ticket("A-1", "standard")
        self.ticket("A-2", "deep", deps="A-1")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")

    def ticket(self, ident, depth, deps=""):
        with open(os.path.join(self.root, "work", "tickets", ident + ".md"), "w", newline="\n") as f:
            f.write(TICKET.format(id=ident, depth=depth, deps=deps))

    def git(self, *args, cwd=None):
        subprocess.run(("git",) + args, cwd=cwd or self.root, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

    def pm(self, *args, role="engineer", cwd=None):
        env = dict(os.environ, PM_ROLE=role)
        return subprocess.run([sys.executable, os.path.join(cwd or self.root, "tools", "pm.py")] + list(args),
                              cwd=cwd or self.root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True)

    def worktree(self, ident):
        return os.path.join(self.root, ".work", ident)

    def commit_file(self, path, text, message, cwd):
        full = os.path.join(cwd, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", newline="\n") as f:
            f.write(text)
        self.git("add", "-A", cwd=cwd)
        self.git("commit", "-qm", message, cwd=cwd)

    def state(self, ident):
        return self.pm("show", ident).stdout.split("state: ")[1].split("\n")[0]


class Flow(Sandbox):
    def test_ticket_goes_from_ready_to_merged_without_any_relay(self):
        self.assertEqual(self.pm("start", "A-1").returncode, 0)
        wt = self.worktree("A-1")
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".work", "_shared")))
        self.commit_file("tests/regress/t.py", "assert False\n", "test(A-1): x [red]", wt)
        self.commit_file("src/a.py", "x = 1\n", "feat(A-1): x", wt)
        done = self.pm("submit", "A-1", "--note", "T0 1 pass", cwd=wt)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.state("A-1"), "review")
        done = self.pm("approve", "A-1", role="lead")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.state("A-1"), "done")
        self.assertTrue(os.path.exists(os.path.join(self.root, "src", "a.py")))
        self.assertFalse(os.path.isdir(wt))

    def test_commit_command_commits_the_worktree(self):
        self.pm("start", "A-1")
        wt = self.worktree("A-1")
        self.assertIn("nothing to commit", self.pm("commit", "A-1", "-m", "x").stdout)
        os.makedirs(os.path.join(wt, "src"))
        with open(os.path.join(wt, "src", "a.py"), "w") as f:
            f.write("x = 1\n")
        done = self.pm("commit", "A-1", "-m", "test(A-1): x [red]", cwd=wt)
        self.assertIn("test(A-1): x [red]", done.stdout)

    def test_engineer_cannot_approve_and_lead_cannot_decide(self):
        self.pm("start", "A-1")
        self.assertIn("belongs to", self.pm("approve", "A-1").stdout)
        self.pm("escalate", "A-1", "question")
        self.assertIn("belongs to", self.pm("decide", "A-1", "yes", role="lead").stdout)
        self.assertEqual(self.pm("decide", "A-1", "yes", role="owner").returncode, 0)
        self.assertEqual(self.state("A-1"), "doing")

    def test_dependencies_and_wip_limit_hold(self):
        self.assertIn("cannot start", self.pm("start", "A-2").stdout)

    def test_deep_ticket_needs_tests_approved_first(self):
        self.pm("start", "A-1")
        wt = self.worktree("A-1")
        self.commit_file("src/a.py", "x = 1\n", "test(A-1): x [red]", wt)
        self.pm("submit", "A-1", "--note", "n", cwd=wt)
        self.pm("approve", "A-1", role="lead")
        self.pm("start", "A-2")
        wt = self.worktree("A-2")
        self.commit_file("src/b.py", "y = 1\n", "test(A-2): y [red]", wt)
        self.assertIn("deep ticket", self.pm("submit", "A-2", "--note", "n", cwd=wt).stdout)
        self.pm("red", "A-2", "--note", "fails as expected", cwd=wt)
        self.assertEqual(self.state("A-2"), "red-review")
        self.pm("approve", "A-2", role="lead")
        self.assertEqual(self.state("A-2"), "doing")
        self.assertEqual(self.pm("submit", "A-2", "--note", "n", cwd=wt).returncode, 0)

    def test_repeated_review_rounds_reach_the_owner(self):
        self.pm("start", "A-1")
        wt = self.worktree("A-1")
        self.commit_file("src/a.py", "x = 1\n", "test(A-1): x [red]", wt)
        for _ in range(POLICY["max_review_rounds"]):
            self.pm("submit", "A-1", "--note", "n", cwd=wt)
            self.pm("changes", "A-1", "1. fix", role="lead")
            self.pm("start", "A-1", cwd=wt)
        self.pm("submit", "A-1", "--note", "n", cwd=wt)
        self.pm("changes", "A-1", "1. fix", role="lead")
        self.assertEqual(self.state("A-1"), "owner")


class SubmitChecks(Sandbox):
    def setUp(self):
        super().setUp()
        self.pm("start", "A-1")
        self.wt = self.worktree("A-1")

    def refused(self, *extra):
        done = self.pm("submit", "A-1", "--note", "n", *extra, cwd=self.wt)
        self.assertEqual(done.returncode, 1, done.stdout)
        return done.stdout

    def test_needs_a_red_commit(self):
        self.commit_file("src/a.py", "x = 1\n", "feat(A-1): x", self.wt)
        self.assertIn("[red]", self.refused())

    def test_protected_paths_and_hashing_and_receipts(self):
        self.commit_file("tests/acceptance/x.c", "int x;\n", "test(A-1): x [red]", self.wt)
        self.commit_file("tools/y.py", "import hashlib\n", "feat(A-1): y", self.wt)
        self.commit_file("docs/run-receipt.json", "{}\n", "docs(A-1): z", self.wt)
        out = self.refused()
        self.assertIn("protected path", out)
        self.assertIn("hashing added", out)
        self.assertIn("receipt-style", out)

    def test_overtesting_is_refused_unless_explained(self):
        lines = "".join("assert %d\n" % i for i in range(200))
        self.commit_file("tests/regress/big.py", lines, "test(A-1): many [red]", self.wt)
        self.commit_file("src/a.py", "x = 1\n", "feat(A-1): x", self.wt)
        self.assertIn("test lines", self.refused())
        done = self.pm("submit", "A-1", "--note", "n", "--override", "generated table", cwd=self.wt)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("OVER BUDGET", self.pm("show", "A-1").stdout)

    def test_long_notes_are_refused(self):
        self.commit_file("src/a.py", "x = 1\n", "test(A-1): x [red]", self.wt)
        done = self.pm("submit", "A-1", "--note", "x" * 700, cwd=self.wt)
        self.assertIn("characters", done.stdout)


class RunWrapper(Sandbox):
    def run_tool(self, *args):
        return subprocess.run([sys.executable, os.path.join(self.root, "tools", "run.py")] + list(args),
                              cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_output_is_short_and_failures_show_errors(self):
        script = "print('error: broken'); [print(i) for i in range(5000)]; raise SystemExit(3)"
        done = self.run_tool("--name", "t", "--", sys.executable, "-c", script)
        self.assertEqual(done.returncode, 3)
        self.assertIn("error: broken", done.stdout)
        self.assertLess(len(done.stdout.splitlines()), 30)

    def test_same_content_is_not_rerun(self):
        command = ("--name", "t", "--inputs", "tools", "--", sys.executable, "-c", "print('ran')")
        self.assertIn("PASS", self.run_tool(*command).stdout)
        self.assertIn("CACHED", self.run_tool(*command).stdout)
        self.commit_file("tools/new.py", "x = 1\n", "change", self.root)
        self.assertIn("PASS", self.run_tool(*command).stdout)

    def test_failures_are_not_cached(self):
        command = ("--name", "t", "--inputs", "tools", "--", sys.executable, "-c", "raise SystemExit(1)")
        self.assertIn("FAIL", self.run_tool(*command).stdout)
        self.assertIn("FAIL", self.run_tool(*command).stdout)


class Dispatcher(Sandbox):
    def test_dry_run_names_the_next_session_and_spends_nothing(self):
        done = subprocess.run([sys.executable, os.path.join(self.root, "tools", "dispatch.py"), "--dry-run"],
                              cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertIn("A-1 ready: engineer session", done.stdout)
        self.assertFalse(os.path.isdir(self.worktree("A-1")))

    def test_usage_parsing_handles_both_agents(self):
        import dispatch
        codex = '{"type":"turn.completed","usage":{"input_tokens":10,"cached_input_tokens":4,"output_tokens":2}}'
        claude = '{"usage":{"input_tokens":1,"cache_read_input_tokens":9,"output_tokens":3}}'
        self.assertEqual(dispatch.parse_usage("engineer", codex), {"input_tokens": 10, "output_tokens": 2})
        self.assertEqual(dispatch.parse_usage("lead", claude), {"input_tokens": 10, "output_tokens": 3})


if __name__ == "__main__":
    unittest.main()
