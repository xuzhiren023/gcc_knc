#!/usr/bin/env python3
"""Static development-only KNC census. No builds, source access, or card jobs.

Counts are instruction sites, not execution counts. Stack accesses are spill/reload
proxies; transfer candidates are same-address observations, not proven dataflow.
"""
import argparse
from array import array
from bisect import bisect_left, bisect_right
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess

DEVELOPMENT = ('STREAM', 'NPB-CG', 'NPB-EP', 'NPB-MG', 'NPB-IS', 'HPCG',
               'SQLite', 'PB-gemm', 'PB-atax', 'PB-cholesky', 'PB-ludcmp',
               'PB-jacobi-2d', 'PB-heat-3d', 'zlib')
COMPILERS = ('gcc-5.1.1', 'gcc-knc')
KEYS = ('instructions bytes unknown vector scalar mask x87 x87_memory fxch '
        'address lea imul sign_extend calls indirect_calls callee_save callee_restore '
        'branches conditional_branches backward_branches forward_branches indirect_branches '
        'loads stores prefetch nontemporal gather_scatter transfer_candidates').split()
KEYS += ['stack_' + direction + '_' + cls
         for cls in ('gpr', 'x87', 'zmm', 'k') for direction in ('load', 'store')]
HEADER = re.compile(r'^\s*([0-9a-f]+) <(.+)>:$')
LINE = re.compile(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)(.*?)\s*$')
MEM = re.compile(r'(?:[-+\w.]+)?\([^)]*\)')
STACK = re.compile(r'%(?:rsp|rbp|esp|ebp)\b')
CALLEE = re.compile(r'^%(?:rbx|rbp|r12|r13|r14|r15)$')


def validate_program(name):
    """Allowlist also refuses alternative spellings of sealed program names."""
    if name not in DEVELOPMENT:
        raise ValueError('refusing non-development program: ' + str(name))


def select_builds(rows, require_complete=True):
    selected = []
    for row in rows:
        # Refuse forged development metadata before consulting any file path.
        if row.get('held_out'):
            continue
        validate_program(row['program'])
        if (row.get('panel') == 'primary' and row.get('check') == 'pass'
                and row.get('requested_flags') == (['-O2', '-march=knc']
                    if row.get('compiler') == 'gcc-knc' else ['-O2'])
                and row.get('variant') in ('serial', 'optimization-fallback')
                and row.get('compiler') in COMPILERS):
            selected.append(row)
    pairs = [(r['program'], r['compiler']) for r in selected]
    if len(set(pairs)) != len(pairs):
        raise ValueError('duplicate primary builds')
    if require_complete and set(pairs) != {(p, c) for p in DEVELOPMENT for c in COMPILERS}:
        raise ValueError('expected exactly 14 development programs under both compilers')
    return selected


def local_path(value):
    match = re.match(r'^/cygdrive/([a-zA-Z])/(.*)', str(value))
    if match and os.name == 'nt':
        return Path(match[1].upper() + ':/' + match[2])
    return Path(value)


def disassemble(program, binary, objdump):
    validate_program(program)
    # Reject a substituted path even if the caller supplies a development name.
    for part in Path(binary).parts:
        if part.lower() in ('pb-adi', 'adi', 'pb-durbin', 'durbin', 'bzip2'):
            raise ValueError('refusing held-out path')
    env = os.environ.copy()
    if os.name == 'nt':
        cygwin = Path(objdump).resolve().parents[2] / 'cygwin/bin'
        env['PATH'] = str(cygwin) + os.pathsep + env.get('PATH', '')
    return subprocess.run([str(objdump), '-d', str(binary)], env=env,
                          check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True).stdout


def operands(text):
    # Commas within addressing modes and mask decorations are not separators.
    return re.split(r',\s*(?![^()]*\))(?![^{}]*\})', text.split('#')[0].strip())


