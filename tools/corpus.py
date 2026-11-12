#!/usr/bin/env python3
"""Frozen M4 corpus: stage on host, lead launches on card, collect on host.

See corpus/README.md. No source patches, compiler builds, or implicit card jobs.
"""
import argparse
from collections import defaultdict, deque
import itertools
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared' if ROOT.parent.name == '.work' else ROOT / '.work/_shared'
SUPPORT = ROOT / 'tools/corpus'
DONOR, KNC = 'gcc-5.1.1', 'gcc-knc'
HELD_OUT = {'PB-adi', 'PB-durbin', 'bzip2'}
PB = {
    'gemm': dict(NI=512, NJ=512, NK=512),
    'atax': dict(M=4096, N=4096),
    'cholesky': dict(N=512),
    'ludcmp': dict(N=512),
    'jacobi-2d': dict(N=512, TSTEPS=100),
    'heat-3d': dict(N=64, TSTEPS=40),
    'adi': dict(N=256, TSTEPS=40),
    'durbin': dict(N=8192),
}
OPENMP = ('STREAM', 'NPB-CG', 'NPB-EP', 'NPB-MG', 'NPB-IS', 'HPCG')
PROGRAMS = tuple('PB-' + name for name in PB) + OPENMP + ('zlib', 'SQLite', 'bzip2')
INPUTS = {'PB-' + name: 'polybench-4.2.1-double-' + '-'.join('%s=%s' % x for x in dims.items())
          for name, dims in PB.items()}
INPUTS.update({p: 'NPB-3.4.2-class-A' for p in OPENMP if p.startswith('NPB-')})
INPUTS.update(STREAM='STREAM-5.10-3x16777216-double-20-iterations',
              HPCG='HPCG-3.1-reference-104x104x104-60s',
              zlib='lcg-seed-11-8MiB-level6', bzip2='lcg-seed-11-8MiB-level9',
              SQLite='sqlite-3.46.1-recursive-100000-v1')
RTOL, ATOL = 1e-8, 1e-10


def flag_sets(extra_flags=None):
    extras = extra_flags or {}
    if set(extras) - {DONOR, KNC}:
        raise ValueError('unknown compiler in extra flags')
    answer = {}
    for compiler in (DONOR, KNC):
        answer[compiler] = []
        for flags in [['-O2']] + extras.get(compiler, []):
            if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags):
                raise ValueError('each extra flag set must be an argument list')
            flags = list(flags)
            if compiler == KNC and '-march=knc' not in flags:
                flags.append('-march=knc')
            if flags not in answer[compiler]:
                answer[compiler].append(flags)
    return answer


def make_plan(repetitions=3, extra_flags=None, *, core_count=None):
    if not isinstance(core_count, int) or isinstance(core_count, bool) or core_count < 1:
        raise ValueError('core_count must come from the card affinity probe')
    if repetitions < 3:
        raise ValueError('at least three repetitions are required')
    variants = flag_sets(extra_flags)
    plan = []
    for program in PROGRAMS:
        for threads in sorted({core_count, 240}) if program in OPENMP else [1]:
            for run in range(repetitions):
                # Alternate first compiler, including additional flag pairs.
                for index in range(max(map(len, variants.values()))):
                    order = (DONOR, KNC) if run % 2 == 0 else (KNC, DONOR)
                    for compiler in order:
                        if index < len(variants[compiler]):
                            plan.append(dict(program=program, compiler=compiler,
                                             flags=variants[compiler][index], run=run,
                                             threads=threads, input=INPUTS[program],
                                             held_out=program in HELD_OUT))
    return plan


def identity(row):
    return (row['program'], row['compiler'], tuple(row['flags']), row['run'],
            row['threads'], row['input'])


