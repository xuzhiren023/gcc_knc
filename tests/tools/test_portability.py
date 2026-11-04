"""S3-12 T0: textual portability and x86 comparison without a GCC build."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import portability


class PortabilityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'gcc'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'base')
        for key, value in (('user.name', 'test'), ('user.email', 'test@example.invalid'),
                           ('core.autocrlf', 'false'), ('core.fileMode', 'false')):
            self.git('config', key, value)
        self.write('shared.c', 'base\n')
        self.write('other.c', 'base\n')
        self.commit('base')
        self.git('tag', 'releases/gcc-16.2.0')
        self.git('checkout', '-qb', 'knc')
        self.write('shared.c', 'knc\n')
        self.commit('knc')
        self.git('checkout', '-qb', 'upstream/master', 'base')
        self.write('shared.c', 'upstream\n')
        self.commit('conflict')
        self.git('checkout', '-qb', 'upstream/releases/gcc-16', 'base')
        self.write('other.c', 'disjoint\n')
        self.commit('disjoint')
        self.git('branch', 'upstream/releases/gcc-9', 'base')
        self.write('other.c', 'staged\n')
        self.git('add', 'other.c')
        self.write('other.c', 'unstaged\n')
        self.write('untracked', 'keep\n')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo)

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf8')

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-qm', message)

    def snapshot(self):
        return (self.git('show-ref'), self.git('symbolic-ref', 'HEAD'),
                (self.repo / '.git/index').read_bytes(),
                {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob('*')
                 if p.is_file() and '.git' not in p.relative_to(self.repo).parts})

    def test_drill_conflict_disjoint_and_no_checkout_changes(self):
        before = self.snapshot()
        report = self.root / 'forward-port.md'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(portability.main(['drill', '--repo', str(self.repo),
                                              '--report', str(report)]), 0)
        text = report.read_text()
        master, release = text.split('### upstream/master')[1].split(
            '### upstream/releases/gcc-16')
        self.assertIn(self.git('rev-parse', 'upstream/master').decode().strip(), master)
        self.assertIn(self.git('show', '-s', '--format=%cs', 'upstream/master').decode().strip(), master)
        for expected in ('Conflicts: 1', 'shared.c', '<<<<<<<', 'upstream', 'knc',
                         '=======', '>>>>>>>', '+1', '-1'):
            self.assertIn(expected, master)
        self.assertIn('Conflicts: 0', release)
        self.assertNotIn('gcc-9', text)
        self.assertEqual(before, self.snapshot())

    def test_x86_fake_compilers_counts_and_diffs(self):
        corpus = self.repo / 'gcc/testsuite/gcc.c-torture/compile'
        corpus.mkdir(parents=True)
        for name in ('same.c', 'different.c'):
            (corpus / name).write_text(
                '/* { dg-additional-options "-std=gnu17 -fpermissive" } */\n'
                'int f(void) { return 1; }\n')
        compilers = []
        for side in ('a', 'b'):
            script = self.root / (side + '.py')
            script.write_text(
                'import pathlib, sys\n'
                'args = sys.argv[1:]\n'
                'assert "-O2" in args\n'
                'assert all(x in args for x in ("-w", "-std=gnu17", "-fpermissive"))\n'
                'source = next(x for x in args if x.endswith(".c"))\n'
                'text = "assembly\\n"\n'
                'if "different.c" in source and "-mavx512f" in args:\n'
                '    text += ' + repr(side + '\n') + '\n'
                'pathlib.Path(args[args.index("-o") + 1]).write_text(text)\n')
            compilers.append([sys.executable, str(script)])
        output = io.StringIO()
        with mock.patch.object(portability, 'build_cc1', side_effect=compilers), \
                mock.patch.object(portability, 'make_is_running', return_value=False), \
                contextlib.redirect_stdout(output):
            result = portability.main(['x86', '--repo', str(self.repo), '--shared', str(self.root),
                                       '--tree', 'base', '--tree', 'knc'])
        self.assertEqual(result, 1)
        self.assertIn('-O2: identical=2 different=0', output.getvalue())
        self.assertIn('-O2 -mavx512f: identical=1 different=1', output.getvalue())
        self.assertIn('DIFFERENT different.c', output.getvalue())
        self.assertIn('-a\n+b\n', output.getvalue())
        self.assertIn('Default torture options: -w', output.getvalue())
        self.assertIn('Dialect options same.c: -std=gnu17 -fpermissive', output.getvalue())

    def test_x86_one_sided_and_shared_failures(self):
        corpus = self.repo / portability.CORPUS
        corpus.mkdir(parents=True)
        for name in ('one-sided.c', 'both.c', 'diagnostics.c'):
            (corpus / name).write_text('int f(void) { return 1; }\n')
        compilers = []
        for side in ('a', 'b'):
            script = self.root / (side + '.py')
            script.write_text(
                'import pathlib, sys\n'
                'args = sys.argv[1:]\n'
                'name = pathlib.Path(next(x for x in args if x.endswith(".c"))).name\n'
                'side = ' + repr(side) + '\n'
                'if name == "both.c":\n'
                '    print("shared error")\n'
                '    sys.exit(1)\n'
                'if name == "diagnostics.c" or side == "b":\n'
                '    print(side + " error")\n'
                '    sys.exit(1)\n'
                'print("a output")\n'
                'pathlib.Path(args[args.index("-o") + 1]).write_text("assembly\\n")\n')
            compilers.append([sys.executable, str(script)])
        with mock.patch.object(portability, 'build_cc1', side_effect=compilers), \
                mock.patch.object(portability, 'make_is_running', return_value=False), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            result = portability.main(['x86', '--repo', str(self.repo), '--shared', str(self.root),
                                       '--tree', 'base', '--tree', 'knc'])
        self.assertEqual(result, 1)
        for flags in ('-O2', '-O2 -mavx512f'):
            self.assertIn(flags + ': identical=0 different=2 both-failed=1', output.getvalue())
        self.assertIn('DIFFERENT one-sided.c', output.getvalue())
        self.assertIn('DIFFERENT diagnostics.c', output.getvalue())
        self.assertIn('BOTH-FAILED both.c', output.getvalue())
        for text in ('a output', 'a error', 'b error', 'base', 'knc'):
            self.assertIn(text, output.getvalue())

    def test_x86_refuses_running_make(self):
        with mock.patch.object(portability.subprocess, 'check_output',
                               return_value='"make.exe","123","Console","1","100 K"\n'), \
                mock.patch.object(portability, 'build_cc1') as build, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(portability.main(['x86', '--tree', 'base', '--tree', 'knc']), 2)
        build.assert_not_called()
        self.assertIn('make.exe', output.getvalue())

    def test_x86_skip_make_check(self):
        corpus = self.repo / portability.CORPUS
        corpus.mkdir(parents=True)
        (corpus / 'probe.c').write_text('int x;\n')
        with mock.patch.object(portability, 'make_is_running',
                               side_effect=AssertionError('must skip tasklist')) as check, \
                mock.patch.object(portability, 'build_cc1', return_value=['cc1']) as build, \
                mock.patch.object(portability.subprocess, 'run',
                                  return_value=subprocess.CompletedProcess([], 1, 'same diagnostic')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(portability.main([
                'x86', '--skip-make-check', '--repo', str(self.repo),
                '--shared', str(self.root), '--tree', 'base', '--tree', 'knc']), 0)
        check.assert_not_called()
        self.assertEqual(build.call_count, 2)
        self.assertIn('make check skipped', output.getvalue())


if __name__ == '__main__':
    unittest.main()
