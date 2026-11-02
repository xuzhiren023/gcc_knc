"""S0-02 T0: seeded forbidden ISA, donor output, and input containers."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
TC = PROJECT / '.work/_shared/toolchain'
ENV = os.environ.copy()
ENV['PATH'] = os.pathsep.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + ENV.get('PATH', '')


class Lint(unittest.TestCase):
    def run_command(self, *args):
        return subprocess.run([str(a) for a in args], env=ENV, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def lint(self, path):
        return self.run_command(sys.executable, ROOT / 'tools/knc_lint', path)

    def test_seeded_rules(self):
        for source in sorted((ROOT / 'tests/isa').glob('*.s')):
            with self.subTest(source=source.name):
                result = self.lint(source)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(str(source), result.stdout)
                self.assertIn('seed', result.stdout)
                self.assertRegex(result.stdout, r':(?:0x[0-9a-f]+|line-\d+):')
                self.assertIn('forbidden', result.stdout)

    def test_encoded_rules(self):
        encodings = {
            'xmm': '0f 28 c8', 'ymm': 'c5 fc 28 c8', 'mmx': '0f 6f c8',
            'emms': '0f 77', 'femms': '0f 0e', 'cmov': '48 0f 44 d8',
            'fcmov': 'da c1', 'fcomi': 'db f1', 'fcomip': 'df f1',
            'fucomi': 'db e9', 'fucomip': 'df e9', 'cmpxchg16b': '48 0f c7 08',
            'pause': 'f3 90', 'rep_nop': 'f3 90', 'mfence': '0f ae f0',
            'lfence': '0f ae e8', 'sfence': '0f ae f8', 'monitor': '0f 01 c8',
            'mwait': '0f 01 c9', 'sysenter': '0f 34', 'sysexit': '0f 35',
            'bad': '0f ff', 'rex_pause': 'f3 40 90', 'rex_w_pause': 'f3 48 90',
        }
        with tempfile.TemporaryDirectory() as temp:
            source, obj = Path(temp) / 'encoded.s', Path(temp) / 'encoded.o'
            for rule, encoding in encodings.items():
                with self.subTest(rule=rule):
                    source.write_text('.text\n.globl seed\nseed:\n.byte ' +
                                      ','.join('0x' + b for b in encoding.split()) + '\nret\n')
                    result = self.run_command(TC / 'cross/bin/k1om-mpss-linux-as.exe',
                                              '-march=k1om', source, '-o', obj)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    result = self.lint(obj)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn(str(obj) + ':seed:0x0: forbidden:', result.stdout)

    def test_symbol_names_and_strings(self):
        with tempfile.TemporaryDirectory() as temp:
            source, obj, linked = (Path(temp) / n for n in ('names.s', 'names.o', 'names.elf'))
            source.write_text('.text\n.globl seed\nseed:\nmovl mm1(%rip),%eax\n'
                              'call xmm0\nret\nxmm0:\nret\n.data\nmm1:\n.long 0\n'
                              '.string "wait; pause; xmm0 cmove"\n'
                              '.string "escaped \\"; pause; # xmm0"\n')
            result = self.lint(source)
            self.assertEqual(result.returncode, 0, result.stdout)
            result = self.run_command(TC / 'cross/bin/k1om-mpss-linux-as.exe',
                                      '-march=k1om', source, '-o', obj)
            self.assertEqual(result.returncode, 0, result.stdout)
            result = self.run_command(TC / 'cross/bin/k1om-mpss-linux-ld.exe',
                                      '-m', 'elf_k1om', '-e', 'seed', obj, '-o', linked)
            self.assertEqual(result.returncode, 0, result.stdout)
            result = self.lint(linked)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_donor_loops_and_containers(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            gcc = TC / 'cross/bin/k1om-mpss-linux-gcc.exe'
            source = ROOT / 'tests/acceptance/m1_affine/loops.c'
            asm, obj = temp / 'loops.s', temp / 'loops.o'
            for mode, output in (('-S', asm), ('-c', obj)):
                result = self.run_command(gcc, '-O2', mode, source, '-o', output)
                self.assertEqual(result.returncode, 0, result.stdout)
            archive, shared, executable = (temp / n for n in ('loops.a', 'loops.so', 'loops.elf'))
            for command in (
                (TC / 'cross/bin/k1om-mpss-linux-ar.exe', 'rcs', archive, obj),
                (TC / 'cross/bin/k1om-mpss-linux-ld.exe', '-m', 'elf_k1om', '-shared', obj, '-o', shared),
                (TC / 'cross/bin/k1om-mpss-linux-ld.exe', '-m', 'elf_k1om', '-e', 'affine_f32', obj, '-o', executable),
            ):
                result = self.run_command(*command)
                self.assertEqual(result.returncode, 0, result.stdout)
            for path in (asm, obj, archive, shared, executable):
                with self.subTest(path=path.name):
                    result = self.lint(path)
                    self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == '__main__':
    unittest.main()
