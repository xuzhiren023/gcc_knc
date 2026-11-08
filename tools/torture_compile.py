#!/usr/bin/env python3
"""S1-05: compile, assemble and lint the fork's C torture compile corpus.

One command: python tools/run.py --name S1-05-torture -- python tools/torture_compile.py

The default run writes detailed failures under
.work/_shared/torture-compile and a small tracked classification summary.
Append unselected dg-options and dg-additional-options in source order.
Option directives with a target selector are skipped; other dg directives are ignored.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import runpy
import shlex
import signal
import subprocess
import sys
import time

import storage

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
BUILD = Path(storage.gcc_build_dir(PROJECT)) / 'gcc'
CORPUS = SHARED / 'gcc/gcc/testsuite/gcc.c-torture/compile'
LEVELS = {'O0': ['-O0'], 'O2': ['-O2'], 'O2-g': ['-O2', '-g'], 'O3': ['-O3']}
CLASSES = ('pass', 'slow', 'hang', 'ICE', 'compiler error', 'float/double ABI error',
           'assembler rejection', 'lint failure', 'infrastructure failure',
           'user inline asm rejected')


def user_asm_rejection(asm, diagnostics):
    """Require every as error location to resolve only to #APP block lines.

    GAS reports logical source locations from GCC's # line markers, so track
    those as well as physical assembly locations. Ambiguous/unlocated errors
    remain assembler rejections rather than hiding generated-code failures.
    """
    locations = {}
    inside = False
    filename, number = str(asm), 1
    for physical, line in enumerate(asm.read_text().splitlines(), 1):
        marker = re.fullmatch(r'\s*#\s*(\d+)(?:\s+"([^"]*)")?(?:\s+.*)?', line)
        if marker:
            number = int(marker[1])
            if marker[2] is not None:
                filename = marker[2]
            if not number:
                filename, number = str(asm), physical + 1
            continue
        if line.strip() == '#APP':
            inside = True
        elif line.strip() == '#NO_APP':
            inside = False
        elif line.strip() and not line.lstrip().startswith('#'):
            for location in ((str(asm), physical), (filename, number)):
                locations.setdefault(location, set()).add(inside)
        number += 1
    errors = [line for line in diagnostics.splitlines() if re.search(r'\bError:', line)]
    if not errors:
        return False
    for error in errors:
        match = re.match(r'^(.*):(\d+):\s*(?:Fatal )?Error:', error)
        if not match or locations.get((match[1], int(match[2]))) != {True}:
            return False
    return True


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
    options = {
        source: [flag for match in re.finditer(
            r'\{\s*dg-(?:additional-)?options\s+(?:"([^"\n]*)"|([^\s{}]+))'
            r'(\s*\{\s*target\b)?',
            source.read_text(encoding='utf8', errors='replace'))
                 if match[3] is None
                 for flag in shlex.split(match[1] if match[1] is not None else match[2])]
        for source in sources
    }
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
                             *LEVELS[level], *options[source], '-S', source, '-o', asm],
                            compiler=True)
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
                    kind = ('user inline asm rejected' if user_asm_rejection(asm, assembled.stdout)
                            else 'assembler rejection')
                    if violations:
                        kind = 'lint failure'
                else:
                    violations.extend(lint['decoded_violations'](
                        obj, TC / 'cross/bin/k1om-mpss-linux-objdump', env))
                    kind = 'lint failure' if violations else 'pass'
                for violation in violations:
                    diagnostic.append('%s:%s:%s: forbidden: %s' % violation)
        except CompilerHang as error:
            diagnostic.append('hang: ' + str(error))
            kind = 'hang'
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            diagnostic.append('infrastructure failure: ' + str(error))
            kind = 'infrastructure failure'
        seconds = time.monotonic() - started
        if retried:
            diagnostic.append('elapsed including initial timeout and retry: %.3fs' % seconds)
        if kind != 'pass' or retried:
            log.write_text('\n'.join(diagnostic), encoding='utf8')
        if kind not in ('assembler rejection', 'user inline asm rejected', 'lint failure', 'ICE'):
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
    counts.update((level, 'slow') for level, kind, _, seconds in results
                  if seconds is not None and kind not in ('hang', 'infrastructure failure'))
    lines = ['GCC 16 KNC C torture compile corpus (S1-05)',
             'Scope: ' + (str(args.source) if args.source else 'gcc/testsuite/gcc.c-torture/compile/**/*.c'),
             'dg-options and dg-additional-options without target selectors are appended; selected directives are skipped.',
             'Flags: -march=knc -S, plus each level below.',
             'Assembler: binutils 2.22, --march=k1om.',
             'Lint: tools/knc_lint source checks and decoded object checks after successful assembly.',
             'Outcome classes are exclusive: compiler failure, then assembler rejection, then lint failure.',
             'FP ABI class requires every compiler error to be the explicit SSE-disabled ABI diagnostic.',
             'User inline asm rejected requires every assembler error inside #APP/#NO_APP; source lint must be clean.',
             'Timeout policy: %.0fs, then one %.0fs compiler retry; both exceeded = hang.' %
             (args.timeout, args.retry_timeout),
             'Slow is an additional timing class: retry completed; underlying outcome is counted too.',
             'Whole-run wall time: %.3f seconds (%.3f minutes), %d workers.' %
             (elapsed, elapsed / 60, args.jobs),
             'Files: %d; measurements: %d.' % (len(sources), len(results)), '',
             'level\t' + '\t'.join(CLASSES)]
    for level in levels:
        lines.append(level + '\t' + '\t'.join(str(counts[level, kind]) for kind in CLASSES))
    table_end = len(lines)
    for level in levels:
        for kind in CLASSES[1:]:
            names = sorted(name + ('\t%.3fs including timeout/retry' % seconds if seconds is not None else '') +
                           ('; reason: every assembler error is inside #APP/#NO_APP' if
                            kind == 'user inline asm rejected' else '') +
                           ('; outcome: ' + cls if kind == 'slow' else '')
                           for lev, cls, name, seconds in results if lev == level and
                           (cls == kind or (kind == 'slow' and seconds is not None and
                                            cls not in ('hang', 'infrastructure failure'))))
            lines.extend(['', '%s / %s (%d)' % (level, kind, len(names)), *names])
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text('\n'.join(lines) + '\n', encoding='utf8')
    print('\n'.join(lines[:table_end]), flush=True)
    print('Summary: ' + str(args.summary), flush=True)
    print('Detailed failures: ' + str(args.output), flush=True)
    return int(any(counts[level, kind] for level in levels for kind in
                   ('hang', 'ICE', 'assembler rejection', 'lint failure', 'infrastructure failure')))


if __name__ == '__main__':
    sys.exit(main())
