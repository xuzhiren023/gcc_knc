#!/usr/bin/env python3
"""S9-12 libgomp reads the KNC card: arena cap, core count, clock (ADR-0012); invoke through tools/run.py.

    python tools/s9_12_checks.py host
        compiles tests/regress/s9_12/arena_host.c and topology_host.c with the Cygwin GCC against
        the lane's libgomp/config/linux/knc/card.h and runs each on its own scratch directory.
    python tools/s9_12_checks.py build
        the card batch .work/_shared/S9-12, built with the installed prefix
        (tools/s7_09_checks.py install):
        - the S9-06 programs, their libraries and run.sh, as tools/s9_06_checks.py build makes
          them (the acceptance case is run.sh 240 in a 6 GiB job, MALLOC_ARENA_MAX unset);
        - tests/regress/s9_10/malloc.c (measurement 7) with libgomp.so.1, and measure.sh;
        - the lint, and files.txt (the --file-list of both).
        The staged libgomp.so.1 must carry the arena cap display, so that it is this ticket's.

Nothing runs natively here: the lead runs the staged programs on the card.
"""
import argparse
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import s7_09_checks as s7
import s9_06_checks as s9

ROOT = Path(__file__).resolve().parents[1]
TC = s7.TC
TESTS = ROOT / 'tests/regress/s9_12'
KNC = s7.SHARED / s7.GCC_TREE / 'libgomp/config/linux/knc'
WORK = s7.SHARED / 'tmp/s9-12'
OUT = s7.SHARED / 'S9-12'
MALLOC = 'claude-s912-malloc.mic'
CAP_LINE = b'KNC malloc arena cap = '
MEASURE_SH = r'''#!/bin/sh
# Lead-only card program for S9-12 measurement 7 (tools/s9_12_checks.py build); files.txt is its
# --file-list. Whole-card --benchmark jobs per ADR-0010, one per job limit, the limit given as
# card_run's memoryMB (it applies it as RLIMIT_AS; ADR-0012 point 4: stand-ins for the 3120,
# 5110P and 7120):
#   memoryMB 6144:  card_run --benchmark --timeout 7200 --file-list .work/_shared/S9-12/files.txt .work/_shared/S9-12/measure.sh
#   memoryMB 8192 and 10240: the same.
# claude-s912-malloc.mic at 240 and 228 threads (a 3120's 57 cores x 4), each doing 100000
# malloc/free of 1 KiB and of the mixed-size pattern (malloc.c), with MALLOC_ARENA_MAX unset
# (libgomp derives the cap: ADR-0012), 240, 120, 64, 60, 30 and 8; 3 runs each. One RESULT line
# per run with wall_s, VmPeak, VmHWM, VmRSS and failed_mallocs; derived runs also print the cap
# libgomp chose (OMP_DISPLAY_ENV=verbose). A run that fails under the limit is data, reported
# as LIMIT with how far it got; only a timeout is UNEXPECTED (exit 1).
# BusyBox 1.19 sh: no timeout applet, so a watcher kills a program after LIMIT seconds.
cd -- "$(dirname -- "$0")" || exit 2
status=0
LIMIT=600
unset MALLOC_ARENA_MAX OMP_DISPLAY_ENV

policy() {
    echo "clocksource $(cat /sys/devices/system/clocksource/clocksource0/current_clocksource 2>/dev/null);" \
         "governor $(cat /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor 2>/dev/null || echo none);" \
         "ulimit -v $(ulimit -v); ulimit -s $(ulimit -s); cpus $(cat /sys/devices/system/cpu/online)"
}

# run ENV PROGRAM ARGS...: output in job.out, exit status in rc (timeout as rc=timeout). ENV is
# NAME=VALUE for the program, or -.
run() {
    env=$1
    shift
    rm -f job.timeout
    ( [ "$env" = - ] || export "$env"; exec "$@" ) > job.out 2>&1 &
    pid=$!
    ( sleep $LIMIT; touch job.timeout; kill -9 $pid ) > /dev/null 2>&1 &
    watcher=$!
    wait $pid
    rc=$?
    kill $watcher 2> /dev/null
    [ -e job.timeout ] && rc=timeout
}

echo "S9-12 malloc start: $(policy)"
limit="$(ulimit -v)"
for threads in 240 228; do
    for pattern in 1k mixed; do
        for arenas in unset 240 120 64 60 30 8; do
            env=OMP_DISPLAY_ENV=verbose
            [ $arenas = unset ] || env=MALLOC_ARENA_MAX=$arenas
            for rep in 1 2 3; do
                run $env ./claude-s912-malloc.mic $threads 100000 $pattern
                line=$(grep '^S9-10 malloc ' job.out)
                cap=$(sed -n "s/^  \[host\] KNC malloc arena cap = //p" job.out)
                tag="malloc/limit=${limit}kB/threads=$threads/$pattern/arenas=$arenas/$rep"
                [ -n "$cap" ] && line="$line cap=$cap"
                if [ "$rc" = 0 ] && [ -n "$line" ]; then
                    echo "RESULT $tag ok: $line"
                elif [ "$rc" != timeout ]; then
                    echo "RESULT $tag LIMIT: exit=$rc ${line:-no result line}"
                    grep -v '^  \[host\]\|^OPENMP' job.out | head -n 5 | sed 's/^/  | /'
                else
                    echo "RESULT $tag UNEXPECTED: exit=$rc"
                    head -n 20 job.out | sed 's/^/  | /'
                    status=1
                fi
            done
        done
    done
done
echo "S9-12 malloc end: $(policy)"
exit $status
'''


