#!/usr/bin/env python3
"""S10-11 host regression: reproduce KNC's scalar x87 evaluation, no card job.

Run through tools/run.py. SSE is the existing host control; x87 uses the
library build's existing flags. The standard-excess-precision control tests
whether honoring C assignments/casts repairs the compensated arithmetic.
Also compile the affected members with lane 2's installed GCC-KNC prefix
for assembly evidence. No shared GCC build or installed archive is modified.
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = str(TC / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())],
            env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    sys.path.insert(0, str(ROOT / 'tools'))
    import knc_vmath as build
    os.environ['PATH'] = ':'.join(map(str, (TC / 'cross/bin', TC / 'cygwin/bin'))) + ':' + os.environ['PATH']
    out = SHARED / 'S10-11'
    out.mkdir(exist_ok=True)
    members = ['vmath_sincos', 'vmath_tan', 'vmath_atan', 'vmath_reducer']

    def run(*args):
        subprocess.run(list(map(str, args)), check=True)

    # The driver retains binary64 SSE evaluation and the same vector ABI.
    driver = out / 'card_rounding.o'
    run('gcc', *build.TEST_FLAGS, '-Wno-psabi', '-c',
        ROOT / 'tests/vmath/card_rounding.c', '-o', driver)
    failed = False
    for name, flags in [('sse', []), ('x87', ['-mfpmath=387']),
                        ('x87-standard', ['-mfpmath=387', '-fexcess-precision=standard'])]:
        objects = []
        for member in members:
            obj = out / (member + '.o')
            run('gcc', *build.LIB_FLAGS, '-Wno-psabi', *flags, '-c',
                build.LIB / (member + '.c'), '-o', obj)
            objects.append(obj)
        exe = out / 'card_rounding.exe'
        run('gcc', driver, *objects, '-lmpfr', '-lgmp', '-lm', '-o', exe)
        print('MODE ' + name, flush=True)
        failed |= subprocess.call([str(exe)]) != 0
    prefix = SHARED / 'gcc-knc-16.2.0-2/bin/k1om-mpss-linux-gcc'
    for member in members + ['vmath_cbrt']:
        run(prefix, '-march=knc', '--sysroot=' + str(TC / 'sysroot'),
            *build.LIB_FLAGS, *build.KNC_LIB_FLAGS,
            *(['-fno-math-errno'] if member == 'vmath_cbrt' else []),
            '-S', build.LIB / (member + '.c'), '-o', out / (member + '.s'))
    print('GCC-KNC lane 2 assembly: ' + str(out), flush=True)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
