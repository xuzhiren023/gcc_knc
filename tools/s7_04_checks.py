#!/usr/bin/env python3
"""S7-04 driver link regression; run through tools/run.py, never on the card.

Keep the static-only control as well as explicit static override: upstream
gcc.cc:init_gcc_specs gives static-libgcc priority over shared-libgcc. The
KNC REAL_LIBGCC_SPEC guard currently rejects that supported combination.
No runtime is installed, and a donor DSO cannot satisfy these probes.
The build-tree DSO must satisfy the donor ABI and import contract too.
"""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

from s7_03_checks import fixture, inspect, mismatches, symbols

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build'
RUNTIME = BUILD / 'k1om-mpss-linux/libgcc'
OUT = SHARED / 'S7-04'
SYSROOT = TC / 'sysroot'
DONOR = SYSROOT / 'lib64/libgcc_s.so.1'


def sonames(output):
    return re.findall(r'\(SONAME\).*\[(.*?)\]', output)


def prefix_errors(prefix):
    resolved = prefix.resolve()
    # resolve() also catches an existing symlink into a protected prefix.
    return ['install prefix is inside ' + str(parent)
            for parent in (SYSROOT, TC)
            if resolved == parent.resolve() or parent.resolve() in resolved.parents]


def donor_errors(output, expected):
    actual = symbols(output)
    errors = mismatches(expected, actual)
    if set(actual) != set(expected):
        errors.append('donor exported symbol set changed')
    if sonames(output) != ['libgcc_s.so.1']:
        errors.append('donor SONAME changed')
    return errors


def provider_names(output):
    result = set()
    for name in symbols(output):
        result.add(name.replace('@@', '@'))
        if '@@' in name or '@' not in name:
            result.add(name.split('@')[0])
    return result


def audit_errors(output, expected, providers):
    errors = mismatches(expected, symbols(output))
    if not re.search(r'Machine:.*(?:K1OM|181|0xb5)', output, re.I):
        errors.append('not ELF K1OM')
    if sonames(output) != ['libgcc_s.so.1']:
        errors.append('wrong shared libgcc SONAME')
    if not re.search(r'^\s*GNU_EH_FRAME\s', output, re.M):
        errors.append('missing PT_GNU_EH_FRAME')
    if re.search(r'\b(?:DT_)?TEXTREL\b', output):
        errors.append('TEXTREL present')
    # Includes version needs as well as versioned undefined dynsym entries.
    for version in set(re.findall(r'\bGLIBC_(\d+(?:\.\d+)+)\b', output)):
        parts = tuple(map(int, version.split('.')))
        if parts + (0,) * max(0, 3 - len(parts)) > (2, 21, 0):
            errors.append('GLIBC import newer than 2.21: ' + version)
    for line in output.splitlines():
        fields = line.split()
        if (len(fields) < 8 or not fields[0].rstrip(':').isdigit()
                or fields[6] != 'UND'):
            continue
        name = fields[7]
        if name.split('@')[0] == '_dl_find_object':
            errors.append('_dl_find_object import')
        if fields[4] == 'GLOBAL' and name not in providers:
            errors.append('undefined symbol not supplied by libc/ld: ' + name)
    needed = re.findall(r'\(NEEDED\).*\[(.*?)\]', output)
    errors.extend('unexpected dependency ' + name for name in needed
                  if name not in ('libc.so.6', 'ld-linux-k1om.so.2'))
    return errors


