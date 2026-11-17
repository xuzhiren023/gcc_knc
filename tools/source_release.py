#!/usr/bin/env python3
"""Audit committed sources and export a full-history bundle and squashed diff.

No working-tree files enter an export. Rejected tracked files are reported, never
silently filtered: filtering would change the branch identity and its history.
The tip must pass the audit. Published history is retained, never rewritten.
"""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile


LIMIT = 1024 * 1024
ARTIFACT_SUFFIXES = {'.o', '.obj', '.a', '.so', '.dll', '.exe', '.mic', '.pyc',
                     '.pyo', '.class', '.bundle', '.log', '.sum', '.su'}
OUTPUT_DIRS = {'.work', '__pycache__', 'CMakeFiles', 'autom4te.cache'}
ROOT_OUTPUTS = {'build', 'install', 'dist', '.tools', 'vendor-docs'}


def git(repo, *args, data=None, codes=(0,)):
    result = subprocess.run(['git', '-C', str(repo), *map(str, args)],
                            input=data, capture_output=True)
    if result.returncode not in codes:
        raise RuntimeError(result.stderr.decode('utf8', 'replace').strip())
    return result.stdout


def entries(repo, revision):
    result = []
    for record in git(repo, 'ls-tree', '-rlz', revision).split(b'\0'):
        if record:
            meta, name = record.split(b'\t', 1)
            mode, kind, oid, size = meta.split()
            result.append((os.fsdecode(name), mode, kind, oid.decode(),
                           int(size) if size != b'-' else 0))
    return result


def ignored_paths(repo, tree):
    # Only the committed ignore rules apply. Global excludes, info/exclude and
    # dirty/untracked .gitignore files in the source checkout cannot affect this.
    with tempfile.TemporaryDirectory(prefix='source-audit-') as temporary:
        scratch = Path(temporary)
        git(scratch, 'init', '-q')
        for name, mode, kind, oid, size in tree:
            if PurePosixPath(name).name == '.gitignore' and mode in (b'100644', b'100755'):
                target = scratch / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(git(repo, 'cat-file', 'blob', oid))
        data = b''.join(os.fsencode(row[0]) + b'\0' for row in tree)
        output = git(scratch, '-c', 'core.excludesFile=' + os.devnull,
                     '-c', 'core.ignoreCase=false',
                     'check-ignore', '--no-index', '-z', '--stdin', data=data,
                     codes=(0, 1)) if data else b''
        return {os.fsdecode(name) for name in output.split(b'\0') if name}


def path_reasons(name, mode, kind, size, size_limit=True):
    path = PurePosixPath(name)
    lower = name.lower()
    reasons = []
    if any(part in OUTPUT_DIRS for part in path.parts) or path.parts[0] in ROOT_OUTPUTS:
        reasons.append('workspace, build output or downloaded-input directory')
    if lower.startswith(('tests/out/', 'toolchain/sysroot/')):
        reasons.append('generated test/card output or external sysroot')
    if (path.suffix.lower() in ARTIFACT_SUFFIXES or re.search(r'\.so\.\d', lower)
            or re.search(r'\.[cCfF].\d{3}[rtil]\.', name)
            or lower.endswith('.opt-record.json.gz')
            or path.name in {'config.status', 'config.log', 'CMakeCache.txt'}):
        reasons.append('build artifact, generated binary or compiler output')
    if size_limit and size > LIMIT:
        reasons.append('size exceeds 1 MiB file limit')
    if (path.suffix.lower() in {'.pdf', '.chm'}
            or ('intrinsic' in lower and path.suffix.lower() == '.xml')
            or re.search(r'(^|/)(svml|libimf)([./_-]|$)', lower)
            or path.name.lower() == 'zmmintrin.h'
            or (re.search(r'(^|/)(icc|intel)(/|[-_])', lower)
                and path.name.lower() in {'immintrin.h', 'xmmintrin.h'})):
        reasons.append('vendor document or prohibited vendor implementation')
    if kind != b'blob':
        reasons.append('submodule is not self-contained source in this bundle')
    return reasons


def binary_blobs(repo, oids, blob_cache):
    """Inspect blobs through one Git process, without loading a tree into memory."""
    missing = set(oids) - blob_cache.keys()
    if not missing:
        return
    with subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        for oid in missing:
            process.stdin.write((oid + '\n').encode())
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3 or header[1] != b'blob':
                raise RuntimeError('cannot read source blob ' + oid)
            size = int(header[2])
            prefix = process.stdout.read(min(size, 8))
            remaining = size - len(prefix)
            while remaining:
                chunk = process.stdout.read(min(remaining, 65536))
                if not chunk:
                    raise RuntimeError('truncated source blob ' + oid)
                remaining -= len(chunk)
            process.stdout.read(1)
            blob_cache[oid] = prefix.startswith((b'\x7fELF', b'MZ', b'!<arch>\n',
                                                b'%PDF-', b'PK\x03\x04', b'\x1f\x8b'))
        process.stdin.close()
        if process.wait():
            raise RuntimeError('source blob inspection failed')


def audit(repo, revision, blob_cache, upstream=None):
    tree = entries(repo, revision)
    ignored = ignored_paths(repo, tree)
    if upstream is not None:
        # Compare mode, type and object identity, including renamed paths.
        # Unchanged upstream content remains in the export but is exempt.
        tree = [row for row in tree if upstream.get(row[0]) != row[1:]]
    size_limit = upstream is None
    binary_blobs(repo, (oid for name, mode, kind, oid, size in tree
                       if kind == b'blob' and name not in ignored
                       and not path_reasons(name, mode, kind, size, size_limit)), blob_cache)
    excluded = []
    for name, mode, kind, oid, size in tree:
        reasons = path_reasons(name, mode, kind, size, size_limit)
        if name in ignored:
            reasons.append('tracked path matches committed gitignore rules')
        # Do not open prohibited vendor content. Small source blobs are checked
        # for executable/archive magic even when their names disguise the type.
        if kind == b'blob' and not reasons:
            if blob_cache[oid]:
                reasons.append('binary executable, archive or document signature')
        if reasons:
            excluded.append({'path': name, 'reason': '; '.join(reasons)})
    return excluded


