#!/usr/bin/env python3
"""S8-19 -mtune=knc without pass_align_tight_loops: card builds for the lead.

    python tools/run.py --name S8-19-acceptance -- python tools/s8_19_checks.py

Stages under .work/_shared/S8-19: s4_masks and s5_ops (S8-08's variants),
m2paired (before = S8-09/m2, the knc objects before this change) and an
A/A pair at the new default (align-64, as s8_08_checks.py --align).
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
    s8.OUT = s8.SHARED / 'S8-19'
    os.environ['PATH'] = ':'.join(str(s8.TC / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    s8.acceptance()
    m2 = s8.ROOT / 'tests/acceptance/m2_kernels'
    s8.run([sys.executable, m2 / 'build.py', '--out', 'S8-19/m2paired', '--before', 'S8-09/m2'])
    print('M2 PAIR S8-19/m2paired/m2-kernels.mic (before = S8-09/m2 knc); card run pending lead',
          flush=True)
    return s8.align(['64'])


if __name__ == '__main__':
    sys.exit(main())
