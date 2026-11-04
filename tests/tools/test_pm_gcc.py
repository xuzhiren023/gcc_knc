"""GCC ticket acceptance, using two disposable repositories."""
import json
import os
import subprocess
from unittest import mock

from test_harness import Sandbox
import dispatch


class GccTickets(Sandbox):
    def setUp(self):
        super().setUp()
        path = os.path.join(self.root, "work", "tickets", "A-1.md")
        with open(path) as f:
            text = f.read()
        with open(path, "w", newline="\n") as f:
            f.write(text.replace("type: code", "type: code\ngcc: yes"))
        self.git("commit", "-qam", "opt in")
        self.gcc = os.path.join(self.root, ".work", "_shared", "gcc")
        os.makedirs(self.gcc)
        self.git("init", "-q", "-b", "knc", cwd=self.gcc)
        for key, value in (("user.email", "t@example.invalid"), ("user.name", "t"),
                           ("core.autocrlf", "false"), ("core.fileMode", "false")):
            self.git("config", key, value, cwd=self.gcc)
        self.commit_file("gcc/imci.md", "base\n", "base", self.gcc)
        self.branch = "s0/A-1"
        self.wt = self.worktree("A-1")

    def output(self, *args, cwd=None):
        return subprocess.check_output(("git",) + args, cwd=cwd or self.gcc, text=True).strip()

    def start(self):
        done = self.pm("start", "A-1")
        self.assertEqual(done.returncode, 0, done.stdout)

    def submit(self):
        done = self.pm("submit", "A-1", "--note", "T0", cwd=self.wt)
        self.assertEqual(done.returncode, 0, done.stdout)

    def changes(self, check=0):
        self.start()
        self.commit_file("tools/check", "raise SystemExit(%d)\n" % check,
                         "test(A-1): check [red]", self.wt)
        self.commit_file("gcc/imci.md", "ticket\n", "feat(A-1): GCC", self.gcc)

    def test_start_creates_from_knc_and_reuses_branch(self):
        base = self.output("rev-parse", "knc")
        self.start()
        self.assertEqual(self.output("branch", "--show-current"), self.branch)
        self.assertEqual(self.output("rev-parse", "HEAD"), base)
        self.commit_file("gcc/imci.md", "ticket\n", "test(A-1): GCC [red]", self.gcc)
        head = self.output("rev-parse", "HEAD")
        self.git("checkout", "-q", "knc", cwd=self.gcc)
        self.start()
        self.assertEqual(self.output("rev-parse", "HEAD"), head)

    def test_commit_gcc_leaves_worktree_untouched(self):
        self.start()
        host_head = self.output("rev-parse", "HEAD", cwd=self.wt)
        with open(os.path.join(self.wt, "host-dirty"), "w") as f:
            f.write("keep uncommitted\n")
        with open(os.path.join(self.gcc, "gcc", "imci.md"), "w") as f:
            f.write("ticket\n")
        done = self.pm("commit", "A-1", "--gcc", "-m", "feat(A-1): GCC", cwd=self.wt)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.output("log", "-1", "--format=%s"), "feat(A-1): GCC")
        self.assertEqual(self.output("status", "--porcelain"), "")
        self.assertEqual(self.output("rev-parse", "HEAD", cwd=self.wt), host_head)
        self.assertEqual(self.output("status", "--porcelain", cwd=self.wt), "?? host-dirty")

    def test_start_refuses_dirty_checkout_and_other_ticket(self):
        with open(os.path.join(self.gcc, "untracked"), "w") as f:
            f.write("dirty")
        done = self.pm("start", "A-1")
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertFalse(os.path.isdir(self.wt))
        os.remove(os.path.join(self.gcc, "untracked"))
        self.git("checkout", "-qb", "s0/A-2", cwd=self.gcc)
        done = self.pm("start", "A-1")
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.output("branch", "--show-current"), "s0/A-2")

    def test_start_keeps_uncommitted_work_on_its_own_branch(self):
        # A session can end with reviewed GCC edits not yet committed; the next one resumes them.
        self.start()
        with open(os.path.join(self.gcc, "gcc", "imci.md"), "w") as f:
            f.write("unfinished\n")
        self.start()
        self.assertEqual(self.output("branch", "--show-current"), self.branch)
        self.assertEqual(self.output("status", "--porcelain"), "M gcc/imci.md")

    def test_dispatcher_stops_cleanly_when_start_is_refused(self):
        ticket = mock.Mock(id="A-1", state="doing", fields={})
        refused = dispatch.pm.Refused("uncommitted changes in the GCC checkout")
        with mock.patch.dict(os.environ), mock.patch.object(dispatch, "over_budget", return_value=None), \
                mock.patch.object(dispatch.pm, "cmd_start", side_effect=refused):
            self.assertFalse(dispatch.run_session(mock.Mock(), ticket, "engineer", False))

    def test_submit_refuses_dirty_gcc(self):
        self.changes()
        with open(os.path.join(self.gcc, "untracked"), "w") as f:
            f.write("dirty")
        done = self.pm("submit", "A-1", "--note", "T0", cwd=self.wt)
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn("GCC", done.stdout)
        self.assertEqual(self.state("A-1"), "doing")

    def test_gcc_only_red_commit_is_visible_and_head_is_recorded(self):
        self.start()
        self.commit_file("gcc/imci.md", "ticket\n", "test(A-1): GCC [red]", self.gcc)
        self.submit()
        self.assertIn("gcc_head: " + self.output("rev-parse", "HEAD"), self.pm("show", "A-1").stdout)

    def test_submit_combines_changed_line_budgets(self):
        path = os.path.join(self.root, "harness", "policy.json")
        with open(path) as f:
            policy = json.load(f)
        policy["budgets"]["standard"]["changed_lines"] = 3
        with open(path, "w") as f:
            json.dump(policy, f)
        self.git("commit", "-qam", "small budget")
        self.changes()  # One host line and three GCC lines (two added, one removed).
        self.commit_file("gcc/imci.md", "ticket\nextra\n", "feat(A-1): extra", self.gcc)
        done = self.pm("submit", "A-1", "--note", "T0", cwd=self.wt)
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn("4 changed lines", done.stdout)

    def test_approve_merges_both_with_no_ff_after_machine_check(self):
        self.changes()
        self.submit()
        head = self.output("rev-parse", "HEAD")
        done = self.pm("approve", "A-1", role="lead")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.output("branch", "--show-current"), "knc")
        self.assertEqual(self.output("rev-parse", "knc^2"), head)
        self.assertEqual(self.state("A-1"), "done")
        self.assertTrue(os.path.exists(os.path.join(self.root, "tools", "check")))

    def test_approve_does_not_rewrite_files_when_knc_is_an_ancestor(self):
        self.changes()
        self.submit()
        target = os.path.join(self.gcc, "gcc", "imci.md")
        os.utime(target, (1000000000, 1000000000))
        tree = self.output("rev-parse", self.branch + "^{tree}")
        done = self.pm("approve", "A-1", role="lead")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(os.stat(target).st_mtime, 1000000000)
        self.assertEqual(self.output("branch", "--show-current"), "knc")
        self.assertEqual(self.output("rev-parse", "knc^{tree}"), tree)
        self.assertEqual(self.output("rev-parse", "knc^2"), self.output("rev-parse", self.branch))
        self.assertEqual(len(self.output("rev-list", "--parents", "-n1", "knc").split()), 3)

    def test_approve_still_merges_when_knc_is_not_an_ancestor(self):
        self.changes()
        self.submit()
        self.git("checkout", "-q", "knc", cwd=self.gcc)
        self.commit_file("gcc/other.md", "other
", "integration", self.gcc)
        self.git("checkout", "-q", self.branch, cwd=self.gcc)
        other = self.output("rev-parse", "knc")
        done = self.pm("approve", "A-1", role="lead")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.output("rev-parse", "knc^1"), other)
        self.assertEqual(self.output("rev-parse", "knc^2"), self.output("rev-parse", self.branch))
        self.assertEqual(self.output("show", "knc:gcc/other.md"), "other")
        self.assertEqual(self.output("show", "knc:gcc/imci.md"), "ticket")

    def test_approve_refuses_moved_gcc_branch(self):
        self.changes()
        self.submit()
        base = self.output("rev-parse", "knc")
        self.commit_file("gcc/imci.md", "moved\n", "feat(A-1): moved", self.gcc)
        done = self.pm("approve", "A-1", role="lead")
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn("since submit", done.stdout)
        self.assertEqual(self.output("rev-parse", "knc"), base)
        self.assertEqual(self.state("A-1"), "review")

    def test_machine_failure_does_not_merge_either_repository(self):
        self.changes(check=1)
        self.submit()
        main = self.output("rev-parse", "main", cwd=self.root)
        knc = self.output("rev-parse", "knc")
        done = self.pm("approve", "A-1", role="lead")
        self.assertIn("tools/check t0 failed", done.stdout)
        self.assertEqual(self.output("rev-parse", "main", cwd=self.root), main)
        self.assertEqual(self.output("rev-parse", "knc"), knc)

    def test_either_merge_conflict_restores_both_repositories(self):
        self.changes()
        self.submit()
        # GCC conflict first, then a host conflict after the GCC merge can succeed.
        for target in ("gcc", "host"):
            with self.subTest(target=target):
                cwd = self.gcc if target == "gcc" else self.root
                if target == "gcc":
                    self.git("checkout", "-q", "knc", cwd=cwd)
                    self.commit_file("gcc/imci.md", "conflict\n", "integration", cwd)
                    self.git("checkout", "-q", self.branch, cwd=cwd)
                else:
                    self.git("branch", "-f", "knc", self.output("rev-parse", self.branch + "^"), cwd=self.gcc)
                    self.commit_file("tools/check", "conflict\n", "integration", cwd)
                main = self.output("rev-parse", "main", cwd=self.root)
                knc = self.output("rev-parse", "knc")
                done = self.pm("approve", "A-1", role="lead")
                self.assertNotEqual(done.returncode, 0, done.stdout)
                self.assertEqual(self.output("rev-parse", "main", cwd=self.root), main)
                self.assertEqual(self.output("rev-parse", "knc"), knc)
                for repo in (self.root, self.gcc):
                    self.assertEqual(self.output("status", "--porcelain", cwd=repo), "")
                self.assertEqual(self.output("branch", "--show-current"), self.branch)
                self.assertEqual(self.state("A-1"), "review")

    def test_review_prompt_and_read_only_tools_include_gcc(self):
        board = dispatch.pm.Board.__new__(dispatch.pm.Board)
        board.policy = {"budgets": {"standard": {"effort": "high"}}}
        ticket = dispatch.pm.Ticket(board, "A-1", {"state": "review", "branch": self.branch}, "")
        command = dispatch.lead_command(board, ticket)
        self.assertIn("git -C .work/_shared/gcc diff knc..." + self.branch, command[2])
        self.assertIn("git -C .work/_shared/gcc log", command[2])
        allowed = command[command.index("--allowedTools") + 1]
        for verb in ("log", "diff", "show"):
            self.assertIn("Bash(git -C .work/_shared/gcc " + verb + "*)", allowed)

    def test_review_prompt_says_the_review_cannot_edit_or_run_checks(self):
        # Reviews three times promised a file edit or a check run that their tools cannot do.
        board = dispatch.pm.Board.__new__(dispatch.pm.Board)
        board.policy = {"budgets": {"standard": {"effort": "high"}}}
        ticket = dispatch.pm.Ticket(board, "A-1", {"state": "blocked", "branch": self.branch}, "")
        prompt = dispatch.lead_command(board, ticket)[2]
        self.assertIn("cannot edit files or run tools/check", prompt)
        self.assertIn("--override", prompt)
        self.assertIn("escalate", prompt)
