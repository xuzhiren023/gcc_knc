"""S3-08 mixed C/Fortran acceptance rows; native execution is S3-10."""
import re


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
    runner.result('t2 affine Fortran driver and runtime-free link', failures)


def t2(runner):
    elf, trace = runner.t2_affine_link()
    runner.t2_abi(elf, trace)
    check_link(runner, elf, trace)
