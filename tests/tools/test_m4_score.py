"""S11-14: executable contract for the proposed M4 scoring policy."""

from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import m4_score


PROGRAMS = (
    "PB-gemm", "PB-atax", "PB-cholesky", "PB-ludcmp", "PB-jacobi-2d", "PB-heat-3d",
    "PB-adi", "PB-durbin", "STREAM", "NPB-CG", "NPB-EP", "NPB-MG", "NPB-IS",
    "HPCG", "zlib", "SQLite", "bzip2",
)
MODELS = ("7120", "3100", "5100")


def primary_spec():
    # Synthetic pilot evidence; this is not a claim about donor build results.
    return m4_score.freeze_primary_spec({
        "-O3": {"assembled": False, "diagnostic": "kmov operand-size mismatch"},
        "-O2": {"assembled": False, "diagnostic": "kmov operand-size mismatch"},
        "-O1": {"assembled": True, "diagnostic": ""},
        "-O0": {"assembled": True, "diagnostic": ""},
    })


def corpus(speedup):
    # Six independent pairs allow exactly balanced AB/BA launch order.
    return {name: {"pairs": [(speedup, 1.0)] * 6,
                   "primary": asdict(primary_spec()[name])} for name in PROGRAMS}


def score_model(rows, **kwargs):
    return m4_score.score_model(rows, primary_spec=primary_spec(), **kwargs)


def score_models(rows, **kwargs):
    return m4_score.score_models(rows, primary_spec=primary_spec(), **kwargs)


