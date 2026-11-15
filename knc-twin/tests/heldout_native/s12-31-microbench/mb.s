# Excerpt of .work/_shared/S12-31/build/mb.s (S12-31 window-5 microbench binary, built 2026-11-15 00:04 EST):
# the row-loop functions measured in windows 3 and 5. Unchanged text; other functions omitted.
	.text
	.p2align 6
	.globl	mb_gas_0
	.type	mb_gas_0, @function
mb_gas_0:
	fldz
	.skip 60, 0x90
.Lo_gas_0:
	xorl	%eax, %eax
	.p2align 4
.Li_gas_0:
	movslq	(%r8,%rax,4), %r10
	fldl	(%rdx,%r10,8)
	fmull	(%rcx,%rax,8)
	addq	$1, %rax
	cmpl	%eax, %esi
	faddp	%st, %st(1)
	jg	.Li_gas_0
	subq	$1, %rdi
	jnz	.Lo_gas_0
	fstpl	(%r9)
	ret

	.p2align 6
	.globl	mb_mis_44
	.type	mb_mis_44, @function
mb_mis_44:
	fldz
	.skip 40, 0x90
.Lo_mis_44:
	xorl	%eax, %eax
.Li_mis_44:
	movslq	(%r8,%rax,4), %r10
	fldl	(%rdx,%r10,8)
	fmull	(%rcx,%rax,8)
	addq	$1, %rax
	cmpl	%eax, %esi
	faddp	%st, %st(1)
	jg	.Li_mis_44
	subq	$1, %rdi
	jnz	.Lo_mis_44
	fstpl	(%r9)
	ret

	.p2align 6
	.globl	mb_inc_0
	.type	mb_inc_0, @function
mb_inc_0:
	fldz
	.skip 60, 0x90
.Lo_inc_0:
	xorl	%eax, %eax
.Li_inc_0:
	movslq	(%r8,%rax,4), %r10
	fldl	(%rdx,%r10,8)
	fmull	(%rcx,%rax,8)
	incq %rax
	cmpl	%eax, %esi
	faddp	%st, %st(1)
	jg	.Li_inc_0
	subq	$1, %rdi
	jnz	.Lo_inc_0
	fstpl	(%r9)
	ret

	.p2align 6
	.globl	mb_adj_0
	.type	mb_adj_0, @function
mb_adj_0:
	fldz
	.skip 60, 0x90
.Lo_adj_0:
	xorl	%eax, %eax
.Li_adj_0:
	movslq	(%r8,%rax,4), %r10
	fldl	(%rdx,%r10,8)
	fmull	(%rcx,%rax,8)
	faddp	%st, %st(1)
	addq	$1, %rax
	cmpl	%eax, %esi
	jg	.Li_adj_0
	subq	$1, %rdi
	jnz	.Lo_adj_0
	fstpl	(%r9)
	ret

	.p2align 6
	.globl	mb_mid_0
	.type	mb_mid_0, @function
mb_mid_0:
	fldz
	.skip 60, 0x90
.Lo_mid_0:
	xorl	%eax, %eax
.Li_mid_0:
	movslq	(%r8,%rax,4), %r10
	fldl	(%rdx,%r10,8)
	fmull	(%rcx,%rax,8)
	addq	$1, %rax
	faddp	%st, %st(1)
	cmpl	%eax, %esi
	jg	.Li_mid_0
	subq	$1, %rdi
	jnz	.Lo_mid_0
	fstpl	(%r9)
	ret

	.p2align 6
	.globl	mb_mov_adj_0
	.type	mb_mov_adj_0, @function
mb_mov_adj_0:
	fldz
	.skip 60, 0x90
.Lo_mov_adj_0:
	xorl	%eax, %eax
.Li_mov_adj_0:
	movslq	(%r8,%rax,4), %r10
	fldl	(%rdx,%r10,8)
	fmull	(%rcx,%rax,8)
	faddp	%st, %st(1)
	addq	$1, %rax
	movl	%eax, %r11d
	cmpl	%eax, %esi
	jg	.Li_mov_adj_0
	subq	$1, %rdi
	jnz	.Lo_mov_adj_0
	fstpl	(%r9)
	ret

	.p2align 6
	.globl	mb_mov_split_0
	.type	mb_mov_split_0, @function
mb_mov_split_0:
	fldz
	.skip 60, 0x90
.Lo_mov_split_0:
	xorl	%eax, %eax
.Li_mov_split_0:
	movslq	(%r8,%rax,4), %r10
	fldl	(%rdx,%r10,8)
	fmull	(%rcx,%rax,8)
	faddp	%st, %st(1)
	addq	$1, %rax
	cmpl	%eax, %esi
	movl	%eax, %r11d
	jg	.Li_mov_split_0
	subq	$1, %rdi
	jnz	.Lo_mov_split_0
	fstpl	(%r9)
	ret
