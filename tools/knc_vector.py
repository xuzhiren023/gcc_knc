"""S3 packed probes, selected with tools/check --vector.

Each operation is a separate compilation: a failure cannot hide later probes.
Native value checks belong to S3-10, not this host-only T1 selection.
"""
import re
import sys

from scalar_abi import allowlist, instructions

MODES = {'v16sf': 'vmovaps', 'v8df': 'vmovapd',
         'v16si': 'vmovdqa32', 'v8di': 'vmovdqa64'}
CASES = ('copy', 'live', 'zero', 'pool', 'arg', 'result', 'member',
         'large_member', 'pressure', 'regcopy')
MOVES = frozenset(MODES.values())


def spill_scan(body, minimum):
    failures = []
    if not re.search(r'\bcall\s+packed_clobber(?:@PLT)?\b', body):
        failures.append('missing ordinary spill-forcing call')
    # A 16-byte-aligned caller gives these four incoming RSP residues.
    for residue in (8, 24, 40, 56):
        addresses = {'rsp': 0x1000 + residue}
        stores, loads, all_loads = set(), set(), set()
        called = False
        for op, args in instructions(body):
            if op == 'call':
                called = True
                addresses = {r: v for r, v in addresses.items()
                             if r in ('rsp', 'rbp', 'rbx', 'r12', 'r13', 'r14', 'r15')}
            if op in MOVES:
                memory = re.search(r'(-?\d*)\(%(\w+)\)', args)
                if memory:
                    if memory[2] not in addresses:
                        if memory[2] in ('rsp', 'rbp'):
                            failures.append('unknown spill address: ' + args)
                    else:
                        slot = addresses[memory[2]] + int(memory[1] or 0)
                        if slot % 64:
                            failures.append('unaligned packed stack access: ' + args)
                        if args.startswith('%zmm') and not called:
                            stores.add(slot)
                        elif not args.startswith('%zmm'):
                            all_loads.add(slot)
                            if called:
                                loads.add(slot)
            if op == 'pushq':
                addresses['rsp'] -= 8
                continue
            if op == 'popq':
                addresses['rsp'] += 8
                addresses.pop(args.lstrip('%'), None)
                continue
            if op in ('leave', 'leaveq'):
                if 'rbp' in addresses:
                    addresses['rsp'] = addresses['rbp'] + 8
                else:
                    failures.append('unknown frame at leave')
                addresses.pop('rbp', None)
                continue
            dest = re.search(r',\s*%(\w+)\s*$', args)
            if not dest or dest[1].startswith(('zmm', 'k', 'st')):
                continue
            if op.startswith(('cmp', 'test')):
                continue
            reg = dest[1]
            source = args.split(',', 1)[0].strip()
            copy = re.fullmatch(r'%(\w+)', source)
            mem = re.fullmatch(r'(-?\d*)\(%(\w+)\)', source)
            imm = re.fullmatch(r'\$(-?\d+)', source)
            value = None
            if op == 'movq' and copy:
                value = addresses.get(copy[1])
            elif op == 'leaq' and mem and mem[2] in addresses:
                value = addresses[mem[2]] + int(mem[1] or 0)
            elif imm and reg in addresses:
                old, amount = addresses[reg], int(imm[1])
                if op == 'andq':
                    value = old & amount
                elif op == 'subq':
                    value = old - amount
                elif op == 'addq':
                    value = old + amount
            if value is None:
                addresses.pop(reg, None)
            else:
                addresses[reg] = value
        if len(stores & loads) < minimum:
            failures.append('fewer than %d distinct spill/reload slots across call' % minimum)
        if stores - all_loads:
            failures.append('packed stack store without reload')
    return sorted(set(failures))


