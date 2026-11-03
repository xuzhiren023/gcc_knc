"""Mutation checks for S2-04's address-loss and transfer scans."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from secondary_reload import lost_addresses, pressure_scan


class SecondaryReload(unittest.TestCase):
    def test_deleted_store_address_copy(self):
        trace = ('Creating newreg=2608 from oldreg=758 to address r2608\n'
                 'Deleting move 2063\n')
        self.assertEqual(lost_addresses(trace),
                         ['deleted move 2063 lost address r2608 <- r758'])
        self.assertEqual(lost_addresses(trace + 'r2608:DI=r758:DI\n'), [])
        self.assertTrue(lost_addresses(trace + 'r2608:SI=r758:DI\n'))
        self.assertEqual(lost_addresses('Deleting move 2063\n'), [])

    def test_pressure_mask_address_and_memory_bridge(self):
        live = '# pressure-live ' + ' '.join('%' + r for r in
            ('rax rbx rcx rdx rsi rdi rbp r8 r9 r10 r11 r12 r13 r14 r15'.split()))
        body = ('movq %rdi, %rax\n' + live + '\n'
                'movl $1, %edx\nkmov %edx, %k1\n'
                'vbroadcastsd (%rax), %zmm0\n'
                'vpackstorelpd %zmm0, (%rax){%k1}\n' + live + '\nret\n')
        self.assertEqual(pressure_scan(body), [])
        for old, new in (('kmov %edx, %k1', ''), ('$1', '$3'),
                         ('(%rax)', '(%r10)'),
                         ('vbroadcastsd (%rax), %zmm0', 'vmovq %rax, %zmm0'),
                         ('vpackstorelpd %zmm0, (%rax){%k1}', 'vmovq %zmm0, %rax'),
                         ('%r15', '%r14')):
            with self.subTest(mutation=old):
                self.assertTrue(pressure_scan(body.replace(old, new)))


if __name__ == '__main__':
    unittest.main()
