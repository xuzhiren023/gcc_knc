"""Summarize the existing development pilot; no runs, sealed reads or M4 vote."""
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
from statistics import median

from s11_15_profile import SHARED, OUT

PROGRAMS = ('PB-gemm', 'PB-atax', 'PB-cholesky', 'PB-ludcmp',
            'PB-jacobi-2d', 'PB-heat-3d', 'STREAM', 'NPB-CG',
            'NPB-EP', 'NPB-MG', 'NPB-IS', 'HPCG', 'zlib', 'SQLite')
PROFILES = ('full', '3100', '5100')
DONOR, KNC = 'gcc-5.1.1', 'gcc-knc'
STAGE = SHARED / 'S11-18'


def read_rows(name):
    with (STAGE / name).open() as source:
        for line in source:
            row = json.loads(line)
            if row['program'] not in PROGRAMS or row.get('held_out'):
                raise ValueError('non-development row in public input')
            # Complete live-outs stay in the original collector artifact.
            row.pop('arrays', None)
            row.pop('secondary_timing_output', None)
            yield row


def metric(row):
    if row['program'] == 'HPCG':
        path = Path(row['stdout']).resolve()
        if path.parent != (STAGE / 'capture').resolve():
            raise ValueError('capture outside development directory')
        values = []
        with path.open() as source:
            for line in source:
                match = re.search(r'^Final Summary::HPCG 2\.4 rating for historical reasons is=([0-9.eE+-]+)\s*$', line)
                if match:
                    values.append(float(match[1]))
        if len(values) != 1:
            raise ValueError('missing or ambiguous historical HPCG rating')
        value = values[0]
    else:
        value = row['time_seconds']
    if not math.isfinite(value) or value <= 0:
        raise ValueError('invalid metric')
    return value


def main():
    checked = {r['launch_order']: r for r in read_rows('results.jsonl')}
    primary, omp = defaultdict(dict), defaultdict(list)
    counts = Counter()
    seen = set()
    for r in read_rows('raw-results.jsonl'):
        order = r['launch_order']
        if order in seen:
            raise ValueError('duplicate launch')
        seen.add(order)
        c = checked[order]
        for field in ('program', 'compiler', 'run', 'profile', 'threads',
                      'flags', 'pair_id', 'time_seconds', 'stdout'):
            if c[field] != r[field]:
                raise ValueError('raw/collector metadata mismatch: ' + field)
        r['check'] = c['check']
        counts[(r['variant'], r['check'])] += 1
        key = r['program'], r['profile']
        if r['panel'] == 'primary':
            if r['threads'] != 1:
                raise ValueError('nonserial primary')
            expected = ['-O3'] if r['program'] == 'SQLite' and r['compiler'] == DONOR else (
                ['-O2'] if r['compiler'] == DONOR else ['-O2', '-march=knc'])
            if r['flags'] != expected:
                raise ValueError('unexpected primary flags')
            primary[key][r['run'], r['compiler']] = r
        else:
            if r['compiler'] != KNC or r['variant'] != 'openmp':
                raise ValueError('unexpected side panel')
            omp[key + (r['threads'],)].append(r)
    if seen != set(checked) or len(seen) != 414:
        raise ValueError('incomplete public pilot')

    output = ['| Program | 7120 | 3100 | 5100 |', '| --- | --- | --- | --- |']
    for program in PROGRAMS:
        cells = []
        for profile in PROFILES:
            group = primary[program, profile]
            if set(group) != {(n, c) for n in range(3) for c in (DONOR, KNC)}:
                raise ValueError('incomplete primary pairs')
            if program == 'NPB-MG':
                failures = sum(r['check'] != 'pass' for r in group.values())
                cells.append('Excluded: %d/6 failed; S11-27' % failures)
                continue
            if any(r['check'] != 'pass' for r in group.values()):
                cells.append('Blocked: failed correctness')
                continue
            old = [metric(group[n, DONOR]) for n in range(3)]
            new = [metric(group[n, KNC]) for n in range(3)]
            ratios = [b/a if program == 'HPCG' else a/b for a, b in zip(old, new)]
            cells.append('%.5g / %.5g; **%.3fx** [%.3f, %.3f]' %
                         (median(old), median(new), median(ratios), min(ratios), max(ratios)))
        output.append('| ' + program + ' | ' + ' | '.join(cells) + ' |')
    output += ['', '| Program | Profile | Threads | GCC-KNC median [min, max] | Status |',
               '| --- | --- | --- | --- | --- |']
    for (program, profile, threads), rows in sorted(omp.items()):
        if len(rows) != 3 or {r['run'] for r in rows} != {0, 1, 2}:
            raise ValueError('incomplete OpenMP group')
        failures = sum(r['check'] != 'pass' for r in rows)
        if failures:
            value, status = 'Excluded', '%d/3 failed' % failures
        else:
            values = [metric(r) for r in rows]
            value = '%.5g [%.5g, %.5g]' % (median(values), min(values), max(values))
            status = '3/3 collector pass'
        output.append('| %s | %s | %d | %s | %s |' %
                      (program, '7120' if profile == 'full' else profile, threads, value, status))
    OUT.mkdir(exist_ok=True)
    (OUT / 'baseline-tables.md').write_text('\n'.join(output) + '\n')
    print('READ 414 development launches; existing collector checks retained: ' + str(dict(counts)))
    print('WROTE ' + str(OUT / 'baseline-tables.md'))
    print('Pilot medians/ranges only; no gate inference, aggregate, or native profiling claim')


if __name__ == '__main__':
    main()
