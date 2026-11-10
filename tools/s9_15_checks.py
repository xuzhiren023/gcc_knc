#!/usr/bin/env python3
"""S9-15 libgomp's KNC spin time before sleeping (best-practice review item 3); invoke through tools/run.py.

    python tools/s9_15_checks.py host
        compiles tests/regress/s9_15/spincount_host.c with the Cygwin GCC against the lane's
        libgomp/config/linux/knc/card.h and runs it: the GOMP_SPINCOUNT of 3, 30 and 200 msec in
        DELAY 128 periods at 1100 and 1238 MHz.
    python tools/s9_15_checks.py build
        builds tests/regress/s9_15/gapjoin.c (fork/join with serial gaps of 1, 10 and 100 ms at 240
        threads) and tests/regress/s9_08/spin_core.c (S9-08 measurement 1, the sibling cost) with the
        installed prefix (tools/s7_09_checks.py install) into the card batch .work/_shared/S9-15, with
        the prefix libraries they need, the lint, run.sh (the card program) and files.txt (its
        --file-list).

Nothing runs natively here: the lead runs run.sh on the card. The default spin count is not changed.
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
TESTS = ROOT / 'tests/regress/s9_15'
KNC = s7.SHARED / s7.GCC_TREE / 'libgomp/config/linux/knc'
WORK = s7.SHARED / 'tmp/s9-15'
OUT = s7.SHARED / 'S9-15'
SPIN = 'claude-s915-spin.mic'
GAPJOIN = 'claude-s915-gapjoin.mic'
RUN_SH = r'''#!/bin/sh
# Lead-only card program for S9-15 (tools/s9_15_checks.py build); files.txt is its --file-list:
#   card_run --benchmark --timeout 3600 --file-list .work/_shared/S9-15/files.txt .work/_shared/S9-15/run.sh
# Timed per ADR-0010; run it in at least three launches. Every result is printed. Exit 0 when every
# program ran and passed.
# 1. claude-s915-spin.mic: S9-08 measurement 1 (tests/regress/s9_08/spin_core.c): one core, the
#    worker alone and with 1-3 spinning siblings, no hint and DELAY 32/128/512; RATIO lines are
#    per-round T(config)/T(alone), SUMMARY their median. The s*-delay128 rows are the sibling cost.
# 2. claude-s915-gapjoin.mic: 240 threads (60x4, the KNC default spread binding), parallel regions
#    after serial gaps of 1, 10 and 100 ms, GOMP_KNC_DELAY=128 and GOMP_SPINCOUNT for 3, 30 and 200
#    msec at this card's clock (gapjoin spincount MSEC 128, card.h's arithmetic), one process per
#    setting, the settings in an order drawn per round. GJSUMMARY lines are, per setting and gap, the
#    median over rounds of the median entry time, region time and process CPU per wall time. Each
#    process shows its GOMP_KNC_DELAY and GOMP_SPINCOUNT from OMP_DISPLAY_ENV=verbose.
# BusyBox 1.19 sh: no timeout applet, so a watcher kills a program after LIMIT seconds.
cd -- "$(dirname -- "$0")" || exit 2
LIMIT=900
ROUNDS=5
SEED=$(date +%s)
status=0

policy() {
    echo "clocksource $(cat /sys/devices/system/clocksource/clocksource0/current_clocksource 2>/dev/null);" \
         "governor $(cat /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor 2>/dev/null || echo none);" \
         "$(grep -m 1 'cpu MHz' /proc/cpuinfo)"
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

echo "S9-15 start: $(policy); seed $SEED"

run spin.out ./claude-s915-spin.mic $ROUNDS $SEED
cat spin.out
if [ "$rc" = 0 ] && grep -q '^SUMMARY' spin.out; then
    echo "RESULT spin_core ok"
else
    echo "RESULT spin_core UNEXPECTED: exit=$rc"
    status=1
fi

for msec in 3 30 200; do
    count=$(./claude-s915-gapjoin.mic spincount $msec 128)
    case $count in
        ''|*[!0-9]*) echo "RESULT spincount msec=$msec UNEXPECTED: '$count'"; exit 1 ;;
    esac
    eval spin$msec=$count
    echo "SPINCOUNT msec=$msec delay=128 count=$count"
done

rm -f gj.txt
round=0
while [ $round -lt $ROUNDS ]; do
    order=$(echo spin3 spin30 spin200 |
            awk -v s=$((SEED + round)) '{ srand(s); for (i = 1; i <= NF; i++) a[i] = $i;
                for (i = NF; i > 1; i--) { j = int(rand() * i) + 1; t = a[i]; a[i] = a[j]; a[j] = t }
                for (i = 1; i <= NF; i++) printf "%s ", a[i] }')
    for config in $order; do
        eval count=\$$config
        export GOMP_KNC_DELAY=128 GOMP_SPINCOUNT=$count OMP_DISPLAY_ENV=verbose
        run gj.out ./claude-s915-gapjoin.mic 240 $config 1 10 100
        unset GOMP_KNC_DELAY GOMP_SPINCOUNT OMP_DISPLAY_ENV
        shown=$(grep -E 'GOMP_KNC_DELAY|GOMP_SPINCOUNT' gj.out | sed "s/^ *\[host\] //; s/'//g" | tr '\n' ' ')
        lines=$(grep -c '^S9-15 gapjoin .* PASS:' gj.out)
        if [ "$rc" = 0 ] && [ "$lines" = 3 ]; then
            grep '^S9-15 gapjoin' gj.out | while read -r line; do
                echo "RESULT gapjoin round=$round config=$config ok: $line; $shown"
            done
            grep '^S9-15 gapjoin' gj.out | sed "s/^/$round $config /" >> gj.txt
        else
            echo "RESULT gapjoin round=$round config=$config UNEXPECTED: exit=$rc"
            head -n 20 gj.out | sed 's/^/  | /'
            status=1
        fi
    done
    round=$((round + 1))
done
if [ -s gj.txt ]; then
    awk 'function field(name,   i) { for (i = 1; i <= NF; i++) if (index($i, name "=") == 1)
                                         return substr($i, length(name) + 2) }
         function median(k, what,   i, j, t, m) {
             m = n[k]; for (i = 1; i <= m; i++) y[i] = v[k, what, i]
             for (i = 1; i <= m; i++) for (j = i + 1; j <= m; j++) if (y[j] < y[i]) { t = y[i]; y[i] = y[j]; y[j] = t }
             return y[int((m + 1) / 2)] }
         { k = $2 " " field("gap_ms"); c[k] = 1; n[k]++
           v[k, "entry", n[k]] = field("entry_median_us"); v[k, "region", n[k]] = field("region_median_us")
           v[k, "cpu", n[k]] = field("cpu_per_wall") }
         END { for (k in c) { split(k, p, " ")
                   printf "GJSUMMARY config=%s gap_ms=%s entry_median_us=%.1f region_median_us=%.1f cpu_per_wall=%.2f rounds=%d\n",
                          p[1], p[2], median(k, "entry"), median(k, "region"), median(k, "cpu"), n[k] } }' gj.txt | sort
fi
echo "S9-15 end: $(policy)"
exit $status
'''


def host_mode():
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    test = WORK / 'spincount_host.exe'
    rc, text = s7.capture(['gcc', '-std=gnu11', '-O2', '-Wall', '-Werror=implicit-function-declaration',
                           '-I%s' % KNC, TESTS / 'spincount_host.c', '-o', test])
    if rc:
        print('\n'.join(line for line in text.splitlines() if 'error' in line)[-3000:])
        print('FAIL host: spincount_host.c does not build against %s' % KNC)
        return 1
    rc, text = s7.capture([test])
    print(text, end='', flush=True)
    return int(rc != 0)


def build_mode():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    failures = []
    programs = [(OUT / SPIN, ROOT / 'tests/regress/s9_08/spin_core.c', ['-pthread']),
                (OUT / GAPJOIN, TESTS / 'gapjoin.c', ['-fopenmp', '-I%s' % KNC])]
    for program, source, flags in programs:
        rc, text = s7.capture([s9.GCC, '-std=gnu11', '-O2', '-Wall', *flags, source,
                               '-Wl,-rpath,$ORIGIN', '-o', program])
        if rc or text.strip():
            print(text.strip()[-1200:])
            print('FAIL build: %s does not build cleanly' % source.name)
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
    if 'libgomp.so.1' not in s7.needed(OUT / GAPJOIN):
        failures.append('%s does not need libgomp.so.1' % GAPJOIN)
    elif b'GOMP_KNC_DELAY' not in (OUT / 'libgomp.so.1').read_bytes():
        failures.append('the staged libgomp.so.1 does not read GOMP_KNC_DELAY')
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    failures += ['lint %s: %s' % (binary.name, row) for binary in binaries
                 for row in lint(binary, TC, os.environ.copy())]
    names = sorted(binary.name for binary in binaries)
    (OUT / 'run.sh').write_bytes(RUN_SH.encode())
    (OUT / 'files.txt').write_bytes(''.join('.work/_shared/S9-15/%s\n' % name for name in names).encode())
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL build: %d problems' % len(failures))
        return 1
    print('PASS build: %s staged; lint clean; native NOT RUN' % ' '.join(names))
    print('Lead card runs, three launches or more: tools/card_run --benchmark --timeout 3600 '
          '--file-list .work/_shared/S9-15/files.txt .work/_shared/S9-15/run.sh')
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
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, args.mode])
    os.environ['TMPDIR'] = str(s7.SHARED / 'tmp')
    return {'host': host_mode, 'build': build_mode}[args.mode]()


if __name__ == '__main__':
    sys.exit(main())