def check_detector():
    row = ' 1: 0000000000001000 8 FUNC GLOBAL DEFAULT 12 helper@@GCC_3.0\n'
    good = ('Machine: Intel K1OM\n'
            ' 0x000000000000000e (SONAME) Library soname: [libgcc_s.so.1]\n'
            ' GNU_EH_FRAME 0x000100 0x000100 0x000100 0x000010 0x000010 R 0x4\n'
            ' 2: 0000000000000000 0 FUNC GLOBAL DEFAULT UND malloc@GLIBC_2.21 (2)\n'
            ' 0x0010: Name: GLIBC_2.21 Flags: none Version: 2\n' + row)
    expected = {'helper@@GCC_3.0': ('FUNC', 0)}
    providers = {'malloc@GLIBC_2.21'}
    assert not audit_errors(good, expected, providers)
    for version in ('2.22', '2.21.1', '3.0'):
        changed = good.replace('GLIBC_2.21', 'GLIBC_' + version)
        assert any('newer than' in e for e in audit_errors(changed, expected, providers))
    for bind in ('GLOBAL', 'WEAK'):
        changed = good + (' 3: 0000000000000000 0 FUNC %s DEFAULT UND '
                          '_dl_find_object@GLIBC_2.35 (3)\n' % bind)
        assert '_dl_find_object import' in audit_errors(changed, expected, providers)
    for name in ('__gmon_start__', 'pthread_once'):
        changed = good + ' 3: 0000000000000000 0 FUNC WEAK DEFAULT UND %s\n' % name
        assert not audit_errors(changed, expected, providers)
    changed = good + ' 3: 0000000000000000 0 FUNC GLOBAL DEFAULT UND __divti3\n'
    assert 'undefined symbol not supplied by libc/ld: __divti3' in audit_errors(changed, expected, providers)
    changed = good + ' 0x0000000000000001 (NEEDED) Shared library: [libpthread.so.0]\n'
    assert 'unexpected dependency libpthread.so.0' in audit_errors(changed, expected, providers)
    for textrel in (' 0x0000000000000016 (TEXTREL) 0x0\n',
                    ' 0x000000000000001e (FLAGS) TEXTREL\n', 'DT_TEXTREL\n'):
        assert 'TEXTREL present' in audit_errors(good + textrel, expected, providers)
    for changed in (good.replace(row, ''), good.replace('helper@@GCC_3.0', 'helper@GCC_3.0')):
        assert any('missing or wrongly versioned' in e
                   for e in audit_errors(changed, expected, providers))
    extra = ' 4: 0000000000001000 8 FUNC GLOBAL DEFAULT 12 extra@@GCC_14.0.0\n'
    assert not audit_errors(good + extra, expected, providers)
    assert not donor_errors(good, expected)
    assert donor_errors(good.replace('libgcc_s.so.1', 'wrong.so'), expected)
    assert donor_errors(good.replace(row, ''), expected)
    assert donor_errors(good + extra, expected)
    assert not prefix_errors(OUT / 'install')
    for prefix in (SYSROOT, SYSROOT / 'lib64', TC, TC / 'private'):
        assert prefix_errors(prefix)
    print('PASS detectors: GLIBC version, _dl_find_object at any bind, weak imports, '
          'unresolved global helpers, extra NEEDED, TEXTREL, donor superset, '
          'private prefix and donor SONAME/export integrity', flush=True)


def audit_dso(expected):
    target = RUNTIME / 'libgcc_s.so.1'
    if not target.is_file():
        print('FAIL DSO audit: build-tree libgcc_s.so.1 is not built: ' + str(target), flush=True)
        return 1
    elf = inspect('readelf', '-W', '-h', '-l', '-d', '--dyn-syms', '-V', target)
    providers = set()
    for name in ('libc.so.6', 'ld-linux-k1om.so.2'):
        providers.update(provider_names(inspect('readelf', '-W', '--dyn-syms', SYSROOT / 'lib64' / name)))
    errors = audit_errors(elf, expected, providers)
    code, lint = run([sys.executable, ROOT / 'tools/knc_lint', target])
    if code:
        errors.append('KNC lint failed')
    log = OUT / 'dso-audit.log'
    log.write_text(elf + '\n' + lint)
    print(('FAIL ' if errors else 'PASS ') + 'DSO audit: ' +
          ('; '.join(errors) if errors else 'ELF, ABI, imports and lint') + '; log=' + str(log), flush=True)
    return int(bool(errors))


def run(command):
    result = subprocess.run(list(map(str, command)), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=120)
    return result.returncode, result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-prefix', type=Path, default=OUT / 'install',
                        help='private validation destination; this red gate does not install')
    args = parser.parse_args()
    before = DONOR.stat()
    donor_stamp = (before.st_size, before.st_mtime_ns)
    expected = fixture()
    check_detector()
    errors = prefix_errors(args.install_prefix)
    errors.extend(donor_errors(inspect('readelf', '-W', '-d', '--dyn-syms', DONOR), expected))
    if errors:
        print('FAIL preflight: ' + '; '.join(errors), flush=True)
        return 1
    print('PASS private install prefix: ' + str(args.install_prefix.resolve()) + '; no install performed', flush=True)
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
    failed = audit_dso(expected)
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
    after = DONOR.stat()
    errors = donor_errors(inspect('readelf', '-W', '-d', '--dyn-syms', DONOR), expected)
    if (after.st_size, after.st_mtime_ns) != donor_stamp:
        errors.append('donor size or mtime changed during checks')
    print(('FAIL ' if errors else 'PASS ') + 'donor integrity after probes: ' +
          ('; '.join(errors) if errors else 'size, mtime, SONAME and exports unchanged'), flush=True)
    failed += bool(errors)
    print('S7-04 checks: %d/%d failed; no install or target execution' % (failed, len(cases) + 2))
    return int(bool(failed))


if __name__ == '__main__':
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', __file__], env=env, text=True).strip()
        sys.exit(subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env))
    sys.exit(main())
