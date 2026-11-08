! S7-08: non-default lower bounds in static, allocatable, dummy and pointer
! arrays, including bounds remapping.
module bounds_helpers
  implicit none
contains
  logical function reset_to_one(x)
    integer, intent(in) :: x(:)
    reset_to_one = lbound(x, 1) == 1 .and. ubound(x, 1) == 7 .and. x(1) == -3 .and. x(4) == 0
  end function reset_to_one

  logical function keep_lower(x)
    integer, intent(in) :: x(-3:)
    keep_lower = lbound(x, 1) == -3 .and. ubound(x, 1) == 3 .and. x(0) == 0 .and. x(3) == 3
  end function keep_lower
end module bounds_helpers

program bounds
  use bounds_helpers
  implicit none
  integer, target :: a(-3:3)
  integer, allocatable :: b(:, :)
  integer, pointer :: p(:)
  integer :: i, failures = 0

  a = [(i, i=-3, 3)]
  call check(lbound(a, 1) == -3 .and. ubound(a, 1) == 3 .and. a(-3) == -3 .and. a(0) == 0, 'static bounds')
  call check(reset_to_one(a), 'assumed-shape dummy resets lower bound')
  call check(keep_lower(a), 'declared lower bound on dummy')

  allocate (b(0:2, 5:7))
  b = reshape([(i, i=1, 9)], [3, 3])
  call check(all(lbound(b) == [0, 5]) .and. all(ubound(b) == [2, 7]), 'allocatable bounds')
  call check(b(0, 5) == 1 .and. b(2, 7) == 9 .and. b(1, 6) == 5, 'allocatable indexing with offsets')
  b = b + 1
  call check(all(lbound(b) == [0, 5]) .and. b(0, 5) == 2, 'same-shape assignment keeps bounds')
  b = b(1:2, 6:7)
  call check(all(lbound(b) == [1, 1]) .and. all(shape(b) == [2, 2]) .and. b(2, 2) == 10, 'reallocating assignment resets bounds')

  p(10:) => a
  call check(lbound(p, 1) == 10 .and. ubound(p, 1) == 16 .and. p(13) == 0 .and. p(16) == 3, 'pointer bounds remap')
  p => a(3:-3:-3)
  call check(size(p) == 3 .and. p(1) == 3 .and. p(2) == 0 .and. p(3) == -3, 'pointer to negative-stride section')
  p(2) = 99
  call check(a(0) == 99, 'write through strided pointer')
  allocate (p(2:4))
  p = [20, 30, 40]
  call check(lbound(p, 1) == 2 .and. p(4) == 40 .and. sum(p) == 90, 'pointer allocate with bounds')
  deallocate (p)
  call check(.not. associated(p), 'pointer deallocate')

  if (failures /= 0) stop 1
  print '(A)', 'PASS bounds'
contains
  subroutine check(ok, what)
    logical, intent(in) :: ok
    character(len=*), intent(in) :: what
    if (.not. ok) then
      print '(A,1X,A)', 'FAIL', what
      failures = failures + 1
    end if
  end subroutine check
end program bounds
