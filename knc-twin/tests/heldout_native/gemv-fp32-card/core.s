# Stand-in inner loop for the per-core compute term (not the benchmark's code): one 64-byte line per iteration.
	.text
.Lgemv_fp32:
	vfmadd231ps	(%rax), %zmm1, %zmm0
	addq	$64, %rax
	cmpq	%rdx, %rax
	jne	.Lgemv_fp32
