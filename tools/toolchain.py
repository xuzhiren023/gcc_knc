#!/usr/bin/env python3
"""Shared compiler maintenance (run builds through tools/run.py).

gcc16: build the shared KNC C/C++/Fortran compilers; do not build target libraries.
rebuild: configure the read-only shared donor, then all-gcc/install-gcc only.
         --install-only resumes installation from the completed shared build.
sysroot: overlay a card-derived tree, if supplied, and restore development files.
         --development-files seeds the retained development input directory once.
verify: check default driver paths and verbose C/Fortran links against card libraries.

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
import time

import gcc_build
import storage

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
# This slot's GCC tree and build, by name inside SHARED (S8-18).
GCC_TREE = Path(storage.gcc_tree(PROJECT)).name
GCC_BUILD = Path(storage.gcc_build_dir(PROJECT)).name
TC = SHARED / 'toolchain'
SYSROOT = TC / 'sysroot'
DEVELOPMENT = ('crt1.o', 'crti.o', 'crtn.o', 'libc.so', 'libc_nonshared.a',
               'libpthread_nonshared.a', 'Scrt1.o', 'gcrt1.o', 'Mcrt1.o')
RUNTIME_LINKS = {
    'm': 'libm.so.6', 'dl': 'libdl.so.2', 'rt': 'librt.so.1',
    'crypt': 'libcrypt.so.1', 'util': 'libutil.so.1', 'resolv': 'libresolv.so.2',
    'nsl': 'libnsl.so.1', 'anl': 'libanl.so.1', 'thread_db': 'libthread_db.so.1',
    'pthread': 'libpthread.so.0',
}
INSTALL_STAGE = '/tmp/knc-stage'


def command(*args, **kwargs):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def gcc16(args):
    """Replace the shared build with the KNC C/Fortran compilers (all-gcc only)."""
    source = SHARED / GCC_TREE
    build = SHARED / GCC_BUILD
    if not (source / 'configure').is_file():
        raise RuntimeError('missing shared GCC source; ask the lead')
    if build.resolve() != SHARED.resolve() / GCC_BUILD or build.is_symlink():
        raise RuntimeError('refusing to clean unexpected build directory: ' + str(build))
    resume = getattr(args, 'resume', False)
    if resume:
        if not (build / 'config.status').is_file():
            raise RuntimeError('missing configured shared GCC build to resume')
    else:
        if build.exists():
            shutil.rmtree(build)
        build.mkdir()
    # As in S0-06, keep host compiler temporaries in the shared area.
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    Path(os.environ['TMPDIR']).mkdir(exist_ok=True)
    flags = [
        '--target=k1om-mpss-linux', '--prefix=' + str(SHARED / 'gcc-install'),
        '--with-sysroot=' + str(SYSROOT),
        '--with-as=' + str(TC / 'cross/bin/k1om-mpss-linux-as'),
        '--with-ld=' + str(TC / 'cross/bin/k1om-mpss-linux-ld'),
        *gcc_build.CONFIGURE_FLAGS, '--disable-bootstrap', '--disable-multilib',
        '--disable-nls', '--without-isl',
        '--disable-libssp', '--disable-libquadmath', '--disable-libquadmath-support',
        '--disable-libsanitizer', '--disable-libitm', '--disable-libcilkrts',
        '--disable-libvtv', '--disable-libmpx', '--disable-libgomp',
    ]
    steps = [('configure', ('bash', source / 'configure', *flags))] if not resume else []
    steps.append(('resumed all-gcc' if resume else 'full all-gcc',
                  ('make', '-j8', 'all-gcc',
                   'CFLAGS=-O2 -g1', 'CXXFLAGS=-O2 -g1')))
    for label, argv in steps:
        start = time.monotonic()
        try:
            command(*argv, cwd=build)
        finally:
            print('MEASURE gcc16 %s: seconds=%.3f' %
                  (label, time.monotonic() - start), flush=True)
    compiler = build / 'gcc/xgcc'
    for flag in ('-dumpmachine', '-print-prog-name=as', '-print-prog-name=ld',
                 '-print-sysroot'):
        command(compiler, flag)


def rebuild(args):
    source = SHARED / 'gcc-donor'
    build = SHARED / 'gcc-donor-build'
    if not (source / 'configure').is_file():
        raise RuntimeError('missing shared gcc-donor source; ask the lead')
    if not os.environ.get('KNC_WINDOWS_INSTALL'):
        raise RuntimeError('run rebuild through Windows Python for the staged overlay')
    if args.install_only:
        if not (build / 'gcc/xgcc.exe').is_file():
            raise RuntimeError('missing completed shared compiler build')
        command('make', 'install-gcc', 'DESTDIR=' + INSTALL_STAGE, cwd=build)
        return
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
    command('make', 'install-gcc', 'DESTDIR=' + INSTALL_STAGE, cwd=build)


def libgcc(args):
    """Build the fork's static target runtime in the existing shared tree."""
    build = SHARED / GCC_BUILD
    if not (build / 'gcc/xgcc.exe').is_file():
        raise RuntimeError('missing shared GCC build; build gcc16 first')
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    command('make', '-j8', 'all-target-libgcc', cwd=build)


def driver(args):
    """Rebuild only xgcc after changing driver specs, not code generation."""
    command('make', '-j8', 'specs', 'CFLAGS=-O2 -g1', 'CXXFLAGS=-O2 -g1',
            cwd=SHARED / GCC_BUILD / 'gcc')


