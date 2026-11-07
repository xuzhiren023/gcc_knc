#!/usr/bin/env python3
"""S7-08 libgfortran slice: card payloads and negative compiles; invoke through tools/run.py.

    python tools/s7_08_checks.py slice      build, verify and lint tests/t2/s7-08/*.f90 for the card
    python tools/s7_08_checks.py negative   kind-16 and selected_real_kind compiles must be rejected

The slice links each program with the uninstalled GCC 16 driver against the libgfortran built in
the shared tree (static, with static libgcc) and refuses any libgfortran, libgcc or module file
from the donor GCC 5 toolchain or the sysroot. Nothing runs natively here: the lead runs
.work/_shared/S7-08/run.sh on the card.
"""
import argparse
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build'
LIBGF = BUILD / 'k1om-mpss-linux/libgfortran'
OUT = SHARED / 'S7-08'
SRC = ROOT / 'tests/t2/s7-08'
ALLOWED_NEEDED = {'libm.so.6', 'libc.so.6', 'libpthread.so.0', 'ld-linux-k1om.so.2'}


def driver(extra):
    return [str(BUILD / 'gcc/gfortran'), '-B' + str(BUILD / 'gcc') + '/',
            '-B' + str(LIBGF) + '/', '-B' + str(LIBGF / '.libs') + '/', '-I' + str(LIBGF),
            '-march=knc', '--sysroot=' + str(TC / 'sysroot'), '-O1', '-Wall',
            '-static-libgfortran', '-static-libgcc', '-J', str(OUT / 'mod'), *map(str, extra)]


def compile_capture(args):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          errors='replace', timeout=300)
    return proc.returncode, proc.stdout


def needed(binary):
    text = subprocess.check_output([str(TC / 'cross/bin/k1om-mpss-linux-readelf'), '-d', str(binary)],
                                   text=True, errors='replace')
    return set(re.findall(r'\(NEEDED\)\s+Shared library: \[([^\]]+)\]', text))


def link_one(source, lint):
    """Build one card program; return a list of failure descriptions."""
    name = source.stem
    binary = OUT / (name + '.mic')
    binary.unlink(missing_ok=True)
    rc, text = compile_capture(driver(['-Wl,--trace', source, '-o', binary]))
    if rc != 0:
        tail = [line for line in text.splitlines() if line.strip()][-6:]
        return ['%s: compile/link exit %d: %s' % (name, rc, ' | '.join(tail))]
    failures = []
    if re.search(r'warning', text, re.I):
        failures.append(name + ': driver reported warnings: ' + text.strip()[:300])
    runtime = [line for line in text.splitlines() if 'libgfortran' in line]
    if not runtime:
        failures.append(name + ': link trace shows no libgfortran archive')
    for line in runtime:
        if 'gcc-build/k1om-mpss-linux/libgfortran' not in line.replace('\\', '/'):
            failures.append(name + ': foreign libgfortran linked: ' + line.strip())
    for line in text.splitlines():
        if re.search(r'libgcc(_s|_eh)?\.(a|so)', line) and '/gcc-build/' not in line.replace('\\', '/'):
            failures.append(name + ': foreign libgcc linked: ' + line.strip())
    dynamic = needed(binary)
    if dynamic - ALLOWED_NEEDED:
        failures.append(name + ': unexpected DT_NEEDED: ' + ' '.join(sorted(dynamic - ALLOWED_NEEDED)))
    violations = [str(row) for row in lint(binary, TC, os.environ.copy())]
    failures.extend(name + ': lint: ' + row for row in violations)
    return failures


def slice_mode():
    (OUT / 'mod').mkdir(parents=True, exist_ok=True)
    for stale in (OUT / 'mod').glob('*.mod'):
        stale.unlink()
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    sources = sorted(SRC.glob('*.f90'))
    failures = []
    for source in sources:
        problems = link_one(source, lint)
        failures.extend(problems)
        print(('PASS ' if not problems else 'FAIL ') + source.stem + ' build/verify/lint', flush=True)
    for problem in failures:
        print('  ' + problem)
    ieee = LIBGF / 'ieee_arithmetic.mod'
    print(('PASS' if ieee.exists() else 'FAIL') + ' fresh IEEE modules at ' + str(LIBGF))
    programs = ' '.join(source.stem + '.mic' for source in sources)
    (OUT / 'run.sh').write_text(
        '#!/bin/sh\n'
        '# Lead-only card runner for S7-08. Copy the complete S7-08 directory to the card.\n'
        '# Usage: sh /absolute/path/S7-08/run.sh   (static libgfortran and libgcc: no loader path)\n'
        'base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        'status=0\n'
        'for exe in ' + programs + '; do\n'
        '    if "$base/$exe" > "$base/$exe.out" 2>&1 && grep -q "^PASS ${exe%.mic}\\$" "$base/$exe.out"; then\n'
        '        echo "PASS $exe"\n'
        '    else\n'
        '        echo "FAIL $exe (exit $?)"; cat "$base/$exe.out"; status=1\n'
        '    fi\n'
        'done\n'
        'exit $status\n', newline='\n')
    if failures or not ieee.exists():
        return 1
    print('PASS build/lint: ' + programs + '; native NOT RUN', flush=True)
    print('Lead invocation: sh ' + str(OUT / 'run.sh') + ' (no arguments; exit 0 means every program passed).')
    return 0


def negative_mode():
    failed = False
    for source in sorted((SRC / 'negative').glob('*.f90')):
        expect = re.match(r'!\s*expect:\s*(.+)', source.read_text()).group(1).strip()
        rc, text = compile_capture(driver(['-fsyntax-only', source]))
        ok = rc != 0 and expect in text
        failed |= not ok
        print(('PASS ' if ok else 'FAIL ') + source.stem + ': exit %d, expected "%s"' % (rc, expect), flush=True)
        if not ok:
            print(text.strip()[:600])
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('slice', 'negative'))
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, args.mode])
    OUT.mkdir(exist_ok=True)
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    return {'slice': slice_mode, 'negative': negative_mode}[args.mode]()


if __name__ == '__main__':
    sys.exit(main())
