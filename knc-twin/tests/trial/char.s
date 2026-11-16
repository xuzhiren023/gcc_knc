# S13-06 consistency kernels: bodies of tests/bench/knc-char s8_compute.py / kernels.py
	.text
.Lc9_vector_u1:
	vaddps	%zmm31, %zmm0, %zmm0
	subq	$1, %rdi
	jnz	.Lc9_vector_u1
.Lc9_vector_u2:
	vaddps	%zmm31, %zmm0, %zmm0
	vaddps	%zmm31, %zmm1, %zmm1
	subq	$1, %rdi
	jnz	.Lc9_vector_u2
.Lc9_vector_u4:
	vaddps	%zmm31, %zmm0, %zmm0
	vaddps	%zmm31, %zmm1, %zmm1
	vaddps	%zmm31, %zmm2, %zmm2
	vaddps	%zmm31, %zmm3, %zmm3
	subq	$1, %rdi
	jnz	.Lc9_vector_u4
.Lc7_reduce_a1:
	vaddps	0(%rsi), %zmm0, %zmm0
	vaddps	64(%rsi), %zmm0, %zmm0
	vaddps	128(%rsi), %zmm0, %zmm0
	vaddps	192(%rsi), %zmm0, %zmm0
	vaddps	256(%rsi), %zmm0, %zmm0
	vaddps	320(%rsi), %zmm0, %zmm0
	vaddps	384(%rsi), %zmm0, %zmm0
	vaddps	448(%rsi), %zmm0, %zmm0
	vaddps	512(%rsi), %zmm0, %zmm0
	vaddps	576(%rsi), %zmm0, %zmm0
	vaddps	640(%rsi), %zmm0, %zmm0
	vaddps	704(%rsi), %zmm0, %zmm0
	vaddps	768(%rsi), %zmm0, %zmm0
	vaddps	832(%rsi), %zmm0, %zmm0
	vaddps	896(%rsi), %zmm0, %zmm0
	vaddps	960(%rsi), %zmm0, %zmm0
	vaddps	1024(%rsi), %zmm0, %zmm0
	vaddps	1088(%rsi), %zmm0, %zmm0
	vaddps	1152(%rsi), %zmm0, %zmm0
	vaddps	1216(%rsi), %zmm0, %zmm0
	vaddps	1280(%rsi), %zmm0, %zmm0
	vaddps	1344(%rsi), %zmm0, %zmm0
	vaddps	1408(%rsi), %zmm0, %zmm0
	vaddps	1472(%rsi), %zmm0, %zmm0
	vaddps	1536(%rsi), %zmm0, %zmm0
	vaddps	1600(%rsi), %zmm0, %zmm0
	vaddps	1664(%rsi), %zmm0, %zmm0
	vaddps	1728(%rsi), %zmm0, %zmm0
	vaddps	1792(%rsi), %zmm0, %zmm0
	vaddps	1856(%rsi), %zmm0, %zmm0
	vaddps	1920(%rsi), %zmm0, %zmm0
	vaddps	1984(%rsi), %zmm0, %zmm0
	subq	$1, %rdi
	jnz	.Lc7_reduce_a1
