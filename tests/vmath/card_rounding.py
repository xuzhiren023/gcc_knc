#!/usr/bin/env python3
"""S10-11 host regression: reproduce KNC's scalar x87 evaluation, no card job.

Run through tools/run.py. SSE is the existing host control; x87 uses the
library build's existing flags. The standard-excess-precision control tests
whether honoring C assignments/casts repairs the compensated arithmetic.
The FMA mode also enables hardware vector contraction, as on KNC. All card
emulation modes include KNC_LIB_FLAGS, so fixes there reach this regression.
No shared GCC build or installed archive is modified.
"""
import os
import argparse
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
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
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
    modes = {'sse': [], 'x87': ['-mfpmath=387'],
             'x87-fma': ['-mfpmath=387', '-mavx2', '-mfma',
                         '-Wa,-muse-unaligned-vector-move'],
             'x87-standard': ['-mfpmath=387', '-fexcess-precision=standard']}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=modes)
    args = parser.parse_args()
    failed = False
    for name, flags in modes.items():
        if args.mode and name != args.mode:
            continue
        # Match the vector ABI/alignment, but keep the MPFR driver on SSE.
        run('gcc', *build.TEST_FLAGS, '-Wno-psabi',
            *[flag for flag in flags if flag in ('-mavx2', '-mfma',
                                                '-Wa,-muse-unaligned-vector-move')], '-c',
            ROOT / 'tests/vmath/card_rounding.c', '-o', driver)
        objects = []
        for member in members:
            obj = out / (member + '.o')
            run('gcc', *build.LIB_FLAGS, *([] if name == 'sse' else build.KNC_LIB_FLAGS),
                '-Wno-psabi', *flags, '-c',
                build.LIB / (member + '.c'), '-o', obj)
            objects.append(obj)
        exe = out / 'card_rounding.exe'
        run('gcc', driver, *objects, '-lmpfr', '-lgmp', '-lm', '-o', exe)
        print('MODE ' + name, flush=True)
        rc = subprocess.call([str(exe)])
        print('EXIT %s: %d' % (name, rc), flush=True)
        failed |= rc != 0
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
