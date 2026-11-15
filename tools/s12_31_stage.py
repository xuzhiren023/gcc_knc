#!/usr/bin/env python3
"""Host-only S12-31 staging: HPCG sparse kernels built several ways and an
executed-padding microbench, linked into one single-core card diagnostic."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

import corpus

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
OUT = SHARED / 'S12-31'
TC = SHARED / 'toolchain'
HPCG = SHARED / 'corpus-build/sources/hpcg-3.1/src'
REAL = SHARED / 'S11-28'
KERNELS = {
    'spmv': ('ComputeSPMV_ref', '_Z15ComputeSPMV_refRK19SparseMatrix_STRUCTR13Vector_STRUCTS3_'),
    'symgs': ('ComputeSYMGS_ref', '_Z16ComputeSYMGS_refRK19SparseMatrix_STRUCTRK13Vector_STRUCTRS2_')}
# name, donor compiler, extra flags, re-encode NOPs without slow prefixes
VARIANTS = [
    ('donor', True, [], False),
    ('donor_pf', True, [], True),
    ('knc', False, [], False),
    ('knc_pf', False, [], True),
    ('knc_noalign', False, ['-fno-align-loops'], False),
    ('knc_skip7', False, ['-falign-loops=16:8:8'], False),
    ('knc_nosched', False, ['-fno-schedule-insns2'], False),
    ('knc_nosched_noalign', False, ['-fno-schedule-insns2', '-fno-align-loops'], False)]
# Prefixes outside the decoder's fast set (R02 p.56): operand and address
# size, segment, lock and rep.
SLOW = {0x66, 0x67, 0x26, 0x2e, 0x36, 0x3e, 0x64, 0x65, 0xf0, 0xf2, 0xf3}
PLAIN = {1: '90', 3: '0f 1f 00', 4: '0f 1f 40 00', 5: '0f 1f 44 00 00',
         7: '0f 1f 80 00 00 00 00', 8: '0f 1f 84 00 00 00 00 00'}
SPLIT = {2: (1, 1), 6: (3, 3), 9: (5, 4), 10: (5, 5), 11: (7, 4), 12: (8, 4),
         13: (8, 5), 14: (7, 7), 15: (8, 7)}
MIS = list(range(4, 64, 4))
LOOP = ['movslq\t(%r8,%rax,4), %r10', 'fldl\t(%rdx,%r10,8)', 'fmull\t(%rcx,%rax,8)',
        'addq\t$1, %rax', 'cmpl\t%eax, %esi', 'faddp\t%st, %st(1)']
HOST = False


def tool(name):
    return name if HOST else TC / 'cross/bin' / ('k1om-mpss-linux-' + name)


def run(*argv, capture=False):
    print('+', ' '.join(map(str, argv)), flush=True)
    done = subprocess.run(list(map(str, argv)), check=True, text=True,
                          stdout=subprocess.PIPE if capture else None)
    return done.stdout


def cxx(donor):
    return 'g++' if HOST else corpus.compiler_path(corpus.DONOR if donor else corpus.KNC, 'g++')


def instructions(path):
    """(address, bytes, text) for every instruction in .text."""
    result = []
    for line in run(tool('objdump'), '-d', '--insn-width=16', '-j', '.text', path, capture=True).splitlines():
        match = re.match(r'\s*([0-9a-f]+):\t((?:[0-9a-f]{2} )+)\s*(?:\t(.*))?$', line)
        if match:
            result.append((int(match.group(1), 16), bytes.fromhex(match.group(2)), match.group(3) or ''))
    return result


def slow_nops(path):
    """(address, length, slow prefixes) for each NOP carrying a slow prefix."""
    result = []
    for address, code, _ in instructions(path):
        rest = code.lstrip(bytes(SLOW))
        slow = len(code) - len(rest)
        if slow and (rest == b'\x90' or rest[:2] == b'\x0f\x1f'):
            result.append((address, len(code), slow))
    return result


def plain(length):
    if length in PLAIN:
        return bytes.fromhex(PLAIN[length])
    return b''.join(plain(part) for part in SPLIT[length])


def reencode(obj):
    """Rewrite slow-prefix NOPs in a relocatable object as prefix-free NOPs of the same length."""
    fields = [line.split() for line in run(tool('objdump'), '-h', obj, capture=True).splitlines()
              if re.match(r'\s*\d+\s+\.text\s', line)][0]
    if int(fields[3], 16):
        raise RuntimeError('.text of a relocatable object must start at 0')
    offset = int(fields[5], 16)
    data = bytearray(obj.read_bytes())
    for address, length, _ in slow_nops(obj):
        data[offset + address:offset + address + length] = plain(length)
    obj.write_bytes(data)
    if slow_nops(obj):
        raise RuntimeError('slow-prefix NOP left in %s' % obj)


def residues(compiler):
    """Start address modulo 64 of each kernel in the S11-28 serial HPCG binary."""
    if HOST:
        return dict.fromkeys(KERNELS, 0)
    table = run(tool('nm'), REAL / compiler / 'serial/workload', capture=True)
    return {kernel: int(re.search(r'^([0-9a-f]+) T ' + symbol + '$', table, re.M).group(1), 16) % 64
            for kernel, (_, symbol) in KERNELS.items()}


def assemble(asm):
    obj = asm.with_suffix('.o')
    run(tool('as'), *([] if HOST else ['--march=k1om']), asm, '-o', obj)
    return obj


def kernel_objects(directory):
    objects, placed = [], {}
    real = {True: residues('gcc-5.1.1'), False: residues('gcc-knc')}
    for variant, donor, extra, prefix_free in VARIANTS:
        flags = ['-O2'] + ([] if donor or HOST else ['-march=knc']) + extra
        for kernel, (source, symbol) in KERNELS.items():
            asm = directory / ('%s_%s.s' % (variant, kernel))
            run(cxx(donor), *flags, '-DHPCG_NO_MPI', '-DHPCG_NO_OPENMP', '-I' + str(HPCG),
                '-S', HPCG / (source + '.cpp'), '-o', asm)
            name = '%s_%s' % (variant, kernel)
            lines = asm.read_text().replace(symbol, name).splitlines()
            # Same start address modulo 64 as in the benchmark binary; the flag
            # variants keep the compiler's own function alignment.
            residue = real[donor][kernel] if not extra else 0
            at = lines.index('\t.globl\t' + name)
            while not lines[at].startswith('\t.p2align'):
                at -= 1
            lines[at:at] = ['\t.p2align 6', '\t.skip %d, 0x90' % residue]
            asm.write_text('\n'.join(lines) + '\n')
            obj = assemble(asm)
            if prefix_free:
                reencode(obj)
            placed[name] = residue
            objects.append(obj)
            print('SLOW-PREFIX NOPS %s:' % name,
                  ' '.join('+0x%x:len%d:slow%d' % nop for nop in slow_nops(obj)) or 'none')
    return objects, placed


def microbench(name, before_top, pad='', loop=LOOP):
    """One row loop; `before_top` bytes run once so the padding lands where wanted."""
    elf = [] if HOST else ['\t.type\tmb_%s, @function' % name]
    return '\n'.join(['\t.p2align 6', '\t.globl\tmb_' + name] + elf + [
        'mb_%s:' % name, '\tfldz', '\t.skip %d, 0x90' % before_top,
        '.Lo_%s:' % name, '\txorl\t%eax, %eax'] + ([pad] if pad else []) + [
        '.Li_%s:' % name] + ['\t' + insn for insn in loop] + [
        '\tjg\t.Li_' + name, '\tsubq\t$1, %rdi', '\tjnz\t.Lo_' + name,
        '\tfstpl\t(%r9)', '\tret', ''])


def microbench_objects(directory):
    """Padding of 0-15 bytes run before a loop whose top is at 0 mod 64 (the
    assembler's NOPs, single-byte NOPs, prefix-free NOPs), no padding with the
    top at other offsets, and two loop-body controls."""
    expect, plainest, patched = {}, ['\t.text'], ['\t.text']
    for pad in range(16):
        for style, directive, text in [('gas', '\t.p2align 4', plainest),
                                       ('one', '\t.p2align 4,0x90', plainest),
                                       ('pf', '\t.p2align 4', patched)]:
            name = '%s_%d' % (style, pad)
            text.append(microbench(name, (60 - pad) % 64, directive))
            expect[name] = (0, pad)
    for top in MIS:
        plainest.append(microbench('mis_%d' % top, top - 4))
        expect['mis_%d' % top] = (top, 0)
    plainest.append(microbench('inc_0', 60, loop=[i.replace('addq\t$1,', 'incq') for i in LOOP]))
    plainest.append(microbench('adj_0', 60, loop=LOOP[:3] + [LOOP[5], LOOP[3], LOOP[4]]))
    expect['inc_0'] = expect['adj_0'] = (0, 0)
    objects = []
    for stem, text in [('mb', plainest), ('mbpf', patched)]:
        (directory / (stem + '.s')).write_text('\n'.join(text))
        objects.append(assemble(directory / (stem + '.s')))
    reencode(objects[1])
    # gas_0 first: the driver reports every microbench against it.
    order = ['%s_%d' % (style, pad) for style in ['gas', 'one', 'pf'] for pad in range(16)]
    return objects, expect, order + ['mis_%d' % top for top in MIS] + ['inc_0', 'adj_0']


def check_layout(binary, placed, expect):
    """The linked code is where the experiment says it is."""
    symbols = {}
    for line in run(tool('nm'), binary, capture=True).splitlines():
        parts = line.split()
        if len(parts) == 3:
            symbols[parts[2]] = int(parts[0], 16)
    for name, residue in placed.items():
        if symbols[name] % 64 != residue:
            raise RuntimeError('%s is at %#x, wanted %d mod 64' % (name, symbols[name], residue))
    code = instructions(binary)
    index = {address: i for i, (address, _, _) in enumerate(code)}
    for name, (top, pad) in expect.items():
        i = index[symbols['mb_' + name]]
        while not code[i][2].startswith('xor'):
            i += 1
        j = i
        while not code[j][2].startswith('movslq'):
            j += 1
        got = (code[j][0] % 64, code[j][0] - code[i][0] - 2)
        if got != (top, pad):
            raise RuntimeError('mb_%s: loop top and padding %r, wanted %r' % (name, got, (top, pad)))
        if name.startswith('pf_') and any(set(c[1][:1]) & SLOW for c in code[i:j]):
            raise RuntimeError('mb_%s: slow prefix in padding' % name)


def main():
    global HOST
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', action='store_true',
                        help='build and run the driver logic natively with the Cygwin compiler (no card code)')
    HOST = parser.parse_args().host
    if sys.platform != 'cygwin':
        raise RuntimeError('use shared Cygwin python3')
    os.environ['PATH'] = ':'.join([str(TC / 'cross/bin'), str(TC / 'cygwin/bin'), os.environ['PATH']])
    directory = OUT / ('host' if HOST else 'build')
    directory.mkdir(parents=True, exist_ok=True)
    kernels, placed = kernel_objects(directory)
    benches, expect, order = microbench_objects(directory)
    (directory / 's12_31_hpcg.inc').write_text(''.join('X(%s)\n' % v[0] for v in VARIANTS))
    (directory / 's12_31_mb.inc').write_text(''.join('X(%s)\n' % name for name in order))
    binary = directory / 's12-31-bench'
    static = [] if HOST else ['-static-libstdc++', '-static-libgcc', *corpus.link_paths(), '-lrt']
    run(cxx(True), '-O2', '-DHPCG_NO_MPI', '-DHPCG_NO_OPENMP', '-I' + str(HPCG), '-I' + str(directory),
        ROOT / 'tools/s12_31_bench.cpp', *kernels, *benches, *static, '-o', binary)
    if HOST:
        check_layout(Path(str(binary) + '.exe'), {}, expect)
        run(binary, 8, 2, 2000)
        print('HOST LOGIC CHECK ONLY: not KNC code, no card result.')
        return
    check_layout(binary, placed, expect)
    run(sys.executable, ROOT / 'tools/knc_lint', binary)
    print('STAGED:', binary, 'single-core timing; lead: card_run --benchmark --profile full --threads 1 --timeout 600')
    print('No card execution. No GCC build. Native outputs and timing remain pending.')


if __name__ == '__main__':
    main()
