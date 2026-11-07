#!/usr/bin/env python3
"""S7-04 driver link regression; run through tools/run.py, never on the card.

Keep the static-only control as well as explicit static override: upstream
gcc.cc:init_gcc_specs gives static-libgcc priority over shared-libgcc. The
KNC REAL_LIBGCC_SPEC guard currently rejects that supported combination.
No runtime is installed, and a donor DSO cannot satisfy these probes.
This is the red driver gate, not the final shared-runtime ABI/import audit.
"""
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build'
RUNTIME = BUILD / 'k1om-mpss-linux/libgcc'
OUT = SHARED / 'S7-04'


def run(command):
    result = subprocess.run(list(map(str, command)), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=120)
    return result.returncode, result.stdout


def main():
    OUT.mkdir(exist_ok=True)
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    cc = [BUILD / 'gcc/xgcc', '-B' + str(BUILD / 'gcc') + '/',
          '-B' + str(RUNTIME) + '/']
    source = ROOT / 'tests/t2/knc-libgcc-link.c'
    cases = (
        ('shared-exe', ['-shared-libgcc'], False, True),
        ('shared-dso', ['-shared', '-shared-libgcc'], True, True),
        ('default-exe', [], False, True),
        ('default-dso', ['-shared'], True, True),
        ('static-exe', ['-static-libgcc'], False, False),
        ('static-override', ['-shared-libgcc', '-static-libgcc'], False, False),
    )
    failed = 0
    for name, flags, dso, dynamic in cases:
        target = OUT / (name + ('.so' if dso else '.mic'))
        target.unlink(missing_ok=True)
        command = [*cc, '-O2', '-fno-builtin', '-fPIC',
                   *(['-DPROBE_DSO'] if dso else []), *flags,
                   '-Wl,-z,defs,--trace', source, '-o', target]
        code, output = run(command)
        errors = []
        log = shlex.join(map(str, command)) + '\n' + output
        if code:
            errors.append('link exited ' + str(code))
        else:
            readelf = TC / 'cross/bin/k1om-mpss-linux-readelf'
            code, elf = run([readelf, '-W', '-h', '-d', '-s', target])
            log += '\n' + elf
            if code:
                errors.append('readelf failed')
            else:
                needed = re.findall(r'\(NEEDED\).*\[(.*?)\]', elf)
                if ('libgcc_s.so.1' in needed) != dynamic:
                    errors.append('wrong runtime selection: NEEDED=' + repr(needed))
                if not re.search(r'Machine:.*(?:K1OM|181|0xb5)', elf, re.I):
                    errors.append('not ELF K1OM')
                if dynamic:
                    if not re.search(r'\bUND\s+_Unwind_Backtrace@GCC_3\.3\b', elf):
                        errors.append('unwinder is not imported from versioned shared libgcc')
                    # The trace must name the fork build, not the sysroot donor.
                    if str(RUNTIME / 'libgcc_s.so') not in output:
                        errors.append('link did not select the built fork libgcc_s.so')
                elif not re.search(r'\b(?:GLOBAL|LOCAL)\s+\w+\s+\d+\s+_Unwind_Backtrace\s*$', elf, re.M):
                    errors.append('static unwinder definition missing')
            for crt in (('crtbeginS.o', 'crtendS.o') if dso else ('crtbegin.o', 'crtend.o')):
                if not any(str(directory / crt) in output for directory in (RUNTIME, BUILD / 'gcc')):
                    errors.append('fork CRT missing from trace: ' + crt)
            code, lint = run([sys.executable, ROOT / 'tools/knc_lint', target])
            log += '\n' + lint
            if code:
                errors.append('KNC lint failed')
        path = OUT / (name + '.log')
        path.write_text(log)
        print(('FAIL ' if errors else 'PASS ') + name + ': ' +
              ('; '.join(errors) if errors else 'runtime selection, CRTs and lint') +
              '; log=' + str(path), flush=True)
        if code and not target.exists():
            print(output[-1200:], flush=True)
        failed += bool(errors)
    print('S7-04 driver probes: %d/%d failed; no target code executed' % (failed, len(cases)))
    return int(bool(failed))


if __name__ == '__main__':
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', __file__], env=env, text=True).strip()
        sys.exit(subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env))
    sys.exit(main())
