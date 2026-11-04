"""Prepare S3-10 on the host; invoke through tools/run.py. Never access the card."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build/gcc'
OUT = SHARED / 'tmp/S3-10'
OPTIONS = re.compile(r'\{\s*dg-(?:additional-)?options\s+(?:"([^"\n]*)"|\{([^{}\n]*)\}|([^\s{}]+))'
                     r'(\s*\{\s*target\b)?')


def run(args, check=True):
    args = list(map(str, args))
    print('+ ' + shlex.join(args), flush=True)
    result = subprocess.run(args, capture_output=True, text=True, errors='replace', timeout=300)
    if result.stdout:
        print(result.stdout, end='', flush=True)
    if result.stderr:
        print(result.stderr, end='', flush=True)
    if check and result.returncode:
        raise RuntimeError('command exit %d' % result.returncode)
    return result


def permissions():
    files = [p for p in OUT.iterdir() if p.is_file()]
    if sys.platform == 'cygwin':
        # Match S2-08: inherited ACL entries otherwise hide artifacts from the lead.
        for start in range(0, len(files), 100):
            subprocess.run([str(TC / 'cygwin/bin/setfacl'), '-b', '--',
                            *map(str, files[start:start + 100])], check=True)
    for path in files:
        path.chmod(0o755 if path.suffix == '.mic' or path.name == 'claude-torture' else 0o644)


def main():
    if os.name == 'nt':
        env = dict(os.environ)
        env['PATH'] = os.pathsep.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
    os.environ['PATH'] = ':'.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    os.environ['LC_ALL'] = 'C'
    OUT.mkdir(exist_ok=True)
    branch = run(['git', '-C', SHARED / 'gcc', 'branch', '--show-current']).stdout.strip()
    assert branch == 'knc', 'the shared compiler must be the merged knc branch'
    commit = run(['git', '-C', SHARED / 'gcc', 'rev-parse', 'HEAD']).stdout.strip()
    cc = [BUILD / 'xgcc', '-B' + str(BUILD) + '/', '-march=knc']
    donor = [TC / 'cross/bin/k1om-mpss-linux-gcc', '-march=knc']
    host = [TC / 'cygwin/bin/gcc']
    assert Path(run([*cc, '-print-libgcc-file-name']).stdout.strip()).resolve() == (BUILD / 'libgcc.a').resolve()
    rows = []

    def row(name, expected=None, arguments=(), memory=128):
        expected_file = name.removesuffix('.mic') + '.expected.txt'
        if expected is not None:
            (OUT / expected_file).write_text(expected)
        rows.append((name, json.dumps(list(arguments)), str(memory), expected_file))

    fixture = ROOT / 'tests/acceptance/m1_affine'
    exact = ['-O2', '-ftree-vectorize', '-ffp-contract=off']
    loops = OUT / 'loops.o'
    run([*cc, *exact, '-c', fixture / 'loops.c', '-o', loops])
    for tag, compiler, fortran in (('claude-m1', cc, False), ('claude-m1-donor', donor, False),
                                    ('claude-m1-fortran', cc, True)):
        objects = [loops]
        if fortran:
            obj = OUT / 'fortran.o'
            run([BUILD / 'gfortran', '-B' + str(BUILD) + '/', '-march=knc', *exact,
                 '-c', fixture / 'affine_fortran.f90', '-o', obj])
            objects.append(obj)
        driver = OUT / (tag + '.o')
        run([*compiler, *exact, *(['-DKNC_WITH_FORTRAN'] if fortran else []),
             '-c', fixture / 'driver.c', '-o', driver])
        run([*cc, driver, *objects, '-o', OUT / (tag + '.mic')])
        row(tag + '.mic', 'ACCEPT-PASS scalar=3.00 failures=0\n')

    vectors = ROOT / 'tests/acceptance/s3_vec_card'
    for opt in (0, 2):
        for name, source, expected in (
                ('vec', 'vec_card.c', 'expected.txt'),
                ('fp', 'fp_card.c', 'expected-fp-O%d.txt' % opt),
                ('special', 'fp_special.c', None)):
            program = 'claude-%s-O%d.mic' % (name, opt)
            run([*cc, '-O%d' % opt, vectors / source, '-lm', '-o', OUT / program])
            if expected:
                text = (vectors / expected).read_text()
            else:
                exe = OUT / 'reference.exe'
                run([*host, '-O%d' % opt, vectors / source, '-lm', '-o', exe])
                reference = run([exe]).stdout
                text = '\n'.join(line for line in reference.splitlines() if not line.startswith('INFO ')) + '\n'
                exe.unlink()
            row(program, text)

    abi = ROOT / 'tests/t2'
    abi_flags = ['-ffp-contract=off', '-frounding-math', '-fexcess-precision=standard']
    exe = OUT / 'reference.exe'
    run([*host, '-O2', *abi_flags, abi / 'knc-abi-gaps-caller.c',
         abi / 'knc-abi-gaps-callee.c', '-lm', '-o', exe])
    reference = run([exe]).stdout
    exe.unlink()
    for opt in (0, 2):
        for reverse in (0, 1):
            objects = []
            for role in ('caller', 'callee'):
                compiler = donor if (role == 'caller') == bool(reverse) else cc
                obj = OUT / (role + '.o')
                run([*compiler, '-O%d' % opt, *abi_flags, '-c',
                     abi / ('knc-abi-gaps-' + role + '.c'), '-o', obj])
                objects.append(obj)
            program = 'claude-abi-O%d-%d.mic' % (opt, reverse)
            run([*cc, *objects, '-lm', '-o', OUT / program])
            row(program, reference)

    # Default contraction in the loop TU; reference precision in its own TU.
    run([*cc, '-O2', '-ftree-vectorize', '-c', fixture / 'loops.c', '-o', loops])
    source = ROOT / 'tests/regress/knc-affine-inexact.c'
    obj = OUT / 'inexact.o'
    run([*cc, '-O0', '-I' + str(fixture), '-c', source, '-o', obj])
    run([*cc, obj, loops, '-o', OUT / 'claude-inexact.mic'])
    for bias in (0, 1):
        run([*host, '-O0', '-DCONTROL_BIAS=%d' % bias, '-I' + str(fixture),
             source, fixture / 'loops.c', '-o', exe])
        result = run([exe], check=not bias)
        if bias:
            assert result.returncode != 0 and 'loop-ulp=' in result.stdout, '1 ULP guard cannot fail'
        else:
            row('claude-inexact.mic', '\n'.join(line for line in result.stdout.splitlines()
                                               if not line.startswith('INFO ')) + '\n')
        exe.unlink()

    run([*cc, '-O2', ROOT / 'tools/claude-torture.c', '-o', OUT / 'claude-torture'])
    corpus = SHARED / 'gcc/gcc/testsuite/gcc.c-torture/execute'
    sources = sorted(corpus.glob('*.c'))
    assert len(sources) == 1692, len(sources)

    def build(source):
        extra = []
        for m in OPTIONS.finditer(source.read_text(errors='replace')):
            if m[4] is None:
                extra.extend(shlex.split(next(g for g in m.groups()[:3] if g is not None)))
        obj = OUT / (source.stem + '.o')
        program = 'claude-t-' + source.stem + '.mic'
        binary = OUT / program
        commands = [[*cc, '-O2', '-w', *extra, '-c', source, '-o', obj],
                    [*cc, '-O2', obj, '-lm', '-o', binary]]
        state, log = 'linked', ''
        for stage, args in zip(('compile', 'link'), commands):
            args = list(map(str, args))
            log += '+ ' + shlex.join(args) + '\n'
            try:
                r = subprocess.run(args, capture_output=True, text=True, errors='replace', timeout=300)
                log += r.stdout + r.stderr
                if r.returncode:
                    state = 'ICE' if 'internal compiler error' in r.stderr else stage + ' error'
                    break
            except subprocess.TimeoutExpired:
                state = stage + ' timeout'
                break
        obj.unlink(missing_ok=True)
        if state != 'linked':
            binary.unlink(missing_ok=True)
            (OUT / (source.stem + '.build.log')).write_text(log)
        return source.name, program, state, shlex.join(extra)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(build, sources))
    (OUT / 'compile.tsv').write_text('source\tprogram\tresult\tdg-options\n' + ''.join(
        '\t'.join(r) + '\n' for r in results))
    linked = [(source, program) for source, program, state, _ in results if state == 'linked']
    (OUT / 'claude-torture.list').write_text(''.join(p + ' ' + s + '\n' for s, p in linked))
    (OUT / 'torture.expected.txt').write_text(''.join('PASS ' + s + '\n' for s, _ in linked))
    row('claude-torture', arguments=['-j', '30', '--limit-mb', '128', 'claude-torture.list'], memory=3840)
    # A single full-suite job fits the staging cap; the lead runner avoids the
    # Windows argv length limit by invoking card_run in its Python process.
    cap = json.loads((PROJECT / 'config/card.local.json').read_text()).get('maxStageMiB', 64) * 2**20
    size = sum((OUT / p).stat().st_size for _, p in linked)
    size += (OUT / 'claude-torture').stat().st_size + (OUT / 'claude-torture.list').stat().st_size + 65536
    assert size < cap, (size, cap)
    header = '# S3-10; merged knc compiler ' + commit + '\n'
    header += '# INFO lines are measurements: retain raw output, omit INFO only for expected comparison.\n'
    header += '# m1: -O2 -ftree-vectorize -ffp-contract=off; inexact loops: default contraction.\n'
    header += '# S3-09 is deferred to Sprint 4. TLS already passed; compiler has no change after S3-15.\n'
    header += '# Native NOT RUN. No full-suite pre-S3-07 native baseline is recorded; S2-08 covers 256.\n'
    header += 'program\targuments\tmemoryMB\texpected\n'
    (OUT / 'batch.txt').write_text(header + ''.join('\t'.join(r) + '\n' for r in rows))
    for path in OUT.glob('*.o'):
        path.unlink()
    permissions()
    print('Torture compile:', dict(Counter(r[2] for r in results)), 'stage bytes', size, '/', cap)
    old = SHARED / 'tmp/suite-S3-14/build.tsv'
    if old.exists():
        previous = {r['source']: r['result'] == 'linked' for r in csv.DictReader(old.open(), delimiter='\t')}
        regressions = [s for s, _, state, _ in results if previous.get(s) and state != 'linked']
        assert not regressions, 'new compile failures versus S3-14: ' + str(regressions)
    # Ensure a concurrent compiler change cannot silently mix this batch.
    assert run(['git', '-C', SHARED / 'gcc', 'rev-parse', 'HEAD']).stdout.strip() == commit
    run([sys.executable, ROOT / 'tests/regress/check_s3_10_batch.py'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
