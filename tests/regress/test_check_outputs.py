"""S12-37: fake T1/T2 file operations must stay inside the run directory.

The fake compiler supplies empty assembly, not ISA/ABI evidence. Semantic
scan results are collected separately; infrastructure errors still fail.
"""
import ast
from contextlib import ExitStack
from pathlib import Path
import re
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import check
import knc_vmath


class CheckOutputs(unittest.TestCase):
    def test_fake_t1_t2_with_old_destinations_unwritable(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            base = Path(temporary)
            out = base / 'run'
            out.mkdir()
            runner = check.Runner.__new__(check.Runner)
            runner.args = SimpleNamespace(compiler='gcc16', varargs_case=None)
            runner.tc = base / 'old/toolchain'
            runner.sysroot = runner.tc / 'sysroot'
            runner.gcc_build = base / 'old/gcc-build'
            runner.cc = runner.gcc_build / 'gcc/xgcc'
            runner.cc.parent.mkdir(parents=True)
            runner.cc.with_name('gfortran').write_text('fake driver')
            runner.cc_flags = []
            runner.flags = []
            runner.env = {}
            runner.out = out
            runner.fixture = ROOT / 'tests/acceptance/m1_affine'
            runner.source_dir = ROOT / 'tests/t1'
            runner.off_object = None
            runner.say = lambda text: None
            runner.t2_abi = lambda elf, trace, **kw: None  # Fake output is not ELF.
            runner.function_body = lambda assembly, name: ''  # Fake bodies for path coverage.
            results, writes = [], []

            def result(label, failures):
                results.append(label)
                self.assertNotIn('infrastructure', label, (label, failures))

            runner.result = result
            # Deny ALL writes outside runner.out, including mkdir and unlink.
            # This is deterministic on Windows/admin accounts where chmod is
            # insufficient, and also covers ROOT-relative destinations.
            for method in ('mkdir', 'unlink', 'write_text', 'write_bytes', 'open'):
                original = getattr(Path, method)

                def guarded(path, *args, _method=method, _original=original, **kwargs):
                    mode = args[0] if args else kwargs.get('mode', 'r')
                    writing = _method != 'open' or any(c in mode for c in 'wax+')
                    if writing:
                        if path.resolve() != out.resolve() and out.resolve() not in path.resolve().parents:
                            raise PermissionError('old output is unwritable: ' + str(path))
                        writes.append(path)
                    return _original(path, *args, **kwargs)

                stack.enter_context(patch.object(Path, method, guarded))

            def fake_command(*args, check=True, **kwargs):
                args = [str(arg) for arg in args]
                if '-o' in args and args[args.index('-o') + 1] != '-':
                    Path(args[args.index('-o') + 1]).write_text(
                        'sqrt_loop:\n ret\n .size sqrt_loop, .-sqrt_loop\n')
                for arg in args:
                    if arg.startswith('-fdump-') and '=' in arg:
                        Path(arg.split('=', 1)[1]).write_text('')
                return '' if check else SimpleNamespace(returncode=0, stdout='', stderr='')

            runner.command = fake_command
            stack.enter_context(patch.object(check.subprocess, 'run',
                side_effect=lambda args, **kw: fake_command(*args, check=False)))
            stack.enter_context(patch.object(knc_vmath, 'prefix',
                return_value=(base / 'old/prefix', base / 'old/prefix/lib')))
            # Exercise the default tiers AND every selectable module handler.
            runner.t1()
            runner.t2()
            for selection, (_, handlers) in check.SELECTIONS.items():
                runner.args = SimpleNamespace(compiler='gcc16', varargs_case=None,
                                              **{selection: True})
                for tier in handlers:
                    with self.subTest(selection=selection, tier=tier):
                        getattr(runner, tier)()
            self.assertTrue(any(label.startswith('t1 ') for label in results))
            self.assertTrue(any(label.startswith('t2 ') for label in results))
            self.assertTrue(writes)
            for name in ('vecarg-O0-O2.mic', 'vmath-loop.mic',
                         'atomic-counter.mic', 'secondary-pressure.mic',
                         'gcc16-libgcc.mic', 'knc-storent-publish.mic'):
                self.assertTrue(any(path.name == name for path in writes), name)

    def test_grep_no_fixed_output_paths_in_runner_checks(self):
        # Discover modules from the dispatch table and imports, rather than
        # maintaining a list that could silently omit a new check module.
        pending = ['check']
        seen, violations = set(), []
        fixed = re.compile(r'\b(?:runner|self)\.tc\.parent\b|_shared|\bSHARED\b|'
                           r'\bstorage\.(?:shared_area|main_root)\(')
        while pending:
            name = pending.pop()
            path = ROOT / 'tools' / (name + '.py')
            if name in seen or not path.is_file():
                continue
            seen.add(name)
            source = path.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    pending.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    pending.append(node.module)
                elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                      and node.func.attr == 'import_module' and node.args
                      and isinstance(node.args[0], ast.Constant)):
                    pending.append(node.args[0].value)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not any(arg.arg in ('runner', 'self') for arg in node.args.args):
                    continue
                if name == 'check' and node.name in ('__init__', 'run'):
                    continue  # Allocate runner.out; explicit --record destination.
                for line in ast.get_source_segment(source, node).splitlines():
                    if re.search(r'^\s*(?:out|output|dest|directory|elf|asm|obj)\s*=', line) and fixed.search(line):
                        violations.append(name + ': ' + line.strip())
        self.assertFalse(violations, '\n'.join(violations))


if __name__ == '__main__':
    unittest.main()
