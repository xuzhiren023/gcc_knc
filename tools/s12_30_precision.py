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
import storage

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
        # Index arrays arrive as a col/cols parameter or, in the struct
        # nests, through a ->cols field load.
        sources = {self.param('col'), self.param('cols')} - {None}
        sources |= {name for name, value in self.defs.items()
                    if re.search(r'->cols$', value)}
        result = []
        for bb, arg in self.hints:
            ancestors = self.ancestry(arg)
            if self.param('x') not in ancestors:
                continue
            for name in ancestors:
                address = self.address(name)
                if address and sources & self.ancestry(address):
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
    """Default-on automatic hints in strict indexed reductions only."""
    OUT.mkdir(exist_ok=True)
    source_flags = ['-std=gnu99', '-DPHASE2_T1', '-march=knc',
                    '--sysroot=' + str(runner.sysroot)]
    enabled = '-mknc-indirect-prefetch'
    disabled = '-mno-knc-indirect-prefetch'
    eligible = ('sparse_rows', 'sparse_slice', 'sparse_hpcg')
    counts = {}
    default_assembly = None
    for mode, options, expected in (
            ('controls', ['-O2', '-ffp-contract=off', disabled,
                          '-fprefetch-loop-arrays'], False),
            ('disabled', ['-O2', '-ffp-contract=off', disabled,
                          '-fprefetch-loop-arrays'], False),
            ('default', ['-O2', '-ffp-contract=off'], True),
            ('off', ['-O2', '-ffp-contract=off', enabled,
                     '-fprefetch-loop-arrays'], True),
            ('fast', ['-O2', '-ffp-contract=fast', enabled,
                      '-fprefetch-loop-arrays'], True),
            ('min4', ['-O2', '-ffp-contract=off', MIN_TRIPS + '4'], True),
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
                        if mode == 'controls' else (*eligible, 'alias_bounds'))
            if bounds_dump.exists():
                chunks = re.split(r'^;; Function (\w+) .*$',
                                  bounds_dump.read_text(), flags=re.M)
                bounds_bodies = dict(zip(chunks[1::2], chunks[2::2]))
            missing = [name for name in required if name not in bounds_bodies]
            runner.result('t1 sparse ' + mode + ' pre-ivopts bounds dump',
                          ['missing aprefetch function ' + name for name in missing])
        assembly = asm_bodies(asm.read_text())
        if mode == 'default':
            default_assembly = assembly
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
        if mode == 'off':
            runner.result('t1 sparse default-on probe identity',
                          [name + ' differs from default -O2'
                           for name in (*eligible, 'volatile_indices',
                                        'sentinel_slice', 'alias_bounds')
                           if default_assembly is None
                           or assembly[name] != default_assembly[name]])
        for name in (*eligible, 'volatile_indices', 'sentinel_slice', 'alias_bounds'):
            want = expected and name in eligible
            graph = Gimple(bodies[name])
            found = bool(graph.indirect())
            errors = []
            if expected and name == 'alias_bounds':
                # A guarded row-local hint is legal; only cross-row
                # speculation is forbidden when output may change row[].
                if Gimple(bounds_bodies.get(name, '')).cross_row('csr'):
                    errors.append('later-row hint crosses an aliasing bounds store')
            elif found != want:
                errors.append(('missing' if want else 'unexpected') + ' automatic indirect prefetch')
            if want:
                bounds_graph = Gimple(bounds_bodies.get(name, ''))
                if 'disabled' not in counts or counts[mode][name] <= counts['disabled'][name]:
                    errors.append('vprefetch count must exceed switch-off with stream hints on')
                # The hinted arm is chosen at run time from a locality
                # sample (one FP64 line apart), never from the count alone.
                if not re.search(r'Bounded indirect prefetch in loop \d+: [^\n]*'
                                 r'locality sample of 3, more than 8 apart',
                                 bounds_bodies.get(name, '')):
                    errors.append('hinted arm lacks the locality sample')
                if mode == 'min4' and (default_assembly is None
                                       or assembly[name] == default_assembly[name]):
                    errors.append('row cutoff parameter has no effect')
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

    # Preserve the scalar baseline comparison with the current compiler's
    # explicit switch-off build now that plain -O2 enables the new policy.
    baselines = []
    for label, extra in (('plain', []), ('novect', ['-fno-tree-vectorize'])):
        asm = OUT / ('phase1-baseline-' + label + '.s')
        runner.command(runner.cc, *runner.cc_flags, '-O2', '-std=gnu99',
                       '--sysroot=' + str(runner.sysroot), disabled,
                       '-march=knc', '-ffp-contract=off', '-DPREFIX=knc_',
                       *extra, '-S', SOURCE, '-o', asm)
        baselines.append(asm_bodies(asm.read_text())['knc_scalar'])
    runner.result('t1 switch-off -O2 scalar baseline identity',
                  [] if baselines[0] == baselines[1]
                  else ['switch-off -O2 scalar function differs with vectorization disabled; inspect assembly'])
    runner.result('t1 HPCG application-shaped recognition',
                  ['see hpcg-shapes on/off failures above'] if hpcg_shapes_t1() else [])
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


