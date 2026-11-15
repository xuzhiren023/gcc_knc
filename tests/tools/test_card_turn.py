"""S12-36: turn reservations keep a multi-job window; fake card only."""
from datetime import datetime, timedelta, timezone
import unittest
from unittest import mock

import test_card_run as fixtures


class CardTurn(unittest.TestCase):
    setUp = fixtures.CardRun.setUp
    other_start = fixtures.CardRun.other_start
    queued_other = fixtures.CardRun.queued_other
    advance = fixtures.CardRun.advance
    ledger_rows = fixtures.CardRun.ledger_rows
    names = fixtures.CardRun.names

    def run_card(self, **options):
        with mock.patch.dict("os.environ", {"USERNAME": "fixture", "PM_ROLE": "test"}):
            return fixtures.CardRun.run_card(self, **options)

    def turn_row(self):
        return self.other_start(
            project="gcc-knc", event="queued", jobId="claude-turn-s12-36", cores=[],
            queuedTime=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())

    def test_open_turn_keeps_benchmark_window(self):
        turn = self.turn_row()
        self.queued_other()
        self.other_start(project="gcc-knc", event="finish", jobId="last-timed")
        with mock.patch("time.sleep", self.advance):
            result = self.run_card(benchmark=True)
        self.assertEqual(result["result_class"], "program", result["detail"])
        self.assertIn("execute", self.names())
        self.assertEqual(self.transport.now, 12.0, "start without waiting for the foreign queue")
        self.assertIn(turn["jobId"], self.runner["active_jobs"](self.ledger_rows()))

    def test_closed_turn_resumes_round_robin(self):
        turn = self.turn_row()
        self.queued_other()
        self.other_start(**dict(turn, event="finish"))
        with mock.patch("time.sleep", self.advance):
            result = self.run_card(benchmark=True)
        self.assertEqual(result["result_class"], "refused")
        self.assertIn("their turn", result["detail"])
        self.assertNotIn("stage", self.names())

    test_round_robin_yields_to_other_project = fixtures.CardRun.test_round_robin_yields_to_other_project


if __name__ == "__main__":
    unittest.main()
