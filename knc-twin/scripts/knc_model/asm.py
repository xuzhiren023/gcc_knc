"""GAS AT&T syntax subset -> normalized records.

Accepted (documented in references/input-format.md):
  label:                       labels
  # comment                    comments (also trailing)
  .directives                  ignored and listed in notes (.text, .globl, .p2align, .type, .size, .cfi_*)
  mnemonic[q|l] ops            AT&T operand order (source first); q/l suffix on scalar ops sets width 64/32
  %reg  $imm  disp(%base,%index,scale)   operands
  dest{%k1}                    write mask on the destination operand
  mem{1to16} / mem{1to8}       memory broadcast
  dest{rn}|{rd}|{ru}|{rz}      rounding on the destination (KNC swizzle field used for rounding)
  lock addl $imm, mem          -> lock_add
Rejected: any other swizzle ({cdab}, {aaaa}, ...), 8/16-bit registers, segment prefixes, unknown mnemonics.
"""
import re

from .errors import InvalidInput, Unsupported

_IGNORED_DIRECTIVES = (".text", ".globl", ".global", ".p2align", ".align", ".type", ".size", ".cfi_", ".file", ".section", ".ident", ".ret")
_LABEL_RE = re.compile(r"^([A-Za-z_.$][\w.$]*):(.*)$")
_MEM_RE = re.compile(r"^(?P<disp>[-+]?(0x[0-9a-fA-F]+|\d+))?\((?P<inner>[^)]*)\)$")
_SIZE_SUFFIX_OPS = ("mov", "add", "sub", "and", "or", "xor", "cmp", "test", "lea", "inc", "dec", "neg", "not", "shl", "shr", "sar", "imul")
_ROUNDING = {"rn": "rn", "rd": "rd", "ru": "ru", "rz": "rz", "rn-sae": "rn", "rd-sae": "rd", "ru-sae": "ru", "rz-sae": "rz"}


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


def _parse_reg(tok, where):
    if not tok.startswith("%"):
        raise InvalidInput("%s: expected register, got %r" % (where, tok))
    return tok[1:].lower()


def _parse_operand(tok, where, idx, n_ops):
    """Returns (operand, mask, rounding)."""
    mask = None
    rounding = None
    broadcast = None
    # trailing {...} groups
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
        elif grp in ("1to16", "1to8"):
            broadcast = grp
        else:
            raise Unsupported("%s: swizzle/modifier {%s} is not supported" % (where, grp))
    if tok.startswith("$"):
        return {"imm": tok[1:]}, mask, rounding
    if tok.startswith("%"):
        return tok[1:].lower(), mask, rounding
    m = _MEM_RE.match(tok)
    if m:
        d = {}
        if m.group("disp"):
            d["disp"] = m.group("disp")
        inner = [p.strip() for p in m.group("inner").split(",")]
        if inner and inner[0]:
            d["base"] = _parse_reg(inner[0], where)
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
        return d, mask, rounding
    if re.match(r"^[A-Za-z_.$][\w.$]*$", tok):
        return tok, mask, rounding  # label
    raise InvalidInput("%s: cannot parse operand %r" % (where, tok))


def parse_gas(text):
    """Return (records, notes). Raises InvalidInput/Unsupported on anything outside the subset."""
    records = []
    notes = []
    pending_label = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = _LABEL_RE.match(line)
        if m:
            if pending_label is not None:
                raise InvalidInput("line %d: two labels without an instruction between them (%s, %s)" % (lineno, pending_label, m.group(1)))
            pending_label = m.group(1)
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
        if mnem == "lock":
            sub = rest.split(None, 1)
            if not sub or not sub[0].lower().startswith("add"):
                raise Unsupported("%s: only 'lock add' is accepted among lock-prefixed instructions" % where)
            mnem = "lock_add"
            rest = sub[1] if len(sub) > 1 else ""
            width = 32 if sub[0].lower().endswith("l") else 64
        else:
            width = None
        if mnem in ("ret", "nop"):
            raise Unsupported("%s: %r is outside the kernel subset (strip the function epilogue)" % (where, mnem))
        base = mnem
        if mnem not in ("lock_add",) and not mnem.startswith(("v", "k", "j", "f")):
            for b in _SIZE_SUFFIX_OPS:
                if mnem == b + "q":
                    base, width = b, 64
                    break
                if mnem == b + "l":
                    base, width = b, 32
                    break
                if mnem in (b + "w", b + "b"):
                    raise Unsupported("%s: 8/16-bit operation %r not supported" % (where, mnem))
        toks = _split_operands(rest) if rest else []
        ops = []
        mask = None
        rounding = None
        for i, tok in enumerate(toks):
            o, mk, rd = _parse_operand(tok, where, i, len(toks))
            ops.append(o)
            if mk:
                mask = mk
            if rd:
                rounding = rd
        ops.reverse()  # AT&T source-first -> Intel destination-first
        rec = {"id": "L%d" % lineno, "op": base, "ops": ops}
        if mask:
            rec["mask"] = mask
        if rounding:
            rec["rounding"] = rounding
        if width:
            rec["width"] = width
        if pending_label:
            rec["label"] = pending_label
            pending_label = None
        records.append(rec)
    if pending_label is not None:
        raise InvalidInput("trailing label %r without an instruction" % pending_label)
    return records, notes


def emit_gas(stream):
    """Records -> AT&T text for the supported subset (used by prepare-native)."""
    lines = []
    for insn in stream.insns:
        if insn.label:
            lines.append("%s:" % insn.label)
        mnem = insn.op
        if insn.kind in ("scalar", "load", "store") and insn.op in _SIZE_SUFFIX_OPS and insn.width:
            mnem = insn.op + ("q" if insn.width == 64 else "l")
        if insn.op == "lock_add":
            mnem = "lock addl" if insn.width == 32 else "lock addq"
        toks = []
        for k, (opnd, role) in enumerate(zip(insn.operands, insn.roles)):
            name = type(opnd).__name__
            if name == "Reg":
                t = "%" + opnd.name
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
            if k == 0 and insn.mask is not None:
                t += "{%%%s}" % insn.mask.name
            if k == 0 and insn.rounding is not None and insn.kind == "vector":
                t += "{%s}" % insn.rounding
            toks.append(t)
        toks.reverse()
        lines.append("\t%s %s" % (mnem, ", ".join(toks)) if toks else "\t" + mnem)
    return "\n".join(lines) + "\n"
