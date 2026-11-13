#!/usr/bin/env python3
"""Frozen M4 corpus: stage on host, lead launches on card, collect on host.

See corpus/README.md. Only the ticket-authorized staged HPCG fix is applied.
No compiler builds or implicit card jobs.
"""
import argparse
from collections import defaultdict, deque
import json
import itertools
import statistics
import math
import os
from pathlib import Path
import re
import shutil
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
OPENMP_PANEL = 'the donor toolchain has no OpenMP runtime'
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
    if not isinstance(repetitions, int) or isinstance(repetitions, bool) or repetitions < 3:
        raise ValueError('at least three pairs are required')
    variants = flag_sets(extra_flags)
    plan = []
    # ADR-0015: complete primary rounds before any side panel.
    for side_panel in (False, True):
      for run in range(repetitions):
       for profile, cores in [('full', core_count), ('3100', 56), ('5100', 59)]:
        for program in PROGRAMS:
            panels = [(1, 'serial', 'primary')]
            if side_panel:
                panels = ([(t, 'openmp', OPENMP_PANEL) for t in (cores, cores * 2, cores * 4)]
                          if program in OPENMP else [])
            for threads, variant, panel in panels:
                for index in range(max(map(len, variants.values()))):
                    order = (DONOR, KNC) if run % 2 == 0 else (KNC, DONOR)
                    if side_panel:
                        order = (KNC,)
                    for start_order, compiler in enumerate(order):
                        if index < len(variants[compiler]):
                            plan.append(dict(program=program, compiler=compiler,
                                flags=variants[compiler][index], run=run,
                                threads=threads, input=INPUTS[program],
                                profile=profile, variant=variant, panel=panel,
                                pair_id=None if side_panel else '%s/%s/%d/%d' % (profile, program, index, run),
                                start_order=start_order, launch_order=len(plan),
                                held_out=program in HELD_OUT))
    return plan


def identity(row):
    return (row['program'], row['compiler'], tuple(row['flags']), row['run'],
            row['threads'], row['input'], row.get('profile', 'full'), row.get('variant', 'serial'))


def arrays_match(left, right):
    if not isinstance(left, list) or not isinstance(right, list) or not left or len(left) != len(right):
        return False
    for a, b in zip(left, right):
        x, y = a.get('values'), b.get('values')
        if a.get('array') != b.get('array') or not isinstance(x, list) or not isinstance(y, list) or not x or len(x) != len(y):
            return False
        for u, v in zip(x, y):
            if (not isinstance(u, (int, float)) or not isinstance(v, (int, float))
                    or not math.isfinite(u) or not math.isfinite(v)
                    or not math.isclose(u, v, rel_tol=RTOL, abs_tol=ATOL)):
                return False
    return True


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


# Legacy v1 analysis API; v2 collection emits no scores.
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
    dependencies, installed = {}, []
    def revision(path):
        result = subprocess.run([str(readelf), '-p', '.comment', str(path)],
                                capture_output=True, text=True)
        return result.stdout.strip() or 'revision unavailable in installed ELF'
    while queue:
        current = queue.pop()
        output = subprocess.check_output([str(readelf), '-d', str(current)], text=True)
        needed = re.findall(r'\(NEEDED\).*\[(.*?)\]', output)
        dependencies[current.name] = needed
        for name in needed:
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
            installed.append(dict(name=name, selected_path=str(path.resolve()),
                                  revision=revision(path)))
            queue.append(target)
    record = directory / 'runtime-prefix.json'
    write_json(record, dict(compiler=compiler, prefix=str(compiler_prefix(compiler)),
                           compiler_revision=subprocess.check_output(
                               [str(compiler_path(compiler)), '--version'], text=True).strip(),
                           binary_revision=revision(binary), needed=dependencies,
                           installed_libraries=installed,
                           system_runtime_names=sorted(system & set(sum(dependencies.values(), []))),
                           system_runtime_revision='card supplied; captured by launcher at execution'))
    files.append(record)
    return files


def build_program(program, compiler, flags, source, out, log, setparams, variant='openmp'):
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
        original = hpcg / 'ComputeResidual.cpp'
        fixed = out / original.name
        content = original.read_text()
        before = 'shared(local_residual, v1v, v2v)'
        if content.count(before) != 1:
            raise RuntimeError('HPCG source does not match authorized one-line fix')
        fixed.write_text(content.replace(before, 'shared(local_residual, v1v, v2v, n)'))
        sources = [fixed if p == original else p for p in sources]
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
    if variant == 'serial':
        extra = [f for f in extra if f != '-fopenmp']
        if program == 'HPCG':
            extra.append('-DHPCG_NO_OPENMP')
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


