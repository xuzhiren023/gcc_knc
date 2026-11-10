#!/usr/bin/env python3
"""S9-07 libgomp KNC affinity defaults; invoke through tools/run.py.

    python tools/s9_07_checks.py host
        writes the two fixture trees (a sysfs CPU topology, and a /proc/cpuinfo alone) for the
        card's 244 CPUs into .work/_shared/tmp/s9-07, compiles tests/regress/s9_07/places.c with
        the Cygwin GCC against the lane's libgomp sources in the k1om config_path order, and runs
        it on each tree: the place list, omp_get_num_procs and the default team size for the
        whole card, a 120-CPU mask and a mask with only the OS core.
    python tools/s9_07_checks.py build
        builds tests/regress/s9_07/bind.c with the installed prefix into the card batch
        .work/_shared/S9-07, with the prefix libraries it needs, the lint, run.sh (the card
        program) and files.txt (its --file-list).

The fixture is synthetic: the topology is the card's (docs/research/knc-measurement.md "Topology
and working sets"; S9-06 card probe 2026-11-10), the cpuinfo text is the x86 layout with the
fields a topology reader could use. Nothing runs natively here: the lead runs run.sh on the card.
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
TESTS = ROOT / 'tests/regress/s9_07'
LIBGOMP = s7.SHARED / s7.GCC_TREE / 'libgomp'
WORK = s7.SHARED / 'tmp/s9-07'
OUT = s7.SHARED / 'S9-07'
PROGRAM = 'claude-s9bind.mic'
# Core c of 0-59 is CPUs 4c+1..4c+4; core 60, the OS core, is CPUs 0 and 241-243.
CORES = {core: list(range(4 * core + 1, 4 * core + 5)) for core in range(60)}
CORES[60] = [0, 241, 242, 243]
RUN_SH = r'''#!/bin/sh
# Lead-only card program for S9-07 (tools/s9_07_checks.py build); files.txt is its --file-list:
#   card_run --benchmark --timeout 1800 --file-list .work/_shared/S9-07/files.txt .work/_shared/S9-07/run.sh
#   card_run --cores <30 cores> --timeout 1800 --file-list .work/_shared/S9-07/files.txt .work/_shared/S9-07/run.sh
# No arguments: the team sizes follow the mask, 1, 2 and 4 threads per core of it (60, 120 and
# 240 on the whole card). The environment passes through. Exit 0 when every RESULT line says ok.
# The first three jobs are the KNC defaults (no OMP_PROC_BIND, OMP_PLACES or GOMP_CPU_AFFINITY),
# then the opt-out, then the explicit settings of docs/research/knc-libgomp.md section 3, which
# must behave as before.
# BusyBox 1.19 sh: no timeout applet, so a watcher kills a program after LIMIT seconds.
cd -- "$(dirname -- "$0")" || exit 2
LIMIT=300
status=0
export OMP_DISPLAY_AFFINITY=true

# job LABEL PLACES PER-PLACE BIND [NAME=VALUE...]: one RESULT line; status=1 unless the program
# passes (its arguments: tests/regress/s9_07/bind.c) and libgomp displays one affinity line per
# thread, PER-PLACE of them with the affinity of the first line.
job() {
    label=$1 places=$2 per=$3 bind=$4
    shift 4
    rm -f job.timeout
    ( for setting in "$@"; do export "$setting"; done
      exec ./claude-s9bind.mic "$places" "$per" "$bind" ) > job.out 2>&1 &
    pid=$!
    ( sleep $LIMIT; touch job.timeout; kill -9 $pid ) > /dev/null 2>&1 &
    watcher=$!
    wait $pid
    rc=$?
    kill $watcher 2> /dev/null
    [ -e job.timeout ] && rc=timeout
    threads=$(sed -n 's/^S9-07 bind PASS .* threads=\([0-9]*\),.*/\1/p' job.out)
    shown=$(grep -c ' affinity ' job.out)
    first=$(sed -n 's/^.* affinity \(.*\)$/\1/p' job.out | head -n 1)
    same=$(grep -c " affinity $first\$" job.out)
    why=
    [ "$rc" = 0 ] || why="$why exit=$rc"
    [ -n "$threads" ] || why="$why no-PASS-line"
    [ "$shown" = "$threads" ] || why="$why displayed=$shown(want ${threads:-?})"
    [ "$per" = 0 ] || [ "$same" = "$per" ] || why="$why displayed-on-$first=$same(want $per)"
    if [ -z "$why" ]; then
        echo "RESULT $label ok: $(grep '^S9-07 bind' job.out); first affinity $first"
    else
        echo "RESULT $label UNEXPECTED:$why"
        grep -v ' affinity ' job.out | head -n 20 | sed 's/^/  | /'
        grep ' affinity ' job.out | head -n 8 | sed 's/^/  | /'
        status=1
    fi
}

job default-1-per-core cores 1 spread
job default-2-per-core cores 2 spread
job default-4-per-core cores 4 spread
job proc-bind-false none 0 false OMP_PROC_BIND=false
job places cores 4 true 'OMP_PLACES={1:4}:60:4'
job places-spread cores 1 spread 'OMP_PLACES={1:4}:60:4' OMP_PROC_BIND=spread
job places-close cores 2 close 'OMP_PLACES={1:4}:60:4' OMP_PROC_BIND=close
job cpu-affinity first 1 true GOMP_CPU_AFFINITY=1-237:4
exit $status
'''


def cpu_list(cpus):
    """The kernel's list format: 1-4 or 0,241-243."""
    runs = []
    for cpu in sorted(cpus):
        if runs and runs[-1][1] == cpu - 1:
            runs[-1][1] = cpu
        else:
            runs.append([cpu, cpu])
    return ','.join(str(a) if a == b else '%d-%d' % (a, b) for a, b in runs)


