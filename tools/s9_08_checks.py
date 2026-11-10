#!/usr/bin/env python3
"""S9-08 libgomp spin-wait with DELAY; invoke through tools/run.py.

    python tools/s9_08_checks.py host
        compiles tests/regress/s9_08/delay.c with the Cygwin GCC against the lane's libgomp
        sources in the k1om config_path order and runs it: GOMP_KNC_DELAY parsing, the KNC default
        spin count and the omp_display_env line.
    python tools/s9_08_checks.py scan
        T1 scan of the installed libgomp.so.1 (tools/s7_09_checks.py install): in each function
        that inlines do_spin (config/linux/wait.h) named below, a DELAY whose register is loaded
        from gomp_knc_delay sits inside a loop (a later backward branch to an address at or before
        it); the library carries the GOMP_KNC_DELAY name; the lint finds no pause.
    python tools/s9_08_checks.py build
        builds measurements 1 and 3 of docs/research/knc-libgomp.md section 4
        (tests/regress/s9_08/spin_core.c and forkjoin.c) with the installed prefix into the card
        batch .work/_shared/S9-08, with the prefix libraries they need, the lint, run.sh (the card
        program) and files.txt (its --file-list).

Nothing runs natively here: the lead runs run.sh on the card.
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
import s9_06_checks as s9

ROOT = Path(__file__).resolve().parents[1]
TC = s7.TC
TESTS = ROOT / 'tests/regress/s9_08'
LIBGOMP = s7.SHARED / s7.GCC_TREE / 'libgomp'
WORK = s7.SHARED / 'tmp/s9-08'
OUT = s7.SHARED / 'S9-08'
SPIN = 'claude-s9spin.mic'
FORKJOIN = 'claude-s9forkjoin.mic'
# Functions whose wait loop is do_spin inlined (bar.c, mutex.c of config/linux).
SPINNERS = ('gomp_barrier_wait_end', 'gomp_team_barrier_wait_end', 'gomp_mutex_lock_slow')
RUN_SH = r'''#!/bin/sh
# Lead-only card program for S9-08 (tools/s9_08_checks.py build); files.txt is its --file-list:
#   card_run --benchmark --timeout 3600 --file-list .work/_shared/S9-08/files.txt .work/_shared/S9-08/run.sh
# Measurements 1 and 3 of docs/research/knc-libgomp.md section 4, timed per ADR-0010; run it in at
# least three launches. Every sample is printed. Exit 0 when every program ran and passed.
# 1. claude-s9spin.mic: one core, the worker alone and with 1-3 spinning siblings, no hint and
#    DELAY 32/128/512; RATIO lines are per-round T(config)/T(alone), SUMMARY their median.
# 2. claude-s9forkjoin.mic: empty parallel regions at 240 threads (60x4, the KNC default spread
#    binding), one process per setting, the five settings in an order drawn per round; FJRATIO
#    lines are per-round us/region over the default setting's, FJSUMMARY their median. Each process
#    shows its GOMP_KNC_DELAY and GOMP_SPINCOUNT from OMP_DISPLAY_ENV=verbose.
# BusyBox 1.19 sh: no timeout applet, so a watcher kills a program after LIMIT seconds.
cd -- "$(dirname -- "$0")" || exit 2
LIMIT=900
ROUNDS=5
SEED=$(date +%s)
status=0

policy() {
    echo "clocksource $(cat /sys/devices/system/clocksource/clocksource0/current_clocksource 2>/dev/null);" \
         "governor $(cat /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor 2>/dev/null || echo none)"
}

# run OUT PROGRAM ARGS...: the program's exit status in rc, timeout as rc=timeout.
run() {
    out=$1
    shift
    rm -f job.timeout
    "$@" > "$out" 2>&1 &
    pid=$!
    ( sleep $LIMIT; touch job.timeout; kill -9 $pid ) > /dev/null 2>&1 &
    watcher=$!
    wait $pid
    rc=$?
    kill $watcher 2> /dev/null
    [ -e job.timeout ] && rc=timeout
}

echo "S9-08 start: $(policy); seed $SEED"

run spin.out ./claude-s9spin.mic $ROUNDS $SEED
cat spin.out
if [ "$rc" = 0 ] && grep -q '^SUMMARY' spin.out; then
    echo "RESULT spin_core ok"
else
    echo "RESULT spin_core UNEXPECTED: exit=$rc"
    status=1
fi

rm -f fj.txt
round=0
while [ $round -lt $ROUNDS ]; do
    order=$(echo default delay128 delay512 active passive |
            awk -v s=$((SEED + round)) '{ srand(s); for (i = 1; i <= NF; i++) a[i] = $i;
                for (i = NF; i > 1; i--) { j = int(rand() * i) + 1; t = a[i]; a[i] = a[j]; a[j] = t }
                for (i = 1; i <= NF; i++) printf "%s ", a[i] }')
    for config in $order; do
        unset OMP_WAIT_POLICY GOMP_KNC_DELAY
        case $config in
            delay128) export GOMP_KNC_DELAY=128 ;;
            delay512) export GOMP_KNC_DELAY=512 ;;
            active) export OMP_WAIT_POLICY=active ;;
            passive) export OMP_WAIT_POLICY=passive ;;
        esac
        OMP_DISPLAY_ENV=verbose run fj.out ./claude-s9forkjoin.mic 240 $config
        unset OMP_WAIT_POLICY GOMP_KNC_DELAY
        grep '^SAMPLE' fj.out | sed "s/^/round=$round /"
        line=$(grep '^S9-08 forkjoin' fj.out)
        shown=$(grep -E 'GOMP_KNC_DELAY|GOMP_SPINCOUNT' fj.out | sed "s/^ *\[host\] //; s/'//g" | tr '\n' ' ')
        median=$(echo "$line" | sed -n 's/.*PASS:.* median_us_per_region=\([0-9.]*\).*/\1/p')
        if [ "$rc" = 0 ] && [ -n "$median" ]; then
            echo "RESULT forkjoin round=$round config=$config ok: $line; $shown"
            echo "$round $config $median" >> fj.txt
        else
            echo "RESULT forkjoin round=$round config=$config UNEXPECTED: exit=$rc"
            head -n 20 fj.out | sed 's/^/  | /'
            status=1
        fi
    done
    round=$((round + 1))
done
if [ -s fj.txt ]; then
    awk '{ m[$1, $2] = $3; r[$1] = 1; c[$2] = 1 }
         END { for (round in r) for (k in c) if ((round, k) in m && (round, "default") in m) {
                   v = m[round, k] / m[round, "default"]; printf "FJRATIO round=%s config=%s ratio=%.4f\n", round, k, v
                   n[k]++; x[k, n[k]] = v }
               for (k in c) { for (i = 1; i <= n[k]; i++) for (j = i + 1; j <= n[k]; j++)
                                  if (x[k, j] < x[k, i]) { t = x[k, i]; x[k, i] = x[k, j]; x[k, j] = t }
                              if (n[k]) printf "FJSUMMARY config=%s median_ratio=%.4f min=%.4f max=%.4f rounds=%d\n",
                                               k, x[k, int((n[k] + 1) / 2)], x[k, 1], x[k, n[k]], n[k] } }' fj.txt
fi
echo "S9-08 end: $(policy)"
exit $status
'''


def host_mode():
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    test = WORK / 'delay.exe'
    includes = [TESTS] + [LIBGOMP / 'config' / part for part in s9.CONFIG_PATH.split()]
    rc, text = s7.capture(['gcc', '-std=gnu11', '-O1', '-Wall', *('-I%s' % d for d in includes),
                           TESTS / 'delay.c', '-o', test])
    if rc:
        print('\n'.join(text.splitlines()[-15:]))
        print('FAIL host: delay.c does not build against %s' % LIBGOMP)
        return 1
    rc, text = s7.capture([test])
    print(text, end='', flush=True)
    return int(rc != 0)


def function_bodies(text):
    bodies, name = {}, None
    for line in text.splitlines():
        head = re.match(r'^[0-9a-f]+ <([^>]+)>:$', line)
        if head:
            name = head.group(1)
            bodies[name] = []
        elif name is not None:
            insn = re.match(r'^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2} )+\s*\t(.*)$', line)
            if insn:
                bodies[name].append((int(insn.group(1), 16), insn.group(2)))
    return bodies


def spin_loop(body):
    """True when a DELAY of a register just loaded from gomp_knc_delay lies inside a loop."""
    for i, (addr, insn) in enumerate(body):
        delay = re.match(r'delay\s+%(\w+)', insn)
        if not delay:
            continue
        loaded = any(re.match(r'mov\s+\S+,%' + delay.group(1) + r'\s+#.*<gomp_knc_delay>', prev)
                     for _, prev in body[max(0, i - 4):i])
        looped = any(a > addr and re.match(r'j\w+\s+([0-9a-f]+)\s', ins)
                     and int(re.match(r'j\w+\s+([0-9a-f]+)', ins).group(1), 16) <= addr
                     for a, ins in body)
        if loaded and looped:
            return True
    return False


def scan_mode():
    library = s9.LIBDIR / 'libgomp.so.1'
    if not library.is_file():
        print('FAIL scan: no %s (install the prefix first)' % library)
        return 1
    text = subprocess.check_output([str(TC / 'cross/bin/k1om-mpss-linux-objdump'), '-d', str(library)],
                                   text=True, errors='replace')
    bodies = function_bodies(text)
    problems = []
    for name in SPINNERS:
        if name not in bodies:
            problems.append('%s is not in libgomp.so.1' % name)
        elif not spin_loop(bodies[name]):
            problems.append('%s: no DELAY of gomp_knc_delay inside its spin loop' % name)
    if b'GOMP_KNC_DELAY' not in library.read_bytes():
        problems.append('libgomp.so.1 does not read GOMP_KNC_DELAY')
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    problems += ['lint libgomp.so.1: %s' % row for row in lint(library, TC, os.environ.copy())]
    for problem in problems:
        print('  ' + problem)
    print('%s scan %s: DELAY of gomp_knc_delay in the spin loop of %s; GOMP_KNC_DELAY read; lint '
          '(no pause)' % ('FAIL' if problems else 'PASS', library, ', '.join(SPINNERS)))
    return int(bool(problems))


def build_mode():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    failures = []
    programs = [(OUT / SPIN, TESTS / 'spin_core.c', ['-pthread']),
                (OUT / FORKJOIN, TESTS / 'forkjoin.c', ['-fopenmp'])]
    for program, source, flags in programs:
        rc, text = s7.capture([s9.GCC, '-std=gnu11', '-O2', '-Wall', *flags, source,
                               '-Wl,-rpath,$ORIGIN', '-o', program])
        if rc:
            print(text.strip()[-1200:])
            print('FAIL build: %s does not build' % source.name)
            return 1
    binaries, pending = [], [program for program, _, _ in programs]
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
    if 'libgomp.so.1' not in s7.needed(OUT / FORKJOIN):
        failures.append('%s does not need libgomp.so.1' % FORKJOIN)
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    failures += ['lint %s: %s' % (binary.name, row) for binary in binaries
                 for row in lint(binary, TC, os.environ.copy())]
    names = sorted(binary.name for binary in binaries)
    (OUT / 'run.sh').write_bytes(RUN_SH.encode())
    (OUT / 'files.txt').write_bytes(''.join('.work/_shared/S9-08/%s\n' % name for name in names).encode())
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL build: %d problems' % len(failures))
        return 1
    print('PASS build: %s staged; lint clean; native NOT RUN' % ' '.join(names))
    print('Lead card runs, three launches or more: tools/card_run --benchmark --timeout 3600 '
          '--file-list .work/_shared/S9-08/files.txt .work/_shared/S9-08/run.sh')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('host', 'scan', 'build'))
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__))],
                                         text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, args.mode])
    os.environ['TMPDIR'] = str(s7.SHARED / 'tmp')
    return {'host': host_mode, 'scan': scan_mode, 'build': build_mode}[args.mode]()


if __name__ == '__main__':
    sys.exit(main())
