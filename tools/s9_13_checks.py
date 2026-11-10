#!/usr/bin/env python3
"""S9-13 -mknc-card=: the S8-03 prefetch M2 pairs for the lead's card run.

    python tools/run.py --name S9-13-m2 -- python tools/s9_13_checks.py

Stages under .work/_shared/S9-13: m2-o2 (M2 at its usual -O2 -march=knc) and,
for each model, kernels-<model> (kernels-gcc with -mknc-card=<model>) and the
pair m2-<model>/m2-kernels.mic, where m2_*_gcc is -mknc-card=<model> and
m2_*_gccbefore is plain -O2 -march=knc.  generic and 7100 carry the default
distances, so their kernels must equal m2-o2's (the script checks): on the
7120P they are A/A pairs.  3100 and 5100 time their derived distances on a
7100, which only bounds what they cost there.
"""
import os
import shutil
import subprocess
import sys

import s8_08_checks as s8

MODELS = ('generic', '7100', '3100', '5100')


def kernels(folder, flags):
    """build.py's kernels-gcc flags plus FLAGS; kernels-x87 from S9-13/m2-o2."""
    m2 = s8.ROOT / 'tests/acceptance/m2_kernels'
    out = s8.SHARED / folder
    out.mkdir(parents=True, exist_ok=True)
    for suffix in ('.s', '.o'):
        shutil.copyfile(s8.SHARED / 'S9-13/m2-o2' / ('kernels-x87' + suffix),
                        out / ('kernels-x87' + suffix))
    s8.run([s8.BUILD / 'xgcc', '-B' + str(s8.BUILD) + '/', '--sysroot=' + str(s8.TC / 'sysroot'),
            '-march=knc', '-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-ffp-contract=fast',
            '-DBUILD=gcc', '-ftree-vectorize', *flags, '-pthread', '-S', m2 / 'kernels.c',
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
        return subprocess.call([str(s8.TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    os.environ['PATH'] = ':'.join(str(s8.TC / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    (s8.SHARED / 'S9-13').mkdir(exist_ok=True)
    m2 = s8.ROOT / 'tests/acceptance/m2_kernels'
    build = [sys.executable, m2 / 'build.py', '--out']
    s8.run([*build, 'S9-13/m2-o2'])
    default = (s8.SHARED / 'S9-13/m2-o2/kernels-gcc.s').read_text()
    status = 0
    for model in MODELS:
        kernels('S9-13/kernels-' + model, ['-mknc-card=' + model])
        same = (s8.SHARED / 'S9-13' / ('kernels-' + model) / 'kernels-gcc.s').read_text() == default
        if same != (model in ('generic', '7100')):
            print('FAIL kernels-%s %s the default' % (model, 'equals' if same else 'differs from'),
                  flush=True)
            status = 1
        s8.run([*build, 'S9-13/m2-' + model, '--reuse-kernels', 'S9-13/kernels-' + model,
                '--before', 'S9-13/m2-o2'])
    print('M2 PAIRS S9-13/m2-{%s}/m2-kernels.mic (gcc = -mknc-card=MODEL, before = '
          '-O2 -march=knc); generic and 7100 are A/A; card run pending lead' % ','.join(MODELS),
          flush=True)
    return status


if __name__ == '__main__':
    sys.exit(main())
