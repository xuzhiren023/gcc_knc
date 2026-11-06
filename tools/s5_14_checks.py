#!/usr/bin/env python3
"""S5-14 focused T1 scans; invoke through tools/run.py with action t1."""
from types import SimpleNamespace
import sys

import s5_12_checks as checks

checks.OUT = checks.SHARED / 's5-14'


def t1():
    from check import Runner
    runner = Runner(SimpleNamespace(cc=None, compiler='gcc16'))
    runner.out = checks.OUT
    sources = sorted((checks.ROOT / 'tests/t1').glob('knc-*8-*.c'))
    assert len(sources) == 4
    runner.t1_sources(sources)
    return int(runner.failed)


if __name__ == '__main__':
    # Reuse the Cygwin trampoline and fixed before/after torture options.
    checks.__file__ = __file__
    checks.t1 = t1
    sys.exit(checks.main())
