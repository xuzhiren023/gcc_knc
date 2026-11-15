"""S12-09 installed-prefix record and host-only execute/benchmark staging."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
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
OUT = SHARED / 'S12-09'
TC = SHARED / 'toolchain'
PREFIX = SHARED / 'gcc-knc-16.2.0'
CC = PREFIX / 'bin/k1om-mpss-linux-gcc.exe'
ENV = dict(os.environ, PATH=os.pathsep.join(str(TC / p) for p in
           ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH'])


def capture(*args):
    return subprocess.check_output(list(map(str, args)), env=ENV, text=True,
                                   stderr=subprocess.STDOUT).strip()


def prefixes():
    lines = ['S12-09 installed compiler/runtime record',
             'Installed compiler output below reports GCC 16.2.0 without a Git revision.',
             'The lane 1 checkout/build stamp is recorded separately; it does not attest lane 2 installation.',
             'Project HEAD: ' + capture('git', 'rev-parse', 'HEAD'),
             'GCC knc: ' + capture('git', '-C', SHARED / 'gcc', 'rev-parse', 'knc'),
             'Lane 1 build stamp: ' + (SHARED / 'gcc-build/.gcc-build-stamp.json').read_text(),
             'vmath source: ' + capture('git', 'log', '-1', '--format=%H %s', '--', 'contrib/knc-vecmath')]
    for suffix in ('', '-2'):
        prefix = SHARED / ('gcc-knc-16.2.0' + suffix)
        cc = prefix / 'bin/k1om-mpss-linux-gcc.exe'
        lines += ['', 'Prefix: ' + str(prefix), capture(cc, '-v')]
        for name in ('libgcc.a', 'libgcc_s.so', 'libgomp.a', 'libgfortran.a',
                     'libstdc++.a', 'libatomic.a', 'libknc_vmath.a'):
            path = capture(cc, '-print-file-name=' + name)
            if path == name:
                raise RuntimeError('missing ' + name + ' in ' + str(prefix))
            lines.append(name + ': ' + path)
        for subdir in ('bin', 'lib/gcc/k1om-mpss-linux/16.2.0', 'k1om-mpss-linux/lib'):
            directory = prefix / subdir
            lines.append(subdir + ': ' + ', '.join(sorted(p.name for p in directory.iterdir()))
                         if directory.is_dir() else subdir + ': absent')
        lines.append('vmath members: ' + capture(TC / 'cross/bin/k1om-mpss-linux-ar.exe',
                     't', prefix / 'lib/gcc/k1om-mpss-linux/16.2.0/libknc_vmath.a'))
    # Only our lane's build tree is inspected. Record actual filesystem times,
    # including the oldest object, rather than infer freshness from install time.
    import datetime
    for library in ('libgcc', 'libgomp', 'libgfortran', 'libstdc++-v3', 'libatomic'):
        directory = SHARED / 'gcc-build/k1om-mpss-linux' / library
        objects = list(directory.rglob('*.o'))
        for label, obj in [('oldest', min(objects, key=lambda p: p.stat().st_mtime)),
                           ('newest', max(objects, key=lambda p: p.stat().st_mtime))]:
            stamp = datetime.datetime.fromtimestamp(obj.stat().st_mtime).astimezone().isoformat()
            lines.append(f'{library} {label} object: {obj}; modified {stamp}')
    (ROOT / 'tests/baseline/S12-09-prefixes.txt').write_text('\n'.join(lines) + '\n')
    print('Recorded both installed prefixes and lane 1 target object dates.')
    return 0


def execute():
    out = OUT / 'execute'
    out.mkdir(parents=True, exist_ok=True)
    cc = [str(CC), '-march=knc', '-O2', '-w']
    sources = SHARED / 'gcc/gcc/testsuite/gcc.c-torture/execute'
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    import re
    options = re.compile(r'\{\s*dg-(?:additional-)?options\s+(?:"([^"\n]*)"|([^\s{}]+))(\s*\{\s*target\b)?')

    def build(source):
        flags = [flag for m in options.finditer(source.read_text(errors='replace'))
                 if m[3] is None for flag in shlex.split(m[1] or m[2])]
        binary = out / ('claude-t-' + source.stem + '.mic')
        binary.unlink(missing_ok=True)
        result = subprocess.run([*cc, *flags, str(source), '-lm', '-o', str(binary)],
                                env=ENV, capture_output=True, text=True, timeout=300)
        text = result.stdout + result.stderr
        state = ('ICE' if 'internal compiler error' in text else 'compile/link error') if result.returncode else 'linked'
        if state == 'linked':
            violations = list(lint(binary, TC, ENV))
            if violations:
                state = 'lint failure'
                text += '\n' + '\n'.join(map(str, violations))
        if state != 'linked':
            binary.unlink(missing_ok=True)
            (out / (source.stem + '.log')).write_text(text)
        return source.name, binary.name, state

    with ThreadPoolExecutor(8) as pool:
        rows = list(pool.map(build, sorted(sources.glob('*.c'))))
    (out / 'build.tsv').write_text('source\tprogram\tresult\n' + ''.join('\t'.join(r) + '\n' for r in rows))
    linked = [r for r in rows if r[2] == 'linked']
    (out / 'claude-torture.list').write_text(''.join(p + ' ' + s + '\n' for s, p, _ in linked))
    driver = out / 'claude-torture.mic'
    subprocess.run([*cc, str(ROOT / 'tools/claude-torture.c'), '-o', str(driver)], env=ENV, check=True)
    violations = list(lint(driver, TC, ENV))
    if violations:
        raise RuntimeError(str(violations))
    staged = [out / 'claude-torture.list', *[out / p for _, p, _ in linked]]
    (out / 'card-files.list').write_text(''.join(p.relative_to(PROJECT).as_posix() + '\n' for p in staged))
    with (SHARED / 'S11-12/execute/build.tsv').open() as stream:
        baseline = {r['source']: r['result'] for r in csv.DictReader(stream, delimiter='\t')}
    regressions = [s for s, _, state in rows if baseline.get(s) == 'linked' and state != 'linked']
    print('Compile/link/lint:', dict(Counter(r[2] for r in rows)))
    print('New failures versus S11-12:', regressions)
    print('Native execution NOT RUN; staged:', driver)
    return int(bool(regressions) or any(r[2] in ('ICE', 'lint failure') for r in rows))


def benchmark():
    bench.OUT = OUT / 'bench'
    bench.ELF = bench.OUT / 'vmath-bench.mic'
    return bench.build()


def jobs():
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ['# S12-09 lead card window\n\nNo native result is claimed. Run from the merged project root with Windows Python; '
             'coordinate one exclusive window. Estimates: execute 5-30 minutes; '
             'six vmath launches about 10-30 minutes each, total about 65-210 minutes, '
             'hard timeout budget 210 minutes. Actual calibration may fail; retain failures.\n\n',
             'Execute (60 allocated CPUs, 60 serial children, 64 MiB each):\n\n```\n'
             'python tools/card_run --threads 60 --timeout 1800 '
             '--file-list .work/_shared/S12-09/execute/card-files.list '
             '--collect claude-torture.details --collect-dir .work/_shared/S12-09/execute/collected '
             '.work/_shared/S12-09/execute/claude-torture.mic -j 60 --limit-mb 64 claude-torture.list\n```\n\n',
             'Vmath uses all 240 allocated CPUs at density 4 and 60 at density 1. '
             'Run in this order; retain each capture under bench/card-dD-lL.txt.\n\n```\n']
    for launch in range(1, 4):
        for density in ((1, 4) if launch % 2 else (4, 1)):
            lines.append(f'cmd /c "python tools/card_run --benchmark --threads {60 * density} --timeout 1800 '
                         f'.work/_shared/S12-09/bench/vmath-bench.mic --cores 60 --density {density} '
                         f'> .work/_shared/S12-09/bench/card-d{density}-l{launch}.txt 2>&1"\n')
    lines += ['```\n\nAssess all captures once with:\n\n```\n'
              'python tools/run.py --name s12-09-vmath-summary -- python tools/s10_04_vmath_bench.py '
              'summary --out .work/_shared/S12-09/bench --launches 3\n```\n\n'
              'Require every execute row to pass; retain details. Vmath requires all kernels and sets, '
              'clean checks, completed launches, and valid 50-200 ms batches. Staging is not numerical '
              'qualification or a measured speedup. x86 identity is lead-owned.\n']
    (OUT / 'README.md').write_text(''.join(lines))
    print('Staged lead commands:', OUT / 'README.md')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prefixes', 'execute', 'benchmark', 'jobs'])
    args = parser.parse_args()
    raise SystemExit(globals()[args.action]())