def host_mode(args):
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    failed = 0
    for name in ('arena_host', 'topology_host'):
        test = WORK / (name + '.exe')
        rc, text = s7.capture(['gcc', '-std=gnu11', '-O2', '-Wall', '-I%s' % KNC, TESTS / (name + '.c'),
                               '-o', test])
        if rc:
            print('\n'.join(line for line in text.splitlines() if 'error' in line)[-3000:])
            print('FAIL %s: does not build against %s' % (name, KNC))
            failed += 1
            continue
        scratch = WORK / (name + '.d')
        scratch.mkdir()
        result = subprocess.run([str(test), str(scratch)], capture_output=True, text=True, timeout=120)
        out = result.stdout.strip()
        print('\n'.join(line for line in out.splitlines() if not line.startswith('ok  ')) or
              'FAIL %s: no output, exit %s' % (name, result.returncode), flush=True)
        failed += result.returncode != 0
    print('%s host: %d of 2 tests failed' % ('FAIL' if failed else 'PASS', failed))
    return int(failed != 0)


def build_mode(args):
    # As tools/s9_10_checks.py: main's tests/acceptance/s9_omp/locks.c has a literal newline in a
    # printf string; built from a temporary copy with only that line fixed (lead, 2026-11-10 08:26).
    sources = WORK / 's9_omp'
    shutil.rmtree(sources, ignore_errors=True)
    shutil.copytree(s9.PROGRAMS, sources)
    locks = (sources / 'locks.c').read_bytes()
    fixed = locks.replace(b'printf ("omp_get_wtick %g\n", ', b'printf ("omp_get_wtick %g\\n", ')
    (sources / 'locks.c').write_bytes(fixed)
    s9.PROGRAMS = sources
    s9.OUT = OUT
    if s9.build_mode():
        print('FAIL build: the S9-06 programs (above)')
        return 1
    failures = []
    library = OUT / 'libgomp.so.1'
    if CAP_LINE not in library.read_bytes():
        failures.append('%s lacks the arena cap display: not this ticket\'s libgomp' % library)
    rc, out = s7.capture([s9.GCC, '-std=gnu11', '-O2', '-Wall', '-fopenmp', ROOT / 'tests/regress/s9_10/malloc.c',
                          '-Wl,-rpath,$ORIGIN', '-o', OUT / MALLOC])
    if rc or out.strip():
        failures.append('%s: %s' % (MALLOC, out.strip()[-600:]))
    elif 'libgomp.so.1' not in s7.needed(OUT / MALLOC):
        failures.append('%s does not need libgomp.so.1' % MALLOC)
    else:
        lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
        failures += ['lint %s: %s' % (MALLOC, row) for row in lint(OUT / MALLOC, TC, os.environ.copy())]
    run_sh = (OUT / 'run.sh').read_text().replace('.work/_shared/S9-06/', '.work/_shared/S9-12/')
    (OUT / 'run.sh').write_bytes(run_sh.encode())
    (OUT / 'measure.sh').write_bytes(MEASURE_SH.encode())
    names = sorted(p.name for p in OUT.iterdir() if p.name != 'files.txt')
    (OUT / 'files.txt').write_bytes(''.join('.work/_shared/S9-12/%s\n' % name for name in names).encode())
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL build: %d problems' % len(failures))
        return 1
    print('PASS build: %d files staged in %s (the S9-06 batch, %s); libgomp.so.1 has the arena cap display; '
          'lint clean; native NOT RUN' % (len(names), OUT, MALLOC))
    print('Lead card runs: run.sh 240 with memoryMB 6144 and MALLOC_ARENA_MAX unset (the tasks acceptance); '
          'measure.sh as whole-card --benchmark jobs at memoryMB 6144, 8192 and 10240.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('host', 'build'))
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__))],
                                         text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]])
    os.environ['TMPDIR'] = str(s7.SHARED / 'tmp')
    return {'host': host_mode, 'build': build_mode}[args.mode](args)


if __name__ == '__main__':
    sys.exit(main())
