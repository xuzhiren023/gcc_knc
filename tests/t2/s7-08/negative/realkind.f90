! expect: Kind -1 not supported for type REAL
program realkind
  integer, parameter :: k = selected_real_kind(30)
  real(k) :: x
  x = 1
  print *, x
end program realkind
