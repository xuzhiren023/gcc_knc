"""S12-01: counters use synthetic AT&T objdump text, never corpus sources."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import code_census as census


class CensusTest(unittest.TestCase):
    def test_counters_and_loop(self):
        text = '''0000000000000100 <kernel>:
 100: 53                   push %rbx
 101: 48 89 44 24 08       mov %rax,0x8(%rsp)
 106: 48 8b 44 24 08       mov 0x8(%rsp),%rax
 10b: db 7c 24 10          fstpt 0x10(%rsp)
 10f: 62 01 02 03          vmovapd 0x10(%rsp),%zmm0
 113: 62 01 02 03          vmovapd %zmm1,0x20(%rsp)
 117: dd 44 24 20          fldl 0x20(%rsp)
 11b: c5 01 02             kmov %k1,0x30(%rsp)
 11e: c5 01 02             kmov 0x30(%rsp),%k2
 121: d9 c9                fxch %st(1)
 123: 48 8d 04 40          lea (%rax,%rax,2),%rax
 127: 48 63 c0             movslq %eax,%rax
 12a: 48 6b c0 03          imul $3,%rax,%rax
 12e: e8 00 00 00 00       callq 200 <helper>
 133: 75 ee                jne 123 <kernel+0x23>
 135: 5b                   pop %rbx
 136: c3                   retq
0000000000000200 <helper>:
 200: c3                   retq
'''
        result = census.parse_disassembly(text)
        f = result['functions'][0]
        c = f['counts']
        self.assertEqual(f['name'], 'kernel')
        self.assertEqual(c['instructions'], 17)
        self.assertEqual(c['bytes'], 55)
        for cls in ('gpr', 'x87', 'zmm', 'k'):
            self.assertEqual(c['stack_store_' + cls], 1)
            self.assertEqual(c['stack_load_' + cls], 1)
        for key, expected in dict(x87_memory=2, fxch=1, transfer_candidates=2,
                                  calls=1, callee_save=1, callee_restore=1,
                                  branches=1, backward_branches=1, vector=2,
                                  address=3, unknown=0).items():
            self.assertEqual(c[key], expected, key)
        self.assertEqual(f['loops'][0]['counts']['address'], 3)
        self.assertEqual(f['loops'][0]['start'], 0x123)

    def test_memory_is_not_automatically_a_spill_or_transfer(self):
        f = census.parse_disassembly('''0000 <f>:
 0: dd 00        fldl (%rax)
 2: dd 18        fstpl (%rax)
 4: 48 8d 44 24 08 lea 8(%rsp),%rax
 9: 48 89 44 24 08 mov %rax,8(%rsp)
 e: 48 89 54 24 08 mov %rdx,8(%rsp)
 13: 62 01 02 03 vmovapd 8(%rsp),%zmm0
 17: 0f 85 00 00 00 00 jne 99 <elsewhere>
''')['functions'][0]['counts']
        self.assertEqual(f['x87_memory'], 2)
        self.assertEqual(f['stack_load_gpr'], 0)
        self.assertEqual(f['transfer_candidates'], 0)
        self.assertEqual(f['backward_branches'], 0)

    def test_held_out_refused_before_disassembly(self):
        for name in ('PB-adi', 'adi', 'PolyBench adi', 'PB-durbin', 'durbin', 'bzip2'):
            with self.subTest(name=name), patch.object(census.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    census.disassemble(name, Path('unused'), 'objdump')
                run.assert_not_called()
        with self.assertRaises(ValueError):
            census.select_builds([dict(program='PB-adi', held_out=False)])

    def test_primary_selection_excludes_optional_panels(self):
        rows = [dict(program='STREAM', compiler='gcc-knc', check='pass',
                     panel='primary', requested_flags=['-O2'], variant='serial',
                     held_out=False, files=['workload'])]
        self.assertEqual(census.select_builds(rows, require_complete=False), rows)
        with self.assertRaises(ValueError):
            census.select_builds(rows)


if __name__ == '__main__':
    unittest.main()
