"""S2-04 T1 checks; run tools/check.py t1 --compiler gcc16 --secondary-reload.

The Fortran dump check is exactly the symptom documented in its header, not
an assertion that GCC 16 uses the donor's secondary-store mechanism. The C
probe forces register-bank reloads, with 14 GPRs live and one scratch free.
Native validation is separate: PRESSURE_MAIN prints integer bit results for
comparison with the host reference, through tools/card_run once available.
"""
import re
import sys

from scalar_abi import allowlist, instructions


def lost_addresses(dump):
    lines = dump.splitlines()
    failures = []
    for index, line in enumerate(lines):
        deleted = re.search(r'Deleting move\s+(\d+)', line)
        if not deleted:
            continue
        for before in lines[max(0, index - 14):index]:
            created = re.search(r'Creating newreg=(\d+) from oldreg=(\d+).*to address r\1\b', before)
            if not created:
                continue
            new, old = created.groups()
            # LRA prints the short rN:MODE form in its transformation trace.
            copy = r'\br' + new + r':(\w+)=r' + old + r':\1\b'
            if not re.search(copy, dump):
                failures.append('deleted move %s lost address r%s <- r%s' %
                                (deleted[1], new, old))
    return failures


def gpr(reg):
    for stem, full in (('a', 'rax'), ('b', 'rbx'), ('c', 'rcx'), ('d', 'rdx')):
        if reg in (full, 'e' + stem + 'x', stem + 'x', stem + 'l', stem + 'h'):
            return full
    for stem in ('si', 'di', 'bp', 'sp'):
        if reg in ('r' + stem, 'e' + stem, stem, stem + 'l'):
            return 'r' + stem
    return re.sub(r'^(r\d+)[dwb]$', r'\1', reg)


def gpr_writes(op, args):
    """Explicit and implicit destinations in the probe's scalar allowlist."""
    if op.startswith(('cmp', 'test', 'push', 'j')):
        return set()
    regs = re.findall(r'%(\w+)', args)
    dest = re.search(r'(?:^|,)\s*%(\w+)\s*$', args)
    written = {gpr(dest[1])} if dest else set()
    if op.startswith('xchg'):
        written.update(map(gpr, regs))
    if op in ('cltq', 'cwtl'):
        written.add('rax')
    if op in ('cqto', 'cltd'):
        written.add('rdx')
    if re.fullmatch(r'(?:i?div|mul)[bwlq]?|imul[bwlq]?', op) and ',' not in args:
        written.update(('rax', 'rdx'))
    if op == 'fnstsw' and not args:
        written.add('rax')
    if op == 'call':
        written.update(('rax', 'rcx', 'rdx', 'rsi', 'rdi', 'r8', 'r9', 'r10', 'r11'))
    return written


def pressure_scan(body, live=True, mask_value=1):
    failures = allowlist(body)
    markers = re.findall(r'# pressure-live([^\n]*)', body)
    expected = {'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp',
                *('r' + str(i) for i in range(8, 15))}
    if live and (len(markers) != 2 or any(len(re.findall(r'%(\w+)', m)) != 14 or
                              set(re.findall(r'%(\w+)', m)) != expected for m in markers)):
        failures.append('missing both barriers with 14 GPRs live and r15 free')
    regions = re.split(r'# pressure-live[^\n]*', body)
    if len(regions) == 3:
        region_writes = set()
        for op, args in instructions(regions[1]):
            written = gpr_writes(op, args)
            for reg in sorted(written & expected):
                failures.append('write to live GPR ' + reg + ': ' + op + ' ' + args)
            # Preamble values in live GPRs are not transfer addresses. Only
            # rsp or the free r15, set within these barriers, can address spills.
            if re.search(r'%zmm\d+', args):
                for address in re.findall(r'\(([^)]*)\)', args):
                    for reg in re.findall(r'%(\w+)', address):
                        if reg != 'rsp' and (reg != 'r15' or reg not in region_writes):
                            failures.append('invalid pressure transfer address: ' + reg)
            region_writes.update(written)
    masks, values = {}, {}
    transfers = 0
    for op, args in instructions(body):
        # This probe is straight-line; require an explicit reaching mask-one
        # definition and initialized address registers at each memory transfer.
        if re.search(r'%zmm\d+', args):
            if re.match(r'%(?:r\w+|e\w+),\s*%zmm\d+\s*$', args):
                failures.append('direct GPR-to-zmm transfer: ' + op + ' ' + args)
            if re.match(r'%zmm\d+,\s*%(?:r\w+|e\w+)\s*$', args):
                failures.append('direct zmm-to-GPR transfer: ' + op + ' ' + args)
            if '(' in args:
                transfers += 1
                for address in re.findall(r'\(([^)]*)\)', args):
                    for reg in re.findall(r'%(\w+)', address):
                        if reg not in ('rsp', 'rbp') and reg not in values:
                            failures.append('uninitialized transfer address: ' + reg)
                if op.startswith(('vpackstore', 'vloadunpack')):
                    mask = re.search(r'\{%?(k\d+)\}', args)
                    if not mask or masks.get(mask[1]) != mask_value:
                        failures.append('transfer without reaching mask-%d setup: %s' %
                                        (mask_value, args))
        dest = re.search(r',\s*%(\w+)\s*$', args)
        if not dest:
            continue
        reg = dest[1]
        canonical = gpr(reg)
        if op == 'kmov' and reg.startswith('k'):
            source = re.match(r'%(\w+),', args)
            source = source[1] if source else ''
            source = gpr(source)
            masks[reg] = values.get(source)
        elif not reg.startswith(('zmm', 'k', 'st')):
            immediate = re.match(r'\$(\d+),', args)
            values[canonical] = int(immediate[1]) if immediate and op.startswith('mov') else None
    if transfers < 2:
        failures.append('missing memory bridge in both directions')
    return sorted(set(failures))


