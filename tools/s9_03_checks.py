#!/usr/bin/env python3
"""S9-03 libstdc++ and libatomic for k1om, host side; invoke through tools/run.py.

    python tools/s9_03_checks.py configure  the build's libstdc++ configure results: cpu/generic,
                                            gnu symbol versions, gthreads, no rdrand, futex,
                                            generic C locale, static zoneinfo
    python tools/s9_03_checks.py abi        the installed libstdc++.so.6 exports every donor symbol
                                            at the same size (tools/abi_compare.py), and its
                                            extract_symvers output is the k1om baseline
    python tools/s9_03_checks.py links      build the lead's tests/acceptance/s9_cxx programs with
                                            the installed g++ into .work/_shared/S9-03, then check
                                            the static and shared hello (iostream), eh (throw/catch)
                                            and rtti (dynamic_cast) links, the staged libraries and lint

The compiler is the lane's prefix (tools/s7_09_checks.py install). The baseline diff stands in for
`make check-abi`, which needs DejaGnu. "Static" is libstdc++ and libgcc linked in with shared glibc:
the k1om sysroot has no libc.a.
Nothing runs natively here: the lead runs .work/_shared/S9-03/runs.txt on the card.
"""
import argparse
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

import abi_compare
import s7_09_checks as s7

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
TC = s7.TC
GXX = s7.PREFIX / 'bin/k1om-mpss-linux-g++'
LIBDIR = s7.PREFIX / 'k1om-mpss-linux/lib64'
OUT = s7.SHARED / 'S9-03'
LIBSTDCXX = s7.BUILD / 'k1om-mpss-linux/libstdc++-v3'
BASELINE = s7.SHARED / s7.GCC_TREE / 'libstdc++-v3/config/abi/post/k1om-linux-gnu/baseline_symbols.txt'
# What libstdc++'s configure must have decided (docs/research/knc-libstdcxx.md section 1.4).
CONFIG_NOTICES = ('CPU config directory is cpu/generic',
                  'versioning on shared library symbols is gnu')
CONFIG_RESULTS = {'for C locale to use': 'generic', 'for gthreads library': 'yes',
                  'for rdrand support in assembler': 'no'}
CONFIG_H = ('#define HAVE_LINUX_FUTEX 1', '#define _GLIBCXX_HAS_GTHREADS 1',
            '#define _GLIBCXX_STATIC_TZDATA 1')
CONFIG_H_ABSENT = ('_GLIBCXX_X86_RDRAND', '_GLIBCXX_X86_RDSEED')
PROGRAMS = ('hello', 'eh', 'rtti')
OURS = {'libstdc++.so.6', 'libgcc_s.so.1'}
SONAMES = ('libstdc++.so.6', 'libatomic.so.1', 'libgcc_s.so.1')


def configure_mode():
    log = (LIBSTDCXX / 'config.log').read_text(errors='replace')
    header = (LIBSTDCXX / 'config.h').read_text(errors='replace')
    failures = ['config.log lacks "%s"' % line for line in CONFIG_NOTICES
                if not re.search(r'^configure:[0-9]+: %s$' % re.escape(line), log, re.M)]
    for check, expected in CONFIG_RESULTS.items():
        # The result follows its check, after the output of whatever the check compiled.
        found = re.search(r'^configure:[0-9]+: checking %s$.*?^configure:[0-9]+: result: ([^\n]*)$'
                          % re.escape(check), log, re.M | re.S)
        if not found or found.group(1) != expected:
            failures.append('config.log: checking %s: %s, expected %s'
                            % (check, found.group(1) if found else 'not run', expected))
    failures += ['config.h lacks "%s"' % line for line in CONFIG_H if line not in header]
    failures += ['config.h defines ' + name for name in CONFIG_H_ABSENT
                 if re.search(r'^#define %s\b' % name, header, re.M)]
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL configure: %d problems' % len(failures))
        return 1
    print('PASS configure: cpu/generic, gnu symvers, gthreads yes, rdrand no, futex yes, '
          'clocale generic, zoneinfo static')
    return 0


