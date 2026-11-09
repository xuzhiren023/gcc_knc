#!/usr/bin/env python3
"""S8-08 -mtune=knc tune flags: card builds of s4_masks and s5_ops.

    python tools/run.py --name S8-08-acceptance -- python tools/s8_08_checks.py

Builds and lints .work/_shared/S8-08/{s4_masks,s5_ops}/*.mic with the same
variants as S8-02; the lead runs them on the card.
"""
import os
from pathlib import Path
import subprocess
import sys

import storage

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
BUILD = Path(storage.gcc_build_dir(ROOT.parent.parent)) / 'gcc'
OUT = SHARED / 'S8-08'


def cc():
    return [str(BUILD / 'xgcc'), '-B' + str(BUILD) + '/', '-march=knc',
            '--sysroot=' + str(TC / 'sysroot')]


def run(args):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def acceptance():
    for fixture in ('s4_masks', 's5_ops'):
        source = ROOT / 'tests/acceptance' / fixture
        dest = OUT / fixture
        dest.mkdir(parents=True, exist_ok=True)
        driver = dest / 'driver.o'
        run([*cc(), '-O0', '-fwrapv', '-c', source / 'driver.c', '-o', driver])
        variants = [('o2v', ['-O2', '-ftree-vectorize']), ('o3', ['-O3'])]
        if fixture == 's5_ops':
            variants += [('fast', ['-O3', '-ffast-math']),
                         ('neg', ['-O2', '-ftree-vectorize', '-DNEGATIVE_CONTROL'])]
        for name, flags in variants:
            obj = dest / (name + '.o')
            elf = dest / (name + '.mic')
            run([*cc(), *flags, '-fwrapv', '-c', source / 'loops.c', '-o', obj])
            run([*cc(), *flags, '-fwrapv', driver, obj, '-lm', '-o', elf])
            run([sys.executable, ROOT / 'tools/knc_lint', elf])
            print('BUILT and LINTED ' + fixture + '/' + name + '.mic; card run pending lead',
                  flush=True)
    return 0


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                      ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', __file__],
            env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'),
                                script, *sys.argv[1:]], env=env)
    os.environ['PATH'] = ':'.join(str(TC / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    return acceptance()


if __name__ == '__main__':
    sys.exit(main())
