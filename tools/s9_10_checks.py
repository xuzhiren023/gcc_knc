#!/usr/bin/env python3
"""S9-10 libgomp KNC padding, static run-sched-var default and malloc hint; invoke through tools/run.py.

    python tools/s9_10_checks.py host
        compiles the lane's libgomp/env.c with the Cygwin GCC, -D__k1om__, the k1om config_path
        and the build's config.h, together with tests/regress/s9_10/env_host.c, which fails to
        compile when libgomp.h's or knc/bar.h's KNC layout checks fail; runs its two cases (see
        that file) with their environments.

Nothing runs natively here: the lead runs the staged programs on the card.
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
TESTS = ROOT / 'tests/regress/s9_10'
LIBGOMP = s7.SHARED / s7.GCC_TREE / 'libgomp'
OBJDIR = s7.BUILD / 'k1om-mpss-linux/libgomp'
WORK = s7.SHARED / 'tmp/s9-10'
# The variables the cases set; the default case runs with none of them.
KNOBS = ('OMP_SCHEDULE', 'MALLOC_ARENA_MAX', 'OMP_STACKSIZE', 'GOMP_STACKSIZE', 'OMP_DISPLAY_ENV')
CASES = (('default', {}),
         ('set', {'OMP_SCHEDULE': 'dynamic,4', 'MALLOC_ARENA_MAX': '60', 'OMP_STACKSIZE': '2M'}))


def host_mode(args):
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    test = WORK / 'env_host.exe'
    includes = [LIBGOMP / 'config' / part for part in s9.CONFIG_PATH.split()]
    rc, text = s7.capture(['gcc', '-std=gnu11', '-O2', '-Wall', '-Wno-attributes', '-D__k1om__', '-DHAVE_CONFIG_H',
                           '-I%s' % OBJDIR, *('-I%s' % d for d in includes), '-I%s' % LIBGOMP,
                           '-I%s' % (LIBGOMP.parent / 'include'), LIBGOMP / 'env.c', TESTS / 'env_host.c',
                           '-o', test])
    if rc:
        print('\n'.join(line for line in text.splitlines() if 'error' in line)[-3000:])
        print('FAIL host: env.c and env_host.c do not build against %s (layout checks above)' % LIBGOMP)
        return 1
    failed = 0
    for case, settings in CASES:
        env = {k: v for k, v in os.environ.items() if k not in KNOBS}
        env.update(settings)
        result = subprocess.run([str(test), case], env=env, capture_output=True, text=True, timeout=60)
        print(result.stdout.strip() or 'FAIL %s: no output, exit %s' % (case, result.returncode), flush=True)
        failed += result.returncode != 0
    print('%s host: %d of %d cases failed' % ('FAIL' if failed else 'PASS', failed, len(CASES)))
    return int(failed != 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('host',))
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
