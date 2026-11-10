#!/usr/bin/env python3
"""S9-03 libstdc++ and libatomic for k1om, host side; invoke through tools/run.py.

    python tools/s9_03_checks.py links   build the lead's tests/acceptance/s9_cxx programs with the
                                         installed g++ into .work/_shared/S9-03, then check the static
                                         and shared hello (iostream), eh (throw/catch) and rtti
                                         (dynamic_cast) links, the staged libraries and lint

"Static" is libstdc++ and libgcc linked in with shared glibc: the k1om sysroot has no libc.a.
Nothing runs natively here: the lead runs .work/_shared/S9-03/runs.txt on the card.
"""
import argparse
import os
from pathlib import Path
import runpy
import subprocess
import sys

import s7_09_checks as s7

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
TC = s7.TC
GXX = s7.PREFIX / 'bin/k1om-mpss-linux-g++'
LIBDIR = s7.PREFIX / 'k1om-mpss-linux/lib64'
OUT = s7.SHARED / 'S9-03'
PROGRAMS = ('hello', 'eh', 'rtti')
OURS = {'libstdc++.so.6', 'libgcc_s.so.1'}
SONAMES = ('libstdc++.so.6', 'libatomic.so.1', 'libgcc_s.so.1')


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
    parser.add_argument('mode', choices=('links',))
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, args.mode])
    OUT.mkdir(exist_ok=True)
    os.environ['TMPDIR'] = str(s7.SHARED / 'tmp')
    return {'links': links_mode}[args.mode]()


if __name__ == '__main__':
    sys.exit(main())
