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
    different_total = failed_total = 0
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        assemblies = [Path(temporary) / (slot + '.s') for slot in ('a', 'b')]
        for flags in (['-O2'], ['-O2', '-mavx512f']):
            identical = different = failed = 0
            for source in sources:
                name = source.relative_to(args.repo / CORPUS).as_posix()
                texts = []
                for compiler, assembly in zip(compilers, assemblies):
                    assembly.unlink(missing_ok=True)
                    try:
                        result = subprocess.run([*compiler, '-quiet', *flags, str(source),
                                                 '-o', str(assembly)], stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, text=True,
                                                errors='replace', timeout=300)
                        if result.returncode or not assembly.is_file():
                            print('FAILED ' + name + ' (' + shlex.join(compiler) + '):\n' + result.stdout)
                            break
                        texts.append(assembly.read_text(encoding='utf8', errors='replace'))
                    except subprocess.TimeoutExpired:
                        print('FAILED ' + name + ': compiler timed out')
                        break
                if len(texts) != 2:
                    failed += 1
                elif texts[0] == texts[1]:
                    identical += 1
                else:
                    different += 1
                    print('DIFFERENT ' + name + ' (' + ' '.join(flags) + ')')
                    print(''.join(difflib.unified_diff(texts[0].splitlines(True),
                                                     texts[1].splitlines(True),
                                                     fromfile=args.tree[0] + '/' + name,
                                                     tofile=args.tree[1] + '/' + name)), end='')
            print(' '.join(flags) + ': identical=' + str(identical) +
                  ' different=' + str(different) + ' failed=' + str(failed), flush=True)
            different_total += different
            failed_total += failed
    return 2 if failed_total else int(bool(different_total))


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
