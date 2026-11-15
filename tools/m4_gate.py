#!/usr/bin/env python3
"""S13-01 primary staging and lead-only execution/scoring of ADR-0015.

Never invokes a card command during stage. Full results stay sealed; the
engineer sees readiness/pass/fail only. Optional panels are separate work.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from types import SimpleNamespace

import corpus as c
import m4_score as scoring

PREFIX_REVISION = 'b2ce6a9eebf'
DISCLOSURE = ('Serial -O2 GCC-KNC versus GCC 5.1.1, with the SQLite donor assembly exception. '
              '3100/5100 model cores and memory on a 7120, not clock or per-core bandwidth.')
CONTROLS = ('PB-gemm', 'STREAM', 'NPB-CG', 'HPCG', 'zlib', 'SQLite')


def schedule(profile, extension=False):
    rows = [j for j in c.make_plan(6, core_count=60) if j['panel'] == 'primary' and j['profile'] == profile]
    for i, job in enumerate(rows):
        if extension:
            job['run'] += 6
            job['pair_id'] = '%s/%s/0/%d' % (profile, job['program'], job['run'])
        job['block'] = 'extension' if extension else 'initial'
        job['launch_order'] = i
    if extension:
        for i in range(0, len(rows), 2):
            rows[i], rows[i+1] = rows[i+1], rows[i]
            rows[i]['start_order'], rows[i+1]['start_order'] = 0, 1
            rows[i]['launch_order'], rows[i+1]['launch_order'] = i, i+1
    return rows


def selected_build(job, builds, spec):
    flags = list(spec[job['program']].donor_flags if job['compiler'] == c.DONOR else spec[job['program']].new_flags)
    choices = [b for b in builds if b['program'] == job['program'] and b['compiler'] == job['compiler']
               and b['flags'] == flags and b['variant'] in ('serial', 'optimization-fallback') and b['check'] == 'pass']
    if len(choices) != 1:
        # Avoid any held-out compiler diagnostics in public errors.
        raise ValueError(job['program'] + ': readiness fail')
    return choices[0]


def load_freeze(stage):
    data = json.loads((stage / 'freeze.json').read_text())
    spec = scoring.freeze_primary_spec(data['sqlite_pilot'])
    if data['prefix_revision'] != PREFIX_REVISION or data['inputs'] != c.INPUTS:
        raise ValueError('gate freeze differs from the declared prefix or inputs')
    return data, spec


def environment_valid(row):
    snapshots = row.get('environment', {})
    start, end = snapshots.get('start', {}), snapshots.get('end', {})
    fields = ('governor','minimum_frequency','maximum_frequency','boost','clocksource',
              'transparent_hugepage','MALLOC_ARENA_MAX','MALLOC_MMAP_THRESHOLD_',
              'MALLOC_TRIM_THRESHOLD_','LD_LIBRARY_PATH','LD_PRELOAD','OMP_NUM_THREADS',
              'OMP_DYNAMIC','OMP_PROC_BIND','GOMP_CPU_AFFINITY','affinity')
    if not start or not end or any(not start.get(k) or start.get(k) != end.get(k) for k in fields):
        return False
    if any(start.get(k) == ['unavailable'] for k in ('clocksource','affinity')):
        return False
    for snapshot in (start,end):
        if not snapshot.get('pages') or snapshot['pages'] == ['unavailable'] or not snapshot.get('linked'):
            return False
    # A lead policy record covers power controls absent from generic Linux sysfs.
    return (start['affinity'] == [row['affinity']['cpus']] and
            row['affinity']['threads'] == 1 and start['LD_PRELOAD'] == ['unset'])


def stage(args):
    args.stage.mkdir(parents=True, exist_ok=True)
    c.stage(SimpleNamespace(stage=args.stage, extra_flags={}, repetitions=6, only=None, primary_only=True))
    print('Host builds/references staged. Finalize with Windows Python: tools/m4_gate.py freeze')


def freeze(args):
    if os.name != 'nt':
        raise ValueError('freeze uses Windows Python and Windows Git; stage uses Cygwin Python')
    builds = c.read_partition(args.stage, 'builds.json')
    pilot = {}
    for level in scoring.SQLITE_LEVELS:
        build, = [b for b in builds if b['program'] == 'SQLite' and b['compiler'] == c.DONOR and b['flags'] == [level]]
        pilot[level] = dict(assembled=build['check'] == 'pass', diagnostic=build.get('cause', ''))
    spec = scoring.freeze_primary_spec(pilot)
    for job in schedule('full'):
        selected_build(job, builds, spec)
    freeze = dict(prefix_revision=PREFIX_REVISION, prefix=str(c.compiler_prefix(c.KNC)),
                  sqlite_pilot=pilot, primary={p: asdict(s) for p, s in spec.items()},
                  inputs=c.INPUTS, runner_revision=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                  disclosure=DISCLOSURE, controls=list(CONTROLS))
    c.write_json(args.stage / 'freeze.json', freeze)
    # Keep the exact small host runner after this worktree is deleted on merge.
    runner = args.stage / 'runner'
    runner.mkdir(exist_ok=True)
    for name in ('corpus.py','m4_gate.py','m4_score.py'):
        shutil.copyfile(Path(__file__).parent / name, runner / name)
    project = c.ROOT.parent.parent if c.ROOT.parent.name == '.work' else c.ROOT
    (runner / 'entry.py').write_text(
        'from pathlib import Path\nimport corpus, m4_score\n'
        'corpus.ROOT = Path(' + repr(c.windows_path(project)) + ')\n'
        'corpus.SHARED = Path(' + repr(c.windows_path(c.SHARED)) + ')\n'
        'm4_score.SEALED_ROOT = corpus.SHARED / "m4-sealed"\n'
        'import m4_gate\nraise SystemExit(m4_gate.main())\n')
    for block in ('initial', 'extension'):
        plan = sum((schedule(p, block == 'extension') for p in ('full','3100','5100')), [])
        c.write_partition(args.stage, block + '-plan.json', plan)
        entry = c.windows_path(runner / 'entry.py').replace("'", "''")
        destination = c.windows_path(args.stage).replace("'", "''")
        script = ("param([ValidateSet('full','3100','5100')][string]$Profile, [switch]$AclVerified)\n"
                  "if (!$Profile -or !$AclVerified) { throw 'Lead must select profile and verify sealed ACLs first' }\n"
                  "& python.exe '" + entry + "' run --stage '" + destination + "' --profile $Profile --block " + block +
                  " --acl-verified\nexit $LASTEXITCODE\n")
        (args.stage / (block + '.ps1')).write_text(script)
    (args.stage / 'lead.ps1').unlink(missing_ok=True)  # Never leave the pilot entry point beside the gate.
    (args.stage / 'README.md').write_text((c.SUPPORT / 'gate-readme.md').read_text())
    print('Primary gate readiness: pass; native correctness: not run')


def paths(stage, profile, block):
    # Every profile/block has its own declared record, never overwrite another.
    return '%s-%s' % (block, profile)


def prepare_job(job, builds, spec):
    build = selected_build(job, builds, spec)
    job.update(flags=build['flags'], variant=build['variant'], primary=asdict(spec[job['program']]))
    return build


def run_job(stage, job, build, builds, folder, number, timeout):
    files = [c.windows_path(f) for f in build['files'] if not f.endswith('.json')]
    program = job['program']
    if program in ('zlib','bzip2'):
        files.append(c.windows_path(stage / 'input.bin'))
        peer, = [b for b in builds if b['program'] == program and b['compiler'] != job['compiler']
                 and b['check'] == 'pass' and b['variant'] == 'serial']
        archive_path = folder / 'peer.tar'
        with tarfile.open(archive_path, 'w', format=tarfile.USTAR_FORMAT) as archive:
            for filename in peer['files']:
                if filename.endswith('.json'):
                    continue
                info = archive.gettarinfo(c.windows_path(filename), arcname=Path(filename).name)
                info.mode = 0o755 if info.name == 'workload' else 0o644
                with open(c.windows_path(filename), 'rb') as source:
                    archive.addfile(info, source)
        files.append(c.windows_path(archive_path))
    if program == 'SQLite':
        files.append(c.windows_path(stage / 'input.sql'))
    if program == 'HPCG':
        files.append(c.windows_path(stage / 'hpcg.dat'))
    out, err = folder / ('%03d.stdout' % number), folder / ('%03d.stderr' % number)
    transport = {}
    rc = c.card_call(stage, files, program + ('-control' if job.get('control') else ''),
                     'serial', out, err, job['profile'], timeout, record=transport)
    row = c.output_result(job, out.read_text(errors='replace'), err.read_text(errors='replace'), rc)
    row.update(stdout=str(out), stderr=str(err), transport=transport,
               runtime_prefix=next(c.windows_path(f) for f in build['files'] if f.endswith('runtime-prefix.json')))
    row['control_injected'] = ('CORPUS_INJECTED ' + program) in out.read_text(errors='replace')
    # Keep the transport observations in the launch row, not a receipt artifact.
    if (transport.get('result_class') != 'program' or transport.get('program_exit_code') not in ((0,1) if job.get('control') else (0,))
            or transport.get('foreign_processes') or transport.get('overlapping_jobs')
            or transport.get('timingValid') is False):
        row.update(check='fail', cause='transport, exclusivity or resource validity failure')
    return row


def run(args):
    if not args.acl_verified:
        raise ValueError('lead must provision and verify sealed ACLs before run')
    freeze, spec = load_freeze(args.stage)
    policy = json.loads((args.stage / 'environment-policy.json').read_text())
    if not policy.get('lead_verified') or not policy.get('clock_power_policy') or not policy.get('exclusive_window'):
        raise ValueError('lead must freeze clock/power policy and exclusive window before run')
    builds = c.read_partition(args.stage, 'builds.json')
    tag = paths(args.stage, args.profile, args.block)
    order = ('full','3100','5100')
    for preceding in order[:order.index(args.profile)]:
        if not (args.stage / (args.block + '-' + preceding + '-done.json')).exists():
            raise ValueError('profiles must run in frozen 7120/3100/5100 order')
    if args.block == 'extension':
        report = json.loads((c.sealed_dir(args.stage) / 'score.json').read_text())
        if not report.get('extend'):
            raise ValueError('predeclared extension is not called for by the protocol')
        for p in ('full','3100','5100'):
            if not (args.stage / ('initial-' + p + '-done.json')).exists():
                raise ValueError('all three initial profiles must finish first')
    if (args.stage / (tag + '-started.json')).exists():
        raise ValueError('block already attempted; preserve it and obtain a lead recovery decision')
    plan = schedule(args.profile, args.block == 'extension')
    for job in plan:
        prepare_job(job, builds, spec)
    c.write_json(args.stage / (tag + '-started.json'), dict(attempted=True))
    # Negative controls are native launches outside the scored windows.
    controls = []
    for program in CONTROLS:
        job = dict(next(j for j in plan if j['program'] == program and j['compiler'] == c.KNC), control=True)
        controls.append(job)
    c.write_partition(args.stage, 'plan.json', controls + plan)
    public_folder = args.stage / (tag + '-capture')
    private_folder = c.sealed_dir(args.stage) / (tag + '-capture')
    public_folder.mkdir(exist_ok=True); private_folder.mkdir(exist_ok=True)
    public_rows, private_rows = [], []
    # Streams are flushed per launch, including interrupted/invalid attempts.
    with (args.stage / (tag + '-raw.jsonl')).open('w') as public, (c.sealed_dir(args.stage) / (tag + '-raw.jsonl')).open('w') as private:
        for number, job in enumerate(controls + plan):
            build = prepare_job(job, builds, spec)
            held = job['program'] in c.HELD_OUT
            row = run_job(args.stage, job, build, builds, private_folder if held else public_folder, number, args.timeout)
            row['lead_environment_policy'] = policy
            if job.get('control'):
                row['negative_control'] = True
            output = private if held else public
            output.write(json.dumps(row, allow_nan=False) + '\n'); output.flush()
    checked = check_block(args.stage, args.profile, args.block)
    c.write_json(args.stage / (tag + '-done.json'), dict(ready=True, passed=checked))
    print('Primary block: ' + ('pass' if checked else 'fail'))
    return 0 if checked else 1


def check_block(stage, profile, block):
    tag = paths(stage, profile, block)
    rows = c.read_partition(stage, tag + '-raw.jsonl')
    # collect is the same independent correctness path used for pilot records.
    controls = [r for r in rows if r.get('negative_control')]
    normal = [r for r in rows if not r.get('negative_control')]
    c.write_partition(stage, 'plan.json', normal)
    c.write_partition(stage, 'raw-results.jsonl', normal)
    c.collect(SimpleNamespace(stage=stage))
    checked = c.read_partition(stage, 'results.jsonl')
    c.write_partition(stage, tag + '-checked.jsonl', checked)
    # PB controls must be rejected by collect's independent oracle, too.
    for row in controls:
        if row['program'].startswith('PB-') and row['check'] == 'pass':
            if not c.reference_matches(row.get('arrays'), c.load_reference(stage, row['program'])):
                row['check'] = 'fail'
                row['cause'] = 'independent complete-output reference failed or unavailable'
    control_good = (Counter(r['program'] for r in controls) == Counter(CONTROLS)
                    and all(r['check'] == 'fail' and r.get('time_seconds') and r.get('control_injected') and
                            r.get('transport', {}).get('result_class') == 'program' for r in controls))
    c.write_partition(stage, tag + '-controls.jsonl', controls)
    return control_good and len(checked) == 204 and all(r['check'] == 'pass' and environment_valid(r) for r in checked)


def score(args):
    _, spec = load_freeze(args.stage)
    models, failures = {}, []
    policies = []
    for profile, model in (('full','7120'), ('3100','3100'), ('5100','5100')):
        blocks = ['initial', 'extension'] if args.extended else ['initial']
        rows = []
        expected = []
        for block in blocks:
            if not check_block(args.stage, profile, block):
                failures.append(dict(profile=profile, reason='correctness or controls failed'))
            rows.extend(c.read_partition(args.stage, paths(args.stage, profile, block) + '-checked.jsonl'))
            expected.extend(schedule(profile, block == 'extension'))
        # Complete exact launch coverage, including duplicate and extra records.
        key = lambda r: (r['program'], r['compiler'], r['run'], r['profile'])
        if Counter(map(key, rows)) != Counter(map(key, expected)):
            failures.append(dict(profile=profile, reason='missing, duplicate or extra launch'))
        programs = {}
        for program in c.PROGRAMS:
            pairs = []
            for run_index in range(12 if args.extended else 6):
                pair = [r for r in rows if r['program'] == program and r['run'] == run_index]
                old = [r for r in pair if r['compiler'] == c.DONOR]
                new = [r for r in pair if r['compiler'] == c.KNC]
                if len(old) != 1 or len(new) != 1:
                    continue
                old, new = old[0], new[0]
                order = (c.DONOR, c.KNC) if (run_index < 6 and run_index % 2 == 0) or (run_index >= 6 and run_index % 2 == 1) else (c.KNC, c.DONOR)
                chronological = sorted(pair, key=lambda r: r.get('start_order', -1))
                good = all(r['check'] == 'pass' and r['threads'] == 1 and r['input'] == c.INPUTS[program]
                           and r.get('primary') == json.loads(json.dumps(asdict(spec[program]))) for r in pair)
                good &= ([r['compiler'] for r in chronological] == list(order)
                         and [r['start_order'] for r in chronological] == [0,1]
                         and old['pair_id'] == new['pair_id']
                         and chronological[0]['timing']['utc_start_ns'] < chronological[1]['timing']['utc_start_ns'])
                good &= old['flags'] == list(spec[program].donor_flags) and new['flags'] == list(spec[program].new_flags)
                for row in pair:
                    policy = row.get('lead_environment_policy', {})
                    good &= bool(policy.get('lead_verified') and policy.get('exclusive_window') and policy.get('clock_power_policy'))
                    policies.append(policy.get('clock_power_policy'))
                keys = ('governor','minimum_frequency','maximum_frequency','boost','clocksource',
                        'transparent_hugepage','MALLOC_ARENA_MAX','MALLOC_MMAP_THRESHOLD_','MALLOC_TRIM_THRESHOLD_')
                good &= all(old.get('environment', {}).get('start', {}).get(k) ==
                            new.get('environment', {}).get('start', {}).get(k) for k in keys)
                if not good:
                    failures.append(dict(profile=profile, program=program, run=run_index, reason='invalid pair'))
                    continue
                pairs.append((old['time_seconds'],new['time_seconds']))
            programs[program] = dict(pairs=pairs, primary=asdict(spec[program]))
        models[model] = programs
    if policies and any(p != policies[0] for p in policies):
        failures.append(dict(reason='clock/power policy changed across the gate'))
    if failures:
        report = dict(held_out=True, ready=False, passed=False, failures=failures, disclosure=DISCLOSURE)
    else:
        review_file = c.sealed_dir(args.stage) / 'reviewed-causes.json'
        reviews = json.loads(review_file.read_text()) if review_file.exists() else {}
        report = scoring.score_models(models, primary_spec=spec, known_causes=reviews)
        report.update(ready=True, disclosure=DISCLOSURE)
        report['owner_target_misses'] = [dict(model=model, program=p,
            status='found; held out, never tuned' if p in c.HELD_OUT else 'development defect')
            for model, result in report['models'].items() for p, value in result['programs'].items() if value['speedup'] <= 1.]
        report['correctness'] = 'every launch passed; all six checker families rejected corruption'
    status = scoring.write_report(report, c.sealed_dir(args.stage) / 'score.json', held_out=True,
                                  ready=report['ready'], passed=report.get('pass',False))
    print(json.dumps(status))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage','freeze','run','score'))
    parser.add_argument('--stage', type=Path, default=c.SHARED / 'S13-01')
    parser.add_argument('--profile', choices=('full','3100','5100'))
    parser.add_argument('--block', choices=('initial','extension'), default='initial')
    parser.add_argument('--acl-verified', action='store_true')
    parser.add_argument('--extended', action='store_true')
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    args.stage = args.stage.resolve()
    if args.action == 'run' and not args.profile:
        parser.error('run requires --profile')
    try:
        return globals()[args.action](args) or 0
    except Exception:
        # No held-out values or diagnostics in engineer-facing console output.
        print('Gate readiness/execution: fail; lead must inspect sealed records', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
