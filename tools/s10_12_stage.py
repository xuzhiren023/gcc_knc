#!/usr/bin/env python3
"""Stage the S10-12 qualifier crash reproducer; never run a card job.

Link the S10-11 archive that exhibited the crash. Keep its machine code intact
so a new library build cannot mask the fault. Only the qualifier gains -g and
VMATH_CRASH_TRACE; its normal optimization and oracle flags are preserved.
"""
import os
from pathlib import Path
import subprocess
import sys

import knc_vmath as v


def run(*args, **kwargs):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = str(v.TC / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output(
            [str(v.TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())],
            env=env, text=True).strip()
        return subprocess.call([str(v.TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
    os.environ['PATH'] = ':'.join(map(str, (v.TC / 'cross/bin', v.TC / 'cygwin/bin'))) + ':' + os.environ['PATH']
    out = v.SHARED / 'S10-12/card'
    out.mkdir(parents=True, exist_ok=True)
    if sys.argv[1:] == ['--regression']:
        host = v.SHARED / 'S10-12/host'
        host.mkdir(parents=True, exist_ok=True)
        exe = host / 'cbrt_screen.exe'
        run('gcc', *v.TEST_FLAGS, '-DVMATH_MPFR', '-Wno-psabi',
            v.ROOT / 'tests/vmath/cbrt_screen.c',
            v.SHARED / 'S10-11/host/libknc_vmath.a',
            '-pthread', '-lmpfr', '-lgmp', '-lm', '-o', exe)
        run(exe)
        return 0
    archive = v.SHARED / 'S10-11/knc/libknc_vmath.a'
    if not archive.is_file():
        raise SystemExit('Missing crash baseline: ' + str(archive))
    gcc = v.gcc_build()
    cc = [gcc / 'xgcc', '-B' + str(gcc) + '/', '--sysroot=' + str(v.TC / 'sysroot'), '-march=knc']
    stem = out / 'qualify_v1'
    run(*cc, *v.TEST_FLAGS, '-g', '-DVMATH_CRASH_TRACE', '-S',
        v.ROOT / 'tests/vmath/qualify_v1.c', '-o', stem.with_suffix('.s'))
    run(v.TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om',
        stem.with_suffix('.s'), '-o', stem.with_suffix('.o'))
    run(*cc, stem.with_suffix('.o'), archive, '-pthread', '-lm', '-o', stem.with_suffix('.mic'))
    run(sys.executable, v.ROOT / 'tools/knc_lint', stem.with_suffix('.mic'))
    for tool, flags, suffix in [('nm', ['-n', '-S'], '.nm'),
                                ('objdump', ['-d', '-l'], '.objdump')]:
        with stem.with_suffix(suffix).open('w') as output:
            run(v.TC / ('cross/bin/k1om-mpss-linux-' + tool), *flags,
                stem.with_suffix('.mic'), stdout=output)
    # Objects/assembly can be regenerated; keep only the ELF and its address maps.
    stem.with_suffix('.o').unlink()
    stem.with_suffix('.s').unlink()
    for function, threshold in [('cbrt', '0.6'), ('cbrtf', '0.5')]:
        print('LEAD: python tools/card_run --threads 1 --timeout 60 '
              '.work/_shared/S10-12/card/qualify_v1.mic '
              + function + ' --blocks 65536 --dump ' + threshold)
    print('STAGED only: native crash output and root cause pending the lead card turn.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
