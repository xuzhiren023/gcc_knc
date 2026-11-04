"""S2-11 RED: shared-card policy, entirely fake transport, never SSH.

Snapshot adds raw cpuinfo/meminfo and a pinning capability. Execute receives
cpus (logical CPU IDs) and memory_mb (an enforced address-space limit). The CLI
reads ledger and memoryMB from its config. BusyBox replacement tests are in test_card_backend.py, using the
owner-reported tool availability; none of these tests connects to the card.
"""
import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
BOOT = "00000000-0000-0000-0000-000000000001"
REBOOT = "00000000-0000-0000-0000-000000000002"
FOREIGN = dict(pid=42, ppid=1, name="wrf", exe="/other/wrf", cwd="/other")
# Deliberately scrambled IDs and multiple logical CPUs per physical core.
CPUINFO = "\n\n".join(
    "processor : %d\nphysical id : 0\ncore id : %d" % pair
    for pair in ((7, 60), (91, 40), (2, 39), (13, 59), (4, 40), (88, 0))) + "\n"


class SharedTransport:
    def __init__(self):
        self.events = []
        self.boot = BOOT
        self.cpuinfo = CPUINFO
        self.free_kb = [4_000_000]
        self.pinning = True
        self.stage_failure = False
        self.reboot = False
        self.unreachable = False
        self.timed_out = False
        self.status = 0
        self.processes = []
        self.now = 0.0
        self.ledger = None
        self.run_dir = None
        self.observed_at_execute = []
        self.on_wait = None

    def connect(self, run_dir, *, timeout):
        self.events.append(("connect", run_dir))
        if self.unreachable:
            raise ConnectionError("card unreachable on reconnect")
        self.run_dir = run_dir
        return self

    def snapshot(self, *, timeout, include_cpuinfo=True):
        self.events.append(("snapshot",))
        if self.unreachable:
            raise ConnectionError("card unreachable mid-run")
        free = self.free_kb[0]
        if len(self.free_kb) > 1:
            self.free_kb.pop(0)
        return dict(boot_id=self.boot, processes=self.processes,
                    cpuinfo=self.cpuinfo if include_cpuinfo else "",
                    meminfo="MemTotal: 16000000 kB\nMemFree: %d kB\n" % free,
                    pinning=self.pinning)

    def stage(self, run_dir, program, *, timeout, files=()):
        self.events.append(("stage", run_dir))
        self.staged_files = list(files)
        if self.stage_failure:
            raise OSError("partial staging failure")

    def reap_stale(self, boot_id, *, timeout):
        self._guard(self.run_dir, boot_id)
        self.events.append(("reap_stale", boot_id))
        return dict(reaped=[], stale_kept=[])

    def execute(self, run_dir, argv, *, timeout, card_timeout, cpus=None, memory_mb=None):
        self.events.append(("execute", run_dir, cpus, memory_mb))
        self.observed_at_execute = self.read_ledger()
        self.now += 12
        if self.reboot:
            self.boot = REBOOT
        if self.unreachable == "execute":
            raise OSError("card unreachable mid-run")
        if self.timed_out:
            raise TimeoutError("program deadline")
        return self.status

    def signal_owned(self, run_dir, boot_id, *, timeout):
        self._guard(run_dir, boot_id)
        self.events.append(("signal_owned", run_dir))

    def cleanup(self, run_dir, boot_id, *, timeout):
        self._guard(run_dir, boot_id)
        self.events.append(("cleanup", run_dir))

    def _guard(self, run_dir, boot_id):
        if run_dir != self.run_dir or boot_id != self.boot or self.unreachable:
            raise AssertionError("unsafe cleanup/signalling")

    def close(self):
        self.events.append(("close",))

    def read_ledger(self):
        return [json.loads(line) for line in self.ledger.read_text(encoding="utf8").splitlines()]

    def wait(self, seconds):
        self.events.append(("wait", seconds))
        self.now += seconds
        if self.on_wait:
            self.on_wait()
        if sum(e[0] == "wait" for e in self.events) > 3:
            raise OSError("fake wait budget exhausted")


