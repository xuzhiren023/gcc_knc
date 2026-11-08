"""S8-01 host contract: complete point catalog and emitted result fields."""
from pathlib import Path
import re
import subprocess
import sys
from kernels import CASES


def expected():
    names = {f'c1.store.{op}' for op in ('normal', 'nr', 'ngo')}
    names |= {f'c2.{op}' for op in ('vector', 'prefetch0', 'prefetch1',
                                    'vector_prefetch0', 'vector_prefetch1')}
    names |= {f'c4.pages.{kb}' for kb in (128, 256, 384, 448)}
    names |= {f'c5.{kernel}.l1_{a}.l2_{b}'
              for kernel in ('stream', 'stencil', 'row7', 'row8', 'row9')
              for a in (0, 8, 16, 32, 64) for b in (0, 32, 64, 128)}
    names |= {f'c6.{mode}.n{n}' for mode in ('x87', 'aligned', 'peel', 'gather')
              for n in range(1, 34)}
    names |= {f'c7.reduce.a{a}' for a in (1, 2)}
    names |= {f'c9.{chain}.u{u}' for chain in ('vector', 'memory') for u in (1, 2, 4)}
    names |= {f'c10.branch.{mode}' for mode in ('fixed', 'random')}
    return names


def worker_allocations():
    """Worker-side malloc gives each thread a 64 MB arena; job 19 hit ENOMEM at 240 threads."""
    source = (Path(__file__).parent / 'driver.c').read_text()
    calls = []
    for function in ('prepare', 'worker_main'):
        body = re.search(r'\n[^\n]*\b' + function + r'\([^)]*\) \{\n(.*?)\n\}\n', source, re.S)
        assert body, 'missing ' + function
        calls += [function + ': ' + c for c in
                  re.findall(r'\b(?:malloc|calloc|realloc|posix_memalign|aligned_alloc|free)\b',
                             body.group(1))]
    return calls


def c5_bases():
    """Array base displacements in the short-row bodies (S8-12: no 1 MiB aliasing)."""
    bases = set()
    for case in CASES:
        if case['name'].startswith('c5.row') and '.l1_0.l2_0' in case['name']:
            bases |= {int(d) for d in re.findall(r'vmovaps (\d+)\(%r11\)', case['body'])}
            bases |= {int(d) for d in re.findall(r'%zmm0, (\d+)\(%r11\)', case['body'])}
    return sorted(bases)


def c9_memory_on_chain(body):
    """S8-12: each folded load reads the slot its own result is stored to next."""
    lines = body.splitlines()
    adds = [l for l in lines if l.startswith('vaddps ')]
    for add in adds:
        source, reg, dest = [t.strip() for t in add[len('vaddps '):].split(',')]
        assert '(' in source and reg != dest, add
        assert f'vmovaps {dest}, {source}' in lines, 'load off the recurrence: ' + add
    return len(adds)


def c4_layout(binary, density):
    out = subprocess.check_output([binary, '--dry-run', '--layout', '--check', 'c4',
                                   '--threads', str(density)], text=True)
    rows = [dict(t.split('=', 1) for t in line.split()[2:])
            for line in out.splitlines() if line.startswith('layout ')]
    assert len(rows) == 4 * density, out
    for row in rows:
        pages = int(row['pages'])
        assert int(row['cycle']) == pages, row
        assert int(row['page_offsets']) == min(pages, 64), row


if __name__ == '__main__':
    calls = worker_allocations()
    assert not calls, 'worker threads allocate: ' + ', '.join(calls)
    names = expected()
    missing = names - {c['name'] for c in CASES}
    assert not missing, 'missing S8 points: ' + ', '.join(sorted(missing))
    bases = c5_bases()
    assert len(bases) == 8, bases
    assert len({b % 1048576 for b in bases}) == 8, 'C5 arrays 1 MiB-aligned apart'
    assert len({b % 4096 // 64 for b in bases}) == 8, 'C5 arrays share an L1 set'
    for u in (1, 2, 4):
        case = next(c for c in CASES if c['name'] == f'c9.memory.u{u}')
        assert c9_memory_on_chain(case['body']) == u, case['name']
    assert len(sys.argv) == 2, 'supply the CHAR_HOST executable for output checks'
    for density in (1, 2, 4):
        lines = subprocess.check_output([sys.argv[1], '--dry-run', '--threads',
                                         str(density)], text=True).splitlines()
        results = {line.split()[1]: line.split() for line in lines}
        for name in names:
            fields = dict(token.split('=', 1) for token in results[name][3:])
            assert set(('cycles', 'cycle_unit', 'worker', 'ns_per_unit', 'spread',
                        'accepted', 'cores', 'bytes', 'units', 'instructions')) <= fields.keys(), name
            assert fields['cycles'] == fields['ns_per_unit'] == 'unmeasured', name
    for density in (1, 4):
        c4_layout(sys.argv[1], density)
    print(f'PASS S8 catalog and output keys: {len(names)} points, densities 1/2/4; no card execution')