def scan(assembly, case, move, body):
    # Extend the S2 allowlist with only the ADR-0005 zero idiom.
    failures = allowlist('\n'.join(line for line in assembly.splitlines()
                                   if not re.match(r'\s*vpxord\b', line)))
    if re.search(r'%(?:xmm|ymm)\d|\bvmovups\b|\{z\}', assembly):
        failures.append('forbidden SSE/AVX or zero-mask form')
    if not body:
        return failures + ['missing packed_' + case]
    if case == 'zero':
        if not re.search(r'\bvpxord\s+(%zmm\d+),\s*\1,\s*\1', body):
            failures.append('zero must use vpxord')
    elif case == 'pool':
        reference = re.search(r'\bvmovaps\s+(\.LC\d+)\(%rip\),\s*%zmm\d+', body)
        if not reference:
            failures.append('nonzero constant must load with vmovaps from pool')
        elif not re.search(r'\.(?:align\s+64|balign\s+64|p2align\s+6)[^\n]*\n\s*'
                           + re.escape(reference[1]) + ':', assembly):
            failures.append('constant pool entry is not explicitly 64-byte aligned')
    elif not re.search(r'\b' + move + r'\b', body):
        failures.append('missing aligned ' + move)
    if case in ('live', 'pressure'):
        failures += spill_scan(body, 32 if case == 'pressure' else 1)
    return failures


def t1(runner):
    sources = sorted(runner.source_dir.glob('knc-vec-*.c'))
    fixtures = {runner.source_dir / ('knc-vec-' + mode + '.c') for mode in MODES}
    runner.t1_sources([source for source in sources if source not in fixtures])
    t1_packed(runner)
    t1_unaligned(runner)


UNALIGNED_CASES = ('unknown', 'unknown_load', 'unknown_store', 'under_member',
                   'unknown_live')
PAIR_SUFFIX = dict(zip(MODES, ('ps', 'pd', 'd', 'q')))
PAIRS = frozenset(prefix + half + suffix
                  for prefix in ('vloadunpack', 'vpackstore')
                  for half in ('l', 'h') for suffix in PAIR_SUFFIX.values())


def scan_unaligned(assembly, case, mode, body):
    # Keep the S2 allowlist, adding exactly the full-width pair instructions.
    failures = allowlist('\n'.join(line for line in assembly.splitlines()
                                   if not re.match(r'\s*(?:' + '|'.join(PAIRS)
                                                   + r')\b', line)))
    if re.search(r'%(?:xmm|ymm)\d|\bvmovups\b|\{z\}', assembly):
        failures.append('forbidden SSE/AVX or zero-mask form')
    if not body:
        return failures + ['missing packed_' + case]
    ops = list(instructions(body))
    suffix = PAIR_SUFFIX[mode]
    for direction, needed in (('load', case != 'unknown_store'),
                              ('store', case != 'unknown_load')):
        prefix = 'vloadunpack' if direction == 'load' else 'vpackstore'
        halves = []
        for half in ('l', 'h'):
            matches = [args for op, args in ops if op == prefix + half + suffix]
            if len(matches) != int(needed):
                failures.append('%s %s: expected %d %s half, got %d' %
                                (mode, direction, int(needed), half, len(matches)))
            halves.append(matches)
        if not needed or any(len(matches) != 1 for matches in halves):
            continue
        decoded = []
        for matches in halves:
            args = matches[0]
            pattern = (r'(-?\d*)\(([^)]+)\),\s*(%zmm\d+)' if direction == 'load'
                       else r'(%zmm\d+),\s*(-?\d*)\(([^)]+)\)')
            match = re.fullmatch(pattern, args)
            if not match:
                failures.append('unexpected pair operands or mask: ' + args)
                break
            displacement, base, reg = (match.groups() if direction == 'load'
                                        else (match[2], match[3], match[1]))
            if re.search(r'%(?:rsp|rbp)\b', base):
                failures.append('packed spill/reload must not use a pair: ' + args)
            decoded.append((int(displacement or 0), base, reg))
        if len(decoded) == 2:
            low, high = decoded
            if high != (low[0] + 64, low[1], low[2]):
                failures.append(direction + ': high must use low address + 64 and same zmm')
            if ops.index((prefix + 'l' + suffix, halves[0][0])) > ops.index(
                    (prefix + 'h' + suffix, halves[1][0])):
                failures.append(direction + ': high precedes low')
    expected = {prefix + half + suffix for prefix in ('vloadunpack', 'vpackstore')
                for half in ('l', 'h')}
    if any(op in PAIRS and op not in expected for op, args in ops):
        failures.append('pair uses the wrong element form')
    if case in ('unknown_load', 'unknown_store'):
        # The other pointer still has the original vector's known alignment.
        move = MODES[mode]
        known = (r'%zmm\d+,\s*-?\d*\(([^)]+)\)' if case == 'unknown_load'
                 else r'-?\d*\(([^)]+)\),\s*%zmm\d+')
        accesses = [re.fullmatch(known, args) for op, args in ops if op == move]
        if not any(match and not re.search(r'%(?:rsp|rbp)\b', match[1])
                   for match in accesses):
            failures.append('known-aligned side must use ' + move)
    if case == 'unknown_live':
        failures += spill_scan(body, 1)
    return failures