def instruction_counts(insns, prefix=None, transfers=None):
    c = Counter({k: 0 for k in KEYS})
    stored = {}
    for index, i in enumerate(insns):
        m, op = i['mnemonic'], i['operands']
        c['instructions'] += 1
        c['bytes'] += i['size']
        if m in ('(bad)', '.byte'):
            c['unknown'] += 1
        vec = bool(re.search(r'%[zy]mm\d+', op))
        mask = bool(re.search(r'%k\d+', op)) and not vec
        x87 = m.startswith('f') and m not in ('fence',)
        c['vector' if vec else 'mask' if mask else 'scalar'] += 1
        c['x87'] += int(x87)
        c['fxch'] += int(m.startswith('fxch'))
        c['prefetch'] += int('prefetch' in m)
        c['nontemporal'] += int('nt' in m and m.startswith(('v', 'mov')) or 'ngo' in m)
        c['gather_scatter'] += int('gather' in m or 'scatter' in m)
        lea = m.startswith('lea')
        imul = m.startswith('imul')
        ext = m.startswith(('movsbl', 'movsbq', 'movswl', 'movswq', 'movslq', 'movsx')) or m in ('cltq', 'cdqe', 'cwde')
        c['lea'] += int(lea)
        c['imul'] += int(imul)
        c['sign_extend'] += int(ext)
        c['address'] += int(lea or imul or ext)
        parts = operands(op)
        memory = [(n, MEM.search(p).group()) for n, p in enumerate(parts) if MEM.search(p)]
        # AT&T source,destination; compare/test and prefetch only read memory.
        store = bool(memory and memory[-1][0] == len(parts)-1
                     and len(parts) > 1 and not m.startswith(('cmp', 'test', 'vcom', 'vucom')))
        store = store or bool(memory and m.startswith(('fst', 'fist', 'stmxcsr', 'fnst')))
        load = bool(memory and not store)
        if memory and not lea and 'prefetch' not in m:
            # Read-modify-write arithmetic consumes as well as writes memory.
            rmw = store and not m.startswith(('mov', 'vmov', 'kmov', 'fst', 'fist', 'vst', 'st', 'fnst'))
            c['loads'] += int(load or rmw)
            c['stores'] += int(store)
            c['x87_memory'] += int(x87 and m.startswith(('fld', 'fst')))
            cls = 'zmm' if vec else 'k' if mask else 'x87' if x87 else 'gpr'
            slot = memory[-1][1].replace(' ', '')
            if STACK.search(slot):
                c['stack_load_' + cls] += int(load or rmw)
                c['stack_store_' + cls] += int(store)
            # Strictly local, same textual memory address, bounded window. An
            # intervening store replaces the candidate; control flow resets it.
            if load and slot in stored:
                old_cls, age, source_index = stored[slot]
                if {old_cls, cls} == {'x87', 'zmm'} and i['address'] - age <= 64:
                    c['transfer_candidates'] += 1
                    if transfers is not None:
                        transfers.append((source_index, index))
                stored.pop(slot, None)
            if store:
                stored[slot] = (cls, i['address'], index)
        if m.startswith('push') and CALLEE.match(op.strip()):
            c['callee_save'] += 1
        if m.startswith('pop') and CALLEE.match(op.strip()):
            c['callee_restore'] += 1
        if m.startswith(('mov', 'vmov')) and memory and STACK.search(memory[-1][1]):
            if store and CALLEE.match(parts[0].strip()):
                c['callee_save'] += 1
            if load and CALLEE.match(parts[-1].strip()):
                c['callee_restore'] += 1
        if m.startswith('call'):
            c['calls'] += 1
            c['indirect_calls'] += int('*' in op)
        if m.startswith('j') or m.startswith('loop'):
            c['branches'] += 1
            c['conditional_branches'] += int(not m.startswith('jmp'))
            target = re.match(r'^([0-9a-f]+)\b', op)
            if target:
                c['backward_branches' if int(target[1], 16) < i['address'] else 'forward_branches'] += 1
            else:
                c['indirect_branches'] += 1
        if m.startswith(('j', 'loop', 'call', 'ret', 'push', 'pop')) or re.search(r',\s*%(?:r|e)(?:sp|bp)\b', op):
            stored.clear()
        if prefix is not None:
            for key in KEYS:
                prefix[key].append(c[key])
    return dict(c)


