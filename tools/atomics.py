"""S2-06 T1/T2; native execution is exclusively through tools/card_run."""
import re
import sys


def t1(runner):
    for name in ('knc-atomics', 'knc-spin-hint'):
        asm = runner.out / (name + '.s')
        flags = ['-mrelax-cmpxchg-loop'] if name == 'knc-spin-hint' else []
        result = runner.command(runner.cc, *runner.cc_flags, '-O2', '-march=knc',
                                *flags,
                                '-S', runner.root / ('tests/t1/' + name + '.c'),
                                '-o', asm, check=False)
        failures = []
        if result.returncode:
            failures.append(result.stdout[-2200:])
        else:
            assembly = asm.read_text()
            if name == 'knc-atomics':
                for op in ('load', 'store', 'exchange', 'add', 'cas'):
                    body = runner.function_body(assembly, 'atomic_' + op + '_16')
                    if not body or not re.search(r'\b(?:call|jmp)\s+__atomic_\w+_16\b', body):
                        failures.append('atomic_' + op + '_16: missing libatomic call')
                for op in ('add', 'cas', 'lock', 'unlock'):
                    body = runner.function_body(assembly, 'sync_' + op + '_16')
                    if not body or not re.search(r'\b(?:call|jmp)\s+__atomic_\w+_16\b', body):
                        failures.append('sync_' + op + '_16: missing libatomic call')
            else:
                for function in ('spin_hint', 'spin_wait', 'spin_update'):
                    body = runner.function_body(assembly, function)
                    if not body or not re.search(r'^\s*delay\s+%', body, re.M):
                        failures.append(function + ': missing delay')
            obj = asm.with_suffix('.o')
            assembled = runner.command(runner.tool('as'), '--march=k1om', asm,
                                       '-o', obj, check=False)
            if assembled.returncode:
                failures.append('assembler: ' + assembled.stdout[-1600:])
            lint = runner.command(sys.executable, runner.root / 'tools/knc_lint',
                                  asm, *([obj] if not assembled.returncode else []), check=False)
            if lint.returncode:
                failures.append('lint: ' + lint.stdout[-1600:])
        runner.result('t1 ' + name, failures)


def t2(runner):
    out = runner.tc.parent / 'tmp/S2-06'
    out.mkdir(parents=True, exist_ok=True)
    donor = runner.tc / 'cross/lib/gcc/k1om-mpss-linux/5.1.1'
    libraries = runner.tc / 'cross/k1om-mpss-linux/lib64'
    for library in ('gcc_s', 'atomic'):
        (out / ('lib' + library + '_asneeded.so')).write_text(
            'INPUT ( AS_NEEDED ( -l' + library + ' ) )\n')
    elf = out / 'atomic-counter.mic'
    linked = runner.command(runner.cc, *runner.cc_flags, '-O2', '-pthread',
                            '-B' + str(donor) + '/', '-L' + str(out),
                            '-L' + str(libraries),
                            runner.root / 'tests/t2/knc-atomic-counter.c',
                            runner.root / 'tests/t1/knc-atomics.c',
                            runner.root / 'tests/t1/knc-spin-hint.c',
                            '-o', elf, check=False)
    failures = [linked.stdout[-2200:]] if linked.returncode else []
    if not failures:
        lint = runner.command(sys.executable, runner.root / 'tools/knc_lint', elf, check=False)
        if lint.returncode:
            failures.append(lint.stdout[-1600:])
    runner.result('t2 atomic pthread counter link (donor runtime bridge)', failures)
    runner.say('Native counter, not yet run: ' + str(elf))
