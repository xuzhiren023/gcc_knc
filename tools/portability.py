#!/usr/bin/env python3
"""ADR-0006: forward-port conflicts and x86 assembly stability.

Run through tools/run.py. No fetches. drill only writes Git objects and its report;
x86 uses separate shared worktrees/builds and must run under Cygwin Python.
"""
import argparse
import csv
import datetime
import difflib
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
BASE = 'releases/gcc-16.2.0'
CORPUS = 'gcc/testsuite/gcc.c-torture/compile'


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True,
                                   encoding='utf8', errors='replace').strip('\n')


def default_refs(repo):
    refs = git(repo, 'for-each-ref', '--format=%(refname:short)',
               'refs/remotes/upstream/releases/', 'refs/heads/upstream/releases/').splitlines()
    releases = [(tuple(map(int, ref.rsplit('gcc-', 1)[1].split('.'))), ref)
                for ref in refs if re.fullmatch(r'upstream/releases/gcc-\d+(?:\.\d+)*', ref)]
    if not releases:
        raise RuntimeError('no upstream release branch; never fetching automatically')
    return ['upstream/master', max(releases)[1]]


def conflict_hunks(text):
    hunks, current = [], None
    for line in text.splitlines():
        if re.match(r'^<{7,} ', line):
            current = []
        if current is not None:
            current.append(line)
        if current is not None and re.match(r'^>{7,} ', line):
            hunks.append('\n'.join(current))
            current = None
    return hunks