def parse_disassembly(text):
    functions = []
    current = None
    previous = None
    for line in text.splitlines():
        h = HEADER.match(line)
        if h:
            current = dict(name=h[2], start=int(h[1], 16), insns=[])
            functions.append(current)
            previous = None
            continue
        match = LINE.match(line)
        if not match or current is None:
            continue
        body = match[3].strip()
        size = len(match[2].split())
        if not body:
            if previous is not None:
                previous['size'] += size
            continue
        fields = body.split(None, 1)
        previous = dict(address=int(match[1], 16), size=size,
                        mnemonic=fields[0], operands=fields[1] if len(fields) > 1 else '')
        current['insns'].append(previous)
    total = Counter({k: 0 for k in KEYS})
    loop_total = Counter({k: 0 for k in KEYS})
    for f in functions:
        insns = f.pop('insns')
        prefix = {key: array('Q', [0]) for key in KEYS}
        transfers = []
        f['counts'] = instruction_counts(insns, prefix, transfers)
        total.update(f['counts'])
        intervals = set()
        addresses = {i['address'] for i in insns}
        for i in insns:
            if i['mnemonic'].startswith(('j', 'loop')):
                target = re.match(r'^([0-9a-f]+)\b', i['operands'])
                if target and int(target[1], 16) in addresses and int(target[1], 16) < i['address']:
                    intervals.add((int(target[1], 16), i['address']))
        ordered_addresses = [i['address'] for i in insns]

        def region_counts(a, b):
            lo = bisect_left(ordered_addresses, a)
            hi = bisect_right(ordered_addresses, b)
            counts = {key: prefix[key][hi] - prefix[key][lo] for key in KEYS}
            # Do not import a store from outside this interval.
            counts['transfer_candidates'] -= sum(source < lo <= dest < hi
                                                 for source, dest in transfers)
            return counts

        f['loops'] = [dict(start=a, end=b, counts=region_counts(a, b))
                      for a, b in sorted(intervals)]
        # Union prevents double counting nested/overlapping intervals in totals.
        merged = []
        for a, b in sorted(intervals):
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(b, merged[-1][1])
            else:
                merged.append([a, b])
        union = Counter({key: 0 for key in KEYS})
        for a, b in merged:
            union.update(region_counts(a, b))
        f['loop_counts'] = dict(union)
        loop_total.update(f['loop_counts'])
    return dict(functions=functions, counts=dict(total), loop_counts=dict(loop_total))


