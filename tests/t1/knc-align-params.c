// S8-14 (E5-13, ADR-0009 point 5 and amendment 1 point 3): the cache sizes
// the loop optimizers read.  L1 32 KB with 64-byte lines; L2 is the smaller
// of the 512 KB cache and the DTLB reach, 64 entries of 4 KiB (S8-12 C4).
// options: -O2 -Q --help=params
// scan-output: ^\s*--param=l1-cache-line-size=\s+64\s*$
// scan-output: ^\s*--param=l1-cache-size=\s+32\s*$
// scan-output: ^\s*--param=l2-cache-size=\s+256\s*$
int knc_cache_params (void) { return 0; }
