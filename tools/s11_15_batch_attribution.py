"""Host-only attribution of the authorized S11-15 development captures.

No workload launch, rebuild, sealed capture, or new timing experiment.
Output stays in the existing shared ticket directory.
"""
from collections import Counter, defaultdict
import json
import os
import re
import subprocess

from s11_15_attribution import load_address, require
from s11_15_profile import SHARED, OUT, host_path

SERIAL = ('STREAM', 'PB-atax', 'PB-cholesky', 'PB-heat-3d', 'PB-jacobi-2d',
          'PB-ludcmp', 'NPB-CG', 'NPB-EP', 'NPB-IS', 'zlib', 'SQLite')
OPENMP = ('STREAM', 'NPB-CG', 'NPB-EP', 'NPB-MG', 'NPB-IS')
# Manually inspected, disjoint regions within each program. Inclusive/exclusive
# bounds are instruction boundaries in the frozen binaries, not source lines.
REGIONS = {
    'STREAM': [('scale', 0x400960, 0x400996), ('add', 0x400a00, 0x400a4a),
               ('triad', 0x400ac0, 0x400b0a)],
    'PB-atax': [('matrix initialization', 0x400be0, 0x400c9c),
                ('strict reduction', 0x400d30, 0x400da7),
                ('vector update', 0x400e00, 0x400e56)],
    'PB-cholesky': [('matrix initialization', 0x400b50, 0x400c5a),
                    ('factorization reduction', 0x400eb0, 0x400ec5)],
    'PB-ludcmp': [('matrix initialization', 0x400c80, 0x400d8c),
                  ('factorization reduction A', 0x400fc0, 0x4010b7),
                  ('factorization reduction B', 0x4011e0, 0x4012da)],
    'PB-heat-3d': [('stencil A', 0x400c20, 0x400ce4),
                   ('stencil B', 0x400fc0, 0x401084)],
    'PB-jacobi-2d': [('unrolled stencil A', 0x400ba0, 0x400f1d),
                     ('unrolled stencil B', 0x4010b0, 0x40142d)],
    'NPB-CG': [('indexed reduction', 0x402480, 0x402499),
               ('sparse setup search', 0x403e90, 0x403eae)],
    'NPB-EP': [('scalar transform/call site', 0x4010ff, 0x40122f),
               ('random generation loop', 0x402510, 0x4025eb)],
    'NPB-IS': [('random generator function', 0x400ec0, 0x400ffc),
               ('rank bucket loop', 0x401743, 0x4019bd)],
    'zlib': [('slide hash loop A', 0x401d70, 0x401d8b),
             ('slide hash loop B', 0x401da0, 0x401dbb)],
    'SQLite': [('index search envelope', 0x481f60, 0x481fb5)],
}
CROSS = SHARED / 'toolchain/cross/bin'
ENV = dict(os.environ)
ENV['PATH'] = str(SHARED / 'toolchain/cygwin/bin') + os.pathsep + ENV['PATH']


def command(tool, *args):
    return subprocess.check_output([str(CROSS / ('k1om-mpss-linux-' + tool + '.exe')),
                                    *map(str, args)], env=ENV, text=True)


def capture(key):
    path = OUT / 'batch-capture'
    # Stream stdout: PolyBench live-outs were already checked by the lead.
    times, metas = {}, {}
    for mode in ('plain', 'sample'):
        with (path / (key + '-' + mode + '.stdout')).open() as source:
            for line in source:
                if line.startswith('CORPUS_TIME '):
                    require(mode not in times, 'duplicate timing')
                    times[mode] = float(line.split()[1])
                elif line.startswith('CORPUS_META '):
                    metas[mode] = json.loads(line.split(' ', 1)[1])
    require(set(times) == {'plain', 'sample'}, 'missing timing: ' + key)
    require(metas['plain'] == metas['sample'], 'affinity mismatch')
    meta = metas['sample']
    require(meta['cores'] == 60 and meta['granted_cpus'] == 240 and
            meta['threads'] == (60 if key.startswith('openmp-') else 1), 'wrong profile')
    text = (path / (key + '-sample.stderr')).read_text()
    require('PROFILE_BLOCKED' not in text and text.count('PROFILE_SAMPLER_COMPLETE') == 1,
            'incomplete sampler: ' + key)
    account = re.search(r'^PROFILE_ACCOUNT (.+)$', text, re.M)
    require(account is not None, 'missing account')
    a = {k: float(v) for k, v in re.findall(r'(\w+)=([\d.]+)', account[1])}
    pcs = [(int(pc, 16), int(tid)) for pc, tid in
           re.findall(r'^PROFILE_PC ([0-9a-f]+) tid=(\d+)$', text, re.M)]
    require(a['overflow'] == 0 and a['samples'] == len(pcs) > 0 and
            a['interval_us'] == 10000, 'invalid samples')
    maps = []
    for row in text.split('PROFILE_MAPS_BEGIN\n')[1].split('PROFILE_MAPS_END')[0].splitlines():
        fields = row.split(maxsplit=5)
        if 'x' not in fields[1]:
            continue
        start, end = (int(v, 16) for v in fields[0].split('-'))
        maps.append(dict(start=start, end=end, offset=int(fields[2], 16),
                         name=fields[5] if len(fields) == 6 else ''))
    return dict(key=key, times=times, meta=meta, account=a, pcs=pcs, maps=maps)


