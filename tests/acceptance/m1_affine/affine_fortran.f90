! Fortran twin of affine_f32.  Uses no libgfortran entry point, so it exercises
! the frontend and backend before the Fortran runtime exists.
subroutine affine_f32_fortran (y, x, a, b, n) bind(c)
  use, intrinsic :: iso_c_binding, only: c_float, c_long
  implicit none
  integer(c_long), intent(in) :: n
  real(c_float), intent(out) :: y(n)
  real(c_float), intent(in) :: x(n)
  real(c_float), intent(in) :: a, b
  integer(c_long) :: i
  do i = 1, n
     y(i) = a * x(i) + b
  end do
end subroutine affine_f32_fortran
