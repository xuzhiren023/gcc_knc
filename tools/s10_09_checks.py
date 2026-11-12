#!/usr/bin/env python3
"""S10-09 assembly comparison, card builds and the libknc_vmath check; invoke through tools/run.py.

    before | after   KNC torture compile assembly at -O0 and -O2 (as tools/s5_11_checks.py)
    acceptance       s5_ops (-fno-math-errno) and tests/regress/knc-v8df-divsqrt.c for the card
    vmath            libknc_vmath rebuilt: no x87 division or square root in asin and cbrt

Outputs go to .work/_shared/S10-09. Card runs are the lead's.
"""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import os
from pathlib import Path
import re
import subprocess
import sys

import storage

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
BUILD = Path(storage.gcc_build_dir(PROJECT)) / 'gcc'
OUT = SHARED / 'S10-09'
X87 = re.compile(r'\bf(?:div|sqrt)\w*\b')


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                      ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', __file__], env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]],
                               env=env)
    os.environ['PATH'] = ':'.join(str(TC / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    action = sys.argv[1]
    OUT.mkdir(exist_ok=True)
    if action == 'acceptance':
        return acceptance()
    if action == 'vmath':
        return vmath()
    if action not in ('before', 'after'):
        raise ValueError('expected before, after, acceptance or vmath')
    return torture(action)


def torture(action):
    # Fixed options, dialect directives only (portability.py), so dg-options cannot change the level.
    from portability import torture_dialect_options
    corpus = SHARED / 'gcc/gcc/testsuite/gcc.c-torture/compile'
    sources = sorted(corpus.rglob('*.c'))
    assert sources

    def functions(text, relative):
        bodies = {}
        for name in re.findall(r'^\s*\.type\s+([^,]+),\s*@function', text, re.M):
            match = re.search(r'^' + re.escape(name) + r':\n(.*?)^\s*\.size\s+'
                              + re.escape(name) + r'\s*,[^\n]*', text, re.M | re.S)
            assert match, (relative, name)
            bodies[name] = match[0]
        return bodies

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
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace',
            timeout=300)
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
        a, b = functions(before, relative), functions(after, relative)
        changed = [name for name in sorted(a.keys() | b.keys()) if a.get(name) != b.get(name)]
        return level, 'changed assembly', str(relative), changed

    counts = Counter()
    changes = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = ((source, level) for level in ('O0', 'O2') for source in sources)
        for level, status, name, changed in pool.map(compile_one, jobs):
            counts[level, status] += 1
            if status.startswith('changed'):
                changes.append(name + ': ' + status + '; functions: '
                               + (', '.join(changed) or '(outside function bodies)'))
    lines = ['S10-09 KNC torture assembly ' + action,
             'Fixed -O0 / -O2, -w; unconditional dialect directives only.',
             'Sources: ' + str(len(sources))]
    lines += [str(key) + ': ' + str(count) for key, count in sorted(counts.items())]
    lines += changes
    report = OUT / ('torture-' + action + '.txt')
    report.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines), flush=True)
    print('Report: ' + str(report), flush=True)
    return int(any(status == 'changed failure' for _, status in counts))


def run(args):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def vectorized(report, source, marker, name):
    """NAME's loop, on the line after MARKER in SOURCE, is in the -fopt-info-vec report."""
    line = next(i for i, text in enumerate(source.read_text().splitlines(), 1) if marker in text)
    assert any(source.name + ':' + str(line + 1) + ':' in text and '64 byte vectors' in text
               for text in report.read_text().splitlines()), name + ': not vectorized'
    print('VECTORIZED ' + name, flush=True)


def function_body(asm, name):
    match = re.search(r'^' + re.escape(name) + r':\n(.*?)^\s*\.size\s+' + re.escape(name) + r'\s*,',
                      asm, re.M | re.S)
    assert match, name
    return match[1]


def acceptance():
    cc = [str(BUILD / 'xgcc'), '-B' + str(BUILD) + '/', '-march=knc',
          '--sysroot=' + str(TC / 'sysroot')]
    source = ROOT / 'tests/acceptance/s5_ops'
    dest = OUT / 's5_ops'
    dest.mkdir(exist_ok=True)
    driver = dest / 'driver.o'
    run([*cc, '-O0', '-fwrapv', '-c', source / 'driver.c', '-o', driver])
    for name, flags in (('o2v', ['-O2', '-ftree-vectorize']), ('o3', ['-O3'])):
        flags = [*flags, '-fno-math-errno', '-fwrapv']
        report, asm = dest / (name + '.vect'), dest / (name + '.s')
        report.unlink(missing_ok=True)
        run([*cc, *flags, '-fopt-info-vec-optimized=' + str(report), '-S', source / 'loops.c',
             '-o', asm])
        run([*cc, *flags, driver, asm, '-lm', '-o', dest / (name + '.mic')])
        text = asm.read_text()
        for kernel in ('div_f64', 'sqrt_f64'):
            vectorized(report, source / 'loops.c', 'void ' + kernel + ' ', name + ' ' + kernel)
            # A variable bound: the masked tail must not fall back to the x87.
            assert not X87.search(function_body(text, kernel)), name + ' ' + kernel + ': x87'
    native = ROOT / 'tests/regress/knc-v8df-divsqrt.c'
    report, asm = OUT / 'knc-v8df-divsqrt.vect', OUT / 'knc-v8df-divsqrt.s'
    report.unlink(missing_ok=True)
    flags = ['-O2', '-fno-math-errno']
    run([*cc, *flags, '-fopt-info-vec-optimized=' + str(report), '-S', native, '-o', asm])
    run([*cc, *flags, asm, '-lm', '-o', OUT / 'knc-v8df-divsqrt.mic'])
    text = asm.read_text()
    for kernel in ('div_kernel', 'div_kernel_n', 'sqrt_kernel', 'sqrt_kernel_n'):
        body = function_body(text, kernel)
        assert re.search(r'\bvr(?:cp|sqrt)23ps\b', body), kernel + ': not vectorized'
        assert not X87.search(body), kernel + ': x87'
        print('VECTORIZED ' + kernel, flush=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/knc_lint'),
                    str(OUT / 'knc-v8df-divsqrt.mic'), *map(str, sorted(dest.glob('*.mic')))],
                   check=True)
    print('BUILT s5_ops o2v.mic, o3.mic and knc-v8df-divsqrt.mic; native execution pending lead',
          flush=True)
    return 0


def vmath():
    run([sys.executable, ROOT / 'tools/knc_vmath.py', '--out', 'S10-09/vmath'])
    for member in ('vmath_asin', 'vmath_cbrt'):
        text = (OUT / 'vmath/knc' / (member + '.s')).read_text()
        hits = sorted(set(X87.findall(text)))
        assert not hits, member + ': x87 ' + ' '.join(hits)
        assert re.search(r'\bvr(?:cp|sqrt)23ps\b', text), member + ': no vector sequence'
        print('NO X87 DIVISION OR SQUARE ROOT ' + member, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
