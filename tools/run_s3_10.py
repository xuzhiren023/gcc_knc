"""Lead-only card execution of the prepared S3-10 batch.

Usage from the merged checkout: python tools/run_s3_10.py [PROGRAM]
No automatic retry. The full torture suite is one job at -j 30 / 3840 MiB.
Raw output is retained alongside the expected files, including INFO measurements.
"""
import csv
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
OUT = PROJECT / '.work/_shared/tmp/S3-10'


def main():
    lines = (OUT / 'batch.txt').read_text().splitlines()
    rows = list(csv.DictReader((line for line in lines if not line.startswith('#')), delimiter='\t'))
    if sys.argv[1:2] == ['--one']:
        # Stay in-process for card_run: 1661 --file paths exceed Windows argv.
        row = next(r for r in rows if r['program'] == sys.argv[2])
        config = json.loads((PROJECT / 'config/card.local.json').read_text())
        config['memoryMB'] = int(row['memoryMB'])
        cfg = OUT / 'card-job.json'
        cfg.write_text(json.dumps(config), encoding='utf8')
        files = []
        if row['program'] == 'claude-torture':
            files = [OUT / 'claude-torture.list'] + [OUT / line.split()[0] for line in
                      (OUT / 'claude-torture.list').read_text().splitlines()]
        sys.argv = [str(ROOT / 'tools/card_run'), '--config', str(cfg),
                    '--timeout', '900', '--transport-timeout', '900']
        for path in files:
            sys.argv.extend(['--file', str(path)])
        sys.argv.extend([str(OUT / row['program']), *json.loads(row['arguments'])])
        try:
            return runpy.run_path(str(ROOT / 'tools/card_run'))['main']()
        finally:
            cfg.unlink(missing_ok=True)
    selected = sys.argv[1:]
    if selected:
        assert len(selected) == 1 and selected[0] in {r['program'] for r in rows}, selected
    print(lines[0], flush=True)
    failures = 0
    for row in rows:
        name = row['program']
        if selected and name != selected[0]:
            continue
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--one', name],
                                capture_output=True, text=True, errors='replace')
        actual = OUT / (name + '.actual.txt')
        actual.write_text(result.stdout, encoding='utf8')
        (OUT / (name + '.stderr.txt')).write_text(result.stderr, encoding='utf8')
        output = result.stdout.splitlines()
        # card_run appends its JSON status after the program output.
        status = json.loads(output.pop()) if output and output[-1].startswith('{') else {}
        observed = '\n'.join(line for line in output if not line.startswith('INFO ')) + '\n'
        expected = OUT / row['expected']
        ok = result.returncode == 0 and status.get('result_class') == 'program' and observed == expected.read_text()
        print('%s %s actual=%s expected=%s' % ('PASS' if ok else 'FAIL', name, actual, expected), flush=True)
        if not ok:
            failures += 1
            if name == 'claude-torture':
                print('Sources: .work/_shared/gcc/gcc/testsuite/gcc.c-torture/execute/; mapping: ' + str(OUT / 'compile.tsv'))
            elif name.startswith('claude-abi'):
                print('Sources: tests/t2/knc-abi-gaps-{caller,callee}.c')
            elif name.startswith('claude-m1'):
                print('Sources: tests/acceptance/m1_affine/{driver.c,loops.c,affine_fortran.f90}')
            elif name.startswith('claude-inexact'):
                print('Sources: tests/regress/knc-affine-inexact.c; tests/acceptance/m1_affine/loops.c')
            else:
                print('Sources: tests/acceptance/s3_vec_card/{vec_card.c,fp_card.c,fp_special.c}')
            print('Compiler: ' + lines[0] + '; retain both output files and report; do not fix here.', flush=True)
            # A runner refusal or infrastructure failure is not a native result.
            if status.get('result_class') != 'program':
                break
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
