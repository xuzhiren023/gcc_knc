#!/usr/bin/env python3
"""Stage S12-30's native routes and exercise their host model once.

No GCC checkout/build or card execution. Native slots share IMCI assembly.
The host model validates C control flow only, never IMCI behavior/performance.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

import corpus

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
OUT = SHARED / 'S12-30'
SOURCE = ROOT / 'tools/s12_30_precision.c'


def asm_bodies(text):
    return dict(re.findall(r'^([\w.]+):\n(.*?)^\s*\.size\s+\1\s*,',
                           text, re.M | re.S))


def indirect_hints(body):
    """Trace prefetch address SSA operands, rejecting plain col/x streams.

    This is a codegen presence check, not a bounds or future-distance proof.
    Native guard pages and a GIMPLE/assembly audit remain required at green.
    """
    names = r'\b(?:[a-zA-Z]\w*)?_\d+\b'
    definitions = dict(re.findall(r'^\s*(' + names + r') = ([^;]+);', body, re.M))
    result = []
    for arg in re.findall(r'__builtin_prefetch\s*\(([^,]+),', body):
        pending, seen, terms = re.findall(names, arg), set(), [arg]
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            value = definitions.get(name, '')
            terms.append(value)
            pending.extend(re.findall(names, value))
        expression = ' '.join(terms)
        if (re.search(r'\bcol_\d+', expression)
                and re.search(r'\bx_\d+', expression)
                and re.search(r'\*_|\bMEM\[', expression)):
            result.append(expression)
    return result


def t1(runner):
    """Phase-two red: automatic hints in strict indexed reductions only."""
    OUT.mkdir(exist_ok=True)
    source_flags = ['-std=gnu99', '-DPHASE2_T1', '-march=knc',
                    '--sysroot=' + str(runner.sysroot)]
    for mode, options, expected in (
            ('off', ['-O2', '-ffp-contract=off'], True),
            ('fast', ['-O2', '-ffp-contract=fast'], True),
            ('disabled', ['-O2', '-ffp-contract=off', '-fno-prefetch-loop-arrays'], False),
            ('size', ['-Os', '-ffp-contract=off'], False)):
        asm = OUT / ('phase2-' + mode + '.s')
        dump = OUT / ('phase2-' + mode + '.optimized')
        runner.command(runner.cc, *runner.cc_flags, *source_flags, *options,
                       '-fdump-tree-optimized=' + str(dump), '-S', SOURCE, '-o', asm)
        obj = asm.with_suffix('.o')
        runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj)
        runner.command(sys.executable, ROOT/'tools/knc_lint', asm, obj)
        runner.result('t1 sparse ' + mode + ' compile/assemble/lint', [])
        chunks = re.split(r'^;; Function (\w+) .*$', dump.read_text(), flags=re.M)
        bodies = dict(zip(chunks[1::2], chunks[2::2]))
        assembly = asm_bodies(asm.read_text())
        runner.result('t1 sparse ' + mode + ' scanner controls',
                      [] if indirect_hints(bodies['explicit_indirect'])
                      and not indirect_hints(bodies['explicit_stream'])
                      else ['cannot distinguish indexed and affine hints'])
        for name in ('sparse_rows', 'sparse_slice', 'volatile_indices', 'sentinel_slice'):
            want = expected and name in ('sparse_rows', 'sparse_slice')
            found = bool(indirect_hints(bodies[name]))
            errors = []
            if found != want:
                errors.append(('missing' if want else 'unexpected') + ' automatic indirect prefetch')
            if want and not re.search(r'\bvprefetch\w*\b', assembly[name]):
                errors.append('no emitted prefetch instruction')
            if name in ('sparse_rows', 'sparse_slice'):
                if not re.search(r'\bfadd\w*\b', assembly[name]):
                    errors.append('ordered scalar x87 fold missing')
                if re.search(r'\bv(?:add|fmadd|fmsub|fnmadd)\w*\b', assembly[name]):
                    errors.append('unexpected vector reduction or contraction')
            runner.result('t1 sparse ' + mode + ' ' + name, errors)

    # Lead requested that the measured -fno-tree-vectorize baseline be checked
    # against ordinary -O2. Use the installed Phase 1 compiler, not gcc2 xgcc.
    baselines = []
    for label, extra in (('plain', []), ('novect', ['-fno-tree-vectorize'])):
        asm = OUT / ('phase1-baseline-' + label + '.s')
        runner.command(corpus.compiler_path(corpus.KNC), '-O2', '-std=gnu99',
                       '-march=knc', '-ffp-contract=off', '-DPREFIX=knc_',
                       *extra, '-S', SOURCE, '-o', asm)
        baselines.append(asm_bodies(asm.read_text())['knc_scalar'])
    runner.result('t1 phase1 installed -O2 scalar baseline identity',
                  [] if baselines[0] == baselines[1]
                  else ['plain -O2 scalar function differs from measured baseline; inspect assembly'])
    runner.say('S12-30 phase2 outputs: ' + str(OUT) + '/phase2-*; no native phase2 run')


def run(*args):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=OUT, check=True)


def build(host=False):
    objects = []
    stem = 'host-' if host else ''
    for name, compiler in [('donor', corpus.DONOR), ('knc', corpus.KNC),
                           ('fast', corpus.KNC)]:
        cc = TC/'cygwin/bin/gcc' if host else corpus.compiler_path(compiler)
        flags = ['-O2', '-std=gnu99', '-ffp-contract=' + ('fast' if name == 'fast' else 'off')]
        if host:
            flags += ['-mfpmath=387', '-fexcess-precision=fast', '-DHOST_MODEL']
        elif name != 'donor':
            flags += ['-march=knc']
        # Explicit assembly supplies gathers to both scalar-only donor and KNC.
        flags += ['-fno-tree-vectorize', '-DPREFIX=' + name + '_']
        if name == 'donor':
            flags += ['-DSEED_TREES']
        obj = OUT/(stem+name+'-precision.o')
        if host:
            run(cc, *flags, '-c', SOURCE, '-o', obj)
        else:
            run(cc, '--version')
            asm = obj.with_suffix('.s')
            run(cc, *flags, '-S', SOURCE, '-o', asm)
            run(TC/'cross/bin/k1om-mpss-linux-as', '--march=k1om', asm, '-o', obj)
        objects.append(obj)
    cc = TC/'cygwin/bin/gcc' if host else corpus.compiler_path(corpus.DONOR)
    binary = OUT/('host-precision.exe' if host else 'precision-gate')
    flags = ['-O2', '-std=gnu99', '-ffp-contract=off', '-fno-tree-vectorize']
    if host:
        flags += ['-mfpmath=387', '-fexcess-precision=fast', '-DHOST_MODEL']
    run(cc, *flags, '-DDRIVER', SOURCE, *objects,
        *([] if host else corpus.link_paths()), '-lrt', '-lm', '-o', binary)
    if not host:
        run(sys.executable, ROOT/'tools/knc_lint', binary)
    return binary


def main():
    if sys.platform != 'cygwin':
        raise RuntimeError('use shared Cygwin python3')
    OUT.mkdir(exist_ok=True)
    os.environ['PATH'] = ':'.join(map(str, [TC/'cross/bin', TC/'cygwin/bin', os.environ['PATH']]))
    binary = build()
    print('STAGED:', binary, '; lead card_run --threads 1 --timeout 1150; binary argument: 12345', flush=True)
    host = build(host=True)
    # The approved red already demonstrated both seeded tree failures once.
    print('HOST MODEL ONLY: all routes; native correctness/timing pending', flush=True)
    return subprocess.run([str(host), '12345', '--correctness'], cwd=OUT).returncode


if __name__ == '__main__':
    sys.exit(main())
