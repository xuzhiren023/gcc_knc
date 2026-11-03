"""S2-05 T1: python tools/check.py t1 --compiler gcc16 --x87-spill.

Check signaling/quiet instruction families and exercise unchanged emitted
x87/integer instructions using a SysV host driver. This is host T1 validation,
not native KNC validation. The C fixture also supplies the eventual card table.
The donor is a missing-compare sanity check and an expected-red invalid-flag
table: its legacy quiet relational compares must not dictate GCC 16 semantics.
Simulate XI spill addresses for all four possible 16-byte incoming alignments;
do not add -mstackrealign or an aligned local that could mask a backend defect.
"""
import re
import sys

from scalar_abi import allowlist, instructions


FORMS = ('eq ne lt le gt ge isless islessequal isgreater isgreaterequal '
         'islessgreater isunordered isordered unlt unle ungt unge').split()
SIGNALING = ('lt', 'le', 'gt', 'ge', 'unlt', 'unle', 'ungt', 'unge')
COMPARE = re.compile(r'^(?:fu?com)(?:p{0,2}|p?[sl])$')


def allowed(body):
    # Scalar memory compare suffixes are valid x87, absent from the ABI probes.
    return allowlist('\n'.join(line for line in body.splitlines()
                              if not re.match(r'\s*fcomp?[sl]\b', line)))


def compare_scan(body, donor, form):
    failures = allowed(body)
    actual = [op for op, _ in instructions(body) if COMPARE.fullmatch(op)]
    reference = [op for op, _ in instructions(donor) if COMPARE.fullmatch(op)]
    if not actual or not reference:
        failures.append('missing x87 compare (actual=%s donor=%s)' % (actual, reference))
    # C Annex F relational operators signal invalid even on quiet NaNs;
    # negating their boolean result does not change that exception behavior.
    if form in SIGNALING:
        if not actual or any(not op.startswith('fcom') for op in actual):
            failures.append('signaling comparison requires fcom family')
    else:
        if not actual or any(not op.startswith('fucom') for op in actual):
            failures.append('quiet comparison requires fucom family')
    if not any(op == 'fnstsw' for op, _ in instructions(body)):
        failures.append('missing x87 status-word extraction')
    return failures


def spill_scan(body, high):
    failures = allowed(body)
    if not re.search(r'# xi-high\s+%zmm' + str(high) + r'\b', body):
        failures.append('missing forced zmm%d definition' % high)
    if not re.search(r'\bcall\s+spill_clobber(?:@PLT)?\b', body):
        failures.append('missing spill-forcing call')
    # Absolute representatives let us also check restoration of the entry RSP.
    # CALL pushes 8 bytes: entry RSP residues are 8,24,40,56 for callers whose
    # stack has only the SysV 16-byte guarantee.
    for residue in (8, 24, 40, 56):
        entry = 0x1000 + residue
        addresses, stores, loads, called = {'rsp': entry}, set(), set(), False
        returned = False
        for op, args in instructions(body):
            if op == 'call':
                called = True
                # Only callee-saved address registers survive the call.
                addresses = {r: v for r, v in addresses.items()
                             if r in ('rsp', 'rbp', 'rbx', 'r12', 'r13', 'r14', 'r15')}
            if op in ('vmovaps', 'vmovapd', 'vmovdqa32', 'vmovdqa64'):
                memory = re.search(r'(-?\d*)\(%(\w+)\)', args)
                if memory and memory[2] in addresses:
                    address = addresses[memory[2]] + int(memory[1] or 0)
                    if address % 64:
                        failures.append('entry rsp%%%d= %d: unaligned XI access: %s' %
                                        (64, residue, args))
                    if args.lstrip().startswith('%zmm') and not called:
                        stores.add(address)
                    elif not args.lstrip().startswith('%zmm') and called:
                        loads.add(address)
                elif memory and memory[2] in ('rsp', 'rbp'):
                    failures.append('unknown stack address: ' + args)
            if op == 'pushq':
                addresses['rsp'] -= 8
                continue
            if op == 'popq':
                addresses['rsp'] += 8
                addresses.pop(args.lstrip('%'), None)
                continue
            if op in ('leave', 'leaveq'):
                if 'rbp' not in addresses:
                    failures.append('unknown frame at leave')
                else:
                    addresses['rsp'] = addresses['rbp'] + 8
                addresses.pop('rbp', None)
                continue
            if op in ('ret', 'retq'):
                returned = True
                if addresses.get('rsp') != entry:
                    failures.append('entry stack pointer not restored')
            dest = re.search(r',\s*%(\w+)\s*$', args)
            if not dest or dest[1].startswith(('zmm', 'k', 'st')):
                continue
            reg = dest[1]
            source = args.split(',', 1)[0].strip()
            copy = re.fullmatch(r'%(\w+)', source)
            memory = re.fullmatch(r'(-?\d*)\(%(\w+)\)', source)
            immediate = re.fullmatch(r'\$(-?\d+)', source)
            value = None
            if op == 'movq' and copy:
                value = addresses.get(copy[1])
            elif op == 'leaq' and memory and memory[2] in addresses:
                value = addresses[memory[2]] + int(memory[1] or 0)
            elif immediate and reg in addresses:
                old, amount = addresses[reg], int(immediate[1])
                if op == 'andq':
                    value = old & amount
                elif op == 'subq':
                    value = old - amount
                elif op == 'addq':
                    value = old + amount
            # CMP/TEST do not modify their register operand.
            if op.startswith(('cmp', 'test')):
                continue
            if value is None:
                addresses.pop(reg, None)
            else:
                addresses[reg] = value
        if not stores.intersection(loads):
            failures.append('no full-width stack store/reload pair across call')
        if not returned:
            failures.append('missing return')
    return sorted(set(failures))


