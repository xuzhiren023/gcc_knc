"""Stage the IMUL-cost comparison; only the lead runs the card batch."""
import argparse
import difflib
import json
import os
from pathlib import Path
import re
import shlex
import statistics
import subprocess
import sys
import tarfile

import corpus
import s12_21_stage as phase1
import storage

OUT = corpus.SHARED / 'S12-21/phase2'
BASE = corpus.SHARED / phase1.STAGE_SUBDIR
PROGRAMS = tuple(p for p in phase1.DEVELOPMENT if p != 'HPCG')
FLAGS = ['-O2', '-march=knc']


def stage():
    build = Path(storage.gcc_build_dir(storage.main_root())) / 'gcc'
    stamp = json.loads((build.parent / '.gcc-build-stamp.json').read_text())
    if storage.gcc_slot() != '2' or not stamp.get('clean') or not stamp['commit'].startswith('1a4f5aab0a2'):
        raise ValueError('require the lead-built S12-21 lane-2 compiler')
    candidate = OUT / 'new'
    phase1.prepare_stage(candidate)
    original_driver = corpus.compiler_path
    prefix = corpus.compiler_prefix(corpus.KNC)
    # Search installed startup files/libraries first, but take cc1/f951 from
    # the lead-built lane. Both variants use the installed runtime libraries.
    libgcc = Path(subprocess.check_output(
        [str(original_driver(corpus.KNC)), '-print-libgcc-file-name'], text=True).strip()).parent
    for language in ('gcc', 'gfortran'):
        wrapper = OUT / ('new-' + language)
        command = [str(original_driver(corpus.KNC, language)),
                   '-B' + str(libgcc) + '/', '-B' + str(build) + '/',
                   '-L' + str(libgcc)]
        if language == 'gfortran':
            library = Path(subprocess.check_output(
                [str(original_driver(corpus.KNC, language)), '-print-file-name=libgfortran.so'],
                text=True).strip()).parent
            command += ['-L' + str(library), '-fintrinsic-modules-path=' +
                        str(build.parent / 'k1om-mpss-linux/libgfortran')]
        phase1.write(wrapper, '#!/bin/sh\nexec ' + shlex.join(command) + ' "$@"\n')
        wrapper.chmod(0o755)
    corpus.compiler_path = lambda compiler, language='gcc': OUT / ('new-' + language)

    def runtimes(binary, compiler, folder, log):
        corpus.compiler_path = original_driver
        try:
            return phase1.runtime_files(binary, compiler, folder, log)
        finally:
            corpus.compiler_path = lambda compiler, language='gcc': OUT / ('new-' + language)

    try:
        for program in PROGRAMS:
            folder = candidate / program
            folder.mkdir()
            with (folder / 'build.log').open('w') as log:
                corpus.build_program(program, corpus.KNC, FLAGS + ['-save-temps=obj'],
                    corpus.SHARED / 'corpus-build/sources', folder, log, BASE / 'setparams',
                    variant='serial', runtime_stager=runtimes)
            for pattern in ('*.i', '*.ii', '*.o', '*.mod'):
                for path in folder.glob(pattern):
                    path.unlink()
            print('BUILT/LINTED new/' + program, flush=True)
    finally:
        corpus.compiler_path = original_driver
    census()
    package()


