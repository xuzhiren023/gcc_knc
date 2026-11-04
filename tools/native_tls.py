"""S3-14 T1: compare native TLS addressing with donor-generated assembly."""
import re


FUNCTIONS = (('read_defined', 'tv'), ('read_external', 'te'))
# Compare the ordered ABI operations, ignoring register allocation, prologues,
# local labels and assembler prefix spelling across GCC versions.
TLS_OPERATION = re.compile(r'%fs:|\b(?:tv|te)@(?:tpoff|gottpoff|tlsgd)\b|'
                           r'\b__tls_get_addr\b', re.I)


def scan(body, symbol, pic):
    failures = []
    if body is None:
        return ['missing function boundary'], []
    body = '\n'.join(line.split('#', 1)[0] for line in body.splitlines())
    if '__emutls' in body:
        failures.append('emulated TLS (__emutls)')
    relocation = 'tlsgd' if pic else ('tpoff' if symbol == 'tv' else 'gottpoff')
    if not re.search(r'\b' + symbol + '@' + relocation + r'\b', body, re.I):
        failures.append('missing ' + symbol + '@' + relocation)
    if pic:
        # General-dynamic PIC obtains the thread address through the resolver;
        # local-exec/initial-exec instead read the %fs thread pointer directly.
        if not re.search(r'\bcall\s+__tls_get_addr(?:@PLT)?\b', body):
            failures.append('missing native TLS resolver call')
    elif '%fs:' not in body:
        failures.append('missing %fs thread-pointer access')
    return failures, [match[0].lower() for match in TLS_OPERATION.finditer(body)]


def t1(runner):
    source = runner.root / 'tests/t1/knc-tls.c'
    for mode, options in (('O2', ['-O2']), ('O2-PIC', ['-O2', '-fPIC']),
                          ('O0', ['-O0'])):
        pic = '-fPIC' in options
        signatures = {}
        for tag, compiler, flags in (('donor', runner.tool('gcc'), []),
                                     ('selected', runner.cc, runner.cc_flags)):
            asm = runner.out / ('tls-' + tag + '-' + mode + '.s')
            compiled = runner.command(compiler, *flags, *options, '-march=knc',
                                      '--sysroot=' + str(runner.sysroot),
                                      '-S', source, '-o', asm, check=False)
            if compiled.returncode:
                runner.result('t1 native TLS ' + tag + ' ' + mode,
                              ['compiler: ' + compiled.stdout[-2200:]])
                continue
            assembly = asm.read_text()
            failures = []
            if '__emutls' in assembly:
                failures.append('assembly contains __emutls')
            signatures[tag] = {}
            for function, symbol in FUNCTIONS:
                problems, operations = scan(runner.function_body(assembly, function),
                                            symbol, pic)
                failures.extend(function + ': ' + problem for problem in problems)
                signatures[tag][function] = operations
                runner.say('TLS ' + tag + ' ' + mode + ' ' + function + ': ' +
                           repr(operations))
            if tag == 'selected' and 'donor' in signatures:
                for function, symbol in FUNCTIONS:
                    expected = signatures['donor'][function]
                    actual = signatures[tag][function]
                    if actual != expected:
                        failures.append(function + ': TLS sequence differs from donor; '
                                        + repr(actual) + ' != ' + repr(expected))
            runner.result('t1 native TLS ' + tag + ' ' + mode, failures)