def parse_results(text):
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            identity(row)
            if row['check'] not in ('pass', 'fail', 'error'):
                raise ValueError('unknown check result')
            seconds = row['time_seconds']
            if row['check'] == 'pass' and (isinstance(seconds, bool) or
                    not isinstance(seconds, (float, int)) or not math.isfinite(seconds) or seconds <= 0):
                raise ValueError('invalid successful timing')
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('result line %d: %s' % (number, exc)) from exc
        rows.append(row)
    return rows


def checksum_matches(left, right):
    """Compare numeric live-out reductions; no file hashes or provenance data."""
    if not isinstance(left, list) or not isinstance(right, list) or not left or len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if a.get('array') != b.get('array') or a.get('count', 0) <= 0 or a.get('count') != b.get('count'):
            return False
        for field in ('sum', 'abs', 'squares', 'weighted'):
            x, y = a.get(field), b.get(field)
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                return False
            if not math.isfinite(x) or not math.isfinite(y) or not math.isclose(x, y, rel_tol=RTOL, abs_tol=ATOL):
                return False
    return True


def summarize(plan, results):
    expected = {identity(row): row for row in plan}
    observed = defaultdict(list)
    failures = []
    for row in results:
        key = identity(row)
        observed[key].append(row)
        if key not in expected:
            failures.append(dict(row, cause='unexpected launch identity'))
    valid = {}
    groups = defaultdict(dict)
    for key, job in expected.items():
        matches = observed[key]
        if len(matches) != 1 or matches[0]['check'] != 'pass':
            cause = ('missing launch' if not matches else 'duplicate launch' if len(matches) > 1
                     else matches[0].get('cause', matches[0]['check']))
            failures.append(dict(job, cause=cause))
        else:
            row = matches[0]
            seconds = row.get('time_seconds')
            if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) and math.isfinite(seconds) and seconds > 0:
                valid[key] = row
            else:
                failures.append(dict(job, cause='invalid timing'))
        group = (job['program'], job['threads'], job['input'])
        groups[group].setdefault((job['compiler'], tuple(job['flags'])), {})[job['run']] = key
    report = dict(development=[], held_out=[], failures=failures)
    for (program, threads, inp), variants in sorted(groups.items()):
        donors = [v for v in variants if v[0] == DONOR]
        candidates = [v for v in variants if v[0] == KNC]
        for donor, candidate in itertools.product(donors, candidates):
            ratios, complete = [], True
            runs = set(variants[donor]) | set(variants[candidate])
            for run in sorted(runs):
                dk, ck = variants[donor].get(run), variants[candidate].get(run)
                a, b = valid.get(dk), valid.get(ck)
                if a is None or b is None:
                    complete = False
                    continue
                if program.startswith('PB-'):
                    if not checksum_matches(a.get('checksum'), b.get('checksum')):
                        complete = False
                        failures.append(dict(expected[ck], cause='PolyBench checksum mismatch', check='fail'))
                        continue
                ratios.append(a['time_seconds'] / b['time_seconds'])
            row = dict(program=program, threads=threads, input=inp,
                       donor_flags=list(donor[1]), candidate_flags=list(candidate[1]),
                       speedup=statistics.median(ratios) if complete and len(ratios) >= 3 else None)
            report['held_out' if program in HELD_OUT else 'development'].append(row)
    for partition, field in [('development', 'median_speedup'), ('held_out', 'held_out_median_speedup')]:
        values = [row['speedup'] for row in report[partition]]
        # An incomplete corpus never receives a misleading headline median.
        report[field] = statistics.median(values) if values and all(v is not None for v in values) else None
    return report


