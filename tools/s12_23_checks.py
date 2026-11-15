#!/usr/bin/env python3
"""S12-23 red gate and card staging; invoke through tools/run.py.

Only gcc2 is used. No compiler build or card execution. Assembly inspection
checks the CD28 workaround requirement, not a simulation of the silicon bug.
"""
import importlib.util
import os
from pathlib import Path
import re
import runpy
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
GCC = SHARED / 'gcc-2'
BUILD = SHARED / 'gcc-build-2/gcc'
OUT = SHARED / 'S12-23'


def run(args):
    subprocess.run(list(map(str, args)), check=True, timeout=120)


def compiler():
    return [BUILD / 'xgcc', '-B' + str(BUILD) + '/', '-march=knc',
            '--sysroot=' + str(TC / 'sysroot'), '-O0', '-std=gnu11',
            '-I' + str(OUT), '-I' + str(GCC / 'libgfortran/config')]


def check(ok, message):
    print(('PASS ' if ok else 'FAIL ') + message, flush=True)
    return int(not ok)


def assembly_contract():
    source = OUT / 'runtime.c'
    source.write_text('#include <stddef.h>\n#include "constants.h"\n'
                      'static struct { int fpe; } options;\n'
                      'extern void estr_write(const char *);\n'
                      '#include "fpu-knc.h"\n')
    asm = OUT / 'runtime.s'
    run(compiler() + ['-S', source, '-o', asm])
    text = asm.read_text()
    bodies = dict(re.findall(r'^([\w.]+):\n(.*?)^\s*\.size\s+\1\s*,',
                             text, re.M | re.S))

    def reachable(name, seen=None):
        seen = set() if seen is None else seen
        if name in seen:
            return ''
        seen.add(name)
        body = bodies[name]
        return body + ''.join(reachable(callee, seen) for callee in
                              re.findall(r'\bcall\s+([\w.]+)', body)
                              if callee in bodies)

    failures = 0
    for name in ('set_fpu_except_flags', 'set_fpu_state'):
        body = reachable(name)
        failures += check(bool(re.search(r'\bfnsave\b', body)
                               and re.search(r'\bfrstor\b', body))
                          and not re.search(r'\bfn?clex\b', body),
                          name + ': reachable FNSAVE/FRSTOR recovery for CD28')
    return failures


def probe_contract():
    text = (ROOT / 'tests/t2/s7-07/fp-probe.c').read_text()
    case = re.search(r'\{"underflow",\s*(0x[0-9a-fA-F]+),\s*'
                     r'(0x[0-9a-fA-F]+),\s*16,\s*1\}', text)
    if not case:
        raise RuntimeError('review underflow case parser after probe change')
    x, y = [struct.unpack('<f', struct.pack('<I', int(v, 16)))[0]
            for v in case.groups()]
    rounded = struct.unpack('<I', struct.pack('<f', x * y))[0]
    return check(0 < rounded < 0x00800000,
                 'old underflow probe distinguishes gradual from FZ: '
                 'nearest binary32 result=%08x' % rounded)


def main():
    os.environ['PATH'] = os.pathsep.join(str(TC / p) for p in
                                        ('cross/bin', 'cygwin/bin')) + os.pathsep + os.environ['PATH']
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script])
    OUT.mkdir(exist_ok=True)
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    spec = importlib.util.spec_from_file_location('s7_07', ROOT / 'tools/s7_07_checks.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    old.GCC, old.OUT = GCC, OUT
    old.prepare_callers()
    binary = OUT / 'fp-env.mic'
    run(compiler() + ['-static-libgcc', ROOT / 'tests/t2/s12-23/fp-env.c', '-o', binary])
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    violations = list(lint(binary, TC, os.environ.copy()))
    for row in violations:
        print(row)
    if violations:
        return 1
    print('PASS build/lint: ' + str(binary) + '; native NOT RUN', flush=True)
    print('Lead: run fp-env.mic tiny, fp-env.mic clear, fp-env.mic restore separately; '
          'each is bounded under one minute, recovery is isolated crash diagnosis.', flush=True)
    failures = probe_contract() + assembly_contract()
    failures += old.host()
    print('S12-23 red gate: %d failed checks/groups; no native result claimed' % failures)
    return int(failures != 0)


if __name__ == '__main__':
    sys.exit(main())
