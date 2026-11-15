"""End-to-end CLI tests: statuses, exit codes, result fields, compare rules, native export, analytic scales."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import helpers

KT = os.path.join(helpers.SCRIPTS, "knc_twin.py")


def run(*args):
    tmp = tempfile.mkdtemp(prefix="knc-twin-test-")
    out = os.path.join(tmp, "out")
    p = subprocess.run([sys.executable, KT] + list(args) + ["--out", out], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    res = None
    rp = os.path.join(out, "result.json")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as f:
            res = json.load(f)
    return p.returncode, res, out, p


class TestCLI(unittest.TestCase):
    def test_capabilities(self):
        code, res, out, p = run("capabilities")
        self.assertEqual(code, 0, p.stderr)
        caps = res["capabilities"]
        self.assertIn("card", caps["scales"])
        self.assertTrue(any(i["mnemonic"] == "vfmadd231ps" and i["functional"] for i in caps["instructions"]))
        self.assertTrue(os.path.exists(os.path.join(out, "capabilities.json")))

    def test_validate_and_result_fields(self):
        code, res, out, p = run("validate", helpers.fixture("saxpy_loop.json"))
        self.assertEqual(code, 0, p.stderr)
        for key in ("result_type", "status", "engine_version", "input", "invocation", "artifacts", "assumptions", "unsupported"):
            self.assertIn(key, res)
        self.assertEqual(res["input"]["kernel"]["representation"], "normalized-records")

    def test_simulate_fields_and_statuses(self):
        code, res, out, p = run("simulate", helpers.fixture("saxpy_loop.json"))
        self.assertEqual(code, 0, p.stderr)
        self.assertEqual(res["result_type"], "timing_prediction")
        self.assertEqual(res["functional_check"]["status"], "ok")
        self.assertEqual(res["profile"]["id"], "card-7120-measured")
        self.assertEqual(len(res["profile"]["hash"]), 64)
        self.assertEqual(len(res["input"]["hash_sha256"]), 64)
        self.assertIn("predicted_cycles", res["prediction"])
        self.assertIn("calibration_status", res)
        self.assertIn("imported_microbenchmarks", res["calibration_status"]["state"])
        self.assertTrue(res["limiting_constraints"])
        self.assertIsNotNone(res["python_execution_seconds"])
        self.assertTrue(os.path.exists(os.path.join(out, "summary.md")))

    def test_statuses_and_exit_codes(self):
        cases = [
            (("simulate", helpers.fixture("unknown_insn.json")), "unsupported", 3),
            (("simulate", helpers.fixture("vpermd_common_profile.json"), "--profile", "knc-common"), "missing_parameter", 4),
            (("simulate", helpers.fixture("saxpy_bad_candidate.json")), "functional_mismatch", 6),
            (("functional", helpers.fixture("saxpy_bad_candidate.json")), "functional_mismatch", 6),
            (("simulate", helpers.fixture("budget_long_loop.json"), "--max-cycles", "500"), "budget_exhausted", 5),
            (("simulate", helpers.fixture("budget_long_loop.json"), "--max-steps", "100"), "budget_exhausted", 5),
            (("bounds", "--scale", "card", "--params", helpers.fixture("card_params_readonly_missing.json")), "needs_parameters", 7),
            (("simulate", helpers.fixture("fence_unknown_param.json"), "--trace-source", "static"), "missing_parameter", 4),
        ]
        for args, status, code in cases:
            rc, res, out, p = run(*args)
            self.assertEqual(rc, code, (args, p.stdout, p.stderr))
            self.assertEqual(res["status"], status, args)
            self.assertIsNone(res.get("prediction"), "no prediction is reported with a non-ok status")
        rc, res, out, p = run("simulate", helpers.fixture("budget_long_loop.json"), "--max-cycles", "500")
        self.assertIn("partial", res)
        self.assertIn("NOT a completed result", res["partial"]["note"])

    def test_invalid_input(self):
        tmp = tempfile.mkdtemp()
        bad = os.path.join(tmp, "bad.json")
        with open(bad, "w") as f:
            f.write('{"schema": "knc-twin.kernel/1", "streams": [{"context": 0, "instructions": [{"op": "add", "ops": ["rax"]}]}]}')
        rc, res, out, p = run("validate", bad)
        self.assertEqual(rc, 2)
        self.assertEqual(res["status"], "invalid_input")

    def test_synthetic_profile_is_labeled(self):
        rc, res, out, p = run("simulate", helpers.fixture("saxpy_loop.json"), "--profile", "synthetic-demo")
        self.assertEqual(rc, 0)
        self.assertTrue(res["profile"]["synthetic"])
        self.assertIn("SYNTHETIC", res["message"])
        self.assertIn("SYNTHETIC", res["calibration_status"]["note"])

    def test_compare_rules(self):
        rc, a, out_a, _ = run("simulate", helpers.fixture("stream_cold_nopf.json"))
        rc, b, out_b, _ = run("simulate", helpers.fixture("stream_cold_pf.json"))
        rc, c, out_c, _ = run("simulate", helpers.fixture("stream_cold_pf.json"), "--profile", "synthetic-demo")
        rc, cmp_ok, out, p = run("compare", os.path.join(out_a, "result.json"), os.path.join(out_b, "result.json"))
        self.assertEqual(rc, 0, p.stderr)
        self.assertTrue(cmp_ok["prediction"]["compatible"])
        row = [m for m in cmp_ok["prediction"]["metrics"] if m["metric"] == "predicted_cycles_per_unit"][0]
        self.assertLess(row["ratio_candidate_over_baseline"], 0.5)
        rc, cmp_bad, out, p = run("compare", os.path.join(out_a, "result.json"), os.path.join(out_c, "result.json"))
        self.assertEqual(rc, 8)
        self.assertEqual(cmp_bad["status"], "incompatible")
        self.assertTrue(any("profile hash" in s for s in cmp_bad["incompatibilities"]))

    def test_bounds_loop_and_search(self):
        rc, res, out, p = run("bounds", helpers.fixture("reduce_1acc.json"), "--loop")
        self.assertEqual(rc, 0, p.stderr)
        self.assertEqual(res["result_type"], "analytical_bound")
        self.assertEqual(res["prediction"]["mii_cycles_per_iteration"], 4)
        rc, res, out, p = run("bounds", helpers.fixture("agi_gap1.json"), "--search")
        self.assertEqual(rc, 0, p.stderr)
        self.assertTrue(res["search"]["space_exhausted"])
        self.assertIn("proven optimum within the search space", res["search"]["claim"])

    def test_analytic_scales(self):
        rc, res, out, p = run("bounds", "--scale", "card", "--params", helpers.fixture("card_params_stream.json"))
        self.assertEqual(rc, 0, p.stderr)
        self.assertEqual(res["result_type"], "analytical_scenario_estimate")
        sc = res["prediction"]["scenarios"][0]
        self.assertEqual(sc["binding"], "memory")
        self.assertIn("not_an_estimate", res["prediction"])
        rc, res, out, p = run("bounds", "--scale", "card", "--params", helpers.fixture("card_params_readonly_sweep.json"))
        self.assertEqual(rc, 0, p.stderr)
        self.assertEqual(len(res["prediction"]["scenarios"]), 4)
        rc, res, out, p = run("bounds", "--scale", "pair", "--params", helpers.fixture("pair_params.json"))
        self.assertEqual(rc, 0, p.stderr)
        self.assertEqual(len(res["prediction"]["scenarios"]), 4)

    def test_prepare_and_import_native(self):
        rc, sim, out_sim, _ = run("simulate", helpers.fixture("saxpy_loop.json"))
        rc, res, out, p = run("prepare-native", helpers.fixture("saxpy_loop.json"), "--prediction", os.path.join(out_sim, "result.json"))
        self.assertEqual(rc, 0, p.stderr)
        for fn in ("request.json", "kernel.S", "driver.c", "README.md"):
            self.assertTrue(os.path.exists(os.path.join(out, fn)), fn)
        with open(os.path.join(out, "request.json")) as f:
            req = json.load(f)
        self.assertEqual(req["kernel_hash_sha256"], sim["input"]["hash_sha256"])
        asm = open(os.path.join(out, "kernel.S")).read()
        self.assertIn("vfmadd231ps %zmm0, %zmm2, %zmm1", asm)
        self.assertIn("jnz knc_twin_kernel_ctx0_L", asm)
        # a measurement answering the request
        meas = {"schema": "knc-twin.native-measurement/1", "request_hash_sha256": req["request_hash_sha256"], "job_id": "test-job-0001",
                "measured_utc": "2026-01-01T00:00:00Z", "card_profile": "card-7120-measured",
                "results": [{"threads_per_core": 1, "ticks_per_unit_per_thread": 20.0, "spread_pct": 0.5, "check": "ok"}],
                "parameters": [{"name": "latency.vector_arith", "value": 2, "unit": "cycles", "note": "hypothetical test value"}]}
        mp = os.path.join(out, "measurement.json")
        with open(mp, "w") as f:
            json.dump(meas, f)
        rc, imp, out2, p = run("import-native", mp, "--request", os.path.join(out, "request.json"), "--prediction", os.path.join(out_sim, "result.json"))
        self.assertEqual(rc, 0, p.stderr)
        self.assertEqual(imp["result_type"], "imported_native_measurement")
        self.assertTrue(os.path.exists(os.path.join(out2, "overlay-profile.json")))
        self.assertAlmostEqual(imp["prediction"]["scenarios"][0]["error_pct"], 100.0 * (sim["prediction"]["predicted_cycles_per_unit"] - 20.0) / 20.0)
        # the overlay changes the model hash and the prediction
        rc, sim2, out3, p = run("simulate", helpers.fixture("saxpy_loop.json"), "--overlay", os.path.join(out2, "overlay-profile.json"))
        self.assertEqual(rc, 0, p.stderr)
        self.assertNotEqual(sim2["profile"]["hash"], sim["profile"]["hash"])
        self.assertLess(sim2["prediction"]["predicted_cycles"], sim["prediction"]["predicted_cycles"])
        meas["request_hash_sha256"] = "0" * 64
        with open(mp, "w") as f:
            json.dump(meas, f)
        rc, imp, out4, p = run("import-native", mp, "--request", os.path.join(out, "request.json"))
        self.assertEqual(rc, 2, "a measurement for another request is rejected")

    def test_output_dir_must_be_fresh(self):
        tmp = tempfile.mkdtemp()
        out = os.path.join(tmp, "o")
        os.makedirs(out)
        with open(os.path.join(out, "x"), "w") as f:
            f.write("x")
        p = subprocess.run([sys.executable, KT, "validate", helpers.fixture("saxpy_loop.json"), "--out", out], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("not empty", p.stderr)


class TestBatchAndAdapter(unittest.TestCase):
    def test_batch_ranks_and_queues(self):
        rc, res, out, p = run("batch", helpers.fixture(os.path.join("batch", "manifest.json")))
        self.assertEqual(rc, 0, p.stderr + p.stdout[-800:])
        pred = res["prediction"]
        self.assertEqual(pred["kind"], "batch_ranking")
        self.assertEqual(len(pred["ranking"]), 7)
        self.assertEqual(pred["ranking"][0], "donor-off")
        self.assertTrue(all(c["result_class"] == "unvalidated_scenario_estimate" for c in pred["candidates"]))
        self.assertTrue(all(c["uncertain"] for c in pred["candidates"]), "every variant is within 5% of the baseline or has unvalidated memory behaviour")
        self.assertEqual(len(pred["queued_for_native"]), 7)
        self.assertTrue(os.path.exists(os.path.join(out, "queue", "knc-switch-off", "request.json")))
        self.assertTrue(os.path.exists(os.path.join(out, "batch.md")))

    def test_batch_refuses_changed_profile(self):
        import tempfile as _tf
        with open(helpers.fixture(os.path.join("batch", "manifest.json")), encoding="utf-8") as f:
            man = json.load(f)
        man["frozen_profile_hash"] = "0" * 64
        d = _tf.mkdtemp()
        mp = os.path.join(d, "manifest.json")
        for c in man["candidates"]:
            c["kernel"] = os.path.join(helpers.FIXTURES, "batch", c["kernel"])
        with open(mp, "w", encoding="utf-8") as f:
            json.dump(man, f)
        rc, res, out, p = run("batch", mp)
        self.assertEqual(rc, 2)
        self.assertEqual(res["status"], "invalid_input")

    def test_adapter_cli(self):
        import tempfile as _tf
        d = _tf.mkdtemp()
        out = os.path.join(d, "k.json")
        p = subprocess.run([sys.executable, os.path.join(helpers.SCRIPTS, "from_gcc_s.py"), os.path.join(helpers.FIXTURES, "gcc", "x87test.s"),
                            "--function", "g", "--init", os.path.join(helpers.FIXTURES, "gcc", "g_init.json"), "--out", out],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.path.exists(out) and os.path.exists(os.path.join(d, "k.coverage.json")))
        rc, res, out2, p2 = run("simulate", out)
        self.assertEqual(rc, 0, p2.stderr)
        self.assertEqual(res["functional_check"]["status"], "ok")
        self.assertEqual(res["prediction"]["result_class"]["class"], "unvalidated_scenario_estimate")
        p = subprocess.run([sys.executable, os.path.join(helpers.SCRIPTS, "from_gcc_s.py"), os.path.join(helpers.FIXTURES, "gcc", "s12-30-compiler-knc.s"), "--audit"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("knc_csr_raw", p.stdout)


if __name__ == "__main__":
    unittest.main()
