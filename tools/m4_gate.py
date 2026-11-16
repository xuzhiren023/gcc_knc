#!/usr/bin/env python3
"""S13-01 primary staging and lead-only execution/scoring of ADR-0015.

Never invokes a card command during stage. Full results stay sealed; the
engineer sees readiness/pass/fail only. Optional panels are separate work.
"""
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys
import tarfile
import time
from types import SimpleNamespace

import corpus as c
import m4_score as scoring

PREFIX_REVISION = 'b2ce6a9eebf'
DISCLOSURE = ('Serial -O2 GCC-KNC versus GCC 5.1.1, with the SQLite donor assembly exception. '
              '3100/5100 model cores and memory on a 7120, not clock or per-core bandwidth.')
CONTROLS = ('PB-gemm', 'STREAM', 'NPB-CG', 'HPCG', 'zlib', 'SQLite')
# Transport-failure resume (ADR-0015 protocol note): a launch that observed no
# workload result is attempted again, at most this many attempts in all.
TRANSPORT_ATTEMPTS = 5
PROBE_TIMEOUT = 300
PAUSED_EXIT, LATCH_EXIT = 3, 4
DMA_LATCH = 'DMA cleanup unresolved'
_sleep = time.sleep  # tests replace the backoff wait


def backoff_seconds(retry):
    """Wait before re-attempt number `retry` (1-based): 30 s doubling, capped at 10 min."""
    return min(30 * 2 ** (retry - 1), 600)


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
    row = derive_row(job, build, out, err, rc, transport)
    row['card_run_exit'] = rc
    return row


def derive_row(job, build, out, err, rc, transport):
    """One launch row from its stored captures; run and recheck share it."""
    stdout = out.read_text(errors='replace')
    row = c.output_result(job, stdout, err.read_text(errors='replace'), rc)
    row.update(stdout=str(out), stderr=str(err), transport=transport,
               runtime_prefix=next(c.windows_path(f) for f in build['files'] if f.endswith('runtime-prefix.json')))
    row['control_injected'] = ('CORPUS_INJECTED ' + job['program']) in stdout
    # Keep the transport observations in the launch row, not a receipt artifact.
    if (transport.get('result_class') != 'program' or transport.get('program_exit_code') not in ((0,1) if job.get('control') else (0,))
            or transport.get('foreign_processes') or transport.get('overlapping_jobs')
            or transport.get('timingValid') is False):
        row.update(check='fail', cause='transport, exclusivity or resource validity failure')
    return row


def transport_failure(stdout, transport):
    """The card_run class when a launch has no workload result because the
    transport failed before the program started; None when the launch is final.

    Qualifies only: class refused or infrastructure (no receipt at all counts as
    infrastructure), no program exit status, no card execution time and no
    CORPUS_ line in stdout, so no CORPUS_TIME. Pass, fail, timeout, resource and
    any launch whose program reported start are final.
    """
    kind = transport.get('result_class') or 'infrastructure'
    if kind not in ('refused', 'infrastructure'):
        return None
    if re.search(r'^CORPUS_', stdout, re.M) or 'CORPUS_TIME' in stdout:
        return None
    if transport.get('program_exit_code') is not None or transport.get('card_minutes'):
        return None
    return kind


def dma_latch(transport):
    return transport.get('result_class') == 'refused' and DMA_LATCH in str(transport.get('detail', ''))


def stdout_receipt(stdout):
    """card_run prints its result record as the last JSON line of stdout."""
    for line in reversed(stdout.splitlines()):
        if line.startswith('{') and '"result_class"' in line:
            try:
                return json.loads(line)
            except ValueError:
                return {}
    return {}


