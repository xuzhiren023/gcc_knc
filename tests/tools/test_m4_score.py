"""S11-14: executable contract for the proposed M4 scoring policy."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import m4_score


PROGRAMS = (
    "gemm", "atax", "cholesky", "ludcmp", "jacobi-2d", "heat-3d",
    "adi", "durbin", "stream", "npb-cg", "npb-ep", "npb-mg", "npb-is",
    "hpcg", "zlib", "sqlite", "bzip2",
)
MODELS = ("7120", "3100", "5100")


def corpus(speedup):
    # Six independent pairs allow exactly balanced AB/BA launch order.
    return {name: [(speedup, 1.0)] * 6 for name in PROGRAMS}


class M4ScoreContract(unittest.TestCase):
    def test_pair_ratios_precede_program_median(self):
        pairs = [(10, 5), (100, 100), (9, 3), (6, 2), (30, 10), (12, 4)]
        result = m4_score.score_program(pairs)
        self.assertEqual(result["pair_speedups"], [2, 1, 3, 3, 3, 3])
        self.assertEqual(result["speedup"], 3)
        self.assertAlmostEqual(result["time_ratio"], 1 / 3)

    def test_one_program_one_vote_and_no_missing_rows(self):
        rows = corpus(1)
        for name in PROGRAMS[:9]:
            rows[name] = [(2, 1)] * 6
        result = m4_score.score_model(rows)
        self.assertEqual(result["median_speedup"], 2)
        self.assertTrue(result["pass"])
        del rows["hpcg"]
        with self.assertRaises(ValueError):
            m4_score.score_model(rows)

    def test_fixed_seed_bootstrap_bounds(self):
        # Nonconstant pairs: the percentile endpoints are 1 and 2;
        # resampling individual times would introduce spurious ratios.
        pairs = [(1, 1), (10, 10), (100, 100), (2, 1), (20, 10), (200, 100)]
        result = m4_score.score_program(pairs, seed=1514, draws=10000)
        self.assertEqual(result["speedup"], 1.5)
        self.assertEqual(result["speedup_ci95"], [1, 2])
        model = m4_score.score_model(corpus(1.25), seed=1514, draws=10000)
        self.assertEqual(model["lower95"], 1.25)
        self.assertTrue(model["pass"])

    def test_regression_is_strictly_more_than_five_percent(self):
        self.assertEqual(m4_score.regression_status(1.05, 1.05), "clear")
        self.assertEqual(m4_score.regression_status(1.05001, 1.06), "regression")
        self.assertEqual(m4_score.regression_status(1.04, 1.06), "unresolved")
        self.assertEqual(m4_score.regression_status(1.05, 1.06), "unresolved")
        # A speedup of .951 is a >5% time regression, despite exceeding .95.
        result = m4_score.score_program([(0.951, 1)] * 6)
        self.assertEqual(result["regression"], "regression")

    def test_regression_review_is_required_even_when_median_passes(self):
        rows = corpus(2)
        rows["zlib"] = [(1, 1.1)] * 6
        self.assertFalse(m4_score.score_model(rows)["pass"])
        result = m4_score.score_model(
            rows, known_causes={"zlib": "lead-reviewed cause: diagnostic ticket reference"}
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["programs"]["zlib"]["regression"], "regression")

    def test_every_model_must_pass(self):
        rows = {model: corpus(1.25) for model in MODELS}
        self.assertTrue(m4_score.score_models(rows)["pass"])
        rows["5100"] = corpus(1.24)
        result = m4_score.score_models(rows)
        self.assertFalse(result["pass"])
        self.assertFalse(result["models"]["5100"]["pass"])
        del rows["5100"]
        with self.assertRaises(ValueError):
            m4_score.score_models(rows)

    def test_invalid_or_insufficient_times_cannot_be_scored(self):
        for bad in (0, -1, float("nan"), float("inf")):
            with self.subTest(time=bad), self.assertRaises(ValueError):
                m4_score.score_program([(bad, 1)] * 6)
        with self.assertRaises(ValueError):
            m4_score.score_program([(1, 1)] * 4)

    def test_held_out_details_only_go_to_sealed_output(self):
        # The runner/lead provisions the real directory with access controls.
        # This tests routing and redaction, not Windows ACL enforcement.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sealed = root / "m4-sealed"
            sealed.mkdir()
            report = {"timings": [123], "profiles": "private", "diagnostic": "private"}
            with patch.object(m4_score, "SEALED_ROOT", sealed):
                for path in (root / "public.json", sealed / ".." / "leak.json",
                             root / "m4-sealed-lookalike" / "leak.json"):
                    with self.subTest(path=path), self.assertRaises(ValueError):
                        m4_score.write_report(report, path, held_out=True,
                                              ready=True, passed=False)
                    self.assertFalse(path.exists())
                destination = sealed / "results.json"
                public = m4_score.write_report(report, destination, held_out=True,
                                              ready=True, passed=False)
                self.assertEqual(public, {"ready": True, "pass": False})
                self.assertEqual(json.loads(destination.read_text()), report)


if __name__ == "__main__":
    unittest.main()
