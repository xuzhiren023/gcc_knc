/* Diagnostic ABI boundary: the double argument and result are both in zmm0.
   Handwritten controls intentionally hold these sequences equal across GCCs. */
        .text
        .globl identity_boundary
        .type identity_boundary, @function
identity_boundary:
        ret
        .size identity_boundary, .-identity_boundary

/* n is positive and divisible by eight; p, q and result are 64-byte aligned.
   Signature matches the C kernels: n, p, q, unused, result. */
        .globl vector_control
        .type vector_control, @function
vector_control:
        movl %edi, %ecx
        shrl $3, %ecx
        testl %ecx, %ecx
        jz .Ldone
.Lvector:
        vmovapd (%rsi), %zmm0
        vaddpd (%rdx), %zmm0, %zmm0
        vmovapd %zmm0, (%r8)
        addq $64, %rsi
        addq $64, %rdx
        addq $64, %r8
        decl %ecx
        jnz .Lvector
.Ldone:
        ret
        .size vector_control, .-vector_control
        .section .note.GNU-stack,"",@progbits
