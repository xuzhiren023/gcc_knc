"""IMCI microkernel catalog and assembly emitter (Intel 327364-001).

Generated assembly/header live only in the shared output directory.
Each round contains 32 measurement units; no compiler schedules their bodies.
"""
from pathlib import Path

CASES = []


def add(name, body, description, setup='', finish='', kind=0, unit=1,
        core_bytes=0, repeat=1, loop_scale=1, verify_start=0, verify_length=0):
    CASES.append(dict(name=name, body=body, description=description,
                      setup=setup, finish=finish, kind=kind, unit=unit,
                      core_bytes=core_bytes, repeat=repeat, loop_scale=loop_scale,
                      verify_start=verify_start, verify_length=verify_length))


def arithmetic(name, instruction, description):
    for mode in ('lat', 'rt'):
        body = '\n'.join(instruction.format(z=i % 8 if mode == 'rt' else 0,
                                               r=8 + i % 3 if mode == 'rt' else 8,
                                               k=1 + i % 6 if mode == 'rt' else 1)
                         for i in range(32))
        add(name + '.' + mode, body, description + ('; one dependent chain' if mode == 'lat'
                                                   else '; independent destinations/chains'))


for name, insn, desc in (
    ('vaddps', 'vaddps %zmm31, %zmm{z}, %zmm{z}', 'FP32 vector add'),
    ('vmulps', 'vmulps %zmm31, %zmm{z}, %zmm{z}', 'FP32 vector multiply by one'),
    ('vfmadd213ps', 'vfmadd213ps %zmm31, %zmm31, %zmm{z}', 'FP32 fused multiply-add'),
    ('vpaddd', 'vpaddd %zmm31, %zmm{z}, %zmm{z}', 'Vector integer add'),
    ('vpxord', 'vpxord %zmm31, %zmm{z}, %zmm{z}', 'Vector integer XOR, distinct operands'),
    ('vpermd', 'vpermd %zmm{z}, %zmm30, %zmm{z}', 'Dword permutation, data dependency'),
    ('vpermf32x4', 'vpermf32x4 $0x1b, %zmm{z}, %zmm{z}', '128-bit block permutation'),
    ('vrcp23ps', 'vrcp23ps %zmm{z}, %zmm{z}', 'FP32 approximate reciprocal of one'),
    ('scalar_add', 'addq $1, %r{r}', 'Scalar 64-bit integer add (three chains in rt)'),
    ('scalar_xor', 'xorq %rax, %r{r}', 'Scalar integer XOR (three chains in rt)'),
    ('kmov', 'kmov %k{k}, %k{k}', 'Mask register move (six destinations in rt)'),
    ('kand', 'kand %k7, %k{k}', 'Mask AND (six chains in rt)'),
    ('kxor', 'kxor %k7, %k{k}', 'Mask XOR (six chains in rt)'),
):
    arithmetic(name, insn, desc)
for swizzle in ('cdab', 'badc', 'dacb', 'aaaa', 'bbbb', 'cccc', 'dddd'):
    arithmetic('swizzle_' + swizzle,
               'vmovdqa32 %zmm{z}{{' + swizzle + '}}, %zmm{z}',
               '32-bit register swizzle ' + swizzle)
for name in ('vaddpd', 'vmulpd', 'vfmadd213pd'):
    arithmetic(name, name + (' %zmm31, %zmm31, %zmm{z}' if name.startswith('vfmadd') else
                             ' %zmm31, %zmm{z}, %zmm{z}'), 'FP64 vector arithmetic')
    for case in CASES[-2:]:
        case['setup'] = 'vmovaps double_ones(%rip), %zmm31\n' + '\n'.join(
            f'vmovaps %zmm31, %zmm{z}' for z in range(8))
for form in ('dq2ps', 'udq2ps', 'ps2dq', 'ps2udq', 'pd2dq', 'pd2udq'):
    arithmetic('vcvtfxpnt' + form,
               'vcvtfxpnt' + form + ' $0, %zmm{z}, %zmm{z}',
               'Fixed-point conversion scale zero; register bit-pattern recurrence')

