#!/usr/bin/env python3
"""Stage S12-30's native routes and exercise their host model once.

No GCC checkout/build or card execution. Native slots share IMCI assembly.
The host model validates C control flow only, never IMCI behavior/performance.
"""
import os
from pathlib import Path
import subprocess
import sys

import corpus

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
OUT = SHARED / 'S12-30'
SOURCE = ROOT / 'tools/s12_30_precision.c'


def run(*args):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=OUT, check=True)


def build(host=False):
    objects = []
    stem = 'host-' if host else ''
    for name, compiler in [('donor', corpus.DONOR), ('knc', corpus.KNC),
                           ('fast', corpus.KNC)]:
        cc = TC/'cygwin/bin/gcc' if host else corpus.compiler_path(compiler)
        flags = ['-O2', '-std=gnu99', '-ffp-contract=' + ('fast' if name == 'fast' else 'off')]
        if host:
            flags += ['-mfpmath=387', '-fexcess-precision=fast', '-DHOST_MODEL']
        elif name != 'donor':
            flags += ['-march=knc']
        # Explicit assembly supplies gathers to both scalar-only donor and KNC.
        flags += ['-fno-tree-vectorize', '-DPREFIX=' + name + '_']
        if name == 'donor':
            flags += ['-DSEED_TREES']
        obj = OUT/(stem+name+'-precision.o')
        if host:
            run(cc, *flags, '-c', SOURCE, '-o', obj)
        else:
            run(cc, '--version')
            asm = obj.with_suffix('.s')
            run(cc, *flags, '-S', SOURCE, '-o', asm)
            run(TC/'cross/bin/k1om-mpss-linux-as', '--march=k1om', asm, '-o', obj)
        objects.append(obj)
    cc = TC/'cygwin/bin/gcc' if host else corpus.compiler_path(corpus.DONOR)
    binary = OUT/('host-precision.exe' if host else 'precision-gate')
    flags = ['-O2', '-std=gnu99', '-ffp-contract=off', '-fno-tree-vectorize']
    if host:
        flags += ['-mfpmath=387', '-fexcess-precision=fast', '-DHOST_MODEL']
    run(cc, *flags, '-DDRIVER', SOURCE, *objects,
        *([] if host else corpus.link_paths()), '-lrt', '-lm', '-o', binary)
    if not host:
        run(sys.executable, ROOT/'tools/knc_lint', binary)
    return binary


def main():
    if sys.platform != 'cygwin':
        raise RuntimeError('use shared Cygwin python3')
    OUT.mkdir(exist_ok=True)
    os.environ['PATH'] = ':'.join(map(str, [TC/'cross/bin', TC/'cygwin/bin', os.environ['PATH']]))
    binary = build()
    print('STAGED:', binary, '; lead card_run --threads 1 --timeout 1150; binary argument: 12345', flush=True)
    host = build(host=True)
    # The approved red already demonstrated both seeded tree failures once.
    print('HOST MODEL ONLY: all routes; native correctness/timing pending', flush=True)
    return subprocess.run([str(host), '12345', '--correctness'], cwd=OUT).returncode


if __name__ == '__main__':
    sys.exit(main())
