"""S0-04 RED contract: seven T0 cases; no SSH, configuration, or card needed."""
import json
from pathlib import Path
import re
import runpy
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
BOOT = "00000000-0000-0000-0000-000000000001"
REBOOT = "00000000-0000-0000-0000-000000000002"
RUN_DIR = re.compile(r"/var/volatile/tmp/gcc-knc-[0-9a-f]{32}\Z")
DAEMON = {"pid": 1, "ppid": 0, "name": "sshd", "exe": "/usr/sbin/sshd", "cwd": "/"}
FOREIGN = {"pid": 42, "name": "other-job", "exe": "/opt/other/job", "cwd": "/opt/other"}
UNKNOWN = {"pid": 43, "name": None, "exe": None, "cwd": None}


class FakeTransport:
    """Record every operation and reject unsafe mutation requests immediately."""

    def __init__(self):
        self.events = []
        self.now = 0.0
        self.boot = BOOT
        self.run_dir = None
        self.staged = False
        self.processes = []
        self.late_processes = []
        self.foreign_path = None
        self.unreachable = False
        self.link_broken = False
        self.stage_failure = False
        self.timed_out = False
        self.reboot = False
        self.status = 0

    def monotonic(self):
        return self.now

    def connect(self, run_dir, *, timeout):
        self._directory(run_dir)
        self.events.append(("connect", run_dir, timeout))
        if self.unreachable is True:
            raise OSError("fake card unreachable")
        self.run_dir = run_dir
        return self

    def snapshot(self, *, timeout):
        self.events.append(("snapshot", timeout))
        if self.link_broken:
            raise OSError("fake SSH link broken")
        processes = [DAEMON] + self.processes
        if self.staged:
            processes += self.late_processes
        if self.run_dir:
            if self.foreign_path == "prefix-cwd":
                processes += [{"pid": 44, "name": "other-job", "exe": "/opt/other/job",
                               "cwd": self.run_dir + "0"}]
            elif self.foreign_path == "other-run-exe":
                other_dir = self.run_dir[:-1] + ("0" if self.run_dir[-1] != "0" else "1")
                processes += [{"pid": 45, "name": "other-job", "exe": other_dir + "/job",
                               "cwd": "/opt/other"}]
            # A runner helper is owned by cwd, even though its exe is /bin/sh.
            processes += [{"pid": 80, "name": "sh", "exe": "/bin/sh", "cwd": self.run_dir}]
        return {"boot_id": self.boot, "processes": processes}

    def stage(self, run_dir, program, *, timeout):
        self._owned(run_dir, BOOT)
        if self.staged:
            raise AssertionError("must not restage/retry")
        self.staged = True
        self.events.append(("stage", run_dir, Path(program), timeout))
        if self.stage_failure:
            raise OSError("fake partial staging failure")

    def execute(self, run_dir, argv, *, timeout, card_timeout=None):
        self._owned(run_dir, BOOT)
        self.events.append(("execute", run_dir, list(argv), timeout, card_timeout))
        self.now += timeout if self.timed_out else 12.0
        if self.unreachable == "execute":
            self.link_broken = True
            raise OSError("fake SSH link broken during execute")
        if self.reboot:
            self.boot = REBOOT
        if self.timed_out:
            raise TimeoutError("fake program deadline")
        return self.status

    def signal_owned(self, run_dir, boot_id, *, timeout):
        self._owned(run_dir, boot_id)
        self.events.append(("signal_owned", run_dir, boot_id, timeout))

    def cleanup(self, run_dir, boot_id, *, timeout):
        self._owned(run_dir, boot_id)
        self.events.append(("cleanup", run_dir, boot_id, timeout))

    def close(self):
        self.events.append(("close",))

    @staticmethod
    def _directory(run_dir):
        if not isinstance(run_dir, str) or not RUN_DIR.fullmatch(run_dir):
            raise AssertionError("action outside exact private directory: %r" % (run_dir,))

    def _owned(self, run_dir, boot_id):
        self._directory(run_dir)
        if run_dir != self.run_dir or boot_id != self.boot:
            raise AssertionError("action outside this run or across a reboot")