def sealed_dir(stage_dir):
    destination = SHARED / 'm4-sealed' / stage_dir.name
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def write_partition(stage_dir, name, rows):
    private = sealed_dir(stage_dir)
    for directory, held in ((stage_dir, False), (private, True)):
        selected = [r for r in rows if (r['program'] in HELD_OUT) == held]
        if name.endswith('.jsonl'):
            (directory / name).write_text(''.join(json.dumps(r, allow_nan=False) + '\n' for r in selected))
        else:
            write_json(directory / name, selected)


def read_partition(stage_dir, name):
    result = []
    for directory in (stage_dir, sealed_dir(stage_dir)):
        path = directory / name
        if path.exists():
            result.extend(parse_results(path.read_text()) if name.endswith('.jsonl')
                          else json.loads(path.read_text()))
    return result


def stage_build(program, compiler, flags, variant, flag_index, source, stage_dir, reason=None):
    held = program in HELD_OUT
    base = sealed_dir(stage_dir) if held else stage_dir
    # Build diagnostics for held-out programs never enter the public build tree.
    build_base = base / 'build' if held else SHARED / 'corpus-build/v2'
    build_variant = variant
    if variant == 'optimization-fallback':
        build_variant += next(f for f in flags if re.fullmatch(r'-O[0-3]', f))
    out = build_base / compiler / str(flag_index) / build_variant / program
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():
        if old.is_file():
            old.unlink()
    actual_flags = list(flags) + (['-fopenmp'] if program in OPENMP and variant == 'openmp' else [])
    record = dict(program=program, compiler=compiler, flags=actual_flags,
                  requested_flags=list(flags), variant=variant,
                  panel=OPENMP_PANEL if variant == 'openmp' else 'primary',
                  held_out=held, log=str(out / 'build.log'), source_changes=[])
    if reason:
        record['fallback_reason'] = reason
    if program == 'HPCG':
        record['source_changes'] = [dict(file='hpcg-3.1/src/ComputeResidual.cpp',
            reason='Owner S11-18: add n to default(none) shared list in staged copy only')]
    with (out / 'build.log').open('w') as log:
        try:
            files = build_program(program, compiler, flags, source, out, log,
                                  stage_dir / 'setparams', variant)
            dest = base / compiler / str(flag_index) / build_variant / program
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
                diagnostic = list(deque(diagnostics, maxlen=30))
            reasons = [s.strip() for s in diagnostic if re.search(
                r'error:|undefined reference|cannot find|runtime unavailable|forbidden', s, re.I)]
            record.update(check='error', cause=str(exc) + ': ' + ' | '.join(reasons[-3:])[:1000], files=[])
    print('%s: %s' % (program, record['check']) if held else
          '%s %s %s %s: %s' % (compiler, program, variant, actual_flags, record['check']), flush=True)
    return record


