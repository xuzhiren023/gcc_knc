"""Kernel input: normalized instruction records (and the GAS AT&T subset via asm.py).

The evaluated representation is a list of instruction records per hardware context.
Records are not machine encodings: this validates operand forms against the ISA
table, derives register/flag/mask/memory dependencies, and rejects anything the
table does not list. It does not validate instruction encodings, loading, or the ABI.
"""
import os

from . import KERNEL_SCHEMA
from .errors import InvalidInput, Unsupported
from .util import load_json, parse_int
from . import isa

GPR64 = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp"] + ["r%d" % i for i in range(8, 16)]
GPR32 = ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"] + ["r%dd" % i for i in range(8, 16)]
GPR16 = ["ax", "bx", "cx", "dx", "si", "di", "bp", "sp"] + ["r%dw" % i for i in range(8, 16)]
GPR8 = ["al", "bl", "cl", "dl", "sil", "dil", "bpl", "spl"] + ["r%db" % i for i in range(8, 16)]
GPR8H = {"ah": "rax", "bh": "rbx", "ch": "rcx", "dh": "rdx"}
_TO64 = {}
for _lst in (GPR32, GPR16, GPR8):
    _TO64.update(dict(zip(_lst, GPR64)))
ZMM = ["zmm%d" % i for i in range(32)]
KREG = ["k%d" % i for i in range(8)]
VALID_ROUNDING = ("rn", "rd", "ru", "rz")
MEMORY_LEVELS = ("l1", "l2", "memory")


class Reg(object):
    __slots__ = ("name", "kind", "base", "width", "high", "index", "swizzle", "conv")

    def __init__(self, name, swizzle=None, conv=None):
        n = name.lower()
        self.high = False
        self.index = None
        self.swizzle = swizzle
        self.conv = conv
        if n in GPR64:
            self.kind, self.base, self.width = "g", n, 64
        elif n in GPR32:
            self.kind, self.base, self.width = "g", _TO64[n], 32
        elif n in GPR16:
            self.kind, self.base, self.width = "g", _TO64[n], 16
        elif n in GPR8:
            self.kind, self.base, self.width = "g", _TO64[n], 8
        elif n in GPR8H:
            self.kind, self.base, self.width, self.high = "g", GPR8H[n], 8, True
        elif n in ZMM:
            self.kind, self.base, self.width = "v", n, 512
        elif n in KREG:
            self.kind, self.base, self.width = "k", n, 16
        elif n == "st" or n == "st(0)":
            self.kind, self.base, self.width, self.index = "x", "x87", 80, 0
        elif n.startswith("st(") and n.endswith(")") and n[3:-1].isdigit() and int(n[3:-1]) < 8:
            self.kind, self.base, self.width, self.index = "x", "x87", 80, int(n[3:-1])
        else:
            raise InvalidInput("unknown register %r" % name)
        if swizzle is not None:
            if self.kind != "v":
                raise InvalidInput("swizzle on a non-vector register %r" % name)
            if swizzle not in isa.SWIZZLES:
                raise Unsupported("swizzle {%s} is not supported (%s)" % (swizzle, ", ".join(isa.SWIZZLES)))
        if conv is not None and self.kind != "v":
            raise InvalidInput("conversion modifier on a non-vector register %r" % name)
        self.name = n

    def __repr__(self):
        s = self.name
        if self.swizzle:
            s += "{%s}" % self.swizzle
        if self.conv:
            s += "{%s}" % self.conv
        return s


