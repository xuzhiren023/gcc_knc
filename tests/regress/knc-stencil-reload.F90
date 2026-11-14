! S11-27: local stencil arrays live across scalar-to-vector broadcasts.
! Compile the driver with -DDRIVER -O0 and the kernel separately at -O2.
! All inputs and expected results are exactly representable in binary64.
#ifdef DRIVER
program check_stencil
  implicit none
  integer i, n, failures
  double precision x(40), y(40), result(40), a(3), want, left, right
  failures = 0
  a = (/ -2.0d0, 0.5d0, 0.25d0 /)
  do i = 1, 40
    x(i) = dble(i)
    y(i) = dble(3*i+1)
  end do
  do n = 4, 34
    result = -999.0d0
    call stencil(n, x, y, result, n, n, n, a)
    do i = 2, n-1
      left = (x(i-1)+y(i-1)) + (x(i+1)+y(i+1))
      right = (x(i-1)-y(i-1)) + (x(i+1)-y(i+1))
      want = y(i) - a(1)*x(i) - a(2)*(x(i)-y(i)+left) - a(3)*right
      if (result(i) /= want) then
        failures = failures + 1
        if (failures <= 12) print *, 'MISMATCH', n, i, result(i), want
      end if
    end do
    if (result(1) /= -999.0d0 .or. result(n) /= -999.0d0) failures = failures + 1
  end do
  if (failures /= 0) then
    print *, 'FAIL stencil', failures
    stop 1
  end if
  print *, 'PASS stencil: lengths 4..34, exact values and boundary guards'
end program
! Separate compilation keeps a call with stack arguments, as in MG's resid.
subroutine observe(p1,p2,p3,p4,p5,p6,p7,p8)
  implicit none
  integer p1,p2,p3,p4,p5,p6,p7,p8
end subroutine
#else
subroutine stencil(n, x, y, result, pad1, pad2, pad3, a)
  implicit none
  integer n, i, pad1, pad2, pad3
  double precision x(n), y(n), a(3), result(n), near(40), far(40)
  ! Keep the producer scalar to isolate the consumer loop seen in serial MG.
  !GCC$ novector
  do i = 1, n
    near(i) = x(i) + y(i)
    far(i) = x(i) - y(i)
  end do
  do i = 2, n-1
    result(i) = y(i) - a(1)*x(i) &
        - a(2)*(far(i)+near(i-1)+near(i+1)) &
        - a(3)*(far(i-1)+far(i+1))
  end do
  call observe(n,n,n,n,n,n,n,n)
end subroutine
#endif
