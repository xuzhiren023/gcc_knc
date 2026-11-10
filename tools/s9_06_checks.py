#!/usr/bin/env python3
"""S9-06 libgomp for k1om: selection, packaging and link guard; invoke through tools/run.py.

    python tools/s9_06_checks.py configure
        libgomp/configure.tgt selects the KNC futex runtime for k1om, and the shared build's
        libgomp was configured with --enable-linux-futex and that config_path.
    python tools/s9_06_checks.py build
        builds the tests/acceptance/s9_omp programs (build.py) with the installed prefix into one
        flat card batch in .work/_shared/S9-06; checks SONAME, version nodes, DT_NEEDED, DT_RPATH
        and the lint (delay present; no pause, cmpxchg16b or SSE). Writes run.sh (the card
        program) and files.txt (its --file-list).
    python tools/s9_06_checks.py guard
        a -fopenmp link that finds an older libgomp.so.1 first (-L to a stub without the GOMP_6.0
        symbols) must fail with the guard text.

The compiler is the lane's installed prefix (tools/s7_09_checks.py install). Nothing runs natively
here: the lead runs run.sh on the card.
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
OUT = s7.SHARED / 'S9-06'
GCC = s7.PREFIX / 'bin/k1om-mpss-linux-gcc'
LIBDIR = s7.PREFIX / 'k1om-mpss-linux/lib64'
PROGRAMS = ROOT / 'tests/acceptance/s9_omp'
TARGET = 'k1om-mpss-linux-gnu'
CONFIG_PATH = 'linux/knc linux/x86 linux posix'
# The newest node of each family in libgomp.map (docs/research/knc-libgomp.md section 2).
VERSION_NODES = ('OMP_5.2', 'GOMP_6.0.1', 'OACC_2.6.1', 'GOACC_2.0.2', 'GOMP_PLUGIN_1.4')
GLIBC = {'libc.so.6', 'libm.so.6', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1',
         'ld-linux-k1om.so.2'}
RPATH = '$ORIGIN/../lib'
GUARD = "GCC-KNC: the libgomp found first is older than this compiler's libgomp.so.1"
RUN_SH = r'''#!/bin/sh
# Lead-only card program for S9-06 (tools/s9_06_checks.py build); files.txt is its --file-list:
#   card_run --timeout 1800 --file-list .work/_shared/S9-06/files.txt .work/_shared/S9-06/run.sh THREADS
# THREADS is OMP_NUM_THREADS: 60 (60x1) or 240 (60x4, the whole-card --benchmark job). The
# environment passes through (MALLOC_ARENA_MAX, OMP_STACKSIZE). Exit 0 when every RESULT and CHECK
# line says ok. In order: each runs.txt job with OMP_DISPLAY_ENV=verbose; the passing shared
# programs under OMP_WAIT_POLICY=passive and then active, with the CPU ticks of each pass (this
# shell's cutime+cstime in /proc/$$/stat); the OpenMP runtimes on the card; the topology files;
# the S9-07 fixture (/proc/cpuinfo and the sysfs cpu list).
# BusyBox 1.19 sh: no timeout applet and no grep -x, so a watcher kills a program after LIMIT
# seconds and a read loop does the exact match (as in S9-05's runner).
cd -- "$(dirname -- "$0")" || exit 2
threads=${1:-60}
LIMIT=300
status=0
export OMP_NUM_THREADS=$threads OMP_DISPLAY_ENV=verbose

has_line() {
    found=1
    while IFS= read -r have; do [ "$have" = "$2" ] && found=0; done < "$1"
    return $found
}

child_ticks() {
    set -- $(cat /proc/$$/stat)
    echo $((${16} + ${17}))
}

# run_job PROGRAM EXPECTED-LINE LABEL DISPLAY-LINE: one RESULT line; status=1 unless the program
# prints EXPECTED-LINE and its thread count, exits to match, and libgomp displays DISPLAY-LINE.
run_job() {
    prog=$1 want=$2 label=$3 display=$4
    rm -f "$prog.timeout"
    ./"$prog" > "$prog.out" 2>&1 &
    pid=$!
    ( sleep $LIMIT; touch "$prog.timeout"; kill -9 $pid ) > /dev/null 2>&1 &
    watcher=$!
    wait $pid
    rc=$?
    kill $watcher 2> /dev/null
    [ -e "$prog.timeout" ] && rc=timeout
    case $want in *" FAIL "*) wantrc=1;; *) wantrc=0;; esac
    set -- $want
    why=
    [ "$rc" = "$wantrc" ] || why="$why exit=$rc(want $wantrc)"
    has_line "$prog.out" "$want" || why="$why no-result-line"
    has_line "$prog.out" "S9-OMP $2 threads=$threads" || why="$why no-threads=$threads-line"
    grep -q "OMP_NUM_THREADS = '$threads'" "$prog.out" || why="$why no-OMP_NUM_THREADS-display"
    grep -q "$display" "$prog.out" || why="$why no-display($display)"
    if [ -z "$why" ]; then
        echo "RESULT threads=$threads $label $prog exit=$rc ok"
    else
        echo "RESULT threads=$threads $label $prog UNEXPECTED:$why"
        sed 's/^/  | /' "$prog.out" | head -n 60
        status=1
    fi
}

while read -r prog files want <&3; do
    run_job "$prog" "$want" default "GOMP_SPINCOUNT = '"
    case $prog in *-runtime-shared.mic) grep '^mapped ' "$prog.out" | sed 's/^/  | /';; esac
done 3< runs.txt

# policy_pass POLICY SPINCOUNT: the passing shared programs again; CPU ticks of the pass in $ticks.
policy_pass() {
    export OMP_WAIT_POLICY=$1
    before=$(child_ticks)
    while read -r prog files want <&3; do
        case $prog in *-break-*|*-static.mic) continue;; esac
        run_job "$prog" "$want" "$1" "GOMP_SPINCOUNT = '$2'"
    done 3< runs.txt
    after=$(child_ticks)
    unset OMP_WAIT_POLICY
    ticks=$((after - before))
}
policy_pass passive 0
passive=$ticks
policy_pass active 30000000000
if [ "$passive" -lt "$ticks" ]; then
    echo "CHECK threads=$threads wait-policy cpu-ticks passive=$passive active=$ticks ok"
else
    echo "CHECK threads=$threads wait-policy cpu-ticks passive=$passive active=$ticks UNEXPECTED: passive waiters used no less CPU than spinning ones"
    status=1
fi

echo "PROBE OpenMP runtimes on the card:"
for f in $(find /lib64 /usr/lib64 /lib /usr/lib /opt -name '*gomp*' -o -name '*iomp*' 2> /dev/null); do
    echo "PROBE runtime $(ls -l "$f")"
    [ -f "$f" ] && [ ! -h "$f" ] || continue
    if command -v readelf > /dev/null 2>&1; then
        readelf -d -V "$f" 2>&1 | grep -e SONAME -e NEEDED -e 'Name: ' | sed 's/^/  | /'
    elif command -v strings > /dev/null 2>&1; then
        echo "  | names (strings): $(strings "$f" | grep -e '^G*OMP_[0-9.]*$' -e '^G*OACC_[0-9.]*$' \
            -e '^GOMP_PLUGIN_[0-9.]*$' -e '^VERSION$' -e '^lib[a-z0-9_]*\.so[.0-9]*$' | sort -u | tr '\n' ' ')"
    else
        echo "  | no readelf or strings on the card"
    fi
done
for f in thread_siblings_list core_siblings_list; do
    path=/sys/devices/system/cpu/cpu1/topology/$f
    if [ -r "$path" ]; then echo "PROBE cpu1 $f: $(cat "$path")"; else echo "PROBE cpu1 $f: missing"; fi
done
echo "BEGIN /proc/cpuinfo"
cat /proc/cpuinfo
echo "END /proc/cpuinfo"
echo "BEGIN ls /sys/devices/system/cpu"
ls /sys/devices/system/cpu 2>&1
echo "END ls /sys/devices/system/cpu"
exit $status
'''


def configure_mode():
    failures = []
    tgt = s7.SHARED / s7.GCC_TREE / 'libgomp/configure.tgt'
    rc, text = s7.capture(['bash', '-c', 'target=$1; enable_linux_futex=yes; gcc_cv_have_tls=yes; '
                           'XCFLAGS=; CC=false; CFLAGS=; . "$2" > /dev/null && '
                           'printf "%s\\n" "$config_path"', 'configure.tgt', TARGET, tgt])
    selected = text.strip()
    ok = rc == 0 and selected == CONFIG_PATH
    print('%s configure.tgt, %s with futex: config_path="%s"' % ('PASS' if ok else 'FAIL', TARGET, selected))
    if not ok:
        failures.append('configure.tgt does not select "%s"' % CONFIG_PATH)

    status = s7.BUILD / 'k1om-mpss-linux/libgomp/config.status'
    if not status.is_file():
        failures.append('the shared build has no configured libgomp (%s)' % status)
    else:
        text = status.read_text(errors='replace')
        built = re.search(r'^S\["config_path"\]="(.*)"$', text, re.M)
        built = built.group(1) if built else None
        options = re.search(r'^ac_cs_config="(.*)"$', text, re.M)
        forced = bool(options) and "'--enable-linux-futex'" in options.group(1)
        # --enable-linux-futex makes a failed futex link probe a configure error (config/futex.m4),
        # so a finished configure with it and a linux config_path is "futex yes".
        ok = built == CONFIG_PATH and forced
        print('%s built libgomp: config_path="%s", --enable-linux-futex %s'
              % ('PASS' if ok else 'FAIL', built, 'given' if forced else 'NOT given'))
        if not ok:
            failures.append('the built libgomp is not the forced-futex KNC configuration')
    for problem in failures:
        print('  ' + problem)
    return int(bool(failures))


def paths(binary):
    return re.findall(r'\((RPATH|RUNPATH)\)\s+Library r(?:un)?path: \[([^\]]+)\]', s7.readelf('-d', binary))


def build_mode():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    rc, text = s7.capture([sys.executable, PROGRAMS / 'build.py', OUT, '--cc', GCC,
                           '--fc', s7.GFORTRAN, '--libdir', LIBDIR], timeout=1800)
    if rc:
        print('\n'.join(text.splitlines()[-15:]))
        print('FAIL build.py exit %d: the OpenMP programs do not build and link' % rc)
        return 1
    failures = []
    rows = [row.split(' ', 2) for row in (OUT / 'runs.txt').read_text().splitlines()]
    staged = set()
    for name in sorted({lib for _, libs, _ in rows for lib in libs.split(',') if lib != '-'}):
        # A library the prefix lacks is a failure only if something staged needs it (below).
        if (LIBDIR / name).is_file():
            shutil.copyfile(LIBDIR / name, OUT / name)
            staged.add(name)
    binaries = sorted(OUT.glob('*.mic')) + [OUT / name for name in sorted(staged)]
    for binary in binaries:
        foreign = s7.needed(binary) - GLIBC - staged
        if foreign:
            failures.append('%s: DT_NEEDED not from the prefix: %s' % (binary.name, ' '.join(sorted(foreign))))
    for prog, _, _ in rows:
        dynamic = 'libgomp.so.1' in s7.needed(OUT / prog)
        if dynamic != prog.endswith('-shared.mic'):
            failures.append('%s: libgomp.so.1 %s DT_NEEDED' % (prog, 'in' if dynamic else 'not in'))
    print('%s %d programs (%d C and Fortran sources, shared and static libgomp): DT_NEEDED from '
          'the prefix and glibc only' % ('FAIL' if failures else 'PASS', len(rows),
                                         len({row[2].split()[1] for row in rows})), flush=True)

    problems = []
    library = OUT / 'libgomp.so.1'
    if 'libgomp.so.1' not in staged:
        problems.append('no libgomp.so.1 in ' + str(LIBDIR))
    else:
        if not re.search(r'\(SONAME\)\s+Library soname: \[libgomp\.so\.1\]', s7.readelf('-d', library)):
            problems.append('libgomp.so.1 lacks SONAME libgomp.so.1')
        defined = re.search(r"Version definition section.*?(?=\nVersion needs section|\Z)",
                            s7.readelf('-V', library), re.S)
        nodes = set(re.findall(r'Name: (\S+)', defined.group(0))) if defined else set()
        missing = [node for node in VERSION_NODES if node not in nodes]
        if missing:
            problems.append('libgomp.so.1 does not define version ' + ' '.join(missing))
        text = subprocess.check_output([str(TC / 'cross/bin/k1om-mpss-linux-objdump'), '-d', str(library)],
                                       text=True, errors='replace')
        delays = len(re.findall(r'^\s*[0-9a-f]+:\s.*\tdelay\s+%', text, re.M))
        if not delays:
            problems.append('libgomp.so.1 has no delay instruction: cpu_relax is not the KNC one')
        print('libgomp.so.1: %d version nodes, %d delay instructions' % (len(nodes), delays))
    target = s7.SHARED / 'tmp/s9-06-rpath.mic'
    rc, text = s7.capture([GCC, '-std=gnu11', '-O2', '-fopenmp', '-I', PROGRAMS, PROGRAMS / 'for.c',
                           '-Wl,-rpath,' + RPATH, '-o', target])
    if rc:
        problems.append('link with -Wl,-rpath,%s: %s' % (RPATH, text.strip()[-400:]))
    else:
        if paths(target) != [('RPATH', RPATH)] or 'libgomp.so.1' not in s7.needed(target):
            problems.append('prefix-layout link: loader path %r, DT_NEEDED %s; expected DT_RPATH %s '
                            'and libgomp.so.1' % (paths(target), ' '.join(sorted(s7.needed(target))), RPATH))
        target.unlink()
    print('%s libgomp.so.1: SONAME, version nodes %s, delay; DT_RPATH %s on a program'
          % ('FAIL' if problems else 'PASS', ' '.join(VERSION_NODES), RPATH), flush=True)
    failures.extend(problems)

    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    problems = ['lint %s: %s' % (binary.name, row) for binary in binaries
                for row in lint(binary, TC, os.environ.copy())]
    print('%s lint of %d binaries: no pause, cmpxchg16b or SSE' % ('FAIL' if problems else 'PASS', len(binaries)),
          flush=True)
    failures.extend(problems)

    (OUT / 'run.sh').write_bytes(RUN_SH.encode())
    names = [p.name for p in sorted(OUT.iterdir()) if p.name not in ('run.sh', 'files.txt')]
    (OUT / 'files.txt').write_bytes(''.join('.work/_shared/S9-06/%s\n' % name for name in names).encode())
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL build: %d problems' % len(failures))
        return 1
    print('PASS build: %d card jobs, %d staged files; native NOT RUN' % (len(rows), len(names)))
    print('Lead card runs: tools/card_run --timeout 1800 --file-list .work/_shared/S9-06/files.txt '
          '.work/_shared/S9-06/run.sh 60, and the same with 240 as the whole-card job; exit 0 means '
          'every RESULT and CHECK line is ok.')
    return 0


def guard_mode():
    """An "older libgomp.so.1": a stub with the SONAME and every libgomp symbol the program
    calls, but not the GOMP_6.0 one that libgomp-knc.ld requires."""
    work = s7.SHARED / 'tmp/s9-06-guard'
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    obj, stub, target = work / 'for.o', work / 'stub.c', work / 'old-runtime.mic'
    try:
        rc, text = s7.capture([GCC, '-std=gnu11', '-O2', '-fopenmp', '-I', PROGRAMS, '-c',
                               PROGRAMS / 'for.c', '-o', obj])
        if rc:
            print(text.strip()[-600:])
            print('FAIL guard: the program does not compile with -fopenmp')
            return 1
        undefined = subprocess.check_output([str(TC / 'cross/bin/k1om-mpss-linux-nm'), '-u', str(obj)], text=True)
        symbols = re.findall(r'\bU ((?:GOMP|omp)_\w+)', undefined)
        stub.write_text(''.join('void %s (void) {}\n' % symbol for symbol in symbols))
        rc, text = s7.capture([GCC, '-shared', '-fPIC', '-nostdlib', '-Wl,-soname,libgomp.so.1', stub,
                               '-o', work / 'libgomp.so'])
        if rc or not symbols:
            print(text.strip()[-600:])
            print('FAIL guard: could not build the old libgomp.so.1 stub (%d symbols)' % len(symbols))
            return 1
        rc, text = s7.capture([GCC, '-fopenmp', '-L', work, obj, '-o', target])
        ok = rc != 0 and GUARD in text and not target.exists()
        print('%s guard: link against an older libgomp.so.1 (%d-symbol stub): exit %d, expected "%s"'
              % ('PASS' if ok else 'FAIL', len(symbols), rc, GUARD))
        if not ok:
            print(text.strip()[-600:])
        return int(not ok)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('configure', 'build', 'guard'))
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__))],
                                         text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, args.mode])
    os.environ['TMPDIR'] = str(s7.SHARED / 'tmp')
    return {'configure': configure_mode, 'build': build_mode, 'guard': guard_mode}[args.mode]()


if __name__ == '__main__':
    sys.exit(main())