# Proof slots: name, switch, contraction.  min4 is the default-on compiler
# with the cutoff at its minimum; twin is switch-off code with two copies
# of the plain nest in one function; manual is the hand-written policy.
PROOF_SLOTS = (('donor', False, 'off'), ('knc', False, 'off'),
               ('enabled', True, 'off'), ('fast', True, 'fast'),
               ('min4', True, 'off'), ('twin', False, 'off'),
               ('manual', False, 'off'))
MIN_TRIPS = '--param=knc-indirect-prefetch-min-trips='


def build_compiler_proof():
    """Stage legal guard/timing fixtures with generated and manual hints.

    This requires the lead's built gcc2 compiler.  Assembly plus the
    aprefetch dump must demonstrate actual automatic cross-row hints;
    a scalar fallback cannot masquerade as a compiler correctness proof.
    """
    project = ROOT.parent.parent
    gcc = Path(storage.gcc_build_dir(project, '2')) / 'gcc'
    objects = []
    for name, enabled, contract in PROOF_SLOTS:
        cc = corpus.compiler_path(corpus.DONOR) if name == 'donor' else gcc/'xgcc'
        flags = ['-O2', '-std=gnu99', '-ffp-contract=' + contract,
                 '-DLEGAL_PROOF', '-DCOMPILER_PROOF', '-DPREFIX=' + name + '_']
        if name in ('manual', 'twin'):
            flags += ['-D' + name.upper() + '_PROOF=1']
        if name != 'donor':
            flags += ['-B' + str(gcc) + '/', '-march=knc',
                      '--sysroot=' + str(TC/'sysroot'),
                      '-mknc-indirect-prefetch' if enabled else '-mno-knc-indirect-prefetch']
        if name == 'min4':
            flags += [MIN_TRIPS + '4']
        stem = OUT/('compiler-' + name)
        asm, obj, dump = stem.with_suffix('.s'), stem.with_suffix('.o'), stem.with_suffix('.aprefetch')
        dump.unlink(missing_ok=True)
        run(cc, *flags, '-fdump-tree-aprefetch-details=' + str(dump), '-S', SOURCE, '-o', asm)
        run(TC/'cross/bin/k1om-mpss-linux-as', '--march=k1om', asm, '-o', obj)
        run(sys.executable, ROOT/'tools/knc_lint', asm, obj)
        run(TC/'cross/bin/k1om-mpss-linux-size', '-A', obj)
        assembly = asm_bodies(asm.read_text())
        for layout in ('csr', 'hpcg', 'lone'):
            suffix = '_scalar' if layout == 'lone' else '_raw'
            body = assembly[name + '_' + layout + suffix]
            print('STATIC_HINTS', name, layout, len(re.findall(r'\bvprefetch\w*\b', body)), flush=True)
            # A zero kept on the x87 stack across a nest shows as copies of
            # st(0); the twin control must reproduce what switch-on has.
            print('X87_ZERO_COPIES', name, layout, len(re.findall(r'\bfld\s+%st', body)), flush=True)
        if enabled:
            # Require the recognized form, not merely some indirect hint:
            # a row-local fallback cannot prove cross-row bounds.
            if not dump.exists():
                raise RuntimeError('missing compiler proof aprefetch dump: ' + str(dump))
            chunks = re.split(r'^;; Function (\w+) .*$', dump.read_text(), flags=re.M)
            bodies = dict(zip(chunks[1::2], chunks[2::2]))
            for function, shape in (('csr_raw', 'future row bound'),
                                    ('hpcg_raw', 'next-row pointers'),
                                    ('lone_scalar', 'row-local bound'),
                                    ('shape_spmv', 'next-row pointers'),
                                    ('shape_forward', 'next-row pointers'),
                                    ('shape_backward', 'next-row pointers')):
                body = bodies.get(name + '_' + function, '')
                if not re.search(r'Bounded indirect prefetch in loop \d+: ' + shape
                                 + r'.*locality sample', body):
                    raise RuntimeError('compiler proof did not transform ' + name + '_' + function)
                if '__builtin_prefetch' not in body:
                    raise RuntimeError('compiler proof lacks emitted hints: ' + name + '_' + function)
        objects.append(obj)
    binary = OUT/'compiler-gate-hpcg'
    run(corpus.compiler_path(corpus.DONOR), '-O2', '-std=gnu99',
        '-ffp-contract=off', '-fno-tree-vectorize', '-DLEGAL_PROOF',
        '-DCOMPILER_PROOF', '-DDRIVER', SOURCE, *objects,
        *corpus.link_paths(), '-lrt', '-lm', '-o', binary)
    run(sys.executable, ROOT/'tools/knc_lint', binary)
    print('STAGED:', binary, '; lead card_run --threads 1 --timeout 590; argument: 12345',
          '(add --correctness for the guard suites and decisions without timing)', flush=True)
    return 0