def census():
    summary = {}
    for program in PROGRAMS:
        variants = {'old': phase1.assembly_records(BASE / 'default' / program),
                    'new': phase1.assembly_records(OUT / 'new' / program)}
        changes = []
        for name in sorted(set(variants['old']) | set(variants['new'])):
            a = variants['old'].get(name, {}).get('instructions', [])
            b = variants['new'].get(name, {}).get('instructions', [])
            edits = [dict(kind=kind, old=[i, j], new=[k, l])
                     for kind, i, j, k, l in difflib.SequenceMatcher(None, a, b).get_opcodes()
                     if kind != 'equal']
            if edits:
                changes.append(dict(function=name, edits=edits,
                    changed=sum(max(x['old'][1]-x['old'][0], x['new'][1]-x['new'][0]) for x in edits)))
        summary[program] = dict(changed=sum(c['changed'] for c in changes), **{
            label: dict(instructions=sum(len(f['instructions']) for f in records.values()),
                        imul=sum(len(f['imul']) for f in records.values()))
            for label, records in variants.items()})
        phase1.save_json(OUT / 'code' / (program + '.json'), dict(variants=variants, changes=changes))
    phase1.save_json(OUT / 'code-summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


def card_plan(summary):
    if set(summary) != set(PROGRAMS):
        raise ValueError('require all thirteen permitted programs')
    affected = sorted(p for p in PROGRAMS if summary[p]['changed'])
    controls = [p for p in ('NPB-IS', 'STREAM') if not summary[p]['changed']]
    if len(controls) != 2:
        raise ValueError('need two programs with unchanged code as controls')
    # Two repetitions reverse order. The outer card_run limit bounds total
    # time; fixed benchmark inputs are never shortened to fit the reservation.
    rows = [dict(program=p, label=label, run=repeat, threads=1, profile='full',
                 benchmark=True, variant='serial', flags=FLAGS, compiler=corpus.KNC)
            for repeat in range(2) for p in affected + controls
            for label in (('old', 'new') if repeat == 0 else ('new', 'old'))]
    return dict(affected=affected, controls=controls, selected=affected+controls,
                pairs=rows, timeout=1440, total_budget=1500)


def package():
    plan = card_plan(json.loads((OUT / 'code-summary.json').read_text()))
    lines = ['#!/bin/sh', 'set -eu', 'cd -- "$(dirname -- "$0")"',
             'tar -xzf payload.tar.gz', 'chmod +x launch']
    runtimes = {}
    with tarfile.open(OUT / 'payload.tar.gz', 'w:gz', format=tarfile.USTAR_FORMAT) as archive:
        for name in ('launch', 'input.bin', 'input.sql'):
            archive.add(BASE / name, arcname=name)
        for label in ('old', 'new'):
            for program in plan['selected']:
                folder = (BASE / 'default' if label == 'old' else OUT / 'new') / program
                archive.add(folder / 'workload', arcname=label + '/' + program + '/workload')
                for library in folder.glob('*.so*'):
                    runtimes.setdefault(library.name, library)
                if program == 'zlib':
                    peer = (OUT / 'new' if label == 'old' else BASE / 'default') / program
                    peer_tar = OUT / (label + '-peer.tar')
                    with tarfile.open(peer_tar, 'w', format=tarfile.USTAR_FORMAT) as nested:
                        for path in [peer / 'workload', *peer.glob('*.so*')]:
                            nested.add(path, arcname=path.name)
                    archive.add(peer_tar, arcname=label + '/zlib/peer.tar')
                    peer_tar.unlink()
        for name, path in sorted(runtimes.items()):
            archive.add(path, arcname='runtime/' + name)
    if (OUT / 'payload.tar.gz').stat().st_size > 64 * 1024 * 1024:
        raise ValueError('payload exceeds card runner limit')
    for index, row in enumerate(plan['pairs']):
        lines += ['echo S12_21_COST_BEGIN ' + str(index), '(',
                  'cd ' + row['label'] + '/' + row['program'], 'chmod +x workload',
                  'ln -sf ../../input.bin input.bin', 'ln -sf ../../input.sql input.sql',
                  'for lib in ../../runtime/*; do [ ! -f "$lib" ] || ln -sf "$lib" "${lib##*/}"; done',
                  '../../launch serial ' + row['program'], ')',
                  'echo S12_21_COST_END ' + str(index)]
    lines += ['echo "RESULT S12-21 COST PASS"', '']
    phase1.write(OUT / 'batch.sh', '\n'.join(lines))
    subprocess.run(['sh', '-n', str(OUT / 'batch.sh')], check=True)
    phase1.write(OUT / 'files.txt', corpus.windows_path(OUT / 'payload.tar.gz') + '\n')
    phase1.save_json(OUT / 'card-plan.json', plan)
    phase1.write(OUT / 'README.txt',
        'Lead only: exclusive full profile, serial workloads pinned by launch.\n'
        'Two adjacent A/B pairs per program, reverse order on second repetition.\n'
        'HPCG excluded; fixed inputs unchanged. Runner limit 1440 seconds,\n'
        'leaving 60 seconds of the 25-minute budget for transport overhead.\n'
        'Incomplete batch is not a pass; retain its log for review.\n'
        'Baseline: existing phase-one default binaries; candidate: lane-2 code generation.\n'
        'Installed runtimes common to both variants. No native result yet.\n'
        'LEAD (project root; save stdout/stderr to phase2/native.log):\n'
        'python tools/card_run --benchmark --profile full --threads 240 --timeout 1440 '
        '--file-list .work/_shared/S12-21/phase2/files.txt .work/_shared/S12-21/phase2/batch.sh\n'
        'COLLECT: python tools/s12_21_phase2.py collect .work/_shared/S12-21/phase2/native.log\n')
    print('STAGED', plan['affected'], 'controls', plan['controls'],
          len(plan['pairs']), 'runs; shell syntax PASS; native NOT RUN', flush=True)


def collect(path):
    plan = json.loads((OUT / 'card-plan.json').read_text())
    text = path.read_text(errors='replace')
    if text.count('RESULT S12-21 COST PASS') != 1:
        raise ValueError('batch incomplete/failed')
    blocks = re.findall(r'^S12_21_COST_BEGIN (\d+)\r?\n(.*?)^S12_21_COST_END \1\r?$', text, re.M | re.S)
    if [int(i) for i, _ in blocks] != list(range(len(plan['pairs']))):
        raise ValueError('missing, reordered or duplicate run')
    results = [corpus.output_result(dict(row, input=corpus.INPUTS[row['program']]), body, '', 0)
               for row, (_, body) in zip(plan['pairs'], blocks)]
    for a, b in zip(results[::2], results[1::2]):
        if a['check'] != 'pass' or b['check'] != 'pass' or a['affinity'] != b['affinity']:
            raise ValueError('correctness/affinity failure: ' + a['program'])
        if 'arrays' in a and not corpus.arrays_match(a['arrays'], b['arrays']):
            raise ValueError('A/B array mismatch: ' + a['program'])
    answer = {}
    for program in plan['selected']:
        ratios = []
        for repeat in range(2):
            pair = {r['label']: r['time_seconds'] for r in results if r['program'] == program and r['run'] == repeat}
            ratios.append(pair['old'] / pair['new'])
        answer[program] = dict(old_over_new=ratios, median=statistics.median(ratios))
    phase1.save_json(OUT / 'native-analysis.json', dict(programs=answer, results=results,
        qualification='Review exclusive reservation, clocks and sibling activity before interpreting ratios.'))
    print(json.dumps(answer, indent=2))


def main():
    if os.name == 'nt':
        tc = corpus.SHARED / 'toolchain'
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(tc / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'), '-u', __file__], text=True).strip()
        return subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'package', 'collect'))
    parser.add_argument('log', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'collect':
        collect(args.log)
    else:
        globals()[args.action]()
    return 0


if __name__ == '__main__':
    sys.exit(main())
