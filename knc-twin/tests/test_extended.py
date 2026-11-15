"""Extended instruction forms: x87 stack semantics checked against GCC-KNC output, swizzles,
unpack/packstore, scatter, 8/16-bit registers, up/down conversions, the compiler-output adapter,
and the TLB / hardware-prefetcher / memory-service sub-models."""
import os
import sys
import unittest

import helpers
from helpers import kernel, profile, simulate
from knc_model import functional, fp
from knc_model.errors import MissingParameter, Unsupported
from knc_model.kernel import load_kernel

sys.path.insert(0, helpers.SCRIPTS)
import from_gcc_s  # noqa: E402

GCC_FIX = os.path.join(helpers.FIXTURES, "gcc")


def run(k):
    interp, steps, check = functional.run_functional(k)
    return interp, check


class TestCompiledFunctions(unittest.TestCase):
    """The expected values were computed by hand from the C source; the assembly is GCC-KNC's."""

    def test_x87_double_function(self):
        k = load_kernel(os.path.join(GCC_FIX, "x87test_f.json"))
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"][:1])
        self.assertEqual(interp.contexts[0].fdepth(), 0, "the function leaves the x87 stack empty")

    def test_x87_float_dot_product_loop(self):
        k = load_kernel(os.path.join(GCC_FIX, "x87test_g.json"))
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"][:1])
        res, sim, _ = simulate(k)
        self.assertGreater(res["completion_cycles"], 0)
        self.assertTrue(any("x87" in a for a in sim.assumptions))

    def test_scalar_integer_loop(self):
        k = load_kernel(os.path.join(GCC_FIX, "x87test_h.json"))
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"][:1])

    def test_adapter_regenerates_the_fixture(self):
        prof = profile()
        kd, rows, summary = from_gcc_s.convert(os.path.join(GCC_FIX, "x87test.s"), "f", profile=prof)
        self.assertTrue(summary["complete"]["functional"] and summary["complete"]["timing"], summary)
        self.assertEqual(summary["instructions"], 15)
        kd2, rows2, s2 = from_gcc_s.convert(os.path.join(GCC_FIX, "x87test.s"), "g", loop_label=".L6", profile=prof)
        self.assertTrue(s2["complete"]["functional"])
        self.assertEqual(kd2["loop"]["label"], ".L6")
        self.assertTrue(any(r["text"].startswith("vprefetch") for r in rows2))

    def test_adapter_audit_reports_blockers(self):
        prof = profile()
        rep = from_gcc_s.audit([os.path.join(GCC_FIX, "s12-30-compiler-knc.s")], prof, None)
        funcs = {e["function"]: e for e in rep["files"][0]["functions"]}
        csr = funcs["knc_csr_raw"]["summary"]
        self.assertEqual(csr["instructions"], csr["isa_known"], "every instruction of the gate kernel is readable")
        hot = [l for l in funcs["knc_csr_raw"]["loops"] if l["label"] == ".L6"][0]["summary"]
        self.assertTrue(hot["complete"]["functional"] and hot["complete"]["timing"], hot)
        self.assertEqual(hot["instructions"], 43)


