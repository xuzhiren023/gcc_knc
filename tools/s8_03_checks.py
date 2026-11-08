#!/usr/bin/env python3
"""S8-03 two-level software prefetch: T1 scans.

    python tools/run.py --name S8-03-t1 -- python tools/s8_03_checks.py t1

t1 runs only the prefetch scans (tests/t1/knc-prefetch-*.c).
"""
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

PREFETCH_SOURCES = ('knc-prefetch-O2.c', 'knc-prefetch-O3.c',
                    'knc-prefetch-param.c', 'knc-prefetch-density.c')


def t1():
    from check import Runner
    runner = Runner(SimpleNamespace(compiler='gcc16', cc=None))
    with runner._output:
        runner.t1_sources(runner.source_dir / name for name in PREFETCH_SOURCES)
    return int(runner.failed)


def main(argv):
    if argv[1:] != ['t1']:
        raise SystemExit(__doc__)
    return t1()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