def host_shapes():
    """Host model of the compiler-proof driver, control flow only.

    Plain C and the hand-written policy must pass every fixture, and the
    policy must take the expected arm in every timing case (stencil, random,
    ascending, below the cutoff).  Then one slot gets a next-row hint with
    no count/stored-vector overlap test: only that slot's overlap child
    may die, which shows that the fixture can fail.  Seeds 2 and 3 break
    the hand-written sample (no row cutoff; no nonempty test): the manual
    slot, and no other, must fault.
    """
    cc = TC/'cygwin/bin/gcc'
    flags = ['-O2', '-std=gnu99', '-ffp-contract=off', '-mfpmath=387',
             '-fexcess-precision=fast', '-DHOST_MODEL', '-DLEGAL_PROOF', '-DCOMPILER_PROOF']
    seeded = 'FAIL shape child struct-spmv count-in-stored-vector knc-switch-on status='
    errors = []
    for seed in (0, 1, 2, 3):
        objects = []
        for name, _, _ in PROOF_SLOTS:
            obj = OUT/('host-shape-' + name + '.o')
            run(cc, *flags, '-DPREFIX=' + name + '_', '-DMANUAL_PROOF=' + str(int(name == 'manual')),
                '-DTWIN_PROOF=' + str(int(name == 'twin')),
                '-DSHAPE_SEED=' + str(int(seed == 1 and name == 'enabled')),
                '-DSAMPLE_SEED=' + str(seed-1 if seed > 1 and name == 'manual' else 0),
                '-c', SOURCE, '-o', obj)
            objects.append(obj)
        binary = OUT/'host-shapes.exe'
        run(cc, *flags, '-DDRIVER', SOURCE, *objects, '-lrt', '-lm', '-o', binary)
        result = subprocess.run([str(binary), '12345', '--correctness'], cwd=OUT,
                                stdout=subprocess.PIPE, text=True)
        lines = result.stdout.splitlines()
        failed = [line for line in lines if line.startswith('FAIL')]
        shapes = sum(line.startswith('SHAPES') for line in lines)
        decisions = [line for line in lines if line.startswith('DECISION')]
        print('HOST_SHAPES seed=' + str(seed), 'exit=' + str(result.returncode),
              'shape_children=' + str(shapes), 'decisions=' + str(len(decisions)),
              *failed, sep=' | ', flush=True)
        if seed == 1:
            if not result.returncode or len(failed) != 1 or not failed[0].startswith(seeded):
                errors.append('seeded stale-count hint was not caught as the only failure')
            continue
        if seed:
            if (not result.returncode or not failed
                    or not all('knc-handwritten-policy' in line and 'status=11' in line
                               for line in failed)):
                errors.append('seeded sample defect %d was not caught in the manual slot alone' % (seed-1))
            continue
        print(*decisions, sep='\n', flush=True)
        arms = {'hint': 0, 'scalar': 0}
        for line in decisions:
            arms[line.rsplit('=', 1)[1]] += 1
        if result.returncode or failed or shapes != 6*len(PROOF_SLOTS):
            errors.append('plain C or the hand-written policy failed the fixtures')
        if len(decisions) != 32 or not arms['hint'] or not arms['scalar']:
            errors.append('expected 32 policy decisions, some for each arm')
    print(('FAIL ' + '; '.join(errors)) if errors else
          'PASS host shapes: fixtures and policy decisions pass; the seeded stale-count hint and both seeded samples fault',
          flush=True)
    return int(bool(errors))


