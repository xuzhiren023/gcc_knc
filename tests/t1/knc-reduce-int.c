// S5-07 / ADR-0008 point 2, knc-gather-reduce.md section 4.3.
// Two block permutations and two folded swizzles reduce 16 lanes.
// The long carry tree instead uses two block permutations and vpshufd.
// options: -O3 -fwrapv
// scan-asm-func sum_i32: \bvpermf32x4\s+\$78,[\s\S]*\bvpaddd\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvpaddd\s[\s\S]*\bvpaddd\s+%zmm\d+\{badc\}[\s\S]*\bvpaddd\s+%zmm\d+\{cdab\}
// scan-asm-loop-not sum_i32: \([^\n)]*%(?:rsp|rbp)[^\n)]*\)
// scan-asm-func sum_i64: \bvpermf32x4\s+\$78,[\s\S]*\bvpaddsetcd\s[\s\S]*\bvpadcd\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvpaddsetcd\s[\s\S]*\bvpadcd\s[\s\S]*\bvpshufd\s+\$78,[\s\S]*\bvpaddsetcd\s[\s\S]*\bvpadcd\s
// scan-asm-func max_i32: \bvpermf32x4\s+\$78,[\s\S]*\bvpmaxsd\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvpmaxsd\s[\s\S]*\bvpmaxsd\s+%zmm\d+\{badc\}[\s\S]*\bvpmaxsd\s+%zmm\d+\{cdab\}
// scan-asm-func min_i32: \bvpermf32x4\s+\$78,[\s\S]*\bvpminsd\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvpminsd\s[\s\S]*\bvpminsd\s+%zmm\d+\{badc\}[\s\S]*\bvpminsd\s+%zmm\d+\{cdab\}
// scan-asm-func max_u32: \bvpermf32x4\s+\$78,[\s\S]*\bvpmaxud\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvpmaxud\s[\s\S]*\bvpmaxud\s+%zmm\d+\{badc\}[\s\S]*\bvpmaxud\s+%zmm\d+\{cdab\}
// scan-asm-func min_u32: \bvpermf32x4\s+\$78,[\s\S]*\bvpminud\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvpminud\s[\s\S]*\bvpminud\s+%zmm\d+\{badc\}[\s\S]*\bvpminud\s+%zmm\d+\{cdab\}
// scan-asm-func and_i32: \bvpermf32x4\s+\$78,[\s\S]*\bvpandd\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvpandd\s[\s\S]*\bvpandd\s+%zmm\d+\{badc\}[\s\S]*\bvpandd\s+%zmm\d+\{cdab\}
// scan-asm-func or_i32: \bvpermf32x4\s+\$78,[\s\S]*\bvpord\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvpord\s[\s\S]*\bvpord\s+%zmm\d+\{badc\}[\s\S]*\bvpord\s+%zmm\d+\{cdab\}
// scan-asm-func xor_i32: \bvpermf32x4\s+\$78,[\s\S]*\bvpxord\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvpxord\s[\s\S]*\bvpxord\s+%zmm\d+\{badc\}[\s\S]*\bvpxord\s+%zmm\d+\{cdab\}
// scan-asm-func and_i64: \bvpermf32x4\s+\$78,[\s\S]*\bvpandq\s[\s\S]*\bvpandq\s+%zmm\d+\{badc\}[\s\S]*\bvpandq\s+%zmm\d+\{cdab\}
// scan-asm-func or_i64: \bvpermf32x4\s+\$78,[\s\S]*\bvporq\s[\s\S]*\bvporq\s+%zmm\d+\{badc\}[\s\S]*\bvporq\s+%zmm\d+\{cdab\}
// scan-asm-func xor_i64: \bvpermf32x4\s+\$78,[\s\S]*\bvpxorq\s[\s\S]*\bvpxorq\s+%zmm\d+\{badc\}[\s\S]*\bvpxorq\s+%zmm\d+\{cdab\}

#define REDUCE(NAME, T, INIT, OP)                         \
  T NAME (const T *a, int n)                             \
  {                                                     \
    T r = INIT;                                         \
    for (int i = 0; i < n; ++i) r = r OP a[i];           \
    return r;                                           \
  }
REDUCE (sum_i32, int, 0, +)
REDUCE (sum_i64, long, 0, +)
REDUCE (and_i32, int, -1, &)
REDUCE (or_i32, int, 0, |)
REDUCE (xor_i32, int, 0, ^)
REDUCE (and_i64, long, -1, &)
REDUCE (or_i64, long, 0, |)
REDUCE (xor_i64, long, 0, ^)

#define MINMAX(NAME, T, INIT, CMP)                        \
  T NAME (const T *a, int n)                             \
  {                                                     \
    T r = INIT;                                         \
    for (int i = 0; i < n; ++i)                         \
      r = r CMP a[i] ? r : a[i];                        \
    return r;                                           \
  }
MINMAX (max_i32, int, (-__INT_MAX__ - 1), >)
MINMAX (min_i32, int, __INT_MAX__, <)
MINMAX (max_u32, unsigned, 0, >)
MINMAX (min_u32, unsigned, ~0u, <)
