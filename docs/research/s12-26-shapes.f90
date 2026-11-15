! Original unscored loop-shape inputs for compiler latency experiments.
! Compile as a module; no model data or runtime dependencies are required.
! Callers provide valid bounds, positive log/root inputs and nonzero divisors.
module scalar_shapes
  implicit none
contains
  subroutine fixed_chain(n, a, b, x)
    integer, intent(in) :: n
    real, intent(in) :: a(n), b(n)
    real, intent(inout) :: x(n)
    real :: v, e
    integer :: lane, step
    do lane = 1, n
      v = x(lane)
      do step = 1, 3
        e = exp(b(lane)*v)
        v = v - (a(lane)*e + v)/(a(lane)*b(lane)*e + 1.0)
      end do
      x(lane) = v
    end do
  end subroutine

  subroutine conditional_math(n, active, a, b, y)
    integer, intent(in) :: n
    logical, intent(in) :: active(n)
    real, intent(in) :: a(n), b(n)
    real, intent(inout) :: y(n)
    real :: v
    integer :: lane
    do lane = 1, n
      if (.not. active(lane)) cycle
      v = sqrt(a(lane))/b(lane)
      y(lane) = exp(log(v)*b(lane))/(1.0+v)
    end do
  end subroutine

  subroutine independent_math(n, a, b, y)
    integer, intent(in) :: n
    real, intent(in) :: a(n), b(n)
    real, intent(out) :: y(n)
    integer :: lane
    do lane = n, 1, -1
      y(lane) = (a(lane)/b(lane))**0.25
    end do
  end subroutine

  subroutine prefix_height(n, dz, limit, last)
    integer, intent(in) :: n
    real, intent(in) :: dz(n), limit
    integer, intent(out) :: last
    real :: height
    integer :: lane
    height = 0.0
    last = 0
    do lane = 1, n
      height = height + dz(lane)
      if (height > limit) exit
      last = lane
    end do
  end subroutine

  subroutine forward_solve(n, lower, diagonal, upper, rhs, q, z)
    integer, intent(in) :: n
    real, intent(in) :: lower(n), diagonal(n), upper(n), rhs(n)
    real, intent(out) :: q(n), z(n)
    real :: pivot
    integer :: row
    q(1) = upper(1)/diagonal(1)
    z(1) = rhs(1)/diagonal(1)
    do row = 2, n
      pivot = diagonal(row) - lower(row)*q(row-1)
      q(row) = upper(row)/pivot
      z(row) = (rhs(row)-lower(row)*z(row-1))/pivot
    end do
  end subroutine

  subroutine backward_solve(n, q, z, x)
    integer, intent(in) :: n
    real, intent(in) :: q(n), z(n)
    real, intent(out) :: x(n)
    integer :: row
    x(n) = z(n)
    do row = n-1, 1, -1
      x(row) = z(row) - q(row)*x(row+1)
    end do
  end subroutine

  subroutine flux_difference(nx, nz, ny, flux, weight, value)
    integer, intent(in) :: nx, nz, ny
    real, intent(in) :: flux(nx+1,nz,ny), weight(nz)
    real, intent(inout) :: value(nx,nz,ny)
    integer :: x, z, y
    do y = 1, ny
      do z = 1, nz
        do x = 1, nx
          value(x,z,y) = value(x,z,y) - &
            weight(z)*(flux(x+1,z,y)-flux(x,z,y))
        end do
      end do
    end do
  end subroutine

  subroutine face_limiter(n, capacity, amount, face)
    integer, intent(in) :: n
    real, intent(in) :: capacity(n), amount(n)
    real, intent(inout) :: face(n+1)
    real :: factor
    integer :: cell
    do cell = 1, n
      if (amount(cell) > capacity(cell)) then
        factor = max(0.0, capacity(cell)/(amount(cell)+1.e-12))
        if (face(cell+1) > 0.0) face(cell+1) = factor*face(cell+1)
        if (face(cell) < 0.0) face(cell) = factor*face(cell)
      end if
    end do
  end subroutine

  subroutine pointwise_update(n, old, forcing, mass, result)
    integer, intent(in) :: n
    real, intent(in) :: old(n), forcing(n), mass(n)
    real, intent(out) :: result(n)
    integer :: cell
    do cell = 1, n
      result(cell) = (mass(cell)*old(cell)+forcing(cell))/mass(cell)
    end do
  end subroutine

  subroutine transport_sweep(n, absorption, source, radiation)
    integer, intent(in) :: n
    real, intent(in) :: absorption(n), source(n)
    real, intent(inout) :: radiation(n+1)
    integer :: level
    do level = n, 1, -1
      radiation(level) = source(level) + &
        (1.0-absorption(level))*radiation(level+1)
    end do
  end subroutine
end module
