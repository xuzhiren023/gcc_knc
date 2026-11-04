"""S3-10 readiness check, run explicitly after preparing the shared card batch.

This checks host preparation only. It never executes a KNC program.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
OUT = PROJECT / '.work/_shared/tmp/S3-10'


def check():
    batch = OUT / 'batch.txt'
    assert batch.is_file(), 'S3-10 batch has not been prepared'
    rows = list(csv.DictReader((line for line in batch.read_text().splitlines()
                               if not line.startswith('#')), delimiter='\t'))
    programs = {row['program'] for row in rows}
    required = {'claude-m1.mic', 'claude-m1-donor.mic', 'claude-m1-fortran.mic',
                'claude-inexact.mic', 'claude-torture'}
    required.update('claude-%s-O%d.mic' % (name, opt)
                    for name in ('vec', 'fp', 'special') for opt in (0, 2))
    required.update('claude-abi-O%d-%d.mic' % (opt, reverse)
                    for opt in (0, 2) for reverse in (0, 1))
    assert required <= programs, 'missing programs: ' + str(required - programs)
    for row in rows:
        assert (OUT / row['program']).is_file(), row['program']
        assert (OUT / row['expected']).is_file(), row['expected']
        assert isinstance(json.loads(row['arguments']), list), row['arguments']
        assert 0 < int(row['memoryMB']) <= 7168, row['memoryMB']
    for name in ('claude-m1', 'claude-m1-donor', 'claude-m1-fortran'):
        assert (OUT / (name + '.expected.txt')).read_text() == (
            'ACCEPT-PASS scalar=3.00 failures=0\n')
    builds = list(csv.DictReader((OUT / 'compile.tsv').open(), delimiter='\t'))
    sources = {p.name for p in (PROJECT / '.work/_shared/gcc/gcc/testsuite/'
                               'gcc.c-torture/execute').glob('*.c')}
    assert len(sources) == 1692, len(sources)
    assert {row['source'] for row in builds} == sources, 'incomplete torture sweep'
    linked = [row for row in builds if row['result'] == 'linked']
    entries = (OUT / 'claude-torture.list').read_text().splitlines()
    assert entries == [row['program'] + ' ' + row['source'] for row in linked]
    for row in linked:
        assert (OUT / row['program']).is_file(), row['program']
    expected = ''.join('PASS ' + row['source'] + '\n' for row in linked)
    assert (OUT / 'torture.expected.txt').read_text() == expected
    torture = next(row for row in rows if row['program'] == 'claude-torture')
    assert json.loads(torture['arguments']) == [
        '-j', '30', '--limit-mb', '128', 'claude-torture.list']
    assert int(torture['memoryMB']) >= 30 * 128
    assert (OUT / 'claude-inexact.expected.txt').read_text() == (
        'S3-INEXACT PASS failures=0\n')
    print('S3-10 READY: %d batch rows; %d/%d torture programs linked; native NOT RUN'
          % (len(rows), len(linked), len(builds)))


if __name__ == '__main__':
    check()
