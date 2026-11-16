	.file	"trial.c"
	.text
	.p2align 6
	.globl	saxpy
	.type	saxpy, @function
saxpy:
.LFB0:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movl	$1, %eax
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	kmov	%eax, %k1
	andq	$-64, %rsp
	vpackstorelps	%zmm0, -4(%rsp){%k1}
	testq	%rdi, %rdi
	flds	-4(%rsp)
	je	.L22
	leaq	-1(%rdi), %rax
	movq	%rsi, %r9
	cmpq	$14, %rax
	movq	%rdx, %r8
	jbe	.L11
	fstps	-8(%rsp)
	movq	%rdi, %rsi
	vbroadcastss	-8(%rsp), %zmm4
	shrq	$4, %rsi
	leaq	-1(%rsi), %rax
	cmpq	$126, %rax
	vpermf32x4	$0, %zmm4, %zmm1
	vmovaps	%zmm1{aaaa}, %zmm1
	jbe	.L4
	movq	%r9, %rdx
	movq	%r8, %rax
	xorl	%ecx, %ecx
	.p2align 4,,7
	.p2align 3
.L5:
	vmovaps	(%rax), %zmm0
	addq	$1, %rcx
	vprefetch1	2048(%rdx)
	vprefetch0	1024(%rdx)
	vprefetch1	2048(%rax)
	vprefetch0	1024(%rax)
	vfmadd231ps	(%rdx), %zmm1, %zmm0
	addq	$64, %rax
	addq	$64, %rdx
	vmovaps	%zmm0, -64(%rax)
	cmpq	%rsi, %rcx
	jne	.L5
.L6:
	salq	$4, %rsi
	cmpq	%rsi, %rdi
	je	.L1
.L3:
	vpxord	%zmm2, %zmm2, %zmm2
	leaq	0(,%rsi,4), %rax
	addq	%rax, %r9
	addq	%rax, %r8
	xorl	%eax, %eax
	subq	%rsi, %rdi
	setne	%al
	negq	%rax
	andq	%rax, %rdi
	cmpq	$16, %rdi
	sbbq	%rax, %rax
	subq	$16, %rdi
	andq	%rax, %rdi
	movl	$1, %eax
	leaq	16(%rdi), %rcx
	sall	%cl, %eax
	subl	$1, %eax
	kmov	%eax, %k0
	jknzd	.L19, %k0
.L8:
	vpxord	%zmm0, %zmm0, %zmm0
	kmov	%eax, %k7
	jknzd	.L20, %k7
.L9:
	vpxord	%zmm3, %zmm3, %zmm3
	kmov	%eax, %k2
	vblendmps	%zmm0, %zmm3, %zmm0{%k2}
	vfmadd231ps	%zmm1, %zmm2, %zmm0{%k2}
	jknzd	.L21, %k2
	jmp	.L1
	.p2align 4,,10
	.p2align 3
.L22:
	fstp	%st(0)
.L1:
	leave
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
	.p2align 4,,10
	.p2align 3
.L21:
	.cfi_restore_state
	vmovaps	%zmm0, (%r8){%k2}
	leave
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
	.p2align 4,,10
	.p2align 3
.L20:
	.cfi_restore_state
	vmovaps	(%r8), %zmm0{%k7}
	jmp	.L9
	.p2align 4,,10
	.p2align 3
.L19:
	kmov	%eax, %k4
	vmovaps	(%r9), %zmm2{%k4}
	jmp	.L8
	.p2align 4,,10
	.p2align 3
.L4:
	movq	%rsi, %rdx
	xorl	%eax, %eax
	salq	$6, %rdx
	.p2align 4,,7
	.p2align 3
.L7:
	vmovaps	(%r8,%rax), %zmm0
	vfmadd231ps	(%r9,%rax), %zmm1, %zmm0
	vmovaps	%zmm0, (%r8,%rax)
	addq	$64, %rax
	cmpq	%rdx, %rax
	jne	.L7
	jmp	.L6
.L11:
	fstps	-8(%rsp)
	xorl	%esi, %esi
	vbroadcastss	-8(%rsp), %zmm5
	vpermf32x4	$0, %zmm5, %zmm1
	vmovaps	%zmm1{aaaa}, %zmm1
	jmp	.L3
	.cfi_endproc
.LFE0:
	.size	saxpy, .-saxpy
	.p2align 6
	.globl	fsum
	.type	fsum, @function