def install_stage(cygpath, env):
    """Resolve and guard the one shared staging tree before copying or deleting."""
    stage = Path(subprocess.check_output(
        [cygpath, '-w', INSTALL_STAGE], env=env, text=True).strip()).resolve()
    expected = (TC / 'cygwin/tmp/knc-stage').resolve()
    if stage != expected or stage.is_symlink():
        raise RuntimeError('unexpected install stage: ' + str(stage))
    print('Install stage: %s -> %s' % (INSTALL_STAGE, stage), flush=True)
    return stage


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
    for runtime in RUNTIME_LINKS.values():
        if not (SYSROOT / 'lib64' / runtime).is_file():
            raise RuntimeError('missing card runtime: ' + str(SYSROOT / 'lib64' / runtime))
    for relative in ('lib', 'usr/lib', 'usr/lib64'):
        (SYSROOT / relative).mkdir(parents=True, exist_ok=True)
    for name in DEVELOPMENT:
        shutil.copy2(development / name, SYSROOT / 'usr/lib64' / name)
        print('Restored ' + str(SYSROOT / 'usr/lib64' / name), flush=True)
    for library, runtime in RUNTIME_LINKS.items():
        link = SYSROOT / 'usr/lib64' / ('lib' + library + '.so')
        # GNU ld roots absolute script paths in its sysroot. Ordinary text files
        # work with both native Windows and Cygwin tools, unlike Cygwin symlinks.
        if link.is_symlink():
            link.unlink()
        group = '/lib64/' + runtime
        if library == 'pthread':
            group += ' /usr/lib64/libpthread_nonshared.a'
        link.write_text('GROUP ( ' + group + ' )\n')
        print('Created ' + str(link), flush=True)


def verify(args):
    command(sys.executable, ROOT / 'tools/doctor')
    (SHARED / 'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SHARED / 'tmp', prefix='donor-link-') as directory:
        probes = (
            ('gcc', 'hello.c', '''#include <stdio.h>
#include <math.h>
#include <pthread.h>
#include <dlfcn.h>
#include <time.h>
static void *worker(void *arg) { return arg; }
int main(int argc, char **argv) {
    pthread_t thread;
    struct timespec now;
    void *handle = dlopen(0, RTLD_NOW);
    if (pthread_create(&thread, 0, worker, argv)) return 1;
    if (pthread_join(thread, 0)) return 2;
    if (clock_gettime(CLOCK_REALTIME, &now)) return 3;
    printf("KNC %f\\n", cos((double)argc));
    return handle ? dlclose(handle) : 4;
}
''', ['-lm', '-lpthread', '-ldl', '-lrt'],
             ('libm.so.6', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1')),
            ('gfortran', 'hello.f90', 'program hello\nprint *, "KNC"\nend program hello\n',
             [], ('libm.so.6',)),
        )
        for driver, filename, text, flags, libraries in probes:
            source = Path(directory) / filename
            source.write_text(text)
            compiler = TC / ('cross/bin/k1om-mpss-linux-' + driver)
            result = subprocess.run([str(compiler), '-v', '-Wl,--trace', str(source),
                                     *flags, '-o', str(source.with_suffix('.mic'))],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            print(result.stdout, flush=True)
            if result.returncode:
                raise RuntimeError('verbose %s link exited %d' % (driver, result.returncode))
            if 'phiweather' in result.stdout.lower():
                raise RuntimeError('verbose %s link still uses PhiWeather' % driver)
            for library in (*libraries, 'libc.so.6', 'ld-linux-k1om.so.2'):
                if str(SYSROOT / 'lib64' / library) not in result.stdout:
                    raise RuntimeError('%s link trace missing card-derived %s' % (driver, library))
            print('PASS default %s link against card-derived libraries' % driver, flush=True)


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
        stage = None
        if arguments[:1] == ['rebuild']:
            stage = install_stage(cygpath, env)
            if stage.exists():
                shutil.rmtree(stage)
            env['KNC_WINDOWS_INSTALL'] = '1'
        result = subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'),
                                  posix(__file__), *arguments], env=env)
        if result == 0 and stage is not None:
            # DESTDIR contains the absolute POSIX prefix as ordinary directories.
            # Overlay only install-gcc's files, retaining the target libraries.
            staged_prefix = stage / posix(TC / 'cross').lstrip('/')
            if not (staged_prefix / 'bin/k1om-mpss-linux-gcc.exe').is_file():
                raise RuntimeError('staged compiler missing: ' + str(staged_prefix))
            print('Overlay %s -> %s' % (staged_prefix, TC / 'cross'), flush=True)
            shutil.copytree(staged_prefix, TC / 'cross', dirs_exist_ok=True)
            shutil.rmtree(stage)
            print('Installed compiler; removed stage; retained target libraries', flush=True)
        return result
    os.environ['PATH'] = ':'.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + ':' + os.environ.get('PATH', '')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=('rebuild', 'sysroot', 'verify', 'gcc16', 'libgcc', 'driver'))
    parser.add_argument('--card-root')
    parser.add_argument('--development-files')
    parser.add_argument('--install-only', action='store_true',
                        help='resume rebuild at staged install-gcc without rebuilding')
    parser.add_argument('--resume', action='store_true',
                        help='resume gcc16 in its existing configured shared build')
    args = parser.parse_args()
    try:
        globals()[args.step](args)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print('FAILED toolchain %s: %s' % (args.step, error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
