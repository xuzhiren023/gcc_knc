/* S9-18 kernel "dispatch": a register-machine bytecode interpreter with 20 opcodes and a skewed
   opcode mix. In mix 0, opcodes 0-3 are 85% of the program; mix 1 (mismatched training only)
   draws mostly opcodes 4-19. DIV and MOD have an error path for a zero divisor.

   Built by tools/s9_18_pgo.py like skewed.c. */
#include <stdlib.h>
#include "pgo.h"

#define N 8192
enum { ADD, ADDI, XOR, LOAD, /* the hot four in mix 0 */
       SUB, MUL, SHL, SHR, AND, OR, NOT, NEG, ROT, SWAP, MIN, MAX, MOV, INC, DIV, MOD, NOPS };

struct insn { unsigned char op, d, s, imm; };
struct dispatch { struct insn code[N]; unsigned mem[256]; };

#ifdef SETUP
void *setup(int mix, unsigned seed)
{
    struct dispatch *p = malloc(sizeof *p);
    unsigned x = seed * 2654435761u + 1;
    if (!p)
        abort();
    for (int i = 0; i < N; i++) {
        x ^= x << 13, x ^= x >> 17, x ^= x << 5;
        int hot = x % 100 < (mix ? 10u : 85u);
        unsigned r = x >> 8;
        p->code[i].op = hot ? r % 4 : 4 + r % (NOPS - 4);
        p->code[i].d = (r >> 5) & 7;
        p->code[i].s = (r >> 8) & 7;
        p->code[i].imm = r >> 11;
    }
    for (int i = 0; i < 256; i++)
        p->mem[i] = i * 0x9e3779b9u;
    return p;
}
#else
unsigned long NAME(const void *in)
{
    const struct dispatch *p = in;
    unsigned r[8] = { 1, 2, 3, 4, 5, 6, 7, 8 };
    unsigned long sum = 0, errors = 0;
    for (int pc = 0; pc < N; pc++) {
        struct insn i = p->code[pc];
        unsigned *d = &r[i.d], s = r[i.s];
        if (LIKELY(i.op <= LOAD)) {
            switch (i.op) {
            case ADD: *d += s; break;
            case ADDI: *d += i.imm; break;
            case XOR: *d ^= s; break;
            default: *d = p->mem[(s + i.imm) & 255]; break;
            }
        } else {
            switch (i.op) {
            case SUB: *d -= s; break;
            case MUL: *d *= s | 1; break;
            case SHL: *d <<= s & 31; break;
            case SHR: *d >>= s & 31; break;
            case AND: *d &= s | i.imm; break;
            case OR: *d |= s & i.imm; break;
            case NOT: *d = ~s; break;
            case NEG: *d = -s; break;
            case ROT: *d = (*d << (s & 31)) | (*d >> (-s & 31)); break;
            case SWAP: r[i.s] = *d; *d = s; break;
            case MIN: *d = *d < s ? *d : s; break;
            case MAX: *d = *d > s ? *d : s; break;
            case MOV: *d = s; break;
            case INC: *d += 1; break;
            case DIV:
            case MOD:
                if (UNLIKELY(s == 0)) {
                    errors++;
                    *d = 0;
                } else {
                    *d = i.op == DIV ? *d / s : *d % s;
                }
                break;
            }
        }
        sum += r[i.d];
    }
    return sum + errors;
}
#endif
