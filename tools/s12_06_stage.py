"""Build phase-one diagnostics only. Never starts card jobs or builds GCC."""
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
OUT = SHARED / 'S12-06'
TC = SHARED / 'toolchain'


def run(args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                     ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', __file__], env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    OUT.mkdir(exist_ok=True)
    source = ROOT / 'tools/s12_06_scalar.c'
    transform = ROOT / 'tools/s12_06_transform.F90'
    sysroot = TC / 'sysroot'
    links = ['-Wl,-rpath-link,' + str(sysroot / p) for p in ('lib64', 'usr/lib64')]
    binaries = []
    for label, prefix in [('donor', TC / 'cross'), ('knc', SHARED / 'gcc-knc-16.2.0')]:
        cc = prefix / 'bin/k1om-mpss-linux-gcc'
        fc = prefix / 'bin/k1om-mpss-linux-gfortran'
        flags = ['-O2', '--sysroot=' + str(sysroot)]
        if label == 'knc':
            flags += ['-march=knc']
        run([cc, '--version'])
        controls = OUT / (label + '-controls.o')
        run([cc, *flags, '-fPIC', '-c', ROOT / 'tools/s12_06_controls.S', '-o', controls])
        objects = [controls]
        for suffix, defines in [('kernels', []), ('callees', ['-DCALLEE'])]:
            assembly = OUT / (label + '-' + suffix + '.s')
            obj = assembly.with_suffix('.o')
            run([cc, *flags, '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fPIC',
                 *defines, '-S', source, '-o', assembly])
            run([cc, *flags, '-c', assembly, '-o', obj])
            objects.append(obj)
        for mode, name, boundary in [(1, 'log', ''), (2, 'table', ''),
                                     (3, 'identity', 'identity_boundary'),
                                     (4, 'memory', 'memory_boundary')]:
            assembly = OUT / (label + '-transform-' + name + '.s')
            obj = assembly.with_suffix('.o')
            defines = ['-DMODE=' + str(mode), '-DTRANSFORM=transform_' + name,
                       '-DENTRY="transform_' + name + '"']
            if boundary:
                defines += ['-DBOUNDARY="' + boundary + '"']
            run([fc, *flags, '-fPIC', *defines, '-S', transform, '-o', assembly])
            run([cc, *flags, '-c', assembly, '-o', obj])
            objects.append(obj)
        library = OUT / ('scalar-' + label + '.so')
        run([cc, *flags, '-shared', *objects, *links, '-lm', '-o', library])
        binaries.append(library)
        if label == 'knc':
            binary = OUT / 'scalar-diagnostic.mic'
            run([cc, *flags, '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-DDRIVER',
                 source, *links, '-pthread', '-ldl', '-lm', '-lrt', '-o', binary])
            binaries.append(binary)
    run([sys.executable, ROOT / 'tools/knc_lint', *binaries])
    objdump = TC / 'cross/bin/k1om-mpss-linux-objdump'
    readelf = TC / 'cross/bin/k1om-mpss-linux-readelf'
    for binary in binaries:
        dynamic = subprocess.check_output([str(readelf), '-d', str(binary)], text=True)
        unexpected = set(re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic)) - {
            'libc.so.6', 'libm.so.6', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1'}
        if unexpected:
            raise RuntimeError('unstaged dependencies: ' + str(unexpected))
        with binary.with_suffix('.asm').open('w') as out:
            run([objdump, '-d', binary], stdout=out)
    # A file list is transport input, not a content/provenance manifest.
    windows_paths = [subprocess.check_output([str(TC / 'cygwin/bin/cygpath'), '-m', str(p)],
                                            text=True).strip() for p in binaries]
    (OUT / 'files.txt').write_text(''.join(p + '\n' for p in windows_paths))
    shell = OUT / 'diagnostic.sh'
    shell.write_text('#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\n'
                     'chmod +x scalar-diagnostic.mic\nexec ./scalar-diagnostic.mic\n')
    run([TC / 'cygwin/bin/bash', '-n', shell])
    print('STAGED', OUT, 'build/lint/dependencies/shell PASS; native NOT RUN')
    print('LEAD: python tools/card_run --threads 1 --timeout 1500 --file-list '
          '.work/_shared/S12-06/files.txt .work/_shared/S12-06/diagnostic.sh')
    return 0


if __name__ == '__main__':
    sys.exit(main())
