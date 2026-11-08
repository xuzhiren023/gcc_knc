! S7-09: one program linked against the installed private prefix, static and shared.
! It touches the IEEE module from the prefix's finclude directory, the allocator,
! formatted and internal I/O and a runtime error path that stays unused.
program runtime
  use ieee_arithmetic
  implicit none
  real(8), allocatable :: a(:)
  real(8) :: nan
  character(len=32) :: text
  integer :: i, failures = 0

  allocate(a(1000))
  a = [(real(i, 8), i = 1, size(a))]
  call check(sum(a) == 500500.0d0, 'allocate and sum')
  write(text, '(F10.3)') a(3) / 4.0d0
  call check(adjustl(text) == '0.750', 'internal formatted write')
  nan = ieee_value(nan, ieee_quiet_nan)
  call check(ieee_is_nan(nan) .and. ieee_support_datatype(nan), 'ieee_arithmetic from the prefix')
  deallocate(a)
  call check(.not. allocated(a), 'deallocate')
  if (failures == 0) print '(A)', 'PASS runtime'
  if (failures /= 0) stop 1

contains
  subroutine check(ok, what)
    logical, intent(in) :: ok
    character(len=*), intent(in) :: what
    if (.not. ok) then
      print '(2A)', 'FAIL ', what
      failures = failures + 1
    end if
  end subroutine check
end program runtime
