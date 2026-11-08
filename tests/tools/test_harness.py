"""Tests for the board, the hook and the run wrapper. Reviewer-owned, like the harness."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ["PM_NO_NOTIFY"] = "1"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "harness"))
sys.path.insert(0, os.path.join(REPO, "tools"))
import hook_policy  # noqa: E402

POLICY = hook_policy.load_policy()
# The Codex engineer path, still selectable per ticket (backend field) or by policy.
CODEX = dict(POLICY, engineer_backend="codex")


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
                            ignore=shutil.ignore_patterns("__pycache__", "check", "check.py"))
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

    def test_status_page_follows_every_ticket_change_without_anyone_asking(self):
        page = os.path.join(self.root, "STATUS.md")
        done = self.pm("start", "A-1")
        self.assertIn("PM update: A-1 is in progress", done.stdout)
        wt = self.worktree("A-1")
        with open(page, encoding="utf8") as f:
            self.assertIn("| A-1 | Demo | In progress |", f.read())
        self.commit_file("src/a.py", "x = 1\n", "test(A-1): x [red]", wt)
        self.pm("submit", "A-1", "--note", "first version works", cwd=wt)
        with open(page, encoding="utf8") as f:
            text = f.read()
        self.assertIn("Next: the tech lead, on A-1", text)
        self.assertIn("first version works", text)
        self.pm("escalate", "A-1", "which option?", role="lead")
        with open(page, encoding="utf8") as f:
            self.assertIn("Waiting for you:** A-1", f.read())
        status = subprocess.run(["git", "status", "--short"], cwd=self.root, stdout=subprocess.PIPE,
                                universal_newlines=True).stdout
        self.assertEqual(status, "", "the page is committed with the ticket")

    def test_broken_status_page_does_not_stop_the_work(self):
        os.makedirs(os.path.join(self.root, "STATUS.md"))
        done = self.pm("start", "A-1")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("Status page not updated", done.stdout)
        self.assertEqual(self.state("A-1"), "doing")

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
        refusal = self.refused()
        self.assertIn("test lines", refusal)
        # Engineers asked instead of overriding because the refusal never named the flag.
        self.assertIn("--override", refusal)
        done = self.pm("submit", "A-1", "--note", "n", "--override", "generated table", cwd=self.wt)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("OVER BUDGET", self.pm("show", "A-1").stdout)

    def test_ticket_can_declare_the_test_files_its_acceptance_needs(self):
        for i in range(6):
            self.commit_file("tests/isa/f%d.s" % i, "nop\n", "test(A-1): f%d [red]" % i, self.wt)
        self.assertIn("6 new test files", self.refused())
        path = os.path.join(self.root, "work", "tickets", "A-1.md")
        with open(path, encoding="utf8") as f:
            text = f.read()
        with open(path, "w", encoding="utf8", newline="\n") as f:
            f.write(text.replace("depth: standard", "depth: standard\nnew_test_files: 6"))
        self.git("commit", "-qam", "declare")
        done = self.pm("submit", "A-1", "--note", "n", cwd=self.wt)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertNotIn("OVER BUDGET", self.pm("show", "A-1").stdout)

    def test_long_notes_are_refused(self):
        self.commit_file("src/a.py", "x = 1\n", "test(A-1): x [red]", self.wt)
        done = self.pm("submit", "A-1", "--note", "x" * 700, cwd=self.wt)
        self.assertIn("characters", done.stdout)


class MachineCheck(Sandbox):
    def submitted_with_check(self, code):
        self.pm("start", "A-1")
        self.wt = self.worktree("A-1")
        self.commit_file("tools/check", "raise SystemExit(%d)\n" % code, "test(A-1): x [red]", self.wt)
        self.assertEqual(self.pm("submit", "A-1", "--note", "n", cwd=self.wt).returncode, 0)

    def test_failing_check_stops_the_merge(self):
        self.submitted_with_check(1)
        done = self.pm("approve", "A-1", "--note", "looks fine", role="lead")
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("tools/check t0 failed", done.stdout)
        self.assertEqual(self.state("A-1"), "review")
        self.assertTrue(os.path.isdir(self.wt))

    def test_passing_check_merges_and_says_so(self):
        self.submitted_with_check(0)
        self.assertEqual(self.pm("approve", "A-1", "--note", "works", role="lead").returncode, 0)
        self.assertEqual(self.state("A-1"), "done")
        self.assertIn("Machine check: tools/check t0 passed", self.pm("show", "A-1").stdout)

    def card_change_blocks_merge(self, path):
        self.pm("start", "A-1")
        self.wt = self.worktree("A-1")
        self.commit_file("tools/check", "raise SystemExit(0)\n", "test(A-1): T0 [red]", self.wt)
        self.commit_file("tests/tools/test_card_approval.py",
                         "import sys, unittest\n"
                         "class CardCheck(unittest.TestCase):\n"
                         "    def test_gate(self):\n"
                         "        self.assertEqual(sys.platform, 'cygwin')\n"
                         "        self.fail('card approval gate ran under Cygwin')\n",
                         "test(A-1): card approval gate [red]", self.wt)
        with open(os.path.join(self.wt, path), encoding="utf8") as f:
            original = f.read()
        self.commit_file(path, original + "\n", "fix(A-1): card change", self.wt)
        submitted = self.pm("submit", "A-1", "--note", "n", cwd=self.wt)
        self.assertEqual(submitted.returncode, 0, submitted.stdout)
        done = self.pm("approve", "A-1", role="lead")
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("card approval gate ran under Cygwin", done.stdout)
        self.assertEqual(self.state("A-1"), "review")
        self.assertTrue(os.path.isdir(self.wt))

    def test_card_runner_change_requires_cygwin_card_tests(self):
        self.card_change_blocks_merge("tools/card_run")

    def test_card_shell_change_requires_cygwin_card_tests(self):
        self.card_change_blocks_merge("tools/card_run_remote.sh")

    def test_card_helper_change_requires_cygwin_card_tests(self):
        self.card_change_blocks_merge("tools/claude-pin.c")


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
        claude = '{"usage":{"input_tokens":1,"cache_read_input_tokens":9,"cache_creation_input_tokens":5,"output_tokens":3}}'
        self.assertEqual(dispatch.parse_usage("engineer", codex), {"input_tokens": 10, "output_tokens": 2})
        self.assertEqual(dispatch.parse_usage("lead", claude), {"input_tokens": 15, "output_tokens": 3})

    def test_engineer_can_write_logs_and_shared_builds_outside_its_worktree(self):
        import dispatch
        import pm
        import storage
        ticket = mock.Mock(fields={"depth": "standard"})
        board = mock.Mock(root=self.root, policy=CODEX, budget=lambda _t: POLICY["budgets"]["standard"])
        self.assertTrue(pm)
        command = dispatch.engineer_command(board, ticket, self.worktree("A-1"))
        setting = [arg for arg in command if arg.startswith("sandbox_workspace_write.writable_roots=")]
        self.assertEqual(len(setting), 1)
        roots = json.loads(setting[0].split("=", 1)[1])
        self.assertEqual(roots, [storage.state_dir(self.root), storage.shared_area(self.root)])

    def test_engineer_can_append_to_the_card_ledger_named_in_the_local_card_config(self):
        import dispatch
        import storage
        ledger_dir = os.path.join(self.root, "outside", "card-coordination")
        os.makedirs(os.path.join(self.root, "config"), exist_ok=True)
        with open(os.path.join(self.root, "config", "card.local.json"), "w", encoding="utf8") as f:
            json.dump({"host": "h", "ledger": os.path.join(ledger_dir, "jobs.jsonl")}, f)
        ticket = mock.Mock(fields={"depth": "standard"})
        board = mock.Mock(root=self.root, policy=CODEX, budget=lambda _t: POLICY["budgets"]["standard"])
        command = dispatch.engineer_command(board, ticket, self.worktree("A-1"))
        setting = [arg for arg in command if arg.startswith("sandbox_workspace_write.writable_roots=")]
        roots = json.loads(setting[0].split("=", 1)[1])
        self.assertEqual(roots, [storage.state_dir(self.root), storage.shared_area(self.root), ledger_dir])

    def test_policy_can_set_engineer_effort_and_service_tier(self):
        import dispatch
        ticket = mock.Mock(fields={"depth": "light"})
        policy = dict(CODEX, engineer_effort="high", engineer_service_tier="priority")
        board = mock.Mock(root=self.root, policy=policy, budget=lambda _t: POLICY["budgets"]["light"])
        command = dispatch.engineer_command(board, ticket, self.worktree("A-1"))
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn('service_tier="priority"', command)
        unset = {k: v for k, v in policy.items() if k not in ("engineer_effort", "engineer_service_tier")}
        board.policy = unset
        command = dispatch.engineer_command(board, ticket, self.worktree("A-1"))
        self.assertIn('model_reasoning_effort="low"', command)
        self.assertFalse([arg for arg in command if arg.startswith("service_tier=")])

    def test_engineer_model_comes_from_ticket_then_depth_then_policy(self):
        import dispatch
        budgets = {depth: {k: v for k, v in b.items() if k != "model"} for depth, b in POLICY["budgets"].items()}
        budgets["deep"]["model"] = "deep-model"
        policy = dict(CODEX, engineer_model="default-model", budgets=budgets)
        board = mock.Mock(root=self.root, policy=policy, budget=lambda t: budgets[t.fields["depth"]])
        for fields, model in (({"depth": "deep"}, "deep-model"), ({"depth": "light"}, "default-model"),
                              ({"depth": "deep", "model": "ticket-model"}, "ticket-model")):
            command = dispatch.engineer_command(board, mock.Mock(fields=fields), self.worktree("A-1"))
            self.assertEqual(command[command.index("-m") + 1], model)

    def test_ticket_backend_overrides_the_policy_backend(self):
        import dispatch
        policy = dict(POLICY, engineer_backend="claude")
        board = mock.Mock(root=self.root, policy=policy, budget=lambda _t: POLICY["budgets"]["deep"])
        claude = dispatch.engineer_command(board, mock.Mock(id="A-1", fields={"depth": "deep"}), self.worktree("A-1"))
        self.assertIn("--model", claude)
        codex = dispatch.engineer_command(board, mock.Mock(id="A-1", fields={"depth": "deep", "backend": "codex",
                                                                             "model": "gpt-6.1-sol"}), self.worktree("A-1"))
        self.assertEqual(codex[1], "exec")
        self.assertEqual(codex[codex.index("-m") + 1], "gpt-6.1-sol")

    def test_engineer_git_trusts_the_shared_gcc_checkout(self):
        # The sandbox user does not own the shared checkout, so git refuses it as dubious.
        # Codex drops variables containing KEY, so GIT_CONFIG_KEY_0 cannot carry the setting.
        import dispatch
        import storage
        ticket = mock.Mock(id="A-1", fields={})
        board = mock.Mock(root=self.root, policy=POLICY)
        gcc = os.path.join(storage.shared_area(self.root), "gcc").replace("\\", "/")
        env = dispatch.session_env(board, ticket, "engineer")
        cygwin = "/cygdrive/%s%s" % (gcc[0].lower(), gcc[2:])
        self.assertEqual(env.get("GIT_CONFIG_PARAMETERS"),
                         "'safe.directory'='%s' 'safe.directory'='%s'" % (gcc, cygwin))
        self.assertFalse([k for k in env if k.startswith("GIT_CONFIG_KEY")])
        self.assertNotIn("GIT_CONFIG_PARAMETERS", dispatch.session_env(board, ticket, "lead"))

    def test_ticket_can_raise_its_session_limit(self):
        import dispatch
        import pm
        os.makedirs(os.path.join(self.root, ".work", "_state"))
        with open(os.path.join(self.root, ".work", "_state", "ledger.jsonl"), "w", encoding="utf8") as f:
            f.write((json.dumps({"ticket": "A-1", "role": "engineer"}) + "\n") * 3)
        path = os.path.join(self.root, "work", "tickets", "A-1.md")
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        board = pm.Board()
        self.assertIn("3 engineer sessions", dispatch.over_budget(board, board.load("A-1")))
        with open(path, encoding="utf8") as f:
            text = f.read()
        with open(path, "w", encoding="utf8", newline="\n") as f:
            f.write(text.replace("depth: standard", "depth: standard\nsessions: 4"))
        self.assertIsNone(dispatch.over_budget(board, board.load("A-1")))

    def test_the_lead_can_raise_a_ticket_token_budget(self):
        import dispatch
        import pm
        os.makedirs(os.path.join(self.root, ".work", "_state"))
        with open(os.path.join(self.root, ".work", "_state", "ledger.jsonl"), "w", encoding="utf8") as f:
            f.write(json.dumps({"ticket": "A-1", "role": "engineer", "input_tokens": 7000000}) + "\n")
        path = os.path.join(self.root, "work", "tickets", "A-1.md")
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        board = pm.Board()
        self.assertIn("7000000 input tokens", dispatch.over_budget(board, board.load("A-1")))
        with open(path, encoding="utf8") as f:
            text = f.read()
        with open(path, "w", encoding="utf8", newline="\n") as f:
            f.write(text.replace("depth: standard", "depth: standard\ninput_tokens: 12000000"))
        self.assertIsNone(dispatch.over_budget(board, board.load("A-1")))

    def test_status_page_shows_a_session_as_soon_as_it_is_recorded(self):
        import dispatch
        import pm
        self.pm("start", "A-1")
        os.environ["PM_ROLE"] = "engineer"
        self.addCleanup(os.environ.pop, "PM_ROLE", None)
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        board = pm.Board()
        with open(os.path.join(board.state_dir(), "ledger.jsonl"), "w", encoding="utf8") as f:
            f.write(json.dumps({"ticket": "A-1", "role": "engineer", "input_tokens": 2500000}) + "\n")
        dispatch.refresh_status(board)
        with open(os.path.join(self.root, "STATUS.md"), encoding="utf8") as f:
            self.assertIn("engineer: 1 sessions, 2.5M", f.read())
        left = subprocess.run(["git", "status", "--short"], cwd=self.root, stdout=subprocess.PIPE,
                              universal_newlines=True).stdout
        self.assertEqual(left, "", "the page is committed")


class Lanes(Sandbox):
    """GCC tickets share one checkout and build; everything else may run beside them (owner, 2026-11-03)."""

    def raw_ticket(self, ident, extra, state="ready", deps=""):
        text = TICKET.format(id=ident, depth="standard", deps=deps).replace("state: ready", "state: " + state)
        with open(os.path.join(self.root, "work", "tickets", ident + ".md"), "w", newline="\n") as f:
            f.write(text.replace("---\n## Outcome", extra + "---\n## Outcome"))

    def board(self):
        import pm
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        return pm, pm.Board()

    def test_a_tools_ticket_starts_while_a_gcc_ticket_is_in_progress(self):
        for ident in ("A-1", "A-2"):
            os.remove(os.path.join(self.root, "work", "tickets", ident + ".md"))
        self.raw_ticket("G-1", "gcc: yes\n", state="doing")
        self.raw_ticket("T-1", "")
        pm, board = self.board()
        self.assertEqual([(r, t.id) for r, t in [pm.next_action(board, "gcc")]], [("engineer", "G-1")])
        self.assertEqual([(r, t.id) for r, t in [pm.next_action(board, "tools")]], [("engineer", "T-1")])
        # Without a lane the board behaves as before: one ticket in progress at a time.
        self.assertEqual(pm.next_action(board)[1].id, "G-1")

    def test_a_lane_field_puts_a_ticket_that_uses_the_gcc_build_in_the_gcc_lane(self):
        for ident in ("A-1", "A-2"):
            os.remove(os.path.join(self.root, "work", "tickets", ident + ".md"))
        self.raw_ticket("G-1", "gcc: yes\n", state="doing")
        self.raw_ticket("U-1", "lane: gcc\n")
        pm, board = self.board()
        self.assertEqual(pm.lane_of(board.load("U-1")), "gcc")
        self.assertIsNone(pm.next_action(board, "tools"))
        self.assertEqual(pm.next_action(board, "gcc")[1].id, "G-1")

    def test_pm_start_counts_work_in_progress_per_lane(self):
        for ident in ("A-1", "A-2"):
            os.remove(os.path.join(self.root, "work", "tickets", ident + ".md"))
        self.raw_ticket("G-1", "gcc: yes\n", state="doing")
        self.raw_ticket("T-1", "")
        self.git("add", "-A")
        self.git("commit", "-qm", "lanes")
        done = self.pm("start", "T-1")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.state("T-1"), "doing")

    def test_board_changes_wait_for_the_board_lock_held_by_another_process(self):
        pm, board = self.board()
        env = dict(os.environ, PM_ROLE="engineer", PM_LOCK_WAIT="1")
        command = [sys.executable, os.path.join(self.root, "tools", "pm.py"), "start", "A-1"]
        with pm.board_lock(self.root):
            with pm.board_lock(self.root):  # re-entrant inside one process
                pass
            busy = subprocess.run(command, cwd=self.root, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, universal_newlines=True)
            self.assertNotEqual(busy.returncode, 0)
            self.assertIn("board is busy", busy.stdout)
            self.assertEqual(self.state("A-1"), "ready")
        done = subprocess.run(command, cwd=self.root, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.state("A-1"), "doing")

    def test_a_lane_dispatcher_stops_only_for_owner_tickets_in_its_own_lane(self):
        for ident in ("A-1", "A-2"):
            os.remove(os.path.join(self.root, "work", "tickets", ident + ".md"))
        self.raw_ticket("G-1", "gcc: yes\n", state="owner")
        self.raw_ticket("T-1", "")
        self.git("add", "-A")
        self.git("commit", "-qm", "lanes")
        env = dict(os.environ, PM_ROLE="engineer")
        run = lambda lane: subprocess.run(
            [sys.executable, os.path.join(self.root, "tools", "dispatch.py"), "--dry-run", "--max-sessions", "1",
             "--lane", lane], cwd=self.root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True)
        self.assertIn("T-1 ready: engineer session", run("tools").stdout)
        self.assertNotIn("session", run("gcc").stdout.split("\n")[0])


class HandStartedUsage(unittest.TestCase):
    def setUp(self):
        import status
        self.status = status
        self.top = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.top, ignore_errors=True)
        self.root = os.path.join(self.top, "my_proj")
        patch = mock.patch.dict(os.environ, CODEX_HOME=os.path.join(self.top, "codex"),
                                CLAUDE_CONFIG_DIR=os.path.join(self.top, "claude"))
        patch.start()
        self.addCleanup(patch.stop)

    def write(self, parts, lines):
        path = os.path.join(self.top, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf8") as f:
            f.write("".join(json.dumps(line) + "\n" for line in lines))

    def rollout(self, name, cwd, *totals):
        counts = [{"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": n}}}}
                  for n in totals]
        self.write(("codex", "sessions", "2026", name), [{"type": "session_meta", "payload": {"cwd": cwd}}] + counts)

    def test_gpt_sessions_in_this_project_count_their_last_total(self):
        self.rollout("rollout-a.jsonl", self.root, 10, 40)
        self.rollout("rollout-b.jsonl", os.path.join(self.root, ".work", "A-1"), 5)
        self.rollout("rollout-c.jsonl", self.root + "_other", 999)
        self.assertEqual(self.status.hand_usage(self.root), {"GPT": (2, 45)})

    def test_claude_calls_count_once_each_across_content_blocks(self):
        usage = {"input_tokens": 1, "cache_read_input_tokens": 2, "cache_creation_input_tokens": 3}
        call = {"type": "assistant", "message": {"id": "m1", "usage": usage}}
        folder = re.sub(r"[^A-Za-z0-9]", "-", os.path.normpath(self.root))
        self.write(("claude", "projects", folder, "s.jsonl"), [call, call, {"type": "user", "message": {"content": "usage"}}])
        self.assertEqual(self.status.hand_usage(self.root), {"Claude": (1, 6)})


if __name__ == "__main__":
    unittest.main()