def t1(runner):
    source = runner.root / 'tests/regress/knc-secondary-reload.f90'
    asm = runner.out / 'secondary-fortran.s'
    # Use the language driver as well as f951: a C-only xgcc does not accept
    # Fortran options such as -J, even with -x f95.
    compiler, flags = ((runner.cc.with_name('gfortran'), runner.cc_flags) if runner.args.compiler == 'gcc16'
                       else (runner.tool('gfortran'), []))
    if not compiler.exists() and not compiler.with_suffix('.exe').exists():
        runner.result('t1 secondary Fortran infrastructure',
                      ['missing Fortran driver: ' + str(compiler)])
    else:
        compiled = runner.command(compiler, *flags, '-w', '-ffree-form',
            '-ffree-line-length-none', '-fconvert=big-endian', '-frecord-marker=4',
            '-std=legacy', '-O1', '-march=knc', '-fno-tree-vectorize', '-J' + str(runner.out),
            '-S', '-fdump-rtl-reload', source, '-o', asm, check=False)
        if compiled.returncode:
            runner.result('t1 secondary Fortran compile', [compiled.stdout[-2200:]])
        else:
            dumps = list(runner.out.glob('*reload'))
            failures = [] if dumps else ['missing reload dump']
            for dump in dumps:
                failures.extend(lost_addresses(dump.read_text()))
            runner.result('t1 secondary Fortran deleted-store address setups', failures)

    # The donor has different register constraints. It calibrates only the
    # preserved Fortran symptom; the new C reload probes target GCC 16.
    if runner.args.compiler != 'gcc16':
        return

    source = runner.root / 'tests/regress/knc-secondary-pressure.c'
    for level, number, mode in ((level, number, mode)
                               for level in ('-O1', '-O2')
                               for number, mode in enumerate(('si', 'di', 'sf', 'df',
                                   'sf_u32', 'u32_sf', 'df_u64', 'u64_df', 'ti', 'tf'), 1)):
        asm = runner.out / 'secondary-pressure.s'
        compiled = runner.command(runner.cc, *runner.cc_flags, level, '-march=knc',
            '-fomit-frame-pointer', '-fno-tree-vectorize', '-ffp-contract=off',
            '-DPRESSURE_MODE=' + str(number), '-S', source, '-o', asm, check=False)
        failures = []
        if compiled.returncode:
            failures.append('compile: ' + compiled.stdout[-2200:])
        else:
            assembly = asm.read_text()
            body = runner.function_body(assembly, 'pressure_' + mode)
            failures.extend(pressure_scan(body, live=number <= 8,
                                          mask_value=3 if number > 8 else 1)
                            if body else ['missing function'])
            assembled = runner.command(runner.tool('as'), '--march=k1om', asm,
                                       '-o', asm.with_suffix('.o'), check=False)
            if assembled.returncode:
                failures.append('assembler: ' + assembled.stdout[-1500:])
            else:
                lint = runner.command(sys.executable, runner.root / 'tools/knc_lint',
                                      asm, asm.with_suffix('.o'), check=False)
                if lint.returncode:
                    failures.append('lint: ' + lint.stdout[-1500:])
        runner.result('t1 secondary mixed pressure ' + level + ' ' + mode, failures)


def t2(runner):
    """Link the native probe and measure its host reference; no card execution."""
    source = runner.root / 'tests/regress/knc-secondary-pressure.c'
    flags = ['-O2', '-fomit-frame-pointer', '-fno-tree-vectorize',
             '-ffp-contract=off', '-DPRESSURE_MAIN']
    out = runner.tc.parent / 'tmp/S2-04'
    out.mkdir(parents=True, exist_ok=True)
    host = out / 'secondary-host.exe'
    compiled = runner.command(runner.tc / 'cygwin/bin/gcc.exe', *flags,
                              source, '-o', host, check=False)
    failures = []
    if compiled.returncode:
        failures.append('host compile: ' + compiled.stdout[-1800:])
    else:
        reference = runner.command(host, check=False)
        (out / 'host-reference.txt').write_text(reference.stdout)
        runner.say('secondary host reference:\n' + reference.stdout)
        if reference.returncode:
            failures.append('host reference exit ' + str(reference.returncode))
    runner.result('t2 secondary host reference (not a card result)', failures)

    elf = out / 'secondary-pressure.mic'
    linked = runner.command(runner.cc, *runner.cc_flags, *flags, '-march=knc',
        '--sysroot=' + str(runner.sysroot),
        source, '-o', elf, '-Wl,--trace', check=False)
    if linked.returncode:
        runner.result('t2 secondary mixed pressure link',
                      ['link: ' + linked.stdout[-1800:]])
    else:
        runner.t2_abi(elf, linked.stdout)
        runner.result('t2 secondary mixed pressure link', [])
    host.unlink(missing_ok=True)
    runner.say('Native comparison pending: ' + str(elf)
               + ' against ' + str(out / 'host-reference.txt')
               + ' through tools/card_run after the owner releases the card hold.')