class TestX87Semantics(unittest.TestCase):
    def test_att_subtraction_forms(self):
        # fsub %st(1), %st : st0 = st0 - st1 ; fsubrp %st, %st(1): st1 = st1 - st0 ; fsubp %st, %st(1): st1 = st0 - st1
        k = kernel(None, streams=[{"context": 0, "asm": """
            fldl (%rdi)
            fldl 8(%rdi)
            fsub %st(1), %st
            fstpl (%rsi)
            fldl (%rdi)
            fldl 8(%rdi)
            fsubrp %st, %st(1)
            fstpl 8(%rsi)
            fldl (%rdi)
            fldl 8(%rdi)
            fsubp %st, %st(1)
            fstpl 16(%rsi)
            fldl (%rdi)
            fdivrl 8(%rdi)
            fstpl 24(%rsi)
        """}], init={"registers": {"rdi": "0x1000", "rsi": "0x2000"}, "memory": [{"addr": "0x1000", "f64": [10.0, 4.0]}]},
            expected={"memory": [{"addr": "0x2000", "f64": [-6.0, 6.0, -6.0, 0.4]}]})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"])

    def test_extended_precision_and_rounding_on_store(self):
        # 1 + 2^-60 is exact in extended precision; storing to double rounds it back to 1.0
        k = kernel(None, streams=[{"context": 0, "asm": """
            fldl (%rdi)
            fldl 8(%rdi)
            faddp %st, %st(1)
            fld %st(0)
            fstpl (%rsi)
            fstpt 16(%rsi)
        """}], init={"registers": {"rdi": "0x1000", "rsi": "0x2000"}, "memory": [{"addr": "0x1000", "f64": [1.0, 2.0 ** -60]}]},
            expected={"memory": [{"addr": "0x2000", "f64": [1.0]}]})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"])
        img = interp.memory.read(0x2010, 10)
        bits = fp.f80_from_memory(img)
        self.assertNotEqual(fp.convert(bits, fp.F80, fp.F64)[0], 0, "extended image written")
        self.assertEqual(fp.to_fraction(bits, fp.F80), fp.Fraction(1) + fp.Fraction(1, 2 ** 60), "the sum stays exact in 64-bit precision")

    def test_control_word_rounding_and_fistp(self):
        # RC = truncate (0x0f7f) makes fistpl truncate 2.7 -> 2; default rounds to 3
        k = kernel(None, streams=[{"context": 0, "asm": """
            fldl (%rdi)
            fistpl (%rsi)
            fldcw 8(%rdi)
            fldl (%rdi)
            fistpl 4(%rsi)
        """}], init={"registers": {"rdi": "0x1000", "rsi": "0x2000"}, "memory": [{"addr": "0x1000", "f64": [2.7]}, {"addr": "0x1008", "u16": ["0x0f7f"]}]},
            expected={"memory": [{"addr": "0x2000", "i32": [3, 2]}]})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"])

    def test_fcom_fnstsw_pattern(self):
        k = kernel(None, streams=[{"context": 0, "asm": """
            fldl (%rdi)
            fldl 8(%rdi)
            fucom %st(1)
            fnstsw %ax
            fstp %st(0)
            fstp %st(0)
            testb $69, %ah
            jne L1
            movl $1, %ecx
        L1: nop
        """}], init={"registers": {"rdi": "0x1000", "rcx": 0}, "memory": [{"addr": "0x1000", "f64": [3.0, 5.0]}]},
            expected={"registers": {"0": {"rcx": 0, "x87_depth": 0}}})
        # st0 = 5, st1 = 3: st0 > st1 -> C0 = C2 = C3 = 0 -> ah & 0x45 == 0 -> branch not taken -> rcx = 1
        interp, check = run(k)
        self.assertEqual(check["status"], "mismatch")
        self.assertEqual(interp.contexts[0].gpr["rcx"], 1)

    def test_sqrt_and_stack_errors(self):
        k = kernel(None, streams=[{"context": 0, "asm": "fldl (%rdi)\n fsqrt\n fstpl (%rsi)"}],
                   init={"registers": {"rdi": "0x1000", "rsi": "0x2000"}, "memory": [{"addr": "0x1000", "f64": [2.0]}]},
                   expected={"memory": [{"addr": "0x2000", "f64": [1.4142135623730951]}]})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"])
        with self.assertRaises(MissingParameter):
            simulate(k)  # latency.x87_sqrt is unknown in the measured profile
        k2 = kernel(None, streams=[{"context": 0, "asm": "fstpl (%rsi)"}], init={"registers": {"rsi": "0x2000"}})
        with self.assertRaises(Exception):
            run(k2)