def drill(args):
    refs = args.onto or default_refs(args.repo)
    changed = git(args.repo, 'diff', '--no-renames', '--name-only', '-z', BASE, 'knc').split('\0')
    changed = [path for path in changed if path]
    lines = ['## ' + datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
             '', 'Base: `' + BASE + '`; KNC: `' + git(args.repo, 'rev-parse', 'knc') + '`.',
             'Local refs only; no fetch, checkout, index update or ref update.', '']
    for ref in refs:
        commit = git(args.repo, 'rev-parse', '--verify', ref + '^{commit}')
        date = git(args.repo, 'show', '-s', '--format=%cI', commit)
        result = subprocess.run(['git', '-C', str(args.repo), 'merge-tree', '--write-tree',
                                 '--merge-base=' + BASE, '--name-only', '-z', '--no-messages',
                                 ref, 'knc'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding='utf8', errors='replace')
        if result.returncode not in (0, 1):
            raise RuntimeError('merge-tree ' + ref + ': ' + result.stderr.strip())
        fields = result.stdout.rstrip('\0\n').split('\0')
        tree, conflicts = fields[0], [field for field in fields[1:] if field]
        lines += ['### ' + ref, '', 'Commit: `' + commit + '`; date: ' + date + '.',
                  '', 'Conflicts: ' + str(len(conflicts)), '']
        for path in conflicts:
            lines += ['#### `' + path + '`', '']
            blob = subprocess.run(['git', '-C', str(args.repo), 'show', tree + ':' + path],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, encoding='utf8', errors='replace')
            hunks = conflict_hunks(blob.stdout) if blob.returncode == 0 else []
            if not hunks:
                # Delete/modify and rename conflicts need not have textual markers.
                lines += ['Structural conflict; upstream and KNC changes from the base:', '']
                hunks = [git(args.repo, 'diff', '--no-ext-diff', '--no-color', BASE, side,
                             '--', path) for side in (ref, 'knc')]
            for hunk in hunks:
                lines += ['```diff', hunk, '```', '']
        lines += ['Upstream line churn since 16.2 in files changed by KNC:', '',
                  '| File | Added | Removed |', '| --- | ---: | ---: |']
        churn = {}
        if changed:
            for record in git(args.repo, 'diff', '--no-renames', '--numstat', '-z',
                              BASE, commit, '--', *changed).split('\0'):
                if record:
                    added, removed, path = record.split('\t', 2)
                    churn[path] = (added, removed)
        for path in changed:
            added, removed = churn.get(path, ('0', '0'))
            lines.append('| `' + path + '` | +' + added + ' | -' + removed + ' |')
        lines.append('')
        print(ref + ' ' + commit + ' ' + date + ': conflicts=' + str(len(conflicts)))
        for path in conflicts:
            print('  ' + path)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('a', encoding='utf8', newline='\n') as report:
        report.write('\n'.join(lines) + '\n')
    print('Report: ' + str(args.report))
    return 0


def make_is_running():
    text = subprocess.check_output(['tasklist.exe', '/FI', 'IMAGENAME eq make.exe',
                                    '/FO', 'CSV', '/NH'], text=True)
    return any(row and row[0].casefold() == 'make.exe' for row in csv.reader(text.splitlines()))


def command(argv, cwd):
    print('+ (cd ' + shlex.quote(str(cwd)) + ' && ' + shlex.join(map(str, argv)) + ')', flush=True)
    subprocess.run(list(map(str, argv)), cwd=cwd, check=True)


def build_cc1(repo, shared, tree, slot):
    commit = git(repo, 'rev-parse', '--verify', tree + '^{commit}')
    home = shared / 'portability' / ('x86-' + slot)
    source, build = home / 'source', home / 'build'
    home.mkdir(parents=True, exist_ok=True)
    git_options = ['git', '-c', 'core.autocrlf=false', '-c', 'core.fileMode=false']
    if not source.exists():
        command([*git_options, '-C', repo, 'worktree', 'add', '--detach', source, commit], shared)
    else:
        if git(source, 'status', '--porcelain'):
            raise RuntimeError('dirty portability worktree: ' + str(source))
        if git(source, 'rev-parse', 'HEAD') != commit:
            command([*git_options, '-C', source, 'checkout', '--detach', commit], shared)
    build.mkdir(exist_ok=True)
    print('Tree ' + tree + ': ' + commit, flush=True)
    # Reconfigure in place; make reuses all current objects, including on repeat runs.
    command(['bash', source / 'configure', '--build=x86_64-pc-cygwin',
             '--host=x86_64-pc-cygwin', '--target=x86_64-pc-cygwin',
             '--enable-languages=c', '--disable-bootstrap', '--disable-multilib',
             '--disable-nls', '--without-isl'], build)
    command(['make', '-j8', 'all-gcc', 'CFLAGS=-O2 -g1', 'CXXFLAGS=-O2 -g1'], build)
    compiler = build / 'gcc/cc1.exe'
    if not compiler.is_file():
        raise RuntimeError('build did not produce ' + str(compiler))
    return [str(compiler)]


def torture_dialect_options(source):
    # compile.exp/c-torture.exp supply -w. gcc-dg.exp also applies each
    # test's dialect directives; these are needed for legacy C under GCC 14+.
    # Only unconditional dialect options apply to this fixed assembly check;
    # this is not a replacement for DejaGNU's target selectors/options.
    options = []
    text = source.read_text(encoding='utf8', errors='replace')
    for directive in re.finditer(r'\{\s*dg-(?:additional-)?options\s+"([^"]*)"\s*\}', text):
        options.extend(flag for flag in shlex.split(directive[1])
                       if flag.startswith('-std=') or flag in ('-fpermissive', '-fno-permissive'))
    return options


def x86(args):
    if make_is_running():
        raise RuntimeError('refusing x86 while make.exe is running')
    if len(args.tree) != 2:
        raise RuntimeError('x86 needs exactly two --tree arguments')
    sources = sorted((args.repo / CORPUS).rglob('*.c'))
    if not sources:
        raise RuntimeError('empty torture compile corpus: ' + str(args.repo / CORPUS))
    compilers = [build_cc1(args.repo, args.shared, tree, slot)
                 for tree, slot in zip(args.tree, ('a', 'b'))]
    output = args.shared / 'portability'
    output.mkdir(parents=True, exist_ok=True)
    different_total = error_total = 0
    print('Default torture options: -w', flush=True)
    dialects = {source: torture_dialect_options(source) for source in sources}
    for source, options in dialects.items():
        if options:
            print('Dialect options ' + source.relative_to(args.repo / CORPUS).as_posix() +
                  ': ' + shlex.join(options), flush=True)
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        assemblies = [Path(temporary) / (slot + '.s') for slot in ('a', 'b')]
        for flags in (['-O2'], ['-O2', '-mavx512f']):
            identical = different = both_failed = errors = 0
            for source in sources:
                name = source.relative_to(args.repo / CORPUS).as_posix()
                outcomes = []
                for compiler, assembly in zip(compilers, assemblies):
                    assembly.unlink(missing_ok=True)
                    try:
                        result = subprocess.run([*compiler, '-quiet', '-w', *flags,
                                                 *dialects[source], str(source),
                                                 '-o', str(assembly)], stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, text=True,
                                                errors='replace', timeout=300)
                        if result.returncode:
                            outcomes.append(('failed', result.stdout, ''))
                        elif not assembly.is_file():
                            outcomes.append(('error', result.stdout + '\nmissing assembly output', ''))
                        else:
                            outcomes.append(('ok', result.stdout,
                                             assembly.read_text(encoding='utf8', errors='replace')))
                    except subprocess.TimeoutExpired:
                        outcomes.append(('error', 'compiler timed out', ''))
                    except OSError as error:
                        outcomes.append(('error', str(error), ''))
                statuses = [outcome[0] for outcome in outcomes]
                if 'error' in statuses:
                    errors += 1
                    label = 'TOOL-ERROR'
                elif statuses == ['failed', 'failed'] and outcomes[0][1] == outcomes[1][1]:
                    both_failed += 1
                    print('BOTH-FAILED ' + name + ' (' + ' '.join(flags) + '):\n' + outcomes[0][1])
                    continue
                elif 'failed' in statuses:
                    different += 1
                    label = 'DIFFERENT'
                elif outcomes[0][2] == outcomes[1][2]:
                    identical += 1
                    continue
                else:
                    different += 1
                    print('DIFFERENT ' + name + ' (' + ' '.join(flags) + ')')
                    print(''.join(difflib.unified_diff(outcomes[0][2].splitlines(True),
                                                     outcomes[1][2].splitlines(True),
                                                     fromfile=args.tree[0] + '/' + name,
                                                     tofile=args.tree[1] + '/' + name)), end='')
                    continue
                print(label + ' ' + name + ' (' + ' '.join(flags) + ')')
                for tree, (status, diagnostics, _) in zip(args.tree, outcomes):
                    print(tree + ' (' + status + '):\n' + (diagnostics or '<no diagnostics>'))
            print(' '.join(flags) + ': identical=' + str(identical) +
                  ' different=' + str(different) + ' both-failed=' + str(both_failed) +
                  ' errors=' + str(errors), flush=True)
            different_total += different
            error_total += errors
    return 2 if error_total else int(bool(different_total))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    drill_parser = sub.add_parser('drill')
    drill_parser.add_argument('--onto', action='append')
    drill_parser.add_argument('--report', type=Path, default=ROOT / 'docs/research/forward-port.md')
    x86_parser = sub.add_parser('x86')
    x86_parser.add_argument('--tree', action='append', required=True)
    x86_parser.add_argument('--shared', type=Path, default=SHARED)
    for command_parser in (drill_parser, x86_parser):
        command_parser.add_argument('--repo', type=Path, default=SHARED / 'gcc')
    args = parser.parse_args(argv)
    try:
        return drill(args) if args.action == 'drill' else x86(args)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print('ERROR: ' + str(error))
        return 2


if __name__ == '__main__':
    if os.name == 'nt' and sys.argv[1:2] == ['x86']:
        tc = SHARED / 'toolchain'
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(tc / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        def posix(path):
            return subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'), '-u', str(path)],
                                           env=env, text=True).strip()
        arguments = sys.argv[1:]
        for flag in ('--repo', '--shared'):
            if flag in arguments:
                index = arguments.index(flag) + 1
                arguments[index] = posix(arguments[index])
        sys.exit(subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), posix(__file__),
                                  *arguments], env=env))
    sys.exit(main())
