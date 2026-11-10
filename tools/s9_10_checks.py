#!/usr/bin/env python3
"""S9-10 libgomp KNC padding, static run-sched-var default and malloc hint; invoke through tools/run.py.

    python tools/s9_10_checks.py host
        compiles the lane's libgomp/env.c with the Cygwin GCC, -D__k1om__, the k1om config_path
        and the build's config.h, together with tests/regress/s9_10/env_host.c, which fails to
        compile when libgomp.h's or knc/bar.h's KNC layout checks fail; runs its two cases (see
        that file) with their environments.
    python tools/s9_10_checks.py build
        the card batch .work/_shared/S9-10, built with the installed prefix
        (tools/s7_09_checks.py install):
        - the eight S9-06 programs, their libraries and run.sh, as tools/s9_06_checks.py build
          makes them (the S9-06 check at 60x4 is run.sh 240);
        - tests/regress/s9_10/reduction.c (measurement 6) and malloc.c (measurement 7) with
          libgomp.so.1, and measure.sh, their card program;
        - the lint, and files.txt (the --file-list of both programs).
        The staged libgomp.so.1 must carry the KNC display hint, so that it is this ticket's.

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
TESTS = ROOT / 'tests/regress/s9_10'
LIBGOMP = s7.SHARED / s7.GCC_TREE / 'libgomp'
OBJDIR = s7.BUILD / 'k1om-mpss-linux/libgomp'
WORK = s7.SHARED / 'tmp/s9-10'
# The variables the cases set; the default case runs with none of them.
KNOBS = ('OMP_SCHEDULE', 'MALLOC_ARENA_MAX', 'OMP_STACKSIZE', 'GOMP_STACKSIZE', 'OMP_DISPLAY_ENV')
CASES = (('default', {}),
         ('set', {'OMP_SCHEDULE': 'dynamic,4', 'MALLOC_ARENA_MAX': '60', 'OMP_STACKSIZE': '2M'}))
OUT = s7.SHARED / 'S9-10'
REDUCTION = 'claude-s9red-reduction.mic'
MALLOC = 'claude-s9red-malloc.mic'
HINT = b'  [host] KNC hint: '
MEASURE_SH = r'''#!/bin/sh
# Lead-only card program for S9-10 (tools/s9_10_checks.py build); files.txt is its --file-list.
# Whole-card jobs, timed per ADR-0010, never in one window with a correctness run:
#   card_run --benchmark --timeout 3600 --file-list .work/_shared/S9-10/files.txt .work/_shared/S9-10/measure.sh reduction
#   card_run --benchmark --timeout 3600 --file-list .work/_shared/S9-10/files.txt .work/_shared/S9-10/measure.sh malloc
# reduction: measurement 6 of docs/research/knc-libgomp.md section 5. claude-s9red-reduction.mic
#   at 60 and 240 threads: one reduction clause (atomic path), two clauses (GOMP_atomic_start
#   lock path) and padded partials summed by the master; 10000 regions a batch; the order of
#   the three is drawn per round, 3 rounds. RATIO lines are per-round median_us(mode)/median_us(padded),
#   SUMMARY their median over the rounds.
# malloc: measurement 7 of section 6 as ADR-0012 point 4 sets it. claude-s9red-malloc.mic at
#   240 threads, each doing 100000 malloc/free of 1 KiB, with MALLOC_ARENA_MAX unset, 240, 120,
#   64, 60, 30 and 8, under ulimit -v 6, 8 and 10 GiB (stand-ins for the 3120, 5110P and 7120),
#   3 runs each; one line per run with wall_s, VmPeak, VmHWM and VmRSS. A limit above the job's
#   own is SKIP (the job needs 10 GiB of card_run memory for all three). A run that fails under
#   a limit (S9-06 tasks at 240: Out of memory) is data, reported as LIMIT with how far it got.
# Exit 0 when no RESULT line says UNEXPECTED (a reduction that fails, or a malloc run that times out).
# BusyBox 1.19 sh: no timeout applet, so a watcher kills a program after LIMIT seconds.
cd -- "$(dirname -- "$0")" || exit 2
status=0
unset MALLOC_ARENA_MAX

policy() {
    echo "clocksource $(cat /sys/devices/system/clocksource/clocksource0/current_clocksource 2>/dev/null);" \
         "governor $(cat /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor 2>/dev/null || echo none);" \
         "ulimit -v $(ulimit -v)"
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

reduction() {
    LIMIT=900
    ROUNDS=3
    SEED=$(date +%s)
    echo "S9-10 reduction start: $(policy); seed $SEED"
    rm -f m.txt
    round=0
    while [ $round -lt $ROUNDS ]; do
        order=$(awk -v s=$((SEED + round)) 'BEGIN { srand(s); n = split("atomic lock padded", m, " ");
                for (i = n; i > 1; i--) { j = int(rand() * i) + 1; t = m[i]; m[i] = m[j]; m[j] = t }
                print m[1], m[2], m[3] }')
        for threads in 60 240; do
            for mode in $order; do
                run - ./claude-s9red-reduction.mic $mode $threads
                grep '^SAMPLE' job.out | sed "s|^|round=$round |"
                line=$(grep "^S9-10 reduction $mode PASS" job.out)
                median=$(echo "$line" | sed -n 's/.* median_us=\([0-9.]*\).*/\1/p')
                if [ "$rc" = 0 ] && [ -n "$median" ]; then
                    echo "RESULT round=$round reduction/$threads/$mode ok: $line"
                    echo "$round $threads $mode $median" >> m.txt
                else
                    echo "RESULT round=$round reduction/$threads/$mode UNEXPECTED: exit=$rc"
                    head -n 20 job.out | sed 's/^/  | /'
                    status=1
                fi
            done
        done
        round=$((round + 1))
    done
    if [ -s m.txt ]; then
        awk '{ m[$1, $2, $3] = $4; r[$1] = 1; t[$2] = 1 }
             END { split("atomic lock", modes, " ")
                   for (round in r) for (th in t) for (k = 1; k <= 2; k++) {
                       key = th "/" modes[k]
                       if ((round, th, modes[k]) in m && m[round, th, "padded"] > 0) {
                           v = m[round, th, modes[k]] / m[round, th, "padded"]
                           printf "RATIO round=%s threads=%s %s/padded=%.4f\n", round, th, modes[k], v
                           n[key]++; x[key, n[key]] = v; keys[key] = 1 } }
                   for (key in keys) { for (i = 1; i <= n[key]; i++) for (j = i + 1; j <= n[key]; j++)
                                           if (x[key, j] < x[key, i]) { s = x[key, i]; x[key, i] = x[key, j]; x[key, j] = s }
                                       printf "SUMMARY threads/mode=%s median_over_padded=%.4f min=%.4f max=%.4f rounds=%d\n",
                                              key, x[key, int((n[key] + 1) / 2)], x[key, 1], x[key, n[key]], n[key] } }' m.txt
    fi
    echo "S9-10 reduction end: $(policy)"
}

malloc() {
    LIMIT=600
    echo "S9-10 malloc start: $(policy)"
    have=$(ulimit -v)
    for gib in 6 8 10; do
        kib=$((gib * 1024 * 1024))
        if [ "$have" != unlimited ] && [ "$have" -lt $kib ]; then
            echo "RESULT malloc/limit=${gib}G SKIP: the job's ulimit -v is $have kB; give the job ${gib} GiB"
            continue
        fi
        for arenas in unset 240 120 64 60 30 8; do
            env=-
            [ $arenas = unset ] || env=MALLOC_ARENA_MAX=$arenas
            for rep in 1 2 3; do
                run $env sh -c "ulimit -v $kib && exec ./claude-s9red-malloc.mic 240"
                line=$(grep '^S9-10 malloc ' job.out)
                tag="malloc/limit=${gib}G/arenas=$arenas/$rep"
                if [ "$rc" = 0 ] && [ -n "$line" ]; then
                    echo "RESULT $tag ok: $line"
                elif [ "$rc" != timeout ]; then
                    echo "RESULT $tag LIMIT: exit=$rc ${line:-no result line}"
                    head -n 5 job.out | sed 's/^/  | /'
                else
                    echo "RESULT $tag UNEXPECTED: exit=$rc"
                    head -n 20 job.out | sed 's/^/  | /'
                    status=1
                fi
            done
        done
    done
    echo "S9-10 malloc end: $(policy)"
}

case $1 in
    reduction) reduction ;;
    malloc) malloc ;;
    *) echo "usage: measure.sh reduction|malloc"; exit 2 ;;
esac
exit $status
'''


def host_mode(args):
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    test = WORK / 'env_host.exe'
    includes = [LIBGOMP / 'config' / part for part in s9.CONFIG_PATH.split()]
    rc, text = s7.capture(['gcc', '-std=gnu11', '-O2', '-Wall', '-Wno-attributes', '-D__k1om__', '-DHAVE_CONFIG_H',
                           '-I%s' % OBJDIR, *('-I%s' % d for d in includes), '-I%s' % LIBGOMP,
                           '-I%s' % (LIBGOMP.parent / 'include'), LIBGOMP / 'env.c', TESTS / 'env_host.c',
                           '-o', test])
    if rc:
        print('\n'.join(line for line in text.splitlines() if 'error' in line)[-3000:])
        print('FAIL host: env.c and env_host.c do not build against %s (layout checks above)' % LIBGOMP)
        return 1
    failed = 0
    for case, settings in CASES:
        env = {k: v for k, v in os.environ.items() if k not in KNOBS}
        env.update(settings)
        result = subprocess.run([str(test), case], env=env, capture_output=True, text=True, timeout=60)
        print(result.stdout.strip() or 'FAIL %s: no output, exit %s' % (case, result.returncode), flush=True)
        failed += result.returncode != 0
    print('%s host: %d of %d cases failed' % ('FAIL' if failed else 'PASS', failed, len(CASES)))
    return int(failed != 0)


def build_mode(args):
    # main's tests/acceptance/s9_omp/locks.c (58a2473) has a literal newline in a printf string; the
    # lead allowed (2026-11-10 08:26) building from a temporary copy with only that line fixed.
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
    if HINT not in library.read_bytes():
        failures.append('%s lacks the KNC display hint: not this ticket\'s libgomp' % library)
    for source, target in (('reduction.c', REDUCTION), ('malloc.c', MALLOC)):
        rc, out = s7.capture([s9.GCC, '-std=gnu11', '-O2', '-Wall', '-fopenmp', TESTS / source,
                              '-Wl,-rpath,$ORIGIN', '-o', OUT / target])
        if rc or out.strip():
            failures.append('%s: %s' % (target, out.strip()[-600:]))
        elif 'libgomp.so.1' not in s7.needed(OUT / target):
            failures.append('%s does not need libgomp.so.1' % target)
    if not failures:
        # The lock path is the reason for the two-clause mode.
        undefined = subprocess.check_output([str(TC / 'cross/bin/k1om-mpss-linux-nm'), '-u', str(OUT / REDUCTION)],
                                            text=True)
        if 'GOMP_atomic_start' not in undefined:
            failures.append('%s does not call GOMP_atomic_start: no lock-path reduction' % REDUCTION)
        lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
        failures += ['lint %s: %s' % (name, row) for name in (REDUCTION, MALLOC)
                     for row in lint(OUT / name, TC, os.environ.copy())]
    run_sh = (OUT / 'run.sh').read_text().replace('.work/_shared/S9-06/', '.work/_shared/S9-10/')
    if fixed != locks:
        run_sh = run_sh.replace('\n', '\n# S9-10: locks built from a copy of tests/acceptance/s9_omp/locks.c with only line 43 '
                                'fixed to "omp_get_wtick %g\\n" (lead 2026-11-10 08:26).\n', 1)
    (OUT / 'run.sh').write_bytes(run_sh.encode())
    (OUT / 'measure.sh').write_bytes(MEASURE_SH.encode())
    names = sorted(p.name for p in OUT.iterdir() if p.name != 'files.txt')
    (OUT / 'files.txt').write_bytes(''.join('.work/_shared/S9-10/%s\n' % name for name in names).encode())
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL build: %d problems' % len(failures))
        return 1
    print('PASS build: %d files staged in %s (the S9-06 batch, %s, %s); libgomp.so.1 has the KNC hint; '
          'lint clean; native NOT RUN%s' % (len(names), OUT, REDUCTION, MALLOC,
                                            '; locks.c from a copy with the printf newline fixed' if fixed != locks else ''))
    print('Lead card runs: tools/card_run --benchmark --timeout 1800 --file-list .work/_shared/S9-10/files.txt '
          '.work/_shared/S9-10/run.sh 240 (the S9-06 check at 60x4); measure.sh reduction and measure.sh malloc '
          'as whole-card --benchmark jobs.')
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
