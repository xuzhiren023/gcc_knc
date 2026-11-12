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
    raise ValueError('expected host')


if __name__ == '__main__':
    sys.exit(main())
