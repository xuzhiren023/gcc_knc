#!/usr/bin/env python3
"""Binary adapter: a K1OM object file or linked ELF -> knc-twin kernel with code layout.

  from_binary.py FILE --function NAME [--disassembly DIS.txt | --objdump TOOL]
                 [--with-callee NAME ...] [--calls CALLS.json] [--init INIT.json]
                 [--loop ADDR|.A_xxxx] [--innermost]
                 [--out KERNEL.json] [--report REPORT.json] [--profile ID]
  from_binary.py FILE --list [--disassembly DIS.txt | --objdump TOOL]

The whole function is converted as the assembler and linker left it: entry code, alignment
padding with its real NOP encodings, every instruction's address, length and prefixes
(`encoding` on each record), calls and returns. No source `.s` file is needed, so a build
that kept only objects or the executable can be analysed. The disassembly is the text of
`objdump -d` (linked file) or `objdump -dr` (object file) from the K1OM binutils; give it
with --disassembly, or let the adapter run the tool named by --objdump or $KNC_OBJDUMP.

Calls: a callee named by --with-callee is taken into the region and executed; any other
callee must be declared in --calls (a costed stub, see knc_model/stubs.py). Well-known
noreturn routines (__assert_fail, abort, ...) are declared automatically. Relocated read-only switch tables are resolved; other indirect jumps and calls are unsupported.
--report collects every unsupported line and writes no partial kernel. --loop selects a
loop head through its last backward branch; --innermost lists candidates with coverage.

Data: sections the code refers to (constants, string tables, .data, .bss) are copied from the
file. In an object file they are placed at synthetic addresses; in a linked file they keep
their addresses. Arguments and heap data come from --init, as for from_gcc_s.py.
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from knc_model import asm as asm_mod  # noqa: E402
from knc_model import layout  # noqa: E402
from knc_model.elf import Elf, SHF_ALLOC, SHF_EXECINSTR  # noqa: E402
from knc_model.errors import InvalidInput, TwinError, Unsupported  # noqa: E402
from knc_model.profile import load_profile  # noqa: E402
from knc_model.util import dump_json, load_json, sha256_of_file  # noqa: E402
import from_gcc_s  # noqa: E402

DATA_BASE = 0x20000000
NORETURN = ("__assert_fail", "abort", "__stack_chk_fail", "_Unwind_Resume", "exit", "_exit", "__cxa_throw", "__cxa_bad_alloc",
            "_gfortran_runtime_error", "_gfortran_runtime_error_at", "_gfortran_os_error", "_gfortran_stop_string", "__GI_abort")
_TARGET_RE = re.compile(r"^(\S+)\s+([0-9a-fA-F]+)\s+<([^>+]+)(\+0x[0-9a-fA-F]+)?>(?:,(%k[0-7]))?\s*$")
MAX_SECTION = 8 << 20


def disassemble(path, dis_path=None, tool=None):
    if dis_path:
        with open(dis_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    tool = tool or os.environ.get("KNC_OBJDUMP")
    if not tool:
        raise InvalidInput("give --disassembly FILE (text of 'objdump -dr'), or --objdump TOOL, or set KNC_OBJDUMP")
    try:
        out = subprocess.run([tool, "-dr", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        raise InvalidInput("could not run %s -dr %s: %s" % (tool, path, e))
    return out.stdout.decode("utf-8", errors="replace")


class Converter(object):
    def __init__(self, path, text):
        self.path = path
        self.elf = Elf(path)
        self.funcs, self.order, self.starts = layout.parse_objdump(text)
        self.sym_addr = {}       # data symbol or section -> address in the simulated memory
        self.memory = []         # init.memory blocks
        self.loaded_sections = set()
        self.next_data = DATA_BASE
        self.unresolved = set()
        self.notes = []
        self.got = {}
        self.tls = {}
        self._insns = {}
        self._tables = {}

    # ---- data ---------------------------------------------------------------------------------
    def _place_section(self, sec):
        """Object file: give an allocated data section a synthetic address and copy its bytes."""
        if sec.name in self.sym_addr:
            return self.sym_addr[sec.name]
        align = max(64, sec.align or 1)
        addr = (self.next_data + align - 1) // align * align
        self.sym_addr[sec.name] = addr
        self.next_data = addr + max(64, (sec.size + 63) // 64 * 64)
        if sec.size > MAX_SECTION:
            self.notes.append("section %s is %d bytes: not copied (give the data in --init)" % (sec.name, sec.size))
        elif sec.size:
            self.memory.append({"addr": "0x%x" % addr, "hex": self.elf.section_bytes(sec).hex(), "comment": "section %s" % sec.name})
        return addr

    def _load_linked_section(self, addr):
        sec = self.elf.section_of_addr(addr)
        if sec is None or sec.flags & SHF_EXECINSTR or sec.index in self.loaded_sections:
            return
        self.loaded_sections.add(sec.index)
        if sec.size > MAX_SECTION:
            self.notes.append("section %s is %d bytes: not copied (give the data in --init)" % (sec.name, sec.size))
            return
        self.memory.append({"addr": "0x%x" % sec.addr, "hex": self.elf.section_bytes(sec).hex(), "comment": "section %s" % sec.name})

    def symbol_address(self, name):
        """Address of a data symbol of an object file, or None when it is undefined there."""
        if name in self.sym_addr:
            return self.sym_addr[name]
        sec = self.elf.section(name)
        if sec is not None and sec.flags & SHF_ALLOC and not sec.flags & SHF_EXECINSTR:
            return self._place_section(sec)
        rec = self.elf.symbols.get(name)
        if rec is None or rec[0] == 0 or rec[0] >= len(self.elf.sections):
            return None
        sec = self.elf.sections[rec[0]]
        if sec.flags & SHF_EXECINSTR or not sec.flags & SHF_ALLOC:
            return None
        a = self._place_section(sec) + rec[1]
        self.sym_addr[name] = a
        return a

    def _sym_ref(self, sym, addend):
        """Text for a symbol reference; registers the symbol's address."""
        base = sym
        if "@" in sym:
            return sym, addend
        a = self.symbol_address(base)
        if a is None:
            self.unresolved.add(base)
        return base, addend

    # ---- code regions -------------------------------------------------------------------------
    def instructions(self, name):
        if name in self._insns:
            return self._insns[name]
        if name not in self.funcs or not self.funcs[name]:
            raise InvalidInput("function %r not in the disassembly; functions: %s" % (name, ", ".join(self.order[:40])))
        insns = list(self.funcs[name])
        while len(insns) > 1 and layout.is_nop_text(insns[-1].text.split("#")[0]):
            insns.pop()
        self._insns[name] = insns
        return insns

    def loop_ranges(self, name):
        """One interval per head, ending at its last direct backward branch."""
        insns = self.instructions(name)
        positions = {di.addr: i for i, di in enumerate(insns)}
        ends = {}
        for i, di in enumerate(insns):
            m = _TARGET_RE.match(di.text.split("#")[0].strip())
            if m and m.group(1).startswith("j") and not di.relocs:
                head = positions.get(int(m.group(2), 16))
                if head is not None and head < i:
                    ends[head] = i
        return sorted(ends.items())

    def loop_report(self, name, rows):
        """Coverage from the same complete listing, including failed lines."""
        insns = self.instructions(name)
        ranges = self.loop_ranges(name)
        inner = [(a, b) for a, b in ranges if not any(a <= c and d <= b and (a, b) != (c, d) for c, d in ranges)]
        result = []
        for a, b in inner:
            start, end = insns[a].addr, insns[b].addr
            body = [r for r in rows if r.get("function") == name and start <= r["address"] <= end]
            result.append({"label": ".A_%x" % start, "address": start, "end_address": end,
                           "instruction_count": b - a + 1, "summary": from_gcc_s.summarize(body),
                           "unsupported": [r for r in body if not r["functional"]]})
        return result

    def loop_location(self, loop, func=None):
        try:
            addr = int(loop[3:] if loop.startswith(".A_") else loop, 16)
        except ValueError:
            raise InvalidInput("--loop needs a hexadecimal address or .A_xxxx label")
        names = [func] if func else self.order
        matches = [(name, a, b) for name in names for a, b in self.loop_ranges(name)
                   if self.instructions(name)[a].addr == addr]
        if len(matches) != 1:
            raise InvalidInput("loop %s matches %d loops; specify --function for ambiguous object addresses" % (loop, len(matches)))
        return matches[0]

    def _symbol_offset(self, target):
        m = re.fullmatch(r"(.*?)([+-]0x[0-9a-fA-F]+)?", target)
        sym, add = m.group(1), int(m.group(2), 16) if m.group(2) else 0
        rec = self.elf.symbols.get(sym)
        if rec is None:
            raise Unsupported("unresolved table symbol %s" % sym)
        if not 0 < rec[0] < len(self.elf.sections):
            raise Unsupported("undefined table symbol %s" % sym)
        if rec[2] and not 0 <= add < rec[2]:
            raise Unsupported("table reference is outside sized symbol %s" % sym)
        return self.elf.sections[rec[0]], rec[1] + add, rec[2] - add if rec[2] else 0

    def jump_table(self, di, name):
        """Resolve contiguous absolute rodata entries; never guess indirect register targets."""
        text = di.text.split("#")[0].strip()
        match = re.fullmatch(r"jmpq?\s+\*(?:0x[0-9a-fA-F]+|[0-9]+)\(,\s*%([a-z0-9]+),\s*8\)", text)
        if not match:
            return None
        rels = [r for r in di.relocs if r[1] in ("R_X86_64_32", "R_X86_64_32S", "R_X86_64_64")]
        if len(rels) != 1:
            raise Unsupported("indirect jump table needs one absolute rodata relocation")
        sec, start, size = self._symbol_offset(rels[0][2])
        if sec.name != ".rodata" and not sec.name.startswith(".rodata."):
            raise Unsupported("jump table is not in rodata")
        if start < 0 or start % 8 or start >= sec.size:
            raise Unsupported("jump table start is outside rodata or unaligned")
        insns = self.instructions(name)
        addresses = {i.addr for i in insns}
        function = self.elf.symbols.get(name)
        if function is None:
            raise Unsupported("jump table needs the function's ELF symbol")
        relocations = {off: (kind, target) for off, kind, target in self.elf.relocations.get(sec.name, [])}
        # An object symbol's size bounds a named table; section symbols have size zero.
        stop = min(sec.size, start + size) if size else sec.size
        if name not in self._tables:
            starts = []
            for instruction in insns:
                if re.match(r"jmpq?\s+\*", instruction.text):
                    for _, kind, target in instruction.relocs:
                        if kind in ("R_X86_64_32", "R_X86_64_32S", "R_X86_64_64"):
                            other, offset, _ = self._symbol_offset(target)
                            starts.append((other.index, offset))
            self._tables[name] = starts
        stop = min([stop] + [offset for section, offset in self._tables[name] if section == sec.index and offset > start])
        targets = []
        for off in range(start, stop, 8):
            if off not in relocations:
                break
            kind, target = relocations[off]
            if kind != "R_X86_64_64":
                raise Unsupported("jump table entry at 0x%x is not R_X86_64_64" % off)
            dest, addr, _ = self._symbol_offset(target)
            if dest.index != function[0] or addr not in addresses:
                # A contiguous table belonging to the next function is not ours.
                if targets:
                    break
                raise Unsupported("jump table target is outside the function or not an instruction")
            targets.append(addr)
        if not targets:
            raise Unsupported("jump table has no resolvable entries")
        return match.group(1), targets

    def instruction_records(self, di, name, included, calls, region=None):
        insns = self.instructions(name)
        lo, hi = insns[0].addr, insns[-1].addr + len(insns[-1].raw)
        prefix = "" if name == included[0] else _label(name)
        def target_label(addr):
            if region is not None and not region[0] <= addr <= region[1]:
                return "__knc_twin_end"
            return _label(name) if region is None and addr == lo else prefix + ".A_%x" % addr
        text = di.text.split("#")[0].strip()
        if not text or text.startswith("(bad)"):
            raise Unsupported("bytes %s do not disassemble" % di.raw.hex())
        table = self.jump_table(di, name)
        if table:
            reg, targets = table
            return [{"op": "jmp_table", "ops": [reg], "targets": [target_label(a) for a in targets]}]
        if layout.is_nop_text(text):
            text = "nop"
        m = _TARGET_RE.match(text)
        tail = False
        if m:
            mnem, taddr, tsym, toff = m.group(1), int(m.group(2), 16), m.group(3), m.group(4)
            kreg = m.group(5)
            rel = [r for r in di.relocs if r[1] in ("R_X86_64_PC32", "R_X86_64_PLT32")]
            callee = re.sub(r"[+-]0x[0-9a-fA-F]+$", "", rel[0][2]) if rel else (tsym.split("@")[0] if not toff else None)
            internal = lo <= taddr < hi and not rel
            if mnem.startswith("call"):
                if internal and callee is None:
                    raise Unsupported("call into the middle of %s" % name)
                callee = callee or tsym
                text = "call %s" % _label(callee)
            elif region is not None or internal:
                text = "%s %s%s" % ("jmp" if mnem == "jmpq" else mnem,
                                       target_label(taddr) if internal else "__knc_twin_end",
                                       (", " + kreg) if kreg else "")
            else:
                callee = callee or tsym
                if mnem not in ("jmp", "jmpq"):
                    raise Unsupported("conditional jump out of %s to %s" % (name, callee))
                if callee in included:
                    text = "jmp %s" % _label(callee)
                else:
                    text, tail = "call %s" % _label(callee), True
                    self.notes.append("0x%x: tail call to %s converted to call plus ret" % (di.addr, callee))
            if callee in NORETURN and callee not in included and callee not in calls:
                calls[callee] = {"model": "noreturn", "source": "declared automatically (noreturn runtime routine)"}
        else:
            text = self._rewrite_operands(di, text)
            if region is not None and text in ("ret", "retq", "rep ret", "repz retq"):
                text = "jmp __knc_twin_end"
        records, _ = asm_mod.parse_gas(text)
        if tail:
            records.append({"op": "ret", "ops": []})
        return records

    def _rewrite_operands(self, di, text):
        text = re.sub(r"\s*<[^>]*>", "", text)
        end = di.addr + len(di.raw)
        for off, rtype, target in di.relocs:
            m = re.match(r"^(.*?)([+-]0x[0-9a-fA-F]+)?$", target)
            sym, add = m.group(1), int(m.group(2), 16) if m.group(2) else 0
            if add >= (1 << 63):
                add -= 1 << 64
            if rtype in ("R_X86_64_PC32", "R_X86_64_GOTPCREL", "R_X86_64_GOTTPOFF", "R_X86_64_GOTPCRELX", "R_X86_64_REX_GOTPCRELX"):
                add += end - off          # displacement is relative to the end of the instruction
                suffix = {"R_X86_64_GOTTPOFF": "@gottpoff", "R_X86_64_PC32": ""}.get(rtype, "@GOTPCREL")
                name, add = self._sym_ref(sym + suffix, add) if suffix else self._sym_ref(sym, add)
                expr = name + ("%+d" % add if add else "")
                text, n = re.subn(r"-?(0x)?[0-9a-fA-F]+\(%rip\)", expr.replace("\\", "\\\\") + "(%rip)", text, count=1)
                if not n:
                    raise Unsupported("0x%x: relocation %s without a rip-relative operand in %r" % (di.addr, rtype, di.text))
            elif rtype in ("R_X86_64_32", "R_X86_64_32S", "R_X86_64_64"):
                name, add = self._sym_ref(sym, add)
                expr = name + ("%+d" % add if add else "")
                if re.search(r"\$-?(0x)?[0-9a-fA-F]+", text):
                    text = re.sub(r"\$-?(0x)?[0-9a-fA-F]+", "$" + expr, text, count=1)
                else:
                    text, n = re.subn(r"(^|[\s,])-?0x[0-9a-fA-F]+(\(|,|$)", lambda mm: mm.group(1) + expr + mm.group(2), text, count=1)
                    if not n:
                        raise Unsupported("0x%x: relocation %s not matched in %r" % (di.addr, rtype, di.text))
            elif rtype == "R_X86_64_TPOFF32":
                expr = sym + "@tpoff" + ("%+d" % add if add else "")
                text, n = re.subn(r"(%fs:)-?(0x)?[0-9a-fA-F]+", lambda mm: mm.group(1) + expr, text, count=1)
                if not n:
                    text = re.sub(r"\$-?(0x)?[0-9a-fA-F]+", "$" + expr, text, count=1)
            else:
                raise Unsupported("0x%x: relocation type %s is not handled" % (di.addr, rtype))
        if not di.relocs:
            # linked file: rip-relative operands become absolute addresses (objdump prints the target in the comment)
            m = re.search(r"(-?0x[0-9a-fA-F]+|-?\d+)?\(%rip\)", text)
            if m:
                disp = int(m.group(1), 0) if m.group(1) else 0
                target = end + disp
                self._load_linked_section(target)
                text = text[:m.start()] + ("0x%x" % target) + text[m.end():]
            for m in re.finditer(r"(?:^|[\s,])(0x[0-9a-fA-F]+)(?=\(,|,|$)", text):
                self._load_linked_section(int(m.group(1), 16))
        return text

    # ---- kernel --------------------------------------------------------------------------------
    def convert(self, func, with_callees=(), calls=None, init_overlay=None, profile=None, loop=None, report=False):
        calls = dict(calls or {})
        selected = None
        if loop is not None:
            func, first, last = self.loop_location(loop, func)
            selected = self.instructions(func)[first:last + 1]
        included = [func] + [c for c in with_callees if c != func]
        records, rows = [], []
        for f in included:
            insns = selected if f == func and selected is not None else self.instructions(f)
            prefix = "" if f == func else _label(f)
            region = (insns[0].addr, insns[-1].addr) if f == func and selected is not None else None
            for di in insns:
                try:
                    recs = self.instruction_records(di, f, included, calls, region)
                    for i, rec in enumerate(recs):
                        rec.pop("source", None)
                        rec["id"] = "%sa%x%s" % (prefix + "_" if prefix else "", di.addr, "_%d" % i if i else "")
                        if i == 0:
                            rec["encoding"] = layout.encoding_of(di.raw, di.text, di.addr)
                            rec["label"] = _label(f) if region is None and di is insns[0] else prefix + ".A_%x" % di.addr
                    classified = from_gcc_s.classify_records(recs, profile)
                    for row in classified:
                        row.update(address=di.addr, text=di.text, function=f)
                    if not report and any(not r["parser"] or not r["isa"] for r in classified):
                        raise Unsupported(classified[0]["reason"])
                    records.extend(recs)
                    rows.extend(classified)
                except TwinError as e:
                    if not report:
                        raise
                    rows.append({"address": di.addr, "function": f, "line": None, "id": "%sa%x" % (prefix + "_" if prefix else "", di.addr),
                                 "text": di.text, "parser": False, "isa": False, "functional": False,
                                 "timing": False if profile else None, "memory": False, "class": None,
                                 "reason": e.status + ": " + e.message})
            if region is not None:
                records.append({"id": "region_end", "op": "nop", "ops": [], "label": "__knc_twin_end"})
                if with_callees:
                    raise InvalidInput("--loop and --with-callee cannot be combined; use costed stubs for region calls")
        # symbols referenced
        syms = {}
        for rec in records:
            for o in rec["ops"]:
                if isinstance(o, dict):
                    for key in ("symbol", "imm_symbol"):
                        s = o.get(key)
                        if s:
                            syms[s] = None
        init = {"registers": {}, "memory": [], "symbols": {}}
        for s in sorted(syms):
            base, _, suffix = s.partition("@")
            if suffix.lower() in ("gottpoff", "tpoff"):
                off = self.tls.setdefault(base, -64 * (len(self.tls) + 1))
                if suffix.lower() == "tpoff":
                    init["symbols"][s] = off
                else:
                    slot = self.got.setdefault(s, self._got_slot(off))
                    init["symbols"][s] = "0x%x" % slot
                continue
            if suffix.lower() == "gotpcrel":
                a = self.symbol_address(base)
                if a is None:
                    self.unresolved.add(base)
                    continue
                init["symbols"][s] = "0x%x" % self.got.setdefault(s, self._got_slot(a))
                continue
            a = self.symbol_address(s)
            if a is None:
                self.unresolved.add(s)
            else:
                init["symbols"][s] = "0x%x" % a
        init["memory"] = self.memory
        live = from_gcc_s.live_in_registers(records)
        for r in live:
            if r != "rsp":
                init["registers"][r] = 0
        summary = from_gcc_s.summarize(rows)
        callees = sorted(set(o for rec in records if rec["op"] == "call" for o in rec["ops"] if isinstance(o, str)) - set(_label(f) for f in included))
        undeclared = [c for c in callees if c not in calls]
        kernel = {"schema": "knc-twin.kernel/1", "name": "%s__%s" % (os.path.splitext(os.path.basename(self.path))[0], func),
                  "description": "function %s from %s (adapter from_binary.py: code layout, calls and returns kept)" % (func, self.path),
                  "entry": "region" if loop is not None else "function", "unit_of_work": {"description": "TODO: define the unit", "count": 1}, "memory_default": 0,
                  "init": init, "calls": calls, "streams": [{"context": 0, "instructions": records}],
                  "provenance": {"adapter": "from_binary.py", "source_file": os.path.abspath(self.path), "source_sha256": sha256_of_file(self.path),
                                 "function": func, "loop": loop, "included_callees": included[1:], "layout": True,
                                 "live_in_registers_placeholders": sorted(init["registers"]), "unresolved_symbols": sorted(self.unresolved),
                                 "undeclared_callees": undeclared, "coverage": summary, "notes": self.notes,
                                 "padding_nops": sum(1 for r in records if r["op"] == "nop" and r.get("encoding")),
                                 "slow_prefix_instructions": sum(1 for r in records if r.get("encoding", {}).get("slow_prefixes"))}}
        if init_overlay:
            from_gcc_s.apply_overlay(kernel, init_overlay)
        if not all(summary["complete"][k] for k in ("parser", "isa", "functional")):
            kernel = None
        return kernel, rows, summary

    def _got_slot(self, value):
        addr = (self.next_data + 63) // 64 * 64
        self.next_data = addr + 64
        self.memory.append({"addr": "0x%x" % addr, "u64": [value & 0xFFFFFFFFFFFFFFFF], "comment": "synthetic GOT slot"})
        return addr