class RetryLog:
    """Per-block transport-retry log; held-out launches go to the sealed copy."""

    def __init__(self, stage, tag):
        self.stage, self.name = stage, tag + '-transport-retries.json'
        self.entries = c.read_partition(stage, self.name)
        c.write_partition(stage, self.name, self.entries)  # an empty log records zero retries

    def add(self, job, number, **fields):
        entry = dict(launch='%03d' % number, program=job['program'], compiler=job['compiler'],
                     run=job['run'], profile=job['profile'], block=job['block'],
                     control=bool(job.get('control')), utc=datetime.now(timezone.utc).isoformat(), **fields)
        self.entries.append(entry)
        c.write_partition(self.stage, self.name, self.entries)

    def failed_launches(self):
        return sum(e['event'] == 'launch' for e in self.entries)


def keep_attempt(folder, number, kind):
    """Move the canonical NNN captures aside as the next numbered attempt."""
    index = 1 + len(list(folder.glob('%03d.%s-*.stdout' % (number, kind))))
    kept = []
    for stream in ('stdout', 'stderr'):
        source = folder / ('%03d.%s' % (number, stream))
        target = folder / ('%03d.%s-%d.%s' % (number, kind, index, stream))
        if source.exists():
            source.replace(target)
        kept.append(str(target))
    return kept


def launch_until_result(stage, job, build, builds, folder, number, timeout, log):
    """Run one launch until its workload produces a result, pass or fail.

    Returns (row, None), or (None, 'dma-latch' | 'unreachable') when the block
    must pause. A failed transport attempt keeps its captures as
    NNN.transport-K.* plus a retry-log entry and writes no row; only the
    attempt with a workload result is final, under the canonical NNN names.
    """
    out = folder / ('%03d.stdout' % number)
    failures = 0
    for attempt in range(1, TRANSPORT_ATTEMPTS + 1):
        if attempt > 1:
            wait = backoff_seconds(attempt - 1)
            _sleep(wait)
            index = 1 + len(list(folder.glob('%03d.probe-*.stdout' % number)))
            probe_out, probe_err = (folder / ('%03d.probe-%d.%s' % (number, index, s)) for s in ('stdout', 'stderr'))
            probe = {}
            rc = c.card_call(stage, [], 'probe', 'probe', probe_out, probe_err, job['profile'],
                             PROBE_TIMEOUT, record=probe)
            reachable = rc == 0 and probe.get('result_class') == 'program'
            log.add(job, number, event='probe', attempt=attempt, waited_seconds=wait, reachable=reachable,
                    result_class=probe.get('result_class'), exit_code=rc,
                    detail=str(probe.get('detail', ''))[:300], stdout=str(probe_out), stderr=str(probe_err))
            if dma_latch(probe):
                return None, 'dma-latch'
            if not reachable:
                continue
        row = run_job(stage, job, build, builds, folder, number, timeout)
        transport = row['transport']
        kind = transport_failure(out.read_text(errors='replace'), transport)
        if kind is None:
            row['transport_retries'] = failures
            return row, None
        failures += 1
        stdout, stderr = keep_attempt(folder, number, 'transport')
        log.add(job, number, event='launch', attempt=attempt, result_class=kind,
                exit_code=row['card_run_exit'], detail=str(transport.get('detail', ''))[:300],
                stdout=stdout, stderr=stderr)
        if dma_latch(transport):
            return None, 'dma-latch'
    return None, 'unreachable'


def finished_launches(stage, tag, jobs):
    """Numbers of the launches with a final row.

    They must be exactly the first ones in schedule order, except in a block
    started by adopt, whose kept launches may leave gaps that resume fills.
    """
    rows = c.read_partition(stage, tag + '-raw.jsonl')
    numbers = [int(PureWindowsPath(r['stdout']).name.split('.')[0]) for r in rows]
    if len(set(numbers)) != len(numbers) or any(n >= len(jobs) for n in numbers):
        raise ValueError('stored launch records repeat a launch or leave the frozen schedule')
    if not (stage / (tag + '-adopted.json')).exists() and sorted(numbers) != list(range(len(rows))):
        raise ValueError('stored launch records are not a prefix of the frozen schedule')
    for number, row in zip(numbers, rows):
        if any(row.get(k) != jobs[number].get(k) for k in ('program','compiler','run','profile','block','control')):
            raise ValueError('stored launch record does not match the frozen schedule')
    return set(numbers)


