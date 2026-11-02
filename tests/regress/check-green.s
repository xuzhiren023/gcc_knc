.text
.type affine_f32, @function
affine_f32:
.L32:
 vmulps %zmm0, %zmm1, %zmm2
 vaddps %zmm2, %zmm3, %zmm4
 jne .L32
 ret
.size affine_f32, .-affine_f32
.type affine_f64, @function
affine_f64:
.L64:
 vmulpd %zmm0, %zmm1, %zmm2
 vaddpd %zmm2, %zmm3, %zmm4
 jne .L64
 ret
.size affine_f64, .-affine_f64
.type recurrence_f32, @function
recurrence_f32:
.LR:
 fsubs (%rax)
 jne .LR
 ret
.size recurrence_f32, .-recurrence_f32