def ice_sweep(corpora=('gcc.c-torture/compile', 'gcc.dg/vect')):
    """Compile the lane's torture/vector corpora with the new switch enabled.

    This is an ICE check, not a dg diagnostic/assembly/native verdict.
    Unsupported options and ordinary compile errors are counted separately.
    """
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor
    import shlex
    import signal
    project = ROOT.parent.parent
    gcc = Path(storage.gcc_build_dir(project, '2')) / 'gcc'
    tests = Path(storage.gcc_tree(project, '2')) / 'gcc/testsuite'
    totals = Counter()
    report = OUT/'ice-sweep.log'
    def compile_one(job):
        source, level = job
        options = [flag for match in re.finditer(
            r'\{\s*dg-(?:additional-)?options\s+(?:"((?:\\.|[^"\\\n])*)"|([^\s{}]+))'
            r'(\s*\{\s*target\b)?', source.read_text(errors='replace'))
            if match[3] is None
            for flag in shlex.split(match[1] if match[1] is not None else match[2])
            if not flag.startswith(('-fdump', '-save-temps', '-flto'))]
        command = list(map(str, [gcc/'xgcc', '-B' + str(gcc) + '/',
                       *options, '-' + level, '-march=knc', '-mknc-indirect-prefetch',
                       '--sysroot=' + str(TC/'sysroot'), '-w', '-S', source, '-o', '/dev/null']))
        with subprocess.Popen(command, cwd=OUT, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              start_new_session=True) as proc:
            try:
                diagnostic, _ = proc.communicate(timeout=120)
                kind = ('ICE' if re.search(r'internal compiler error|segmentation fault', diagnostic, re.I)
                        else 'compile-error' if proc.returncode else 'compiled')
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                diagnostic, _ = proc.communicate()
                kind = 'timeout'
        return level, kind, source.relative_to(tests), command, diagnostic
    with report.open('w', newline='\n') as log:
        for corpus_path in corpora:
            sources = sorted((tests/corpus_path).rglob('*.c'))
            if not sources:
                raise RuntimeError('empty ICE corpus ' + corpus_path)
            counts = Counter()
            with ThreadPoolExecutor(max_workers=4) as pool:
                for level, kind, name, command, diagnostic in pool.map(
                        compile_one, ((source, level) for level in ('O2', 'O3') for source in sources)):
                    counts[level, kind] += 1
                    totals[kind] += 1
                    if kind != 'compiled':
                        log.write(f'{level} {kind} {name}\n' + shlex.join(command) + '\n' + diagnostic + '\n')
            print('ICE_SWEEP', corpus_path, 'files=' + str(len(sources)), dict(counts), flush=True)
        print('ICE_SWEEP totals', dict(totals), 'details=' + str(report), flush=True)
    return int(bool(totals['ICE'] or totals['timeout']))