class TestVectorForms(unittest.TestCase):
    def test_swizzle_semantics_and_latency(self):
        k = kernel([{"op": "vmovdqa32", "ops": ["zmm1", {"reg": "zmm0", "swizzle": "cdab"}], "id": "s"},
                    {"op": "vpaddd", "ops": ["zmm2", {"reg": "zmm0", "swizzle": "aaaa"}, "zmm0"], "id": "a"}],
                   init={"registers": {"zmm0": {"u32": list(range(16))}}},
                   expected={"registers": {"0": {"zmm1": {"u32": [2, 3, 0, 1, 6, 7, 4, 5, 10, 11, 8, 9, 14, 15, 12, 13]},
                                                 "zmm2": {"u32": [0, 1, 2, 3, 8, 9, 10, 11, 16, 17, 18, 19, 24, 25, 26, 27]}}}})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"][:1])
        res, sim, _ = simulate(k)
        log = {e["id"]: e for e in sim.issue_log}
        self.assertEqual(log["s"]["done"] - log["s"]["cycle"], 6, "a swizzled source costs the long-vector latency")

    def test_unpack_pack_round_trip_unaligned(self):
        # load 16 floats from an address 16 bytes into a line, store them to another unaligned address
        vals = [float(i) for i in range(16)]
        k = kernel(None, streams=[{"context": 0, "asm": """
            vloadunpacklps (%rdi), %zmm0
            vloadunpackhps 64(%rdi), %zmm0
            vpackstorelps %zmm0, (%rsi)
            vpackstorehps %zmm0, 64(%rsi)
        """}], init={"registers": {"rdi": "0x1010", "rsi": "0x2030"}, "memory": [{"addr": "0x1010", "f32": vals}]},
            expected={"memory": [{"addr": "0x2030", "f32": vals}], "registers": {"0": {"zmm0": {"f32": vals}}}})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"][:1])
        tr = interp.traces[0]
        self.assertEqual(tr[0].nbytes, 48, "the low half covers the 12 elements before the line boundary")
        self.assertEqual(tr[1].nbytes, 16)

    def test_up_and_down_conversion(self):
        k = kernel(None, streams=[{"context": 0, "asm": """
            vmovaps (%rdi){float16}, %zmm0
            vmovaps %zmm0{float16}, (%rsi)
            vmovaps 64(%rdi){uint8}, %zmm1
        """}], init={"registers": {"rdi": "0x1000", "rsi": "0x2000"},
                     "memory": [{"addr": "0x1000", "f16": [1.0, -2.0, 0.5, 65504.0] + [0.0] * 12}, {"addr": "0x1040", "u8": list(range(16))}]},
            expected={"registers": {"0": {"zmm0": {"f32": [1.0, -2.0, 0.5, 65504.0] + [0.0] * 12}, "zmm1": {"f32": [float(i) for i in range(16)]}}},
                      "memory": [{"addr": "0x2000", "f16": [1.0, -2.0, 0.5, 65504.0] + [0.0] * 12}]})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"][:1])

    def test_scatter_semantics_and_missing_occupancy(self):
        k = kernel([{"op": "vscatterdps", "ops": [{"base": "rax", "vindex": "zmm1", "scale": 4}, "zmm0"], "mask": "k1"}],
                   init={"memory": [{"addr": "0x2000", "u32": [0] * 64}], "registers": {"rax": "0x2000", "k1": "0x000f", "zmm1": {"u32": [0, 16, 32, 48] + [0] * 12}, "zmm0": {"u32": [7, 8, 9, 10] + [0] * 12}}},
                   expected={"memory": [{"addr": "0x2000", "u32": [7]}, {"addr": "0x2040", "u32": [8]}, {"addr": "0x20c0", "u32": [10]}], "registers": {"0": {"k1": 0}}})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"][:1])
        self.assertEqual(len(interp.traces[0][0].lines), 4)
        with self.assertRaises(MissingParameter):
            simulate(k)
        res, _, _ = simulate(k, prof=profile("synthetic-demo"))
        self.assertEqual(res["completion_cycles"], 4 * 7)

    def test_byte_registers_and_partial_writes(self):
        k = kernel(None, streams=[{"context": 0, "asm": """
            movq $0x1122334455667788, %rax
            movb $0xaa, %al
            movw $0xbbcc, %dx
            movsbl %al, %ecx
            movzbl %al, %esi
            imulq $3, %rdi
            cltq
        """}], init={"registers": {"rdx": "0xffffffff00000000", "rdi": 5}},
            expected={"registers": {"0": {"rdx": "0xffffffff0000bbcc", "rcx": "0xffffffaa", "rsi": "0xaa", "rdi": 15}}})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"][:1])
        self.assertEqual(interp.contexts[0].gpr["rax"] & 0xFFFFFFFF, 0x55667788 & 0xFFFFFF00 | 0xaa & 0xFF | 0, "cltq sign-extends eax; low byte replaced")

    def test_memory_destination_rmw_and_setcc(self):
        k = kernel(None, streams=[{"context": 0, "asm": """
            addl $5, (%rdi)
            orb $1, 4(%rdi)
            cmpl $7, (%rdi)
            sete %al
            setg %bl
        """}], init={"registers": {"rdi": "0x1000", "rax": 0, "rbx": 0}, "memory": [{"addr": "0x1000", "u32": [2, 0x10]}]},
            expected={"memory": [{"addr": "0x1000", "u32": [7, 0x11]}], "registers": {"0": {"rax": 1, "rbx": 0}}})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check["mismatches"][:1])
        res, sim, _ = simulate(k)
        self.assertEqual(sim.issue_log[0]["op"], "add")
        self.assertGreater(sim.issue_log[0]["done"], sim.issue_log[0]["cycle"] + 3, "a memory RMW waits for its load before the ALU result")


