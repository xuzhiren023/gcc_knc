"""S2-02 host checks. The donor supplies ABI locations, never golden assembly.

Probe functions expose one argument at a time. Compare incoming registers and
stack slots relative to entry RSP, plus result registers for constant returns.
Instruction selection inside the function may differ. Scalar probes and the
donor fixture use the scalar KNC allowlist; GCC16 affine loops may vectorize.
Cross-links are T2, not native proof.
"""
import re
import sys


INTEGER = re.compile(r'^(?:mov(?:abs|s[blw]|z[blw])?|lea|push|pop|add|sub|and|or|xor|'
                     r'cmp|test|neg|not|sal|sar|shl|shr|imul|mul|idiv|div|inc|dec|'
                     r'xchg|nop)[bwlq]?$')
SCALAR = set('ret retq leave leaveq call jmp cltq cqto cwtl cltd endbr64 '
             'fld flds fldl fldt fld1 fldz fldcw fldenv '
             'fst fsts fstl fstps fstpl fstpt fstp fstcw fnstcw fnstsw '
             'fadd fadds faddl faddp fsub fsubs fsubl fsubp fsubr fsubrs fsubrl fsubrp '
             'fmul fmuls fmull fmulp fdiv fdivs fdivl fdivp fdivr fdivrs fdivrl fdivrp '
             'fild filds fildl fildq fist fistp fistps fistpl fistpq '
             'fxch fchs fabs fucom fucomp fucompp fcom fcomp fcompp '
             'fnstenv ffree fwait wait sahf kmov '
             'vbroadcastss vbroadcastsd vpackstorelps vpackstorehps '
             'vpbroadcastd vpbroadcastq vpackstoreld vpackstorelq '
             'vpackstorelpd vpackstorehpd vloadunpacklps vloadunpackhps '
             'vloadunpacklpd vloadunpackhpd vmovaps vmovapd '
             'vmovdqa32 vmovdqa64'.split())
CONDITIONS = 'e ne a ae b be g ge l le s ns o no p np z nz nb'.split()
SCALAR.update('j' + c for c in CONDITIONS)
SCALAR.update('set' + c for c in CONDITIONS)

# Lead-approved exception: these donor -O0 probes ICE at knc.md:96.
# Never infer fallback from an arbitrary compilation failure.
DONOR_O0_FALLBACK = frozenset(('abi_in_ff_a', 'abi_in_ff_b'))


def instructions(body):
    for line in body.splitlines():
        line = line.split('#', 1)[0].strip()
        if not line or line.startswith('.') or line.endswith(':'):
            continue
        words = line.split(None, 1)
        if words[0] in ('rep', 'repz') and len(words) == 2:
            words = words[1].split(None, 1)
        yield words[0], words[1] if len(words) == 2 else ''


def forbidden_registers(assembly):
    return sorted(set('SSE/AVX register: ' + operands
                      for _, operands in instructions(assembly)
                      if re.search(r'%(?:[xy]mm\d+|mm[0-7])\b', operands)))


def allowlist(assembly):
    failures = []
    for mnemonic, operands in instructions(assembly):
        if mnemonic not in SCALAR and not INTEGER.fullmatch(mnemonic):
            failures.append('instruction outside scalar IMCI/x87 allowlist: ' + mnemonic)
    return sorted(set(failures + forbidden_registers(assembly)))


def register(name):
    for family in ('di', 'si', 'dx', 'cx'):
        if name in (family, 'e' + family, 'r' + family, family + 'l'):
            return 'r' + family
    return re.sub(r'^(r[89])[dwb]$', r'\1', name)


