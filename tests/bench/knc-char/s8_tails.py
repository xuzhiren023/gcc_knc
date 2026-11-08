"""Length 1..33 affine tails: y=x+1, identical logical elements in each variant."""


def register(add):
    for n in range(1, 34):
        for mode in ('x87', 'aligned', 'peel', 'gather'):
            # Peel starts at float offset 1, others at aligned offset 0.
            start = 1 if mode == 'peel' else 0
            pos = start
            end = start + n
            body = []
            if mode == 'x87':
                for i in range(n):
                    body += [f'flds {4*i}(%rsi)', 'fadd %st(1), %st',
                             f'fstps {512+4*i}(%rsi)']
            else:
                while mode == 'peel' and pos < end and pos % 16:
                    body += [f'flds {4*pos}(%rsi)', 'fadd %st(1), %st',
                             f'fstps {512+4*pos}(%rsi)']
                    pos += 1
                while pos < end:
                    lanes = min(16, end-pos)
                    body += [f'movl ${(1 << lanes)-1}, %eax', 'kmov %eax, %k1']
                    if mode == 'gather' and lanes < 16:
                        body += ['2:', f'vgatherdps {4*pos}(%rsi,%zmm30,4), %zmm0{{%k1}}',
                                 'jknzd 2b, %k1', f'movl ${(1 << lanes)-1}, %eax', 'kmov %eax, %k1']
                    else:
                        body += [f'vmovaps {4*pos}(%rsi), %zmm0{{%k1}}']
                    body += ['vaddps %zmm31, %zmm0, %zmm0',
                             f'vmovaps %zmm0, {512+4*pos}(%rsi){{%k1}}']
                    pos += lanes
            add(f'c6.{mode}.n{n}', '\n'.join(body),
                f'One affine invocation ({n} elements); peel input/output offset one float',
                setup='fld1', finish='fstp %st(0)', repeat=32, unit=0,
                verify_start=start, verify_length=n)
