#!/usr/bin/env python3
"""Host-only phase-one S12-07 assembly audit and paired diagnostic staging."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

import corpus

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
OUT = SHARED / 'S12-07'
TC = SHARED / 'toolchain'
SOURCE = SHARED / 'corpus-build/sources'


def run(*argv, cwd=OUT):
    print('+', ' '.join(map(str, argv)), flush=True)
    subprocess.run(list(map(str, argv)), cwd=cwd, check=True)


def cc(language, donor=False):
    return [corpus.compiler_path(corpus.DONOR if donor else corpus.KNC, language)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver-only', action='store_true',
                        help='relink the driver with existing, unchanged kernel objects')
    args = parser.parse_args()
    if sys.platform != 'cygwin':
        raise RuntimeError('use shared Cygwin python3')
    OUT.mkdir(exist_ok=True)
    os.environ['PATH'] = ':'.join([str(TC/'cross/bin'), str(TC/'cygwin/bin'), os.environ['PATH']])
    objects = []
    variants = [('donor', True, []), ('knc', False, []),
                ('nosched', False, ['-fno-schedule-insns2']),
                ('nopf', False, ['-fno-prefetch-loop-arrays'])]
    for variant, donor, extra in variants:
        directory = OUT / variant
        if args.driver_only:
            for language in ['gcc', 'gfortran']:
                obj = directory / (language + '.o')
                if not obj.is_file():
                    raise FileNotFoundError(obj)
                objects.append(obj)
            continue
        directory.mkdir(exist_ok=True)
        flags = ['-O2'] + ([] if donor else ['-march=knc']) + extra
        run(*cc('gcc', donor), '--version')
        for language, source, define in [
            ('gcc', 's12_07_sparse.c', '-DPREFIX=' + variant + '_'),
            ('gfortran', 's12_07_sparse.F90', '-DSYMBOL="' + variant + '_cg"')]:
            asm = directory / (language + '.s')
            # The donor rejects filenames on -fopt-info. Use its ordinary dump
            # naming, with all output contained in the fixed variant directory.
            run(*cc(language, donor), *flags, define, '-fdump-tree-vect-details',
                '-fdump-rtl-sched2',
                '-S', ROOT/'tools'/source, '-o', asm, cwd=directory)
            obj = asm.with_suffix('.o')
            run(TC/'cross/bin/k1om-mpss-linux-as', '--march=k1om', asm, '-o', obj)
            objects.append(obj)
        if donor or variant == 'knc':
            npb = SOURCE / 'NPB3.4.2/NPB3.4-OMP'
            params = SHARED/'corpus-build/v2/gcc-knc/0/serial/NPB-CG'
            includes = ['-I'+str(directory), '-I'+str(params), '-I'+str(npb/'common'), '-J'+str(directory)]
            for source in [npb/'common/timers.f90', npb/'CG/cg_data.f90', npb/'CG/cg.f90']:
                run(*cc('gfortran', donor), *flags, *includes,
                    '-fdump-tree-vect-details',
                    '-S', source, '-o', directory/(source.stem+'.s'), cwd=directory)
            hpcg = SOURCE / 'hpcg-3.1/src'
            for name in ['ComputeSPMV_ref', 'ComputeSYMGS_ref']:
                run(*cc('g++', donor), *flags, '-DHPCG_NO_MPI', '-DHPCG_NO_OPENMP',
                    '-I'+str(hpcg), '-fdump-tree-vect-details',
                    '-S', hpcg/(name+'.cpp'), '-o', directory/(name+'.s'), cwd=directory)
    run(*cc('gcc', True), '-O2', '-DDRIVER', ROOT/'tools/s12_07_sparse.c', *objects,
        *corpus.link_paths(), '-lrt', '-o', OUT/'sparse-paired')
    run(sys.executable, ROOT/'tools/knc_lint', OUT/'sparse-paired')
    print('STAGED:', OUT/'sparse-paired', 'single-core timing; lead card_run --threads 1 --timeout 200')
    print('No card execution. No GCC build. Native outputs and timing remain pending.')


if __name__ == '__main__':
    main()
