"""S3-24: build reuse with disposable Git repos and fake build commands."""
import contextlib
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import portability

RUN = subprocess.run


class BuildReuseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.build = self.root / 'build'
        self.build.mkdir()
        self.git('init', '-q')
        for key, value in (('user.name', 'test'), ('user.email', 'test@example.invalid'),
                           ('core.autocrlf', 'false'), ('core.fileMode', 'false')):
            self.git('config', key, value)
        (self.repo / 'configure').write_text('# fake configure\n')
        (self.repo / 'source.c').write_text('int x;\n')
        corpus = self.repo / portability.CORPUS
        corpus.mkdir(parents=True)
        (corpus / 'probe.c').write_text('int x;\n')
        self.commit('base')
        self.calls = self.root / 'calls.jsonl'
        self.fake = self.root / 'fake.py'
        self.fake.write_text(
            'import json, pathlib, sys\n'
            'tool, log, *args = sys.argv[1:]\n'
            'with open(log, "a") as f: f.write(json.dumps([tool, args]) + "\\n")\n'
            'if pathlib.Path("fail-" + tool).exists(): sys.exit(7)\n'
            'if tool == "configure": pathlib.Path("config.status").touch()\n'
            'if tool == "make":\n'
            '    pathlib.Path("gcc").mkdir(exist_ok=True)\n'
            '    pathlib.Path("gcc/cc1.exe").touch()\n')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args],
                                       text=True).strip()

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-qm', message)

    def command(self, argv, cwd):
        argv = list(map(str, argv))
        if argv[0] in ('make', 'bash'):
            tool = 'make' if argv[0] == 'make' else 'configure'
            args = argv[1:] if tool == 'make' else argv[2:]
            RUN([sys.executable, str(self.fake), tool, str(self.calls), *args],
                cwd=cwd, check=True)
        else:
            RUN(argv, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def recorded(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def shared(self, *flags):
        module = importlib.import_module('gcc_build')
        with mock.patch.object(module, 'command', side_effect=self.command), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            code = module.main(['--repo', str(self.repo), '--build', str(self.build), *flags])
        return code, output.getvalue()

    def shared_stamp(self):
        return self.build / '.gcc-build-stamp.json'

    def test_shared_clean_tree_reuse_and_same_tree_commit(self):
        self.assertEqual(self.shared('--if-stale')[0], 0)
        stamp = json.loads(self.shared_stamp().read_text())
        self.assertEqual(stamp['commit'], self.git('rev-parse', 'HEAD'))
        self.assertEqual(stamp['tree'], self.git('rev-parse', 'HEAD^{tree}'))
        self.assertTrue(stamp['clean'])
        self.assertIn('SKIP', self.shared('--if-stale')[1])
        self.git('commit', '--allow-empty', '-qm', 'same tree')
        self.assertIn('SKIP', self.shared('--if-stale')[1])
        self.assertEqual(self.recorded(), [['make', ['-j8', 'all-gcc',
                                                    'CFLAGS=-O2 -g1', 'CXXFLAGS=-O2 -g1']]])

    def test_shared_changes_dirty_missing_and_unreadable_stamp(self):
        self.assertEqual(self.shared('--if-stale')[0], 0)
        (self.repo / 'source.c').write_text('int changed;\n')
        self.commit('changed tree')
        self.assertEqual(self.shared('--if-stale')[0], 0)
        (self.repo / 'source.c').write_text('int dirty;\n')
        self.assertEqual(self.shared('--if-stale')[0], 0)
        self.assertFalse(json.loads(self.shared_stamp().read_text())['clean'])
        self.git('restore', 'source.c')
        self.assertEqual(self.shared('--if-stale')[0], 0)  # Dirty build cannot certify HEAD.
        (self.repo / 'untracked').touch()
        self.assertEqual(self.shared('--if-stale')[0], 0)
        (self.repo / 'untracked').unlink()
        self.shared_stamp().unlink()
        self.assertEqual(self.shared('--if-stale')[0], 0)
        self.shared_stamp().write_text('broken json')
        self.assertEqual(self.shared('--if-stale')[0], 0)
        self.assertEqual(len(self.recorded()), 7)

    def test_shared_failure_invalidates_success_and_retries(self):
        self.assertEqual(self.shared()[0], 0)
        (self.build / 'fail-make').touch()
        self.assertNotEqual(self.shared()[0], 0)
        self.assertFalse(self.shared_stamp().exists())
        (self.build / 'fail-make').unlink()
        self.assertEqual(self.shared('--if-stale')[0], 0)
        self.assertEqual(len(self.recorded()), 3)

    def slot(self, tree='HEAD', **kwargs):
        with mock.patch.object(portability, 'command', side_effect=self.command), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            compiler = portability.build_cc1(self.repo, self.root, tree, 'a', **kwargs)
        return compiler, output.getvalue()

    def slot_build(self):
        return self.root / 'portability/x86-a/build'

    def test_slot_reuses_configure_and_make_and_requires_compiler(self):
        self.slot()
        self.assertIn('SKIP', self.slot()[1])
        self.assertEqual([call[0] for call in self.recorded()], ['configure', 'make'])
        (self.slot_build() / 'gcc/cc1.exe').unlink()
        self.slot()
        self.assertEqual([call[0] for call in self.recorded()], ['configure', 'make', 'make'])

    def test_slot_commit_make_and_configure_arguments(self):
        self.slot()
        (self.repo / 'source.c').write_text('int changed;\n')
        self.commit('change')
        self.slot()
        self.assertEqual([call[0] for call in self.recorded()], ['configure', 'make', 'make'])
        make_args = ['-j2', 'all-gcc']
        self.slot(make_args=make_args)
        self.assertEqual(self.recorded()[-1], ['make', make_args])
        self.assertEqual(len(self.recorded()), 4)
        self.slot(make_args=make_args, configure_args=['--disable-bootstrap'])
        self.assertEqual(self.recorded()[-2:], [['configure', ['--disable-bootstrap']],
                                               ['make', make_args]])
        self.assertIn('SKIP', self.slot(make_args=make_args,
                                       configure_args=['--disable-bootstrap'])[1])

    def test_slot_failed_build_and_configure_are_retried(self):
        self.slot()
        stamp = self.slot_build() / '.cc1-build-stamp.json'
        (self.slot_build() / 'fail-make').touch()
        with self.assertRaises(subprocess.CalledProcessError):
            self.slot(make_args=['all-gcc'])
        self.assertFalse(stamp.exists())
        (self.slot_build() / 'fail-make').unlink()
        self.slot(make_args=['all-gcc'])
        (self.slot_build() / 'fail-configure').touch()
        with self.assertRaises(subprocess.CalledProcessError):
            self.slot(configure_args=['--changed'])
        self.assertFalse(stamp.exists())
        (self.slot_build() / 'fail-configure').unlink()
        self.slot(configure_args=['--changed'])
        self.assertEqual([call[0] for call in self.recorded()],
                         ['configure', 'make', 'make', 'make', 'configure', 'configure', 'make'])

    def test_x86_reuses_both_slots(self):
        def compile_fake(argv, **kwargs):
            if not str(argv[0]).endswith('cc1.exe'):
                return RUN(argv, **kwargs)
            Path(argv[argv.index('-o') + 1]).write_text('same assembly\n')
            return subprocess.CompletedProcess(argv, 0, '')

        args = ['x86', '--skip-make-check', '--repo', str(self.repo),
                '--shared', str(self.root), '--tree', 'HEAD', '--tree', 'HEAD']
        with mock.patch.object(portability, 'command', side_effect=self.command), \
                mock.patch.object(portability.subprocess, 'run', side_effect=compile_fake), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(portability.main(args), 0)
            self.assertEqual(portability.main(args), 0)
        self.assertEqual([call[0] for call in self.recorded()],
                         ['configure', 'make', 'configure', 'make'])
        self.assertEqual(output.getvalue().count('SKIP'), 2)


if __name__ == '__main__':
    unittest.main()
