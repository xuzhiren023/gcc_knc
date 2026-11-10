#!/usr/bin/env python3
"""Build the configured shared GCC tree, optionally skipping a current clean tree.

Run through tools/run.py. This does not install GCC. It reconfigures a build whose options lack
CONFIGURE_FLAGS or carry DROPPED_FLAGS, and configures an empty slot 2 build (--slot 2 or
KNC_GCC_SLOT=2) with slot 1's other options.
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
             'all-target-libstdc++-v3', 'all-target-libatomic', 'all-target-libgomp',
             'CFLAGS=-O2 -g1', 'CXXFLAGS=-O2 -g1']
# S9-03: C++ and libstdc++ with the donor's generic C locale model, and tzdata built in because
# the card sysroot has no zoneinfo (docs/research/knc-libstdcxx.md sections 1.4 and 2.2).
# S9-06: libgomp, with --enable-linux-futex so that a failed futex probe is a configure error and
# not a silent fall back to the posix runtime (docs/research/knc-libgomp.md, Risks).
CONFIGURE_FLAGS = ['--enable-languages=c,c++,fortran,lto', '--enable-clocale=generic',
                   '--with-libstdcxx-zoneinfo=static', '--enable-linux-futex']
# Options of an older configure that a build must no longer carry.
DROPPED_FLAGS = ['--disable-libgomp']


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


def configured_options(build):
    """The configure options recorded in BUILD's config.status, or None if it records none."""
    status = build / 'config.status'
    match = re.search(r'^ac_cs_config="(.*)"$', status.read_text(encoding='utf8', errors='replace'), re.M)
    return shlex.split(match.group(1)) if match else None


def configure(repo, build, slot):
    """Configure BUILD unless its options already carry CONFIGURE_FLAGS and none of
    DROPPED_FLAGS; True if it configured.

    An empty slot 2 build takes its other options from slot 1's build (S8-18)."""
    configured = (build / 'config.status').is_file()
    if not configured and storage.gcc_slot(slot) != '2':
        return False
    source = build if configured else Path(storage.gcc_build_dir(PROJECT, '1'))
    options = configured_options(source)
    if options is None:
        if configured:
            return False
        raise OSError('no configure options in ' + str(source / 'config.status'))
    replaced = {flag.split('=')[0] for flag in CONFIGURE_FLAGS}
    wanted = [o for o in options
              if o.split('=')[0] not in replaced and o not in DROPPED_FLAGS] + CONFIGURE_FLAGS
    if configured and sorted(options) == sorted(wanted):
        return False
    build.mkdir(parents=True, exist_ok=True)
    command(['bash', repo / 'configure', *wanted], build)
    # The top level configures gcc only when gcc/Makefile is missing, and its languages changed.
    (build / 'gcc/Makefile').unlink(missing_ok=True)
    return True


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
        reconfigured = configure(args.repo, args.build, args.slot)
        healthy = mddeps_healthy(args.build)
        if (args.if_stale and not reconfigured and healthy and clean and stamp.get('clean') is True
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
