#!/usr/bin/env python3
"""S5-11 assembly comparison and acceptance builds; invoke through tools/run.py."""
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
OUT = SHARED / 's5-11'


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
    if action == 'model':
        import unittest
        sys.path.insert(0, str(ROOT / 'tests/regress'))
        suite = unittest.TestLoader().loadTestsFromName('test_sqrt_model.DivModel')
        return int(not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful())
    if action == 't0':
        # E1/E2/E4 already ran once in the dedicated model job.
        import unittest
        suite = unittest.TestSuite()
        for path in sorted((ROOT / 'tests/regress').glob('test_*.py')):
            suite.addTests(unittest.TestLoader().discover(str(path.parent), pattern=path.name))
        for name in ('test_doctor.py', 'test_portability.py', 'test_knc_lint.py'):
            suite.addTests(unittest.TestLoader().discover(str(ROOT / 'tests/tools'), pattern=name))
        def remaining(tests):
            for test in tests:
                if isinstance(test, unittest.TestSuite):
                    yield from remaining(test)
                elif not test.id().endswith('.DivModel.test_models'):
                    yield test
        return int(not unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(remaining(suite))).wasSuccessful())
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
    lines = ['S5-11 KNC torture assembly ' + action,
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
        variants = [('o2v', ['-O2', '-ftree-vectorize', '-fno-math-errno']), ('o3', ['-O3', '-fno-math-errno'])]
        for name, flags in variants:
            obj = dest / (name + '.o')
            (dest / (name + '.vect')).unlink(missing_ok=True)
            run([*cc, *flags, '-fwrapv', '-fopt-info-vec-optimized=' + str(dest / (name + '.vect')), '-c', source / 'loops.c', '-o', obj])
            run([*cc, *flags, '-fwrapv', driver, obj, '-lm', '-o', dest / (name + '.mic')])
            print('BUILT ' + fixture + '/' + name + '.mic; native execution pending lead', flush=True)
    reports = [(dest / (row + '.vect')).read_text() for row in ('o2v', 'o3')]
    lines = (source / 'loops.c').read_text().splitlines()
    for name in ('div_f32',):
        start = next(i for i, line in enumerate(lines, 1) if line.startswith('void ' + name + ' '))
        assert all(any('loops.c:' + str(start + 1) + ':' in line
                       and '64 byte vectors' in line for line in report.splitlines())
                   for report in reports), name + ': not vectorized in both rows'
        print('VECTORIZED ' + name)
    native = ROOT / 'tests/regress/knc-div-sets.c'
    native_report = OUT / 'div-sets.vect'
    native_report.unlink(missing_ok=True)
    run([*cc, '-O2', '-ftree-vectorize', '-fno-math-errno',
         '-fopt-info-vec-optimized=' + str(native_report), native, '-lm',
         '-o', OUT / 'knc-div-sets.mic'])
    kernel_line = next(i for i, line in enumerate(native.read_text().splitlines(), 1)
                       if 'for (int i = 0; i < N;' in line)
    assert any('knc-div-sets.c:' + str(kernel_line) + ':' in line
               and '64 byte vectors' in line
               for line in native_report.read_text().splitlines()), 'native kernel not vectorized'
    print('BUILT division sets checker; native execution pending lead')
    subprocess.run([sys.executable, str(ROOT / 'tools/knc_lint'),
                    str(OUT / 'knc-div-sets.mic'),
                    *map(str, sorted(dest.glob('*.mic')))], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
