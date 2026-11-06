"""Compile/lint the vector math qualification harness (ADR-0011); card runs are lead-only.

Outputs go to .work/_shared/vecmath-qualify.
"""
import argparse
import os
from pathlib import Path
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
    parser.parse_args()
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = str(TC / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())],
            env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    os.environ['PATH'] = ':'.join(map(str, (TC / 'cross/bin', TC / 'cygwin/bin'))) + ':' + os.environ['PATH']
    out = SHARED / 'vecmath-qualify'
    out.mkdir(exist_ok=True)
    build = SHARED / 'gcc-build/gcc'
    cc = [build / 'xgcc', '-B' + str(build) + '/',
          '--sysroot=' + str(TC / 'sysroot'), '-march=knc']
    assembler = TC / 'cross/bin/k1om-mpss-linux-as'
    algorithms = ROOT / 'contrib/knc-vecmath/native/translation/math_algorithms'
    arm = ROOT / 'contrib/knc-vecmath/native/upstream/arm-optimized-routines-v26.01-dp/math'
    # The cores build as a user would build them (-O2, GCC's default contraction); the harness and
    # its x87 oracle do not vectorize or contract.
    units = [('expf', algorithms / 'e_width_experiment/e_expf.c', ['-O2']),
             ('logf', algorithms / 'e_width_experiment/e_logf.c', ['-O2']),
             ('powf', algorithms / 'powf_e16/powf_e16.c', ['-O2', '-I' + str(arm)]),
             ('powf_log2_data', algorithms / 'powf_e16/upstream/powf_log2_data.c', ['-O2', '-I' + str(arm)]),
             ('exp2f_data', arm.parent.parent / 'arm-optimized-routines-v26.01/math/exp2f_data.c',
              ['-O2', '-I' + str(arm)]),
             ('qualify', HERE / 'qualify.c', ['-O2', '-Wextra', '-Werror', '-fno-tree-vectorize',
                                              '-fno-tree-slp-vectorize', '-ffp-contract=off'])]
    errors = 0
    for name, source, extra in units:
        assembly = out / (name + '.s')
        rc = command(*cc, '-std=gnu11', '-Wall', *extra, '-pthread', '-S', source, '-o', assembly)
        errors += bool(rc)
        if not rc:
            errors += bool(command(assembler, '--march=k1om', assembly, '-o', out / (name + '.o')))
    if errors:
        print('FAIL: %d compile/assembly steps; nothing linked' % errors)
        return 1
    exe = out / 'qualify.mic'
    rc = command(*cc, *(out / (n + '.o') for n in ('qualify', 'expf', 'logf', 'powf',
                                                  'powf_log2_data', 'exp2f_data')),
                 '-pthread', '-lm', '-o', exe)
    if rc:
        return 1
    if command(sys.executable, ROOT / 'tools/knc_lint', exe):
        return 1
    print('BUILT and LINTED (NOT executed on card): ' + str(exe))
    return 0


if __name__ == '__main__':
    sys.exit(main())