def stage(args):
    if os.name == 'nt':
        raise RuntimeError('stage with the shared Cygwin Python (see README)')
    source = SHARED / 'corpus-build/sources'
    extract_packages(source)
    stage_dir = args.stage.resolve()
    stage_dir.mkdir(parents=True, exist_ok=True)
    settings = dict(extra_flags=args.extra_flags, repetitions=args.repetitions or 3)
    if args.only:
        previous = json.loads((stage_dir / 'settings.json').read_text())
        if settings != previous:
            raise ValueError('selective staging must preserve the existing flag sets and repetitions')
        records = [r for r in read_partition(stage_dir, 'builds.json') if r['program'] not in args.only]
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
            execute(['gcc', source / 'NPB3.4.2/NPB3.4-OMP/sys/setparams.c', '-o', stage_dir / 'setparams'], stage_dir, log)
    # Selective restaging must also refresh the launcher protocol.
    with (stage_dir / 'support.log').open('a') as log:
        execute([compiler_path(DONOR), '-O2', SUPPORT / 'launch.c', *link_paths(), '-lrt', '-pthread', '-o', stage_dir / 'launch'], stage_dir, log)
        execute([sys.executable, ROOT / 'tools/knc_lint', stage_dir / 'launch'], stage_dir, log)
    for compiler, flag_variants in flag_sets(args.extra_flags).items():
        for flag_index, flags in enumerate(flag_variants):
            for program in PROGRAMS:
                if args.only and program not in args.only:
                    continue
                variants = ['openmp', 'serial'] if program in OPENMP else ['serial']
                for variant in variants:
                    record = stage_build(program, compiler, flags, variant, flag_index,
                                         source, stage_dir,
                                         OPENMP_PANEL if program in OPENMP and variant == 'serial' else None)
                    records.append(record)
                    if program == 'SQLite' and compiler == DONOR and record['check'] == 'error':
                        # Try descending optimization levels; retain every failed attempt.
                        for level in ('-O3', '-O2', '-O1', '-O0'):
                            fallback_flags = [f for f in flags if not re.fullmatch(r'-O(?:[0-3sgz]|fast)', f)] + [level]
                            if fallback_flags == flags or set(fallback_flags) == set(flags):
                                continue
                            fallback = stage_build(program, compiler, fallback_flags,
                                'optimization-fallback', flag_index, source, stage_dir, record['cause'])
                            fallback['requested_flags'] = flags
                            records.append(fallback)
                            if fallback['check'] == 'pass':
                                break
                            fallback['variant'] = 'failed-optimization-attempt'
    write_partition(stage_dir, 'builds.json', records)
    write_json(stage_dir / 'held-out-status.json', [dict(program=p, check=(
        'ready' if all(r['check'] == 'pass' for r in records if r['program'] == p) else 'fail'))
        for p in HELD_OUT if any(r['program'] == p for r in records)])
    write_json(stage_dir / 'settings.json', settings)
    # Runtime dependencies are staged per compiler, all input and runtime files
    # are transferred by card_run; the lead invokes this script explicitly.
    write_lead_script(stage_dir)
    (stage_dir / 'lead.sh').unlink(missing_ok=True)
    print('Staged lead script:', stage_dir / 'lead.ps1')
    print('Baseline estimate: 4-7 hours including staging; no native timing calibration yet.')
    print('Build failures:', sum(r['check'] != 'pass' for r in records), 'of', len(records))


def write_lead_script(stage_dir):
    project = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
    quote = lambda path: "'" + windows_path(path).replace("'", "''") + "'"
    (stage_dir / 'lead.ps1').write_text(
        "# Windows Python is required by card_run. Use this ticket until merged.\n" +
        "# Pilot: 468 launches across full/3100/5100, initially estimated 4-7 hours; NPB may extend this.\n" +
        "param([int]$Pairs = 3, [int]$TimeoutSeconds = 3600)\n" +
        '$corpusEntry = ' + quote(Path(__file__).resolve()) + '\n' +
        'if (!(Test-Path -LiteralPath $corpusEntry)) { $corpusEntry = ' + quote(project / 'tools/corpus.py') + ' }\n' +
        '& (Get-Command python.exe).Source $corpusEntry lead --stage ' + quote(stage_dir) + ' --pairs $Pairs --timeout $TimeoutSeconds\nexit $LASTEXITCODE\n')
    shutil.copyfile(SUPPORT / 'README.md', stage_dir / 'README.md')


