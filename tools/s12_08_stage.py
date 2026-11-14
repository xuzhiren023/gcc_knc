"""S12-08 phase-one diagnostics. Build/lint only; never launches card or GCC build."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
OUT = SHARED / 'S12-08'
TC = SHARED / 'toolchain'


def run(args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    if os.environ.get('KNC_GCC_SLOT') != '2':
        raise RuntimeError('S12-08 requires lane gcc2')
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                     ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        path = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                        '-u', __file__], env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), path], env=env)
    OUT.mkdir(exist_ok=True)
    cc = SHARED / 'gcc-build-2/gcc/xgcc'
    flags = ['-B' + str(cc.parent) + '/', '-O2', '-march=knc',
             '--sysroot=' + str(TC / 'sysroot')]
    run([cc, *flags, '--version'])
    source = ROOT / 'tools/s12_08_pressure.c'
    objects = []
    for label, extra in [('base', []), ('scalar', ['-fno-tree-vectorize'])]:
        asm = OUT / (label + '.s')
        run([cc, *flags, *extra, '-DSUFFIX=_' + label, '-Wall', '-Wextra', '-Werror',
             '-fdump-tree-vect-details', '-fdump-rtl-expand', '-fdump-rtl-ira',
             '-fdump-rtl-reload', '-fverbose-asm', '-S', source, '-o', asm], cwd=OUT)
        obj = OUT / (label + '.o')
        run([cc, *flags, '-c', asm, '-o', obj])
        objects.append(obj)
    binary = OUT / 'pressure-diagnostic.mic'
    links = ['-Wl,-rpath-link,' + str(TC / 'sysroot' / p)
             for p in ('lib64', 'usr/lib64')]
    run([cc, *flags, '-fno-tree-vectorize', '-DDRIVER', '-Wall', '-Wextra', '-Werror',
         source, *objects, *links, '-lrt', '-o', binary])
    run([sys.executable, ROOT / 'tools/knc_lint', binary])
    # Capture actual benchmark lowering without modifying or copying upstream source.
    pb = SHARED / 'corpus-build/sources/polybench-c-4.2.1-beta'
    for name in ('ludcmp', 'cholesky'):
        run([cc, *flags, '-DN=512', '-DDATA_TYPE_IS_DOUBLE', '-DPOLYBENCH_DUMP_ARRAYS',
             '-I' + str(pb / 'utilities'), '-include', ROOT / 'tools/corpus/polybench_capture.h',
             '-fdump-tree-vect-details', '-fdump-rtl-expand', '-fdump-rtl-ira',
             '-fdump-rtl-reload', '-fverbose-asm', '-S',
             pb / ('linear-algebra/solvers/' + name + '/' + name + '.c'),
             '-o', OUT / (name + '.s')], cwd=OUT)
    # Transport list, not a content manifest.
    path = subprocess.check_output([str(TC / 'cygwin/bin/cygpath'), '-m', str(binary)],
                                   text=True).strip()
    (OUT / 'files.txt').write_text(path + '\n')
    shell = OUT / 'diagnostic.sh'
    shell.write_text('#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\n'
                     'chmod +x pressure-diagnostic.mic\nexec ./pressure-diagnostic.mic\n')
    run([TC / 'cygwin/bin/bash', '-n', shell])
    print('STAGED', OUT, 'build/lint/shell PASS; native NOT RUN')
    print('LEAD: python tools/card_run --threads 1 --timeout 60 --file-list '
          '.work/_shared/S12-08/files.txt .work/_shared/S12-08/diagnostic.sh')
    return 0


if __name__ == '__main__':
    sys.exit(main())
