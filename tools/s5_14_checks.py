#!/usr/bin/env python3
"""S5-14 T1, acceptance builds and torture; invoke through tools/run.py."""
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


def acceptance():
    from s5_13_checks import acceptance as build_acceptance
    checks.OUT = checks.SHARED / 's5-14'
    # The lead permits mgat_f64 to stay scalar: its masked store is misaligned.
    return build_acceptance(('gat_f64', 'gat_i64', 'sca_f64'))


if __name__ == '__main__':
    # Reuse the Cygwin trampoline and fixed before/after torture options.
    checks.__file__ = __file__
    checks.t1 = t1
    checks.acceptance = acceptance
    sys.exit(checks.main())
