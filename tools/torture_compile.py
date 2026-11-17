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
CORPUS = Path(storage.gcc_tree(PROJECT)) / 'gcc/testsuite/gcc.c-torture/compile'
LEVELS = {'O0': ['-O0'], 'O2': ['-O2'], 'O2-g': ['-O2', '-g'], 'O3': ['-O3']}
CLASSES = ('pass', 'slow', 'hang', 'ICE', 'compiler error', 'float/double ABI error',
           'assembler rejection', 'lint failure', 'infrastructure failure',
           'user inline asm rejected', 'link failure')
SUITES = {'compile': 'gcc.c-torture/compile', 'execute': 'gcc.c-torture/execute',
          'vect': 'gcc.dg/vect', 'builtins': 'gcc.c-torture/execute/builtins'}


def suite_sources(testsuite, suites):
    return [(source, source.relative_to(testsuite).as_posix())
            for suite in suites for source in sorted((testsuite / SUITES[suite]).rglob('*.c'))
            if 'builtins' not in source.relative_to(testsuite).parts or
            (source.parent.name == 'builtins' and not source.stem.endswith('-lib'))]


def builtin_harness(source):
    """Model builtins.exp; companions include their required lib/*.c support."""
    if source.parent.name != 'builtins':
        return [], []
    return [source.with_name(source.stem + '-lib.c'), source.parent / 'lib/main.c'], [
        '-fno-tree-dse', '-fno-tree-loop-distribute-patterns', '-fno-tracer',
        '-fno-ipa-ra', '-fno-inline-functions']


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
        for flag in ('--source', '--output', '--summary', '--cc'):
            if flag in arguments:
                index = arguments.index(flag) + 1
                arguments[index] = subprocess.check_output(
                    [cygpath, '-u', arguments[index]], env=env, text=True).strip()
        script = subprocess.check_output([cygpath, '-u', str(Path(__file__).resolve())],
                                         env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script,
                                *arguments], env=env)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', type=Path, help='installed compiler, without a build-tree -B')
    parser.add_argument('--source', type=Path, help='one reduced case instead of the corpus')
    parser.add_argument('--suite', action='append', choices=SUITES)
    parser.add_argument('--stage-execute', action='store_true',
                        help='link and lint successful O3 execute objects; never run them')
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
    entries = ([(args.source.resolve(), args.source.name)] if args.source else
               suite_sources(CORPUS.parents[1], args.suite) if args.suite else
               [(s, s.relative_to(CORPUS).as_posix()) for s in sorted(CORPUS.rglob('*.c'))])
    sources = [source for source, _ in entries]
    names = dict(entries)
    if not sources:
        raise RuntimeError('empty torture corpus')
    options = {
        source: [flag for match in re.finditer(
            r'\{\s*dg-(?:additional-)?options\s+(?:"((?:\\.|[^"\\])*)"|([^\s{}]+))'
            r'(\s*\{\s*target\b)?',
            source.read_text(encoding='utf8', errors='replace'))
                 if match[3] is None
                 for flag in shlex.split(match[1] if match[1] is not None else match[2])]
        for source in sources
    }
    for source in sources:
        options[source].extend(builtin_harness(source)[1])
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
        name = names[source]
        base = args.output / level / name
        base.parent.mkdir(parents=True, exist_ok=True)
        asm, obj, log = [Path(str(base) + suffix) for suffix in ('.s', '.o', '.log')]
        binary = args.output / 'card' / ('claude-t-' + name.replace('/', '__') + '.mic')
        stage = (args.stage_execute and level == 'O3' and
                 name.startswith('gcc.c-torture/execute/'))
        if stage:
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.unlink(missing_ok=True)
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
        artifacts = []
        violations = []
        try:
            cc = [args.cc] if args.cc else [BUILD / 'xgcc', '-B' + str(BUILD) + '/']
            objects = []
            artifacts = []
            for index, unit in enumerate([source, *builtin_harness(source)[0]]):
                asm, obj = [Path(str(base) + '.unit%d' % index + suffix)
                            for suffix in ('.s', '.o')]
                artifacts.extend([asm, obj])
                result = invoke([*cc, *options[source], '-march=knc',
                                 *LEVELS[level], '-S', unit, '-o', asm],
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
                if kind != 'pass':
                    break
                objects.append(obj)
            if kind == 'pass' and stage:
                linked = invoke([*cc, '-march=knc', *LEVELS[level], *objects,
                                 '-lm', '-o', binary])
                if linked.returncode:
                    kind = 'link failure'
                else:
                    violations.extend(lint['lint'](binary, TC, env))
                    if violations:
                        kind = 'lint failure'
                if kind != 'pass':
                    binary.unlink(missing_ok=True)
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
        for artifact in artifacts:
            if kind == 'pass' or (artifact.suffix == '.o' and kind != 'lint failure'):
                artifact.unlink(missing_ok=True)
        return level, kind, name, seconds if retried else None

    start = time.monotonic()
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for number, result in enumerate(pool.map(measure, ((s, l) for l in levels for s in sources)), 1):
            results.append(result)
            if number % 250 == 0:
                print('measured %d/%d' % (number, len(sources) * len(levels)), flush=True)
    elapsed = time.monotonic() - start
    if args.stage_execute:
        card = args.output / 'card'
        card.mkdir(parents=True, exist_ok=True)
        binaries = sorted(card.glob('claude-t-*.mic'))
        listing = card / 'claude-torture.list'
        listing.write_text(''.join(p.name + ' ' + p.name[9:-4] + '\n' for p in binaries))
        driver = card / 'claude-torture.mic'
        cc = [args.cc] if args.cc else [BUILD / 'xgcc', '-B' + str(BUILD) + '/']
        if not driver.exists():
            result = run([*cc, '-march=knc', '-O2', ROOT / 'tools/claude-torture.c',
                          '-o', driver], args.timeout)
            (card / 'driver.log').write_text(result.stdout)
            if result.returncode or list(lint['lint'](driver, TC, env)):
                raise RuntimeError('driver build/lint failed; see ' + str(card / 'driver.log'))
        (card / 'card-files.list').write_text(''.join(
            p.relative_to(PROJECT).as_posix() + '\n' for p in [listing, *binaries]))
        print('Staged %d execute binaries; native execution NOT RUN.' % len(binaries), flush=True)
    counts = Counter((level, kind) for level, kind, _, _ in results)
    counts.update((level, 'slow') for level, kind, _, seconds in results
                  if seconds is not None and kind not in ('hang', 'infrastructure failure'))
    lines = ['GCC 16 KNC C torture compile corpus (S1-05)',
             'Scope: ' + (str(args.source) if args.source else ', '.join(args.suite or ['compile'])),
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
                   ('hang', 'ICE', 'assembler rejection', 'lint failure', 'infrastructure failure', 'link failure')))


if __name__ == '__main__':
    sys.exit(main())