class CardRun(unittest.TestCase):
    def setUp(self):
        runner_path = ROOT / "tools/card_run"
        self.assertTrue(runner_path.is_file(), "S0-04 RED: tools/card_run is not implemented")
        self.runner = runpy.run_path(str(runner_path))
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.program = self.directory / "hello.mic"
        self.program.write_bytes(b"fake executable; never run on host")
        self.lock = self.directory / "card.lock"
        self.external = self.directory / "foreign.lock"
        self.receipt = self.directory / "result.json"
        self.transport = FakeTransport()

    def run_card(self):
        result = self.runner["run"](
            self.program, ["argument with spaces"], lock_path=self.lock,
            external_locks=[self.external], baseline_names={"sshd"},
            timeout=30.0, transport_timeout=1.0, receipt_path=self.receipt,
            transport=self.transport, monotonic=self.transport.monotonic)
        self.assertEqual(json.loads(self.receipt.read_text(encoding="utf8")), result)
        codes = [self.runner[name] for name in ("REFUSED_EXIT", "TIMEOUT_EXIT", "INFRA_EXIT")]
        self.assertEqual(len(set(codes)), 3)
        self.assertTrue(all(isinstance(code, int) and code != 0 for code in codes))
        return result

    def names(self):
        return [event[0] for event in self.transport.events]

    def assert_result(self, result, kind, code, before=BOOT, after=BOOT, seconds=0.0,
                      program_status=None):
        self.assertEqual(result["result_class"], kind)
        self.assertEqual(result["exit_code"], code)
        self.assertEqual(result["program_exit_code"], program_status)
        self.assertEqual(result["boot_id_before"], before)
        self.assertEqual(result["boot_id_after"], after)
        self.assertAlmostEqual(result["card_minutes"], seconds / 60.0)

    def assert_released(self):
        self.assertFalse(self.lock.exists(), "release our acquired local lock")
        self.assertEqual(self.names().count("connect"), 1, "no connection retries")
        self.assertEqual(self.names().count("close"), 1)

    def assert_cleaned(self):
        cleanups = [event for event in self.transport.events if event[0] == "cleanup"]
        self.assertEqual(cleanups, [("cleanup", self.transport.run_dir, BOOT, 1.0)])
        self.assert_released()

    def test_lock_present_refuses_without_touching_owner(self):
        for lock in (self.lock, self.external):
            with self.subTest(lock=lock.name):
                lock.write_text("foreign-or-stale-owner", encoding="utf8")
                try:
                    result = self.run_card()
                    self.assert_result(result, "refused", self.runner["REFUSED_EXIT"],
                                       before=None, after=None)
                    self.assertEqual(lock.read_text(encoding="utf8"), "foreign-or-stale-owner")
                    self.assertEqual(self.transport.events, [])
                    self.assertIn(str(lock), result["detail"])
                    if lock == self.external:
                        self.assertFalse(self.lock.exists())
                finally:
                    # Test fixture teardown only; the runner may not remove it.
                    lock.unlink()

    def test_worktree_roots_share_default_lock(self):
        main = self.directory / "project"
        expected = main / ".work/_state/card.lock"
        roots = (main, main / ".work/S0-04", main / ".work/another-ticket")
        for root in roots:
            with self.subTest(root=root):
                self.assertEqual(self.runner["default_lock"](root), expected)

    def test_foreign_or_unknown_process_refuses_before_staging_or_exec(self):
        cases = ((False, FOREIGN, None), (False, UNKNOWN, None), (True, FOREIGN, None),
                 (False, {"pid": 46, "ppid": 1, "name": "kworker/0:1",
                          "exe": None, "cwd": None}, None),
                 (False, {"pid": 44}, "prefix-cwd"),
                 (False, {"pid": 45}, "other-run-exe"))
        for late, process, foreign_path in cases:
            with self.subTest(late=late, pid=process["pid"], foreign_path=foreign_path):
                self.transport = FakeTransport()
                self.transport.foreign_path = foreign_path
                if foreign_path is None:
                    if late:
                        self.transport.late_processes = [process]
                    else:
                        self.transport.processes = [process]
                result = self.run_card()
                self.assert_result(result, "refused", self.runner["REFUSED_EXIT"])
                self.assertIn(str(process["pid"]), result["detail"])
                self.assertNotIn("execute", self.names())
                self.assertNotIn("signal_owned", self.names())
                if late:
                    self.assert_cleaned()
                    names = self.names()
                    stage = names.index("stage")
                    self.assertIn("snapshot", names[:stage])
                    self.assertIn("snapshot", names[stage + 1:names.index("cleanup")])
                else:
                    self.assertNotIn("stage", self.names())
                    self.assert_cleaned()

    def test_kernel_threads_are_allowed_by_parent_not_name(self):
        self.transport.processes = [
            {"pid": 2, "ppid": 0, "name": "kthreadd", "exe": None, "cwd": None},
            {"pid": 47, "ppid": 2, "name": "kworker/0:1", "exe": None, "cwd": None}]
        result = self.run_card()
        self.assert_result(result, "program", 0, seconds=12.0, program_status=0)
        self.assert_cleaned()

    def test_timeout_signals_only_owned_directory_then_cleans_up(self):
        self.transport.timed_out = True
        result = self.run_card()
        self.assert_result(result, "timeout", self.runner["TIMEOUT_EXIT"], seconds=30.0)
        names = self.names()
        self.assertLess(names.index("stage"), names.index("execute"))
        self.assertIn("snapshot", names[names.index("stage") + 1:names.index("execute")])
        self.assertIn("snapshot", names[names.index("execute") + 1:names.index("signal_owned")])
        self.assertLess(names.index("signal_owned"), names.index("cleanup"))
        self.assertEqual([e for e in self.transport.events if e[0] == "signal_owned"],
                         [("signal_owned", self.transport.run_dir, BOOT, 1.0)])
        execute = next(e for e in self.transport.events if e[0] == "execute")
        self.assertIsInstance(execute[4], int, "card sleep requires whole seconds")
        self.assertEqual([e for e in self.transport.events if e[0] == "execute"],
                         [("execute", self.transport.run_dir, ["argument with spaces"], 30.0, 35)])
        self.assert_cleaned()

        # A control poll started just before the deadline gets its full transport
        # budget; expiry is then a program timeout, not a broken SSH connection.
        session = object.__new__(self.runner["SSHSession"])
        session.run_dir = self.transport.run_dir
        session.boot_id = BOOT
        session.transport_timeout = 1.0
        session.rpc = mock.Mock(side_effect=[b"", b"", b"", b"running"])
        with mock.patch.object(self.runner["time"], "monotonic",
                               side_effect=[0.0, 29.9, 30.0, 30.0]), \
                mock.patch.object(self.runner["time"], "sleep"):
            with self.assertRaises(TimeoutError):
                session.execute(session.run_dir, [], timeout=30.0, card_timeout=35)
        self.assertTrue(all(call.args[1] == 1.0 for call in session.rpc.call_args_list))
        self.assertIn("start_job 35 ", session.rpc.call_args_list[0].args[0])

    def test_unreachable_is_infrastructure_without_retry(self):
        for phase in (True, "execute"):
            with self.subTest(phase=phase):
                self.transport = FakeTransport()
                self.transport.unreachable = phase
                result = self.run_card()
                self.assertEqual(result["result_class"], "infrastructure")
                self.assertEqual(result["exit_code"], self.runner["INFRA_EXIT"])
                self.assertFalse(self.lock.exists())
                self.assertEqual(self.names().count("connect"), 1)
                self.assertNotIn("signal_owned", self.names())
                self.assertNotIn("cleanup", self.names())
                if phase is True:
                    self.assert_result(result, "infrastructure", self.runner["INFRA_EXIT"],
                                       before=None, after=None)
                    self.assertEqual(self.names(), ["connect"])
                    self.assertEqual(self.transport.events[0][2], 1.0)
                    self.assertIn("unreachable", result["detail"].lower())
                else:
                    self.assert_result(result, "infrastructure", self.runner["INFRA_EXIT"], seconds=12.0)
                    execute = next(e for e in self.transport.events if e[0] == "execute")
                    self.assertEqual(execute[4], 35.0, "watchdog armed before a link can break")
                    self.assertIn("link broken", result["detail"])
                    self.assert_released()

    def test_reboot_during_run_is_infrastructure_and_forbids_cleanup(self):
        self.transport.reboot = True
        result = self.run_card()
        self.assert_result(result, "infrastructure", self.runner["INFRA_EXIT"],
                           after=REBOOT, seconds=12.0, program_status=0)
        self.assertEqual(self.names().count("execute"), 1)
        self.assertNotIn("signal_owned", self.names())
        self.assertNotIn("cleanup", self.names())
        self.assertIn("boot", result["detail"].lower())
        self.assert_released()

    def test_nonzero_exit_is_preserved_with_boot_ids_and_card_minutes(self):
        self.transport.status = 23
        result = self.run_card()
        self.assert_result(result, "program", 23, seconds=12.0, program_status=23)
        names = self.names()
        self.assertIn("snapshot", names[names.index("stage") + 1:names.index("execute")])
        self.assertIn("snapshot", names[names.index("execute") + 1:names.index("cleanup")])
        self.assertNotIn("signal_owned", names)
        self.assert_cleaned()

    def test_partial_staging_failure_cleans_owned_directory_and_releases_lock(self):
        self.transport.stage_failure = True
        result = self.run_card()
        self.assert_result(result, "infrastructure", self.runner["INFRA_EXIT"])
        self.assertNotIn("execute", self.names())
        self.assertNotIn("signal_owned", self.names())
        self.assertIn("snapshot", self.names()[self.names().index("stage") + 1:
                                               self.names().index("cleanup")])
        self.assert_cleaned()


if __name__ == "__main__":
    unittest.main()