def locations(body, result=False):
    incoming, written, outputs, stack = set(), set(), set(), set()
    x87_depth = 0
    # Track frame addresses even when the body realigns RSP to 64 bytes.
    addresses = {'rsp': 0}
    for mnemonic, operands in instructions(body):
        if mnemonic in ('fld', 'flds', 'fldl', 'fldt', 'fld1', 'fldz'):
            x87_depth += 1
        elif mnemonic in ('fstp', 'fstps', 'fstpl', 'fstpt', 'faddp', 'fsubp', 'fmulp', 'fdivp'):
            x87_depth -= 1
        regs = [register(r) for r in re.findall(r'%([a-z0-9]+)', operands)]
        dest = re.search(r',\s*%([a-z0-9]+)\s*$', operands)
        dest = register(dest[1]) if dest else None
        reads = regs[:-1] if dest else regs
        # The zero idiom defines its destination without reading its old value.
        if mnemonic.startswith('xor') and regs == [dest, dest]:
            reads = []
        if mnemonic.startswith(('push', 'cmp', 'test')):
            reads, dest = regs, None
        for reg in reads:
            if re.fullmatch(r'zmm[0-7]|rdi|rsi|rdx|rcx|r8|r9', reg) and reg not in written:
                incoming.add(reg)
        if mnemonic != 'leaq':
            for offset, base in re.findall(r'(-?\d*)\(%(\w+)\)', operands):
                if addresses.get(base) is not None:
                    slot = addresses[base] + int(offset or 0)
                    if slot > 0:
                        stack.add(slot)
        if mnemonic.startswith('push') and addresses.get('rsp') is not None:
            addresses['rsp'] -= 8
        elif mnemonic in ('addq', 'subq') and dest == 'rsp':
            amount = re.match(r'\$(-?\d+),', operands)
            if amount and addresses.get('rsp') is not None:
                addresses['rsp'] += int(amount[1]) * (1 if mnemonic == 'addq' else -1)
        elif dest:
            address = re.match(r'(-?\d*)\(%(\w+)\),', operands)
            copy = re.match(r'%(\w+),', operands)
            value = (addresses.get(address[2]) if address and mnemonic == 'leaq' else
                     addresses.get(copy[1]) if copy and mnemonic == 'movq' else None)
            addresses[dest] = (value + int(address[1] or 0)
                               if address and value is not None else value)
        if dest:
            written.add(dest)
            if re.fullmatch(r'zmm[01]', dest):
                outputs.add(dest)
    if x87_depth > 0:
        outputs.add('st0')
    return (sorted(incoming), sorted(stack), sorted(outputs) if result else [])


def compare(runner, assembly, donor, names=None):
    names = re.findall(r'^(abi_\w+):', donor, re.M) if names is None else names
    failures = [] if names else ['donor emitted no ABI probe functions']
    for name in names:
        actual, reference = (runner.function_body(text, name) for text in (assembly, donor))
        if actual is None or reference is None:
            failures.append(name + ': missing function boundary')
            continue
        got, want = (locations(body, name.startswith('abi_out_')) for body in (actual, reference))
        if got != want:
            failures.append('%s: ABI locations %s; donor %s' % (name, got, want))
    return failures


def struct_probes(runner, source):
    # Each struct probe occupies one line; retain declarations and ARGS, but
    # isolate functions so a donor ICE cannot suppress unrelated comparisons.
    lines = source.read_text().splitlines(keepends=True)
    pattern = re.compile(r'^(?:void|struct \w+) (abi_\w+)\(.*\) \{.*\}\s*$')
    probes = [(i, pattern.fullmatch(line)[1]) for i, line in enumerate(lines)
              if pattern.fullmatch(line)]
    if len(probes) != len(re.findall(r'\babi_\w+\s*\(', ''.join(lines))):
        raise RuntimeError('struct probe definitions must each occupy one line')
    if not DONOR_O0_FALLBACK.issubset(name for _, name in probes):
        raise RuntimeError('missing explicit donor -O0 fallback probes')
    function_lines = {i for i, _ in probes}
    for selected, name in probes:
        probe = runner.out / (name + '.c')
        probe.write_text(''.join(line for i, line in enumerate(lines)
                                 if i not in function_lines or i == selected))
        yield probe, name


def t1_probe(runner, source, level, name=None):
    label = 't1 scalar ABI ' + (name or source.name) + ' ' + level
    failures = []
    texts = []
    fallback = level == '-O0' and name in DONOR_O0_FALLBACK
    if fallback:
        label += ' [donor -O2 fallback; GCC16 -O0]'
    for compiler, flags, tag in ((runner.tool('gcc'), [], 'donor'),
                                 (runner.cc, runner.cc_flags, 'gcc16')):
        asm = runner.out / (source.stem + tag + '.s')
        compiled = runner.command(compiler, *flags, level, '-march=knc',
                                  '-ffp-contract=off', '-S', source, '-o', asm, check=False)
        if fallback and tag == 'donor':
            if (compiled.returncode == 0 or
                    'internal compiler error:' not in compiled.stdout or
                    'config/i386/knc.md:96' not in compiled.stdout):
                failures.append('expected donor -O0 ICE at knc.md:96 missing: '
                                + compiled.stdout[-1800:])
                texts.append(None)
                continue
            compiled = runner.command(compiler, *flags, '-O2', '-march=knc',
                                      '-ffp-contract=off', '-S', source, '-o', asm,
                                      check=False)
        if compiled.returncode:
            failures.append(tag + ' compile: ' + compiled.stdout[-1800:])
            texts.append(None)
            continue
        text = asm.read_text()
        texts.append(text)
        failures.extend(tag + ': ' + f for f in allowlist(text))
        obj = asm.with_suffix('.o')
        assembled = runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj, check=False)
        if assembled.returncode:
            failures.append(tag + ' assembler: ' + assembled.stdout[-1000:])
        else:
            lint = runner.command(sys.executable, runner.root / 'tools/knc_lint',
                                  asm, obj, check=False)
            if lint.returncode:
                failures.append(tag + ' lint: ' + lint.stdout[-1000:])
    if all(text is not None for text in texts):
        failures.extend(compare(runner, texts[1], texts[0], [name] if name else None))
    runner.result(label, failures)


