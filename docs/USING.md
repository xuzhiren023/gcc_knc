# Using GCC-KNC

How to compile programs for the Xeon Phi x100 card (Knights Corner). Build the compiler first
([BUILDING.md](BUILDING.md)). Every flag is described in more detail in
[gcc-knc-flags.md](gcc-knc-flags.md).

In the examples, `CC` is the installed driver or the build-tree driver:

```sh
# Installed prefix (full build)
CC=.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc
# Build tree only (minimal build: -S works, linking does not)
CC="$PWD/.work/_shared/gcc-build/gcc/xgcc -B$PWD/.work/_shared/gcc-build/gcc/"
```

`g++` and `gfortran` sit beside `gcc` in the prefix.

## 1. The two flags most people need

| Flags | Use |
|---|---|
| `-O2 -march=knc` | The safe default. Vectorizes with the cheap cost model, prefetches, masks loop tails and keeps IEEE semantics. |
| `-mphinix` | One flag for the measured best set: `-O3 -march=knc -mtune=knc -fprefetch-loop-arrays -munroll-only-small-loops -malign-data=cacheline -fno-math-errno`. Still IEEE. |

`-march=knc` is already the default for `k1om-mpss-linux`, but say it anyway. It also sets
`-mtune=knc`. Do not pass SSE, AVX or MMX options: `-march=knc` rejects them, because KNC has
none of them.

`-mknc-card=3100`, `5100` or `7100` tunes prefetch distances for one card model.
`-mknc-card=native` detects the card on a Linux host with MPSS, or on the card itself. Without
it, the code is the same on every card.

## 2. Assembly

```sh
$CC -O2 -march=knc -S saxpy.c -o saxpy.s
python3 tools/knc_lint saxpy.s      # exit 0: only KNC instructions
```

For this loop:

```c
void saxpy(int n, float a, const float *restrict x, float *restrict y)
{
    for (int i = 0; i < n; i++)
        y[i] = a * x[i] + y[i];
}
```

the inner loop is IMCI on 16 floats at a time: unaligned loads (`vloadunpacklps`/`hps`),
two-level prefetches, a fused multiply-add on `zmm` registers and unaligned stores. This is
the `-O2 -march=knc -S` output of a fresh-clone build of `knc` `b2ce6a9eebf`
([BUILDING.md](BUILDING.md) section 5):

```text
.L5:
        vloadunpacklps  (%rax), %zmm0
        vloadunpackhps  64(%rax), %zmm0
        vloadunpacklps  (%rdx), %zmm5
        vloadunpackhps  64(%rdx), %zmm5
        vprefetch1      2048(%rdx)
        vprefetch0      1024(%rdx)
        addq    $64, %rdx
        vprefetch1      2048(%rax)
        vprefetch0      1024(%rax)
        addq    $64, %rax
        vfmadd231ps     %zmm1, %zmm5, %zmm0
        vpackstorelps   %zmm0, -64(%rax)
        vpackstorehps   %zmm0, (%rax)
        cmpq    %rcx, %rdx
        jne     .L5
```

The last 1 to 15 elements run as one masked vector step (`vgatherdps` and `vscatterdps` under a
`k` mask), not as a scalar loop.

Ask the vectorizer what it did with `-fopt-info-vec-optimized` and `-fopt-info-vec-missed`.

### Floating-point reductions

A plain `float` sum is not vectorized at `-O2`: reordering the additions would change the
result, and GCC-KNC keeps IEEE semantics. Allow it for one file with `-ffast-math` (or just
`-fassociative-math -fno-signed-zeros -fno-trapping-math`), or in a loop with
`#pragma omp simd reduction(+:s)` and `-fopenmp-simd`.

## 3. Linking and running

Linking needs the full build: the k1om binutils and the card sysroot.

```sh
$CC -O2 -march=knc hello.c -o hello.mic
.work/_shared/toolchain/cross/bin/k1om-mpss-linux-readelf -h hello.mic | grep Machine
```

- The output is a K1OM ELF that loads with `/lib64/ld-linux-k1om.so.2` and the card's glibc
  2.21.
- Copy it to the card and run it there, for example `scp hello.mic mic0:/tmp/` and
  `ssh mic0 /tmp/hello.mic`: **card only**. This project runs card jobs through
  `tools/card_run` ([card-run.md](card-run.md)).
