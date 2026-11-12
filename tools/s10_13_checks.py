"""S10-13 T1: scalar cbrtl replacement and once-per-call-site diagnostics.

Run through tools/run.py with tools/check.py t1 --compiler gcc16 --cbrtl --worker.
This compiles assembly only; the full x86 portability check belongs to the lead.
"""
import re


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
                    if '[' + WARNING + ']' not in warning:
                        failures.append('wrong warning option: ' + warning)
                    if not all(re.search(word, warning, re.I)
                               for word in ('MPSS', 'cbrtl', 'unsafe', 'replace')):
                        failures.append('warning must explain unsafe MPSS cbrtl replacement')
                runner.result(label, failures)