def resume_command(args):
    entry = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else Path(__file__).resolve()
    command = 'python.exe "%s" run --stage "%s" --profile %s --block %s --acl-verified --resume' % (
        c.windows_path(entry), c.windows_path(args.stage), args.profile, args.block)
    if getattr(args, 'timeout', 3600) != 3600:
        command += ' --timeout %d' % args.timeout
    return command


def pause_block(args, tag, job, number, reason, log):
    """Stop the block without a row for this launch; --resume continues here."""
    log.add(job, number, event='pause', reason=reason)
    c.write_json(args.stage / (tag + '-paused.json'), dict(
        paused=True, launch='%03d' % number, reason=reason, utc=datetime.now(timezone.utc).isoformat()))
    if reason == 'dma-latch':
        print('card_run refused: DMA cleanup latch present (.work/_state/card-dma-active.lock). '
              'Not deleted: latch recovery is a lead decision. Block %s paused at launch %03d; '
              'finished launches are kept. After recovery, resume with: %s'
              % (tag, number, resume_command(args)), file=sys.stderr)
        return LATCH_EXIT
    print('Card unreachable: launch %03d of block %s had %d transport attempts (launch or probe) and no '
          'workload result; nothing recorded for it. Block paused; finished launches are kept. Resume with: %s'
          % (number, tag, TRANSPORT_ATTEMPTS, resume_command(args)), file=sys.stderr)
    return PAUSED_EXIT


def launches(profile, block, builds, spec):
    plan = schedule(profile, block == 'extension')
    for job in plan:
        prepare_job(job, builds, spec)
    # Negative controls are native launches outside the scored windows.
    controls = [dict(next(j for j in plan if j['program'] == program and j['compiler'] == c.KNC), control=True)
                for program in CONTROLS]
    return controls, plan


def rederive_block(stage, profile, block):
    """Re-derive every launch row of a block from its stored captures.

    Jobs come from the frozen schedule, transport and lead policy from the stored
    launch record; the raw records and captures are only read.
    """
    _, spec = load_freeze(stage)
    builds = c.read_partition(stage, 'builds.json')
    tag = paths(stage, profile, block)
    controls, plan = launches(profile, block, builds, spec)
    stored = {PureWindowsPath(r['stdout']).name: r for r in c.read_partition(stage, tag + '-raw.jsonl')}
    if len(stored) != len(controls + plan):
        raise ValueError('stored launch records do not cover the block')
    rows = []
    for number, job in enumerate(controls + plan):
        name = '%03d.stdout' % number
        raw = stored.get(name)
        if raw is None or any(raw.get(k) != job.get(k) for k in ('program','compiler','run','profile','block','control')):
            raise ValueError('stored launch record does not match the frozen schedule')
        build = prepare_job(job, builds, spec)
        folder = (c.sealed_dir(stage) if job['program'] in c.HELD_OUT else stage) / (tag + '-capture')
        transport = raw.get('transport', {})
        row = derive_row(job, build, folder / name, folder / ('%03d.stderr' % number),
                         transport.get('exit_code', 255), transport)
        row['lead_environment_policy'] = raw.get('lead_environment_policy')
        row['transport_retries'] = raw.get('transport_retries', 0)
        if raw.get('negative_control'):
            row['negative_control'] = True
        rows.append(row)
    return rows


