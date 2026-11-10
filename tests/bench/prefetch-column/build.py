"""Build the S8-11 prefetch column case for the card with this lane's shared GCC build.

usage: python tools/run.py --name <name> -- python tests/bench/prefetch-column/build.py OUTDIR
column.c is compiled three times at -O2 -march=knc: column_pf (-fprefetch-loop-arrays),
column_nopf (-fno-prefetch-loop-arrays) and column_ref (scalar, -ffp-contract=off). Writes
OUTDIR/column-{pf,nopf}.s, links OUTDIR/column.mic and lints it. Prints whether each build's
assembly has vprefetch. Does not run anything on the card.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import storage  # noqa: E402

PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
BUILD = Path(storage.gcc_build_dir(PROJECT)) / 'gcc'
CC = [(BUILD / 'xgcc.exe').as_posix(), '-B' + BUILD.as_posix() + '/', '-march=knc', '-O2',
      '-std=gnu11', '-Wall', '-Wextra', '-Werror']
VARIANTS = {'pf': ['-fprefetch-loop-arrays'], 'nopf': ['-fno-prefetch-loop-arrays'],
            'ref': ['-fno-prefetch-loop-arrays', '-fno-tree-vectorize',
                    '-fno-tree-slp-vectorize', '-ffp-contract=off']}


def run(*args):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    return subprocess.call(list(map(str, args)), env=ENV)


ENV = dict(os.environ, PATH=str(SHARED / 'toolchain/cygwin/bin') + os.pathsep + os.environ['PATH'])


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    errors = 0
    for name, flags in VARIANTS.items():
        common = [*CC, *flags, '-DNAME=column_' + name, '-I', HERE.as_posix()]
        errors += bool(run(*common, '-S', HERE / 'column.c', '-o', out / ('column-' + name + '.s')))
        errors += bool(run(*common, '-c', HERE / 'column.c', '-o', out / ('column-' + name + '.o')))
    errors += bool(run(*CC, *VARIANTS['ref'], '-pthread', '-I', HERE.as_posix(), '-c',
                       HERE / 'driver.c', '-o', out / 'driver.o'))
    if errors:
        print('FAIL: %d compile steps' % errors)
        return 1
    for name in ('pf', 'nopf'):
        text = (out / ('column-' + name + '.s')).read_text()
        print('%s: %d vprefetch0, %d vprefetch1' % (name, len(re.findall(r'\bvprefetch0\b', text)),
                                                    len(re.findall(r'\bvprefetch1\b', text))))
    exe = out / 'column.mic'
    if run(*CC, out / 'driver.o', *(out / ('column-' + n + '.o') for n in VARIANTS),
           '-pthread', '-o', exe):
        return 1
    if run(sys.executable, ROOT / 'tools/knc_lint', exe):
        return 1
    print('BUILT and LINTED (NOT executed on card): ' + str(exe))
    return 0


if __name__ == '__main__':
    sys.exit(main())
