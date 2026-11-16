"""Exact functional interpreter for the supported record subset.

Produces final architectural state per context, a dynamic trace (addresses, taken
branches, lines touched, x87 physical registers) for the timing engine, and an
expected-output check. Contexts run one after another; a kernel whose contexts
communicate through memory is rejected (sequential execution would not reproduce
the interleaving).
"""
from fractions import Fraction
import os
import struct
import time

from .errors import BudgetExhausted, InvalidInput, Unsupported
from .kernel import Imm, Label, Mem, Reg, GPR64
from .util import mask32, mask64, parse_int, to_signed
from . import fp

LINE = 64
INT_INDEFINITE = {1: 0x80, 2: 0x8000, 4: 0x80000000, 8: 0x8000000000000000}
ENTRY_SENTINEL = 0x7D5E4E7141E10000   # return address of the simulated function's caller
ENTRY_STACK = 0x7F0000000000
SWIZZLE_MAP = {"cdab": (2, 3, 0, 1), "badc": (1, 0, 3, 2), "dacb": (3, 0, 2, 1), "aaaa": (0, 0, 0, 0), "bbbb": (1, 1, 1, 1), "cccc": (2, 2, 2, 2), "dddd": (3, 3, 3, 3)}


class TraceEvent(object):
    __slots__ = ("ctx", "insn", "addr", "nbytes", "lines", "taken", "mask_bits", "seq", "pf_level", "xreads", "xwrites", "stub", "ret_target", "branch_target")

    def __init__(self, ctx, insn, addr=None, nbytes=0, lines=(), taken=None, mask_bits=None, seq=0, pf_level=None):
        self.ctx = ctx
        self.insn = insn
        self.addr = addr
        self.nbytes = nbytes
        self.lines = tuple(lines)
        self.taken = taken
        self.mask_bits = mask_bits
        self.seq = seq
        self.pf_level = pf_level
        self.xreads = None
        self.xwrites = None
        self.stub = None
        self.ret_target = None
        self.branch_target = None

    def to_dict(self):
        return {"ctx": self.ctx, "id": self.insn.id, "op": self.insn.op, "addr": self.addr, "nbytes": self.nbytes,
                "lines": list(self.lines), "taken": self.taken, "mask_bits": self.mask_bits,
                "x87": {"reads": sorted(self.xreads), "writes": sorted(self.xwrites)} if self.xreads is not None else None}


class Memory(object):
    """Sparse byte memory keyed by 64-byte line."""

    def __init__(self, default=None):
        self.lines = {}
        self.default = default
        self.touched_default = False
        self.stores_by_ctx = {}
        self.loads_by_ctx = {}

    def _line(self, addr, create):
        la = addr & ~(LINE - 1)
        buf = self.lines.get(la)
        if buf is None:
            if not create and self.default is None:
                raise InvalidInput("read of uninitialized memory at 0x%x (set init.memory, or kernel.memory_default to allow filled reads)" % addr)
            if not create:
                self.touched_default = True
            buf = bytearray([self.default or 0]) * LINE if self.default else bytearray(LINE)
            self.lines[la] = buf
        return buf

    def read(self, addr, n, ctx=None):
        out = bytearray()
        a = addr
        while n > 0:
            buf = self._line(a, False)
            off = a & (LINE - 1)
            take = min(n, LINE - off)
            out += buf[off:off + take]
            a += take
            n -= take
        if ctx is not None:
            self.loads_by_ctx.setdefault(ctx, set()).update(lines_of(addr, len(out)))
        return bytes(out)

    def write(self, addr, data, ctx=None):
        a = addr
        i = 0
        n = len(data)
        while i < n:
            buf = self._line(a, True)
            off = a & (LINE - 1)
            take = min(n - i, LINE - off)
            buf[off:off + take] = data[i:i + take]
            a += take
            i += take
        if ctx is not None:
            self.stores_by_ctx.setdefault(ctx, set()).update(lines_of(addr, n))

    def init_block(self, addr, data):
        self.write(addr, data)

    def snapshot(self):
        return {("0x%x" % la): bytes(buf).hex() for la, buf in sorted(self.lines.items())}


def _info_flags(info, *args):
    """Flags of one lane from an fp.* result info dict, plus the invalid flag for an sNaN operand.
    args: the operand bit patterns followed by the format."""
    fmt = args[-1]
    flags = set(info.get("flags", ()))
    if info.get("invalid"):
        flags.add("invalid")
    for b in args[:-1]:
        if fp.is_snan(b, fmt):
            flags.add("invalid")
    return flags


def mxcsr_from_policy(pol):
    """MXCSR as the numerical policy sets it: all exceptions masked (0x1F80), RC from the rounding mode, FZ and DAZ (R27 section 2.4)."""
    rc = {"rn": 0, "rd": 1, "ru": 2, "rz": 3}[pol["rounding"]]
    v = 0x1F80 | (rc << 13)
    if pol.get("ftz"):
        v |= 1 << 15
    if pol.get("daz"):
        v |= 1 << 6
    return v


def round_exact_overflow(fmt, pol, sign):
    """The overflow result of a huge scaling: inf or the largest finite, by rounding mode (R27 p.591: as vmulps would)."""
    return fp.round_exact((Fraction(-1) if sign else Fraction(1)) * (Fraction(2) ** 2000), fmt, pol)


def lines_of(addr, n):
    if n <= 0:
        return ()
    first = addr & ~(LINE - 1)
    last = (addr + n - 1) & ~(LINE - 1)
    return tuple(range(first, last + 1, LINE))


# --- value encoding helpers ---------------------------------------------------------

def _special_bits(s, fmt):
    table = {"nan": fmt.inf | fmt.quiet_bit, "+nan": fmt.inf | fmt.quiet_bit, "-nan": fmt.sign_bit | fmt.inf | fmt.quiet_bit,
             "inf": fmt.inf, "+inf": fmt.inf, "-inf": fmt.sign_bit | fmt.inf, "-0.0": fmt.sign_bit}
    return table.get(s)


def _f32_bits(v, what):
    if isinstance(v, str):
        s = v.strip().lower()
        if s.startswith("0x"):
            return int(s, 16) & 0xFFFFFFFF
        sp = _special_bits(s, fp.F32)
        if sp is not None:
            return sp
        try:
            v = float(s)
        except ValueError:
            raise InvalidInput("%s: cannot parse f32 value %r" % (what, v))
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise InvalidInput("%s: f32 value must be a number or bit string" % what)
    bits = fp.f32_bits_from_float(float(v))
    if fp.float_from_f32_bits(bits) != float(v):
        raise InvalidInput("%s: %r is not exactly representable in binary32; give the bit pattern (0x...) instead" % (what, v))
    return bits


def _f64_bits(v, what):
    if isinstance(v, str):
        s = v.strip().lower()
        if s.startswith("0x"):
            return int(s, 16) & 0xFFFFFFFFFFFFFFFF
        sp = _special_bits(s, fp.F64)
        if sp is not None:
            return sp
        v = float(s)
    return fp.f64_bits_from_float(float(v))


def encode_values(spec, what):
    """{'f32': [...]} | {'u32': [...]} | {'i32': [...]} | {'u64': [...]} | {'f64': [...]} | {'u8': [...]} | {'u16': [...]} | {'f16': [...]} -> bytes."""
    if "f32" in spec:
        return b"".join(struct.pack("<I", _f32_bits(v, what)) for v in spec["f32"])
    if "f64" in spec:
        return b"".join(struct.pack("<Q", _f64_bits(v, what)) for v in spec["f64"])
    if "f16" in spec:
        out = b""
        for v in spec["f16"]:
            if isinstance(v, str) and v.strip().lower().startswith("0x"):
                out += struct.pack("<H", int(v, 16) & 0xFFFF)
            else:
                b32 = _f32_bits(v, what)
                b16, info = fp.convert(b32, fp.F32, fp.F16)
                if info.get("flags"):
                    raise InvalidInput("%s: %r is not exactly representable in binary16" % (what, v))
                out += struct.pack("<H", b16)
        return out
    if "u32" in spec:
        return b"".join(struct.pack("<I", mask32(parse_int(v, what))) for v in spec["u32"])
    if "i32" in spec:
        return b"".join(struct.pack("<i", to_signed(parse_int(v, what), 32)) for v in spec["i32"])
    if "u64" in spec:
        return b"".join(struct.pack("<Q", mask64(parse_int(v, what))) for v in spec["u64"])
    if "u16" in spec:
        return b"".join(struct.pack("<H", parse_int(v, what) & 0xFFFF) for v in spec["u16"])
    if "u8" in spec:
        return bytes(parse_int(v, what) & 0xFF for v in spec["u8"])
    if "i64" in spec:
        return b"".join(struct.pack("<q", to_signed(parse_int(v, what), 64)) for v in spec["i64"])
    if "hex" in spec:
        try:
            return bytes.fromhex(spec["hex"])
        except ValueError:
            raise InvalidInput("%s: 'hex' is not a hexadecimal byte string" % what)
    raise InvalidInput("%s: need one of f32, f64, f16, u32, i32, i64, u64, u16, u8, hex, file" % what)


_TEXT_FORMATS = {"i32": "<i", "u32": "<I", "i64": "<q", "u64": "<Q", "f32": "<f", "f64": "<d", "u8": "<B", "i8": "<b", "u16": "<H", "i16": "<h"}