def recheck(args):
    """Lead only: re-derive a completed block's launches from its stored captures.

    Never rewrites captures or the -raw.jsonl records. Writes the -recheck record
    (launches whose check changed; held-out ones sealed), then the derived
    -checked/-controls/-done files; check_block re-derives from then on.
    """
    tag = paths(args.stage, args.profile, args.block)
    if not (args.stage / (tag + '-done.json')).exists():
        raise ValueError('recheck needs a completed block')
    stored = {PureWindowsPath(r['stdout']).name: r for r in c.read_partition(args.stage, tag + '-raw.jsonl')}
    changes = []
    for row in rederive_block(args.stage, args.profile, args.block):
        old = stored[PureWindowsPath(row['stdout']).name]
        if row['check'] != old['check']:
            changes.append(dict(launch=PureWindowsPath(row['stdout']).name, program=row['program'], compiler=row['compiler'],
                                run=row['run'], negative_control=bool(row.get('negative_control')),
                                stored_check=old['check'], stored_cause=old.get('cause'),
                                check=row['check'], cause=row.get('cause')))
    c.write_partition(args.stage, tag + '-recheck.json', changes)
    checked = check_block(args.stage, args.profile, args.block)
    c.write_json(args.stage / (tag + '-done.json'), dict(ready=True, passed=checked, rechecked=True))
    print('Primary block recheck: ' + ('pass' if checked else 'fail'))
    return 0 if checked else 1


ADOPT_UNTIMED = 'adopted: transport failure, no timing observed'
ADOPT_SPLIT = 'adopted: pair split by transport failure'


def timing_observed(stdout):
    return any(line.startswith('CORPUS_TIME ') for line in stdout.splitlines())