def write_fixtures():
    shutil.rmtree(WORK, ignore_errors=True)
    core_of = {cpu: core for core, cpus in CORES.items() for cpu in cpus}
    everything = cpu_list(core_of)
    for cpu, core in core_of.items():
        topology = WORK / ('sysfs/sys/devices/system/cpu/cpu%d/topology' % cpu)
        topology.mkdir(parents=True)
        (topology / 'thread_siblings_list').write_bytes((cpu_list(CORES[core]) + '\n').encode())
        (topology / 'core_siblings_list').write_bytes((everything + '\n').encode())
    (WORK / 'cpuinfo/proc').mkdir(parents=True)
    (WORK / 'cpuinfo/proc/cpuinfo').write_bytes(''.join(
        'processor\t: %d\nvendor_id\t: GenuineIntel\ncpu family\t: 11\nmodel\t\t: 1\n'
        'physical id\t: 0\nsiblings\t: %d\ncore id\t\t: %d\ncpu cores\t: %d\n\n'
        % (cpu, len(core_of), core_of[cpu], len(CORES)) for cpu in sorted(core_of)).encode())


def host_mode():
    write_fixtures()
    test = WORK / 'places.exe'
    includes = [TESTS] + [LIBGOMP / 'config' / part for part in s9.CONFIG_PATH.split()]
    rc, text = s7.capture(['gcc', '-std=gnu11', '-O1', '-Wall', *('-I%s' % d for d in includes),
                           TESTS / 'places.c', '-o', test])
    if rc:
        print('\n'.join(text.splitlines()[-15:]))
        print('FAIL host: places.c does not build against %s' % LIBGOMP)
        return 1
    failed = 0
    for tree in ('sysfs', 'cpuinfo'):
        rc, text = s7.capture([test, tree, WORK / tree])
        print(text, end='', flush=True)
        failed += rc != 0
    print('%s host: default places from the sysfs tree and from /proc/cpuinfo alone'
          % ('FAIL' if failed else 'PASS'))
    return int(bool(failed))


def build_mode():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    program = OUT / PROGRAM
    rc, text = s7.capture([s9.GCC, '-std=gnu11', '-O2', '-Wall', '-fopenmp', TESTS / 'bind.c',
                           '-Wl,-rpath,$ORIGIN', '-o', program])
    if rc:
        print(text.strip()[-1200:])
        print('FAIL build: bind.c does not build and link with -fopenmp')
        return 1
    failures = []
    binaries, pending = [], [program]
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
    if 'libgomp.so.1' not in s7.needed(program):
        failures.append('%s does not need libgomp.so.1' % PROGRAM)
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    failures += ['lint %s: %s' % (binary.name, row) for binary in binaries
                 for row in lint(binary, TC, os.environ.copy())]
    names = sorted(binary.name for binary in binaries)
    (OUT / 'run.sh').write_bytes(RUN_SH.encode())
    (OUT / 'files.txt').write_bytes(''.join('.work/_shared/S9-07/%s\n' % name for name in names).encode())
    for problem in failures:
        print('  ' + problem)
    if failures:
        print('FAIL build: %d problems' % len(failures))
        return 1
    print('PASS build: %s staged with %s; lint clean; native NOT RUN' % (PROGRAM, ' '.join(names[1:])))
    print('Lead card runs: tools/card_run --benchmark --timeout 1800 --file-list '
          '.work/_shared/S9-07/files.txt .work/_shared/S9-07/run.sh, and the same with a 30-core '
          '--cores list in place of --benchmark; exit 0 means every RESULT line is ok.')
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
