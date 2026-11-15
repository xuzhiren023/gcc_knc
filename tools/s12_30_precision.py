#!/usr/bin/env python3
"""Stage S12-30's native red and exercise the fixture on the host once.

No GCC checkout/build or card execution. A/B/A+B missing slots are failures.
The host run validates the fixture only, never native behavior or performance.
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
            flags += ['-mfpmath=387', '-fexcess-precision=fast']
        elif name != 'donor':
            flags += ['-march=knc']
        # Scalar baseline only; green will use explicit gather/multiply
        # operations for A, retaining the ordered fold.
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
        flags += ['-mfpmath=387', '-fexcess-precision=fast']
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
    print('HOST FIXTURE ONLY: seed a balanced tree at both accumulator precisions', flush=True)
    mutation = subprocess.run([str(host), '12345', '--seed-tree'], cwd=OUT, capture_output=True, text=True)
    print(mutation.stdout, end='', flush=True)
    if mutation.returncode != 1 or 'tree53_caught=1 tree64_caught=1' not in mutation.stdout:
        raise RuntimeError('order oracle failed to catch seeded tree folds: ' + mutation.stderr)
    print('HOST FIXTURE ONLY: absent implementations must fail; native pending', flush=True)
    return subprocess.run([str(host), '12345', '--correctness'], cwd=OUT).returncode


if __name__ == '__main__':
    sys.exit(main())
