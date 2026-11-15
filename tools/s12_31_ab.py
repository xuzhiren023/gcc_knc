#!/usr/bin/env python3
"""S12-31 paired A/B: staging on the host, and the lead's card round.

HPCG (S11-28 fixed work) and two controls are each built twice from the same
sources with -O2 -march=knc: `before` by the installed GCC-KNC, `after` by the
build tree's compiler through the same driver (-B, at compile time only).
Both are assembled and linked by the installed driver with its runtimes, so
the two programs differ only in the generated assembly.

  stage   host only, shared Cygwin python3
  lead    card jobs, lead only, Windows Python; a finished launch is not
          repeated, so the round can be split over card turns
  report  print the table again"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tarfile

import corpus
import hpcg_round
import storage

OUT = corpus.SHARED / 'S12-31/ab'
SOURCES = corpus.SHARED / 'corpus-build/sources'
PROJECT = corpus.ROOT.parent.parent if corpus.ROOT.parent.name == '.work' else corpus.ROOT
ARMS = ('before', 'after')
# x87 inner loops (the compare-and-jump rule applies); no floating point at
# all (only loop padding may change).
CONTROLS = ('PB-cholesky', 'zlib')
PROGRAMS = ('HPCG',) + CONTROLS
PROFILES = ('full', '3100', '5100')
FLAGS = ['-O2', '-march=knc']


def recipe(program):
    """Driver, flags and (source, flags) units of corpus.build_program's serial build."""
    if program == 'HPCG':
        # The owner's one-line OpenMP fix (S11-18) is inside a pragma that a
        # serial build ignores, so the original sources are the pilot's code.
        hpcg = SOURCES / 'hpcg-3.1/src'
        return 'g++', ['-DHPCG_NO_MPI', '-I' + str(hpcg), '-DHPCG_NO_OPENMP'], [
            (source, []) for source in sorted(hpcg.glob('*.cpp'))]
    if program.startswith('PB-'):
        name = program[3:]
        pb = SOURCES / 'polybench-c-4.2.1-beta'
        flags = ['-I' + str(pb / 'utilities'), '-DPOLYBENCH_DUMP_ARRAYS', '-DDATA_TYPE_IS_DOUBLE']
        flags += ['-D%s=%s' % item for item in corpus.PB[name].items()]
        return 'gcc', flags, [
            (next(pb.rglob(name + '.c')), ['-include', str(corpus.SUPPORT / 'polybench_capture.h')]),
            (pb / 'utilities/polybench.c', []), (corpus.SUPPORT / 'polybench_capture.c', [])]
    lib = SOURCES / 'zlib-1.3.1'
    names = ('adler32', 'crc32', 'deflate', 'infback', 'inffast', 'inflate', 'inftrees', 'trees',
             'zutil', 'compress', 'uncompr')
    return 'gcc', ['-I' + str(lib), '-DCORPUS_ZLIB'], [
        (lib / (name + '.c'), []) for name in names] + [(corpus.SUPPORT / 'roundtrip.c', [])]


def build(program, arm, after, log):
    language, flags, units = recipe(program)
    out = OUT / arm / program
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    driver = corpus.compiler_path(corpus.KNC, language)
    listings = []
    for source, more in units:
        listings.append(out / (source.stem + '.s'))
        corpus.execute([driver, *(after if arm == 'after' else []), *FLAGS, *flags, *more,
                        '-S', source, '-o', listings[-1]], out, log)
    binary = out / 'workload'
    corpus.execute([driver, *FLAGS, *listings, *corpus.link_paths(), '-lm', '-o', binary], out, log)
    corpus.execute([sys.executable, corpus.ROOT / 'tools/knc_lint', binary], out, log)
    files = [binary] + corpus.stage_runtimes(binary, corpus.KNC, out, log)
    return dict(program=program, arm=arm, files=list(map(str, files))), listings


def changed(before, after):
    """Listings that differ in more than alignment directives."""
    code = lambda path: [line for line in path.read_text().splitlines()
                         if not re.match(r'\s*\.p2align\b', line)]
    return [b.name for b, a in zip(before, after) if code(b) != code(a)]


def stage(args):
    if sys.platform != 'cygwin':
        raise RuntimeError('stage with the shared Cygwin python3')
    tc = corpus.SHARED / 'toolchain'
    os.environ['PATH'] = ':'.join([str(tc / 'cross/bin'), str(tc / 'cygwin/bin'), os.environ['PATH']])
    OUT.mkdir(parents=True, exist_ok=True)
    tree = Path(storage.gcc_build_dir(str(PROJECT))) / 'gcc'
    after = ['-B' + str(tree) + '/']
    for language, proper in [('gcc', 'cc1'), ('g++', 'cc1plus')]:
        found = subprocess.check_output([str(corpus.compiler_path(corpus.KNC, language)), *after,
                                         '-print-prog-name=' + proper], text=True).strip()
        if Path(found).parent.resolve() != tree.resolve():
            raise RuntimeError('%s would come from %s, not the build tree' % (proper, found))
    records = []
    with (OUT / 'build.log').open('w') as log:
        for program in PROGRAMS:
            listings = {}
            for arm in ARMS:
                record, listings[arm] = build(program, arm, after, log)
                records.append(record)
            differ = changed(listings['before'], listings['after'])
            print('%s: %d of %d listings differ beyond alignment directives%s' % (
                program, len(differ), len(listings['before']), ': ' + ' '.join(differ) if differ else ''))
            if bool(differ) != (program != 'zlib'):
                raise RuntimeError('%s: zlib has no x87 and must not change; the others must' % program)
    old = corpus.SHARED / 'S11-18'
    for name in ('launch', 'input.bin'):
        shutil.copyfile(old / name, OUT / name)
    hpcg_round.input_file(OUT, 104)
    # The launcher decodes zlib's output with another compiler's build (S11-18).
    peer, = [b for b in json.loads((old / 'builds.json').read_text())
             if b['program'] == 'zlib' and b['compiler'] == corpus.DONOR and b['check'] == 'pass']

    def mode(member):
        member.mode = 0o755 if member.name == 'workload' else 0o644
        return member
    with tarfile.open(OUT / 'peer.tar', 'w') as archive:
        for file in peer['files']:
            if not file.endswith('.json'):
                archive.add(file, arcname=Path(file).name, filter=mode)
    commit = subprocess.check_output(['git', '-C', storage.gcc_tree(str(PROJECT)), 'rev-parse', 'HEAD'],
                                     text=True).strip()
    corpus.write_json(OUT / 'builds.json', dict(after_gcc_commit=commit, builds=records))
    print('Staged and linted, no card run:', OUT)
    print('Lead: python tools/s12_31_ab.py lead   (Windows Python; about 13 minutes per HPCG launch, '
          '12 of them; controls about 15 s and 2 s per launch, 12 each)')