def t1_vector_diagnostics(runner):
    source = runner.source_dir / 'knc-abi-mixed.c'
    for case in ('parameter', 'result', 'field'):
        for level in ('-O0', '-O2'):
            compiled = runner.command(
                runner.cc, *runner.cc_flags, level, '-march=knc',
                '-DABI_VECTOR_' + case.upper(), '-S', source,
                '-o', runner.out / 'vector.s', check=False)
            rejected = (compiled.returncode != 0
                        and 'internal compiler error' not in compiled.stdout
                        and 'confused by earlier errors' not in compiled.stdout
                        and 'error: unsupported KNC register ABI mode' in compiled.stdout)
            runner.result('t1 KNC rejects 64-byte int vector ABI ' + case + ' ' + level,
                          [] if rejected else [compiled.stdout[-1800:]
                                               or 'unsupported vector ABI accepted'])


def t1_vector_compatibility(runner, cases=('VECTOR32_PARAMETER', 'VECTOR1_PARAMETER',
                                         'VECTOR1_RESULT')):
    source = runner.source_dir / 'knc-abi-mixed.c'
    for case in cases:
        for level in ('-O0', '-O2'):
            asm = runner.out / 'vector.s'
            compiled = runner.command(
                runner.cc, *runner.cc_flags, level, '-march=knc',
                '-DABI_' + case, '-S', source,
                '-o', asm, check=False)
            failures = ([compiled.stdout[-1800:] or 'compile failed']
                        if compiled.returncode or compiled.stdout.strip()
                        else allowlist(asm.read_text()))
            runner.result('t1 KNC preserves ' + case.lower() + ' ' + level, failures)


def t1_abi_gaps(runner):
    source = runner.root / 'tests/regress/knc-abi-gaps.c'
    for element in ('float', 'double', 'int', 'long long'):
        for record in (False, True):
            for case in ('VAR_CALL', 'VAR_GET', 'MS_CALL', 'MS_PARAM',
                         'MS_RETURN_CALL', 'MS_RETURN_DEF'):
                for level in ('-O0', '-O2'):
                    compiled = runner.command(
                        runner.cc, *runner.cc_flags, level, '-march=knc',
                        '-DELEMENT=' + element, '-D' + case,
                        *(['-DRECORD'] if record else []), '-S', source,
                        '-o', runner.out / 'abi-gap.s', check=False)
                    rejected = (compiled.returncode != 0
                                and 'internal compiler error' not in compiled.stdout
                                and 'confused by earlier errors' not in compiled.stdout
                                and 'error: unsupported KNC register ABI mode' in compiled.stdout)
                    runner.result('t1 packed ABI %s %s %s %s' %
                                  (element, 'record' if record else 'vector', case, level),
                                  [] if rejected else [compiled.stdout[-1800:]
                                                       or 'unsupported ABI accepted'])


def t1(runner):
    t1_vector_diagnostics(runner)
    t1_vector_compatibility(runner)
    t1_abi_gaps(runner)
    for source in sorted(runner.source_dir.glob('knc-abi-*.c')):
        for level in ('-O0', '-O2', '-Os'):
            if source.name == 'knc-abi-structs.c' and level == '-O0':
                for probe, name in struct_probes(runner, source):
                    t1_probe(runner, probe, level, name)
            else:
                t1_probe(runner, source, level)
    affine(runner)
    # S2-02 owns per-function feature gates and zero-call-used-regs, too.
    for feature in ('sse', 'sse2', 'avx', 'avx512f'):
        source = runner.out / 'attribute.c'
        source.write_text('__attribute__((target("%s"))) int f(void) { return 1; }\n' % feature)
        compiled = runner.command(runner.cc, *runner.cc_flags, '-march=knc', '-S', source,
                                  '-o', source.with_suffix('.s'), check=False)
        rejected = (compiled.returncode != 0 and 'internal compiler error' not in compiled.stdout
                    and 'confused by earlier errors' not in compiled.stdout
                    and re.search(r'error:.*(?:knc|KNC)', compiled.stdout))
        runner.result('t1 KNC rejects target attribute ' + feature,
                      [] if rejected else [compiled.stdout or 'feature attribute accepted'])
    source = runner.source_dir / 'knc-abi-float.c'
    asm = runner.out / 'zero.s'
    compiled = runner.command(runner.cc, *runner.cc_flags, '-O2', '-march=knc',
                              '-fzero-call-used-regs=all', '-S', source, '-o', asm, check=False)
    if compiled.returncode:
        supported_diagnostic = ('internal compiler error' not in compiled.stdout and
                                'confused by earlier errors' not in compiled.stdout and
                                re.search(r'error:.*(?:zero-call-used-regs|unsupported)', compiled.stdout))
        failures = [] if supported_diagnostic else [compiled.stdout[-1800:]]
    else:
        failures = allowlist(asm.read_text())
        obj = asm.with_suffix('.o')
        assembled = runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj, check=False)
        if assembled.returncode:
            failures.append(assembled.stdout[-1000:])
    runner.result('t1 KNC zero-call-used-regs legal code or unsupported diagnostic', failures)


