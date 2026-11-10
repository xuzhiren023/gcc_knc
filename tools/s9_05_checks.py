#!/usr/bin/env python3
"""S9-05 libstdc++ runtime slice, host side; invoke through tools/run.py.

    python tools/s9_05_checks.py build [--prefix DIR]
        builds one flat card batch in .work/_shared/S9-05: the tests/acceptance/s9_cxx programs
        (build.py), the docs/research/knc-libstdcxx.md section 5.3 testsuite slice and the three
        tests/regress/s9_05 programs that document known deviations; compile- and link-only slice
        tests are verdicts here. Writes run.sh (the card program), files.txt (its --file-list),
        expected.txt (one RESULT line per program).
    python tools/s9_05_checks.py compare OUTPUT
        compares the RESULT lines of the card job's stdout byte for byte with expected.txt.

The compiler is the lane's installed prefix (tools/s7_09_checks.py install); --prefix names another
one (an older prefix without g++ shows the batch is new). Nothing runs natively here.
"""
import argparse
import itertools
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys

import s7_09_checks as s7

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
TC = s7.TC
OUT = s7.SHARED / 'S9-05'
TESTSUITE = s7.SHARED / s7.GCC_TREE / 'libstdc++-v3/testsuite'
DEVIATIONS = ROOT / 'tests/regress/s9_05'
# Section 5.3; each test's dg-do (run, compile or link) decides whether it goes to the card.
SLICE = """
18_support/exception_ptr/current_exception.cc 18_support/exception_ptr/rethrow_exception.cc
18_support/exception_ptr/lifespan.cc 18_support/exception_ptr/move.cc
18_support/nested_exception/rethrow_nested.cc 18_support/nested_exception/throw_with_nested.cc
18_support/nested_exception/rethrow_if_nested.cc 18_support/uncaught_exceptions/uncaught_exceptions.cc
18_support/bad_cast/cons_virtual_derivation.cc 18_support/bad_typeid/cons_virtual_derivation.cc
18_support/new_aligned.cc 18_support/headers/new/synopsis.cc
30_threads/thread/cons/1.cc 30_threads/thread/cons/2.cc 30_threads/thread/cons/3.cc
30_threads/thread/cons/4.cc 30_threads/thread/cons/5.cc
30_threads/condition_variable/members/1.cc 30_threads/condition_variable/members/2.cc
30_threads/condition_variable/members/3.cc
30_threads/future/members/get.cc 30_threads/future/members/wait.cc
30_threads/future/members/wait_for.cc 30_threads/future/members/wait_until.cc
30_threads/call_once/call_once1.cc 30_threads/call_once/once_flag.cc
29_atomics/atomic/is_always_lock_free.cc 29_atomics/atomic/lock_free_aliases.cc
29_atomics/atomic_integral/is_always_lock_free.cc 29_atomics/atomic/cons/user_pod.cc
29_atomics/atomic/wait_notify/1.cc
26_numerics/random/random_device/cons/default.cc 26_numerics/random/random_device/cons/token.cc
27_io/filesystem/operations/copy_file.cc 27_io/filesystem/operations/status.cc
27_io/filesystem/operations/last_write_time.cc 27_io/filesystem/operations/temp_directory_path.cc
27_io/filesystem/operations/remove_all.cc
""".split()
# What the research note says the card does (sections 1.7 and 3.3); a different line is a change.
DEVIATION_LINES = {
    'hw_concurrency': 'S9-CXX hwconc PASS hardware_concurrency() is the online CPU count, not the affinity mask',
    'cv_clock': 'S9-CXX cvclock PASS steady_clock wait_until times out at its deadline; '
                'waits on system_clock (pthread_cond_timedwait, no pthread_cond_clockwait)',
    'f128_from_chars': 'S9-CXX f128 PASS from_chars(_Float128) (not declared in <charconv>) '
                       'reads 1+2^-100 at 64-bit (strtold fallback) precision',
}
# libstdc++.exp's flags for a test without dg-options (lib/libstdc++.exp v3_target_compile).
TS_FLAGS = ['-O2', '-D_GNU_SOURCE', '-DLOCALEDIR="."', '-fmessage-length=0', '-pthread']
RUN_SH = r'''#!/bin/sh
# Lead-only card program for S9-05 (tools/s9_05_checks.py build). Stage files.txt beside it:
#   card_run --timeout 600 --file-list .work/_shared/S9-05/files.txt .work/_shared/S9-05/run.sh
# Prints one RESULT line per program; the host compares them with expected.txt
# (tools/s9_05_checks.py compare). Exit 1 if any RESULT line is not in expected.txt.
cd -- "$(dirname -- "$0")" || exit 2
status=0
for prog in %s; do
    ./"$prog" > "$prog.out" 2>&1
    rc=$?
    line=$(grep '^S9-CXX ' "$prog.out" | tail -n 1)
    result="RESULT $prog exit=$rc ${line:--}"
    echo "$result"
    case $prog in *hw_concurrency*) sed 's/^/  | /' "$prog.out";; esac
    if ! grep -qxF "$result" expected.txt; then
        echo "UNEXPECTED $prog"; sed 's/^/  | /' "$prog.out" | head -n 40; status=1
    fi
done
exit $status
'''


def dg(text, kind):
    return re.findall(r'\{\s*dg-%s\s+([^}]*?)\s*(?:\{[^}]*\}\s*)?\}' % kind, text)