fsum:
.LFB1:
	.cfi_startproc
	testq	%rdi, %rdi
	je	.L29
	leaq	-1(%rdi), %rax
	cmpq	$2046, %rax
	jbe	.L25
	leaq	-17(%rdi), %rcx
	movq	%rsi, %rax
	andq	$-16, %rcx
	xorl	%edx, %edx
	fldz
	addq	$16, %rcx
	.p2align 4,,7
	.p2align 3
.L26:
	fadds	(%rax)
	addq	$16, %rdx
	fadds	4(%rax)
	vprefetch1	2048(%rax)
	fadds	8(%rax)
	vprefetch0	1024(%rax)
	fadds	12(%rax)
	addq	$64, %rax
	fadds	-48(%rax)
	fadds	-44(%rax)
	fadds	-40(%rax)
	fadds	-36(%rax)
	fadds	-32(%rax)
	fadds	-28(%rax)
	fadds	-24(%rax)
	fadds	-20(%rax)
	fadds	-16(%rax)
	fadds	-12(%rax)
	fadds	-8(%rax)
	fadds	-4(%rax)
	cmpq	%rcx, %rdx
	jne	.L26
	fadds	(%rsi,%rdx,4)
	movq	%rdx, %rax
	notq	%rax
	leaq	(%rax,%rdi), %rcx
	leaq	1(%rdx), %rax
	cmpq	%rdi, %rax
	jnb	.L23
	andl	$1, %ecx
	je	.L27
	fadds	(%rsi,%rax,4)
	leaq	2(%rdx), %rax
	cmpq	%rdi, %rax
	jnb	.L23
	.p2align 4,,7
	.p2align 3
.L27:
	fadds	(%rsi,%rax,4)
	fadds	4(%rsi,%rax,4)
	addq	$2, %rax
	cmpq	%rdi, %rax
	jb	.L27
.L23:
	fstps	-8(%rsp)
	vbroadcastss	-8(%rsp), %zmm0
	ret
	.p2align 4,,10
	.p2align 3
.L25:
	fldz
	leaq	(%rsi,%rdi,4), %rax
	andl	$1, %edi
	je	.L28
	fadds	(%rsi)
	addq	$4, %rsi
	cmpq	%rsi, %rax
	je	.L23
	.p2align 4,,7
	.p2align 3
.L28:
	fadds	(%rsi)
	addq	$8, %rsi
	fadds	-4(%rsi)
	cmpq	%rsi, %rax
	jne	.L28
	jmp	.L23
	.p2align 4,,10
	.p2align 3
.L29:
	fldz
	fstps	-8(%rsp)
	vbroadcastss	-8(%rsp), %zmm0
	ret
	.cfi_endproc
.LFE1:
	.size	fsum, .-fsum
	.p2align 6
	.globl	stencil1
	.type	stencil1, @function
stencil1:
.LFB2:
	.cfi_startproc
	testq	%rdi, %rdi
	movq	%rsi, %r8
	movq	%rdx, %rsi
	je	.L44
	leaq	-1(%rdi), %rax
	cmpq	$14, %rax
	jbe	.L55
	movq	%rdi, %rcx
	shrq	$4, %rcx
	leaq	-1(%rcx), %rax
	movq	%rax, %rdx
	salq	$7, %rdx
	cmpq	$262015, %rdx
	jbe	.L108
	movq	%rcx, %rdx
	xorl	%r10d, %r10d
	andl	$3, %edx
	leaq	4(%r8), %rax
	je	.L52
	cmpq	$1, %rdx
	je	.L92
	cmpq	$2, %rdx
	jne	.L109
.L93:
	vloadunpacklps	-8(%rax), %zmm0
	vloadunpackhps	56(%rax), %zmm0
	vloadunpacklps	(%rax), %zmm1
	vloadunpackhps	64(%rax), %zmm1
	movq	%r10, %rdx
	vprefetch1	2048(%rax)
	salq	$6, %rdx
	vprefetch0	1024(%rax)
	vaddps	-4(%rax), %zmm0, %zmm0
	addq	$1, %r10
	addq	$64, %rax
	vaddps	%zmm1, %zmm0, %zmm0
	vmovnrngoaps	%zmm0, (%rsi,%rdx)
.L92:
	vloadunpacklps	-8(%rax), %zmm0
	vloadunpackhps	56(%rax), %zmm0
	vloadunpacklps	(%rax), %zmm1
	vloadunpackhps	64(%rax), %zmm1
	movq	%r10, %rdx
	addq	$1, %r10
	vprefetch1	2048(%rax)
	vprefetch0	1024(%rax)
	vaddps	-4(%rax), %zmm0, %zmm0
	salq	$6, %rdx
	addq	$64, %rax
	cmpq	%rcx, %r10
	vaddps	%zmm1, %zmm0, %zmm0
	vmovnrngoaps	%zmm0, (%rsi,%rdx)
	je	.L107