def affine(runner):
    # Silent stack/register disagreement must fail even if the fixture compiles.
    failures, texts = [], []
    for cc, flags, tag in ((runner.tool('gcc'), [], 'donor'),
                            (runner.cc, runner.cc_flags, 'gcc16')):
        asm = runner.out / ('affine-' + tag + '.s')
        compiled = runner.command(cc, *flags, '-O2', '-ffp-contract=off',
                                  '--sysroot=' + str(runner.sysroot), '-S', runner.fixture / 'loops.c',
                                  '-o', asm, check=False)
        if compiled.returncode:
            failures.append(tag + ' compile: ' + compiled.stdout[-1800:])
            texts.append(None)
        else:
            texts.append(asm.read_text())
            scan = allowlist if tag == 'donor' else forbidden_registers
            failures.extend(tag + ': ' + f for f in scan(texts[-1]))
    if all(text is not None for text in texts):
        failures.extend(compare(runner, texts[1], texts[0], ['affine_f32', 'affine_f64']))
    runner.result('t1 m1_affine ABI donor locations', failures)


def t2(runner):
    sources = runner.root / 'tests/t2'
    # Fixed shared paths are the S3-10 native inputs; never execute on the host.
    output = runner.tc.parent / 'scalar-abi'
    output.mkdir(exist_ok=True)
    # Keep the existing scalar suite at O2: its ff aggregate has a documented
    # donor O0 ICE.  Every new complex/rounding test runs at both levels.
    for stem, levels in (('knc-scalar-abi', ('-O2',)),
                         ('knc-abi-gaps', ('-O0', '-O2'))):
        symbols = re.findall(r'\b(scalar_\w+)\(', (sources / (stem + '.h')).read_text())
        for level in levels:
            for reverse in (False, True):
                t2_crosscheck(runner, sources, stem, symbols, output, level, reverse)


def t2_crosscheck(runner, sources, stem, symbols, output, level, reverse):
    label = 't2 ' + stem + ' ' + level + ' ' + (
        'donor caller / GCC16 callee' if reverse else 'GCC16 caller / donor callee')
    objects, failures = [], []
    elf = output / ('%s-%s-%d.mic' % (stem[4:], level[1:], int(reverse)))
    elf.unlink(missing_ok=True)
    for role in ('caller', 'callee'):
        use_donor = (role == 'caller') == reverse
        cc, flags = (runner.tool('gcc'), []) if use_donor else (runner.cc, runner.cc_flags)
        obj = runner.out / (role + '.o')
        compiled = runner.command(cc, *flags, level, '-ffp-contract=off',
                                  '-frounding-math', '-fexcess-precision=standard',
                                  '--sysroot=' + str(runner.sysroot), '-c',
                                  sources / (stem + '-' + role + '.c'), '-o', obj, check=False)
        if compiled.returncode:
            failures.append(role + ' compile: ' + compiled.stdout[-1800:])
        else:
            objects.append(obj)
    if not failures:
        linked = runner.command(runner.cc, *runner.cc_flags,
                                '--sysroot=' + str(runner.sysroot), *objects, '-o', elf,
                                '-lm', '-Wl,--trace', check=False)
        if linked.returncode:
            failures.append('link: ' + linked.stdout[-1800:])
        else:
            table = runner.command(runner.tool('nm'), '--defined-only', elf)
            failures.extend('missing linked symbol ' + name for name in symbols
                            if not re.search(r'\bT\s+' + name + r'$', table, re.M))
            runner.t2_abi(elf, linked.stdout)
    runner.result(label, failures)
