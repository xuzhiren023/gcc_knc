"""Exact binary32/binary64 arithmetic against independent oracles.

Oracles: (1) binary64 arithmetic followed by a binary32 conversion is exactly the correctly
rounded binary32 result for +, -, * in round-to-nearest-even (double rounding is innocuous
when the wide format has >= 2p+2 bits: 53 >= 50; Figueroa 1995). (2) Python floats are
IEEE binary64 RNE for the binary64 tests. (3) Hand-derived vectors for FMA, directed
rounding, FTZ and special values.
"""
import random
import struct
import unittest

import helpers  # noqa: F401
from knc_model import fp


def f32(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def f32v(b):
    return struct.unpack("<f", struct.pack("<I", b))[0]


def f64(x):
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def f64v(b):
    return struct.unpack("<d", struct.pack("<Q", b))[0]


class TestBinary32Oracle(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(12345)

    def random_f32_bits(self):
        # finite values across the exponent range, including subnormals
        while True:
            b = self.rng.getrandbits(32)
            if (b >> 23) & 0xFF != 0xFF:
                return b

    def test_add_mul_match_double_rounding_oracle(self):
        for _ in range(4000):
            a, b = self.random_f32_bits(), self.random_f32_bits()
            fa, fb = f32v(a), f32v(b)
            try:
                want_add = f32(fa + fb)
                want_mul = f32(fa * fb)
            except OverflowError:
                continue  # struct cannot express overflow to infinity; specials are tested separately
            got_add, _ = fp.fadd(a, b, fp.F32)
            got_mul, _ = fp.fmul(a, b, fp.F32)
            self.assertEqual(got_add, want_add, "add %08x %08x" % (a, b))
            self.assertEqual(got_mul, want_mul, "mul %08x %08x" % (a, b))

    def test_sub_matches_oracle(self):
        for _ in range(2000):
            a, b = self.random_f32_bits(), self.random_f32_bits()
            want = f32(f32v(a) - f32v(b))
            got, _ = fp.fsub(a, b, fp.F32)
            self.assertEqual(got, want)

    def test_binary64_matches_python(self):
        rng = self.rng
        for _ in range(2000):
            a = rng.uniform(-1e300, 1e300) * rng.choice([1, 1e-200, 1e-300])
            b = rng.uniform(-1e300, 1e300) * rng.choice([1, 1e-200, 1e-300])
            ba, bb = f64(a), f64(b)
            got, _ = fp.fadd(ba, bb, fp.F64)
            self.assertEqual(got, f64(a + b))
            got, _ = fp.fmul(ba, bb, fp.F64)
            self.assertEqual(got, f64(a * b))


class TestFMA(unittest.TestCase):
    def test_fused_differs_from_unfused(self):
        a = 0x3f800001  # 1 + 2^-23
        b = 0x3f7fffff  # 1 - 2^-24
        c = 0xbf800000  # -1
        # exact: (1+2^-23)(1-2^-24) - 1 = 2^-24 - 2^-47 = 0x337ffffe
        got, _ = fp.ffma(a, b, c, fp.F32)
        self.assertEqual(got, 0x337ffffe)
        # unfused: product rounds to 1.0, sum is +0
        p, _ = fp.fmul(a, b, fp.F32)
        s, _ = fp.fadd(p, c, fp.F32)
        self.assertEqual(s, 0x00000000)

    def test_fma_exact_integers(self):
        for a, b, c in ((3.0, 4.0, 5.0), (-2.0, 8.0, 1.0), (0.5, 0.25, -0.125)):
            got, _ = fp.ffma(f32(a), f32(b), f32(c), fp.F32)
            self.assertEqual(got, f32(a * b + c))

    def test_fnmadd_fmsub(self):
        a, b, c = f32(2.0), f32(3.0), f32(1.0)
        self.assertEqual(fp.ffma(a, b, c, fp.F32, negate_product=True)[0], f32(-5.0))
        self.assertEqual(fp.ffma(a, b, c, fp.F32, negate_c=True)[0], f32(5.0))
        self.assertEqual(fp.ffma(a, b, c, fp.F32, negate_product=True, negate_c=True)[0], f32(-7.0))

    def test_fma_f64(self):
        # 2^53+1 is not representable; (2^27+1)*(2^26+1) ... use an exact-cancellation case
        a = f64(1.0 + 2.0 ** -52)
        b = f64(1.0 - 2.0 ** -53)
        c = f64(-1.0)
        # exact = 2^-53 - 2^-105
        got, _ = fp.ffma(a, b, c, fp.F64)
        self.assertEqual(f64v(got), 2.0 ** -53 - 2.0 ** -105)


class TestRoundingAndSpecials(unittest.TestCase):
    def test_directed_rounding(self):
        one, tiny = 0x3f800000, 0x33800000  # 1, 2^-24
        self.assertEqual(fp.fadd(one, tiny, fp.F32, fp.Policy(fp.RN))[0], one)
        self.assertEqual(fp.fadd(one, tiny, fp.F32, fp.Policy(fp.RD))[0], one)
        self.assertEqual(fp.fadd(one, tiny, fp.F32, fp.Policy(fp.RU))[0], 0x3f800001)
        self.assertEqual(fp.fadd(one, tiny, fp.F32, fp.Policy(fp.RZ))[0], one)
        self.assertEqual(fp.fadd(one | 0x80000000, tiny | 0x80000000, fp.F32, fp.Policy(fp.RD))[0], 0xbf800001)

    def test_exact_zero_sign(self):
        one, mone = 0x3f800000, 0xbf800000
        self.assertEqual(fp.fadd(one, mone, fp.F32)[0], 0x00000000)
        self.assertEqual(fp.fadd(one, mone, fp.F32, fp.Policy(fp.RD))[0], 0x80000000)
        self.assertEqual(fp.fadd(0x80000000, 0x80000000, fp.F32)[0], 0x80000000)
        self.assertEqual(fp.fadd(0x00000000, 0x80000000, fp.F32)[0], 0x00000000)

    def test_infinities_and_nans(self):
        inf, ninf = 0x7f800000, 0xff800000
        r, info = fp.fadd(inf, ninf, fp.F32)
        self.assertTrue(fp.is_nan(r, fp.F32))
        self.assertTrue(info.get("invalid"))
        self.assertEqual(fp.fadd(inf, 0x3f800000, fp.F32)[0], inf)
        r, info = fp.fmul(inf, 0, fp.F32)
        self.assertTrue(fp.is_nan(r, fp.F32) and info.get("invalid"))
        qnan = 0x7fc00007
        snan = 0x7f800007
        self.assertEqual(fp.fmul(qnan, 0x3f800000, fp.F32)[0], qnan)
        self.assertEqual(fp.fadd(0x3f800000, snan, fp.F32)[0], snan | 0x00400000)
        # overflow
        big = 0x7f7fffff
        self.assertEqual(fp.fmul(big, 0x40000000, fp.F32)[0], inf)
        self.assertEqual(fp.fmul(big, 0x40000000, fp.F32, fp.Policy(fp.RZ))[0], big)

    def test_subnormals_ftz_daz(self):
        minnorm, half = 0x00800000, 0x3f000000
        self.assertEqual(fp.fmul(minnorm, half, fp.F32)[0], 0x00400000)
        self.assertEqual(fp.fmul(minnorm, half, fp.F32, fp.Policy(ftz=True))[0], 0x00000000)
        self.assertEqual(fp.fmul(minnorm | 0x80000000, half, fp.F32, fp.Policy(ftz=True))[0], 0x80000000)
        # tiny_and_inexact rule keeps an exact subnormal
        self.assertEqual(fp.fmul(minnorm, half, fp.F32, fp.Policy(ftz=True, ftz_rule="tiny_and_inexact"))[0], 0x00400000)
        # DAZ: subnormal input is zero
        self.assertEqual(fp.fadd(0x00400000, 0x00000000, fp.F32, fp.Policy(daz=True))[0], 0x00000000)
        self.assertEqual(fp.fadd(0x00400000, 0x00400000, fp.F32)[0], 0x00800000)

    def test_conversions(self):
        self.assertEqual(fp.int_to_float(16777217, fp.F32)[0], f32(16777216.0))  # RNE tie to even
        self.assertEqual(fp.int_to_float(16777217, fp.F32, fp.Policy(fp.RU))[0], f32(16777218.0))
        self.assertEqual(fp.float_to_int(f32(2.5), fp.F32, fp.Policy(fp.RN)), (2, None))
        self.assertEqual(fp.float_to_int(f32(3.5), fp.F32, fp.Policy(fp.RN)), (4, None))
        self.assertEqual(fp.float_to_int(f32(-2.5), fp.F32, fp.Policy(fp.RZ)), (-2, None))
        self.assertEqual(fp.float_to_int(f32(-2.5), fp.F32, fp.Policy(fp.RD)), (-3, None))
        self.assertEqual(fp.float_to_int(f32(3e9), fp.F32, fp.Policy(fp.RN))[1], "invalid")
        self.assertEqual(fp.float_to_int(f32(3e9), fp.F32, fp.Policy(fp.RN), signed=False), (3000000000, None))

    def test_compare(self):
        self.assertEqual(fp.fcompare(f32(1.0), f32(2.0), fp.F32), "lt")
        self.assertEqual(fp.fcompare(0x00000000, 0x80000000, fp.F32), "eq")
        self.assertEqual(fp.fcompare(0x7fc00000, f32(1.0), fp.F32), "unordered")
        self.assertEqual(fp.fcompare(0x7f800000, f32(1e38), fp.F32), "gt")


if __name__ == "__main__":
    unittest.main()
