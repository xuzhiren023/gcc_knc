! S7-08: formatted internal and external read and write, and IOSTAT failures
! that must be reported rather than abort.
program io
  implicit none
  character(len=64) :: buf
  character(len=3) :: short
  integer :: ios, n, m, u, failures = 0
  real(8) :: x, y
  real :: s

  write (buf, '(I5,1X,F8.3,1X,A)') 42, 3.125d0, 'txt'
  call check(buf == '   42    3.125 txt', 'formatted internal write')
  read (buf, '(I5,1X,F8.3)') n, x
  call check(n == 42 .and. x == 3.125d0, 'formatted internal read')
  write (buf, *) 1.5e0, 2
  read (buf, *) s, m
  call check(s == 1.5e0 .and. m == 2, 'list-directed internal round trip')
  write (buf, '(ES12.4E2)') -1.0d0 / 3.0d0
  call check(buf(1:12) == ' -3.3333E-01', 'ES edit descriptor: ' // buf(1:12))
  write (buf, '(2(I3,","))') 7, -8
  call check(buf(1:8) == '  7, -8,', 'repeated group format')

  open (newunit=u, status='scratch', form='formatted', action='readwrite', iostat=ios)
  call check(ios == 0, 'open scratch unit')
  write (u, '(A,I3)') 'line', 1
  write (u, '(A,I3)') 'line', 2
  write (u, '(ES12.4)') 1.0d0 / 3.0d0
  rewind (u)
  read (u, '(A4,I3)') buf(1:4), n
  call check(buf(1:4) == 'line' .and. n == 1, 'external formatted read, record 1')
  read (u, '(4X,I3)') n
  call check(n == 2, 'external formatted read, record 2')
  read (u, '(ES12.4)') y
  call check(abs(y - 1.0d0 / 3.0d0) < 1.0d-4, 'external real read')
  read (u, '(A)', iostat=ios) buf
  call check(ios /= 0 .and. is_iostat_end(ios), 'IOSTAT end of file')
  rewind (u)
  read (u, '(I3)', iostat=ios) n
  call check(ios > 0, 'IOSTAT bad integer field from file')
  close (u)

  buf = 'abc'
  read (buf, '(I3)', iostat=ios) n
  call check(ios > 0, 'IOSTAT bad integer field from internal unit')
  write (short, '(I5)', iostat=ios) 12345
  call check(ios /= 0 .and. is_iostat_eor(ios), 'IOSTAT internal record overflow is end-of-record')
  read (buf, '(F4.1)', iostat=ios) x
  call check(ios > 0, 'IOSTAT bad real field')
  open (newunit=u, file='/nonexistent-s7-08/x.dat', status='old', action='read', iostat=ios)
  call check(ios /= 0, 'IOSTAT open of missing file')

  if (failures /= 0) stop 1
  print '(A)', 'PASS io'
contains
  subroutine check(ok, what)
    logical, intent(in) :: ok
    character(len=*), intent(in) :: what
    if (.not. ok) then
      print '(A,1X,A)', 'FAIL', what
      failures = failures + 1
    end if
  end subroutine check
end program io