class TestMemorySubmodels(unittest.TestCase):
    def cold(self, extra):
        sc = {"memory": dict({"type": "line_tracking", "cold_level": "memory"}, **extra), "branch": {"type": "all_predicted"}}
        ins = [{"op": "vmovaps", "ops": ["zmm%d" % (i % 8), {"base": "rax", "disp": 4096 * i}], "id": "ld%d" % i} for i in range(70)]
        return kernel(ins, init={"registers": {"rax": "0x100000"}}, memory_default=0, scenario=sc)

    def test_tlb_penalty_after_64_pages(self):
        base, _, _ = simulate(self.cold({}))
        tlb, simt, _ = simulate(self.cold({"tlb": "modeled"}))
        self.assertEqual(tlb["memory"]["stats"]["tlb_misses"], 70, "70 distinct pages: every access misses the 64-entry DTLB")
        self.assertGreaterEqual(tlb["completion_cycles"] - base["completion_cycles"], 70 * 25)
        self.assertIn("tlb", tlb["memory"]["submodels"])

    def test_hardware_prefetcher_hides_sequential_misses(self):
        ins = [{"op": "vmovaps", "ops": ["zmm%d" % (i % 8), {"base": "rax", "disp": 64 * i}], "id": "ld%d" % i} for i in range(32)]
        sc_off = {"memory": {"type": "line_tracking", "cold_level": "memory"}, "branch": {"type": "all_predicted"}}
        sc_on = {"memory": {"type": "line_tracking", "cold_level": "memory", "hardware_prefetcher": "modeled"}, "branch": {"type": "all_predicted"}}
        k_off = kernel(ins, init={"registers": {"rax": "0x100000"}}, memory_default=0, scenario=sc_off)
        k_on = kernel(ins, init={"registers": {"rax": "0x100000"}}, memory_default=0, scenario=sc_on)
        off, _, _ = simulate(k_off)
        on, _, _ = simulate(k_on)
        self.assertGreater(on["memory"]["stats"]["hw_prefetches"], 0)
        self.assertLess(on["completion_cycles"], off["completion_cycles"] * 0.7, "prefetched lines turn memory misses into L2 hits")
        self.assertEqual(on["memory"]["stats"]["memory"] + on["memory"]["stats"]["l2_hits"], 32)

    def test_memory_service_spaces_fills(self):
        ins = [{"op": "vprefetch0", "ops": [{"base": "rax", "disp": 64 * i}], "id": "pf%d" % i} for i in range(8)]
        sc = {"memory": {"type": "line_tracking", "cold_level": "memory", "memory_service": "modeled"}, "branch": {"type": "all_predicted"}}
        k = kernel(ins + [{"op": "vmovaps", "ops": ["zmm0", {"base": "rax", "disp": 64 * 7}], "id": "ld"}], init={"registers": {"rax": "0x100000"}}, memory_default=0, scenario=sc)
        res, sim, _ = simulate(k)
        self.assertGreaterEqual(res["memory"]["stats"]["memory_service_waits"], 6)
        log = {e["id"]: e for e in sim.issue_log}
        self.assertGreaterEqual(log["ld"]["done"], 357 + 7 * 20, "the eighth line arrives after seven service intervals")

    def test_result_class_labels(self):
        from knc_model.cli import memory_result_class
        k = load_kernel(helpers.fixture("saxpy_loop.json"))
        prof = profile()
        c = memory_result_class("simulate", k, prof, {"l1_hits": 10}, k.scenario)
        self.assertEqual(c["class"], "unvalidated_scenario_estimate")
        self.assertEqual(memory_result_class("bound", k, prof)["class"], "conditional_bound")
        k.raw["provenance"] = {"shape": "l1_resident_vector_chain"}
        prof.calibration = dict(prof.calibration, validated_shapes={"l1_resident_vector_chain": {"median_abs_error_pct": 2.0}})
        self.assertEqual(memory_result_class("simulate", k, prof, {"l1_hits": 10}, k.scenario)["class"], "calibrated_forecast")


if __name__ == "__main__":
    unittest.main()
