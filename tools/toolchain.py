#!/usr/bin/env python3
"""Shared donor toolchain maintenance (run builds through tools/run.py).

rebuild: configure the read-only shared donor, then all-gcc/install-gcc only.
sysroot: overlay a card-derived tree, if supplied, and restore development files.
         --development-files seeds the retained development input directory once.
verify: check default driver paths and a verbose C link against the card libc.

Example: python tools/run.py --name donor-rebuild --inputs tools/toolchain.py --
         python tools/toolchain.py rebuild
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
SYSROOT = TC / 'sysroot'
DEVELOPMENT = ('crt1.o', 'crti.o', 'crtn.o', 'libc.so', 'libc_nonshared.a')


def command(*args, **kwargs):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def rebuild(args):
    source = SHARED / 'gcc-donor'
    build = SHARED / 'gcc-donor-build'
    if not (source / 'configure').is_file():
        raise RuntimeError('missing shared gcc-donor source; ask the lead')
    # Configure caches from an earlier host attempt must not survive a rebuild.
    expected = SHARED.resolve() / 'gcc-donor-build'
    if build.resolve() != expected or build.is_symlink():
        raise RuntimeError('refusing to clean unexpected build directory: ' + str(build))
    if build.exists():
        shutil.rmtree(build)
    build.mkdir()
    # GCC 5 libiberty probes dup3 successfully on modern Cygwin, but its host
    # source lacks the declaration. Use its existing dup2 fallback (S0-08).
    os.environ['ac_cv_func_dup3'] = 'no'
    print('Host configure override: ac_cv_func_dup3=no (libiberty dup2 fallback)',
          flush=True)
    # GCC 5 uses bool increment in reload1.c, removed in the modern host's
    # default C++17 mode. This flag applies only to building host executables.
    os.environ['CXXFLAGS'] = '-g -O2 -std=gnu++98'
    print('Host CXXFLAGS: ' + os.environ['CXXFLAGS'], flush=True)
    # Installed donor's final configure invocation, with only its source location,
    # prefix, sysroot, assembler and linker relocated (S0-08 lead instruction).
    flags = [
        '--target=k1om-mpss-linux', '--prefix=' + str(TC / 'cross'),
        '--with-sysroot=' + str(SYSROOT),
        '--with-as=' + str(TC / 'cross/bin/k1om-mpss-linux-as'),
        '--with-ld=' + str(TC / 'cross/bin/k1om-mpss-linux-ld'),
        '--enable-languages=c,c++,fortran', '--enable-threads=posix',
        '--disable-multilib', '--disable-bootstrap', '--disable-nls',
        '--disable-libssp', '--disable-libquadmath', '--disable-libquadmath-support',
        '--disable-libsanitizer', '--disable-libitm', '--disable-libcilkrts',
        '--disable-libvtv', '--disable-libmpx', '--disable-libgomp', '--without-isl',
        '--with-system-zlib', '--enable-shared', '--enable-checking=release',
    ]
    command('bash', source / 'configure', *flags, cwd=build)
    command('make', '-j8', 'all-gcc', cwd=build)
    command('make', 'install-gcc', cwd=build)


def sysroot(args):
    development = TC / 'sysroot-development'
    if args.development_files:
        origin = Path(args.development_files).resolve()
        # Keep the existing donor development objects as repeatable shared inputs;
        # runtime libc and loader always come from the card-derived tree.
        for name in DEVELOPMENT:
            if not (origin / name).is_file():
                raise RuntimeError('missing development input: ' + str(origin / name))
        development.mkdir(exist_ok=True)
        for name in DEVELOPMENT:
            shutil.copy2(origin / name, development / name)
    for name in DEVELOPMENT:
        if not (development / name).is_file():
            raise RuntimeError('missing %s; seed with --development-files <donor usr/lib64>' %
                               (development / name))
    if args.card_root:
        origin = Path(args.card_root).resolve()
        if origin == SYSROOT.resolve():
            raise RuntimeError('--card-root must be a separate card-derived input tree')
        for relative in ('usr/include', 'lib64', 'usr/lib64'):
            if not (origin / relative).is_dir():
                raise RuntimeError('missing card-derived directory: ' + str(origin / relative))
        for relative in ('usr/include', 'lib64', 'usr/lib64'):
            shutil.copytree(origin / relative, SYSROOT / relative, dirs_exist_ok=True)
    for relative in ('usr/include', 'lib64'):
        if not (SYSROOT / relative).is_dir():
            raise RuntimeError('missing card sysroot; supply --card-root <extracted card tree>')
    for relative in ('lib', 'usr/lib', 'usr/lib64'):
        (SYSROOT / relative).mkdir(parents=True, exist_ok=True)
    for name in DEVELOPMENT:
        shutil.copy2(development / name, SYSROOT / 'usr/lib64' / name)
        print('Restored ' + str(SYSROOT / 'usr/lib64' / name), flush=True)


def verify(args):
    command(sys.executable, ROOT / 'tools/doctor')
    cc = TC / 'cross/bin/k1om-mpss-linux-gcc'
    (SHARED / 'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SHARED / 'tmp', prefix='donor-link-') as directory:
        source = Path(directory) / 'hello.c'
        source.write_text('#include <stdio.h>\nint main(void) { return puts("KNC"); }\n')
        result = subprocess.run([str(cc), '-v', '-Wl,--trace', str(source),
                                 '-o', str(Path(directory) / 'hello.mic')],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(result.stdout, flush=True)
        if result.returncode:
            raise RuntimeError('verbose C link exited %d' % result.returncode)
        if 'phiweather' in result.stdout.lower():
            raise RuntimeError('verbose C link still uses PhiWeather')
        for library in ('libc.so.6', 'ld-linux-k1om.so.2'):
            if str(SYSROOT / 'lib64' / library) not in result.stdout:
                raise RuntimeError('link trace missing card-derived ' + library)
    print('PASS default paths and verbose C link against card-derived libc')


def main():
    # Run the maintenance steps with the shared Cygwin host tools and POSIX paths.
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        cygpath = str(TC / 'cygwin/bin/cygpath.exe')
        def posix(path):
            return subprocess.check_output([cygpath, '-u', str(path)], env=env, text=True).strip()
        arguments = sys.argv[1:]
        for flag in ('--card-root', '--development-files'):
            if flag in arguments:
                index = arguments.index(flag) + 1
                arguments[index] = posix(arguments[index])
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'),
                                posix(__file__), *arguments], env=env)
    os.environ['PATH'] = ':'.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + ':' + os.environ.get('PATH', '')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=('rebuild', 'sysroot', 'verify'))
    parser.add_argument('--card-root')
    parser.add_argument('--development-files')
    args = parser.parse_args()
    try:
        globals()[args.step](args)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print('FAILED toolchain %s: %s' % (args.step, error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
