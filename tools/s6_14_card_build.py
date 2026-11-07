#!/usr/bin/env python3
"""Build and lint S6-14 card binaries; execution belongs to the lead."""
import os
from pathlib import Path
import runpy
import subprocess
import sys

import vect_suite as suite


def main():
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(str(suite.TC / p) for p in
                                ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
    if os.name == 'nt':
        script = subprocess.check_output([str(suite.TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(suite.TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    out = suite.SHARED / 'S6-14'
    out.mkdir(exist_ok=True)
    env['TMPDIR'] = str(suite.SHARED / 'tmp')
    build = suite.SHARED / 'gcc-build/gcc'
    cc = [str(build / 'xgcc.exe'), '-B' + str(build) + '/', '-march=knc',
          '--sysroot=' + str(suite.TC / 'sysroot')]
    lint = runpy.run_path(str(suite.ROOT / 'tools/knc_lint'))['lint']
    failed = False

    def command(*args):
        subprocess.run([*cc, *map(str, args)], env=env, check=True, timeout=120)

    def check(artifact):
        nonlocal failed
        violations = list(lint(artifact, suite.TC, env))
        failed |= bool(violations)
        print(('FAIL ' if violations else 'PASS ') + str(artifact) + ': build/lint; native pending')
        for violation in violations[:3]:
            print(violation)

    artifact = out / 'reduced.mic'
    command('-O2', suite.ROOT / 'tests/t1/knc-loop-store-mask.c', '-o', artifact)
    check(artifact)
    source = suite.ROOT / 'tests/acceptance/s4_masks'
    driver, obj = out / 'masks-driver.o', out / 'masks-loops.o'
    command('-O0', '-fwrapv', '-c', source / 'driver.c', '-o', driver)
    for name, flags in (('o2v', ['-O2', '-ftree-vectorize']), ('o3', ['-O3'])):
        artifact = out / ('s4_masks-' + name + '.mic')
        command(*flags, '-fwrapv', '-c', source / 'loops.c', '-o', obj)
        command(driver, obj, '-lm', '-o', artifact)
        check(artifact)
    driver.unlink()
    obj.unlink()
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
