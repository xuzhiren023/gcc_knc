/* M1 acceptance fixture interface.  Reviewer-owned: see ../README.md.  */
#ifndef KNC_ACCEPT_AFFINE_H
#define KNC_ACCEPT_AFFINE_H

/* Must vectorize: independent outputs, restrict-qualified, runtime length.  */
void affine_f32 (float *restrict y, const float *restrict x,
		 float a, float b, unsigned long n);
void affine_f64 (double *restrict y, const double *restrict x,
		 double a, double b, unsigned long n);

/* Must not vectorize as a plain loop: y[i] depends on y[i-1].  */
void recurrence_f32 (float *restrict y, const float *restrict x,
		     unsigned long n);

/* Fortran BIND(C) twin of affine_f32; linked only with -DKNC_WITH_FORTRAN.  */
void affine_f32_fortran (float *restrict y, const float *restrict x,
			 const float *a, const float *b,
			 const unsigned long *n);

#endif