.Lc7_reduce_a2:
	vaddps	0(%rsi), %zmm0, %zmm0
	vaddps	64(%rsi), %zmm1, %zmm1
	vaddps	128(%rsi), %zmm0, %zmm0
	vaddps	192(%rsi), %zmm1, %zmm1
	vaddps	256(%rsi), %zmm0, %zmm0
	vaddps	320(%rsi), %zmm1, %zmm1
	vaddps	384(%rsi), %zmm0, %zmm0
	vaddps	448(%rsi), %zmm1, %zmm1
	vaddps	512(%rsi), %zmm0, %zmm0
	vaddps	576(%rsi), %zmm1, %zmm1
	vaddps	640(%rsi), %zmm0, %zmm0
	vaddps	704(%rsi), %zmm1, %zmm1
	vaddps	768(%rsi), %zmm0, %zmm0
	vaddps	832(%rsi), %zmm1, %zmm1
	vaddps	896(%rsi), %zmm0, %zmm0
	vaddps	960(%rsi), %zmm1, %zmm1
	vaddps	1024(%rsi), %zmm0, %zmm0
	vaddps	1088(%rsi), %zmm1, %zmm1
	vaddps	1152(%rsi), %zmm0, %zmm0
	vaddps	1216(%rsi), %zmm1, %zmm1
	vaddps	1280(%rsi), %zmm0, %zmm0
	vaddps	1344(%rsi), %zmm1, %zmm1
	vaddps	1408(%rsi), %zmm0, %zmm0
	vaddps	1472(%rsi), %zmm1, %zmm1
	vaddps	1536(%rsi), %zmm0, %zmm0
	vaddps	1600(%rsi), %zmm1, %zmm1
	vaddps	1664(%rsi), %zmm0, %zmm0
	vaddps	1728(%rsi), %zmm1, %zmm1
	vaddps	1792(%rsi), %zmm0, %zmm0
	vaddps	1856(%rsi), %zmm1, %zmm1
	vaddps	1920(%rsi), %zmm0, %zmm0
	vaddps	1984(%rsi), %zmm1, %zmm1
	subq	$1, %rdi
	jnz	.Lc7_reduce_a2
.Lpair_vector_scalar:
	vaddps	%zmm31, %zmm0, %zmm0
	addq	$1, %r8
	vaddps	%zmm31, %zmm1, %zmm1
	addq	$1, %r8
	vaddps	%zmm31, %zmm2, %zmm2
	addq	$1, %r8
	vaddps	%zmm31, %zmm3, %zmm3
	addq	$1, %r8
	vaddps	%zmm31, %zmm4, %zmm4
	addq	$1, %r8
	vaddps	%zmm31, %zmm5, %zmm5
	addq	$1, %r8
	vaddps	%zmm31, %zmm6, %zmm6
	addq	$1, %r8
	vaddps	%zmm31, %zmm7, %zmm7
	addq	$1, %r8
	vaddps	%zmm31, %zmm0, %zmm0
	addq	$1, %r8
	vaddps	%zmm31, %zmm1, %zmm1
	addq	$1, %r8
	vaddps	%zmm31, %zmm2, %zmm2
	addq	$1, %r8
	vaddps	%zmm31, %zmm3, %zmm3
	addq	$1, %r8
	vaddps	%zmm31, %zmm4, %zmm4
	addq	$1, %r8
	vaddps	%zmm31, %zmm5, %zmm5
	addq	$1, %r8
	vaddps	%zmm31, %zmm6, %zmm6
	addq	$1, %r8
	vaddps	%zmm31, %zmm7, %zmm7
	addq	$1, %r8
	vaddps	%zmm31, %zmm0, %zmm0
	addq	$1, %r8
	vaddps	%zmm31, %zmm1, %zmm1
	addq	$1, %r8
	vaddps	%zmm31, %zmm2, %zmm2
	addq	$1, %r8
	vaddps	%zmm31, %zmm3, %zmm3
	addq	$1, %r8
	vaddps	%zmm31, %zmm4, %zmm4
	addq	$1, %r8
	vaddps	%zmm31, %zmm5, %zmm5
	addq	$1, %r8
	vaddps	%zmm31, %zmm6, %zmm6
	addq	$1, %r8
	vaddps	%zmm31, %zmm7, %zmm7
	addq	$1, %r8
	vaddps	%zmm31, %zmm0, %zmm0
	addq	$1, %r8
	vaddps	%zmm31, %zmm1, %zmm1
	addq	$1, %r8
	vaddps	%zmm31, %zmm2, %zmm2
	addq	$1, %r8
	vaddps	%zmm31, %zmm3, %zmm3
	addq	$1, %r8
	vaddps	%zmm31, %zmm4, %zmm4
	addq	$1, %r8
	vaddps	%zmm31, %zmm5, %zmm5
	addq	$1, %r8
	vaddps	%zmm31, %zmm6, %zmm6
	addq	$1, %r8
	vaddps	%zmm31, %zmm7, %zmm7
	addq	$1, %r8
	subq	$1, %rdi
	jnz	.Lpair_vector_scalar
