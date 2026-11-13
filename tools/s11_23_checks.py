"""Run the S11-23 GCC tests with the T1 sysroot and IMCI lint checks."""
import re
import sys


def check_source(runner, relative, fortran=False):
    source = runner.gcc_build.parent / 'gcc/gcc/testsuite' / relative
    asm = runner.out / (source.stem + '.s')
    obj = asm.with_suffix('.o')
    compiler = runner.cc.with_name('gfortran') if fortran else runner.cc
    options = ['-O2', '-march=knc']
    if fortran:
        options += ['-J' + str(runner.out)]
    else:
        options += ['-fopt-info-vec']
    label = 't1 ' + source.name
    try:
        report = runner.command(compiler, *runner.cc_flags, *options,
                                '--sysroot=' + str(runner.sysroot),
                                '-S', source, '-o', asm)
        if report:
            runner.say(report.rstrip())
        if not fortran and re.search(r'%[xy]mm\d+', asm.read_text()):
            runner.result(label, ['SSE or AVX register in scalar SLP output'])
            return
        runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj)
        runner.command(sys.executable, runner.root / 'tools/knc_lint', asm, obj)
        runner.result(label + ' compile, assembly and knc_lint', [])
    except RuntimeError as error:
        runner.result(label, [str(error)])


def t1(runner):
    check_source(runner, 'gfortran.dg/knc-rrtm-reload.f90', fortran=True)
    check_source(runner, 'gcc.target/i386/knc-slp-width.c')
