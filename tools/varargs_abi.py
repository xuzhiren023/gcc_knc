"""S2-03: donor varargs ABI, ADR-0004 point 4; T2 never runs target code.

Run: python tools/check.py t1 t2 --compiler gcc16 --varargs-abi
Native follow-up: build donor-only and both cross-links from tests/t2/knc-varargs-*,
run through tools/card_run, compare their exit status and stdout byte for byte.
"""
import re
import struct

from scalar_abi import allowlist, instructions


def reg(name):
    return {'al': 'rax', 'ax': 'rax', 'eax': 'rax',
            'edx': 'rdx', 'ecx': 'rcx', 'edi': 'rdi', 'esi': 'rsi',
            'ebp': 'rbp', 'esp': 'rsp'}.get(name, name)


def literals(assembly):
    """Read the constant pool used by the straight-line overflow caller."""
    values, label, words = {}, None, []
    for line in assembly.splitlines():
        match = re.fullmatch(r'(\.LC\w+):', line.strip())
        if match:
            label, words = match[1], []
        data = re.match(r'\s*\.(long|quad)\s+(-?\d+)\s*$', line)
        if data and label:
            size = 32 if data[1] == 'long' else 64
            words.extend((int(data[2]) % (1 << size)).to_bytes(size // 8, 'little'))
            values[label] = int.from_bytes(bytes(words[:8]), 'little')
    return values


def step(mnemonic, operands, known, pool):
    """Track immediate copies; invalidate other explicit register writes."""
    dest = re.search(r'(?:^|,)\s*%([a-z0-9]+)\s*$', operands)
    if not dest or mnemonic.startswith(('test', 'cmp', 'push', 'call', 'j')):
        return
    name = reg(dest[1])
    value = None
    if mnemonic.startswith(('mov', 'kmov')):
        source = operands.split(',', 1)[0].strip()
        if re.fullmatch(r'\$-?\d+', source):
            value = int(source[1:])
        elif source.startswith('%'):
            value = known.get(reg(source[1:]))
        else:
            match = re.fullmatch(r'(\.LC\w+)\(%rip\)', source)
            if match:
                value = pool.get(match[1])
    elif mnemonic.startswith('xor') and operands.replace(' ', '').split(',') == ['%' + dest[1]] * 2:
        value = 0
    known[name] = value


def caller(body, count, pool):
    known, stack, sp = {}, {}, 0
    x87 = []
    for mnemonic, operands in instructions(body):
        if mnemonic == 'call' and re.match(r'var_target(?:@PLT)?$', operands):
            failures = []
            if known.get('rax') != min(count, 8):
                failures.append('AL at call is %s, expected %d' % (known.get('rax'), min(count, 8)))
            if count > 8:
                for slot, value in enumerate((9., 10.)):
                    bits = int.from_bytes(struct.pack('<d', value), 'little')
                    if stack.get(sp + 8 * slot) != bits:
                        failures.append('overflow double %d missing from outgoing stack slot %d' % (9 + slot, slot))
            return failures
        if mnemonic in ('subq', 'addq') and operands.endswith(', %rsp'):
            amount = re.match(r'\$(\d+),', operands)
            if amount:
                sp += int(amount[1]) * (-1 if mnemonic == 'subq' else 1)
        if mnemonic == 'leaq':
            adjust = re.fullmatch(r'(-?\d+)\(%rsp\),\s*%rsp', operands)
            if adjust:
                sp += int(adjust[1])
        source = operands.split(',', 1)[0].strip()
        value = (int(source[1:]) if re.fullmatch(r'\$-?\d+', source)
                 else known.get(reg(source[1:])) if source.startswith('%')
                 else pool.get(source))
        memory_source = re.fullmatch(r'(-?\d*)\(%rsp\)', source)
        if memory_source:
            value = stack.get(sp + int(memory_source[1] or 0))
        if mnemonic == 'pushq':
            sp -= 8
            stack[sp] = value
        memory = re.search(r',\s*(-?\d*)\(%rsp\)$', operands)
        if mnemonic.startswith('mov') and memory:
            stack[sp + int(memory[1] or 0)] = value
        if mnemonic in ('fldl', 'flds'):
            constant = re.fullmatch(r'(\.LC\w+)\(%rip\)', operands)
            value = pool.get(constant[1]) if constant else None
            if mnemonic == 'flds' and value is not None:
                single = struct.unpack('<f', value.to_bytes(4, 'little'))[0]
                value = int.from_bytes(struct.pack('<d', single), 'little')
            x87.append(value)
        elif mnemonic == 'fld1':
            x87.append(int.from_bytes(struct.pack('<d', 1.), 'little'))
        if mnemonic == 'fstpl':
            memory = re.fullmatch(r'(-?\d*)\(%rsp\)', operands)
            value = x87.pop() if x87 else None
            if memory:
                stack[sp + int(memory[1] or 0)] = value
        step(mnemonic, operands, known, pool)
    return ['missing var_target call']


def save_area(body):
    failures, stores, known = [], {}, {}
    tested, guarded, offset48 = False, False, False
    for mnemonic, operands in instructions(body):
        if mnemonic == 'testb' and re.fullmatch(r'%al,\s*%al', operands):
            tested = True
        elif mnemonic == 'je' and tested:
            guarded = True
            target = operands
        dest = re.search(r',\s*%(rax|eax|ax|al)\s*$', operands)
        if dest and not tested:
            failures.append('scratch overwrites AL before its incoming test')
        if mnemonic == 'vpackstorelq':
            match = re.fullmatch(r'%zmm([0-7]),\s*(-?\d*)\(%(\w+)\)\{%((?:k)[0-7])\}', operands)
            if not match:
                failures.append('unrecognized save store: ' + operands)
                continue
            if not guarded or known.get(match[4]) != 3:
                failures.append('save needs AL zero guard and mask 3: ' + operands)
            stores[int(match[1])] = (int(match[2] or 0), match[3])
        step(mnemonic, operands, known, {})
        # GCC can combine gp_offset=8 and fp_offset=48 into one 64-bit store.
        if mnemonic.startswith('mov'):
            source = operands.split(',', 1)[0].strip()
            value = (int(source[1:]) if re.fullmatch(r'\$-?\d+', source)
                     else known.get(reg(source[1:])) if source.startswith('%') else None)
            if value is not None and (value == 48 or value >> 32 == 48):
                offset48 = True
    if sorted(stores) != list(range(8)):
        failures.append('expected saves of zmm0-zmm7; got ' + repr(sorted(stores)))
    elif any(stores[i] != (stores[0][0] + 16 * i, stores[0][1]) for i in range(8)):
        failures.append('register save slots do not have 16-byte stride: ' + repr(stores))
    if not tested or not guarded:
        failures.append('missing incoming AL test / zero branch')
    elif stores and body.find(target + ':') < body.rfind('vpackstorelq'):
        failures.append('AL zero branch does not skip all save stores')
    if not offset48:
        failures.append('missing fp_offset=48 initialization')
    return failures


def t1(runner):
    source = runner.source_dir / 'knc-varargs.c'
    for level in ('-O0', '-O2'):
        for callee in (False, True):
            role = 'callee' if callee else 'caller'
            for cc, flags, tag in ((runner.tool('gcc'), [], 'donor'),
                                    (runner.cc, runner.cc_flags, 'gcc16')):
                selected = runner.args.varargs_case
                if selected and tag + '-' + role + '-' + level[1:] not in selected:
                    continue
                asm = runner.out / ('varargs-' + role + '-' + tag + '.s')
                compiled = runner.command(cc, *flags, level, '-march=knc',
                    '-fno-optimize-sibling-calls', '-ffp-contract=off',
                    *(['-DVARARGS_CALLEE'] if callee else []),
                    '-S', source, '-o', asm, check=False)
                failures = []
                if compiled.returncode:
                    failures.append('compile: ' + compiled.stdout[-1800:])
                else:
                    assembly = asm.read_text()
                    failures.extend(allowlist(assembly))
                    if callee:
                        body = runner.function_body(assembly, 'var_save')
                        failures.extend(save_area(body) if body else ['missing var_save'])
                    else:
                        for count in (0, 1, 8, 10):
                            body = runner.function_body(assembly, 'var_call_' + str(count))
                            failures.extend('call %d: %s' % (count, f) for f in
                                (caller(body, count, literals(assembly)) if body else ['missing function']))
                            if count == 10 and body and any('overflow double' in f for f in failures):
                                runner.say('Overflow diagnostic ' + tag + ' ' + level + ':\n' + body)
                    assembled = runner.command(runner.tool('as'), '--march=k1om', asm,
                                                '-o', asm.with_suffix('.o'), check=False)
                    if assembled.returncode:
                        failures.append('assembler: ' + assembled.stdout[-1000:])
                runner.result('t1 varargs ' + tag + ' ' + role + ' ' + level, failures)


def t2(runner):
    sources = runner.root / 'tests/t2'
    for donor_caller in (True, False):
        objects, failures = [], []
        for role in ('caller', 'callee'):
            cc, flags = ((runner.tool('gcc'), []) if (role == 'caller') == donor_caller
                         else (runner.cc, runner.cc_flags))
            obj = runner.out / ('varargs-' + role + '.o')
            compiled = runner.command(cc, *flags, '-O2', '-march=knc', '-fno-builtin',
                '--sysroot=' + str(runner.sysroot), '-c',
                sources / ('knc-varargs-' + role + '.c'), '-o', obj, check=False)
            if compiled.returncode:
                failures.append(role + ' compile: ' + compiled.stdout[-1800:])
            objects.append(obj)
        if not failures:
            elf = runner.out / ('varargs-' + str(int(donor_caller)) + '.mic')
            linked = runner.command(runner.cc, *runner.cc_flags,
                '--sysroot=' + str(runner.sysroot), *objects, '-o', elf,
                '-Wl,--trace', check=False)
            if linked.returncode:
                failures.append('link: ' + linked.stdout[-1800:])
            else:
                runner.t2_abi(elf, linked.stdout)
                symbols = runner.command(runner.tool('readelf'), '--dyn-syms', '--wide', elf)
                for name in ('printf', 'snprintf', 'vsnprintf'):
                    if not re.search(r'\bUND\s+' + name + r'@', symbols):
                        failures.append('missing libc varargs reference ' + name)
        runner.result('t2 varargs ' + ('donor caller / GCC16 callee' if donor_caller
                                       else 'GCC16 caller / donor callee'), failures)