- Programs that use GCC-KNC's shared runtimes (`libgcc_s`, `libstdc++`, `libgfortran`,
  `libgomp`) carry `RPATH $ORIGIN/../lib`. On the card, put the program in a `bin` folder and
  the `.so` files it needs, from `gcc-knc-16.2.0/k1om-mpss-linux/lib64/`, in a `lib` folder
  beside it. The card's own GCC 5 runtimes are older and must not be used instead; the link
  refuses an older libgfortran or libgomp with a clear message.
- `-static` does not work with the project's sysroot (it has no `libc.a`).
  `-static-libgcc`, `-static-libstdc++` and `-static-libgfortran` do.
- Floating-point `long double` is the x87 80-bit format in 16 bytes, as with ICC and GCC 5.

## 4. C++ and Fortran

```sh
CXX=.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-g++
FC=.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gfortran
$CXX -O2 -march=knc app.cpp -o app.mic
$FC -O2 -march=knc model.f90 -o model.mic
```

Fortran vectorizes calls to `exp`, `log` and `**` by default, because Fortran has no `errno`.

## 5. OpenMP

```sh
$CC -mphinix -fopenmp omp.c -o omp.mic
# on the card: OMP_NUM_THREADS=240 ./omp.mic    (card only)
```

- The compiler assumes 4 threads per core, the tuned case. If you run 1 to 3 threads per core,
  say so with `--param knc-threads-per-core=N`.
- libgomp's KNC defaults were measured on the card: spread places, short spin, a flat barrier,
  and `MALLOC_ARENA_MAX` from the card's memory unless you set it. Set `OMP_STACKSIZE` for 240
  threads if they use large stack arrays.
- `-fopenmp` links GCC-KNC's `libgomp.so.1`, not Intel's `libiomp5`. Do not mix the two in one
  program.

## 6. Vector math (`libknc_vmath`)

A vectorized loop that calls `expf`, `logf`, `powf`, `exp`, `log` or `pow` calls
`__knc_vmath_<name>_<lanes>` (16 float lanes, 8 double lanes) from `libknc_vmath`. The results
are within 1 ULP, rounded to nearest, with IEEE special values.

```c
#include <math.h>
void f(int n, const float *restrict x, float *restrict y)
{
    for (int i = 0; i < n; i++)
        y[i] = expf(x[i]);
}
```

```sh
$CC -O2 -march=knc -fno-math-errno -S f.c     # calls __knc_vmath_expf_16
$CC -mphinix -S f.c                           # the same: -mphinix adds -fno-math-errno
```

- C and C++ need `-fno-math-errno` (or `-mphinix`): with `errno` the loop stays scalar.
  `-frounding-math` also keeps it scalar.
- The driver adds `libknc_vmath.a` to every link after `-lm`, so no library flag is needed.
  With `-nostdlib` or `-nodefaultlibs`, add it yourself.
- The vector argument ABI: 64-byte vectors (`vector_size (64)`) pass and return in
  `zmm0`-`zmm7`, like scalar `float` and `double`; masks are 16-bit integers
  ([ADR-0014](adr/0014-knc-vector-abi-and-vmath-binding.md)).

## 7. Profile-guided optimization

Standard GCC instrumented PGO works on KNC (S11-17). Training must run on the card.

```sh
$CC -O2 -march=knc -fprofile-generate -fprofile-update=atomic prog.c -o prog-train.mic
# on the card (card only): write the .gcda files to a folder you can copy back
#   GCOV_PREFIX=$PWD/gcda GCOV_PREFIX_STRIP=64 ./prog-train.mic <training input>
# copy the .gcda files back next to the objects, then:
$CC -O2 -march=knc -fprofile-use -Werror=coverage-mismatch prog.c -o prog.mic
```

- Use the same source and flags for both builds, or the profile does not match.
- `-fprofile-update=atomic` keeps the counters right with OpenMP.
- A one-flag PGO driver (build, train, rebuild) is planned, not built.

## 8. Floating point

GCC-KNC keeps IEEE semantics at every `-O` level: subnormals are kept, and vector division and
square root are correctly rounded. ICC's `-mmic` default was faster and less exact. To match it,
use `-ffast-math`, which also flushes subnormals to zero. See
[gcc-knc-flags.md](gcc-knc-flags.md) for the ICC flag map.

## 9. Not available

- IMCI intrinsics (`_mm512_*`): no header yet. Write plain loops and let the vectorizer work.
- LTO (`-flto`): the k1om binutils 2.22 cannot load the plugin.
- Offload (`#pragma offload`, `-fopenmp-targets`): programs run natively on the card.
