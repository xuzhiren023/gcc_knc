"""Build the red-stage card negative control, or run the host checker test.

Invoke through tools/run.py. Card execution is exclusively lead-run.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'


def command(*args):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('negative', 'host-negative'))
    args = parser.parse_args()
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = str(TC / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())],
            env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script,
                                args.mode], env=env)
    os.environ['PATH'] = ':'.join(map(str, (TC / 'cross/bin', TC / 'cygwin/bin'))) + ':' + os.environ['PATH']
    out = SHARED / 'S6-02'
    out.mkdir(exist_ok=True)
    flags = ['-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
             '-fno-tree-vectorize', '-ffp-contract=off']
    if args.mode == 'host-negative':
        exe = out / 'checker-host-negative.exe'
        command(TC / 'cygwin/bin/gcc', *flags, '-DHOST_CHECKER_SELFTEST',
                HERE / 'driver.c', '-o', exe)
        # Preserve the failing status: a negative control must not be greenwashed.
        return subprocess.call([str(exe)])
    build = SHARED / 'gcc-build/gcc'
    cc = [build / 'xgcc', '-B' + str(build) + '/',
          '--sysroot=' + str(TC / 'sysroot'), '-march=knc']
    assembler = TC / 'cross/bin/k1om-mpss-linux-as'
    command(*cc, '--version')
    command(assembler, '--version')
    command(*cc, *flags, '-DNEGATIVE_CONTROL', '-S', HERE / 'driver.c',
            '-o', out / 'driver-negative.s')
    for source, obj in ((out / 'driver-negative.s', out / 'driver-negative.o'),
                        (HERE / 'negative.s', out / 'negative.o')):
        command(assembler, '--march=k1om', source, '-o', obj)
    exe = out / 'm2-negative.mic'
    command(*cc, out / 'driver-negative.o', out / 'negative.o', '-o', exe)
    command(sys.executable, ROOT / 'tools/knc_lint', exe)
    print('BUILT and LINTED (not executed on card): ' + str(exe))
    return 0


if __name__ == '__main__':
    sys.exit(main())
