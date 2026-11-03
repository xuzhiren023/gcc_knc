"""S2-11 native-review regressions; local shells and fake transport only."""
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import test_card_shared as shared
from test_card_shared import BOOT, REBOOT, SharedTransport

ROOT = Path(__file__).resolve().parents[2]


class CardRecovery(unittest.TestCase):
    setUp = shared.SharedCardRules.setUp
    invoke = shared.SharedCardRules.invoke
    own_lines = shared.SharedCardRules.own_lines

    def test_remote_error_on_same_boot_is_not_card_fault(self):
        snapshot = self.transport.snapshot
        calls = 0

        def transient(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("snapshot failed (status 1): diagnostic")
            return snapshot(**kwargs)

        self.transport.snapshot = transient
        result = self.invoke()
        self.assertEqual(result["result_class"], "infrastructure")
        self.assertEqual(result["boot_id_after"], BOOT)
        self.assertEqual([line["event"] for line in self.own_lines()], ["start", "finish"])
        self.assertEqual(self.own_lines()[-1]["outcome"], "infrastructure-failure")

    def lost_session(self, recovery):
        old = self.transport
        fresh = SharedTransport()
        fresh.ledger = self.ledger
        connect = old.connect
        attempts = []
        transport_error = self.runner.get("TransportError", OSError)

        def reconnect(run_dir, **kwargs):
            attempts.append(run_dir)
            if len(attempts) == 1:
                return connect(run_dir, **kwargs)
            if recovery == "unreachable":
                raise transport_error("reconnect: card unreachable")
            fresh.boot = REBOOT if recovery == "reboot" else BOOT
            return fresh.connect(run_dir, **kwargs)

        def execute(*args, **kwargs):
            old.unreachable = True
            raise transport_error("execute: SSH session ended")

        old.connect = reconnect
        old.execute = execute
        return fresh, attempts

    def test_reconnect_once_same_boot_cleans_without_replaying_job(self):
        fresh, attempts = self.lost_session("same")
        result = self.invoke()
        self.assertEqual(len(attempts), 2, result)
        self.assertEqual(attempts[0], attempts[1])
        self.assertEqual(result["result_class"], "infrastructure")
        self.assertEqual(result["boot_id_after"], BOOT)
        self.assertIn(("cleanup", result["run_dir"]), fresh.events)
        self.assertFalse(any(e[0] in ("stage", "execute") for e in fresh.events))
        self.assertEqual([line["event"] for line in self.own_lines()], ["start", "finish"])

    def test_failed_reconnect_or_changed_boot_faults_without_mutation(self):
        for recovery in ("unreachable", "reboot"):
            with self.subTest(recovery=recovery):
                self.transport = SharedTransport()
                self.transport.ledger = self.ledger
                fresh, attempts = self.lost_session(recovery)
                offset = len(self.own_lines())
                result = self.invoke()
                self.assertEqual(len(attempts), 2, result)
                self.assertEqual(result["result_class"], "infrastructure")
                self.assertEqual([line["event"] for line in self.own_lines()[offset:]],
                                 ["start", "card-fault", "finish"])
                self.assertFalse(any(e[0] in ("cleanup", "signal_owned") for e in fresh.events))

    def test_admission_reaps_stale_dirs_before_staging(self):
        self.transport.reap_stale = mock.Mock()
        result = self.invoke()
        self.assertEqual(result["result_class"], "program", result)
        self.transport.reap_stale.assert_called_once_with(BOOT, timeout=1)


class RemoteReview(unittest.TestCase):
    def setUp(self):
        self.runner = runpy.run_path(str(ROOT / "tools/card_run"))
        self.remote = (ROOT / "tools/card_run_remote.sh").read_text()
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.proc = self.directory / "proc"
        (self.proc / "sys/kernel/random").mkdir(parents=True)
        (self.proc / "sys/kernel/random/boot_id").write_text(BOOT + "\n")
        (self.proc / "cpuinfo").write_text("processor : 91\ncore id : 30\n")
        (self.proc / "meminfo").write_text("MemFree: 4000000 kB\n")

    def process(self, pid, ppid, cwd="/outside", exe="/bin/sh"):
        directory = self.proc / str(pid)
        directory.mkdir()
        (directory / "status").write_text("Name:\tworker\nPPid:\t%d\n" % ppid)
        (directory / "comm").write_text("worker\n")
        if ppid != 2:
            (directory / "exe").symlink_to(exe)
            (directory / "cwd").symlink_to(cwd)

    def shell(self, script):
        return subprocess.run([shutil.which("sh"), "-c", script],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)

    def test_snapshot_has_constant_external_command_count(self):
        self.process(42, 1, cwd="/other work")
        for pid in range(100, 400):
            self.process(pid, 2)
        counter = self.directory / "commands"
        wrappers = "\n".join(
            '%s() { printf "%s\\n" >> "%s"; command %s "$@"; }' %
            (tool, tool, counter, tool) for tool in ("readlink", "cat", "ls", "awk"))
        script = self.remote.replace("/proc/", str(self.proc) + "/")
        answer = self.shell(script + "\n" + wrappers + "\nsnapshot\n")
        self.assertEqual(answer.returncode, 0, answer.stderr)
        commands = counter.read_text().splitlines()
        self.assertLessEqual(len(commands), 3, commands[:12])
        self.assertNotIn("readlink", commands)
        session = object.__new__(self.runner["SSHSession"])
        session.boot_id = None
        session.rpc = mock.Mock(return_value=answer.stdout.rstrip(b"\n"))
        snapshot = session.snapshot(timeout=1)
        self.assertEqual([p["pid"] for p in snapshot["processes"]], ["42"])
        self.assertEqual(snapshot["processes"][0]["cwd"], "/other work")

    def test_remote_failure_names_snapshot_and_captures_stderr(self):
        session = self.runner["SSHSession"]([shutil.which("sh")], "/unused", 1)
        self.addCleanup(session.close)
        session.rpc("snapshot() { echo snapshot-diagnostic >&2; return 1; }", 1)
        with self.assertRaises(OSError) as raised:
            session.snapshot(timeout=1)
        self.assertIn("snapshot", str(raised.exception))
        self.assertIn("snapshot-diagnostic", str(raised.exception))
        self.assertIn("status 1", str(raised.exception))

    def test_remote_deadline_names_snapshot(self):
        session = self.runner["SSHSession"]([shutil.which("sh")], "/unused", 1)
        self.addCleanup(session.close)
        session.rpc("snapshot() { sleep 1; }", 1)
        with self.assertRaises(OSError) as raised:
            session.snapshot(timeout=0.02)
        self.assertIn("snapshot", str(raised.exception))
        self.assertIn("deadline", str(raised.exception))

    def test_stale_reaper_preserves_live_foreign_symlink_and_bad_names(self):
        parent = self.directory / "claude"
        parent.mkdir()
        stale = parent / ("claude-" + "a" * 32)
        live = parent / ("claude-" + "b" * 32)
        foreign = parent / "gpt61-job"
        malformed = parent / "claude-short"
        for directory in (stale, live, foreign, malformed):
            directory.mkdir()
            (directory / "output").write_text("keep")
        link = parent / ("claude-" + "c" * 32)
        link.symlink_to(foreign, target_is_directory=True)
        self.process(42, 1, cwd=str(live))
        session = object.__new__(self.runner["SSHSession"])
        session.run_dir = "/tmp/claude/claude-" + "d" * 32
        session.boot_id = BOOT
        method = getattr(session, "reap_stale", None)
        self.assertTrue(callable(method), "admission needs guarded stale-directory recovery")
        for boot in (REBOOT, BOOT):
            with self.subTest(boot=boot):
                def rpc(script, timeout, **kwargs):
                    script = (self.remote + "\n" + script).replace(
                        "/tmp/claude", str(parent)).replace("/proc/", str(self.proc) + "/")
                    answer = self.shell(script)
                    if answer.returncode:
                        raise OSError(answer.stderr.decode())
                    return answer.stdout
                session.rpc = rpc
                if boot == REBOOT:
                    with self.assertRaises(OSError):
                        method(boot, timeout=1)
                    self.assertTrue(stale.exists())
                else:
                    method(boot, timeout=1)
                    self.assertFalse(stale.exists())
                for directory in (live, foreign, malformed):
                    self.assertEqual((directory / "output").read_text(), "keep")
                self.assertTrue(link.is_symlink())


if __name__ == "__main__":
    unittest.main()
