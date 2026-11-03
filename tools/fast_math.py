"""S2-15 T2 links; retain the -Ofast executable for the lead's card run."""
import re


def t2(runner):
    if runner.args.compiler != 'gcc16':
        raise RuntimeError('fast-math checks require --compiler gcc16')
    runtime = runner.tc.parent / 'gcc-build/gcc/crtfastmath.o'
    out = runner.tc.parent / 'tmp/S2-15'
    out.mkdir(parents=True, exist_ok=True)
    options = [('-Ofast',), ('-ffast-math',),
               ('-funsafe-math-optimizations',), ('-mdaz-ftz',),
               ('-Ofast', '-mno-daz-ftz')]
    for flags in options:
        tag = flags[-1].lstrip('-')
        elf = out / (tag + '.mic')
        elf.unlink(missing_ok=True)
        link = runner.command(runner.cc, *runner.cc_flags, *flags, '-v',
                              '-Wl,--trace', runner.root / 'tests/t2/knc-fast-math.c',
                              '-o', elf, check=False)
        runner.say(link.stdout)
        failures = ['link exited ' + str(link.returncode)] if link.returncode else []
        if flags[-1] == '-mno-daz-ftz':
            if 'crtfastmath.o' in link.stdout:
                failures.append('disabled startup still links crtfastmath.o')
        elif str(runtime) not in link.stdout:
            failures.append('link did not use fork crtfastmath.o')
        runner.result('t2 fast-math ' + ' '.join(flags), failures)
        if flags != ('-Ofast',):
            elf.unlink(missing_ok=True)
    if not runtime.is_file():
        runner.result('t2 fast-math MXCSR read-modify-write', ['missing ' + str(runtime)])
        return
    dump = runner.command(runner.tool('objdump'), '-dr', '--no-show-raw-insn', runtime)
    runner.say(dump)
    insns = re.findall(r'^\s*[0-9a-f]+:\s+(\S+)(?:\s+([^\n]*))?$', dump, re.M)
    failures = []
    # An exact four-instruction body excludes CPUID and any other MXCSR write.
    if [op for op, _ in insns] != ['stmxcsr', 'orl', 'ldmxcsr', 'retq']:
        failures.append('expected only stmxcsr; orl; ldmxcsr; retq')
    elif (insns[0][1] != insns[2][1]
          or insns[1][1] != '$0x8040,' + insns[0][1]):
        failures.append('MXCSR must be read, ORed with only 0x8040, and written back')
    runner.result('t2 fast-math MXCSR read-modify-write', failures)
    runner.say('Lead card executable: ' + str(out / 'Ofast.mic'))
