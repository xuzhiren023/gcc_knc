"""Exact IEEE binary32/binary64 arithmetic with explicit rounding, FTZ/DAZ and NaN policy.

Python's float is binary64 with round-to-nearest-even. It is NOT used as the IMCI
implementation here: every operation computes the exact rational result with
fractions.Fraction and rounds once, in the requested mode, to the target format.
Double rounding, FMA fusion, subnormals and signed zeros are therefore handled
explicitly. The tests compare against independent oracles (the double-rounding
theorem for binary32 add/mul via binary64, hand-derived FMA vectors).
"""
from fractions import Fraction
import struct

from .errors import Unsupported

RN, RD, RU, RZ = "rn", "rd", "ru", "rz"
ROUNDING_MODES = (RN, RD, RU, RZ)


class Fmt(object):
    __slots__ = ("bits", "mant", "expbits", "bias", "emax", "emin", "name")

    def __init__(self, name, bits, mant, expbits):
        self.name = name
        self.bits = bits
        self.mant = mant
        self.expbits = expbits
        self.bias = (1 << (expbits - 1)) - 1
        self.emax = self.bias
        self.emin = 1 - self.bias

    @property
    def sign_bit(self):
        return 1 << (self.bits - 1)

    @property
    def mant_mask(self):
        return (1 << self.mant) - 1

    @property
    def exp_mask(self):
        return (1 << self.expbits) - 1

    @property
    def quiet_bit(self):
        return 1 << (self.mant - 1)

    @property
    def default_nan(self):
        return self.sign_bit | (self.exp_mask << self.mant) | self.quiet_bit

    @property
    def inf(self):
        return self.exp_mask << self.mant

    @property
    def max_finite(self):
        return ((self.exp_mask - 1) << self.mant) | self.mant_mask


F32 = Fmt("f32", 32, 23, 8)
F64 = Fmt("f64", 64, 52, 11)


class Policy(object):
    """Numerical policy of one operation: rounding, flush-to-zero, denormals-are-zero."""
    __slots__ = ("rounding", "ftz", "daz", "ftz_rule")

    def __init__(self, rounding=RN, ftz=False, daz=False, ftz_rule="tiny"):
        if rounding not in ROUNDING_MODES:
            raise Unsupported("rounding mode %r not supported (rn, rd, ru, rz)" % rounding)
        if ftz_rule not in ("tiny_and_inexact", "tiny"):
            raise Unsupported("ftz rule %r not supported" % ftz_rule)
        self.rounding = rounding
        self.ftz = ftz
        self.daz = daz
        self.ftz_rule = ftz_rule


DEFAULT_POLICY = Policy()

# --- classification --------------------------------------------------------

NAN, INF, ZERO, NUM = "nan", "inf", "zero", "num"


def classify(bits, fmt, policy=DEFAULT_POLICY):
    """Return (kind, sign, value). value: Fraction for NUM, payload bits for NAN, None otherwise."""
    bits &= (1 << fmt.bits) - 1
    sign = 1 if bits & fmt.sign_bit else 0
    e = (bits >> fmt.mant) & fmt.exp_mask
    m = bits & fmt.mant_mask
    if e == fmt.exp_mask:
        if m == 0:
            return INF, sign, None
        return NAN, sign, bits
    if e == 0:
        if m == 0:
            return ZERO, sign, None
        if policy.daz:
            return ZERO, sign, None
        # subnormal
        val = Fraction(m, 1 << (fmt.mant - fmt.emin))
        return NUM, sign, -val if sign else val
    val = Fraction(m + (1 << fmt.mant), 1 << fmt.mant) * (Fraction(2) ** (e - fmt.bias))
    return NUM, sign, -val if sign else val


def is_nan(bits, fmt):
    return classify(bits, fmt)[0] == NAN


def is_snan(bits, fmt):
    k, _, _ = classify(bits, fmt)
    return k == NAN and not (bits & fmt.quiet_bit)


def quiet(bits, fmt):
    return bits | fmt.quiet_bit


# --- rounding ---------------------------------------------------------------

def _floor_log2(fr):
    """floor(log2(fr)) for a positive Fraction."""
    n, d = fr.numerator, fr.denominator
    e = n.bit_length() - d.bit_length()
    # 2^e <= n/d < 2^(e+2); fix up
    if e >= 0:
        if n < d << e:
            e -= 1
    else:
        if n << (-e) < d:
            e -= 1
    return e


