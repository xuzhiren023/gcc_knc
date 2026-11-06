/* KNC IMCI, donor gas 2.22 --march=k1om; no AVX512/SSE instructions.
   FMA contraction matches the C build; exact inputs also match the scalar oracle.
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
        /* Compute low (n % lanes) bits once; retain n in rcx. */
        .macro tailmask lanes
        movq %rcx, %r8
        andl $(\lanes-1), %ecx
        movl $1, %eax
        shll %cl, %eax
        subl $1, %eax
        kmov %eax, %k1
        movq %r8, %rcx
        .endm
        .macro loadps offset, reg
        vloadunpacklps \offset(%rsi), \reg
        vloadunpackhps (\offset+64)(%rsi), \reg
        .endm
        .macro storeps reg, offset=0, pred=
        vpackstorelps \reg, \offset(%rdi)\pred
        vpackstorehps \reg, (\offset+64)(%rdi)\pred
        .endm
        /* One 256-byte block ahead to L1, eight blocks ahead to L2. */
        .macro prefetch offset=0
        vprefetch0 (\offset+256)(%rsi)
        vprefetch1 (\offset+2048)(%rsi)
        .endm
        .macro affine_load offset, reg, suffix, unaligned
        .if \unaligned
        loadps \offset, \reg
        .else
        vmovap\suffix \offset(%rsi), \reg
        .endif
        .endm
        .macro affine_store offset, reg, suffix, unaligned, pred=
        .if \unaligned
        storeps \reg, \offset, \pred
        .else
        vmovap\suffix \reg, \offset(%rdi)\pred
        .endif
        .endm
        .macro affine name, suffix, lanes, size, unaligned=0
        start \name
        testq %rcx, %rcx
        je .Ldone\@
        tailmask \lanes
        .if \unaligned
        /* Short calls still walk a potentially memory-sized input stream. */
        prefetch
        .endif
        vbroadcasts\suffix (%rdx), %zmm1
        vbroadcasts\suffix \size(%rdx), %zmm2
        cmpq $(4*\lanes), %rcx
        jb .Lsingle\@
.Lloop\@:
        .irp off,0,64,128,192
        prefetch \off
        .endr
        affine_load 0, %zmm0, \suffix, \unaligned
        affine_load 64, %zmm3, \suffix, \unaligned
        affine_load 128, %zmm4, \suffix, \unaligned
        affine_load 192, %zmm5, \suffix, \unaligned
        .irp reg,0,3,4,5
        vfmadd213p\suffix %zmm2, %zmm1, %zmm\reg
        .endr
        affine_store 0, %zmm0, \suffix, \unaligned
        affine_store 64, %zmm3, \suffix, \unaligned
        affine_store 128, %zmm4, \suffix, \unaligned
        affine_store 192, %zmm5, \suffix, \unaligned
        addq $256, %rsi
        addq $256, %rdi
        subq $(4*\lanes), %rcx
        cmpq $(4*\lanes), %rcx
        jae .Lloop\@
.Lsingle\@:
        cmpq $\lanes, %rcx
        jb .Ltail\@
        affine_load 0, %zmm0, \suffix, \unaligned
        vfmadd213p\suffix %zmm2, %zmm1, %zmm0
        affine_store 0, %zmm0, \suffix, \unaligned
        addq $64, %rsi
        addq $64, %rdi
        subq $\lanes, %rcx
        jmp .Lsingle\@
.Ltail\@:
        testq %rcx, %rcx
        je .Ldone\@
        affine_load 0, %zmm0, \suffix, \unaligned
        vfmadd213p\suffix %zmm2, %zmm1, %zmm0
        affine_store 0, %zmm0, \suffix, \unaligned, {%k1}
.Ldone\@:
        finish \name
        .endm
        affine affine_f32, s, 16, 4
        affine affine_f64, d, 8, 8
        affine short, s, 16, 4, 1

        /* Four independent chains, interleaved at each addition stage.
           Stencil2's four vectors cover exactly one 64-column output row. */
        .macro stencil_body two, regs:vararg
        .irp reg,\regs
        loadps (\reg*64-4), %zmm\reg
        .if \two
        vaddps (\reg*64-384)(%rsi), %zmm\reg, %zmm\reg
        .endif
        .endr
        .irp reg,\regs
        vaddps (\reg*64)(%rsi), %zmm\reg, %zmm\reg
        .endr
        .irp reg,\regs
        loadps (\reg*64+4), %zmm4
        vaddps %zmm4, %zmm\reg, %zmm\reg
        .endr
        .if \two
        .irp reg,\regs
        vaddps (\reg*64+384)(%rsi), %zmm\reg, %zmm\reg
        .endr
        .endif
        .endm
        .macro stencil name, two=0
        start \name
        testq %rcx, %rcx
        je .Ldone\@
        tailmask 16
        cmpq $64, %rcx
        jb .Lsingle\@
.Lloop\@:
        .irp off,0,64,128,192
        .if \two
        /* Next row's center/south to L1; row +8 and its neighbors to L2. */
        vprefetch0 (\off+384)(%rsi)
        vprefetch0 (\off+768)(%rsi)
        vprefetch1 (\off+2688)(%rsi)
        vprefetch1 (\off+3072)(%rsi)
        vprefetch1 (\off+3456)(%rsi)
        .else
        prefetch \off
        .endif
        .endr
        stencil_body \two, 0,1,2,3
        .irp reg,0,1,2,3
        vmovaps %zmm\reg, (\reg*64)(%rdi)
        .endr
        addq $(256+128*\two), %rsi
        addq $256, %rdi
        subq $64, %rcx
        cmpq $64, %rcx
        jae .Lloop\@
.Lsingle\@:
        cmpq $16, %rcx
        jb .Ltail\@
        stencil_body \two, 0
        vmovaps %zmm0, (%rdi)
        addq $64, %rsi
        addq $64, %rdi
        subq $16, %rcx
        jmp .Lsingle\@
.Ltail\@:
        testq %rcx, %rcx
        je .Ldone\@
        stencil_body \two, 0
        vmovaps %zmm0, (%rdi){%k1}
.Ldone\@:
        finish \name
        .endm
        stencil stencil1
        stencil stencil2, 1

        /* Vectorize independent output rows, retaining each dot product's
           left-to-right order. 8x8 has an explicitly padded leading dim 16. */
        .macro matrix dim
        start mat\dim
        testq %rcx, %rcx
        je .Lmatdone\@
        tailmask \dim
        .if \dim == 8
        movl $255, %eax
        kmov %eax, %k2
        .endif
.Lmat\@:
        prefetch
        vpxord %zmm0, %zmm0, %zmm0
        movq %rdx, %r8
        movq %rsi, %r9
        movl $\dim, %r10d
.Ldot\@:
        vbroadcastss (%r9), %zmm1
        vfmadd231ps (%r8), %zmm1, %zmm0
        addq $64, %r8
        addq $4, %r9
        subl $1, %r10d
        jne .Ldot\@
        cmpq $\dim, %rcx
        jb .Lmattail\@
        .if \dim == 8
        /* Eight rows occupy half a cache line; preserve the other half. */
        storeps %zmm0, 0, {%k2}
        .else
        vmovaps %zmm0, (%rdi)
        .endif
        addq $64, %rsi
        addq $(\dim*4), %rdi
        subq $\dim, %rcx
        jg .Lmat\@
        jmp .Lmatdone\@
.Lmattail\@:
        storeps %zmm0, 0, {%k1}
.Lmatdone\@:
        finish mat\dim
        .endm
        matrix 8
        matrix 16
        .section .note.GNU-stack,"",@progbits
