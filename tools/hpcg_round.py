"""S11-28 staging and explicit lead-only HPCG rounds; no engineer card jobs."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

import corpus

STAGE = corpus.SHARED / 'S11-28'


def input_file(stage, grid):
    (stage / 'hpcg.dat').write_text(
        'HPCG fixed work\nS11-28: one benchmark CG set\n%d %d %d\n0\n' % (grid, grid, grid))


def stage(args):
    dest = args.stage
    dest.mkdir(parents=True, exist_ok=True)
    old = corpus.SHARED / 'S11-18'
    records = []
    for record in json.loads((old / 'builds.json').read_text()):
        if record['program'] != 'HPCG' or record['check'] != 'pass':
            continue
        folder = dest / record['compiler'] / record['variant']
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        for name in record['files']:
            source = Path(corpus.windows_path(name)) if os.name == 'nt' else Path(name)
            if source.suffix == '.json':
                continue
            target = folder / source.name
            shutil.copyfile(source, target)
            files.append(str(target))
        records.append(dict(record, files=files))
    if len(records) != 3:
        raise ValueError('expected donor serial and KNC serial/OpenMP builds')
    shutil.copyfile(old / 'launch', dest / 'launch')
    corpus.write_json(dest / 'builds.json', records)
    input_file(dest, 104)  # Diagnostic candidate, not a frozen grid choice.
    (dest / 'arena.flag').write_text('diagnostic only\n')
    shutil.copyfile(corpus.SUPPORT / 'hpcg_round.md', dest / 'README.md')
    for action in ('memory', 'pilot'):
        command = "& (Get-Command python.exe).Source $entry %s-lead --stage '%s'" % (action, corpus.windows_path(dest))
        header = ''
        if action == 'pilot':
            header = 'param([Parameter(Mandatory=$true)][ValidateSet(80,88,96,104)][int]$Grid)\n'
            command += ' --grid $Grid'
        entry = corpus.windows_path(corpus.ROOT / 'tools/hpcg_round.py')
        fallback = corpus.windows_path(corpus.ROOT.parent.parent / 'tools/hpcg_round.py')
        (dest / ('lead-' + action + '.ps1')).write_text(header +
            "$entry = '%s'\nif (!(Test-Path -LiteralPath $entry)) { $entry = '%s' }\n" % (entry, fallback) +
            command + '\nexit $LASTEXITCODE\n')
    if os.name == 'nt':
        raise RuntimeError('compile diagnostic supervisor with shared Cygwin Python')
    folder = dest / 'monitor'
    folder.mkdir(exist_ok=True)
    with (dest / 'build.log').open('w') as log:
        corpus.execute([corpus.compiler_path(corpus.DONOR), '-O2',
                        corpus.SUPPORT / 'hpcg_memory.c', *corpus.link_paths(),
                        '-o', folder / 'workload'], dest, log)
        corpus.execute([sys.executable, corpus.ROOT / 'tools/knc_lint', folder / 'workload'], dest, log)
    print('Staged HPCG builds and linted memory supervisor:', dest)


def builds(stage):
    return json.loads((stage / 'builds.json').read_text())


def files_for(stage, compiler, variant, diagnostic=False):
    record, = [b for b in builds(stage) if b['compiler'] == compiler and b['variant'] == variant]
    files = [str(Path(corpus.windows_path(f))) for f in record['files']]
    if diagnostic:
        original, = [f for f in files if Path(f).name == 'workload']
        shutil.copyfile(original, stage / 'hpcg')
        files = [f for f in files if f != original]
        files += [str(stage / 'hpcg'), str(stage / 'monitor/workload')]
    return files + [str(stage / 'hpcg.dat')]


def memory_lead(args):
    stage = args.stage
    capture = stage / 'memory'
    capture.mkdir(exist_ok=True)
    cases = [(p, d, 104, False, 'openmp') for p in ('3100', '5100') for d in ('one', 'two', 'full')]
    cases += [('3100', 'full', 104, True, 'openmp')]
    cases += [('3100', 'full', g, False, 'openmp') for g in (96, 88, 80)]
    cases += [('3100', 'serial', 104, False, 'serial')]
    rows = []
    # Eleven independent card_run calls. At most 60s of workload each, plus transport.
    for i, (profile, density, grid, arena, variant) in enumerate(cases):
        input_file(stage, grid)
        files = files_for(stage, corpus.KNC, variant, diagnostic=True)
        if arena:
            files.append(str(stage / 'arena.flag'))
        out, err = capture / ('%02d.stdout' % i), capture / ('%02d.stderr' % i)
        rc = corpus.card_call(stage, files, 'HPCG', density, out, err, profile, timeout=75)
        text = out.read_text(errors='replace')
        peaks = {}
        for field in ('VmPeak', 'VmHWM', 'VmSize'):
            values = [int(v) for v in re.findall(r'^HPCG_MEMORY \d+ ' + field + r':\s+(\d+) kB', text, re.M)]
            peaks[field + '_KiB'] = max(values) if values else None
        complete = False
        try:
            work = corpus.hpcg_work(text)
            complete = rc == 0 and work['sets'] == 1
        except ValueError:
            work = None
        rows.append(dict(profile=profile, density=density, grid=grid, arena=arena,
                         variant=variant, exit_code=rc, complete=complete,
                         hpcg_work=work, stdout=str(out), stderr=str(err), **peaks))
        corpus.write_json(stage / 'memory-results.json', rows)
        print(profile, density, grid, 'arena=2' if arena else 'default', rc, peaks, flush=True)
    input_file(stage, 104)
    print('Partial/timed-out VmHWM values are lower bounds; do not freeze a grid from them.')


def pilot_lead(args):
    stage = args.stage
    if args.grid is None:
        raise ValueError('--grid requires the lead-reviewed memory choice; no default')
    input_file(stage, args.grid)
    capture = stage / 'pilot'
    capture.mkdir(exist_ok=True)
    plan, rows = [], []
    for run in range(2):
        for profile, cores in [('full', 60), ('3100', 56), ('5100', 59)]:
            serial = [(c, 'serial', 'serial', 1) for c in
                      ((corpus.DONOR, corpus.KNC) if run == 0 else (corpus.KNC, corpus.DONOR))]
            panel = [(corpus.KNC, 'openmp', d, cores * n) for d, n in [('one', 1), ('two', 2), ('full', 4)]]
            for compiler, variant, density, threads in serial + panel:
                job = dict(program='HPCG', compiler=compiler, variant=variant,
                           flags=['-O2'] + (['-march=knc'] if compiler == corpus.KNC else []),
                           run=run, threads=threads, profile=profile,
                           input='HPCG-3.1-%dx%dx%d-rt0' % (args.grid, args.grid, args.grid),
                           panel='primary' if variant == 'serial' else corpus.OPENMP_PANEL)
                out, err = capture / ('%02d.stdout' % len(rows)), capture / ('%02d.stderr' % len(rows))
                rc = corpus.card_call(stage, files_for(stage, compiler, variant), 'HPCG', density,
                                      out, err, profile, args.timeout)
                row = corpus.output_result(job, out.read_text(errors='replace'), err.read_text(errors='replace'), rc)
                row.update(stdout=str(out), stderr=str(err))
                plan.append(job)
                rows.append(row)
                corpus.write_json(stage / 'plan.json', plan)
                (stage / 'raw-results.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    corpus.collect(args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'memory-lead', 'pilot-lead'))
    parser.add_argument('--stage', type=Path, default=STAGE)
    parser.add_argument('--grid', type=int, choices=(80, 88, 96, 104))
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()
    if args.action.endswith('-lead') and os.name != 'nt':
        parser.error('lead card rounds require Windows Python')
    globals()[args.action.replace('-', '_')](args)
