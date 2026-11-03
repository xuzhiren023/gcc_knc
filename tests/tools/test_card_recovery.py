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

    def test_deadline_after_reconnect_same_boot_is_not_card_fault(self):
        for step in ("signal_owned", "cleanup"):
            with self.subTest(step=step):
                self.transport = SharedTransport()
                self.transport.ledger = self.ledger
                fresh, attempts = self.lost_session("same")
                original = getattr(fresh, step)

                def deadline(*args, **kwargs):
                    original(*args, **kwargs)
                    raise self.runner["TransportError"](step + ": deadline exceeded")

                setattr(fresh, step, deadline)
                offset = len(self.own_lines())
                result = self.invoke()
                self.assertEqual(len(attempts), 2, result)
                self.assertEqual(result["boot_id_after"], BOOT)
                self.assertEqual(result["result_class"], "infrastructure")
                self.assertIn(step + ": deadline exceeded", result["detail"])
                self.assertIn((step, result["run_dir"]), fresh.events)
                lines = self.own_lines()[offset:]
                self.assertEqual([line["event"] for line in lines], ["start", "finish"])
                self.assertEqual(lines[-1]["outcome"], "infrastructure-failure")

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

    def test_session_lost_during_cleanup_also_reconnects_once(self):
        fresh, attempts = self.lost_session("same")
        self.transport.execute = SharedTransport.execute.__get__(self.transport)

        def disconnect(*args, **kwargs):
            self.transport.unreachable = True
            raise self.runner["TransportError"]("cleanup: SSH session ended")

        self.transport.cleanup = disconnect
        result = self.invoke()
        self.assertEqual(len(attempts), 2, result)
        self.assertEqual(result["result_class"], "infrastructure")
        self.assertIn(("cleanup", result["run_dir"]), fresh.events)
        self.assertFalse(any(e[0] in ("stage", "execute") for e in fresh.events))
        self.assertEqual([line["event"] for line in self.own_lines()], ["start", "finish"])

    def test_admission_reaps_stale_dirs_before_staging(self):
        self.transport.reap_stale = mock.Mock(return_value=dict(reaped=[], stale_kept=[]))
        result = self.invoke()
        self.assertEqual(result["result_class"], "program", result)
        self.transport.reap_stale.assert_called_once_with(BOOT, timeout=1)

    def test_result_lists_reaped_and_live_stale_directories(self):
        reaped = ["/tmp/claude/claude-" + "a" * 32]
        kept = ["/tmp/claude/claude-" + "b" * 32]
        self.transport.reap_stale = mock.Mock(return_value=dict(reaped=reaped, stale_kept=kept))
        result = self.invoke()
        self.assertEqual(result["result_class"], "program", result)
        self.assertEqual(result.get("reaped"), reaped)
        self.assertEqual(result.get("stale_kept"), kept)

    def test_cpuinfo_read_once_including_waits_and_reconnect(self):
        for reconnect in (False, True):
            with self.subTest(reconnect=reconnect):
                self.transport = SharedTransport()
                self.transport.ledger = self.ledger
                self.transport.free_kb = [1_000_000, 4_000_000]
                requests = []
                sessions = [self.transport]
                if reconnect:
                    fresh, attempts = self.lost_session("same")
                    sessions.append(fresh)
                for session in sessions:
                    original = session.snapshot

                    def snapshot(*, timeout, include_cpuinfo=True, original=original):
                        requests.append(include_cpuinfo)
                        return original(timeout=timeout, include_cpuinfo=include_cpuinfo)

                    session.snapshot = snapshot
                result = self.invoke()
                self.assertEqual(result["result_class"], "infrastructure" if reconnect else "program", result)
                self.assertEqual(result["cpus"], [4, 13, 91])
                self.assertGreaterEqual(len(requests), 4)
                self.assertEqual(requests, [True] + [False] * (len(requests) - 1))
                if reconnect:
                    self.assertEqual(len(attempts), 2)


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
        # Linux kernel threads still have links visible to lstat/-L, but their
        # targets cannot be followed. Model that rather than omitting the links.
        kernel = pid == 2 or ppid == 2
        (directory / "exe").symlink_to("/missing-kernel-exe" if kernel else exe)
        (directory / "cwd").symlink_to("/missing-kernel-cwd" if kernel else cwd)

    def shell(self, script, timeout=60):
        return subprocess.run([shutil.which("sh"), "-c", script],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)

    def symlink_tmp(self):
        physical = self.directory / "var/volatile/tmp"
        physical.mkdir(parents=True)
        logical = self.directory / "tmp"
        logical.symlink_to(physical, target_is_directory=True)
        remote = self.remote.replace("/tmp", str(logical)).replace(
            "/proc/", str(self.proc) + "/")
        return logical, physical, remote

    def test_snapshot_physical_run_dir_excludes_our_watchdog_and_program(self):
        logical, physical, remote = self.symlink_tmp()
        job = "claude-" + "a" * 32
        run_dir = logical / "claude" / job
        physical_dir = physical / "claude" / job
        # Snapshot must work before staging creates the directory too.
        self.process(42, 1, cwd=str(physical_dir), exe="/bin/sleep")
        self.process(43, 1, exe=str(physical_dir / "claude-program"))
        self.process(44, 1, cwd=str(physical_dir) + "-foreign")
        self.process(45, 1, exe=str(run_dir / "claude-program"))
        answer = self.shell(remote + '\nrun_dir="%s"\nsnapshot\n' % run_dir)
        self.assertEqual(answer.returncode, 0, answer.stderr)
        session = object.__new__(self.runner["SSHSession"])
        session.boot_id = None
        session.rpc = mock.Mock(return_value=answer.stdout.rstrip(b"\n"))
        snapshot = session.snapshot(timeout=1)
        foreign = self.runner["foreign_processes"](snapshot, str(run_dir), set())
        self.assertEqual([p["pid"] for p in foreign], ["44"], foreign)
        self.assertEqual(snapshot.get("physical_run_dir"), str(physical_dir))

    def test_tmp_symlink_guard_owned_identity_and_cleanup(self):
        logical, physical, remote = self.symlink_tmp()
        job = "claude-" + "a" * 32
        run_dir = logical / "claude" / job
        run_dir.mkdir(parents=True)
        self.process(42, 1, cwd=str(physical / "claude" / job))
        script = remote + '\nrun_dir="%s"\nboot_id="%s"\n' % (run_dir, BOOT)
        # Resolve /tmp once in this shell, even across repeated guards.
        script += ('cd() { if [ "$*" = "%s" ]; then echo resolve-tmp >&2; fi; '
                   'command cd "$@"; }\n' % logical)
        script += ('cd -- "$run_dir" && guard_boot && guard_boot && owned_pid 42\n'
                   'identity=$?\n[ "$identity" = 0 ] || exit "$identity"\n'
                   'rm -rf "%s/42"\nsleep() { :; }\ncleanup\n' % self.proc)
        answer = self.shell(script)
        self.assertEqual(answer.returncode, 0, answer.stderr)
        self.assertEqual(answer.stderr.count(b"resolve-tmp"), 1, answer.stderr)
        self.assertFalse(run_dir.exists())
        self.assertFalse((physical / "claude").exists())

    def test_tmp_symlink_reaper_removes_old_dirs_preserves_live_and_foreign(self):
        logical, physical, remote = self.symlink_tmp()
        parent = logical / "claude"
        parent.mkdir()
        stale = [parent / ("claude-" + digit * 32) for digit in "ab"]
        live = parent / ("claude-" + "c" * 32)
        foreign = parent / "gpt61-job"
        malformed = parent / "claude-short"
        for directory in stale + [live, foreign, malformed]:
            directory.mkdir()
            (directory / "output").write_text("keep")
        link = parent / ("claude-" + "d" * 32)
        link.symlink_to(foreign, target_is_directory=True)
        self.process(42, 1, cwd=str(physical / "claude" / live.name))
        answer = self.shell(remote + '\nrun_dir="%s/claude-%s"\nboot_id="%s"\n'
                            'cd "%s"\nreap_stale\n' %
                            (parent, "e" * 32, BOOT, self.directory))
        self.assertEqual(answer.returncode, 0, answer.stderr)
        self.assertTrue(all(not directory.exists() for directory in stale))
        for directory in (live, foreign, malformed):
            self.assertEqual((directory / "output").read_text(), "keep")
        self.assertTrue(link.is_symlink())

    def test_directory_and_boot_guards_name_each_failed_check(self):
        logical, physical, remote = self.symlink_tmp()
        run_dir = logical / "claude" / ("claude-" + "a" * 32)
        run_dir.mkdir(parents=True)
        link = run_dir.parent / ("claude-" + "b" * 32)
        link.symlink_to(run_dir, target_is_directory=True)
        cases = (
            (str(run_dir) + "x", "", "guard_dir", "directory shape"),
            (str(run_dir)[:-1] + "z", "", "guard_dir", "lowercase hex"),
            (str(link), "", "guard_dir", "symlink"),
            (str(run_dir)[:-1] + "c", "", "guard_dir", "directory missing"),
            (str(run_dir), 'cd "%s"' % physical, "guard_dir", "physical cwd"),
            (str(run_dir), 'id() { echo -1; }', "guard_dir", "owner"),
            (str(run_dir), 'boot_id=', "check_boot", "boot ID missing"),
            (str(run_dir), 'boot_id=changed', "check_boot", "boot ID mismatch"),
            (str(run_dir), 'cat() { return 1; }', "check_boot", "boot ID unreadable"),
        )
        for path, setup, operation, diagnostic in cases:
            with self.subTest(check=diagnostic):
                answer = self.shell(remote + '\nrun_dir="%s"\nboot_id="%s"\n'
                                    'cd "%s"\n%s\n%s\n' %
                                    (path, BOOT, run_dir, setup, operation))
                self.assertNotEqual(answer.returncode, 0)
                self.assertIn(diagnostic.encode(), answer.stderr)

    def test_snapshot_has_constant_external_command_count(self):
        # Match the native 240-CPU /proc file, including 23 unused lines/block.
        cpuinfo = "\n\n".join(
            "processor : %d\ncore id : %d\n" % (cpu, cpu // 4 + 1) +
            "\n".join("unused%d : ignored" % field for field in range(23))
            for cpu in range(240)) + "\n\n"
        (self.proc / "cpuinfo").write_text(cpuinfo)
        (self.proc / "meminfo").write_text(
            "MemTotal: 16000000 kB\nMemFree: 4000000 kB\nCached: 2000000 kB\n")
        self.process(42, 1, cwd="/other work")
        for pid in range(100, 400):
            self.process(pid, 2)
        counter = self.directory / "commands"
        wrappers = "\n".join(
            '%s() { printf "%s\\n" >> "%s"; command %s "$@"; }' %
            (tool, tool, counter, tool)
            for tool in ("readlink", "cat", "ls", "awk", "read", "printf"))
        # Count shell builtins too: per-line read/printf caused the native deadline.
        wrappers = wrappers.replace('printf "', 'command printf "')
        script = self.remote.replace("/proc/", str(self.proc) + "/")
        script += "\nrun_dir=/tmp/claude/claude-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        answer = self.shell(script + "\n" + wrappers + "\nsnapshot\n")
        self.assertEqual(answer.returncode, 0, answer.stderr)
        commands = counter.read_text().splitlines()
        self.assertLessEqual(len(commands), 1000, commands[:12])
        self.assertLessEqual(sum(c not in ("read", "printf") for c in commands), 5)
        self.assertNotIn("readlink", commands)
        session = object.__new__(self.runner["SSHSession"])
        session.boot_id = None
        session.rpc = mock.Mock(return_value=answer.stdout.rstrip(b"\n"))
        snapshot = session.snapshot(timeout=1)
        self.assertEqual([p["pid"] for p in snapshot["processes"]], ["42"])
        self.assertEqual(snapshot["processes"][0]["cwd"], "/other work")
        self.assertEqual(self.runner["cpu_binding"](snapshot["cpuinfo"]),
                         self.runner["cpu_binding"](cpuinfo))
        self.assertNotIn("unused", snapshot["cpuinfo"])
        self.assertEqual(snapshot["meminfo"], "MemFree: 4000000 kB")
        # Subsequent snapshots must still refresh memory/process/boot data.
        answer = self.shell(script + "\n" + wrappers + "\nsnapshot skip-cpu\n")
        self.assertEqual(answer.returncode, 0, answer.stderr)
        self.assertNotIn(b"CPU\t", answer.stdout)
        self.assertIn(b"MEM\tMemFree: 4000000 kB", answer.stdout)
        session.rpc.return_value = answer.stdout.rstrip(b"\n")
        snapshot = session.snapshot(timeout=1, include_cpuinfo=False)
        session.rpc.assert_called_with("snapshot skip-cpu", 1, step="snapshot")
        self.assertEqual(snapshot["cpuinfo"], "")
        self.assertEqual(snapshot["meminfo"], "MemFree: 4000000 kB")

    def test_remote_failure_names_snapshot_and_captures_stderr(self):
        session = self.runner["SSHSession"]([shutil.which("sh")], "/unused", 1)
        self.addCleanup(session.close)
        session.rpc("snapshot() { echo snapshot-diagnostic >&2; return 1; }", 1)
        with self.assertRaises(OSError) as raised:
            session.snapshot(timeout=1)
        self.assertIn("snapshot", str(raised.exception))
        self.assertIn("snapshot-diagnostic", str(raised.exception))
        self.assertIn("status 1", str(raised.exception))

    def test_cleanup_and_reaper_skip_kernel_threads_without_commands(self):
        self.process(42, 1)
        self.process(2, 0)
        for pid in range(100, 400):
            self.process(pid, 2)
        for operation in ("stop_owned", "cleanup", "reap_stale"):
            with self.subTest(operation=operation):
                parent = self.directory / "claude"
                run_dir = parent / ("claude-" + "a" * 32)
                run_dir.mkdir(parents=True)
                foreign = parent / "gpt61-job"
                foreign.mkdir(exist_ok=True)
                (foreign / "output").write_text("keep")
                counter = self.directory / "commands"
                counter.write_text("")
                wrappers = "\n".join(
                    '%s() { printf "%s\\n" >> "%s"; command %s "$@"; }' %
                    (tool, tool, counter, tool)
                    for tool in ("readlink", "cat", "ls", "awk", "id", "rm", "rmdir"))
                # No wait or signal is needed with no live owned process.
                wrappers += '\nsleep() { :; }\nkill() { echo unexpected-signal >&2; return 99; }'
                script = self.remote.replace("/tmp", str(self.directory)).replace(
                    "/proc/", str(self.proc) + "/")
                cwd = self.directory if operation == "reap_stale" else run_dir
                try:
                    answer = self.shell(script + "\n" + wrappers +
                                        '\nrun_dir="%s"\nboot_id="%s"\ncd -- "%s"\n%s\n' %
                                        (run_dir, BOOT, cwd, operation), timeout=10)
                except subprocess.TimeoutExpired:
                    answer = None
                commands = counter.read_text().splitlines()
                remaining = run_dir.exists()
                # Keep the next subcase independent even when stop_owned keeps cwd.
                if run_dir.exists():
                    run_dir.rmdir()
                self.assertLessEqual(len(commands), 24, commands[:12])
                self.assertLessEqual(commands.count("readlink"), 6)
                self.assertIsNotNone(answer, "cleanup exceeded deadline despite bounded commands")
                self.assertEqual(answer.returncode, 0, answer.stderr)
                self.assertNotIn(b"unexpected-signal", answer.stderr)
                self.assertEqual((foreign / "output").read_text(), "keep")
                self.assertEqual(remaining, operation == "stop_owned")

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
        self.process(2, 0)
        for pid in range(100, 400):
            self.process(pid, 2)
        session = object.__new__(self.runner["SSHSession"])
        session.run_dir = "/tmp/claude/claude-" + "d" * 32
        session.boot_id = BOOT
        method = getattr(session, "reap_stale", None)
        self.assertTrue(callable(method), "admission needs guarded stale-directory recovery")
        for boot in (REBOOT, BOOT):
            with self.subTest(boot=boot):
                def rpc(script, timeout, **kwargs):
                    script = (self.remote + "\n" + script).replace(
                        "/tmp", str(self.directory)).replace("/proc/", str(self.proc) + "/")
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
                    report = method(boot, timeout=1)
                    self.assertFalse(stale.exists())
                    self.assertEqual(report, dict(reaped=[str(stale)], stale_kept=[str(live)]))
                for directory in (live, foreign, malformed):
                    self.assertEqual((directory / "output").read_text(), "keep")
                self.assertTrue(link.is_symlink())


if __name__ == "__main__":
    unittest.main()