def ts_build(test, gxx, failures):
    """Builds one slice test; returns (program name, expected RESULT) for run tests, else None."""
    text = (TESTSUITE / test).read_text(errors='replace')
    what = (dg(text, 'do') or ['run'])[0].split()[0]
    std = '-std=gnu++20' if re.search(r'target c\+\+20', text) else '-std=gnu++17'
    options = [o for line in dg(text, 'options') for o in line.strip('"').split()]
    extra = ['-latomic'] if 'atomic/cons/user_pod' in test else []
    cmd = [gxx, std, *TS_FLAGS, *options, '-I', TESTSUITE / 'util', TESTSUITE / test]
    name = 'claude-s9ts-' + test[:-3].replace('/', '-') + '.mic'
    if what == 'compile':
        target = s7.SHARED / 'tmp/s9-05-compile.o'
        rc, out = s7.capture([*cmd, '-c', '-o', target])
        target.unlink(missing_ok=True)
    elif what == 'link':
        target = s7.SHARED / 'tmp/s9-05-link.mic'
        rc, out = s7.capture([*cmd, *extra, '-o', target])
        target.unlink(missing_ok=True)
    else:
        rc, out = s7.capture([*cmd, '-Wl,-rpath,$ORIGIN', *extra, '-o', OUT / name])
    print('%s %s %s: exit %d' % ('PASS' if rc == 0 else 'FAIL', what, test, rc), flush=True)
    if rc:
        failures.append('%s %s: %s' % (what, test, out.strip()[-600:]))
        return None
    return (name, 'RESULT %s exit=0 -' % name) if what == 'run' else None


def build_mode(prefix):
    gxx = prefix / 'bin/k1om-mpss-linux-g++'
    libdir = prefix / 'k1om-mpss-linux/lib64'
    if not gxx.exists():
        print('FAIL no C++ driver at %s: no libstdc++ to build the batch with' % gxx)
        return 1
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    failures, runs = [], []
    # build.py finds .work/_shared from its own path, so the main checkout's copy is the one to run.
    rc, text = s7.capture([sys.executable, PROJECT / 'tests/acceptance/s9_cxx/build.py', OUT,
                           '--cxx', gxx, '--libdir', libdir], timeout=1800)
    if rc:
        print('\n'.join(text.splitlines()[-15:]))
        print('FAIL build.py exit %d' % rc)
        return 1
    for row in (OUT / 'runs.txt').read_text().splitlines():
        prog, _, line = row.split(' ', 2)
        runs.append((prog, 'RESULT %s exit=%d %s' % (prog, ' FAIL ' in line, line)))
    (OUT / 'runs.txt').unlink()
    for test in SLICE:
        built = ts_build(test, gxx, failures)
        if built:
            runs.append(built)
    for name, line in DEVIATION_LINES.items():
        prog = 'claude-s9dev-%s.mic' % name
        rc, out = s7.capture([gxx, '-std=gnu++17', '-O2', '-pthread', DEVIATIONS / (name + '.cc'),
                              '-Wl,-rpath,$ORIGIN', '-o', OUT / prog])
        if rc:
            failures.append('%s: %s' % (prog, out.strip()[-600:]))
            continue
        runs.append((prog, 'RESULT %s exit=0 %s' % (prog, line)))

    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    binaries = sorted(OUT.glob('*.mic')) + sorted(OUT.glob('*.so*'))
    for binary in binaries:
        failures.extend('lint %s: %s' % (binary.name, row) for row in lint(binary, TC, os.environ.copy()))
    (OUT / 'expected.txt').write_bytes(''.join(line + '\n' for _, line in runs).encode())
    (OUT / 'run.sh').write_bytes((RUN_SH % ' '.join(prog for prog, _ in runs)).encode())
    staged = [p for p in sorted(OUT.iterdir()) if p.name not in ('run.sh', 'files.txt')]
    (OUT / 'files.txt').write_bytes(''.join('.work/_shared/S9-05/%s\n' % p.name for p in staged).encode())
    mib = sum(p.stat().st_size for p in staged) / 2 ** 20
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL build: %d problems' % len(failures))
        return 1
    print('PASS build: %d card programs, %d binaries lint clean, %d staged files (%.0f MiB); '
          '%d compile/link-only slice tests built on the host; native NOT RUN'
          % (len(runs), len(binaries), len(staged), mib, len(SLICE) - sum(p.startswith('claude-s9ts') for p, _ in runs)))
    print('Lead card run: tools/card_run --timeout 600 --file-list .work/_shared/S9-05/files.txt '
          '.work/_shared/S9-05/run.sh > card-out.txt; then tools/s9_05_checks.py compare card-out.txt')
    return 0


def compare_mode(output):
    got = [line for line in output.read_bytes().split(b'\n') if line.startswith(b'RESULT ')]
    want = (OUT / 'expected.txt').read_bytes().split(b'\n')[:-1]
    for g, w in itertools.zip_longest(got, want, fillvalue=b'(none)'):
        if g != w:
            print('  got:      %s\n  expected: %s' % (g.decode(errors='replace'), w.decode(errors='replace')))
    if got != want:
        print('FAIL compare: card RESULT lines differ from expected.txt')
        return 1
    print('PASS compare: %d RESULT lines byte-identical to expected.txt' % len(want))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('build', 'compare'))
    parser.add_argument('output', nargs='?', type=Path)
    parser.add_argument('--prefix', type=Path, default=s7.PREFIX)
    args = parser.parse_args()
    if args.mode == 'compare':
        if args.output is None:
            parser.error('compare needs the card output file')
        return compare_mode(args.output)
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        cyg = lambda p: subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(p)],
                                                text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), cyg(Path(__file__)), 'build',
                                '--prefix', cyg(args.prefix.resolve())])
    os.environ['TMPDIR'] = str(s7.SHARED / 'tmp')
    return build_mode(args.prefix)


if __name__ == '__main__':
    sys.exit(main())