def round_exact(x, fmt, policy=DEFAULT_POLICY, zero_sign=0):
    """Round an exact Fraction to fmt bits. Returns (bits, flags) where flags is a set of
    'inexact', 'underflow', 'overflow'. zero_sign is used only when x == 0."""
    flags = set()
    if x == 0:
        return (fmt.sign_bit if zero_sign else 0), flags
    sign = 1 if x < 0 else 0
    ax = -x if sign else x
    e = _floor_log2(ax)
    if e < fmt.emin:
        quantum_exp = fmt.emin - fmt.mant  # subnormal spacing
        tiny_candidate = True
    else:
        quantum_exp = e - fmt.mant
        tiny_candidate = False
    scaled = ax / (Fraction(2) ** quantum_exp)  # exact, >= 2^mant for normals
    q, r = divmod(scaled.numerator, scaled.denominator)
    rem = Fraction(r, scaled.denominator)  # in [0,1)
    inexact = rem != 0
    if inexact:
        flags.add("inexact")
        mode = policy.rounding
        if mode == RN:
            if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and (q & 1)):
                q += 1
        elif mode == RZ:
            pass
        elif mode == RD:
            if sign:
                q += 1
        elif mode == RU:
            if not sign:
                q += 1
    # renormalize after rounding
    if not tiny_candidate:
        if q == (1 << (fmt.mant + 1)):
            q >>= 1
            e += 1
        if e > fmt.emax:
            flags.add("overflow")
            flags.add("inexact")
            mode = policy.rounding
            to_inf = (mode == RN) or (mode == RU and not sign) or (mode == RD and sign)
            bits = fmt.inf if to_inf else fmt.max_finite
            return (bits | (fmt.sign_bit if sign else 0)), flags
        bits = ((e + fmt.bias) << fmt.mant) | (q - (1 << fmt.mant))
    else:
        # subnormal range; q may have rounded up to the minimum normal
        if q >= (1 << fmt.mant):
            bits = (1 << fmt.mant) | (q - (1 << fmt.mant))  # e field = 1, mantissa bits
            # tininess detected after rounding: a result that rounds up to the min normal is not tiny
            if inexact:
                flags.add("inexact")
        else:
            tiny = True
            if inexact:
                flags.add("underflow")
            if policy.ftz and tiny and (policy.ftz_rule == "tiny" or inexact):
                flags.add("underflow")
                return (fmt.sign_bit if sign else 0), flags
            bits = q  # e field 0
    return (bits | (fmt.sign_bit if sign else 0)), flags


# --- arithmetic ---------------------------------------------------------------

def _nan_result(operands, fmt, invalid):
    """x86-style: first NaN operand (quieted) wins; invalid operation gives the default NaN."""
    for b in operands:
        k, _, _ = classify(b, fmt)
        if k == NAN:
            return quiet(b, fmt)
    if invalid:
        return fmt.default_nan
    return None


def _zero_sign_for_sum(signs, policy):
    """Sign of an exact zero sum. Both operands zero with equal sign keep it; otherwise +0 (RD: -0)."""
    if len(set(signs)) == 1:
        return signs[0]
    return 1 if policy.rounding == RD else 0


def fadd(a, b, fmt, policy=DEFAULT_POLICY, negate_b=False):
    ka, sa, va = classify(a, fmt, policy)
    kb, sb, vb = classify(b, fmt, policy)
    if negate_b:
        sb ^= 1
        if kb == NUM:
            vb = -vb
        b ^= fmt.sign_bit
    if ka == NAN or kb == NAN:
        return _nan_result([a, b], fmt, False), {"invalid": False}
    if ka == INF and kb == INF:
        if sa != sb:
            return fmt.default_nan, {"invalid": True}
        return a, {}
    if ka == INF:
        return a, {}
    if kb == INF:
        return b, {}
    if ka == ZERO and kb == ZERO:
        zs = _zero_sign_for_sum([sa, sb], policy)
        return (fmt.sign_bit if zs else 0), {}
    xa = va if ka == NUM else Fraction(0)
    xb = vb if kb == NUM else Fraction(0)
    s = xa + xb
    if s == 0:
        # exact cancellation of nonzero operands
        zs = 1 if policy.rounding == RD else 0
        return (fmt.sign_bit if zs else 0), {}
    bits, flags = round_exact(s, fmt, policy)
    return bits, {"flags": sorted(flags)}


def fsub(a, b, fmt, policy=DEFAULT_POLICY):
    return fadd(a, b, fmt, policy, negate_b=True)


def fmul(a, b, fmt, policy=DEFAULT_POLICY):
    ka, sa, va = classify(a, fmt, policy)
    kb, sb, vb = classify(b, fmt, policy)
    if ka == NAN or kb == NAN:
        return _nan_result([a, b], fmt, False), {}
    sign = sa ^ sb
    if (ka == INF and kb == ZERO) or (ka == ZERO and kb == INF):
        return fmt.default_nan, {"invalid": True}
    if ka == INF or kb == INF:
        return fmt.inf | (fmt.sign_bit if sign else 0), {}
    if ka == ZERO or kb == ZERO:
        return (fmt.sign_bit if sign else 0), {}
    bits, flags = round_exact(va * vb, fmt, policy)
    return bits, {"flags": sorted(flags)}