def export(repo, ref, revision, base, output):
    branch = git(repo, 'rev-parse', '--symbolic-full-name', ref).decode().strip()
    if not branch.startswith('refs/heads/'):
        raise ValueError('--ref must name a branch for a clonable bundle')
    base_ref = base_commit = None
    if base:
        base_ref = git(repo, 'rev-parse', '--symbolic-full-name', base).decode().strip()
        if not base_ref.startswith('refs/tags/'):
            raise ValueError('--base must name the upstream tag')
        base_commit = git(repo, 'rev-parse', '--verify', base + '^{commit}').decode().strip()
        git(repo, 'merge-base', '--is-ancestor', base_commit, revision)
    if output.exists() and any(output.iterdir()):
        raise ValueError('output must be empty; remove the previous release deliberately')
    upstream = {row[0]: row[1:] for row in entries(repo, base_commit)} if base_commit else None
    cache, seen = {}, set()
    rejected = audit(repo, revision, cache, upstream)
    if rejected:
        print(json.dumps({'commit': revision, 'excluded': rejected}, indent=2))
        return 1
    historical = {}
    history = base_commit + '..' + revision if base_commit else revision
    for row in git(repo, 'log', '--format=%H %T', history).decode().splitlines():
        commit, tree = row.split()
        if tree in seen:
            continue
        seen.add(tree)
        rejected = audit(repo, commit, cache, upstream)
        if rejected:
            for item in rejected:
                historical.setdefault((item['path'], item['reason']), commit)
    # Freeze refs in a small temporary bare repository sharing only the source
    # object store. No refs are changed in the source repository, and a branch
    # advancing during export cannot change the already audited revision.
    objects = git(repo, 'rev-parse', '--git-path', 'objects').decode().strip()
    objects = (repo / objects).resolve() if not Path(objects).is_absolute() else Path(objects)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='source-export-') as temporary:
        scratch = Path(temporary)
        git(scratch, 'init', '--bare', '-q')
        (scratch / 'objects/info/alternates').write_text(objects.as_posix() + '\n', encoding='utf8')
        git(scratch, 'update-ref', branch, revision)
        refs = [branch]
        if base_ref:
            tag = git(repo, 'rev-parse', '--verify', base_ref).decode().strip()
            git(scratch, 'update-ref', base_ref, tag)
            refs.append(base_ref)
        git(scratch, 'bundle', 'create', output / 'source.bundle', *refs)
        if base_commit:
            patches = output / 'patches'
            patches.mkdir()
            (patches / '0001-knc-squashed.patch').write_bytes(
                git(scratch, 'diff', '--no-ext-diff', '--no-textconv', '--no-renames',
                    '--full-index', '--binary', base_commit, revision))
    (output / 'README.txt').write_text(
        'Source release\nBranch: ' + branch + '\nCommit: ' + revision + '\n'
        + ('Upstream tag: ' + base + '\nUpstream commit: ' + base_commit + '\n' if base else '')
        + 'source.bundle contains complete reachable history, without prerequisites.\n'
        + ('The tip changes from upstream passed the source audit; unchanged upstream files\n'
           'are exempt and retained. The project-only 1 MiB limit does not apply here.\n'
           'Historical findings cover fork changes after the upstream tag.\n' if base else
           'The entire tip tree passed the source audit, including the 1 MiB file limit.\n')
        + 'Historical artifacts are retained; published history is never rewritten.\n'
        + 'Untracked/ignored workspace files are excluded because only Git objects are exported.\n'
        + ('Apply patches/0001-knc-squashed.patch with git apply from the upstream tag.\n'
           'The squashed diff includes merge resolutions; the bundle preserves full history.\n' if base else '')
        + '\nHistorical findings (path: reason; example commit):\n'
        + ''.join(path + ': ' + reason + '; ' + commit + '\n'
                  for (path, reason), commit in sorted(historical.items())),
        encoding='utf8')
    print('Exported ' + revision + ' to ' + str(output))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('audit', 'export'))
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--ref', help='default: knc with --base, otherwise main')
    parser.add_argument('--base', help='GCC upstream tag: audit only changes; no project size limit')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        args.ref = args.ref or ('knc' if args.base else 'main')
        revision = git(repo, 'rev-parse', '--verify', args.ref + '^{commit}').decode().strip()
        if args.action == 'export':
            if args.output is None:
                parser.error('export needs --output')
            return export(repo, args.ref, revision, args.base, args.output.resolve())
        upstream = None
        if args.base:
            base_commit = git(repo, 'rev-parse', '--verify', args.base + '^{commit}').decode().strip()
            git(repo, 'merge-base', '--is-ancestor', base_commit, revision)
            upstream = {row[0]: row[1:] for row in entries(repo, base_commit)}
        report = {'commit': revision, 'excluded': audit(repo, revision, {}, upstream)}
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for item in report['excluded']:
                print(item['path'] + ': ' + item['reason'])
            print(('FAIL' if report['excluded'] else 'PASS') + ' source audit ' + revision)
        return int(bool(report['excluded']))
    except (OSError, ValueError, RuntimeError) as error:
        print('FAILED source release: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
