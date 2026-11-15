# Stand-in inner loop for the per-core compute term (not the benchmark's code): one 64-byte line per iteration.
	.text
.Lread:
	vaddps	(%rax), %zmm0, %zmm0
	addq	$64, %rax
	cmpq	%rdx, %rax
	jne	.Lread