.L52:
	vloadunpacklps	-8(%rax), %zmm0
	vloadunpackhps	56(%rax), %zmm0
	vloadunpacklps	(%rax), %zmm1
	vloadunpackhps	64(%rax), %zmm1
	movq	%r10, %rdx
	vprefetch1	2048(%rax)
	salq	$6, %rdx
	vprefetch0	1024(%rax)
	vaddps	-4(%rax), %zmm0, %zmm0
	leaq	64(%rax), %r9
	subq	$-128, %rax
	vprefetch1	2048(%r9)
	vprefetch0	1024(%r9)
	vaddps	%zmm1, %zmm0, %zmm0
	vmovnrngoaps	%zmm0, (%rsi,%rdx)
	leaq	1(%r10), %rdx
	vloadunpacklps	-72(%rax), %zmm0
	vloadunpackhps	-8(%rax), %zmm0
	vloadunpacklps	-64(%rax), %zmm1
	vloadunpackhps	(%rax), %zmm1
	salq	$6, %rdx
	vaddps	-68(%rax), %zmm0, %zmm0
	vprefetch1	2048(%rax)
	vprefetch0	1024(%rax)
	vaddps	%zmm1, %zmm0, %zmm0
	vmovnrngoaps	%zmm0, (%rsi,%rdx)
	movq	%r10, %rdx
	vloadunpacklps	-8(%rax), %zmm0
	vloadunpackhps	56(%rax), %zmm0
	vloadunpacklps	(%rax), %zmm1
	vloadunpackhps	64(%rax), %zmm1
	salq	$6, %rdx
	vaddps	-4(%rax), %zmm0, %zmm0
	leaq	128(%r9), %rax
	vprefetch1	2048(%rax)
	vprefetch0	1024(%rax)
	leaq	192(%r9), %rax
	vaddps	%zmm1, %zmm0, %zmm0
	vmovnrngoaps	%zmm0, 128(%rdx,%rsi)
	leaq	1(%r10), %rdx
	vloadunpacklps	120(%r9), %zmm0
	vloadunpackhps	184(%r9), %zmm0
	vloadunpacklps	128(%r9), %zmm1
	vloadunpackhps	192(%r9), %zmm1
	addq	$4, %r10
	salq	$6, %rdx
	cmpq	%rcx, %r10
	vaddps	124(%r9), %zmm0, %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovnrngoaps	%zmm0, 128(%rdx,%rsi)
	jne	.L52
.L107:
	lock; addl	$0, (%rsp)
.L50:
	salq	$4, %rcx
	cmpq	%rcx, %rdi
	je	.L110
.L46:
	leaq	0(,%rcx,4), %rax
	leaq	-4(%r8,%rcx,4), %rdx
	leaq	(%r8,%rax), %r9
	addq	%rax, %rsi
	vmovaps	.LC2(%rip), %zmm1
	leaq	4(%r8,%rax), %r8
	vpxord	%zmm0, %zmm0, %zmm0
	xorl	%eax, %eax
	vpxord	%zmm2, %zmm2, %zmm2
	subq	%rcx, %rdi
	setne	%al
	negq	%rax
	andq	%rax, %rdi
	cmpq	$16, %rdi
	sbbq	%rax, %rax
	subq	$16, %rdi
	andq	%rax, %rdi
	movl	$1, %eax
	leaq	16(%rdi), %rcx
	sall	%cl, %eax
	subl	$1, %eax
	kmov	%eax, %k1
	kmov	%eax, %k0
	.Lknc_gather420:
	vgatherdps	(%rdx,%zmm1,4), %zmm0{%k1}
	jknzd	.Lknc_gather420, %k1
	jkzd	.L53, %k0
	kmov	%eax, %k5
	vmovaps	(%r9), %zmm2{%k5}
.L53:
	kmov	%eax, %k2
	kmov	%eax, %k3
	vpxord	%zmm3, %zmm3, %zmm3
	vaddps	%zmm2, %zmm0, %zmm3{%k2}
	vpxord	%zmm0, %zmm0, %zmm0
	.Lknc_gather432:
	vgatherdps	(%r8,%zmm1,4), %zmm0{%k3}
	jknzd	.Lknc_gather432, %k3
	vpxord	%zmm1, %zmm1, %zmm1
	vaddps	%zmm0, %zmm3, %zmm1{%k2}
	jkzd	.L44, %k2
	vmovaps	%zmm1, (%rsi){%k2}
