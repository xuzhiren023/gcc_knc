"""S14-11 red cases from brief 01: relocated switches and YMM conversions.

The switch is a reduced listing using the WRF relocation form recorded in the
brief. Its case bodies and data are synthetic; no WRF object is required.
"""
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from helpers import kernel
import from_binary
from knc_model import functional
from knc_model.elf import Elf
from knc_model.errors import InvalidInput, Unsupported
from knc_model.kernel import Kernel, Reg


SWITCH = """Disassembly of section .text:
0000000000000000 <switch_case>:
   0:\tff 24 d5 00 00 00 00 \tjmpq *0x0(,%rdx,8)
            3: R_X86_64_32S .rodata+0x88
   7:\tb8 0b 00 00 00 \tmov $0xb,%eax
   c:\tc3 \tretq
   d:\tb8 16 00 00 00 \tmov $0x16,%eax
  12:\tc3 \tretq
"""


class SwitchElf(Elf):
    """ELF-like section/symbol/relocation fixture, without an on-disk object.

    Relocations use the listing reader's (offset, type, target) triples,
    grouped by the relocated section. The table starts after unrelated data
    and deliberately selects case bodies in reverse address order.
    """

    def __init__(self):
        self.relocatable = True
        self.sections = [
            SimpleNamespace(index=0, name="", flags=0, size=0),
            SimpleNamespace(index=1, name=".text", flags=6, size=0x13),
            SimpleNamespace(index=2, name=".rodata", flags=2, size=0x98,
                            align=8, addr=0),
        ]
        self.symbols = {".text": (1, 0, 0, 3), ".rodata": (2, 0, 0, 3),
                        "switch_case": (1, 0, 0x13, 2)}
        self.relocations = {".rodata": [
            (0x88, "R_X86_64_64", ".text+0xd"),
            (0x90, "R_X86_64_64", ".text+0x7"),
        ]}

    def section_bytes(self, section):
        return bytes(section.size)


class TestWrfSwitch(unittest.TestCase):
    def converted(self):
        with patch.object(from_binary, "Elf", return_value=SwitchElf()):
            converter = from_binary.Converter(__file__, SWITCH)
        raw, rows, summary = converter.convert("switch_case")
        self.assertTrue(summary["complete"]["functional"], summary)
        jumps = [r for r in raw["streams"][0]["instructions"]
                 if r["op"] == "jmp_table"]
        self.assertEqual(len(jumps), 1)
        self.assertEqual(jumps[0]["encoding"]["bytes"], 7)
        return raw

    def test_relocated_table_preserves_entry_order(self):
        raw = self.converted()
        for index, expected in ((0, 22), (1, 11)):
            with self.subTest(index=index):
                raw["init"]["registers"]["rdx"] = index
                interp, _, check = functional.run_functional(Kernel(raw, None))
                self.assertEqual(check["status"], "ok", check)
                self.assertEqual(interp.contexts[0].gpr["rax"], expected)

    def test_table_index_outside_entries_is_invalid_input(self):
        raw = self.converted()
        for index in (2, 0xffffffffffffffff):
            with self.subTest(index=index):
                raw["init"]["registers"]["rdx"] = index
                with self.assertRaises(InvalidInput):
                    functional.run_functional(Kernel(raw, None))


class TestWrfYmmConversion(unittest.TestCase):
    def test_ymm_registers_alias_zmm_at_width_256(self):
        for number in range(32):
            with self.subTest(number=number):
                reg = Reg("ymm%d" % number)
                self.assertEqual((reg.kind, reg.base, reg.width),
                                 ("v", "zmm%d" % number, 256))

    def test_conversion_reads_low_eight_lanes_even_with_aliasing(self):
        values = [0.0, -0.0, 1.0, -2.0, 0.5, 16.0, 1.5, -32.0]
        bits = [struct.unpack("<I", struct.pack("<f", x))[0] for x in values]
        expected = [struct.unpack("<Q", struct.pack("<d", x))[0] for x in values]
        for number in (0, 31):
            with self.subTest(number=number):
                name = "zmm%d" % number
                k = kernel(None, init={"registers": {
                    name: {"u32": bits + [0x7fc00000] * 8}}},
                    streams=[{"context": 0, "asm":
                              "vcvtps2pd %%ymm%d,%%%s" % (number, name)}])
                interp, _, check = functional.run_functional(k)
                self.assertEqual(check["status"], "ok", check)
                lanes = interp.contexts[0].zmm[name]
                self.assertEqual([lanes[i] | (lanes[i + 1] << 32)
                                  for i in range(0, 16, 2)], expected)

    def test_ymm_rejected_outside_conversion_source(self):
        for text in ("vaddps %ymm0,%zmm1,%zmm2",
                     "vmovaps %ymm0,%ymm1", "vcvtps2pd %ymm0,%ymm1"):
            with self.subTest(text=text):
                with self.assertRaisesRegex((InvalidInput, Unsupported), "ymm"):
                    k = kernel(None, streams=[{"context": 0, "asm": text}])
                    functional.run_functional(k)


if __name__ == "__main__":
    unittest.main()
