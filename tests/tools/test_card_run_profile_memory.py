"""S11-29: profile memory is process-tree usage, never virtual reservations.

All transport operations are fake: these tests never connect to a card.
"""
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest import mock

import test_card_run as fixtures


ROOT = Path(__file__).resolve().parents[2]


class MemoryCard(fixtures.FakeTransport):
    def __init__(self):
        super().__init__()
        self.peak_resident_kib = 900 * 1024
        self.swap_kib = 0

    def snapshot(self, **kwargs):
        result = super().snapshot(**kwargs)
        result["meminfo"] = "MemFree: 16000000 kB\n"
        return result

    def execute(self, *args, **kwargs):
        status = super().execute(*args, **kwargs)
        # The card-side reader reports the simultaneous sum over the job tree.
        self.memory_report = dict(peak_resident_kib=self.peak_resident_kib,
                                 peak_memory_kib=self.peak_resident_kib + self.swap_kib)
        return status


class ProfileMemory(unittest.TestCase):
    def setUp(self):
        self.runner = runpy.run_path(str(ROOT / "tools/card_run"))
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.program = self.directory / "program.mic"
        self.program.write_bytes(b"fake; never executed")
        self.ledger = self.directory / "jobs.jsonl"
        self.ledger.write_text("", encoding="utf8")
        self.receipt = self.directory / "result.json"
        self.card = MemoryCard()
        patch = mock.patch.dict(self.runner["run"].__globals__,
                                RECEIPT_DIR=self.directory / "receipts")
        patch.start()
        self.addCleanup(patch.stop)

    def run_card(self, **options):
        # Only fake transports may bypass the engineer guard in host fixtures.
        with mock.patch.dict("os.environ", {"USERNAME": "fixture", "PM_ROLE": "test"}):
            result = self.runner["run"](
                self.program, [], lock_path=self.directory / "card.lock",
                external_locks=[], baseline_names={"sshd"}, timeout=30,
                transport_timeout=1, receipt_path=self.receipt, transport=self.card,
                ledger_path=self.ledger, monotonic=self.card.monotonic, **options)
        self.assertEqual(result, json.loads(self.receipt.read_text(encoding="utf8")))
        return result

    def test_profile_receipts_record_limit_and_resident_peak(self):
        for profile, limit in (("3100", 5632), ("5100", 7680), ("7100", None), ("full", None)):
            with self.subTest(profile=profile):
                self.card = MemoryCard()
                result = self.run_card(profile=profile)
                self.assertEqual(result["result_class"], "program", result)
                self.assertEqual(result["profile_memory_limit_mib"], limit)
                self.assertEqual(result["peak_resident_kib"], 900 * 1024)
                self.assertEqual(result["peak_memory_kib"], 900 * 1024)

    def test_generated_monitor_uses_supported_delay_and_throttled_listing(self):
        source = (ROOT / "tools/card_run").read_text(encoding="utf8")
        start = source.index("PROFILE_START = r'''")
        end = source.index("'''", start + len("PROFILE_START = r'''"))
        monitor = source[start:end]
        self.assertNotRegex(monitor, r'(?<![A-Za-z0-9_])sleep\s+[0-9]+\.[0-9]+')

    def test_exceeding_tree_resident_limit_is_resource_with_peak_and_limit(self):
        self.card.peak_resident_kib = 6 * 1024 * 1024
        result = self.run_card(profile="3100")
        self.assertEqual(result["result_class"], "resource", result)
        self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual(result["peak_resident_kib"], 6 * 1024 * 1024)
        self.assertEqual(result["profile_memory_limit_mib"], 5632)
        self.assertIn(str(6 * 1024 * 1024), result["detail"])
        self.assertIn(str(5632 * 1024), result["detail"])

    def test_swap_counts_toward_the_limit(self):
        self.card.peak_resident_kib = 5 * 1024 * 1024
        self.card.swap_kib = 1024 * 1024
        result = self.run_card(profile="3100")
        self.assertEqual(result["result_class"], "resource", result)
        self.assertEqual(result["peak_memory_kib"], 6 * 1024 * 1024)

    def test_full_and_exclusive_have_no_memory_failure(self):
        for options in ({"profile": "full"}, {}):
            with self.subTest(options=options):
                self.card = MemoryCard()
                self.card.peak_resident_kib = 6 * 1024 * 1024
                result = self.run_card(**options)
                self.assertEqual(result["result_class"], "program", result)
                self.assertEqual(result["exit_code"], 0)
                self.assertIsNone(result["memory_mb"])

    def test_real_ssh_launch_does_not_apply_profile_address_space_limit(self):
        # Exercise the real command builder with fake RPC and empty output.
        # start_job's third argument is passed directly to claude-pin's RLIMIT_AS.
        for profile, memory in (("3100", 5632), ("5100", 7680), ("full", None), (None, None)):
            with self.subTest(profile=profile):
                cls = self.runner["SSHSession"]
                session = cls.__new__(cls)
                session.run_dir = "/tmp/claude/claude-" + "a" * 32
                session.boot_id = fixtures.BOOT
                session.transport_timeout = 1
                session.profile = profile
                scripts = []

                def rpc(script, timeout, *, step):
                    scripts.append((step, script))
                    if step == "read-memory":
                        return b"921600 921600 2 0"
                    return b"0" if step == "read-status" else b""

                session.rpc = rpc
                session.read_output = lambda *args: b""
                session.execute(session.run_dir, [], timeout=30, card_timeout=35,
                                cpus=[0, 1], memory_mb=memory)
                launch = next(script for step, script in scripts if step == "start-job")
                self.assertIn("start_job 35 0,1 0 ", launch)

    def test_timeout_records_unreadable_memory_without_masking_deadline(self):
        session = self.runner["SSHSession"].__new__(self.runner["SSHSession"])
        session.run_dir = "/tmp/claude/claude-" + "a" * 32
        session.boot_id = fixtures.BOOT
        session.transport_timeout = 1
        session.profile = "3100"
        for error in (OSError("read-memory failed"), None):
            with self.subTest(error=error):
                session.rpc = mock.Mock(side_effect=[b"", error or b"malformed"])
                with mock.patch.object(self.runner["time"], "monotonic",
                                       side_effect=[0, 0, 31]):
                    with self.assertRaisesRegex(TimeoutError, "deadline exceeded"):
                        session.execute(session.run_dir, [], timeout=30, card_timeout=35,
                                        cpus=[1], memory_mb=5632)
                self.assertIn("memory_report_error", session.memory_report)


if __name__ == "__main__":
    unittest.main()