class M4ScoreContract(unittest.TestCase):
    def test_primary_spec_freezes_owner_exceptions_and_rejects_mismatches(self):
        specs = primary_spec()
        self.assertEqual(set(specs), set(PROGRAMS))
        for spec in specs.values():
            self.assertEqual(spec.build_mode, "serial")
            self.assertEqual(spec.workers, 1)
            self.assertEqual(spec.new_flags, ("-O2", "-march=knc"))
        self.assertEqual(specs["SQLite"].donor_flags, ("-O1",))
        self.assertIn("kmov", specs["SQLite"].donor_diagnostic)
        self.assertEqual(specs["HPCG"].source_fix, "default(none): add n to shared list; both compilers")
        self.assertEqual(specs["STREAM"].donor_flags, ("-O2",))
        with self.assertRaises(TypeError):
            specs["SQLite"] = specs["STREAM"]
        for name, field, value in (
            ("STREAM", "build_mode", "openmp"),
            ("STREAM", "workers", 240),
            ("NPB-CG", "donor_flags", ("-O2", "-fopenmp")),
            ("NPB-MG", "new_flags", ("-O2", "-march=knc", "-fopenmp")),
            ("zlib", "new_flags", ("-O3", "-march=knc")),
            ("SQLite", "donor_flags", ("-O2",)),
            ("SQLite", "donor_diagnostic", ""),
            ("HPCG", "source_fix", "unchanged"),
        ):
            with self.subTest(program=name, field=field):
                rows = corpus(2)
                rows[name]["primary"][field] = value
                with self.assertRaises(ValueError):
                    score_model(rows)
        rows = corpus(2)
        del rows["STREAM"]["primary"]
        with self.assertRaises(ValueError):
            score_model(rows)
        result = score_model(corpus(2))
        self.assertEqual(result["programs"]["SQLite"]["primary"], asdict(specs["SQLite"]))

    def test_sqlite_level_is_highest_assembling_pilot_level(self):
        pilot = {level: {"assembled": False, "diagnostic": "kmov operand-size mismatch"}
                 for level in ("-O3", "-O2", "-O1", "-O0")}
        with self.assertRaises(ValueError):
            m4_score.freeze_primary_spec(pilot)
        for level in ("-O0", "-O1", "-O2", "-O3"):
            pilot[level] = {"assembled": True, "diagnostic": ""}
            self.assertEqual(m4_score.freeze_primary_spec(pilot)["SQLite"].donor_flags, (level,))
        del pilot["-O3"]
        with self.assertRaises(ValueError):
            m4_score.freeze_primary_spec(pilot)

    def test_openmp_panel_cannot_enter_primary_median(self):
        rows = corpus(1)
        self.assertEqual(score_model(rows)["median_speedup"], 1)
        for name in ("STREAM", "NPB-CG", "NPB-EP", "NPB-MG", "NPB-IS", "HPCG"):
            rows[name + ":openmp"] = {"pairs": [(100, 1)] * 6,
                                      "label": "the donor toolchain has no OpenMP runtime"}
        with self.assertRaises(ValueError):
            score_model(rows)

    def test_pair_ratios_precede_program_median(self):
        pairs = [(10, 5), (100, 100), (9, 3), (6, 2), (30, 10), (12, 4)]
        result = m4_score.score_program(pairs)
        self.assertEqual(result["pair_speedups"], [2, 1, 3, 3, 3, 3])
        self.assertEqual(result["speedup"], 3)
        self.assertAlmostEqual(result["time_ratio"], 1 / 3)

    def test_one_program_one_vote_and_no_missing_rows(self):
        self.assertEqual(m4_score.PROGRAMS, PROGRAMS)
        rows = corpus(1)
        for name in PROGRAMS[:9]:
            rows[name]["pairs"] = [(2, 1)] * 6
        result = score_model(rows)
        self.assertEqual(result["median_speedup"], 2)
        self.assertTrue(result["pass"])
        del rows["HPCG"]
        with self.assertRaises(ValueError):
            score_model(rows)

    def test_fixed_seed_bootstrap_bounds(self):
        # Nonconstant pairs: the percentile endpoints are 1 and 2;
        # resampling individual times would introduce spurious ratios.
        pairs = [(1, 1), (10, 10), (100, 100), (2, 1), (20, 10), (200, 100)]
        result = m4_score.score_program(pairs, seed=1514, draws=10000)
        self.assertEqual(result["speedup"], 1.5)
        self.assertEqual(result["speedup_ci95"], [1, 2])
        model = score_model(corpus(1.25), seed=1514, draws=10000)
        self.assertEqual(model["lower95"], 1.25)
        self.assertTrue(model["pass"])
        noisy_rows = corpus(1)
        for row in noisy_rows.values():
            row["pairs"] = pairs
        noisy = score_model(noisy_rows,
                                     seed=1514, draws=10000)
        self.assertEqual(noisy["median_speedup"], 1.5)
        self.assertEqual(noisy["lower95"], 1)
        self.assertTrue(noisy["inconclusive"])
        self.assertFalse(noisy["pass"])

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
        rows["zlib"]["pairs"] = [(1, 1.1)] * 6
        self.assertFalse(score_model(rows)["pass"])
        result = score_model(
            rows, known_causes={"zlib": "lead-reviewed cause: diagnostic ticket reference"}
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["programs"]["zlib"]["regression"], "regression")
        rows["zlib"]["pairs"] = [(1, 1)] * 3 + [(1, 1.1)] * 3
        self.assertFalse(score_model(
            rows, known_causes={"zlib": "a cause cannot resolve an interval"}
        )["pass"])

    def test_every_model_must_pass(self):
        rows = {model: corpus(1.25) for model in MODELS}
        self.assertTrue(score_models(rows)["pass"])
        rows["5100"] = corpus(1.24)
        result = score_models(rows)
        self.assertFalse(result["pass"])
        self.assertFalse(result["models"]["5100"]["pass"])
        extended = {name: {**row, "pairs": row["pairs"] * 2}
                    for name, row in rows["5100"].items()}
        rows["5100"] = extended
        with self.assertRaises(ValueError):
            score_models(rows)
        del rows["5100"]
        with self.assertRaises(ValueError):
            score_models(rows)

    def test_invalid_or_insufficient_times_cannot_be_scored(self):
        for bad in (0, -1, float("nan"), float("inf")):
            with self.subTest(time=bad), self.assertRaises(ValueError):
                m4_score.score_program([(bad, 1)] * 6)
        with self.assertRaises(ValueError):
            m4_score.score_program([(1, 1)] * 4)

    def test_sealed_root_in_main_checkout_and_ticket_worktree(self):
        project = Path(__file__).resolve().parents[2]
        if project.parent.name == ".work":
            project = project.parent.parent
        expected = project / ".work" / "_shared" / "m4-sealed"
        for root in (project, project / ".work" / "S11-14"):
            with self.subTest(root=root):
                self.assertEqual(m4_score.sealed_root(root), expected)
        self.assertEqual(m4_score.SEALED_ROOT, expected)

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
                with self.assertRaises(ValueError):
                    m4_score.write_report({"held_out": True}, root / "public.json",
                                          held_out=False, ready=True, passed=True)


if __name__ == "__main__":
    unittest.main()