THEMES = {
    'Scalar overhead': ('address', 'branches', 'calls', 'bytes'),
    'Pressure-aware scheduling': tuple('stack_' + d + '_' + r for r in ('gpr', 'x87', 'zmm', 'k') for d in ('load', 'store')) + ('fxch', 'transfer_candidates'),
    'Legal reuse': ('loads', 'stores'),
    'Alias-sensitive vectorization': ('vector', 'scalar', 'gather_scatter'),
    'Prefetch/store choice': ('prefetch', 'stores', 'nontemporal'),
    'Scalar FP on VPU': ('x87', 'x87_memory', 'fxch', 'transfer_candidates'),
}


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def report(results):
    lines = ['# M4 development code census', '',
        'Static snapshot of S11-18 primary executables, generated by `tools/code_census.py`.',
        'Static counts are not time. S11-15 profiles must supply execution frequency and removable wall-time weighting; this census selects no theme.', '',
        '## Scope and interpretation', '',
        'Only the 14 allowlisted development programs are disassembled, once per compiler. '
        'The metadata held-out flag is filtered before file access; names and input path components are also guarded. '
        'No corpus source, shared library, held-out executable, card job or compiler build is accessed. '
        'All executable sections from `objdump -d` are included: startup, PLT and statically linked helpers can contribute. '
        'Different linked helpers and inlining prevent treating whole-executable differences as isolated backend effects.', '',
        'Primary requested flags are `-O2`. Actual flags and variants are recorded below; '
        'SQLite donor uses its staged assembly fallback, so its comparison is not an equal-optimization-level backend experiment.', '',
        'Counts are sites. Bytes sum decoded instruction bytes (including wrapped byte lines), not ELF file size. '
        'Vector means an explicit zmm/ymm operand; mask-only instructions are separate. Scalar includes integer, x87, '
        'control, padding and setup. Vector share is instruction share, not lane utilization or FP work.', '',
        'Stack loads/stores via rsp/rbp are proxies, not proven spills: frame locals, arguments, callee saves and frame-pointer-free rbp data can contribute. '
        'GPR/x87/zmm/k classes follow explicit operands/mnemonics. Push/pop callee saves are counted separately; '
        'mov-based stack saves/restores are candidates and overlap stack counts. '
        'x87 memory counts fld/fst families; fxch is separate. Transfer candidates are store then load to the same textual '
        'address within 64 instruction bytes, across x87/zmm classes, cleared at calls/control flow/stack-base changes. '
        'Aliasing, widths, base-register changes and dataflow are not proved; these are inspection leads, not confirmed transfers.', '',
        'Loop regions are address intervals ending in a backward direct branch to an instruction in the same function. '
        'They are CFG layout proxies, not dominator-proven natural loops; cold paths, nested loops and unstructured flow can distort them. '
        'Per-loop JSON counts may overlap; loop totals use the union of intervals. No opt-info is required. '
        'Address proxies count lea, imul and sign extensions; imul may be data arithmetic rather than index work. '
        'Loads/stores use explicit AT&T parenthesized operands and read-modify-write heuristics; implicit string/stack traffic, '
        'absolute addresses and exact vector memory semantics are not fully represented.', '',
        'Backward/forward branch counts expose layout direction only. Taken frequency, prediction hints, branch probabilities, '
        'alias blocking, reuse distance, cache misses and profitable scalar FP conversion cannot be recovered from these binaries.', '',
        '## Per-program comparison', '',
        'D = GCC 5.1.1; K = GCC-KNC. Each cell is D / K. No dynamic ratio is implied.', '']
    paired = {p: {r['compiler']: r for r in results if r['program'] == p} for p in DEVELOPMENT}
    def pairs(keys, loop=False):
        rows = []
        for p in DEVELOPMENT:
            row = [p]
            for k in keys:
                row.append(' / '.join(str(paired[p][c]['loop_counts' if loop else 'counts'][k]) for c in COMPILERS))
            rows.append(row)
        return rows
    lines += [table(['Program', 'Actual D flags', 'Actual K flags'], [
        [p] + [' '.join(paired[p][c]['flags']) for c in COMPILERS] for p in DEVELOPMENT]), '']
    groups = [(['instructions', 'bytes', 'vector', 'scalar', 'mask', 'unknown'], False),
              (['calls', 'indirect_calls', 'callee_save', 'callee_restore', 'branches', 'backward_branches', 'forward_branches', 'indirect_branches'], False),
              (['x87', 'x87_memory', 'fxch', 'transfer_candidates'], False),
              (list(THEMES['Pressure-aware scheduling'][:-2]), False),
              (['address', 'lea', 'imul', 'sign_extend', 'loads', 'stores', 'prefetch', 'nontemporal', 'gather_scatter'], True)]
    for keys, loop in groups:
        lines += [('Loop-region union' if loop else 'Whole executable') + ':', '', table(['Program'] + keys, pairs(keys, loop)), '']
    lines += [table(['Program', 'D vector %', 'K vector %', 'D functions/regions', 'K functions/regions'], [
        [p] + ['%.2f' % (100 * paired[p][c]['counts']['vector'] / max(1, paired[p][c]['counts']['instructions'])) for c in COMPILERS] +
        ['%d/%d' % (len(paired[p][c]['functions']), sum(len(f['loops']) for f in paired[p][c]['functions'])) for c in COMPILERS]
        for p in DEVELOPMENT]), '', '## Candidate-theme aggregates', '',
        'Keys in each row are independent counters, not an additive score. Themes overlap. Loop-union counts focus '
        'inspection but do not establish hotness. Each following table also supplies per-program theme evidence.', '']
    for theme, keys in THEMES.items():
        lines += ['### ' + theme, '', table(['Program'] + list(keys), pairs(keys, True)), '']
        totals = [[c] + [sum(r['loop_counts'][k] for r in results if r['compiler'] == c) for k in keys] for c in COMPILERS]
        lines += [table(['Loop total'] + list(keys), totals), '']
    def observed(program, key, loop=False):
        return ' / '.join(str(paired[program][c]['loop_counts' if loop else 'counts'][key])
                          for c in COMPILERS)

    larger = [p for p in DEVELOPMENT if paired[p]['gcc-knc']['counts']['bytes'] >
              paired[p]['gcc-5.1.1']['counts']['bytes']]
    lines += ['## Observed patterns', '',
        'Scalar overhead: GCC-KNC has more decoded instruction bytes in %d of 14 programs. '
        'Loop address sites differ in both directions: SQLite %s, HPCG %s, zlib %s (D / K). '
        'Inlining, vector setup, tails, helper coverage and the SQLite flag exception all complicate causality.' %
        (len(larger), observed('SQLite', 'address', True), observed('HPCG', 'address', True),
         observed('zlib', 'address', True)), '',
        'Pressure: stack traffic spans dense, sparse and control-heavy styles. '
        'PB-ludcmp has %s x87 stack-load sites; HPCG has %s and SQLite %s GPR stack-load sites '
        '(whole executable, D / K). These are pressure/local-storage leads, not verified allocator spills.' %
        (observed('PB-ludcmp', 'stack_load_x87'), observed('HPCG', 'stack_load_gpr'),
         observed('SQLite', 'stack_load_gpr')), '',
        'Reuse: loop loads/stores are %s / %s in STREAM and %s / %s in PB-gemm '
        '(each pair D / K). Static memory-site differences cannot distinguish duplicated paths, '
        'new vector setup, redundant accesses and necessary work.' %
        (observed('STREAM', 'loads', True), observed('STREAM', 'stores', True),
         observed('PB-gemm', 'loads', True), observed('PB-gemm', 'stores', True)), '',
        'Vectorization: zlib has %s explicit vector sites, while PB-gemm has %s and '
        'NPB-MG %s (whole executable, D / K). Dense and stencil code show vector expansion; '
        'branch-heavy integer code remains scalar by this measure. None of these counts identifies aliasing as the cause.' %
        (observed('zlib', 'vector'), observed('PB-gemm', 'vector'), observed('NPB-MG', 'vector')), '',
        'Prefetch/store choice: loop prefetch sites are %s in STREAM, %s in NPB-CG and %s in SQLite '
        '(D / K), reaching streaming, sparse and database styles. '
        'STREAM has %s non-temporal/NGO mnemonic sites. Extra sites are neither proof of useful coverage nor waste.' %
        (observed('STREAM', 'prefetch', True), observed('NPB-CG', 'prefetch', True),
         observed('SQLite', 'prefetch', True), observed('STREAM', 'nontemporal', True)), '',
        'Scalar FP: x87 sites remain in dependence-heavy science (PB-cholesky %s, PB-ludcmp %s), '
        'random/math work (NPB-EP %s), and database code (SQLite %s); zlib has %s '
        '(whole executable, D / K). This locates FP styles for profile correlation without implying '
        'that strict scalar-to-VPU conversion is legal or profitable.' %
        (observed('PB-cholesky', 'x87'), observed('PB-ludcmp', 'x87'), observed('NPB-EP', 'x87'),
         observed('SQLite', 'x87'), observed('zlib', 'x87')), '',
        '## Code-style interpretation and boundaries', '',
        'Style groupings follow [S11-20](code-style-coverage.md), not source edits or a skill-level classification of authors. '
        'The tables above identify which programs actually expose each proxy; zeros are retained.', '',
        '| Theme | Development programs/styles to inspect alongside counts | What remains unproved |',
        '| --- | --- | --- |',
        '| Scalar overhead | SQLite/zlib control-heavy library code; NPB-IS integer indexing; HPCG sparse C++; PB-atax and stencil loops | Hotness of addressing/calls/branches, index versus data imul, removable overhead |',
        '| Pressure-aware scheduling | PB-gemm/heat-3d regular nests, NPB-CG/HPCG sparse work, SQLite/zlib complex functions | Actual spills versus locals, live ranges, latency and scheduling benefit |',
        '| Legal reuse | PB-gemm/atax/jacobi-2d/heat-3d dense and stencil work; NPB-MG/HPCG memory operations | Redundant versus necessary loads, alias/dependence legality, locality |',
        '| Alias-sensitive vectorization | STREAM regular streams, PB-atax/heat-3d arrays, HPCG pointer-rich sparse loops; scalar-only rows also remain evidence | Alias rejection versus strict recurrences, pass eligibility, masks, tails and profitable checks |',
        '| Prefetch/store choice | STREAM contiguous streams; NPB-CG/MG and HPCG sparse/multigrid accesses | Access strides, page/cache state, bandwidth pressure, reuse, NGO legality |',
        '| Scalar FP on VPU | PB-cholesky/ludcmp dependence-heavy dense science and NPB-EP random/math work; other x87-positive rows | Strict semantics, eligible FP regions, transfer cost and dynamic payoff |', '',
        'These are property matches, not claims of removable cost. Educational, generated and abstraction-heavy C++ '
        'coverage remains limited as described in S11-20. No new generality programs are added here.', '',
        '## Reproduction and detailed locations', '',
        '`python tools/run.py --name S12-01-census --inputs tools/code_census.py -- python tools/code_census.py`', '',
        'Default input: `.work/_shared/S11-18/builds.json`. Default JSON output: '
        '`.work/_shared/S12-01/census.json`. It records program/compiler/actual flags, '
        'each function name and start address, each loop interval and all counters. '
        'The report is regenerated in place. Large disassembly text is processed in memory and not retained.', '']
    return '\n'.join(lines)