def extract_packages(destination):
    """Unpack once into a fixed shared directory, never write into a package."""
    destination.mkdir(parents=True, exist_ok=True)
    for archive in sorted((SHARED / 'corpus').iterdir()):
        if archive.name.endswith('.tar.gz'):
            with tarfile.open(archive) as package:
                members = package.getmembers()
                for member in members:
                    target = (destination / member.name).resolve()
                    if not target.is_relative_to(destination.resolve()) or member.issym() or member.islnk():
                        raise ValueError('unsafe archive member: ' + member.name)
                top = members[0].name.split('/')[0]
                if not (destination / top).exists():
                    package.extractall(destination)
        elif archive.suffix == '.zip':
            with zipfile.ZipFile(archive) as package:
                for name in package.namelist():
                    if not (destination / name).resolve().is_relative_to(destination.resolve()):
                        raise ValueError('unsafe zip member')
                if not (destination / package.namelist()[0].split('/')[0]).exists():
                    package.extractall(destination)
        elif archive.name == 'stream.c' and not (destination / archive.name).exists():
            shutil.copyfile(archive, destination / archive.name)


def execute(command, cwd, log):
    command = list(map(str, command))
    log.write('COMMAND ' + json.dumps(command) + '\n')
    log.flush()
    result = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('exit %d: %s (see build.log)' % (result.returncode, command[0]))


def compiler_prefix(compiler):
    return SHARED / ('toolchain/cross' if compiler == DONOR else 'gcc-knc-16.2.0')


def compiler_path(compiler, language='gcc'):
    return compiler_prefix(compiler) / 'bin' / ('k1om-mpss-linux-' + language)


def link_paths():
    # The old cross linker does not automatically search the relocated sysroot
    # for transitive DT_NEEDED dependencies (for example librt -> libpthread).
    sysroot = SHARED / 'toolchain/sysroot'
    return ['-Wl,-rpath-link,' + str(sysroot / 'lib64'),
            '-Wl,-rpath-link,' + str(sysroot / 'usr/lib64')]