def hpcg_shapes_t1():
    """Focused recognition gate; native bounds safety remains a separate gate."""
    gcc = Path(storage.gcc_build_dir(ROOT.parent.parent, '2')) / 'gcc'
    failures = 0
    names = ('sparse_struct_spmv', 'sparse_struct_forward', 'sparse_struct_backward')
    for enabled in (False, True):
        stem = 'hpcg-shapes-' + ('on' if enabled else 'off')
        asm, dump = OUT/(stem + '.s'), OUT/(stem + '.aprefetch')
        dump.unlink(missing_ok=True)
        run(gcc/'xgcc', '-B' + str(gcc) + '/', '--sysroot=' + str(TC/'sysroot'),
            '-O2', '-march=knc', '-std=gnu99', '-ffp-contract=off', '-DPHASE2_T1',
            '-mknc-indirect-prefetch' if enabled else '-mno-knc-indirect-prefetch',
            '-fdump-tree-aprefetch-details=' + str(dump), '-S', SOURCE, '-o', asm)
        obj = asm.with_suffix('.o')
        run(TC/'cross/bin/k1om-mpss-linux-as', '--march=k1om', asm, '-o', obj)
        run(sys.executable, ROOT/'tools/knc_lint', asm, obj)
        chunks = re.split(r'^;; Function (\w+) .*$', dump.read_text(), flags=re.M)
        bodies = dict(zip(chunks[1::2], chunks[2::2]))
        assembly = asm_bodies(asm.read_text())
        # Scanner control: the hand-written struct next-row hint must be
        # seen as indirect, and is not a compiler transformation.
        control = bodies['explicit_struct']
        errors = []
        if not Gimple(control).indirect():
            errors.append('scanner misses the hand-written ->cols hint')
        if 'Bounded indirect prefetch' in control:
            errors.append('hand-written hint reported as a transformation')
        failures += bool(errors)
        print(('FAIL' if errors else 'PASS'), stem, 'explicit_struct', '; '.join(errors), flush=True)
        for name in names:
            body = bodies[name]
            cross_row = bool(re.search(r'Bounded indirect prefetch in loop \d+: next-row pointers'
                                       r'[^\n]*locality sample of 3, more than 8 apart', body))
            indirect = bool(Gimple(body).indirect())
            fold = r'\bfadd\w*\b' if name.endswith('spmv') else r'\bfsub\w*\b'
            errors = []
            if cross_row != enabled or indirect != enabled:
                errors.append('missing cross-row indexed hint' if enabled else 'unexpected indexed hint')
            if not re.search(fold, assembly[name]):
                errors.append('ordered scalar fold missing')
            if re.search(r'\bv(?:add|sub|fmadd|fmsub|fnmadd)\w*\b', assembly[name]):
                errors.append('unexpected vector fold or contraction')
            failures += bool(errors)
            print(('FAIL' if errors else 'PASS'), stem, name, '; '.join(errors), flush=True)
    return int(bool(failures))