class Mem(object):
    __slots__ = ("base", "index", "scale", "disp", "broadcast", "conv", "size", "vindex", "symbol", "segment", "absolute")

    def __init__(self, d, what):
        if not isinstance(d, dict):
            raise InvalidInput("%s: memory operand must be an object" % what)
        allowed = {"base", "index", "scale", "disp", "broadcast", "conv", "size", "mem", "vindex", "symbol", "segment", "abs"}
        extra = set(d) - allowed
        if extra:
            raise InvalidInput("%s: unknown memory operand keys %s" % (what, sorted(extra)))
        self.base = Reg(d["base"]) if d.get("base") else None
        self.index = Reg(d["index"]) if d.get("index") else None
        self.vindex = Reg(d["vindex"]) if d.get("vindex") else None
        self.scale = parse_int(d.get("scale", 1), what + ".scale")
        self.disp = parse_int(d.get("disp", 0), what + ".disp")
        self.broadcast = d.get("broadcast")
        self.conv = d.get("conv")
        self.symbol = d.get("symbol")
        self.size = d.get("size")
        self.segment = d.get("segment")
        self.absolute = bool(d.get("abs"))
        if self.segment is not None and self.segment not in ("fs", "gs"):
            raise Unsupported("%s: segment %r not supported (fs and gs only: thread-local access)" % (what, self.segment))
        if self.scale not in (1, 2, 4, 8):
            raise InvalidInput("%s: scale must be 1, 2, 4 or 8" % what)
        if self.base is not None and self.base.kind != "g":
            raise InvalidInput("%s: base must be a general register" % what)
        if self.index is not None and self.index.kind != "g":
            raise InvalidInput("%s: index must be a general register" % what)
        if self.vindex is not None and self.vindex.kind != "v":
            raise InvalidInput("%s: vindex must be a zmm register" % what)
        if self.broadcast is not None and self.broadcast not in isa.BROADCASTS:
            raise Unsupported("%s: broadcast %r not supported (%s)" % (what, self.broadcast, ", ".join(isa.BROADCASTS)))
        if self.conv is not None and self.conv not in isa.UPCONV_PS:
            raise Unsupported("%s: conversion %r not supported (%s)" % (what, self.conv, ", ".join(isa.UPCONV_PS)))
        if self.base is None and self.index is None and self.vindex is None and self.symbol is None and not self.absolute and self.segment is None:
            raise InvalidInput("%s: memory operand needs a base, index, vindex register or a symbol" % what)

    def regs(self):
        out = []
        for r in (self.base, self.index, self.vindex):
            if r is not None:
                out.append(r)
        return out

    def __repr__(self):
        parts = []
        if self.segment:
            parts.append("%" + self.segment + ":")
        if self.symbol:
            parts.append(self.symbol)
        if self.base:
            parts.append(self.base.name)
        if self.index:
            parts.append("%s*%d" % (self.index.name, self.scale))
        if self.vindex:
            parts.append("%s*%d" % (self.vindex.name, self.scale))
        s = "[" + "+".join(parts)
        if self.disp:
            s += "%+d" % self.disp
        s += "]"
        if self.broadcast:
            s += "{%s}" % self.broadcast
        if self.conv:
            s += "{%s}" % self.conv
        return s


class Imm(object):
    __slots__ = ("value", "symbol")

    def __init__(self, v, symbol=None):
        self.value = v
        self.symbol = symbol

    def __repr__(self):
        return "$%d" % self.value


class Label(object):
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


def _is_reg_name(low):
    return (low in GPR64 or low in GPR32 or low in GPR16 or low in GPR8 or low in GPR8H or low in ZMM or low in KREG
            or low == "st" or (low.startswith("st(") and low.endswith(")")))


