# Building GCC-KNC on an x86_64 Linux host

Status: **derived from the Windows/Cygwin recipe; not yet run on Linux**.
Every shell block below is an unexecuted Linux procedure. Host fixture tests
exercise export integrity and host selection, not a Linux compiler build or
native card execution. The owner runs the first Linux build and the x86 check.

## Sources and release policy

Use `tools/source_release.py` from the reviewed project checkout. The default
project ref is `main`; with `--base` the default GCC ref is `knc`. Explicit refs
must be local branches. Output directories must be empty.

```sh
python3 tools/run.py --name release-project -- \
  python3 tools/source_release.py export --repo . --ref main \
  --output .work/_shared/S13-04/project
python3 tools/run.py --name release-gcc -- \
  python3 tools/source_release.py export --repo .work/_shared/gcc --ref knc \
  --base releases/gcc-16.2.0 --output .work/_shared/S13-04/gcc
```

Each export README names the exact commit; GCC also names the upstream tag and
commit. The bundle has complete reachable history, with no prerequisite bundle.
Published history is retained, including deleted artifacts reported in the
README. The tip must pass the audit. The GCC patch is one squashed binary-capable
diff, including merge resolutions, per the lead's 2026-11-17 decision. Apply it
with `git apply`, not `git am`. The bundle is the authoritative history.

Only committed Git objects enter an export. Untracked source, ignored workspace
files, toolchains, build trees, card outputs and local connection settings do
not enter it. Tracked forbidden paths cause failure rather than silent removal.
The audit checks committed ignore rules case-sensitively, output directories,
artifact extensions and binary signatures, and vendor document names. The
project audit covers every tip file and rejects files over 1 MiB. With `--base`,
the GCC audit covers only files differing from the upstream tag; unchanged
upstream files remain in the bundle and are exempt. GCC has no 1 MiB limit.
GCC historical findings cover fork changes after the tag, while project findings
cover all reachable history. Neither export rewrites that history.
Historical reports inspect artifact paths, sizes and binary signatures in
committed file versions; committed ignore rules are checked at the release tip.
It does not redistribute the external toolchain or sysroot. Shipped
`contrib/knc-vecmath/` sources and their existing license files belong to the
project bundle; `tools/knc_vmath.py` builds them.

```sh
git clone --branch main /path/to/project/source.bundle gcc_knc
cd gcc_knc
mkdir -p .work/_shared
git clone --branch knc /path/to/gcc/source.bundle .work/_shared/gcc
git -C .work/_shared/gcc config core.autocrlf false
git -C .work/_shared/gcc config core.fileMode false
export KNC_GCC_SLOT=1
export SHARED="$PWD/.work/_shared"
export TC="$SHARED/toolchain"
export PREFIX="$SHARED/gcc-knc-16.2.0"
export PATH="$TC/cross/bin:$PREFIX/bin:$PATH"
```

Compare the two checked-out commits with the export READMEs before building.
To use the diff instead, start a separate checkout at the named upstream tag,
then run `git apply --check /path/to/0001-knc-squashed.patch` followed by
`git apply /path/to/0001-knc-squashed.patch`.

## Host and external inputs

Derived package list for Debian/Ubuntu; not validated on the owner's distribution:

```sh
sudo apt-get install build-essential gfortran git python3 bash bison flex \
  texinfo libgmp-dev libmpfr-dev libmpc-dev zlib1g-dev dejagnu expect \
  openssh-client procps
```

The Windows reference manifest records host GCC 14.4.0, Make 4.4.1, Python
3.12.12, target binutils 2.22, and donor GCC 5.1.1. These are reference versions,
not a claim that a Linux build with another version passed. Record actual Linux
versions. Use Python 3.12 for the first reproduction and a modern host C++ compiler.
The KNC compiler's expected version is 16.2.0.

Obtain the **MPSS K1OM binutils 2.22** source package or Linux-host tools from
the owner's original MPSS SDK installation/archive, under its distribution
terms. Ordinary distribution x86 binutils are not a substitute. If that archive
is unavailable, obtain the matching SDK through its original supplier before
continuing; this repository supplies no MPSS download or redistribution.
Install the native Linux tools under `$TC/cross/bin` with names
`k1om-mpss-linux-{as,ld,ar,nm,objdump,readelf}`. Do not copy the Windows executables.
For an authorized extracted binutils source tree, the derived build procedure is:

```sh
mkdir -p "$SHARED/binutils-build"
cd "$SHARED/binutils-build"
bash "$MPSS_BINUTILS_SOURCE/configure" --target=k1om-mpss-linux \
  --prefix="$TC/cross" --disable-nls --disable-werror
make -j8
make install
cd "$SHARED/../.."
```

`MPSS_BINUTILS_SOURCE` must be the absolute path of that extracted source tree.
All build commands must be invoked through `tools/run.py`; for the block above,
put it in a local shell script and run `python3 tools/run.py --name linux-binutils
-- bash /path/to/script`. Do the same for configure/install blocks below.

