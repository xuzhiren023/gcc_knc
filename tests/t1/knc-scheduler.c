// options: -O2 -march=knc -mtune=knc -ffp-contract=off -fno-unroll-loops
// Dependent vector arithmetic must have useful scalar work between it.
// scan-asm-func schedule_loop: vmulps[^\n]*, (%zmm[0-9]+)\n(?:[^\n]*\n)*?\s+(?:addq|subq|leaq)[^\n]*\n(?:[^\n]*\n)*?\s+vaddps[^\n]*\1
// A pointer update and its next address use need an intervening instruction.
// scan-asm-func schedule_loop: movq\s+64\((%r[a-z0-9]+)\), \1\n\s+[a-z][^\n]*\n(?:[^\n]*\n)*?\s+v[a-z0-9]+[^\n]*\(\1\)
typedef float v16sf __attribute__((vector_size(64)));
struct node { v16sf x; const struct node *next; };

void schedule_loop (v16sf *restrict out, const struct node *in,
                    unsigned long n, const v16sf *coeff)
{
  v16sf a = coeff[0], b = coeff[1];
  while (n--)
    {
      in = in->next;
      v16sf x = in->x;
      *out++ = x * a + b;
    }
}
