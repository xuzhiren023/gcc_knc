#!/usr/bin/env python3
"""S5-08 assembly comparison and acceptance builds; invoke through tools/run.py."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build/gcc'
OUT = SHARED / 's5-08'


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', __file__],
            env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'),
                                script, *sys.argv[1:]], env=env)
    os.environ['PATH'] = ':'.join(str(TC / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    action = sys.argv[1]
    OUT.mkdir(exist_ok=True)
    if action == 'acceptance':
        return acceptance()
    if action not in ('before', 'after'):
        raise ValueError('expected before, after or acceptance')
    # Same fixed-option comparison as portability.py: dialect directives
    # only, so dg-options cannot override the requested optimization level.
    from portability import torture_dialect_options
    corpus = SHARED / 'gcc/gcc/testsuite/gcc.c-torture/compile'
    sources = sorted(corpus.rglob('*.c'))
    assert sources

    def compile_one(job):
        source, level = job
        relative = Path(level) / source.relative_to(corpus)
        dest = OUT / action / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        asm, error = Path(str(dest) + '.s'), Path(str(dest) + '.err')
        asm.unlink(missing_ok=True)
        error.unlink(missing_ok=True)
        result = subprocess.run(
            [str(BUILD / 'cc1'), '-quiet', '-w', '-march=knc', '-' + level,
             *torture_dialect_options(source), str(source), '-o', str(asm)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors='replace', timeout=300)
        if result.returncode:
            asm.unlink(missing_ok=True)
            error.write_text(result.stdout)
        if action == 'before':
            return level, 'failed' if result.returncode else 'compiled', str(relative), []
        old = OUT / 'before' / relative
        oldasm, olderr = Path(str(old) + '.s'), Path(str(old) + '.err')
        if error.exists() or olderr.exists():
            same = (error.exists() and olderr.exists()
                    and error.read_bytes() == olderr.read_bytes())
            return level, 'same failure' if same else 'changed failure', str(relative), []
        before, after = oldasm.read_text(), asm.read_text()
        if before == after:
            return level, 'identical', str(relative), []
        def functions(text):
            names = re.findall(r'^\s*\.type\s+([^,]+),\s*@function', text, re.M)
            bodies = {}
            for name in names:
                pattern = (r'^' + re.escape(name) + r':\n(.*?)^\s*\.size\s+'
                           + re.escape(name) + r'\s*,[^\n]*')
                match = re.search(pattern, text, re.M | re.S)
                assert match, (relative, name)
                bodies[name] = match[0]
            return bodies
        a, b = functions(before), functions(after)
        changed = [name for name in sorted(a.keys() | b.keys()) if a.get(name) != b.get(name)]
        return level, 'changed assembly', str(relative), changed

    counts = Counter()
    changes = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = ((source, level) for level in ('O0', 'O2') for source in sources)
        for level, status, name, functions in pool.map(compile_one, jobs):
            counts[level, status] += 1
            if status.startswith('changed'):
                changes.append(name + ': ' + status + '; functions: '
                               + (', '.join(functions) or '(outside function bodies)'))
    lines = ['S5-08 KNC torture assembly ' + action,
             'Fixed -O0 / -O2, -w; unconditional dialect directives only.',
             'Sources: ' + str(len(sources))]
    lines += [str(key) + ': ' + str(count) for key, count in sorted(counts.items())]
    lines += changes
    report = OUT / ('torture-' + action + '.txt')
    report.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines), flush=True)
    print('Report: ' + str(report), flush=True)
    return int(any(status == 'changed failure' for _, status in counts))


def acceptance():
    cc = [str(BUILD / 'xgcc'), '-B' + str(BUILD) + '/', '-march=knc',
          '--sysroot=' + str(TC / 'sysroot')]
    for fixture in ('s5_ops',):
        source = ROOT / 'tests/acceptance' / fixture
        dest = OUT / fixture
        dest.mkdir(exist_ok=True)
        def run(args):
            print('+ ' + ' '.join(map(str, args)), flush=True)
            subprocess.run(list(map(str, args)), check=True)
        driver = dest / 'driver.o'
        run([*cc, '-O0', '-fwrapv', '-c', source / 'driver.c', '-o', driver])
        variants = [('o2v', ['-O2', '-ftree-vectorize']), ('o3', ['-O3'])]
        if fixture == 's5_ops':
            variants += [('fast', ['-O3', '-ffast-math']),
                         ('neg', ['-O2', '-ftree-vectorize', '-DNEGATIVE_CONTROL'])]
        for name, flags in variants:
            obj = dest / (name + '.o')
            run([*cc, *flags, '-fwrapv', '-fopt-info-vec-optimized=' + str(dest / (name + '.vect')), '-c', source / 'loops.c', '-o', obj])
            run([*cc, *flags, '-fwrapv', driver, obj, '-lm', '-o', dest / (name + '.mic')])
            print('BUILT ' + fixture + '/' + name + '.mic; native execution pending lead', flush=True)
    report = (dest / 'o2v.vect').read_text()
    lines = (source / 'loops.c').read_text().splitlines()
    for name in ('cvt_i32_f32', 'cvt_u32_f32'):
        start = next(i for i, line in enumerate(lines, 1) if line.startswith('void ' + name + ' '))
        assert any('loops.c:' + str(start + 1) + ':' in row
                   and '64 byte vectors' in row for row in report.splitlines()), name + ': not vectorized'
        print('VECTORIZED ' + name)
    subprocess.run([sys.executable, str(ROOT / 'tools/knc_lint'),
                    *map(str, sorted(dest.glob('*.mic')))], check=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
