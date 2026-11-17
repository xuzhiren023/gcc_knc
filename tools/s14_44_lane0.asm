# Original S14-44 alternatives: only lane 0 performs FP arithmetic.
# R27 pp.114-115,144-147: verified architectural interface, early KNC spec.
# These are host-assembled research probes, not production replacements.
.text
.globl s14_subindex
.type s14_subindex,@function
s14_subindex:
    movl $1, %eax
    kmov %eax, %k1
    vbroadcastsd (%rsi), %zmm0
    vbroadcastsd (%rdx), %zmm1
    vcmppd $2, %zmm0, %zmm1, %k2{%k1}
    kmov %k2, %eax
    sall $2, %eax
    vbroadcastsd 8(%rsi), %zmm0
    vbroadcastsd 8(%rdx), %zmm1
    vcmppd $2, %zmm0, %zmm1, %k2{%k1}
    kmov %k2, %ecx
    leal (%eax,%ecx,2), %eax
    vbroadcastsd 16(%rsi), %zmm0
    vbroadcastsd 16(%rdx), %zmm1
    vcmppd $2, %zmm0, %zmm1, %k2{%k1}
    kmov %k2, %ecx
    addl %ecx, %eax
    movl %eax, (%rdi)
    ret
.size s14_subindex,.-s14_subindex

# Same live-in pointers/counter as PB-ludcmp main:.L31; accumulator in zmm0.
# Setup is charged to this candidate; baseline accumulator is already live.
.globl s14_ludcmp
.type s14_ludcmp,@function
s14_ludcmp:
    movl $1, %eax
    kmov %eax, %k1
.Llud:
    movq %rcx, %rax
    salq $12, %rax
    vbroadcastsd (%r10,%rax), %zmm1
    vbroadcastsd (%r15,%rcx,8), %zmm2
    vmulpd %zmm2, %zmm1, %zmm1{%k1}
    addq $1, %rcx
    cmpl %ecx, %r8d
    vsubpd %zmm1, %zmm0, %zmm0{%k1}
    jg .Llud
    ret
.size s14_ludcmp,.-s14_ludcmp

.globl s14_mix_lane
.type s14_mix_lane,@function
s14_mix_lane:
    movl $1, %eax
    kmov %eax, %k1
    xorl %eax, %eax
    vpxord %zmm0, %zmm0, %zmm0
    testl %ecx, %ecx
    je .Lmix_done
    movl %ecx, %ecx
    addq %rdi, %rcx
.Lmix:
    movzbl (%rdi), %r8d
    roll $5, %eax
    addq $1, %rdi
    xorl %r8d, %eax
    vbroadcastsd (%rsi,%r8,8), %zmm1
    vaddpd %zmm1, %zmm0, %zmm0{%k1}
    cmpq %rdi, %rcx
    jne .Lmix
.Lmix_done:
    vpackstorelpd %zmm0, (%rdx){%k1}
    ret
.size s14_mix_lane,.-s14_mix_lane
.section .note.GNU-stack,"",@progbits
