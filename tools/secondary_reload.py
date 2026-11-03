"""S2-04 T1 checks; run tools/check.py t1 --compiler gcc16 --secondary-reload.

The Fortran dump check is exactly the symptom documented in its header, not
an assertion that GCC 16 uses the donor's secondary-store mechanism. The C
probe forces register-bank reloads, with all 15 GPRs live across the moves.
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


def pressure_scan(body):
    failures = allowlist(body)
    markers = re.findall(r'# pressure-live([^\n]*)', body)
    expected = {'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp',
                *('r' + str(i) for i in range(8, 16))}
    if len(markers) != 2 or any(set(re.findall(r'%(\w+)', m)) != expected for m in markers):
        failures.append('missing both barriers with all 15 GPRs live')
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
                if op.startswith('vpackstore'):
                    mask = re.search(r'\{%?(k\d+)\}', args)
                    if not mask or masks.get(mask[1]) != 1:
                        failures.append('store without reaching mask-one setup: ' + args)
        dest = re.search(r',\s*%(\w+)\s*$', args)
        if not dest:
            continue
        reg = dest[1]
        canonical = {'eax': 'rax', 'ebx': 'rbx', 'ecx': 'rcx', 'edx': 'rdx',
                     'esi': 'rsi', 'edi': 'rdi', 'ebp': 'rbp'}.get(reg, re.sub(r'^(r\d+)[dwb]$', r'\1', reg))
        if op == 'kmov' and reg.startswith('k'):
            source = re.match(r'%(\w+),', args)
            source = source[1] if source else ''
            source = {'eax': 'rax', 'ebx': 'rbx', 'ecx': 'rcx', 'edx': 'rdx',
                      'esi': 'rsi', 'edi': 'rdi'}.get(source, re.sub(r'^(r\d+)[dwb]$', r'\1', source))
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
    for level in ('-O1', '-O2'):
        asm = runner.out / 'secondary-pressure.s'
        compiled = runner.command(runner.cc, *runner.cc_flags, level, '-march=knc',
            '-fomit-frame-pointer', '-fno-tree-vectorize', '-ffp-contract=off',
            '-S', source, '-o', asm, check=False)
        failures = []
        if compiled.returncode:
            failures.append('compile: ' + compiled.stdout[-2200:])
        else:
            assembly = asm.read_text()
            for mode in ('si', 'di', 'sf', 'df'):
                body = runner.function_body(assembly, 'pressure_' + mode)
                failures.extend(mode + ': ' + f for f in
                                (pressure_scan(body) if body else ['missing function']))
            assembled = runner.command(runner.tool('as'), '--march=k1om', asm,
                                       '-o', asm.with_suffix('.o'), check=False)
            if assembled.returncode:
                failures.append('assembler: ' + assembled.stdout[-1500:])
            else:
                lint = runner.command(sys.executable, runner.root / 'tools/knc_lint',
                                      asm, asm.with_suffix('.o'), check=False)
                if lint.returncode:
                    failures.append('lint: ' + lint.stdout[-1500:])
        runner.result('t1 secondary mixed pressure ' + level, failures)