def adopt(args):
    """Lead only: start a block from a preserved block's timed launches.

    The source block <from>-<block>-<profile> is only read and copied. A launch
    whose stored capture has a CORPUS_TIME is kept, its row re-derived from the
    copied capture with the current parser (as recheck does). Every other launch
    is unfinished, and so are both members of a frozen AB pair with only one
    timed member, so the pair reruns adjacently; unfinished launches get an entry
    in the new transport-retry log and their captures are kept as
    NNN.adopted-1.*. Then run --resume runs exactly the unfinished launches in
    frozen order. Held-out rows, captures and records stay sealed.
    """
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*', args.source or ''):
        raise ValueError('adopt needs --from naming a preserved block prefix')
    _, spec = load_freeze(args.stage)
    builds = c.read_partition(args.stage, 'builds.json')
    tag = paths(args.stage, args.profile, args.block)
    source = args.source + '-' + tag
    sealed = c.sealed_dir(args.stage)
    if source == tag or not (args.stage / (source + '-started.json')).exists():
        raise ValueError('adopt needs a preserved, started source block')
    if any(p.name.startswith(tag + '-') for d in (args.stage, sealed) for p in d.iterdir()):
        raise ValueError('target block already has records; preserve it first')
    controls, plan = launches(args.profile, args.block, builds, spec)
    jobs = controls + plan
    stored = {}
    for row in c.read_partition(args.stage, source + '-raw.jsonl'):
        # Stored paths name the block before it was preserved; use the launch name only.
        name = PureWindowsPath(row['stdout']).name
        number = int(name.split('.')[0])
        if name in stored or number >= len(jobs) or any(
                row.get(k) != jobs[number].get(k) for k in ('program','compiler','run','profile','block','control')):
            raise ValueError('source launch record does not match the frozen schedule')
        stored[name] = row
    partition = lambda job: sealed if job['program'] in c.HELD_OUT else args.stage
    timed, started = {}, {}
    for number, job in enumerate(jobs):
        out = partition(job) / (source + '-capture') / ('%03d.stdout' % number)
        text = out.read_text(errors='replace') if out.exists() else ''
        raw = stored.get('%03d.stdout' % number)
        timed[number] = timing_observed(text)
        started[number] = bool(text) and transport_failure(text, (raw or {}).get('transport') or stdout_receipt(text)) is None
        if timed[number] and raw is None:
            raise ValueError('a timed source launch has no stored row; lead recovery decision required')
        if not timed[number] and raw is not None and raw.get('time_seconds') is not None:
            raise ValueError('a stored source row has a time its capture lacks')
    reason = {n: ADOPT_UNTIMED for n in timed if not timed[n]}
    pairs = {}
    for number, job in enumerate(jobs):
        if not job.get('control'):
            pairs.setdefault(job['pair_id'], []).append(number)
    split = 0
    for members in pairs.values():
        if len(members) != 2 or members[1] != members[0] + 1:
            raise ValueError('frozen pair is not adjacent')
        if timed[members[0]] != timed[members[1]]:
            split += 1
            for n in members:
                reason[n] = ADOPT_SPLIT
    # Copy, never move: the source block stays exactly as preserved.
    rows, entries = [], c.read_partition(args.stage, source + '-transport-retries.json')
    for entry in entries:
        entry['adopted_from'] = source
    utc = datetime.now(timezone.utc).isoformat()
    for directory in (args.stage, sealed):
        (directory / (tag + '-capture')).mkdir()
    for number, job in enumerate(jobs):
        origin, target = (partition(job) / (name + '-capture') for name in (source, tag))
        for path in sorted(origin.glob('%03d.*' % number)):
            canonical = path.name in ('%03d.stdout' % number, '%03d.stderr' % number)
            if canonical and number in reason:
                shutil.copyfile(path, target / path.name.replace('.', '.adopted-1.', 1))
            else:
                shutil.copyfile(path, target / path.name)
        if number in reason:
            entries.append(dict(launch='%03d' % number, program=job['program'], compiler=job['compiler'],
                                run=job['run'], profile=job['profile'], block=job['block'],
                                control=bool(job.get('control')), utc=utc, event='adopted',
                                reason=reason[number], timing_observed=timed[number],
                                program_started=started[number], source=source))
            continue
        raw = stored['%03d.stdout' % number]
        build = prepare_job(job, builds, spec)
        transport = raw.get('transport', {})
        row = derive_row(job, build, target / ('%03d.stdout' % number), target / ('%03d.stderr' % number),
                         transport.get('exit_code', 255), transport)
        row.update(card_run_exit=raw.get('card_run_exit', transport.get('exit_code')),
                   lead_environment_policy=raw.get('lead_environment_policy'),
                   transport_retries=raw.get('transport_retries', 0), adopted_from=source)
        if job.get('control'):
            row['negative_control'] = True
        rows.append(row)
    c.write_partition(args.stage, tag + '-raw.jsonl', rows)
    c.write_partition(args.stage, tag + '-transport-retries.json', entries)
    for directory, held in ((args.stage, False), (sealed, True)):
        mine = [n for n, job in enumerate(jobs) if (job['program'] in c.HELD_OUT) == held]
        c.write_json(directory / (tag + '-adopted.json'), dict(
            source=source, partition='sealed' if held else 'public', utc=utc,
            kept=sum(n not in reason for n in mine), unfinished=sum(n in reason for n in mine),
            reasons=dict(Counter(reason[n] for n in mine if n in reason)),
            split_pairs=sum(reason.get(n) == ADOPT_SPLIT for n in mine) // 2,
            controls_kept=sum(n not in reason for n in mine if jobs[n].get('control')),
            controls_rerun=sum(n in reason for n in mine if jobs[n].get('control')),
            untimed_but_program_started=sum(started[n] and not timed[n] for n in mine),
            unfinished_launches=['%03d' % n for n in mine if n in reason]))
    c.write_json(args.stage / (tag + '-started.json'), dict(attempted=True, adopted_from=source))
    public = [n for n, job in enumerate(jobs) if job['program'] not in c.HELD_OUT]
    print('Adopted %s from %s: public partition kept %d, unfinished %d; %d launches to run in all; '
          'held-out counts are in the sealed record. Resume with: %s'
          % (tag, source, sum(n not in reason for n in public), sum(n in reason for n in public),
             len(reason), resume_command(args)))
    return 0


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
    resume = getattr(args, 'resume', False)
    started = (args.stage / (tag + '-started.json')).exists()
    if resume:
        if not started or (args.stage / (tag + '-done.json')).exists():
            raise ValueError('--resume continues a started, unfinished block only')
    elif started:
        raise ValueError('block already attempted; preserve it and obtain a lead recovery decision')
    controls, plan = launches(args.profile, args.block, builds, spec)
    jobs = controls + plan
    finished = finished_launches(args.stage, tag, jobs) if resume else set()
    pending = [n for n in range(len(jobs)) if n not in finished]
    if not resume:
        c.write_json(args.stage / (tag + '-started.json'), dict(attempted=True))
    c.write_partition(args.stage, 'plan.json', jobs)
    public_folder = args.stage / (tag + '-capture')
    private_folder = c.sealed_dir(args.stage) / (tag + '-capture')
    public_folder.mkdir(exist_ok=True); private_folder.mkdir(exist_ok=True)
    folder_of = lambda job: private_folder if job['program'] in c.HELD_OUT else public_folder
    log = RetryLog(args.stage, tag)
    if resume and pending:
        first = pending[0]
        job, folder = jobs[first], folder_of(jobs[first])
        orphan = folder / ('%03d.stdout' % first)
        if orphan.exists():
            # Captures without a row: interrupted. Retry only if no timing was observed.
            text = orphan.read_text(errors='replace')
            receipt = stdout_receipt(text)
            if transport_failure(text, receipt) is None:
                print('Launch %03d of block %s has program output but no recorded row; not repeated. '
                      'Lead recovery decision required.' % (first, tag), file=sys.stderr)
                return 1
            stdout, stderr = keep_attempt(folder, first, 'transport')
            log.add(job, first, event='launch', attempt=0, result_class=transport_failure(text, receipt),
                    exit_code=receipt.get('exit_code'), detail='interrupted before a row was recorded',
                    stdout=stdout, stderr=stderr)
        log.add(job, first, event='resume')
        (args.stage / (tag + '-paused.json')).unlink(missing_ok=True)
    # Streams are flushed per launch; a resume appends after the finished launches.
    mode = 'a' if resume else 'w'
    with (args.stage / (tag + '-raw.jsonl')).open(mode) as public, (c.sealed_dir(args.stage) / (tag + '-raw.jsonl')).open(mode) as private:
        for number, job in enumerate(jobs):
            if number in finished:
                continue
            build = prepare_job(job, builds, spec)
            held = job['program'] in c.HELD_OUT
            row, pause = launch_until_result(args.stage, job, build, builds, folder_of(job), number,
                                             args.timeout, log)
            if pause:
                return pause_block(args, tag, job, number, pause, log)
            row['lead_environment_policy'] = policy
            if job.get('control'):
                row['negative_control'] = True
            output = private if held else public
            output.write(json.dumps(row, allow_nan=False) + '\n'); output.flush()
    checked = check_block(args.stage, args.profile, args.block)
    c.write_json(args.stage / (tag + '-done.json'), dict(ready=True, passed=checked,
                                                        transport_retries=log.failed_launches()))
    print('Primary block: ' + ('pass' if checked else 'fail'))
    return 0 if checked else 1