def load_input_file(blk, kernel_dir, what):
    """init.memory block {"addr", "file", "format"?, "offset"?, "length"?}: bytes of a file captured from the
    measured run (raw dump, default) or a text file of numbers in the named element format.
    Returns (data, record) where record names the file and its SHA-256 for the report."""
    import hashlib
    path = blk["file"]
    if not os.path.isabs(path):
        path = os.path.join(kernel_dir, path)
    if not os.path.isfile(path):
        raise InvalidInput("%s: input file %s not found" % (what, path))
    with open(path, "rb") as f:
        raw = f.read()
    fmt = blk.get("format", "raw")
    if fmt == "raw":
        off = parse_int(blk.get("offset", 0), what + ".offset")
        ln = parse_int(blk["length"], what + ".length") if "length" in blk else len(raw) - off
        data = raw[off:off + ln]
        if len(data) != ln:
            raise InvalidInput("%s: file %s has %d bytes after offset %d, %d wanted" % (what, path, len(raw) - off, off, ln))
    elif fmt in _TEXT_FORMATS:
        toks = raw.decode("ascii", errors="replace").replace(",", " ").split()
        try:
            vals = [float(t) if fmt in ("f32", "f64") else int(t, 0) for t in toks]
            data = b"".join(struct.pack(_TEXT_FORMATS[fmt], v) for v in vals)
        except (ValueError, struct.error) as e:
            raise InvalidInput("%s: file %s is not a list of %s values (%s)" % (what, path, fmt, e))
    else:
        raise InvalidInput("%s: format %r; use raw or one of %s" % (what, fmt, ", ".join(sorted(_TEXT_FORMATS))))
    rec = {"file": os.path.basename(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(data), "format": fmt}
    return data, rec


def zmm_from_spec(spec, what):
    if isinstance(spec, str):
        v = parse_int(spec, what)
        data = v.to_bytes(64, "little")
    elif isinstance(spec, dict):
        if "f32_broadcast" in spec:
            data = struct.pack("<I", _f32_bits(spec["f32_broadcast"], what)) * 16
        elif "u32_broadcast" in spec:
            data = struct.pack("<I", mask32(parse_int(spec["u32_broadcast"], what))) * 16
        elif "f64_broadcast" in spec:
            data = struct.pack("<Q", _f64_bits(spec["f64_broadcast"], what)) * 8
        elif "u64_broadcast" in spec:
            data = struct.pack("<Q", mask64(parse_int(spec["u64_broadcast"], what))) * 8
        else:
            data = encode_values(spec, what)
    else:
        raise InvalidInput("%s: zmm value must be an object or hex string" % what)
    if len(data) != 64:
        raise InvalidInput("%s: zmm value must be exactly 64 bytes (got %d)" % (what, len(data)))
    return list(struct.unpack("<16I", data))


def u32s_to_u64s(lanes):
    return [lanes[2 * i] | (lanes[2 * i + 1] << 32) for i in range(8)]


def u64s_to_u32s(lanes):
    out = []
    for v in lanes:
        out.append(v & 0xFFFFFFFF)
        out.append((v >> 32) & 0xFFFFFFFF)
    return out


# --- machine state -------------------------------------------------------------------------

class Context(object):
    def __init__(self, ctx, fcw=0x037F):
        self.ctx = ctx
        self.gpr = {r: 0 for r in GPR64}
        self.zmm = {"zmm%d" % i: [0] * 16 for i in range(32)}
        self.k = {"k%d" % i: 0 for i in range(8)}
        self.k["k0"] = 0xFFFF  # k0 means 'all lanes' when used as a write mask
        self.flags = {"ZF": 0, "SF": 0, "CF": 0, "OF": 0, "PF": 0}
        self.pc = 0
        self.fst = [None] * 8  # physical x87 registers, F80 bits or None (empty)
        self.ftop = 0
        self.fcw = fcw
        self.fcc = {"C0": 0, "C1": 0, "C2": 0, "C3": 0}
        self.mxcsr = 0x1F80
        self.seg_base = {"fs": 0x7E0000000000 + (ctx << 32), "gs": 0x7E8000000000 + (ctx << 32)}
        self.call_depth = 0

    # x87 helpers
    def fphys(self, i):
        return (self.ftop + i) & 7

    def fget(self, i, insn):
        v = self.fst[self.fphys(i)]
        if v is None:
            raise InvalidInput("instruction %s: x87 stack underflow (st(%d) is empty)" % (insn.id, i))
        return v

    def fpush(self, bits, insn):
        self.ftop = (self.ftop - 1) & 7
        if self.fst[self.ftop] is not None:
            raise InvalidInput("instruction %s: x87 stack overflow" % insn.id)
        self.fst[self.ftop] = bits

    def fpop(self, insn):
        if self.fst[self.ftop] is None:
            raise InvalidInput("instruction %s: x87 stack underflow on pop" % insn.id)
        self.fst[self.ftop] = None
        self.ftop = (self.ftop + 1) & 7

    def fdepth(self):
        return sum(1 for v in self.fst if v is not None)

    def apply_init(self, regs, what):
        for name, val in regs.items():
            n = name.lower()
            if n in self.gpr:
                self.gpr[n] = mask64(parse_int(val, what + "." + name))
            elif n in self.zmm:
                self.zmm[n] = zmm_from_spec(val, what + "." + name)
            elif n in self.k:
                self.k[n] = parse_int(val, what + "." + name) & 0xFFFF
            elif n == "flags":
                for f, v in val.items():
                    self.flags[f.upper()] = 1 if v else 0
            elif n == "x87":
                # list of values pushed in order (last = st0); each f64 number/bit string or {"f80": "0x..."}
                for item in val:
                    if isinstance(item, dict) and "f80" in item:
                        bits = parse_int(item["f80"], what + ".x87")
                    else:
                        b64 = _f64_bits(item, what + ".x87")
                        bits = fp.convert(b64, fp.F64, fp.F80)[0]
                    self.ftop = (self.ftop - 1) & 7
                    self.fst[self.ftop] = bits
            elif n == "fcw":
                self.fcw = parse_int(val, what + ".fcw") & 0xFFFF
            elif n in ("fs_base", "gs_base"):
                self.seg_base[n[:2]] = mask64(parse_int(val, what + "." + name))
            elif n == "mxcsr":
                self.mxcsr = parse_int(val, what + ".mxcsr") & 0xFFFF
            else:
                raise InvalidInput("%s: unknown register %r" % (what, name))

    def snapshot(self):
        st = []
        for i in range(self.fdepth()):
            bits = self.fst[self.fphys(i)]
            st.append({"f80": "0x%020x" % bits, "f64": fp.fmt_bits(fp.convert(bits, fp.F80, fp.F64)[0], fp.F64)})
        return {"gpr": {r: "0x%x" % v for r, v in sorted(self.gpr.items()) if v},
                "k": {r: "0x%x" % v for r, v in sorted(self.k.items())},
                "zmm": {r: ["0x%08x" % l for l in lanes] for r, lanes in sorted(self.zmm.items()) if any(lanes)},
                "flags": dict(self.flags), "x87": st, "fcw": "0x%04x" % self.fcw}


class Interpreter(object):
    def __init__(self, kernel, max_steps=None, deadline=None):
        self.kernel = kernel
        self.memory = Memory(default=kernel.memory_default)
        self.max_steps = max_steps or kernel.max_steps
        self.deadline = deadline
        self.assumptions = []
        self.assumption_set = set()
        self.traces = {}
        self.contexts = {}
        self.steps = {}
        self.stub_calls = {}
        self.heap = None
        self.heap_allocations = []
        self.approximate_stubs = set()
        self.approximate_instructions = set()
        from .reciprocal_tables import Tables
        self.reciprocal_tables = Tables(kernel.numerical_policy.get("reciprocal_tables", {}))
        self.gather_one_line = kernel.numerical_policy.get("gather_completion", "one_line") == "one_line"
        if any(i.cls in ("vector_gather", "vector_scatter") for s in kernel.streams for i in s.insns):
            if self.gather_one_line:
                self.assume("a gather or scatter execution completes the pending lanes that share the cache line of the lowest pending lane and leaves the rest in the mask (R05 section V.D; the jknzd loop re-executes it); numerical_policy.gather_completion 'all' restores one-shot completion")
            else:
                self.assume("numerical_policy.gather_completion 'all': every pending lane completes in one execution (not the hardware's behaviour for lanes on several cache lines)")
        pol = kernel.numerical_policy
        self.base_policy = fp.Policy(pol["rounding"], bool(pol.get("ftz")), bool(pol.get("daz")), pol.get("ftz_rule", "tiny"))
        self.input_files = []
        for i, blk in enumerate(kernel.init.get("memory", [])):
            if "addr" not in blk:
                raise InvalidInput("init.memory[%d] needs addr" % i)
            addr = parse_int(blk["addr"], "init.memory[%d].addr" % i)
            if "file" in blk:
                data, rec = load_input_file(blk, kernel.dir, "init.memory[%d]" % i)
                rec["addr"] = "0x%x" % addr
                self.input_files.append(rec)
                self.memory.init_block(addr, data)
                continue
            if "fill" in blk:
                f = blk["fill"]
                unit = encode_values({k: [f[k]] for k in f if k in ("f32", "f64", "f16", "u32", "i32", "u64", "u16", "u8")}, "init.memory[%d].fill" % i)
                count = parse_int(f.get("count", 1), "fill.count")
                data = unit * count
            else:
                data = encode_values(blk, "init.memory[%d]" % i)
            self.memory.init_block(addr, data)

    def assume(self, text):
        if text not in self.assumption_set:
            self.assumption_set.add(text)
            self.assumptions.append(text)

    # ---------------------------------------------------------------------------------------
    def run(self):
        total = 0
        for stream in self.kernel.streams:
            cx, trace = self._start_stream(stream)
            steps = 0
            n = len(stream.insns)
            # Keep full execution on the original tight loop. Yielding and
            # publishing the step count per instruction is only for sampling.
            while cx.pc < n:
                if steps >= self.max_steps:
                    raise BudgetExhausted("functional step budget (%d) exhausted in context %d at %s; the kernel did not finish" % (self.max_steps, stream.context, stream.insns[cx.pc].id),
                                          {"context": stream.context, "steps": steps, "pc": stream.insns[cx.pc].id},
                                          partial={"contexts_completed": sorted(k for k in self.traces if k != stream.context)})
                if self.deadline is not None and (steps & 255) == 0 and time.time() > self.deadline:
                    raise BudgetExhausted("python time budget exhausted during functional execution (context %d, step %d)" % (stream.context, steps),
                                          {"context": stream.context, "steps": steps})
                insn = stream.insns[cx.pc]
                nxt = self.execute(cx, insn, stream, trace, steps)
                cx.pc = nxt
                steps += 1
            self.steps[stream.context] = steps
            total += steps
        for a, stores in self.memory.stores_by_ctx.items():
            for b, loads in self.memory.loads_by_ctx.items():
                if a != b and stores & loads:
                    raise Unsupported("context %d stores to lines that context %d loads; contexts communicating through memory are not supported by the sequential functional model" % (a, b),
                                      {"lines": ["0x%x" % l for l in sorted(stores & loads)][:8]})
            for b, stores_b in self.memory.stores_by_ctx.items():
                if a < b and stores & stores_b:
                    raise Unsupported("contexts %d and %d store to the same lines; not supported by the sequential functional model" % (a, b))
        if self.memory.touched_default:
            self.assume("reads of uninitialized memory returned the kernel's memory_default byte 0x%02x" % (self.kernel.memory_default or 0))
        return total

    def _start_stream(self, stream):
        """Initialize the same context and trace for full and sampled execution."""
        cx = Context(stream.context, self.kernel.numerical_policy["x87_control_word"])
        cx.mxcsr = mxcsr_from_policy(self.kernel.numerical_policy)
        cx.apply_init(self.kernel.init.get("registers", {}), "init.registers")
        cx.apply_init(stream.init.get("registers", {}), "streams[%d].init.registers" % stream.context)
        self.contexts[stream.context] = cx
        if self.kernel.entry == "function":
            if cx.gpr["rsp"] == 0:
                cx.gpr["rsp"] = ENTRY_STACK - (stream.context << 24) - 8
            self.memory.write(cx.gpr["rsp"], ENTRY_SENTINEL.to_bytes(8, "little"))
        trace = []
        self.traces[stream.context] = trace
        return cx, trace

    def iter_stream(self, stream):
        """Execute one stream incrementally, preserving state and the dynamic trace.

        Consumers that stop early must not check final expected outputs or claim
        whole-function correctness. Full execution uses run() without yielding.
        """
        cx, trace = self._start_stream(stream)
        steps = 0
        n = len(stream.insns)
        while cx.pc < n:
            if steps >= self.max_steps:
                raise BudgetExhausted("functional step budget (%d) exhausted in context %d at %s; the kernel did not finish" % (self.max_steps, stream.context, stream.insns[cx.pc].id),
                                      {"context": stream.context, "steps": steps, "pc": stream.insns[cx.pc].id},
                                      partial={"contexts_completed": sorted(k for k in self.traces if k != stream.context)})
            if self.deadline is not None and (steps & 255) == 0 and time.time() > self.deadline:
                raise BudgetExhausted("python time budget exhausted during functional execution (context %d, step %d)" % (stream.context, steps),
                                      {"context": stream.context, "steps": steps})
            insn = stream.insns[cx.pc]
            nxt = self.execute(cx, insn, stream, trace, steps)
            cx.pc = nxt
            steps += 1
            self.steps[stream.context] = steps
            yield trace[-1]
        self.steps[stream.context] = steps

    # ---------------------------------------------------------------------------------------
    def policy_for(self, insn, imm_rounding=None):
        r = imm_rounding or insn.rounding
        if r is None:
            return self.base_policy
        return fp.Policy(r, self.base_policy.ftz, self.base_policy.daz, self.base_policy.ftz_rule)

    def ea(self, cx, mem, lane_index=None):
        a = mem.disp
        if mem.base is not None:
            a += cx.gpr[mem.base.base]
        if mem.index is not None:
            a += cx.gpr[mem.index.base] * mem.scale
        if lane_index is not None:
            a += lane_index * mem.scale
        if mem.segment is not None:
            a += cx.seg_base[mem.segment]
        return mask64(a)

    # scalar register access with widths
    def rget(self, cx, reg, width=None):
        w = width or reg.width
        v = cx.gpr[reg.base]
        if reg.high:
            return (v >> 8) & 0xFF
        return v & ((1 << w) - 1)

    def rset(self, cx, reg, value, width=None):
        w = width or reg.width
        value &= (1 << w) - 1
        if reg.high:
            cx.gpr[reg.base] = (cx.gpr[reg.base] & ~0xFF00) | (value << 8)
        elif w >= 32:
            cx.gpr[reg.base] = value  # 32-bit writes zero-extend
        else:
            cx.gpr[reg.base] = (cx.gpr[reg.base] & ~((1 << w) - 1)) | value

    def gval(self, cx, opnd, width):
        if isinstance(opnd, Reg):
            return self.rget(cx, opnd, width if opnd.width >= width else opnd.width) & ((1 << width) - 1)
        if isinstance(opnd, Imm):
            return opnd.value & ((1 << width) - 1)
        raise InvalidInput("unexpected operand %r" % (opnd,))

    def mload(self, cx, mem, nbytes, trace_mem):
        addr = self.ea(cx, mem)
        data = self.memory.read(addr, nbytes, cx.ctx)
        trace_mem.append((addr, nbytes))
        return int.from_bytes(data, "little"), addr

    def mstore(self, cx, mem, value, nbytes, trace_mem):
        addr = self.ea(cx, mem)
        self.memory.write(addr, (value & ((1 << (8 * nbytes)) - 1)).to_bytes(nbytes, "little"), cx.ctx)
        trace_mem.append((addr, nbytes))
        return addr

    def sval(self, cx, opnd, width, trace_mem):
        """Scalar source value (register, immediate or memory) of the given width."""
        if isinstance(opnd, Mem):
            v, _ = self.mload(cx, opnd, width // 8, trace_mem)
            return v
        return self.gval(cx, opnd, width)

    def sset(self, cx, opnd, value, width, trace_mem):
        if isinstance(opnd, Mem):
            self.mstore(cx, opnd, value, width // 8, trace_mem)
        else:
            self.rset(cx, opnd, value, width)

    # vector sources -------------------------------------------------------------------------
    def _upconvert(self, data, conv, target_float, policy):
        """Memory bytes -> 16 u32 lanes under an up-conversion modifier."""
        if conv == "float16":
            if not target_float:
                raise Unsupported("float16 up-conversion into an integer vector is not supported")
            halves = struct.unpack("<16H", data)
            return [fp.convert(h, fp.F16, fp.F32)[0] for h in halves]
        if conv in ("uint8", "sint8"):
            vals = struct.unpack("<16B" if conv == "uint8" else "<16b", data)
        else:
            vals = struct.unpack("<16H" if conv == "uint16" else "<16h", data)
        if target_float:
            return [fp.int_to_float(v, fp.F32, policy)[0] for v in vals]
        return [v & 0xFFFFFFFF for v in vals]

    def _swizzle(self, lanes, swz, elem):
        perm = SWIZZLE_MAP[swz]
        if elem == 4:
            out = []
            for g in range(4):
                base = 4 * g
                out.extend(lanes[base + perm[j]] for j in range(4))
            return out
        v64 = u32s_to_u64s(lanes)
        out = []
        for g in range(2):
            base = 4 * g
            out.extend(v64[base + perm[j]] for j in range(4))
        return u64s_to_u32s(out)

    def vsrc(self, cx, opnd, insn, trace_mem, elem=4, target_float=True):
        """Vector source as 16 u32 lanes; memory sources are loaded (and recorded)."""
        if isinstance(opnd, Reg):
            lanes = list(cx.zmm[opnd.base])
            if opnd.swizzle:
                lanes = self._swizzle(lanes, opnd.swizzle, elem)
            return lanes
        if isinstance(opnd, Mem):
            addr = self.ea(cx, opnd)
            pol = self.policy_for(insn)
            if opnd.broadcast:
                n = {"1to16": 4, "4to16": 16, "1to8": 8, "4to8": 32}[opnd.broadcast]
                if opnd.conv:
                    raise Unsupported("instruction %s: broadcast combined with a conversion is not supported" % insn.id)
                data = self.memory.read(addr, n, cx.ctx)
                trace_mem.append((addr, n))
                if opnd.broadcast == "1to16":
                    return list(struct.unpack("<I", data)) * 16
                if opnd.broadcast == "4to16":
                    return list(struct.unpack("<4I", data)) * 4
                if opnd.broadcast == "1to8":
                    return u64s_to_u32s(list(struct.unpack("<Q", data)) * 8)
                return u64s_to_u32s(list(struct.unpack("<4Q", data)) * 2)
            if opnd.conv:
                n = 32 if opnd.conv in ("float16", "uint16", "sint16") else 16
                if elem != 4:
                    raise Unsupported("instruction %s: up-conversion into 64-bit lanes is not supported" % insn.id)
                data = self.memory.read(addr, n, cx.ctx)
                trace_mem.append((addr, n))
                return self._upconvert(data, opnd.conv, target_float, pol)
            if addr % 64:
                raise InvalidInput("instruction %s: 64-byte vector access at 0x%x is not 64-byte aligned (faults on KNC)" % (insn.id, addr))
            data = self.memory.read(addr, 64, cx.ctx)
            trace_mem.append((addr, 64))
            return list(struct.unpack("<16I", data))
        raise InvalidInput("instruction %s: bad vector source" % insn.id)

    def kmask(self, cx, insn):
        return cx.k[insn.mask.base] if insn.mask is not None else 0xFFFF

    def merge32(self, cx, dst, new_lanes, kbits):
        old = cx.zmm[dst.base]
        cx.zmm[dst.base] = [new_lanes[i] if (kbits >> i) & 1 else old[i] for i in range(16)]

    def merge64(self, cx, dst, new64, kbits):
        old = u32s_to_u64s(cx.zmm[dst.base])
        cx.zmm[dst.base] = u64s_to_u32s([new64[i] if (kbits >> i) & 1 else old[i] for i in range(8)])

    def _is_float_op(self, insn):
        f = insn.spec.get("fmt")
        if f:
            return f in ("f32", "f64")
        return insn.op.endswith(("ps", "pd")) or insn.op in ("vmovaps", "vmovapd")

    # ---------------------------------------------------------------------------------------
    def execute(self, cx, insn, stream, trace, seq):
        fn = insn.spec.get("fn")
        if fn is None:
            raise Unsupported("instruction %s (%s) has timing support only; functional execution is not implemented for it" % (insn.id, insn.op),
                              {"instruction": insn.id, "mnemonic": insn.op})
        handler = getattr(self, "h_" + fn)
        trace_mem = []
        ev = TraceEvent(cx.ctx, insn, seq=seq)
        nxt = handler(cx, insn, ev, trace_mem, stream)
        if trace_mem and ev.addr is None:
            addr, n = trace_mem[0]
            ev.addr, ev.nbytes = addr, n
            lines = set()
            for a, k in trace_mem:
                lines.update(lines_of(a, k))
            ev.lines = tuple(sorted(lines))
        trace.append(ev)
        return cx.pc + 1 if nxt is None else nxt

    # --- scalar -------------------------------------------------------------------------------
    def _set_flags_arith(self, cx, a, b, r, width, op, carry_in=0):
        msb = 1 << (width - 1)
        cx.flags["ZF"] = 1 if r == 0 else 0
        cx.flags["SF"] = 1 if r & msb else 0
        cx.flags["PF"] = 1 if bin(r & 0xFF).count("1") % 2 == 0 else 0
        if op == "add":
            cx.flags["CF"] = 1 if a + b + carry_in >= (1 << width) else 0
            cx.flags["OF"] = 1 if ((a ^ r) & (b ^ r) & msb) else 0
        else:
            cx.flags["CF"] = 1 if a < b + carry_in else 0
            cx.flags["OF"] = 1 if ((a ^ b) & (a ^ r) & msb) else 0

    def _set_flags_logic(self, cx, r, width):
        cx.flags["ZF"] = 1 if r == 0 else 0
        cx.flags["SF"] = 1 if r & (1 << (width - 1)) else 0
        cx.flags["PF"] = 1 if bin(r & 0xFF).count("1") % 2 == 0 else 0
        cx.flags["CF"] = 0
        cx.flags["OF"] = 0

    def h_alu2(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        w = insn.width
        a = self.sval(cx, dst, w, trace_mem)
        b = self.sval(cx, src, w, trace_mem)
        m = (1 << w) - 1
        opn = insn.spec.get("base_op", insn.op)
        if opn in ("add", "adc"):
            cin = cx.flags["CF"] if opn == "adc" else 0
            r = (a + b + cin) & m
            self._set_flags_arith(cx, a, b, r, w, "add", cin)
        elif opn in ("sub", "sbb"):
            cin = cx.flags["CF"] if opn == "sbb" else 0
            r = (a - b - cin) & m
            self._set_flags_arith(cx, a, b, r, w, "sub", cin)
        else:
            r = {"and": a & b, "or": a | b, "xor": a ^ b}[opn] & m
            self._set_flags_logic(cx, r, w)
        self.sset(cx, dst, r, w, trace_mem)

    def h_cmp(self, cx, insn, ev, trace_mem, stream):
        w = insn.width
        a_op, b_op = insn.operands
        a = self.sval(cx, a_op, w, trace_mem)
        b = self.sval(cx, b_op, w, trace_mem)
        if isinstance(b_op, Imm) and w > 8:
            b = to_signed(b_op.value, 32 if w >= 32 else w) & ((1 << w) - 1) if b_op.value < 0 or b_op.value >= (1 << 31) else b
        r = (a - b) & ((1 << w) - 1)
        self._set_flags_arith(cx, a, b, r, w, "sub")

    def h_test(self, cx, insn, ev, trace_mem, stream):
        w = insn.width
        a_op, b_op = insn.operands
        a = self.sval(cx, a_op, w, trace_mem)
        b = self.sval(cx, b_op, w, trace_mem)
        self._set_flags_logic(cx, a & b, w)

    def h_bt(self, cx, insn, ev, trace_mem, stream):
        w = insn.width
        a_op, b_op = insn.operands
        a = self.sval(cx, a_op, w, trace_mem)
        b = self.gval(cx, b_op, 64) & (w - 1)
        cx.flags["CF"] = (a >> b) & 1

    def h_mov(self, cx, insn, ev, trace_mem, stream):
        w = insn.width
        dst, src = insn.operands
        v = self.sval(cx, src, w, trace_mem)
        self.sset(cx, dst, v, w, trace_mem)

    def h_movx(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        sw, dw = insn.spec["src_width"], insn.spec["dst_width"]
        v = self.sval(cx, src, sw, trace_mem)
        if insn.spec["sign"]:
            v = to_signed(v, sw) & ((1 << dw) - 1)
        self.rset(cx, dst, v, dw)

    def h_cltq(self, cx, insn, ev, trace_mem, stream):
        cx.gpr["rax"] = to_signed(cx.gpr["rax"] & 0xFFFFFFFF, 32) & 0xFFFFFFFFFFFFFFFF

    def h_cltd(self, cx, insn, ev, trace_mem, stream):
        cx.gpr["rdx"] = 0xFFFFFFFF if cx.gpr["rax"] & 0x80000000 else 0

    def h_cqto(self, cx, insn, ev, trace_mem, stream):
        cx.gpr["rdx"] = 0xFFFFFFFFFFFFFFFF if cx.gpr["rax"] & (1 << 63) else 0

    def h_lea(self, cx, insn, ev, trace_mem, stream):
        dst, mem = insn.operands
        self.rset(cx, dst, self.ea(cx, mem), insn.width)

    def h_incdec(self, cx, insn, ev, trace_mem, stream):
        (dst,) = insn.operands
        w = insn.width
        a = self.sval(cx, dst, w, trace_mem)
        cf = cx.flags["CF"]
        if insn.spec.get("base_op", insn.op) == "inc":
            r = (a + 1) & ((1 << w) - 1)
            self._set_flags_arith(cx, a, 1, r, w, "add")
        else:
            r = (a - 1) & ((1 << w) - 1)
            self._set_flags_arith(cx, a, 1, r, w, "sub")
        cx.flags["CF"] = cf
        self.sset(cx, dst, r, w, trace_mem)

    def h_neg(self, cx, insn, ev, trace_mem, stream):
        (dst,) = insn.operands
        w = insn.width
        a = self.sval(cx, dst, w, trace_mem)
        r = (-a) & ((1 << w) - 1)
        self._set_flags_arith(cx, 0, a, r, w, "sub")
        cx.flags["CF"] = 1 if a != 0 else 0
        self.sset(cx, dst, r, w, trace_mem)

    def h_not(self, cx, insn, ev, trace_mem, stream):
        (dst,) = insn.operands
        w = insn.width
        self.sset(cx, dst, (~self.sval(cx, dst, w, trace_mem)) & ((1 << w) - 1), w, trace_mem)

    def h_shift(self, cx, insn, ev, trace_mem, stream):
        dst = insn.operands[0]
        w = insn.width
        if len(insn.operands) == 1:
            c = 1
        else:
            cnt = insn.operands[1]
            c = cnt.value if isinstance(cnt, Imm) else self.rget(cx, cnt, 8)
        c &= 63 if w == 64 else 31
        a = self.sval(cx, dst, w, trace_mem)
        if c == 0:
            return None
        m = (1 << w) - 1
        if insn.op in ("shl", "sal"):
            r = (a << c) & m
            cf = (a >> (w - c)) & 1
            if c == 1:
                cx.flags["OF"] = ((r >> (w - 1)) & 1) ^ cf
        elif insn.op == "shr":
            r = a >> c
            cf = (a >> (c - 1)) & 1
            if c == 1:
                cx.flags["OF"] = (a >> (w - 1)) & 1
        else:
            r = (to_signed(a, w) >> c) & m
            cf = (a >> (c - 1)) & 1
            if c == 1:
                cx.flags["OF"] = 0
        cx.flags["CF"] = cf
        cx.flags["ZF"] = 1 if r == 0 else 0
        cx.flags["SF"] = 1 if r & (1 << (w - 1)) else 0
        cx.flags["PF"] = 1 if bin(r & 0xFF).count("1") % 2 == 0 else 0
        if c > 1:
            self.assume("OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged")
        self.sset(cx, dst, r, w, trace_mem)

    def h_imul(self, cx, insn, ev, trace_mem, stream):
        w = insn.width
        if len(insn.operands) == 2:
            dst, src = insn.operands
            a = self.rget(cx, dst, w)
            b = self.sval(cx, src, w, trace_mem)
        else:
            dst, src, imm = insn.operands
            a = self.sval(cx, src, w, trace_mem)
            b = imm.value & ((1 << w) - 1)
        full = to_signed(a, w) * to_signed(b, w)
        r = full & ((1 << w) - 1)
        ovf = 0 if to_signed(r, w) == full else 1
        cx.flags["CF"] = ovf
        cx.flags["OF"] = ovf
        self.assume("ZF/SF after imul are architecturally undefined; the model leaves them unchanged")
        self.rset(cx, dst, r, w)

    def h_idiv(self, cx, insn, ev, trace_mem, stream):
        (src,) = insn.operands
        w = insn.width
        d = self.sval(cx, src, w, trace_mem)
        if d == 0:
            raise InvalidInput("instruction %s: division by zero (#DE)" % insn.id)
        lo = cx.gpr["rax"] & ((1 << w) - 1)
        hi = cx.gpr["rdx"] & ((1 << w) - 1)
        num = (hi << w) | lo
        if insn.spec["signed"]:
            num = to_signed(num, 2 * w)
            d = to_signed(d, w)
            q = abs(num) // abs(d)
            if (num < 0) != (d < 0):
                q = -q
            r = num - q * d
            if not -(1 << (w - 1)) <= q < (1 << (w - 1)):
                raise InvalidInput("instruction %s: signed division overflow (#DE)" % insn.id)
        else:
            q, r = divmod(num, d)
            if q >= (1 << w):
                raise InvalidInput("instruction %s: unsigned division overflow (#DE)" % insn.id)
        self.rset(cx, Reg("rax"), q & ((1 << w) - 1), w)
        self.rset(cx, Reg("rdx"), r & ((1 << w) - 1), w)
        self.assume("flags after idiv/div are architecturally undefined; the model leaves them unchanged")

    def h_push(self, cx, insn, ev, trace_mem, stream):
        (src,) = insn.operands
        v = self.sval(cx, src, 64, trace_mem) if not isinstance(src, Imm) else (to_signed(src.value, 32) & 0xFFFFFFFFFFFFFFFF)
        cx.gpr["rsp"] = mask64(cx.gpr["rsp"] - 8)
        self.memory.write(cx.gpr["rsp"], v.to_bytes(8, "little"), cx.ctx)
        trace_mem.append((cx.gpr["rsp"], 8))

    def h_pop(self, cx, insn, ev, trace_mem, stream):
        (dst,) = insn.operands
        data = self.memory.read(cx.gpr["rsp"], 8, cx.ctx)
        trace_mem.append((cx.gpr["rsp"], 8))
        cx.gpr["rsp"] = mask64(cx.gpr["rsp"] + 8)
        self.sset(cx, dst, int.from_bytes(data, "little"), 64, trace_mem)

    def h_leave(self, cx, insn, ev, trace_mem, stream):
        cx.gpr["rsp"] = cx.gpr["rbp"]
        data = self.memory.read(cx.gpr["rsp"], 8, cx.ctx)
        trace_mem.append((cx.gpr["rsp"], 8))
        cx.gpr["rbp"] = int.from_bytes(data, "little")
        cx.gpr["rsp"] = mask64(cx.gpr["rsp"] + 8)

    def h_xchg(self, cx, insn, ev, trace_mem, stream):
        a_op, b_op = insn.operands
        w = insn.width
        a = self.sval(cx, a_op, w, trace_mem)
        b = self.sval(cx, b_op, w, trace_mem)
        self.sset(cx, a_op, b, w, trace_mem)
        self.sset(cx, b_op, a, w, trace_mem)

    def h_xadd(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        w = insn.width
        a = self.sval(cx, dst, w, trace_mem)
        b = self.sval(cx, src, w, trace_mem)
        r = (a + b) & ((1 << w) - 1)
        self._set_flags_arith(cx, a, b, r, w, "add")
        self.sset(cx, src, a, w, trace_mem)
        self.sset(cx, dst, r, w, trace_mem)

    def h_cmpxchg(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        w = insn.width
        a = self.sval(cx, dst, w, trace_mem)
        acc = cx.gpr["rax"] & ((1 << w) - 1)
        self._set_flags_arith(cx, acc, a, (acc - a) & ((1 << w) - 1), w, "sub")
        if acc == a:
            self.sset(cx, dst, self.sval(cx, src, w, trace_mem), w, trace_mem)
        else:
            self.rset(cx, Reg({64: "rax", 32: "eax", 16: "ax", 8: "al"}[w]), a, w)

    def h_sahf(self, cx, insn, ev, trace_mem, stream):
        ah = (cx.gpr["rax"] >> 8) & 0xFF
        cx.flags["SF"] = (ah >> 7) & 1
        cx.flags["ZF"] = (ah >> 6) & 1
        cx.flags["PF"] = (ah >> 2) & 1
        cx.flags["CF"] = ah & 1

    # --- calls ---------------------------------------------------------------------------------
    def h_call(self, cx, insn, ev, trace_mem, stream):
        target = insn.target
        if target in stream.labels:
            ret_value = stream.return_value(insn.index)
            cx.gpr["rsp"] = mask64(cx.gpr["rsp"] - 8)
            self.memory.write(cx.gpr["rsp"], ret_value.to_bytes(8, "little"), cx.ctx)
            trace_mem.append((cx.gpr["rsp"], 8))
            ev.taken = True
            cx.call_depth += 1
            return stream.labels[target]
        stub = self.kernel.calls.get(target)
        if stub is None:
            raise Unsupported("instruction %s: call to %r, which is neither in the region nor declared in the kernel's 'calls'" % (insn.id, target),
                              {"instruction": insn.id, "callee": target})
        from . import stubs
        ev.stub = target
        self.stub_calls[target] = self.stub_calls.get(target, 0) + 1
        ev.taken = False
        stubs.run_stub(self, cx, insn, target, stub, trace_mem)
        return None

    def h_ret(self, cx, insn, ev, trace_mem, stream):
        data = self.memory.read(cx.gpr["rsp"], 8, cx.ctx)
        trace_mem.append((cx.gpr["rsp"], 8))
        cx.gpr["rsp"] = mask64(cx.gpr["rsp"] + 8)
        value = int.from_bytes(data, "little")
        ev.taken = True
        if value == ENTRY_SENTINEL:
            ev.ret_target = -1
            return len(stream.insns)
        idx = stream.return_sites.get(value)
        if idx is None:
            raise InvalidInput("instruction %s: ret to 0x%x, which is not a return site of this region (stack corrupted, or no entry sentinel: set kernel 'entry' to 'function')" % (insn.id, value))
        cx.call_depth -= 1
        ev.ret_target = idx
        return idx

    def h_vpmadd231d(self, cx, insn, ev, trace_mem, stream):
        dst, a_op, b_op = insn.operands
        a = cx.zmm[a_op.base]
        b = self.vsrc(cx, b_op, insn, trace_mem, 4, False)
        old = cx.zmm[dst.base]
        out = [(old[i] + to_signed(a[i], 32) * to_signed(b[i], 32)) & 0xFFFFFFFF for i in range(16)]
        self.merge32(cx, dst, out, self.kmask(cx, insn))


    # --- MXCSR and the IMCI special-value instructions (0.3.1) ---------------------------------------
    MXCSR_FLAG_BITS = {"invalid": 0, "denormal": 1, "zero_divide": 2, "overflow": 3, "underflow": 4, "inexact": 5}

    def _fpflags(self, cx, insn, flags, operands=(), fmt=None):
        """OR the exception flags of one lane into MXCSR unless the instruction suppresses them ({sae}).
        A subnormal operand raises the denormal flag when DAZ is off (R27 section 4.1.3)."""
        if insn.sae:
            return
        bits = 0
        for f in flags or ():
            b = self.MXCSR_FLAG_BITS.get(f)
            if b is not None:
                bits |= 1 << b
        if fmt is not None and not self.base_policy.daz:
            for o in operands:
                if (o & fmt.exp_mask << fmt.mant) == 0 and (o & fmt.mant_mask) != 0:
                    bits |= 1 << 1
        cx.mxcsr |= bits

    def _mark_approximate(self, insn):
        self.approximate_instructions.add(insn.op)
        self.assume("%s is approximate on the hardware (R27 gives a relative-error bound, not the bit pattern); the twin substitutes the correctly rounded value, "
                    "so values that depend on its exact bits are not bit-exact (calibration plan: capture the hardware table)" % insn.op)

    def _lanes_in(self, cx, insn, opnd, fmt, trace_mem):
        elem = 4 if fmt is fp.F32 else 8
        v = self.vsrc(cx, opnd, insn, trace_mem, elem)
        return v if fmt is fp.F32 else u32s_to_u64s(v)

    def _lanes_out(self, cx, dst, out, fmt, kbits):
        if fmt is fp.F32:
            self.merge32(cx, dst, out, kbits)
        else:
            self.merge64(cx, dst, out, kbits & 0xFF)

    def h_vgminmax(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2 = insn.operands
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        a = self._lanes_in(cx, insn, s1, fmt, trace_mem)
        b = self._lanes_in(cx, insn, s2, fmt, trace_mem)
        kbits = self.kmask(cx, insn)
        want_max = insn.spec["want_max"]
        out = []
        for i in range(16 if fmt is fp.F32 else 8):
            x, y = a[i], b[i]
            kx, sx, _ = fp.classify(x, fmt, pol)
            ky, sy, _ = fp.classify(y, fmt, pol)
            if kx == fp.ZERO and ky == fp.ZERO and sx != sy:
                # FpMax(-0,+0) = B, FpMax(+0,-0) = A; FpMin(-0,+0) = A, FpMin(+0,-0) = B  (R27 pp.337, 345)
                r = (y if sx else x) if want_max else (x if sx else y)
            elif kx == fp.NAN and ky == fp.NAN:
                r = x
            elif kx == fp.NAN:
                r = y
            elif ky == fp.NAN:
                r = x
            else:
                c = fp.fcompare(x, y, fmt, pol)
                if want_max:
                    r = x if c in ("gt", "eq") else y
                else:
                    r = x if c == "lt" else y
            if (kx == fp.NAN and fp.is_snan(x, fmt)) or (ky == fp.NAN and fp.is_snan(y, fmt)):
                self._fpflags(cx, insn, ["invalid"])
            out.append(r)
        self._fpflags(cx, insn, [], [a[i] for i in range(len(out)) if (kbits >> i) & 1] + [b[i] for i in range(len(out)) if (kbits >> i) & 1], fmt)
        self._lanes_out(cx, dst, out, fmt, kbits)
        ev.mask_bits = kbits

    def h_vgetexp(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        a = self._lanes_in(cx, insn, src, fmt, trace_mem)
        kbits = self.kmask(cx, insn)
        out = []
        for i in range(16 if fmt is fp.F32 else 8):
            x = a[i]
            k, s, v = fp.classify(x, fmt, pol)
            if k == fp.NAN:
                if fp.is_snan(x, fmt):
                    self._fpflags(cx, insn, ["invalid"])
                out.append(fp.quiet(x, fmt))
            elif k == fp.INF:
                out.append(fmt.inf)
            elif k == fp.ZERO:
                out.append(fmt.inf | fmt.sign_bit)
            else:
                e = fp._floor_log2(abs(v))          # unbiased exponent of the normalized value (denormals normalized)
                out.append(fp.round_exact(Fraction(e), fmt, pol)[0])
        self._fpflags(cx, insn, [], [a[i] for i in range(len(out)) if (kbits >> i) & 1], fmt)
        self._lanes_out(cx, dst, out, fmt, kbits)
        ev.mask_bits = kbits

    def h_vgetmant(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        interv, sc = imm.value & 3, (imm.value >> 2) & 3
        a = self._lanes_in(cx, insn, src, fmt, trace_mem)
        kbits = self.kmask(cx, insn)
        out = []
        for i in range(16 if fmt is fp.F32 else 8):
            x = a[i]
            k, s, v = fp.classify(x, fmt, pol)
            sign = 0 if (sc & 1) else s
            if k == fp.NAN:
                if fp.is_snan(x, fmt):
                    self._fpflags(cx, insn, ["invalid"])
                out.append(fp.quiet(x, fmt))
                continue
            if (sc & 2) and s:
                self._fpflags(cx, insn, ["invalid"])
                out.append(fmt.default_nan)
                continue
            if k == fp.INF:
                out.append(fmt.inf | (fmt.sign_bit if sign else 0))
                continue
            if k == fp.ZERO:
                out.append(fmt.sign_bit if sign else 0)
                continue
            # normalized significand: v = m * 2^e with 1 <= m < 2 (denormals are normalized here)
            e = fp._floor_log2(abs(v))
            m = abs(v) / (Fraction(2) ** e)
            mant_bits = int((m - 1) * (1 << fmt.mant))     # exact: m has at most fmt.mant fraction bits
            odd = e & 1
            if interv == 2 or (interv == 1 and odd) or (interv == 3 and (mant_bits >> (fmt.mant - 1)) & 1):
                exp_field = fmt.bias - 1       # [1/2,1)
            else:
                exp_field = fmt.bias           # [1,2)
            out.append((fmt.sign_bit if sign else 0) | (exp_field << fmt.mant) | mant_bits)
        self._fpflags(cx, insn, [], [a[i] for i in range(len(out)) if (kbits >> i) & 1], fmt)
        self._lanes_out(cx, dst, out, fmt, kbits)
        ev.mask_bits = kbits

    def h_vscale(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2 = insn.operands
        fmt = fp.F32
        pol = self.policy_for(insn)
        a = self.vsrc(cx, s1, insn, trace_mem, 4)
        kv = self.vsrc(cx, s2, insn, trace_mem, 4, target_float=False)
        kbits = self.kmask(cx, insn)
        out = []
        for i in range(16):
            x = a[i]
            k, s, v = fp.classify(x, fmt, pol)
            n = to_signed(kv[i], 32)
            if k == fp.NAN:
                if fp.is_snan(x, fmt):
                    self._fpflags(cx, insn, ["invalid"])
                out.append(fp.quiet(x, fmt))
                continue
            if k in (fp.INF, fp.ZERO):
                out.append(x)
                continue
            if n > 400:
                bits, flags = round_exact_overflow(fmt, pol, s)
            elif n < -400:
                bits, flags = fp.round_exact(Fraction(1 if not s else -1, 1 << 2000), fmt, pol)
            else:
                bits, flags = fp.round_exact(v * (Fraction(2) ** n), fmt, pol)
            self._fpflags(cx, insn, flags)
            out.append(bits)
        self._fpflags(cx, insn, [], [a[i] for i in range(16) if (kbits >> i) & 1], fmt)
        self.merge32(cx, dst, out, kbits)
        ev.mask_bits = kbits

    def _recip_like(self, cx, insn, ev, trace_mem, stream, rsqrt):
        dst, src = insn.operands
        fmt = fp.F32
        pol = fp.Policy("rn", False, False, "tiny")
        a = self.vsrc(cx, src, insn, trace_mem, 4)
        kbits = self.kmask(cx, insn)
        captured = insn.op in self.reciprocal_tables.descriptors
        if captured:
            desc = self.reciprocal_tables.descriptors[insn.op]
            self.assume("%s uses %s table %s (%s); exponent scaling was declared verified by the importer" %
                        (insn.op, desc["status"], desc["file"], desc["source"]))
        else:
            self._mark_approximate(insn)
        out = []
        for i in range(16):
            if not (kbits >> i) & 1:
                out.append(0)  # merge preserves inactive lanes; no table read or flags
                continue
            x = a[i]
            k, s, v = fp.classify(x, fmt, pol)
            if k == fp.NUM and ((x >> fmt.mant) & fmt.exp_mask) == 0:
                k, v = fp.ZERO, None      # both instructions treat input denormals as zeros (R27 pp.577, 588)
            if k == fp.NAN:
                if fp.is_snan(x, fmt):
                    self._fpflags(cx, insn, ["invalid"])
                out.append(fp.quiet(x, fmt))
            elif k == fp.ZERO:
                if rsqrt and s:
                    self._fpflags(cx, insn, ["zero_divide"])   # -0: -inf and #Z per the project reading of Table 6.29 (knc-div-sqrt.md)
                    out.append(fmt.inf | fmt.sign_bit)
                else:
                    self._fpflags(cx, insn, ["zero_divide"])
                    out.append(fmt.inf | (fmt.sign_bit if s else 0))
            elif k == fp.INF:
                if rsqrt and s:
                    self._fpflags(cx, insn, ["invalid"])
                    out.append(fmt.default_nan)
                else:
                    out.append(fmt.sign_bit if s else 0)
            elif rsqrt and s:
                self._fpflags(cx, insn, ["invalid"])
                out.append(fmt.default_nan)
            elif captured:
                out.append(self.reciprocal_tables.lookup(insn.op, x))
            else:
                if rsqrt:
                    r, _ = fp.fsqrt(x, fmt, pol)
                    kk, _, vv = fp.classify(r, fmt, pol)
                    bits, flags = fp.round_exact(1 / vv, fmt, pol)
                else:
                    bits, flags = fp.round_exact(1 / v, fmt, pol)
                if "underflow" in flags and not ((bits & ~fmt.sign_bit) == 0):
                    pass
                if (bits & ~fmt.sign_bit) and ((bits >> fmt.mant) & fmt.exp_mask) == 0:
                    bits &= fmt.sign_bit   # tiny results are flushed to zero by these instructions (knc-div-sqrt.md section 1.1)
                out.append(bits)
        self.merge32(cx, dst, out, kbits)
        ev.mask_bits = kbits

    def h_vrcp23(self, cx, insn, ev, trace_mem, stream):
        return self._recip_like(cx, insn, ev, trace_mem, stream, False)

    def h_vrsqrt23(self, cx, insn, ev, trace_mem, stream):
        return self._recip_like(cx, insn, ev, trace_mem, stream, True)

    def h_vfixupnan(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2 = insn.operands
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        a = self._lanes_in(cx, insn, s1, fmt, trace_mem)
        tbl = self.vsrc(cx, s2, insn, trace_mem, 4, target_float=False)
        if fmt is fp.F64:
            tbl = u32s_to_u64s(tbl)
        kbits = self.kmask(cx, insn)
        old = cx.zmm[dst.base] if fmt is fp.F32 else u32s_to_u64s(cx.zmm[dst.base])
        out = []
        for i in range(16 if fmt is fp.F32 else 8):
            x = a[i]
            k, s, v = fp.classify(x, fmt, pol)
            if k == fp.NAN:
                if fp.is_snan(x, fmt):
                    self._fpflags(cx, insn, ["invalid"])
                out.append(fp.quiet(x, fmt))
                continue
            if k == fp.INF:
                cls = 0 if s else 5
            elif k == fp.ZERO:
                cls = 2 if s else 3
            else:
                cls = 1 if s else 4
            token = (tbl[i] >> (3 * cls)) & 7
            r = {0: old[i], 1: fmt.inf | fmt.sign_bit, 2: fmt.sign_bit, 3: 0, 4: fmt.inf, 5: fmt.default_nan,
                 6: fmt.max_finite, 7: fmt.max_finite | fmt.sign_bit}[token]
            out.append(r)
        self._lanes_out(cx, dst, out, fmt, kbits)
        ev.mask_bits = kbits

    def h_stmxcsr(self, cx, insn, ev, trace_mem, stream):
        (dst,) = insn.operands
        self.mstore(cx, dst, cx.mxcsr, 4, trace_mem)

    def h_nop(self, cx, insn, ev, trace_mem, stream):
        return None

    # --- branches -----------------------------------------------------------------------------
    def _cond(self, cx, cond):
        f = cx.flags
        return {"zf": f["ZF"], "nzf": not f["ZF"], "lt": f["SF"] != f["OF"], "ge": f["SF"] == f["OF"],
                "gt": (not f["ZF"]) and f["SF"] == f["OF"], "le": f["ZF"] or f["SF"] != f["OF"],
                "cf": f["CF"], "ncf": not f["CF"], "a": (not f["CF"]) and (not f["ZF"]), "be": f["CF"] or f["ZF"],
                "sf": f["SF"], "nsf": not f["SF"], "pf": f["PF"], "npf": not f["PF"]}[cond]

    def _branch(self, cx, insn, ev, stream, taken):
        ev.taken = bool(taken)
        if taken:
            return stream.labels[insn.target]
        return None

    def h_jmp(self, cx, insn, ev, trace_mem, stream):
        return self._branch(cx, insn, ev, stream, True)

    def h_jmp_table(self, cx, insn, ev, trace_mem, stream):
        index = self.rget(cx, insn.operands[0], insn.operands[0].width)
        if index >= len(insn.targets):
            raise InvalidInput("%s: jump table index %d outside %d entries" % (insn.id, index, len(insn.targets)))
        self.assume("resolved read-only jump table: targets are fixed; indirect target prediction follows the scenario branch rule (assumed, not a documented indirect predictor)")
        ev.taken = True
        ev.branch_target = stream.labels[insn.targets[index]]
        return ev.branch_target

    def h_jcc(self, cx, insn, ev, trace_mem, stream):
        return self._branch(cx, insn, ev, stream, self._cond(cx, insn.spec["cond"]))

    def h_jk(self, cx, insn, ev, trace_mem, stream):
        kreg = insn.operands[0]
        v = cx.k[kreg.base]
        taken = (v == 0) if insn.spec["cond"] == "kz" else (v != 0)
        return self._branch(cx, insn, ev, stream, taken)

    def h_setcc(self, cx, insn, ev, trace_mem, stream):
        (dst,) = insn.operands
        self.sset(cx, dst, 1 if self._cond(cx, insn.spec["cond"]) else 0, 8, trace_mem)

    # --- mask ---------------------------------------------------------------------------------
    def h_kmov(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        v = cx.k[src.base] if src.kind == "k" else (self.rget(cx, src, 32) & 0xFFFF)
        if dst.kind == "k":
            cx.k[dst.base] = v
        else:
            self.rset(cx, dst, v, 32)

    def h_klogic(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        a, b = cx.k[dst.base], cx.k[src.base]
        r = {"kand": a & b, "kor": a | b, "kxor": a ^ b, "kxnor": ~(a ^ b), "kandn": (~a) & b, "kandnr": (~b) & a}[insn.op]
        cx.k[dst.base] = r & 0xFFFF

    def h_knot(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        cx.k[dst.base] = (~cx.k[src.base]) & 0xFFFF

    def h_kortest(self, cx, insn, ev, trace_mem, stream):
        a, b = insn.operands
        v = cx.k[a.base] | cx.k[b.base]
        cx.flags["ZF"] = 1 if v == 0 else 0
        cx.flags["CF"] = 1 if v == 0xFFFF else 0
        cx.flags["SF"] = 0
        cx.flags["OF"] = 0

    # --- vector FP ------------------------------------------------------------------------------
    def _fmt(self, insn):
        return fp.F32 if insn.spec["fmt"] == "f32" else fp.F64

    def _minmax(self, a, b, fmt, pol, want_max):
        ka = fp.classify(a, fmt, pol)[0]
        kb = fp.classify(b, fmt, pol)[0]
        if ka == fp.NAN or kb == fp.NAN:
            return b
        c = fp.fcompare(a, b, fmt, pol)
        if c == "eq":
            return b
        if want_max:
            return a if c == "gt" else b
        return a if c == "lt" else b

    def h_vfp2(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2 = insn.operands
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        elem = 4 if fmt is fp.F32 else 8
        a = self.vsrc(cx, s1, insn, trace_mem, elem)
        b = self.vsrc(cx, s2, insn, trace_mem, elem)
        kbits = self.kmask(cx, insn)
        opk = insn.spec["opk"]
        if fmt is fp.F64:
            a, b = u32s_to_u64s(a), u32s_to_u64s(b)
        out = []
        for i in range(16 if fmt is fp.F32 else 8):
            if opk == "add":
                r, info = fp.fadd(a[i], b[i], fmt, pol)
            elif opk == "sub":
                r, info = fp.fsub(a[i], b[i], fmt, pol)
            elif opk == "subr":
                r, info = fp.fsub(b[i], a[i], fmt, pol)
            else:
                r, info = fp.fmul(a[i], b[i], fmt, pol)
            if (kbits >> i) & 1:
                self._fpflags(cx, insn, _info_flags(info, a[i], b[i], fmt), [a[i], b[i]], fmt)
            out.append(r)
        if fmt is fp.F32:
            self.merge32(cx, dst, out, kbits)
        else:
            self.merge64(cx, dst, out, kbits & 0xFF)
        ev.mask_bits = kbits

    def h_vfma(self, cx, insn, ev, trace_mem, stream):
        o1, o2, o3 = insn.operands
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        elem = 4 if fmt is fp.F32 else 8
        v1 = list(cx.zmm[o1.base])
        v2 = self.vsrc(cx, o2, insn, trace_mem, elem)
        v3 = self.vsrc(cx, o3, insn, trace_mem, elem)
        form = insn.spec["form"]
        negp, negc = insn.spec["negp"], insn.spec["negc"]
        kbits = self.kmask(cx, insn)

        def pick(i, a, b, c):
            if form == "132":
                return a[i], c[i], b[i]
            if form == "213":
                return b[i], a[i], c[i]
            return b[i], c[i], a[i]
        if fmt is fp.F32:
            srcs = (v1, v2, v3)
            lanes = 16
        else:
            srcs = (u32s_to_u64s(v1), u32s_to_u64s(v2), u32s_to_u64s(v3))
            lanes = 8
        out = []
        for i in range(lanes):
            x, y, z = pick(i, *srcs)
            r, info = fp.ffma(x, y, z, fmt=fmt, policy=pol, negate_product=negp, negate_c=negc)
            if (kbits >> i) & 1:
                self._fpflags(cx, insn, _info_flags(info, x, y, z, fmt), [x, y, z], fmt)
            out.append(r)
        if fmt is fp.F32:
            self.merge32(cx, o1, out, kbits)
        else:
            self.merge64(cx, o1, out, kbits & 0xFF)
        ev.mask_bits = kbits

    def h_vcmp(self, cx, insn, ev, trace_mem, stream):
        if "fixed_pred" in insn.spec:
            dst, s1, s2 = insn.operands
            pred = insn.spec["fixed_pred"]
        else:
            dst, s1, s2, imm = insn.operands
            pred = imm.value & 7
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        elem = 4 if fmt is fp.F32 else 8
        a = self.vsrc(cx, s1, insn, trace_mem, elem)
        b = self.vsrc(cx, s2, insn, trace_mem, elem)
        kbits = self.kmask(cx, insn)
        lanes = 16 if fmt is fp.F32 else 8
        if fmt is fp.F64:
            a, b = u32s_to_u64s(a), u32s_to_u64s(b)
        res = 0
        for i in range(lanes):
            if not (kbits >> i) & 1:
                continue
            c = fp.fcompare(a[i], b[i], fmt, pol)
            hit = {0: c == "eq", 1: c == "lt", 2: c in ("lt", "eq"), 3: c == "unordered", 4: c != "eq",
                   5: c != "lt", 6: c not in ("lt", "eq"), 7: c != "unordered"}[pred]
            if hit:
                res |= 1 << i
        cx.k[dst.base] = res
        ev.mask_bits = kbits

    def h_vblendm(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2 = insn.operands
        fmt = fp.F32 if insn.spec.get("fmt") in ("f32", "i32") else fp.F64
        elem = 4 if fmt is fp.F32 else 8
        a = self.vsrc(cx, s1, insn, trace_mem, elem)
        b = self.vsrc(cx, s2, insn, trace_mem, elem)
        kbits = self.kmask(cx, insn)
        if fmt is fp.F32:
            cx.zmm[dst.base] = [b[i] if (kbits >> i) & 1 else a[i] for i in range(16)]
        else:
            a64, b64 = u32s_to_u64s(a), u32s_to_u64s(b)
            cx.zmm[dst.base] = u64s_to_u32s([b64[i] if (kbits >> i) & 1 else a64[i] for i in range(8)])
        ev.mask_bits = kbits

    def _cvt_rounding(self, insn, imm):
        if imm.value >> 2:
            raise Unsupported("instruction %s: conversion immediate 0x%x uses exponent-adjust bits; only the rounding field (bits 1:0) is supported" % (insn.id, imm.value))
        return ("rn", "rd", "ru", "rz")[imm.value & 3]

    def h_vcvt_i2f(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        pol = self.policy_for(insn, self._cvt_rounding(insn, imm))
        a = self.vsrc(cx, src, insn, trace_mem, 4, target_float=False)
        out = [fp.int_to_float(to_signed(a[i], 32), fp.F32, pol)[0] for i in range(16)]
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vcvt_u2f(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        pol = self.policy_for(insn, self._cvt_rounding(insn, imm))
        a = self.vsrc(cx, src, insn, trace_mem, 4, target_float=False)
        out = [fp.int_to_float(a[i], fp.F32, pol)[0] for i in range(16)]
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vcvt_f2i(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        pol = self.policy_for(insn, self._cvt_rounding(insn, imm))
        a = self.vsrc(cx, src, insn, trace_mem, 4)
        signed = insn.spec["signed"]
        out = []
        for i in range(16):
            q, err = fp.float_to_int(a[i], fp.F32, pol, signed=signed, width=32)
            if err:
                self.assume("out-of-range or NaN float-to-int conversion produced the x86 integer indefinite (0x80000000 signed, 0xFFFFFFFF unsigned); KNC-specific value not verified")
                q = 0x80000000 if signed else 0xFFFFFFFF
            out.append(q & 0xFFFFFFFF)
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vcvt_d2i(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        pol = self.policy_for(insn, self._cvt_rounding(insn, imm))
        a = u32s_to_u64s(self.vsrc(cx, src, insn, trace_mem, 8))
        signed = insn.spec["signed"]
        out = []
        for i in range(8):
            q, err = fp.float_to_int(a[i], fp.F64, pol, signed=signed, width=32)
            if err:
                self.assume("out-of-range or NaN double-to-int conversion produced the x86 integer indefinite; KNC-specific value not verified")
                q = 0x80000000 if signed else 0xFFFFFFFF
            out.append(q & 0xFFFFFFFF)
        out += [0] * 8
        self.assume("vcvtfxpntpd2dq/udq write the 8 results to the low lanes and zero the upper 8 (assumed)")
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vcvt_s2d(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        a = self.vsrc(cx, src, insn, trace_mem, 4)
        out = [fp.convert(a[i], fp.F32, fp.F64)[0] for i in range(8)]
        self.merge64(cx, dst, out, self.kmask(cx, insn) & 0xFF)

    def h_vcvt_d2s(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        pol = self.policy_for(insn)
        a = u32s_to_u64s(self.vsrc(cx, src, insn, trace_mem, 8))
        out = [fp.convert(a[i], fp.F64, fp.F32, pol)[0] for i in range(8)] + [0] * 8
        self.assume("vcvtpd2ps writes 8 floats to the low lanes and zeroes the upper 8 (assumed)")
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vrnd(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        pol = self.policy_for(insn, self._cvt_rounding(insn, imm))
        a = self.vsrc(cx, src, insn, trace_mem, 4)
        out = []
        for i in range(16):
            k, s, v = fp.classify(a[i], fp.F32, pol)
            if k != fp.NUM:
                out.append(a[i])
                continue
            q, err = fp.float_to_int(a[i], fp.F32, pol, signed=True, width=64)
            if err:
                out.append(a[i])  # huge values are already integers
                continue
            if q == 0:
                out.append(0x80000000 if s else 0)
            else:
                out.append(fp.int_to_float(q, fp.F32, pol)[0])
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    # --- vector int --------------------------------------------------------------------------------
    def h_vint2(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2 = insn.operands
        a = self.vsrc(cx, s1, insn, trace_mem, 4, target_float=False)
        b = self.vsrc(cx, s2, insn, trace_mem, 4, target_float=False)
        opk = insn.spec["opk"]
        out = []
        for i in range(16):
            x, y = a[i], b[i]
            if opk == "add":
                r = x + y
            elif opk == "sub":
                r = x - y
            elif opk == "subr":
                r = y - x
            elif opk == "and":
                r = x & y
            elif opk == "andn":
                r = (~x) & y
            elif opk == "or":
                r = x | y
            elif opk == "xor":
                r = x ^ y
            elif opk == "mullo":
                r = x * y
            elif opk == "mulhs":
                r = (to_signed(x, 32) * to_signed(y, 32)) >> 32
            elif opk == "mulhu":
                r = (x * y) >> 32
            elif opk == "mins":
                r = min(to_signed(x, 32), to_signed(y, 32))
            elif opk == "maxs":
                r = max(to_signed(x, 32), to_signed(y, 32))
            elif opk == "minu":
                r = min(x, y)
            elif opk == "maxu":
                r = max(x, y)
            elif opk == "shlv":
                r = x << y if y < 32 else 0
            elif opk == "shrv":
                r = x >> y if y < 32 else 0
            elif opk == "sarv":
                r = to_signed(x, 32) >> min(y, 31)
            out.append(r & 0xFFFFFFFF)
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vint2q(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2 = insn.operands
        a = u32s_to_u64s(self.vsrc(cx, s1, insn, trace_mem, 8, target_float=False))
        b = u32s_to_u64s(self.vsrc(cx, s2, insn, trace_mem, 8, target_float=False))
        opk = insn.spec["opk"]
        out = []
        for i in range(8):
            x, y = a[i], b[i]
            r = {"and": x & y, "or": x | y, "xor": x ^ y, "andn": (~x) & y}[opk]
            out.append(r & 0xFFFFFFFFFFFFFFFF)
        self.merge64(cx, dst, out, self.kmask(cx, insn) & 0xFF)

    def h_vshift_imm(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        a = self.vsrc(cx, src, insn, trace_mem, 4, target_float=False)
        c = imm.value & 0xFF
        opk = insn.spec["opk"]
        out = []
        for x in a:
            if opk == "shl":
                r = (x << c) if c < 32 else 0
            elif opk == "shr":
                r = (x >> c) if c < 32 else 0
            else:
                r = to_signed(x, 32) >> min(c, 31)
            out.append(r & 0xFFFFFFFF)
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vpcmp(self, cx, insn, ev, trace_mem, stream):
        if "fixed_pred" in insn.spec:
            dst, s1, s2 = insn.operands
            pred = insn.spec["fixed_pred"]
        else:
            dst, s1, s2, imm = insn.operands
            pred = imm.value & 7
        if pred in (3, 7):
            raise Unsupported("instruction %s: compare predicate %d (false/true) not supported" % (insn.id, pred))
        a = self.vsrc(cx, s1, insn, trace_mem, 4, target_float=False)
        b = self.vsrc(cx, s2, insn, trace_mem, 4, target_float=False)
        signed = insn.spec["signed"]
        kbits = self.kmask(cx, insn)
        res = 0
        for i in range(16):
            if not (kbits >> i) & 1:
                continue
            x, y = (to_signed(a[i], 32), to_signed(b[i], 32)) if signed else (a[i], b[i])
            hit = {0: x == y, 1: x < y, 2: x <= y, 4: x != y, 5: x >= y, 6: x > y}[pred]
            if hit:
                res |= 1 << i
        cx.k[dst.base] = res
        ev.mask_bits = kbits

    def h_vpermd(self, cx, insn, ev, trace_mem, stream):
        dst, idx, src = insn.operands
        ix = list(cx.zmm[idx.base])
        s = self.vsrc(cx, src, insn, trace_mem, 4, target_float=False)
        out = [s[ix[i] & 15] for i in range(16)]
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vpermf32x4(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        s = self.vsrc(cx, src, insn, trace_mem, 4)
        out = []
        for g in range(4):
            sg = (imm.value >> (2 * g)) & 3
            out.extend(s[4 * sg:4 * sg + 4])
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vbroadcast(self, cx, insn, ev, trace_mem, stream):
        dst, mem = insn.operands
        addr = self.ea(cx, mem)
        n = insn.spec["elem"]
        data = self.memory.read(addr, n, cx.ctx)
        trace_mem.append((addr, n))
        if n == 4:
            self.merge32(cx, dst, list(struct.unpack("<I", data)) * 16, self.kmask(cx, insn))
        else:
            self.merge64(cx, dst, list(struct.unpack("<Q", data)) * 8, self.kmask(cx, insn) & 0xFF)

    def h_vbroadcast4(self, cx, insn, ev, trace_mem, stream):
        dst, mem = insn.operands
        addr = self.ea(cx, mem)
        n = insn.spec["mem_size"]
        data = self.memory.read(addr, n, cx.ctx)
        trace_mem.append((addr, n))
        if insn.spec["elem"] == 4:
            self.merge32(cx, dst, list(struct.unpack("<4I", data)) * 4, self.kmask(cx, insn))
        else:
            self.merge64(cx, dst, list(struct.unpack("<4Q", data)) * 2, self.kmask(cx, insn) & 0xFF)

    # --- vector memory -----------------------------------------------------------------------------
    def _downconvert(self, lanes, conv, is_float, policy):
        """16 u32 lanes -> bytes under a down-conversion modifier (saturating integer narrowing assumed)."""
        if conv == "float16":
            if not is_float:
                raise Unsupported("float16 down-conversion of an integer vector is not supported")
            return b"".join(struct.pack("<H", fp.convert(l, fp.F32, fp.F16, policy)[0]) for l in lanes)
        if is_float:
            ints = []
            for l in lanes:
                q, err = fp.float_to_int(l, fp.F32, policy, signed=True, width=64)
                ints.append(0 if err else q)
            self.assume("float-to-integer down-conversion rounds with the policy mode and saturates (assumed)")
        else:
            ints = [to_signed(l, 32) if conv.startswith("s") else l for l in lanes]
            self.assume("integer down-conversion saturates to the target range (assumed)")
        lo, hi, fmtc = {"uint8": (0, 255, "<B"), "sint8": (-128, 127, "<b"), "uint16": (0, 65535, "<H"), "sint16": (-32768, 32767, "<h")}[conv]
        return b"".join(struct.pack(fmtc, max(lo, min(hi, v))) for v in ints)

    def h_vmov(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        kbits = self.kmask(cx, insn)
        ev.mask_bits = kbits
        wide64 = insn.op in ("vmovapd", "vmovdqa64")
        is_float = insn.op in ("vmovaps", "vmovapd")
        if isinstance(dst, Mem):
            addr = self.ea(cx, dst)
            lanes = cx.zmm[src.base]
            if src.swizzle:
                raise Unsupported("instruction %s: swizzle on a store source is not supported" % insn.id)
            if src.conv:
                if wide64:
                    raise Unsupported("instruction %s: down-conversion from 64-bit lanes is not supported" % insn.id)
                data = self._downconvert(lanes, src.conv, is_float, self.policy_for(insn))
                esz = len(data) // 16
                for i in range(16):
                    if (kbits >> i) & 1:
                        self.memory.write(addr + esz * i, data[esz * i:esz * i + esz], cx.ctx)
                trace_mem.append((addr, len(data)))
                return None
            if addr % 64:
                raise InvalidInput("instruction %s: vector store at 0x%x is not 64-byte aligned (faults on KNC)" % (insn.id, addr))
            data = struct.pack("<16I", *lanes)
            esz = 8 if wide64 else 4
            for i in range(64 // esz):
                if (kbits >> i) & 1:
                    self.memory.write(addr + esz * i, data[esz * i:esz * i + esz], cx.ctx)
            trace_mem.append((addr, 64))
        else:
            v = self.vsrc(cx, src, insn, trace_mem, 8 if wide64 else 4, target_float=is_float)
            if wide64:
                self.merge64(cx, dst, u32s_to_u64s(v), kbits & 0xFF)
            else:
                self.merge32(cx, dst, v, kbits)

    def h_vstore_ngo(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        addr = self.ea(cx, dst)
        if addr % 64:
            raise InvalidInput("instruction %s: streaming store at 0x%x is not 64-byte aligned" % (insn.id, addr))
        if insn.mask is not None:
            raise Unsupported("instruction %s: masked no-read store is not supported (whole-line semantics only)" % insn.id)
        self.memory.write(addr, struct.pack("<16I", *cx.zmm[src.base]), cx.ctx)
        trace_mem.append((addr, 64))
        ev.mask_bits = 0xFFFF

    def h_vunpack(self, cx, insn, ev, trace_mem, stream):
        dst, mem = insn.operands
        elem = insn.spec["elem"]
        half = insn.spec["half"]
        is_float = insn.op.endswith(("ps", "pd"))
        kbits = self.kmask(cx, insn)
        addr = self.ea(cx, mem)
        conv = mem.conv
        if conv and elem != 4:
            raise Unsupported("instruction %s: up-conversion into 64-bit lanes is not supported" % insn.id)
        esz = elem if not conv else (2 if conv in ("float16", "uint16", "sint16") else 1)
        count = 16 if elem == 4 else 8
        if half == "l":
            line_end = (addr | 63) + 1
            sel = [i for i in range(count) if addr + esz * i < line_end]
            base = addr
        else:
            line_start = addr & ~63
            base = addr - 64
            sel = [i for i in range(count) if base + esz * i >= line_start]
        new = list(cx.zmm[dst.base]) if elem == 4 else u32s_to_u64s(cx.zmm[dst.base])
        touched = []
        for i in sel:
            if not (kbits >> i) & 1:
                continue
            a = base + esz * i
            data = self.memory.read(a, esz, cx.ctx)
            touched.append((a, esz))
            if conv:
                lanes = self._upconvert(data * 16, conv, is_float, self.policy_for(insn))
                new[i] = lanes[0]
            elif elem == 4:
                new[i] = struct.unpack("<I", data)[0]
            else:
                new[i] = struct.unpack("<Q", data)[0]
        cx.zmm[dst.base] = new if elem == 4 else u64s_to_u32s(new)
        if touched:
            lo = min(a for a, _ in touched)
            hi = max(a + n for a, n in touched)
            trace_mem.append((lo, hi - lo))
        else:
            ev.addr, ev.nbytes, ev.lines = addr, 0, ()
        ev.mask_bits = kbits

    def h_vpackstore(self, cx, insn, ev, trace_mem, stream):
        mem, src = insn.operands
        elem = insn.spec["elem"]
        half = insn.spec["half"]
        is_float = insn.op.endswith(("ps", "pd"))
        kbits = self.kmask(cx, insn)
        addr = self.ea(cx, mem)
        conv = src.conv
        if src.swizzle:
            raise Unsupported("instruction %s: swizzle on a store source is not supported" % insn.id)
        if conv and elem != 4:
            raise Unsupported("instruction %s: down-conversion from 64-bit lanes is not supported" % insn.id)
        esz = elem if not conv else (2 if conv in ("float16", "uint16", "sint16") else 1)
        count = 16 if elem == 4 else 8
        lanes = cx.zmm[src.base]
        if conv:
            data = self._downconvert(lanes, conv, is_float, self.policy_for(insn))
        else:
            data = struct.pack("<16I", *lanes)
        if half == "l":
            line_end = (addr | 63) + 1
            sel = [i for i in range(count) if addr + esz * i < line_end]
            base = addr
        else:
            line_start = addr & ~63
            base = addr - 64
            sel = [i for i in range(count) if base + esz * i >= line_start]
        touched = []
        for i in sel:
            if not (kbits >> i) & 1:
                continue
            a = base + esz * i
            self.memory.write(a, data[esz * i:esz * i + esz], cx.ctx)
            touched.append((a, esz))
        if touched:
            lo = min(a for a, _ in touched)
            hi = max(a + n for a, n in touched)
            trace_mem.append((lo, hi - lo))
        else:
            ev.addr, ev.nbytes, ev.lines = addr, 0, ()
        ev.mask_bits = kbits

    def _lane_addrs(self, cx, insn, mem, elem):
        idx = cx.zmm[mem.vindex.base]
        count = 16 if elem == 4 else 8
        base = (cx.gpr[mem.base.base] if mem.base else 0) + mem.disp
        return [mask64(base + to_signed(idx[i], 32) * mem.scale) for i in range(count)]

    def h_vgather(self, cx, insn, ev, trace_mem, stream):
        dst, mem = insn.operands
        if mem.vindex is None:
            raise InvalidInput("instruction %s: gather needs a vindex register" % insn.id)
        if insn.mask is None:
            raise InvalidInput("instruction %s: gather needs a write mask (completion mask)" % insn.id)
        elem = insn.spec["elem"]
        kbits = cx.k[insn.mask.base]
        addrs = self._lane_addrs(cx, insn, mem, elem)
        out = list(cx.zmm[dst.base]) if elem == 4 else u32s_to_u64s(cx.zmm[dst.base])
        lines = set()
        first = None
        done_bits = 0
        one_line = self.gather_one_line
        for i, a in enumerate(addrs):
            if not (kbits >> i) & 1:
                continue
            if one_line and first is not None and lines_of(a, elem)[0] != lines_of(first, elem)[0]:
                continue  # another cache line: left pending in the mask for the next execution
            data = self.memory.read(a, elem, cx.ctx)
            out[i] = struct.unpack("<I" if elem == 4 else "<Q", data)[0]
            lines.update(lines_of(a, elem))
            done_bits |= 1 << i
            if first is None:
                first = a
        cx.zmm[dst.base] = out if elem == 4 else u64s_to_u32s(out)
        cx.k[insn.mask.base] = kbits & ~done_bits
        ev.addr = first
        ev.nbytes = elem * bin(done_bits).count("1")
        ev.lines = tuple(sorted(lines))
        ev.mask_bits = kbits

    def h_vscatter(self, cx, insn, ev, trace_mem, stream):
        mem, src = insn.operands
        if mem.vindex is None:
            raise InvalidInput("instruction %s: scatter needs a vindex register" % insn.id)
        if insn.mask is None:
            raise InvalidInput("instruction %s: scatter needs a write mask (completion mask)" % insn.id)
        elem = insn.spec["elem"]
        kbits = cx.k[insn.mask.base]
        addrs = self._lane_addrs(cx, insn, mem, elem)
        data = struct.pack("<16I", *cx.zmm[src.base])
        lines = set()
        first = None
        done_bits = 0
        one_line = self.gather_one_line
        for i, a in enumerate(addrs):
            if not (kbits >> i) & 1:
                continue
            if one_line and first is not None and lines_of(a, elem)[0] != lines_of(first, elem)[0]:
                continue
            self.memory.write(a, data[elem * i:elem * i + elem], cx.ctx)
            lines.update(lines_of(a, elem))
            done_bits |= 1 << i
            if first is None:
                first = a
        cx.k[insn.mask.base] = kbits & ~done_bits
        ev.addr = first
        ev.nbytes = elem * bin(done_bits).count("1")
        ev.lines = tuple(sorted(lines))
        ev.mask_bits = kbits

    def h_prefetch(self, cx, insn, ev, trace_mem, stream):
        (mem,) = insn.operands
        addr = self.ea(cx, mem)
        ev.addr = addr
        ev.nbytes = 64
        ev.lines = lines_of(addr & ~63, 64)
        ev.pf_level = insn.spec["level"]

    # --- x87 -------------------------------------------------------------------------------------
    def _x87_policy(self, cx):
        rc = (cx.fcw >> 10) & 3
        pc = (cx.fcw >> 8) & 3
        rounding = ("rn", "rd", "ru", "rz")[rc]
        fmt = {0: fp.F80_P24, 2: fp.F80_P53, 3: fp.F80}.get(pc)
        if fmt is None:
            raise Unsupported("x87 precision control value 1 is reserved")
        if pc != 3:
            self.assume("x87 precision control is %d-bit: results round to that significand with the extended exponent range" % (24 if pc == 0 else 53))
        return fp.Policy(rounding), fmt

    def _x87_round(self, frac_or_bits_fn, cx):
        pass

    def _x87_result(self, exact_value, cx, sign_zero=0):
        """Round an exact Fraction (or special marker) to the current x87 precision -> F80 bits."""
        pol, fmt = self._x87_policy(cx)
        bits, flags = fp.round_exact(exact_value, fmt, pol, zero_sign=sign_zero)
        if fmt is not fp.F80:
            bits = fp.convert(bits, fmt, fp.F80)[0]
        return bits

    def _x87_binop(self, op, a, b, cx):
        """a OP b on F80 bits with x87 rounding. Specials via fp helpers at full extended precision."""
        pol, fmt = self._x87_policy(cx)
        if op == "add":
            r, _ = fp.fadd(a, b, fp.F80, pol)
        elif op == "sub":
            r, _ = fp.fsub(a, b, fp.F80, pol)
        elif op == "mul":
            r, _ = fp.fmul(a, b, fp.F80, pol)
        else:
            r = self._x87_div(a, b, pol)
        if fmt is not fp.F80:
            # re-round to the precision-control significand (double rounding is innocuous: 64 >= 2*53+2 and 2*24+2)
            r = fp.convert(fp.convert(r, fp.F80, fmt, pol)[0], fmt, fp.F80)[0]
        return r

    def _x87_div(self, a, b, pol):
        ka, sa, va = fp.classify(a, fp.F80)
        kb, sb, vb = fp.classify(b, fp.F80)
        fmt = fp.F80
        if ka == fp.NAN or kb == fp.NAN:
            return fp.quiet(a if ka == fp.NAN else b, fmt)
        sign = sa ^ sb
        if ka == fp.INF and kb == fp.INF:
            return fmt.default_nan
        if ka == fp.ZERO and kb == fp.ZERO:
            return fmt.default_nan
        if ka == fp.INF or kb == fp.ZERO:
            return fmt.inf | (fmt.sign_bit if sign else 0)
        if kb == fp.INF or ka == fp.ZERO:
            return fmt.sign_bit if sign else 0
        bits, _ = fp.round_exact(va / vb, fmt, pol)
        return bits

    def _x87_mark(self, ev, cx, reads, writes):
        ev.xreads = set("x87r%d" % cx.fphys(i) for i in reads)
        ev.xwrites = set("x87r%d" % cx.fphys(i) for i in writes)

    def h_x87(self, cx, insn, ev, trace_mem, stream):
        op = insn.spec["op"]
        spec = insn.spec
        pol, _ = self._x87_policy(cx)
        if op == "fld":
            (src,) = insn.operands
            if isinstance(src, Mem):
                n = spec["mem_size"]
                raw, _ = self.mload(cx, src, n, trace_mem)
                if n == 4:
                    bits = fp.convert(raw, fp.F32, fp.F80)[0]
                elif n == 8:
                    bits = fp.convert(raw, fp.F64, fp.F80)[0]
                else:
                    bits = fp.f80_from_memory(raw.to_bytes(10, "little"))
                self._x87_mark(ev, cx, [], [-1])
                cx.fpush(bits, insn)
            else:
                bits = cx.fget(src.index, insn)
                self._x87_mark(ev, cx, [src.index], [-1])
                cx.fpush(bits, insn)
            return None
        if op == "fild":
            (src,) = insn.operands
            n = spec["mem_size"]
            raw, _ = self.mload(cx, src, n, trace_mem)
            v = to_signed(raw, 8 * n)
            bits = fp.round_exact(Fraction(v), fp.F80, pol)[0]
            self._x87_mark(ev, cx, [], [-1])
            cx.fpush(bits, insn)
            return None
        if op == "fldconst":
            bits = 0 if spec["const"] == "zero" else fp.convert(0x3f800000, fp.F32, fp.F80)[0]
            self._x87_mark(ev, cx, [], [-1])
            cx.fpush(bits, insn)
            return None
        if op == "fst":
            (dst,) = insn.operands
            val = cx.fget(0, insn)
            if isinstance(dst, Mem):
                n = spec["mem_size"]
                if n == 4:
                    out = fp.convert(val, fp.F80, fp.F32, pol)[0]
                elif n == 8:
                    out = fp.convert(val, fp.F80, fp.F64, pol)[0]
                else:
                    out = int.from_bytes(fp.f80_to_memory(val), "little")
                self.mstore(cx, dst, out, n, trace_mem)
                self._x87_mark(ev, cx, [0], [])
            else:
                self._x87_mark(ev, cx, [0], [dst.index])
                cx.fst[cx.fphys(dst.index)] = val
            if spec.get("pop"):
                cx.fpop(insn)
            return None
        if op in ("fistp", "fisttp"):
            (dst,) = insn.operands
            n = spec["mem_size"]
            val = cx.fget(0, insn)
            p = fp.Policy("rz") if op == "fisttp" else pol
            q, err = fp.float_to_int(val, fp.F80, p, signed=True, width=8 * n)
            if err:
                q = INT_INDEFINITE[n]
                self.assume("x87 integer store out of range or NaN produced the integer indefinite")
            self.mstore(cx, dst, q & ((1 << (8 * n)) - 1), n, trace_mem)
            self._x87_mark(ev, cx, [0], [])
            if spec.get("pop"):
                cx.fpop(insn)
            return None
        if op in ("fadd", "fsub", "fsubr", "fmul", "fdiv", "fdivr", "add", "sub", "subr", "mul", "div", "divr"):
            base = op.lstrip("f") if op.startswith("f") else op
            kind = {"add": "add", "sub": "sub", "subr": "subr", "mul": "mul", "div": "div", "divr": "divr"}[base]
            if spec.get("mem"):
                (src,) = insn.operands
                n = spec["mem_size"]
                raw, _ = self.mload(cx, src, n, trace_mem)
                if spec.get("mem_int"):
                    b = fp.round_exact(Fraction(to_signed(raw, 8 * n)), fp.F80, pol)[0]
                else:
                    b = fp.convert(raw, fp.F32 if n == 4 else fp.F64, fp.F80)[0]
                a = cx.fget(0, insn)
                di = 0
                reads = [0]
            elif len(insn.operands) == 0:
                # 'faddp' alone: st(1) = st(1) OP st(0), pop
                a = cx.fget(1, insn)
                b = cx.fget(0, insn)
                di = 1
                reads = [0, 1]
                spec = dict(spec, pop=True)
            else:
                dst, src = insn.operands
                if dst.index == 0 and src.index != 0:
                    a = cx.fget(0, insn)          # st0 = st0 OP st(i)
                    b = cx.fget(src.index, insn)
                    di = 0
                    reads = [0, src.index]
                else:
                    # dest st(i), source st0: GAS reverses the sense of fsub/fdiv for these forms
                    a = cx.fget(dst.index, insn)
                    b = cx.fget(0, insn)
                    di = dst.index
                    reads = [0, dst.index]
                    if kind in ("sub", "subr", "div", "divr"):
                        kind = {"sub": "subr_gas", "subr": "sub_gas", "div": "divr_gas", "divr": "div_gas"}[kind]
            # resolve operand order: result = x OP y
            if kind in ("add", "mul"):
                r = self._x87_binop(kind, a, b, cx)
            elif kind == "sub":            # a - b  (st0 - st(i), or st0 - mem)
                r = self._x87_binop("sub", a, b, cx)
            elif kind == "subr":           # b - a
                r = self._x87_binop("sub", b, a, cx)
            elif kind == "sub_gas":        # AT&T fsubr %st,%st(i): st(i) = st(i) - st0  (a=st(i), b=st0)
                r = self._x87_binop("sub", a, b, cx)
            elif kind == "subr_gas":       # AT&T fsub %st,%st(i): st(i) = st0 - st(i)
                r = self._x87_binop("sub", b, a, cx)
            elif kind == "div":
                r = self._x87_binop("div", a, b, cx)
            elif kind == "divr":
                r = self._x87_binop("div", b, a, cx)
            elif kind == "div_gas":        # fdivr %st,%st(i): st(i) = st(i) / st0
                r = self._x87_binop("div", a, b, cx)
            else:                          # fdiv %st,%st(i): st(i) = st0 / st(i)
                r = self._x87_binop("div", b, a, cx)
            self._x87_mark(ev, cx, reads, [di])
            cx.fst[cx.fphys(di)] = r
            if spec.get("pop"):
                cx.fpop(insn)
            return None
        if op == "fxch":
            i = insn.operands[0].index if insn.operands else 1
            a = cx.fget(0, insn)
            b = cx.fget(i, insn)
            cx.fst[cx.fphys(0)], cx.fst[cx.fphys(i)] = b, a
            self._x87_mark(ev, cx, [0, i], [0, i])
            return None
        if op == "fchs":
            v = cx.fget(0, insn)
            cx.fst[cx.fphys(0)] = v ^ fp.F80.sign_bit
            self._x87_mark(ev, cx, [0], [0])
            return None
        if op == "fabs":
            v = cx.fget(0, insn)
            cx.fst[cx.fphys(0)] = v & ~fp.F80.sign_bit
            self._x87_mark(ev, cx, [0], [0])
            return None
        if op == "fsqrt":
            v = cx.fget(0, insn)
            p2, fmt = self._x87_policy(cx)
            r, _ = fp.fsqrt(v, fp.F80, p2)
            if fmt is not fp.F80:
                r = fp.convert(fp.convert(r, fp.F80, fmt, p2)[0], fmt, fp.F80)[0]
            cx.fst[cx.fphys(0)] = r
            self._x87_mark(ev, cx, [0], [0])
            return None
        if op in ("fcom", "fcomi"):
            if op == "fcomi":
                a_i, b_i = insn.operands[0].index, insn.operands[1].index
                if a_i != 0:
                    a_i, b_i = b_i, a_i
            elif spec.get("mem"):
                a_i, b_i = 0, None
            else:
                a_i = 0
                b_i = insn.operands[0].index if insn.operands else 1
            a = cx.fget(a_i, insn)
            if b_i is None:
                n = spec["mem_size"]
                raw, _ = self.mload(cx, insn.operands[0], n, trace_mem)
                b = fp.convert(raw, fp.F32 if n == 4 else fp.F64, fp.F80)[0]
            else:
                b = cx.fget(b_i, insn)
            c = fp.fcompare(a, b, fp.F80)
            if c == "unordered":
                cc = (1, 1, 1)
            elif c == "lt":
                cc = (1, 0, 0)
            elif c == "eq":
                cc = (0, 0, 1)
            else:
                cc = (0, 0, 0)
            if op == "fcom":
                cx.fcc["C0"], cx.fcc["C2"], cx.fcc["C3"] = cc
                cx.fcc["C1"] = 0
            else:
                cx.flags["CF"], cx.flags["PF"], cx.flags["ZF"] = cc
                cx.flags["OF"] = cx.flags["SF"] = 0
            self._x87_mark(ev, cx, [a_i] + ([b_i] if b_i is not None else []), [])
            pops = spec.get("pop")
            if pops:
                cx.fpop(insn)
                if pops == 2:
                    cx.fpop(insn)
            return None
        if op == "fxam":
            v = cx.fst[cx.fphys(0)]
            if v is None:
                c3, c2, c0, c1 = 1, 0, 1, 0
            else:
                c1 = 1 if v & fp.F80.sign_bit else 0
                kind = fp.classify(v, fp.F80)[0]
                if kind == fp.ZERO:
                    c3, c2, c0 = 1, 0, 0
                elif kind == fp.INF:
                    c3, c2, c0 = 0, 1, 1
                elif kind == fp.NAN:
                    c3, c2, c0 = 0, 0, 1
                elif ((v >> fp.F80.mant) & fp.F80.exp_mask) == 0:
                    c3, c2, c0 = 1, 1, 0
                else:
                    c3, c2, c0 = 0, 1, 0
            cx.fcc["C0"], cx.fcc["C1"], cx.fcc["C2"], cx.fcc["C3"] = c0, c1, c2, c3
            self._x87_mark(ev, cx, [0] if v is not None else [], [])
            return None
        if op == "ftst":
            a = cx.fget(0, insn)
            c = fp.fcompare(a, 0, fp.F80)
            cc = {"unordered": (1, 1, 1), "lt": (1, 0, 0), "eq": (0, 0, 1)}.get(c, (0, 0, 0))
            cx.fcc["C0"], cx.fcc["C2"], cx.fcc["C3"] = cc
            cx.fcc["C1"] = 0
            self._x87_mark(ev, cx, [0], [])
            return None
        if op == "frndint":
            v = cx.fget(0, insn)
            kind = fp.classify(v, fp.F80)[0]
            if kind == fp.NUM:
                q, err = fp.float_to_int(v, fp.F80, pol, signed=True, width=20000)
                r = fp.round_exact(Fraction(q), fp.F80, pol)[0]
                if q == 0 and (v & fp.F80.sign_bit):
                    r |= fp.F80.sign_bit
                cx.fst[cx.fphys(0)] = r
            self._x87_mark(ev, cx, [0], [0])
            return None
        if op == "fnstsw":
            sw = (cx.fcc["C0"] << 8) | (cx.fcc["C1"] << 9) | (cx.fcc["C2"] << 10) | (cx.ftop << 11) | (cx.fcc["C3"] << 14)
            (dst,) = insn.operands
            if isinstance(dst, Mem):
                self.mstore(cx, dst, sw, 2, trace_mem)
            else:
                self.rset(cx, dst, sw, 16)
            ev.xreads, ev.xwrites = set(), set()
            return None
        if op == "fnstcw":
            (dst,) = insn.operands
            self.mstore(cx, dst, cx.fcw, 2, trace_mem)
            ev.xreads, ev.xwrites = set(), set()
            return None
        if op == "fldcw":
            (src,) = insn.operands
            raw, _ = self.mload(cx, src, 2, trace_mem)
            cx.fcw = raw & 0xFFFF
            ev.xreads, ev.xwrites = set(), set()
            return None
        if op == "nop":
            ev.xreads, ev.xwrites = set(), set()
            return None
        raise Unsupported("x87 operation %r not implemented" % op)


# --- expected-output check ------------------------------------------------------------------------

def _compare_lanes(got, want_spec, what, nan_compare, mism):
    if "f32" in want_spec:
        want = [_f32_bits(v, what) for v in want_spec["f32"]]
        for i, (g, w) in enumerate(zip(got, want)):
            if g == w:
                continue
            if nan_compare == "any_nan" and fp.is_nan(g, fp.F32) and fp.is_nan(w, fp.F32):
                continue
            mism.append({"where": "%s[%d]" % (what, i), "got": "0x%08x (%s)" % (g, fp.fmt_bits(g, fp.F32)), "want": "0x%08x (%s)" % (w, fp.fmt_bits(w, fp.F32))})
        if len(want) != len(got):
            mism.append({"where": what, "got": "%d lanes" % len(got), "want": "%d lanes" % len(want)})
    elif "f64" in want_spec:
        want = [_f64_bits(v, what) for v in want_spec["f64"]]
        got64 = u32s_to_u64s(got) if len(got) == 16 else got
        for i, (g, w) in enumerate(zip(got64, want)):
            if g == w:
                continue
            if nan_compare == "any_nan" and fp.is_nan(g, fp.F64) and fp.is_nan(w, fp.F64):
                continue
            mism.append({"where": "%s[%d]" % (what, i), "got": "0x%016x (%s)" % (g, fp.fmt_bits(g, fp.F64)), "want": "0x%016x (%s)" % (w, fp.fmt_bits(w, fp.F64))})
    elif "u32" in want_spec or "i32" in want_spec:
        key = "u32" if "u32" in want_spec else "i32"
        want = [mask32(parse_int(v, what)) for v in want_spec[key]]
        for i, (g, w) in enumerate(zip(got, want)):
            if g != w:
                mism.append({"where": "%s[%d]" % (what, i), "got": "0x%08x" % g, "want": "0x%08x" % w})
    elif "u64" in want_spec:
        want = [mask64(parse_int(v, what)) for v in want_spec["u64"]]
        got64 = u32s_to_u64s(got) if len(got) == 16 else got
        for i, (g, w) in enumerate(zip(got64, want)):
            if g != w:
                mism.append({"where": "%s[%d]" % (what, i), "got": "0x%016x" % g, "want": "0x%016x" % w})
    else:
        raise InvalidInput("%s: expected value needs f32/f64/u32/i32/u64" % what)


def check_expected(kernel, interp):
    """Returns {'status': 'ok'|'mismatch'|'not_specified', 'mismatches': [...], 'checked': n}."""
    mism = []
    checked = 0
    nanc = kernel.numerical_policy["nan_compare"]
    for stream in kernel.streams:
        cx = interp.contexts[stream.context]
        exp = dict(kernel.expected.get("registers", {}).get(str(stream.context), {}))
        exp.update(stream.expected.get("registers", {}))
        for name, want in exp.items():
            n = name.lower()
            what = "ctx%d.%s" % (stream.context, n)
            checked += 1
            if n in cx.gpr:
                w = mask64(parse_int(want, what))
                if cx.gpr[n] != w:
                    mism.append({"where": what, "got": "0x%x" % cx.gpr[n], "want": "0x%x" % w})
            elif n in cx.k:
                w = parse_int(want, what) & 0xFFFF
                if cx.k[n] != w:
                    mism.append({"where": what, "got": "0x%04x" % cx.k[n], "want": "0x%04x" % w})
            elif n in cx.zmm:
                if isinstance(want, dict) and any(k.endswith("_broadcast") for k in want):
                    lanes = zmm_from_spec(want, what)
                    if lanes != cx.zmm[n]:
                        mism.append({"where": what, "got": ["0x%08x" % l for l in cx.zmm[n]], "want": ["0x%08x" % l for l in lanes]})
                else:
                    _compare_lanes(cx.zmm[n], want, what, nanc, mism)
            elif n == "flags":
                for f, v in want.items():
                    if cx.flags.get(f.upper()) != (1 if v else 0):
                        mism.append({"where": what + "." + f.upper(), "got": cx.flags.get(f.upper()), "want": 1 if v else 0})
            elif n.startswith("st") and n[2:].isdigit():
                i = int(n[2:])
                if i >= cx.fdepth():
                    mism.append({"where": what, "got": "empty (depth %d)" % cx.fdepth(), "want": str(want)})
                    continue
                bits = cx.fst[cx.fphys(i)]
                if isinstance(want, dict) and "f80" in want:
                    w = parse_int(want["f80"], what)
                    if bits != w:
                        mism.append({"where": what, "got": "0x%020x" % bits, "want": "0x%020x" % w})
                else:
                    g64 = fp.convert(bits, fp.F80, fp.F64)[0]
                    w = _f64_bits(want["f64"] if isinstance(want, dict) else want, what)
                    if g64 != w and not (nanc == "any_nan" and fp.is_nan(g64, fp.F64) and fp.is_nan(w, fp.F64)):
                        mism.append({"where": what, "got": "0x%016x (%s, rounded from extended)" % (g64, fp.fmt_bits(g64, fp.F64)), "want": "0x%016x (%s)" % (w, fp.fmt_bits(w, fp.F64))})
            elif n == "x87_depth":
                if cx.fdepth() != int(want):
                    mism.append({"where": what, "got": cx.fdepth(), "want": int(want)})
            else:
                raise InvalidInput("%s: unknown register in expected" % what)
    for i, blk in enumerate(kernel.expected.get("memory", [])):
        addr = parse_int(blk["addr"], "expected.memory[%d].addr" % i)
        what = "mem[0x%x]" % addr
        checked += 1
        if "f32" in blk or "u32" in blk or "i32" in blk:
            n = len(blk.get("f32") or blk.get("u32") or blk.get("i32"))
            data = interp.memory.read(addr, 4 * n)
            got = list(struct.unpack("<%dI" % n, data))
            _compare_lanes(got, blk, what, nanc, mism)
        elif "f64" in blk or "u64" in blk:
            n = len(blk.get("f64") or blk.get("u64"))
            data = interp.memory.read(addr, 8 * n)
            got = list(struct.unpack("<%dQ" % n, data))
            _compare_lanes(got, blk, what, nanc, mism)
        elif "f16" in blk or "u16" in blk:
            want = encode_values(blk, what)
            got = interp.memory.read(addr, len(want))
            if got != want:
                mism.append({"where": what, "got": got.hex(), "want": want.hex()})
        elif "u8" in blk:
            want = bytes(parse_int(v, what) & 0xFF for v in blk["u8"])
            got = interp.memory.read(addr, len(want))
            if got != want:
                mism.append({"where": what, "got": got.hex(), "want": want.hex()})
        elif "hex" in blk or "file" in blk:
            if "file" in blk:
                want, _ = load_input_file(blk, kernel.dir, "expected.memory[%d]" % i)
            else:
                want = bytes.fromhex(blk["hex"])
            got = interp.memory.read(addr, len(want))
            if got != want:
                k = next(j for j in range(len(want)) if got[j] != want[j])
                mism.append({"where": "%s+%d" % (what, k), "got": got[k:k + 8].hex(), "want": want[k:k + 8].hex()})
        else:
            raise InvalidInput("%s: expected memory needs f32/f64/f16/u32/i32/u64/u16/u8/hex/file" % what)
    if checked == 0:
        return {"status": "not_specified", "mismatches": [], "checked": 0}
    return {"status": "ok" if not mism else "mismatch", "mismatches": mism, "checked": checked}


def run_functional(kernel, max_steps=None, deadline=None, pre_init=None):
    """pre_init(interp) may poke large initial memory images directly (validation harnesses)."""
    interp = Interpreter(kernel, max_steps=max_steps, deadline=deadline)
    if pre_init is not None:
        pre_init(interp)
    total = interp.run()
    check = check_expected(kernel, interp)
    return interp, total, check
