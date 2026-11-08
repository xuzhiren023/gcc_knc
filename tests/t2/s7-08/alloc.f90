! S7-08: allocate, reallocating assignment and deallocate through the GCC 16
! KNC runtime. Self-checking; prints PASS alloc and exits 0 on success.
program alloc
  implicit none
  integer, allocatable :: a(:), b(:, :), c(:)
  real(8), allocatable :: r(:)
  character(len=:), allocatable :: s
  integer :: failures = 0, i, stat

  allocate (a(5), stat=stat)
  call check(stat == 0 .and. allocated(a) .and. size(a) == 5, 'allocate with stat')
  a = [(i * i, i=1, 5)]
  a = [a, 36, 49]
  call check(size(a) == 7 .and. a(1) == 1 .and. a(7) == 49, 'reallocate on assignment grows')
  a = a(2:4)
  call check(size(a) == 3 .and. all(a == [4, 9, 16]), 'reallocate from own section')
  allocate (a(3), stat=stat)
  call check(stat /= 0 .and. allocated(a), 'allocate of allocated array reports stat')
  deallocate (a)
  call check(.not. allocated(a), 'deallocate')
  deallocate (a, stat=stat)
  call check(stat /= 0, 'deallocate of unallocated array reports stat')

  allocate (b(2, 3), source=reshape([(i, i=1, 6)], [2, 3]))
  call check(all(shape(b) == [2, 3]) .and. b(1, 1) == 1 .and. b(2, 3) == 6, 'sourced rank-2 allocate')
  b = transpose(b)
  call check(all(shape(b) == [3, 2]) .and. b(3, 1) == 5 .and. b(1, 2) == 2, 'rank-2 reallocate on assignment')

  allocate (c(4))
  c = 7
  call move_alloc(c, a)
  call check(allocated(a) .and. .not. allocated(c) .and. size(a) == 4 .and. all(a == 7), 'move_alloc')

  r = [1.5d0, 2.5d0]
  r = r * 2
  call check(size(r) == 2 .and. r(1) == 3.0d0 .and. r(2) == 5.0d0, 'real(8) auto-allocate')
  r = [r, r]
  call check(size(r) == 4 .and. r(4) == 5.0d0, 'real(8) reallocate on assignment')

  s = 'abc'
  s = s // 'def'
  call check(len(s) == 6 .and. s == 'abcdef', 'deferred-length character reallocate')
  deallocate (s, r, b, a)
  call check(.not. (allocated(s) .or. allocated(r) .or. allocated(b) .or. allocated(a)), 'deallocate list')

  if (failures /= 0) stop 1
  print '(A)', 'PASS alloc'
contains
  subroutine check(ok, what)
    logical, intent(in) :: ok
    character(len=*), intent(in) :: what
    if (.not. ok) then
      print '(A,1X,A)', 'FAIL', what
      failures = failures + 1
    end if
  end subroutine check
end program alloc
