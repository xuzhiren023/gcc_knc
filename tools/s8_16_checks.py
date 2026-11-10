#!/usr/bin/env python3
"""S8-16 -mphinix: the M2 pair for the lead's card run.

    python tools/run.py --name S8-16-m2 -- python tools/s8_16_checks.py

Stages under .work/_shared/S8-16: m2-o2 (M2 at its usual -O2 -march=knc),
m2-phinix (kernels-gcc compiled with -mphinix in place of -O2, other flags
unchanged) and m2paired/m2-kernels.mic, where m2_*_gcc is -mphinix and
m2_*_gccbefore is -O2 -march=knc.
"""
import os
import shutil
import subprocess
import sys

import s8_08_checks as s8


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(s8.TC / p) for p in
                                      ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output(
            [str(s8.TC / 'cygwin/bin/cygpath.exe'), '-u', __file__],
            env=env, text=True).strip()
        return subprocess.call([str(s8.TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    os.environ['PATH'] = ':'.join(str(s8.TC / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    out = s8.SHARED / 'S8-16'
    m2 = s8.ROOT / 'tests/acceptance/m2_kernels'
    s8.run([sys.executable, m2 / 'build.py', '--out', 'S8-16/m2-o2'])
    phinix = out / 'm2-phinix'
    phinix.mkdir(parents=True, exist_ok=True)
    for suffix in ('.s', '.o'):
        shutil.copyfile(out / 'm2-o2' / ('kernels-x87' + suffix), phinix / ('kernels-x87' + suffix))
    # build.py's kernels-gcc flags, with -mphinix in place of -O2.
    s8.run([s8.BUILD / 'xgcc', '-B' + str(s8.BUILD) + '/', '--sysroot=' + str(s8.TC / 'sysroot'),
            '-mphinix', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-ffp-contract=fast',
            '-DBUILD=gcc', '-ftree-vectorize', '-pthread', '-S', m2 / 'kernels.c',
            '-o', phinix / 'kernels-gcc.s'])
    s8.run([s8.TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om', phinix / 'kernels-gcc.s',
            '-o', phinix / 'kernels-gcc.o'])
    s8.run([sys.executable, m2 / 'build.py', '--out', 'S8-16/m2paired',
            '--reuse-kernels', 'S8-16/m2-phinix', '--before', 'S8-16/m2-o2'])
    print('M2 PAIR S8-16/m2paired/m2-kernels.mic (gcc = -mphinix, before = -O2 -march=knc); '
          'card run pending lead', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
