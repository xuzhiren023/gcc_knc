#!/usr/bin/env python3
"""Build libknc_vmath v0 (ADR-0014 point 3) and its qualification programs, for KNC and the host.

    python tools/knc_vmath.py            build both, lint the KNC outputs

KNC outputs go to .work/_shared/S10-02/knc (libknc_vmath.a, qualify_f.mic, qualify_d.mic), host
outputs (Cygwin GCC, x86-64, the same sources and flags) to .work/_shared/S10-02/host. Card runs
are the lead's: tests/vmath/card_qualify.py (which also runs the host programs). qualify_f is the accepted harness
(tests/acceptance/vecmath_qualify/qualify.c) linked to the library's cores instead of its own
copies; qualify_d is tests/vmath/qualify_d.c.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

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
# Library members: our six wrappers around the copied cores, and the Arm data tables they read.
MEMBERS = [LIB / ('vmath_%s.c' % f) for f in FUNCTIONS] + [
    ARM_DP / 'exp_data.c', ARM_DP / 'log_data.c', ALGORITHMS / 'pow_e8/upstream/pow_log_data.c',
    ALGORITHMS / 'powf_e16/upstream/powf_log2_data.c', ARM_SP / 'exp2f_data.c']
# The cores build as a user would build them: -O2 and GCC's default contraction, no fast-math.
LIB_FLAGS = ['-std=gnu11', '-O2', '-Wall', '-I' + str(LIB), '-I' + str(ARM_DP),
             '-I' + str(ALGORITHMS / 'e_width_experiment'), '-I' + str(ALGORITHMS / 'pow_e8'),
             '-I' + str(ALGORITHMS / 'powf_e16')]
# The harness and its x87 oracle neither vectorize nor contract.
TEST_FLAGS = ['-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-fno-tree-vectorize',
              '-fno-tree-slp-vectorize', '-ffp-contract=off', '-I' + str(LIB)]
def command(*args, **kwargs):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    return subprocess.call(list(map(str, args)), **kwargs)


def build(target):
    out = OUT / target
    out.mkdir(parents=True, exist_ok=True)
    if target == 'knc':
        gcc = SHARED / 'gcc-build/gcc'
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

    objects = [compile_unit(source, LIB_FLAGS) for source in MEMBERS]
    tests = {'qualify': compile_unit(ROOT / 'tests/acceptance/vecmath_qualify/qualify.c', TEST_FLAGS),
             'qualify_d': compile_unit(ROOT / 'tests/vmath/qualify_d.c', TEST_FLAGS)}
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
    exes = [out / ('qualify_f' + suffix), out / ('qualify_d' + suffix)]
    if (command(*cc, tests['qualify'], *alias, archive, '-pthread', '-lm', '-o', exes[0]) or
            command(*cc, tests['qualify_d'], archive, '-pthread', '-lm', '-o', exes[1])):
        return 1
    if target == 'knc' and command(sys.executable, ROOT / 'tools/knc_lint', *objects, *exes):
        return 1
    print('BUILT %s: %s %s' % (target, archive, ' '.join(map(str, exes))))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args()
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = str(TC / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())],
                                         env=env, universal_newlines=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script] + sys.argv[1:], env=env)
    os.environ['PATH'] = ':'.join(map(str, (TC / 'cross/bin', TC / 'cygwin/bin'))) + ':' + os.environ['PATH']
    host = build('host')
    return build('knc') or host


if __name__ == '__main__':
    sys.exit(main())
