! S9-06: Fortran parallel do with private and reduction, and omp_lib.
! Same output contract as check.h: -DBREAK inverts the first check.
program s9_do
  use omp_lib
  implicit none
  integer, parameter :: n = 100000
  integer :: i, nt, checks, failures
  real(8) :: a(n), s
  integer(8) :: isum
  checks = 0; failures = 0; s = 0; isum = 0; nt = 0
  !$omp parallel do private(i) reduction(+:s, isum)
  do i = 1, n
     a(i) = 2.0d0 * i
     s = s + a(i)
     isum = isum + i
  end do
  !$omp end parallel do
  call check(isum == int(n, 8) * (n + 1) / 2)
  call check(s == real(n, 8) * (n + 1))
  !$omp parallel
  !$omp single
  nt = omp_get_num_threads()
  !$omp end single
  !$omp end parallel
  call check(nt >= 1 .and. a(n) == 2.0d0 * n)
  print '(a,i0)', 'S9-OMP do threads=', nt
  print '(a,a,a,i0,a,i0)', 'S9-OMP do ', merge('FAIL', 'PASS', failures > 0), ' checks=', checks, &
       ' failures=', failures
  if (failures > 0) stop 1
contains
  subroutine check(ok)
    logical, intent(in) :: ok
    logical :: v
    checks = checks + 1
    v = ok
#ifdef BREAK
    if (checks == 1) v = .not. v
#endif
    if (.not. v) then
       failures = failures + 1
       print '(a,i0,a)', 'check ', checks, ' failed'
    end if
  end subroutine check
end program s9_do