def _parse_operand(raw, role, what):
    kinds = role.split(":")[1] if ":" in role else role
    if isinstance(raw, dict):
        if "imm" in raw:
            if "i" not in kinds:
                raise InvalidInput("%s: immediate not allowed here" % what)
            return Imm(parse_int(raw["imm"], what), raw.get("imm_symbol"))
        if "reg" in raw:
            r = Reg(raw["reg"], swizzle=raw.get("swizzle"), conv=raw.get("conv"))
            _check_reg_kind(r, kinds, what, role)
            return r
        if "m" not in kinds:
            raise InvalidInput("%s: memory operand not allowed for role %r" % (what, role))
        return Mem(raw, what)
    if isinstance(raw, bool):
        raise InvalidInput("%s: boolean operand" % what)
    if isinstance(raw, int):
        if "i" not in kinds:
            raise InvalidInput("%s: immediate %d not allowed for role %r" % (what, raw, role))
        return Imm(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if role == "t":
            return Label(s)
        if s.startswith("$"):
            if "i" not in kinds:
                raise InvalidInput("%s: immediate not allowed for role %r" % (what, role))
            return Imm(parse_int(s[1:], what))
        low = s.lower()
        if _is_reg_name(low):
            r = Reg(low)
            _check_reg_kind(r, kinds, what, role)
            return r
        if "i" in kinds:
            try:
                return Imm(parse_int(s, what))
            except InvalidInput:
                pass
        raise InvalidInput("%s: cannot interpret operand %r" % (what, raw))
    raise InvalidInput("%s: bad operand %r" % (what, raw))


def _check_reg_kind(r, kinds, what, role):
    if r.kind not in kinds:
        names = {"g": "general", "v": "zmm", "k": "mask", "x": "x87"}
        raise InvalidInput("%s: %s register %s not allowed for role %r" % (what, names[r.kind], r.name, role))


class Insn(object):
    """One static instruction record with derived dependency sets."""

    def __init__(self, d, index, stream_id):
        if not isinstance(d, dict):
            raise InvalidInput("stream %s instruction %d: record must be an object" % (stream_id, index))
        allowed = {"id", "op", "ops", "mask", "rounding", "label", "encoding", "deps", "addr", "width", "comment", "x87_deps", "lines", "source", "sae"}
        extra = set(d) - allowed
        if extra:
            raise InvalidInput("stream %s instruction %d: unknown record keys %s" % (stream_id, index, sorted(extra)))
        self.index = index
        self.id = str(d.get("id", "s%s_i%d" % (stream_id, index)))
        op = d.get("op")
        if not isinstance(op, str) or not op:
            raise InvalidInput("instruction %s: missing 'op'" % self.id)
        self.op = op.lower()
        spec = isa.lookup(self.op)
        if spec is None:
            raise Unsupported("instruction %s: mnemonic %r is not in the supported subset; it gets no default cost" % (self.id, op),
                              {"mnemonic": op, "instruction": self.id})
        self.spec = spec
        self.cls = spec["class"]
        self.label = d.get("label")
        self.comment = d.get("comment", "")
        self.source = d.get("source")
        self.explicit_deps = list(d.get("deps", []))
        self.encoding = d.get("encoding") or {}
        self.width = d.get("width")
        self.lines_hint = d.get("lines")
        self.addr_desc = None
        if d.get("addr") is not None:
            a = d["addr"]
            if not isinstance(a, dict) or "start" not in a:
                raise InvalidInput("instruction %s: addr must be {start, stride?}" % self.id)
            self.addr_desc = {"start": parse_int(a["start"], self.id + ".addr.start"), "stride": parse_int(a.get("stride", 0), self.id + ".addr.stride")}
        self.rounding = d.get("rounding")
        self.sae = bool(d.get("sae", False))
        if self.rounding is not None and self.rounding not in VALID_ROUNDING:
            raise Unsupported("instruction %s: rounding %r not supported" % (self.id, self.rounding))
        self.mask = Reg(d["mask"]) if d.get("mask") else None
        if self.mask is not None and self.mask.kind != "k":
            raise InvalidInput("instruction %s: mask must be k0-k7" % self.id)
        raw_ops = d.get("ops", [])
        roles_alt = spec["ops"]
        if roles_alt and isinstance(roles_alt[0], list):
            matches = [r for r in roles_alt if len(r) == len(raw_ops)]
            if not matches:
                raise InvalidInput("instruction %s (%s): %d operands given; accepted arities: %s" % (self.id, self.op, len(raw_ops), sorted(set(len(r) for r in roles_alt))))
            roles = matches[0]
        else:
            roles = roles_alt
            if len(raw_ops) != len(roles):
                raise InvalidInput("instruction %s (%s): expected %d operands %s, got %d" % (self.id, self.op, len(roles), roles, len(raw_ops)))
        self.operands = [_parse_operand(r, role, "instruction %s operand %d" % (self.id, i)) for i, (r, role) in enumerate(zip(raw_ops, roles))]
        self.roles = roles
        self._derive()

    # ------------------------------------------------------------------
    def _derive(self):
        self.reads = set()
        self.writes = set()
        self.addr_regs = set()
        self.mem = None
        self.mem_role = None
        self.target = None
        self.imm = None
        self.has_swizzle = False
        self.has_conv = False
        for opnd, role in zip(self.operands, self.roles):
            acc = role.split(":")[0]
            if isinstance(opnd, Reg):
                if opnd.kind == "x":
                    self.reads.add("x87")
                    self.writes.add("x87")
                else:
                    if acc in ("r", "rw"):
                        self.reads.add(opnd.base)
                    if acc in ("w", "rw"):
                        self.writes.add(opnd.base)
                        if opnd.kind == "g" and opnd.width < 32:
                            self.reads.add(opnd.base)  # partial write keeps the upper bits
                if opnd.swizzle:
                    self.has_swizzle = True
                if opnd.conv:
                    self.has_conv = True
            elif isinstance(opnd, Mem):
                for r in opnd.regs():
                    self.addr_regs.add(r.base)
                    self.reads.add(r.base)
                if acc != "a":
                    if self.mem is not None:
                        raise InvalidInput("instruction %s: two memory operands" % self.id)
                    self.mem = opnd
                    self.mem_role = acc
                if opnd.conv or opnd.broadcast:
                    self.has_conv = True
            elif isinstance(opnd, Label):
                self.target = opnd.name
            elif isinstance(opnd, Imm):
                self.imm = opnd.value
        if self.spec.get("fn") == "x87":
            self.reads.add("x87")
            self.writes.add("x87")
            if self.spec.get("op") in ("fldcw", "fnstcw"):
                self.writes.add("fcw") if self.spec.get("op") == "fldcw" else self.reads.add("fcw")
            elif self.spec.get("op") in ("fistp", "fisttp", "fst", "fsqrt", "fadd", "fsub", "fsubr", "fmul", "fdiv", "fdivr", "add", "sub", "subr", "mul", "div", "divr"):
                self.reads.add("fcw")
        if self.op in ("cltq", "cltd", "cqto"):
            self.reads.add("rax")
            self.writes.add("rdx" if self.op != "cltq" else "rax")
        if self.op in ("idiv", "div"):
            self.reads.update(("rax", "rdx"))
            self.writes.update(("rax", "rdx"))
        if self.op == "imul" and len(self.operands) == 1:
            raise Unsupported("instruction %s: one-operand imul (rdx:rax) is not supported" % self.id)
        if self.op in ("push", "pop", "leave"):
            self.reads.add("rsp")
            self.writes.add("rsp")
            if self.op == "leave":
                self.reads.add("rbp")
                self.writes.add("rbp")
        if self.op in ("shl", "shr", "sar", "sal") and len(self.operands) == 2 and isinstance(self.operands[1], Reg):
            if self.operands[1].base != "rcx" or self.operands[1].width != 8:
                raise InvalidInput("instruction %s: variable shift count must be %%cl" % self.id)
        if self.mask is not None:
            self.reads.add(self.mask.base)
            if self.cls in ("vector_gather", "vector_scatter"):
                self.writes.add(self.mask.base)  # completion mask is cleared
        self.flags_r = bool(self.spec.get("flags_r"))
        self.flags_w = bool(self.spec.get("flags_w"))
        self.is_branch = self.cls in ("branch", "call", "ret")
        if self.op in ("call", "ret"):
            self.reads.add("rsp")
            self.writes.add("rsp")
            self.addr_regs.add("rsp")
        if self.op in ("xchg", "lock_xchg", "lock_xadd"):
            for o in self.operands:
                if isinstance(o, Reg):
                    self.reads.add(o.base)
                    self.writes.add(o.base)
        if self.op == "lock_cmpxchg":
            self.reads.add("rax")
            self.writes.add("rax")
        if self.op == "sahf":
            self.reads.add("rax")
        if self.is_branch and self.target is None and self.op != "ret":
            raise InvalidInput("instruction %s: branch needs a target label" % self.id)
        # memory forms and effective timing class
        self.is_load = False
        self.is_store = False
        self.folded_load = False
        if self.mem is not None and self.cls not in ("prefetch_l1", "prefetch_l2", "vector_gather", "vector_scatter", "fence"):
            if self.mem_role in ("w", "rw"):
                self.is_store = True
                if self.mem_role == "rw":
                    self.is_load = True
            else:
                self.is_load = True
        if self.op in ("push", "pop", "leave"):
            self.is_store = self.op == "push"
            self.is_load = self.op != "push"
        if self.op == "call":
            self.is_store = True
        if self.op == "ret":
            self.is_load = True
        if self.op.startswith("vloadunpack"):
            # the two halves merge in the load unit: the destination's old value is not waited for (S6-03 unpack.lat)
            self.reads.discard(self.operands[0].base)
        if self.op in ("mov", "movabs") and self.mem is not None:
            self.cls = "scalar_store" if self.is_store else "scalar_load"
        elif self.op in ("add", "sub", "and", "or", "xor", "adc", "sbb", "inc", "dec", "neg", "not", "shl", "shr", "sar", "sal") and self.mem is not None and self.mem_role == "rw":
            self.cls = "scalar_rmw"
        elif self.op in ("cmp", "test", "bt", "imul") and self.mem is not None:
            self.cls = "scalar_load"
        elif self.op.startswith(("movs", "movz")) and self.mem is not None:
            self.cls = "scalar_load"
        elif self.op in ("add", "sub", "and", "or", "xor", "adc", "sbb") and self.mem is not None:
            self.cls = "scalar_load"  # register destination with a memory source
        elif self.op.startswith("set") and self.mem is not None:
            self.cls = "scalar_store"
        elif self.op in ("vmovaps", "vmovapd", "vmovdqa32", "vmovdqa64"):
            if self.mem is None:
                self.cls = "vector_arith"
            elif self.is_store:
                self.cls = "vector_store"
            else:
                self.cls = "vector_load"
        elif self.cls == "vector_arith" and self.mem is not None:
            self.folded_load = True
        elif self.cls in ("vector_long", "vector_convert_df") and self.mem is not None:
            self.folded_load = True
        if self.cls == "vector_gather":
            self.is_load = True
            # the gathered lanes merge into the destination: a re-executed gather waits for the previous one's data
            self.reads.add(self.operands[0].base)
        if self.cls == "vector_scatter":
            self.is_store = True
        if self.cls == "x87_load" and self.mem is None:
            raise InvalidInput("instruction %s: memory operand required" % self.id)
        if self.spec.get("fn") == "x87" and self.spec.get("mem") and self.mem is not None:
            self.is_load = True
        if self.op == "stmxcsr":
            self.reads.add("mxcsr")
        # vector FP instructions OR their exception flags into MXCSR when they complete; this is a sticky side effect,
        # not a register dependency between them (only stmxcsr reads it)
        self.sets_mxcsr = bool(self.spec.get("fn") in ("vfp2", "vfma", "vscale", "vrcp23", "vrsqrt23", "vgetexp", "vgetmant", "vfixupnan", "vcvt_i2f", "vcvt_u2f",
                                                       "vcvt_f2i", "vcvt_d2i", "vcvt_s2d", "vcvt_d2s", "vrnd", "vgminmax") and not self.sae)
        if self.cls == "x87_control" and self.mem is not None:
            if self.spec.get("op") == "fldcw":
                self.is_load = True
            else:
                self.is_store = True
        if self.op == "fnstsw" and self.mem is None:
            self.writes.add("rax")
        self.pipes = isa.CLASSES[self.cls]["pipes"]
        self.kind = isa.CLASSES[self.cls]["kind"]
        # scalar operand width
        if self.width is None:
            widths = {o.width for o in self.operands if isinstance(o, Reg) and o.kind == "g"}
            if self.op.startswith(("movs", "movz")) and self.spec.get("dst_width"):
                widths = {self.spec["dst_width"]}
            if self.op.startswith("set"):
                widths = {8}
            if len(widths) > 1 and not (self.op in ("shl", "shr", "sar", "sal") and len(self.operands) == 2):
                raise InvalidInput("instruction %s: mixed general register widths" % self.id)
            if self.op in ("shl", "shr", "sar", "sal") and len(self.operands) == 2 and isinstance(self.operands[0], Reg):
                widths = {self.operands[0].width}
            self.width = widths.pop() if widths else (64 if self.kind in ("scalar", "rmw", "load", "store", "branch") else None)
        elif self.width not in (8, 16, 32, 64):
            raise Unsupported("instruction %s: width %r not supported" % (self.id, self.width))
        if self.mem is not None:
            if self.spec.get("mem_size") is not None and not self.op.startswith(("movs", "movz")):
                self.mem_bytes = self.spec["mem_size"]
            elif self.op.startswith(("movs", "movz")):
                self.mem_bytes = self.spec["src_width"] // 8
            else:
                self.mem_bytes = self.width // 8 if self.width else 64
            if self.mem.broadcast in ("1to16",):
                self.mem_bytes = 4
            elif self.mem.broadcast == "1to8":
                self.mem_bytes = 8
            elif self.mem.broadcast in ("4to16",):
                self.mem_bytes = 16
            elif self.mem.broadcast == "4to8":
                self.mem_bytes = 32
            if self.mem.conv in ("float16", "uint16", "sint16") and self.mem_bytes == 64:
                self.mem_bytes = 32
            elif self.mem.conv in ("uint8", "sint8") and self.mem_bytes == 64:
                self.mem_bytes = 16
        else:
            self.mem_bytes = 0

    def functional_supported(self):
        return self.spec.get("fn") is not None

    def short(self):
        s = self.op
        if self.operands:
            s += " " + ", ".join(repr(o) for o in self.operands)
        if self.mask is not None:
            s += " {%s}" % self.mask.name
        return s

    def to_record(self):
        return {"id": self.id, "op": self.op, "text": self.short(), "class": self.cls, "label": self.label}


class Stream(object):
    def __init__(self, d, kernel_dir, idx, symbols=None, calls=None):
        if not isinstance(d, dict):
            raise InvalidInput("streams[%d] must be an object" % idx)
        self.context = d.get("context", idx)
        if not isinstance(self.context, int) or not 0 <= self.context <= 3:
            raise InvalidInput("streams[%d]: context must be 0..3" % idx)
        self.init = d.get("init", {})
        self.expected = d.get("expected", {})
        self.representation = "normalized-records"
        records = d.get("instructions")
        self.asm_notes = []
        if records is None and ("asm" in d or "asm_file" in d):
            from . import asm as asm_mod
            if "asm_file" in d:
                path = d["asm_file"]
                if not os.path.isabs(path):
                    path = os.path.join(kernel_dir, path)
                if not os.path.isfile(path):
                    raise InvalidInput("streams[%d]: asm_file %s not found" % (idx, path))
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                self.asm_source = path
            else:
                text = d["asm"] if isinstance(d["asm"], str) else "\n".join(d["asm"])
                self.asm_source = "<inline>"
            records, self.asm_notes = asm_mod.parse_gas(text)
            self.representation = "gas-att-subset"
        if not isinstance(records, list) or not records:
            raise InvalidInput("streams[%d]: 'instructions' must be a non-empty list (or give 'asm'/'asm_file')" % idx)
        self.insns = [Insn(r, i, self.context) for i, r in enumerate(records)]
        # resolve rip-relative symbols to absolute displacements
        for i in self.insns:
            for o in i.operands:
                if isinstance(o, Mem) and o.symbol == ".Lknc_absolute_rip":
                    o.symbol = None
                elif isinstance(o, Mem) and o.symbol is not None:
                    if not symbols or o.symbol not in symbols:
                        raise InvalidInput("streams[%d]: instruction %s refers to symbol %r; give its address in init.symbols" % (idx, i.id, o.symbol))
                    o.disp += parse_int(symbols[o.symbol], "init.symbols." + o.symbol)
                elif isinstance(o, Imm) and o.symbol is not None:
                    if not symbols or o.symbol not in symbols:
                        raise InvalidInput("streams[%d]: instruction %s uses the address of symbol %r; give it in init.symbols" % (idx, i.id, o.symbol))
                    o.value += parse_int(symbols[o.symbol], "init.symbols." + o.symbol)
            if i.imm is not None and any(isinstance(o, Imm) for o in i.operands):
                i.imm = [o for o in i.operands if isinstance(o, Imm)][-1].value
        ids = [i.id for i in self.insns]
        if len(set(ids)) != len(ids):
            raise InvalidInput("streams[%d]: duplicate instruction ids" % idx)
        self.labels = {}
        for i in self.insns:
            if i.label:
                if i.label in self.labels:
                    raise InvalidInput("streams[%d]: duplicate label %r" % (idx, i.label))
                self.labels[i.label] = i.index
        self.external_calls = []
        for i in self.insns:
            if i.target is not None and i.target not in self.labels:
                if i.op == "call":
                    if not calls or i.target not in calls:
                        raise Unsupported("streams[%d]: instruction %s calls %r, which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {\"cycles\": N, \"model\": ...})" % (idx, i.id, i.target),
                                          {"instruction": i.id, "callee": i.target})
                    self.external_calls.append(i.target)
                    continue
                raise InvalidInput("streams[%d]: branch %s targets unknown label %r" % (idx, i.id, i.target))
            for dep in i.explicit_deps:
                if dep not in ids:
                    raise InvalidInput("streams[%d]: instruction %s depends on unknown id %r" % (idx, i.id, dep))
        self.by_id = {i.id: i for i in self.insns}
        # return sites: the value a call pushes (the real return address when the layout is known)
        self.return_sites = {}
        self._ret_values = {}
        for i in self.insns:
            if i.op == "call" and i.target in self.labels:
                enc = i.encoding
                if enc.get("addr") is not None and enc.get("bytes"):
                    v = parse_int(enc["addr"], "encoding.addr") + enc["bytes"]
                else:
                    v = 0x7D0000000000 + (i.index + 1) * 16
                self._ret_values[i.index] = v
                self.return_sites[v] = i.index + 1

    def return_value(self, index):
        return self._ret_values[index]

    def has_control_flow(self):
        return any(i.is_branch for i in self.insns)


DEFAULT_NUMERICAL_POLICY = {"rounding": "rn", "ftz": False, "daz": False, "nan_compare": "any_nan", "ftz_rule": "tiny", "x87_control_word": "0x037f",
                            "gather_completion": "one_line"}


class Kernel(object):
    def __init__(self, raw, path=None):
        if not isinstance(raw, dict):
            raise InvalidInput("kernel must be a JSON object")
        if raw.get("schema") != KERNEL_SCHEMA:
            raise InvalidInput("kernel schema must be %r (got %r)" % (KERNEL_SCHEMA, raw.get("schema")))
        allowed = {"schema", "name", "description", "representation", "unit_of_work", "numerical_policy", "init", "expected",
                   "streams", "scenario", "loop", "max_steps", "memory_default", "notes", "provenance", "calls", "entry", "inputs"}
        extra = set(raw) - allowed
        if extra:
            raise InvalidInput("kernel: unknown top-level keys %s" % sorted(extra))
        self.raw = raw
        self.path = path
        self.dir = os.path.dirname(os.path.abspath(path)) if path else os.getcwd()
        self.name = raw.get("name", "unnamed")
        self.description = raw.get("description", "")
        self.unit_of_work = raw.get("unit_of_work", {"description": "whole kernel run", "count": 1})
        if "count" not in self.unit_of_work or parse_int(self.unit_of_work["count"], "unit_of_work.count") <= 0:
            raise InvalidInput("unit_of_work.count must be a positive integer")
        self.unit_count = parse_int(self.unit_of_work["count"], "unit_of_work.count")
        pol = dict(DEFAULT_NUMERICAL_POLICY)
        pol.update(raw.get("numerical_policy", {}))
        if pol["rounding"] not in VALID_ROUNDING:
            raise Unsupported("numerical_policy.rounding %r not supported" % pol["rounding"])
        if pol["nan_compare"] not in ("any_nan", "bits"):
            raise InvalidInput("numerical_policy.nan_compare must be any_nan or bits")
        pol["x87_control_word"] = parse_int(pol["x87_control_word"], "numerical_policy.x87_control_word")
        if pol["gather_completion"] not in ("one_line", "all"):
            raise InvalidInput("numerical_policy.gather_completion must be one_line or all")
        self.numerical_policy = pol
        self.init = raw.get("init", {})
        self.expected = raw.get("expected", {})
        self.memory_default = raw.get("memory_default")
        self.max_steps = parse_int(raw.get("max_steps", 200000), "max_steps")
        streams = raw.get("streams")
        if not isinstance(streams, list) or not streams:
            raise InvalidInput("kernel needs a non-empty 'streams' list")
        if len(streams) > 4:
            raise InvalidInput("at most 4 streams (hardware contexts)")
        symbols = self.init.get("symbols", {})
        self.calls = raw.get("calls", {})
        if not isinstance(self.calls, dict):
            raise InvalidInput("'calls' must be an object: callee name -> {cycles, model?, status?, source?}")
        for cname, c in self.calls.items():
            if not isinstance(c, dict):
                raise InvalidInput("calls.%s must be an object" % cname)
            extra_c = set(c) - {"cycles", "cycles_per_byte", "model", "status", "source", "note", "touches"}
            if extra_c:
                raise InvalidInput("calls.%s: unknown keys %s" % (cname, sorted(extra_c)))
        self.entry = raw.get("entry", "region")
        if self.entry not in ("region", "function"):
            raise InvalidInput("'entry' must be 'region' (start at the first record) or 'function' (ABI entry: return sentinel on the stack)")
        self.streams = [Stream(s, self.dir, i, symbols, self.calls) for i, s in enumerate(streams)]
        ctxs = [s.context for s in self.streams]
        if len(set(ctxs)) != len(ctxs):
            raise InvalidInput("two streams use the same context")
        self.streams.sort(key=lambda s: s.context)
        reps = {s.representation for s in self.streams}
        self.representation = "mixed" if len(reps) > 1 else reps.pop()
        declared = raw.get("representation")
        if declared and declared != self.representation and not (declared == "normalized-records" and self.representation == "normalized-records"):
            raise InvalidInput("declared representation %r does not match streams (%s)" % (declared, self.representation))
        self.scenario = self._validate_scenario(raw.get("scenario", {}))
        self.loop = raw.get("loop")
        if self.loop is not None:
            if not isinstance(self.loop, dict) or "label" not in self.loop:
                raise InvalidInput("loop must be {label, trip_count?, back_branch?}")
            for s in self.streams:
                if self.loop["label"] not in s.labels:
                    raise InvalidInput("loop label %r not found in stream for context %d" % (self.loop["label"], s.context))

    def _validate_scenario(self, sc):
        if not isinstance(sc, dict):
            raise InvalidInput("scenario must be an object")
        mem = dict(sc.get("memory", {"type": "fixed_level", "level": "l1"}))
        br = dict(sc.get("branch", {"type": "all_predicted"}))
        t = mem.get("type")
        if t == "fixed_level":
            if mem.get("level") not in MEMORY_LEVELS:
                raise InvalidInput("scenario.memory.level must be one of %s" % (MEMORY_LEVELS,))
        elif t == "classified":
            if mem.get("default") not in MEMORY_LEVELS:
                raise InvalidInput("scenario.memory.default must be a memory level")
            for i, rng in enumerate(mem.get("ranges", [])):
                for k in ("start", "end", "level"):
                    if k not in rng:
                        raise InvalidInput("scenario.memory.ranges[%d] needs start, end, level" % i)
                if rng["level"] not in MEMORY_LEVELS:
                    raise InvalidInput("scenario.memory.ranges[%d].level invalid" % i)
                rng["start"] = parse_int(rng["start"], "range.start")
                rng["end"] = parse_int(rng["end"], "range.end")
        elif t == "line_tracking":
            if mem.get("cold_level", "memory") not in MEMORY_LEVELS:
                raise InvalidInput("scenario.memory.cold_level invalid")
            mem.setdefault("cold_level", "memory")
            for i, rng in enumerate(mem.get("warm", [])):
                for k in ("start", "end", "level"):
                    if k not in rng:
                        raise InvalidInput("scenario.memory.warm[%d] needs start, end, level" % i)
                rng["start"] = parse_int(rng["start"], "warm.start")
                rng["end"] = parse_int(rng["end"], "warm.end")
            hwp = mem.get("hardware_prefetcher", "auto")
            if hwp not in ("off", "modeled", "auto"):
                raise Unsupported("scenario.memory.hardware_prefetcher=%r: use 'auto', 'off' or 'modeled' (streaming L2 prefetcher model)" % hwp)
            mem["hardware_prefetcher"] = hwp
            tlb = mem.get("tlb", "auto")
            if tlb not in ("off", "modeled", "auto"):
                raise Unsupported("scenario.memory.tlb=%r: use 'auto', 'off' or 'modeled'" % tlb)
            mem["tlb"] = tlb
            ps = mem.get("page_bytes", 4096)
            if ps not in (4096, 2097152):
                raise Unsupported("scenario.memory.page_bytes must be 4096 or 2097152")
            mem["page_bytes"] = ps
            svc = mem.get("memory_service", "auto")
            if svc not in ("unlimited", "modeled", "auto"):
                raise Unsupported("scenario.memory.memory_service must be auto, unlimited or modeled")
            mem["memory_service"] = svc
        else:
            raise Unsupported("scenario.memory.type %r not supported (fixed_level, classified, line_tracking)" % t)
        bt = br.get("type")
        if bt not in ("all_predicted", "all_mispredicted", "exit_mispredicted", "ids_mispredicted"):
            raise Unsupported("scenario.branch.type %r not supported (all_predicted, all_mispredicted, exit_mispredicted, ids_mispredicted)" % bt)
        if bt == "ids_mispredicted" and not isinstance(br.get("ids"), list):
            raise InvalidInput("scenario.branch.ids must be a list of instruction ids")
        fe = dict(sc.get("frontend", {"icache": "warm"}))
        if fe.get("icache", "warm") not in ("warm", "cold_l2", "cold_memory"):
            raise Unsupported("scenario.frontend.icache must be warm, cold_l2 or cold_memory")
        fe.setdefault("icache", "warm")
        extra_sc = set(sc) - {"memory", "branch", "frontend"}
        if extra_sc:
            raise InvalidInput("scenario: unknown keys %s" % sorted(extra_sc))
        return {"memory": mem, "branch": br, "frontend": fe}

    def stream_for(self, ctx):
        for s in self.streams:
            if s.context == ctx:
                return s
        return None

    def unsupported_functional(self):
        out = []
        for s in self.streams:
            for i in s.insns:
                if not i.functional_supported():
                    out.append({"id": i.id, "op": i.op, "context": s.context, "note": i.spec.get("note", "")})
        return out

    def describe(self):
        return {"name": self.name, "representation": self.representation, "contexts": [s.context for s in self.streams],
                "instructions": {s.context: len(s.insns) for s in self.streams}, "unit_of_work": self.unit_of_work,
                "numerical_policy": dict(self.numerical_policy, x87_control_word="0x%04x" % self.numerical_policy["x87_control_word"]),
                "scenario": self.scenario, "loop": self.loop}


def load_kernel(path):
    raw = load_json(path, "kernel")
    return Kernel(raw, path)
