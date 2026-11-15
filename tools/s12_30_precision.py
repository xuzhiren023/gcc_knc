#!/usr/bin/env python3
"""Stage the S12-30 legality probe, then run its host x87 model once.

An exit of 1 from the model is the intended red result: retaining addition
order alone does not establish bit identity after product materialization.
Only the lead may execute the staged card binary. No GCC checkout is used.
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


def main():
    if sys.platform != 'cygwin':
        raise RuntimeError('use shared Cygwin python3')
    OUT.mkdir(exist_ok=True)
    os.environ['PATH'] = ':'.join(map(str, [TC/'cross/bin', TC/'cygwin/bin',
                                           os.environ['PATH']]))
    objects = []
    for name, compiler in [('donor', corpus.DONOR), ('knc', corpus.KNC)]:
        cc = corpus.compiler_path(compiler)
        flags = ['-O2'] + (['-march=knc'] if name == 'knc' else [])
        asm = OUT / (name + '-precision.s')
        obj = asm.with_suffix('.o')
        run(cc, '--version')
        run(cc, *flags, '-DPREFIX=' + name + '_', '-S', SOURCE, '-o', asm)
        run(TC/'cross/bin/k1om-mpss-linux-as', '--march=k1om', asm, '-o', obj)
        objects.append(obj)
    binary = OUT/'precision-gate'
    run(corpus.compiler_path(corpus.DONOR), '-O2', '-DDRIVER', SOURCE,
        *objects, *corpus.link_paths(), '-o', binary)
    run(sys.executable, ROOT/'tools/knc_lint', binary)
    print('STAGED:', binary, '; lead card_run --threads 1 --timeout 30', flush=True)
    print('Native execution pending; expected runtime is below one second.', flush=True)

    # Explicitly model the retained x87 intermediates seen in the saved
    # S12-07 assemblies. This host result is not a native KNC result.
    cc = TC/'cygwin/bin/gcc'
    obj = OUT/'host-precision.o'
    run(cc, '-O2', '-mfpmath=387', '-fexcess-precision=fast',
        '-fno-tree-vectorize', '-DPREFIX=host_', '-c', SOURCE, '-o', obj)
    host = OUT/'host-precision.exe'
    run(cc, '-O2', '-DDRIVER', '-DHOST_MODEL', SOURCE, obj, '-o', host)
    print('HOST MODEL ONLY:', flush=True)
    return subprocess.run([str(host)], cwd=OUT).returncode


if __name__ == '__main__':
    sys.exit(main())