def ffma(a, b, c, fmt, policy=DEFAULT_POLICY, negate_product=False, negate_c=False):
    """Fused a*b + c with a single rounding. negate_product gives -(a*b)+c (fnmadd);
    negate_c gives a*b - c (fmsub)."""
    ka, sa, va = classify(a, fmt, policy)
    kb, sb, vb = classify(b, fmt, policy)
    kc, sc, vc = classify(c, fmt, policy)
    if negate_c:
        sc ^= 1
        if kc == NUM:
            vc = -vc
        c ^= fmt.sign_bit
    if ka == NAN or kb == NAN or kc == NAN:
        return _nan_result([a, b, c], fmt, False), {}
    psign = sa ^ sb ^ (1 if negate_product else 0)
    if (ka == INF and kb == ZERO) or (ka == ZERO and kb == INF):
        return fmt.default_nan, {"invalid": True}
    if ka == INF or kb == INF:
        if kc == INF and sc != psign:
            return fmt.default_nan, {"invalid": True}
        return fmt.inf | (fmt.sign_bit if psign else 0), {}
    if kc == INF:
        return c, {}
    if ka == ZERO or kb == ZERO:
        # product is an exact zero of sign psign
        if kc == ZERO:
            zs = _zero_sign_for_sum([psign, sc], policy)
            return (fmt.sign_bit if zs else 0), {}
        bits, flags = round_exact(vc, fmt, policy)
        return bits, {"flags": sorted(flags)}
    p = va * vb
    if negate_product:
        p = -p
    s = p + (vc if kc == NUM else Fraction(0))
    if s == 0:
        if kc == ZERO:
            # p is nonzero here, so s != 0; unreachable, kept for clarity
            pass
        zs = 1 if policy.rounding == RD else 0
        return (fmt.sign_bit if zs else 0), {}
    bits, flags = round_exact(s, fmt, policy)
    return bits, {"flags": sorted(flags)}


# --- comparisons --------------------------------------------------------------

def fcompare(a, b, fmt, policy=DEFAULT_POLICY):
    """Return 'lt', 'eq', 'gt' or 'unordered'."""
    ka, sa, va = classify(a, fmt, policy)
    kb, sb, vb = classify(b, fmt, policy)
    if ka == NAN or kb == NAN:
        return "unordered"

    def key(k, s, v):
        if k == INF:
            return Fraction(-1 if s else 1) * Fraction(10) ** 400
        if k == ZERO:
            return Fraction(0)
        return v
    xa, xb = key(ka, sa, va), key(kb, sb, vb)
    if xa < xb:
        return "lt"
    if xa > xb:
        return "gt"
    return "eq"


# --- conversions ----------------------------------------------------------------

def int_to_float(i, fmt, policy=DEFAULT_POLICY):
    bits, flags = round_exact(Fraction(i), fmt, policy)
    return bits, {"flags": sorted(flags)}


def float_to_int(bits, fmt, policy, signed=True, width=32):
    """Convert with the policy's rounding mode. Out of range or NaN -> (None, 'invalid')."""
    k, s, v = classify(bits, fmt, policy)
    if k == NAN:
        return None, "invalid"
    if k == INF:
        return None, "invalid"
    if k == ZERO:
        return 0, None
    mode = policy.rounding
    n, d = v.numerator, v.denominator
    q, r = divmod(n, d)  # floor division for negatives
    if r:
        if mode == RN:
            twice = 2 * r
            if twice > d or (twice == d and (q & 1)):
                q += 1
        elif mode == RU:
            q += 1
        elif mode == RZ:
            if v < 0:
                q += 1
        # RD: floor already
    if signed:
        lo, hi = -(1 << (width - 1)), (1 << (width - 1)) - 1
    else:
        lo, hi = 0, (1 << width) - 1
    if q < lo or q > hi:
        return None, "invalid"
    return q, None


# --- Python float helpers (for fixtures and oracles only, not the engine) ----------

def f32_bits_from_float(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def float_from_f32_bits(b):
    return struct.unpack("<f", struct.pack("<I", b & 0xFFFFFFFF))[0]


def f64_bits_from_float(x):
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def float_from_f64_bits(b):
    return struct.unpack("<d", struct.pack("<Q", b & 0xFFFFFFFFFFFFFFFF))[0]


def fmt_bits(bits, fmt):
    k, s, v = classify(bits, fmt)
    if k == NAN:
        return "nan(0x%x)" % bits
    if k == INF:
        return "-inf" if s else "inf"
    if k == ZERO:
        return "-0.0" if s else "0.0"
    return repr(float_from_f32_bits(bits) if fmt is F32 else float_from_f64_bits(bits))
