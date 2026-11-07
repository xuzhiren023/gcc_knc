! S7-08: noncontiguous array sections through assumed-shape dummies (strided
! descriptors) and explicit-shape dummies (runtime pack and copy-back).
module assumed_helpers
  implicit none
contains
  subroutine double_shape(x)
    integer, intent(inout) :: x(:)
    x = 2 * x
  end subroutine double_shape

  subroutine add_explicit(x, n)
    integer, intent(in) :: n
    integer, intent(inout) :: x(n)
    integer :: i
    do i = 1, n
      x(i) = x(i) + 100
    end do
  end subroutine add_explicit

  subroutine shift_2d(x)
    real(8), intent(inout) :: x(:, :)
    x = x + 0.5d0
  end subroutine shift_2d

  integer function describe(x)
    integer, intent(in) :: x(:)
    describe = -1
    if (lbound(x, 1) == 1 .and. size(x) == 5) describe = sum(x)
  end function describe
end module assumed_helpers

program assumed
  use assumed_helpers
  implicit none
  integer :: a(10), expect(10), i, failures = 0
  real(8) :: g(4, 4), h(4, 4)

  a = [(i, i=1, 10)]
  call check(describe(a(1:9:2)) == 25, 'strided section seen with unit lower bound')
  call double_shape(a(1:9:2))
  expect = [(i, i=1, 10)]
  expect(1:9:2) = 2 * expect(1:9:2)
  call check(all(a == expect), 'assumed-shape stride-2 write-back')

  call add_explicit(a(10:2:-2), 5)
  expect(10:2:-2) = expect(10:2:-2) + 100
  call check(all(a == expect), 'explicit-shape negative-stride copy-back')

  call add_explicit(a(3:5), 3)
  expect(3:5) = expect(3:5) + 100
  call check(all(a == expect), 'explicit-shape contiguous section')

  g = reshape([(real(i, 8), i=1, 16)], [4, 4])
  h = g
  call shift_2d(g(2:4:2, 1:3:2))
  h(2:4:2, 1:3:2) = h(2:4:2, 1:3:2) + 0.5d0
  call check(all(g == h), 'rank-2 strided assumed-shape write-back')
  call check(g(1, 1) == 1.0d0 .and. g(4, 4) == 16.0d0 .and. g(2, 1) == 2.5d0, 'untouched elements kept')

  if (failures /= 0) stop 1
  print '(A)', 'PASS assumed'
contains
  subroutine check(ok, what)
    logical, intent(in) :: ok
    character(len=*), intent(in) :: what
    if (.not. ok) then
      print '(A,1X,A)', 'FAIL', what
      failures = failures + 1
    end if
  end subroutine check
end program assumed
