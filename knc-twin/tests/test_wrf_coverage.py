"""S14-11 red cases from brief 01: relocated switches and YMM conversions.

The switch is a reduced listing using the WRF relocation form recorded in the
brief. Its case bodies and data are synthetic; no WRF object is required.
"""
import struct
import json
import tempfile
from pathlib import Path
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
    def test_named_table_addend_stays_within_symbol_size(self):
        elf = SwitchElf()
        elf.symbols["table"] = (2, 0x80, 0x10, 1)
        listing = SWITCH.replace(".rodata+0x88", "table+0x8")
        with patch.object(from_binary, "Elf", return_value=elf):
            conv = from_binary.Converter(__file__, listing)
        raw, _, _ = conv.convert("switch_case")
        jump = raw["streams"][0]["instructions"][0]
        self.assertEqual(len(jump["targets"]), 1)
        raw["init"]["registers"]["rdx"] = 1
        with self.assertRaises(InvalidInput):
            functional.run_functional(Kernel(raw, None))

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
                raw["expected"] = {"registers": {"0": {"rax": expected}}}
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
                k = kernel(None, expected={"registers": {"0": {name: {"u64": expected}}}}, init={"registers": {
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


LOOP = """Disassembly of section .text:
0000000000000000 <loop_case>:
   0:\tb8 00 00 00 00 \tmov $0,%eax
   5:\t83 c0 01 \tadd $1,%eax
   8:\t39 c8 \tcmp %ecx,%eax
   a:\t74 05 \tje 11 <loop_case+0x11>
   c:\t39 d0 \tcmp %edx,%eax
   e:\t7c f5 \tjl 5 <loop_case+0x5>
  10:\t90 \tnop
  11:\tc3 \tretq
"""


class TestWrfRegions(unittest.TestCase):
    def converter(self, text=LOOP):
        with patch.object(from_binary, "Elf", return_value=SwitchElf()):
            return from_binary.Converter(__file__, text)

    def test_loop_exits_and_fallthrough_and_live_ins(self):
        conv = self.converter()
        for head in ("5", "0x5", ".A_5"):
            raw, rows, summary = conv.convert(None, loop=head, report=True)
            self.assertEqual(raw["entry"], "region")
            self.assertEqual(len(rows), 5)
            self.assertEqual(set(raw["provenance"]["live_in_registers_placeholders"]), {"rax", "rcx", "rdx"})
            for limit, stop, expected in ((5, 3, 3), (2, 9, 2)):
                raw["init"]["registers"].update(rax=0, rcx=stop, rdx=limit)
                raw["expected"] = {"registers": {"0": {"rax": expected}}}
                _, _, check = functional.run_functional(Kernel(raw, None))
                self.assertEqual(check["status"], "ok", check)
        _, rows, _ = conv.convert("loop_case", report=True)
        loops = conv.loop_report("loop_case", rows)
        self.assertEqual([(r["address"], r["end_address"], r["instruction_count"]) for r in loops], [(5, 14, 5)])

    def test_complete_listing_keeps_all_errors_and_never_writes_partial_kernel(self):
        text = LOOP.replace("add $1,%eax", "unrecognized %eax").replace("cmp %edx,%eax", "jmpq *%rax")
        conv = self.converter(text)
        raw, rows, summary = conv.convert("loop_case", report=True)
        self.assertIsNone(raw)
        self.assertEqual(len(rows), 8)
        self.assertEqual([r["address"] for r in rows if not r["functional"]], [5, 12])
        loops = conv.loop_report("loop_case", rows)
        self.assertFalse(loops[0]["summary"]["complete"]["functional"])
        with tempfile.TemporaryDirectory() as tmp:
            out, report = str(Path(tmp) / "kernel.json"), str(Path(tmp) / "report.json")
            with patch.object(from_binary, "Converter", return_value=self.converter(text)), patch.object(from_binary, "disassemble", return_value=text):
                code = from_binary.main([__file__, "--function", "loop_case", "--report", report, "--out", out])
            self.assertEqual(code, 2)
            self.assertFalse(Path(out).exists())
            saved = json.loads(Path(report).read_text())
            self.assertEqual([r["address"] for r in saved["unsupported"]], [5, 12])

    def test_switch_targets_outside_selected_region_exit(self):
        text = SWITCH.replace("retq", "jmp 0 <switch_case>", 1)
        conv = self.converter(text)
        raw, _, _ = conv.convert("switch_case", loop="0")
        self.assertEqual(raw["entry"], "region")
        raw["init"]["registers"]["rdx"] = 0  # case at d is outside the selected backedge at c
        raw["expected"] = {"registers": {"0": {"rax": 0}}}
        _, _, check = functional.run_functional(Kernel(raw, None))
        self.assertEqual(check["status"], "ok", check)


if __name__ == "__main__":
    unittest.main()
