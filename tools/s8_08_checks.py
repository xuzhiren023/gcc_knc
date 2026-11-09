#!/usr/bin/env python3
"""S8-08 -mtune=knc tune flags: card builds of s4_masks and s5_ops.

    python tools/run.py --name S8-08-acceptance -- python tools/s8_08_checks.py

Builds and lints .work/_shared/S8-08/{s4_masks,s5_ops}/*.mic with the same
variants as S8-02; the lead runs them on the card.  --align stages M2 A/A
pairs under .work/_shared/S8-08/align-{none,16,32,64}.
"""
import os
from pathlib import Path
import re
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


# Lead note 2026-11-08: placement alone moved m2_mat8_gcc 1.21-1.23x.  An A/A
# pair links one kernels-gcc.s twice (gcc and gcc_before, renamed by the M2
# build.py), so the copies differ only in address; the alignment whose ratios
# stay within the 1.6% A/A bias removes the swing.  'none' is the -mtune=knc
# default before S8-08 set 64 (functions 16, loops 0:0:8).
ALIGNS = ('none', '16', '32', '64')


def align():
    m2 = ROOT / 'tests/acceptance/m2_kernels'
    flags = ['-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-ffp-contract=fast',
             '-DWITH_BEFORE', '-pthread']
    units = [('kernels-gcc', ['-DBUILD=gcc', '-ftree-vectorize']),
             ('kernels-x87', ['-DBUILD=x87', '-fno-tree-vectorize', '-fno-tree-slp-vectorize'])]
    for value in ALIGNS:
        kernels = OUT / ('align-' + value + '-k')
        kernels.mkdir(parents=True, exist_ok=True)
        extra = ([] if value == 'none' else
                 ['-falign-functions=' + value, '-falign-loops=' + value])
        for name, unit in units:
            run([*cc(), *flags, *extra, *unit, '-S', m2 / 'kernels.c', '-o', kernels / (name + '.s')])
            run([TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om', kernels / (name + '.s'),
                 '-o', kernels / (name + '.o')])
        # The second copy follows the first by its .text size, a multiple of
        # 64 here, and the 64-byte loop alignment (S8-10) re-pins everything
        # after it, so start every function 32 bytes further into its line
        # instead: the same code, entries and unpinned code at the other half
        # of the line, as in S8-03's 0x4032d0/0x4028b0 case.  At 64 the only
        # legal shift is a whole line, which leaves line offsets unchanged.
        shifted = OUT / ('align-' + value + '-b')
        shifted.mkdir(parents=True, exist_ok=True)
        shift = 64 if value == '64' else 32
        offsets = {}
        for line in subprocess.check_output(
                [str(TC / 'cross/bin/k1om-mpss-linux-nm'), str(kernels / 'kernels-gcc.o')],
                text=True).splitlines():
            address, kind, symbol = line.split()
            if kind == 'T':
                offsets[symbol] = int(address, 16) % 64
        (shifted / 'kernels-gcc.s').write_text(re.sub(
            r'^(\t\.type\t(\w+), @function\n)',
            lambda m: '\t.p2align 6\n\t.skip %d, 0x90\n%s' % ((offsets[m[2]] + shift) % 64 or 64, m[1]),
            (kernels / 'kernels-gcc.s').read_text(), flags=re.M))
        run([TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om', shifted / 'kernels-gcc.s',
             '-o', shifted / 'kernels-gcc.o'])
        folder = 'S8-08/align-' + value
        run([sys.executable, m2 / 'build.py', '--out', folder,
             '--reuse-kernels', 'S8-08/align-' + value + '-k',
             '--before', 'S8-08/align-' + value + '-b'])
        print('A/A PAIR ' + folder + '/m2-kernels.mic (' + (' '.join(extra) or 'default')
              + '); card run pending lead', flush=True)
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
    return align() if sys.argv[1:] == ['--align'] else acceptance()


if __name__ == '__main__':
    sys.exit(main())
