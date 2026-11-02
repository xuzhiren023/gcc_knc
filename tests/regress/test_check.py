"""S0-03: green seed and mutations of every acceptance scan."""
import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('knc_check', ROOT / 'tools/check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class Scans(unittest.TestCase):
    def setUp(self):
        self.asm = (ROOT / 'tests/regress/check-green.s').read_text()
        self.source = (ROOT / 'tests/acceptance/m1_affine/loops.c').read_text()
        self.report = '\n'.join('loops.c:%d:1: note: loop vectorized' % line
                                for line in check.loop_lines(self.source).values())

    def scan(self, asm=None, report=None, fast=False):
        return check.scan_t1(self.asm if asm is None else asm,
                             self.report if report is None else report, self.source, fast)

    def test_seed_and_mutations(self):
        self.assertEqual(self.scan(), [])
        for old, new in [('vmulps', 'fmul'), ('vaddpd', 'fadd'),
                         ('%zmm', '%ymm'), ('jne .L32', 'nop')]:
            with self.subTest(mutation=old):
                self.assertTrue(self.scan(self.asm.replace(old, new)))
        self.assertTrue(self.scan(self.asm.replace('fsubs (%rax)', 'vsubps %zmm0, %zmm1, %zmm2')))
        self.assertTrue(self.scan(report=''))
        # A report for the recurrence or one affine cannot stand in for the other.
        self.assertTrue(self.scan(report=self.report.splitlines()[0]))
        self.assertTrue(self.scan(report=self.report.replace('loops.c:', 'driver.c:')))
        # Packed operations outside the loop cannot satisfy the main-loop scan.
        moved = self.asm.replace(' vmulps %zmm0, %zmm1, %zmm2\n', '')
        self.assertTrue(self.scan(moved.replace('.L32:', ' vmulps %zmm0, %zmm1, %zmm2\n.L32:')))
        self.assertTrue(self.scan(self.asm.replace('affine_f64:', 'unrelated:')))

    def test_contraction(self):
        fast = self.asm.replace('vmulps', 'vfmadd213ps').replace('vmulpd', 'vfmadd213pd')
        self.assertEqual(self.scan(fast, fast=True), [])
        self.assertTrue(self.scan(fast.replace('vfmadd213pd', 'vmulpd'), fast=True))
        self.assertTrue(self.scan(fast))

    def test_elf_and_versions(self):
        loader = b'/lib64/ld-linux-k1om.so.2\0'
        data = bytearray(120 + len(loader))
        data[:6] = b'\x7fELF\x02\x01'
        struct.pack_into('<H', data, 18, 181)
        struct.pack_into('<Q', data, 32, 64)
        struct.pack_into('<HH', data, 54, 56, 1)
        struct.pack_into('<IIQQQQQQ', data, 64, 3, 0, 120, 0, 0, len(loader), 0, 0)
        data[120:] = loader
        self.assertEqual(check.scan_elf(data), [])
        wrong = bytearray(data)
        struct.pack_into('<H', wrong, 18, 62)
        self.assertTrue(check.scan_elf(wrong))
        self.assertTrue(check.scan_elf(data.replace(b'k1om', b'x866')))
        self.assertTrue(check.scan_elf(b'not ELF'))
        required = check.versioned_symbols('  1: 000000 0 FUNC GLOBAL DEFAULT UND printf@GLIBC_2.0 (2)', True)
        provided = check.versioned_symbols('  2: 000100 0 FUNC GLOBAL DEFAULT 12 printf@@GLIBC_2.0', False)
        self.assertEqual(required - provided, set())
        newer = check.versioned_symbols('  1: 000000 0 FUNC GLOBAL DEFAULT UND printf@GLIBC_99.0 (2)', True)
        self.assertTrue(newer - provided)


class Runner(unittest.TestCase):
    def test_runners_use_distinct_temporary_output_directories(self):
        args = SimpleNamespace(compiler='donor', cc=None)
        first, second = check.Runner(args), check.Runner(args)
        for runner in (first, second):
            if hasattr(runner, '_output'):
                self.addCleanup(runner._output.cleanup)
            self.assertNotEqual(runner.out, check.PROJECT / '.work/_shared/check/donor')
        self.assertNotEqual(first.out, second.out)

    def test_link_trace_resolves_parenthesized_sysroot_paths(self):
        runner = check.Runner.__new__(check.Runner)
        runner.sysroot = Path('/shared/sysroot')
        runner.out = Path('/shared/check')
        runner.cc = Path('/shared/gcc')
        runner.flags = []
        runner.fixture = Path('/fixture')
        runner.off_object = Path('/shared/check/loops.o')
        runner.say = Mock()
        runner.result = Mock()
        runner.tool = Mock(return_value='readelf')
        for provider in ('/shared/sysroot', '/outside'):
            with self.subTest(provider=provider):
                trace = '\n'.join('/lib64/%s (%s/lib64/%s)' % (name, provider, name)
                                  for name in ('libc.so.6', 'ld-linux-k1om.so.2'))
                runner.command = Mock(side_effect=lambda *args: trace if '-Wl,--trace' in args else '')
                with patch.object(Path, 'read_bytes', return_value=b''), patch.object(check, 'scan_elf', return_value=[]):
                    if provider == '/outside':
                        with self.assertRaisesRegex(RuntimeError, 'outside shared sysroot'):
                            runner.t2()
                    else:
                        runner.t2()
                        self.assertTrue(any('/shared/sysroot/lib64/libc.so.6' in call.args[0]
                                            for call in runner.say.call_args_list))

    def test_only_t0_can_cache_project_inputs(self):
        for tiers in (['t0'], ['t1'], ['t2'], ['t0', 't1', 't2']):
            with self.subTest(tiers=tiers), patch.object(check, 'os', SimpleNamespace(name='posix')), \
                    patch.object(check.sys, 'argv', ['tools/check', *tiers]), \
                    patch.object(check.subprocess, 'call', return_value=0) as call:
                self.assertEqual(check.main(), 0)
                self.assertEqual('--inputs' in call.call_args.args[0], tiers == ['t0'])


if __name__ == '__main__':
    unittest.main()