def assemble(runner, asm):
    obj = asm.with_suffix('.o')
    result = runner.command(runner.tool('as'), '--march=k1om', asm, '-o', obj, check=False)
    if result.returncode:
        return ['KNC assembler: ' + result.stdout[-1500:]]
    lint = runner.command(sys.executable, runner.root / 'tools/knc_lint', asm, obj, check=False)
    return ['lint: ' + lint.stdout[-1500:]] if lint.returncode else []


def host_table(runner, asm, source, tag):
    # PE gas cannot read ELF metadata directives. Strip only those directives
    # and map ELF text subsections to .text. Every instruction, operand and
    # branch label remains exactly as emitted.
    host_asm = runner.out / 'compare-host.s'
    lines = []
    for line in asm.read_text().splitlines():
        if re.match(r'\s*\.(?:type|size)\b|\s*\.section\s+\.note\.GNU-stack', line):
            continue
        lines.append('\t.text' if re.match(r'\s*\.section\s+\.text\b', line) else line)
    host_asm.write_text('\n'.join(lines) + '\n')
    executable = runner.out / 'compare-host.exe'
    build = runner.command(runner.tc / 'cygwin/bin/gcc.exe', '-O2',
        '-DCOMPARE_DRIVER', source, host_asm, '-o', executable, check=False)
    if build.returncode:
        runner.result('t1 ' + tag + ' host table infrastructure', [build.stdout[-2000:]])
        return
    result = runner.command(executable, check=False)
    runner.say('Host x87 table (' + tag + ', not a card result):\n' + result.stdout)
    if tag == 'donor':
        # Require exactly the known legacy defect, not an arbitrary failed run.
        expected = {(mode, form, str(i), str(j))
                    for mode in ('sf', 'df', 'xf') for form in SIGNALING
                    for i in range(7) for j in range(7) if i == 0 or j == 0}
        observed, unexpected = set(), []
        for line in result.stdout.splitlines():
            match = re.fullmatch(r'FAIL (sf|df|xf) (\w+) ([0-6]) ([0-6]) '
                                 r'got=([01]) expected=([01]) invalid=0 expected_invalid=1', line)
            if match and match[5] == match[6]:
                observed.add(match.group(1, 2, 3, 4))
            elif line not in ('TABLE %s checks=833 failures=104' % mode
                              for mode in ('sf', 'df', 'xf')):
                unexpected.append(line)
        failures = [] if result.returncode == 1 and observed == expected and not unexpected else [
            'donor did not fail solely for missing signaling invalid flags']
        runner.result('t1 donor reported expected-red: 312 missing signaling invalid flags', failures)
        return
    runner.result('t1 ' + tag + ' host emitted-code IEEE results / invalid flag',
                  [] if result.returncode == 0 else ['table exit ' + str(result.returncode)])


def t1(runner):
    source = runner.source_dir / 'knc-x87-compare.c'
    output = runner.root.parent / '_shared/tmp/S2-05'
    output.mkdir(parents=True, exist_ok=True)
    assemblies = {}
    for tag, cc, flags in (('donor', runner.tool('gcc'), []),
                           ('gcc16', runner.cc, runner.cc_flags)):
        asm = output / ('compare-' + tag + '.s')
        result = runner.command(cc, *flags, '-O2', '-march=knc',
            '-fno-fast-math', '-fno-tree-vectorize', '-ffp-contract=off',
            '-S', source, '-o', asm, check=False)
        if result.returncode:
            runner.result('t1 ' + tag + ' comparisons compile', [result.stdout[-1800:]])
            continue
        assemblies[tag] = asm.read_text()
        runner.result('t1 ' + tag + ' comparison ISA', allowed(assemblies[tag]) + assemble(runner, asm))
        host_table(runner, asm, source, tag)
    if 'donor' in assemblies and 'gcc16' in assemblies:
        for mode in ('sf', 'df', 'xf'):
            for form in FORMS:
                name = 'cmp_' + mode + '_' + form
                body, donor = (runner.function_body(assemblies[t], name)
                               for t in ('gcc16', 'donor'))
                runner.result('t1 ' + name + ' signaling/quiet family / status (donor presence)',
                    compare_scan(body, donor, form) if body and donor else ['missing function'])
    for high in (16, 31):
        asm = output / ('xi-spill-zmm%d.s' % high)
        result = runner.command(runner.cc, *runner.cc_flags, '-O2', '-march=knc',
            '-mincoming-stack-boundary=4', '-mpreferred-stack-boundary=4',
            '-fno-tree-vectorize', '-DHIGH_REG="zmm%d"' % high,
            '-S', runner.source_dir / 'knc-xi-spill.c',
            '-o', asm, check=False)
        failures = []
        if result.returncode:
            failures.append('compile: ' + result.stdout[-1800:])
        else:
            body = runner.function_body(asm.read_text(), 'xi_spill')
            failures.extend(spill_scan(body, high) if body else ['missing function'])
            failures.extend(assemble(runner, asm))
        runner.result('t1 XI zmm%d spill / all 16-byte incoming alignments' % high, failures)
