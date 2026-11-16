"""Costed stubs for calls that leave the region.

A callee that is not part of the simulated region must be declared in the kernel:

  "calls": {"exp": {"cycles": 180, "model": "libm.f64.exp", "status": "measured", "source": "..."},
            "__assert_fail": {"model": "noreturn"},
            "memcpy": {"cycles": 40, "cycles_per_byte": 0.25, "model": "memcpy", "status": "assumed"}}

cycles          core cycles the calling context is stalled (required for timing; no default)
cycles_per_byte added per byte for the mem* models
model           functional effect:
                  noreturn        reaching the call is an error (assert/abort paths)
                  none            no functional effect (results after the call are NOT exact)
                  memcpy memmove memset    exact (rdi, rsi, rdx; returns rdi in rax)
                  malloc calloc realloc free    declared init.heap bump allocator; free is a no-op
                  libm.f64.NAME / libm.f32.NAME   argument(s) in the low element of zmm0 (zmm1),
                                  result in the low element of zmm0 (K1OM calling convention).
                                  sqrt fabs floor ceil trunc fmin fmax copysign are exact;
                                  the others use the host math library and are NOT bit-exact
                                  with the card's libm (reported as approximate)

A stub never gets a default cost. mem*, calloc and realloc trace their byte effects;
allocator internal memory traffic is not modeled.
"""
import math
import struct

from .errors import InvalidInput, Unsupported
from . import fp
from .util import parse_int

_EXACT1 = {"fabs": abs, "floor": math.floor, "ceil": math.ceil, "trunc": math.trunc}
_APPROX1 = ("exp", "log", "log10", "log2", "sin", "cos", "tan", "tanh", "sinh", "cosh", "atan", "asin", "acos", "expm1", "log1p", "erf", "erfc", "cbrt")
_APPROX2 = ("pow", "atan2", "fmod", "hypot")


def _f64_low(cx, reg):
    lanes = cx.zmm[reg]
    return struct.unpack("<d", struct.pack("<II", lanes[0], lanes[1]))[0], lanes[0] | (lanes[1] << 32)


def _set_f64_low(cx, reg, bits):
    lanes = list(cx.zmm[reg])
    lanes[0], lanes[1] = bits & 0xFFFFFFFF, (bits >> 32) & 0xFFFFFFFF
    cx.zmm[reg] = lanes


def _f32_low(cx, reg):
    b = cx.zmm[reg][0]
    return struct.unpack("<f", struct.pack("<I", b))[0], b


def _set_f32_low(cx, reg, bits):
    lanes = list(cx.zmm[reg])
    lanes[0] = bits & 0xFFFFFFFF
    cx.zmm[reg] = lanes


def _heap_call(interp, cx, model, trace_mem):
    """Functional scenario allocator, not a model of the card's libc internals."""
    if model == "free":
        interp.assume("heap stubs: free is a no-op; storage is never reused")
        return
    if interp.heap is None:
        spec = interp.kernel.init.get("heap")
        if not isinstance(spec, dict) or "addr" not in spec or "size" not in spec:
            raise InvalidInput("heap stubs require init.heap with addr and size")
        start = parse_int(spec["addr"], "init.heap.addr")
        size = parse_int(spec["size"], "init.heap.size")
        if start <= 0 or size <= 0 or start + size > (1 << 64):
            raise InvalidInput("init.heap must be a nonempty non-null 64-bit address range")
        interp.heap = {"next": (start + 63) & ~63, "end": start + size, "sizes": {}}
        interp.assume("heap stubs use a shared declared init.heap, 64-byte aligned bump allocations, no address reuse; caller must keep the heap disjoint from other memory; allocator internals and allocator cache traffic are not modeled")
    heap = interp.heap
    old = 0
    n = cx.gpr["rdi"]
    if model == "calloc":
        n *= cx.gpr["rsi"]
        if n >= (1 << 64):
            raise InvalidInput("calloc size overflow")
    elif model == "realloc":
        old, n = n, cx.gpr["rsi"]
        if old and old not in heap["sizes"]:
            raise InvalidInput("realloc pointer is not a recorded heap allocation")
        if old and n == 0:
            cx.gpr["rax"] = 0
            interp.assume("realloc(p, 0) returns null and retains the old storage in this bump-allocator scenario")
            return
    addr = heap["next"]
    # Zero-sized allocations still occupy one aligned slot and return distinct pointers.
    if addr + max(1, n) > heap["end"]:
        raise InvalidInput("declared init.heap exhausted allocating %d bytes" % n)
    copied = min(heap["sizes"].get(old, 0), n)
    if (model == "calloc" and n > (1 << 26)) or copied > (1 << 26):
        raise InvalidInput("heap stub memory effect exceeds the 64 MiB per-call limit")
    if model == "calloc" and n:
        interp.memory.write(addr, bytes(n), cx.ctx)
        trace_mem.append((addr, n))
    elif copied:
        data = interp.memory.read(old, copied, cx.ctx)
        interp.memory.write(addr, data, cx.ctx)
        trace_mem.extend(((old, copied), (addr, copied)))
    heap["next"] = (addr + max(1, n) + 63) & ~63
    heap["sizes"][addr] = n
    interp.heap_allocations.append({"model": model, "context": cx.ctx, "addr": addr,
                                    "size": n, "old_addr": old, "copied_bytes": copied})
    cx.gpr["rax"] = addr