def output_result(job, stdout, stderr, returncode):
    row = dict(job, check='error', time_seconds=None)
    try:
        meta = [json.loads(line[len('CORPUS_META '):]) for line in stdout.splitlines() if line.startswith('CORPUS_META ')]
        times = [float(line.split()[1]) for line in stdout.splitlines() if line.startswith('CORPUS_TIME ')]
        if len(meta) != 1 or meta[0]['threads'] != job['threads'] or len(times) != 1 or not math.isfinite(times[0]) or times[0] <= 0:
            raise ValueError('missing or mismatched native timing/affinity metadata')
        clocks = [json.loads(line[len('CORPUS_CLOCK '):]) for line in stdout.splitlines()
                  if line.startswith('CORPUS_CLOCK ')]
        if len(clocks) != 1:
            raise ValueError('missing launch-to-exit clock record')
        timing = clocks[0]
        if (timing.get('clock') != 'CLOCK_MONOTONIC_RAW' or timing.get('boundary') != 'launch-to-exit'
                or any(type(timing.get(k)) is not int for k in ('start_ns', 'end_ns', 'utc_start_ns'))
                or timing['end_ns'] <= timing['start_ns'] or timing['utc_start_ns'] <= 0
                or not math.isclose((timing['end_ns'] - timing['start_ns']) / 1e9,
                                    times[0], rel_tol=1e-9, abs_tol=1e-9)):
            raise ValueError('invalid launch-to-exit clock record')
        row.update(time_seconds=times[0], affinity=meta[0], timing=timing,
                   secondary_timing_output=[line for line in (stdout + '\n' + stderr).splitlines()
                       if re.search(r'Time in seconds|(?:time|Time|seconds|Seconds).*[:=]|Avg time|Min time|Max time', line)],
                   system_runtime=[line for line in stdout.splitlines() if line.startswith('CORPUS_RUNTIME ')])
        if returncode:
            raise ValueError('card_run exit %d' % returncode)
        text = stdout + '\n' + stderr
        program = job['program']
        if program.startswith('PB-'):
            checks = [json.loads(line[len('CORPUS_ARRAY '):]) for line in stdout.splitlines() if line.startswith('CORPUS_ARRAY ')]
            if not arrays_match(checks, checks):
                raise ValueError('missing or nonfinite complete PolyBench output')
            row['arrays'] = checks
        elif program.startswith('NPB-'):
            if not re.search(r'Verification\s*=\s*SUCCESSFUL', text, re.I) or re.search(r'UNSUCCESSFUL|VERIFICATION FAILED', text, re.I):
                raise ValueError('NPB verification failed or absent')
        elif program == 'STREAM':
            if 'Solution Validates:' not in text or 'Failed Validation' in text:
                raise ValueError('STREAM verification failed or absent')
        elif program == 'HPCG':
            row['hpcg_work'] = hpcg_work(text)
        elif 'CORPUS_CHECK pass' not in stdout:
            raise ValueError('correctness check failed or absent')
        if program in ('zlib', 'bzip2') and ('CORPUS_CROSS pass' not in stdout or 'CORPUS_CONTROL rejected' not in stdout):
            raise ValueError('missing cross-compiler decoding or corruption rejection')
        row['check'] = 'pass'
    except (ValueError, KeyError, TypeError) as exc:
        row.update(check='fail' if row['time_seconds'] is not None else 'error', cause=str(exc))
    return row


