"""S8 stores, TLB reach and software-prefetch sweeps."""

# C5 array pitch: 1 MiB plus a page and three lines, so the eight arrays fall in
# different L1 sets and page colours instead of aliasing (S8-12).
C5_PITCH = 1048576 + 4096 + 3*64


def register(add):
    for name, insn in (('normal', 'vmovaps'), ('nr', 'vmovnraps'), ('ngo', 'vmovnrngoaps')):
        add('c1.store.' + name,
            'leaq (%rsi,%rcx), %r11\n' + '\n'.join(
                f'{insn} %zmm{i % 8}, {64*i}(%r11)' for i in range(32)) +
            '\naddq $2048, %rcx\nandq %rdx, %rcx',
            'Write-only memory stream, unmasked full lines; locked drain included in all variants',
            kind=2, core_bytes=16*1024*1024, setup='movl $0, (%rsp)',
            finish='lock addl $0, (%rsp)')
    for kb in (128, 256, 384, 448):
        add(f'c4.pages.{kb}', '\n'.join(['movq (%r11), %r11'] * 32),
            'Randomized page-stride pointer cycle, aggregate footprint per core',
            setup='movq %rsi, %r11', kind=3, core_bytes=kb*1024)
    for kernel in ('stream', 'stencil', 'row7', 'row8', 'row9'):
        for l1 in (0, 8, 16, 32, 64):
            for l2 in (0, 32, 64, 128):
                row = int(kernel[-1]) if kernel.startswith('row') else 16
                # Eight 1 MiB arrays C5_PITCH apart; only rows use all eight, stream/stencil use two.
                setup = f'movl ${(1 << row)-1}, %eax\nkmov %eax, %k1'
                body = []
                for iteration in range(32):
                    body.append('leaq (%rsi,%rcx), %r11')
                    for array in (range(8) if row != 16 else (0, 7)):
                        offset = array * C5_PITCH
                        for distance, hint in ((l1, 0), (l2, 1)):
                            if distance:
                                body.append(f'vprefetch{hint} {offset + distance*64}(%r11)')
                    mask = '{%k1}' if row != 16 else ''
                    body += [f'vmovaps 0(%r11), %zmm0{mask}']
                    if row != 16:
                        for array in range(1, 7):
                            body.append(f'vmovaps {array*C5_PITCH}(%r11), %zmm1{mask}')
                            body.append('vaddps %zmm1, %zmm0, %zmm0')
                    elif kernel == 'stream':
                        body.append('vaddps %zmm31, %zmm0, %zmm0')
                    if kernel == 'stencil':
                        # Forward 3-point stencil, with initialized input halo in array 1.
                        for offset in (4, 8):
                            body += [f'vloadunpacklps {offset}(%r11), %zmm1',
                                     f'vloadunpackhps {offset+64}(%r11), %zmm1',
                                     'vaddps %zmm1, %zmm0, %zmm0']
                    body += [f'vmovaps %zmm0, {7*C5_PITCH}(%r11){mask}',
                             'addq $64, %rcx', 'andq $1048575, %rcx']
                add(f'c5.{kernel}.l1_{l1}.l2_{l2}', '\n'.join(body),
                    'Stream affine, forward 3-point stencil, or seven-input short rows; zero disables hint',
                    setup=setup, unit=0)
