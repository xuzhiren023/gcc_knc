"""S3-16: probe outputs stay in the main checkout's shared area."""
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))


class SharedOutputTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / 'main'
        self.root.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)

    def load(self, relative):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((ROOT / relative).read_text())
        return runpy.run_path(str(target))

    def assert_shared_outputs(self, before, expected):
        shared = self.root / '.work' / '_shared'
        for path in set(self.base.rglob('*')) - before:
            self.assertTrue(path == shared or shared in path.parents or path in shared.parents,
                            'output escaped repository shared area: ' + str(path))
        self.assertTrue((shared / expected).exists(), 'probe did not create its output')

    def test_torture_compile_from_main_checkout(self):
        module = self.load('tests/tools/test_torture_compile.py')
        before = set(self.base.rglob('*'))

        def compile_probe(command, **kwargs):
            output = Path(command[command.index('--output') + 1])
            output.mkdir(parents=True, exist_ok=True)
            Path(command[command.index('--summary') + 1]).write_text(
                'O0\t1\t0\t0\t0\t0\t0\t0\t0\t0\t0')

        with mock.patch('subprocess.run', side_effect=compile_probe):
            module['TortureOptionsTest']('test_both_option_directives').test_both_option_directives()
        self.assert_shared_outputs(before, 'torture-options.txt')

    def test_torture_driver_from_main_checkout(self):
        # Importing the POSIX driver suite must also work in a Windows T0 run.
        with mock.patch.dict(sys.modules, {'resource': mock.Mock()}):
            module = self.load('tests/tools/test_torture_driver.py')
        before = set(self.base.rglob('*'))

        def compile_fixture(command, **kwargs):
            Path(command[command.index('-o') + 1]).write_text('fixture')

        with mock.patch('subprocess.run', side_effect=compile_fixture):
            module['TortureDriverTest'].setUpClass()
        self.assert_shared_outputs(before, 'S2-18-driver/driver.exe')

    def test_x87_probe_from_main_checkout(self):
        module = self.load('tools/x87_spill.py')
        before = set(self.base.rglob('*'))
        runner = SimpleNamespace(
            root=self.root, source_dir=self.root / 'tests/t1', cc='gcc16', cc_flags=[],
            tool=lambda name: name,
            command=lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout='stub compiler'),
            result=lambda *args: None)
        module['t1'](runner)
        self.assert_shared_outputs(before, 'tmp/S2-05')


if __name__ == '__main__':
    unittest.main()
