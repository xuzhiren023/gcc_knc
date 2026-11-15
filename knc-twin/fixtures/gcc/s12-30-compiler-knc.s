	.file	"s12_30_precision.c"
	.text
	.p2align 6
	.type	knc_csr_raw, @function
knc_csr_raw:
.LFB5:
	.cfi_startproc
	testl	%edi, %edi
	jle	.L23
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	movl	%edi, %edi
	movq	%rsi, %r11
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	movq	%rdx, %r10
	leaq	0(,%rdi,4), %r12
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	xorl	%ebp, %ebp
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	%rcx, %rbx
	.p2align 4
	.p2align 3
.L9:
	movl	4(%r11,%rbp), %edi
	movl	(%r11,%rbp), %ecx
	cmpl	%ecx, %edi
	jle	.L10
	leal	-1(%rdi), %eax
	subl	%ecx, %eax
	cmpl	$1022, %eax
	jbe	.L4
	leal	-7(%rdi), %r13d
	leal	1(%rcx), %eax
	cmpl	%eax, %r13d
	jle	.L11
	cmpl	$-2147483641, %edi
	jl	.L11
	fldz
	movslq	%ecx, %rax
	leaq	(%rbx,%rax,8), %rdx
	leaq	(%r10,%rax,4), %rax
	.p2align 4
	.p2align 3