for op in ('add', 'mul', 'div'):
    for mode in ('lat', 'rt'):
        add('x87_' + op + '.' + mode,
            '\n'.join(f'f{op} %st, %st({1 + i % 7 if mode == "rt" else 1})'
                      for i in range(32)),
            'x87 ' + op + ('; dependent st1' if mode == 'lat' else '; seven independent stack registers'),
            setup='\n'.join(['fld1'] * 8), finish='\n'.join(['fstp %st(0)'] * 8))

for mode in ('lat', 'rt'):
    for op, load, store in (
        ('masked_load', 'vmovaps {a}(%rsi), %zmm{z}{{%k1}}', 'vmovaps %zmm{z}, {a}(%rsi){{%k1}}'),
        ('masked_store', 'vmovaps {a}(%rsi), %zmm{z}{{%k1}}', 'vmovaps %zmm{z}, {a}(%rsi){{%k1}}'),
        ('unpack', 'vloadunpacklps 4+{a}(%rsi), %zmm{z}\nvloadunpackhps 68+{a}(%rsi), %zmm{z}',
         'vpackstorelps %zmm{z}, 4+{a}(%rsi)\nvpackstorehps %zmm{z}, 68+{a}(%rsi)'),
        ('convert_up', 'vmovaps {a}(%rsi){{float16}}, %zmm{z}', 'vmovaps %zmm{z}{{float16}}, {a}(%rsi)'),
        ('convert_down', 'vmovaps {a}(%rsi){{float16}}, %zmm{z}', 'vmovaps %zmm{z}{{float16}}, {a}(%rsi)'),
        ('spill_reload', 'vmovaps {a}(%rsp), %zmm{z}', 'vmovaps %zmm{z}, {a}(%rsp)'),
    ):
        seq = (store + '\n' + load) if mode == 'lat' or op == 'spill_reload' else (
            store if op in ('masked_store', 'convert_down') else load)
        add(op + '.' + mode,
            '\n'.join(seq.format(z=i % 8 if mode == 'rt' else 0,
                                  a=128 * (i % 8) if mode == 'rt' else 0)
                      for i in range(32)),
            op + ('; dependent store-to-load round trip, not isolated load/store latency'
                  if mode == 'lat' else '; eight independent buffers; unpack counts L/H pair'),
            unit=(4 if mode == 'lat' else 2) if op == 'unpack' else
                 2 if mode == 'lat' or op == 'spill_reload' else 1)

# Partial masks make merge and sparse-store behavior visible separately.
for case in list(CASES):
    if case['name'].startswith(('masked_load.', 'masked_store.')):
        sparse = case.copy()
        sparse['name'] = case['name'].replace('.', '_sparse.')
        sparse['setup'] = 'movl $21845, %eax\nkmov %eax, %k1'
        sparse['description'] += '; alternating eight active lanes'
        CASES.append(sparse)

for scatter in (False, True):
    for mode in ('lat', 'rt'):
        body = []
        for i in range(32):
            z = i % 8 if mode == 'rt' else 0
            label = '3%d' % i
            if mode == 'lat':
                body.append(f'vpord %zmm{z}, %zmm30, %zmm29')
            body += ['kmov %eax, %k1', label + ':',
                     'vgatherdps (%%rsi,%%zmm%d,4), %%zmm%d{%%k1}' % (29 if mode == 'lat' else 30, z),
                     'jknzd ' + label + 'b, %k1']
        add('gather_' + ('scattered' if scatter else 'all') + '.' + mode, '\n'.join(body),
            'Complete 16-lane gather with mask reset/replay; ' + ('16 cache lines' if scatter else 'one cache line')
            + ('; result-to-index OR dependency on zero data' if mode == 'lat' else '; eight output registers'),
            setup='vpxord %zmm0, %zmm0, %zmm0\nvmovdqa32 ' +
                  ('scatter' if scatter else 'indices') + '(%rip), %zmm30', unit=0)

for pairing, body in (
    ('vector_scalar', 'vaddps %zmm31, %zmm{z}, %zmm{z}\naddq $1, %r8'),
    ('vector_vector', 'vaddps %zmm31, %zmm{z}, %zmm{z}\nvpaddd %zmm31, %zmm{q}, %zmm{q}'),
    ('scalar_scalar', 'addq $1, %r8\naddq $1, %r9'),
):
    add('pair.' + pairing, '\n'.join(body.format(z=i % 8, q=8 + i % 8) for i in range(32)),
        'U/V issue experiment; cycles per two-instruction pair; independent streams', unit=2)