class SharedCardRules(unittest.TestCase):
    def setUp(self):
        self.runner = runpy.run_path(str(ROOT / "tools/card_run"))
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.receipts = self.directory / ".work/_state/card"
        receipt_patch = mock.patch.dict(self.runner["run"].__globals__, RECEIPT_DIR=self.receipts)
        receipt_patch.start()
        self.addCleanup(receipt_patch.stop)
        self.program = self.directory / "hello.mic"
        self.program.write_bytes(b"fake program; never executed")
        self.ledger = self.directory / "jobs.jsonl"
        self.ledger.write_text("", encoding="utf8")
        self.result_path = self.directory / "result.json"
        self.config_path = self.directory / "card.local.json"
        self.config = dict(host="fake", identity="fake", knownHosts="fake",
                           ledger=str(self.ledger), ownLock=str(self.directory / "card.lock"),
                           memoryMB=128, timeout=30, transportTimeout=1)
        self.transport = SharedTransport()
        self.transport.ledger = self.ledger

    def invoke(self, *, default_root=None, files=(), receipt=True):
        if default_root is not None:
            self.config["ownLock"] = str(default_root / "card.lock")
        self.config_path.write_text(json.dumps(self.config), encoding="utf8")
        args = ["card_run"]
        if receipt:
            args += ["--receipt", str(self.result_path)]
        if default_root is None:
            args += ["--config", str(self.config_path)]
        for path in files:
            args += ["--file", str(path)]
        args += [str(self.program)]
        stdout, stderr = io.StringIO(), io.StringIO()
        actual_run = self.runner["run"]

        def clocked_run(*args, **kwargs):
            kwargs["monotonic"] = lambda: self.transport.now
            return actual_run(*args, **kwargs)
        replacements = dict(SSHTransport=mock.Mock(return_value=self.transport), run=clocked_run)
        if default_root is not None:
            replacements["ROOT"] = default_root
        with mock.patch.dict(self.runner["main"].__globals__, replacements), \
                mock.patch("sys.argv", args), \
                mock.patch.object(self.runner["time"], "sleep", self.transport.wait), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = self.runner["main"]()
        self.diagnostic = stderr.getvalue()
        self.code = code
        if self.result_path.exists():
            return json.loads(self.result_path.read_text(encoding="utf8"))
        if stdout.getvalue():
            return json.loads(stdout.getvalue())
        return {}

    def events(self, name):
        return [e for e in self.transport.events if e[0] == name]

    def own_lines(self):
        return [line for line in self.transport.read_ledger() if line.get("agent") == "claude"]

    def test_final_snapshot_race_preserves_program_result_and_notes_skip(self):
        parser = object.__new__(self.runner["SSHSession"])
        parser.boot_id = None
        snapshots = 0

        def snapshot(*, timeout, include_cpuinfo=True):
            nonlocal snapshots
            snapshots += 1
            parser.run_dir = self.transport.run_dir
            raw = ("BOOT\t%s\nCPU\tprocessor : 91\nCPU\tcore id : 40\n"
                   "MEM\tMemFree: 4000000 kB\n" % BOOT).encode()
            if snapshots == 3:  # After execute returned its matched result.
                raw += b"PROC\t43\t1\tending\nPROC\t42\t1\tforeign\t/bin/sh\t/other\n"
            parser.rpc = mock.Mock(return_value=raw)
            return parser.snapshot(timeout=timeout, include_cpuinfo=include_cpuinfo)

        self.transport.snapshot = snapshot
        result = self.invoke()
        self.assertEqual((result["result_class"], result["exit_code"]), ("program", 0))
        self.assertIn("43", str(result["skipped_processes"]))
        self.assertEqual([p["pid"] for p in result["foreign_processes"]], ["42"])

    def test_extra_files_refused_before_connection_or_admission(self):
        extra = self.directory / "batch.mic"
        extra.write_bytes(b"batch")
        other = self.directory / "other"
        other.mkdir()
        duplicate = other / extra.name
        duplicate.write_bytes(b"duplicate basename")
        reserved = self.directory / "claude-program"
        reserved.write_bytes(b"must not replace driver")
        self.config["maxStageMiB"] = 1
        with self.program.open("wb") as stream:
            stream.truncate(1024 * 1024)
        for files in ([extra, duplicate], [self.directory / ".."], [reserved], [extra]):
            with self.subTest(files=files):
                result = self.invoke(files=files)
                self.assertEqual(result.get("result_class"), "refused", self.diagnostic)
                self.assertEqual(self.transport.events, [])
                self.assertEqual(self.ledger.read_text(), "")
        self.program.write_bytes(b"driver")
        self.transport.stage_overhead = lambda: 1024 * 1024
        result = self.invoke()
        self.assertEqual(result.get("result_class"), "refused", self.diagnostic)
        self.assertEqual(self.transport.events, [])
        del self.transport.stage_overhead
        data = self.directory / "input"
        data.write_bytes(b"data")
        result = self.invoke(files=[extra, data])
        self.assertEqual(result.get("result_class"), "program", self.diagnostic)
        self.assertEqual(self.transport.staged_files, [extra, data])

    def test_worktree_default_uses_main_config_without_copy(self):
        main = self.directory / "project"
        worktree = main / ".work/S2-11"
        worktree.mkdir(parents=True)
        (main / "config").mkdir()
        self.config_path = main / "config/card.local.json"
        result = self.invoke(default_root=worktree)
        self.assertEqual(self.code, 0, self.diagnostic)
        self.assertEqual(result["program_exit_code"], 0)
        self.assertFalse((worktree / "config/card.local.json").exists())

    def test_foreign_process_is_reported_and_job_runs(self):
        self.transport.processes = [FOREIGN]
        result = self.invoke()
        self.assertEqual(result["result_class"], "program")
        self.assertIn("foreign_processes", result)
        self.assertIn(FOREIGN, result["foreign_processes"])
        self.assertEqual(len(self.events("execute")), 1)
        self.assertFalse(self.events("signal_owned"))

    def test_old_external_lock_does_not_block_shared_work(self):
        external = self.directory / "old-workload.lock"
        external.write_text("other project's lock", encoding="utf8")
        self.config["externalLocks"] = [str(external)]
        result = self.invoke()
        self.assertEqual(result["program_exit_code"], 0)
        self.assertEqual(external.read_text(encoding="utf8"), "other project's lock")

    def test_start_precedes_execute_and_end_is_appended(self):
        seed = '{"agent":"other","jobId":"other-job","event":"finish"}\n'
        self.ledger.write_text(seed, encoding="utf8")
        result = self.invoke()
        lines = self.own_lines()
        self.assertEqual([line["event"] for line in lines], ["start", "finish"])
        start, end = lines
        self.assertTrue(start["jobId"].startswith("claude-"))
        self.assertEqual(end["jobId"], start["jobId"])
        self.assertEqual(set(start["cores"]), {40, 59})
        self.assertEqual(start["memoryLimitMiB"], 128)
        self.assertTrue(start["startTime"])
        self.assertTrue(start["expectedEnd"])
        self.assertEqual(start["logicalCpus"], [4, 13, 91])
        self.assertFalse(end["timingValid"])
        self.assertEqual(end["outcome"], "success")
        self.assertTrue(end["endTime"])
        self.assertIn(start, self.transport.observed_at_execute)
        self.assertNotIn(end, self.transport.observed_at_execute)
        self.assertTrue(self.ledger.read_text(encoding="utf8").startswith(seed))
        self.assertEqual(result["program_exit_code"], 0)

    def test_end_is_written_after_program_or_staging_failure_or_timeout(self):
        for mode in ("program", "stage", "timeout"):
            with self.subTest(mode=mode):
                self.transport = SharedTransport()
                self.transport.ledger = self.ledger
                self.transport.status = 23 if mode == "program" else 0
                self.transport.stage_failure = mode == "stage"
                self.transport.timed_out = mode == "timeout"
                before = len(self.own_lines())
                self.invoke()
                lines = self.own_lines()[before:]
                self.assertEqual([line["event"] for line in lines], ["start", "finish"])
                self.assertEqual(lines[0]["jobId"], lines[1]["jobId"])
                self.assertEqual(len(self.events("cleanup")), 1)

    def test_cpu_ids_come_from_core_ids_never_os_core(self):
        self.invoke()
        execute = self.events("execute")
        self.assertEqual(len(execute), 1)
        self.assertIsNotNone(execute[0][2], "execution must receive an enforced CPU binding")
        self.assertEqual(set(execute[0][2]), {91, 13, 4})
        self.assertNotIn(7, execute[0][2])

    def test_missing_pinning_or_no_eligible_cores_refuses(self):
        for missing in ("pinning", "cores"):
            with self.subTest(missing=missing):
                self.transport = SharedTransport()
                self.transport.ledger = self.ledger
                if missing == "pinning":
                    self.transport.pinning = False
                else:
                    self.transport.cpuinfo = "processor : 7\ncore id : 60\n"
                result = self.invoke()
                self.assertEqual(result["result_class"], "refused")
                self.assertFalse(self.events("execute"))
                self.assertRegex(result["detail"].lower(), "pin|cpu|core")

    def test_declared_memory_is_passed_to_enforced_execution(self):
        self.config["memoryMB"] = 256
        self.invoke()
        self.assertEqual(len(self.events("execute")), 1)
        self.assertEqual(self.events("execute")[0][3], 256)

    def test_single_job_above_total_memory_budget_refuses(self):
        self.config["memoryMB"] = 8192
        result = self.invoke()
        self.assertEqual(result["result_class"], "refused")
        self.assertFalse(self.events("execute"))

    def test_missing_ledger_fails_before_any_card_access(self):
        del self.config["ledger"]
        result = self.invoke()
        self.assertEqual(self.code, self.runner["INFRA_EXIT"])
        self.assertFalse(self.transport.events)
        self.assertIn("ledger", (self.diagnostic + result.get("detail", "")).lower())

    def test_default_memory_budget_is_small_and_positive(self):
        del self.config["memoryMB"]
        self.invoke()
        self.assertEqual(len(self.events("execute")), 1)
        limit = self.events("execute")[0][3]
        self.assertIsInstance(limit, (int, float))
        self.assertGreater(limit, 0)
        self.assertLessEqual(limit, 256)

    def test_low_free_memory_waits_before_staging(self):
        self.transport.free_kb = [1_000_000, 4_000_000]
        self.invoke()
        names = [e[0] for e in self.transport.events]
        self.assertIn("wait", names)
        self.assertLess(names.index("wait"), names.index("stage"))
        self.assertEqual(len(self.events("execute")), 1)

    def test_aggregate_reservations_wait_and_reread_ledger(self):
        active = dict(agent="claude", jobId="claude-existing", event="start",
                      memoryLimitMiB=6600, cores=[31], startTime="2099-01-01T00:00:00Z",
                      expectedEnd="2099-01-01T00:01:00Z")
        self.ledger.write_text(json.dumps(active) + "\n", encoding="utf8")
        self.config["memoryMB"] = 1024

        def finish_existing():
            with self.ledger.open("a", encoding="utf8") as stream:
                stream.write(json.dumps(dict(agent="claude", jobId="claude-existing",
                                             event="finish")) + "\n")
        self.transport.on_wait = finish_existing
        self.invoke()
        names = [e[0] for e in self.transport.events]
        self.assertIn("wait", names)
        self.assertLess(names.index("wait"), names.index("stage"))
        self.assertEqual(len(self.events("execute")), 1)

    def test_staging_and_cleanup_use_exact_claude_job_directory(self):
        self.invoke()
        self.assertEqual(len(self.events("stage")), 1)
        directory = self.events("stage")[0][1]
        self.assertRegex(directory, r"^/tmp/claude/claude-[A-Za-z0-9-]+$")
        self.assertEqual(self.events("cleanup"), [("cleanup", directory)])

    def test_boot_change_or_link_loss_appends_fault_and_end_without_cleanup(self):
        for fault in ("reboot", "link"):
            with self.subTest(fault=fault):
                self.transport = SharedTransport()
                self.transport.ledger = self.ledger
                self.transport.reboot = fault == "reboot"
                # S2-11 confirms a link fault only if the cleanup reconnect fails.
                # Break only after admission, when execute is entered.
                if fault == "link":
                    original = self.transport.execute

                    def break_link(*args, **kwargs):
                        self.transport.unreachable = "execute"
                        return original(*args, **kwargs)
                    self.transport.execute = break_link
                before = len(self.own_lines())
                result = self.invoke()
                self.assertEqual(result["result_class"], "infrastructure")
                self.assertEqual(result["exit_code"], self.runner["INFRA_EXIT"])
                lines = self.own_lines()[before:]
                self.assertEqual(sum(line["event"] == "card-fault" for line in lines), 1)
                self.assertEqual(lines[-1]["event"], "finish")
                self.assertFalse(self.events("cleanup"))
                self.assertFalse(self.events("signal_owned"))

    def test_overlap_includes_jobs_starting_during_execution(self):
        initial = dict(agent="other", jobId="other-first", event="start")
        self.ledger.write_text(json.dumps(initial) + "\n", encoding="utf8")
        original = self.transport.execute

        def overlap(*args, **kwargs):
            with self.ledger.open("a", encoding="utf8") as stream:
                stream.write(json.dumps(dict(agent="other", jobId="other-late", event="start")) + "\n")
                stream.write(json.dumps(dict(agent="other", jobId="other-late", event="finish")) + "\n")
            return original(*args, **kwargs)
        self.transport.execute = overlap
        result = self.invoke()
        self.assertIn("overlapping_jobs", result)
        self.assertEqual(set(result["overlapping_jobs"]), {"other-first", "other-late"})

    def test_gpt61_ledger_schema_tracks_finished_active_and_late_jobs(self):
        # Real other-agent field names from the owner's 11:02 report.
        start = dict(agent="gpt61", event="start", jobId="gpt61-complete",
                     cores=[0, 29], logicalCpus=[0, 116], memoryLimitMiB=512,
                     startTime="2026-11-03T10:00:00Z", expectedEnd="2026-11-03T10:01:00Z",
                     timingValid=False)
        finish = dict(start, event="finish", endTime="2026-11-03T10:01:00Z", outcome="success")
        active = dict(start, jobId="gpt61-active")
        seed = "".join(json.dumps(line) + "\n" for line in (start, finish, active))
        self.ledger.write_text(seed, encoding="utf8")
        original = self.transport.execute

        def overlap(*args, **kwargs):
            with self.ledger.open("a", encoding="utf8") as stream:
                for line in (dict(start, jobId="gpt61-late"), dict(finish, jobId="gpt61-late")):
                    stream.write(json.dumps(line) + "\n")
            return original(*args, **kwargs)
        self.transport.execute = overlap
        result = self.invoke()
        self.assertEqual(result["result_class"], "program", result)
        self.assertEqual(set(result["overlapping_jobs"]), {"gpt61-active", "gpt61-late"})
        self.assertTrue(self.ledger.read_text(encoding="utf8").startswith(seed))

    def test_success_result_has_boot_ids_and_card_minutes(self):
        result = self.invoke()
        self.assertEqual(result["program_exit_code"], 0)
        self.assertEqual(result["boot_id_before"], BOOT)
        self.assertEqual(result["boot_id_after"], BOOT)
        self.assertAlmostEqual(result["card_minutes"], 0.2)

    def test_missing_required_tool_is_named(self):
        # S2-11 uses dd for binary output; od is no longer a required tool.
        # Execute the actual generated tool-check snippet with a fake shell
        # command lookup. All other RPCs are inert; no card connection occurs.
        sh = shutil.which("sh")
        self.assertIsNotNone(sh, "POSIX sh must be on PATH")
        scripts = []

        class ToolCheckSession:
            def __init__(self, *args):
                pass

            def rpc(self, script, timeout, **kwargs):
                scripts.append(script)
                if "command -v" in script:
                    fake_lookup = 'command() { [ "$2" != "dd" ]; }\n'
                    answer = subprocess.run([sh, "-c", fake_lookup + script],
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    if answer.returncode:
                        raise OSError("remote status %d: %s" %
                                      (answer.returncode, answer.stdout.decode("utf8", "replace")))
                return b""

            def close(self):
                pass

        with mock.patch.dict(self.runner["SSHTransport"].connect.__globals__,
                             SSHSession=ToolCheckSession,
                             RUN_DIR=mock.Mock(fullmatch=mock.Mock(return_value=True))):
            with self.assertRaisesRegex(OSError, "dd"):
                self.runner["SSHTransport"](self.config, 1).connect(
                    "/tmp/claude/claude-" + "a" * 32, timeout=1)
        self.assertTrue(any("command -v" in script for script in scripts))


if __name__ == "__main__":
    unittest.main()
