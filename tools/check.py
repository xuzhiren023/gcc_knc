#!/usr/bin/env python3
"""Run t0 (regressions), t1 (code generation), t2 (link ABI).

Usage: python tools/check t0 t1 t2 --compiler donor
Use --record tests/baseline/donor-gcc5.txt to record a measured baseline.
gcc16 uses the shared build tree's xgcc driver. T3 is reserved for
tools/card_run; this runner never executes target programs on the host.
"""
import argparse
import importlib
import json
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys
import tempfile
import time

import storage

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
FUNCTIONS = ('affine_f32', 'affine_f64', 'recurrence_f32')
PACKED = re.compile(r'\bv(?:addn?|subr?|mul|div|max|min|sqrt|rcp(?:23)?|rsqrt(?:23)?|fmadd\w*|fmsub\w*|fnmadd\w*|fnmsub\w*)(?:ps|pd)\b.*%zmm\d+\b')

# Each entry supplies its CLI help and handlers for the tiers it selects.
# Imports stay lazy so T0 and source-only selections need no probe modules.
SELECTIONS = {
    'tune_align': ('S8-08 -mtune=knc aligns functions to 64 bytes', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-tune-align*.c'))}),
    'tune_prefix': ('S8-08 -mtune=knc avoids 0x66-prefixed forms', {
        't1': lambda runner: runner.t1_sources([runner.source_dir / 'knc-tune-prefix.c'])}),
    'storent': ('S8-13 no-read streaming stores for write-only loops beyond L2', {
        't1': lambda runner: importlib.import_module('storent').t1(runner),
        't2': lambda runner: importlib.import_module('storent').t2(runner)}),
    'align_data': ('S8-14 64-byte data alignment and KNC cache parameters', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-align-*.c'))}),
    'line_pad': ('S8-10 64-byte lines for OpenMP shared blocks and per-thread arrays', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-pad-*.c'))}),
    'int_madd': ('S8-07 V16SI multiply-add as vpmadd231d', {
        't1': lambda runner: runner.t1_sources([runner.source_dir / 'knc-vec-imadd.c'])}),
    'knc_scheduler': ('S6-06 vector/scalar pairing and address separation', {
        't1': lambda runner: runner.t1_sources([runner.source_dir / 'knc-scheduler.c'])}),
    'knc_costs': ('S6-05 measured KNC vectorizer cost decisions', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-cost-*.c'))}),
    'loop_reports': ('S6-04 KNC per-loop optimization reports', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-loop-report-*.c'))}),
    'short_vector_abi': ('S5-21 V16HI stack argument and hidden result pointer', {
        't1': lambda runner: importlib.import_module('scalar_abi').t1_short_vector(runner),
        't2': lambda runner: importlib.import_module('scalar_abi').t2_short_vector(runner)}),
    'byte_word': ('S5-16 byte/word converting loads, stores and alignment', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-convert-byte-*.c'))}),
    'fp_minmax': ('S5-15 FP min/max and reductions', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-fp-minmax-*.c'))}),
    'gather_scatter': ('S5-13 signed 16-lane indexed loads and stores', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-gather16-*.c'))}),
    'division': ('S5-11 correctly rounded FP32 division and masked tail', {
        't1': lambda runner: runner.t1_sources([runner.source_dir / 'knc-div-f32.c'])}),
    'sqrt': ('S5-10 correctly rounded FP32 square root', {
        't1': lambda runner: (runner.t1_sources([runner.source_dir / 'knc-vec-autovec.c']),
                              importlib.import_module('s5_10_checks').t1(runner))}),
    'conversions': ('S5-08 same-width signed and unsigned conversions', {
        't1': lambda runner: runner.t1_sources([runner.source_dir / 'knc-convert-same.c'])}),
    'reductions': ('S5-07 reduction trees and strict FP ordering', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-reduce-*.c'))}),
    'xi_copy': ('S3-20 XI memory copies and byte element updates at O0, O1 and O2', {
        't1': lambda runner: runner.t1_sources(runner.source_dir.glob('knc-xi-copy-O*.c'))}),
    'native_tls': ('S3-14 native TLS sequences versus the donor at O2, PIC and O0', {
        't1': lambda runner: importlib.import_module('native_tls').t1(runner)}),
    'affine_fortran': ('S3-08 Fortran affine acceptance rows (GCC 16)', {
        't1': lambda runner: importlib.import_module('affine_fortran').t1(runner),
        't2': lambda runner: importlib.import_module('affine_fortran').t2(runner)}),
    'fast_math': ('S2-15 fast-math startup links and MXCSR disassembly', {
        't2': lambda runner: importlib.import_module('fast_math').t2(runner)}),
    'libgcc_link': ('S2-07 fork helper link only', {
        't2': lambda runner: importlib.import_module('libgcc').link(runner, 'gcc16')}),
    'libgcc': ('S2-07 static runtime archive lint and helper links', {
        't2': lambda runner: importlib.import_module('libgcc').t2(runner)}),
    'atomics': ('S2-06 atomic widths, libatomic fallbacks and spin hint', {
        't1': lambda runner: importlib.import_module('atomics').t1(runner),
        't2': lambda runner: importlib.import_module('atomics').t2(runner)}),
    'x87_spill': ('S2-05 x87 forms, donor truth tables and XI spill alignment', {
        't1': lambda runner: importlib.import_module('x87_spill').t1(runner)}),
    'secondary_reload': ('S2-04 Fortran address-loss reproducer and mixed GPR/zmm pressure', {
        't1': lambda runner: importlib.import_module('secondary_reload').t1(runner),
        't2': lambda runner: importlib.import_module('secondary_reload').t2(runner)}),
    'varargs_abi': ('S2-03 AL, register save area and varargs cross-links only', {
        't1': lambda runner: importlib.import_module('varargs_abi').t1(runner),
        't2': lambda runner: importlib.import_module('varargs_abi').t2(runner)}),
    'scalar_abi': ('S2-02 donor ABI probes and bidirectional cross-links only', {
        't1': lambda runner: importlib.import_module('scalar_abi').t1(runner),
        't2': lambda runner: importlib.import_module('scalar_abi').t2(runner)}),
    'abi_gaps': ('S3-15 packed varargs and ms_abi diagnostics', {
        't1': lambda runner: importlib.import_module('scalar_abi').t1_abi_gaps(runner)}),
    'link_defaults': ('S1-06 T1 ABI macros and T2 integer link with fork-built runtime', {
        't1': lambda runner: runner.t1_sources([runner.source_dir / 'knc-link-defaults.c']),
        't2': lambda runner: runner.t2_link_defaults()}),
    'vector': ('S3 vector code generation probes (knc-vec-*.c)', {
        't1': lambda runner: importlib.import_module('knc_vector').t1(runner)}),
    'vector_unaligned': ('S3-05 unaligned packed moves only', {
        't1': lambda runner: importlib.import_module('knc_vector').t1_unaligned(runner)}),
    'vector_byte_aligned': ('S3-21 byte-aligned packed accesses at O2 and O3', {
        't1': lambda runner: importlib.import_module('knc_vector').t1_byte_aligned(runner)}),
    'vector_fp': ('S3-06 packed FP arithmetic, broadcasts and generic expressions', {
        't1': lambda runner: importlib.import_module('knc_vector').t1_fp(runner)}),
}


def loop_lines(source):
    """Map each affine function to its loop's source line, for opt-info scans."""
    result = {}
    function = None
    for number, line in enumerate(source.splitlines(), 1):
        for name in FUNCTIONS[:2]:
            if re.match(r'\s*' + name + r'\s*\(', line):
                function = name
        if function and re.search(r'\bfor\s*\(', line):
            result[function] = number
            function = None
    return result


def function_body(assembly, name):
    # Local labels and other functions must never donate instructions to a scan.
    name = re.escape(name)
    match = re.search(r'^' + name + r':\s*\n(.*?)^\s*\.size\s+' + name + r'\s*,',
                      assembly, re.M | re.S)
    return match[1] if match else None


def loops(body):
    """Find CFG cycles closed by layout-backward jumps, including cold blocks."""
    lines = [line.split('#', 1)[0] for line in body.splitlines()]
    labels = {}
    starts = {0, len(lines)}
    jumps = {}
    for i, line in enumerate(lines):
        label = re.match(r'\s*([\w.$]+):', line)
        if label:
            labels[label[1]] = i
            starts.add(i)
        # Accept either operand order for KNC mask branches.
        branch = re.match(r'\s*(j\w+|ret\w*)\b(.*)', line)
        if branch:
            target = re.fullmatch(r'\s*(?:%k[0-7]\s*,\s*)?([\w.$]+)'
                                  r'(?:\s*,\s*%k[0-7])?\s*',
                                  branch[2])
            jumps[i] = (branch[1], target[1] if target else None)
            starts.add(i + 1)

    boundaries = sorted(starts)
    blocks = list(zip(boundaries, boundaries[1:]))
    block_at = {start: b for b, (start, end) in enumerate(blocks)}
    edges = [set() for block in blocks]
    backedges = []
    for b, (start, end) in enumerate(blocks):
        opcode, target = jumps.get(end - 1, ('', None))
        if target in labels:
            header = block_at[labels[target]]
            edges[b].add(header)
            if labels[target] < end - 1:
                backedges.append((b, header))
        if not opcode.startswith(('jmp', 'ret')) and b + 1 < len(blocks):
            edges[b].add(b + 1)
    predecessors = [set() for block in blocks]
    for b, successors in enumerate(edges):
        for successor in successors:
            predecessors[successor].add(b)

    def reachable(seed, graph, header):
        # Never cross the header again: it closes this cycle.
        seen = {seed}
        pending = [seed]
        while pending:
            for successor in graph[pending.pop()]:
                if successor != header and successor not in seen:
                    seen.add(successor)
                    pending.append(successor)
        return seen

    for latch, header in backedges:
        forward = reachable(header, edges, header)
        if latch not in forward:
            continue  # A backward jump alone does not establish a loop.
        backward = reachable(latch, predecessors, header) if latch != header else set()
        members = (forward & backward) | {header}
        yield '\n'.join(line for b in sorted(members)
                        for line in lines[blocks[b][0]:blocks[b][1]])


def scan_t1(assembly, report, source, fast=False):
    failures = []
    locations = loop_lines(source)
    for name in FUNCTIONS:
        body = function_body(assembly, name)
        if body is None:
            failures.append(name + ': missing function boundary')
            continue
        body = '\n'.join(line.split('#', 1)[0] for line in body.splitlines())
        if name == 'recurrence_f32':
            if PACKED.search(body):
                failures.append(name + ': packed zmm FP arithmetic in scalar recurrence')
            continue
        suffix = 'ps' if name.endswith('f32') else 'pd'
        patterns = ([r'vfmadd\w*' + suffix] if fast else ['vmul' + suffix, 'vadd' + suffix])
        # A gather/scatter retry (jknzd back to the insn's own label) is not
        # a loop of the function.
        def retry_only(loop):
            lines = [line for line in loop.splitlines()
                     if line.strip() and not re.match(r'\s*[\w.$]+:', line)]
            return bool(lines) and all(re.search(r'\bv\w*(?:gather|scatter)\w*\b|\bjknzd\b', line)
                                       for line in lines)
        candidates = [loop for loop in loops(body) if not retry_only(loop)]
        scalar_loops = [loop for loop in candidates if not PACKED.search(loop)]
        # S8-02 (ADR-0009 amendment 1 point 9): GCC 16's remainder is a masked
        # gather/scatter epilogue and no x87 loop remains; the donor keeps the
        # x87 remainder loop.
        masked_tail = re.search(r'\bv(?:gather|scatter)d' + suffix + r'\s[^\n]*\{%k[1-7]\}', body)
        if masked_tail:
            if scalar_loops:
                failures.append(name + ': x87 loop remains beside the masked tail')
        elif not scalar_loops or any('%zmm' in loop for loop in scalar_loops):
            failures.append(name + ': missing scalar tail or packed access in scalar loop')
        elif not all(re.search(r'\bfmul\w*\b', loop)
                     and re.search(r'\bfadd\w*\b', loop) for loop in scalar_loops):
            failures.append(name + ': peel/remainder arithmetic is not x87')
        if not any(PACKED.search(loop) for loop in candidates):
            failures.append(name + ': no packed `zmm` arithmetic')
        elif not any(all(re.search(r'\b' + p + r'\b[^\n]*%zmm\d+\b', loop)
                         for p in patterns) for loop in candidates):
            failures.append(name + ': main loop lacks ' + ' and '.join(patterns))
        if not fast and re.search(r'\bv(?:f[mn]|fnm)\w*(?:ps|pd)\b', body):
            failures.append(name + ': fused arithmetic with contraction off')
        line = locations.get(name)
        if line is None or not re.search(r'(?:^|[/\\\s])loops\.c:' + str(line) +
                                         r'(?::\d+)?:[^\n]*\b(?:LOOP VECTORIZED|loop vectorized|vectorized loop)\b', report):
            failures.append(name + ': no -fopt-info-vec report for this loop')
    return failures


def scan_elf(data):
    try:
        if data[:6] != b'\x7fELF\x02\x01':
            return ['not a little-endian ELF64 file']
        failures = []
        if struct.unpack_from('<H', data, 18)[0] != 181:
            failures.append('ELF machine is not 181 (EM_K1OM)')
        offset = struct.unpack_from('<Q', data, 32)[0]
        size, count = struct.unpack_from('<HH', data, 54)
        interpreters = []
        for i in range(count):
            entry = offset + i * size
            if struct.unpack_from('<I', data, entry)[0] == 3:
                start = struct.unpack_from('<Q', data, entry + 8)[0]
                length = struct.unpack_from('<Q', data, entry + 32)[0]
                interpreters.append(data[start:start + length])
        if interpreters != [b'/lib64/ld-linux-k1om.so.2\0']:
            failures.append('wrong or missing KNC interpreter')
        return failures
    except (struct.error, IndexError):
        return ['truncated ELF headers']


def versioned_symbols(text, undefined):
    result = set()
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].endswith(':'):
            continue
        if (fields[6] == 'UND') != undefined:
            continue
        name = fields[7].replace('@@', '@')
        if '@' in name:
            result.add(name)
    return result


class Runner:
    function_body = staticmethod(function_body)
    root = ROOT

    def __init__(self, args):
        self.args = args
        manifest = json.loads((ROOT / 'toolchain/manifest.json').read_text())
        self.tc = PROJECT / manifest['root']
        self.sysroot = self.tc / manifest['sysroot']
        self.gcc_build = Path(storage.gcc_build_dir(PROJECT))
        build = self.gcc_build / 'gcc'
        self.cc = Path(args.cc) if args.cc else (build / 'xgcc' if args.compiler == 'gcc16' else self.tool('gcc'))
        self.cc_flags = ['-B' + str(build) + '/'] if args.compiler == 'gcc16' else []
        self.env = os.environ.copy()
        self.env['PATH'] = os.pathsep.join(str(self.tc / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + self.env.get('PATH', '')
        output_root = PROJECT / '.work/_shared/check'
        output_root.mkdir(parents=True, exist_ok=True)
        self._output = tempfile.TemporaryDirectory(dir=output_root,
                                                  prefix=args.compiler + '-',
                                                  ignore_cleanup_errors=True)
        self.out = Path(self._output.name)
        self.lines = []
        self.failed = False
        self.fixture = ROOT / 'tests/acceptance/m1_affine'
        self.source_dir = ROOT / 'tests/t1'
        self.flags = ['-O2', '-ftree-vectorize', '--sysroot=' + str(self.sysroot)]
        self.off_object = None

    def tool(self, name):
        return self.tc / ('cross/bin/k1om-mpss-linux-' + name + '.exe')

    def say(self, text):
        print(text, flush=True)
        self.lines.append(text)

    def result(self, label, failures):
        self.failed |= bool(failures)
        self.say(('FAIL ' if failures else 'PASS ') + label + (': ' + '; '.join(failures) if failures else ''))

    def command(self, *args, check=True, timeout=60):
        result = subprocess.run([str(a) for a in args], env=self.env, cwd=ROOT,
                                text=True, errors='replace', stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout)
        if not check:
            return result
        if result.returncode:
            raise RuntimeError('command %s exited %d: %s' %
                               (' '.join(str(a) for a in args), result.returncode, result.stdout[-2500:]))
        return result.stdout

    def t0(self):
        # Compiler regressions only; pm/git/dispatch suites have separate runners.
        for directory, pattern in (('tests/regress', 'test_*.py'),
                                   ('tests/tools', 'test_doctor.py'),
                                   ('tests/tools', 'test_portability.py'),
                                   ('tests/tools', 'test_knc_lint.py')):
            label = directory + '/' + pattern
            try:
                # 1800 s: the regress suite takes about 380 s alone and over 900 s while the
                # other GCC lane builds or runs torture (S8-18, two trees; 2026-11-09).
                output = self.command(sys.executable, '-m', 'unittest', 'discover', '-s', directory, '-p', pattern, timeout=1800)
                self.say('PASS t0 ' + label + ': ' + ' '.join(output.strip().splitlines()[-3:]))
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                self.result('t0 ' + label, [str(error)])

    def run_selections(self, tier):
        selected = False
        args = getattr(self, 'args', None)
        for name, (help_text, handlers) in SELECTIONS.items():
            if not getattr(args, name, False) or tier not in handlers:
                continue
            selected = True
            try:
                handlers[tier](self)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                self.result(tier + ' ' + name.replace('_', '-') + ' infrastructure', [str(error)])
        return selected

    def t1(self):
        if self.run_selections('t1'):
            return
        if getattr(getattr(self, 'args', None), 'compiler', None) == 'gcc16':
            import scalar_abi
            scalar_abi.t1(self)
            import secondary_reload
            secondary_reload.t1(self)
            self.t1_sources()
            import s5_10_checks
            s5_10_checks.t1(self)
            import knc_vector
            knc_vector.t1_byte_aligned(self)
            import native_tls
            native_tls.t1(self)
        source = (self.fixture / 'loops.c').read_text()
        for mode in ('off', 'fast'):
            asm = self.out / ('loops-' + mode + '.s')
            obj = self.out / ('loops-' + mode + '.o')
            report = self.command(self.cc, *self.cc_flags, *self.flags, '-ffp-contract=' + mode,
                                  '-fopt-info-vec-all', '-S', self.fixture / 'loops.c', '-o', asm)
            (self.out / ('loops-' + mode + '.vec')).write_text(report)
            self.command(self.tool('as'), '--march=k1om', asm, '-o', obj)
            self.result('t1 ' + mode + ' assembly --march=k1om', [])
            self.command(sys.executable, ROOT / 'tools/knc_lint', asm, obj)
            self.result('t1 ' + mode + ' knc_lint', [])
            self.result('t1 ' + mode + ' function scans', scan_t1(asm.read_text(), report, source, mode == 'fast'))
            if mode == 'off':
                self.off_object = obj
        if getattr(getattr(self, 'args', None), 'compiler', None) == 'gcc16':
            import affine_fortran
            affine_fortran.t1(self)

    def t1_sources(self, sources=None):
        selected = (s for s in self.source_dir.glob('*.c')
                    if not s.name.startswith('knc-abi-')
                    and s.name not in ('knc-vec-byte-aligned.c', 'knc-tls.c',
                                       'knc-short-vector.c'))
        for source in sorted(selected if sources is None else sources):
            label = 't1 ' + source.name
            try:
                directives = []
                options = ['-O2']
                for line in source.read_text().splitlines():
                    match = re.match(r'^\s*//\s*(options|scan-asm|scan-asm-not|scan-output|scan-debug-info|error):\s*(.*)$', line)
                    function = re.match(r'^\s*//\s*(scan-asm-func|scan-asm-loop-not|scan-asm-loop-accumulators)\s+(\S+):\s*(.*)$', line)
                    if match:
                        kind, pattern = match.groups()
                        if kind == 'options':
                            options = shlex.split(pattern)
                        else:
                            directives.append((kind, None, pattern))
                    elif function:
                        directives.append(function.groups())
                errors = [directive for directive in directives if directive[0] == 'error']
                asm = self.out / (source.stem + '.s')
                obj = self.out / (source.stem + '.o')
                compiled = self.command(self.cc, *self.cc_flags, *options,
                                        '--sysroot=' + str(self.sysroot), '-S', source, '-o', asm,
                                        check=False)
                failures = []
                if errors:
                    for kind, name, pattern in errors:
                        if compiled.returncode == 0 or not re.search(pattern, compiled.stdout, re.M):
                            failures.append('error: ' + pattern)
                            break
                else:
                    if compiled.returncode:
                        raise RuntimeError('compile exited %d: %s' %
                                           (compiled.returncode, compiled.stdout[-2500:]))
                    # --help=target reports defaults without producing assembly.
                    output_only = bool(directives) and all(
                        kind == 'scan-output' for kind, name, pattern in directives)
                    assembly = '' if output_only else asm.read_text()
                    debug_info = ''
                    if any(kind == 'scan-debug-info' for kind, name, pattern in directives):
                        self.command(self.tool('as'), '--march=k1om', asm, '-o', obj)
                        debug_info = self.command(self.tool('readelf'), '--debug-dump=info', obj)
                    for kind, name, pattern in directives:
                        body = (compiled.stdout if kind == 'scan-output' else
                                debug_info if kind == 'scan-debug-info' else
                                function_body(assembly, name) if name else assembly)
                        if kind == 'scan-asm-loop-accumulators':
                            # Count distinct self-updating vector sums within
                            # one backward loop, never the horizontal epilogue.
                            counts = []
                            for loop in loops(body or ''):
                                accumulators = set()
                                for line in loop.splitlines():
                                    add = re.match(r'\s*vaddpd\s+(.+),\s*(%zmm\d+)(?:\{%k\d+\})?\s*$', line)
                                    if add and add[2] in re.findall(r'%zmm\d+\b', add[1]):
                                        accumulators.add(add[2])
                                counts.append(len(accumulators))
                            count = max(counts, default=0)
                            expected = int(pattern.rstrip('+'))
                            failed = (count < expected if pattern.endswith('+')
                                      else count != expected)
                            if failed:
                                failures.append('vector accumulators: got %d, expected %s'
                                                % (count, pattern))
                        elif kind == 'scan-asm-loop-not':
                            # Permit scalar-result transport after a reduction,
                            # but reject stack accumulators in a backward loop.
                            candidates = list(loops(body)) if body is not None else []
                            failed = not candidates or any(re.search(pattern, loop, re.M)
                                                           for loop in candidates)
                        else:
                            found = body is not None and re.search(pattern, body, re.M) is not None
                            failed = found if kind == 'scan-asm-not' else not found
                        if failed:
                            failures.append(kind + (' ' + name if name else '') + ': ' + pattern)
                            break
                    if not output_only:
                        if not debug_info:
                            self.command(self.tool('as'), '--march=k1om', asm, '-o', obj)
                        self.command(sys.executable, ROOT / 'tools/knc_lint', asm, obj)
                self.result(label, failures)
            except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError, re.error) as error:
                self.failed = True
                self.say('ERROR ' + label + ': ' + str(error))

    def t2(self):
        if self.run_selections('t2'):
            return
        if getattr(getattr(self, 'args', None), 'compiler', None) == 'gcc16':
            import scalar_abi
            scalar_abi.t2(self)
        elf, trace = self.t2_affine_link()
        self.t2_abi(elf, trace)
        if getattr(getattr(self, 'args', None), 'compiler', None) == 'gcc16':
            import affine_fortran
            affine_fortran.check_link(self, elf, trace)
        if getattr(getattr(self, 'args', None), 'compiler', None) == 'gcc16':
            self.say('T2 affine ABI cross-check: donor-built driver, GCC 16 loops')
            elf, trace = self.t2_affine_link(donor_driver=True)
            self.t2_abi(elf, trace)

    def t2_link_defaults(self):
        elf = self.out / 'knc-link-defaults.mic'
        # libgcc's all target installs its results into the GCC build dir.
        runtime = self.gcc_build / 'gcc'
        linked = self.command(self.cc, *self.cc_flags,
                              '-v', '-Wl,--trace', ROOT / 'tests/t2/knc-link-defaults.c',
                              '-o', elf, check=False)
        trace = linked.stdout
        self.say(trace)
        failures = []
        if not re.search(r'^ [^\n]*\bas(?:\.exe)?\s+[^\n]*--march=k1om(?:\s|$)', trace, re.M):
            failures.append('verbose assembler command lacks --march=k1om')
        if not re.search(r'^ [^\n]*\s-m\s+elf_k1om(?:\s|$)', trace, re.M):
            failures.append('verbose linker command lacks -m elf_k1om')
        for name in ('crtbegin.o', 'crtend.o', 'libgcc.a'):
            if str(runtime / name) not in trace:
                failures.append('link did not use fork-built ' + name)
        if str(self.tc / 'cross/lib/gcc') in trace:
            failures.append('link used donor runtime path')
        if linked.returncode:
            failures.append('integer link exited ' + str(linked.returncode))
        self.result('t2 K1OM driver defaults and fork-built runtime', failures)
        if linked.returncode:
            return
        self.t2_abi(elf, trace, link_defaults=True)
        dynamic = self.command(self.tool('readelf'), '--dynamic', '--wide', elf)
        needed = re.findall(r'\(NEEDED\)[^\n]*\[([^\]]+)\]', dynamic)
        self.say('T2 DT_NEEDED: ' + ', '.join(needed))
        self.result('t2 integer main needs no libgcc_s or libatomic',
                    ['unexpected DT_NEEDED ' + name for name in needed
                     if re.match(r'lib(?:gcc_s|atomic)\.so(?:\.|$)', name)])

    def t2_affine_link(self, donor_driver=False):
        loops_obj = self.off_object or self.out / 'loops-off.o'
        if not self.off_object:
            self.command(self.cc, *self.cc_flags, *self.flags, '-ffp-contract=off', '-c', self.fixture / 'loops.c', '-o', loops_obj)
            self.off_object = loops_obj
        driver = self.out / 'driver.o'
        elf = self.out / 'm1_affine.mic'
        driver_cc = [self.tool('gcc')] if donor_driver else [self.cc, *self.cc_flags]
        objects = [loops_obj]
        driver_flags = []
        if getattr(getattr(self, 'args', None), 'compiler', None) == 'gcc16':
            import affine_fortran
            objects.append(affine_fortran.compile_object(self))
            driver_flags.append('-DKNC_WITH_FORTRAN')
        self.command(*driver_cc, *self.flags, *driver_flags, '-ffp-contract=off', '-c', self.fixture / 'driver.c', '-o', driver)
        trace = self.command(self.cc, *self.cc_flags, '--sysroot=' + str(self.sysroot), driver, *objects,
                             '-Wl,--trace', '-o', elf)
        return elf, trace

    def t2_abi(self, elf, trace, link_defaults=False):
        for library in ('libc.so.6', 'ld-linux-k1om.so.2'):
            paths = []
            for line in trace.splitlines():
                resolved = re.search(r'\(([^()]+)\)\s*$', line)
                path = resolved[1] if resolved else line.strip()
                if path.endswith('/' + library):
                    paths.append(path)
            try:
                for path in paths:
                    Path(path).resolve().relative_to(self.sysroot.resolve())
            except ValueError:
                raise RuntimeError('link trace outside shared sysroot for ' + library + ': ' + repr(paths))
            if not paths:
                raise RuntimeError('link trace outside shared sysroot or missing ' + library + ': ' + repr(paths))
            self.say('T2 link trace: ' + '; '.join(paths))
        self.result('t2 ELF machine and interpreter', scan_elf(elf.read_bytes()))
        symbols = self.command(self.tool('readelf'), '--dyn-syms', '--wide', elf)
        required = versioned_symbols(symbols, True)
        symbol_versions = dict(re.findall(r'\b(\S+@\S+)\s+\((\d+)\)\s*$', symbols, re.M))
        # Resolve version requirements against each named library in the card sysroot,
        # never against host libraries or just a numeric maximum GLIBC version.
        versions = self.command(self.tool('readelf'), '--version-info', '--wide', elf)
        failures = [] if required else ['no versioned symbol requirements found']
        if link_defaults:
            for symbol in sorted(required):
                version = symbol.split('@', 1)[1]
                if version.startswith('GLIBC_'):
                    numbers = version[6:].split('.')
                    if not all(part.isdigit() for part in numbers) or tuple(map(int, numbers)) > (2, 21):
                        failures.append('symbol version exceeds glibc 2.21: ' + symbol)
        for library, section in re.findall(r'File:\s+(\S+)(.*?)(?=\n\s*0x[0-9a-f]+:\s+Version:|\Z)', versions, re.S):
            # libc and libm can both name GLIBC_2.14; the ELF version index
            # identifies which library must provide each imported symbol.
            indices = set(re.findall(r'Name:\s+\S+\s+Flags:[^\n]*Version:\s+(\d+)', section))
            needed = {symbol for symbol in required if symbol_versions.get(symbol) in indices}
            provider = next((self.sysroot / d / library for d in ('lib64', 'usr/lib64')
                             if (self.sysroot / d / library).is_file()), None)
            if provider is None:
                failures.append('missing card sysroot library ' + library)
            else:
                exports = versioned_symbols(self.command(self.tool('readelf'), '--dyn-syms', '--wide', provider), False)
                failures.extend(library + ' lacks ' + symbol for symbol in sorted(needed - exports))
            required -= needed
        failures.extend('unresolved version requirement ' + symbol for symbol in sorted(required))
        self.result('t2 symbol versions against card sysroot', failures)

    def run(self):
        with self._output:
            return self._run()

    def _run(self):
        start = time.monotonic()
        self.say('Compiler: ' + self.command(self.cc, *self.cc_flags, '--version').splitlines()[0])
        for program in ('ld', 'as'):
            self.say('Compiler ' + program + ': ' + self.command(self.cc, *self.cc_flags, '-print-prog-name=' + program).strip())
        self.say('Flags: -O2 -ftree-vectorize -ffp-contract=off / fast; separate driver translation unit')
        self.say('T2 ABI reference: ' + str(self.sysroot) + ' (no native card execution in t0-t2)')
        if self.args.compiler == 'donor':
            self.say('Development files: crt1.o, crti.o, crtn.o, libc.so, libc_nonshared.a from PhiWeather/.tools/knc-bootstrap/sysroot/usr/lib64; origin differs from card runtime. Runtime libraries and loader retained from card; T3 on card is the final proof.')
        for tier in self.args.tiers:
            try:
                getattr(self, tier)()
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                self.result(tier + ' infrastructure', [str(error)])
        self.say('Elapsed: %.2f seconds' % (time.monotonic() - start))
        if self.args.record:
            path = Path(self.args.record)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('\n'.join(self.lines) + '\n')
        return int(self.failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tiers', nargs='+', choices=('t0', 't1', 't2'))
    parser.add_argument('--compiler', choices=('donor', 'gcc16'), default='donor')
    parser.add_argument('--cc', help='override compiler path')
    for name, (help_text, handlers) in SELECTIONS.items():
        parser.add_argument('--' + name.replace('_', '-'), action='store_true', help=help_text)
    parser.add_argument('--varargs-case', action='append', default=[],
                        choices=[tag + '-' + role + '-' + level
                                 for tag in ('donor', 'gcc16')
                                 for role in ('caller', 'callee') for level in ('O0', 'O2')],
                        help='limit varargs T1 to TAG-ROLE-O0 or TAG-ROLE-O2')
    parser.add_argument('--record', help='small baseline result file')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if os.name == 'nt':
        # Cygwin git emits POSIX paths; GCC/ld also need a POSIX sysroot.
        # Keep the complete run (including run.py and regressions) in that runtime.
        manifest = json.loads((ROOT / 'toolchain/manifest.json').read_text())
        tc = PROJECT / manifest['root']
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(tc / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'), '-u',
                                          str(Path(__file__).resolve())], env=env, text=True).strip()
        arguments = list(sys.argv[1:])
        for flag in ('--cc', '--record'):
            if flag in arguments:
                index = arguments.index(flag) + 1
                arguments[index] = subprocess.check_output(
                    [str(tc / 'cygwin/bin/cygpath.exe'), '-u', arguments[index]], env=env, text=True).strip()
        return subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script, *arguments], env=env)
    if args.worker:
        return Runner(args).run()
    command = [sys.executable, str(ROOT / 'tools/run.py'), '--name',
               'check-' + args.compiler + '-' + '-'.join(args.tiers)]
    # External compiler and sysroot changes are not tracked by project inputs.
    if args.tiers == ['t0']:
        command += ['--inputs', 'tools', 'tests/acceptance', 'tests/regress', 'tests/tools', 'toolchain']
    command += ['--', sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], '--worker']
    return subprocess.call(command)


if __name__ == '__main__':
    raise SystemExit(main())