def abi_mode():
    library = LIBDIR / 'libstdc++.so.6'
    donor = abi_compare.library_symbols(abi_compare.DONOR)
    ok = abi_compare.report('library ' + library.name, donor, abi_compare.library_symbols(library))
    fresh = s7.SHARED / 'tmp/s9-03-symvers.txt'
    subprocess.run(['sh', str(LIBSTDCXX / 'scripts/extract_symvers'), str(library), str(fresh)],
                   cwd=str(fresh.parent), check=True)
    built = set(fresh.read_text().split())
    fresh.unlink()
    baseline = set(BASELINE.read_text().split())
    for label, rows in (('not in the baseline', built - baseline), ('only in the baseline', baseline - built)):
        for row in sorted(rows)[:10]:
            print('  %s: %s' % (label, row))
    print('baseline %s: %d symbols; library adds %d, lacks %d'
          % (BASELINE.parent.name, len(baseline), len(built - baseline), len(baseline - built)))
    if not ok or not baseline or built != baseline:
        print('FAIL abi')
        return 1
    print('PASS abi: 0 donor symbols missing, 0 size differences; extract_symvers matches the baseline')
    return 0


def links_mode():
    if not GXX.exists():
        print('FAIL no C++ driver at %s: the installed compiler has no g++ and no libstdc++' % GXX)
        return 1
    failures = []
    for library in ('libstdc++.so', 'libstdc++.a', 'libsupc++.a', 'libatomic.so'):
        _, found = s7.capture([GXX, '-march=knc', '-print-file-name=' + library])
        if not s7.under_prefix(found.strip()):
            failures.append('driver finds %s outside the prefix: %s' % (library, found.strip()))
    # build.py finds .work/_shared from its own path, so the main checkout's copy is the one to run.
    rc, text = s7.capture([sys.executable, PROJECT / 'tests/acceptance/s9_cxx/build.py', OUT,
                           '--cxx', GXX, '--libdir', LIBDIR], timeout=1800)
    if rc != 0:
        print('\n'.join(text.splitlines()[-15:]))
        print('FAIL build.py exit %d' % rc)
        return 1
    for name in PROGRAMS:
        static = OUT / ('claude-s9cxx-new-%s-static.mic' % name)
        linked_in = s7.needed(static) & OURS
        if linked_in:
            failures.append('%s: static link still needs %s' % (static.name, ' '.join(sorted(linked_in))))
        shared = OUT / ('claude-s9cxx-new-%s-shared.mic' % name)
        if not OURS <= s7.needed(shared):
            failures.append('%s: DT_NEEDED %s' % (shared.name, ' '.join(sorted(s7.needed(shared)))))
    for soname in SONAMES:
        library = OUT / soname
        if '(SONAME)' not in s7.readelf('-d', library) or '[%s]' % soname not in s7.readelf('-d', library):
            failures.append('%s lacks SONAME %s' % (library, soname))
        outside = [dep for dep in s7.needed(library)
                   if dep not in SONAMES and not (TC / 'sysroot/lib64' / dep).is_file()]
        if outside:
            failures.append('%s needs libraries the sysroot lacks: %s' % (soname, ' '.join(outside)))
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    binaries = sorted(OUT.glob('*.mic')) + sorted(OUT.glob('*.so*'))
    for binary in binaries:
        failures.extend('lint %s: %s' % (binary.name, row) for row in lint(binary, TC, os.environ.copy()))
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL links: %d problems' % len(failures))
        return 1
    print('PASS links: static and shared %s link; %s from the prefix; %d staged binaries lint clean; '
          'native NOT RUN' % (', '.join(PROGRAMS), ', '.join(SONAMES), len(binaries)))
    print('Lead card run: ' + str(OUT / 'runs.txt'))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('configure', 'abi', 'links'))
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, args.mode])
    OUT.mkdir(exist_ok=True)
    os.environ['TMPDIR'] = str(s7.SHARED / 'tmp')
    return {'configure': configure_mode, 'abi': abi_mode, 'links': links_mode}[args.mode]()


if __name__ == '__main__':
    sys.exit(main())
