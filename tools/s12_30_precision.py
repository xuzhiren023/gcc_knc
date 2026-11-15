#!/usr/bin/env python3
"""Stage S12-30's native routes and exercise their host model once.

No GCC checkout/build or card execution. Native slots share IMCI assembly.
The host model validates C control flow only, never IMCI behavior/performance.
"""
import ast
from fractions import Fraction
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


SSA = r'(?<![\w.])(?:[A-Za-z][\w.]*|)_\d+\b'


def plus(a, b, scale=1):
    result = dict(a)
    for key, value in b.items():
        result[key] = result.get(key, 0) + scale * value
    return {k: v for k, v in result.items() if v}


def times(a, scale):
    return {k: v * scale for k, v in a.items() if v * scale}


class Gimple:
    """Fail-closed SSA/address and branch-edge checks for these T1 probes.

    PHI ancestry is followed with a visited set; affine expressions keep
    PHIs as atoms so a loop backedge cannot invent an equality. Unsupported
    address algebra fails the bounds check, rather than counting a hint.
    This does not replace the native guard suite or the green legality audit.
    """
    def __init__(self, body):
        self.body, self.defs, self.where, self.hints = body, {}, {}, []
        parts = re.split(r'^\s*<bb (\d+)>[^\n]*\n', body, flags=re.M)
        self.blocks = {int(k): v for k, v in zip(parts[1::2], parts[2::2])}
        self.edges, self.guards = {}, []
        for bb, text in self.blocks.items():
            for name, value in re.findall(r'^\s*(?:# )?(' + SSA +
                                          r') = (.*?)(?:;|$)', text, re.M):
                self.defs[name], self.where[name] = value, bb
            for arg in re.findall(r'__builtin_prefetch\s*\(([^,]+),', text):
                self.hints.append((bb, arg))
            dest = list(map(int, re.findall(r'goto <bb (\d+)>', text)))
            # Optimized dumps omit a goto for layout fallthrough.
            if not dest and not re.search(r'\breturn\b', text):
                keys = list(self.blocks)
                pos = keys.index(bb)
                if pos+1 < len(keys):
                    dest = [keys[pos+1]]
            self.edges[bb] = dest
            condition = re.search(r'if \((.*?)\)\s*\n\s*goto <bb', text)
            if condition and len(dest) == 2:
                self.guards.append((bb, condition[1], dest))

    def ancestry(self, expression):
        pending, seen = re.findall(SSA, expression), set()
        while pending:
            name = pending.pop()
            if name not in seen:
                seen.add(name)
                pending.extend(re.findall(SSA, self.defs.get(name, '')))
        return seen

    def param(self, stem):
        names = re.findall(r'\b' + stem + r'_\d+\(D\)', self.body)
        return names[0][:-3] if names else None

    def address(self, name):
        value = self.defs.get(name, '')
        if value.startswith('*'):
            return value[1:]
        match = re.fullmatch(r'MEM(?: <[^>]+>)?\[(.*)\]', value)
        return match[1] if match else None

    def affine(self, expression, seen=frozenset()):
        expression = expression.replace('(D)', '')
        expression = re.sub(r'\((?:const ?|unsigned ?|signed ?|long ?|short ?|int|double|float|sizetype|void|char|\*| )+\)', '', expression)
        expression = re.sub(r'(?<=\d)B\b', '', expression).strip()
        names = {}
        def rename(match):
            key = 'ssa' + str(len(names))
            names[key] = match[0]
            return key
        expression = re.sub(SSA, rename, expression)
        def walk(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, int):
                return {'#': node.value} if node.value else {}
            if isinstance(node, ast.Name) and node.id in names:
                name = names[node.id]
                value = self.defs.get(name, '')
                if not value or name in seen or value.startswith('PHI') or self.address(name):
                    return {name: 1}
                return self.affine(value, seen | {name})
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                return times(walk(node.operand), -1)
            if isinstance(node, ast.BinOp):
                a, b = walk(node.left), walk(node.right)
                if isinstance(node.op, (ast.Add, ast.Sub)):
                    return plus(a, b, -1 if isinstance(node.op, ast.Sub) else 1)
                if isinstance(node.op, ast.Mult):
                    if not (a.keys() - {'#'}):
                        return times(b, a.get('#', 0))
                    if not (b.keys() - {'#'}):
                        return times(a, b.get('#', 0))
            raise ValueError('unsupported affine expression: ' + expression)
        return walk(ast.parse(expression, mode='eval').body)

    def offset(self, name, base, size):
        address = self.address(name)
        if not address or not base:
            return None
        try:
            value = self.affine(address)
            if value.pop(base, 0) != 1:
                return None
            return times(value, Fraction(1, size))
        except (ValueError, SyntaxError):
            return None

    def indirect(self):
        result = []
        for bb, arg in self.hints:
            ancestors = self.ancestry(arg)
            if self.param('x') not in ancestors:
                continue
            for name in ancestors:
                address = self.address(name)
                if address and (self.param('col') in self.ancestry(address)
                                or self.param('cols') in self.ancestry(address)):
                    result.append((bb, name))
        return result

    def edge_dominates(self, edge, target):
        pending, seen = [min(self.blocks)], set()
        while pending:
            bb = pending.pop()
            if bb == target:
                return False
            if bb not in seen:
                seen.add(bb)
                pending.extend(dst for dst in self.edges[bb] if (bb, dst) != edge)
        return True

    def bounded(self, load, bound, index):
        # Demand an edge that dominates the ORDINARY hinted index load,
        # not merely the nonfaulting prefetch instruction.
        wanted = plus({bound: 1}, index, -1)
        for bb, condition, destinations in self.guards:
            match = re.fullmatch(r'(.*?) (<=|>=|<|>) (.*)', condition)
            if not match:
                continue
            try:
                difference = plus(self.affine(match[3]), self.affine(match[1]), -1)
            except (ValueError, SyntaxError):
                continue
            op = match[2]
            if op in ('>', '>='):
                difference = times(difference, -1)
            for branch, dst in enumerate(destinations):
                actual = difference if branch == 0 else times(difference, -1)
                # True strict or false nonstrict means an integer gap >= 1.
                gap = int((op in ('<', '>')) == (branch == 0))
                delta = plus(actual, wanted, -1)
                if not (delta.keys() - {'#'}) and gap - delta.get('#', 0) >= 1:
                    if self.edge_dominates((bb, dst), self.where[load]):
                        return True
        return False

    def cross_row(self, layout):
        """Require a later-row bound on the very index loaded for a hint."""
        for _, load in self.indirect():
            if layout == 'csr':
                index = self.offset(load, self.param('col'), 4)
                if index is None:
                    continue
                # A current j has a PHI ancestry rooted in row[i]. A bound
                # only at row[i+1] is insufficient for the d32/n13,n27 case.
                starts = [self.offset(n, self.param('row'), 4)
                          for n in self.ancestry(self.address(load))]
                starts = [s for s in starts if s is not None]
                for bound in self.defs:
                    future = self.offset(bound, self.param('row'), 4)
                    if future is None or not self.bounded(load, bound, index):
                        continue
                    for start in starts:
                        delta = plus(future, start, -1)
                        if not (delta.keys() - {'#'}) and delta.get('#', 0) >= 2:
                            return True
            else:
                # Pointer and count must describe the SAME future row.
                for pointer in self.ancestry(self.address(load)):
                    future = self.offset(pointer, self.param('cols'), 8)
                    index = self.offset(load, pointer, 4)
                    if future is None or index is None:
                        continue
                    for bound in self.defs:
                        count = self.offset(bound, self.param('count'), 4)
                        if count != future or not self.bounded(load, bound, index):
                            continue
                        for current in self.defs:
                            now = self.offset(current, self.param('count'), 4)
                            if now is not None:
                                delta = plus(future, now, -1)
                                if not (delta.keys() - {'#'}) and delta.get('#', 0) >= 1:
                                    return True
        return False


