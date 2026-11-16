# Building GCC-KNC

GCC-KNC is a cross compiler. It is built and run on a host PC, and it emits code for the Xeon
Phi x100 card (target `k1om-mpss-linux`). There are two ways to build it:

| Path | You need | You get |
|---|---|---|
| [Minimal](#2-minimal-build-imci-assembly-only) | The GCC fork and a host C/C++ compiler | `xgcc` and `cc1`: C, C++ and Fortran to IMCI assembly (`-S`) |
| [Full](#3-full-build-linked-card-programs) | Also the k1om binutils 2.22 and a card sysroot | Linked card programs, the target runtime libraries and `libknc_vmath` |

Section 4 is the Windows + Cygwin host this project was developed on. Every command in it ran on
that host. The Linux steps in sections 2 and 3 are derived from the Windows recipe. Lines marked
**(not yet run on Linux)** have not been tested on a Linux host.

## 1. The sources

### 1.1 The two repositories

```sh
git clone https://github.com/xuzhiren023/gcc_knc.git
cd gcc_knc
mkdir -p .work/_shared
git clone -c core.autocrlf=false -c core.fileMode=false --branch knc \
    https://github.com/xuzhiren023/gcc_16_knc.git .work/_shared/gcc
```

- The fork's `knc` branch is GCC `releases/gcc-16.2.0` plus the KNC changes.
- `.work/` is ignored by git. The project's tools look for the fork at `.work/_shared/gcc`,
  its build at `.work/_shared/gcc-build`, and the KNC toolchain at `.work/_shared/toolchain`.
- On Windows, keep `core.autocrlf=false`. Git for Windows turns it on by default. With CRLF line
  endings, `configure` fails under Cygwin.
- The fork's checkout is about 2.1 GiB, and a build tree 2.3 GiB or more.

### 1.2 The k1om binutils and sysroot

Only the full build needs these. They are not in either repository, and the sysroot is not ours
to redistribute.

| Part | Version | Where it comes from |
|---|---|---|
| `k1om-mpss-linux-as`, `-ld`, `-ar`, `-nm`, `-objdump`, `-readelf` | binutils 2.22+mpss3.8.6 | Built from the GPL binutils source in Intel's MPSS 3.8.6 source release. An MPSS 3.x host install also ships k1om cross binutils (often under `/opt/mpss/<version>/sysroots/`); this project has not tested those. Upstream binutils 2.39 and later have no K1OM support, and upstream releases have no IMCI instructions. |
| Card sysroot | glibc 2.21, MPSS 3.8.6 card image | Copied from a card (`/lib64`, `/usr/lib64`, `/usr/include`), plus the development files `crt1.o`, `crti.o`, `crtn.o`, `Scrt1.o`, `gcrt1.o`, `Mcrt1.o`, `libc.so`, `libc_nonshared.a`, `libpthread_nonshared.a` from an MPSS k1om development sysroot. `tools/toolchain.py sysroot` assembles it. |
| GCC 5.1.1 for k1om (optional) | the "donor" | Only for comparisons and the project's donor tests. Not needed to build or use GCC-KNC. |

The project keeps them in this layout (`toolchain/manifest.json`):

```text
.work/_shared/toolchain/
  cross/bin/k1om-mpss-linux-{as,ld,ar,nm,objdump,readelf}   binutils 2.22
  cross/bin/k1om-mpss-linux-{gcc,g++,gfortran}               GCC 5.1.1 donor (optional)
  sysroot/{lib64,usr/include,usr/lib64}                      card sysroot
  sysroot-development/                                       the development files above
  cygwin/bin/                                                Windows only: the host tools
```

The sysroot does not have a static `libc.a`, so `-static` links do not work with it.

## 2. Minimal build: IMCI assembly only

This needs no binutils and no sysroot. It builds the compiler proper (`make all-gcc`), which
turns C, C++ and Fortran into KNC assembly. It cannot assemble or link.

### 2.1 Host packages (Linux)

**(not yet run on Linux)** The same packages the Cygwin host uses, by their Linux names:

```sh
# Debian, Ubuntu
sudo apt install build-essential g++ gfortran make flex bison texinfo \
    libgmp-dev libmpfr-dev libmpc-dev zlib1g-dev python3 git
# RHEL, Rocky, Alma (enable the CRB or PowerTools repository for texinfo)
sudo dnf install gcc gcc-c++ gcc-gfortran make flex bison texinfo \
    gmp-devel mpfr-devel libmpc-devel zlib-devel python3 git
```

The Windows host used GCC 14.4 as the host compiler.

### 2.2 Configure and build

Run from the project checkout, with the fork at `.work/_shared/gcc` (section 1.1). Use a build
directory outside the source tree.

```sh
mkdir -p .work/_shared/gcc-build && cd .work/_shared/gcc-build
../gcc/configure --target=k1om-mpss-linux --prefix=$PWD/../gcc-install \
    --disable-bootstrap --disable-multilib --disable-nls --without-isl \
    --disable-libssp --disable-libquadmath --disable-libquadmath-support \
    --disable-libsanitizer --disable-libitm --disable-libcilkrts --disable-libvtv \
    --disable-libmpx --enable-languages=c,c++,fortran,lto
make -j8 all-gcc CFLAGS='-O2 -g1' CXXFLAGS='-O2 -g1'
```

- This ran on the Windows host with `--enable-languages=c`, with no k1om binutils on `PATH`
  and no sysroot (section 5). **(not yet run on Linux)**
- Without an assembler, configure cannot probe assembler features and uses its defaults. The
  instructions are the same as a full build's; only directives and local label numbers differ
  (`.align` for `.p2align`, and `.LCFI` labels with a separate unwind table for `.cfi_*`).
- `-O2 -g1` makes the compiler build faster and smaller than GCC's default `-O2 -g`.
- Use `--enable-languages=c` for the fastest build if you need only C.

### 2.3 Produce IMCI assembly

```sh
cat > kernels.c <<'EOF'
void saxpy(int n, float a, const float *restrict x, float *restrict y)
{
    for (int i = 0; i < n; i++)
        y[i] = a * x[i] + y[i];
}
EOF
./gcc/xgcc -B./gcc/ -O2 -march=knc -S kernels.c -o kernels.s
grep -E 'zmm' kernels.s | head
```

`xgcc -B./gcc/` runs the compiler from the build tree without installing it. Look for IMCI
instructions on `zmm` registers, such as `vfmadd231ps`; [USING.md](USING.md) shows the loop
this example gives and has more examples. A file that includes system headers
(`stdio.h`, `math.h`) needs the sysroot, or `-isystem` pointing at a copy of the card's
`usr/include`.

## 3. Full build: linked card programs

This adds the target runtime libraries (libgcc, libstdc++, libgfortran, libatomic, libgomp),
installs a private prefix, and builds `libknc_vmath`. It needs section 1.2.

### 3.1 Configure

The configure that `tools/toolchain.py gcc16` and `tools/gcc_build.py` use. `TC` is the
toolchain directory of section 1.2, as an absolute path.

```sh
TC=$PWD/.work/_shared/toolchain
export PATH=$TC/cross/bin:$PATH
mkdir -p .work/_shared/gcc-build && cd .work/_shared/gcc-build
../gcc/configure --target=k1om-mpss-linux --prefix=$PWD/../gcc-install \
    --with-sysroot=$TC/sysroot \
    --with-as=$TC/cross/bin/k1om-mpss-linux-as \
    --with-ld=$TC/cross/bin/k1om-mpss-linux-ld \
    --disable-bootstrap --disable-multilib --disable-nls --without-isl \
    --disable-libssp --disable-libquadmath --disable-libquadmath-support \
    --disable-libsanitizer --disable-libitm --disable-libcilkrts --disable-libvtv \
    --disable-libmpx \
    --enable-clocale=generic --with-libstdcxx-zoneinfo=static --enable-linux-futex \
    --enable-languages=c,c++,fortran,lto
```

- `--enable-clocale=generic` and `--with-libstdcxx-zoneinfo=static`: the card has no locale data
  and no `zoneinfo` (S9-03).
- `--enable-linux-futex`: libgomp must use futexes; a failed probe stops configure instead of
  falling back silently (S9-06).
- LTO is configured but cannot be used: binutils 2.22 has no plugin support.

### 3.2 Build

```sh
make -j8 all-gcc all-target-libgcc all-target-libgfortran all-target-libstdc++-v3 \
    all-target-libatomic all-target-libgomp CFLAGS='-O2 -g1' CXXFLAGS='-O2 -g1'
```

This is `tools/gcc_build.py`'s make line. It is the only build the project runs on the shared
tree; use it for incremental rebuilds after editing the fork:

```sh
python3 tools/run.py --name gcc-build -- python3 tools/gcc_build.py --if-stale
```

`gcc_build.py` reconfigures a build that lacks the options of section 3.1, but it does not
configure an empty one. Configure once by hand (3.1), or run
`python3 tools/run.py --name gcc16 -- python3 tools/toolchain.py gcc16`, which deletes
`.work/_shared/gcc-build`, configures it as in 3.1 and runs `make all-gcc`.

### 3.3 libknc_vmath and the private prefix

```sh
python3 tools/run.py --name vmath -- python3 tools/knc_vmath.py
python3 tools/run.py --name install -- python3 tools/s7_09_checks.py install
```

- `knc_vmath.py` builds `libknc_vmath.a` from `contrib/knc-vecmath` with the build tree's
  compiler, and the same sources for the host as a reference. The host build needs MPFR.
- `s7_09_checks.py install` runs `make install-gcc install-target-lib*` into a stage and moves it
  to `.work/_shared/gcc-knc-16.2.0`. It then copies `libknc_vmath.a` beside `libgcc.a`, where
  the KNC link spec finds it.
- The prefix is relocatable: the driver finds its own files relative to `bin/`.
- **(not yet run on Linux)** Both scripts were written for the Cygwin host.

The installed compiler is `.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc` (also `g++`,
`gfortran`). [USING.md](USING.md) shows how to use it.

### 3.4 Check the build

```sh
python3 tools/doctor                       # the toolchain of section 1.2
python3 tools/check t0                     # host regression tests (no card)
python3 tools/check t1 t2 --compiler gcc16 # code generation and link checks (no card)
python3 tools/knc_lint kernels.s           # no non-KNC instruction
```

- `tools/doctor` and `tools/check` read `toolchain/manifest.json`, which names Windows `.exe`
  files. **(not yet run on Linux)** They need a Linux manifest first (ticket S13-04).
- `tools/knc_lint` finds the binutils with or without `.exe`. Set `KNC_TOOLCHAIN` to use a
  toolchain directory other than `.work/_shared/toolchain`.
- Native tests (T3) run on the card through `tools/card_run`: **card only**. See
  [card-run.md](card-run.md).

## 4. Windows host with Cygwin

This is the host the project was built on: Windows 10, 12 threads, 16 GB of memory.

### 4.1 Host tools

A private Cygwin in `.work/_shared/toolchain/cygwin` (`toolchain/manifest.json`): GCC 14.4,
make 4.4.1, Python 3.12, flex, bison, texinfo, GMP, MPFR, MPC and zlib development packages.
The k1om binutils in `cross/bin` are Cygwin builds (`.exe`). Native Windows Python 3.8 or newer
runs the project scripts; they switch to the Cygwin Python and `PATH` themselves.

`cygwin/bin` must be on `PATH` when the compiler runs, or `cc1` fails looking for
`cygmpc-3.dll`.

### 4.2 Build

From PowerShell in the project checkout, after section 1:

```powershell
python tools\doctor
python tools\run.py --name gcc16 -- python tools\toolchain.py gcc16
python tools\run.py --name gcc-build -- python tools\gcc_build.py
python tools\run.py --name vmath -- python tools\knc_vmath.py
python tools\run.py --name install -- python tools\s7_09_checks.py install
```

The same configure by hand, from Cygwin `bash`, is section 3.1 with `/cygdrive/c/...` paths.
`tools/run.py` writes the full log to `.work/_state/logs/` and prints a short summary.

### 4.3 Build times on that host

| Step | Time |
|---|---|
| `configure` | about 1 minute |
| Full `all-gcc` rebuild for C at `-O2 -g1` | 1,392 s (S1-07) |
| Rebuild after editing `i386-knc.cc` | about 3 minutes |
| Rebuild after editing an i386 `.md` file | about 5 to 20 minutes |
| Rebuild after editing `i386-knc.h` or `linux-k1om.h` | about 25 minutes |

## 5. Fresh-clone check

Both paths were built from a fresh clone of the fork (`knc` `b2ce6a9eebf`) on the Windows host,
2026-11-15 and 16, with the project's Cygwin toolchain. Both produce IMCI assembly.

```sh
git clone -c core.autocrlf=false --branch knc --single-branch <fork> gcc     # about 1.5 min
```

Without `core.autocrlf=false`, Git for Windows checked out CRLF files and `configure` failed.

| | Full configure (section 3.1, all four languages) | Minimal configure (section 2.2, `--enable-languages=c`) |
|---|---|---|
| binutils, sysroot | `cross/bin` on `PATH`, `--with-as`, `--with-ld`, `--with-sysroot` | none; `cygwin/bin` only on `PATH` |
| `configure` | 62 s | 284 s (host busy) |
| `make all-gcc` | finished in 1,672 s at `nice -j4`, resuming two interrupted runs | 9,256 s at `nice -j4`, one run, below-normal priority on a shared host |
| `xgcc -B gcc/ -O2 -march=knc -S kernels.c` | 207 lines with `zmm`; `tools/knc_lint` exit 0 | the same instructions, directives differ (2.2); assembles with binutils 2.22, `tools/knc_lint` exit 0 |

`kernels.c` held saxpy, a `float` sum and a 3-point stencil. Saxpy and the stencil vectorize
with `vfmadd231ps`/`vfmadd213ps` on `zmm`, `vloadunpack*`/`vpackstore*`, `vprefetch0`/`1`, and
masked `vgatherdps`/`vscatterdps` tails. The sum stays x87 at `-O2`, as
[USING.md](USING.md) explains.

- The first `make -j8` stopped in `libcody` with a Cygwin fork failure ("Resource temporarily
  unavailable", 0xC000012D) while other jobs loaded the host. On a shared host, use `-j4` and a
  lower priority.
- The times are from a busy host and are not benchmarks. An unloaded `-j8` C-only build took
  1,392 s (S1-07).
