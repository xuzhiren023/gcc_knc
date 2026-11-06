"""Compile/lint the M2 suite; execution on the card is lead-only.

Invoke through tools/run.py. Outputs overwrite .work/_shared/S6-02.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'


def command(*args):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    return subprocess.call(list(map(str, args)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('all', 'positive', 'negative'), default='all', nargs='?')
    parser.add_argument('--out', default='S6-02', help='folder under .work/_shared for the outputs')
    parser.add_argument('--before', metavar='FOLDER', help='link FOLDER/kernels-gcc.o as gcc_before')
    parser.add_argument('--before-first', action='store_true', help='reverse GCC object link order')
    parser.add_argument('--reuse-kernels', default=None, metavar='FOLDER',
                        help='take kernels-gcc.{s,o} and kernels-x87.{s,o} from this folder under '
                             '.work/_shared instead of compiling them (when xgcc has changed and '
                             'only the driver is under test)')
    args = parser.parse_args()
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = str(TC / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())],
            env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script,
                                args.mode, '--out', args.out]
                               + (['--reuse-kernels', args.reuse_kernels] if args.reuse_kernels else [])
                               + (['--before', args.before] if args.before else [])
                               + (['--before-first'] if args.before_first else []),
                               env=env)
    os.environ['PATH'] = ':'.join(map(str, (TC / 'cross/bin', TC / 'cygwin/bin'))) + ':' + os.environ['PATH']
    out = SHARED / args.out
    if args.before and out.resolve() == (SHARED / args.before).resolve():
        parser.error('--out must differ from --before to preserve the baseline objects')
    out.mkdir(exist_ok=True)
    build = SHARED / 'gcc-build/gcc'
    cc = [build / 'xgcc', '-B' + str(build) + '/',
          '--sysroot=' + str(TC / 'sysroot'), '-march=knc']
    assembler = TC / 'cross/bin/k1om-mpss-linux-as'
    if command(*cc, '--version') or command(assembler, '--version'):
        return 2
    flags = ['-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-ffp-contract=fast']
    if args.before:
        flags.append('-DWITH_BEFORE')
    elif args.before_first:
        parser.error('--before-first requires --before')
    scalar = ['-fno-tree-vectorize', '-fno-tree-slp-vectorize']
    oracle = [*scalar, '-ffp-contract=off']
    variants = ['positive', 'negative'] if args.mode == 'all' else [args.mode]
    units = [('kernels-gcc', 'kernels.c', ['-DBUILD=gcc', '-ftree-vectorize']),
             ('kernels-x87', 'kernels.c', ['-DBUILD=x87', *scalar]),
             ('timing', 'timing.c', oracle)]
    for variant in variants:
        units.append(('driver-' + variant, 'driver.c',
                      [*oracle, *(['-DNEGATIVE_CONTROL'] if variant == 'negative' else [])]))
    errors = 0
    if args.reuse_kernels:
        source_dir = SHARED / args.reuse_kernels
        for name in ('kernels-gcc', 'kernels-x87'):
            for suffix in ('.s', '.o'):
                print('+ copy %s -> %s' % (source_dir / (name + suffix), out / (name + suffix)), flush=True)
                if (source_dir / (name + suffix)).resolve() != (out / (name + suffix)).resolve():
                    shutil.copyfile(source_dir / (name + suffix), out / (name + suffix))
        units = [u for u in units if not u[0].startswith('kernels-')]
    for name, source, extra in units:
        assembly = out / (name + '.s')
        rc = command(*cc, *flags, *extra, '-pthread', '-S', HERE / source, '-o', assembly)
        errors += bool(rc)
        if not rc:
            errors += bool(command(assembler, '--march=k1om', assembly, '-o', out / (name + '.o')))
    for name in ('imci', 'negative'):
        errors += bool(command(assembler, '--march=k1om', HERE / (name + '.s'), '-o', out / (name + '.o')))
    if args.before:
        renames = []
        for kernel in ('affine_f32', 'affine_f64', 'stencil1', 'stencil2', 'short', 'mat8', 'mat16'):
            renames.extend(['--redefine-sym', 'm2_%s_gcc=m2_%s_gccbefore' % (kernel, kernel)])
        errors += bool(command(TC / 'cross/bin/k1om-mpss-linux-objcopy', *renames,
                               SHARED / args.before / 'kernels-gcc.o', out / 'kernels-gccbefore.o'))
    if errors:
        print('FAIL: %d compile/assembly steps; no binaries linked' % errors)
        return 1
    common = [out / (name + '.o') for name in ('kernels-gcc', 'kernels-x87', 'timing', 'imci', 'negative')]
    if args.before:
        common.insert(0 if args.before_first else 1, out / 'kernels-gccbefore.o')
    for variant in variants:
        exe = out / ('m2-kernels.mic' if variant == 'positive' else 'm2-negative.mic')
        rc = command(*cc, out / ('driver-' + variant + '.o'), *common, '-pthread', '-lrt', '-o', exe)
        errors += bool(rc)
        if not rc:
            lint = command(sys.executable, ROOT / 'tools/knc_lint', exe)
            errors += bool(lint)
            if not lint:
                print('BUILT and LINTED (NOT executed on card): ' + str(exe))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
