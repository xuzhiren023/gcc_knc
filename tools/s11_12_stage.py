#!/usr/bin/env python3
"""S11-12 host-only batch staging. Never launches a card job."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys

import storage
import s10_04_vmath_bench as bench

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
OUT = SHARED / 'S11-12'
TC = SHARED / 'toolchain'
ENV = dict(os.environ, PATH=os.pathsep.join(str(TC / p) for p in
           ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH'])


def entry(name, arguments, estimate, extra=''):
    directory = OUT / name
    directory.mkdir(parents=True, exist_ok=True)
    command = 'python tools/card_run ' + shlex.join(list(map(str, arguments)))
    (directory / 'run.sh').write_bytes((
        '#!/bin/sh\nset -eu\ncd "$(dirname "$0")/../../../.."\nexec ' + command + '\n'
    ).encode('utf8'))
    return f'- `{name}/run.sh`: {estimate}. {extra}\n'


def execute():
    directory = OUT / 'execute'
    rows = [line.split('\t') for line in (directory / 'build.tsv').read_text().splitlines()[1:]]
    programs = [directory / r[1] for r in rows if r[2] == 'linked']
    driver = directory / 'claude-torture.mic'
    build = Path(storage.gcc_build_dir(PROJECT)) / 'gcc'
    subprocess.run([str(build / 'xgcc.exe'), '-B' + build.as_posix() + '/',
                    '-O2', '-march=knc', str(ROOT / 'tools/claude-torture.c'),
                    '-o', str(driver)], env=ENV, check=True)
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']

    def check(path):
        return list(lint(path, TC, ENV))

    with ThreadPoolExecutor(8) as pool:
        failures = [failure for result in pool.map(check, programs + [driver]) for failure in result]
    if failures:
        for failure in failures:
            print('LINT FAILURE', failure)
        return 1
    paths = [directory / 'claude-torture.list', *programs]
    (directory / 'card-files.list').write_text(''.join(
        p.relative_to(PROJECT).as_posix() + '\n' for p in paths))
    print('BUILT/LINTED execute:', len(programs), 'of', len(rows), '; no native execution')
    return 0


def benchmark():
    bench.OUT = OUT / 'bench'
    bench.ELF = bench.OUT / 'vmath-bench.mic'
    return bench.build()


def prefixes():
    def capture(argv):
        return subprocess.check_output(list(map(str, argv)), env=ENV,
                                       stderr=subprocess.STDOUT, universal_newlines=True).strip()

    lines = ['S11-12 compiler/runtime/library record',
             'Project HEAD: ' + capture(['git', 'rev-parse', 'HEAD']),
             'GCC knc: ' + capture(['git', '-C', SHARED / 'gcc', 'rev-parse', 'knc']),
             'GCC built tree: ' + (SHARED / 'gcc-build/.gcc-build-stamp.json').read_text(),
             'Installed revisions below are compiler-reported; the lead records installation.',
             'Runtime sources share the GCC revision; latest path changes:']
    for source in ('libgcc', 'libgfortran', 'libstdc++-v3', 'libatomic', 'libgomp'):
        lines.append(source + ': ' + capture(['git', '-C', SHARED / 'gcc', 'log', '-1',
                     '--format=%h %s', 'knc', '--', source]))
    lines.append('vmath source: ' + capture(['git', 'log', '-1', '--format=%h %s',
                                            '--', 'contrib/knc-vecmath']))
    missing = []
    for lane, suffix in ((1, ''), (2, '-2')):
        prefix = SHARED / ('gcc-knc-16.2.0' + suffix)
        cc = prefix / 'bin/k1om-mpss-linux-gcc.exe'
        lines += ['', 'Lane ' + str(lane) + ': ' + str(prefix)]
        try:
            lines += [capture([cc, '--version']), capture([cc, '-v'])]
            for name in ('libgcc.a', 'libgfortran.a', 'libstdc++.a', 'libatomic.a',
                         'libgomp.a', 'libknc_vmath.a'):
                path = capture([cc, '-print-file-name=' + name])
                lines.append(name + ': ' + path)
                if path == name:
                    missing.append('lane %d missing %s' % (lane, name))
            archive = prefix / 'lib/gcc/k1om-mpss-linux/16.2.0/libknc_vmath.a'
            members = capture([TC / 'cross/bin/k1om-mpss-linux-ar.exe', 't', archive]).splitlines()
            lines.append('vmath archive entries: ' + str(len(members)))
            lines.append('vmath members: ' + ' '.join(members))
            for subdir in ('bin', 'lib/gcc/k1om-mpss-linux/16.2.0', 'k1om-mpss-linux/lib'):
                directory = prefix / subdir
                lines.append(subdir + ': ' + ', '.join(sorted(p.name for p in directory.iterdir()))
                             if directory.is_dir() else subdir + ': absent')
        except (OSError, subprocess.CalledProcessError) as error:
            missing.append('lane %d: %s' % (lane, error))
    lines += ['', *missing]
    (ROOT / 'tests/baseline/S11-12-prefixes.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(line for line in lines if 'entries:' in line or line.startswith('Lane ')))
    for error in missing:
        print('INFRASTRUCTURE:', error)
    return int(bool(missing))


def jobs():
    spec = importlib.util.spec_from_file_location('qualification', ROOT / 'tests/vmath/card_qualify.py')
    qualification = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qualification)
    readme = ['# S11-12 staged card jobs\n\n',
              'Lead only: run each run.sh with sh from Cygwin after coordination. '
              'No card job has run. All paths survive deletion of the ticket worktree. '
              'Times below are scheduling estimates, not measurements. '
              'A profile limits cores/memory; it does not emulate clock or bandwidth.\n\n']
    readme.append(entry('execute', ['--threads', 240, '--timeout', 1800,
        '--file-list', '.work/_shared/S11-12/execute/card-files.list',
        '--collect', 'claude-torture.details',
        '--collect-dir', '.work/_shared/S11-12/execute/collected',
        '.work/_shared/S11-12/execute/claude-torture.mic', '-j', 60,
        '--limit-mb', 64, 'claude-torture.list'],
        'about 5-30 min, hard cap 30 min',
        'Answer-only batch: 60 serial children, one per physical core in capacity. '
        'Each child has a 64 MiB limit; native failures remain failures.'))
    for name, jobset in qualification.JOBS.items():
        for job, program, arguments, expected in jobset:
            timeout = 14400 if name == 'full' else 1800
            estimate = ('about 5-240 min, hard cap 4 h' if name == 'full' else
                        'about 1-30 min, hard cap 30 min')
            readme.append(entry('qualify-' + job,
                ['--threads', 240, '--timeout', timeout,
                 '.work/_shared/S11-12/knc/' + program + '.mic', *arguments],
                estimate, 'Expected ' + expected + '; 240 affinity-aware workers. '
                'Save raw output and assess with tests/vmath/card_qualify.py; '
                'v1 screens require host MPFR recheck before a qualification claim.'))
    for profile, cores in [('full', 60), ('3100', 56), ('5100', 59)]:
        for launch in range(1, 4):
            readme.append(entry(f'bench-{profile}-{launch}',
                ['--benchmark', '--profile', profile, '--threads', 240,
                 '--timeout', 1800, '.work/_shared/S11-12/bench/vmath-bench.mic',
                 '--cores', cores, '--density', 4],
                'about 10-30 min, hard cap 30 min',
                'Exclusive timed job, four workers/core (240/224/236 workers). '
                'Save output; reject invalid batch sizes using '
                'tools/s10_04_vmath_bench.py summary logic.'))
    readme += ['\nQualification jobs are answer-only and each uses its full allocation; '
               'do not pack several 240-worker jobs together. Execute children are serial. '
               'Timed jobs are exclusive. No native or performance result is validated by staging.\n',
               '\nThe host qualification programs are under host/. To analyze saved '
               'qualification output, load tests/vmath/card_qualify.py, set OUT to '
               '.work/_shared/S11-12, and call assess(job, program, arguments, expected, text). '
               'This rechecks v1 dumps with the staged MPFR host program. Negative controls '
               'must fail for their intended numerical reason.\n']
    (OUT / 'README.md').write_text(''.join(readme), encoding='utf8')
    print('STAGED', len(list(OUT.glob('*/run.sh'))), 'entries; no native result')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['execute', 'benchmark', 'jobs', 'prefixes'])
    args = parser.parse_args()
    raise SystemExit(globals()[args.action]())
