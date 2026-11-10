#!/usr/bin/env python3
"""S9-09 libgomp KNC team barrier; invoke through tools/run.py.

    python tools/s9_09_checks.py host [--barriers N]
        compiles tests/regress/s9_09/barrier_stress.c with the Cygwin GCC against the lane's
        libgomp/config/linux/knc/bar.h, bar.c and simple-bar.h and runs its variants: 240 threads,
        100000 barriers each, 60 groups (the cancel variant 36 cores, so that the last group is
        smaller than the others).
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

import s7_09_checks as s7
import s9_06_checks as s9

ROOT = Path(__file__).resolve().parents[1]
TC = s7.TC
TESTS = ROOT / 'tests/regress/s9_09'
LIBGOMP = s7.SHARED / s7.GCC_TREE / 'libgomp'
WORK = s7.SHARED / 'tmp/s9-09'
# (mode, gomp_knc_ncores)
VARIANTS = (('plain', 60), ('tasks-park', 60), ('tasks-spin', 60), ('cancel', 36), ('order', 60))


def host_mode(args):
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    test = WORK / 'barrier_stress.exe'
    includes = [LIBGOMP / 'config' / part for part in s9.CONFIG_PATH.split()]
    rc, text = s7.capture(['gcc', '-std=gnu11', '-O2', '-Wall', '-pthread', *('-I%s' % d for d in includes),
                           TESTS / 'barrier_stress.c', '-o', test])
    if rc or text.strip():
        print('\n'.join(text.splitlines()[-15:]))
    if rc:
        print('FAIL host: barrier_stress.c does not build against %s' % LIBGOMP)
        return 1
    failed = 0
    for mode, ncores in VARIANTS:
        rc, text = s7.capture([test, mode, args.barriers, ncores], timeout=7200)
        print(text.strip() or 'FAIL %s: no output, exit %s' % (mode, rc), flush=True)
        failed += rc != 0
    print('%s host: %d of %d variants failed' % ('FAIL' if failed else 'PASS', failed, len(VARIANTS)))
    return int(failed != 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('host',))
    parser.add_argument('--barriers', type=int, default=100000)
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__))],
                                         text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]])
    os.environ['TMPDIR'] = str(s7.SHARED / 'tmp')
    return {'host': host_mode}[args.mode](args)


if __name__ == '__main__':
    sys.exit(main())
