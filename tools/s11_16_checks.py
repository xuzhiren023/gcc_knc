"""Build/stage the bounded MPSS long-double hazard probe; never run card jobs."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    shared = root.parent / '_shared'
    tc = shared / 'toolchain'
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(str(tc / p) for p in
                                 ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'),
                                          '-u', __file__], env=env, text=True).strip()
        return subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script,
                                *sys.argv[1:]], env=env)
    os.environ.update(env)
    out = shared / 'S11-16'
    out.mkdir(exist_ok=True)
    if sys.argv[1] == 'host':
        return subprocess.call([sys.executable, str(root / 'tests/tools/test_s11_16_probe.py')])
    if sys.argv[1] == 'stage':
        prefix = shared / 'gcc-knc-16.2.0'
        binary = out / 'long-double-probe.mic'
        subprocess.run([str(prefix / 'bin/k1om-mpss-linux-gcc'),
                        '--sysroot=' + str(tc / 'sysroot'), '-O2', '-std=gnu11',
                        '-march=knc', '-Wall', '-Wextra', '-Werror',
                        '-static-libgcc', '-pthread',
                        str(root / 'tools/s11_16_long_double.c'), '-ldl',
                        '-o', str(binary)], check=True)
        subprocess.run([sys.executable, str(root / 'tools/knc_lint'),
                        str(binary)], check=True)
        print('Staged; native results pending lead card run:')
        print('python tools/card_run --threads 240 --timeout 1800 '
              '.work/_shared/S11-16/long-double-probe.mic')
        return 0
    raise ValueError('expected host or stage')


if __name__ == '__main__':
    sys.exit(main())
