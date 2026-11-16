"""Functional interpreter: supported arithmetic and mask edge cases, deliberately wrong
candidates, unknown instructions, alignment faults, inter-context communication."""
import unittest

import helpers
from helpers import kernel
from knc_model import functional
from knc_model.errors import InvalidInput, Unsupported


def run(k):
    interp, steps, check = functional.run_functional(k)
    return interp, check


class TestScalar(unittest.TestCase):
    def test_flags_add_overflow_and_sub_borrow(self):
        k = kernel([
            {"op": "add", "ops": ["rax", "rbx"]},
        ], init={"registers": {"rax": "0x7fffffffffffffff", "rbx": 1}})
        interp, _ = run(k)
        cx = interp.contexts[0]
        self.assertEqual(cx.gpr["rax"], 0x8000000000000000)
        self.assertEqual((cx.flags["OF"], cx.flags["SF"], cx.flags["CF"], cx.flags["ZF"]), (1, 1, 0, 0))
        k = kernel([{"op": "sub", "ops": ["eax", "ebx"]}], init={"registers": {"rax": "0xffffffff00000000", "rbx": 1}})
        interp, _ = run(k)
        cx = interp.contexts[0]
        self.assertEqual(cx.gpr["rax"], 0xffffffff, "32-bit write zero-extends")
        self.assertEqual(cx.flags["CF"], 1)

    def test_inc_dec_keep_cf_and_loop(self):
        k = kernel([
            {"op": "mov", "ops": ["rcx", 0]},
            {"op": "add", "ops": ["rcx", 3], "label": "L"},
            {"op": "dec", "ops": ["rdx"]},
            {"op": "jnz", "ops": ["L"]},
        ], init={"registers": {"rdx": 7, "flags": {"CF": 1}}})
        interp, _ = run(k)
        cx = interp.contexts[0]
        self.assertEqual(cx.gpr["rcx"], 21)
        self.assertEqual(cx.flags["ZF"], 1)
        self.assertEqual(len(interp.traces[0]), 1 + 3 * 7)
        self.assertEqual(sum(1 for e in interp.traces[0] if e.taken), 6)

    def test_shift_imul_lea(self):
        k = kernel([
            {"op": "shl", "ops": ["rax", 4]},
            {"op": "sar", "ops": ["rbx", 1]},
            {"op": "imul", "ops": ["rcx", "rdx"]},
            {"op": "lea", "ops": ["rsi", {"base": "rax", "index": "rcx", "scale": 8, "disp": -16}]},
        ], init={"registers": {"rax": 3, "rbx": "0xfffffffffffffffe", "rcx": -7, "rdx": 6}})
        interp, _ = run(k)
        cx = interp.contexts[0]
        self.assertEqual(cx.gpr["rax"], 48)
        self.assertEqual(cx.gpr["rbx"], 0xffffffffffffffff)
        self.assertEqual(cx.gpr["rcx"], (-42) & 0xffffffffffffffff)
        self.assertEqual(cx.gpr["rsi"], (48 + (-42) * 8 - 16) & 0xffffffffffffffff)

    def test_memory_round_trip_and_uninitialized_read(self):
        k = kernel([
            {"op": "mov", "ops": [{"base": "rax"}, "rbx"], "width": 64},
            {"op": "mov", "ops": ["rcx", {"base": "rax"}], "width": 64},
        ], init={"registers": {"rax": "0x1000", "rbx": "0x1122334455667788"}})
        interp, _ = run(k)
        self.assertEqual(interp.contexts[0].gpr["rcx"], 0x1122334455667788)
        k = kernel([{"op": "mov", "ops": ["rcx", {"base": "rax"}], "width": 64}], init={"registers": {"rax": "0x1000"}})
        with self.assertRaises(InvalidInput):
            run(k)


