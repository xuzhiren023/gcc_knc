! Independent CSR reduction with NPB-CG's ordered Fortran arithmetic.
subroutine sparse_cg(n, row, a, col, x, rhs, y) bind(C, name=SYMBOL)
  use iso_c_binding
  implicit none
  integer(c_int), value :: n
  integer(c_long_long), intent(in) :: row(0:*)
  integer(c_int), intent(in) :: col(0:*)
  real(c_double), intent(in) :: a(0:*), x(0:*), rhs(0:*)
  real(c_double), intent(out) :: y(0:*)
  integer(c_int) :: i
  integer(c_long_long) :: j
  real(c_double) :: s
  do i=0,n-1
    s=0.0_c_double
    do j=row(i),row(i+1)-1
      s=s+a(j)*x(col(j))
    end do
    y(i)=s
  end do
end subroutine
