#!/usr/bin/env python3
"""S7-09 libgfortran isolation and packaging; invoke through tools/run.py.

    python tools/s7_09_checks.py install    install the shared tree's compiler, libgcc and
                                            libgfortran into the private prefix gcc-knc-<version>
    python tools/s7_09_checks.py links      static and shared card builds with the installed driver;
                                            link map, spec, module directory, SONAME, versions, rpath
    python tools/s7_09_checks.py negative   linking the donor's GCC 5 libgfortran (-L to its
                                            directory) or reading its .mod files (-I) must fail
                                            with a clear error

The private prefix is .work/_shared/gcc-knc-<BASE-VER>; the driver relocates relative to its own
path, so `make install DESTDIR=` is staged and moved there. The shared build puts libgfortran.so.5
and libgcc_s.so.1 in a private lib directory next to bin and finds them by DT_RPATH $ORIGIN/../lib,
never over the card's own libraries. Nothing runs natively here: the lead runs
.work/_shared/S7-09/run.sh on the card.
"""
import argparse
import filecmp
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build'
VERSION = (SHARED / 'gcc/gcc/BASE-VER').read_text().strip()
PREFIX = SHARED / ('gcc-knc-' + VERSION)
GFORTRAN = PREFIX / 'bin/k1om-mpss-linux-gfortran'
OUT = SHARED / 'S7-09'
SRC = ROOT / 'tests/t2/s7-09/runtime.f90'
DONOR_LIB = TC / 'cross/k1om-mpss-linux/lib64'
DONOR_FINCLUDE = TC / 'cross/lib/gcc/k1om-mpss-linux/5.1.1/finclude'
STATIC_NEEDED = {'libm.so.6', 'libc.so.6', 'ld-linux-k1om.so.2'}
GUARD = "GCC-KNC: the libgfortran found first is older than this compiler's libgfortran.so.5"
OLD_MOD = 'because it was created by a different version of GNU Fortran'
RPATH = '$ORIGIN/../lib'


def capture(args, timeout=600):
    proc = subprocess.run(list(map(str, args)), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors='replace', timeout=timeout)
    return proc.returncode, proc.stdout


def readelf(*args):
    return subprocess.check_output([str(TC / 'cross/bin/k1om-mpss-linux-readelf'), *map(str, args)],
                                   text=True, errors='replace')


def needed(binary):
    return set(re.findall(r'\(NEEDED\)\s+Shared library: \[([^\]]+)\]', readelf('-d', binary)))


def under_prefix(path):
    return os.path.realpath(path).startswith(os.path.realpath(PREFIX) + '/')


def install_mode():
    configured = re.search(r'^prefix = (\S+)$', (BUILD / 'Makefile').read_text(), re.M).group(1)
    stage = OUT / 'stage'
    shutil.rmtree(stage, ignore_errors=True)
    rc, text = capture(['make', '-C', BUILD, 'install-gcc', 'install-target-libgcc',
                        'install-target-libgfortran', 'DESTDIR=' + str(stage)], timeout=3600)
    if rc != 0:
        print('\n'.join(text.splitlines()[-15:]))
        print('FAIL make install exit %d' % rc)
        return 1
    shutil.rmtree(PREFIX, ignore_errors=True)
    shutil.move(str(stage) + configured, str(PREFIX))
    shutil.rmtree(stage)
    print('PASS installed into ' + str(PREFIX))
    return 0