.L44:
	ret
	.p2align 4,,10
	.p2align 3
.L108:
	cmpq	$126, %rax
	jbe	.L48
	movq	%rcx, %r9
	xorl	%r11d, %r11d
	andl	$3, %r9d
	leaq	-4(%r8), %rax
	movq	%rsi, %rdx
	je	.L49
	cmpq	$1, %r9
	je	.L88
	cmpq	$2, %r9
	je	.L89
	vloadunpacklps	(%rax), %zmm0
	vloadunpackhps	64(%rax), %zmm0
	vloadunpacklps	8(%rax), %zmm1
	vloadunpackhps	72(%rax), %zmm1
	vprefetch1	2056(%rax)
	vprefetch0	1032(%rax)
	vprefetch1	2048(%rsi)
	vprefetch0	1024(%rsi)
	vaddps	4(%rax), %zmm0, %zmm0
	movl	$1, %r11d
	leaq	60(%r8), %rax
	leaq	64(%rsi), %rdx
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, (%rsi)
.L89:
	vloadunpacklps	(%rax), %zmm0
	vloadunpackhps	64(%rax), %zmm0
	vloadunpacklps	8(%rax), %zmm1
	vloadunpackhps	72(%rax), %zmm1
	vprefetch1	2056(%rax)
	vprefetch0	1032(%rax)
	vprefetch1	2048(%rdx)
	vprefetch0	1024(%rdx)
	vaddps	4(%rax), %zmm0, %zmm0
	addq	$1, %r11
	addq	$64, %rax
	addq	$64, %rdx
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, -64(%rdx)
.L88:
	vloadunpacklps	(%rax), %zmm0
	vloadunpackhps	64(%rax), %zmm0
	vloadunpacklps	8(%rax), %zmm1
	vloadunpackhps	72(%rax), %zmm1
	addq	$1, %r11
	vprefetch1	2056(%rax)
	vprefetch0	1032(%rax)
	vprefetch1	2048(%rdx)
	vaddps	4(%rax), %zmm0, %zmm0
	vprefetch0	1024(%rdx)
	addq	$64, %rax
	addq	$64, %rdx
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, -64(%rdx)
	cmpq	%rcx, %r11
	je	.L50
.L49:
	vloadunpacklps	(%rax), %zmm0
	vloadunpackhps	64(%rax), %zmm0
	vloadunpacklps	8(%rax), %zmm1
	vloadunpackhps	72(%rax), %zmm1
	vprefetch1	2056(%rax)
	vprefetch0	1032(%rax)
	leaq	64(%rax), %r9
	leaq	64(%rdx), %r10
	vaddps	4(%rax), %zmm0, %zmm0
	subq	$-128, %rax
	vprefetch1	2056(%r9)
	vprefetch0	1032(%r9)
	vprefetch1	2048(%r10)
	vprefetch0	1024(%r10)
	vaddps	%zmm1, %zmm0, %zmm0
	vprefetch1	2048(%rdx)
	vmovaps	%zmm0, (%rdx)
	vprefetch0	1024(%rdx)
	vloadunpacklps	-64(%rax), %zmm0
	vloadunpackhps	(%rax), %zmm0
	vloadunpacklps	-56(%rax), %zmm1
	vloadunpackhps	8(%rax), %zmm1
	subq	$-128, %rdx
	addq	$4, %r11
	vaddps	-60(%rax), %zmm0, %zmm0
	vprefetch1	2056(%rax)
	vprefetch0	1032(%rax)
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, -64(%rdx)
	vprefetch1	2048(%rdx)
	vloadunpacklps	(%rax), %zmm0
	vloadunpackhps	64(%rax), %zmm0
	vloadunpacklps	8(%rax), %zmm1
	vloadunpackhps	72(%rax), %zmm1
	vprefetch0	1024(%rdx)
	cmpq	%rcx, %r11
	vaddps	4(%rax), %zmm0, %zmm0
	leaq	128(%r9), %rax
	vprefetch1	2056(%rax)
	vprefetch0	1032(%rax)
	leaq	192(%r9), %rax
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, (%rdx)
	leaq	128(%r10), %rdx
	vloadunpacklps	128(%r9), %zmm0
	vloadunpackhps	192(%r9), %zmm0
	vloadunpacklps	136(%r9), %zmm1
	vloadunpackhps	200(%r9), %zmm1
	vprefetch1	2048(%rdx)
	vprefetch0	1024(%rdx)
	leaq	192(%r10), %rdx
	vaddps	132(%r9), %zmm0, %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, 128(%r10)
	jne	.L49
	jmp	.L50
	.p2align 4,,10
	.p2align 3
