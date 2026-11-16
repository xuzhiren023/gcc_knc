"""Minimal ELF64 little-endian reader (sections, symbols, bytes by address).

Enough to take constant data and symbol addresses from a relocatable object or a linked
K1OM/x86-64 ELF file for the binary adapter (scripts/from_binary.py). Standard library only.
"""
import struct

from .errors import InvalidInput

SHT_SYMTAB, SHT_NOBITS, SHT_RELA = 2, 8, 4
SHF_ALLOC, SHF_EXECINSTR, SHF_TLS = 2, 4, 0x400
NUL = bytes(1)


class Section(object):
    __slots__ = ("index", "name", "type", "flags", "addr", "offset", "size", "link", "info", "align", "entsize")


class Elf(object):
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = f.read()
        d = self.data
        if d[:4] != b"\x7fELF" or d[4] != 2 or d[5] != 1:
            raise InvalidInput("%s is not a 64-bit little-endian ELF file" % path)
        self.path = path
        (self.type, self.machine) = struct.unpack_from("<HH", d, 16)
        shoff, = struct.unpack_from("<Q", d, 0x28)
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", d, 0x3A)
        self.sections = []
        for i in range(shnum):
            o = shoff + i * shentsize
            name, typ, flags, addr, off, size, link, info, align, entsize = struct.unpack_from("<IIQQQQIIQQ", d, o)
            s = Section()
            s.index, s.name, s.type, s.flags, s.addr, s.offset, s.size = i, name, typ, flags, addr, off, size
            s.link, s.info, s.align, s.entsize = link, info, align, entsize
            self.sections.append(s)
        strtab = self.sections[shstrndx] if shstrndx < len(self.sections) else None
        for s in self.sections:
            s.name = self._str(strtab, s.name) if strtab is not None else ""
        self.relocatable = self.type == 1
        self.symbols = {}      # name -> (section index, value, size, type)
        symbol_tables = {}
        for s in self.sections:
            if s.type == SHT_SYMTAB:
                st = self.sections[s.link]
                names = []
                for k in range(s.size // 24):
                    nm, info, other, shndx, value, size = struct.unpack_from("<IBBHQQ", d, s.offset + 24 * k)
                    name = self._str(st, nm)
                    typ = info & 0xF
                    if typ == 3 and 0 < shndx < len(self.sections):
                        name = self.sections[shndx].name
                    names.append(name)
                    rec = (shndx, value, size, typ)
                    if name and (name not in self.symbols or (info >> 4) != 0):
                        self.symbols[name] = rec
                symbol_tables[s.index] = names
        # Key by the relocated section, not by the relocation section's spelling.
        self.relocations = {}
        for s in self.sections:
            if s.type != SHT_RELA or not (0 < s.info < len(self.sections)):
                continue
            target = self.sections[s.info]
            if target.name != ".rodata" and not target.name.startswith(".rodata."):
                continue
            names = symbol_tables.get(s.link)
            if names is None or s.entsize != 24 or s.size % 24:
                raise InvalidInput("malformed relocation section %s" % s.name)
            rows = self.relocations.setdefault(target.name, [])
            for off in range(s.offset, s.offset + s.size, 24):
                addr, info, addend = struct.unpack_from("<QQq", d, off)
                index, kind = info >> 32, info & 0xffffffff
                if index >= len(names):
                    raise InvalidInput("bad symbol index in %s" % s.name)
                name = names[index] + ("%s0x%x" % ("+" if addend >= 0 else "-", abs(addend)) if addend else "")
                rows.append((addr, "R_X86_64_64" if kind == 1 else "R_X86_64_%d" % kind, name))

    def _str(self, strtab, off):
        d = self.data
        start = strtab.offset + off
        end = d.index(NUL, start)
        return d[start:end].decode("latin-1")

    def section(self, name):
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def section_bytes(self, s):
        if s.type == SHT_NOBITS:
            return bytes(s.size)
        return self.data[s.offset:s.offset + s.size]

    def read_addr(self, addr, n):
        """Bytes at a virtual address of a linked file (None if no allocated section holds it)."""
        for s in self.sections:
            if s.flags & SHF_ALLOC and s.addr <= addr and addr + n <= s.addr + s.size:
                if s.type == SHT_NOBITS:
                    return bytes(n)
                o = s.offset + (addr - s.addr)
                return self.data[o:o + n]
        return None

    def section_of_addr(self, addr):
        for s in self.sections:
            if s.flags & SHF_ALLOC and s.size and s.addr <= addr < s.addr + s.size:
                return s
        return None

    def function_symbols(self):
        return {n: r for n, r in self.symbols.items() if r[3] == 2}