def link(name, extra, binary):
    """Link the program with the installed driver; return (failures, -v text, map text)."""
    linkmap = OUT / (name + '.map')
    binary.unlink(missing_ok=True)
    rc, text = capture([GFORTRAN, '-v', '-march=knc', '-O1', '-Wall', '-J', OUT / 'mod', *extra,
                        SRC, '-o', binary, '-Wl,-Map,' + str(linkmap)])
    if rc != 0:
        return ['%s: link exit %d: %s' % (name, rc, ' | '.join(text.splitlines()[-6:]))], text, ''
    failures = []
    specs = re.findall(r'^Reading specs from (\S*libgfortran\.spec)$', text, re.M)
    if not specs or not all(under_prefix(spec) for spec in specs):
        failures.append(name + ': libgfortran.spec not read from the prefix: ' + repr(specs))
    modules = re.findall(r'-fintrinsic-modules-path (\S+)', text)
    if not modules or not all(under_prefix(path) and path.rstrip('/').endswith('finclude')
                              for path in modules):
        failures.append(name + ': intrinsic module directory not the prefix finclude: ' + repr(modules))
    maptext = linkmap.read_text(errors='replace')
    runtime = sorted(set(re.findall(r'(\S*lib(?:gfortran|gcc|gcc_eh|gcc_s)\.(?:a|so[.\d]*))', maptext)))
    if not any('libgfortran' in path for path in runtime):
        failures.append(name + ': link map names no libgfortran')
    failures.extend(name + ': runtime from outside the prefix: ' + path
                    for path in runtime if not under_prefix(path))
    return failures, text, maptext


def links_mode():
    for sub in ('bin', 'lib', 'mod'):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    failures = []

    static = OUT / 'bin/static.mic'
    problems, _, maptext = link('static', ['-static-libgfortran', '-static-libgcc'], static)
    if not problems:
        if not re.search(r'\S*libgfortran\.a\(', maptext):
            problems.append('static: link map shows no libgfortran.a members')
        extra = needed(static) - STATIC_NEEDED
        if extra:
            problems.append('static: shared dependencies beyond libc/libm: ' + ' '.join(sorted(extra)))
        again = OUT / 'static-again.mic'
        more, _, _ = link('static-again', ['-static-libgfortran', '-static-libgcc'], again)
        problems.extend(more)
        if not more and not filecmp.cmp(static, again, shallow=False):
            problems.append('static: a second identical invocation produced a different executable')
        again.unlink(missing_ok=True)
        (OUT / 'static-again.map').unlink(missing_ok=True)
    print(('PASS ' if not problems else 'FAIL ') + 'static: prefix archive, spec and finclude; '
          'no shared libgfortran/libgcc; reproducible', flush=True)
    failures.extend(problems)

    shared = OUT / 'bin/shared.mic'
    problems, _, _ = link('shared', ['-Wl,-rpath,' + RPATH], shared)
    if not problems:
        deps = needed(shared)
        if not {'libgfortran.so.5', 'libgcc_s.so.1'} <= deps or 'libgfortran.so.3' in deps:
            problems.append('shared: DT_NEEDED ' + ' '.join(sorted(deps)))
        dynamic = readelf('-d', shared)
        paths = re.findall(r'\((RPATH|RUNPATH)\)\s+Library r(?:un)?path: \[([^\]]+)\]', dynamic)
        if paths != [('RPATH', RPATH)]:
            problems.append('shared: loader path %r, expected DT_RPATH %s' % (paths, RPATH))
        verneed = readelf('-V', shared)
        block = re.search(r'File: libgfortran\.so\.5\s+Cnt: \d+\n((?:\s+0x.*\n)+)', verneed)
        versions = re.findall(r'Name: (\S+)', block.group(1)) if block else []
        if not versions or not all(v.startswith('GFORTRAN_') for v in versions):
            problems.append('shared: libgfortran.so.5 version needs %r' % versions)
        for soname in ('libgfortran.so.5', 'libgcc_s.so.1'):
            shutil.copyfile(PREFIX / 'k1om-mpss-linux/lib64' / soname, OUT / 'lib' / soname)
            library = OUT / 'lib' / soname
            if '[%s]' % soname not in readelf('-d', library):
                problems.append('shared: %s lacks SONAME %s' % (library, soname))
            problems.extend('shared: lint %s: %s' % (soname, row)
                            for row in lint(library, TC, os.environ.copy()))
        defined = readelf('-V', OUT / 'lib/libgfortran.so.5')
        for node in ('GFORTRAN_8', 'GFORTRAN_16'):
            if not re.search(r'Name: %s\n' % re.escape(node), defined):
                problems.append('shared: libgfortran.so.5 does not define version ' + node)
        print('shared: libgfortran.so.5 needs ' + ' '.join(versions))
    print(('PASS ' if not problems else 'FAIL ') + 'shared: SONAME .so.5, GFORTRAN_* versions, '
          'DT_RPATH ' + RPATH, flush=True)
    failures.extend(problems)

    for binary in (static, shared):
        if binary.exists():
            failures.extend('lint %s: %s' % (binary.name, row)
                            for row in lint(binary, TC, os.environ.copy()))
    for problem in failures:
        print('  ' + problem)
    (OUT / 'run.sh').write_text(
        '#!/bin/sh\n'
        '# Lead-only card runner for S7-09. Copy the complete S7-09 directory (bin, lib) to the card.\n'
        '# Usage: sh /absolute/path/S7-09/run.sh   (no arguments; exit 0 means every check passed)\n'
        'base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        'status=0\n'
        'old=$(ls /lib64/libgfortran.so.3 /usr/lib64/libgfortran.so.3 2>/dev/null | head -n 1)\n'
        'if [ -n "$old" ]; then echo "old runtime present: $old"; '
        'else echo "FAIL no libgfortran.so.3 on the card"; status=1; fi\n'
        'for exe in static shared; do\n'
        '    if "$base/bin/$exe.mic" > "$base/$exe.out" 2>&1 && grep -q "^PASS runtime$" "$base/$exe.out"; then\n'
        '        echo "PASS $exe"\n'
        '    else\n'
        '        echo "FAIL $exe"; cat "$base/$exe.out"; status=1\n'
        '    fi\n'
        'done\n'
        'LD_TRACE_LOADED_OBJECTS=1 "$base/bin/shared.mic" > "$base/shared.loader" 2>&1\n'
        'cat "$base/shared.loader"\n'
        'for lib in libgfortran.so.5 libgcc_s.so.1; do\n'
        '    if grep -q "$lib => $base/bin/../lib/$lib " "$base/shared.loader"; then echo "PASS loader $lib private"\n'
        '    else echo "FAIL loader $lib not from $base/lib"; status=1; fi\n'
        'done\n'
        'if grep -q "libgfortran.so.3" "$base/shared.loader"; then echo "FAIL loader pulled libgfortran.so.3"; status=1; fi\n'
        'exit $status\n', newline='\n')
    if failures:
        return 1
    print('PASS build/lint: bin/static.mic bin/shared.mic lib/libgfortran.so.5 lib/libgcc_s.so.1; '
          'native NOT RUN', flush=True)
    print('Lead invocation: sh ' + str(OUT / 'run.sh') + ' (no arguments; exit 0 means every check passed).')
    return 0


