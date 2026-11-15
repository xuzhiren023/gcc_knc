# S13-06: instruction forms of real GCC-KNC -O2 output that the parser or ISA table lacked.
# Each loop is converted by scripts/from_gcc_s.py in tests/trial/cases (gcc_forms_*).
	.text
# movslq (register and memory), salq/sall, jbe, ja, jnb: functional, exact expected values
.Lscalar:
	movslq	(%r8,%rax,4), %r10
	movslq	%r10d, %r11
	salq	$2, %r11
	addq	%r11, %rsi
	addq	$1, %rax
	cmpq	$3, %rax
	jbe	.Lscalar_next
	cmpq	$4, %rax
	ja	.Lscalar_next
	addq	$100, %rsi
	cmpq	$4, %rax
	jnb	.Lscalar_skip
	addq	$1000, %rsi
.Lscalar_skip:
	sall	$1, %edi
.Lscalar_next:
	cmpq	$4, %rax
	jne	.Lscalar
# vloadunpacklps/hps and vpackstorelps/hps (stencil1 and saxpy prologue of trial.s): timing only
.Lunpack:
	vloadunpacklps	-4(%r8,%rax), %zmm0
	vloadunpackhps	60(%r8,%rax), %zmm0
	vaddps	(%r8,%rax), %zmm0, %zmm0
	vpackstorelps	%zmm0, (%rsi,%rax)
	vpackstorehps	%zmm0, 64(%rsi,%rax)
	addq	$64, %rax
	cmpq	%rdx, %rax
	jne	.Lunpack