def application_dumps(hpcg_only=False):
    """Inspect the actual class-A CG and HPCG translation units, without linking."""
    gcc = Path(storage.gcc_build_dir(ROOT.parent.parent, '2')) / 'gcc'
    sources = SHARED / 'corpus-build/sources'
    npb = sources / 'NPB3.4.2/NPB3.4-OMP'
    hpcg = sources / 'hpcg-3.1/src'
    flags = ['-B' + str(gcc) + '/', '--sysroot=' + str(TC/'sysroot'),
             '-O2', '-march=knc', '-mknc-indirect-prefetch', '-fopenmp']
    includes = ['-I' + str(SHARED/'corpus-build/gcc-knc/0/NPB-CG'),
                '-I' + str(npb/'common'), '-J' + str(OUT),
                '-fintrinsic-modules-path=' + str(gcc.parent/'k1om-mpss-linux/libgfortran')]
    cxx_headers = SHARED/'gcc-knc-16.2.0-2/k1om-mpss-linux/include/c++/16.2.0'
    cxx_flags = ['-DHPCG_NO_MPI', '-I' + str(hpcg), '-nostdinc++',
                 '-isystem', str(gcc.parent/'k1om-mpss-linux/libgomp')]
    for directory in (cxx_headers, cxx_headers/'k1om-mpss-linux', cxx_headers/'backward'):
        cxx_flags += ['-isystem', str(directory)]
    units = [('spmv', gcc/'xg++', hpcg/'ComputeSPMV_ref.cpp', cxx_flags),
             ('symgs', gcc/'xg++', hpcg/'ComputeSYMGS_ref.cpp', cxx_flags)]
    if not hpcg_only:
        run(gcc/'gfortran', *flags, *includes, '-c', npb/'CG/cg_data.f90',
            '-o', OUT/'application-cg-data.o')
        units.insert(0, ('cg', gcc/'gfortran', npb/'CG/cg.f90', includes))
    for name, cc, source, extra in units:
        dump = OUT/('application-' + name + '.aprefetch')
        dump.unlink(missing_ok=True)
        run(cc, *flags, *extra, '-fdump-tree-aprefetch-details=' + str(dump),
            '-S', source, '-o', OUT/('application-' + name + '.s'))
        if not dump.exists():
            raise RuntimeError('missing application dump: ' + str(dump))
        matches = [line for line in dump.read_text().splitlines()
                   if 'Bounded indirect prefetch' in line]
        print('APPLICATION_DUMP', name, 'transformations=' + str(len(matches)),
              *matches, 'path=' + str(dump), flush=True)
    return 0


def main():
    if sys.platform != 'cygwin':
        raise RuntimeError('use shared Cygwin python3')
    OUT.mkdir(exist_ok=True)
    os.environ['PATH'] = ':'.join(map(str, [TC/'cross/bin', TC/'cygwin/bin', os.environ['PATH']]))
    if sys.argv[1:] == ['--hpcg-shapes-t1']:
        return hpcg_shapes_t1()
    if sys.argv[1:] == ['--application-dumps']:
        return application_dumps()
    if sys.argv[1:] == ['--application-dumps', 'hpcg']:
        return application_dumps(hpcg_only=True)
    if sys.argv[1:] == ['--compiler-proof']:
        return build_compiler_proof()
    if sys.argv[1:] == ['--shape-host']:
        return host_shapes()
    if sys.argv[1:] == ['--ice-sweep']:
        return ice_sweep()
    if sys.argv[1:] == ['--ice-sweep', 'vect']:
        return ice_sweep(('gcc.dg/vect',))
    legal = sys.argv[1:] == ['--legal']
    if sys.argv[1:] and not legal:
        raise ValueError('expected --compiler-proof, --legal or no arguments')
    binary = build(legal=legal)
    print('STAGED:', binary, '; lead card_run --threads 1 --timeout',
          590 if legal else 1150, '; binary argument: 12345', flush=True)
    host = build(host=True, legal=legal)
    # The approved red already demonstrated both seeded tree failures once.
    print('HOST MODEL ONLY: all routes; native correctness/timing pending', flush=True)
    return subprocess.run([str(host), '12345', '--correctness'], cwd=OUT).returncode


if __name__ == '__main__':
    sys.exit(main())