.L6:
	movslq	(%rax), %rsi
	vprefetch1	2048(%rdx)
	fldl	(%r8,%rsi,8)
	movslq	4(%rax), %rsi
	fmull	(%rdx)
	vprefetch0	1024(%rdx)
	vprefetch1	1024(%rax)
	vprefetch0	512(%rax)
	faddp	%st, %st(1)
	addq	$64, %rdx
	fldl	(%r8,%rsi,8)
	movslq	8(%rax), %rsi
	fmull	-56(%rdx)
	addq	$32, %rax
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-20(%rax), %rsi
	fmull	-48(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-16(%rax), %rsi
	fmull	-40(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-12(%rax), %rsi
	fmull	-32(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-8(%rax), %rsi
	fmull	-24(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-4(%rax), %rsi
	fmull	-16(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	leal	9(%rcx), %esi
	fmull	-8(%rdx)
	addl	$8, %ecx
	cmpl	%esi, %r13d
	faddp	%st, %st(1)
	jg	.L6
.L5:
	movslq	%ecx, %rax
	.p2align 4
	.p2align 3
.L7:
	movslq	(%r10,%rax,4), %rdx
	fldl	(%r8,%rdx,8)
	fmull	(%rbx,%rax,8)
	addq	$1, %rax
	cmpl	%eax, %edi
	faddp	%st, %st(1)
	jg	.L7
	fstpl	(%r9,%rbp,2)
	addq	$4, %rbp
	cmpq	%r12, %rbp
	jne	.L9
.L27:
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
	.p2align 4,,10
	.p2align 3
.L4:
	.cfi_restore_state
	fldz
	movslq	%ecx, %rax
	.p2align 4
	.p2align 3
.L8:
	movslq	(%r10,%rax,4), %rdx
	fldl	(%r8,%rdx,8)
	fmull	(%rbx,%rax,8)
	addq	$1, %rax
	cmpl	%eax, %edi
	faddp	%st, %st(1)
	jg	.L8
	fstpl	(%r9,%rbp,2)
	addq	$4, %rbp
	cmpq	%r12, %rbp
	jne	.L9
	jmp	.L27
	.p2align 4,,10
	.p2align 3
.L10:
	fldz
	fstpl	(%r9,%rbp,2)
	addq	$4, %rbp
	cmpq	%r12, %rbp
	jne	.L9
	jmp	.L27
.L11:
	fldz
	jmp	.L5
.L23:
	.cfi_def_cfa_offset 8
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	ret
	.cfi_endproc
.LFE5:
	.size	knc_csr_raw, .-knc_csr_raw
	.p2align 6
	.type	knc_hpcg_raw, @function
knc_hpcg_raw:
.LFB7:
	.cfi_startproc
	testl	%edi, %edi
	jle	.L42
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	movl	%edi, %r14d
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movq	%rcx, %r13
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	movq	%rdx, %r12
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	movq	%rsi, %rbp
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	xorl	%ebx, %ebx
	.p2align 4
	.p2align 3
.L35:
	movl	0(%rbp,%rbx,4), %edi
	testl	%edi, %edi
	jle	.L36
	leal	-1(%rdi), %eax
	movq	(%r12,%rbx,8), %r11
	cmpl	$1022, %eax
	movq	0(%r13,%rbx,8), %r10
	jbe	.L31
	leal	-9(%rdi), %r15d
	movq	%r10, %rdx
	andl	$-8, %r15d
	movq	%r11, %rax
	fldz
	addl	$8, %r15d
	xorl	%ecx, %ecx
	.p2align 4
	.p2align 3
.L32:
	movslq	(%rax), %rsi
	addl	$8, %ecx
	fldl	(%r8,%rsi,8)
	movslq	4(%rax), %rsi
	fmull	(%rdx)
	vprefetch1	2048(%rdx)
	vprefetch0	1024(%rdx)
	vprefetch1	1024(%rax)
	faddp	%st, %st(1)
	vprefetch0	512(%rax)
	fldl	(%r8,%rsi,8)
	movslq	8(%rax), %rsi
	fmull	8(%rdx)
	addq	$32, %rax
	addq	$64, %rdx
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-20(%rax), %rsi
	fmull	-48(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-16(%rax), %rsi
	fmull	-40(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-12(%rax), %rsi
	fmull	-32(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-8(%rax), %rsi
	fmull	-24(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	movslq	-4(%rax), %rsi
	fmull	-16(%rdx)
	faddp	%st, %st(1)
	fldl	(%r8,%rsi,8)
	fmull	-8(%rdx)
	cmpl	%r15d, %ecx
	faddp	%st, %st(1)
	jne	.L32
	movl	%ecx, %eax
	.p2align 4
	.p2align 3
.L33:
	movslq	(%r11,%rax,4), %rdx
	fldl	(%r8,%rdx,8)
	fmull	(%r10,%rax,8)
	addq	$1, %rax
	cmpl	%eax, %edi
	faddp	%st, %st(1)
	jg	.L33
	fstpl	(%r9,%rbx,8)
	addq	$1, %rbx
	cmpq	%r14, %rbx
	jne	.L35
.L45:
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4,,10
	.p2align 3
.L31:
	.cfi_restore_state
	fldz
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L34:
	movslq	(%r11,%rax,4), %rdx
	fldl	(%r8,%rdx,8)
	fmull	(%r10,%rax,8)
	addq	$1, %rax
	cmpq	%rax, %rdi
	faddp	%st, %st(1)
	jne	.L34
	fstpl	(%r9,%rbx,8)
	addq	$1, %rbx
	cmpq	%r14, %rbx
	jne	.L35
	jmp	.L45
	.p2align 4,,10
	.p2align 3
.L36:
	fldz
	fstpl	(%r9,%rbx,8)
	addq	$1, %rbx
	cmpq	%r14, %rbx
	jne	.L35
	jmp	.L45
.L42:
	.cfi_def_cfa_offset 8
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	.cfi_restore 14
	.cfi_restore 15
	ret
	.cfi_endproc
.LFE7:
	.size	knc_hpcg_raw, .-knc_hpcg_raw
	.p2align 6
	.globl	knc_csr_scalar
	.type	knc_csr_scalar, @function
knc_csr_scalar:
.LFB8:
	.cfi_startproc
	movl	(%rdi), %eax
	movq	32(%rdi), %rcx
	movq	16(%rdi), %rdx
	movq	40(%rdi), %r8
	movq	%rsi, %r9
	movq	8(%rdi), %rsi
	movl	%eax, %edi
	jmp	knc_csr_raw
	.cfi_endproc
.LFE8:
	.size	knc_csr_scalar, .-knc_csr_scalar
	.p2align 6
	.globl	knc_hpcg_scalar
	.type	knc_hpcg_scalar, @function
knc_hpcg_scalar:
.LFB9:
	.cfi_startproc
	movl	(%rdi), %eax
	movq	56(%rdi), %rcx
	movq	48(%rdi), %rdx
	movq	40(%rdi), %r8
	movq	%rsi, %r9
	movq	24(%rdi), %rsi
	movl	%eax, %edi
	jmp	knc_hpcg_raw
	.cfi_endproc
.LFE9:
	.size	knc_hpcg_scalar, .-knc_hpcg_scalar
	.p2align 6
	.globl	knc_lone_scalar
	.type	knc_lone_scalar, @function
knc_lone_scalar:
.LFB11:
	.cfi_startproc
	movq	24(%rdi), %rax
	movq	%rsi, %r11
	movl	(%rax), %r8d
	testl	%r8d, %r8d
	jle	.L54
	leal	-1(%r8), %eax
	movq	16(%rdi), %r10
	cmpl	$1022, %eax
	movq	32(%rdi), %r9
	movq	40(%rdi), %rcx
	jbe	.L50
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset 3, -16
	leal	-9(%r8), %ebx
	movq	%r9, %rdx
	andl	$-8, %ebx
	movq	%r10, %rax
	fldz
	addl	$8, %ebx
	xorl	%esi, %esi
	.p2align 4
	.p2align 3
.L51:
	movslq	(%rax), %rdi
	addl	$8, %esi
	fldl	(%rcx,%rdi,8)
	movslq	4(%rax), %rdi
	fmull	(%rdx)
	vprefetch1	2048(%rdx)
	vprefetch0	1024(%rdx)
	vprefetch1	1024(%rax)
	faddp	%st, %st(1)
	vprefetch0	512(%rax)
	fldl	(%rcx,%rdi,8)
	movslq	8(%rax), %rdi
	fmull	8(%rdx)
	addq	$32, %rax
	addq	$64, %rdx
	faddp	%st, %st(1)
	fldl	(%rcx,%rdi,8)
	movslq	-20(%rax), %rdi
	fmull	-48(%rdx)
	faddp	%st, %st(1)
	fldl	(%rcx,%rdi,8)
	movslq	-16(%rax), %rdi
	fmull	-40(%rdx)
	faddp	%st, %st(1)
	fldl	(%rcx,%rdi,8)
	movslq	-12(%rax), %rdi
	fmull	-32(%rdx)
	faddp	%st, %st(1)
	fldl	(%rcx,%rdi,8)
	movslq	-8(%rax), %rdi
	fmull	-24(%rdx)
	faddp	%st, %st(1)
	fldl	(%rcx,%rdi,8)
	movslq	-4(%rax), %rdi
	fmull	-16(%rdx)
	faddp	%st, %st(1)
	fldl	(%rcx,%rdi,8)
	fmull	-8(%rdx)
	cmpl	%ebx, %esi
	faddp	%st, %st(1)
	jne	.L51
	movl	%esi, %eax
	.p2align 4
	.p2align 3
.L52:
	movslq	(%r10,%rax,4), %rdx
	fldl	(%rcx,%rdx,8)
	fmull	(%r9,%rax,8)
	addq	$1, %rax
	cmpl	%eax, %r8d
	faddp	%st, %st(1)
	jg	.L52
	popq	%rbx
	.cfi_def_cfa_offset 8
	fstpl	(%r11)
	ret
	.p2align 4,,10
	.p2align 3
.L50:
	.cfi_restore 3
	fldz
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L53:
	movslq	(%r10,%rax,4), %rdx
	fldl	(%rcx,%rdx,8)
	fmull	(%r9,%rax,8)
	addq	$1, %rax
	cmpq	%rax, %r8
	faddp	%st, %st(1)
	jne	.L53
	fstpl	(%r11)
	ret
	.p2align 4,,10
	.p2align 3
.L54:
	fldz
	fstpl	(%r11)
	ret
	.cfi_endproc
.LFE11:
	.size	knc_lone_scalar, .-knc_lone_scalar
	.p2align 6
	.globl	knc_shape_spmv
	.type	knc_shape_spmv, @function
knc_shape_spmv:
.LFB14:
	.cfi_startproc
	cmpl	%esi, %edi
	jge	.L71
	pushq	%r12
	.cfi_def_cfa_offset 16
	.cfi_offset 12, -16
	movl	%esi, %r11d
	movq	%rcx, %r9
	pushq	%rbp
	.cfi_def_cfa_offset 24
	.cfi_offset 6, -24
	movslq	%edi, %r10
	pushq	%rbx
	.cfi_def_cfa_offset 32
	.cfi_offset 3, -32
	movq	16(%rdx), %r12
	movq	8(%rdx), %rbp
	movq	(%rdx), %rbx
	.p2align 4
	.p2align 3
.L66:
	movsbl	(%rbx,%r10), %ecx
	testl	%ecx, %ecx
	jle	.L67
	movq	(%r12,%r10,8), %rdi
	movq	0(%rbp,%r10,8), %rsi
	fldz
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L65:
	movslq	(%rsi,%rax,4), %rdx
	fldl	(%r9,%rdx,8)
	fmull	(%rdi,%rax,8)
	addq	$1, %rax
	cmpl	%eax, %ecx
	faddp	%st, %st(1)
	jg	.L65
	fstpl	(%r8,%r10,8)
	addq	$1, %r10
	cmpl	%r10d, %r11d
	jg	.L66
.L74:
	popq	%rbx
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbp
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	ret
	.p2align 4,,10
	.p2align 3
.L67:
	.cfi_restore_state
	fldz
	fstpl	(%r8,%r10,8)
	addq	$1, %r10
	cmpl	%r10d, %r11d
	jg	.L66
	jmp	.L74
.L71:
	.cfi_def_cfa_offset 8
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	ret
	.cfi_endproc
.LFE14:
	.size	knc_shape_spmv, .-knc_shape_spmv
	.p2align 6
	.globl	knc_shape_forward
	.type	knc_shape_forward, @function
knc_shape_forward:
.LFB16:
	.cfi_startproc
	testl	%esi, %esi
	jle	.L83
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	movl	%esi, %r10d
	movq	%rcx, %r11
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	xorl	%esi, %esi
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	16(%rdx), %r13
	movq	8(%rdx), %r12
	movq	(%rdx), %rbp
	movq	24(%rdx), %rbx
	.p2align 4
	.p2align 3
.L79:
	movsbl	0(%rbp,%rsi), %ecx
	movq	(%rbx,%rsi,8), %rax
	fldl	(%rax)
	testl	%ecx, %ecx
	fldl	(%r11,%rsi,8)
	jle	.L77
	movq	0(%r13,%rsi,8), %r9
	movq	(%r12,%rsi,8), %rdi
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L78:
	movslq	(%rdi,%rax,4), %rdx
	fldl	(%r8,%rdx,8)
	fmull	(%r9,%rax,8)
	addq	$1, %rax
	cmpl	%eax, %ecx
	fsubrp	%st, %st(1)
	jg	.L78
.L77:
	fldl	(%r8,%rsi,8)
	fmul	%st(2), %st
	faddp	%st, %st(1)
	fdivp	%st, %st(1)
	fstpl	(%r8,%rsi,8)
	addq	$1, %rsi
	cmpq	%r10, %rsi
	jne	.L79
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
.L83:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	ret
	.cfi_endproc
.LFE16:
	.size	knc_shape_forward, .-knc_shape_forward
	.p2align 6
	.globl	knc_shape_backward
	.type	knc_shape_backward, @function
knc_shape_backward:
.LFB17:
	.cfi_startproc
	movq	%rcx, %r9
	movl	%esi, %ecx
	subl	$1, %ecx
	js	.L94
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	movl	%ecx, %ecx
	movq	%rdx, %rdi
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	movl	%esi, %r11d
	movq	%rcx, %rax
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	leaq	0(,%r11,8), %rdx
	negq	%rax
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	movq	24(%rdi), %rbp
	movq	16(%rdi), %r13
	movq	8(%rdi), %r12
	salq	$3, %rax
	addq	%rdx, %rbp
	addq	%rdx, %r9
	addq	%rdx, %r13
	addq	%rdx, %r12
	addq	(%rdi), %r11
	addq	%r8, %rdx
	addq	%rax, %rbp
	leaq	(%r9,%rax), %rbx
	addq	%rax, %r13
	addq	%rax, %r12
	leaq	(%rdx,%rax), %r10
	subq	%rcx, %r11
	.p2align 4
	.p2align 3
.L90:
	movsbl	-1(%r11,%rcx), %esi
	movq	-8(%rbp,%rcx,8), %rax
	fldl	(%rax)
	testl	%esi, %esi
	fldl	-8(%rbx,%rcx,8)
	jle	.L88
	movq	-8(%r13,%rcx,8), %r9
	movq	-8(%r12,%rcx,8), %rdi
	xorl	%eax, %eax
	.p2align 4
	.p2align 3
.L89:
	movslq	(%rdi,%rax,4), %rdx
	fldl	(%r8,%rdx,8)
	fmull	(%r9,%rax,8)
	addq	$1, %rax
	cmpl	%eax, %esi
	fsubrp	%st, %st(1)
	jg	.L89
.L88:
	fldl	-8(%r10,%rcx,8)
	fmul	%st(2), %st
	faddp	%st, %st(1)
	fdivp	%st, %st(1)
	fstpl	-8(%r10,%rcx,8)
	subq	$1, %rcx
	testl	%ecx, %ecx
	jns	.L90
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
.L94:
	.cfi_restore 3
	.cfi_restore 6
	.cfi_restore 12
	.cfi_restore 13
	ret
	.cfi_endproc
.LFE17:
	.size	knc_shape_backward, .-knc_shape_backward
	.globl	knc_shapes
	.section	.rodata
	.align 16
	.type	knc_shapes, @object
	.size	knc_shapes, 24
knc_shapes:
	.quad	knc_shape_spmv
	.quad	knc_shape_forward
	.quad	knc_shape_backward
	.globl	knc_legal
	.align 16
	.type	knc_legal, @object
	.size	knc_legal, 24
knc_legal:
	.quad	knc_csr_scalar
	.quad	knc_hpcg_scalar
	.quad	knc_lone_scalar
	.globl	knc_twin
	.bss
	.align 4
	.type	knc_twin, @object
	.size	knc_twin, 4
knc_twin:
	.zero	4
	.globl	knc_arm
	.align 4
	.type	knc_arm, @object
	.size	knc_arm, 4
knc_arm:
	.zero	4
	.ident	"GCC: (GNU) 16.2.0"
	.section	.note.GNU-stack,"",@progbits