def t1_unaligned(runner):
    for mode in MODES:
        source = runner.source_dir / ('knc-vec-' + mode + '.c')
        for level in ('-O0', '-O2'):
            for number, case in enumerate(UNALIGNED_CASES, 11):
                label = 't1 unaligned %s %s %s' % (mode, level, case)
                asm = runner.out / (mode + '.s')
                obj = runner.out / (mode + '.o')
                try:
                    result = runner.command(runner.cc, *runner.cc_flags, level,
                                            '-march=knc', '-DCASE=' + str(number),
                                            '--sysroot=' + str(runner.sysroot),
                                            '-S', source, '-o', asm, check=False)
                    if result.returncode:
                        failures = ['compile exited %d: %s' %
                                    (result.returncode, result.stdout[-1600:])]
                    else:
                        assembly = asm.read_text()
                        failures = scan_unaligned(assembly, case, mode,
                            runner.function_body(assembly, 'packed_' + case))
                        runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj)
                        runner.command(sys.executable, runner.root / 'tools/knc_lint', asm, obj)
                    runner.result(label, failures)
                except (OSError, RuntimeError, ValueError) as error:
                    runner.result(label, [str(error)])


def t1_packed(runner):
    for mode, move in MODES.items():
        source = runner.source_dir / ('knc-vec-' + mode + '.c')
        for level in ('-O0', '-O2'):
            for number, case in enumerate(CASES, 1):
                label = 't1 packed %s %s %s' % (mode, level, case)
                asm = runner.out / (mode + '.s')
                obj = runner.out / (mode + '.o')
                dump = runner.out / (mode + '.expand')
                try:
                    result = runner.command(runner.cc, *runner.cc_flags, level,
                                            '-march=knc', '-DCASE=' + str(number),
                                            '-fdump-rtl-expand=' + str(dump),
                                            '--sysroot=' + str(runner.sysroot),
                                            '-S', source, '-o', asm, check=False)
                    if case in ('arg', 'result', 'member', 'large_member'):
                        failures = [] if result.returncode and re.search(
                            'unsupported KNC register ABI mode', result.stdout) and not re.search(
                                'internal compiler error|Segmentation fault', result.stdout) else [
                                'missing unsupported KNC register ABI mode diagnostic']
                    elif result.returncode:
                        failures = ['compile exited %d: %s' % (result.returncode, result.stdout[-1600:])]
                    else:
                        assembly = asm.read_text()
                        failures = scan(assembly, case, move,
                                        runner.function_body(assembly, 'packed_' + case))
                        if not re.search(r'\(reg:' + mode.upper() + r'\b', dump.read_text()):
                            failures.append('missing legal packed register mode ' + mode.upper())
                        if case == 'regcopy' and not re.search(
                                r'\b' + move + r'\s+%zmm0,\s*%zmm31', assembly):
                            failures.append('missing packed zmm0 to zmm31 register copy')
                        runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj)
                        runner.command(sys.executable, runner.root / 'tools/knc_lint', asm, obj)
                    runner.result(label, failures)
                except (OSError, RuntimeError, ValueError) as error:
                    runner.result(label, [str(error)])
