// S1-05: binutils 2.22 must accept the target's default debug format.
// options: -march=knc -O2 -g
int knc_debug(int x) { return x + 1; }
