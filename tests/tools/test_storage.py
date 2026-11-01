"""Tests for the disk limits. Reviewer-owned, like the harness."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_harness import POLICY, Sandbox, deny, hook_policy  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import storage  # noqa: E402


class Measuring(unittest.TestCase):
    def test_hard_links_count_once_and_old_logs_go_first(self):
        with tempfile.TemporaryDirectory() as top:
            first = os.path.join(top, "a.bin")
            with open(first, "wb") as f:
                f.write(b"x" * (2 * storage.MIB))
            os.link(first, os.path.join(top, "b.bin"))
            self.assertEqual(storage.tree_size(top), 2 * storage.MIB)

            logs = os.path.join(top, "state", "logs")
            os.makedirs(logs)
            for age, name in enumerate(("new", "old")):
                path = os.path.join(logs, name)
                with open(path, "wb") as f:
                    f.write(b"x" * storage.MIB)
                os.utime(path, (1000 - age * 500, 1000 - age * 500))
            self.assertEqual(storage.prune_logs(os.path.join(top, "state"), 1), storage.MIB)
            self.assertEqual(os.listdir(logs), ["new"])


class Hook(unittest.TestCase):
    def test_tree_copies_and_downloads_need_the_ticket_to_allow_them(self):
        for command in ("cp -r build build2", "Copy-Item src dst -Recurse", "robocopy a b /E", "git clone x",
                        "tar xf a.tar", "curl -O https://x/y", "git worktree add ../x",
                        "python -c 'import shutil; shutil.copytree(1,2)'"):
            self.assertIn("space", deny(command) or "", command)
            self.assertIsNone(deny(command, {"PM_ALLOW_BULK": "yes"}), command)

    def test_over_the_limit_only_finishing_and_deleting_work(self):
        counts = {"over_limit": "Over."}
        for command in ("gcc a.c", "python x.py"):
            self.assertEqual(hook_policy.check_storage(command, counts, POLICY, {}, lambda: None), "Over.")
        for command in ("git commit -m x", "python tools/pm.py ask X y", "rm -rf out", "Remove-Item out -Recurse"):
            self.assertIsNone(hook_policy.check_storage(command, counts, POLICY, {}, lambda: None), command)

    def test_disk_is_measured_only_every_so_often(self):
        calls = []
        measure = lambda: calls.append(1) or "Over."  # noqa: E731
        every = POLICY["storage"]["hook_check_every_calls"]
        counts = {"tool_calls": every - 1}
        self.assertIsNone(hook_policy.check_storage("ls", counts, POLICY, {}, measure))
        self.assertEqual(calls, [])
        counts["tool_calls"] = every
        self.assertEqual(hook_policy.check_storage("ls", counts, POLICY, {}, measure), "Over.")
        self.assertEqual(calls, [1])


class Limits(Sandbox):
    def set_limits(self, **limits):
        path = os.path.join(self.root, "harness", "policy.json")
        with open(path, encoding="utf8") as f:
            policy = json.load(f)
        policy["storage"].update(limits)
        with open(path, "w", encoding="utf8") as f:
            json.dump(policy, f)

    def dispatch_dry(self):
        return subprocess.run([sys.executable, os.path.join(self.root, "tools", "dispatch.py"), "--dry-run"],
                              cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True).stdout

    def test_no_session_starts_over_the_limit_or_on_a_full_drive(self):
        self.assertIn("A-1 ready: engineer session", self.dispatch_dry())
        self.set_limits(project_hard_gib=0)
        out = self.dispatch_dry()
        self.assertIn("No session started", out)
        self.assertNotIn("engineer session", out)
        self.set_limits(project_hard_gib=100, min_drive_free_gib=10 ** 9)
        self.assertIn("No session started", self.dispatch_dry())

    def test_submit_refuses_large_files_and_oversized_worktrees(self):
        self.pm("start", "A-1")
        wt = self.worktree("A-1")
        self.commit_file("tests/regress/t.py", "assert 0\n", "test(A-1): x [red]", wt)
        with open(os.path.join(wt, "big.bin"), "wb") as f:
            f.write(b"x" * (2 * storage.MIB))
        self.git("add", "-A", cwd=wt)
        self.git("commit", "-qm", "feat(A-1): big", cwd=wt)
        out = self.pm("submit", "A-1", "--note", "n", cwd=wt).stdout
        self.assertIn("big.bin", out)
        self.assertIn("MiB", out)

        path = os.path.join(self.root, "harness", "policy.json")
        with open(path, encoding="utf8") as f:
            policy = json.load(f)
        policy["budgets"]["standard"]["disk_gib"] = 0
        with open(path, "w", encoding="utf8") as f:
            json.dump(policy, f)
        self.assertIn("worktree uses", self.pm("submit", "A-1", "--note", "n", cwd=wt).stdout)

    def test_hand_started_session_gets_the_active_tickets_limits(self):
        """No PM_ variables, as in a Codex session started by hand."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("PM_")}
        event = json.dumps({"session_id": "unit-hand", "tool_name": "Bash", "cwd": self.root,
                            "tool_input": {"command": "git clone x"}})
        hook = os.path.join(self.root, "harness", "hook_policy.py")

        def clone_decision():
            done = subprocess.run([sys.executable, hook], input=event, cwd=self.root, env=env,
                                  stdout=subprocess.PIPE, universal_newlines=True)
            return "deny" in done.stdout

        self.assertTrue(clone_decision())
        path = os.path.join(self.root, "work", "tickets", "A-1.md")
        with open(path, encoding="utf8") as f:
            text = f.read()
        with open(path, "w", encoding="utf8", newline="\n") as f:
            f.write(text.replace("state: ready", "state: doing\nallow_bulk: yes"))
        self.assertFalse(clone_decision())

    def test_run_wrapper_refuses_on_a_full_drive_and_trims_logs(self):
        self.set_limits(min_drive_free_gib=10 ** 9)
        done = subprocess.run([sys.executable, os.path.join(self.root, "tools", "run.py"), "--name", "t", "--",
                               sys.executable, "-c", "print(1)"], cwd=self.root, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(done.returncode, 3)
        self.assertIn("free", done.stdout)


if __name__ == "__main__":
    unittest.main()
