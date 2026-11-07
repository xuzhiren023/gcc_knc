"""Stage/lint the torture execute suite for the lead; never run card jobs."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import os
from pathlib import Path
import re
import runpy
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'


def main():
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
    if os.name == 'nt':
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', __file__], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    out = SHARED / 'S6-06/execute'
    out.mkdir(parents=True, exist_ok=True)
    build = SHARED / 'gcc-build/gcc'
    cc = [str(build / 'xgcc'), '-B' + str(build) + '/', '-march=knc', '-O2', '-w']
    corpus = SHARED / 'gcc/gcc/testsuite/gcc.c-torture/execute'
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    options = re.compile(r'\{\s*dg-(?:additional-)?options\s+(?:"([^"\n]*)"|([^\s{}]+))(\s*\{\s*target\b)?')

    def compile_one(source):
        flags = [flag for m in options.finditer(source.read_text(errors='replace'))
                 if m[3] is None for flag in shlex.split(m[1] or m[2])]
        program = 'claude-t-' + source.stem + '.mic'
        binary = out / program
        result = subprocess.run([*cc, *flags, str(source), '-lm', '-o', str(binary)],
                                env=env, capture_output=True, text=True, timeout=300)
        diagnostic = result.stdout + result.stderr
        state = ('ICE' if 'internal compiler error' in diagnostic else 'compile/link error') if result.returncode else 'linked'
        if state == 'linked':
            violations = list(lint(binary, TC, env))
            if violations:
                state = 'lint failure'
                diagnostic += '\n' + '\n'.join(map(str, violations))
        if state != 'linked':
            binary.unlink(missing_ok=True)
            (out / (source.stem + '.log')).write_text(diagnostic)
        return source.name, program, state

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(compile_one, sorted(corpus.glob('*.c'))))
    (out / 'compile.tsv').write_text('source\tprogram\tresult\n' + ''.join(
        '\t'.join(row) + '\n' for row in rows))
    linked = [row for row in rows if row[2] == 'linked']
    (out / 'claude-torture.list').write_text(''.join(p + ' ' + s + '\n' for s, p, _ in linked))
    driver = out / 'claude-torture.mic'
    subprocess.run([*cc, str(ROOT / 'tools/claude-torture.c'), '-o', str(driver)],
                   env=env, check=True)
    assert not list(lint(driver, TC, env)), 'driver lint failure'
    previous = SHARED / 'tmp/suite-S3-14/build.tsv'
    with previous.open() as f:
        baseline = {r['source']: r['result'] for r in csv.DictReader(f, delimiter='\t')}
    regressions = [s for s, _, state in rows if baseline.get(s) == 'linked' and state != 'linked']
    print('Execute compile/link/lint:', dict(Counter(row[2] for row in rows)))
    print('New failures versus retained S3-14 execute baseline:', regressions)
    print('Native execution pending lead:', driver, '-j 30 --limit-mb 128 claude-torture.list')
    return int(bool(regressions) or any(state in ('ICE', 'lint failure') for _, _, state in rows))


if __name__ == '__main__':
    sys.exit(main())
