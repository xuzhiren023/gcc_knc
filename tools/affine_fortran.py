"""S3-08 mixed C/Fortran acceptance rows; native execution is S3-10."""
import re
import sys


def compile_object(runner, mode='off', scan=False):
    if mode == 'off' and getattr(runner, 'fortran_object', None):
        return runner.fortran_object
    source = runner.fixture / 'affine_fortran.f90'
    asm = runner.out / ('affine-fortran-' + mode + '.s')
    obj = asm.with_suffix('.o')
    compiler = runner.cc.with_name('gfortran')
    report = runner.command(compiler, *runner.cc_flags, *runner.flags,
                            '-ffp-contract=' + mode, '-fopt-info-vec-all',
                            '-S', source, '-o', asm)
    asm.with_suffix('.vec').write_text(report)
    runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj)
    if scan:
        runner.result('t1 affine Fortran ' + mode + ' assembly --march=k1om', [])
        runner.command(sys.executable, runner.root / 'tools/knc_lint', asm, obj)
        runner.result('t1 affine Fortran ' + mode + ' knc_lint', [])
        runner.result('t1 affine Fortran ' + mode + ' vectorization',
                      scan_t1(runner, asm.read_text(), report, source.read_text(), mode))
    if mode == 'off':
        runner.fortran_object = obj
    return obj


def scan_t1(runner, assembly, report, source, mode):
    failures = []
    body = runner.function_body(assembly, 'affine_f32_fortran')
    if body is None:
        return ['missing affine_f32_fortran function boundary']
    body = '\n'.join(line.split('#', 1)[0] for line in body.splitlines())
    from check import loops
    patterns = [r'vfmadd\w*ps'] if mode == 'fast' else ['vmulps', 'vaddps']
    if not any(all(re.search(r'\b' + pattern + r'\b[^\n]*%zmm\d+\b', loop)
                       for pattern in patterns) for loop in loops(body)):
        failures.append('main loop lacks ' + ' and '.join(patterns) + ' on zmm')
    if mode == 'off' and re.search(r'\bv(?:fm|fnm)\w*(?:ps|pd)\b', body):
        failures.append('fused arithmetic with contraction off')
    line = next((i for i, text in enumerate(source.splitlines(), 1)
                 if re.match(r'\s*do\s+i\s*=', text, re.I)), None)
    if line is None or not re.search(r'(?:^|[/\\\s])affine_fortran\.f90:' + str(line) +
                                     r'(?::\d+)?:[^\n]*\bloop vectorized\b', report, re.I):
        failures.append('no -fopt-info-vec report for the Fortran loop')
    return failures


def t1(runner):
    for mode in ('off', 'fast'):
        compile_object(runner, mode, scan=True)


def check_link(runner, elf, trace):
    failures = []
    driver = runner.command(runner.tool('nm'), '-u', runner.out / 'driver.o')
    if not re.search(r'\bU\s+affine_f32_fortran\s*$', driver, re.M):
        failures.append('driver does not call affine_f32_fortran (KNC_WITH_FORTRAN missing)')
    symbols = runner.command(runner.tool('nm'), '--defined-only', elf)
    if not re.search(r'\bT\s+affine_f32_fortran\s*$', symbols, re.M):
        failures.append('linked executable lacks affine_f32_fortran')
    dynamic = runner.command(runner.tool('readelf'), '--dynamic', '--wide', elf)
    if 'libgfortran' in trace or 'libgfortran' in dynamic:
        failures.append('link uses libgfortran')
    obj = getattr(runner, 'fortran_object', None)
    if obj:
        undefined = runner.command(runner.tool('nm'), '-u', obj)
        if re.search(r'\b_gfortran_\w+', undefined):
            failures.append('Fortran object calls libgfortran')
    runner.result('t2 affine Fortran driver and runtime-free link', failures)


def t2(runner):
    elf, trace = runner.t2_affine_link()
    runner.t2_abi(elf, trace)
    check_link(runner, elf, trace)
