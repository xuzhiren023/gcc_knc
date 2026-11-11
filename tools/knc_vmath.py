#!/usr/bin/env python3
"""Build libknc_vmath (ADR-0014 point 3) and its qualification programs, for KNC and the host.

    python tools/knc_vmath.py            build both, lint the KNC outputs
    python tools/knc_vmath.py --out T    build into .work/_shared/T instead of S10-02 (a ticket's
                                         own copy, so that two lanes do not share one archive)
    python tools/knc_vmath.py --install  then copy the KNC archive beside libgcc.a in this lane's
                                         build tree (for xgcc -B) and installed prefix, where the
                                         KNC link spec finds it (S10-03, ADR-0014 point 3)

KNC outputs go to .work/_shared/S10-02/knc (libknc_vmath.a, qualify_f.mic, qualify_d.mic,
qualify_v1.mic), host outputs (Cygwin GCC, x86-64, the same sources and flags) to
.work/_shared/S10-02/host. Card runs
are the lead's: tests/vmath/card_qualify.py (which also runs the host programs). qualify_f is the accepted harness
(tests/acceptance/vecmath_qualify/qualify.c) linked to the library's cores instead of its own
copies; qualify_d is tests/vmath/qualify_d.c. Both take pow's special cases from
tests/vmath/pow_reference.c, not the libm. qualify_v1 is tests/vmath/qualify_v1.c (S10-07): the
host build links MPFR as its exact oracle, the KNC build screens with the card's long double libm.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import storage

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
OUT = SHARED / 'S10-02'
VECMATH = ROOT / 'contrib/knc-vecmath'
LIB = VECMATH / 'libknc_vmath'
ALGORITHMS = VECMATH / 'native/translation/math_algorithms'
ARM_SP = VECMATH / 'native/upstream/arm-optimized-routines-v26.01/math'
ARM_DP = VECMATH / 'native/upstream/arm-optimized-routines-v26.01-dp/math'
FUNCTIONS = ('expf', 'logf', 'powf', 'exp', 'log', 'pow')
LANES = {'expf': 16, 'logf': 16, 'powf': 16, 'exp': 8, 'log': 8, 'pow': 8}
# Library members: our wrappers around the copied cores, and the Arm data tables they read.
MEMBERS = sorted(LIB.glob('vmath_*.c')) + [
    ARM_DP / 'exp_data.c', ARM_DP / 'log_data.c', ALGORITHMS / 'pow_e8/upstream/pow_log_data.c',
    ALGORITHMS / 'powf_e16/upstream/powf_log2_data.c', ARM_SP / 'exp2f_data.c',
    # S10-08: the tables of log2, erf and erfc.
    ARM_SP / 'log2_data.c', ARM_SP / 'aarch64/v_erf_data.c', ARM_SP / 'aarch64/v_erfc_data.c']
# The cores build as a user would build them: -O2 and GCC's default contraction, no fast-math.
LIB_FLAGS = ['-std=gnu11', '-O2', '-Wall', '-I' + str(LIB), '-I' + str(ARM_DP),
             '-I' + str(ALGORITHMS / 'e_width_experiment'), '-I' + str(ALGORITHMS / 'pow_e8'),
             '-I' + str(ALGORITHMS / 'powf_e16'),
             # musl's reducer sources include "libm.h"; this one allows for the x87 (vmath_reducer.c).
             '-I' + str(ALGORITHMS / 'cos_sin_e/native_x87')]
# The harness and its x87 oracle neither vectorize nor contract.
# KNC members also link into shared libraries and, as in libgcc.a, export nothing from them.
KNC_LIB_FLAGS = ['-fPIC', '-fvisibility=hidden']
TEST_FLAGS = ['-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-fno-tree-vectorize',
              '-fno-tree-slp-vectorize', '-ffp-contract=off', '-I' + str(LIB)]
# S10-08: these members take square roots, which must not call libm's sqrt to set errno.
NO_ERRNO = ('vmath_asin.c', 'vmath_cbrt.c')
def command(*args, **kwargs):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    return subprocess.call(list(map(str, args)), **kwargs)


def build(target):
    out = OUT / target
    out.mkdir(parents=True, exist_ok=True)
    if target == 'knc':
        gcc = gcc_build()
        cc = [gcc / 'xgcc', '-B' + str(gcc) + '/', '--sysroot=' + str(TC / 'sysroot'), '-march=knc']
        ar = TC / 'cross/bin/k1om-mpss-linux-ar'
        assembler = [TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om']
        suffix = '.mic'
    else:
        cc, ar, assembler, suffix = ['gcc'], 'ar', None, '.exe'
    errors, objects = 0, []

    def compile_unit(source, flags):
        nonlocal errors
        obj = out / (source.stem + '.o')
        if assembler:
            asm = out / (source.stem + '.s')
            rc = command(*cc, *flags, '-S', source, '-o', asm) or command(*assembler, asm, '-o', obj)
        else:
            rc = command(*cc, *flags, '-c', source, '-o', obj)
        errors += bool(rc)
        return obj

    lib_flags = LIB_FLAGS + (KNC_LIB_FLAGS if target == 'knc' else [])
    objects = [compile_unit(source, lib_flags + (['-fno-math-errno'] if source.name in NO_ERRNO else []))
               for source in MEMBERS]
    tests = {'qualify': compile_unit(ROOT / 'tests/acceptance/vecmath_qualify/qualify.c', TEST_FLAGS),
             'qualify_d': compile_unit(ROOT / 'tests/vmath/qualify_d.c', TEST_FLAGS),
             'pow_reference': compile_unit(ROOT / 'tests/vmath/pow_reference.c', TEST_FLAGS),
             # The host passes 64-byte vectors in memory, which GCC notes with -Wpsabi.
             'qualify_v1': compile_unit(ROOT / 'tests/vmath/qualify_v1.c', TEST_FLAGS + (
                 [] if target == 'knc' else ['-DVMATH_MPFR', '-Wno-psabi']))}
    if errors:
        print('FAIL %s: %d compile steps' % (target, errors))
        return 1
    archive = out / 'libknc_vmath.a'
    if archive.exists():
        archive.unlink()
    if command(ar, 'rcs', archive, *objects):
        return 1
    # The accepted harness calls phi_host_<f>_e16; point those names at the library's cores.
    alias = []
    for f in ('expf', 'logf', 'powf'):
        alias += ['-Wl,-u,__knc_vmath_core_%s_16' % f,
                  '-Wl,--defsym,phi_host_%s_e16=__knc_vmath_core_%s_16' % (f, f)]
    # Both oracles' powl goes through the C99 Annex F table in pow_reference.c (S10-06).
    oracle = [tests['pow_reference'], '-Wl,--wrap=powl']
    exes = [out / (name + suffix) for name in ('qualify_f', 'qualify_d', 'qualify_v1')]
    exact = [] if target == 'knc' else ['-lmpfr', '-lgmp']
    if (command(*cc, tests['qualify'], *oracle, *alias, archive, '-pthread', '-lm', '-o', exes[0]) or
            command(*cc, tests['qualify_d'], *oracle, archive, '-pthread', '-lm', '-o', exes[1]) or
            command(*cc, tests['qualify_v1'], archive, '-pthread', *exact, '-lm', '-o', exes[2])):
        return 1
    if target == 'knc' and command(sys.executable, ROOT / 'tools/knc_lint', *objects, *exes):
        return 1
    print('BUILT %s: %s %s' % (target, archive, ' '.join(map(str, exes))))
    return 0


def gcc_build():
    return SHARED / storage.GCC_SLOTS[storage.gcc_slot()][1] / 'gcc'


def install():
    archive = OUT / 'knc/libknc_vmath.a'
    root, libdir = prefix()
    for directory in (gcc_build(), libdir):
        if not directory.is_dir():
            print('SKIP install: no ' + str(directory))
            continue
        shutil.copyfile(archive, directory / archive.name)
        print('INSTALLED ' + str(directory / archive.name))
    return 0


def prefix():
    """This lane's installed compiler (tools/s7_09_checks.py install) and its libgcc directory."""
    slot = storage.gcc_slot()
    version = (SHARED / storage.GCC_SLOTS[slot][0] / 'gcc/BASE-VER').read_text().strip()
    root = SHARED / ('gcc-knc-' + version + ('' if slot == '1' else '-' + slot))
    return root, root / 'lib/gcc/k1om-mpss-linux' / version


