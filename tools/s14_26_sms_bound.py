"""S14-26: compile unmodified public corpus hot regions for twin inspection."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
OUT = SHARED / 'S14-26'
SRC = SHARED / 'corpus-build/sources'
CC = SHARED / 'gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc'
FC = SHARED / 'gcc-knc-16.2.0/bin/k1om-mpss-linux-gfortran'
OBJDUMP = SHARED / 'toolchain/cross/bin/k1om-mpss-linux-objdump'
os.environ['PATH'] = str(SHARED / 'toolchain/cross/bin') + os.pathsep + str(SHARED / 'toolchain/cygwin/bin') + os.pathsep + os.environ['PATH']


def run(cmd, cwd, output=None):
    print('COMMAND', ' '.join(map(str, cmd)), flush=True)
    if output:
        with output.open('w') as f:
            subprocess.run(list(map(str, cmd)), cwd=cwd, stdout=f, check=True)
    else:
        subprocess.run(list(map(str, cmd)), cwd=cwd, check=True)


def main():
    OUT.mkdir(exist_ok=True)
    run([CC, '--version'], OUT)
    for name, dims in [('gemm', {'NI':512,'NJ':512,'NK':512}),
                       ('jacobi-2d', {'N':512,'TSTEPS':100}),
                       ('heat-3d', {'N':64,'TSTEPS':40})]:
        d = OUT / ('PB-' + name)
        d.mkdir(exist_ok=True)
        pb = SRC / 'polybench-c-4.2.1-beta'
        source = next(pb.rglob(name + '.c'))
        run([CC, '-O2', '-march=knc', '-I' + str(pb / 'utilities'),
             '-DPOLYBENCH_DUMP_ARRAYS', '-DDATA_TYPE_IS_DOUBLE',
             *['-D%s=%s' % item for item in dims.items()],
             '-include', ROOT / 'tools/corpus/polybench_capture.h',
             '-c', source, '-o', d / 'benchmark.o'], d)
        run([OBJDUMP, '-dr', d / 'benchmark.o'], d, d / 'binary.dis')
    for name in ['MG', 'CG']:
        d = OUT / ('NPB-' + name)
        d.mkdir(exist_ok=True)
        npb = SRC / 'NPB3.4.2/NPB3.4-OMP'
        params = SHARED / ('S13-01/build/gcc-knc/0/serial/NPB-' + name)
        run([FC, '-O2', '-march=knc', '-I' + str(params),
             '-I' + str(npb / 'common'), '-c',
             npb / name / (name.lower() + '_data.f90'),
             npb / name / (name.lower() + '.f90')], d)
        run([OBJDUMP, '-dr', d / (name.lower() + '.o')], d, d / 'binary.dis')
    d = OUT / 'zlib'
    d.mkdir(exist_ok=True)
    run([CC, '-O2', '-march=knc', '-I' + str(SRC / 'zlib-1.3.1'),
         '-c', SRC / 'zlib-1.3.1/deflate.c', '-o', d / 'deflate.o'], d)
    run([OBJDUMP, '-dr', d / 'deflate.o'], d, d / 'binary.dis')


if __name__ == '__main__':
    main()