def run_stub(interp, cx, insn, name, stub, trace_mem):
    model = stub.get("model", "none")
    if model in ("malloc", "calloc", "realloc", "free"):
        _heap_call(interp, cx, model, trace_mem)
        return
    if model == "noreturn":
        raise Unsupported("instruction %s: the region reached %s, declared noreturn (an assert or abort path); the input drives the code off its normal path" % (insn.id, name),
                          {"instruction": insn.id, "callee": name})
    if model == "none":
        interp.approximate_stubs.add(name)
        interp.assume("call to %s is a costed stub with no functional effect: values computed from its results are not exact" % name)
        return
    if model in ("memcpy", "memmove", "memset"):
        dst, src, n = cx.gpr["rdi"], cx.gpr["rsi"], cx.gpr["rdx"]
        if n > (1 << 26):
            raise InvalidInput("instruction %s: %s of %d bytes" % (insn.id, name, n))
        if model == "memset":
            data = bytes([src & 0xFF]) * n
        else:
            data = interp.memory.read(src, n, cx.ctx) if n else b""
            if n:
                trace_mem.append((src, n))
        if n:
            interp.memory.write(dst, data, cx.ctx)
            trace_mem.append((dst, n))
        cx.gpr["rax"] = dst
        return
    if model.startswith("libm."):
        parts = model.split(".")
        if len(parts) != 3 or parts[1] not in ("f64", "f32"):
            raise InvalidInput("calls.%s.model %r: use libm.f64.NAME or libm.f32.NAME" % (name, model))
        f32 = parts[1] == "f32"
        fn = parts[2]
        get, put = (_f32_low, _set_f32_low) if f32 else (_f64_low, _set_f64_low)
        fmt = fp.F32 if f32 else fp.F64
        x, xb = get(cx, "zmm0")
        if fn == "sqrt":
            put(cx, "zmm0", fp.fsqrt(xb, fmt, interp.base_policy)[0])
            return
        if fn in ("fmin", "fmax", "copysign") or fn in _APPROX2:
            y, yb = get(cx, "zmm1")
        try:
            if fn in _EXACT1:
                r = float(_EXACT1[fn](x)) if not (math.isnan(x) or math.isinf(x)) else x
                if fn in ("floor", "ceil", "trunc") and r == 0 and math.copysign(1, x) < 0:
                    r = -0.0
            elif fn == "fmin":
                r = y if math.isnan(x) else (x if math.isnan(y) else min(x, y))
            elif fn == "fmax":
                r = y if math.isnan(x) else (x if math.isnan(y) else max(x, y))
            elif fn == "copysign":
                r = math.copysign(x, y)
            elif fn in _APPROX1:
                interp.approximate_stubs.add(name)
                r = getattr(math, fn)(x) if fn != "cbrt" else math.copysign(abs(x) ** (1.0 / 3.0), x)
            elif fn in _APPROX2:
                interp.approximate_stubs.add(name)
                r = getattr(math, fn)(x, y)
            else:
                raise Unsupported("calls.%s.model %r: function not in the stub library" % (name, model))
        except (ValueError, OverflowError):
            r = float("nan")
            interp.approximate_stubs.add(name)
        if name in interp.approximate_stubs:
            interp.assume("call to %s uses the host math library: the value is not bit-exact with the card's libm" % name)
        if f32:
            put(cx, "zmm0", struct.unpack("<I", struct.pack("<f", r))[0])
        else:
            put(cx, "zmm0", struct.unpack("<Q", struct.pack("<d", r))[0])
        return
    raise InvalidInput("calls.%s.model %r is not a stub model (noreturn, none, malloc, calloc, realloc, free, memcpy, memmove, memset, libm.f64.NAME, libm.f32.NAME)" % (name, model))
