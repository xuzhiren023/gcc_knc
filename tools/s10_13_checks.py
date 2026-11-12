"""S10-13 T1: scalar cbrtl replacement and once-per-call-site diagnostics.

Run through tools/run.py with tools/check.py t1 --compiler gcc16 --cbrtl --worker.
This compiles assembly only; the full x86 portability check belongs to the lead.
"""
import re
import os
from pathlib import Path
import subprocess
import sys

import storage


WARNING = '-Wknc-unsafe-cbrtl'
REPLACEMENT = '__knc_cbrtl'


def t1(runner):
    sources = runner.source_dir / 's10-13'
    # Use this lane's compiler with the installed target libstdc++ headers.
    # Do not substitute a hand-written std::cbrt wrapper for the real overload.
    headers = (runner.gcc_build.parent / 'gcc-knc-16.2.0'
               / 'k1om-mpss-linux/include/c++/16.2.0')
    base = [runner.cc, *runner.cc_flags, '--sysroot=' + str(runner.sysroot),
            '-fdiagnostics-color=never', '-fdiagnostics-show-option']
    cases = [('cbrtl.c', ('direct_root', 'builtin_root'), 2),
             ('cbrtl.cc', ('std_root', 'another_std_root'), 2),
             ('cbrtl-generic.c', ('generic_root',), 1)]
    for filename, functions, sites in cases:
        source = sources / filename
        includes = []
        if source.suffix == '.cc':
            includes = ['-std=gnu++11', '-nostdinc++']
            for path in (headers, headers / 'k1om-mpss-linux', headers / 'backward'):
                includes += ['-isystem', str(path)]
        for level in ('-O0', '-O2'):
            for mode in ('knc', 'quiet', 'x86'):
                label = 't1 cbrtl %s %s %s' % (filename, level, mode)
                flags = ['-march=x86-64' if mode == 'x86' else '-march=knc']
                if mode == 'quiet':
                    flags.append('-Wno-knc-unsafe-cbrtl')
                asm = runner.out / (filename + level + '-' + mode + '.s')
                compiled = runner.command(*base, *includes, level, *flags,
                                          '-S', source, '-o', asm, check=False)
                if compiled.returncode:
                    runner.result(label + ' compilation',
                                  ['exit %d: %s' % (compiled.returncode,
                                                   compiled.stdout[-1200:])])
                    continue
                failures = []
                assembly = '\n'.join(line for line in asm.read_text().splitlines()
                                     if not re.match(r'\s*\.file\b', line))
                expected = 'cbrtl' if mode == 'x86' else REPLACEMENT
                forbidden = REPLACEMENT if mode == 'x86' else 'cbrtl'
                # Also cover an out-of-line libstdc++ wrapper at -O0.  A tail
                # jump is a call for this purpose.  No raw cbrtl symbol may
                # survive anywhere in KNC assembly, even in that wrapper.
                call = r'\b(?:call|jmp)\s+' + expected + r'(?:@PLT)?\b'
                if not re.search(call, assembly):
                    failures.append('missing call/tail jump to ' + expected)
                if re.search(r'\b' + forbidden + r'\b', assembly):
                    failures.append('unsafe/unexpected symbol ' + forbidden)
                for name in functions:
                    body = runner.function_body(assembly, name)
                    if body is None:
                        failures.append('missing function ' + name)
                    elif source.suffix != '.cc' and not re.search(call, body):
                        failures.append(name + ' does not call ' + expected)
                warnings = [line for line in compiled.stdout.splitlines()
                            if 'warning:' in line]
                wanted = sites if mode == 'knc' else 0
                if len(warnings) != wanted:
                    failures.append('expected %d warnings, got %d' %
                                    (wanted, len(warnings)))
                for warning in warnings:
                    match = re.search(re.escape(filename) + r':(\d+):', warning)
                    if not match or int(match.group(1)) not in [
                            n for n, line in enumerate(source.read_text().splitlines(), 1)
                            if 'return ' in line and ('cbrt' in line or 'root' in line)]:
                        failures.append('warning not at a user call site: ' + warning)
                    if '[' + WARNING + ']' not in warning:
                        failures.append('wrong warning option: ' + warning)
                    if not all(re.search(word, warning, re.I)
                               for word in ('MPSS', 'cbrtl', 'unsafe', 'replace')):
                        failures.append('warning must explain unsafe MPSS cbrtl replacement')
                runner.result(label, failures)


