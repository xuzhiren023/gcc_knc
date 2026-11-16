"""0.3.1: the IMCI forms PhiWeather's WRF hot loops use (GCC-KNC 16.2 -mphinix): exponent/mantissa extraction,
scaling, vgmax/vgmin, integer compares and blend, MXCSR, x87 memory compares, the approximate reciprocals,
fix-up. Oracles: the R27 operation descriptions (facts only) and IEEE arithmetic in Python."""
import struct
import unittest

import helpers
from helpers import kernel, simulate
from knc_model import asm, functional, fp
from knc_model.errors import Unsupported


def run(k):
    interp, steps, check = functional.run_functional(k)
    return interp, check


def f32(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def asf(bits):
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def vk(text, zregs, policy=None, **extra):
    init = {"registers": zregs}
    kw = {}
    if policy:
        kw["numerical_policy"] = policy
    kw.update(extra)
    return kernel(None, init=init, streams=[{"context": 0, "asm": text}], **kw)


NAN, SNAN, INF, NINF = 0x7FC00000, 0x7F800001, 0x7F800000, 0xFF800000
DENORM = 0x00000001


class TestParserForms(unittest.TestCase):
    def test_wrf_spellings(self):
        recs, _ = asm.parse_gas("vgetmantps {sae},$5,%zmm1,%zmm0\nvgetexpps {sae},%zmm1,%zmm2\nvscaleps {ru},%zmm9,%zmm20,%zmm20{%k6}\n"
                                "vrcp23ps {sae},%zmm3,%zmm4\nvpcmpnled %zmm3,%zmm7,%k1\nvpblendmd %zmm1,%zmm2,%zmm3{%k2}\nstmxcsr -0x24(%rbp)\nfcoms 0x10(%rsp)\nfcomps (%rax)")
        ops = [r["op"] for r in recs]
        self.assertEqual(ops, ["vgetmantps", "vgetexpps", "vscaleps", "vrcp23ps", "vpcmpnled", "vpblendmd", "stmxcsr", "fcoms", "fcomps"])
        self.assertTrue(recs[0]["sae"] and recs[1]["sae"] and recs[3]["sae"])
        self.assertEqual(recs[0]["ops"], ["zmm0", "zmm1", {"imm": 5}])
        self.assertEqual(recs[2]["rounding"], "ru")
        self.assertEqual(recs[2]["mask"], "k6")
        self.assertNotIn("rounding", recs[0])
        kernel(recs)   # every record validates

    def test_vmaxps_is_not_an_imci_instruction(self):
        k = kernel([{"op": "vmaxps", "ops": ["zmm0", "zmm1", "zmm2"]}])
        with self.assertRaises(Unsupported):
            run(k)


class TestGetExpGetMant(unittest.TestCase):
    def test_getexp(self):
        src = [f32(1.0 / 16), f32(1.0), f32(3.0), f32(-6.5), f32(0.0), f32(-0.0), INF, NINF, NAN, SNAN, DENORM, f32(2.0 ** 100)] + [0] * 4
        k = vk("vgetexpps %zmm1,%zmm0", {"zmm1": {"u32": src}})
        interp, _ = run(k)
        out = interp.contexts[0].zmm["zmm0"]
        self.assertEqual([asf(b) for b in out[:4]], [-4.0, 0.0, 1.0, 2.0])
        self.assertEqual(out[4:8], [NINF, NINF, INF, INF])
        self.assertEqual(out[8], NAN)
        self.assertEqual(out[9], SNAN | 0x00400000, "sNaN quieted")
        self.assertEqual(asf(out[10]), -149.0, "denormal normalized before exponent extraction")
        self.assertEqual(asf(out[11]), 100.0)
        self.assertTrue(interp.contexts[0].mxcsr & 1, "sNaN raised the invalid flag")
        self.assertTrue(interp.contexts[0].mxcsr & 2, "denormal operand raised the denormal flag")

    def test_getmant_intervals_and_sign(self):
        x = f32(-6.5)                 # -1.625 * 2^2 (even exponent), significand top bit 1
        y = f32(3.0)                  # 1.5 * 2^1 (odd exponent), top fraction bit 1
        z = f32(1.25)                 # 1.25 * 2^0 (even), top fraction bit 0
        for imm, want in ((0, (-1.625, 1.5, 1.25)),        # [1,2), sign kept
                          (1, (-1.625, 0.75, 1.25)),       # [1/2,2): odd exponent halves
                          (2, (-0.8125, 0.75, 0.625)),     # [1/2,1)
                          (3, (-0.8125, 0.75, 1.25)),      # [3/4,3/2): fraction top bit set halves
                          (4, (1.625, 1.5, 1.25))):        # sign forced to 0
            k = vk("vgetmantps $%d,%%zmm1,%%zmm0" % imm, {"zmm1": {"u32": [x, y, z] + [0] * 13}})
            interp, _ = run(k)
            got = tuple(asf(b) for b in interp.contexts[0].zmm["zmm0"][:3])
            self.assertEqual(got, want, "imm %d" % imm)
        k = vk("vgetmantps $8,%zmm1,%zmm0", {"zmm1": {"u32": [f32(-6.5), f32(3.0), f32(-0.0), INF, DENORM] + [0] * 11}})
        interp, _ = run(k)
        out = interp.contexts[0].zmm["zmm0"]
        self.assertEqual(out[0], 0xFFC00000, "sign control 1x: negative source gives the indefinite NaN")
        self.assertEqual(asf(out[1]), 1.5)
        self.assertEqual(out[2], 0xFFC00000, "-0 is negative for sign control 1x")
        self.assertEqual(out[3], INF)
        self.assertEqual(asf(out[4]), 1.0, "denormal 2^-149 normalizes to 1.0")
        self.assertTrue(interp.contexts[0].mxcsr & 1)

    def test_getmant_sae_raises_no_flags(self):
        k = vk("vgetmantps {sae},$8,%zmm1,%zmm0", {"zmm1": {"u32": [f32(-6.5)] + [0] * 15}})
        interp, _ = run(k)
        self.assertEqual(interp.contexts[0].mxcsr & 0x3F, 0)


class TestScaleMinMax(unittest.TestCase):
    def test_vscale_rounding_and_range(self):
        src = {"zmm1": {"u32": [f32(1.5), f32(-3.0), f32(1.0), f32(1.0), f32(1.0), INF, f32(0.0), NAN] + [0] * 8},
               "zmm2": {"u32": [2, 0xFFFFFFFF, 200, 0xFFFFFF00, 128, 5, 5, 5] + [0] * 8}}
        interp, _ = run(vk("vscaleps %zmm2,%zmm1,%zmm0", src))
        out = interp.contexts[0].zmm["zmm0"]
        self.assertEqual([asf(b) for b in out[:3]], [6.0, -1.5, float("inf")])
        self.assertEqual(out[3], 0, "2^-256 underflows to +0")
        self.assertEqual(out[4], INF, "2^128 overflows")
        self.assertEqual(out[5:8], [INF, 0, NAN])
        m = interp.contexts[0].mxcsr
        self.assertTrue(m & (1 << 3) and m & (1 << 4) and m & (1 << 5), "overflow, underflow and inexact flags set")
        # a rounding override: 1.0 * 2^-149 is exact; 1.5 * 2^-149 rounds up under {ru}, down under {rd}
        interp, _ = run(vk("vscaleps {ru},%zmm2,%zmm1,%zmm0", {"zmm1": {"u32": [f32(1.5)] + [0] * 15}, "zmm2": {"u32": [0xFFFFFF6B] + [0] * 15}}))
        self.assertEqual(interp.contexts[0].zmm["zmm0"][0], 2)
        interp, _ = run(vk("vscaleps {rd},%zmm2,%zmm1,%zmm0", {"zmm1": {"u32": [f32(1.5)] + [0] * 15}, "zmm2": {"u32": [0xFFFFFF6B] + [0] * 15}}))
        self.assertEqual(interp.contexts[0].zmm["zmm0"][0], 1)

    def test_vscale_dynamic_mode_from_policy(self):
        src = {"zmm1": {"u32": [f32(1.5)] + [0] * 15}, "zmm2": {"u32": [0xFFFFFF6B] + [0] * 15}}
        interp, _ = run(vk("vscaleps %zmm2,%zmm1,%zmm0", src, policy={"rounding": "ru"}))
        self.assertEqual(interp.contexts[0].zmm["zmm0"][0], 2)
        self.assertEqual(interp.contexts[0].mxcsr >> 13 & 3, 2, "MXCSR.RC follows the policy")

    def test_vgmax_vgmin(self):
        a = [f32(1.0), f32(-0.0), f32(0.0), NAN, f32(2.0), NAN, NINF, f32(5.0)] + [0] * 8
        b = [f32(2.0), f32(0.0), f32(-0.0), f32(7.0), NAN, SNAN, f32(1.0), INF] + [0] * 8
        interp, _ = run(vk("vgmaxps %zmm2,%zmm1,%zmm0", {"zmm1": {"u32": a}, "zmm2": {"u32": b}}))
        out = interp.contexts[0].zmm["zmm0"]
        self.assertEqual(out[:8], [f32(2.0), f32(0.0), f32(0.0), f32(7.0), f32(2.0), NAN, f32(1.0), INF])
        interp, _ = run(vk("vgminps %zmm2,%zmm1,%zmm0", {"zmm1": {"u32": a}, "zmm2": {"u32": b}}))
        out = interp.contexts[0].zmm["zmm0"]
        self.assertEqual(out[:8], [f32(1.0), f32(-0.0), f32(-0.0), f32(7.0), f32(2.0), NAN, NINF, f32(5.0)])


class TestCompareBlendMxcsr(unittest.TestCase):
    def test_vpcmp_named_predicates_and_blend(self):
        a = {"zmm1": {"u32": list(range(16))}, "zmm2": {"u32": [5] * 16}, "zmm3": {"u32": [100 + i for i in range(16)]}}
        interp, _ = run(vk("vpcmpneqd %zmm2,%zmm1,%k1\nvpcmpnled %zmm2,%zmm1,%k2\nvpblendmd %zmm3,%zmm1,%zmm0{%k2}", a))
        cx = interp.contexts[0]
        self.assertEqual(cx.k["k1"], 0xFFFF & ~(1 << 5))
        self.assertEqual(cx.k["k2"], 0xFFC0, "nle: lanes 6..15 are greater than 5")
        self.assertEqual(cx.zmm["zmm0"], list(range(6)) + [106 + i for i in range(10)])

    def test_stmxcsr_and_flag_accumulation(self):
        text = "stmxcsr (%rdi)\nvmulps %zmm2,%zmm1,%zmm0\nstmxcsr 4(%rdi)\nvmulps {sae},%zmm2,%zmm1,%zmm3\nstmxcsr 8(%rdi)"
        k = kernel(None, init={"registers": {"rdi": "0x1000", "zmm1": {"f32_broadcast": 2.0 ** 120}, "zmm2": {"f32_broadcast": 1024.0}},
                               "memory": [{"addr": "0x1000", "u32": [0, 0, 0]}]},
                   streams=[{"context": 0, "asm": text}], numerical_policy={"rounding": "rz", "ftz": True})
        interp, _ = run(k)
        words = struct.unpack("<3I", interp.memory.read(0x1000, 12))
        self.assertEqual(words[0], 0x1F80 | (3 << 13) | (1 << 15), "masked, RZ, FZ")
        self.assertEqual(words[1], words[0] | (1 << 3) | (1 << 5), "overflow and inexact after the multiply")
        self.assertEqual(words[2], words[1], "{sae} suppressed the second multiply's flags")

    def test_masked_off_lanes_raise_no_flags(self):
        k = kernel(None, init={"registers": {"k1": 1, "zmm1": {"u32": [f32(1.0)] + [SNAN] * 15}, "zmm2": {"f32_broadcast": 1.0}}},
                   streams=[{"context": 0, "asm": "vaddps %zmm2,%zmm1,%zmm0{%k1}"}])
        interp, _ = run(k)
        self.assertEqual(interp.contexts[0].mxcsr & 0x3F, 0)


class TestX87MemoryCompare(unittest.TestCase):
    def test_fcoms_fcomps(self):
        text = "fldl (%rsi)\nfcoms (%rdi)\nfnstsw %ax\nmovl %eax,%r8d\nfcomps 4(%rdi)\nfnstsw %ax"
        k = kernel(None, init={"registers": {"rsi": "0x1000", "rdi": "0x2000"},
                               "memory": [{"addr": "0x1000", "f64": [2.5]}, {"addr": "0x2000", "f32": [2.5, 3.0]}]},
                   streams=[{"context": 0, "asm": text}])
        interp, _ = run(k)
        cx = interp.contexts[0]
        self.assertEqual((cx.gpr["r8"] >> 14) & 1, 1, "st0 == 2.5: C3")
        self.assertEqual((cx.gpr["rax"] >> 8) & 1, 1, "2.5 < 3.0: C0")
        self.assertEqual(cx.fdepth(), 0, "fcomps popped the stack")
        res, sim, _ = simulate(k)
        self.assertGreater(res["completion_cycles"], 0)


class TestApproximateAndFixup(unittest.TestCase):
    def test_vrcp23_specials_and_approximate_marking(self):
        src = [f32(4.0), f32(0.0), f32(-0.0), INF, NINF, NAN, SNAN, DENORM, f32(3.0)] + [0] * 7
        interp, _ = run(vk("vrcp23ps %zmm1,%zmm0", {"zmm1": {"u32": src}}))
        cx = interp.contexts[0]
        out = cx.zmm["zmm0"]
        self.assertEqual(asf(out[0]), 0.25)
        self.assertEqual(out[1:5], [INF, NINF, 0, 0x80000000])
        self.assertEqual(out[5], NAN)
        self.assertEqual(out[6], SNAN | 0x00400000)
        self.assertEqual(out[7], INF, "denormal input treated as zero")
        self.assertEqual(out[8], f32(1.0 / 3.0), "correctly rounded stands in for the hardware's 0.912-ulp value")
        self.assertTrue(cx.mxcsr & (1 << 2), "zero-divide flag")
        self.assertTrue(cx.mxcsr & 1, "invalid flag from the sNaN")
        self.assertEqual(interp.approximate_instructions, {"vrcp23ps"})
        self.assertTrue(any("approximate" in a for a in interp.assumptions))

    def test_vrsqrt23_specials(self):
        src = [f32(4.0), f32(0.0), f32(-0.0), INF, NINF, f32(-1.0)] + [0] * 10
        interp, _ = run(vk("vrsqrt23ps %zmm1,%zmm0", {"zmm1": {"u32": src}}))
        out = interp.contexts[0].zmm["zmm0"]
        self.assertEqual(asf(out[0]), 0.5)
        self.assertEqual(out[1:3], [INF, NINF])
        self.assertEqual(out[3], 0)
        self.assertEqual(out[4], 0xFFC00000)
        self.assertEqual(out[5], 0xFFC00000)

    def test_vfixupnan_table(self):
        # classes: -inf(0) <0(1) -0(2) +0(3) >0(4) +inf(5); tokens: 1 -inf, 2 -0, 3 +0, 4 +inf, 5 NaN, 6 NMAX, 7 -NMAX
        table = (4 << 0) | (6 << 3) | (3 << 6) | (4 << 9) | (0 << 12) | (5 << 15)
        src1 = [NINF, f32(-2.0), f32(-0.0), f32(0.0), f32(7.0), INF, NAN, SNAN] + [0] * 8
        k = kernel(None, init={"registers": {"zmm0": {"f32_broadcast": 9.0}, "zmm1": {"u32": src1}, "zmm2": {"u32": [table] * 16}}},
                   streams=[{"context": 0, "asm": "vfixupnanps %zmm2,%zmm1,%zmm0"}])
        interp, _ = run(k)
        out = interp.contexts[0].zmm["zmm0"]
        self.assertEqual(out[:8], [INF, 0x7F7FFFFF, 0, INF, f32(9.0), 0xFFC00000, NAN, SNAN | 0x00400000])
        self.assertTrue(interp.contexts[0].mxcsr & 1)


if __name__ == "__main__":
    unittest.main()