def _label(name):
    return re.sub(r"[^\w.$]", "_", name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--function")
    ap.add_argument("--loop", help="hexadecimal loop-head address or .A_xxxx label")
    ap.add_argument("--innermost", action="store_true", help="list innermost loops and their coverage")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--disassembly")
    ap.add_argument("--objdump")
    ap.add_argument("--with-callee", action="append", default=[])
    ap.add_argument("--calls")
    ap.add_argument("--init")
    ap.add_argument("--profile", default="card-7120-measured")
    ap.add_argument("--out")
    ap.add_argument("--report")
    args = ap.parse_args(argv)
    try:
        conv = Converter(args.file, disassemble(args.file, args.disassembly, args.objdump))
        if args.list:
            for name in conv.order:
                ins = conv.funcs[name]
                print("%-40s 0x%x %d instructions" % (name, conv.starts[name], len(ins)))
            return 0
        if not args.function and not args.loop:
            raise InvalidInput("give --function NAME or --loop ADDR (or --list)")
        if args.loop:
            args.function = conv.loop_location(args.loop, args.function)[0]
        calls = load_json(args.calls, "calls") if args.calls else {}
        overlay = load_json(args.init, "init") if args.init else None
        kernel, rows, summary = conv.convert(args.function, args.with_callee, calls, overlay, load_profile(args.profile),
                                             loop=args.loop, report=bool(args.report or args.innermost))
    except TwinError as e:
        sys.stderr.write("from_binary: %s: %s\n" % (e.status, e.message))
        return 2
    if args.out and kernel is not None:
        dump_json(kernel, args.out)
    loops = conv.loop_report(args.function, rows)
    unsupported = [r for r in rows if not r["functional"]]
    prov = kernel["provenance"] if kernel else {"function": args.function, "loop": args.loop, "notes": conv.notes}
    if args.report:
        dump_json({"summary": summary, "rows": rows, "unsupported": unsupported, "loops": loops, "provenance": prov}, args.report)
    print("%s %s: %d instructions; complete: %s" % (
        "loop" if args.loop else "function", args.loop or args.function, summary["instructions"], summary["complete"]))
    if args.innermost:
        for row in loops:
            print("%s..0x%x: %d instructions; complete: %s" % (row["label"], row["end_address"], row["instruction_count"], row["summary"]["complete"]))
    if prov.get("undeclared_callees"):
        print("callees without a stub (declare them in --calls): %s" % ", ".join(prov["undeclared_callees"]))
    if prov.get("unresolved_symbols"):
        print("symbols to place in --init init.symbols: %s" % ", ".join(prov["unresolved_symbols"]))
    for u in summary["unsupported"]:
        print("unsupported: %s" % u)
    return 0 if kernel is not None else 2


if __name__ == "__main__":
    sys.exit(main())
