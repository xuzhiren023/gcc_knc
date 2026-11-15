# Stand-in inner loop for the per-core compute term (not the benchmark's code): one 64-byte line per iteration.
	.text
.Lwrite_ngo:
	vmovnrngoaps	%zmm1, (%rax)
	addq	$64, %rax
	cmpq	%rdx, %rax
	jne	.Lwrite_ngo
