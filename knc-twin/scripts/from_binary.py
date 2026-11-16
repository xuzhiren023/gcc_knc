#!/usr/bin/env python3
"""Binary adapter: a K1OM object file or linked ELF -> knc-twin kernel with code layout.

  from_binary.py FILE --function NAME [--disassembly DIS.txt | --objdump TOOL]
                 [--with-callee NAME ...] [--calls CALLS.json] [--init INIT.json]
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
noreturn routines (__assert_fail, abort, ...) are declared automatically. Indirect jumps and
calls are reported as unsupported.

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

    # ---- one function --------------------------------------------------------------------------
    def function_lines(self, name, included, calls):
        if name not in self.funcs:
            raise InvalidInput("function %r not in the disassembly; functions: %s" % (name, ", ".join(self.order[:40])))
        insns = list(self.funcs[name])
        while len(insns) > 1 and layout.is_nop_text(insns[-1].text.split("#")[0]):
            insns.pop()     # padding between this function and the next symbol: never executed
        lo = insns[0].addr
        hi = insns[-1].addr + len(insns[-1].raw)
        targets = set()
        for di in insns:
            m = _TARGET_RE.match(di.text)
            if m and m.group(1).startswith("j"):
                targets.add(int(m.group(2), 16))
        out = []     # (gas text, DInsn or None)
        out.append(("%s:" % _label(name), None))
        for di in insns:
            if di.addr in targets:
                out.append((".A_%x:" % di.addr, None))
            text = di.text.split("#")[0].strip()
            if not text or text.startswith("(bad)"):
                raise Unsupported("0x%x: bytes %s do not disassemble" % (di.addr, di.raw.hex()))
            if layout.is_nop_text(text):
                out.append(("\tnop", di))
                continue
            m = _TARGET_RE.match(text)
            if m:
                mnem, taddr, tsym, toff = m.group(1), int(m.group(2), 16), m.group(3), m.group(4)
                kreg = m.group(5)
                rel = [r for r in di.relocs if r[1] in ("R_X86_64_PC32", "R_X86_64_PLT32")]
                if rel:
                    callee = re.sub(r"[+-]0x[0-9a-fA-F]+$", "", rel[0][2])
                else:
                    callee = tsym.split("@")[0] if not toff else None
                internal = lo <= taddr < hi and not rel
                if mnem.startswith("call"):
                    if internal and callee is None:
                        raise Unsupported("0x%x: call into the middle of %s" % (di.addr, name))
                    callee = callee or tsym
                    if callee not in included and callee not in calls:
                        if callee in NORETURN:
                            calls[callee] = {"model": "noreturn", "source": "declared automatically (noreturn runtime routine)"}
                    out.append(("\tcall %s" % _label(callee), di))
                elif internal:
                    out.append(("\t%s .A_%x%s" % (mnem.rstrip("q") if mnem == "jmpq" else mnem, taddr, (", " + kreg) if kreg else ""), di))
                else:
                    # a jump out of the function: tail call
                    callee = callee or tsym
                    if mnem.rstrip("q") != "jmp":
                        raise Unsupported("0x%x: conditional jump out of %s to %s" % (di.addr, name, callee))
                    if callee in included:
                        out.append(("\tjmp %s" % _label(callee), di))
                    else:
                        if callee in NORETURN and callee not in calls:
                            calls[callee] = {"model": "noreturn", "source": "declared automatically (noreturn runtime routine)"}
                        out.append(("\tcall %s" % _label(callee), di))
                        out.append(("\tret", None))
                        self.notes.append("0x%x: tail call to %s converted to call plus ret" % (di.addr, callee))
                continue
            text = self._rewrite_operands(di, text)
            out.append(("\t" + text, di))
        return out

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
    def convert(self, func, with_callees=(), calls=None, init_overlay=None, profile=None):
        calls = dict(calls or {})
        included = [func] + [c for c in with_callees if c != func]
        lines = []
        for f in included:
            lines.extend(self.function_lines(f, included, calls))
        text = "\n".join(t for t, _ in lines)
        records, notes = asm_mod.parse_gas(text)
        by_line = {i + 1: di for i, (t, di) in enumerate(lines)}
        for rec in records:
            di = by_line.get(rec.get("source"))
            if di is not None:
                rec["encoding"] = layout.encoding_of(di.raw, di.text, di.addr)
                rec["id"] = "a%x" % di.addr
            else:
                rec["id"] = "s%d" % rec["source"]
            rec.pop("source", None)
        ids = set()
        for rec in records:
            while rec["id"] in ids:
                rec["id"] += "_"
            ids.add(rec["id"])
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
        rows = from_gcc_s.classify_records(records, profile)
        summary = from_gcc_s.summarize(rows)
        callees = sorted(set(o for rec in records if rec["op"] == "call" for o in rec["ops"] if isinstance(o, str)) - set(_label(f) for f in included))
        undeclared = [c for c in callees if c not in calls]
        kernel = {"schema": "knc-twin.kernel/1", "name": "%s__%s" % (os.path.splitext(os.path.basename(self.path))[0], func),
                  "description": "function %s from %s (adapter from_binary.py: code layout, calls and returns kept)" % (func, self.path),
                  "entry": "function", "unit_of_work": {"description": "TODO: define the unit", "count": 1}, "memory_default": 0,
                  "init": init, "calls": calls, "streams": [{"context": 0, "instructions": records}],
                  "provenance": {"adapter": "from_binary.py", "source_file": os.path.abspath(self.path), "source_sha256": sha256_of_file(self.path),
                                 "function": func, "included_callees": included[1:], "layout": True,
                                 "live_in_registers_placeholders": sorted(init["registers"]), "unresolved_symbols": sorted(self.unresolved),
                                 "undeclared_callees": undeclared, "coverage": summary, "notes": self.notes,
                                 "padding_nops": sum(1 for r in records if r["op"] == "nop" and r.get("encoding")),
                                 "slow_prefix_instructions": sum(1 for r in records if r.get("encoding", {}).get("slow_prefixes"))}}
        if init_overlay:
            from_gcc_s.apply_overlay(kernel, init_overlay)
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
        if not args.function:
            raise InvalidInput("give --function NAME (or --list)")
        calls = load_json(args.calls, "calls") if args.calls else {}
        overlay = load_json(args.init, "init") if args.init else None
        kernel, rows, summary = conv.convert(args.function, args.with_callee, calls, overlay, load_profile(args.profile))
    except TwinError as e:
        sys.stderr.write("from_binary: %s: %s\n" % (e.status, e.message))
        return 2
    if args.out:
        dump_json(kernel, args.out)
    if args.report:
        dump_json({"summary": summary, "rows": rows, "provenance": kernel["provenance"]}, args.report)
    prov = kernel["provenance"]
    print("function %s: %d instructions, %d padding nops, %d with two-cycle prefixes; complete: %s" % (
        args.function, summary["instructions"], prov["padding_nops"], prov["slow_prefix_instructions"], summary["complete"]))
    if prov["undeclared_callees"]:
        print("callees without a stub (declare them in --calls): %s" % ", ".join(prov["undeclared_callees"]))
    if prov["unresolved_symbols"]:
        print("symbols to place in --init init.symbols: %s" % ", ".join(prov["unresolved_symbols"]))
    for u in summary["unsupported"]:
        print("unsupported: %s" % u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
