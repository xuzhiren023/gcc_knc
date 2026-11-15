"""Regression test for isolated S12-33 short-vector cross-link outputs."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

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
            })()
            runner.out.mkdir()
            calls = []
            runner.command = lambda *args, **kwargs: calls.append(args) or type(
                'Result', (), {'returncode': 0, 'stdout': ''})()
            runner.function_body = lambda *args: ''
            runner.tool = lambda name: name
            runner.result = lambda label, failures: calls.append((label, failures))
            scalar_abi.t2_short_vector(runner)
            output = runner.out / 'short-vector-cross'
            self.assertEqual(sorted(path.name for path in output.iterdir()), [
                'vector-O2-0.mic', 'vector-O2-1.mic'])
            self.assertEqual(blocked.read_bytes(), b'from another run')
            self.assertTrue(calls)


if __name__ == '__main__':
    unittest.main()
