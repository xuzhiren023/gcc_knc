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

    def test_pause_in_object(self):
        with tempfile.TemporaryDirectory() as temp:
            obj = Path(temp) / 'pause.o'
            result = self.run_command(TC / 'cross/bin/k1om-mpss-linux-as.exe',
                                      '-march=k1om', ROOT / 'tests/isa/pause.s', '-o', obj)
            self.assertEqual(result.returncode, 0, result.stdout)
            result = self.lint(obj)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn('seed:0x0:', result.stdout)
            self.assertRegex(result.stdout, r'forbidden: (?:pause|repz\s+nop)')

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
