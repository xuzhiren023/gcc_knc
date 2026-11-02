#!/usr/bin/env python3
"""Run t0 (regressions), t1 (code generation), t2 (link ABI).

Usage: python tools/check t0 t1 t2 --compiler donor
Use --record tests/baseline/donor-gcc5.txt to record a measured baseline.
gcc16 requires --cc pointing at its installed compiler. T3 is reserved for
tools/card_run; this runner never executes target programs on the host.
"""
import argparse
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
FUNCTIONS = ('affine_f32', 'affine_f64', 'recurrence_f32')
PACKED = re.compile(r'\bv(?:addn?|subr?|mul|div|max|min|sqrt|rcp(?:23)?|rsqrt(?:23)?|fmadd\w*|fmsub\w*|fnmadd\w*|fnmsub\w*)(?:ps|pd)\b.*%zmm\d+\b')


def loop_lines(source):
    """Map each affine function to its loop's source line, for opt-info scans."""
    result = {}
    function = None
    for number, line in enumerate(source.splitlines(), 1):
        for name in FUNCTIONS[:2]:
            if re.match(r'\s*' + name + r'\s*\(', line):
                function = name
        if function and re.search(r'\bfor\s*\(', line):
            result[function] = number
            function = None
    return result


def function_body(assembly, name):
    # Local labels and other functions must never donate instructions to a scan.
    match = re.search(r'^' + name + r':\s*\n(.*?)^\s*\.size\s+' + name + r'\s*,',
                      assembly, re.M | re.S)
    return match[1] if match else None


def loops(body):
    lines = [line.split('#', 1)[0] for line in body.splitlines()]
    labels = {}
    for i, line in enumerate(lines):
        label = re.match(r'\s*([\w.$]+):', line)
        if label:
            labels[label[1]] = i
        branch = re.match(r'\s*j\w+\s+([\w.$]+)\s*$', line)
        if branch and branch[1] in labels:
            yield '\n'.join(lines[labels[branch[1]]:i + 1])


def scan_t1(assembly, report, source, fast=False):
    failures = []
    locations = loop_lines(source)
    for name in FUNCTIONS:
        body = function_body(assembly, name)
        if body is None:
            failures.append(name + ': missing function boundary')
            continue
        body = '\n'.join(line.split('#', 1)[0] for line in body.splitlines())
        if name == 'recurrence_f32':
            if PACKED.search(body):
                failures.append(name + ': packed zmm FP arithmetic in scalar recurrence')
            continue
        suffix = 'ps' if name.endswith('f32') else 'pd'
        patterns = ([r'vfmadd\w*' + suffix] if fast else ['vmul' + suffix, 'vadd' + suffix])
        candidates = list(loops(body))
        if not any(PACKED.search(loop) for loop in candidates):
            failures.append(name + ': no packed `zmm` arithmetic')
        elif not any(all(re.search(r'\b' + p + r'\b[^\n]*%zmm\d+\b', loop)
                         for p in patterns) for loop in candidates):
            failures.append(name + ': main loop lacks ' + ' and '.join(patterns))
        if not fast and re.search(r'\bv(?:f[mn]|fnm)\w*(?:ps|pd)\b', body):
            failures.append(name + ': fused arithmetic with contraction off')
        line = locations.get(name)
        if line is None or not re.search(r'(?:^|[/\\\s])loops\.c:' + str(line) +
                                         r'(?::\d+)?:[^\n]*\b(?:LOOP VECTORIZED|loop vectorized|vectorized loop)\b', report):
            failures.append(name + ': no -fopt-info-vec report for this loop')
    return failures


def scan_elf(data):
    try:
        if data[:6] != b'\x7fELF\x02\x01':
            return ['not a little-endian ELF64 file']
        failures = []
        if struct.unpack_from('<H', data, 18)[0] != 181:
            failures.append('ELF machine is not 181 (EM_K1OM)')
        offset = struct.unpack_from('<Q', data, 32)[0]
        size, count = struct.unpack_from('<HH', data, 54)
        interpreters = []
        for i in range(count):
            entry = offset + i * size
            if struct.unpack_from('<I', data, entry)[0] == 3:
                start = struct.unpack_from('<Q', data, entry + 8)[0]
                length = struct.unpack_from('<Q', data, entry + 32)[0]
                interpreters.append(data[start:start + length])
        if interpreters != [b'/lib64/ld-linux-k1om.so.2\0']:
            failures.append('wrong or missing KNC interpreter')
        return failures
    except (struct.error, IndexError):
        return ['truncated ELF headers']


