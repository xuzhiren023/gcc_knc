"""S2-16: prepared card programs must be readable by the lead."""
import ast
from pathlib import Path
import re
import shlex
import stat
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BatchPermissions(unittest.TestCase):
    def test_linked_torture_program_is_0755(self):
        # Exercise the actual nested build function without rebuilding GCC or
        # accessing the card. The compiler stand-in only creates its -o file.
        script = ROOT / 'tools/prepare_s2_08.py'
        tree = ast.parse(script.read_text())
        main = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'main')
        build = next(node for node in main.body
                     if isinstance(node, ast.FunctionDef) and node.name == 'build')
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            source = out / 'sample.c'
            source.write_text('int main(void) { return 0; }\n')

            def bounded(args):
                Path(args[args.index('-o') + 1]).write_bytes(b'linked program')
                return 0, ''

            namespace = dict(OUT=out, cc=['compiler'], bounded=bounded,
                             re=re, shlex=shlex)
            exec(compile(ast.Module(body=[build], type_ignores=[]),
                         str(script), 'exec'), namespace)
            _, state, program, _ = namespace['build'](source)
            self.assertEqual(state, 'linked')
            self.assertEqual(stat.S_IMODE((out / program).stat().st_mode),
                             0o755, 'card programs must be readable by the lead')


if __name__ == '__main__':
    unittest.main()
