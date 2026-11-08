#!/usr/bin/env python3
"""S8-03 two-level software prefetch: T1 scans and a KNC assembly snapshot.

    python tools/run.py --name S8-03-t1 -- python tools/s8_03_checks.py t1
    python tools/s8_03_checks.py asm <folder>

t1 runs only the prefetch scans (tests/t1/knc-prefetch-*.c).
asm compiles each prefetch scan source with its own options line into
<folder>/<stem>.s, so two compilers' KNC output can be compared byte for byte
(round 2: the middle-end changes gated on the two-level hook must leave the
KNC assembly of the T1 files unchanged).
"""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
sys.path.insert(0, str(ROOT / 'tools'))

PREFETCH_SOURCES = ('knc-prefetch-O2.c', 'knc-prefetch-O3.c',
                    'knc-prefetch-param.c', 'knc-prefetch-density.c')


def t1():
    from check import Runner
    runner = Runner(SimpleNamespace(compiler='gcc16', cc=None))
    with runner._output:
        runner.t1_sources(runner.source_dir / name for name in PREFETCH_SOURCES)
    return int(runner.failed)


def asm(folder):
    from check import Runner
    runner = Runner(SimpleNamespace(compiler='gcc16', cc=None))
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    with runner._output:
        for name in PREFETCH_SOURCES:
            source = runner.source_dir / name
            options = ['-O2']
            for line in source.read_text().splitlines():
                match = re.match(r'^\s*//\s*options:\s*(.*)$', line)
                if match:
                    options = shlex.split(match[1])
            out = folder / (source.stem + '.s')
            runner.command(runner.cc, *runner.cc_flags, *options,
                           '--sysroot=' + str(runner.sysroot), '-S', source, '-o', out)
            print('wrote ' + str(out) + ' (' + ' '.join(options) + ')', flush=True)
    return 0


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
        arguments = list(argv[1:])
        if len(arguments) == 2 and arguments[0] == 'asm':
            arguments[1] = subprocess.check_output([cygpath, '-u', arguments[1]],
                                                   env=env, text=True).strip()
        return subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script, *arguments],
                               env=env)
    if argv[1:] == ['t1']:
        return t1()
    if len(argv) == 3 and argv[1] == 'asm':
        return asm(argv[2])
    raise SystemExit(__doc__)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
