! S7-09: list-directed output only. Every runtime entry it calls also exists in the
! GCC 5 libgfortran.so.3, so without a guard it links against that runtime silently.
program hello
  print *, 'hello', 2.5
end program hello