def key(row):
    return row['program'], row['profile'], row['run'], row['arm']


def read_rows():
    path = OUT / 'results.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def lead(args):
    if os.name != 'nt':
        raise RuntimeError('lead requires Windows Python for card_run')
    builds = {(b['program'], b['arm']): b['files']
              for b in json.loads((OUT / 'builds.json').read_text())['builds']}
    capture = OUT / 'capture'
    capture.mkdir(exist_ok=True)
    rows = read_rows()
    for run in range(2):
        for profile in args.profile:
            for program in args.program:
                # The second pair runs in the opposite order.
                for arm in ARMS[::1 - 2 * run]:
                    job = dict(program=program, arm=arm, profile=profile, run=run, threads=1,
                               flags=FLAGS, input=corpus.INPUTS[program])
                    if any(key(r) == key(job) and r['check'] == 'pass' for r in rows):
                        continue
                    files = [corpus.windows_path(f) for f in builds[program, arm] if not f.endswith('.json')]
                    files += [str(OUT / name) for name in
                              {'HPCG': ['hpcg.dat'], 'zlib': ['input.bin', 'peer.tar']}.get(program, [])]
                    name = '-'.join(map(str, key(job)))
                    out, err = capture / (name + '.stdout'), capture / (name + '.stderr')
                    rc = corpus.card_call(OUT, files, program, 'serial', out, err, profile, args.timeout)
                    row = corpus.output_result(job, out.read_text(errors='replace'),
                                               err.read_text(errors='replace'), rc)
                    row.pop('arrays', None)  # compared from the captures in report
                    row.update(stdout=str(out), stderr=str(err))
                    rows = [r for r in rows if key(r) != key(job)] + [row]
                    (OUT / 'results.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
                    print(name, row['check'], row['time_seconds'], row.get('cause', ''), flush=True)
    report(args)


def hpcg_numbers(text):
    value = lambda label: float(re.search(r'^%s=([0-9.eE+-]+)\s*$' % re.escape(label), text, re.M)[1])
    return dict(rating=value('Final Summary::HPCG result is VALID with a GFLOP/s rating of'),
                spmv=value('Benchmark Time Summary::SpMV'), mg=value('Benchmark Time Summary::MG'),
                total=value('Benchmark Time Summary::Total'))


def report(args):
    rows = [r for r in read_rows() if r['check'] == 'pass']
    text = lambda row: Path(row['stdout']).read_text(errors='replace')
    print('after/before below 1 is faster for seconds; above 1 is faster for the HPCG rating')
    for program in PROGRAMS:
        outputs = set()
        for profile in PROFILES:
            arms = {arm: [r for r in rows if r['program'] == program and r['profile'] == profile
                          and r['arm'] == arm] for arm in ARMS}
            if not all(arms.values()):
                continue
            columns = {'launch_seconds': lambda r: r['time_seconds']}
            if program == 'HPCG':
                columns.update((name, lambda r, name=name: hpcg_numbers(text(r))[name])
                               for name in ('rating', 'spmv', 'mg', 'total'))
            for name, get in columns.items():
                before, after = ([get(r) for r in arms[arm]] for arm in ARMS)
                print('%-11s %-5s %-14s before %s after %s after/before %.4f' % (
                    program, profile, name, ' '.join('%.6g' % v for v in before),
                    ' '.join('%.6g' % v for v in after),
                    statistics.median(after) / statistics.median(before)))
            if program.startswith('PB-'):
                outputs.update('\n'.join(line for line in text(r).splitlines()
                                         if line.startswith('CORPUS_ARRAY ')) for r in sum(arms.values(), []))
        if len(outputs) > 1:
            print('%s: FAIL, printed arrays differ between launches' % program)
        elif outputs:
            print('%s: every launch printed the same arrays' % program)
    donor = [hpcg_numbers(Path(r['stdout']).read_text(errors='replace'))['rating']
             for r in map(json.loads, (hpcg_round.STAGE / 'results.jsonl').read_text().splitlines())
             if r['compiler'] == corpus.DONOR and r['variant'] == 'serial' and r['check'] == 'pass']
    if donor:
        print('GCC 5.1.1 HPCG rating in the S11-28 pilot (same input, earlier round): %.6g to %.6g' % (
            min(donor), max(donor)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=('stage', 'lead', 'report'))
    parser.add_argument('--program', nargs='+', choices=PROGRAMS, default=list(PROGRAMS))
    parser.add_argument('--profile', nargs='+', choices=PROFILES, default=list(PROFILES))
    parser.add_argument('--timeout', type=int, default=1200)
    args = parser.parse_args()
    globals()[args.action](args)
