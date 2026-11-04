"""S0-03: green seed and mutations of every acceptance scan."""
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
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

    def test_loop_branch_operands(self):
        for branch in ('jne .L2', 'je .L2', 'jknzd %k1, .L2', 'jkzd %k2, .L2'):
            with self.subTest(branch=branch):
                body = '.L2:\n vmulps %zmm0, %zmm1, %zmm2\n ' + branch
                self.assertEqual(list(check.loops(body)), [body])

    def test_seed_with_mask_branches(self):
        for branch in ('jknzd %k1, ', 'jkzd %k2, '):
            with self.subTest(branch=branch):
                asm = self.asm.replace('jne .L32', branch + '.L32').replace(
                    'jne .L64', branch + '.L64')
                self.assertEqual(self.scan(asm), [])
                self.assertTrue(self.scan(asm.replace(branch + '.L32', 'nop')))

    def test_seed_and_mutations(self):
        self.assertEqual(self.scan(), [])
        for old, new in [('vmulps', 'fmul'), ('vaddpd', 'fadd'),
                         ('%zmm', '%ymm'), ('jne .L32', 'nop')]:
            with self.subTest(mutation=old):
                self.assertTrue(self.scan(self.asm.replace(old, new)))
        self.assertTrue(self.scan(self.asm.replace('fsubs (%rax)', 'vsubps %zmm0, %zmm1, %zmm2')))
        self.assertTrue(self.scan(self.asm.replace('fsubs (%rax)', 'vsubrps %zmm0, %zmm1, %zmm2')))
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

    def test_scalar_tails(self):
        self.assertTrue(self.scan(self.asm.replace('fmuls (%rsi)', 'nop')))
        self.assertTrue(self.scan(self.asm.replace('faddl (%rdi)', 'nop')))
        self.assertTrue(self.scan(self.asm.replace('.LT32:', '.LT32:\n vmovaps (%rsi), %zmm0')))

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
        runner.cc_flags = []
        runner.flags = []
        runner.fixture = Path('/fixture')
        runner.off_object = Path('/shared/check/loops.o')
        runner.say = Mock()
        runner.result = Mock()
        runner.tool = Mock(return_value='readelf')
        cases = [('/outside', 'GLIBC_2.14', 'GLIBC_2.14', None),
                 ('/shared/sysroot', 'GLIBC_2.14', 'GLIBC_2.14', []),
                 ('/shared/sysroot', 'GLIBC_99.0', 'GLIBC_99.0', ['libc.so.6 lacks printf@GLIBC_99.0']),
                 ('/shared/sysroot', 'GLIBC_99.0', 'GLIBC_2.14', ['unresolved version requirement printf@GLIBC_99.0']),
                 ('/shared/sysroot', None, 'GLIBC_2.14', ['no versioned symbol requirements found'])]
        for provider, required, version, failures in cases:
            with self.subTest(provider=provider, required=required, version=version):
                trace = '\n'.join('/lib64/%s (%s/lib64/%s)' % (name, provider, name)
                                  for name in ('libc.so.6', 'ld-linux-k1om.so.2'))
                def command(*args):
                    if '-Wl,--trace' in args:
                        return trace
                    if '--version-info' in args:
                        return ('Version needs section .gnu.version_r contains 1 entry:\n'
                                '  000000: Version: 1  File: libc.so.6  Cnt: 1\n'
                                '  0x0010: Name: %s  Flags: none  Version: 2\n' % version)
                    if '--dyn-syms' in args:
                        if args[-1] == runner.out / 'm1_affine.mic':
                            return ('  1: 0000000000000000 0 FUNC GLOBAL DEFAULT UND printf@%s (2)\n'
                                    % required) if required else ''
                        return '  2: 0000000000010000 0 FUNC GLOBAL DEFAULT 12 printf@@GLIBC_2.14\n'
                    return ''
                runner.command = Mock(side_effect=command)
                runner.result.reset_mock()
                with patch.object(Path, 'read_bytes', return_value=b''), \
                        patch.object(Path, 'is_file', return_value=True), \
                        patch.object(check, 'scan_elf', return_value=[]):
                    if provider == '/outside':
                        with self.assertRaisesRegex(RuntimeError, 'outside shared sysroot'):
                            runner.t2()
                    else:
                        runner.t2()
                        runner.result.assert_called_with('t2 symbol versions against card sysroot', failures)
                        self.assertTrue(any('/shared/sysroot/lib64/libc.so.6' in call.args[0]
                                            for call in runner.say.call_args_list))

    def test_only_t0_can_cache_project_inputs(self):
        for tiers in (['t0'], ['t1'], ['t2'], ['t0', 't1', 't2']):
            with self.subTest(tiers=tiers), patch.object(check, 'os', SimpleNamespace(name='posix')), \
                    patch.object(check.sys, 'argv', ['tools/check', *tiers]), \
                    patch.object(check.subprocess, 'call', return_value=0) as call:
                self.assertEqual(check.main(), 0)
                self.assertEqual('--inputs' in call.call_args.args[0], tiers == ['t0'])


