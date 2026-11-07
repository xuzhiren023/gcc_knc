"""Build and lint S6-05's s5_ops binaries; run through tools/run.py."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', __file__], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    build = SHARED / 'gcc-build/gcc'
    out = SHARED / 'S6-05/s5_ops'
    out.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'tests/acceptance/s5_ops'
    cc = [build / 'xgcc', '-B' + str(build) + '/', '-march=knc',
          '--sysroot=' + str(TC / 'sysroot')]

    def run(args):
        subprocess.run(list(map(str, args)), check=True)

    driver = out / 'driver.o'
    run([*cc, '-O0', '-fwrapv', '-c', source / 'driver.c', '-o', driver])
    for name, flags in [('o2v', ['-O2', '-ftree-vectorize']),
                        ('o3', ['-O3']), ('fast', ['-O3', '-ffast-math']),
                        ('neg', ['-O2', '-ftree-vectorize', '-DNEGATIVE_CONTROL'])]:
        obj, exe = out / (name + '.o'), out / (name + '.mic')
        run([*cc, *flags, '-fwrapv', '-c', source / 'loops.c', '-o', obj])
        run([*cc, *flags, '-fwrapv', driver, obj, '-lm', '-o', exe])
        run([sys.executable, ROOT / 'tools/knc_lint', exe])
        print('BUILT/LINTED, native execution pending lead: ' + str(exe), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
