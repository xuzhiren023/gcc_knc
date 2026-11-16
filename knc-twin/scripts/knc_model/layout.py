"""Code layout from a disassembly listing: addresses, instruction bytes and prefix classes.

The front-end model (timing.py) needs what the assembler produced, not what the compiler
wrote: alignment padding and its NOP encodings, instruction lengths, legacy prefixes. This
module reads `objdump -d` (or `-dr` for relocatable objects) text of the K1OM binutils and
returns, per function, the instruction list with an `encoding` record for each instruction.

Prefix classes (R02 p.56): 62 (vector), c4/c5 (mask), REX and 0f decode with no penalty;
66, 67, lock, segment and rep prefixes take two decode cycles each.
"""
import re

SLOW_PREFIXES = {0x66: "66", 0x67: "67", 0xF0: "lock", 0xF2: "repne", 0xF3: "rep",
                 0x2E: "cs", 0x36: "ss", 0x3E: "ds", 0x26: "es", 0x64: "fs", 0x65: "gs"}
_LINE_RE = re.compile(r"^\s*([0-9a-fA-F]+):\t((?:[0-9a-fA-F]{2} )+)\s*(?:\t(.*))?$")
_FUNC_RE = re.compile(r"^([0-9a-fA-F]+) <([^>]+)>:\s*$")
_RELOC_RE = re.compile(r"^\s+([0-9a-fA-F]+):\s+(R_\S+)\s+(\S+)\s*$")
_NOP_RE = re.compile(r"^(nop[wlq]?\b|data(16|32)\b|xchg\s+%ax,%ax$|fnop$)")


class DInsn(object):
    __slots__ = ("addr", "raw", "text", "relocs")

    def __init__(self, addr, raw, text):
        self.addr = addr
        self.raw = raw
        self.text = text
        self.relocs = []


def parse_objdump(text):
    """-> (functions {name: [DInsn]}, order [name], {name: start address})."""
    funcs, order, starts = {}, [], {}
    cur = None
    last = None
    for line in text.splitlines():
        if line.startswith("Disassembly of section"):
            cur = None
            continue
        m = _FUNC_RE.match(line)
        if m:
            name = m.group(2)
            cur = funcs.setdefault(name, [])
            if name not in starts:
                order.append(name)
                starts[name] = int(m.group(1), 16)
            last = None
            continue
        if cur is None:
            continue
        m = _LINE_RE.match(line)
        if m:
            addr = int(m.group(1), 16)
            raw = bytes(int(b, 16) for b in m.group(2).split())
            txt = (m.group(3) or "").strip()
            if not txt and last is not None and last.addr + len(last.raw) == addr:
                last.raw += raw  # continuation line of a long instruction
                continue
            last = DInsn(addr, raw, txt)
            cur.append(last)
            continue
        m = _RELOC_RE.match(line)
        if m and last is not None:
            last.relocs.append((int(m.group(1), 16), m.group(2), m.group(3)))
    return funcs, order, starts


def encoding_of(raw, text, addr=None):
    """Encoding facts used by the pairing and decode rules: length, slow (two-cycle) prefixes,
    displacement and immediate presence, 32-bit displacement."""
    i = 0
    slow = []
    n = len(raw)
    while i < n and raw[i] in SLOW_PREFIXES:
        slow.append(SLOW_PREFIXES[raw[i]])
        i += 1
    oplen = 1
    if i < n and 0x40 <= raw[i] <= 0x4F:
        i += 1
    if i < n and raw[i] == 0x62:
        i += 4
    elif i < n and raw[i] == 0xC4:
        i += 3
    elif i < n and raw[i] == 0xC5:
        i += 2
    elif i < n and raw[i] == 0x0F:
        oplen = 3 if (i + 1 < n and raw[i + 1] in (0x38, 0x3A)) else 2
    enc = {"bytes": n, "slow_prefixes": len(slow)}
    if addr is not None:
        enc["addr"] = addr
    if slow:
        enc["prefixes"] = slow
    operands = text.split(None, 1)[1] if len(text.split(None, 1)) > 1 else ""
    operands = operands.split("#")[0]
    if "(" in operands or re.search(r"%[a-z]s:", operands):
        m = i + oplen
        if m < n:
            modrm = raw[m]
            mod, rm = modrm >> 6, modrm & 7
            disp = 0
            if mod != 3:
                if mod == 1:
                    disp = 1
                elif mod == 2:
                    disp = 4
                elif rm == 5:
                    disp = 4
                elif rm == 4 and m + 1 < n and (raw[m + 1] & 7) == 5:
                    disp = 4
                if disp:
                    enc["disp"] = True
                if disp == 4:
                    enc["disp32"] = True
    if re.search(r"\$-?(0x)?[0-9a-fA-F]", operands):
        enc["imm"] = True
    return enc


def is_nop_text(text):
    return bool(_NOP_RE.match(text.strip()))
