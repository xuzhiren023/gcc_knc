"""Attribute the returned PB-gemm pilot; never launch workloads or read sealed data."""
from collections import Counter, defaultdict
import json
import os
import re
from statistics import median
import struct
import subprocess

from s11_15_profile import SHARED, OUT

LOG = SHARED.parent / '_state/logs/S11_15_profile_sigprof-20261113-150906.log'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_address(path, mapping, pc):
    # ELF64 PT_LOAD establishes virtual address; file offset alone is insufficient.
    with path.open('rb') as source:
        header = source.read(64)
        require(header[:6] == b'\x7fELF\x02\x01', 'need little-endian ELF64')
        phoff = struct.unpack_from('<Q', header, 32)[0]
        size, count = struct.unpack_from('<HH', header, 54)
        source.seek(phoff)
        headers = source.read(size * count)
    for i in range(count):
        kind, flags, offset, virtual, _, filesz, _, _ = struct.unpack_from(
            '<IIQQQQQQ', headers, i * size)
        if kind == 1 and flags & 1 and (offset & ~4095) == mapping['offset']:
            require(mapping['end'] - mapping['start'] >= filesz,
                    'mapped executable segment shorter than local ELF')
            return pc - mapping['start'] + (virtual & ~4095)
    raise ValueError('no matching executable PT_LOAD: ' + str(path))


def region(address, function):
    if function != 'main':
        return function
    if 0x401320 <= address < 0x40135f:
        return 'main: vector GEMM inner loop'
    if 0x401266 <= address < 0x401397 or 0x401438 <= address < 0x40145f:
        return 'main: GEMM setup/outer/scalar path'
    if 0x401397 <= address < 0x401438 or 0x401460 <= address < 0x4014a6:
        return 'main: live-out emission'
    return 'main: initialization/other'


