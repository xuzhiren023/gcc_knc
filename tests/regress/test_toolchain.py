"""S1-02: GCC 16 must configure against the shared KNC toolchain."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('toolchain', ROOT / 'tools/toolchain.py')
toolchain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toolchain)


class Gcc16(unittest.TestCase):
    def test_resume_build_keeps_j8_and_small_debug_info(self):
        with tempfile.TemporaryDirectory() as directory:
            shared = Path(directory)
            (shared / 'gcc').mkdir()
            (shared / 'gcc/configure').touch()
            build = shared / 'gcc-build'
            build.mkdir()
            (build / 'config.status').touch()
            with patch.object(toolchain, 'SHARED', shared), \
                    patch.object(toolchain.os, 'cpu_count', return_value=12), \
                    patch.object(toolchain, 'command') as command, \
                    contextlib.redirect_stdout(io.StringIO()):
                toolchain.gcc16(SimpleNamespace(resume=True))
            self.assertEqual(command.call_args_list[0].args,
                             ('make', '-j8', 'all-gcc',
                              'CFLAGS=-O2 -g1', 'CXXFLAGS=-O2 -g1'))
            self.assertEqual(command.call_args_list[0].kwargs, {'cwd': build})
            self.assertFalse(any('bash' in call.args for call in command.call_args_list))

    def test_configure_uses_knc_target_and_shared_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            shared = Path(directory)
            source = shared / 'gcc'
            source.mkdir()
            (source / 'configure').touch()
            tc = shared / 'toolchain'
            with patch.object(toolchain, 'SHARED', shared), \
                    patch.object(toolchain, 'TC', tc), \
                    patch.object(toolchain, 'SYSROOT', tc / 'sysroot'), \
                    patch.object(toolchain, 'command') as command, \
                    contextlib.redirect_stdout(io.StringIO()):
                toolchain.gcc16(SimpleNamespace())
            configure = next(call for call in command.call_args_list
                             if str(source / 'configure') in map(str, call.args))
            for flag in ('--target=k1om-mpss-linux',
                         '--with-as=' + str(tc / 'cross/bin/k1om-mpss-linux-as'),
                         '--with-ld=' + str(tc / 'cross/bin/k1om-mpss-linux-ld'),
                         '--with-sysroot=' + str(tc / 'sysroot')):
                self.assertIn(flag, configure.args)


if __name__ == '__main__':
    unittest.main()
