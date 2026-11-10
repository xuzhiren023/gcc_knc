#!/usr/bin/env python3
"""S8-15 -O2 small vector loop unroll: card builds for the lead.

    python tools/run.py --name S8-15-acceptance -- python tools/s8_15_checks.py

Stages under .work/_shared/S8-15: s4_masks and s5_ops (S8-08's variants)
and m2paired (before = S8-19/m2paired, the knc objects before this change).
"""
import os
import subprocess
import sys

import s8_08_checks as s8


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(s8.TC / p) for p in
                                      ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output(
            [str(s8.TC / 'cygwin/bin/cygpath.exe'), '-u', __file__],
            env=env, text=True).strip()
        return subprocess.call([str(s8.TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    s8.OUT = s8.SHARED / 'S8-15'
    os.environ['PATH'] = ':'.join(str(s8.TC / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    s8.acceptance()
    m2 = s8.ROOT / 'tests/acceptance/m2_kernels'
    s8.run([sys.executable, m2 / 'build.py', '--out', 'S8-15/m2paired',
            '--before', 'S8-19/m2paired'])
    print('M2 PAIR S8-15/m2paired/m2-kernels.mic (before = S8-19/m2paired knc); card run pending lead',
          flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
