#!/usr/bin/env python3
"""S1-05: compile, assemble and lint the fork's C torture compile corpus.

One command: python tools/run.py --name S1-05-torture -- python tools/torture_compile.py

The default run writes detailed failures under
.work/_shared/torture-compile and a small tracked classification summary.
This deliberately measures the requested flags, without interpreting dg
directives or changing the language default. compile.exp is a Tcl driver.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import runpy
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build/gcc'
CORPUS = SHARED / 'gcc/gcc/testsuite/gcc.c-torture/compile'
LEVELS = {'O0': ['-O0'], 'O2': ['-O2'], 'O2-g': ['-O2', '-g']}
CLASSES = ('pass', 'slow', 'hang', 'ICE', 'compiler error', 'float/double ABI error',
           'assembler rejection', 'lint failure', 'infrastructure failure')


class CompilerHang(Exception):
    pass


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        cygpath = str(TC / 'cygwin/bin/cygpath.exe')
        arguments = sys.argv[1:]
        for flag in ('--source', '--output', '--summary'):
            if flag in arguments:
                index = arguments.index(flag) + 1
                arguments[index] = subprocess.check_output(
                    [cygpath, '-u', arguments[index]], env=env, text=True).strip()
        script = subprocess.check_output([cygpath, '-u', str(Path(__file__).resolve())],
                                         env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script,
                                *arguments], env=env)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='one reduced case instead of the corpus')
    parser.add_argument('--level', choices=tuple(LEVELS), action='append')
    parser.add_argument('--jobs', type=int, default=8, choices=range(1, 9))
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--retry-timeout', type=float, default=600)
    parser.add_argument('--output', type=Path, default=SHARED / 'torture-compile')
    parser.add_argument('--summary', type=Path,
                        default=ROOT / 'tests/baseline/gcc16-torture-compile.txt')
    args = parser.parse_args()
    env = os.environ.copy()
    env['PATH'] = ':'.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + ':' + env.get('PATH', '')
    env['TMPDIR'] = str(SHARED / 'tmp')
    env['LC_ALL'] = 'C'
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))
    sources = [args.source.resolve()] if args.source else sorted(CORPUS.rglob('*.c'))
    if not sources:
        raise RuntimeError('empty torture corpus')
    levels = args.level or list(LEVELS)
    args.output.mkdir(parents=True, exist_ok=True)

    def run(command, timeout):
        # Kill the driver and cc1 together; a timed-out driver must not leave
        # the compiler consuming resources during its retry or the next run.
        with subprocess.Popen(list(map(str, command)), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors='replace', start_new_session=True) as process:
            try:
                output, _ = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise
            return subprocess.CompletedProcess(command, process.returncode, output)

    def measure(job):
        source, level = job
        name = source.name if args.source else source.relative_to(CORPUS).as_posix()
        base = args.output / level / name
        base.parent.mkdir(parents=True, exist_ok=True)
        asm, obj, log = [Path(str(base) + suffix) for suffix in ('.s', '.o', '.log')]
        for path in (asm, obj, log):
            path.unlink(missing_ok=True)
        diagnostic = []
        retried = False
        started = time.monotonic()

        def invoke(command, compiler=False):
            nonlocal retried
            diagnostic.append('+ ' + ' '.join(map(str, command)))
            try:
                result = run(command, args.timeout)
            except subprocess.TimeoutExpired:
                if not compiler:
                    raise
                retried = True
                diagnostic.append('compile timed out after %.3fs; retry once at %.3fs' %
                                  (args.timeout, args.retry_timeout))
                try:
                    result = run(command, args.retry_timeout)
                except subprocess.TimeoutExpired:
                    raise CompilerHang('compile exceeded both %.3fs and %.3fs' %
                                       (args.timeout, args.retry_timeout))
            diagnostic.append(result.stdout)
            return result

        kind = 'infrastructure failure'
        try:
            result = invoke([BUILD / 'xgcc', '-B' + str(BUILD) + '/', '-march=knc',
                             *LEVELS[level], '-S', source, '-o', asm], compiler=True)
            if result.returncode:
                if 'internal compiler error:' in result.stdout:
                    kind = 'ICE'
                else:
                    errors = re.findall(r'\berror: ([^\n]+)', result.stdout)
                    fp_abi = r'SSE register (?:return|argument) with SSE disabled'
                    kind = ('float/double ABI error' if errors and
                            all(re.fullmatch(fp_abi, e.strip()) for e in errors)
                            else 'compiler error')
            else:
                violations = list(lint['source_violations'](asm))
                assembled = invoke([TC / 'cross/bin/k1om-mpss-linux-as',
                                    '--march=k1om', asm, '-o', obj])
                if assembled.returncode:
                    kind = 'assembler rejection'
                else:
                    violations.extend(lint['decoded_violations'](
                        obj, TC / 'cross/bin/k1om-mpss-linux-objdump', env))
                    kind = 'lint failure' if violations else 'pass'
                for violation in violations:
                    diagnostic.append('%s:%s:%s: forbidden: %s' % violation)
            if retried and kind == 'pass':
                kind = 'slow'
        except CompilerHang as error:
            diagnostic.append('hang: ' + str(error))
            kind = 'hang'
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            diagnostic.append('infrastructure failure: ' + str(error))
            kind = 'infrastructure failure'
        seconds = time.monotonic() - started
        if retried:
            diagnostic.append('elapsed including initial timeout and retry: %.3fs' % seconds)
        if kind != 'pass':
            log.write_text('\n'.join(diagnostic), encoding='utf8')
        if kind not in ('assembler rejection', 'lint failure', 'ICE'):
            asm.unlink(missing_ok=True)
        if kind != 'lint failure':
            obj.unlink(missing_ok=True)
        return level, kind, name, seconds if retried else None

    start = time.monotonic()
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for number, result in enumerate(pool.map(measure, ((s, l) for l in levels for s in sources)), 1):
            results.append(result)
            if number % 250 == 0:
                print('measured %d/%d' % (number, len(sources) * len(levels)), flush=True)
    elapsed = time.monotonic() - start
    counts = Counter((level, kind) for level, kind, _, _ in results)
    lines = ['GCC 16 KNC C torture compile corpus (S1-05)',
             'Scope: ' + (str(args.source) if args.source else 'gcc/testsuite/gcc.c-torture/compile/**/*.c'),
             'Raw compile corpus; dg options/skips are not applied; compiler language default retained.',
             'Flags: -march=knc -S, plus each level below.',
             'Assembler: binutils 2.22, --march=k1om.',
             'Lint: tools/knc_lint source checks and decoded object checks after successful assembly.',
             'Classes are exclusive: compiler failure, then assembler rejection, then lint failure.',
             'FP ABI class requires every compiler error to be the explicit SSE-disabled ABI diagnostic.',
             'Timeout policy: %.0fs, then one %.0fs compiler retry; both exceeded = hang.' %
             (args.timeout, args.retry_timeout),
             'Slow = retry completed and assembly/lint passed; other retry outcomes keep their failure class.',
             'Whole-run wall time: %.3f seconds (%.3f minutes), %d workers.' %
             (elapsed, elapsed / 60, args.jobs),
             'Files: %d; measurements: %d.' % (len(sources), len(results)), '',
             'level\t' + '\t'.join(CLASSES)]
    for level in levels:
        lines.append(level + '\t' + '\t'.join(str(counts[level, kind]) for kind in CLASSES))
    for level in levels:
        for kind in CLASSES[1:]:
            names = sorted(name + ('\t%.3fs including timeout/retry' % seconds if seconds is not None else '')
                           for lev, cls, name, seconds in results if lev == level and cls == kind)
            lines.extend(['', '%s / %s (%d)' % (level, kind, len(names)), *names])
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text('\n'.join(lines) + '\n', encoding='utf8')
    print('\n'.join(lines[:len(levels) + 14]), flush=True)
    print('Summary: ' + str(args.summary), flush=True)
    print('Detailed failures: ' + str(args.output), flush=True)
    return int(any(counts[level, kind] for level in levels for kind in
                   ('hang', 'ICE', 'assembler rejection', 'lint failure', 'infrastructure failure')))


if __name__ == '__main__':
    sys.exit(main())