def t1(runner):
    """Phase-two red: automatic hints in strict indexed reductions only."""
    OUT.mkdir(exist_ok=True)
    source_flags = ['-std=gnu99', '-DPHASE2_T1', '-march=knc',
                    '--sysroot=' + str(runner.sysroot)]
    enabled = '-mknc-indirect-prefetch'
    disabled = '-mno-knc-indirect-prefetch'
    eligible = ('sparse_rows', 'sparse_slice', 'sparse_hpcg')
    counts = {}
    for mode, options, expected in (
            ('controls', ['-O2', '-ffp-contract=off',
                          '-fprefetch-loop-arrays'], False),
            ('disabled', ['-O2', '-ffp-contract=off', disabled,
                          '-fprefetch-loop-arrays'], False),
            ('off', ['-O2', '-ffp-contract=off', enabled,
                     '-fprefetch-loop-arrays'], True),
            ('fast', ['-O2', '-ffp-contract=fast', enabled,
                      '-fprefetch-loop-arrays'], True),
            ('size', ['-Os', '-ffp-contract=off', enabled], False)):
        asm = OUT / ('phase2-' + mode + '.s')
        dump = OUT / ('phase2-' + mode + '.optimized')
        bounds_dump = OUT / ('phase2-' + mode + '.aprefetch')
        # Do not let an old dump masquerade as output from an unsupported flag.
        asm.unlink(missing_ok=True)
        dump.unlink(missing_ok=True)
        bounds_dump.unlink(missing_ok=True)
        bounds_flags = (['-fdump-tree-aprefetch=' + str(bounds_dump)]
                        if mode == 'controls' or expected else [])
        compiled = runner.command(runner.cc, *runner.cc_flags, *source_flags, *options,
                                  *bounds_flags,
                                  '-fdump-tree-optimized=' + str(dump), '-S', SOURCE,
                                  '-o', asm, check=False)
        if compiled.returncode:
            runner.result('t1 sparse ' + mode + ' requested option/compile',
                          [compiled.stdout.strip()[-1200:]])
            continue
        obj = asm.with_suffix('.o')
        runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj)
        runner.command(sys.executable, ROOT/'tools/knc_lint', asm, obj)
        runner.result('t1 sparse ' + mode + ' compile/assemble/lint', [])
        chunks = re.split(r'^;; Function (\w+) .*$', dump.read_text(), flags=re.M)
        bodies = dict(zip(chunks[1::2], chunks[2::2]))
        bounds_bodies = {}
        if bounds_flags:
            required = (('explicit_csr', 'explicit_rowlocal', 'explicit_hpcg')
                        if mode == 'controls' else eligible)
            if bounds_dump.exists():
                chunks = re.split(r'^;; Function (\w+) .*$',
                                  bounds_dump.read_text(), flags=re.M)
                bounds_bodies = dict(zip(chunks[1::2], chunks[2::2]))
            missing = [name for name in required if name not in bounds_bodies]
            runner.result('t1 sparse ' + mode + ' pre-ivopts bounds dump',
                          ['missing aprefetch function ' + name for name in missing])
        assembly = asm_bodies(asm.read_text())
        counts[mode] = {name: len(re.findall(r'\bvprefetch\w*\b', assembly[name]))
                        for name in eligible}
        if mode == 'controls':
            controls = {
                'straight indexed hint': bool(Gimple(bodies['explicit_indirect']).indirect()),
                'affine stream rejected': not Gimple(bodies['explicit_stream']).indirect(),
                'post-ivopts loop indexed hint': bool(Gimple(bodies['explicit_loop']).indirect()),
                'loop has ivtmp PHI': bool(re.search(r'# ivtmp\.\d+_\d+ = PHI', bodies['explicit_loop'])),
                'CSR future-bound guard': Gimple(bounds_bodies.get('explicit_csr', '')).cross_row('csr'),
                'row-local d32 rejected': 'explicit_rowlocal' in bounds_bodies and not Gimple(bounds_bodies['explicit_rowlocal']).cross_row('csr'),
                'HPCG future-pointer/count guard': Gimple(bounds_bodies.get('explicit_hpcg', '')).cross_row('hpcg'),
            }
            for label, ok in controls.items():
                runner.result('t1 sparse scanner ' + label, [] if ok else ['control failed'])
        if mode == 'disabled':
            runner.result('t1 sparse disabled keeps stream prefetch enabled',
                          [] if counts[mode]['sparse_rows'] > 0 else ['no stream hints in CSR'])
        for name in (*eligible, 'volatile_indices', 'sentinel_slice', 'alias_bounds'):
            want = expected and name in eligible
            graph = Gimple(bodies[name])
            found = bool(graph.indirect())
            errors = []
            if mode != 'controls' and found != want:
                errors.append(('missing' if want else 'unexpected') + ' automatic indirect prefetch')
            if want:
                bounds_graph = Gimple(bounds_bodies.get(name, ''))
                if 'disabled' not in counts or counts[mode][name] <= counts['disabled'][name]:
                    errors.append('vprefetch count must exceed switch-off with stream hints on')
                if name in ('sparse_rows', 'sparse_hpcg'):
                    if not bounds_graph.cross_row('csr' if name == 'sparse_rows' else 'hpcg'):
                        errors.append('hinted index lacks a dominating later-row bound')
                elif not any(bounds_graph.bounded(load, bounds_graph.param('end'), index)
                             for _, load in bounds_graph.indirect()
                             for index in [bounds_graph.offset(load, bounds_graph.param('col'), 4)]
                             if index is not None):
                    errors.append('slice hinted index lacks an end bound')
            if name in eligible:
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


