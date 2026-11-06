// S5-13, ADR-0008 point 6; Intel 327364-001 pp.300-302, 598-600.
// The same non-k0 mask must decorate the access and close its retry loop.
// Accept numeric local labels and compiler-generated named local labels.
// options: -O3
// scan-asm-func gather_f32: ^\s*(?P<label>\.L[\w.$]+|[0-9]+):\s*\n\s*vgatherdps\s+[^\n]*\{%k(?P<mask>[1-7])\}\s*\n\s*jknzd\s+(?P=label)b?,\s*%k(?P=mask)\b
// scan-asm-func scatter_f32: ^\s*(?P<label>\.L[\w.$]+|[0-9]+):\s*\n\s*vscatterdps\s+[^\n]*\{%k(?P<mask>[1-7])\}\s*\n\s*jknzd\s+(?P=label)b?,\s*%k(?P=mask)\b
float a_f32[1024] __attribute__((aligned(64)));
int idx_f32[1024] __attribute__((aligned(64)));

void gather_f32 (const float *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    a_f32[i] = b[idx_f32[i]];
}

void scatter_f32 (float *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    b[idx_f32[i]] = a_f32[i];
}
