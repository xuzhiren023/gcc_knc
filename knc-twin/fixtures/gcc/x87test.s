	.file	"x87test.c"
	.text
	.p2align 6
	.globl	f
	.type	f, @function
f:
.LFB0:
	.cfi_startproc
	fldl	(%rdi)
	fldl	8(%rdi)
	fld	%st(1)
	fsub	%st(1), %st
	fdivl	16(%rdi)
	fxch	%st(2)
	fmulp	%st, %st(1)
	faddp	%st, %st(1)
	fstpl	(%rsi)
	fldl	(%rdi)
	fmull	8(%rdi)
	fsubrl	16(%rdi)
	fstpl	8(%rsi)
	ret
	.cfi_endproc
.LFE0:
	.size	f, .-f
	.p2align 6
	.globl	g
	.type	g, @function
g:
.LFB1:
	.cfi_startproc
	testl	%esi, %esi
	jle	.L9
	leal	-1(%rsi), %eax
	cmpl	$2046, %eax
	jbe	.L5
	leal	-17(%rsi), %ecx
	movq	%rdi, %rax
	andl	$-16, %ecx
	xorl	%edx, %edx
	fldz
	addl	$16, %ecx
	.p2align 4,,7
	.p2align 3
.L6:
	flds	(%rax)
	addl	$16, %edx
	fmul	%st(0), %st
	vprefetch1	2048(%rax)
	vprefetch0	1024(%rax)
	addq	$64, %rax
	faddp	%st, %st(1)
	flds	-60(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-56(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-52(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-48(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-44(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-40(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-36(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-32(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-28(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-24(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-20(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-16(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-12(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-8(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	flds	-4(%rax)
	fmul	%st(0), %st
	faddp	%st, %st(1)
	cmpl	%ecx, %edx
	jne	.L6
	movl	%edx, %eax
	.p2align 4,,7
	.p2align 3
.L7:
	flds	(%rdi,%rax,4)
	addq	$1, %rax
	fmul	%st(0), %st
	faddp	%st, %st(1)
	cmpl	%eax, %esi
	jg	.L7
	fstps	-8(%rsp)
	vbroadcastss	-8(%rsp), %zmm0
	ret
	.p2align 4,,10
	.p2align 3
.L5:
	fldz
	movl	%esi, %esi
	leaq	(%rdi,%rsi,4), %rax
	.p2align 4,,7
	.p2align 3
.L8:
	flds	(%rdi)
	addq	$4, %rdi
	fmul	%st(0), %st
	faddp	%st, %st(1)
	cmpq	%rdi, %rax
	jne	.L8
	fstps	-8(%rsp)
	vbroadcastss	-8(%rsp), %zmm0
	ret
	.p2align 4,,10
	.p2align 3
.L9:
	fldz
	fstps	-8(%rsp)
	vbroadcastss	-8(%rsp), %zmm0
	ret
	.cfi_endproc
.LFE1:
	.size	g, .-g
	.p2align 6
	.globl	h
	.type	h, @function
h:
.LFB2:
	.cfi_startproc
	movl	%edx, %r9d
	movq	%rsi, %r8
	testl	%r9d, %r9d
	jle	.L13
	leal	-1(%r9), %eax
	cmpl	$2046, %eax
	jbe	.L15
	leal	-17(%r9), %r10d
	movq	%rsi, %rdx
	andl	$-16, %r10d
	movq	%rdi, %rax
	addl	$16, %r10d
	xorl	%ecx, %ecx
	.p2align 4,,7
	.p2align 3
.L16:
	movl	(%rdx), %esi
	vprefetch1	2048(%rdx)
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	vprefetch0	1024(%rdx)
	movl	%esi, (%rax)
	vprefetch1	2048(%rax)
	movl	4(%rdx), %esi
	vprefetch0	1024(%rax)
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 4(%rax)
	movl	8(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 8(%rax)
	movl	12(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 12(%rax)
	movl	16(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 16(%rax)
	movl	20(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 20(%rax)
	movl	24(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 24(%rax)
	movl	28(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 28(%rax)
	movl	32(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 32(%rax)
	movl	36(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 36(%rax)
	movl	40(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 40(%rax)
	movl	44(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 44(%rax)
	movl	48(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 48(%rax)
	movl	52(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 52(%rax)
	movl	56(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	movl	%esi, 56(%rax)
	movl	60(%rdx), %esi
	leal	(%rsi,%rsi,2), %r11d
	sarl	$2, %esi
	addl	%r11d, %esi
	addl	$16, %ecx
	movl	%esi, 60(%rax)
	addq	$64, %rdx
	addq	$64, %rax
	cmpl	%r10d, %ecx
	jne	.L16
	movl	%ecx, %eax
	.p2align 4,,7
	.p2align 3
.L17:
	movl	(%r8,%rax,4), %edx
	leal	(%rdx,%rdx,2), %ecx
	sarl	$2, %edx
	addl	%ecx, %edx
	movl	%edx, (%rdi,%rax,4)
	addq	$1, %rax
	cmpl	%eax, %r9d
	jg	.L17
	ret
	.p2align 4,,10
	.p2align 3
.L15:
	salq	$2, %r9
	xorl	%edx, %edx
	.p2align 4,,7
	.p2align 3
.L18:
	movl	(%r8,%rdx), %eax
	leal	(%rax,%rax,2), %ecx
	sarl	$2, %eax
	addl	%ecx, %eax
	movl	%eax, (%rdi,%rdx)
	addq	$4, %rdx
	cmpq	%rdx, %r9
	jne	.L18
.L13:
	ret
	.cfi_endproc
.LFE2:
	.size	h, .-h
	.ident	"GCC: (GNU) 16.2.0"
	.section	.note.GNU-stack,"",@progbits