def negative_mode():
    target = OUT / 'old-runtime.mic'
    hello = SRC.parent / 'negative/hello.f90'
    cases = (
        ('old shared runtime', [GFORTRAN, '-march=knc', '-L', DONOR_LIB, hello, '-o', target], GUARD),
        ('old static runtime', [GFORTRAN, '-march=knc', '-static-libgfortran', '-L', DONOR_LIB,
                                hello, '-o', target], GUARD),
        ('old IEEE modules', [GFORTRAN, '-march=knc', '-fsyntax-only', '-I', DONOR_FINCLUDE, SRC],
         OLD_MOD),
    )
    failed = False
    for label, args, expect in cases:
        target.unlink(missing_ok=True)
        rc, text = capture(args)
        ok = rc != 0 and expect in text and not target.exists()
        failed |= not ok
        print(('PASS ' if ok else 'FAIL ') + label + ': exit %d, expected "%s"' % (rc, expect), flush=True)
        if not ok:
            print(text.strip()[-600:])
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('install', 'links', 'negative'))
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, args.mode])
    OUT.mkdir(exist_ok=True)
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    if args.mode != 'install' and not GFORTRAN.exists():
        print('FAIL no installed driver at ' + str(GFORTRAN) + '; run the install mode first')
        return 1
    return {'install': install_mode, 'links': links_mode, 'negative': negative_mode}[args.mode]()


if __name__ == '__main__':
    sys.exit(main())
