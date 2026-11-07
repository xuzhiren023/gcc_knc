#!/usr/bin/env python3
"""S7-07 red tests and discovery payload; invoke through tools/run.py.

Host tests execute runtime C with real x87 and instrumented MXCSR storage.
The fallback fpu-387 has CPUID SSE disabled, reproducing KNC's missing path.
Candidate flag positions require lead-run probe evidence, not this model.
"""
import argparse
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
GCC = SHARED / 'gcc'
OUT = SHARED / 'S7-07'
SRC = ROOT / 'tests/t2/s7-07'


def run(args):
    return subprocess.run(list(map(str, args)), check=True, timeout=120)


def function(text, name):
    """Extract an existing C definition, retaining its actual control flow."""
    start = re.search(r'\n' + name + r'\s*\([^;]*?\)\s*\{', text)
    if not start:
        raise RuntimeError('missing runtime function: ' + name)
    opening = text.index('{', start.start())
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start.start():end]


def host():
    config = GCC / 'libgfortran/configure.host'
    failed = False
    for libc in ('yes', 'no'):
        env = os.environ.copy()
        env.update(host='k1om-mpss-linux', host_cpu='k1om', host_os='linux',
                   have_feenableexcept=libc, have_soft_float='no',
                   have_fp_enable='no', have_fp_trap='no', have_fpsetmask='no')
        selected = subprocess.check_output(
            ['bash', '-c', '. "$1"; printf "%s" "$fpu_host"', 'sh', str(config)],
            env=env, text=True)
        ok = selected == 'fpu-knc'
        failed |= not ok
        print(('PASS' if ok else 'FAIL') + ' explicit k1om selection: libc=' + libc
              + ' selected=' + selected, flush=True)
    backend = GCC / 'libgfortran/config/fpu-knc.h'
    if not backend.exists():
        backend = backend.with_name('fpu-387.h')
        print('Baseline: fpu-387 with CPUID SSE=0; KNC backend missing.', flush=True)
    source = backend.read_text()
    # Replace only single-memory-operand MXCSR assembly, not state logic.
    # Refuse unrecognized access rather than execute it on the host.
    asm = re.compile(r'__asm__\s*(?:__volatile__\s*)?\(\s*"(?:%v)?(stmxcsr|ldmxcsr)'
                     r'\\t%0"\s*:\s*(?:"=m"\s*|:\s*"m"\s*)'
                     r'\(([^()]*)\)\s*\);')

    def replace(m):
        operand = m[2].strip()
        return (operand + ' = model_mxcsr;' if m[1] == 'stmxcsr'
                else 'model_write (' + operand + ');')

    source, count = asm.subn(replace, source)
    if not count or re.search(r'"[^"\n]*(?:stmxcsr|ldmxcsr)', source):
        raise RuntimeError('MXCSR instrumentation requires review for this backend')
    (OUT / 'backend.h').write_text(source)
    (OUT / 'cpuid.h').write_text(
        '#define bit_SSE (1u << 25)\n'
        'static int __get_cpuid(unsigned int n, unsigned int *a, unsigned int *b, '
        'unsigned int *c, unsigned int *d) { *a=*b=*c=*d=0; return 1; }\n')
    constants = (GCC / 'gcc/fortran/libgfortran.h').read_text()
    (OUT / 'constants.h').write_text('\n'.join(
        line for line in constants.splitlines() if line.startswith('#define GFC_FPE_')) + '\n')
    helper = (GCC / 'libgfortran/ieee/ieee_helper.c').read_text()
    read = (GCC / 'libgfortran/io/read.c').read_text()
    (OUT / 'callers.h').write_text(
        'void' + function(helper, 'ieee_procedure_entry') + '\nvoid'
        + function(helper, 'ieee_procedure_exit') + '\nstatic int'
        + function(read, 'convert_real') + '\n')
    binary = OUT / 'state-host.exe'
    run([TC / 'cygwin/bin/gcc', '-O0', '-std=gnu11', '-mfpmath=387',
         '-I' + str(OUT), SRC / 'state-host.c', '-o', binary])
    result = subprocess.run([str(binary)], timeout=30)
    return int(failed or result.returncode != 0)


def probes():
    build = SHARED / 'gcc-build/gcc'
    binary = OUT / 'fp-probe.mic'
    run([build / 'xgcc', '-B' + str(build) + '/', '-march=knc',
         '--sysroot=' + str(TC / 'sysroot'), '-O0', '-static-libgcc',
         SRC / 'fp-probe.c', '-o', binary])
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    violations = list(lint(binary, TC, os.environ.copy()))
    for row in violations:
        print(row)
    if violations:
        return 1
    print('PASS build/lint: ' + str(binary) + '; native NOT RUN', flush=True)
    print('Lead invocation: fp-probe.mic (fork-isolated observations; no arguments).')
    print('No signal with x87 unmasked does not prove absence of another vector trap mechanism.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('host', 'probes'))
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, args.mode])
    OUT.mkdir(exist_ok=True)
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    return host() if args.mode == 'host' else probes()


if __name__ == '__main__':
    sys.exit(main())