Obtain a separate card-derived root tree containing `usr/include`, `lib64` and
`usr/lib64`, and the matching MPSS SDK/donor development files. These are private
inputs, not part of either source bundle. Preserve the card runtime libraries
and loader. `tools/toolchain.py` supplies the sysroot layout and development-file
list; do not substitute the host's `/usr/include` or libc.

```sh
python3 tools/run.py --name linux-sysroot -- python3 tools/toolchain.py sysroot \
  --card-root /path/to/card-root \
  --development-files /path/to/donor-sysroot/usr/lib64
```

If running donor comparisons, also build/install the matching MPSS GCC 5.1.1
donor into `$TC/cross`. The donor is a separate external source input; the fork
bundle does not contain it.

## Configure, build and install

Flags below come from `tools/toolchain.py`'s fork configure and
`tools/gcc_build.py`'s `CONFIGURE_FLAGS`. Linux configure detects the host;
do not supply `x86_64-pc-cygwin`.

```sh
mkdir -p "$SHARED/gcc-build"
cd "$SHARED/gcc-build"
bash "$SHARED/gcc/configure" --target=k1om-mpss-linux \
  --prefix="$PREFIX" --with-sysroot="$TC/sysroot" \
  --with-as="$TC/cross/bin/k1om-mpss-linux-as" \
  --with-ld="$TC/cross/bin/k1om-mpss-linux-ld" \
  --enable-languages=c,c++,fortran,lto --enable-clocale=generic \
  --with-libstdcxx-zoneinfo=static --enable-linux-futex \
  --disable-bootstrap --disable-multilib --disable-nls --without-isl \
  --disable-libssp --disable-libquadmath --disable-libquadmath-support \
  --disable-libsanitizer --disable-libitm --disable-libcilkrts \
  --disable-libvtv --disable-libmpx
cd "$SHARED/../.."
python3 tools/run.py --name linux-gcc-build -- python3 tools/gcc_build.py --if-stale
python3 tools/run.py --name linux-gcc-install -- make -C "$SHARED/gcc-build" install
python3 tools/run.py --name linux-vmath -- python3 tools/knc_vmath.py --install
```

Run configure through the wrapper as described above. Build only at the top
level; never invoke make inside `gcc-build/gcc`. `knc_vmath.py` builds and lints
the KNC library and qualification programs, builds host counterparts, and copies
`libknc_vmath.a` beside the build-tree and installed `libgcc.a`. The installed
library directory is `$PREFIX/lib/gcc/k1om-mpss-linux/16.2.0`. These operations
do not run target programs on the host or card.

## Owner verification and return checklist

All commands remain **unrun on Linux**:

```sh
python3 tools/check t0 t1 t2 --compiler gcc16 \
  --record .work/_shared/S13-04/linux-check.txt
python3 tools/check t1 t2 --compiler gcc16 --vmath
python3 tools/run.py --name linux-x86 -- python3 tools/portability.py x86 \
  --tree releases/gcc-16.2.0 --tree knc
```

`tools/check` already invokes the logging wrapper. PASS means exit zero and no
FAIL/infrastructure rows, successful code-generation scans, assembly/lint and
ABI/link checks. T0 skips requiring unavailable optional sibling repositories
must be recorded, not described as executed tests. T2 is link validation only.
The x86 check builds two native host compilers and compares the torture compile
corpus at `-O2` and `-O2 -mavx512f`; expect `different=0`, `errors=0`, and inspect
`both-failed` separately from `identical`. It can take hours; the lead/owner runs
it, not the ticket engineer.

The last full batch reference is **S12-09**, GCC `knc` commit `b2ce6a9eebf`:
`work/tickets/S12-09.md` (15:45 submit, 17:45 approval), with evidence in
`tests/baseline/S12-09-*`, supplied by the lead on 2026-11-17. Expected results:

| Check | Reference result |
| --- | --- |
| T0 | 59 tests PASS |
| T1 | PASS (no numerical count supplied) |
| T2 | PASS (no numerical count supplied) |
| x86 identity | 1962 identical / 0 different |
| Native execute | 1680/1681; `930529-1.c` is a known harness-option case |

The native execute result is historical card evidence, not an expected host
execution result or a card job requested here. Newer exported tips can add tests;
report actual counts and explain differences from this reference instead of
claiming an exact match. `docs/research/m4-result.md` separately records the M4
application gate; its application counts do not replace compiler-batch counts.

For later owner-authorized card use, `tools/card_run` selects native `ssh` and
`/dev/null` on Linux. Supply Linux paths for the identity, known-hosts file and
pin helper in private `config/card.local.json`; select SSH transfer to avoid
requiring a host DMA helper. Keep strict host-key verification. No card jobs
are part of this source-release ticket.

Return the export commit IDs, Linux distribution/architecture, tool versions,
configure arguments, wrapper log paths, T0 test/skip counts, T1/T2 result counts,
and both x86 summary lines. Report failures and infrastructure failures as such.
Include any local source changes and the first relevant error context. Do not
send vendor archives, sysroots, full build trees, or private SSH configuration.