def hpcg_work(text):
    """Read HPCG 3.1's text report; derive sets from both reported totals.

    ReportResults.cpp emits totals = iterations per set * numberOfCgSets,
    rather than a separate set-count field. YAML is also transferred by the
    launcher; only the unambiguous text-report fields below are consumed.
    """
    if 'HPCG result is VALID' not in text or 'INVALID' in text or 'Result=FAILED' in text:
        raise ValueError('HPCG validity report failed or absent')
    for section in ('Spectral Convergence Tests', 'Iteration Count Information',
                    'Reproducibility Information'):
        if text.splitlines().count(section + '::Result=PASSED') != 1:
            raise ValueError('HPCG required test failed or absent: ' + section)
    if len(re.findall(r'^Departure from Symmetry .*::Result=PASSED$', text, re.M)) != 1:
        raise ValueError('HPCG symmetry test failed or absent')
    work = {}
    for key, label in [('reference_per_set', 'Reference CG iterations per set'),
                       ('optimized_per_set', 'Optimized CG iterations per set'),
                       ('reference_total', 'Total number of reference iterations'),
                       ('optimized_total', 'Total number of optimized iterations')]:
        values = re.findall(r'^Iteration Count Information::' + label + r'=(\d+)$', text, re.M)
        if len(values) != 1 or int(values[0]) <= 0:
            raise ValueError('HPCG missing or invalid iteration count: ' + label)
        work[key] = int(values[0])
    counts = []
    for kind in ('reference', 'optimized'):
        total, per_set = work[kind + '_total'], work[kind + '_per_set']
        if total % per_set:
            raise ValueError('HPCG inconsistent iteration totals')
        counts.append(total // per_set)
    if counts[0] != counts[1]:
        raise ValueError('HPCG inconsistent set counts')
    work['sets'] = counts[0]
    return work


def card_call(stage_dir, files, mode, density, stdout, stderr, profile='full', timeout=3600):
    # Called only by the explicit lead subcommand, never by stage or collect.
    threads = {'full': 240, '3100': 224, '5100': 236}[profile]
    # card_run requires a transport record; keep only its transient working file.
    transport_record = stdout.parent / 'card-result.json'
    command = [sys.executable, str(ROOT / 'tools/card_run'), '--benchmark', '--threads', str(threads),
               '--timeout', str(timeout),
               '--receipt', str(transport_record)]
    if profile != 'full':
        command += ['--profile', profile]
    for file in files:
        command += ['--file', str(file)]
    command += [str(stage_dir / 'launch'), density, mode]
    try:
        with stdout.open('w') as out, stderr.open('w') as err:
            return subprocess.run(command, stdout=out, stderr=err).returncode
    finally:
        transport_record.unlink(missing_ok=True)


def lead(args):
    if os.name != 'nt':
        raise RuntimeError('lead requires Windows Python for card_run and its Windows OpenSSH paths')
    stage_dir = args.stage.resolve()
    settings = json.loads((stage_dir / 'settings.json').read_text())
    if args.repetitions is not None:
        settings['repetitions'] = args.repetitions
    builds = read_partition(stage_dir, 'builds.json')
    capture = stage_dir / 'capture'
    capture.mkdir(exist_ok=True)
    out, err = capture / 'probe.stdout', capture / 'probe.stderr'
    rc = card_call(stage_dir, [], 'probe', 'probe', out, err)
    if rc:
        raise RuntimeError('card affinity probe failed; see ' + str(err))
    metadata = [json.loads(s[len('CORPUS_META '):]) for s in out.read_text().splitlines() if s.startswith('CORPUS_META ')]
    if len(metadata) != 1 or metadata[0]['granted_cpus'] != metadata[0]['cores'] * 4:
        raise RuntimeError('missing or incomplete card topology probe')
    plan = make_plan(**settings, core_count=metadata[0]['cores'])
    selected = []
    for job in plan:
        matches = [b for b in builds if b['program'] == job['program'] and
                   b['compiler'] == job['compiler'] and b['requested_flags'] == job['flags'] and
                   b['variant'] == job['variant']]
        if job['program'] == 'SQLite' and job['compiler'] == DONOR:
            fallback = [b for b in builds if b['program'] == 'SQLite' and b['compiler'] == DONOR and
                        b['requested_flags'] == job['flags'] and b['variant'] == 'optimization-fallback' and b['check'] == 'pass']
            matches = fallback or matches
        if len(matches) != 1:
            raise RuntimeError('missing or ambiguous staged build: ' + job['program'])
        build = matches[0]
        job.update(flags=build['flags'], variant=build['variant'], panel=build['panel'])
        if 'fallback_reason' in build:
            job['fallback_reason'] = build['fallback_reason']
        selected.append(build)
    write_partition(stage_dir, 'plan.json', plan)
    private = sealed_dir(stage_dir)
    (private / 'capture').mkdir(exist_ok=True)
    # Keep the two streams separate from their first byte, even on interruption.
    with (stage_dir / 'raw-results.jsonl').open('w') as public, (private / 'raw-results.jsonl').open('w') as sealed:
        for number, (job, build) in enumerate(zip(plan, selected)):
            job['timeout_seconds'] = args.timeout
            held = job['program'] in HELD_OUT
            folder = private / 'capture' if held else capture
            out, err = folder / ('%03d.stdout' % number), folder / ('%03d.stderr' % number)
            if build['check'] != 'pass':
                row = dict(job, check='error', time_seconds=None, cause='build: ' + build['cause'], log=build['log'])
            else:
                files = [windows_path(file) for file in build['files'] if not file.endswith('.json')]
                ready = True
                if job['program'] in ('zlib', 'bzip2'):
                    files.append(str(stage_dir / 'input.bin'))
                    peers = [b for b in builds if b['program'] == job['program'] and
                             b['compiler'] != job['compiler'] and b['check'] == 'pass']
                    ready = bool(peers)
                    if ready:
                        peer = folder / 'peer.tar'
                        def peer_mode(member):
                            member.mode = 0o755 if member.name == 'workload' else 0o644
                            return member
                        with tarfile.open(peer, 'w') as archive:
                            for file in peers[0]['files']:
                                if not file.endswith('.json'):
                                    archive.add(windows_path(file), arcname=Path(file).name, filter=peer_mode)
                        files.append(str(peer))
                elif job['program'] == 'SQLite':
                    files.append(str(stage_dir / 'input.sql'))
                elif job['program'] == 'HPCG':
                    files.append(str(stage_dir / 'hpcg.dat'))
                cores = {'full': metadata[0]['cores'], '3100': 56, '5100': 59}[job['profile']]
                density = 'serial' if job['threads'] == 1 else 'full' if job['threads'] == 4 * cores else 'two' if job['threads'] == 2 * cores else 'one'
                if ready:
                    rc = card_call(stage_dir, files, job['program'], density, out, err, job['profile'], args.timeout)
                    row = output_result(job, out.read_text(errors='replace'), err.read_text(errors='replace'), rc)
                    row.update(stdout=str(out), stderr=str(err))
                    row['runtime_prefix'] = next((windows_path(f) for f in build['files'] if f.endswith('runtime-prefix.json')), None)
                else:
                    row = dict(job, check='error', time_seconds=None, cause='other compiler decoder build unavailable')
            results = sealed if held else public
            results.write(json.dumps(row, allow_nan=False) + '\n')
            results.flush()
    collect(args)


def collect(args):
    stage_dir = args.stage.resolve()
    plan = read_partition(stage_dir, 'plan.json')
    rows = read_partition(stage_dir, 'raw-results.jsonl')
    # Migrate imported v1 files immediately; never trust a held_out label.
    write_partition(stage_dir, 'plan.json', plan)
    write_partition(stage_dir, 'raw-results.jsonl', rows)
    donors = defaultdict(list)
    def pair(row):
        return (row['program'], row['run'], row['threads'], row['input'],
                row.get('profile', 'full'), row.get('variant', 'serial'))
    for row in rows:
        if row['compiler'] == DONOR and row['program'].startswith('PB-'):
            donors[pair(row)].append(row)
        if row['compiler'] == DONOR and row['program'] == 'HPCG':
            donors[pair(row)].append(row)
    for row in rows:
        if row['program'] == 'HPCG' and row['check'] == 'pass':
            work = row.get('hpcg_work')
            if not work or work.get('sets') != 1:
                row.update(check='fail', cause='HPCG requires exactly one reported CG set')
            elif row.get('variant', 'serial') == 'serial' and row['compiler'] == KNC:
                paired = donors[pair(row)]
                if len(paired) != 1 or paired[0]['check'] != 'pass' or paired[0].get('hpcg_work') != work:
                    row.update(check='fail', cause='HPCG unequal work or missing reference')
        if row['program'].startswith('PB-') and row['check'] == 'pass':
            if not arrays_match(row.get('arrays'), row.get('arrays')):
                row.update(check='fail', cause='missing or invalid complete PolyBench output')
            elif row['compiler'] == KNC:
                paired = donors[pair(row)]
                if not paired or any(d['check'] != 'pass' or not arrays_match(d.get('arrays'), row['arrays']) for d in paired):
                    row.update(check='fail', cause='PolyBench elementwise mismatch or missing reference')
    write_partition(stage_dir, 'results.jsonl', rows)
    observed = defaultdict(list)
    for row in rows:
        observed[identity(row)].append(row)
    states = []
    for program in sorted({p['program'] for p in plan}):
        jobs = [p for p in plan if p['program'] == program]
        good = all(len(observed[identity(p)]) == 1 and
                   observed[identity(p)][0]['check'] == 'pass' for p in jobs)
        expected = {identity(p) for p in jobs}
        good = good and all(identity(r) in expected for r in rows if r['program'] == program)
        states.append(dict(program=program, check='pass' if good else 'fail'))
    # Scoring belongs to S11-14 / ADR-0015, not this harness.
    write_json(stage_dir / 'status.json', states)
    for old in ('summary.json', 'summary.md'):
        (stage_dir / old).unlink(missing_ok=True)
    for state in states:
        print('%s: %s' % (state['program'], state['check']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'lead', 'collect'))
    parser.add_argument('--stage', type=Path, default=SHARED / 'S11-18')
    parser.add_argument('--extra-flags', type=json.loads, default={})
    parser.add_argument('--pairs', '--repetitions', dest='repetitions', type=int,
                        help='paired launches: pilot default 3; ADR-0015 gate 6 (lead overrides staged count)')
    parser.add_argument('--timeout', type=int, default=3600, help='per-launch seconds, including serial NPB pilot')
    parser.add_argument('--only', nargs='+', choices=PROGRAMS,
                        help='stage only these programs, retaining previous build records and inputs')
    args = parser.parse_args()
    if args.repetitions is not None and args.repetitions < 3:
        parser.error('at least three repetitions')
    if args.timeout < 1:
        parser.error('timeout must be positive')
    globals()[args.action](args)


if __name__ == '__main__':
    main()