def symbols(path, addresses):
    result = {}
    addresses = sorted(addresses)
    # Bound argv size for Windows; symbols are looked up once per distinct PC.
    for offset in range(0, len(addresses), 500):
        batch = addresses[offset:offset + 500]
        lines = command('addr2line', '-f', '-C', '-e', path, *map(hex, batch)).splitlines()
        require(len(lines) == 2 * len(batch), 'bad addr2line output')
        result.update({pc: (lines[2*i], lines[2*i+1]) for i, pc in enumerate(batch)})
    ranges = []
    for option in ([], ['-D']):
        for row in command('nm', *option, '-S', '--defined-only', path).splitlines():
            match = re.fullmatch(r'([0-9a-fA-F]+) ([0-9a-fA-F]+) [TWtw] (.+)', row)
            if match:
                start, size, name = match.groups()
                ranges.append((int(start, 16), int(size, 16), name))
    for pc, (name, line) in result.items():
        if name == '??':
            names = sorted({n for s, size, n in ranges if s <= pc < s + size})
            if names:
                result[pc] = ('/'.join(names), 'sized symbol; source unavailable')
    # Stripped internal helpers extend beyond exported symbol sizes. Name only
    # explicitly inspected code reached from a named entry, never nearest symbols.
    helpers = {
        'libc-2.21.so': (0x7f600, 0x7f734, 'memcpy aligned helper', 0x7f540, 0x7f5f4,
                        r'7f5e8:\s+callq\s+7f600'),
        'libm-2.21.so': (0x8090, 0x80fc, 'log internal x87 path', 0xc120, 0xc1b1,
                       r'c156:\s+jmpq\s+8090'),
    }
    if path.name in helpers:
        start, end, label, entry, stop, branch = helpers[path.name]
        assembly = command('objdump', '-d', '--no-show-raw-insn',
                           '--start-address=' + hex(entry), '--stop-address=' + hex(stop), path)
        require(re.search(branch, assembly), 'sysroot helper branch changed')
        (OUT / (path.name + '-entry.asm')).write_text(assembly)
        for pc, (name, line) in result.items():
            if name == '??' and start <= pc < end:
                result[pc] = (label, 'sysroot branch-traced helper; source unavailable')
    return result, sorted(set(ranges))


