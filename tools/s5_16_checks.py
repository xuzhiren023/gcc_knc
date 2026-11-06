#!/usr/bin/env python3
"""S5-16 fixed-option torture comparison and README acceptance builds."""
import sys
import os
import subprocess
import s5_12_checks as checks

checks.OUT = checks.SHARED / 's5-16'


def native():
    """Build only; card execution belongs to the lead."""
    cc = [str(checks.BUILD / 'xgcc'), '-B' + str(checks.BUILD) + '/',
          '-march=knc', '--sysroot=' + str(checks.TC / 'sysroot'),
          '-Wall', '-Wextra']
    source = checks.ROOT / 'tests/regress/knc-byte-guard.c'
    out = checks.OUT
    kernels = out / 'byte-loops.o'
    driver = out / 'byte-driver.o'
    asm = out / 'byte-loops.s'
    binary = out / 'knc-byte-guard.mic'
    subprocess.run([*cc, '-O2', '-ftree-vectorize', '-DKNC_BYTE_LOOPS',
                    '-save-temps=obj', '-c', str(source), '-o', str(kernels)], check=True)
    subprocess.run([*cc, '-O0', '-c', str(source), '-o', str(driver)], check=True)
    subprocess.run([*cc, str(driver), str(kernels), '-o', str(binary)], check=True)
    from check import function_body
    text = asm.read_text()
    for name, instruction in [('byte_to_int', 'vmovdqa32'),
                              ('byte_to_float', 'vmovaps'),
                              ('int_to_byte', 'vmovdqa32')]:
        body = function_body(text, name)
        assert body and instruction in body and '{uint8}' in body, name
    subprocess.run([sys.executable, str(checks.ROOT / 'tools/knc_lint'),
                    str(asm), str(binary)], check=True)
    (out / 'byte-loops.i').unlink(missing_ok=True)
    print('BUILT and linted ' + str(binary) + '; native execution pending lead')
    return 0


if __name__ == '__main__':
    checks.__file__ = __file__
    if os.name != 'nt' and sys.argv[1] == 'native':
        os.environ['PATH'] = ':'.join(str(checks.TC / p) for p in
                                      ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
        sys.exit(native())
    sys.exit(checks.main())
