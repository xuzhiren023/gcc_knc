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


if __name__ == '__main__':
    calls = worker_allocations()
    assert not calls, 'worker threads allocate: ' + ', '.join(calls)
    names = expected()
    missing = names - {c['name'] for c in CASES}
    assert not missing, 'missing S8 points: ' + ', '.join(sorted(missing))
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
    print(f'PASS S8 catalog and output keys: {len(names)} points, densities 1/2/4; no card execution')
