#!/usr/bin/env python3
"""Stage class-S vectorizer counter cases; only the lead executes narrow-card.py."""
import os
from pathlib import Path
import re
import subprocess
import sys

import s11_27_mg as mg


def build():
    os.environ['PATH'] = ':'.join([str(mg.TC / 'cross/bin'),
                                 str(mg.TC / 'cygwin/bin'), os.environ['PATH']])
    directory = mg.OUT / 'narrow'
    directory.mkdir(exist_ok=True)
    base = mg.OUT / 'S/O2'
    source = mg.SOURCE / 'MG/mg.f90'
    cases = []
    mapping = []

    def compile_case(name, flags):
        info = directory / (name + '.vec')
        asm = directory / (name + '.s')
        info.unlink(missing_ok=True)
        output = mg.run(*mg.compiler('gfortran'), '-O2', '-march=knc',
                        '-I' + str(base), '-I' + str(mg.SOURCE / 'common'),
                        '-fopt-info-vec-optimized=' + str(info), *flags,
                        '-S', source, '-o', asm, cwd=directory)
        (directory / (name + '.compile')).write_text(output)
        mapping.append(name + ': ' + ' '.join(flags) + '\n' + info.read_text())
        return output

    def assemble_link(name):
        obj = directory / (name + '.o')
        print(mg.run(mg.TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om',
                     directory / (name + '.s'), '-o', obj))
        binary = 'mg-S-' + name
        mg.link(mg.OUT / binary,
                [obj if n == 'mg' else base / (n + '.o') for n in mg.NAMES])
        cases.append(binary)

    profile = compile_case('vect-all', ['-fdbg-cnt-list', '-fdump-tree-vect-details'])
    total = int(re.search(r'^\s*vect_loop\s+(\d+)', profile, re.M)[1])
    print('Vectorizer counter total:', total, flush=True)
    if not 0 < total <= 60:
        raise RuntimeError('unexpected counter count; inspect before sizing the round')
    assemble_link('vect-all')
    # Prefixes locate transitions; singleton cases check independent bad loops.
    for count in range(total + 1):
        name = 'vect-first-' + str(count)
        compile_case(name, ['-fdbg-cnt=vect_loop:' + str(count)])
        assemble_link(name)
    for count in range(1, total + 1):
        name = 'vect-only-' + str(count)
        compile_case(name, ['-fdbg-cnt=vect_loop:%d-%d' % (count, count)])
        assemble_link(name)
    # Outlining changes the serial code paths even with one OpenMP worker.
    compile_case('openmp', ['-fopenmp'])
    # Use the matching modules/objects and the same installed runtime at link.
    obj = directory / 'openmp.o'
    print(mg.run(mg.TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om',
                 directory / 'openmp.s', '-o', obj))
    binary = 'mg-S-openmp'
    print(mg.run(*mg.compiler('gfortran', True), '-fopenmp',
                 *[obj if n == 'mg' else base / (n + '.o') for n in mg.NAMES],
                 '-Wl,-rpath-link,' + str(mg.TC / 'sysroot/lib64'),
                 '-Wl,-rpath-link,' + str(mg.TC / 'sysroot/usr/lib64'),
                 '-lm', '-o', mg.OUT / binary))
    print(mg.run(sys.executable, mg.ROOT / 'tools/knc_lint', mg.OUT / binary))
    cases.append(binary)
    import shutil
    runtime = mg.run(*mg.compiler('gfortran', True),
                     '-print-file-name=libgomp.so.1').strip()
    shutil.copyfile(runtime, mg.OUT / 'libgomp.so.1')
    (directory / 'loops.txt').write_text('\n'.join(mapping))
    runner = (mg.ROOT / 'tools/s11_27_parallel.c').read_text()
    runner = runner.replace('/* CASES */', ',\n'.join('"' + n + '"' for n in cases))
    (directory / 'parallel.c').write_text(runner)
    print(mg.run(mg.TC / 'cross/bin/k1om-mpss-linux-gcc', '-O2',
                 directory / 'parallel.c', '-o', mg.OUT / 'parallel'))
    print(mg.run(sys.executable, mg.ROOT / 'tools/knc_lint', mg.OUT / 'parallel'))
    card = '''import pathlib
import subprocess
import sys
root = pathlib.Path(__file__).resolve().parent
repo = root.parent.parent / 'S11-27'
cmd = [sys.executable, str(repo / 'tools/card_run'), '--threads', '240', '--timeout', '540']
for name in CASE_NAMES + ['libgfortran.so.5', 'libgcc_s.so.1', 'libgomp.so.1']:
    cmd += ['--file', str(root / name)]
cmd += [str(root / 'parallel')]
with (root / 'narrow-card.log').open('w') as log:
    code = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT)
print('card_run exit:', code, 'log:', root / 'narrow-card.log')
raise SystemExit(code)
'''.replace('CASE_NAMES', repr(cases))
    (mg.OUT / 'narrow-card.py').write_text(card)
    print('Prepared', len(cases), 'linted cases; loop mapping:', directory / 'loops.txt')
    print('Lead entry point:', mg.OUT / 'narrow-card.py')


if __name__ == '__main__':
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(mg.TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(mg.TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__).resolve())],
                                         env=env, text=True).strip()
        raise SystemExit(subprocess.call([str(mg.TC / 'cygwin/bin/python3.12.exe'), script], env=env))
    try:
        build()
    except subprocess.CalledProcessError as error:
        print(error.output, flush=True)
        raise
