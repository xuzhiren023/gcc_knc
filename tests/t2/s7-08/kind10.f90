! S7-08: kind 10 (x87 80-bit) arithmetic and formatted conversion, and the
! kind map for the configuration without kind 16.
program kind10
  implicit none
  integer, parameter :: qp = selected_real_kind(18)
  real(qp) :: a, b
  real(8) :: d
  character(len=40) :: buf
  integer :: failures = 0

  call check(qp == 10, 'selected_real_kind(18) is kind 10')
  call check(selected_real_kind(6) == 4 .and. selected_real_kind(15) == 8, 'kinds 4 and 8')
  call check(selected_real_kind(30) == -1, 'no kind for 30 digits (kind 16 disabled)')
  call check(precision(a) == 18 .and. digits(a) == 64 .and. maxexponent(a) == 16384, 'kind 10 model')
  call check(storage_size(a) == 128, 'kind 10 occupies 16 bytes')

  a = 1.0_qp / 3.0_qp
  d = real(a, 8)
  call check(abs(d - 1.0d0 / 3.0d0) <= epsilon(d), 'kind 10 to kind 8 conversion')
  call check(real(d, qp) /= a, 'kind 10 keeps bits that kind 8 loses')
  call check(real(d, qp) - a /= 0.0_qp .and. abs(real(d, qp) - a) < 1.0e-16_qp, 'conversion residual is tiny')
  call check(huge(a) > real(huge(d), qp) .and. real(huge(d), qp) == huge(d), 'kind 8 range inside kind 10')
  call check(int(7.9_qp) == 7 .and. nint(2.5_qp) == 3, 'kind 10 to integer')

  write (buf, '(ES30.22)') a
  read (buf, '(ES30.22)') b
  call check(b == a, 'kind 10 formatted round trip: ' // trim(buf))
  write (buf, '(F6.3)') 2.5_qp
  call check(buf(1:6) == ' 2.500', 'kind 10 fixed format')
  buf = '0.1'
  read (buf, *) b
  call check(b == 0.1_qp, 'kind 10 decimal input is correctly rounded')
  call check(real(b, 8) == 0.1d0, 'rounded kind 10 input converts to kind 8 0.1')
  buf = '1.0e4000'
  read (buf, *) b
  call check(b == 1.0e4000_qp .and. b > huge(d), 'kind 10 exponent beyond kind 8')

  if (failures /= 0) stop 1
  print '(A)', 'PASS kind10'
contains
  subroutine check(ok, what)
    logical, intent(in) :: ok
    character(len=*), intent(in) :: what
    if (.not. ok) then
      print '(A,1X,A)', 'FAIL', what
      failures = failures + 1
    end if
  end subroutine check
end program kind10
