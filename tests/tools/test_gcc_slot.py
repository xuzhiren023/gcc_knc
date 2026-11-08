"""S8-18: a second GCC tree (slot 2) for lane gcc2 tickets, beside today's slot 1."""
import os
from unittest import mock

from test_harness import POLICY, Sandbox
import dispatch
import pm
import storage
import test_pm_gcc


class Resolver(Sandbox):
    def test_slot_one_or_unset_is_todays_tree_and_slot_two_is_its_own(self):
        shared = storage.shared_area(self.root)
        for value, tree, build in ((None, "gcc", "gcc-build"), ("1", "gcc", "gcc-build"),
                                   ("2", "gcc-2", "gcc-build-2")):
            with self.subTest(slot=value), mock.patch.dict(os.environ):
                os.environ.pop("KNC_GCC_SLOT", None)
                if value:
                    os.environ["KNC_GCC_SLOT"] = value
                self.assertEqual(storage.gcc_tree(self.root), os.path.join(shared, tree))
                self.assertEqual(storage.gcc_build_dir(self.root), os.path.join(shared, build))

    def test_lane_of_accepts_gcc2(self):
        ticket = pm.Ticket(None, "U-1", {"gcc": "yes", "lane": "gcc2"}, "")
        self.assertEqual(pm.lane_of(ticket), "gcc2")

    def test_dispatch_sets_slot_two_only_for_a_gcc2_ticket(self):
        board = mock.Mock(root=self.root, policy=POLICY)
        gcc2 = mock.Mock(id="U-1", fields={"gcc": "yes", "lane": "gcc2"})
        gcc1 = mock.Mock(id="U-2", fields={"gcc": "yes", "lane": "gcc"})
        with mock.patch.dict(os.environ, KNC_GCC_SLOT="2"):
            env = dispatch.session_env(board, gcc2, "engineer")
            self.assertEqual(env["KNC_GCC_SLOT"], "2")
            tree = os.path.join(storage.shared_area(self.root), "gcc-2").replace("\\", "/")
            self.assertIn("'safe.directory'='%s'" % tree, env["GIT_CONFIG_PARAMETERS"])
            self.assertNotIn("KNC_GCC_SLOT", dispatch.session_env(board, gcc1, "engineer"))


class SlotTickets(Sandbox):
    def setUp(self):
        # GccTickets' setUp, copied: inheriting would rerun its tests here.
        Sandbox.setUp(self)
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

    output = test_pm_gcc.GccTickets.output
    start = test_pm_gcc.GccTickets.start

    def test_submit_refuses_a_branch_behind_knc(self):
        self.start()
        self.commit_file("tools/check", "raise SystemExit(0)\n", "test(A-1): check [red]", self.wt)
        self.commit_file("gcc/imci.md", "ticket\n", "feat(A-1): GCC", self.gcc)
        # The other lane merged into knc after this branch started.
        self.git("checkout", "-q", "knc", cwd=self.gcc)
        self.commit_file("gcc/other.md", "other\n", "Merge S0-9", self.gcc)
        self.git("checkout", "-q", self.branch, cwd=self.gcc)
        done = self.pm("submit", "A-1", "--note", "T0", cwd=self.wt)
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn("rebase", done.stdout)
        self.assertEqual(self.state("A-1"), "doing")

    def test_gcc2_ticket_works_in_slot_two_and_merges_while_slot_one_holds_knc(self):
        path = os.path.join(self.root, "work", "tickets", "A-1.md")
        with open(path) as f:
            text = f.read()
        with open(path, "w", newline="\n") as f:
            f.write(text.replace("gcc: yes", "gcc: yes\nlane: gcc2"))
        self.git("commit", "-qam", "lane gcc2")
        gcc2 = os.path.join(self.root, ".work", "_shared", "gcc-2")
        self.git("worktree", "add", "-q", "--detach", gcc2, "knc", cwd=self.gcc)
        self.start()
        self.assertEqual(self.output("branch", "--show-current", cwd=gcc2), self.branch)
        self.assertEqual(self.output("branch", "--show-current"), "knc")
        self.commit_file("tools/check", "raise SystemExit(0)\n", "test(A-1): check [red]", self.wt)
        self.commit_file("gcc/imci.md", "ticket\n", "feat(A-1): GCC", gcc2)
        done = self.pm("submit", "A-1", "--note", "T0", cwd=self.wt)
        self.assertEqual(done.returncode, 0, done.stdout)
        done = self.pm("approve", "A-1", role="lead")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.output("rev-parse", "knc^2"), self.output("rev-parse", self.branch))
        self.assertEqual(self.output("rev-parse", "HEAD", cwd=gcc2), self.output("rev-parse", "knc"))
        # Slot 1 no longer has knc checked out, so moving knc left no stale files behind.
        self.assertEqual(self.output("status", "--porcelain"), "")
        self.assertEqual(self.state("A-1"), "done")
