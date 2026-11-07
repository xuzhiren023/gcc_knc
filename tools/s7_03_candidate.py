#!/usr/bin/env python3
"""Build the isolated S7-03 ABI candidate; never install or run target code.

Run through tools/run.py.  This configures only libgcc in _shared/S7-03,
using the existing shared compiler and upstream libgcc make rules.  The
command-line enable_shared override is confined to this ABI experiment;
the production runtime and driver guards remain for E6-01b.
"""
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'


def run(*args, cwd=None):
    print('+ ' + shlex.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, check=True)


def main():
    out = SHARED / 'S7-03'
    out.mkdir(exist_ok=True)
    gcc = SHARED / 'gcc-build/gcc'
    source = SHARED / 'gcc/libgcc'
    env_cc = f'{gcc}/xgcc -B{gcc}/ -B{TC}/cross/bin/'
    os.environ['CC'] = env_cc
    run('sh', source / 'configure', '--build=x86_64-pc-cygwin',
        '--host=k1om-mpss-linux', '--target=k1om-mpss-linux',
        '--with-cross-host=x86_64-pc-cygwin', '--disable-multilib',
        '--disable-nls', '--disable-decimal-float', '--disable-gcov',
        '--enable-shared', f'--with-sysroot={TC}/sysroot',
        f'--prefix={out}/private', cwd=out)
    # Target only the isolated DSO, never `all` (which installs into gcc_objdir).
    run('make', '-j8', f'gcc_objdir={gcc}', 'enable_shared=yes',
        'libgcc_s.so', cwd=out)
    run(sys.executable, ROOT / 'tools/s7_03_checks.py',
        '--candidate', out / 'libgcc_s.so.1')
    sf = ('addsf3 divsf3 eqsf2 gesf2 lesf2 mulsf3 negsf2 subsf3 '
          'unordsf2 fixsfsi floatsisf floatunsisf').split()
    run(sys.executable, ROOT / 'tools/knc_lint',
        *(out / (name + '_s.o') for name in [*sf, 'knc-cpuinfo']))


if __name__ == '__main__':
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', __file__], env=env, text=True).strip()
        sys.exit(subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env))
    main()