def main():
    root = Path(__file__).resolve().parents[1]
    shared = root.parent / '_shared' if root.parent.name == '.work' else root / '.work/_shared'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--builds', type=Path, default=shared / 'S11-18/builds.json')
    parser.add_argument('--objdump', type=Path, default=shared / 'toolchain/cross/bin' / ('k1om-mpss-linux-objdump.exe' if os.name == 'nt' else 'k1om-mpss-linux-objdump'))
    parser.add_argument('--output', type=Path, default=shared / 'S12-01/census.json')
    parser.add_argument('--report', type=Path, default=root / 'docs/research/m4-code-census.md')
    args = parser.parse_args()
    rows = select_builds(json.loads(args.builds.read_text(encoding='utf8')))
    results = []
    for row in rows:
        binaries = [local_path(p) for p in row['files'] if Path(p).name == 'workload']
        if len(binaries) != 1 or row['program'] not in binaries[0].parts:
            raise ValueError('expected one program-specific workload')
        result = parse_disassembly(disassemble(row['program'], binaries[0], args.objdump))
        if not result['counts']['instructions'] or result['counts']['unknown']:
            raise ValueError('empty or undecodable disassembly: ' + row['program'])
        result.update(program=row['program'], compiler=row['compiler'], flags=row['flags'],
                      variant=row['variant'], binary=str(binaries[0]))
        results.append(result)
        print('%s %s: %d functions, %d instructions' % (row['program'], row['compiler'], len(result['functions']), result['counts']['instructions']), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + '\n', encoding='utf8')
    args.report.write_text(report(results), encoding='utf8')
    print('14 development pairs; details: %s; report: %s' % (args.output, args.report))


if __name__ == '__main__':
    main()
