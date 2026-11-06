/* KNC IMCI, donor gas 2.22 --march=k1om; no AVX512/SSE instructions.
   All FP operations are separate multiply/add in the same order as C.
   Inputs have initialized padding. Masked stores preserve output guards.
   SysV integer arguments y=rdi, x=rsi, p=rdx, n=rcx. Only caller-saved regs. */
        .text
        .macro start name
        .p2align 4
        .globl m2_\name\()_imci
        .type m2_\name\()_imci,@function
m2_\name\()_imci:
        .endm
        .macro finish name
        ret
        .size m2_\name\()_imci,.-m2_\name\()_imci
        .endm
        /* Low min(n,lanes) bits; rcx retained. */
        .macro mask lanes
        movl $-1, %eax
        cmpq $\lanes, %rcx
        jae .Lmask\@
        movl $1, %eax
        shll %cl, %eax
        subl $1, %eax
.Lmask\@:
        kmov %eax, %k1
        .endm
        .macro loadps offset, reg
        vloadunpacklps \offset(%rsi), \reg
        vloadunpackhps (\offset+64)(%rsi), \reg
        .endm
        .macro storeps
        vpackstorelps %zmm0, (%rdi){%k1}
        vpackstorehps %zmm0, 64(%rdi){%k1}
        .endm
        .macro affine name, suffix, lanes, size, unaligned=0
        start \name
        testq %rcx, %rcx
        je .Ldone\@
        vbroadcasts\suffix (%rdx), %zmm1
        vbroadcasts\suffix \size(%rdx), %zmm2
.Lloop\@:
        mask \lanes
        .if \unaligned
        loadps 0, %zmm0
        .else
        vmovap\suffix (%rsi), %zmm0
        .endif
        vmulp\suffix %zmm1, %zmm0, %zmm0
        vaddp\suffix %zmm2, %zmm0, %zmm0
        .if \unaligned
        storeps
        .else
        vmovap\suffix %zmm0, (%rdi){%k1}
        .endif
        addq $64, %rsi
        addq $64, %rdi
        subq $\lanes, %rcx
        jg .Lloop\@
.Ldone\@:
        finish \name
        .endm
        affine affine_f32, s, 16, 4
        affine affine_f64, d, 8, 8
        affine short, s, 16, 4, 1

        start stencil1
        testq %rcx, %rcx
        je .Lend1
.Lstencil1:
        mask 16
        loadps -4, %zmm0
        vaddps (%rsi), %zmm0, %zmm0
        loadps 4, %zmm1
        vaddps %zmm1, %zmm0, %zmm0
        vmovaps %zmm0, (%rdi){%k1}
        addq $64, %rsi
        addq $64, %rdi
        subq $16, %rcx
        jg .Lstencil1
.Lend1:
        finish stencil1

        start stencil2
        testq %rcx, %rcx
        je .Lend2
        movq $64, %r8
.Lstencil2:
        mask 16
        vmovaps -384(%rsi), %zmm0
        loadps -4, %zmm1
        vaddps %zmm1, %zmm0, %zmm0
        vaddps (%rsi), %zmm0, %zmm0
        loadps 4, %zmm1
        vaddps %zmm1, %zmm0, %zmm0
        vaddps 384(%rsi), %zmm0, %zmm0
        vmovaps %zmm0, (%rdi){%k1}
        addq $64, %rsi
        addq $64, %rdi
        subq $16, %rcx
        jle .Lend2
        subq $16, %r8
        jne .Lstencil2
        addq $128, %rsi
        movq $64, %r8
        jmp .Lstencil2
.Lend2:
        finish stencil2

        /* Vectorize independent output rows, retaining each dot product's
           left-to-right order. 8x8 has an explicitly padded leading dim 16. */
        .macro matrix dim
        start mat\dim
        testq %rcx, %rcx
        je .Lmatdone\@
.Lmat\@:
        mask \dim
        .if \dim == 8
        andl $255, %eax
        kmov %eax, %k1
        .endif
        vpxord %zmm0, %zmm0, %zmm0
        movq %rdx, %r8
        movq %rsi, %r9
        movl $\dim, %r10d
.Ldot\@:
        vbroadcastss (%r9), %zmm1
        vmulps (%r8), %zmm1, %zmm1
        vaddps %zmm1, %zmm0, %zmm0
        addq $64, %r8
        addq $4, %r9
        subl $1, %r10d
        jne .Ldot\@
        storeps
        addq $64, %rsi
        addq $(\dim*4), %rdi
        subq $\dim, %rcx
        jg .Lmat\@
.Lmatdone\@:
        finish mat\dim
        .endm
        matrix 8
        matrix 16
        .section .note.GNU-stack,"",@progbits
