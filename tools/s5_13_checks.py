#!/usr/bin/env python3
"""S5-13 acceptance builds and before/after torture; run through tools/run.py."""
import subprocess
import sys

import s5_12_checks as checks

checks.OUT = checks.SHARED / 's5-13'


def acceptance():
    cc = [str(checks.BUILD / 'xgcc'), '-B' + str(checks.BUILD) + '/',
          '-march=knc', '--sysroot=' + str(checks.TC / 'sysroot')]
    source = checks.ROOT / 'tests/acceptance/s5_ops'
    dest = checks.OUT / 's5_ops'
    dest.mkdir(exist_ok=True)

    def run(args):
        print('+ ' + ' '.join(map(str, args)), flush=True)
        subprocess.run(list(map(str, args)), check=True)

    driver = dest / 'driver.o'
    run([*cc, '-O0', '-fwrapv', '-c', source / 'driver.c', '-o', driver])
    for name, flags in [('o2v', ['-O2', '-ftree-vectorize']),
                        ('o3', ['-O3']), ('fast', ['-O3', '-ffast-math']),
                        ('neg', ['-O2', '-ftree-vectorize', '-DNEGATIVE_CONTROL'])]:
        obj = dest / (name + '.o')
        report = dest / (name + '.vect')
        report.unlink(missing_ok=True)
        run([*cc, *flags, '-fwrapv', '-fopt-info-vec-all=' + str(report),
             '-c', source / 'loops.c', '-o', obj])
        run([*cc, *flags, '-fwrapv', driver, obj, '-lm', '-o', dest / (name + '.mic')])
        print('BUILT ' + name + '; native execution pending lead', flush=True)
    report = (dest / 'o3.vect').read_text()
    lines = (source / 'loops.c').read_text().splitlines()
    failures = []
    for name in ('gat_f32', 'gat_i32', 'mgat_f32', 'sca_f32', 'msca_f32'):
        start = next(i for i, line in enumerate(lines, 1)
                     if line.startswith('void ' + name + ' '))
        passed = any('loops.c:' + str(start + 1) + ':' in row
                     and '64 byte vectors' in row for row in report.splitlines())
        print(('VECTORIZED ' if passed else 'FAIL not vectorized: ') + name)
        if not passed:
            failures.append(name)
    return bool(failures)


if __name__ == '__main__':
    # Reuse the fixed-option, byte-for-byte comparison and function listing.
    # Its Windows trampoline reenters this script, preserving these overrides.
    checks.__file__ = __file__
    checks.acceptance = acceptance
    sys.exit(checks.main())
