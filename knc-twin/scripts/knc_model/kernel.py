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
GPR32_TO_64 = dict(zip(GPR32, GPR64))
ZMM = ["zmm%d" % i for i in range(32)]
KREG = ["k%d" % i for i in range(8)]
VALID_ROUNDING = ("rn", "rd", "ru", "rz")
MEMORY_LEVELS = ("l1", "l2", "memory")


class Reg(object):
    __slots__ = ("name", "kind", "base", "width")

    def __init__(self, name):
        n = name.lower()
        if n in GPR64:
            self.kind, self.base, self.width = "g", n, 64
        elif n in GPR32:
            self.kind, self.base, self.width = "g", GPR32_TO_64[n], 32
        elif n in ZMM:
            self.kind, self.base, self.width = "v", n, 512
        elif n in KREG:
            self.kind, self.base, self.width = "k", n, 16
        else:
            raise InvalidInput("unknown register %r" % name)
        self.name = n

    def __repr__(self):
        return self.name


class Mem(object):
    __slots__ = ("base", "index", "scale", "disp", "broadcast", "size", "vindex")

    def __init__(self, d, what):
        if not isinstance(d, dict):
            raise InvalidInput("%s: memory operand must be an object" % what)
        allowed = {"base", "index", "scale", "disp", "broadcast", "size", "mem", "vindex"}
        extra = set(d) - allowed
        if extra:
            raise InvalidInput("%s: unknown memory operand keys %s" % (what, sorted(extra)))
        self.base = Reg(d["base"]) if d.get("base") else None
        self.index = Reg(d["index"]) if d.get("index") else None
        self.vindex = Reg(d["vindex"]) if d.get("vindex") else None
        self.scale = parse_int(d.get("scale", 1), what + ".scale")
        self.disp = parse_int(d.get("disp", 0), what + ".disp")
        self.broadcast = d.get("broadcast")
        self.size = d.get("size")
        if self.scale not in (1, 2, 4, 8):
            raise InvalidInput("%s: scale must be 1, 2, 4 or 8" % what)
        if self.base is not None and self.base.kind != "g":
            raise InvalidInput("%s: base must be a general register" % what)
        if self.index is not None and self.index.kind != "g":
            raise InvalidInput("%s: index must be a general register" % what)
        if self.vindex is not None and self.vindex.kind != "v":
            raise InvalidInput("%s: vindex must be a zmm register" % what)
        if self.broadcast not in (None, "1to16", "1to8"):
            raise Unsupported("%s: broadcast %r not supported (1to16, 1to8 only)" % (what, self.broadcast))
        if self.base is None and self.index is None and self.vindex is None:
            raise InvalidInput("%s: memory operand needs a base, index or vindex register" % what)

    def regs(self):
        out = []
        for r in (self.base, self.index, self.vindex):
            if r is not None:
                out.append(r)
        return out

    def __repr__(self):
        parts = []
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
        return s


class Imm(object):
    __slots__ = ("value",)

    def __init__(self, v):
        self.value = v

    def __repr__(self):
        return "$%d" % self.value


class Label(object):
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


def _parse_operand(raw, role, what):
    kinds = role.split(":")[1] if ":" in role else role
    if isinstance(raw, dict):
        if "imm" in raw:
            if "i" not in kinds:
                raise InvalidInput("%s: immediate not allowed here" % what)
            return Imm(parse_int(raw["imm"], what))
        if "m" not in kinds and kinds not in ("mi",):
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
        if low in GPR64 or low in GPR32 or low in ZMM or low in KREG:
            r = Reg(low)
            if r.kind == "g" and "g" not in kinds:
                raise InvalidInput("%s: general register %s not allowed for role %r" % (what, s, role))
            if r.kind == "v" and "v" not in kinds:
                raise InvalidInput("%s: zmm register %s not allowed for role %r" % (what, s, role))
            if r.kind == "k" and "k" not in kinds:
                raise InvalidInput("%s: mask register %s not allowed for role %r" % (what, s, role))
            return r
        if "i" in kinds:
            try:
                return Imm(parse_int(s, what))
            except InvalidInput:
                pass
        raise InvalidInput("%s: cannot interpret operand %r" % (what, raw))
    raise InvalidInput("%s: bad operand %r" % (what, raw))


