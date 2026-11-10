#!/usr/bin/env python3
"""S9-09 libgomp KNC team barrier; invoke through tools/run.py.

    python tools/s9_09_checks.py host [--barriers N]
        compiles tests/regress/s9_09/barrier_stress.c with the Cygwin GCC against the lane's
        libgomp/config/linux/knc/bar.h, bar.c and simple-bar.h and runs its variants: 240 threads,
        100000 barriers each, 60 groups (the cancel variant 36 cores, so that the last group is
        smaller than the others).
    python tools/s9_09_checks.py build
        the card batch .work/_shared/S9-09, built with the installed prefix
        (tools/s7_09_checks.py install):
        - SUITE below, from libgomp's testsuite, each as claude-s9t-<name>.mic with the options and
          environment of its dg- lines (tests.txt);
        - tests/regress/s9_09/tasks_cancel.c (10000 tasks; cancel parallel) with libgomp.so.1;
        - tests/regress/s9_09/barrier_measure.c (measurements 2, 4 and 5) twice, with libgomp
          linked in: the prefix's libgomp.a, and one built here from the same sources, config.h
          and flags plus -DGOMP_KNC_FLAT_BARRIER, the one-level Linux barrier;
        - the lint, run.sh (the card program) and files.txt (its --file-list).

Nothing runs natively here: the lead runs run.sh on the card.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys

import s7_09_checks as s7
import s9_06_checks as s9

ROOT = Path(__file__).resolve().parents[1]
TC = s7.TC
TESTS = ROOT / 'tests/regress/s9_09'
LIBGOMP = s7.SHARED / s7.GCC_TREE / 'libgomp'
OBJDIR = s7.BUILD / 'k1om-mpss-linux/libgomp'
WORK = s7.SHARED / 'tmp/s9-09'
OUT = s7.SHARED / 'S9-09'
# (mode, gomp_knc_ncores)
VARIANTS = (('plain', 60), ('tasks-park', 60), ('tasks-spin', 60), ('cancel', 36), ('order', 60))
# libgomp/testsuite: the barrier, cancel, single, ordered and task tests of libgomp.c, the ones there
# that use taskwait, and the taskwait tests of libgomp.c-c++-common.
SUITE = ['libgomp.c/%s.c' % name for name in (
    'barrier-1 cancel-for-1 cancel-for-2 cancel-parallel-1 cancel-parallel-2 cancel-parallel-3 '
    'cancel-sections-1 omp-single-1 omp-single-2 omp-single-3 ordered-1 ordered-2 ordered-3 ordered-5 '
    'single-1 single-2 task-1 task-2 task-3 task-4 task-5 task-6 task-7 task-8 task-reduction-1 '
    'task-reduction-2 task-reduction-3 task-reduction-4 depend-1 depend-5 pr61200').split()] + [
    'libgomp.c-c++-common/%s.c' % name for name in
    ('taskwait-depend-1', 'taskwait-depend-nowait-1', 'taskwait-depend-nowait-2')]
MEASURE = 'claude-s9bar-measure-%s.mic'
TASKS = 'claude-s9bar-tasks.mic'
RUN_SH = r'''#!/bin/sh
# Lead-only card program for S9-09 (tools/s9_09_checks.py build); files.txt is its --file-list.
# Two whole-card jobs (60x4), never in one window (ADR-0010 point 5):
#   card_run --benchmark --timeout 3600 --file-list .work/_shared/S9-09/files.txt .work/_shared/S9-09/run.sh check
#   card_run --benchmark --timeout 3600 --file-list .work/_shared/S9-09/files.txt .work/_shared/S9-09/run.sh measure
# check: each libgomp testsuite program of tests.txt with its environment and the runtime's default
#   thread count, then 10000 tasks and `cancel parallel' at 240 threads (claude-s9bar-tasks.mic).
#   Exit 0 when every RESULT line says ok.
# measure: measurements 2, 4 and 5 of docs/research/knc-libgomp.md section 4, timed per ADR-0010;
#   run it in at least three launches. claude-s9bar-measure-hier.mic has the KNC barrier in per-core
#   groups, -flat.mic the one-level Linux barrier; one process per barrier and setting, the two
#   barriers in an order drawn per round. Every sample is printed. RATIO lines are per-round
#   median_us(hier)/median_us(flat), SUMMARY their median: barrier is us per barrier at 60x1, 60x2
#   and 60x4; fanout the last arrival to the last thread leaving, waiters spinning (active) and
#   asleep (passive); imbalance us per round when one thread does twice the work.
# BusyBox 1.19 sh: no timeout applet, so a watcher kills a program after LIMIT seconds.
cd -- "$(dirname -- "$0")" || exit 2
status=0

policy() {
    echo "clocksource $(cat /sys/devices/system/clocksource/clocksource0/current_clocksource 2>/dev/null);" \
         "governor $(cat /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor 2>/dev/null || echo none)"
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

check() {
    LIMIT=300
    while read -r prog env <&3; do
        run "$env" ./"$prog"
        if [ "$rc" = 0 ]; then
            echo "RESULT suite $prog $env ok"
        else
            echo "RESULT suite $prog $env UNEXPECTED: exit=$rc"
            head -n 20 job.out | sed 's/^/  | /'
            status=1
        fi
    done 3< tests.txt
    for job in "tasks -" "cancel OMP_CANCELLATION=true"; do
        set -- $job
        run "$2" ./claude-s9bar-tasks.mic "$1" 240
        if [ "$rc" = 0 ] && grep -q "^S9-09 $1 PASS" job.out; then
            echo "RESULT $1 ok: $(grep "^S9-09 $1 PASS" job.out)"
        else
            echo "RESULT $1 UNEXPECTED: exit=$rc"
            head -n 20 job.out | sed 's/^/  | /'
            status=1
        fi
    done
}

measure() {
    LIMIT=900
    ROUNDS=5
    SEED=$(date +%s)
    echo "S9-09 measure start: $(policy); seed $SEED"
    rm -f m.txt
    round=0
    while [ $round -lt $ROUNDS ]; do
        order=$(awk -v s=$((SEED + round)) 'BEGIN { srand(s); print rand() < 0.5 ? "hier flat" : "flat hier" }')
        for job in "barrier 60 -" "barrier 120 -" "barrier 240 -" "fanout 240 OMP_WAIT_POLICY=active" \
                   "fanout 240 OMP_WAIT_POLICY=passive" "imbalance 240 -"; do
            set -- $job
            for lib in $order; do
                run "$3" ./claude-s9bar-measure-$lib.mic "$1" "$2" $lib
                grep '^SAMPLE' job.out | sed "s|^|round=$round $1/$2/$3 |"
                line=$(grep "^S9-09 $1 $lib PASS" job.out)
                median=$(echo "$line" | sed -n 's/.* median_us=\([0-9.]*\).*/\1/p')
                if [ "$rc" = 0 ] && [ -n "$median" ]; then
                    echo "RESULT round=$round $1/$2/$3 ok: $line"
                    echo "$round $1/$2/$3 $lib $median" >> m.txt
                else
                    echo "RESULT round=$round $1/$2/$3 $lib UNEXPECTED: exit=$rc"
                    head -n 20 job.out | sed 's/^/  | /'
                    status=1
                fi
            done
        done
        round=$((round + 1))
    done
    if [ -s m.txt ]; then
        awk '{ m[$1, $2, $3] = $4; r[$1] = 1; c[$2] = 1 }
             END { for (round in r) for (k in c) if ((round, k, "hier") in m && m[round, k, "flat"] > 0) {
                       v = m[round, k, "hier"] / m[round, k, "flat"]
                       printf "RATIO round=%s %s hier/flat=%.4f\n", round, k, v
                       n[k]++; x[k, n[k]] = v }
                   for (k in c) { for (i = 1; i <= n[k]; i++) for (j = i + 1; j <= n[k]; j++)
                                      if (x[k, j] < x[k, i]) { t = x[k, i]; x[k, i] = x[k, j]; x[k, j] = t }
                                  if (n[k]) printf "SUMMARY %s median_hier/flat=%.4f min=%.4f max=%.4f rounds=%d\n",
                                                   k, x[k, int((n[k] + 1) / 2)], x[k, 1], x[k, n[k]], n[k] } }' m.txt
    fi
    echo "S9-09 measure end: $(policy)"
}

case $1 in
    check) check ;;
    measure) measure ;;
    *) echo "usage: run.sh check|measure"; exit 2 ;;
esac
exit $status
'''


def host_mode(args):
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    test = WORK / 'barrier_stress.exe'
    includes = [LIBGOMP / 'config' / part for part in s9.CONFIG_PATH.split()]
    rc, text = s7.capture(['gcc', '-std=gnu11', '-O2', '-Wall', '-pthread', *('-I%s' % d for d in includes),
                           TESTS / 'barrier_stress.c', '-o', test])
    if rc or text.strip():
        print('\n'.join(text.splitlines()[-15:]))
    if rc:
        print('FAIL host: barrier_stress.c does not build against %s' % LIBGOMP)
        return 1
    failed = 0
    for mode, ncores in VARIANTS:
        rc, text = s7.capture([test, mode, args.barriers, ncores], timeout=7200)
        print(text.strip() or 'FAIL %s: no output, exit %s' % (mode, rc), flush=True)
        failed += rc != 0
    print('%s host: %d of %d variants failed' % ('FAIL' if failed else 'PASS', failed, len(VARIANTS)))
    return int(failed != 0)


def flat_library(failures):
    """libgomp.a with the one-level barrier: every C object of the build's libgomp, compiled as its
    Makefile does (the non-PIC half of LTCOMPILE) plus -DGOMP_KNC_FLAT_BARRIER."""
    make = (OBJDIR / 'Makefile').read_text()

    def var(name):
        return re.search(r'^%s = ((?:.*\\\n)*.*)$' % name, make, re.M).group(1).replace('\\\n', ' ').split()
    search = [LIBGOMP / 'config' / part for part in var('config_path')] + [LIBGOMP, LIBGOMP.parent / 'include']
    flags = ['-DHAVE_CONFIG_H', '-I', OBJDIR, '-I', LIBGOMP, *('-I%s' % d for d in search),
             *(flag.replace('-Wc,', '') for flag in var('XCFLAGS')), *var('CFLAGS'), '-DGOMP_KNC_FLAT_BARRIER']
    flat = WORK / 'flat'
    shutil.rmtree(flat, ignore_errors=True)
    flat.mkdir(parents=True)
    jobs = []
    for name in var('am_libgomp_la_OBJECTS'):
        source = next((d / (name[:-3] + '.c') for d in search if (d / (name[:-3] + '.c')).is_file()), None)
        if name.endswith('.lo') and source:
            jobs.append([s9.GCC, *flags, '-c', source, '-o', flat / (name[:-3] + '.o')])
    with ThreadPoolExecutor(8) as pool:
        for job, (rc, text) in zip(jobs, pool.map(s7.capture, jobs)):
            if rc:
                failures.append('flat libgomp: %s: %s' % (job[-3].name, text.strip()[-600:]))
    archive = flat / 'libgomp.a'
    rc, text = s7.capture([TC / 'cross/bin/k1om-mpss-linux-ar', 'rcs', archive, *(job[-1] for job in jobs)])
    if rc:
        failures.append('flat libgomp: ar: ' + text.strip()[-300:])
    print('flat libgomp.a: %d objects with %s' % (len(jobs), ' '.join(map(str, flags[5 + len(search):]))), flush=True)
    return archive


def build_mode(args):
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    failures, rows = [], []
    for path in SUITE:
        source = LIBGOMP / 'testsuite' / path
        text = source.read_text(errors='replace')
        # Options and environment that are not for one target only (ordered-5.c's are for SSE and AVX).
        options = [flag for group in re.findall(r'\{ dg-additional-options "([^"]*)" \}', text) for flag in group.split()]
        env = re.search(r'\{ dg-set-target-env-var (\w+) "([^"]*)" \}', text)
        program = 'claude-s9t-%s.mic' % source.stem
        rc, out = s7.capture([s9.GCC, '-O2', '-fopenmp', *options, '-I', LIBGOMP, '-I', OBJDIR, source,
                              '-Wl,-rpath,$ORIGIN', '-o', OUT / program])
        if rc:
            failures.append('%s: %s' % (path, out.strip()[-600:]))
        rows.append('%s %s' % (program, '%s=%s' % env.groups() if env else '-'))
    (OUT / 'tests.txt').write_bytes(''.join(row + '\n' for row in rows).encode())
    print('%d libgomp testsuite programs: %s' % (len(rows), ' '.join(SUITE)), flush=True)

    archives = {'hier': s9.LIBDIR / 'libgomp.a', 'flat': flat_library(failures)}
    links = [([TESTS / 'tasks_cancel.c', '-fopenmp'], OUT / TASKS)]
    links += [([TESTS / 'barrier_measure.c', '-fopenmp', '-c'], WORK / 'barrier_measure.o')]
    links += [([WORK / 'barrier_measure.o', archive, '-pthread', '-ldl'], OUT / (MEASURE % kind))
              for kind, archive in archives.items()]
    for inputs, target in links:
        rc, out = s7.capture([s9.GCC, '-std=gnu11', '-O2', '-Wall', *inputs, '-Wl,-rpath,$ORIGIN', '-o', target])
        if rc or out.strip():
            failures.append('%s: %s' % (target.name, out.strip()[-600:]))
    if failures:
        for problem in failures:
            print('  ' + problem)
        print('FAIL build: %d problems' % len(failures))
        return 1

    # The dock's functions exist only with the grouped barrier (knc/simple-bar.h); nothing else tells
    # the two measurement programs apart.
    nm = str(TC / 'cross/bin/k1om-mpss-linux-nm')
    for kind in archives:
        grouped = ' gomp_simple_barrier_wait\n' in subprocess.check_output([nm, str(OUT / (MEASURE % kind))], text=True)
        deps = s7.needed(OUT / (MEASURE % kind))
        if grouped != (kind == 'hier') or 'libgomp.so.1' in deps:
            failures.append('%s: grouped barrier %s, DT_NEEDED %s' % (MEASURE % kind, grouped, ' '.join(sorted(deps))))
    binaries, pending = [], sorted(OUT.glob('*.mic'))
    while pending:
        binary = pending.pop()
        binaries.append(binary)
        for name in sorted(s7.needed(binary) - s9.GLIBC):
            if (OUT / name).exists():
                continue
            if not (s9.LIBDIR / name).is_file():
                failures.append('%s: DT_NEEDED %s is not in the prefix' % (binary.name, name))
                continue
            shutil.copyfile(s9.LIBDIR / name, OUT / name)
            pending.append(OUT / name)
    if 'libgomp.so.1' not in s7.needed(OUT / TASKS):
        failures.append('%s does not need libgomp.so.1' % TASKS)
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    failures += ['lint %s: %s' % (binary.name, row) for binary in binaries
                 for row in lint(binary, TC, os.environ.copy())]
    names = sorted(p.name for p in OUT.iterdir())
    (OUT / 'run.sh').write_bytes(RUN_SH.encode())
    (OUT / 'files.txt').write_bytes(''.join('.work/_shared/S9-09/%s\n' % name for name in names).encode())
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL build: %d problems' % len(failures))
        return 1
    print('PASS build: %d files staged in %s (%d suite programs, %s, %s and %s with libgomp linked in); '
          'lint clean; native NOT RUN' % (len(names), OUT, len(rows), TASKS, MEASURE % 'hier', MEASURE % 'flat'))
    print('Lead card runs, whole card: tools/card_run --benchmark --timeout 3600 --file-list '
          '.work/_shared/S9-09/files.txt .work/_shared/S9-09/run.sh check, and the same with measure in '
          'three launches or more.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('host', 'build'))
    parser.add_argument('--barriers', type=int, default=100000)
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
