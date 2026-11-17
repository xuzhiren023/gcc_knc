#!/usr/bin/env python3
"""Audit committed sources and export a full-history bundle and numbered patches.

No working-tree files enter an export. Rejected tracked files are reported, never
silently filtered: filtering would change the branch identity and its history.
An export audits every reachable tree, including historical trees. Large real
repositories therefore need a reviewed release policy before using this strict
fixture/project policy; there is deliberately no skip-audit switch.
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
                     'check-ignore', '--no-index', '-z', '--stdin', data=data,
                     codes=(0, 1)) if data else b''
        return {os.fsdecode(name) for name in output.split(b'\0') if name}


def path_reasons(name, mode, kind, size):
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
    if size > LIMIT:
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


def audit(repo, revision, blob_cache):
    tree = entries(repo, revision)
    ignored = ignored_paths(repo, tree)
    excluded = []
    for name, mode, kind, oid, size in tree:
        reasons = path_reasons(name, mode, kind, size)
        if name in ignored:
            reasons.append('tracked path matches committed gitignore rules')
        # Do not open prohibited vendor content. Small source blobs are checked
        # for executable/archive magic even when their names disguise the type.
        if kind == b'blob' and not reasons:
            if oid not in blob_cache:
                data = git(repo, 'cat-file', 'blob', oid)
                blob_cache[oid] = data.startswith((b'\x7fELF', b'MZ', b'!<arch>\n',
                                                   b'%PDF-', b'PK\x03\x04', b'\x1f\x8b'))
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
        # format-patch drops merge commits. Refuse rather than omit their edits.
        if git(repo, 'rev-list', '--merges', base_commit + '..' + revision).strip():
            raise ValueError('merge commits require a reviewed patch-series policy')
    if output.exists() and any(output.iterdir()):
        raise ValueError('output must be empty; remove the previous release deliberately')
    cache, seen = {}, set()
    for row in git(repo, 'log', '--format=%H %T', revision).decode().splitlines():
        commit, tree = row.split()
        if tree in seen:
            continue
        seen.add(tree)
        rejected = audit(repo, commit, cache)
        if rejected:
            print(json.dumps({'commit': commit, 'excluded': rejected}, indent=2))
            return 1
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
            git(scratch, 'format-patch', '--no-signature', '--no-renames', '--full-index',
                '--binary', '--numbered', '--output-directory', patches,
                base_commit + '..' + revision)
    (output / 'README.txt').write_text(
        'Source release\nBranch: ' + branch + '\nCommit: ' + revision + '\n'
        + ('Upstream tag: ' + base + '\nUpstream commit: ' + base_commit + '\n' if base else '')
        + 'source.bundle contains complete reachable history, without prerequisites.\n'
        + 'All reachable committed trees passed the strict source audit.\n'
        + 'Untracked/ignored workspace files are excluded because only Git objects are exported.\n'
        + ('Apply patches in numbered order with git am from the upstream tag.\n' if base else ''),
        encoding='utf8')
    print('Exported ' + revision + ' to ' + str(output))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('audit', 'export'))
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--ref', required=True)
    parser.add_argument('--base')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        revision = git(repo, 'rev-parse', '--verify', args.ref + '^{commit}').decode().strip()
        if args.action == 'export':
            if args.output is None:
                parser.error('export needs --output')
            return export(repo, args.ref, revision, args.base, args.output.resolve())
        report = {'commit': revision, 'excluded': audit(repo, revision, {})}
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
