! Original reduced polar-transform diagnostic; no benchmark source is copied.
! Full mode preserves the ordered FP operations, call, conversion and tally.
! Other modes are diagnostic counterfactuals, not proposed strict-FP changes.
subroutine TRANSFORM(n, p, q, logs, result) bind(C, name=ENTRY)
  use iso_c_binding
  implicit none
  integer(c_int), value :: n
  real(c_double), intent(in) :: p(n), q(n), logs(n)
  real(c_double), intent(out) :: result(18)
  real(c_double) :: u, v, radius, factor, a, b, logarithm
  integer :: i, bucket
#if MODE >= 3
  interface
    function boundary(x) bind(C, name=BOUNDARY) result(y)
      import c_double
      real(c_double), value :: x
      real(c_double) :: y
    end function
  end interface
#endif
  result = 0
  do i = 1, n
    u = 2 * p(i) - 1
    v = 2 * q(i) - 1
    radius = u*u + v*v
    if (radius > 0 .and. radius <= 1) then
#if MODE == 1
      logarithm = log(radius)
#elif MODE == 2
      logarithm = logs(i)
#else
      logarithm = boundary(logs(i))
#endif
      factor = sqrt(-2 * logarithm / radius)
      a = abs(u * factor)
      b = abs(v * factor)
      bucket = int(max(a,b))
      result(3 + bucket) = result(3 + bucket) + 1
      result(1) = result(1) + a
      result(2) = result(2) + b
    end if
  end do
end subroutine
