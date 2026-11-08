"""S8 issue, recurrence and branch experiments; Intel 327364 IMCI syntax."""


def register(add):
    for op in ('vector', 'prefetch0', 'prefetch1', 'vector_prefetch0', 'vector_prefetch1'):
        body = []
        for i in range(32):
            if 'vector' in op:
                body.append(f'vaddps %zmm31, %zmm{i % 8}, %zmm{i % 8}')
            if 'prefetch' in op:
                body.append(f'vprefetch{op[-1]} {64 * (i % 8)}(%rsi)')
        add('c2.' + op, '\n'.join(body),
            'Prefetch-only and vector-only controls versus adjacent independent vector/prefetch pairs',
            unit=2 if op.startswith('vector_') else 1)
    for accumulators in (1, 2):
        add(f'c7.reduce.a{accumulators}', '\n'.join(
            f'vaddps {64*i}(%rsi), %zmm{i % accumulators}, %zmm{i % accumulators}'
            for i in range(32)), '32 vector reduction updates; same inputs and operation count',
            setup='vpxord %zmm0, %zmm0, %zmm0\nvpxord %zmm1, %zmm1, %zmm1',
            finish=('vaddps %zmm1, %zmm0, %zmm0\n' if accumulators == 2 else '')
                   + 'vmovaps %zmm0, 2048(%rsi)')
    for chain in ('vector', 'memory'):
        for unroll in (1, 2, 4):
            # U expanded iterations, U independent recurrences, 32 updates total.
            source = '%zmm31' if chain == 'vector' else '(%rsi)'
            body = '\n'.join(f'vaddps {source}, %zmm{i}, %zmm{i}' for i in range(unroll))
            add(f'c9.{chain}.u{unroll}', body,
                f'{unroll} independent recurrences, register (4-cycle) or memory-operand (12-cycle) add',
                loop_scale=32 // unroll)
    for mode in ('fixed', 'random'):
        body = []
        for i in range(32):
            body += [f'cmpb $0, {i}(%rsi,%rcx)', 'je 2f', 'addq $1, %r8',
                     'jmp 4f', '2:', 'addq $2, %r8', 'jmp 4f', '4:']
        body += ['addq $32, %rcx', 'andq %rdx, %rcx']
        add('c10.branch.' + mode, '\n'.join(body),
            'Precomputed direction bits; identical executed instruction count on both paths; no RNG in timing',
            kind=5 if mode == 'random' else 6, unit=0)
