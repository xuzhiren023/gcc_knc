/* Deliberately wrong affine reference: copies x, omitting both multiply and
   add. Full blocks execute IMCI; the tail copies only in-range scalar bits.
   SysV integer arguments: y=%rdi, x=%rsi, ab=%rdx, n=%rcx. */
        .text
        .p2align 4
        .globl m2_affine_f32_imci_negative
        .type m2_affine_f32_imci_negative,@function
m2_affine_f32_imci_negative:
        cmpq $16, %rcx
        jb .Ltail
.Lvector:
        vmovaps (%rsi), %zmm0
        vmovaps %zmm0, (%rdi)
        addq $64, %rsi
        addq $64, %rdi
        subq $16, %rcx
        cmpq $16, %rcx
        jae .Lvector
.Ltail:
        testq %rcx, %rcx
        je .Ldone
.Lscalar:
        movl (%rsi), %eax
        movl %eax, (%rdi)
        addq $4, %rsi
        addq $4, %rdi
        subq $1, %rcx
        jne .Lscalar
.Ldone:
        ret
        .size m2_affine_f32_imci_negative,.-m2_affine_f32_imci_negative
        .section .note.GNU-stack,"",@progbits