class Insn(object):
    """One static instruction record with derived dependency sets."""

    def __init__(self, d, index, stream_id):
        if not isinstance(d, dict):
            raise InvalidInput("stream %s instruction %d: record must be an object" % (stream_id, index))
        allowed = {"id", "op", "ops", "mask", "rounding", "label", "encoding", "deps", "addr", "width", "comment", "x87_deps", "lines"}
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
        if self.rounding is not None and self.rounding not in VALID_ROUNDING:
            raise Unsupported("instruction %s: rounding %r not supported" % (self.id, self.rounding))
        self.mask = Reg(d["mask"]) if d.get("mask") else None
        if self.mask is not None and self.mask.kind != "k":
            raise InvalidInput("instruction %s: mask must be k0-k7" % self.id)
        raw_ops = d.get("ops", [])
        roles = spec["ops"]
        if roles == ["x87"]:
            self.operands = []
            self.roles = []
        else:
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
        for opnd, role in zip(self.operands, self.roles):
            acc = role.split(":")[0]
            if isinstance(opnd, Reg):
                if acc in ("r", "rw"):
                    self.reads.add(opnd.base)
                if acc in ("w", "rw"):
                    self.writes.add(opnd.base)
            elif isinstance(opnd, Mem):
                for r in opnd.regs():
                    self.addr_regs.add(r.base)
                    self.reads.add(r.base)
                if acc == "a":
                    pass  # lea: address only
                else:
                    if self.mem is not None:
                        raise InvalidInput("instruction %s: two memory operands" % self.id)
                    self.mem = opnd
                    self.mem_role = acc
            elif isinstance(opnd, Label):
                self.target = opnd.name
            elif isinstance(opnd, Imm):
                self.imm = opnd.value
        if self.mask is not None:
            self.reads.add(self.mask.base)
            if self.cls == "vector_gather":
                self.writes.add(self.mask.base)  # completion mask is cleared
        self.flags_r = bool(self.spec.get("flags_r"))
        self.flags_w = bool(self.spec.get("flags_w"))
        self.is_branch = self.cls == "branch"
        if self.is_branch and self.target is None:
            raise InvalidInput("instruction %s: branch needs a target label" % self.id)
        # effective timing class for memory forms
        self.is_load = False
        self.is_store = False
        self.folded_load = False
        if self.mem is not None and self.cls not in ("prefetch_l1", "prefetch_l2", "vector_gather", "fence"):
            if self.mem_role in ("w", "rw") and self.mem_role != "r":
                self.is_store = True
                if self.mem_role == "rw":
                    self.is_load = True
            else:
                self.is_load = True
        if self.op == "mov" and self.mem is not None:
            self.cls = "scalar_store" if self.is_store else "scalar_load"
        elif self.op in ("add", "sub", "and", "or", "xor", "inc", "dec", "neg", "not", "shl", "shr", "sar") and self.mem is not None:
            raise Unsupported("instruction %s: read-modify-write memory form of %s is not supported" % (self.id, self.op))
        elif self.op in ("cmp", "test", "imul", "movzx") and self.mem is not None:
            self.cls = "scalar_load"
        elif self.op in ("vmovaps", "vmovapd", "vmovdqa32", "vmovdqa64"):
            if self.mem is None:
                self.cls = "vector_arith"  # register move
                self.spec = dict(self.spec, note="register-to-register move modeled as vector_arith latency")
            elif self.is_store:
                self.cls = "vector_store"
            else:
                self.cls = "vector_load"
        elif self.cls == "vector_arith" and self.mem is not None:
            self.folded_load = True  # arithmetic with a memory source: load folded into the U-pipe op
        if self.cls == "vector_gather":
            self.is_load = self.mem_role == "r"
            self.is_store = self.mem_role == "w"
        self.pipes = isa.CLASSES[self.cls]["pipes"]
        self.kind = isa.CLASSES[self.cls]["kind"]
        # scalar operand width
        if self.width is None:
            widths = {o.width for o in self.operands if isinstance(o, Reg) and o.kind == "g"}
            if len(widths) > 1:
                raise InvalidInput("instruction %s: mixed 32/64-bit general registers" % self.id)
            self.width = widths.pop() if widths else (64 if self.kind in ("scalar", "load", "store", "branch") else None)
        elif self.width not in (32, 64):
            raise Unsupported("instruction %s: width %r not supported (32 or 64)" % (self.id, self.width))
        if self.mem is not None and self.spec.get("mem_size") is None and self.cls in ("scalar_load", "scalar_store"):
            self.mem_bytes = self.width // 8
        elif self.mem is not None:
            self.mem_bytes = self.spec.get("mem_size") or (self.width // 8 if self.width else 64)
            if self.mem.broadcast == "1to16":
                self.mem_bytes = 4
            elif self.mem.broadcast == "1to8":
                self.mem_bytes = 8
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
    def __init__(self, d, kernel_dir, idx):
        if not isinstance(d, dict):
            raise InvalidInput("streams[%d] must be an object" % idx)
        self.context = d.get("context", idx)
        if not isinstance(self.context, int) or not 0 <= self.context <= 3:
            raise InvalidInput("streams[%d]: context must be 0..3" % idx)
        self.init = d.get("init", {})
        self.expected = d.get("expected", {})
        self.representation = "normalized-records"
        records = d.get("instructions")
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
        else:
            self.asm_notes = []
        if not isinstance(records, list) or not records:
            raise InvalidInput("streams[%d]: 'instructions' must be a non-empty list (or give 'asm'/'asm_file')" % idx)
        self.insns = [Insn(r, i, self.context) for i, r in enumerate(records)]
        ids = [i.id for i in self.insns]
        if len(set(ids)) != len(ids):
            raise InvalidInput("streams[%d]: duplicate instruction ids" % idx)
        self.labels = {}
        for i in self.insns:
            if i.label:
                if i.label in self.labels:
                    raise InvalidInput("streams[%d]: duplicate label %r" % (idx, i.label))
                self.labels[i.label] = i.index
        for i in self.insns:
            if i.target is not None and i.target not in self.labels:
                raise InvalidInput("streams[%d]: branch %s targets unknown label %r" % (idx, i.id, i.target))
            for dep in i.explicit_deps:
                if dep not in ids:
                    raise InvalidInput("streams[%d]: instruction %s depends on unknown id %r" % (idx, i.id, dep))
        self.by_id = {i.id: i for i in self.insns}

    def has_control_flow(self):
        return any(i.is_branch for i in self.insns)


DEFAULT_NUMERICAL_POLICY = {"rounding": "rn", "ftz": False, "daz": False, "nan_compare": "any_nan", "ftz_rule": "tiny"}


class Kernel(object):
    def __init__(self, raw, path=None):
        if not isinstance(raw, dict):
            raise InvalidInput("kernel must be a JSON object")
        if raw.get("schema") != KERNEL_SCHEMA:
            raise InvalidInput("kernel schema must be %r (got %r)" % (KERNEL_SCHEMA, raw.get("schema")))
        allowed = {"schema", "name", "description", "representation", "unit_of_work", "numerical_policy", "init", "expected",
                   "streams", "scenario", "loop", "max_steps", "memory_default", "notes"}
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
        self.numerical_policy = pol
        self.init = raw.get("init", {})
        self.expected = raw.get("expected", {})
        self.memory_default = raw.get("memory_default")  # None = reading uninitialized memory is an error
        self.max_steps = parse_int(raw.get("max_steps", 200000), "max_steps")
        streams = raw.get("streams")
        if not isinstance(streams, list) or not streams:
            raise InvalidInput("kernel needs a non-empty 'streams' list")
        if len(streams) > 4:
            raise InvalidInput("at most 4 streams (hardware contexts)")
        self.streams = [Stream(s, self.dir, i) for i, s in enumerate(streams)]
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
            if mem.get("hardware_prefetcher", "off") != "off":
                raise Unsupported("scenario.memory.hardware_prefetcher=%r: the L2 hardware prefetcher is not modeled; only 'off' is supported" % mem.get("hardware_prefetcher"))
        else:
            raise Unsupported("scenario.memory.type %r not supported (fixed_level, classified, line_tracking)" % t)
        bt = br.get("type")
        if bt not in ("all_predicted", "all_mispredicted", "exit_mispredicted", "ids_mispredicted"):
            raise Unsupported("scenario.branch.type %r not supported (all_predicted, all_mispredicted, exit_mispredicted, ids_mispredicted)" % bt)
        if bt == "ids_mispredicted" and not isinstance(br.get("ids"), list):
            raise InvalidInput("scenario.branch.ids must be a list of instruction ids")
        return {"memory": mem, "branch": br}

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
                "numerical_policy": self.numerical_policy, "scenario": self.scenario, "loop": self.loop}


def load_kernel(path):
    raw = load_json(path, "kernel")
    return Kernel(raw, path)