def check_block(stage, profile, block):
    tag = paths(stage, profile, block)
    # After a lead recheck, launches are re-derived from the stored captures.
    rows = (rederive_block(stage, profile, block) if (stage / (tag + '-recheck.json')).exists()
            else c.read_partition(stage, tag + '-raw.jsonl'))
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
    parser.add_argument('action', choices=('stage','freeze','run','recheck','adopt','score'))
    parser.add_argument('--stage', type=Path, default=c.SHARED / 'S13-01')
    parser.add_argument('--profile', choices=('full','3100','5100'))
    parser.add_argument('--block', choices=('initial','extension'), default='initial')
    parser.add_argument('--acl-verified', action='store_true')
    parser.add_argument('--resume', action='store_true',
                        help='run: continue a paused block from its next unfinished launch')
    parser.add_argument('--from', dest='source', metavar='PREFIX',
                        help='adopt: preserved block prefix, e.g. aborted-2 for aborted-2-initial-full')
    parser.add_argument('--extended', action='store_true')
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    args.stage = args.stage.resolve()
    if args.action in ('run', 'recheck', 'adopt') and not args.profile:
        parser.error(args.action + ' requires --profile')
    try:
        return globals()[args.action](args) or 0
    except Exception:
        # No held-out values or diagnostics in engineer-facing console output.
        print('Gate readiness/execution: fail; lead must inspect sealed records', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
