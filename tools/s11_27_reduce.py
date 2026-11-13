#!/usr/bin/env python3
"""Prepare the standalone stencil and reload diagnostics; never runs the card."""
import os
from pathlib import Path
import re
import subprocess
import sys

import s11_27_mg as mg


def bridge_scan(dump, function):
    """Require LRA's bridge pseudos to stay memory-only through allocation."""
    sections = re.split(r'^;; Function ', dump, flags=re.M)
    body = next((part for part in sections
                 if part.startswith(function + ' (')), '')
    bridges = set(re.findall(
        r'Creating newreg=(\d+), assigning class NO_REGS to KNC bridge r\1\b', body))
    if not bridges:
        return ['missing NO_REGS bridge creation in ' + function]
    errors = []
    for reg in sorted(bridges, key=int):
        if re.search(r'Assign \d+ to [^\n]*\br' + reg + r'\b', body):
            errors.append('bridge r' + reg + ' assigned a hard register')
        if re.search(r'class (?!NO_REGS\b)\w+ (?:for|to) [^\n]*\br' + reg + r'\b', body):
            errors.append('bridge r' + reg + ' changed out of NO_REGS')
    if 'Dataflow summary:' not in body:
        errors.append('missing final reload RTL in ' + function)
    else:
        final = body.split('Dataflow summary:', 1)[1]
        for reg in sorted(bridges, key=int):
            if re.search(r'\(reg(?::\w+|/\w+)* ' + reg + r'\b', final):
                errors.append('unspilled bridge r' + reg + ' in final RTL')
    return errors


def scan(asm, vector=True):
    """Check scratch stores against the two live 40-double local arrays.

    Discover array bases from the scalar producer's indexed stores, rather
    than baking in register numbers or frame displacements. A changed code
    shape is an explicit failure requiring review, never a vacuous pass.
    """
    if 'stencil_:\n' not in asm:
        return ['missing stencil body; review scanner']
    body = asm.split('stencil_:\n', 1)[1].split('.size\tstencil_', 1)[0]
    bases = {}
    for offset, frame, reg in re.findall(
            r'leaq\s+(-?\d+)\(%(rbp|rsp)\), %(\w+)', body):
        if re.search(r'fstpl\s+\(%' + reg + r',%\w+,8\)', body):
            bases[reg] = (frame, int(offset))
    if len(bases) != 2 or (vector and not re.search(r'\bvaddpd\b', body)):
        return ['unrecognized producer/vector loop; review scanner']
    overlaps = []
    for offset, frame in re.findall(r'fstpl\s+(-?\d+)\(%(rbp|rsp)\)', body):
        off = int(offset)
        for array_frame, base in bases.values():
            if frame == array_frame and base <= off < base + 40 * 8:
                overlaps.append((off, base, (off - base) // 8 + 1))
    if overlaps:
        return ['broadcast scratch overwrites live local array: ' + str(overlaps)]
    return []


def check():
    failed = False
    for name in ('O2', 'novec', 'noreuse'):
        errors = scan((mg.OUT / 'reduce' / (name + '.s')).read_text(),
                      vector=name != 'novec')
        print('FAIL' if errors else 'PASS', name,
              '; '.join(errors) if errors else 'scalar scratch does not overlap local stencil arrays')
        failed |= bool(errors)
    return int(failed)


def t1(runner):
    """Compile fresh assembly with the selected T1 compiler, then scan and lint."""
    source = runner.root / 'tests/regress/knc-stencil-reload.F90'
    compiler = runner.cc.with_name('gfortran')
    for name, flags in [('O2', []), ('novec', ['-fno-tree-vectorize']),
                        ('noreuse', ['-fstack-reuse=none'])]:
        asm = runner.out / ('stencil-' + name + '.s')
        obj = asm.with_suffix('.o')
        dump = asm.with_suffix('.reload')
        label = 't1 stencil reload ' + name
        try:
            runner.command(compiler, *runner.cc_flags, '-O2', '-march=knc',
                           *flags, '--sysroot=' + str(runner.sysroot),
                           '-fdump-rtl-reload=' + str(dump),
                           '-S', source, '-o', asm)
            errors = scan(asm.read_text(), vector=name != 'novec')
            if name != 'novec':
                errors.extend(bridge_scan(dump.read_text(), 'stencil'))
            runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj)
            runner.command(sys.executable, runner.root / 'tools/knc_lint', asm, obj)
            runner.result(label + ' scratch bounds, assembly and knc_lint', errors)
        except RuntimeError as error:
            runner.result(label, [str(error)])


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
