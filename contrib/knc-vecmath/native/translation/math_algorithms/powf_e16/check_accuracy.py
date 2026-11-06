"""Fresh, bounded binary-powf assay using the project's exact IEEE helpers.

This invokes only the new pointer algorithm on the Windows SSE2 host. Decimal
power at two precisions supplies independent reference intervals; neither the
candidate's reduction/tables nor a scalar libm pow is used by the oracle.
"""
from __future__ import annotations
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from HostMathReference import bits_fraction, fraction_bits, ulp_fraction
from ProjectHostCompiler import environment, posix


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def nan(word):
    return (word & 0x7fffffff) > 0x7f800000


def signaling(word):
    return nan(word) and not (word & 0x400000)


@lru_cache(maxsize=None)
def reference(xb, yb):
    """Return rounded bits/None-for-NaN, interval and mandatory severe flags.

    Severity names deliberately exclude inexact/underflow when the rounded
    result is finite: intermediate inexact and tininess conventions are not
    inferred from an output bit pattern.
    """
    xm, ym = xb & 0x7fffffff, yb & 0x7fffffff
    if not ym:
        return (None, None, {"invalid"}) if signaling(xb) else (0x3f800000, (Fraction(1), Fraction(1)), set())
    if xb == 0x3f800000:
        return (None, None, {"invalid"}) if signaling(yb) else (0x3f800000, (Fraction(1), Fraction(1)), set())
    if nan(xb) or nan(yb):
        return None, None, {"invalid"} if signaling(xb) or signaling(yb) else set()
    if ym == 0x7f800000:
        word = 0x3f800000 if xm == 0x3f800000 else (0 if ((xm < 0x3f800000) == (not (yb >> 31))) else 0x7f800000)
        return word, None, set()
    y = bits_fraction(yb)
    integer = y.denominator == 1
    odd = integer and bool(y.numerator & 1)
    sign = 0x80000000 if xb >> 31 and odd else 0
    if xm in (0, 0x7f800000):
        word = sign | (0 if ((xm == 0) == (y > 0)) else 0x7f800000)
        return word, None, {"divbyzero"} if not xm and y < 0 else set()
    if xb >> 31 and not integer:
        return None, None, {"invalid"}
    x = abs(bits_fraction(xb))
    negative = bool(sign)
    if integer and abs(y) <= 256:
        exact = x ** int(y)
        if negative:
            exact = -exact
        rounded = fraction_bits(exact, negative_zero=negative)
        flags = {"overflow"} if (rounded & 0x7fffffff) == 0x7f800000 else set()
        return rounded, (exact, exact), flags
    if x == 1:
        exact = Fraction(-1 if negative else 1)
        return fraction_bits(exact), (exact, exact), set()
    intervals, rounded = [], []
    # Input conversion is exact (all binary32 values fit exactly in binary64).
    dx = Decimal.from_float(abs(struct.unpack("<f", struct.pack("<I", xb))[0]))
    dy = Decimal.from_float(struct.unpack("<f", struct.pack("<I", yb))[0])
    # Avoid materializing astronomical powers from finite raw-y specials. These
    # margins lie at least a full binary exponent beyond any binary32 rounding
    # boundary; a100-digit log bound resolves only the obvious range cases.
    with localcontext() as ctx:
        ctx.prec = 100
        logarithm = dx.ln() * dy
        ln2 = Decimal(2).ln()
        if logarithm > 129 * ln2:
            return sign | 0x7f800000, None, {"overflow"}
        if logarithm < -151 * ln2:
            return sign, None, {"underflow"}
    for precision in (100, 160):
        with localcontext() as ctx:
            ctx.prec = precision
            center_decimal = ctx.power(dx, dy)
            center = Fraction(*center_decimal.as_integer_ratio())
            # Decimal's C power is almost always correctly rounded. Four last
            # places enclose its documented <1ULP error, with a second precision
            # and a nesting/rounding check rather than a binary64 conversion.
            quantum = 4 * Fraction(10) ** center_decimal.as_tuple().exponent
            lo, hi = center - quantum, center + quantum
            if negative:
                lo, hi = -hi, -lo
        ends = (fraction_bits(lo, negative_zero=negative), fraction_bits(hi, negative_zero=negative))
        if ends[0] != ends[1]:
            raise ArithmeticError("pow reference straddles a binary32 rounding boundary")
        intervals.append((lo, hi))
        rounded.append(ends[0])
    if rounded[0] != rounded[1] or not (intervals[0][0] <= intervals[1][0] <= intervals[1][1] <= intervals[0][1]):
        raise ArithmeticError("pow reference precision intervals disagree")
    flags = {"overflow"} if (rounded[0] & 0x7fffffff) == 0x7f800000 else set()
    return rounded[0], intervals[1], flags


