! S9-06: Fortran sections, atomic, critical and workshare.
! Same output contract as check.h: -DBREAK inverts the first check.
program s9_sections
  use omp_lib
  implicit none
  integer :: checks, failures, hit(3), cnt, crit, nt
  real(8) :: x(1000), y(1000)
  checks = 0; failures = 0; hit = 0; cnt = 0; crit = 0; nt = 0
  x = 1.0d0
  !$omp parallel
  !$omp sections
  !$omp section
  hit(1) = hit(1) + 1
  !$omp section
  hit(2) = hit(2) + 1
  !$omp section
  hit(3) = hit(3) + 1
  !$omp end sections
  !$omp atomic
  cnt = cnt + 1
  !$omp critical
  crit = crit + 2
  !$omp end critical
  !$omp workshare
  y = 3.0d0 * x + 1.0d0
  !$omp end workshare
  !$omp master
  nt = omp_get_num_threads()
  !$omp end master
  !$omp end parallel
  call check(all(hit == 1))
  call check(cnt == nt .and. crit == 2 * nt)
  call check(all(y == 4.0d0))
  print '(a,i0)', 'S9-OMP sections threads=', nt
  print '(a,a,a,i0,a,i0)', 'S9-OMP sections ', merge('FAIL', 'PASS', failures > 0), ' checks=', checks, &
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
end program s9_sections
