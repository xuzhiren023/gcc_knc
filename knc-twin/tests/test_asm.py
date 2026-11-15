"""GAS AT&T subset parser: accepted forms and rejections."""
import unittest

import helpers  # noqa: F401
from knc_model import asm
from knc_model.errors import InvalidInput, Unsupported
from knc_model.kernel import load_kernel


class TestAsm(unittest.TestCase):
    def test_operand_forms(self):
        recs, notes = asm.parse_gas("""
            .text
        L:  vmovaps 64(%rax,%rcx,4), %zmm0          # load
            vfmadd231ps (%rbx){1to16}, %zmm2, %zmm1{%k1}
            vaddps %zmm3, %zmm4, %zmm5{rd}
            addq $16, %rcx
            movl $0x10, %edx
            kmov %k1, %k2
            vprefetch1 128(%rax)
            jnz L
        """)
        self.assertEqual(len(recs), 8)
        self.assertEqual(recs[0]["op"], "vmovaps")
        self.assertEqual(recs[0]["ops"], ["zmm0", {"disp": 64, "base": "rax", "index": "rcx", "scale": 4}])
        self.assertEqual(recs[0]["label"], "L")
        self.assertEqual(recs[1]["ops"][2], {"base": "rbx", "broadcast": "1to16"})
        self.assertEqual(recs[1]["mask"], "k1")
        self.assertEqual(recs[2]["rounding"], "rd")
        self.assertEqual(recs[3]["op"], "add")
        self.assertEqual(recs[3]["width"], 64)
        self.assertEqual(recs[3]["ops"], ["rcx", {"imm": 16}])
        self.assertEqual(recs[4]["width"], 32)
        self.assertEqual(recs[7]["ops"], ["L"])
        self.assertTrue(any("directive ignored" in n for n in notes))

    def test_rejections(self):
        with self.assertRaises(Unsupported):
            asm.parse_gas("vaddps %zmm1{sint32}, %zmm2, %zmm3")
        recs, _ = asm.parse_gas("vaddps %zmm1{cdab}, %zmm2, %zmm3")
        self.assertEqual(recs[0]["ops"], ["zmm3", "zmm2", {"reg": "zmm1", "swizzle": "cdab"}])
        recs, _ = asm.parse_gas("movw $1, %ax")
        self.assertEqual((recs[0]["op"], recs[0]["width"]), ("mov", 16))
        with self.assertRaises(Unsupported):
            asm.parse_gas(".byte 0x90")
        recs, notes = asm.parse_gas("L1:\nL2:\n addq $1, %rax\n jne L2")
        self.assertEqual(recs[0]["label"], "L1")
        self.assertEqual(recs[1]["ops"], ["L1"], "an alias label is redirected to the kept label")
        recs, _ = asm.parse_gas("1:\n addq $1, %rax\n jne 1b\n2:\n decq %rdx\n jne 2b")
        self.assertEqual(recs[0]["label"], "L1_1")
        self.assertEqual(recs[1]["ops"], ["L1_1"])
        self.assertEqual(recs[3]["ops"], ["L2_1"])
        with self.assertRaises(InvalidInput):
            asm.parse_gas(" jne 3b")

    def test_asm_fixture_matches_records(self):
        a = load_kernel(helpers.fixture("saxpy_asm.json"))
        b = load_kernel(helpers.fixture("saxpy_loop.json"))
        self.assertEqual(a.representation, "gas-att-subset")
        self.assertEqual([i.short() for i in a.streams[0].insns], [i.short() for i in b.streams[0].insns])

    def test_emit_round_trip(self):
        k = load_kernel(helpers.fixture("saxpy_loop.json"))
        text = asm.emit_gas(k.streams[0])
        recs, _ = asm.parse_gas(text)
        self.assertEqual([r["op"] for r in recs], [i.op for i in k.streams[0].insns])


if __name__ == "__main__":
    unittest.main()
