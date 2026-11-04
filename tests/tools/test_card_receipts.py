"""S3-18: retained job diagnostics, using only the fake card."""
import json
import os
import unittest
from unittest import mock

import test_card_shared as shared


class CardReceipts(unittest.TestCase):
    setUp = shared.SharedCardRules.setUp
    invoke = shared.SharedCardRules.invoke

    def saved(self, result):
        path = self.receipts / (result["job_id"] + ".json")
        self.assertTrue(path.is_file(), "every job must leave its own receipt")
        return json.loads(path.read_text(encoding="utf8"))

    def test_refused_job_has_receipt_without_receipt_option(self):
        self.transport.pinning = False
        result = self.invoke(receipt=False)
        self.assertEqual(result["result_class"], "refused")
        self.assertIn("CPU pinning unavailable", result["detail"])
        self.assertEqual(self.saved(result), result)

    def test_success_has_receipt_without_receipt_option(self):
        result = self.invoke(receipt=False)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(self.saved(result), result)
        self.assertEqual(self.transport.read_ledger()[-1]["detail"], "")

    def test_finish_retains_bounded_refusal_and_failure_detail(self):
        detail = "staging diagnostic: " + "x" * 400
        for error, kind in ((self.runner["Refused"], "refused"), (OSError, "infrastructure")):
            with self.subTest(kind=kind), mock.patch.object(
                    self.transport, "stage", side_effect=error(detail)):
                result = self.invoke()
                self.assertEqual(result["result_class"], kind)
                self.assertEqual(result["detail"], detail)
                finish = self.transport.read_ledger()[-1]
                self.assertEqual(finish["event"], "finish")
                self.assertEqual(finish["detail"], detail[:300])
                self.assertEqual(self.saved(result), result)

    def test_receipts_keep_newest_200(self):
        self.receipts.mkdir(parents=True)
        paths = []
        for number in range(201):
            path = self.receipts / ("claude-%032x.json" % number)
            path.write_text("{}\n", encoding="utf8")
            os.utime(path, (number + 1, number + 1))
            paths.append(path)
        result = self.invoke(receipt=False)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(self.saved(result), result)
        self.assertEqual(set(self.receipts.iterdir()),
                         set(paths[2:] + [self.receipts / (result["job_id"] + ".json")]))


if __name__ == "__main__":
    unittest.main()
