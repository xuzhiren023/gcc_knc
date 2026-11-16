"""GAS AT&T syntax subset -> normalized records.

Accepted (documented in references/input-format.md):
  label:  .Lname:  1:             labels, including numeric local labels (targets 1b / 1f)
  # comment                       comments (trailing too)
  .directives                     ignored (listed in notes): .text .globl .p2align .type .size .cfi_* .section .file
                                  .ident .align .loc .string? -> no: data directives are rejected here (the adapter handles them)
  mnemonic[q|l|w|b] ops           AT&T operand order (source first); size suffix on scalar ops sets the width
  %reg  $imm  disp(%base,%index,scale)  symbol(%rip)  disp expressions like 4+0(%rsi)
  %st  %st(i)                     x87 stack registers
  dest{%k1}                       write mask on the destination operand
  reg{cdab} ...                   register swizzles (cdab badc dacb aaaa bbbb cccc dddd)
  mem{1to16} {4to16} {1to8} {4to8}  memory broadcasts
  mem{float16} {uint8} {sint8} {uint16} {sint16}   up-conversion on a memory source
  reg{float16} ...                down-conversion on the register source of a store
  dest{rn}|{rd}|{ru}|{rz}         rounding on the destination (KNC swizzle field)
  lock addl / lock; addl          -> lock_add
  rep; ret / rep ret              -> ret
Rejected: 8/16-bit forms outside the table, segment prefixes, unknown mnemonics and directives.
"""
import re

from .errors import InvalidInput, Unsupported
from . import isa

_IGNORED_DIRECTIVES = (".text", ".globl", ".global", ".p2align", ".align", ".type", ".size", ".cfi_", ".file", ".section",
                       ".ident", ".loc", ".local", ".weak", ".hidden", ".balign", ".data", ".bss", ".rodata")
_LABEL_RE = re.compile(r"^([A-Za-z_.$][\w.$]*|\d+):(.*)$")
_MEM_RE = re.compile(r"^(?P<disp>[^()]*)\((?P<inner>[^)]*)\)$")
_SIZE_SUFFIX_OPS = ("mov", "add", "sub", "and", "or", "xor", "adc", "sbb", "cmp", "test", "lea", "inc", "dec", "neg", "not",
                    "shl", "shr", "sar", "sal", "imul", "idiv", "div", "push", "pop", "bt", "xchg", "xadd", "cmpxchg")
_ROUNDING = {"rn": "rn", "rd": "rd", "ru": "ru", "rz": "rz", "rn-sae": "rn", "rd-sae": "rd", "ru-sae": "ru", "rz-sae": "rz"}
_ALIASES = {"retq": "ret", "callq": "call", "jmpq": "jmp", "repz": "rep", "pushq": "push", "popq": "pop", "leaveq": "leave"}
_NO_SUFFIX = {"movslq", "movsbl", "movsbq", "movswl", "movswq", "movzbl", "movzbq", "movzwl", "movzwq", "movsbw", "movzbw",
              "cltq", "cltd", "cqto", "leave", "nop", "ret", "call", "jmp", "movabsq"}


