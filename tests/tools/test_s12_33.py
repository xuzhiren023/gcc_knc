"""Regression test for isolated S12-33 short-vector cross-link outputs."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / 'tools'))
SCALAR_ABI = ROOT / 'tools/scalar_abi.py'
spec = importlib.util.spec_from_file_location('scalar_abi', SCALAR_ABI)
scalar_abi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scalar_abi)


class OutputIsolation(unittest.TestCase):
    def test_short_vector_uses_runner_temporary_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_output = root / 'toolchain' / 'S5-21'
            old_output.mkdir(parents=True)
            blocked = old_output / 'short-vector-O2-0.mic'
            blocked.write_bytes(b'from another run')
            blocked.chmod(0o444)
            runner = type('Runner', (), {
                'root': root,
                'out': root / 'run-output',
                'args': type('Args', (), {'compiler': 'gcc16'})(),
                'source_dir': root / 'tests' / 't1',
                'cc': 'cc',
                'cc_flags': [],
                'sysroot': root / 'sysroot',
            })()
            runner.out.mkdir()
            runner.command = lambda *args, **kwargs: type(
                'Result', (), {'returncode': 1, 'stdout': ''})()
            runner.function_body = lambda *args: ''
            runner.t2_abi = lambda *args: None
            runner.result = lambda label, failures: None
            with mock.patch.object(scalar_abi, 't2_crosscheck') as crosscheck:
                scalar_abi.t2_short_vector(runner)
            output = runner.out / 'short-vector-cross'
            self.assertEqual(crosscheck.call_count, 2)
            for call in crosscheck.call_args_list:
                self.assertEqual(call.args[4], output)
            self.assertEqual(output.parent, runner.out)
            self.assertEqual(blocked.read_bytes(), b'from another run')


if __name__ == '__main__':
    unittest.main()
