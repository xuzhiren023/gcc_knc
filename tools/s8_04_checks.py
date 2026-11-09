#!/usr/bin/env python3
"""S8-04 small-matrix kernels: the broadcast-load T1 scan alone.

    python tools/run.py --name S8-04-t1 -- python tools/s8_04_checks.py t1

t1 runs only tests/t1/knc-broadcast-load.c through check.py's T1 runner.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
sys.path.insert(0, str(ROOT / 'tools'))

SOURCES = ('knc-broadcast-load.c',)


def t1():
    from check import Runner
    runner = Runner(SimpleNamespace(compiler='gcc16', cc=None))
    with runner._output:
        runner.t1_sources(runner.source_dir / name for name in SOURCES)
    return int(runner.failed)


def main(argv):
    if os.name == 'nt':
        # check.py's Runner needs the Cygwin runtime (POSIX sysroot paths,
        # Python 3.12); re-exec there as check.py itself does.
        manifest = json.loads((ROOT / 'toolchain/manifest.json').read_text())
        tc = PROJECT / manifest['root']
        env = os.environ.copy()
        env['PATH'] = (os.pathsep.join(str(tc / p) for p in ('cross/bin', 'cygwin/bin'))
                       + os.pathsep + env.get('PATH', ''))
        cygpath = str(tc / 'cygwin/bin/cygpath.exe')
        script = subprocess.check_output([cygpath, '-u', str(Path(__file__).resolve())],
                                         env=env, text=True).strip()
        return subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script, *argv[1:]],
                               env=env)
    if argv[1:] == ['t1']:
        return t1()
    raise SystemExit(__doc__)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