def main():
    root = Path(__file__).resolve().parents[1]
    project = root.parent.parent if root.parent.name == '.work' else root
    shared = project / '.work/_shared'
    tc = shared / 'toolchain'
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(tc / p) for p in
                                      ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'), '-u', __file__],
                                         env=env, text=True).strip()
        return subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]],
                               env=env)
    os.environ['PATH'] = ':'.join(str(tc / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    out = shared / 'S10-13'
    out.mkdir(exist_ok=True)
    source = root / 'tests/t1/s10-13/cbrtl.c'
    build = Path(storage.gcc_build_dir(project))
    runtime = Path(storage.gcc_tree(project)) / 'libgcc/config/i386/knc-cbrtl.c'

    def run(*args):
        subprocess.run(list(map(str, args)), check=True)

    action = sys.argv[1]
    if action == 'model':
        model = out / 'cbrtl-model.exe'
        run('gcc', '-O2', '-std=gnu11', '-ffp-contract=off', '-DCBRTL_MODEL',
            source, runtime, '-lmpfr', '-lgmp', '-pthread', '-o', model)
        run(model, out / 'expected')
    elif action == 'stage':
        flags = ['-B' + str(build / 'gcc') + '/',
                 '-B' + str(build / 'k1om-mpss-linux/libgcc') + '/',
                 '--sysroot=' + str(tc / 'sysroot'), '-O2', '-std=gnu11',
                 '-march=knc', '-static-libgcc', '-pthread']
        native, fault = out / 'cbrtl-native.mic', out / 'cbrtl-fault.mic'
        run(build / 'gcc/xgcc', *flags, '-DCBRTL_NATIVE', source, '-o', native)
        run(build / 'gcc/xgcc', *flags, '-DCBRTL_FAULT', source, '-lm', '-o', fault)
        run(sys.executable, root / 'tools/knc_lint', native, fault)
        print('Staged only; native results pending lead card run.')
        for part in range(4):
            print('python tools/card_run --threads 240 --timeout 1800 --file '
                  '.work/_shared/S10-13/expected-%d.bin .work/_shared/S10-13/cbrtl-native.mic '
                  'expected-%d.bin %d' % (part, part, part))
        print('python tools/card_run --threads 1 --timeout 30 .work/_shared/S10-13/cbrtl-fault.mic')
    elif action == 'audit':
        installed = shared / 'gcc-knc-16.2.0'
        seen = set()
        for path in sorted(installed.rglob('*')):
            if not path.is_file() or not (path.name.endswith('.a') or '.so' in path.name):
                continue
            path = path.resolve()
            if path in seen:
                continue
            with path.open('rb') as stream:
                magic = stream.read(8)
            if not (magic.startswith(b'\x7fELF') or magic == b'!<arch>\n'):
                continue  # linker scripts are not libraries with symbol tables
            seen.add(path)
            flags = ['-D'] if magic.startswith(b'\x7fELF') else []
            result = subprocess.run(['k1om-mpss-linux-nm', *flags, '-u', str(path)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode:
                raise RuntimeError('nm failed for %s: %s' % (path, result.stderr))
            if re.search(r'\b[Uwv]\s+cbrtl(?:@\S+)?\s*$', result.stdout, re.M):
                raise RuntimeError('unsafe cbrtl reference in ' + str(path))
        if not seen:
            raise RuntimeError('no installed target libraries audited')
        print('PASS cbrtl audit: %d installed libraries, no unsafe references' % len(seen))
    else:
        raise ValueError('expected model, stage or audit')
    return 0


if __name__ == '__main__':
    sys.exit(main())
