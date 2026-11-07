"""Compile M2 cost diagnostics; invoke through tools/run.py."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', __file__], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script,
                                *sys.argv[1:]], env=env)
    build = SHARED / 'gcc-build/gcc'
    source = ROOT.parents[1] / 'tests/acceptance/m2_kernels/kernels.c'
    for tune in sys.argv[1:] or ['knc', 'generic']:
        out = SHARED / 'S6-05' / ('stencils-' + tune)
        subprocess.run(list(map(str, [build / 'xgcc', '-B' + str(build) + '/',
            '--sysroot=' + str(TC / 'sysroot'), '-march=knc', '-mtune=' + tune,
            '-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-ffp-contract=fast',
            '-DBUILD=gcc', '-ftree-vectorize', '-pthread', '-S', source,
            '-o', str(out) + '.s', '-fdump-tree-vect-details=' + str(out) + '.vect',
            '-fdump-tree-ivopts-details=' + str(out) + '.ivopts'])), check=True)
        print('M2 diagnostic: ' + str(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