for gap in range(5):
    add('agi.gap%d' % gap,
        '\n'.join(['addq $0, %rsi\n' + 'nop\n' * gap + 'movq (%rsi), %r8'] * 32),
        'Pointer ALU update then load separated by %d scalar NOP instructions (not assumed cycles)' % gap,
        unit=gap+2)
for level in ('l1', 'l2', 'memory'):
    add(level + '.load_lat', '\n'.join(['movq (%r11), %r11'] * 32),
        'Dependent randomized 64-byte-line pointer cycle; per-worker ' + level + ' budget',
        setup='movq %rsi, %r11', kind=1)
    for op, insn in (('load_rt', 'vmovaps {a}(%r11), %zmm{z}'),
                     ('store_normal', 'vmovaps %zmm{z}, {a}(%r11)'),
                     ('store_stream', 'vmovnraps %zmm{z}, {a}(%r11)')):
        add(level + '.' + op,
            'leaq (%rsi,%rcx), %r11\n' +
            '\n'.join(insn.format(a=64*i, z=i % 8) for i in range(32)) +
            '\naddq $2048, %rcx\nandq %rdx, %rcx',
            'Sequential 64-byte lines; ' + ('globally ordered no-read stores' if op == 'store_stream' else op)
            + '; bytes/ns derives bandwidth, includes loop/address overhead', kind=2)


from s8_memory import register as memory_checks
from s8_compute import register as compute_checks
from s8_tails import register as tail_checks
memory_checks(add)
compute_checks(add)
tail_checks(add)


def emit(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    header = ['/* Generated by kernels.py. */',
              'typedef void (*kernel_fn)(unsigned long, void *, unsigned long);',
              'struct test { const char *name; kernel_fn fn; int kind, instructions; unsigned long core_bytes; int verify_start, verify_length; };']
    asm = ['.text']
    for index, case in enumerate(CASES):
        symbol = 'char_kernel_%d' % index
        header += ['#ifdef CHAR_HOST',
                   'static void %s(unsigned long n, void *p, unsigned long b) {(void)n;(void)p;(void)b;}' % symbol,
                   '#else', 'extern void %s(unsigned long, void *, unsigned long);' % symbol, '#endif']
        asm += ['.p2align 6', '.globl ' + symbol, '.type ' + symbol + ', @function', symbol + ':',
                'pushq %rbp', 'movq %rsp, %rbp', 'andq $-64, %rsp', 'subq $1024, %rsp',
                'xorl %ecx, %ecx', 'subq $1, %rdx', 'movl $65535, %eax',
                'movq $1, %r8', 'movq $1, %r9', 'movq $1, %r10',
                'vmovaps ones(%rip), %zmm31', 'vmovdqa32 indices(%rip), %zmm30']
        asm += [f'vmovaps %zmm31, %zmm{z}' for z in range(16)]
        asm += [f'kmov %eax, %k{k}' for k in range(1, 8)]
        asm += [case['setup'], f'imulq ${case["loop_scale"]}, %rdi', '.p2align 6', '1:',
                f'.rept {case["repeat"]}', case['body'], '.endr', 'subq $1, %rdi', 'jnz 1b',
                case['finish'], 'leave', 'ret', '.size ' + symbol + ', .-' + symbol]
    header += ['static const struct test tests[] = {']
    header += ['{"%s", char_kernel_%d, %d, %d, %d, %d, %d},' %
               (c['name'], i, c['kind'], c['unit'], c['core_bytes'], c['verify_start'], c['verify_length'])
               for i, c in enumerate(CASES)]
    header += ['};', '#define NTESTS (sizeof(tests)/sizeof(tests[0]))']
    asm += ['.section .rodata', '.p2align 6', 'ones:', '.rept 16', '.long 0x3f800000', '.endr',
            'double_ones:', '.rept 8', '.quad 0x3ff0000000000000', '.endr',
            'indices:', '.long ' + ','.join(str(i) for i in range(16)),
            'scatter:', '.long ' + ','.join(str(16*i) for i in range(16)),
            '.section .note.GNU-stack,"",@progbits']
    (out / 'kernels.h').write_text('\n'.join(header) + '\n')
    (out / 'kernels.s').write_text('\n'.join(asm) + '\n')


if __name__ == '__main__':
    import sys
    emit(sys.argv[1])
