#!/usr/bin/env python3
"""Build the configured shared GCC tree, optionally skipping a current clean tree.

Run through tools/run.py. This does not install GCC, and configures only an empty slot 2 build
(--slot 2 or KNC_GCC_SLOT=2), with slot 1's options.
Example: python tools/run.py --name gcc-build -- python tools/gcc_build.py --if-stale
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

import storage

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
MAKE_ARGS = ['-j8', 'all-gcc', 'all-target-libgcc', 'all-target-libgfortran',
             'CFLAGS=-O2 -g1', 'CXXFLAGS=-O2 -g1']


def read_stamp(path):
    try:
        value = json.loads(path.read_text(encoding='utf8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_stamp(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')
    temporary.replace(path)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True,
                                   encoding='utf8', errors='replace').strip()


def mddeps_healthy(build):
    """True when gcc/mddeps.mk lists the KNC and SSE .md files under MD_INCLUDES."""
    try:
        text = (build / 'gcc/mddeps.mk').read_text(encoding='utf8', errors='replace')
    except OSError:
        return False
    return ('MD_INCLUDES' in text and 'config/i386/imci.md' in text
            and 'config/i386/sse.md' in text)


def configure_like_slot_one(repo, build):
    """Configure an empty slot 2 build with the options slot 1's build was configured with (S8-18)."""
    status = Path(storage.gcc_build_dir(PROJECT, '1')) / 'config.status'
    match = re.search(r'^ac_cs_config="(.*)"$', status.read_text(encoding='utf8', errors='replace'), re.M)
    if not match:
        raise OSError('no configure options in ' + str(status))
    build.mkdir(parents=True, exist_ok=True)
    command(['bash', repo / 'configure', *shlex.split(match.group(1))], build)


def command(argv, cwd):
    print('+ (cd ' + shlex.quote(str(cwd)) + ' && ' + shlex.join(map(str, argv)) + ')', flush=True)
    subprocess.run(list(map(str, argv)), cwd=cwd, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=sorted(storage.GCC_SLOTS),
                        help='GCC tree and build to use (default: KNC_GCC_SLOT, else 1)')
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--if-stale', action='store_true',
                        help='skip make when the last successful build has this clean Git tree')
    args = parser.parse_args(argv)
    args.repo = args.repo or Path(storage.gcc_tree(PROJECT, args.slot))
    args.build = args.build or Path(storage.gcc_build_dir(PROJECT, args.slot))
    stamp_path = args.build / '.gcc-build-stamp.json'
    try:
        commit = git(args.repo, 'rev-parse', 'HEAD')
        tree = git(args.repo, 'rev-parse', 'HEAD^{tree}')
        clean = not git(args.repo, 'status', '--porcelain', '--untracked-files=all')
        stamp = read_stamp(stamp_path)
        if storage.gcc_slot(args.slot) == '2' and not (args.build / 'config.status').is_file():
            configure_like_slot_one(args.repo, args.build)
        healthy = mddeps_healthy(args.build)
        if (args.if_stale and healthy and clean and stamp.get('clean') is True
                and stamp.get('tree') == tree and stamp.get('make_args') == MAKE_ARGS):
            print('SKIP shared GCC: clean tree ' + tree + ' already built at ' +
                  str(stamp.get('commit')))
            return 0
        # Invalidate before make: failure or interruption must never certify old objects.
        stamp_path.unlink(missing_ok=True)
        if not healthy:
            print('mddeps.mk is missing or lost its .md includes; removing s-mddeps to regenerate')
            (args.build / 'gcc/s-mddeps').unlink(missing_ok=True)
        print('BUILD shared GCC: ' + commit + ' tree=' + tree + ' clean=' + str(clean), flush=True)
        command(['make', *MAKE_ARGS], args.build)
        if not mddeps_healthy(args.build):
            print('ERROR: mddeps.mk still lacks config/i386/imci.md or sse.md after the build; '
                  'not certifying it')
            return 1
        clean = (clean and git(args.repo, 'rev-parse', 'HEAD') == commit
                 and not git(args.repo, 'status', '--porcelain', '--untracked-files=all'))
        write_stamp(stamp_path, {'commit': commit, 'tree': tree, 'clean': clean,
                                'make_args': MAKE_ARGS})
        return 0
    except (OSError, subprocess.CalledProcessError) as error:
        print('ERROR: ' + str(error))
        return 1


if __name__ == '__main__':
    if os.name == 'nt' and not any(arg in ('-h', '--help') for arg in sys.argv[1:]):
        tc = SHARED / 'toolchain'
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(tc / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')

        def posix(path):
            return subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'), '-u', str(path)],
                                           env=env, text=True).strip()

        arguments = sys.argv[1:]
        for flag in ('--repo', '--build'):
            if flag in arguments:
                index = arguments.index(flag) + 1
                arguments[index] = posix(arguments[index])
        sys.exit(subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), posix(__file__),
                                  *arguments], env=env))
    sys.exit(main())
