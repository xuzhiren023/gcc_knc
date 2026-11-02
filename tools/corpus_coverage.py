"""S0-07 compile-only proxy. Run with the shared Cygwin Python via tools/run.py.

Inputs are the lead's extracted archives; no downloads or benchmark execution.
Outputs overwrite one directory outside git. No fast-math or target code runs.
"""
import argparse
import json
from pathlib import Path
import subprocess

FLAGS = ['-O3', '-march=skylake-avx512', '-mprefer-vector-width=512',
         '-fopt-info-vec-all', '-fdump-tree-vect-details', '-fdump-tree-cfg-lineno']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    ap.add_argument('--only', default='all')
    args = ap.parse_args()
    root = args.root.resolve()
    out = root / 'coverage'
    out.mkdir(exist_ok=True)
    jobs = []
    jobs.append(('STREAM', [root / 'stream.c'], ['-fopenmp']))
    pb = root / 'polybench-c-4.2.1-beta'
    for name in ['gemm', 'atax', 'cholesky', 'ludcmp', 'jacobi-2d', 'heat-3d', 'adi', 'durbin']:
        src = next(pb.rglob(name + '.c'))
        jobs.append(('PB-' + name, [src], ['-I' + str(pb / 'utilities'), '-DSMALL_DATASET']))
    npb = root / 'NPB3.4.2/NPB3.4-OMP'
    if args.only == 'all':
        # Only this configuration helper is executed; it is not a benchmark.
        (npb / 'config/make.def').write_text((npb / 'config/NAS.samples/make.def_gcc').read_text())
        subprocess.run(['gcc', str(npb / 'sys/setparams.c'), '-o', str(out / 'setparams')], check=True)
        for name in ['CG', 'EP', 'MG', 'IS', 'FT']:
            d = npb / name
            subprocess.run([str(out / 'setparams'), name.lower(), 'S'], cwd=d, check=True)
            sources = sorted(d.glob('*.c' if name == 'IS' else '*.f90'),
                             key=lambda p: ('_data' not in p.stem, p.name))
            jobs.append(('NPB-' + name, sources, ['-fopenmp', '-I' + str(npb / 'common')]))
    hpcg = root / 'hpcg-3.1/src'
    jobs.append(('HPCG', sorted(hpcg.glob('*.cpp')), ['-fopenmp', '-DHPCG_NO_MPI', '-I' + str(hpcg)]))
    zlib = root / 'zlib-1.3.1'
    jobs.append(('zlib', sorted(zlib.glob('*.c')), []))
    jobs.append(('SQLite', [root / 'sqlite-amalgamation-3460100/sqlite3.c'], []))
    bz = root / 'bzip2-1.0.8'
    jobs.append(('bzip2', [bz / (s + '.c') for s in
                          ['blocksort', 'huffman', 'crctable', 'randtable', 'compress', 'decompress', 'bzlib']], []))
    results = []
    for name, sources, extra in jobs:
        if args.only != 'all' and name != args.only:
            continue
        if args.only == 'all' and name == 'STREAM':
            continue  # already measured in the initial diagnostic-format run
        d = out / name
        d.mkdir(exist_ok=True)
        failures = []
        for src in sources:
            compiler = 'gfortran' if src.suffix == '.f90' else 'g++' if src.suffix == '.cpp' else 'gcc'
            command = [compiler] + FLAGS + extra + ['-c', str(src), '-o', str(d / (src.stem + '.o'))]
            with (d / (src.stem + '.log')).open('w') as log:
                log.write('COMMAND ' + ' '.join(command) + '\n')
                log.flush()
                rc = subprocess.run(command, cwd=d, stdout=log, stderr=subprocess.STDOUT).returncode
            if rc:
                failures.append(src.name)
        results.append(dict(name=name, sources=[str(p.relative_to(root)) for p in sources], failures=failures))
        print(name, len(sources), 'translation units; failures:', ','.join(failures) or 'none', flush=True)
    (out / ('jobs-' + args.only + '.json')).write_text(json.dumps(results, indent=2))
    print(subprocess.check_output(['gcc', '--version'], text=True).splitlines()[0])


if __name__ == '__main__':
    main()
