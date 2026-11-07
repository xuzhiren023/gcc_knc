! expect: Kind 16 not supported for type REAL
program kind16
  real(16) :: x
  x = 1.0_16
  print *, x
end program kind16