def main():
    builds = json.loads((SHARED / 'S11-18/builds.json').read_text())
    runs, queries = [], defaultdict(set)
    for variant, programs in (('serial', SERIAL), ('openmp', OPENMP)):
        for program in programs:
            rows = [r for r in builds if r['program'] == program and
                    r['variant'] == variant and r['compiler'] == 'gcc-knc']
            require(len(rows) == 1 and not rows[0]['held_out'] and
                    rows[0]['check'] == 'pass', 'ineligible build')
            paths = {host_path(p).name: host_path(p) for p in rows[0]['files']}
            paths['profile-workload'] = paths['workload']
            paths['profile-batch.so'] = OUT / 'profile-batch.so'
            run = capture(variant + '-' + program)
            run['binary'] = paths['workload']
            run['locations'] = []
            for pc, tid in run['pcs']:
                maps = [m for m in run['maps'] if m['start'] <= pc < m['end']]
                require(len(maps) == 1, 'PC outside unique executable map')
                m = maps[0]
                name = m['name'].rsplit('/', 1)[-1]
                path = paths.get(name, SHARED / 'toolchain/sysroot' / m['name'].lstrip('/'))
                if path.is_file():
                    address = load_address(path, m, pc)
                    queries[path].add(address)
                else:
                    path, address = None, pc
                run['locations'].append((name, path, address, tid))
            runs.append(run)
    lookup, ranges = {}, {}
    for path, addresses in queries.items():
        lookup[path], ranges[path] = symbols(path, addresses)
    output, details = [], []
    for run in runs:
        a, key = run['account'], run['key']
        assembly = command('objdump', '-d', '--no-show-raw-insn', run['binary'])
        (OUT / (key + '.asm')).write_text(assembly)
        # Exact PLT entry PCs, including EP's log entry; no nearest-name inference.
        for address, name in re.findall(r'^([0-9a-f]+) <([^>]+@plt)>:', assembly, re.M):
            pc = int(address, 16)
            if pc in lookup[run['binary']] and lookup[run['binary']][pc][0] == '??':
                lookup[run['binary']][pc] = (name, 'exact PLT entry')
        counts, pc_counts, tids, wait_tids = Counter(), Counter(), Counter(), Counter()
        wait = compute = unknown = other_gomp = 0
        for module, path, address, tid in run['locations']:
            function, line = lookup.get(path, {}).get(address, ('??', '??:0'))
            counts[module + ': ' + function] += 1
            tids[tid] += 1
            if function == '??':
                unknown += 1
            elif 'libgomp' in module and re.search(r'wait|barrier|spin', function, re.I):
                wait += 1
                wait_tids[tid] += 1
            else:
                compute += 1
                other_gomp += 'libgomp' in module
            if path == run['binary']:
                pc_counts[address] += 1
            details.append(f'{key} {module} {address:x} tid={tid} {function} {line}')
        total = len(run['pcs'])
        cadence = 100 * (total * .01 / (a['user'] + a['system']) - 1)
        overhead = 100 * (run['times']['sample'] / run['times']['plain'] - 1)
        issues = []
        if abs(cadence) > 20:
            issues.append('cadence')
        if overhead > 10:
            issues.append('overhead')
        if unknown / total > .05:
            issues.append('unknown PCs')
        if total < 300:
            issues.append('fewer than 300 PCs')
        if len(tids) < run['meta']['threads']:
            issues.append('worker coverage')
        # Decode the frozen executable once. Backedges are candidate loop envelopes,
        # not control-flow proofs; overlapping envelopes must never be summed.
        instructions = []
        for row in assembly.splitlines():
            match = re.match(r'\s*([0-9a-f]+):\s+(\S+)\s*(.*)', row)
            if match:
                instructions.append((int(match[1], 16), match[2], match[3]))
        loops = []
        for i, (address, op, operands) in enumerate(instructions[:-1]):
            target = re.match(r'([0-9a-f]+) <', operands)
            if op.startswith('j') and target and int(target[1], 16) < address:
                start, end = int(target[1], 16), instructions[i+1][0]
                if not any(s <= start < end <= s+size for s, size, _ in ranges[run['binary']]):
                    continue
                n = sum(v for pc, v in pc_counts.items() if start <= pc < end)
                if n:
                    loops.append(dict(start=hex(start), end=hex(end), bytes=end-start,
                                      samples=n, share=100*n/total))
        hot_functions = []
        for start, size, name in ranges[run['binary']]:
            n = sum(v for pc, v in pc_counts.items() if start <= pc < start+size)
            if n:
                hot_functions.append(dict(name=name, start=hex(start), bytes=size,
                                          samples=n, share=100*n/total))
        record = dict(key=key, account=a, times=run['times'], threads=run['meta']['threads'],
                      samples=total, overhead=overhead, cadence=cadence,
                      tids=len(tids), tid_min=min(tids.values()), tid_max=max(tids.values()),
                      user_capacity=100*a['user']/(a['wall']*run['meta']['threads']),
                      residual=a['wall']*run['meta']['threads']-a['user']-a['system'],
                      boundary=run['times']['sample']-a['wall'],
                      wait=wait, compute=compute, unknown=unknown, other_gomp=other_gomp,
                      issues=issues,
                      functions=[dict(name=n, samples=c, share=100*c/total,
                                      cpu_seconds=(c/total*a['user'] if abs(cadence) <= 20 else None))
                                 for n, c in counts.most_common()],
                      hot_functions=sorted(hot_functions, key=lambda r: -r['samples']),
                      loops=sorted(loops, key=lambda r: -r['samples']),
                      top_pcs=[dict(pc=hex(pc), samples=c) for pc, c in pc_counts.most_common(12)])
        record['regions'] = []
        if key.startswith('serial-'):
            for label, start, end in REGIONS.get(key[7:], []):
                n = sum(v for pc, v in pc_counts.items() if start <= pc < end)
                record['regions'].append(dict(name=label, start=hex(start), end=hex(end),
                                              bytes=end-start, samples=n, share=100*n/total,
                                              cpu_seconds=n/total*a['user']))
        output.append(record)
        print(f'{key}: {total} PCs, {len(tids)}/{run["meta"]["threads"]} TIDs; '
              f'overhead {overhead:.2f}%, cadence {cadence:.2f}%; '
              f'limits: {", ".join(issues) or "none (single launch)"}')
        print('  ' + '; '.join(f'{f["name"]} {f["share"]:.2f}%'
                               for f in record['functions'][:5]))
    (OUT / 'batch-attribution.json').write_text(json.dumps(output, indent=2) + '\n')
    (OUT / 'batch-attribution-pcs.txt').write_text('\n'.join(details) + '\n')
    print('PASS host attribution: 16 development pairs; qualification limits retained; no card jobs')


if __name__ == '__main__':
    main()