.Lpair_vector_vector:
	vaddps	%zmm31, %zmm0, %zmm0
	vpaddd	%zmm31, %zmm8, %zmm8
	vaddps	%zmm31, %zmm1, %zmm1
	vpaddd	%zmm31, %zmm9, %zmm9
	vaddps	%zmm31, %zmm2, %zmm2
	vpaddd	%zmm31, %zmm10, %zmm10
	vaddps	%zmm31, %zmm3, %zmm3
	vpaddd	%zmm31, %zmm11, %zmm11
	vaddps	%zmm31, %zmm4, %zmm4
	vpaddd	%zmm31, %zmm12, %zmm12
	vaddps	%zmm31, %zmm5, %zmm5
	vpaddd	%zmm31, %zmm13, %zmm13
	vaddps	%zmm31, %zmm6, %zmm6
	vpaddd	%zmm31, %zmm14, %zmm14
	vaddps	%zmm31, %zmm7, %zmm7
	vpaddd	%zmm31, %zmm15, %zmm15
	vaddps	%zmm31, %zmm0, %zmm0
	vpaddd	%zmm31, %zmm8, %zmm8
	vaddps	%zmm31, %zmm1, %zmm1
	vpaddd	%zmm31, %zmm9, %zmm9
	vaddps	%zmm31, %zmm2, %zmm2
	vpaddd	%zmm31, %zmm10, %zmm10
	vaddps	%zmm31, %zmm3, %zmm3
	vpaddd	%zmm31, %zmm11, %zmm11
	vaddps	%zmm31, %zmm4, %zmm4
	vpaddd	%zmm31, %zmm12, %zmm12
	vaddps	%zmm31, %zmm5, %zmm5
	vpaddd	%zmm31, %zmm13, %zmm13
	vaddps	%zmm31, %zmm6, %zmm6
	vpaddd	%zmm31, %zmm14, %zmm14
	vaddps	%zmm31, %zmm7, %zmm7
	vpaddd	%zmm31, %zmm15, %zmm15
	vaddps	%zmm31, %zmm0, %zmm0
	vpaddd	%zmm31, %zmm8, %zmm8
	vaddps	%zmm31, %zmm1, %zmm1
	vpaddd	%zmm31, %zmm9, %zmm9
	vaddps	%zmm31, %zmm2, %zmm2
	vpaddd	%zmm31, %zmm10, %zmm10
	vaddps	%zmm31, %zmm3, %zmm3
	vpaddd	%zmm31, %zmm11, %zmm11
	vaddps	%zmm31, %zmm4, %zmm4
	vpaddd	%zmm31, %zmm12, %zmm12
	vaddps	%zmm31, %zmm5, %zmm5
	vpaddd	%zmm31, %zmm13, %zmm13
	vaddps	%zmm31, %zmm6, %zmm6
	vpaddd	%zmm31, %zmm14, %zmm14
	vaddps	%zmm31, %zmm7, %zmm7
	vpaddd	%zmm31, %zmm15, %zmm15
	vaddps	%zmm31, %zmm0, %zmm0
	vpaddd	%zmm31, %zmm8, %zmm8
	vaddps	%zmm31, %zmm1, %zmm1
	vpaddd	%zmm31, %zmm9, %zmm9
	vaddps	%zmm31, %zmm2, %zmm2
	vpaddd	%zmm31, %zmm10, %zmm10
	vaddps	%zmm31, %zmm3, %zmm3
	vpaddd	%zmm31, %zmm11, %zmm11
	vaddps	%zmm31, %zmm4, %zmm4
	vpaddd	%zmm31, %zmm12, %zmm12
	vaddps	%zmm31, %zmm5, %zmm5
	vpaddd	%zmm31, %zmm13, %zmm13
	vaddps	%zmm31, %zmm6, %zmm6
	vpaddd	%zmm31, %zmm14, %zmm14
	vaddps	%zmm31, %zmm7, %zmm7
	vpaddd	%zmm31, %zmm15, %zmm15
	subq	$1, %rdi
	jnz	.Lpair_vector_vector
.Lagi_gap0:
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	addq	$0, %rsi
	movq	(%rsi), %r8
	subq	$1, %rdi
	jnz	.Lagi_gap0
.Lagi_gap1:
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	addq	$0, %rsi
	nop
	movq	(%rsi), %r8
	subq	$1, %rdi
	jnz	.Lagi_gap1