def corpus():
    rng = random.Random(0x504f5746453136)
    pairs = []
    # Directed reduction/exponent/subnormal boundaries, integer parity, signs,
    # overflow/underflow and the especially sensitive near-one/large-y domain.
    xs = [1, 2, 3, 0x007fffff, 0x00800000, 0x00800001, 0x3f32ffff,
          0x3f330000, 0x3f330001, 0x3f7fffff, 0x3f800000, 0x3f800001,
          0x3fffffff, 0x40000000, 0x40000001, 0x7f7ffffe, 0x7f7fffff]
    ys = [bits(v) for v in [-150., -149.5, -149., -128., -32., -3., -2., -1.5,
                            -1., -0.5, -2**-20, 0., 2**-20, .5, 1., 1.5, 2.,
                            3., 32., 126., 127., 127.5, 128., 149., 150.]]
    for x in xs:
        pairs.extend((x, y) for y in ys)
        pairs.extend((x | 0x80000000, bits(float(y))) for y in range(-9, 10))
    for _ in range(32768):
        category = rng.randrange(4)
        if category == 0:
            x = rng.randrange(1, 0x7f800000)
            y = bits(rng.uniform(-2, 2))
        elif category == 1:
            x = 0x3f800000 + rng.randrange(-8192, 8193)
            y = bits(rng.uniform(-16384, 16384))
        elif category == 2:
            x = rng.randrange(1, 0x00800000)
            y = bits(rng.uniform(-1, 1))
        else:
            x = rng.randrange(1, 0x7f800000)
            if rng.randrange(2):
                x |= 0x80000000
            y = bits(float(rng.randrange(-16, 17)))
        pairs.append((x, y))
    specials = [0, 0x80000000, 1, 0x80000001, 0x00800000, 0x80800000,
                0x3f000000, 0xbf000000, 0x3f800000, 0xbf800000, 0x40000000,
                0xc0000000, 0x7f7fffff, 0xff7fffff, 0x7f800000, 0xff800000,
                0x7fc12345, 0xffc12345, 0x7f812345, 0xff812345]
    pairs.extend((x, y) for x in specials for y in specials)
    while len(pairs) % 16:
        pairs.append((0x3f800000, 0))
    rows = []
    for start in range(0, len(pairs), 16):
        block = pairs[start:start+16]
        rows.append((65535, (start//16) % 4, [p[0] for p in block], [p[1] for p in block], [rng.getrandbits(32) for _ in block]))
    # Every mask and alias class: inactive lane poison includes signaling NaN,
    # negative-domain inputs, zero-negative powers, overflow and underflow.
    poison = [(0x7f812345, 0x3f800000), (0xbf800000, 0x3f000000), (0, 0xbf800000),
              (0x7f7fffff, 0x7f7fffff), (1, 0x7f7fffff)]
    masks = [0, 65535, 0x5555, 0xaaaa] + [1 << i for i in range(16)] + [65535 ^ (1 << i) for i in range(16)]
    for mask in masks:
        for mode in range(4):
            x, y = [], []
            for lane in range(16):
                pair = (bits(2.), bits(3.)) if mask & (1 << lane) else poison[(lane+mode) % len(poison)]
                x.append(pair[0]); y.append(pair[1])
            rows.append((mask, mode, x, y, [rng.getrandbits(32) for _ in range(16)]))
    return rows


def million_corpus():
    """New deterministic broad corpus; it does not replay the35k screening."""
    rng = random.Random(0x504f57464d504652)
    pairs = []
    for i in range(1048576):
        category = i & 3
        if category == 0:
            x = rng.randrange(1, 0x7f800000)
            y = bits(rng.uniform(-1, 1))
        elif category == 1:
            x = rng.randrange(1, 0x7f800000)
            y = bits((1 if rng.randrange(2) else -1) * rng.uniform(.25, .75))
        elif category == 2:
            x = 0x3f800000 + rng.randrange(-8192, 8193)
            y = bits(rng.uniform(-16384, 16384))
        else:
            x = rng.randrange(1, 0x7f800000) | 0x80000000
            y = bits(float(rng.randrange(-2, 3)))
        pairs.append((x, y))
    # All finite binary32 exponent/sign bins of BOTH operands, including tiny
    # and enormous y. These include easy range outcomes; the oracle reports
    # zeros/infinities separately instead of calling them difficult accuracy.
    for _ in range(262144):
        x = rng.randrange(1, 0x7f800000)
        if rng.randrange(2):
            x |= 0x80000000
        y = rng.randrange(0, 0x7f800000) | (rng.randrange(2) << 31)
        pairs.append((x, y))
    # Fresh NaN payloads, integer parity edges, subnormal and range boundaries.
    for i in range(4096):
        x = [rng.randrange(1, 0x00800000), 0x80000000, 0x7f800000, 0xff800000,
             0x7f800000 | rng.randrange(1, 0x800000), 0xff800000 | rng.randrange(1, 0x800000),
             0xbf800000, 0x3f800000][i & 7]
        y = [0, 0x80000000, 0x7f800000, 0xff800000, 0x7f800000 | rng.randrange(1, 0x800000),
             0x4b7fffff, 0x4b800000, 0xcb800001, bits(rng.uniform(-150, 150))][(i//8) % 9]
        pairs.append((x, y))
    rows = []
    for start in range(0, len(pairs), 16):
        block = pairs[start:start+16]
        rows.append((65535, (start//16) % 4, [p[0] for p in block], [p[1] for p in block], [rng.getrandbits(32) for _ in block]))
    return rows


def write_input(path, rows):
    with path.open("wb") as stream:
        stream.write(struct.pack("<8I", 0x49575050, 1, 16, 208, len(rows), 0, 0, 0))
        for index, (mask, mode, x, y, merge) in enumerate(rows):
            stream.write(struct.pack("<QII48I", index, mask, mode, *x, *y, *merge))


def inspect_output(path, rows, flags):
    hist, special_counts = Counter(), Counter()
    maximum = Fraction(0)
    worst = None
    active_count = merge_count = 0
    with path.open("rb") as stream:
        if stream.read(32) != struct.pack("<8I", 0x4f575050, 1, 16, 88, len(rows), 0, 0, 0):
            raise ValueError("wrong output header")
        for index, (mask, mode, x, y, merge) in enumerate(rows):
            raw = stream.read(88)
            if len(raw) != 88:
                raise ValueError("truncated output")
            fields = struct.unpack("<QII18I", raw)
            if fields[:3] != (index, mask, mode):
                raise ValueError("wrong output record identity")
            output, observed_flags, mxcsr = fields[3:19], fields[19], fields[20]
            if (mxcsr & ~63) != 0x1f80:
                raise ValueError("changed MXCSR control bits")
            mandatory = set()
            for lane, got in enumerate(output):
                if not mask & (1 << lane):
                    merge_count += 1
                    if got != merge[lane]:
                        raise ValueError("inactive merge bits changed")
                    continue
                active_count += 1
                expected, interval, required = reference(x[lane], y[lane])
                mandatory |= required
                if expected is None:
                    if not nan(got) or not got & 0x400000:
                        raise ValueError("special NaN classification/quieting mismatch")
                    special_counts["NaN"] += 1
                elif (expected & 0x7fffffff) == 0x7f800000 or interval is None:
                    if got != expected:
                        raise ValueError(f"special bits mismatch row{index}lane{lane}: {got:08x}!={expected:08x}")
                    special_counts["directOrInfinity"] += 1
                else:
                    if (got & 0x7fffffff) >= 0x7f800000:
                        raise ValueError("nonfinite result for finite reference")
                    value = bits_fraction(got)
                    # Reference spacing is the binary32 ULP at the exact
                    # result, inferred from the correctly rounded reference.
                    error = max(abs(value-interval[0]), abs(value-interval[1])) / ulp_fraction(expected)
                    if error > maximum:
                        maximum, worst = error, {"row": index, "lane": lane, "x": f"{x[lane]:08x}", "y": f"{y[lane]:08x}", "actual": f"{got:08x}", "nearest": f"{expected:08x}"}
                    hist["<=0.5" if error <= Fraction(1, 2) else "<=0.75" if error <= Fraction(3, 4) else "<=1" if error <= 1 else ">1"] += 1
                    if error > 1:
                        raise ValueError(f"powf exceeded1ULP: {worst}, {float(error)}")
                    if not expected and got != expected:
                        raise ValueError("zero sign mismatch")
            for severe in ("invalid", "divbyzero"):
                if bool(observed_flags & flags[severe]) != (severe in mandatory):
                    raise ValueError(f"{severe} flag mismatch row{index}")
            if "overflow" in mandatory and not observed_flags & flags["overflow"]:
                raise ValueError(f"missing overflow flag row{index}")
            if "underflow" in mandatory and not observed_flags & flags["underflow"]:
                raise ValueError(f"missing underflow flag row{index}")
            if mask == 0 or index >= len(rows)-144:
                # Last144 rows contain only exact2^3 or masked poison.
                if observed_flags or mxcsr & 63:
                    raise ValueError("inactive poison produced FP flags")
            if mask and all(((x[i], y[i]) == (bits(2.), bits(3.))) for i in range(16) if mask & (1 << i)):
                special_counts["exactMaskedVectors"] += 1
        if stream.read(1):
            raise ValueError("trailing output")
    return {"packets": len(rows), "activeLanes": active_count, "mergeLanes": merge_count,
            "maxUlpBound": float(maximum), "worst": worst, "ulpHistogram": dict(hist),
            "specialCounts": dict(special_counts), "metadataMergeFlagMismatches": 0}


def main():
    million = sys.argv[1:] == ["--mpfr-million"]
    if sys.argv[1:] and not million:
        raise SystemExit("only --mpfr-million is supported")
    output = ROOT / "artifacts/test-state/host-powf-e16" / uuid.uuid4().hex
    output.mkdir(parents=True)
    record = {"status": "Running", "hostOnly": True, "gatePassed": False, "targetQualified": False,
              "family": ["__knc_vmath_powf_16", "__knc_vmath_powf_8", "__knc_vmath_powf_4"],
              "artifacts": str(output), "commands": [], "variants": {}, "profile": "baseline x86-64/SSE2; nearest-even/masked/FTZ-DAZ-off; strict flags; no FMA"}
    started = time.time()
    try:
        rows = million_corpus() if million else corpus()
        inp = output / "input.bin"; write_input(inp, rows)
        env = environment()
        compiler = ROOT / ".tools/knc-bootstrap/cygwin/bin/gcc.exe"
        upstream = ROOT / "native/upstream/arm-optimized-routines-v26.01-dp/math"
        expdata = ROOT / "native/upstream/arm-optimized-routines-v26.01/math/exp2f_data.c"
        common = ["-std=c11", "-O3", "-march=x86-64", "-mno-avx", "-mno-avx2", "-mno-fma", "-mno-avx512f", "-fno-fast-math", "-fmath-errno", "-frounding-math", "-ftrapping-math", "-fsignaling-nans", "-Wall", "-Wextra", "-Werror", "-Wno-error=attributes", "-DHAVE_FAST_FMA=0", "-I"+posix(HERE), "-I"+posix(upstream)]
        sources = [HERE / "host_assay.c", HERE / "powf_e16.c", HERE / "upstream/powf_log2_data.c", expdata]
        def run(args, timeout=90):
            result = subprocess.run([str(a) for a in args], cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout)
            record["commands"].append({"argv": [str(a) for a in args], "exit": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
            if result.returncode:
                raise RuntimeError(f"command exited{result.returncode}: {result.stderr[-1000:]}")
            return result.stdout
        mpfr = output / "mpfr-oracle.exe"
        if million:
            run([compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-Wno-misleading-indentation", posix(HERE / "mpfr_reference.c"), "-lmpfr", "-lgmp", "-o", posix(mpfr)])
            record["reference"] = {"kind": "MPFR directed pow endpoints", "precisions": [256, 384], "executableSha256": sha(mpfr), "sourceSha256": sha(HERE / "mpfr_reference.c")}
        for contraction in ("off", "fast"):
            exe = output / ("powf-"+contraction+".exe")
            run([compiler, *common, "-ffp-contract="+contraction, *map(posix, sources), "-o", posix(exe)])
            capabilities = json.loads(run([exe, "--capabilities"]))
            if not capabilities["avx2"] or capabilities["avx512f"] or capabilities["mxcsr"] != 0x1f80 or capabilities["rounding"]:
                raise ValueError("unadmitted host profile")
            if "INVALID_MASK_ZERO_FP_UNCHANGED" not in run([exe, "--invalid-mask"]):
                raise ValueError("invalid mask control missing")
            raw = output / ("powf-"+contraction+".bin")
            run([exe, posix(inp), posix(raw)])
            result = json.loads(run([mpfr, posix(inp), posix(raw)], timeout=300)) if million else inspect_output(raw, rows, capabilities["flags"])
            assembly = output / ("powf-"+contraction+".s")
            run([compiler, *common, "-ffp-contract="+contraction, "-S", posix(HERE / "powf_e16.c"), "-o", posix(assembly)])
            text = assembly.read_text()
            if re.search(r"\b(?:call|jmp)\s+_?(?:powf?|log2?f?|exp2?f?)\b", text):
                raise ValueError("scalar math delegation detected")
            vector = len(re.findall(r"\b(?:add|sub|mul|div)p[sd]\s+[^\n]*%xmm", text))
            if not vector:
                raise ValueError("no packed SSE2 arithmetic in algorithm")
            if re.search(r"%[yz]mm|%k[0-7]", text):
                raise ValueError("wide register in baseline host profile")
            result.update({"capabilities": capabilities, "packedSseArithmeticLines": vector, "binarySha256": sha(exe), "rawSha256": sha(raw), "assemblySha256": sha(assembly)})
            # A completed wrong-result stream must fail through the actual
            # independent validator; malformed/truncated output is separate.
            mutant = bytearray(raw.read_bytes()); mutant[32+16+3] ^= 0x40
            bad = output / ("wrong-"+contraction+".bin"); bad.write_bytes(mutant)
            if million:
                negative = subprocess.run([str(mpfr), posix(inp), posix(bad)], cwd=ROOT, env=env, text=True, capture_output=True, timeout=90)
                record["commands"].append({"argv": [str(mpfr), posix(inp), posix(bad)], "exit": negative.returncode, "stdout": negative.stdout, "stderr": negative.stderr, "expectedMismatchExit": [6, 8]})
                if negative.returncode not in (6, 8):
                    raise ValueError("completed wrong-result control did not fail numerically")
                result["completedWrongResultRejected"] = True
            else:
                try:
                    inspect_output(bad, rows, capabilities["flags"])
                except ValueError:
                    result["completedWrongResultRejected"] = True
                else:
                    raise ValueError("wrong-result control was not rejected")
            record["variants"][contraction] = result
        record["status"] = "MillionInputHostPowfAlgorithmChecked" if million else "BoundedHostPowfAlgorithmChecked"
    except Exception as error:
        record["status"] = "Stopped"
        record["error"] = f"{type(error).__name__}: {error}"
    record["elapsedSeconds"] = time.time()-started
    tracked = [HERE / "powf_e16.c", HERE / "powf_e16.h", HERE / "host_assay.c", HERE / "mpfr_reference.c", Path(__file__), HERE / "upstream/powf_log2_data.c", HERE / "upstream/powf.c"]
    snapshot = output / "sources"; snapshot.mkdir()
    for path in tracked:
        destination = snapshot / ("upstream-"+path.name if path.parent.name == "upstream" else path.name)
        shutil.copyfile(path, destination)
    record["sourceSha256"] = {str(path.relative_to(ROOT)): sha(path) for path in tracked}
    (output / "accuracy.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "artifact": str(output / "accuracy.json"), "variants": record["variants"], "error": record.get("error")}, indent=2))
    return 0 if record["status"] in ("BoundedHostPowfAlgorithmChecked", "MillionInputHostPowfAlgorithmChecked") else 1


if __name__ == "__main__":
    raise SystemExit(main())