class OptionalSelections(unittest.TestCase):
    def test_new_table_entry_defaults_without_args_and_dispatches_both_tiers(self):
        runner = check.Runner.__new__(check.Runner)
        callbacks = {'t1': Mock(), 't2': Mock()}
        with patch.dict(check.SELECTIONS, {'future': ('future probe', callbacks)}):
            for tier in callbacks:
                self.assertFalse(runner.run_selections(tier))
                callbacks[tier].assert_not_called()
            runner.args = SimpleNamespace(future=True)
            for tier in callbacks:
                getattr(runner, tier)()
                callbacks[tier].assert_called_once_with(runner)

    def test_existing_selections_combine_in_each_tier(self):
        modules = {name: SimpleNamespace(t1=Mock(), t2=Mock(), link=Mock())
                   for name in ('atomics', 'x87_spill', 'secondary_reload',
                                'varargs_abi', 'scalar_abi', 'fast_math', 'libgcc')}
        selected = dict.fromkeys((*modules, 'libgcc_link'), True)
        runner = check.Runner.__new__(check.Runner)
        runner.args = SimpleNamespace(**selected)
        with patch.dict(sys.modules, modules):
            runner.t1()
            runner.t2()
        for name in ('atomics', 'x87_spill', 'secondary_reload', 'varargs_abi', 'scalar_abi'):
            with self.subTest(tier='t1', selection=name):
                modules[name].t1.assert_called_once_with(runner)
        for name in ('fast_math', 'libgcc', 'atomics', 'secondary_reload', 'varargs_abi', 'scalar_abi'):
            with self.subTest(tier='t2', selection=name):
                modules[name].t2.assert_called_once_with(runner)
        modules['libgcc'].link.assert_called_once_with(runner, 'gcc16')
        modules['x87_spill'].t2.assert_not_called()

    def test_selection_error_is_reported_and_later_selections_still_run(self):
        runner = check.Runner.__new__(check.Runner)
        runner.args = SimpleNamespace(broken=True, later=True)
        runner.lines, runner.failed = [], False
        later = Mock(side_effect=lambda runner: runner.result('t1 later', []))
        selections = {
            'broken': ('broken probe', {'t1': Mock(side_effect=RuntimeError('seed failure'))}),
            'later': ('later probe', {'t1': later}),
        }
        with patch.dict(check.SELECTIONS, selections, clear=True):
            runner.t1()
        self.assertTrue(runner.failed)
        self.assertEqual(runner.lines, ['FAIL t1 broken infrastructure: seed failure', 'PASS t1 later'])
        later.assert_called_once_with(runner)

    def test_vector_cli_selects_only_vector_sources(self):
        runner = check.Runner.__new__(check.Runner)
        runner.run = Mock(return_value=0)
        with patch.object(check, 'os', SimpleNamespace(name='posix')), \
                patch.object(check.sys, 'argv', ['tools/check', 't1', '--vector', '--worker']), \
                patch.object(check, 'Runner', return_value=runner) as constructor:
            self.assertEqual(check.main(), 0)
        runner.args = constructor.call_args.args[0]
        self.assertTrue(runner.args.vector)
        with tempfile.TemporaryDirectory() as directory:
            runner.source_dir = Path(directory)
            for name in ('knc-vec-b.c', 'knc-vec-a.c', 'knc-abi-other.c', 'other.c'):
                (runner.source_dir / name).touch()
            runner.t1_sources = Mock()
            import knc_vector
            with patch.object(knc_vector, 't1_packed') as packed, \
                    patch.object(knc_vector, 't1_unaligned') as unaligned, \
                    patch.object(knc_vector, 't1_fp') as fp:
                runner.t1()
            runner.t1_sources.assert_called_once_with([
                runner.source_dir / 'knc-vec-a.c', runner.source_dir / 'knc-vec-b.c'])
            packed.assert_called_once_with(runner)
            unaligned.assert_called_once_with(runner)
            fp.assert_called_once_with(runner)


