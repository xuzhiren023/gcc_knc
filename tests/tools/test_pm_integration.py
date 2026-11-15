"""Submission and approval with integration branches that advanced independently."""
import os
import subprocess

from test_harness import Sandbox


class Integration(Sandbox):
    def output(self, *args, cwd=None):
        return subprocess.check_output(("git",) + args, cwd=cwd or self.root, text=True).strip()

    def start(self, gcc=False):
        self.gcc = None
        if gcc:
            path = os.path.join(self.root, "work", "tickets", "A-1.md")
            with open(path) as f:
                text = f.read()
            with open(path, "w") as f:
                f.write(text.replace("type: code", "type: code\ngcc: yes"))
            self.git("commit", "-qam", "GCC ticket")
            self.gcc = os.path.join(self.root, ".work", "_shared", "gcc")
            os.makedirs(self.gcc)
            self.git("init", "-q", "-b", "knc", cwd=self.gcc)
            self.git("config", "user.email", "t@example.invalid", cwd=self.gcc)
            self.git("config", "user.name", "t", cwd=self.gcc)
            self.commit_file("gcc/a", "base\n", "base", self.gcc)
        done = self.pm("start", "A-1")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.wt = self.worktree("A-1")
        self.commit_file("src/a", "ticket\n", "test(A-1): change [red]", self.wt)
        if gcc:
            self.commit_file("gcc/a", "ticket\n", "feat(A-1): change", self.gcc)

    def submit(self):
        done = self.pm("submit", "A-1", "--note", "host tests", cwd=self.wt)
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_status_only_behind_submits(self):
        self.start()
        for path in ("work/note", "STATUS.md", "CURRENT_STATE.md"):
            self.commit_file(path, "status\n", "status", self.root)
        self.submit()
        self.assertEqual(self.state("A-1"), "review")

    def test_real_changes_even_when_reverted_require_lead_merge(self):
        self.start()
        self.commit_file("src/other", "real\n", "real change", self.root)
        self.git("revert", "--no-edit", "HEAD")
        done = self.pm("submit", "A-1", "--note", "host tests", cwd=self.wt)
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn("ask the lead to merge main", done.stdout)
        self.assertNotIn("rebase", done.stdout)
        self.assertEqual(self.state("A-1"), "doing")

    def test_approve_merges_main_before_machine_check(self):
        self.start()
        self.commit_file("tools/check", "import os\nassert os.path.exists('src/other')\n",
                         "test(A-1): merged main check", self.wt)
        self.submit()
        self.commit_file("src/other", "main\n", "advance main", self.root)
        main = self.output("rev-parse", "main")
        done = self.pm("approve", "A-1", role="lead")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.output("rev-parse", "s0/A-1^2"), main)

    def test_main_conflict_aborts_and_names_path(self):
        self.start()
        self.submit()
        self.commit_file("src/a", "main\n", "conflict", self.root)
        main = self.output("rev-parse", "main")
        branch = self.output("rev-parse", "s0/A-1")
        done = self.pm("approve", "A-1", role="lead")
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn("src/a", done.stdout)
        self.assertIn("merge main", done.stdout)
        self.assertEqual(self.output("rev-parse", "main"), main)
        self.assertEqual(self.output("rev-parse", "s0/A-1"), branch)
        self.assert_clean(self.root)
        self.assert_clean(self.wt)
        self.assertEqual(self.state("A-1"), "review")

    def advance_knc(self, conflict=False):
        self.git("checkout", "-q", "knc", cwd=self.gcc)
        self.commit_file("gcc/a" if conflict else "gcc/other", "integration\n", "advance knc", self.gcc)
        self.git("checkout", "-q", "s0/A-1", cwd=self.gcc)

    def test_behind_knc_requires_lead_merge(self):
        self.start(gcc=True)
        self.advance_knc()
        done = self.pm("submit", "A-1", "--note", "host tests", cwd=self.wt)
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn("ask the lead to merge knc", done.stdout)
        self.assertNotIn("rebase", done.stdout)

    def test_approve_merges_knc_into_ticket_branch(self):
        self.start(gcc=True)
        self.submit()
        self.advance_knc()
        knc = self.output("rev-parse", "knc", cwd=self.gcc)
        done = self.pm("approve", "A-1", role="lead")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.output("rev-parse", "s0/A-1^2", cwd=self.gcc), knc)

    def test_knc_conflict_aborts_and_names_path(self):
        self.start(gcc=True)
        self.submit()
        self.advance_knc(conflict=True)
        knc = self.output("rev-parse", "knc", cwd=self.gcc)
        branch = self.output("rev-parse", "s0/A-1", cwd=self.gcc)
        done = self.pm("approve", "A-1", role="lead")
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn("gcc/a", done.stdout)
        self.assertIn("merge knc", done.stdout)
        self.assertEqual(self.output("rev-parse", "knc", cwd=self.gcc), knc)
        self.assertEqual(self.output("rev-parse", "s0/A-1", cwd=self.gcc), branch)
        for repo in (self.root, self.wt, self.gcc):
            self.assert_clean(repo)
        self.assertEqual(self.state("A-1"), "review")

    def assert_clean(self, repo):
        self.assertEqual(self.output("status", "--porcelain", cwd=repo), "")
        self.assertFalse(os.path.exists(self.output("rev-parse", "--path-format=absolute",
                                                   "--git-path", "MERGE_HEAD", cwd=repo)))