def build(host=False, legal=False):
    objects = []
    stem = ('host-' if host else '') + ('legal-' if legal else '')
    for name, compiler in [('donor', corpus.DONOR), ('knc', corpus.KNC),
                           ('fast', corpus.KNC)]:
        cc = TC/'cygwin/bin/gcc' if host else corpus.compiler_path(compiler)
        flags = ['-O2', '-std=gnu99', '-ffp-contract=' + ('fast' if name == 'fast' else 'off')]
        if host:
            flags += ['-mfpmath=387', '-fexcess-precision=fast', '-DHOST_MODEL']
        elif name != 'donor':
            flags += ['-march=knc']
        # Explicit assembly supplies gathers to both scalar-only donor and KNC.
        flags += (['-DLEGAL_PROOF'] if legal else ['-fno-tree-vectorize'])
        flags += ['-DPREFIX=' + name + '_']
        if name == 'donor' and not legal:
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
    binary = OUT/(('host-legal.exe' if host else 'legal-gate') if legal
                  else ('host-precision.exe' if host else 'precision-gate'))
    flags = ['-O2', '-std=gnu99', '-ffp-contract=off', '-fno-tree-vectorize']
    if host:
        flags += ['-mfpmath=387', '-fexcess-precision=fast', '-DHOST_MODEL']
    if legal:
        flags += ['-DLEGAL_PROOF']
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
    legal = sys.argv[1:] == ['--legal']
    if sys.argv[1:] and not legal:
        raise ValueError('expected --legal or no arguments')
    binary = build(legal=legal)
    print('STAGED:', binary, '; lead card_run --threads 1 --timeout',
          590 if legal else 1150, '; binary argument: 12345', flush=True)
    host = build(host=True, legal=legal)
    # The approved red already demonstrated both seeded tree failures once.
    print('HOST MODEL ONLY: all routes; native correctness/timing pending', flush=True)
    return subprocess.run([str(host), '12345', '--correctness'], cwd=OUT).returncode


if __name__ == '__main__':
    sys.exit(main())
