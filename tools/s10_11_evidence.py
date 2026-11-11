#!/usr/bin/env python3
"""S10-11 assembly evidence and card staging; run through tools/run.py.

Uses the dispatched lane's installed prefix. Does not run anything on the card.
The cbrt diagnostic deliberately retains the failing build's library flags.
"""
import argparse
import difflib
import os
from pathlib import Path
import shutil
import subprocess
import sys

import knc_vmath as build


def run(*args, **kwargs):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = str(build.TC / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output(
            [str(build.TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())],
            env=env, text=True).strip()
        return subprocess.call([str(build.TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-only', action='store_true', help='reuse completed assembly evidence')
    args = parser.parse_args()
    os.environ['PATH'] = ':'.join(map(str, (build.TC / 'cross/bin', build.TC / 'cygwin/bin'))) + ':' + os.environ['PATH']
    out = build.SHARED / 'S10-11'
    card = out / 'card'
    card.mkdir(parents=True, exist_ok=True)
    prefix, _ = build.prefix()
    cc = [prefix / 'bin/k1om-mpss-linux-gcc', '--sysroot=' + str(build.TC / 'sysroot'), '-march=knc']
    cross = build.TC / 'cross/bin'
    old_flags = ['-fPIC', '-fvisibility=hidden']
    for member in (() if args.stage_only else ('vmath_sincos', 'vmath_reducer', 'vmath_tan', 'vmath_atan')):
        source = build.LIB / (member + '.c')
        before, after = out / (member + '.before.s'), out / (member + '.s')
        for asm, flags in ((before, old_flags), (after, build.KNC_LIB_FLAGS)):
            run(*cc, *build.LIB_FLAGS, *flags, '-S', source, '-o', asm)
        old, new = before.read_text().splitlines(), after.read_text().splitlines()
        print('ASSEMBLY DIFF ' + member, flush=True)
        print('\n'.join(difflib.unified_diff(old, new, fromfile=before.name, tofile=after.name)))
        for label, lines in (('before', old), ('after', new)):
            fmas = [s.strip() for s in lines if any(op in s for op in ('vfmadd', 'vfmsub', 'vfnmadd', 'vfnmsub'))]
            print('%s %s: %d contracted instructions' % (member, label, len(fmas)), flush=True)
        before.unlink()

    objects = []
    for name, source, flags in (
            ('cbrt-original', build.LIB / 'vmath_cbrt.c',
             build.LIB_FLAGS + old_flags + ['-fno-math-errno']),
            ('cbrt-diagnostic', build.ROOT / 'tests/vmath/card_rounding.c',
             build.TEST_FLAGS + ['-DKNC_CBRT_DIAGNOSTIC'])):
        asm, obj = card / (name + '.s'), card / (name + '.o')
        run(*cc, *flags, '-g', '-S', source, '-o', asm)
        run(cross / 'k1om-mpss-linux-as', '--march=k1om', asm, '-o', obj)
        objects.append(obj)
    elf = card / 'cbrt-diagnostic.mic'
    run(*cc, *objects, '-lm', '-o', elf)
    for tool, args, suffix in (('nm', ['-n'], '.nm'), ('objdump', ['-drwC'], '.objdump')):
        with (card / ('cbrt-diagnostic' + suffix)).open('w') as log:
            run(cross / ('k1om-mpss-linux-' + tool), *args, elf, stdout=log)
    for name in ('qualify_f', 'qualify_d', 'qualify_v1'):
        shutil.copyfile(out / 'knc' / (name + '.mic'), card / (name + '.mic'))
    run(sys.executable, build.ROOT / 'tools/knc_lint', elf, card / 'qualify_v1.mic')
    for function in ('cbrt', 'cbrtf'):
        print('LEAD: python tools/card_run --threads 1 --timeout 60 '
              '.work/_shared/S10-11/card/cbrt-diagnostic.mic ' + function)
    for function in ('sin', 'cos', 'tan', 'atan2', 'cbrt', 'cbrtf'):
        print('LEAD: python tests/vmath/card_qualify.py --out S10-11 --only ' + function)
    return 0


if __name__ == '__main__':
    sys.exit(main())
