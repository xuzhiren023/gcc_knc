# Stand-in inner loop for the per-core compute term (not the benchmark's code): one 64-byte line per iteration.
	.text
.Lrmw:
	vmovaps	(%rax), %zmm0
	vaddps	%zmm1, %zmm0, %zmm0
	vmovaps	%zmm0, (%rax)
	addq	$64, %rax
	cmpq	%rdx, %rax
	jne	.Lrmw
