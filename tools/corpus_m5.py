#!/usr/bin/env python3
"""M5 staging helpers. No downloads, compiler builds or card launches."""
import argparse
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

import corpus
import genset


def host_check(stage, programs):
    """Build frozen host fixtures, preserving the already validated Q captures.

    Q input and source pins have not changed since the approved red run. Their
    sealed captures can be consumed without rebuilding or rerunning them.
    """
    checked = {}
    q_programs = [p for p in programs if p in corpus.M5_Q_UNITS]
    if q_programs:
        q_stage = corpus.sealed_dir(stage) / 'q-host'
        required = [q for p in q_programs for q in members(p)]
        if any(not (q_stage / 'oracles' / (q + '.txt')).is_file()
               or not (q_stage / 'host' / q / 'O2/stdout').is_file() for q in required):
            with patch.object(genset, 'STAGE', q_stage):
                genset.host_check()
        for program in q_programs:
            references, actuals = [], []
            for q in members(program):
                references.append((q_stage / 'oracles' / (q + '.txt')).read_text())
                directory = q_stage / 'host' / q / 'O2'
                actuals.append(genset.payload((directory / 'stdout').read_text(),
                                              (directory / 'stderr').read_text()))
            checked[program] = '\n'.join(references), '\n'.join(actuals)
    for program in programs:
        if program == 'MilkyWay-Nbody':
            from corpus_milkyway import host_check as milkyway_host
            checked[program] = milkyway_host(stage)
        elif program not in corpus.M5_Q_UNITS:
            raise ValueError('host build not implemented: ' + program)
    return checked


def members(program):
    if program not in corpus.M5_Q_UNITS:
        raise ValueError('not a Q vote: ' + program)
    return ('Q1', 'Q2') if program == 'Q1/Q2' else (program,)


def reference_path(stage, program):
    base = corpus.sealed_dir(stage) if program in corpus.HELD_OUT else stage
    return base / 'references' / (program.replace('/', '-') + '.txt')


def build_q(program, compiler, flags, out, log, runtime_stager):
    """Use the frozen S12-02 drivers at the scored flags, serial throughout."""
    runtime_stager = runtime_stager or genset.runtimes
    parts = []
    for q in members(program):
        binary = genset.build(q, out / q, *(corpus.compiler_path(compiler, lang)
                             for lang in ('gcc', 'g++', 'gfortran')), flags, log)
        target = out / (q + '-workload' if program == 'Q1/Q2' else 'workload')
        shutil.copyfile(binary, target)
        parts.append(target)
    binary = out / 'workload'
    if program == 'Q1/Q2':
        corpus.execute([corpus.compiler_path(compiler), *flags, '-std=gnu99',
                        corpus.SUPPORT / 'q_pair.c', *corpus.link_paths(),
                        '-o', binary], out, log)
        parts.append(binary)
    files = list(parts)
    for executable in parts:
        corpus.execute([sys.executable, corpus.ROOT / 'tools/knc_lint', executable], out, log)
        files.extend(runtime_stager(executable, compiler, out, log))
    return list(dict.fromkeys(files))


def stage_q(stage, oracles, only=None):
    """Stage ten serial builds and a correctness run list for the lead.

    Oracles must come from the already-passed S14-56 host check. Reading them
    does not run that check again. Q3/Q5 references, binaries and diagnostics
    are written only under the sealed partition.
    """
    stage = stage.resolve()
    stage.mkdir(parents=True, exist_ok=True)
    programs = only or corpus.M5_Q_UNITS
    if only and not (stage / 'launch').is_file():
        raise ValueError('selective staging requires the existing linted launcher')
    for program in programs:
        reference = '\n'.join((oracles / (q + '.txt')).read_text() for q in members(program))
        if not reference.strip():
            raise ValueError('empty host oracle: ' + program)
        destination = reference_path(stage, program)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(reference)
    records = [r for r in corpus.read_partition(stage, 'builds.json')
               if r['program'] not in programs]
    for compiler, variants in corpus.flag_sets().items():
        for program in programs:
            record = corpus.stage_build(program, compiler, variants[0], 'serial',
                                        0, None, stage)
            record.update(style=corpus.M5_STYLES[program], source=corpus.M5_SOURCES[program])
            records.append(record)
    corpus.write_partition(stage, 'builds.json', records)
    if not only:
        with (stage / 'support.log').open('w') as log:
            corpus.execute([corpus.compiler_path(corpus.DONOR), '-O2', corpus.SUPPORT / 'launch.c',
                            *corpus.link_paths(), '-lrt', '-pthread', '-o', stage / 'launch'], stage, log)
            corpus.execute([sys.executable, corpus.ROOT / 'tools/knc_lint', stage / 'launch'], stage, log)
    jobs = []
    for record in records:
        if record['program'] not in corpus.M5_Q_UNITS:
            continue
        program = record['program']
        jobs.append(dict(program=program, compiler=record['compiler'], flags=record['flags'],
                         input=corpus.INPUTS[program], style=corpus.M5_STYLES[program],
                         held_out=program in corpus.HELD_OUT, threads=1, variant='serial',
                         check=record['check'], files=record['files'],
                         reference=corpus.windows_path(reference_path(stage, program)),
                         launcher=corpus.windows_path(stage / 'launch'),
                         args=['serial', program], checker='corpus.check_m5_output'))
    corpus.write_partition(stage, 'correctness-jobs.json', jobs)
    failures = sum(r['check'] != 'pass' for r in records if r['program'] in corpus.M5_Q_UNITS)
    print('Q votes staged; %d build failures; no card jobs run' % failures)
    if failures:
        raise RuntimeError('Q staging failed; inspect partitioned builds.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage-q'])
    parser.add_argument('--stage', type=Path, default=corpus.SHARED / 'S14-56')
    parser.add_argument('--only', nargs='+', choices=corpus.M5_Q_UNITS)
    parser.add_argument('--oracles', type=Path,
                        default=corpus.sealed_dir(corpus.SHARED / 'S14-56') / 'q-host/oracles')
    args = parser.parse_args()
    stage_q(args.stage, args.oracles, args.only)


if __name__ == '__main__':
    main()
