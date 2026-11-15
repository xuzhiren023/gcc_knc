# Excerpts of .work/_shared/S12-30/compiler-knc.s (switch-off slot) and compiler-donor.s (GCC 5.1.1),
# the listings of the window-8 gate binary compiler-gate-hpcg (built 2026-11-15 07:50 EST). Unchanged text.
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
	.p2align 4,,15
	.type	donor_csr_raw, @function
donor_csr_raw:
.LFB5:
	.cfi_startproc
	testl	%edi, %edi
	jle	.L13
	pushq	%r12
	.cfi_def_cfa_offset 16
	.cfi_offset 12, -16
	fldz
	xorl	%r12d, %r12d
	pushq	%rbp
	.cfi_def_cfa_offset 24
	.cfi_offset 6, -24
	fld	%st(0)
	pushq	%rbx
	.cfi_def_cfa_offset 32
	.cfi_offset 3, -32
	.p2align 4,,7
	.p2align 3
.L8:
	movslq	(%rsi,%r12,4), %rax
	movl	4(%rsi,%r12,4), %r11d
	cmpl	%eax, %r11d
	jle	.L7
	decl	%r11d
	fld	%st(1)
	subl	%eax, %r11d
	leaq	(%rcx,%rax,8), %rbp
	leaq	(%rdx,%rax,4), %rbx
	incq	%r11
	xorl	%eax, %eax
	.p2align 4,,7
	.p2align 3
.L4:
	movslq	(%rbx,%rax,4), %r10
	fldl	(%r8,%r10,8)
	fmull	0(%rbp,%rax,8)
	incq	%rax
	cmpq	%rax, %r11
	faddp	%st, %st(1)
	jne	.L4
	fstpl	(%r9,%r12,8)
	incq	%r12
	cmpl	%r12d, %edi
	jg	.L8
	fstp	%st(0)
	fstp	%st(0)
.L15:
	popq	%rbx
	.cfi_restore 3
	.cfi_def_cfa_offset 24
	popq	%rbp
	.cfi_restore 6
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_restore 12
	.cfi_def_cfa_offset 8
.L13:
	ret
.L7:
	.cfi_def_cfa_offset 32
	.cfi_offset 3, -32
	.cfi_offset 6, -24
	.cfi_offset 12, -16
	fld	%st(0)
	fstpl	(%r9,%r12,8)
	incq	%r12
	cmpl	%r12d, %edi
	jg	.L8
	fstp	%st(0)
	fstp	%st(0)
	jmp	.L15
	.cfi_endproc
.LFE5:
	.size	donor_csr_raw, .-donor_csr_raw
