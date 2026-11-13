#!/usr/bin/env python3
"""Prepare the S11-27 MG bisection; execute card.py only in a lead card turn."""
import difflib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import storage

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
OUT = SHARED / 'S11-27'
TC = SHARED / 'toolchain'
BUILD = Path(storage.gcc_build_dir(ROOT.parent.parent)) / 'gcc'
PREFIX = SHARED / 'gcc-knc-16.2.0'
SOURCE = SHARED / 'corpus-build/sources/NPB3.4.2/NPB3.4-OMP'
NAMES = ('mg_data', 'mg', 'print_results', 'randi8', 'timers', 'wtime')
OPTIONS = {
    'O0': ['-O0', '-march=knc'],
    'O1': ['-O1', '-march=knc'],
    'O2': ['-O2', '-march=knc'],
    'novec': ['-O2', '-march=knc', '-fno-tree-vectorize'],
    'noslp': ['-O2', '-march=knc', '-fno-tree-slp-vectorize'],
    'default': ['-O2'],
}


def run(*args, cwd=None):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.check_output(list(map(str, args)), cwd=cwd, text=True,
                                   stderr=subprocess.STDOUT)


def compiler(name, prefix=False):
    if prefix:
        return [PREFIX / ('bin/k1om-mpss-linux-' + name)]
    cmd = [BUILD / ('xgcc' if name == 'gcc' else name), '-B' + str(BUILD) + '/']
    if name == 'gfortran':
        cmd += ['-fintrinsic-modules-path=' + str(BUILD.parent / 'k1om-mpss-linux/libgfortran')]
    return cmd


def compile_set(directory, flags, prefix=False):
    directory.mkdir(parents=True, exist_ok=True)
    params = directory.parent / 'npbparams.h'
    shutil.copyfile(params, directory / 'npbparams.h')
    for name in NAMES:
        language = 'gcc' if name == 'wtime' else 'gfortran'
        src = SOURCE / ('MG' if name in ('mg', 'mg_data') else 'common')
        src /= name + ('.c' if name == 'wtime' else '.f90')
        print(run(*compiler(language, prefix), *flags, '-I' + str(directory),
                  '-I' + str(SOURCE / 'common'), '-S', src,
                  '-o', directory / (name + '.s'), cwd=directory))
        print(run(TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om',
                  directory / (name + '.s'), '-o', directory / (name + '.o')))


def link(output, objects):
    # Keep the installed runtime common to the old and new compiler objects.
    print(run(*compiler('gfortran', True), *objects,
              '-Wl,-rpath-link,' + str(TC / 'sysroot/lib64'),
              '-Wl,-rpath-link,' + str(TC / 'sysroot/usr/lib64'), '-lm', '-o', output))
    print(run(sys.executable, ROOT / 'tools/knc_lint', output))


def build():
    OUT.mkdir(exist_ok=True)
    os.environ['PATH'] = ':'.join([str(TC / 'cross/bin'), str(TC / 'cygwin/bin'),
                                 os.environ.get('PATH', '')])
    stamp = json.loads((BUILD.parent / '.gcc-build-stamp.json').read_text())
    source_tree = Path(storage.gcc_tree(ROOT.parent.parent))
    git = ['git', '-c', 'safe.directory=' + str(source_tree), '-C', source_tree]
    # A merge commit may differ while the built source tree remains identical.
    run(*git, 'diff', '--exit-code', stamp['commit'], 'HEAD')
    if not stamp['clean']:
        raise RuntimeError('selected build is stamped unclean; lead build required')
    print('Built commit:', stamp['commit'], 'same source tree as selected lane HEAD')
    config = OUT / 'config'
    config.mkdir(exist_ok=True)
    (config / 'make.def').write_text('F77 = gfortran\nFLINK = gfortran\n'
                                   'FFLAGS = -O2 -march=knc\nRAND = randi8\n')
    diff = []
    summary = []
    binaries = []
    for cls in ('S', 'A'):
        directory = OUT / cls
        directory.mkdir(exist_ok=True)
        print(run(SHARED / 'S11-18/setparams', 'mg', cls, cwd=directory))
        for variant, flags in OPTIONS.items():
            compile_set(directory / variant, flags)
            output = OUT / ('mg-' + cls + '-' + variant)
            link(output, [directory / variant / (n + '.o') for n in NAMES])
            binaries.append(output.name)
        for name in NAMES:
            output = OUT / ('mg-' + cls + '-only-' + name)
            link(output, [directory / ('O2' if n == name else 'O0') / (n + '.o')
                          for n in NAMES])
            binaries.append(output.name)
        if cls == 'A':
            compile_set(directory / 'prefix', OPTIONS['O2'], prefix=True)
            for name in NAMES:
                old = (directory / 'prefix' / (name + '.s')).read_text().splitlines(True)
                new = (directory / 'O2' / (name + '.s')).read_text().splitlines(True)
                changes = list(difflib.unified_diff(old, new, fromfile='prefix/' + name,
                                                    tofile='slot2/' + name))
                summary.append(name + ': ' + ('DIFFERENT' if changes else 'IDENTICAL'))
                diff.extend(changes)
    (OUT / 'assembly.diff').write_text(''.join(diff))
    (OUT / 'assembly-summary.txt').write_text('\n'.join(summary) + '\n')
    print('\n'.join(summary))
    # Copy only the installed shared runtimes needed by the common link.
    for lib in ('libgfortran.so.5', 'libgcc_s.so.1'):
        path = run(*compiler('gfortran', True), '-print-file-name=' + lib).strip()
        shutil.copyfile(path, OUT / lib)
    # S establishes a cheap baseline; A prioritizes current -O2 and the -O0 control.
    order = ['O2', 'O0', 'O1', 'novec', 'noslp', 'default']
    order += ['only-' + n for n in ('mg', 'randi8', 'mg_data', 'print_results', 'timers', 'wtime')]
    cases = ['mg-' + cls + '-' + variant for cls in ('S', 'A') for variant in order]
    source = (ROOT / 'tools/s11_27_batch.c').read_text()
    source = source.replace('/* CASES */', ',\n'.join('"' + n + '"' for n in cases))
    (OUT / 'batch.c').write_text(source)
    print(run(TC / 'cross/bin/k1om-mpss-linux-gcc', '-O2', OUT / 'batch.c',
              '-o', OUT / 'batch'))
    print(run(sys.executable, ROOT / 'tools/knc_lint', OUT / 'batch'))
    # This entry point only stages/runs through card_run, and is for the lead.
    card = '''#!/usr/bin/env python3
import pathlib
import subprocess
import sys
root = pathlib.Path(__file__).resolve().parent
repo = root.parent.parent / 'S11-27'
cmd = [sys.executable, str(repo / 'tools/card_run'), '--threads', '1', '--timeout', '555']
for name in CASE_NAMES + ['libgfortran.so.5', 'libgcc_s.so.1']:
    cmd += ['--file', str(root / name)]
cmd += [str(root / 'batch')]
with (root / 'card.log').open('w') as log:
    code = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT)
print('card_run exit:', code, 'log:', root / 'card.log')
raise SystemExit(code)
'''.replace('CASE_NAMES', repr(cases))
    (OUT / 'card.py').write_text(card)
    print('Prepared', len(binaries), 'linted MG binaries; lead entry point:', OUT / 'card.py')
    print('Batch: serial, 540-second total execution budget; unfinished cases explicitly reported.')


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u',
                                          str(Path(__file__).resolve())], env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    try:
        build()
    except subprocess.CalledProcessError as error:
        print(error.output, flush=True)
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
