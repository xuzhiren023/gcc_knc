"""Run the scheduler probe or full T1/T2, retaining assembly for review."""
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
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script,
                                *sys.argv[1:]], env=env)
    import argparse
    import check
    runner = check.Runner(argparse.Namespace(compiler='gcc16', cc=None))
    runner.out = SHARED / 'S6-06'
    runner.out.mkdir(exist_ok=True)
    if '--all' in sys.argv:
        runner.t1()
        runner.t2()
    else:
        runner.t1_sources([ROOT / 'tests/t1/knc-scheduler.c'])
    if runner.failed:
        print((runner.out / 'knc-scheduler.s').read_text())
    return int(runner.failed)


if __name__ == '__main__':
    sys.exit(main())
