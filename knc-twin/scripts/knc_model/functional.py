"""Exact functional interpreter for the supported record subset.

Produces final architectural state per context, a dynamic trace (addresses, taken
branches, lines touched) for the timing engine, and an expected-output check.
Contexts run one after another; a kernel whose contexts communicate through memory
is rejected (sequential execution would not reproduce the interleaving).
"""
import struct
import time

from .errors import BudgetExhausted, InvalidInput, Unsupported
from .kernel import Imm, Label, Mem, Reg, GPR64
from .util import mask32, mask64, parse_int, to_signed
from . import fp

LINE = 64


class TraceEvent(object):
    __slots__ = ("ctx", "insn", "addr", "nbytes", "lines", "taken", "mask_bits", "seq", "pf_level")

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

    def to_dict(self):
        return {"ctx": self.ctx, "id": self.insn.id, "op": self.insn.op, "addr": self.addr, "nbytes": self.nbytes,
                "lines": list(self.lines), "taken": self.taken, "mask_bits": self.mask_bits}


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
                raise InvalidInput("read of uninitialized memory at 0x%x (set init.memory, or kernel.memory_default to allow zero-filled reads)" % addr)
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


def lines_of(addr, n):
    if n <= 0:
        return ()
    first = addr & ~(LINE - 1)
    last = (addr + n - 1) & ~(LINE - 1)
    return tuple(range(first, last + 1, LINE))


# --- value encoding helpers ---------------------------------------------------------

def _f32_bits(v, what):
    if isinstance(v, str):
        s = v.strip().lower()
        if s.startswith("0x"):
            return int(s, 16) & 0xFFFFFFFF
        if s in ("nan", "+nan"):
            return 0x7FC00000
        if s == "-nan":
            return 0xFFC00000
        if s in ("inf", "+inf"):
            return 0x7F800000
        if s == "-inf":
            return 0xFF800000
        if s == "-0.0":
            return 0x80000000
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
        if s in ("nan", "+nan"):
            return 0x7FF8000000000000
        if s == "-nan":
            return 0xFFF8000000000000
        if s in ("inf", "+inf"):
            return 0x7FF0000000000000
        if s == "-inf":
            return 0xFFF0000000000000
        if s == "-0.0":
            return 0x8000000000000000
        v = float(s)
    return fp.f64_bits_from_float(float(v))


def encode_values(spec, what):
    """{'f32': [...]} | {'u32': [...]} | {'i32': [...]} | {'u64': [...]} | {'f64': [...]} | {'u8': [...]} -> bytes."""
    if "f32" in spec:
        return b"".join(struct.pack("<I", _f32_bits(v, what)) for v in spec["f32"])
    if "f64" in spec:
        return b"".join(struct.pack("<Q", _f64_bits(v, what)) for v in spec["f64"])
    if "u32" in spec:
        return b"".join(struct.pack("<I", mask32(parse_int(v, what))) for v in spec["u32"])
    if "i32" in spec:
        return b"".join(struct.pack("<i", to_signed(parse_int(v, what), 32)) for v in spec["i32"])
    if "u64" in spec:
        return b"".join(struct.pack("<Q", mask64(parse_int(v, what))) for v in spec["u64"])
    if "u8" in spec:
        return bytes(parse_int(v, what) & 0xFF for v in spec["u8"])
    raise InvalidInput("%s: need one of f32, f64, u32, i32, u64, u8" % what)


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
        else:
            data = encode_values(spec, what)
    else:
        raise InvalidInput("%s: zmm value must be an object or hex string" % what)
    if len(data) != 64:
        raise InvalidInput("%s: zmm value must be exactly 64 bytes (got %d)" % (what, len(data)))
    return list(struct.unpack("<16I", data))


# --- machine state -------------------------------------------------------------------------

