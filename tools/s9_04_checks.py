#!/usr/bin/env python3
"""S9-04 libstdc++ packaging and the g++ link guard, host side; invoke through tools/run.py.

    python tools/s9_04_checks.py negative   a g++ link whose -lstdc++ finds the donor's GCC 5
                                            library (-L to its directory), shared or with
                                            -static-libstdc++, must fail with the guard's message;
                                            the same links without it must succeed
    python tools/s9_04_checks.py package    readelf on the prefix's libstdc++.so.6 and libatomic.so.1
                                            (SONAME, version nodes) and on the s9_cxx cross-DSO pairs
                                            (DT_RPATH $ORIGIN/../lib), staged for the card in
                                            .work/_shared/S9-04 (bin, lib, run.sh)

The compiler is the lane's prefix (tools/s7_09_checks.py install). The card payload is the s9_cxx
xdso pairs: a GCC 16 main with a donor-built library, and a donor-built main with a GCC 16 library,
both loading this prefix's libstdc++.so.6 from lib/ beside bin/. Nothing runs natively here: the
lead runs .work/_shared/S9-04/run.sh on the card.
"""
import argparse
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys

import s7_09_checks as s7

ROOT = Path(__file__).resolve().parents[1]
TC = s7.TC
GXX = s7.PREFIX / 'bin/k1om-mpss-linux-g++'
DONOR_GXX = TC / 'cross/bin/k1om-mpss-linux-g++'
LIBDIR = s7.PREFIX / 'k1om-mpss-linux/lib64'
DONOR_LIB = TC / 'cross/k1om-mpss-linux/lib64'
SRC = ROOT / 'tests/acceptance/s9_cxx'
OUT = s7.SHARED / 'S9-04'
GUARD = "GCC-KNC: the libstdc++ found first is older than this compiler's libstdc++.so.6"
RPATH = s7.RPATH
OURS = ('libstdc++.so.6', 'libgcc_s.so.1', 'libatomic.so.1')
NEWEST = 'GLIBCXX_3.4.36'
FLAGS = ['-std=gnu++14', '-O2', '-pthread', '-I', SRC]
EXPECT = 'S9-CXX xdso PASS checks=5 failures=0'


def negative_mode():
    target = OUT / 'old-runtime.mic'
    hello = SRC / 'hello.cc'
    static = ['-static-libstdc++', '-static-libgcc']
    failed = False
    for label, extra in (('shared', []), ('static', static)):
        # The same link without the donor's directory must still succeed: the guard passes ours.
        target.unlink(missing_ok=True)
        rc, text = s7.capture([GXX, *FLAGS, *extra, hello, '-o', target])
        ok = rc == 0 and target.exists()
        failed |= not ok
        print(('PASS ' if ok else 'FAIL ') + 'own %s libstdc++: exit %d' % (label, rc), flush=True)
        if not ok:
            print(text.strip()[-600:])
        target.unlink(missing_ok=True)
        rc, text = s7.capture([GXX, *FLAGS, *extra, '-L', DONOR_LIB, hello, '-o', target])
        ok = rc != 0 and GUARD in text and not target.exists()
        failed |= not ok
        print(('PASS ' if ok else 'FAIL ') + 'donor %s libstdc++: exit %d, expected "%s"'
              % (label, rc, GUARD), flush=True)
        if not ok:
            print(text.strip()[-600:])
    target.unlink(missing_ok=True)
    return int(failed)


def defined_versions(library):
    return re.findall(r'Name: (\S+)\n', s7.readelf('-V', library).split('Version needs section')[0])


