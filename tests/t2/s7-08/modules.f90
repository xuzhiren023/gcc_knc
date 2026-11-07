! S7-08: module use: a user module, the compiler-provided iso_fortran_env and
! the freshly built ieee_arithmetic module over the S7-07 KNC backend.
module shapes
  implicit none
  private
  public :: box, area, calls
  type :: box
    real(8) :: w, h
  end type box
  integer, protected :: calls = 0
contains
  function area(b) result(r)
    type(box), intent(in) :: b
    real(8) :: r
    r = b%w * b%h
    calls = calls + 1
  end function area
end module shapes

program modules
  use, intrinsic :: iso_fortran_env, only: real32, real64, real128, output_unit
  use, intrinsic :: ieee_arithmetic
  use shapes
  implicit none
  real(8) :: nan, zero, x
  real(10) :: e
  logical :: flag
  type(ieee_round_type) :: mode
  integer :: failures = 0

  call check(real32 == 4 .and. real64 == 8, 'iso_fortran_env kinds 4 and 8')
  call check(real128 == -1, 'iso_fortran_env real128 is -1 without kind 16')
  call check(area(box(2.0d0, 3.0d0)) == 6.0d0 .and. calls == 1, 'user module procedure and protected state')

  nan = ieee_value(nan, ieee_quiet_nan)
  call check(ieee_is_nan(nan) .and. .not. ieee_is_finite(nan), 'ieee_value quiet NaN')
  call check(ieee_support_datatype(x) .and. ieee_support_datatype(e), 'ieee support for kinds 8 and 10')
  call ieee_get_rounding_mode(mode)
  call check(mode == ieee_nearest, 'default rounding mode is nearest')
  call ieee_set_flag(ieee_all, .false.)
  call ieee_get_flag(ieee_divide_by_zero, flag)
  call check(.not. flag, 'flags clear after ieee_set_flag')
  zero = 0.0d0
  x = 1.0d0 / zero
  call ieee_get_flag(ieee_divide_by_zero, flag)
  call check(flag .and. .not. ieee_is_finite(x), 'divide by zero raises the flag')
  call ieee_set_flag(ieee_divide_by_zero, .false.)
  call ieee_get_flag(ieee_divide_by_zero, flag)
  call check(.not. flag, 'flag cleared again')

  if (failures /= 0) stop 1
  write (output_unit, '(A)') 'PASS modules'
contains
  subroutine check(ok, what)
    logical, intent(in) :: ok
    character(len=*), intent(in) :: what
    if (.not. ok) then
      print '(A,1X,A)', 'FAIL', what
      failures = failures + 1
    end if
  end subroutine check
end program modules
