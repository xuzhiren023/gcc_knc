// S5-13, ADR-0008 point 6; Intel 327364-001 pp.484-486, 530-532.
// options: -O3 -fvect-cost-model=unlimited
// scan-asm-func gather_i32: ^\s*(?P<label>\.L[\w.$]+|[0-9]+):\s*\n\s*vpgatherdd\s+[^\n]*\{%k(?P<mask>[1-7])\}\s*\n\s*jknzd\s+(?P=label)b?,\s*%k(?P=mask)\b
// scan-asm-func scatter_i32: ^\s*(?P<label>\.L[\w.$]+|[0-9]+):\s*\n\s*vpscatterdd\s+[^\n]*\{%k(?P<mask>[1-7])\}\s*\n\s*jknzd\s+(?P=label)b?,\s*%k(?P=mask)\b
int a_i32[1024] __attribute__((aligned(64)));
int idx_i32[1024] __attribute__((aligned(64)));

void gather_i32 (const int *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    a_i32[i] = b[idx_i32[i]];
}

void scatter_i32 (int *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    b[idx_i32[i]] = a_i32[i];
}
