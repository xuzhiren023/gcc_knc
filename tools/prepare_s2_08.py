"""S2-08 host-only batch preparation; invoke through tools/run.py.

No card access. The lead runs donor twins first to establish native references.
Large artifacts stay in the single shared tmp/S2-08 directory.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build/gcc'
OUT = SHARED / 'tmp/S2-08'


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__).resolve())], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script,
                                *sys.argv[1:]], env=env)
    os.environ['PATH'] = ':'.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    os.environ['LC_ALL'] = 'C'
    OUT.mkdir(exist_ok=True)
    cc = [BUILD / 'xgcc', '-B' + str(BUILD) + '/']
    donor = [TC / 'cross/bin/k1om-mpss-linux-gcc']
    host = [TC / 'cygwin/bin/gcc']
    flags = ['-O2', '-march=knc', '-ffp-contract=off']
    # Review changes affect only scalar-fp and the driver's link. Reuse the
    # already passing programs and torture compile summary in this mode.
    refresh = '--refresh-affected' in sys.argv

    def run(args, check=True):
        args = list(map(str, args))
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors='replace')
        print('+ ' + shlex.join(args), flush=True)
        if result.stdout:
            print(result.stdout, end='', flush=True)
        if check and result.returncode:
            raise RuntimeError('command exit ' + str(result.returncode))
        return result

    if '--torture-only' not in sys.argv:
        # Assert the actual driver-selected runtime, with no donor -B or scripts.
        runtime = run([*cc, '-print-libgcc-file-name']).stdout.strip()
        if Path(runtime).resolve() != (BUILD / 'libgcc.a').resolve():
            raise RuntimeError('GCC 16 did not select its own libgcc: ' + runtime)
        sources = {
            'hello': '#include <stdio.h>\nint main(void){return puts("hello from KNC")<0;}\n',
            'scalar-fp': '''#include <stdio.h>
int main(void) {
  volatile float f = 1.5f, g = 2.0f;
  volatile double d = 7.5, e = 2.0;
  volatile long double x = 3.125L, y = 0.5L;
  float a = (f+g)*g-f/g;
  double b = (d-e)*e+d/e;
  long double c = (x+y)*y-x/y;
  volatile float third_f = g / (g+4.0f);
  volatile double third_d = e / (e+4.0);
  volatile long double third_l = y / (y+1.0L);
  printf("scalar %.6f %.6f %.6Lf\\n", (double)a, b, c);
  printf("thirds %.9g %.17g %.21Lg\\n", (double)third_f, third_d, third_l);
  return a != 6.25f || b != 14.75 || c != -4.4375L;
}
''',
            'printf': '''#include <stdio.h>
int main(void) {
  volatile int i = -17;
  volatile double d = 2.5;
  volatile long double x = 3.125L;
  return printf("printf %d|%.3f|%.4Lf\\n", i, d, x) < 0;
}
'''}
        rows = []
        for name, text in sources.items():
            source = OUT / (name + '.c')
            if ('--resume-after-compare-link' not in sys.argv
                    and (not refresh or name == 'scalar-fp')):
                source.write_text(text)
                for tag, compiler in (('donor-', donor), ('', cc)):
                    run([*compiler, *flags, '-fno-builtin', source,
                         '-o', OUT / (tag + name + '.mic')])
                # Provisional until the lead runs the donor twins.
                exe = OUT / (name + '-host.exe')
                run([*host, '-O2', '-ffp-contract=off', '-fno-builtin', source, '-o', exe])
                result = run([exe])
                (OUT / (name + '.expected.txt')).write_text(result.stdout)
                exe.unlink()
            for prefix in ('donor-', ''):
                expected = prefix + name + '.expected.txt'
                if prefix:
                    (OUT / expected).write_bytes((OUT / (name + '.expected.txt')).read_bytes())
                rows.append((prefix + name + '.mic', '[]', '128', expected))
        for name, source, extra in (
                ('compare', ROOT / 'tests/t1/knc-x87-compare.c', ['-DCOMPARE_MAIN']),
                ('libgcc', ROOT / 'tests/t2/knc-libgcc.c', ['-fno-builtin'])):
            if refresh:
                rows.append((name + '.mic', '[]', '128', name + '.expected.txt'))
                continue
            if name != 'compare' or '--resume-after-compare-link' not in sys.argv:
                run([*cc, *flags, *extra, source, '-o', OUT / (name + '.mic')])
            exe = OUT / (name + '-host.exe')
            if name == 'compare':
                # S2-05's adapter avoids Cygwin GCC's mixed-ABI definition ICE.
                asm = OUT / 'compare-functions.s'
                run([*cc, *flags, '-S', source, '-o', asm])
                lines = []
                for line in asm.read_text().splitlines():
                    if re.match(r'\s*\.(?:type|size)\b|\s*\.section\s+\.note\.GNU-stack', line):
                        continue
                    lines.append('\t.text' if re.match(r'\s*\.section\s+\.text\b', line) else line)
                adapter = OUT / 'compare-host.s'
                adapter.write_text('\n'.join(lines) + '\n')
                run([*host, '-O2', '-DCOMPARE_DRIVER', source, adapter, '-o', exe])
            else:
                run([*host, '-O2', '-ffp-contract=off', *extra, source, '-o', exe])
            result = run([exe])
            (OUT / (name + '.expected.txt')).write_text(result.stdout)
            exe.unlink()
            rows.append((name + '.mic', '[]', '128', name + '.expected.txt'))
        run([*cc, *flags, ROOT / 'tools/claude-torture.c',
             '-o', OUT / 'claude-torture'])
        elf = run([TC / 'cross/bin/k1om-mpss-linux-readelf', '-l', '-d',
                   OUT / 'claude-torture']).stdout
        if 'INTERP' not in elf or '(NEEDED)' not in elf or 'libc.so.6' not in elf:
            raise RuntimeError('driver must use the shared sysroot dynamic glibc')
        header = '# S2-10 format; paths relative to batch.txt; memory in MiB.\n'
        header += '# Run donor twins first; host oracles await donor confirmation.\n'
        header += 'program\targuments\tmemoryMB\texpected\n'
        (OUT / 'batch.txt').write_text(header + ''.join('\t'.join(row) + '\n' for row in rows))

    corpus = SHARED / 'gcc/gcc/testsuite/gcc.c-torture/execute'
    selected = sorted(corpus.glob('*.c'))[:256]
    if len(selected) != 256:
        raise RuntimeError('expected at least 256 execute sources')

    def bounded(args):
        with subprocess.Popen(list(map(str, args)), stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, errors='replace',
                              start_new_session=True) as process:
            try:
                output, _ = process.communicate(timeout=60)
                return process.returncode, output
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                output, _ = process.communicate()
                return 124, output + '\nHOST COMPILE TIMEOUT\n'

    def build(source):
        extra = [flag for match in re.finditer(
            r'\{\s*dg-(?:additional-)?options\s+(?:"([^"\n]*)"|([^\s{}]+))'
            r'(\s*\{\s*target\b)?', source.read_text(errors='replace'))
                 if match[3] is None
                 for flag in shlex.split(match[1] if match[1] is not None else match[2])]
        obj = OUT / (source.stem + '.o')
        binary = OUT / ('claude-t-' + source.stem + '.mic')
        compile_args = [*cc, '-O2', '-march=knc', *extra, '-c', source, '-o', obj]
        code, output = bounded(compile_args)
        state = 'compile timeout' if code == 124 else 'compile failure' if code else 'linked'
        log = '+ ' + shlex.join(map(str, compile_args)) + '\n' + output
        if not code:
            link_args = [*cc, '-O2', '-march=knc', obj, '-lm', '-o', binary]
            code, output = bounded(link_args)
            log += '+ ' + shlex.join(map(str, link_args)) + '\n' + output
            if code:
                state = 'link timeout' if code == 124 else 'link failure'
        (OUT / (source.stem + '.build.log')).write_text(log)
        obj.unlink(missing_ok=True)
        if state != 'linked':
            binary.unlink(missing_ok=True)
        else:
            binary.chmod(0o700)
        return source.name, state, binary.name, shlex.join(extra)

    if refresh:
        results = [tuple(line.split('\t')) for line in
                   (OUT / 'compile.tsv').read_text().splitlines()[1:]]
    else:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(build, selected))
    counts = Counter(row[1] for row in results)
    linked = [(name, binary) for name, state, binary, _ in results if state == 'linked']
    (OUT / 'compile.tsv').write_text('source\tresult\tprogram\tdg-options\n' + ''.join(
        '\t'.join(row) + '\n' for row in results))
    (OUT / 'claude-torture.list').write_text(''.join(binary + ' ' + name + '\n' for name, binary in linked))
    (OUT / 'torture.expected.txt').write_text(''.join('PASS ' + name + '\n' for name, _ in linked))
    files = [OUT / 'claude-torture.list', *(OUT / binary for _, binary in linked)]
    config = json.loads((PROJECT / 'config/card.local.json').read_text())
    helper = Path(config.get('pinHelper', str(SHARED / 'claude-pin.mic')))
    if not helper.is_absolute():
        helper = PROJECT / helper
    # Reserve 64 KiB beyond payload for the runner's watchdog script.
    size = sum(path.stat().st_size for path in [OUT / 'claude-torture', helper, *files]) + 65536
    cap = config.get('maxStageMiB', 64) * 1024 * 1024
    if size >= cap:
        raise RuntimeError('staging exceeds cap: %d >= %d' % (size, cap))
    command = ['python', 'tools/card_run', '--timeout', str(2 * len(linked) + 30),
               '--transport-timeout', '900']
    for path in files:
        command.extend(['--file', str(path)])
    command.extend([str(OUT / 'claude-torture'), 'claude-torture.list'])
    (OUT / 'run-torture.sh').write_text('# Lead only; run from the merged checkout, under Cygwin.\n' +
                                       shlex.join(command) + '\n')
    batch = OUT / 'batch.txt'
    text = batch.read_text()
    text = '\n'.join(line for line in text.splitlines() if not line.startswith('claude-torture\t')) + '\n'
    text += 'claude-torture\t["claude-torture.list"]\t128\ttorture.expected.txt\n'
    batch.write_text(text)
    summary = ['S2-08 first execute subset: GCC 16 -O2 -march=knc',
               'Selection: first 256 top-level *.c in lexical filename order, before compilation.',
               'Unselected dg-options/dg-additional-options applied as in S1-05; other dg directives ignored.',
               'Link flags: -lm, GCC 16 own static libgcc; no donor -B or generated linker scripts.',
               'Counts: ' + ', '.join('%s=%d' % item for item in sorted(counts.items())),
               'Stage bytes including helper and 64 KiB watchdog reserve: %d / %d' % (size, cap),
               'Complete per-source compile/link results: .work/_shared/tmp/S2-08/compile.tsv',
               'Diagnostics: same directory, <source-stem>.build.log',
               'Native results: NOT RUN; lead runs run-torture.sh (all --file arguments included).',
               '', 'Nonlinked files:']
    summary.extend(name + ': ' + state for name, state, _, _ in results if state != 'linked')
    (ROOT / 'tests/baseline/gcc16-torture-execute.txt').write_text('\n'.join(summary) + '\n')
    print('\n'.join(summary[:9]), flush=True)
    print('READY ' + str(OUT / 'batch.txt'), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