def _split_operands(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(" or ch == "{":
            depth += 1
        elif ch == ")" or ch == "}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _eval_disp(text, where):
    """Integer displacement expressions: digits, hex, + and -; optionally a leading symbol
    (with an @gottpoff/@tpoff/@GOTPCREL/@PLT suffix kept in the symbol name)."""
    t = text.strip()
    if not t:
        return 0, None
    m = re.match(r"^([A-Za-z_.$][\w.$]*(?:@\w+)?)?(.*)$", t)
    sym = m.group(1)
    rest = m.group(2).strip()
    if sym and rest and rest[0] not in "+-":
        raise InvalidInput("%s: bad displacement %r" % (where, text))
    total = 0
    for sign, num in re.findall(r"([+-]?)\s*(0x[0-9a-fA-F]+|\d+)", rest):
        v = int(num, 0)
        total += -v if sign == "-" else v
    if not re.fullmatch(r"(\s*[+-]?\s*(0x[0-9a-fA-F]+|\d+))*\s*", rest):
        raise InvalidInput("%s: cannot evaluate displacement %r" % (where, text))
    return total, sym


def _parse_reg(tok, where):
    if not tok.startswith("%"):
        raise InvalidInput("%s: expected register, got %r" % (where, tok))
    return tok[1:].lower()


def _parse_operand(tok, where, branch=False):
    """Returns (operand, mask, rounding)."""
    mask = None
    rounding = None
    broadcast = None
    conv = None
    swizzle = None
    while tok.endswith("}"):
        pos = tok.rfind("{")
        if pos < 0:
            raise InvalidInput("%s: unbalanced brace in %r" % (where, tok))
        grp = tok[pos + 1:-1].strip()
        tok = tok[:pos].strip()
        if grp.startswith("%k"):
            mask = grp[1:].lower()
        elif grp in _ROUNDING:
            rounding = _ROUNDING[grp]
        elif grp in isa.BROADCASTS:
            broadcast = grp
        elif grp in isa.SWIZZLES:
            swizzle = grp
        elif grp in isa.UPCONV_PS:
            conv = grp
        else:
            raise Unsupported("%s: modifier {%s} is not supported" % (where, grp))
    segment = None
    mseg = re.match(r"^%([fg]s):(.*)$", tok)
    if mseg:
        segment, tok = mseg.group(1), mseg.group(2).strip()
        if not tok.endswith(")"):
            disp, sym = _eval_disp(tok, where)
            d = {"segment": segment, "disp": disp}
            if sym:
                d["symbol"] = sym
            return d, mask, rounding
    elif re.match(r"^%[cdes]s:", tok):
        raise Unsupported("%s: segment override in %r not supported (fs and gs only)" % (where, tok))
    if tok.startswith("$"):
        v, sym = _eval_disp(tok[1:], where)
        if sym:
            return {"imm": v, "imm_symbol": sym}, mask, rounding
        return {"imm": v}, mask, rounding
    if tok.startswith("%"):
        name = tok[1:].lower()
        if swizzle or conv:
            d = {"reg": name}
            if swizzle:
                d["swizzle"] = swizzle
            if conv:
                d["conv"] = conv
            return d, mask, rounding
        return name, mask, rounding
    m = _MEM_RE.match(tok)
    if m:
        d = {}
        if segment:
            d["segment"] = segment
        disp, sym = _eval_disp(m.group("disp"), where)
        if disp:
            d["disp"] = disp
        inner = [p.strip() for p in m.group("inner").split(",")]
        if inner and inner[0]:
            base = _parse_reg(inner[0], where)
            if base == "rip":
                if not sym:
                    raise InvalidInput("%s: rip-relative operand without a symbol" % where)
            else:
                d["base"] = base
        if sym:
            d["symbol"] = sym
        if len(inner) > 1 and inner[1]:
            r = _parse_reg(inner[1], where)
            if r.startswith("zmm"):
                d["vindex"] = r
            else:
                d["index"] = r
        if len(inner) > 2 and inner[2]:
            d["scale"] = int(inner[2], 0)
        if len(inner) > 3:
            raise InvalidInput("%s: bad memory operand %r" % (where, tok))
        if broadcast:
            d["broadcast"] = broadcast
        if conv:
            d["conv"] = conv
        return d, mask, rounding
    if tok.startswith("*"):
        raise Unsupported("%s: indirect branch or call %r is not supported (jump tables, function pointers)" % (where, tok))
    if branch:
        if re.match(r"^[A-Za-z_.$][\w.$]*(@PLT|@plt)?$", tok):
            return tok.split("@")[0], mask, rounding  # label
    elif re.match(r"^(0x[0-9a-fA-F]+|\d+)$", tok):
        return {"disp": int(tok, 0), "abs": True}, mask, rounding  # absolute address
    elif re.match(r"^[A-Za-z_.$][\w.$]*(@\w+)?([+-](0x[0-9a-fA-F]+|\d+))?$", tok):
        disp, sym = _eval_disp(tok, where)
        return {"disp": disp, "symbol": sym} if disp else {"symbol": sym}, mask, rounding
    if re.match(r"^[A-Za-z_.$][\w.$]*$", tok):
        return tok, mask, rounding  # label
    if re.match(r"^\d+[bf]$", tok):
        return tok, mask, rounding  # numeric local label reference
    if re.match(r"^[A-Za-z_.$][\w.$]*(\+\d+)?$", tok):
        raise Unsupported("%s: absolute symbol operand %r not supported" % (where, tok))
    raise InvalidInput("%s: cannot parse operand %r" % (where, tok))


def _strip_suffix(mnem, where):
    """(base mnemonic, width or None)."""
    if mnem in _NO_SUFFIX or mnem.startswith(("v", "k", "j", "f", "set", "cmov")) or isa.lookup(mnem) is not None and mnem not in ("mov",):
        if mnem == "movabsq":
            return "movabs", 64
        return mnem, None
    for b in _SIZE_SUFFIX_OPS:
        for suf, w in (("q", 64), ("l", 32), ("w", 16), ("b", 8)):
            if mnem == b + suf:
                return b, w
    return mnem, None


def parse_gas(text):
    """Return (records, notes). Raises InvalidInput/Unsupported on anything outside the subset."""
    records = []
    notes = []
    pending_labels = []
    numeric_defs = {}   # "1" -> count of definitions so far
    pending_numeric_refs = []  # (record index, token) for 'Nf' references
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        while True:
            m = _LABEL_RE.match(line)
            if not m:
                break
            name = m.group(1)
            if name.isdigit():
                n = numeric_defs.get(name, 0) + 1
                numeric_defs[name] = n
                pending_labels.append("L%s_%d" % (name, n))
            else:
                pending_labels.append(name)
            line = m.group(2).strip()
        if not line:
            continue
        if line.startswith("."):
            if any(line.startswith(p) for p in _IGNORED_DIRECTIVES):
                notes.append("line %d: directive ignored: %s" % (lineno, line))
                continue
            raise Unsupported("line %d: directive %r not accepted" % (lineno, line.split()[0]))
        where = "line %d" % lineno
        parts = line.split(None, 1)
        mnem = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        width = None
        mnem = _ALIASES.get(mnem, mnem)
        while mnem in ("data16", "data32", "cs", "ds", "es", "ss"):
            # prefix tokens the disassembler prints in front of padding nops
            sub = rest.split(None, 1)
            if not sub:
                break
            mnem, rest = sub[0].lower(), (sub[1] if len(sub) > 1 else "")
        locked = False
        if mnem in ("lock", "lock;"):
            sub = rest.split(None, 1)
            if not sub:
                raise InvalidInput("%s: lock prefix without an instruction" % where)
            mnem = sub[0].lower()
            rest = sub[1] if len(sub) > 1 else ""
            locked = True
        elif mnem in ("rep", "rep;"):
            sub = rest.split(None, 1)
            if sub and sub[0].lower() in ("ret", "retq"):
                mnem, rest = "ret", ""
            else:
                raise Unsupported("%s: rep-prefixed string instruction %r is not supported" % (where, rest.strip() or mnem))
        if mnem in ("nopw", "nopl", "nopq", "fnop") or (mnem == "nop" and rest) or (mnem == "xchg" and rest.replace(" ", "") == "%ax,%ax"):
            mnem, rest = "nop", ""   # multi-byte NOP: one instruction, operands are padding
        mnem = _ALIASES.get(mnem, mnem)
        base, w = _strip_suffix(mnem, where)
        if w is not None:
            width = w
        if locked:
            if isa.lookup("lock_" + base) is None:
                raise Unsupported("%s: lock-prefixed %r is not supported" % (where, mnem))
            base = "lock_" + base
        toks = _split_operands(rest) if rest else []
        ops = []
        mask = None
        rounding = None
        is_branch = base.startswith("j") or base == "call"
        for tok in toks:
            o, mk, rd = _parse_operand(tok, where, is_branch)
            ops.append(o)
            if mk:
                mask = mk
            if rd:
                rounding = rd
        ops.reverse()  # AT&T source-first -> Intel destination-first
        rec = {"id": "L%d" % lineno, "op": base, "ops": ops, "source": lineno}
        if mask:
            rec["mask"] = mask
        if rounding:
            rec["rounding"] = rounding
        if width:
            rec["width"] = width
        if pending_labels:
            rec["label"] = pending_labels[0]
            for extra in pending_labels[1:]:
                notes.append("line %d: labels %s and %s name the same instruction; %s kept as alias" % (lineno, pending_labels[0], extra, extra))
                rec.setdefault("aliases", []).append(extra)
            pending_labels = []
        # numeric label references
        for k, o in enumerate(ops):
            if isinstance(o, str) and re.match(r"^\d+[bf]$", o):
                num, dirn = o[:-1], o[-1]
                if dirn == "b":
                    n = numeric_defs.get(num, 0)
                    if n == 0:
                        raise InvalidInput("%s: backward reference %s has no definition" % (where, o))
                    ops[k] = "L%s_%d" % (num, n)
                else:
                    ops[k] = "L%s_%d" % (num, numeric_defs.get(num, 0) + 1)
        records.append(rec)
    if pending_labels:
        raise InvalidInput("trailing label %r without an instruction" % pending_labels[0])
    # label aliases: rewrite branch targets to the kept label
    alias_map = {}
    for rec in records:
        for a in rec.pop("aliases", []):
            alias_map[a] = rec["label"]
    if alias_map:
        for rec in records:
            rec["ops"] = [alias_map.get(o, o) if isinstance(o, str) else o for o in rec["ops"]]
    return records, notes


def emit_gas(stream):
    """Records -> AT&T text for the supported subset (used by prepare-native)."""
    lines = []
    for insn in stream.insns:
        if insn.label:
            lines.append("%s:" % insn.label)
        mnem = insn.op
        if insn.op in _SIZE_SUFFIX_OPS and insn.width and insn.spec.get("fn") != "x87":
            mnem = insn.op + {64: "q", 32: "l", 16: "w", 8: "b"}[insn.width]
        if insn.op == "movabs":
            mnem = "movabsq"
        if insn.op.startswith("lock_"):
            mnem = "lock " + insn.op[5:] + {64: "q", 32: "l", 16: "w", 8: "b"}[insn.width or 64]
        toks = []
        for k, (opnd, role) in enumerate(zip(insn.operands, insn.roles)):
            name = type(opnd).__name__
            if name == "Reg":
                if opnd.kind == "x":
                    t = "%st" if opnd.index == 0 else "%%st(%d)" % opnd.index
                else:
                    t = "%" + opnd.name
                if opnd.swizzle:
                    t += "{%s}" % opnd.swizzle
                if opnd.conv:
                    t += "{%s}" % opnd.conv
            elif name == "Imm":
                t = "$%d" % opnd.value
            elif name == "Label":
                t = opnd.name
            else:
                t = ""
                if opnd.disp:
                    t += str(opnd.disp)
                inner = "%" + opnd.base.name if opnd.base else ""
                if opnd.index or opnd.vindex:
                    inner += ",%" + (opnd.index or opnd.vindex).name + ",%d" % opnd.scale
                t += "(" + inner + ")"
                if opnd.broadcast:
                    t += "{%s}" % opnd.broadcast
                if opnd.conv:
                    t += "{%s}" % opnd.conv
            if k == 0 and insn.mask is not None:
                t += "{%%%s}" % insn.mask.name
            if k == 0 and insn.rounding is not None and insn.kind == "vector":
                t += "{%s}" % insn.rounding
            toks.append(t)
        toks.reverse()
        lines.append("\t%s %s" % (mnem, ", ".join(toks)) if toks else "\t" + mnem)
    return "\n".join(lines) + "\n"
