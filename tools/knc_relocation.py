#!/usr/bin/env python3
"""S3-13 acceptance: capture before, then compare after a KNC-only relocation.

Run through tools/run.py. Assembly and comparison state stay in the shared area.
No fixtures are added: use torture compile and the existing --vector selection.
"""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import os
from pathlib import Path
import pickle
import re
import subprocess
import sys

import check
import storage
from portability import torture_dialect_options

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
GCC = Path(storage.gcc_tree(ROOT.parent.parent))
BUILD = Path(storage.gcc_build_dir(ROOT.parent.parent)) / 'gcc'
OUT = SHARED / 'knc-relocation'
STATE = OUT / 'before.pickle'


def structure():
    """S3-22: the last shared KNC bodies must be entry hooks (ADR-0006)."""
    directory = GCC / 'gcc/config/i386'
    source = (directory / 'i386.cc').read_text()
    def body(name):
        start = source.index('\n' + name + ' (')
        start = source.index('\n{', start)
        return source[start:source.index('\n}', start) + 2]
    zero = body('ix86_zero_call_used_regs')
    hook = ('\n{\n  if (TARGET_KNC)\n'
            '    return ix86_knc_zero_call_used_regs (need_zeroed_hardregs);')
    checks = {
        'zero-call-used-regs entry hook only': zero.startswith(hook)
            and 'KNC' not in zero[len(hook):],
        'CAS16 undef outside shared i386-c.cc': not re.search(
            r'cpp_undef\s*\([^;]*__GCC_HAVE_SYNC_COMPARE_AND_SWAP_16',
            (directory / 'i386-c.cc').read_text()),
        'varargs only retains SSE-or-KNC conditions': 'TARGET_KNC' not in
            body('setup_incoming_varargs_64').replace('TARGET_SSE || TARGET_KNC', ''),
    }
    for name, passed in checks.items():
        print(('PASS ' if passed else 'FAIL ') + name, flush=True)
    return int(not all(checks.values()))


def metrics():
    paths = ['gcc/config/i386', 'gcc/common/config/i386',
             ':!gcc/config/i386/imci.md', ':!gcc/config/i386/linux-k1om.h',
             ':!gcc/config/i386/i386-knc.cc', ':!gcc/config/i386/i386-knc.h']
    def diff(*args):
        return subprocess.check_output(['git', '-C', str(GCC), 'diff', *args,
                                        'releases/gcc-16.2.0', 'HEAD', '--', *paths],
                                       text=True, timeout=60)
    lines = sum(int(n) for row in diff('--numstat').splitlines()
                for n in row.split('\t')[:2])
    hunks = sum(line.startswith('@@ ') for line in diff().splitlines())
    return lines, hunks


def capture():
    OUT.mkdir(exist_ok=True)
    corpus = GCC / 'gcc/testsuite/gcc.c-torture/compile'
    sources = sorted(corpus.rglob('*.c'))
    if not sources:
        raise RuntimeError('empty torture compile corpus')
    jobs = [(s, level) for level in ('-O0', '-O2') for s in sources]
    def compile_one(job):
        source, level = job
        # A source has only one job per level; each worker overwrites its output.
        asm = OUT / (source.relative_to(corpus).as_posix().replace('/', '_') + level + '.s')
        asm.unlink(missing_ok=True)
        result = subprocess.run([str(BUILD / 'cc1'), '-quiet', '-w', '-march=knc',
                                 level, *torture_dialect_options(source), str(source),
                                 '-o', str(asm)], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=300)
        data = asm.read_bytes() if result.returncode == 0 else result.stdout
        asm.unlink(missing_ok=True)
        return (source.relative_to(corpus).as_posix(), level), (result.returncode, data)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assemblies = dict(pool.map(compile_one, jobs))
    for level in ('-O0', '-O2'):
        values = [v for k, v in assemblies.items() if k[1] == level]
        print('torture ' + level + ': assembly=%d rejected=%d' %
              (sum(v[0] == 0 for v in values), sum(v[0] != 0 for v in values)), flush=True)

    original = check.Runner.command
    def command(runner, *args, **kwargs):
        result = original(runner, *args, **kwargs)
        argv = list(map(str, args))
        if '-S' in argv and '-o' in argv:
            output = Path(argv[argv.index('-o') + 1])
            # Temporary directories vary; assembly bytes are compared verbatim.
            key = tuple(arg for i, arg in enumerate(argv)
                        if i not in (argv.index('-o'), argv.index('-o') + 1))
            status = result.returncode if isinstance(result, subprocess.CompletedProcess) else 0
            assemblies[('vector', key)] = (status, output.read_bytes()
                                           if status == 0 and output.is_file() else b'')
        return result
    check.Runner.command = command
    results = []
    try:
        for flags in (['t0', 't1', 't2'], ['t1', '--vector']):
            sys.argv = ['check', *flags, '--compiler', 'gcc16', '--worker']
            text = io.StringIO()
            with contextlib.redirect_stdout(text):
                code = check.main()
            content = text.getvalue()
            print(content, end='', flush=True)
            results.append((code, [line for line in content.splitlines()
                                   if line.startswith(('PASS ', 'FAIL '))]))
    finally:
        check.Runner.command = original
    return assemblies, results


def main(action):
    if action == 'structure':
        return structure()
    current = metrics()
    print('shared added+removed=%d hunks=%d' % current, flush=True)
    if action == 'before':
        assemblies, results = capture()
        with STATE.open('wb') as output:
            pickle.dump((current, assemblies, results), output)
        return 0
    with STATE.open('rb') as baseline:
        previous, before, old_results = pickle.load(baseline)
    if current[0] >= previous[0] or current[1] > previous[1]:
        print('FAIL shared diff must shrink without increasing hunks: before=%s after=%s' %
              (previous, current))
        return 1
    after, new_results = capture()
    # The tier runner also compiles generated scalar/Fortran probes in temporary
    # directories. The requested T1 assembly corpus is its --vector sources.
    def requested(data):
        # The dump destination is transient, just like the -o destination.
        # Retain the dump option while comparing every assembly byte.
        def stable(key):
            if key[0] != 'vector':
                return key
            return ('vector', tuple(arg.split('=', 1)[0]
                                    if arg.startswith('-fdump-rtl-expand=') else arg
                                    for arg in key[1]))
        return {stable(key): value for key, value in data.items()
                if key[0] != 'vector'
                or any('/tests/t1/knc-vec-' in arg for arg in key[1])}
    before, after = requested(before), requested(after)
    different = [key for key in before.keys() | after.keys()
                 if before.get(key) != after.get(key)]
    for key in different:
        print('DIFFERENT ' + str(key))
    # Compare tier outcomes; timings and transient paths remain in the log.
    def outcomes(groups):
        return [(code, [line.split(': ', 1)[0] for line in rows])
                for code, rows in groups]
    same_results = outcomes(old_results) == outcomes(new_results)
    print('assembly comparisons=%d different=%d; tier results identical=%s' %
          (len(before), len(different), same_results))
    return int(bool(different) or not same_results)


if __name__ == '__main__':
    if os.name == 'nt':
        tc = SHARED / 'toolchain'
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(tc / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'), '-u', __file__], text=True).strip()
        sys.exit(subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env))
    sys.exit(main(sys.argv[1]))
