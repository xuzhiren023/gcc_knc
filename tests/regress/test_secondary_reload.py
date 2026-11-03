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
            ('rax rbx rcx rdx rsi rdi rbp r8 r9 r10 r11 r12 r13 r14'.split()))
        body = ('leaq 10(%rdi), %r10\n' + live + '\n'
                'movl $1, %r15d\nkmov %r15d, %k1\n'
                'vbroadcastsd (%rsp), %zmm0\n'
                'vpackstorelpd %zmm0, (%rsp){%k1}\n' + live + '\nret\n')
        self.assertEqual(pressure_scan(body), [])
        r15_body = body.replace('(%rsp)', '(%r15)')
        r15_before_setup = r15_body.replace('vbroadcastsd (%r15), %zmm0\n', '').replace(
            'movl $1', 'vbroadcastsd (%r15), %zmm0\nmovl $1')
        self.assertTrue(pressure_scan('leaq (%rsp), %r15\n' + r15_before_setup))
        self.assertEqual(pressure_scan(r15_body.replace(
            'vbroadcastsd', 'leaq (%rsp), %r15\nvbroadcastsd')), [])
        for old, new in (('kmov %r15d, %k1', ''), ('$1', '$3'),
                         ('(%rsp)', '(%r10)'),
                         ('(%rsp)', '(%rbp)'),
                         ('vbroadcastsd (%rsp), %zmm0', 'vmovq %rax, %zmm0'),
                         ('vpackstorelpd %zmm0, (%rsp){%k1}', 'vmovq %zmm0, %rax'),
                         ('%r14', '%r13')):
            with self.subTest(mutation=old):
                self.assertTrue(pressure_scan(body.replace(old, new)))

        pair = body.replace('$1', '$3').replace(
            'vbroadcastsd (%rsp), %zmm0',
            'vloadunpacklpd (%rsp), %zmm0{%k1}')
        self.assertEqual(pressure_scan(pair, live=False, mask_value=3), [])
        for old, new in (('$3', '$1'), ('kmov %r15d, %k1', ''),
                         ('%zmm0{%k1}', '%zmm0')):
            with self.subTest(pair_mutation=old):
                self.assertTrue(pressure_scan(pair.replace(old, new),
                                              live=False, mask_value=3))

        # Mask setup using a live register is wrong even if its value is saved
        # and restored later. Cover subregisters and implicit GPR destinations.
        for write in ('movl $1, %edx', 'movb $1, %al', 'movb $1, %ah',
                      'movw $1, %r14w', 'incq %rax', 'popq %rbx',
                      'xchgq %rax, %r15', 'mulq %r15', 'cqto',
                      'movq %rdi, %rax'):
            with self.subTest(live_write=write):
                errors = pressure_scan(body.replace('movl $1, %r15d',
                                                    write + '\nmovl $1, %r15d'))
                self.assertTrue(any('write to live GPR' in e for e in errors), errors)


if __name__ == '__main__':
    unittest.main()
