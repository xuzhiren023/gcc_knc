#!/usr/bin/env python3
"""S10-04: measure loops calling libknc_vmath against scalar libm (ADR-0014, ADR-0010).

    python tools/run.py --name s10-04-build --inputs tests/bench/vmath -- python tools/s10_04_vmath_bench.py build
    python tools/s10_04_vmath_bench.py card [--launches 3] [--dry-run]     (lead only)
    python tools/s10_04_vmath_bench.py summary                            (re-read saved outputs)

build: tests/bench/vmath/kernels.c twice with this lane's installed driver,
  -O2 -march=knc -fno-math-errno (vec: must call all six __knc_vmath_* entry points) and the same
  with -fno-tree-vectorize (scl: must call none), plus driver.c; linked with -pthread -lm only
  (libknc_vmath comes from the link spec) into .work/_shared/S10-04/vmath-bench.mic and linted.
card: per launch, one card_run --benchmark job at 60 cores for each of 1 and 4 threads per core
  (order alternates between launches), every kernel at the l2 and mem sets. Outputs overwrite
  .work/_shared/S10-04/card-d<D>-l<L>.txt. Then the summary.
summary: per kernel, set and density, each launch's median ratio vec/scl, and over all rounds of
  all launches the median ratio with a bootstrap percentile 95% interval (ADR-0010 amendment 2
  point 7), the speedup 1/median, failed checks and invalid batch sizes.
"""
import argparse
import os
from pathlib import Path
import random
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import storage  # noqa: E402

PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
OUT = SHARED / 'S10-04'
SRC = ROOT / 'tests/bench/vmath'
ELF = OUT / 'vmath-bench.mic'
ENTRY = {'__knc_vmath_%s_%d' % (f, 16 if f.endswith('f') else 8)
         for f in ('expf', 'logf', 'powf', 'exp', 'log', 'pow')}
FLAGS = ['-O2', '-march=knc', '-fno-math-errno', '-std=gnu11', '-Wall', '-Wextra', '-Werror']
BUILDS = {'vec': [], 'scl': ['-fno-tree-vectorize']}
DENSITIES = (1, 4)
ENV = dict(os.environ, PATH=os.pathsep.join(map(str, (TC / 'cross/bin', TC / 'cygwin/bin')))
           + os.pathsep + os.environ['PATH'])


def run(*args, capture=False):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    proc = subprocess.run(list(map(str, args)), env=ENV, stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None, universal_newlines=True)
    return proc


def driver():
    slot = storage.gcc_slot()
    version = (SHARED / storage.GCC_SLOTS[slot][0] / 'gcc/BASE-VER').read_text().strip()
    root = SHARED / ('gcc-knc-' + version + ('' if slot == '1' else '-' + slot))
    return root / 'bin/k1om-mpss-linux-gcc.exe'


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    ELF.unlink(missing_ok=True)
    cc = [driver(), '--sysroot=' + (TC / 'sysroot').as_posix()]
    failures, objects = [], []
    for name, extra in BUILDS.items():
        obj = OUT / ('kernels-%s.o' % name)
        if run(*cc, *FLAGS, *extra, '-DBUILD=' + name, '-c', SRC / 'kernels.c', '-o', obj).returncode:
            return 1
        nm = run(TC / 'cross/bin/k1om-mpss-linux-nm', '-u', obj, capture=True).stdout
        found = set(re.findall(r'\b__knc_vmath_\w+', nm))
        wanted = ENTRY if name == 'vec' else set()
        print('%s calls %s' % (name, sorted(found) or 'no vmath entry point'))
        if found != wanted:
            failures.append('%s calls %s, expected %s' % (name, sorted(found), sorted(wanted)))
        objects.append(obj)
    if run(*cc, *FLAGS, '-fno-tree-vectorize', '-pthread', '-c', SRC / 'driver.c',
           '-o', OUT / 'driver.o').returncode:
        return 1
    if failures:
        print('FAIL: ' + '; '.join(failures))
        return 1
    if (run(*cc, OUT / 'driver.o', *objects, '-pthread', '-lm', '-o', ELF).returncode or
            run(sys.executable, ROOT / 'tools/knc_lint', ELF).returncode):
        return 1
    print('BUILT and LINTED (NOT executed on card): ' + str(ELF))
    return 0


def output(density, launch):
    return OUT / ('card-d%d-l%d.txt' % (density, launch))


def card(launches, timeout, dry_run):
    for launch in range(1, launches + 1):
        order = DENSITIES if launch % 2 else DENSITIES[::-1]
        for density in order:
            cmd = [sys.executable, ROOT / 'tools/card_run', '--benchmark', '--timeout', timeout,
                   ELF, '--cores', 60, '--density', density]
            print('+ ' + ' '.join(map(str, cmd)), flush=True)
            if dry_run:
                continue
            proc = subprocess.run(list(map(str, cmd)), stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, universal_newlines=True)
            output(density, launch).write_text(proc.stdout)
            print('launch %d density %d: exit %d, %s' % (launch, density, proc.returncode,
                                                         output(density, launch)))
    return 0 if dry_run else summary(launches)


def median(values):
    v = sorted(values)
    return v[len(v) // 2] if len(v) % 2 else 0.5 * (v[len(v) // 2 - 1] + v[len(v) // 2])


def bootstrap(values, draws=10000):
    rng = random.Random(1004)
    meds = sorted(median(rng.choices(values, k=len(values))) for _ in range(draws))
    return meds[int(0.025 * draws)], meds[int(0.975 * draws) - 1]


def fields(line):
    return dict(re.findall(r'(\w+)=(\S+)', line))


def summary(launches):
    rounds, launch_med, problems, keys = {}, {}, [], []
    for density in DENSITIES:
        for launch in range(1, launches + 1):
            path = output(density, launch)
            if not path.exists():
                problems.append('missing ' + path.name)
                continue
            text = path.read_text()
            if 'S10-04 vmath bench' not in text:
                problems.append('%s: no final line (infrastructure or crash)' % path.name)
            for line in text.splitlines():
                f = fields(line)
                key = (f.get('kernel'), f.get('set'), density)
                if line.startswith('check ') and line.endswith('FAIL'):
                    problems.append('%s: %s' % (path.name, line))
                elif line.startswith('round '):
                    if key not in rounds:
                        keys.append(key)
                    rounds.setdefault(key, []).append(float(f['ratio_vec_over_scl']))
                elif line.startswith('summary '):
                    launch_med.setdefault(key, []).append(f['median_ratio_vec_over_scl'])
                    if f['batches'] != 'valid':
                        problems.append('%s: invalid batch size: %s' % (path.name, line))
    print('kernel set threads_per_core | median vec/scl per launch | all rounds: median [95% CI] '
          'speedup')
    for key in keys:
        low, high = bootstrap(rounds[key])
        m = median(rounds[key])
        print('%s %s %d | %s | %.4f [%.4f, %.4f] %.2fx (%d rounds)'
              % (*key, ' '.join(launch_med.get(key, [])), m, low, high, 1 / m, len(rounds[key])))
    for p in problems:
        print('PROBLEM ' + p)
    return 1 if problems else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=['build', 'card', 'summary'])
    parser.add_argument('--launches', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=1800, help='card_run timeout per job, s')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.action == 'build':
        return build()
    if args.action == 'card':
        return card(args.launches, args.timeout, args.dry_run)
    return summary(args.launches)


if __name__ == '__main__':
    sys.exit(main())