class Context(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.gpr = {r: 0 for r in GPR64}
        self.zmm = {"zmm%d" % i: [0] * 16 for i in range(32)}
        self.k = {"k%d" % i: 0 for i in range(8)}
        self.k["k0"] = 0xFFFF  # k0 means 'all lanes' when used as a write mask
        self.flags = {"ZF": 0, "SF": 0, "CF": 0, "OF": 0}
        self.pc = 0

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
            else:
                raise InvalidInput("%s: unknown register %r" % (what, name))

    def snapshot(self):
        return {"gpr": {r: "0x%x" % v for r, v in sorted(self.gpr.items()) if v},
                "k": {r: "0x%x" % v for r, v in sorted(self.k.items())},
                "zmm": {r: ["0x%08x" % l for l in lanes] for r, lanes in sorted(self.zmm.items()) if any(lanes)},
                "flags": dict(self.flags)}


def u32s_to_u64s(lanes):
    return [lanes[2 * i] | (lanes[2 * i + 1] << 32) for i in range(8)]


def u64s_to_u32s(lanes):
    out = []
    for v in lanes:
        out.append(v & 0xFFFFFFFF)
        out.append((v >> 32) & 0xFFFFFFFF)
    return out


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
        pol = kernel.numerical_policy
        self.base_policy = fp.Policy(pol["rounding"], bool(pol.get("ftz")), bool(pol.get("daz")), pol.get("ftz_rule", "tiny"))
        for i, blk in enumerate(kernel.init.get("memory", [])):
            if "addr" not in blk:
                raise InvalidInput("init.memory[%d] needs addr" % i)
            addr = parse_int(blk["addr"], "init.memory[%d].addr" % i)
            if "fill" in blk:
                f = blk["fill"]
                unit = encode_values({k: [f[k]] for k in f if k in ("f32", "f64", "u32", "i32", "u64", "u8")}, "init.memory[%d].fill" % i)
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
            cx = Context(stream.context)
            cx.apply_init(self.kernel.init.get("registers", {}), "init.registers")
            cx.apply_init(stream.init.get("registers", {}), "streams[%d].init.registers" % stream.context)
            self.contexts[stream.context] = cx
            trace = []
            self.traces[stream.context] = trace
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
            total += steps
        # inter-context communication through memory invalidates sequential execution
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
        return mask64(a)

    def gval(self, cx, opnd, width):
        if isinstance(opnd, Reg):
            v = cx.gpr[opnd.base]
            return v & ((1 << width) - 1)
        if isinstance(opnd, Imm):
            return opnd.value & ((1 << width) - 1)
        raise InvalidInput("unexpected operand %r" % (opnd,))

    def gset(self, cx, reg, value, width):
        # 32-bit writes zero-extend; 64-bit writes replace
        cx.gpr[reg.base] = value & ((1 << width) - 1)

    def vsrc(self, cx, opnd, insn, trace_mem):
        """Vector source as 16 u32 lanes; memory sources are loaded (and recorded)."""
        if isinstance(opnd, Reg):
            return list(cx.zmm[opnd.base])
        if isinstance(opnd, Mem):
            addr = self.ea(cx, opnd)
            if opnd.broadcast == "1to16":
                data = self.memory.read(addr, 4, cx.ctx)
                trace_mem.append((addr, 4))
                return list(struct.unpack("<I", data)) * 16
            if opnd.broadcast == "1to8":
                data = self.memory.read(addr, 8, cx.ctx)
                trace_mem.append((addr, 8))
                return u64s_to_u32s(list(struct.unpack("<Q", data)) * 8)
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
            ev.lines = lines_of(addr, n)
        trace.append(ev)
        return cx.pc + 1 if nxt is None else nxt

    # --- scalar -------------------------------------------------------------------------------
    def _set_flags_arith(self, cx, a, b, r, width, op):
        msb = 1 << (width - 1)
        cx.flags["ZF"] = 1 if r == 0 else 0
        cx.flags["SF"] = 1 if r & msb else 0
        if op == "add":
            cx.flags["CF"] = 1 if a + b >= (1 << width) else 0
            cx.flags["OF"] = 1 if ((a ^ r) & (b ^ r) & msb) else 0
        else:
            cx.flags["CF"] = 1 if a < b else 0
            cx.flags["OF"] = 1 if ((a ^ b) & (a ^ r) & msb) else 0

    def _set_flags_logic(self, cx, r, width):
        cx.flags["ZF"] = 1 if r == 0 else 0
        cx.flags["SF"] = 1 if r & (1 << (width - 1)) else 0
        cx.flags["CF"] = 0
        cx.flags["OF"] = 0

    def _scalar_dst_src(self, cx, insn, trace_mem):
        w = insn.width
        dst, src = insn.operands
        if isinstance(dst, Mem):
            raise Unsupported("instruction %s: memory destination for %s not supported" % (insn.id, insn.op))
        if isinstance(src, Mem):
            addr = self.ea(cx, src)
            data = self.memory.read(addr, w // 8, cx.ctx)
            trace_mem.append((addr, w // 8))
            b = int.from_bytes(data, "little")
        else:
            b = self.gval(cx, src, w)
        return dst, self.gval(cx, dst, w), b, w

    def h_alu2(self, cx, insn, ev, trace_mem, stream):
        dst, a, b, w = self._scalar_dst_src(cx, insn, trace_mem)
        m = (1 << w) - 1
        if insn.op == "add":
            r = (a + b) & m
            self._set_flags_arith(cx, a, b, r, w, "add")
        elif insn.op == "sub":
            r = (a - b) & m
            self._set_flags_arith(cx, a, b, r, w, "sub")
        else:
            r = {"and": a & b, "or": a | b, "xor": a ^ b}[insn.op] & m
            self._set_flags_logic(cx, r, w)
        self.gset(cx, dst, r, w)

    def h_cmp(self, cx, insn, ev, trace_mem, stream):
        w = insn.width
        a_op, b_op = insn.operands
        if isinstance(a_op, Mem):
            addr = self.ea(cx, a_op)
            a = int.from_bytes(self.memory.read(addr, w // 8, cx.ctx), "little")
            trace_mem.append((addr, w // 8))
        else:
            a = self.gval(cx, a_op, w)
        if isinstance(b_op, Mem):
            addr = self.ea(cx, b_op)
            b = int.from_bytes(self.memory.read(addr, w // 8, cx.ctx), "little")
            trace_mem.append((addr, w // 8))
        else:
            b = self.gval(cx, b_op, w)
        r = (a - b) & ((1 << w) - 1)
        self._set_flags_arith(cx, a, b, r, w, "sub")

    def h_test(self, cx, insn, ev, trace_mem, stream):
        w = insn.width
        a_op, b_op = insn.operands
        if isinstance(a_op, Mem):
            addr = self.ea(cx, a_op)
            a = int.from_bytes(self.memory.read(addr, w // 8, cx.ctx), "little")
            trace_mem.append((addr, w // 8))
        else:
            a = self.gval(cx, a_op, w)
        b = self.gval(cx, b_op, w)
        self._set_flags_logic(cx, a & b, w)

    def h_mov(self, cx, insn, ev, trace_mem, stream):
        w = insn.width
        dst, src = insn.operands
        if isinstance(src, Mem):
            addr = self.ea(cx, src)
            data = self.memory.read(addr, w // 8, cx.ctx)
            trace_mem.append((addr, w // 8))
            v = int.from_bytes(data, "little")
        else:
            v = self.gval(cx, src, w)
        if isinstance(dst, Mem):
            addr = self.ea(cx, dst)
            self.memory.write(addr, (v & ((1 << w) - 1)).to_bytes(w // 8, "little"), cx.ctx)
            trace_mem.append((addr, w // 8))
        else:
            self.gset(cx, dst, v, w)

    def h_lea(self, cx, insn, ev, trace_mem, stream):
        dst, mem = insn.operands
        self.gset(cx, dst, self.ea(cx, mem), insn.width)

    def h_incdec(self, cx, insn, ev, trace_mem, stream):
        (dst,) = insn.operands
        w = insn.width
        if isinstance(dst, Mem):
            raise Unsupported("instruction %s: memory form not supported" % insn.id)
        a = self.gval(cx, dst, w)
        cf = cx.flags["CF"]
        if insn.op == "inc":
            r = (a + 1) & ((1 << w) - 1)
            self._set_flags_arith(cx, a, 1, r, w, "add")
        else:
            r = (a - 1) & ((1 << w) - 1)
            self._set_flags_arith(cx, a, 1, r, w, "sub")
        cx.flags["CF"] = cf
        self.gset(cx, dst, r, w)

    def h_neg(self, cx, insn, ev, trace_mem, stream):
        (dst,) = insn.operands
        w = insn.width
        a = self.gval(cx, dst, w)
        r = (-a) & ((1 << w) - 1)
        self._set_flags_arith(cx, 0, a, r, w, "sub")
        cx.flags["CF"] = 1 if a != 0 else 0
        self.gset(cx, dst, r, w)

    def h_not(self, cx, insn, ev, trace_mem, stream):
        (dst,) = insn.operands
        w = insn.width
        self.gset(cx, dst, (~self.gval(cx, dst, w)) & ((1 << w) - 1), w)

    def h_shift(self, cx, insn, ev, trace_mem, stream):
        dst, cnt = insn.operands
        w = insn.width
        if isinstance(dst, Mem):
            raise Unsupported("instruction %s: memory form not supported" % insn.id)
        c = cnt.value & (63 if w == 64 else 31)
        a = self.gval(cx, dst, w)
        if c == 0:
            return None
        m = (1 << w) - 1
        if insn.op == "shl":
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
        if c > 1:
            self.assume("OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged")
        self.gset(cx, dst, r, w)

    def h_imul(self, cx, insn, ev, trace_mem, stream):
        dst, a, b, w = self._scalar_dst_src(cx, insn, trace_mem)
        full = to_signed(a, w) * to_signed(b, w)
        r = full & ((1 << w) - 1)
        ovf = 0 if to_signed(r, w) == full else 1
        cx.flags["CF"] = ovf
        cx.flags["OF"] = ovf
        self.assume("ZF/SF after imul are architecturally undefined; the model leaves them unchanged")
        self.gset(cx, dst, r, w)

    # --- branches -----------------------------------------------------------------------------
    def _branch(self, cx, insn, ev, stream, taken):
        ev.taken = bool(taken)
        if taken:
            return stream.labels[insn.target]
        return None

    def h_jmp(self, cx, insn, ev, trace_mem, stream):
        return self._branch(cx, insn, ev, stream, True)

    def h_jcc(self, cx, insn, ev, trace_mem, stream):
        f = cx.flags
        cond = insn.spec["cond"]
        taken = {"zf": f["ZF"], "nzf": not f["ZF"], "lt": f["SF"] != f["OF"], "ge": f["SF"] == f["OF"],
                 "gt": (not f["ZF"]) and f["SF"] == f["OF"], "le": f["ZF"] or f["SF"] != f["OF"],
                 "cf": f["CF"], "ncf": not f["CF"], "sf": f["SF"], "nsf": not f["SF"]}[cond]
        return self._branch(cx, insn, ev, stream, taken)

    def h_jk(self, cx, insn, ev, trace_mem, stream):
        kreg = insn.operands[0]
        v = cx.k[kreg.base]
        taken = (v == 0) if insn.spec["cond"] == "kz" else (v != 0)
        return self._branch(cx, insn, ev, stream, taken)

    # --- mask ---------------------------------------------------------------------------------
    def h_kmov(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        v = cx.k[src.base] if src.kind == "k" else (cx.gpr[src.base] & 0xFFFF)
        if dst.kind == "k":
            cx.k[dst.base] = v
        else:
            cx.gpr[dst.base] = v

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

    def h_vfp2(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2 = insn.operands
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        a = self.vsrc(cx, s1, insn, trace_mem)
        b = self.vsrc(cx, s2, insn, trace_mem)
        kbits = self.kmask(cx, insn)
        opk = insn.spec["opk"]
        if fmt is fp.F32:
            out = []
            for i in range(16):
                if opk == "add":
                    r, _ = fp.fadd(a[i], b[i], fmt, pol)
                elif opk == "sub":
                    r, _ = fp.fsub(a[i], b[i], fmt, pol)
                else:
                    r, _ = fp.fmul(a[i], b[i], fmt, pol)
                out.append(r)
            self.merge32(cx, dst, out, kbits)
        else:
            a64, b64 = u32s_to_u64s(a), u32s_to_u64s(b)
            out = []
            for i in range(8):
                if opk == "add":
                    r, _ = fp.fadd(a64[i], b64[i], fmt, pol)
                elif opk == "sub":
                    r, _ = fp.fsub(a64[i], b64[i], fmt, pol)
                else:
                    r, _ = fp.fmul(a64[i], b64[i], fmt, pol)
                out.append(r)
            self.merge64(cx, dst, out, kbits & 0xFF)
        ev.mask_bits = kbits

    def h_vfma(self, cx, insn, ev, trace_mem, stream):
        o1, o2, o3 = insn.operands
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        v1 = list(cx.zmm[o1.base])
        v2 = self.vsrc(cx, o2, insn, trace_mem)
        v3 = self.vsrc(cx, o3, insn, trace_mem)
        form = insn.spec["form"]
        negp, negc = insn.spec["negp"], insn.spec["negc"]
        kbits = self.kmask(cx, insn)

        def pick(i, a, b, c):
            if form == "132":
                return a[i], c[i], b[i]   # op1*op3 + op2
            if form == "213":
                return b[i], a[i], c[i]   # op2*op1 + op3
            return b[i], c[i], a[i]       # 231: op2*op3 + op1
        if fmt is fp.F32:
            out = []
            for i in range(16):
                x, y, z = pick(i, v1, v2, v3)
                r, _ = fp.ffma(x, y, z, fmt, pol, negate_product=negp, negate_c=negc)
                out.append(r)
            self.merge32(cx, o1, out, kbits)
        else:
            a64, b64, c64 = u32s_to_u64s(v1), u32s_to_u64s(v2), u32s_to_u64s(v3)
            out = []
            for i in range(8):
                x, y, z = pick(i, a64, b64, c64)
                r, _ = fp.ffma(x, y, z, fmt, pol, negate_product=negp, negate_c=negc)
                out.append(r)
            self.merge64(cx, o1, out, kbits & 0xFF)
        ev.mask_bits = kbits

    def h_vcmp(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2, imm = insn.operands
        fmt = self._fmt(insn)
        pol = self.policy_for(insn)
        a = self.vsrc(cx, s1, insn, trace_mem)
        b = self.vsrc(cx, s2, insn, trace_mem)
        pred = imm.value & 7
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
                   5: c not in ("lt",), 6: c not in ("lt", "eq"), 7: c != "unordered"}[pred]
            if hit:
                res |= 1 << i
        cx.k[dst.base] = res
        ev.mask_bits = kbits

    def _cvt_rounding(self, insn, imm):
        if imm.value >> 2:
            raise Unsupported("instruction %s: conversion immediate 0x%x uses exponent-adjust bits; only the rounding field (bits 1:0) is supported" % (insn.id, imm.value))
        return ("rn", "rd", "ru", "rz")[imm.value & 3]

    def h_vcvt_i2f(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        pol = self.policy_for(insn, self._cvt_rounding(insn, imm))
        a = self.vsrc(cx, src, insn, trace_mem)
        out = [fp.int_to_float(to_signed(a[i], 32), fp.F32, pol)[0] for i in range(16)]
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vcvt_u2f(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        pol = self.policy_for(insn, self._cvt_rounding(insn, imm))
        a = self.vsrc(cx, src, insn, trace_mem)
        out = [fp.int_to_float(a[i], fp.F32, pol)[0] for i in range(16)]
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vcvt_f2i(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        pol = self.policy_for(insn, self._cvt_rounding(insn, imm))
        a = self.vsrc(cx, src, insn, trace_mem)
        signed = insn.spec["signed"]
        out = []
        for i in range(16):
            q, err = fp.float_to_int(a[i], fp.F32, pol, signed=signed, width=32)
            if err:
                self.assume("out-of-range or NaN float-to-int conversion produced the x86 integer indefinite (0x80000000 signed, 0xFFFFFFFF unsigned); KNC-specific value not verified")
                q = 0x80000000 if signed else 0xFFFFFFFF
            out.append(q & 0xFFFFFFFF)
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    # --- vector int --------------------------------------------------------------------------------
    def h_vint2(self, cx, insn, ev, trace_mem, stream):
        dst, s1, s2 = insn.operands
        a = self.vsrc(cx, s1, insn, trace_mem)
        b = self.vsrc(cx, s2, insn, trace_mem)
        opk = insn.spec["opk"]
        out = []
        for i in range(16):
            x, y = a[i], b[i]
            if opk == "add":
                r = x + y
            elif opk == "sub":
                r = x - y
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
            elif opk == "mins":
                r = min(to_signed(x, 32), to_signed(y, 32))
            elif opk == "maxs":
                r = max(to_signed(x, 32), to_signed(y, 32))
            elif opk == "minu":
                r = min(x, y)
            elif opk == "maxu":
                r = max(x, y)
            elif opk == "shlv":
                r = x << (y & 31) if y < 32 else 0
            elif opk == "shrv":
                r = x >> (y & 31) if y < 32 else 0
            elif opk == "sarv":
                r = to_signed(x, 32) >> min(y, 31)
            out.append(r & 0xFFFFFFFF)
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vshift_imm(self, cx, insn, ev, trace_mem, stream):
        dst, src, imm = insn.operands
        a = self.vsrc(cx, src, insn, trace_mem)
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
        a = self.vsrc(cx, s1, insn, trace_mem)
        b = self.vsrc(cx, s2, insn, trace_mem)
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
        s = self.vsrc(cx, src, insn, trace_mem)
        out = [s[ix[i] & 15] for i in range(16)]
        self.merge32(cx, dst, out, self.kmask(cx, insn))

    def h_vbroadcast(self, cx, insn, ev, trace_mem, stream):
        dst, mem = insn.operands
        addr = self.ea(cx, mem)
        n = insn.spec["elem"]
        data = self.memory.read(addr, n, cx.ctx)
        trace_mem.append((addr, n))
        if n == 4:
            out = list(struct.unpack("<I", data)) * 16
            self.merge32(cx, dst, out, self.kmask(cx, insn))
        else:
            out = list(struct.unpack("<Q", data)) * 8
            self.merge64(cx, dst, out, self.kmask(cx, insn) & 0xFF)

    # --- vector memory -----------------------------------------------------------------------------
    def h_vmov(self, cx, insn, ev, trace_mem, stream):
        dst, src = insn.operands
        kbits = self.kmask(cx, insn)
        ev.mask_bits = kbits
        wide64 = insn.op in ("vmovapd", "vmovdqa64")
        if isinstance(dst, Mem):
            addr = self.ea(cx, dst)
            if addr % 64:
                raise InvalidInput("instruction %s: vector store at 0x%x is not 64-byte aligned (faults on KNC)" % (insn.id, addr))
            lanes = cx.zmm[src.base]
            data = struct.pack("<16I", *lanes)
            if wide64:
                for i in range(8):
                    if (kbits >> i) & 1:
                        self.memory.write(addr + 8 * i, data[8 * i:8 * i + 8], cx.ctx)
            else:
                for i in range(16):
                    if (kbits >> i) & 1:
                        self.memory.write(addr + 4 * i, data[4 * i:4 * i + 4], cx.ctx)
            trace_mem.append((addr, 64))
        else:
            v = self.vsrc(cx, src, insn, trace_mem)
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

    def h_vgather(self, cx, insn, ev, trace_mem, stream):
        dst, mem = insn.operands
        if mem.vindex is None:
            raise InvalidInput("instruction %s: gather needs a vindex register" % insn.id)
        if insn.mask is None:
            raise InvalidInput("instruction %s: gather needs a write mask (completion mask)" % insn.id)
        idx = cx.zmm[mem.vindex.base]
        kbits = cx.k[insn.mask.base]
        old = cx.zmm[dst.base]
        out = list(old)
        lines = set()
        first = None
        for i in range(16):
            if not (kbits >> i) & 1:
                continue
            a = mask64(mem.disp + (cx.gpr[mem.base.base] if mem.base else 0) + to_signed(idx[i], 32) * mem.scale)
            data = self.memory.read(a, 4, cx.ctx)
            out[i] = struct.unpack("<I", data)[0]
            lines.update(lines_of(a, 4))
            if first is None:
                first = a
        cx.zmm[dst.base] = out
        cx.k[insn.mask.base] = 0  # completed in one shot: all requested lanes gathered
        ev.addr = first
        ev.nbytes = 4 * bin(kbits).count("1")
        ev.lines = tuple(sorted(lines))
        ev.mask_bits = kbits

    def h_prefetch(self, cx, insn, ev, trace_mem, stream):
        (mem,) = insn.operands
        addr = self.ea(cx, mem)
        ev.addr = addr
        ev.nbytes = 64
        ev.lines = lines_of(addr & ~63, 64)
        ev.pf_level = insn.spec["level"]


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
        elif "u8" in blk:
            want = bytes(parse_int(v, what) & 0xFF for v in blk["u8"])
            got = interp.memory.read(addr, len(want))
            if got != want:
                mism.append({"where": what, "got": got.hex(), "want": want.hex()})
        else:
            raise InvalidInput("%s: expected memory needs f32/f64/u32/i32/u64/u8" % what)
    if checked == 0:
        return {"status": "not_specified", "mismatches": [], "checked": 0}
    return {"status": "ok" if not mism else "mismatch", "mismatches": mism, "checked": checked}


def run_functional(kernel, max_steps=None, deadline=None):
    interp = Interpreter(kernel, max_steps=max_steps, deadline=deadline)
    total = interp.run()
    check = check_expected(kernel, interp)
    return interp, total, check
