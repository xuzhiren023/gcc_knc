#!/usr/bin/env python3
"""First KNC gcc.dg/vect/*.c baseline (one non-LTO configuration).

Run through tools/run.py. Outputs overwrite .work/_shared/S6-07.
Target selectors use a deliberately small KNC capability table: unresolved
requirements are recorded as skips, never assumed to be supported. Scans are
counted, not evaluated. No card job is started.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import fnmatch
import os
from pathlib import Path
import re
import runpy
import shlex
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
CORPUS = SHARED / 'gcc/gcc/testsuite/gcc.dg/vect'
DEFAULT = ['-O2', '-ftree-vectorize', '-fno-tree-loop-distribute-patterns',
           '-fno-vect-cost-model', '-fno-common']
# Basic 32-bit integer and FP vectors are implemented by the KNC backend;
# LP64 and these OS facilities are properties of the MPSS target sysroot.
YES = {'vect_int', 'vect_float', 'vect_double', 'lp64', 'int32plus',
       'size32plus', 'size_t32plus', 'ptr32plus', 'mmap', 'signal', 'alarm',
       'posix_memalign', 'sysconf', 'c99_runtime', 'c99_runtime_complex'}
NO = {'ilp32', 'sse', 'sse2', 'sse2_runtime', 'avx', 'avx_runtime',
      'avx2', 'avx2_runtime', 'avx512f', 'avx512f_runtime', 'section_anchors'}


def words(text):
    """Split the braced/quoted Tcl list subset used by dg directives.

    Keep nested list contents intact; escaped quotes/braces do not terminate
    a word. This does not execute Tcl or interpret scan regular expressions.
    """
    result, i = [], 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        start = i
        if text[i] in '{"':
            opening = text[i]
            closing = '}' if opening == '{' else '"'
            i += 1
            start = i
            depth = 1
            quoted = False
            while i < len(text):
                ch = text[i]
                if ch == '\\':
                    i += 2
                    continue
                if opening == '{' and ch == '"':
                    quoted = not quoted
                if not quoted and ch == closing:
                    depth -= 1
                    if depth == 0:
                        break
                elif opening == '{' and not quoted and ch == '{':
                    depth += 1
                i += 1
            if i == len(text):
                raise ValueError('unbalanced directive/list')
            result.append(text[start:i])
            i += 1
        else:
            while i < len(text) and not text[i].isspace():
                i += 1
            result.append(text[start:i])
    return result


def directives(text):
    for match in re.finditer(r'\{\s*(dg-[\w-]+)\b', text):
        # Scan one balanced outer list, respecting quoted scan regexes.
        start, i, depth, quoted = match.start(), match.end(), 1, False
        while i < len(text) and depth:
            ch = text[i]
            if ch == '\\':
                i += 2
                continue
            if ch == '"':
                quoted = not quoted
            elif not quoted:
                depth += (ch == '{') - (ch == '}')
            i += 1
        if depth:
            raise ValueError('unbalanced ' + match[1])
        yield words(text[start + 1:i - 1])


def target(expression):
    """Three-valued selector evaluation; None means capability unverified."""
    parts = words(expression)
    if not parts:
        return None
    if parts[0] == 'target':
        return target(' '.join(parts[1:]))
    if len(parts) == 1:
        atom = parts[0]
        if atom != expression.strip():
            return target(atom)
        if atom in YES:
            return True
        if atom in NO or atom.startswith(('sse', 'avx', 'arm_', 'aarch64', 'riscv', 'powerpc', 's390', 'loongarch')):
            return False
        if '-' in atom and any(ch in atom for ch in '*?'):
            return fnmatch.fnmatchcase('k1om-mpss-linux', atom)
        return None
    if parts[0] == '!':
        value = target(' '.join(parts[1:]))
        return None if value is None else not value
    # Tcl target lists without operators are OR lists; && binds before ||.
    if '||' in parts:
        groups, group = [], []
        for part in parts + ['||']:
            if part == '||':
                groups.append(target(' '.join('{' + p + '}' if ' ' in p else p for p in group)))
                group = []
            else:
                group.append(part)
        return True if True in groups else None if None in groups else False
    if '&&' in parts:
        values = [target(p) for p in parts if p != '&&']
        return False if False in values else None if None in values else True
    values = [target(p) for p in parts]
    return True if True in values else None if None in values else False


@dataclass
class Spec:
    action: str = 'run'  # vect.exp, vector-capable target default
    options: list = field(default_factory=list)
    skip: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    scans: int = 0
    replaces_defaults: bool = False


def parse_directives(text):
    spec = Spec(scans=len(re.findall(r'\bscan-tree-dump(?:-times|-not)?\b', text)))
    ds = list(directives(text))
    do_seen = False
    do_match = False
    for d in ds:
        name, args = d[0], d[1:]
        selectors = [a for a in args if words(a)[:1] == ['target']]
        selected = target(selectors[-1]) if selectors else True
        if selected is not True:
            spec.notes.append(name + ': selector ' + str(selectors) +
                              (' unmet' if selected is False else ' unverified'))
            if name == 'dg-do':
                do_seen = True
            elif selected is None and name in ('dg-options', 'dg-additional-options',
                                               'dg-require-effective-target', 'dg-add-options'):
                spec.skip.append('unverified selector: ' + selectors[-1])
            continue
        if name == 'dg-do':
            do_seen = do_match = True
            spec.action = args[0]
        elif name == 'dg-options':
            spec.options = shlex.split(args[0])
            spec.replaces_defaults = True
        elif name == 'dg-additional-options':
            # Brace-list option payloads sometimes wrap one quoted string.
            payload = words(args[0])
            spec.options.extend(shlex.split(payload[0] if len(payload) == 1 else args[0]))
        elif name == 'dg-require-effective-target':
            value = target(args[0])
            if value is not True:
                spec.skip.append(args[0] + (': unsupported on KNC' if value is False
                                            else ': capability unverified on KNC'))
        elif name == 'dg-add-options':
            # Tcl procedures can inject architecture flags. Never ignore them.
            spec.skip.append('unimplemented option bundle: ' + args[0])
        elif name in ('dg-require-ifunc', 'dg-require-weak', 'dg-require-alias',
                      'dg-require-visibility', 'dg-additional-sources', 'dg-lto-do'):
            spec.skip.append('unimplemented directive: ' + name)
    if do_seen and not do_match:
        spec.skip.append('dg-do: no matching KNC target selector')
    if spec.action not in ('run', 'compile', 'assemble'):
        spec.skip.append('unsupported dg-do action: ' + spec.action)
    for d in ds:
        if d[0] == 'dg-skip-if':
            args = d[1:]
            selected = target(args[1])
            include = words(args[2]) if len(args) > 2 else []
            exclude = words(args[3]) if len(args) > 3 else []
            flags = DEFAULT + spec.options + ['-march=knc']
            matches = lambda patterns: any(fnmatch.fnmatchcase(f, p) for p in patterns if p for f in flags)
            if selected is not False and (not any(include) or matches(include)) and not matches(exclude):
                spec.skip.append('dg-skip-if: ' + args[0] +
                                 (' (target unverified)' if selected is None else ''))
    # Target options must never enable a foreign ISA or replace KNC's ABI.
    foreign = [f for f in spec.options if f.startswith('-m') and
               f not in ('-march=knc', '-mtune=knc')]
    if foreign:
        spec.skip.append('non-KNC machine options: ' + ' '.join(foreign))
    return spec


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, choices=range(1, 9), default=8)
    parser.add_argument('--stage-only', action='store_true',
                        help='finish driver/pack staging from the recorded baseline without recompiling tests')
    args = parser.parse_args()
    out = SHARED / 'S6-07'
    out.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['PATH'] = ':'.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + ':' + env.get('PATH', '')
    env['TMPDIR'] = str(SHARED / 'tmp')
    env['LC_ALL'] = 'C'
    build = SHARED / 'gcc-build/gcc'
    cc = [str(build / 'xgcc.exe'), '-B' + str(build) + '/']
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']

    def invoke(command):
        with subprocess.Popen(list(map(str, command)), env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, errors='replace',
                              start_new_session=True) as proc:
            try:
                output, _ = proc.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                output, _ = proc.communicate()
                return 124, output + '\ncompiler timeout'
        return proc.returncode, output

    # The upstream header tests SSE2 when no SSE macro is set. On KNC that
    # would silently exit(0), skipping every test body. Adapt just this header
    # for the card target; retain the test bodies and all result checks.
    header = (CORPUS / 'tree-vect.h').read_text()
    header = header.replace('#elif defined(__i386__) || defined(__x86_64__)',
                            '#elif defined(__k1om__)\n  /* KNC card selected by the job. */\n'
                            '#elif defined(__i386__) || defined(__x86_64__)')
    (out / 'tree-vect.h').write_text(header)

    def build_one(source):
        text = source.read_text(errors='replace')
        spec = parse_directives(text)
        result, compiled, linked, note = 'skipped', 0, 0, ''
        prog = out / ('claude-t-vect-' + source.stem + '.mic')
        obj = out / (source.stem + '.o')
        asm = out / (source.stem + '.s')
        log = out / (source.stem + '.log')
        staged = out / source.name
        prog.unlink(missing_ok=True)
        if not spec.skip:
            # The copy changes only the header lookup location. Other quoted
            # includes still resolve in the original corpus via -iquote.
            staged.write_text('#line 1 "' + str(source) + '"\n' + text)
            flags = [*(spec.options if spec.replaces_defaults else DEFAULT + spec.options),
                     '-march=knc', '-iquote', str(CORPUS), '-w']
            artifact = asm if spec.action == 'compile' else obj
            command = [*cc, *flags, '-S' if spec.action == 'compile' else '-c', staged, '-o', artifact]
            code, diagnostic = invoke(command)
            log.write_text(shlex.join(map(str, command)) + '\n' + diagnostic)
            if code:
                result = 'ICE' if re.search(r'internal compiler error|segmentation fault', diagnostic, re.I) else 'compile error'
                note = (diagnostic.strip().splitlines() or ['unknown error'])[-1]
            else:
                compiled, result = 1, 'compiled'
                if spec.action == 'run':
                    command = [*cc, *flags, obj, '-lm', '-o', prog]
                    code, diagnostic = invoke(command)
                    with log.open('a') as stream:
                        stream.write(shlex.join(map(str, command)) + '\n' + diagnostic)
                    if code:
                        result = 'ICE' if 'internal compiler error' in diagnostic else 'link error'
                        note = (diagnostic.strip().splitlines() or ['unknown error'])[-1]
                    else:
                        violations = list(lint(prog, TC, env))
                        if violations:
                            result, note = 'lint failure', repr(violations[:3])
                            prog.unlink()
                        else:
                            result, linked = 'linked', 1
            for path in (obj, asm, staged):
                path.unlink(missing_ok=True)
            for path in out.glob(source.stem + '.*t.*'):
                path.unlink()
            for path in out.glob(source.stem + '.*i.*'):
                path.unlink()
        note = '; '.join(spec.skip + spec.notes + ([note] if note else []))
        return source.name, spec.action, result, compiled, linked, spec.scans, note.replace('\t', ' ').replace('\n', ' ')

    sources = sorted(CORPUS.glob('*.c'))
    if not sources:
        raise RuntimeError('empty vect corpus')
    if args.stage_only:
        report = (ROOT / 'tests/baseline/gcc16-vect.txt').read_text()
        rows = []
        for line in report.split('\n\nsource\t', 1)[1].splitlines()[1:]:
            r = line.split('\t')
            rows.append((r[0], r[1], r[2], int(r[3]), int(r[4]), int(r[5]), r[6]))
    else:
        with ThreadPoolExecutor(args.jobs) as pool:
            rows = list(pool.map(build_one, sources))
    counts = Counter(row[2] for row in rows)
    summary = ['KNC GCC 16 gcc.dg/vect/*.c baseline',
               'Configuration: vect.exp defaults, per-test dg options, -march=knc; no LTO variant.',
               'Scans counted only; no scan or native execution verdict.',
               'Unverified effective targets and option bundles conservatively skipped.',
               'tree-vect.h adapted for __k1om__ to avoid the upstream SSE2 early exit.',
               'Run executables linted; list and driver staged for one packed card_run job.',
               'sources: ' + str(len(rows)),
               'compiled (including linked/link failures): ' + str(sum(r[3] for r in rows)),
               'scan-tree-dump directives: ' + str(sum(r[5] for r in rows))]
    summary += [kind + ': ' + str(counts[kind]) for kind in
                ('compiled', 'linked', 'skipped', 'compile error', 'link error', 'lint failure', 'ICE')]
    report = '\n'.join(summary) + '\n\nsource\taction\tresult\tcompiled\tlinked\tscans\treason/notes\n'
    report += ''.join('\t'.join(map(str, row)) + '\n' for row in rows)
    if not args.stage_only:
        (ROOT / 'tests/baseline/gcc16-vect.txt').write_text(report)
    (out / 'claude-vect.list').write_text(''.join('claude-t-vect-' + Path(r[0]).stem + '.mic ' + r[0] + '\n'
                                               for r in rows if r[4]))
    driver = out / 'claude-vect.mic'
    code, diagnostic = invoke([*cc, '-O2', '-march=knc', ROOT / 'tools/claude-torture.c', '-o', driver])
    (out / 'driver.log').write_text(diagnostic)
    if code or list(lint(driver, TC, env)):
        raise RuntimeError('card driver build/lint failed: ' + str(out / 'driver.log'))
    paths = [out / 'claude-vect.list'] + [out / ('claude-t-vect-' + Path(r[0]).stem + '.mic') for r in rows if r[4]]
    # Relative to the durable main checkout; ticket worktrees are deleted.
    (out / 'card-files.list').write_text(''.join(os.path.relpath(p, PROJECT) + '\n' for p in paths))
    (out / 'README.txt').write_text(
        'Lead only; run from the main gcc_knc checkout.\n'
        'python tools/card_run --timeout 1800 --file-list .work/_shared/S6-07/card-files.list '
        '.work/_shared/S6-07/claude-vect.mic claude-vect.list\n'
        'No native run has been performed. Driver records PASS/FAIL/TIMEOUT and claude-torture.details.\n')
    print('\n'.join(summary))
    print('Staged:', out)
    return 0  # ICEs are baseline outcomes, not native/scan pass claims.


if __name__ == '__main__':
    sys.exit(main())
