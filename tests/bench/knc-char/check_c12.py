"""S8-17 host contract for C12: phase order, fields and sensor parsing, inert kernels."""
from pathlib import Path
import subprocess
import sys
import tempfile

ORDER = ['idle', 'x87', 'fma', 'stream', 'fma', 'x87', 'idle']
UNITS = {'idle': ('none', 'none'), 'x87': ('gflop_per_s', 'flop'),
         'fma': ('gflop_per_s', 'flop'), 'stream': ('gbyte_per_s', 'byte')}
KEYS = {'index', 'name', 'seconds', 'samples', 'work', 'work_unit', 'joules_per_op', 'op',
        'freq_khz', 'temp'}
KEYS |= {f'{s}_{k}_watts' for s in ('card', 'core', 'uncore', 'memory') for k in ('mean', 'min', 'max')}
KEYS |= {f'{s}_mean_volts' for s in ('core', 'uncore', 'memory')}
# The m2 fixture (test_power.c): total 110 W; rails 8-10 as power uW, current, voltage uV.
FIXTURE = Path(__file__).resolve().parents[2] / 'acceptance/m2_kernels/sample-power.txt'
EXPECT = {'card': 110.0, 'core': 28.0, 'uncore': 32.0, 'memory': 30.0}
VOLTS = {'core': 1.043, 'uncore': 1.0, 'memory': 1.501}


def run(binary, sensor, *extra):
    return subprocess.run([binary, '--dry-run', '--check', 'c12', '--cores', '1', '--threads', '2',
                           '--phase-seconds', '2', '--power-file', str(sensor), *extra],
                          capture_output=True, text=True, timeout=120)


def phases(binary):
    result = run(binary, FIXTURE)
    assert result.returncode == 0, result.stderr
    rows = [dict(t.split('=', 1) for t in line.split()[1:])
            for line in result.stdout.splitlines() if line.startswith('phase ')]
    assert [r['name'] for r in rows] == ORDER, result.stdout
    for i, row in enumerate(rows):
        assert KEYS <= row.keys(), (row['name'], sorted(KEYS - row.keys()))
        assert int(row['index']) == i and int(row['seconds']) == 2, row
        # Two-second phases minus the dropped first second, at 50 ms.
        assert 10 <= int(row['samples']) <= 21, row
        for rail, watts in EXPECT.items():
            for k in ('mean', 'min', 'max'):
                assert abs(float(row[f'{rail}_{k}_watts']) - watts) < 1e-9, (rail, row)
        for rail, volts in VOLTS.items():
            assert abs(float(row[f'{rail}_mean_volts']) - volts) < 1e-9, (rail, row)
        assert (row['work_unit'], row['op']) == UNITS[row['name']], row
    return rows


def malformed(binary):
    lines = FIXTURE.read_text().splitlines()
    cases = {
        'total not a number': ['garbage'] + lines[1:],
        'negative total': ['-1'] + lines[1:],
        'truncated before rails': lines[:9],
        'rail missing voltage': lines[:7] + ['28000000 0'] + lines[8:],
        'rail junk': lines[:8] + ['32000000 0 1000000junk'] + lines[9:],
        'empty': [],
    }
    with tempfile.TemporaryDirectory() as tmp:
        for label, content in cases.items():
            sensor = Path(tmp) / 'power'
            sensor.write_text(''.join(l + '\n' for l in content))
            result = run(binary, sensor)
            assert result.returncode == 2, (label, result.returncode, result.stdout)
            assert 'malformed power sensor' in result.stderr, (label, result.stderr)
            assert not any(l.startswith('phase ') for l in result.stdout.splitlines()), label
    return len(cases)


if __name__ == '__main__':
    assert len(sys.argv) == 2, 'supply the CHAR_HOST executable'
    rows = phases(sys.argv[1])
    for args in (['--phase-seconds', '1'], ['--phase-seconds', 'x'], ['--power-file']):
        result = subprocess.run([sys.argv[1], '--dry-run', '--check', 'c12', *args],
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 2, args
    bad = malformed(sys.argv[1])
    print(f'PASS C12 host dry run: {len(rows)} phases in order with all fields; '
          f'{bad} malformed sensor files rejected; no card execution')