def package_mode():
    shutil.rmtree(OUT / 'bin', ignore_errors=True)
    shutil.rmtree(OUT / 'lib', ignore_errors=True)
    (OUT / 'bin').mkdir(parents=True)
    (OUT / 'lib').mkdir()
    failures = []
    for soname in OURS:
        shutil.copyfile(LIBDIR / soname, OUT / 'lib' / soname)
        if '[%s]' % soname not in s7.readelf('-d', OUT / 'lib' / soname):
            failures.append('%s lacks SONAME %s' % (soname, soname))
    nodes = defined_versions(OUT / 'lib/libstdc++.so.6')
    for node in ('GLIBCXX_3.4.21', NEWEST, 'CXXABI_1.3.9'):
        if node not in nodes:
            failures.append('libstdc++.so.6 does not define version ' + node)
    glibcxx = [n for n in nodes if n.startswith('GLIBCXX_3.4')]
    if glibcxx and max(glibcxx, key=lambda n: [int(p) for p in n[8:].split('.')]) != NEWEST:
        failures.append('libstdc++.so.6 newest GLIBCXX node is not ' + NEWEST)
    print('libstdc++.so.6 defines %d version nodes, newest GLIBCXX %s' % (len(nodes), glibcxx[-1:]))
    if 'LIBATOMIC_1.0' not in defined_versions(OUT / 'lib/libatomic.so.1'):
        failures.append('libatomic.so.1 does not define LIBATOMIC_1.0')

    # (main compiler, library compiler): the shared program, and the donor-built program.
    compilers = {'new': GXX, 'donor': DONOR_GXX}
    pairs = (('new', 'donor'), ('donor', 'new'))
    for ltag in ('new', 'donor'):
        lib = OUT / 'lib' / ('libclaude-s9x-%s.so' % ltag)
        rc, text = s7.capture([compilers[ltag], *FLAGS, '-fPIC', '-shared', '-Wl,-soname,' + lib.name,
                               SRC / 'xlib.cc', '-o', lib])
        if rc:
            failures.append('%s: exit %d: %s' % (lib.name, rc, text.strip()[-400:]))
    for mtag, ltag in pairs:
        prog = OUT / 'bin' / ('claude-s9cxx-xdso-%s-%s.mic' % (mtag, ltag))
        lib = OUT / 'lib' / ('libclaude-s9x-%s.so' % ltag)
        rc, text = s7.capture([compilers[mtag], *FLAGS, SRC / 'xmain.cc', lib, '-Wl,-rpath,' + RPATH,
                               '-o', prog])
        if rc:
            failures.append('%s: exit %d: %s' % (prog.name, rc, text.strip()[-400:]))
            continue
        paths = re.findall(r'\((RPATH|RUNPATH)\)\s+Library r(?:un)?path: \[([^\]]+)\]', s7.readelf('-d', prog))
        if paths != [('RPATH', RPATH)]:
            failures.append('%s: loader path %r, expected DT_RPATH %s' % (prog.name, paths, RPATH))
        if 'libstdc++.so.6' not in s7.needed(prog):
            failures.append('%s: DT_NEEDED %s' % (prog.name, ' '.join(sorted(s7.needed(prog)))))
        block = re.search(r'File: libstdc\+\+\.so\.6\s+Cnt: \d+\n((?:\s+0x\w+:\s+Name:.*\n)+)', s7.readelf('-V', prog))
        print('%s: RPATH %s; libstdc++.so.6 needs %s' % (prog.name, paths,
              ' '.join(re.findall(r'Name: (\S+)', block.group(1))) if block else 'nothing'))

    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    binaries = sorted((OUT / 'bin').glob('*.mic')) + sorted((OUT / 'lib').glob('*.so*'))
    for binary in binaries:
        failures.extend('lint %s: %s' % (binary.name, row) for row in lint(binary, TC, os.environ.copy()))
    (OUT / 'run.sh').write_text(
        '#!/bin/sh\n'
        '# Lead-only card runner for S9-04. Copy the complete S9-04 directory (bin, lib) to the card.\n'
        '# Usage: sh /absolute/path/S9-04/run.sh   (no arguments; exit 0 means every check passed)\n'
        'base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        'status=0\n'
        'donor=$(ls -d /lib64/libstdc++.so.6 /usr/lib64/libstdc++.so.6 2>/dev/null | head -n 1)\n'
        'if [ -n "$donor" ]; then donor=$(dirname "$donor"); echo "donor libstdc++ directory: $donor"; '
        'else echo "FAIL no libstdc++.so.6 on the card"; exit 1; fi\n'
        'for exe in %s; do\n'
        '    out="$base/$exe.out"\n'
        '    if LD_LIBRARY_PATH="$donor" "$base/bin/$exe.mic" > "$out" 2>&1 && grep -qx "%s" "$out"; then\n'
        '        echo "PASS $exe"\n'
        '    else\n'
        '        echo "FAIL $exe"; cat "$out"; status=1\n'
        '    fi\n'
        '    LD_TRACE_LOADED_OBJECTS=1 LD_LIBRARY_PATH="$donor" "$base/bin/$exe.mic" > "$base/$exe.loader" 2>&1\n'
        '    cat "$base/$exe.loader"\n'
        '    if grep -q "libstdc++.so.6 => $base/bin/../lib/libstdc++.so.6 " "$base/$exe.loader"; then\n'
        '        echo "PASS loader $exe: libstdc++.so.6 private"\n'
        '    else echo "FAIL loader $exe: libstdc++.so.6 not from $base/lib"; status=1; fi\n'
        'done\n'
        'exit $status\n' % (' '.join('claude-s9cxx-xdso-%s-%s' % pair for pair in pairs), EXPECT),
        newline='\n')
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL package: %d problems' % len(failures))
        return 1
    print('PASS package: SONAMEs %s; libstdc++.so.6 defines %s; xdso pairs DT_RPATH %s; '
          '%d staged binaries lint clean; native NOT RUN' % (', '.join(OURS), NEWEST, RPATH, len(binaries)))
    print('Lead invocation: sh ' + str(OUT / 'run.sh') + ' (no arguments; exit 0 means every check passed).')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('negative', 'package'))
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, args.mode])
    OUT.mkdir(exist_ok=True)
    os.environ['TMPDIR'] = str(s7.SHARED / 'tmp')
    if not GXX.exists():
        print('FAIL no installed driver at ' + str(GXX) + '; run tools/s7_09_checks.py install first')
        return 1
    return {'negative': negative_mode, 'package': package_mode}[args.mode]()


if __name__ == '__main__':
    sys.exit(main())