def stage_runtimes(binary, compiler, directory, log):
    """Resolve compiler runtimes via that driver, never borrow the other prefix."""
    readelf = SHARED / 'toolchain/cross/bin/k1om-mpss-linux-readelf'
    queue, seen, files = [binary], set(), []
    system = {'libc.so.6', 'libm.so.6', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1', 'ld-linux-k1om.so.2'}
    while queue:
        current = queue.pop()
        output = subprocess.check_output([str(readelf), '-d', str(current)], text=True)
        for name in re.findall(r'\(NEEDED\).*\[(.*?)\]', output):
            if name in system or name in seen:
                continue
            seen.add(name)
            found = subprocess.check_output([str(compiler_path(compiler)), '-print-file-name=' + name], text=True).strip()
            path = Path(found)
            if found == name or not path.is_file():
                raise RuntimeError('runtime unavailable from %s: %s' % (compiler, name))
            # The selected driver can legitimately use the configured sysroot.
            log.write('RUNTIME %s %s\n' % (name, path))
            target = directory / name
            shutil.copyfile(path, target)
            files.append(target)
            queue.append(target)
    return files


def build_program(program, compiler, flags, source, out, log, setparams):
    cc = compiler_path(compiler)
    common = list(flags)
    sources, extra, language = [], [], 'gcc'
    if program.startswith('PB-'):
        name = program[3:]
        pb = source / 'polybench-c-4.2.1-beta'
        benchmark = next(pb.rglob(name + '.c'))
        extra = ['-I' + str(pb / 'utilities'), '-DPOLYBENCH_DUMP_ARRAYS', '-DDATA_TYPE_IS_DOUBLE']
        extra += ['-D%s=%s' % item for item in PB[name].items()]
        # Redirect only the benchmark's dump calls; original files stay untouched.
        execute([cc, *common, *extra, '-include', SUPPORT / 'polybench_capture.h',
                 '-c', benchmark, '-o', out / 'benchmark.o'], out, log)
        sources = [out / 'benchmark.o', pb / 'utilities/polybench.c', SUPPORT / 'polybench_capture.c']
    elif program == 'STREAM':
        sources = [source / 'stream.c']
        extra = ['-fopenmp', '-DSTREAM_ARRAY_SIZE=16777216', '-DNTIMES=20']
    elif program.startswith('NPB-'):
        name = program[4:]
        npb = source / 'NPB3.4.2/NPB3.4-OMP'
        config = out.parent / 'config'
        config.mkdir(exist_ok=True)
        (config / 'make.def').write_text('F77 = gfortran\nFLINK = gfortran\nCC = gcc\nCLINK = gcc\n'
                                       'FFLAGS = ' + ' '.join(common) + '\nCFLAGS = ' + ' '.join(common) + '\nRAND = randi8\n')
        (out / 'npbparams.h').unlink(missing_ok=True)
        execute([setparams, name.lower(), 'A'], out, log)
        extra = ['-fopenmp', '-I' + str(out), '-I' + str(npb / 'common')]
        if name == 'IS':
            sources = [npb / 'IS/is.c'] + [npb / 'common' / f for f in ('c_print_results.c', 'c_timers.c', 'wtime.c')]
        else:
            language = 'gfortran'
            # Build the C timer with C, then link the ordered Fortran modules.
            execute([cc, *common, '-I' + str(npb / 'common'), '-c', npb / 'common/wtime.c',
                     '-o', out / 'wtime.o'], out, log)
            sources = [npb / name / (name.lower() + '_data.f90'), npb / name / (name.lower() + '.f90')]
            if name == 'EP':
                sources.append(npb / name / 'verify.f90')
            sources += [npb / 'common' / f for f in ('print_results.f90', 'randi8.f90', 'timers.f90')]
            sources.append(out / 'wtime.o')
    elif program == 'HPCG':
        hpcg = source / 'hpcg-3.1/src'
        sources = sorted(hpcg.glob('*.cpp'))
        extra, language = ['-fopenmp', '-DHPCG_NO_MPI', '-I' + str(hpcg)], 'g++'
    elif program == 'zlib':
        lib = source / 'zlib-1.3.1'
        sources = [lib / (s + '.c') for s in ('adler32', 'crc32', 'deflate', 'infback', 'inffast', 'inflate', 'inftrees', 'trees', 'zutil', 'compress', 'uncompr')]
        sources.append(SUPPORT / 'roundtrip.c')
        extra = ['-I' + str(lib), '-DCORPUS_ZLIB']
    elif program == 'bzip2':
        lib = source / 'bzip2-1.0.8'
        sources = [lib / (s + '.c') for s in ('blocksort', 'huffman', 'crctable', 'randtable', 'compress', 'decompress', 'bzlib')]
        sources.append(SUPPORT / 'roundtrip.c')
        extra = ['-I' + str(lib)]
    elif program == 'SQLite':
        lib = source / 'sqlite-amalgamation-3460100'
        sources = [lib / 'sqlite3.c', SUPPORT / 'sqlite.c']
        extra = ['-I' + str(lib), '-lpthread', '-ldl']
    binary = out / 'workload'
    execute([compiler_path(compiler, language), *common, *extra, *sources, *link_paths(), '-lm', '-o', binary], out, log)
    execute([sys.executable, ROOT / 'tools/knc_lint', binary], out, log)
    return [binary] + stage_runtimes(binary, compiler, out, log)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def windows_path(value):
    value = str(value)
    match = re.match(r'^/cygdrive/([a-zA-Z])/(.*)', value)
    return match[1].upper() + ':/' + match[2] if match else value


def stage(args):
    if os.name == 'nt':
        raise RuntimeError('stage with the shared Cygwin Python (see README)')
    source = SHARED / 'corpus-build/sources'
    extract_packages(source)
    stage_dir = args.stage.resolve()
    stage_dir.mkdir(parents=True, exist_ok=True)
    settings = dict(extra_flags=args.extra_flags, repetitions=args.repetitions)
    if args.only:
        previous = json.loads((stage_dir / 'settings.json').read_text())
        if settings != previous:
            raise ValueError('selective staging must preserve the existing flag sets and repetitions')
        records = [r for r in json.loads((stage_dir / 'builds.json').read_text()) if r['program'] not in args.only]
    else:
        records = []
    # Inputs are staged once and shared by every compiler and flag set.
    if not args.only:
        state = 11
        data = bytearray()
        text = b'GCC KNC corpus fixed input\n'
        for i in range(8 * 1024 * 1024):
            state = (1664525 * state + 1013904223) & 0xffffffff
            data.append((state >> 24) if i % 4096 < 1024 else text[i % len(text)])
        (stage_dir / 'input.bin').write_bytes(data)
        shutil.copyfile(SUPPORT / 'input.sql', stage_dir / 'input.sql')
        # Reference input, retained verbatim in the package; no source edits.
        shutil.copyfile(source / 'hpcg-3.1/bin/hpcg.dat', stage_dir / 'hpcg.dat')
        with (stage_dir / 'support.log').open('w') as log:
            execute([compiler_path(DONOR), '-O2', SUPPORT / 'launch.c', *link_paths(), '-lrt', '-pthread', '-o', stage_dir / 'launch'], stage_dir, log)
            execute([sys.executable, ROOT / 'tools/knc_lint', stage_dir / 'launch'], stage_dir, log)
            execute(['gcc', source / 'NPB3.4.2/NPB3.4-OMP/sys/setparams.c', '-o', stage_dir / 'setparams'], stage_dir, log)
    for compiler, variants in flag_sets(args.extra_flags).items():
        for variant, flags in enumerate(variants):
            for program in PROGRAMS:
                if args.only and program not in args.only:
                    continue
                out = SHARED / 'corpus-build' / compiler / str(variant) / program
                out.mkdir(parents=True, exist_ok=True)
                # Clear stale artifacts in this fixed, harness-owned build folder.
                for old in out.iterdir():
                    if old.is_file():
                        old.unlink()
                record = dict(program=program, compiler=compiler, flags=flags,
                              held_out=program in HELD_OUT, log=str(out / 'build.log'))
                with (out / 'build.log').open('w') as log:
                    try:
                        files = build_program(program, compiler, flags, source, out, log, stage_dir / 'setparams')
                        dest = stage_dir / compiler / str(variant) / program
                        dest.mkdir(parents=True, exist_ok=True)
                        for old in dest.iterdir():
                            if old.is_file():
                                old.unlink()
                        staged = []
                        for file in files:
                            shutil.copyfile(file, dest / file.name)
                            staged.append(str(dest / file.name))
                        record.update(check='pass', files=staged)
                    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                        log.write(str(exc) + '\n')
                        log.flush()
                        with (out / 'build.log').open(errors='replace') as diagnostics:
                            diagnostic = [s.strip() for s in deque(diagnostics, maxlen=30)]
                        reasons = [s for s in diagnostic if re.search(r'error:|undefined reference|cannot find|runtime unavailable|forbidden', s, re.I)]
                        record.update(check='error', cause=str(exc) + ': ' + ' | '.join(reasons[-3:])[:1000], files=[])
                records.append(record)
                print('%s %s %s: %s' % (compiler, program, flags, record['check']), flush=True)
    write_json(stage_dir / 'builds.json', records)
    write_json(stage_dir / 'settings.json', settings)
    # Runtime dependencies are staged per compiler, all input and runtime files
    # are transferred by card_run; the lead invokes this script explicitly.
    write_lead_script(stage_dir)
    (stage_dir / 'lead.sh').unlink(missing_ok=True)
    print('Staged lead script:', stage_dir / 'lead.ps1')
    print('Baseline estimate: 70-110 min including staging; no native timing calibration yet.')
    print('Build failures:', sum(r['check'] != 'pass' for r in records), 'of', len(records))


def write_lead_script(stage_dir):
    project = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
    quote = lambda path: "'" + windows_path(path).replace("'", "''") + "'"
    (stage_dir / 'lead.ps1').write_text(
        "# Windows Python is required by card_run. Prefer the merged checkout.\n" +
        "# Baseline estimate: 70-110 minutes; native calibration is pending.\n" +
        '$corpusEntry = ' + quote(project / 'tools/corpus.py') + '\n' +
        'if (!(Test-Path -LiteralPath $corpusEntry)) { $corpusEntry = ' + quote(Path(__file__).resolve()) + ' }\n' +
        '& (Get-Command python.exe).Source $corpusEntry lead --stage ' + quote(stage_dir) + '\nexit $LASTEXITCODE\n')
    shutil.copyfile(SUPPORT / 'README.md', stage_dir / 'README.md')


def output_result(job, stdout, stderr, returncode):
    row = dict(job, check='error', time_seconds=None)
    try:
        if returncode:
            raise ValueError('card_run exit %d' % returncode)
        meta = [json.loads(line[len('CORPUS_META '):]) for line in stdout.splitlines() if line.startswith('CORPUS_META ')]
        times = [float(line.split()[1]) for line in stdout.splitlines() if line.startswith('CORPUS_TIME ')]
        if len(meta) != 1 or meta[0]['threads'] != job['threads'] or len(times) != 1 or not math.isfinite(times[0]) or times[0] <= 0:
            raise ValueError('missing or mismatched native timing/affinity metadata')
        row.update(time_seconds=times[0], affinity=meta[0])
        text = stdout + '\n' + stderr
        program = job['program']
        if program.startswith('PB-'):
            checks = [json.loads(line[len('CORPUS_ARRAY '):]) for line in stdout.splitlines() if line.startswith('CORPUS_ARRAY ')]
            if not checksum_matches(checks, checks):
                raise ValueError('missing or nonfinite PolyBench checksums')
            row['checksum'] = checks
        elif program.startswith('NPB-'):
            if not re.search(r'Verification\s*=\s*SUCCESSFUL', text, re.I) or re.search(r'UNSUCCESSFUL|VERIFICATION FAILED', text, re.I):
                raise ValueError('NPB verification failed or absent')
        elif program == 'STREAM':
            if 'Solution Validates:' not in text or 'Failed Validation' in text:
                raise ValueError('STREAM verification failed or absent')
        elif program == 'HPCG':
            if 'HPCG result is VALID' not in text or 'INVALID' in text or 'Result=FAILED' in text:
                raise ValueError('HPCG validity report failed or absent')
        elif 'CORPUS_CHECK pass' not in stdout:
            raise ValueError('correctness check failed or absent')
        row['check'] = 'pass'
    except (ValueError, KeyError, TypeError) as exc:
        row.update(check='fail' if row['time_seconds'] is not None else 'error', cause=str(exc))
    return row


def card_call(stage_dir, files, mode, density, stdout, stderr):
    # Called only by the explicit lead subcommand, never by stage or collect.
    command = [sys.executable, str(ROOT / 'tools/card_run'), '--benchmark', '--threads', '240',
               '--timeout', '180' if mode == 'HPCG' else '45']
    for file in files:
        command += ['--file', str(file)]
    command += [str(stage_dir / 'launch'), density, mode]
    with stdout.open('w') as out, stderr.open('w') as err:
        return subprocess.run(command, stdout=out, stderr=err).returncode


def lead(args):
    if os.name != 'nt':
        raise RuntimeError('lead requires Windows Python for card_run and its Windows OpenSSH paths')
    stage_dir = args.stage.resolve()
    settings = json.loads((stage_dir / 'settings.json').read_text())
    builds = json.loads((stage_dir / 'builds.json').read_text())
    capture = stage_dir / 'capture'
    capture.mkdir(exist_ok=True)
    out, err = capture / 'probe.stdout', capture / 'probe.stderr'
    rc = card_call(stage_dir, [], 'probe', 'probe', out, err)
    if rc:
        raise RuntimeError('card affinity probe failed; see ' + str(err))
    metadata = [json.loads(s[len('CORPUS_META '):]) for s in out.read_text().splitlines() if s.startswith('CORPUS_META ')]
    if len(metadata) != 1:
        raise RuntimeError('missing card topology probe')
    plan = make_plan(**settings, core_count=metadata[0]['cores'])
    write_json(stage_dir / 'plan.json', plan)
    index = {(r['program'], r['compiler'], tuple(r['flags'])): r for r in builds}
    # Fixed flat output files, overwritten on the next full pass.
    with (stage_dir / 'raw-results.jsonl').open('w') as results:
        for number, job in enumerate(plan):
            build = index[(job['program'], job['compiler'], tuple(job['flags']))]
            if build['check'] != 'pass':
                row = dict(job, check='error', time_seconds=None, cause='build: ' + build['cause'], log=build['log'])
            else:
                files = [windows_path(file) for file in build['files']]
                if job['program'] in ('zlib', 'bzip2'):
                    files.append(str(stage_dir / 'input.bin'))
                elif job['program'] == 'SQLite':
                    files.append(str(stage_dir / 'input.sql'))
                elif job['program'] == 'HPCG':
                    files.append(str(stage_dir / 'hpcg.dat'))
                density = 'serial' if job['program'] not in OPENMP else 'full' if job['threads'] == 240 else 'one'
                out, err = capture / ('%03d.stdout' % number), capture / ('%03d.stderr' % number)
                rc = card_call(stage_dir, files, job['program'], density, out, err)
                row = output_result(job, out.read_text(errors='replace'), err.read_text(errors='replace'), rc)
                row.update(stdout=str(out), stderr=str(err))
            results.write(json.dumps(row, allow_nan=False) + '\n')
            results.flush()
    collect(args)


def collect(args):
    stage_dir = args.stage.resolve()
    plan = json.loads((stage_dir / 'plan.json').read_text())
    rows = parse_results((stage_dir / 'raw-results.jsonl').read_text())
    # Explicitly mark each mismatching candidate as failed in the final JSONL.
    donors = defaultdict(list)
    for row in rows:
        if row['compiler'] == DONOR and row['program'].startswith('PB-'):
            donors[(row['program'], row['run'], row['threads'], row['input'])].append(row)
    for row in rows:
        if row['compiler'] == KNC and row['program'].startswith('PB-') and row['check'] == 'pass':
            paired = donors[(row['program'], row['run'], row['threads'], row['input'])]
            if not paired or any(d['check'] != 'pass' or not checksum_matches(d.get('checksum'), row.get('checksum')) for d in paired):
                row.update(check='fail', cause='PolyBench cross-compiler checksum mismatch or missing reference')
    (stage_dir / 'results.jsonl').write_text(''.join(json.dumps(row, allow_nan=False) + '\n' for row in rows))
    report = summarize(plan, rows)
    write_json(stage_dir / 'summary.json', report)
    lines = []
    for partition, median in [('development', 'median_speedup'), ('held_out', 'held_out_median_speedup')]:
        lines += [partition, 'program | threads | donor flags | candidate flags | speedup', '--- | ---: | --- | --- | ---:']
        for row in report[partition]:
            lines.append('%s | %s | %s | %s | %s' % (row['program'], row['threads'], ' '.join(row['donor_flags']),
                         ' '.join(row['candidate_flags']), 'FAILED' if row['speedup'] is None else '%.4fx' % row['speedup']))
        lines.append('Median: ' + str(report[median]))
    lines += ['Failures:', *[json.dumps(row) for row in report['failures']]]
    (stage_dir / 'summary.md').write_text('\n'.join(lines) + '\n')
    print('Collected %d launches; %d failures; see %s' % (len(rows), len(report['failures']), stage_dir / 'summary.md'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'lead', 'collect'))
    parser.add_argument('--stage', type=Path, default=SHARED / 'S11-11')
    parser.add_argument('--extra-flags', type=json.loads, default={})
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--only', nargs='+', choices=PROGRAMS,
                        help='stage only these programs, retaining previous build records and inputs')
    args = parser.parse_args()
    if args.repetitions < 3:
        parser.error('at least three repetitions')
    globals()[args.action](args)


if __name__ == '__main__':
    main()
