#!/usr/bin/env python3
"""S8-20 density-following small-loop unroll: M2 pairs for the lead's card run.

    python tools/run.py --name S8-20-before -- python tools/s8_20_checks.py before
    python tools/run.py --name S8-20-m2 -- python tools/s8_20_checks.py

'before' runs with the GCC tree at the S8-16 knc head and compiles M2's
kernels-gcc with --param knc-threads-per-core=1 into S8-20/before-d1.  The
default mode stages under .work/_shared/S8-20:
  m2-d4  default -O2 -march=knc (4 threads per core), before = S8-16/m2-o2;
         run at --density 4
  m2-d1  kernels-gcc with --param knc-threads-per-core=1, before =
         S8-20/before-d1; run at --density 1
  m2-aa  m2-d4's objects against themselves (A/A)
"""
import os
import shutil
import subprocess
import sys

import s8_08_checks as s8


def kernels(folder, param):
    """build.py's kernels-gcc flags plus PARAM; kernels-x87 from S8-16/m2-o2."""
    m2 = s8.ROOT / 'tests/acceptance/m2_kernels'
    out = s8.SHARED / folder
    out.mkdir(parents=True, exist_ok=True)
    for suffix in ('.s', '.o'):
        shutil.copyfile(s8.SHARED / 'S8-16/m2-o2' / ('kernels-x87' + suffix),
                        out / ('kernels-x87' + suffix))
    s8.run([s8.BUILD / 'xgcc', '-B' + str(s8.BUILD) + '/', '--sysroot=' + str(s8.TC / 'sysroot'),
            '-march=knc', '-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-ffp-contract=fast',
            '-DBUILD=gcc', '-ftree-vectorize', *param, '-pthread', '-S', m2 / 'kernels.c',
            '-o', out / 'kernels-gcc.s'])
    s8.run([s8.TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om', out / 'kernels-gcc.s',
            '-o', out / 'kernels-gcc.o'])


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(s8.TC / p) for p in
                                      ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output(
            [str(s8.TC / 'cygwin/bin/cygpath.exe'), '-u', __file__],
            env=env, text=True).strip()
        return subprocess.call([str(s8.TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]],
                               env=env)
    os.environ['PATH'] = ':'.join(str(s8.TC / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    density1 = ['--param', 'knc-threads-per-core=1']
    if sys.argv[1:] == ['before']:
        kernels('S8-20/before-d1', density1)
        print('BEFORE S8-20/before-d1 (S8-16 head, knc-threads-per-core=1)', flush=True)
        return 0
    m2 = s8.ROOT / 'tests/acceptance/m2_kernels'
    build = [sys.executable, m2 / 'build.py', '--out']
    s8.run([*build, 'S8-20/m2-d4', '--before', 'S8-16/m2-o2'])
    kernels('S8-20/kernels-d1', density1)
    s8.run([*build, 'S8-20/m2-d1', '--reuse-kernels', 'S8-20/kernels-d1',
            '--before', 'S8-20/before-d1'])
    s8.run([*build, 'S8-20/m2-aa', '--reuse-kernels', 'S8-20/m2-d4', '--before', 'S8-20/m2-d4'])
    print('M2 PAIRS S8-20/m2-d4 (--density 4, before = S8-16/m2-o2), S8-20/m2-d1 '
          '(--density 1, before = S8-20/before-d1), S8-20/m2-aa (A/A); card run pending lead',
          flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
