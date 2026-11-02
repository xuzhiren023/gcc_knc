.text
.globl seed
seed:
    cmpxchg16b (%rax)
    ret