def t2(runner):
    """S10-03: tests/t2/knc-vmath-loop.c built with the installed driver and no library flag but
    -lm, staged for the card. The vector object must call the six entry points, the scalar one
    none, and the link must take libknc_vmath.a from the prefix by itself."""
    root, libdir = prefix()
    driver = root / 'bin/k1om-mpss-linux-gcc'
    source = ROOT / 'tests/t2/knc-vmath-loop.c'
    output = SHARED / 'S10-03'
    output.mkdir(exist_ok=True)
    elf = output / 'vmath-loop.mic'
    elf.unlink(missing_ok=True)
    wanted = {'__knc_vmath_%s_%d' % (f, LANES[f]) for f in FUNCTIONS}
    objects, failures = [], []
    for role, flags, calls in (('vector', ['-fno-math-errno', '-DVMATH_VECTOR'], wanted),
                               ('scalar', [], set())):
        obj = runner.out / ('vmath-loop-' + role + '.o')
        compiled = runner.command(driver, '-O2', '-march=knc', *flags,
                                  '--sysroot=' + str(runner.sysroot), '-c', source, '-o', obj,
                                  check=False)
        if compiled.returncode or compiled.stdout.strip():
            failures.append(role + ' compile: ' + compiled.stdout[-1800:])
            continue
        found = set(re.findall(r'\b__knc_vmath_\w+', runner.command(runner.tool('nm'), '-u', obj)))
        if found != calls:
            failures.append('%s object calls %s, expected %s'
                            % (role, sorted(found) or 'no entry point', sorted(calls) or 'none'))
        objects.append(obj)
    if not failures:
        linked = runner.command(driver, '--sysroot=' + str(runner.sysroot), *objects, '-lm',
                                '-o', elf, '-Wl,--trace', check=False)
        lint = linked if linked.returncode else runner.command(
            sys.executable, ROOT / 'tools/knc_lint', elf, check=False)
        if lint.returncode:
            failures.append('link or lint: ' + lint.stdout[-1800:])
            elf.unlink(missing_ok=True)
        else:
            archives = set(re.findall(r'^\(?(\S*libknc_vmath\.a)\)?', linked.stdout, re.M))
            if not archives or any(Path(a).resolve() != (libdir / 'libknc_vmath.a').resolve()
                                   for a in archives):
                failures.append('libknc_vmath.a not taken from %s: %s' % (libdir, sorted(archives)))
            runner.t2_abi(elf, linked.stdout)
    runner.result('t2 knc-vmath-loop: six loops call libknc_vmath, linked with no library flag',
                  failures)


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--install', action='store_true',
                        help='copy the KNC archive into the build tree and the installed prefix')
    parser.add_argument('--out', default=OUT.name, help='output folder under .work/_shared')
    args = parser.parse_args()
    OUT = SHARED / args.out
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = str(TC / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())],
                                         env=env, universal_newlines=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script] + sys.argv[1:], env=env)
    os.environ['PATH'] = ':'.join(map(str, (TC / 'cross/bin', TC / 'cygwin/bin'))) + ':' + os.environ['PATH']
    host = build('host')
    return build('knc') or host or (install() if args.install else 0)


if __name__ == '__main__':
    sys.exit(main())