def main():
    runs = {}
    current = None
    in_maps = False
    complete = False
    for line in LOG.read_text().splitlines():
        require(not line.startswith('PROFILE_BLOCKED'), line)
        if line.startswith('PROFILE_BEGIN '):
            require(current is None, 'nested launch')
            fields = dict(re.findall(r'(\w+)=(\S+)', line))
            key = int(fields['pair']), int(fields['repeat']), fields['mode']
            require(key not in runs, 'duplicate launch')
            current = dict(maps=[], pcs=[], complete=0, liveout=0)
            runs[key] = current
        elif line.startswith('PROFILE_END '):
            require(current is not None, 'end without begin')
            fields = dict(re.findall(r'(\w+)=(\S+)', line))
            require(key == (int(fields['pair']), int(fields['repeat']), fields['mode']),
                    'mismatched end')
            current = None
        elif line.startswith('PROFILE_CAPTURE_COMPLETE '):
            complete = True
        elif current is not None:
            if line.startswith('CORPUS_META '):
                current['meta'] = json.loads(line.split(' ', 1)[1])
            elif line.startswith('CORPUS_TIME '):
                current['elapsed'] = float(line.split()[1])
            elif line.startswith('PROFILE_ACCOUNT '):
                current['account'] = {k: float(v) for k, v in
                                      re.findall(r'(\w+)=([\d.]+)', line)}
            elif line == 'PROFILE_MAPS_BEGIN':
                in_maps = True
            elif line == 'PROFILE_MAPS_END':
                in_maps = False
            elif in_maps:
                fields = line.split(maxsplit=5)
                start, end = (int(x, 16) for x in fields[0].split('-'))
                current['maps'].append(dict(start=start, end=end, perms=fields[1],
                    offset=int(fields[2], 16), name=fields[5] if len(fields) == 6 else ''))
            elif line.startswith('PROFILE_PC '):
                current['pcs'].append(int(line.split()[1], 16))
            elif line == 'PROFILE_SAMPLER_COMPLETE':
                current['complete'] += 1
            elif line == 'PROFILE_LIVEOUT identical':
                current['liveout'] += 1
    require(complete and current is None and not in_maps, 'incomplete capture')
    require(set(runs) == {(p, r, m) for p in (1, 2, 3) for r in (1, 2)
                         for m in ('plain', 'sample')}, 'missing launches')
    for run in runs.values():
        require(run['liveout'] == 1 and run['elapsed'] > 0, 'bad launch')
        require(run['meta'] == dict(cores=60, granted_cpus=240, threads=1, cpus='1'),
                'affinity mismatch')

    env = dict(os.environ)
    env['PATH'] = str(SHARED / 'toolchain/cygwin/bin') + os.pathsep + env['PATH']
    addr2line = SHARED / 'toolchain/cross/bin/k1om-mpss-linux-addr2line.exe'
    queries = defaultdict(set)
    for key, run in runs.items():
        if key[2] != 'sample':
            continue
        a = run['account']
        require(run['complete'] == 1 and a['overflow'] == 0 and
                a['samples'] == len(run['pcs']) > 0 and a['interval_us'] == 10000,
                'invalid sampler accounting')
        run['locations'] = []
        for pc in run['pcs']:
            mappings = [m for m in run['maps'] if m['start'] <= pc < m['end']
                        and 'x' in m['perms']]
            require(len(mappings) == 1, 'PC outside unique executable mapping')
            m = mappings[0]
            name = m['name'].rsplit('/', 1)[-1]
            path = OUT / name if name in ('gemm', 'profile-sigprof.so') else (
                SHARED / 'toolchain/sysroot' / m['name'].lstrip('/'))
            if not path.is_file():
                run['locations'].append((name, None, pc))
                continue
            address = load_address(path, m, pc)
            queries[path].add(address)
            run['locations'].append((name, path, address))
    symbols = {}
    for path, addresses in queries.items():
        addresses = sorted(addresses)
        result = subprocess.check_output([str(addr2line), '-f', '-C', '-e', str(path),
                    *[hex(a) for a in addresses]], env=env, text=True).splitlines()
        require(len(result) == len(addresses) * 2, 'unexpected addr2line result')
        for i, address in enumerate(addresses):
            symbols[path, address] = result[i*2], result[i*2+1]

        # addr2line cannot name stripped DSOs from .dynsym on this toolchain.
        # Accept only containment in a sized dynamic text symbol, never nearest-name guesses.
        nm = SHARED / 'toolchain/cross/bin/k1om-mpss-linux-nm.exe'
        dynamic = subprocess.check_output([str(nm), '-D', '-S', '--defined-only',
                                          str(path)], env=env, text=True)
        ranges = []
        for row in dynamic.splitlines():
            match = re.fullmatch(r'([0-9a-fA-F]+) ([0-9a-fA-F]+) [TWtw] (.+)', row)
            if match:
                start, length, name = match.groups()
                ranges.append((int(start, 16), int(length, 16), name))
        for address in addresses:
            if symbols[path, address][0] != '??':
                continue
            names = sorted({name for start, size, name in ranges
                            if start <= address < start + size})
            if names:
                symbols[path, address] = '/'.join(names), 'dynamic-symbol; source unavailable'
    # These are the two exact PLT entry PCs in the frozen staged disassembly.
    for address, name in ((0x400830, 'strcmp@plt'), (0x400850, 'fwrite@plt')):
        if (OUT / 'gemm', address) in symbols:
            symbols[OUT / 'gemm', address] = name, 'gemm.asm; source unavailable'

    output = ['# PB-gemm SIGPROF host attribution', '',
              'Library symbols use the same-version sysroot ELF; card ELF identity is not established by maps.',
              'Shares are conditional PC shares, not wall fractions. Unknowns stay in the denominator.', '',
              '| Block/repeat | Plain s | Sample s | Overhead % | PCs | User/wall % | System/wall % | CPU cadence error % | Outside interior ms |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    aggregate, by_run, overheads, unknowns, details = Counter(), {}, [], [], []
    for p in (1, 2, 3):
        for r in (1, 2):
            run, plain = runs[p, r, 'sample'], runs[p, r, 'plain']['elapsed']
            a = run['account']
            overhead = 100 * (run['elapsed'] / plain - 1)
            overheads.append(overhead)
            cadence = 100 * (len(run['pcs']) * .010 / (a['user'] + a['system']) - 1)
            output.append('| %d/%d | %.6f | %.6f | %.3f | %d | %.3f | %.3f | %.3f | %.3f |' %
                (p, r, plain, run['elapsed'], overhead, len(run['pcs']),
                 100*a['user']/a['wall'], 100*a['system']/a['wall'], cadence,
                 1000*(run['elapsed']-a['wall'])))
            require(abs(cadence) <= 20, 'CPU cadence gate failed')
            counts, unknown = Counter(), 0
            for name, path, address in run['locations']:
                function, line = symbols.get((path, address), ('??', '??:0'))
                label = name + ': ' + (region(address, function) if name == 'gemm' else function)
                counts[label] += 1
                unknown += function == '??'
                details.append('%d/%d %s %x %s %s' % (p, r, name, address, function, line))
            by_run[p, r] = counts
            unknowns.append(unknown)
            aggregate.update(counts)
    total = sum(aggregate.values())
    output += ['', 'Overhead median %.3f%%, range [%.3f, %.3f]%%; block medians %s%%.' %
               (median(overheads), min(overheads), max(overheads),
                ', '.join('%.3f' % median(overheads[i:i+2]) for i in (0, 2, 4))),
               'Samples %d; function-unattributed %d (%.3f%%).' %
               (total, sum(unknowns), 100*sum(unknowns)/total), '',
               '| Module / region | PCs | Pooled % | Per-launch % (1/1, 1/2, 2/1, 2/2, 3/1, 3/2) |',
               '| --- | --- | --- | --- |']
    for label, count in aggregate.most_common():
        output.append('| %s | %d | %.3f | %s |' % (label, count, 100*count/total,
            ', '.join('%.2f' % (100*c[label]/sum(c.values())) for c in by_run.values())))
    require(total >= 300 and median(overheads) <= 5 and max(overheads) <= 10,
            'sample count or overhead gate failed')
    output += ['', 'Capture, count, cadence and overhead gates PASS.',
               'Function-attribution gate (conditional on matching card/sysroot ELF): ' +
               ('PASS' if sum(unknowns)/total <= .05 else 'BLOCKED'),
               'Wall attribution, module identity and hot-order qualification require interpretation.']
    (OUT / 'attribution.md').write_text('\n'.join(output) + '\n')
    (OUT / 'attribution-pcs.txt').write_text('\n'.join(details) + '\n')
    print('\n'.join(output))


if __name__ == '__main__':
    main()
