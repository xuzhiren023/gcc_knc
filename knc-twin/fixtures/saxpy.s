# saxpy inner loop in the knc-twin GAS subset (AT&T, k1om)
	.text
L:
	vmovaps (%rax,%rcx,4), %zmm0
	vmovaps (%rbx,%rcx,4), %zmm1
	vfmadd231ps %zmm0, %zmm2, %zmm1
	vmovaps %zmm1, (%rbx,%rcx,4)
	addq $16, %rcx
	decq %rdx
	jnz L
