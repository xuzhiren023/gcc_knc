#!/usr/bin/env python3
"""S5-15 fixed-option torture comparison and README acceptance builds."""
import subprocess
import sys
import s5_12_checks as checks

checks.OUT = checks.SHARED / 's5-15'


def acceptance():
    from check import function_body
    from s5_07_checks import acceptance as build
    import s5_07_checks
    s5_07_checks.OUT = checks.OUT
    build()
    cc = [str(checks.BUILD / 'xgcc'), '-B' + str(checks.BUILD) + '/',
          '-march=knc', '--sysroot=' + str(checks.TC / 'sysroot')]
    asm = checks.OUT / 's5_ops/fast.s'
    subprocess.run([*cc, '-O3', '-ffast-math', '-fwrapv', '-S',
                    str(checks.ROOT / 'tests/acceptance/s5_ops/loops.c'),
                    '-o', str(asm)], check=True)
    assert 'vgmaxps' in function_body(asm.read_text(), 'maxf_f32')
    print('PASS s5_ops maxf_f32 vectorizes under -ffast-math')
    return 0


if __name__ == '__main__':
    checks.__file__ = __file__
    checks.acceptance = acceptance
    sys.exit(checks.main())