def versioned_symbols(text, undefined):
    result = set()
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].endswith(':'):
            continue
        if (fields[6] == 'UND') != undefined:
            continue
        name = fields[7].replace('@@', '@')
        if '@' in name:
            result.add(name)
    return result


class Runner:
    def __init__(self, args):
        self.args = args
        manifest = json.loads((ROOT / 'toolchain/manifest.json').read_text())
        self.tc = PROJECT / manifest['root']
        self.sysroot = self.tc / manifest['sysroot']
        self.cc = Path(args.cc) if args.cc else self.tool('gcc')
        self.env = os.environ.copy()
        self.env['PATH'] = os.pathsep.join(str(self.tc / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + self.env.get('PATH', '')
        output_root = PROJECT / '.work/_shared/check'
        output_root.mkdir(parents=True, exist_ok=True)
        self._output = tempfile.TemporaryDirectory(dir=output_root,
                                                  prefix=args.compiler + '-',
                                                  ignore_cleanup_errors=True)
        self.out = Path(self._output.name)
        self.lines = []
        self.failed = False
        self.fixture = ROOT / 'tests/acceptance/m1_affine'
        self.flags = ['-O2', '-ftree-vectorize', '--sysroot=' + str(self.sysroot)]
        self.off_object = None

    def tool(self, name):
        return self.tc / ('cross/bin/k1om-mpss-linux-' + name + '.exe')

    def say(self, text):
        print(text, flush=True)
        self.lines.append(text)

    def result(self, label, failures):
        self.failed |= bool(failures)
        self.say(('FAIL ' if failures else 'PASS ') + label + (': ' + '; '.join(failures) if failures else ''))

    def command(self, *args):
        result = subprocess.run([str(a) for a in args], env=self.env, cwd=ROOT,
                                text=True, errors='replace', stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=60)
        if result.returncode:
            raise RuntimeError('command %s exited %d: %s' %
                               (' '.join(str(a) for a in args), result.returncode, result.stdout[-2500:]))
        return result.stdout

    def t0(self):
        # Compiler regressions only; pm/git/dispatch suites have separate runners.
        for directory, pattern in (('tests/regress', 'test_*.py'),
                                   ('tests/tools', 'test_doctor.py'),
                                   ('tests/tools', 'test_knc_lint.py')):
            label = directory + '/' + pattern
            try:
                output = self.command(sys.executable, '-m', 'unittest', 'discover', '-s', directory, '-p', pattern)
                self.say('PASS t0 ' + label + ': ' + ' '.join(output.strip().splitlines()[-3:]))
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                self.result('t0 ' + label, [str(error)])

    def t1(self):
        source = (self.fixture / 'loops.c').read_text()
        for mode in ('off', 'fast'):
            asm = self.out / ('loops-' + mode + '.s')
            obj = self.out / ('loops-' + mode + '.o')
            report = self.command(self.cc, *self.flags, '-ffp-contract=' + mode,
                                  '-fopt-info-vec-all', '-S', self.fixture / 'loops.c', '-o', asm)
            (self.out / ('loops-' + mode + '.vec')).write_text(report)
            self.command(self.tool('as'), '--march=k1om', asm, '-o', obj)
            self.result('t1 ' + mode + ' assembly --march=k1om', [])
            self.command(sys.executable, ROOT / 'tools/knc_lint', asm, obj)
            self.result('t1 ' + mode + ' knc_lint', [])
            self.result('t1 ' + mode + ' function scans', scan_t1(asm.read_text(), report, source, mode == 'fast'))
            if mode == 'off':
                self.off_object = obj

    def t2(self):
        loops_obj = self.off_object or self.out / 'loops-off.o'
        if not self.off_object:
            self.command(self.cc, *self.flags, '-ffp-contract=off', '-c', self.fixture / 'loops.c', '-o', loops_obj)
        driver = self.out / 'driver.o'
        elf = self.out / 'm1_affine.mic'
        self.command(self.cc, *self.flags, '-ffp-contract=off', '-c', self.fixture / 'driver.c', '-o', driver)
        trace = self.command(self.cc, '--sysroot=' + str(self.sysroot), driver, loops_obj,
                             '-Wl,--trace', '-o', elf)
        for library in ('libc.so.6', 'ld-linux-k1om.so.2'):
            paths = []
            for line in trace.splitlines():
                resolved = re.search(r'\(([^()]+)\)\s*$', line)
                path = resolved[1] if resolved else line.strip()
                if path.endswith('/' + library):
                    paths.append(path)
            try:
                for path in paths:
                    Path(path).resolve().relative_to(self.sysroot.resolve())
            except ValueError:
                raise RuntimeError('link trace outside shared sysroot for ' + library + ': ' + repr(paths))
            if not paths:
                raise RuntimeError('link trace outside shared sysroot or missing ' + library + ': ' + repr(paths))
            self.say('T2 link trace: ' + '; '.join(paths))
        self.result('t2 ELF machine and interpreter', scan_elf(elf.read_bytes()))
        required = versioned_symbols(self.command(self.tool('readelf'), '--dyn-syms', '--wide', elf), True)
        # Resolve version requirements against each named library in the card sysroot,
        # never against host libraries or just a numeric maximum GLIBC version.
        versions = self.command(self.tool('readelf'), '--version-info', '--wide', elf)
        failures = [] if required else ['no versioned symbol requirements found']
        for library, section in re.findall(r'File:\s+(\S+)(.*?)(?=\n\s*0x[0-9a-f]+:\s+Version:|\Z)', versions, re.S):
            names = set(re.findall(r'Name:\s+(\S+)', section))
            needed = {symbol for symbol in required if symbol.split('@', 1)[1] in names}
            provider = next((self.sysroot / d / library for d in ('lib64', 'usr/lib64')
                             if (self.sysroot / d / library).is_file()), None)
            if provider is None:
                failures.append('missing card sysroot library ' + library)
            else:
                exports = versioned_symbols(self.command(self.tool('readelf'), '--dyn-syms', '--wide', provider), False)
                failures.extend(library + ' lacks ' + symbol for symbol in sorted(needed - exports))
            required -= needed
        failures.extend('unresolved version requirement ' + symbol for symbol in sorted(required))
        self.result('t2 symbol versions against card sysroot', failures)

    def run(self):
        with self._output:
            return self._run()

    def _run(self):
        start = time.monotonic()
        self.say('Compiler: ' + self.command(self.cc, '--version').splitlines()[0])
        for program in ('ld', 'as'):
            self.say('Compiler ' + program + ': ' + self.command(self.cc, '-print-prog-name=' + program).strip())
        self.say('Flags: -O2 -ftree-vectorize -ffp-contract=off / fast; separate driver translation unit')
        self.say('T2 ABI reference: ' + str(self.sysroot) + ' (no native card execution in t0-t2)')
        if self.args.compiler == 'donor':
            self.say('Development files: crt1.o, crti.o, crtn.o, libc.so, libc_nonshared.a from PhiWeather/.tools/knc-bootstrap/sysroot/usr/lib64; origin differs from card runtime. Runtime libraries and loader retained from card; T3 on card is the final proof.')
        for tier in self.args.tiers:
            try:
                getattr(self, tier)()
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                self.result(tier + ' infrastructure', [str(error)])
        self.say('Elapsed: %.2f seconds' % (time.monotonic() - start))
        if self.args.record:
            path = Path(self.args.record)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('\n'.join(self.lines) + '\n')
        return int(self.failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tiers', nargs='+', choices=('t0', 't1', 't2'))
    parser.add_argument('--compiler', choices=('donor', 'gcc16'), default='donor')
    parser.add_argument('--cc', help='installed gcc16 compiler path')
    parser.add_argument('--record', help='small baseline result file')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.compiler == 'gcc16' and not args.cc:
        parser.error('--compiler gcc16 requires --cc')
    if os.name == 'nt':
        # Cygwin git emits POSIX paths; GCC/ld also need a POSIX sysroot.
        # Keep the complete run (including run.py and regressions) in that runtime.
        manifest = json.loads((ROOT / 'toolchain/manifest.json').read_text())
        tc = PROJECT / manifest['root']
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(tc / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'), '-u',
                                          str(Path(__file__).resolve())], env=env, text=True).strip()
        arguments = list(sys.argv[1:])
        for flag in ('--cc', '--record'):
            if flag in arguments:
                index = arguments.index(flag) + 1
                arguments[index] = subprocess.check_output(
                    [str(tc / 'cygwin/bin/cygpath.exe'), '-u', arguments[index]], env=env, text=True).strip()
        return subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script, *arguments], env=env)
    if args.worker:
        return Runner(args).run()
    command = [sys.executable, str(ROOT / 'tools/run.py'), '--name',
               'check-' + args.compiler + '-' + '-'.join(args.tiers)]
    # External compiler and sysroot changes are not tracked by project inputs.
    if args.tiers == ['t0']:
        command += ['--inputs', 'tools', 'tests/acceptance', 'tests/regress', 'tests/tools', 'toolchain']
    command += ['--', sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], '--worker']
    return subprocess.call(command)


if __name__ == '__main__':
    raise SystemExit(main())