class TestMaskAndVector(unittest.TestCase):
    def test_kortest_and_logic(self):
        k = kernel([
            {"op": "kortest", "ops": ["k1", "k2"]},
            {"op": "jc", "ops": ["ALL"]},
            {"op": "mov", "ops": ["rax", 1]},
            {"op": "kandnr", "ops": ["k1", "k2"], "label": "ALL"},
            {"op": "kxnor", "ops": ["k3", "k3"]},
        ], init={"registers": {"k1": "0xf0f0", "k2": "0x0f0f", "k3": "0x1234"}})
        interp, _ = run(k)
        cx = interp.contexts[0]
        self.assertEqual(cx.gpr["rax"], 0, "CF set for all-ones OR, branch taken")
        self.assertEqual(cx.k["k1"], 0xf0f0 & ~0x0f0f & 0xffff)
        self.assertEqual(cx.k["k3"], 0xffff)

    def test_masked_merge_and_compare(self):
        k = kernel([
            {"op": "vpaddd", "ops": ["zmm2", "zmm0", "zmm1"], "mask": "k1"},
            {"op": "vpcmpd", "ops": ["k2", "zmm2", "zmm1", 1], "mask": "k1"},
            {"op": "vcmpps", "ops": ["k3", "zmm3", "zmm4", 1]},
        ], init={"registers": {"k1": "0x00ff", "zmm0": {"u32": [0xFFFFFFFF] * 16}, "zmm1": {"u32_broadcast": 1},
                               "zmm2": {"u32_broadcast": 77}, "zmm3": {"f32": [1.0] * 8 + [3.0] * 8}, "zmm4": {"f32_broadcast": 2.0}}})
        interp, _ = run(k)
        cx = interp.contexts[0]
        self.assertEqual(cx.zmm["zmm2"], [0] * 8 + [77] * 8, "merge keeps masked-out lanes")
        self.assertEqual(cx.k["k2"], 0x00ff, "0 < 1 in the enabled lanes; masked-out lanes give 0")
        self.assertEqual(cx.k["k3"], 0x00ff, "1.0 < 2.0 for the first 8 lanes")

    def test_gather_clears_mask_and_touches_lines(self):
        k = kernel([
            {"op": "vgatherdps", "ops": ["zmm0", {"base": "rax", "vindex": "zmm1", "scale": 4}], "mask": "k1"},
        ], init={"memory": [{"addr": "0x2000", "u32": list(range(512))}],
                 "registers": {"rax": "0x2000", "k1": "0x000f", "zmm1": {"u32": [0, 16, 32, 48] + [0] * 12}, "zmm0": {"u32_broadcast": 9}}})
        interp, _ = run(k)
        cx = interp.contexts[0]
        # one execution completes the lanes of one cache line and leaves the others in the mask (0.3.0)
        self.assertEqual(cx.zmm["zmm0"][:4], [0, 9, 9, 9])
        self.assertEqual(cx.k["k1"], 0x000e)
        self.assertEqual(len(interp.traces[0][0].lines), 1)
        k.numerical_policy["gather_completion"] = "all"
        interp, _ = run(k)
        cx = interp.contexts[0]
        self.assertEqual(cx.zmm["zmm0"][:4], [0, 16, 32, 48])
        self.assertEqual(cx.zmm["zmm0"][4:], [9] * 12)
        self.assertEqual(cx.k["k1"], 0)
        self.assertEqual(len(interp.traces[0][0].lines), 4)

    def test_conversions_and_broadcast(self):
        k = kernel([
            {"op": "vbroadcastss", "ops": ["zmm0", {"base": "rax"}]},
            {"op": "vcvtfxpntps2dq", "ops": ["zmm1", "zmm0", 0]},
            {"op": "vcvtfxpntps2dq", "ops": ["zmm2", "zmm0", 1]},
            {"op": "vcvtfxpntdq2ps", "ops": ["zmm3", "zmm1", 0]},
        ], init={"memory": [{"addr": "0x1000", "f32": [2.5]}], "registers": {"rax": "0x1000"}})
        interp, _ = run(k)
        cx = interp.contexts[0]
        self.assertEqual(cx.zmm["zmm1"], [2] * 16)
        self.assertEqual(cx.zmm["zmm2"], [2] * 16)
        self.assertEqual(cx.zmm["zmm3"], [0x40000000] * 16)

    def test_misaligned_vector_access_is_rejected(self):
        k = kernel([{"op": "vmovaps", "ops": ["zmm0", {"base": "rax"}]}], init={"memory": [{"addr": "0x1000", "u32": [0] * 32}], "registers": {"rax": "0x1010"}})
        with self.assertRaises(InvalidInput):
            run(k)


class TestChecksAndRejections(unittest.TestCase):
    def test_fixture_expectations_hold(self):
        from knc_model.kernel import load_kernel
        for name in ("saxpy_loop.json", "int_mask_edge.json", "fp_edge.json", "fp_edge_ftz.json", "gather_one_line.json", "reduce_2acc.json", "saxpy_asm.json"):
            k = load_kernel(helpers.fixture(name))
            interp, check = run(k)
            self.assertEqual(check["status"], "ok", (name, check["mismatches"][:1]))

    def test_deliberately_wrong_candidate_is_caught(self):
        from knc_model.kernel import load_kernel
        k = load_kernel(helpers.fixture("saxpy_bad_candidate.json"))
        interp, check = run(k)
        self.assertEqual(check["status"], "mismatch")
        self.assertEqual(len(check["mismatches"]), 1)
        self.assertIn("mem[0x2000000][3]", check["mismatches"][0]["where"])

    def test_unknown_instruction_rejected_at_load(self):
        with self.assertRaises(Unsupported) as cm:
            kernel([{"op": "vpmadd52luq", "ops": ["zmm0", "zmm1", "zmm2"]}])
        self.assertIn("no default cost", str(cm.exception))

    def test_timing_only_instruction_rejected_in_functional(self):
        k = kernel([{"op": "vlog2ps", "ops": ["zmm0", "zmm1"]}])
        with self.assertRaises(Unsupported):
            run(k)

    def test_contexts_communicating_through_memory_rejected(self):
        k = kernel(None, init={"memory": [{"addr": "0x1000", "u32": [0] * 16}]}, streams=[
            {"context": 0, "init": {"registers": {"rax": "0x1000", "zmm0": {"u32_broadcast": 1}}}, "instructions": [{"op": "vmovaps", "ops": [{"base": "rax"}, "zmm0"]}]},
            {"context": 1, "init": {"registers": {"rax": "0x1000"}}, "instructions": [{"op": "vmovaps", "ops": ["zmm1", {"base": "rax"}]}]},
        ])
        with self.assertRaises(Unsupported):
            run(k)

    def test_nan_compare_policy(self):
        k = kernel([{"op": "vaddps", "ops": ["zmm0", "zmm1", "zmm2"]}],
                   init={"registers": {"zmm1": {"u32_broadcast": 0x7f800000}, "zmm2": {"u32_broadcast": 0xff800000}}},
                   expected={"registers": {"0": {"zmm0": {"u32_broadcast": 0x7fc00000}}}}, numerical_policy={"nan_compare": "bits"})
        interp, check = run(k)
        self.assertEqual(check["status"], "mismatch", "default NaN is 0xffc00000; bitwise compare must flag the payload")
        k = kernel([{"op": "vaddps", "ops": ["zmm0", "zmm1", "zmm2"]}],
                   init={"registers": {"zmm1": {"u32_broadcast": 0x7f800000}, "zmm2": {"u32_broadcast": 0xff800000}}},
                   expected={"registers": {"0": {"zmm0": {"f32": ["nan"] * 16}}}})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok")


if __name__ == "__main__":
    unittest.main()
