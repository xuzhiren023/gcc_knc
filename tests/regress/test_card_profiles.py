"""S9-14: card_run model profiles and exclusive-turn budgets; fake transport, never the card."""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/tools"))
from test_card_shared import CPUINFO, SharedTransport  # noqa: E402

FREE_KB = 16_000_000  # 15625 MiB free, so free less the 1536 MiB margin is 14089 MiB.
OTHER = dict(agent="other", project="phiweather", jobId="wrf-1", event="start", cores=list(range(40)),
             memoryLimitMiB=7168, timingValid=False, startTime="2099-01-01T00:00:00Z")


class CardProfiles(unittest.TestCase):
    def setUp(self):
        self.runner = runpy.run_path(str(ROOT / "tools/card_run"))
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        for patch in (mock.patch.dict(self.runner["run"].__globals__, RECEIPT_DIR=self.directory / "receipts"),
                      mock.patch.dict(os.environ, {"PM_ROLE": "lead"})):
            patch.start()
            self.addCleanup(patch.stop)
        self.program = self.directory / "hello.mic"
        self.program.write_bytes(b"fake program; never executed")
        self.ledger = self.directory / "jobs.jsonl"
        self.ledger.write_text("", encoding="utf8")
        self.transport = SharedTransport()
        self.transport.ledger = self.ledger
        self.transport.free_kb = [FREE_KB]
        self.topology = self.runner["cpu_binding"](CPUINFO)

    def logical(self, cores):
        return sorted(cpu for cpu, core in self.topology.items() if core in cores)

    def run_card(self, timeout=30, **options):
        with mock.patch.object(self.runner["time"], "sleep", self.transport.wait):
            return self.runner["run"](self.program, [], lock_path=self.directory / "card.lock",
                                      external_locks=[], baseline_names=set(), timeout=timeout,
                                      transport_timeout=1, receipt_path=None, transport=self.transport,
                                      ledger_path=self.ledger, monotonic=lambda: self.transport.now,
                                      **options)

    def main(self, *options):
        config = self.directory / "card.json"
        config.write_text(json.dumps(dict(host="fake", identity="fake", knownHosts="fake",
                                          ledger=str(self.ledger), ownLock=str(self.directory / "card.lock"),
                                          timeout=30, transportTimeout=1)), encoding="utf8")
        argv = ["card_run", "--config", str(config), "--receipt", str(self.directory / "r.json"),
                *options, str(self.program)]
        stdout = io.StringIO()
        with mock.patch.dict(self.runner["main"].__globals__,
                             SSHTransport=mock.Mock(return_value=self.transport)), \
                mock.patch("sys.argv", argv), mock.patch.object(self.runner["time"], "sleep", self.transport.wait), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            self.runner["main"]()
        return json.loads(stdout.getvalue())

    def starts(self):
        return [row for row in self.transport.read_ledger() if row.get("event") == "start"
                and row.get("project") == "gcc-knc"]

    def test_each_profile_gives_its_cores_and_limit(self):
        for profile, cores, limit in (("3100", range(56), 5632), ("5100", range(59), 7680),
                                      ("7100", range(60), 14089), ("full", range(60), 14089)):
            with self.subTest(profile=profile):
                self.transport.events.clear()
                result = self.run_card(profile=profile)
                self.assertEqual(result["result_class"], "program", result["detail"])
                execute = [e for e in self.transport.events if e[0] == "execute"][-1]
                self.assertEqual(execute[2], self.logical(set(cores)))
                self.assertEqual(execute[3], limit)
                self.assertEqual(result["profile"], profile)
                self.assertEqual(self.starts()[-1]["profile"], profile)

    def test_benchmark_accepts_profile_cores_but_not_explicit_cores(self):
        result = self.main("--benchmark", "--profile", "3100")
        self.assertEqual(result["result_class"], "program", result["detail"])
        self.assertEqual(result["cpus"], self.logical(set(range(56))))
        start = self.starts()[-1]
        self.assertEqual((start["timingValid"], start["cores"]), (True, list(range(60))))
        result = self.main("--benchmark", "--cores", "0,1")
        self.assertEqual(result["result_class"], "refused")

    def test_budget_follows_exclusive_or_shared_turn(self):
        # Our exclusive turn: free memory less the margin, above the shared 10 GiB, and any cores.
        result = self.run_card(memory_mb=12288, threads=240)
        self.assertEqual(result["result_class"], "program", result["detail"])
        self.assertEqual(result["cpus"], self.logical(set(range(60))))
        # Another project's job running: the shared 10 GiB budget and its cores 0-39 are kept.
        self.ledger.write_text(json.dumps(OTHER) + "\n", encoding="utf8")
        self.transport.events.clear()
        result = self.run_card(memory_mb=12288, timeout=2)
        self.assertEqual(result["result_class"], "refused")
        self.assertIn("memory", result["detail"])
        self.transport.events.clear()
        result = self.run_card(memory_mb=2048, threads=80)
        self.assertEqual(result["result_class"], "program", result["detail"])
        self.assertEqual(result["cpus"], self.logical(set(range(40, 60))))


if __name__ == "__main__":
    unittest.main()