class SourceTests(unittest.TestCase):
    """Compile seeded sources with a fake compiler, without a GCC build."""

    ASSEMBLY = ('smoke:\n .L1:\n movl $7, %eax\n ret\n .size smoke, .-smoke\n'
                'other:\n forbidden\n .size other, .-other\n')

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.source_dir = self.directory / 'sources'
        self.source_dir.mkdir()
        self.source = self.source_dir / 'seed.c'
        self.compiler = self.directory / 'compiler.py'
        self.runner = check.Runner(SimpleNamespace(compiler='gcc16', cc=None))
        self.addCleanup(self.runner._output.cleanup)
        self.runner.cc = Path(sys.executable)
        self.runner.cc_flags = [str(self.compiler)]
        self.runner.source_dir = self.source_dir
        self.runner.say = Mock()
        command = self.runner.command

        def dispatch(*args, **kwargs):
            if args[0] == self.runner.cc:
                return command(*args, **kwargs)
            return ''  # Seed assembler and lint success; inspect their calls below.

        self.runner.command = Mock(side_effect=dispatch)

    def run_seed(self, header, required=('-O2',), code=0, diagnostic=''):
        self.source.write_text(header + '\nint smoke(void) { return 7; }\n')
        self.compiler.write_text(
            'import pathlib, sys\n'
            'args = sys.argv[1:]\n'
            'if not all(flag in args for flag in %r):\n'
            '    print("error: missing seeded option")\n'
            '    sys.exit(2)\n'
            'print(%r)\n'
            'if %d == 0:\n'
            '    pathlib.Path(args[args.index("-o") + 1]).write_text(%r)\n'
            'sys.exit(%d)\n' % (required, diagnostic, code, self.ASSEMBLY, code))
        self.runner.failed = False
        self.runner.say.reset_mock()
        self.runner.command.reset_mock()
        self.runner.t1_sources()
        lines = [call.args[0] for call in self.runner.say.call_args_list]
        self.assertEqual(len(lines), 1, lines)
        return lines[0]

    def test_options(self):
        for header, required, passed in (
                ('', ('-O2',), True),
                ('// options: -O0 -DNAME="two words"', ('-O0', '-DNAME=two words'), True),
                ('// options: -O0', ('-O2',), False)):
            with self.subTest(header=header, required=required):
                line = self.run_seed(header, required)
                self.assertEqual(line.startswith('PASS '), passed, line)

    def test_scan_asm(self):
        self.assertTrue(self.run_seed('// scan-asm: movl.*%eax').startswith('PASS '))
        self.assertIn('scan-asm: absent', self.run_seed('// scan-asm: absent'))
        calls = self.runner.command.call_args_list
        self.assertTrue(any('--march=k1om' in call.args for call in calls))
        self.assertTrue(any(str(check.ROOT / 'tools/knc_lint') in
                            [str(arg) for arg in call.args] for call in calls))

    def test_scan_asm_not(self):
        self.assertTrue(self.run_seed('// scan-asm-not: absent').startswith('PASS '))
        line = self.run_seed('// scan-asm-not: forbidden\n// scan-asm: absent')
        self.assertIn('scan-asm-not: forbidden', line)
        self.assertNotIn('scan-asm: absent', line)

    def test_scan_asm_func(self):
        self.assertTrue(self.run_seed('// scan-asm-func smoke: movl.*%eax').startswith('PASS '))
        for directive in ('// scan-asm-func smoke: forbidden',
                          '// scan-asm-func missing: movl'):
            with self.subTest(directive=directive):
                self.assertIn(directive[3:], self.run_seed(directive))

    def test_error(self):
        directive = '// error: unsupported.*KNC'
        self.assertTrue(self.run_seed(directive, code=1,
                                      diagnostic='error: unsupported mode on KNC').startswith('PASS '))
        self.assertEqual(self.runner.command.call_count, 1)
        for code, diagnostic in ((0, 'unsupported mode on KNC'), (1, 'unrelated error')):
            with self.subTest(code=code):
                line = self.run_seed(directive, code=code, diagnostic=diagnostic)
                self.assertTrue(line.startswith('FAIL '), line)
                self.assertIn('error: unsupported.*KNC', line)
                self.assertEqual(self.runner.command.call_count, 1)


if __name__ == '__main__':
    unittest.main()