.L109:
	vloadunpacklps	-8(%rax), %zmm0
	vloadunpackhps	56(%rax), %zmm0
	vloadunpacklps	(%rax), %zmm1
	vloadunpackhps	64(%rax), %zmm1
	vprefetch1	2048(%rax)
	vprefetch0	1024(%rax)
	vaddps	-4(%rax), %zmm0, %zmm0
	leaq	68(%r8), %rax
	vaddps	%zmm1, %zmm0, %zmm0
	vmovnrngoaps	%zmm0, (%rsi,%r10)
	movl	$1, %r10d
	jmp	.L93
.L55:
	xorl	%ecx, %ecx
	jmp	.L46
.L48:
	movq	%rcx, %r9
	xorl	%eax, %eax
	salq	$6, %r9
	leaq	-64(%r9), %rdx
	shrq	$6, %rdx
	addq	$1, %rdx
	andl	$3, %edx
	je	.L51
	cmpq	$1, %rdx
	je	.L90
	cmpq	$2, %rdx
	je	.L91
	vloadunpacklps	-4(%r8), %zmm0
	vloadunpackhps	60(%r8), %zmm0
	vloadunpacklps	4(%r8), %zmm1
	vloadunpackhps	68(%r8), %zmm1
	movl	$64, %eax
	vaddps	(%r8), %zmm0, %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, (%rsi)
.L91:
	vloadunpacklps	-4(%r8,%rax), %zmm0
	vloadunpackhps	60(%r8,%rax), %zmm0
	vloadunpacklps	4(%r8,%rax), %zmm1
	vloadunpackhps	68(%r8,%rax), %zmm1
	vaddps	(%r8,%rax), %zmm0, %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, (%rsi,%rax)
	addq	$64, %rax
.L90:
	vloadunpacklps	-4(%r8,%rax), %zmm0
	vloadunpackhps	60(%r8,%rax), %zmm0
	vloadunpacklps	4(%r8,%rax), %zmm1
	vloadunpackhps	68(%r8,%rax), %zmm1
	vaddps	(%r8,%rax), %zmm0, %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, (%rsi,%rax)
	addq	$64, %rax
	cmpq	%rax, %r9
	je	.L50
.L51:
	vloadunpacklps	-4(%r8,%rax), %zmm0
	vloadunpackhps	60(%r8,%rax), %zmm0
	vloadunpacklps	4(%r8,%rax), %zmm1
	vloadunpackhps	68(%r8,%rax), %zmm1
	vaddps	(%r8,%rax), %zmm0, %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, (%rsi,%rax)
	vloadunpacklps	60(%r8,%rax), %zmm0
	vloadunpackhps	124(%r8,%rax), %zmm0
	vloadunpacklps	68(%r8,%rax), %zmm1
	vloadunpackhps	132(%r8,%rax), %zmm1
	vaddps	64(%r8,%rax), %zmm0, %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, 64(%rsi,%rax)
	vloadunpacklps	124(%r8,%rax), %zmm0
	vloadunpackhps	188(%r8,%rax), %zmm0
	vloadunpacklps	132(%r8,%rax), %zmm1
	vloadunpackhps	196(%r8,%rax), %zmm1
	vaddps	128(%r8,%rax), %zmm0, %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, 128(%rsi,%rax)
	vloadunpacklps	188(%r8,%rax), %zmm0
	vloadunpackhps	252(%r8,%rax), %zmm0
	vloadunpacklps	196(%r8,%rax), %zmm1
	vloadunpackhps	260(%r8,%rax), %zmm1
	vaddps	192(%r8,%rax), %zmm0, %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, 192(%rsi,%rax)
	addq	$256, %rax
	cmpq	%rax, %r9
	jne	.L51
	jmp	.L50
.L110:
	ret
	.cfi_endproc
.LFE2:
	.size	stencil1, .-stencil1
	.section	.rodata
	.align 64
.LC2:
	.long	0
	.long	1
	.long	2
	.long	3
	.long	4
	.long	5
	.long	6
	.long	7
	.long	8
	.long	9
	.long	10
	.long	11
	.long	12
	.long	13
	.long	14
	.long	15
	.ident	"GCC: (GNU) 16.2.0"
	.section	.note.GNU-stack,"",@progbits
