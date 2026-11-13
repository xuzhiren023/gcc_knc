#!/usr/bin/env python3
"""Prepare the standalone stencil and reload diagnostics; never runs the card."""
import os
from pathlib import Path
import re
import subprocess
import sys

import s11_27_mg as mg


def check():
    """Check scratch stores against the two live 40-double local arrays.

    Discover array bases from the scalar producer's indexed stores, rather
    than baking in register numbers or frame displacements. A changed code
    shape is an explicit failure requiring review, never a vacuous pass.
    """
    failed = False
    for name in ('O2', 'novec', 'noreuse'):
        asm = (mg.OUT / 'reduce' / (name + '.s')).read_text()
        body = asm.split('stencil_:\n', 1)[1].split('.size\tstencil_', 1)[0]
        bases = {}
        for offset, frame, reg in re.findall(
                r'leaq\s+(-?\d+)\(%(rbp|rsp)\), %(\w+)', body):
            if re.search(r'fstpl\s+\(%' + reg + r',%\w+,8\)', body):
                bases[reg] = (frame, int(offset))
        if len(bases) != 2 or (name != 'novec' and not re.search(r'\bvaddpd\b', body)):
            print('FAIL', name, 'unrecognized producer/vector loop; review scanner')
            failed = True
            continue
        overlaps = []
        for offset, frame in re.findall(r'fstpl\s+(-?\d+)\(%(rbp|rsp)\)', body):
            off = int(offset)
            for array_frame, base in bases.values():
                if frame == array_frame and base <= off < base + 40 * 8:
                    overlaps.append((off, base, (off - base) // 8 + 1))
        if overlaps:
            print('FAIL', name, 'broadcast scratch overwrites live local array:', overlaps)
            failed = True
        else:
            print('PASS', name, 'scalar scratch does not overlap local stencil arrays')
    return int(failed)


def build():
    os.environ['PATH'] = ':'.join([str(mg.TC / 'cross/bin'),
                                 str(mg.TC / 'cygwin/bin'), os.environ['PATH']])
    directory = mg.OUT / 'reduce'
    directory.mkdir(exist_ok=True)
    source = mg.ROOT / 'tests/regress/knc-stencil-reload.F90'
    cases = []

    def assemble(asm):
        obj = asm.with_suffix('.o')
        print(mg.run(mg.TC / 'cross/bin/k1om-mpss-linux-as', '--march=k1om',
                     asm, '-o', obj))
        return obj

    driver = directory / 'driver.s'
    print(mg.run(*mg.compiler('gfortran'), '-O0', '-march=knc', '-DDRIVER',
                 '-S', source, '-o', driver))
    driver_obj = assemble(driver)
    for name, flags in [('O2', []), ('novec', ['-fno-tree-vectorize']),
                        ('noreuse', ['-fstack-reuse=none'])]:
        asm = directory / (name + '.s')
        info = directory / (name + '.vec')
        info.unlink(missing_ok=True)
        print(mg.run(*mg.compiler('gfortran'), '-O2', '-march=knc', *flags,
                     '-fopt-info-vec-optimized=' + str(info),
                     '-fdump-rtl-expand', '-fdump-rtl-ira', '-fdump-rtl-reload',
                     '-S', source, '-o', asm, cwd=directory))
        binary = 'stencil-' + name
        mg.link(mg.OUT / binary, [driver_obj, assemble(asm)])
        cases.append(binary)

    # Keep one original failing loop while exposing reload's new stack slots.
    base = mg.OUT / 'S/O2'
    asm = directory / 'mg.s'
    if not asm.exists():
        print(mg.run(*mg.compiler('gfortran'), '-O2', '-march=knc',
                     '-I' + str(base), '-I' + str(mg.SOURCE / 'common'),
                     '-fdbg-cnt=vect_loop:16-16', '-fdump-rtl-expand',
                     '-fdump-rtl-ira', '-fdump-rtl-reload',
                     '-S', mg.SOURCE / 'MG/mg.f90', '-o', asm, cwd=directory))

    runner = (mg.ROOT / 'tools/s11_27_parallel.c').read_text()
    runner = runner.replace('/* CASES */', ',\n'.join('"' + n + '"' for n in cases))
    (directory / 'parallel.c').write_text(runner)
    print(mg.run(mg.TC / 'cross/bin/k1om-mpss-linux-gcc', '-O2',
                 directory / 'parallel.c', '-o', mg.OUT / 'reduce-parallel'))
    print(mg.run(sys.executable, mg.ROOT / 'tools/knc_lint', mg.OUT / 'reduce-parallel'))
    card = (mg.OUT / 'narrow-card.py').read_text()
    start = card.index('for name in ')
    end = card.index(" + ['libgfortran", start)
    card = card[:start] + 'for name in ' + repr(cases) + card[end:]
    card = card.replace("root / 'parallel'", "root / 'reduce-parallel'")
    card = card.replace('narrow-card.log', 'reduce-card.log')
    (mg.OUT / 'reduce-card.py').write_text(card)
    print('Prepared', len(cases), 'linted reduced cases:', mg.OUT / 'reduce-card.py')
    return check()


if __name__ == '__main__':
    if '--check-only' in sys.argv:
        raise SystemExit(check())
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(mg.TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(mg.TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__).resolve())],
                                         env=env, text=True).strip()
        raise SystemExit(subprocess.call([str(mg.TC / 'cygwin/bin/python3.12.exe'), script], env=env))
    try:
        raise SystemExit(build())
    except subprocess.CalledProcessError as error:
        print(error.output, flush=True)
        raise
