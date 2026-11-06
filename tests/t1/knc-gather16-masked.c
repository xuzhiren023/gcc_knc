// S5-13: the conditional gather must use the compare mask, directly or copied
// with kmov because the gather consumes it and the masked store still needs it.
// The destination is aligned to permit the existing KNC masked-store lowering.
// options: -O3
// scan-asm-func masked_gather: \bvpcmpd\s+\$4,[^\n]*,\s*%k(?P<cmp>[0-7])\s*\n(?:(?!\s*[^\n]*,\s*%k(?P=cmp)\s*$)[\s\S])*?(?:\bkmov\s+%k(?P=cmp),\s*%k(?P<copy>[1-7])\s*\n[\s\S]*?)?\bvgatherdps\s+[^\n]*\{%k(?(copy)(?P=copy)|(?P=cmp))\}
// scan-asm-func masked_gather: ^\s*(?P<label>\.L[\w.$]+|[0-9]+):\s*\n\s*vgatherdps\s+[^\n]*\{%k(?P<mask>[1-7])\}\s*\n\s*jknzd\s+(?P=label)b?,\s*%k(?P=mask)\b
float a_masked[1024] __attribute__((aligned(64)));
int idx_masked[1024] __attribute__((aligned(64)));
int m[1024] __attribute__((aligned(64)));

void masked_gather (const float *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    if (m[i])
      a_masked[i] = b[idx_masked[i]];
}
