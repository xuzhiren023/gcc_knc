# libstdc++ for KNC: build, ABI, runtime, default dialect, testing (E6-06 input)

S9-02, 2026-11-08. Static research: no GCC build, no configure run, no card job. The only host
commands were `readelf` on the sysroot, `xgcc -dM -E` on an empty file with the already-built
GCC 16 driver, and a Python comparison of symbol tables; all through `tools/run.py`
(logs `.work/_state/logs/S9_02_abi-20261108-030928.log`, `S9_02_macros-20261108-030727.log`;
script and output in `.work/_shared/S9-02/`).

**Proven** = read in a source file, an ELF table or a compiler macro dump, or a settled ticket
fact. **Inferred** = a consequence that has not been built or run. **Unknown** = needs the build
or the card.

Paths without a prefix are relative to `.work/_shared/gcc` (branch `knc`, HEAD `497bbe8bedf`;
the checked-out `s7/S7-10` is identical to `knc` in `libstdc++-v3`, `libatomic`,
`gcc/c-family` and `gcc/config/i386`). `SYS:` is `.work/_shared/toolchain/sysroot`
(glibc 2.21: `SYS:usr/include/features.h:357`; kernel headers 2.6.38:
`SYS:usr/include/linux/version.h:1`, `LINUX_VERSION_CODE 132646`). `DONOR:` is
`SYS:usr/lib64/libstdc++.so.6.0.21` (GCC 5.1, `__GLIBCXX__ 20150423`,
`SYS:usr/include/c++/k1om-mpss-linux/bits/c++config.h:34`).

## Summary

- **Build (proven at source level):** nothing in libstdc++-v3 needs glibc newer than 2.21 or a
  kernel newer than 2.6.38; the missing glibc features (`getentropy`, `pthread_cond_clockwait`,
  `copy_file_range`, `strtof128`, `__libc_single_threaded`) all have configure probes and
  fallbacks. `configure.host` has no `k1om` case, so the library configures as a generic CPU, which
  on KNC is the right thing (no SSE code paths) but leaves no ABI baseline. `--enable-languages=c++`
  also adds libatomic, which configures generic for `k1om`; libitm, libvtv and libsanitizer mark
  `k1om` unsupported by themselves.
- **ABI (proven):** GCC 16's version nodes are a superset of the donor's 35. At the symbol level,
  5,242 donor symbols compared against GCC 16's x86_64 baseline leave 75 missing, 72 of them for
  one reason: the donor was built with the **generic C-locale model** (`__c_locale` = `int*`,
  mangled `Pi`), while GCC 16 defaults Linux to the `gnu` model (`P15__locale_struct`). Build ours
  with `--enable-clocale=generic` and the export set is a superset (inferred). Install it private,
  like `libgcc_s` (S7-06) and `libgfortran` (S7-09): the card's `libzypp` and `libcoi_device`
  need the donor `/usr/lib64/libstdc++.so.6`.
- **Runtime (proven at source level, unknown on the card):** exceptions and RTTI need only
  `GCC_3.0`/`GCC_3.3`/`GCC_4.2.0` from `libgcc_s`, which S7-05/S7-06 proved. Threads work with
  `-pthread` (glibc 2.21 keeps libpthread separate). Atomics of 1 to 8 bytes are inline; 16 bytes
  need a k1om libatomic that does not exist yet. `std::filesystem` and `<random>` have all they
  need; `random_device` is `/dev/urandom`. `hardware_destructive_interference_size` is 64.
- **Default dialect:** GCC 16 defaults to `gnu++20`; the corpus's only C++ program (HPCG) shows no
  C++20-sensitive construct. No KNC-specific default is warranted.
- **Testing:** DejaGnu cannot drive the card (lead-only `tools/card_run`), so: host
  `check-compile`, a k1om ABI baseline with `check-abi`, and a flat batch of self-contained
  `dg-do run` executables through `card_run --file-list` (2,224 of 4,004 run tests have no
  directive requirements).

## 1. Build: `--enable-languages=c++` and libstdc++-v3 for `k1om-mpss-linux`

### 1.1 What the top level builds (proven)

- `configure.ac:158` lists `target-libstdc++-v3`; `configure.ac:528-536` disables it only with
  `--disable-libstdcxx`, and `configure.ac:665-690` disables it by target only for VxWorks, WinCE,
  avr, bpf and ft32. `k1om-*-linux*` therefore builds libstdc++ once `c++` is enabled.
- The current GCC 16 configure (`tools/toolchain.py:63-72`) has `--enable-languages=c,fortran`
  and disables libssp, libquadmath, libsanitizer, libitm, libcilkrts, libvtv, libmpx and libgomp.
  The donor's own configure (`tools/toolchain.py:121-130`) had `c,c++,fortran`,
  `--enable-threads=posix`, `--enable-shared` and the same disables.
- libatomic: `libatomic/configure.tgt:86` matches only `i[3456]86 | x86_64`; `k1om` falls to
  `*) ARCH="${target_cpu}"` (`:144`), has no `config/k1om` directory (`:147-149`), and
  `*-*-linux*` adds `posix` (`:175-179`). Result: the generic, lock-based libatomic with no x86
  `cmpxchg16b` ifunc. Inferred: it builds; needed for 16-byte `std::atomic` (section 3.4).
- libitm (`libitm/configure.tgt:122-128`, `test -d config/$ARCH || UNSUPPORTED=1`), libvtv
  (`libvtv/configure.tgt:56`) and libsanitizer (`libsanitizer/configure.tgt:88-89`) are
  `UNSUPPORTED` for `k1om` on their own; the explicit `--disable-*` flags stay harmless.

### 1.2 How libstdc++ configures as a cross (proven)

- `libstdc++-v3/configure.ac:36-58`: `build != host` sets `GLIBCXX_IS_NATIVE=false` and calls
  `GCC_NO_EXECUTABLES`. `configure.ac:277-345`: the native branch is skipped and
  `GLIBCXX_CROSSCONFIG` (`:494`) runs the `*-linux*` block of `crossconfig.m4:177-192`, which
  still performs link tests (`GLIBCXX_CHECK_LINKER_FEATURES`, `GLIBCXX_CHECK_MATH_SUPPORT`,
  `GLIBCXX_CHECK_STDLIB_SUPPORT`, `GCC_CHECK_TLS`, `AC_CHECK_FUNCS`). Link tests against the
  sysroot are the same mechanism S7-08 used for libgfortran, which built (`CURRENT_STATE.md:68`).
- `crossconfig.m4:182-183` hard-codes `_GLIBCXX_USE_DEV_RANDOM` and `_GLIBCXX_USE_RANDOM_TR1`.
- `AC_CHECK_FUNCS` in `crossconfig.m4:185-190` and the sysroot: `__cxa_thread_atexit_impl`
  (`GLIBC_2.18`), `aligned_alloc` (`GLIBC_2.16`), `timespec_get` (`GLIBC_2.16`), `sockatmark`,
  `uselocale` (`GLIBC_2.14`), `secure_getenv` (`GLIBC_2.17`) are all in `SYS:lib64/libc.so.6`
  (readelf, dynamic symbols; the libc's newest node is `GLIBC_2.18`, so glibc 2.21 adds no node
  after 2.18). The donor's own c++config lacks `__cxa_thread_atexit_impl`
  (`SYS:usr/include/c++/k1om-mpss-linux/bits/c++config.h:1187`), so ours will differ there; both
  implementations sit behind the exported `__cxa_thread_atexit`.

### 1.3 CPU and OS selection (proven)

- `libstdc++-v3/configure.host:119-121` maps `i[567]86 | x86_64` to `cpu/i486`; `k1om` matches
  nothing and there is no `config/cpu/k1om` (`:132-136`), so `cpu_include_dir=cpu/generic`
  (`:144`). Effects: `config/cpu/generic/opt/bits/opt_random.h` (no SSE3 `normal_distribution`),
  generic `atomicity.h` through `__atomic` builtins, `atomic_flags` empty (`:172-174`, used only
  by `check-parallel`), and **no `abi_baseline_pair`** (`:354-366`): `check-abi` has no baseline.
  The same block picks the baseline from `config/abi/post/${host_cpu}-linux-gnu` when `try_cpu` is
  generic (`:358-365`), so adding `config/abi/post/k1om-linux-gnu/baseline_symbols.txt` is enough.
- `configure.host:277` selects `os/gnu-linux` for `*-linux*`. Its `os_defines.h` version gates:
  `__GLIBC_PREREQ(2,15)` and `(2,23)` are met (`:44-50`); `_GLIBCXX_HAVE_FLOAT128_MATH` needs 2.26
  (`:55-60`): **off**; `_GLIBCXX_NATIVE_THREAD_ID` needs 2.27 (`:71-80`): uses the
  `__gthread_active_p()` form; `_GLIBCXX_GTHREAD_USE_WEAK 0` needs 2.34 (`:83-86`): **pthread
  symbols stay weak references** (section 3.3).

### 1.4 Probes that will turn features off, and what replaces them (proven)

| Probe (`libstdc++-v3/acinclude.m4`) | Sysroot fact | Result |
| --- | --- | --- |
| `GLIBCXX_CHECK_X86_RDRAND` `:4341-4356`, `_RDSEED` `:4360-4375` | case matches `i?86-*-* \| x86_64-*-*` only, not `k1om-*-linux*` | `_GLIBCXX_X86_RDRAND/RDSEED` undefined, as in the donor (`c++config.h:1404`). Correct for KNC, which has no `rdrand`. |
| `GLIBCXX_CHECK_GETENTROPY` `:5223-5240`, `_ARC4RANDOM` `:5244-5260` | `SYS:usr/include/sys/random.h` absent; no `arc4random` in `stdlib.h` | `random_device` uses `/dev/urandom` (`src/c++11/random.cc:74-82`, `:88-95`). |
| `GLIBCXX_CHECK_PTHREAD_COND_CLOCKWAIT` `:4485-4505` (called `configure.ac:241-247`) | `SYS:usr/include/pthread.h:1002` has `pthread_cond_timedwait` only (clockwait is glibc 2.30) | `condition_variable` uses `system_clock` internally (`include/std/condition_variable:74-79`). |
| `GLIBCXX_CHECK_FILESYSTEM_DEPS` `:4807-4910` | `d_type` (`SYS:usr/include/bits/dirent.h:52`), `realpath` (`stdlib.h:733`), `utimensat`, `fchmodat`, `fchmod` (`sys/stat.h:296-371`), `truncate`, `linkat`, `symlinkat` (`unistd.h:796-1016`), `sendfile` (`sys/sendfile.h:33`) present; `copy_file_range` absent (glibc 2.27) | all `_GLIBCXX_USE_*` on except `COPY_FILE_RANGE`; `copy_file` takes the `sendfile` path (`src/filesystem/ops-common.h:52-57`, `:406`). |
| `GLIBCXX_ENABLE_LIBSTDCXX_TIME` auto `:1790-1800` | `clock_gettime@@GLIBC_2.17` in libc | monotonic and realtime clocks, `nanosleep`, `sched_yield` on. |
| `GCC_LINUX_FUTEX` (`configure.ac:530`, `config/futex.m4:8-27`) | `SYS:usr/include/linux/futex.h` present | `_GLIBCXX_HAVE_LINUX_FUTEX` (section 3.3). |
| `GLIBCXX_CHECK_GTHREADS` `:4223-4316` | `gthr-posix.h`, `pthread_mutex_timedlock` (`pthread.h:769`), `pthread_rwlock_t` | `_GLIBCXX_HAS_GTHREADS`, `_GTHREAD_USE_MUTEX_TIMEDLOCK 1`, `_GLIBCXX_USE_PTHREAD_RWLOCK_T`. |
| `GLIBCXX_CHECK_GET_NPROCS` `:4380-4396` | `sys/sysinfo.h` `get_nprocs` (glibc) | `hardware_concurrency()` = online CPUs (section 3.3). |
| `GLIBCXX_ENABLE_FLOAT128` `:3516-3550` | compile test: `__float128` distinct from `double` and `long double`; `__SIZEOF_FLOAT128__ 16`, `__FLT128_MANT_DIG__ 113`, `__LDBL_MANT_DIG__ 64` (macro dump) | on; `config/abi/pre/float128.ver` appended (`configure.ac:175-177`), giving `CXXABI_FLOAT128` as in the donor. |
| `GLIBCXX_CHECK_SDT_H` `:4668` | `SYS:usr/include/sys/sdt.h` absent | no SystemTap probes. |
| `GLIBCXX_CHECK_UCHAR_H` `:2407` | `uchar.h` present; `c8rtomb` (glibc 2.36) absent | C++11 `<cuchar>` on, the C++20 `char8_t` conversions off. |
| `GLIBCXX_ENABLE_CLOCALE` auto `:2782-2808` | `linux*` selects `gnu` | **differs from the donor's `generic`**; see section 2.2. Use `--enable-clocale=generic`. |
| `GLIBCXX_ZONEINFO_DIR` `:5564-5576` | default `/usr/share/zoneinfo`; the sysroot has no `usr/share/zoneinfo` | `chrono::tzdb` fails at run time unless `--with-libstdcxx-zoneinfo=static` embeds `tzdata.zi`. Card content unknown. |
| `GLIBCXX_ENABLE_BACKTRACE` auto `:5447-5454` | hosted | builds `libstdc++exp` with libbacktrace. Inferred buildable; `--disable-libstdcxx-backtrace` is the fallback. |
| `GLIBCXX_ENABLE_SYMVERS` `:3963`, `:4040-4061` | needs a shared `libgcc_s` (S7-06) and GNU ld >= 2.14 (`:4065`) | gnu symbol versioning on. |
| `GLIBCXX_CHECK_LINKER_FEATURES` `:198-242`, `:285-301` | `k1om-mpss-linux-ld` is GNU Binutils 2.22.52.20120302 (host `--version`); `--gc-sections` needs > 2.16.02 (`:240`); `-z relro` by `ld --help` (`:299`) | both on (inferred: the probes pass). |
| `GLIBCXX_DEFAULT_ABI` `:4723-4741` | default `new` | `_GLIBCXX_USE_CXX11_ABI 1`, same as the donor (`c++config.h:212`). |

### 1.5 Kernel requirements (proven at source level)

`src/c++11/futex.cc:42-48` and `src/c++20/atomic.cc:116-157` use `FUTEX_WAIT` (0), `FUTEX_WAKE`
(1), `FUTEX_WAIT_BITSET` (9), `FUTEX_PRIVATE_FLAG` (128) and `FUTEX_CLOCK_REALTIME` (256). Linux
added these in 2.6.0, 2.6.22, 2.6.25 and 2.6.28 (futex(2) man page), all before 2.6.38, and
`futex.cc:58-59` keeps run-time fallbacks for `ENOSYS`. No other syscall in `src/` is newer than
`sendfile` and `utimensat` (2.6.22). Nothing needs `statx`, `getrandom` or `copy_file_range`.

### 1.6 SSE, AVX and x86 assumptions in the library sources (proven)

Grep of `include/`, `src/`, `libsupc++/` and `config/` for `__SSE*`, `__AVX*`, `__RDRND__`,
`__builtin_ia32_*`, `_mm_pause`, `__cpuid` and `__x86_64__`:

- `include/bits/atomic_wait.h:144-145`: `__builtin_ia32_pause()` under `__x86_64__` (which the
  KNC compiler defines, macro dump). `gcc/config/i386/i386.md:30320-30331` expands `pause` for
  `TARGET_KNC` into `knc_pause`, `gcc/config/i386/imci.md:485-495`: `delay %1` with 32 cycles,
  from Intel 327364-001 Appendix A. No `rep; nop` is emitted for KNC.
- `include/bits/simd_*.h`: the C++26 `std::simd` is gated on `__SSE2__` for x86
  (`include/bits/version.h:2660`), so `__cpp_lib_simd` is undefined on KNC and the headers'
  SSE paths are not compiled. Nothing else in the library selects on an ISA macro.
- `src/c++11/random.cc:31-37` compiles `rdrand`/`rdseed` only with the probes above (off).
- No `cmpxchg16b` is assumed: the headers go through `__atomic_*` builtins; GCC's KNC backend
  routes 16-byte CAS, load and store to libatomic calls (`gcc/config/i386/i386-knc.cc:815-845`,
  "KNC has no CMPXCHG16B, Intel 327364-001 Appendix B").

Macro dump of GCC 16 at `-march=knc` (empty translation unit): `__x86_64__ 1`, `__k1om__ 1`,
`__KNC__ 1`, `__GCC_ATOMIC_{CHAR,SHORT,INT,LLONG,POINTER}_LOCK_FREE 2`,
`__GCC_HAVE_SYNC_COMPARE_AND_SWAP_{1,2,4,8}` (no `_16`), `__GCC_DESTRUCTIVE_SIZE 64`,
`__GCC_CONSTRUCTIVE_SIZE 64`, `__SIZEOF_LONG_DOUBLE__ 16`, `__LDBL_MANT_DIG__ 64`,
`__SIZEOF_INT128__ 16`, `__SIZEOF_FLOAT128__ 16`, `__FLT128_MANT_DIG__ 113`; no `__SSE*`,
`__AVX*`, `__RDRND__`, `__RDSEED__` or `__CX16__`.

### 1.7 float128 (proven, one inferred consequence)

The compiler supports `__float128` and `_Float128`, so `CXXABI_FLOAT128` typeinfo is exported as in
the donor (`DONOR` exports `_ZTIg`, `_ZTIPg`, `_ZTIPKg` plus the `_ZTS*` names). Without
`_GLIBCXX_HAVE_FLOAT128_MATH` (glibc 2.26): `to_chars(_Float128)` is still built
(`src/c++17/floating_to_chars.cc:44-50` keys on `__FLT128_MANT_DIG__` and `__GLIBC_PREREQ`), but
`from_chars(_Float128)` binds `strtof128` weak (`src/c++17/floating_from_chars.cc:65-73`) and, when
it is null at run time, parses through `strtold` (`:687-695`): **64-bit mantissa precision for a
113-bit type**. Inferred defect to document, not a build blocker. `<stdfloat>` math overloads for
`_Float128` are absent for the same reason.

### 1.8 Blockers found statically

None that stops the build. Items that need a decision or a flag:

1. `--enable-clocale=generic` (section 2.2); the default `gnu` changes 72 exported symbol names.
2. No k1om ABI baseline: add `config/abi/post/k1om-linux-gnu/baseline_symbols.txt` from the first
   build (`make new-abi-baseline`, `testsuite/Makefile.am:158-161`; `scripts/extract_symvers.in:48-50`
   uses `readelf`, so it runs on the host).
3. libatomic must be built and shipped for 16-byte atomics (section 3.4).
4. `--with-libstdcxx-zoneinfo=static` or an accepted `tzdb` failure.
5. The donor headers in `SYS:usr/include/c++/` are GCC 5's. GCC 16 does not search them (its own
   `include/c++/16.x` comes first), but any `-isystem` of the sysroot's `c++` directory would mix
   header generations. Inferred.

## 2. ABI and coexistence

### 2.1 Version nodes (proven)

`DONOR` defines 35 version nodes: `GLIBCXX_3.4` to `GLIBCXX_3.4.21`, `CXXABI_1.3` to
`CXXABI_1.3.9`, `CXXABI_TM_1`, `CXXABI_FLOAT128` (readelf `--version-info`). Its needs are
`GLIBC_2.14`, `GLIBC_2.17` (`clock_gettime`), `GCC_3.0`, `GCC_3.3`, `GCC_4.2.0`, and it is linked
against `libm.so.6`, `libc.so.6`, `ld-linux-k1om.so.2`, `libgcc_s.so.1`.

GCC 16's `libstdc++-v3/config/abi/pre/gnu.ver` defines `GLIBCXX_3.4` through `GLIBCXX_3.4.36`
(`:2627`), `CXXABI_1.3` through `CXXABI_1.3.17` (`:2638-2986`) and `CXXABI_TM_1` (`:3003`);
`float128.ver` adds `CXXABI_FLOAT128`. Every donor node is present. The library is
`libstdc++.so.6.0.36` (`acinclude.m4:4099`, `libtool_VERSION=6:36:0`), SONAME `libstdc++.so.6`,
the same SONAME as the donor's `.so.6.0.21`.

### 2.2 Symbols: superset except for the C-locale model (proven, with one inferred step)

`.work/_shared/S9-02/abi_compare.py` reads `DONOR`'s defined, default-versioned
(`name@@VERSION`) `GLIBCXX_*`/`CXXABI_*` symbols and looks each up in GCC 16's own x86_64 baseline
(`config/abi/post/x86_64-linux-gnu/baseline_symbols.txt`, 6,081 entries, which is the export list
GCC 16 checks itself against). Result (`.work/_shared/S9-02/abi_compare.txt`):

| Measure | Count |
| --- | --- |
| Donor defined versioned symbols | 5,242 |
| Donor symbols absent from the GCC 16 baseline | 75 |
| Donor `OBJECT` symbols with a different size in the baseline | 0 |
| Baseline symbols in the donor's nodes that the donor lacks | 72 |

The 75 and the 72 are the same 72 symbols spelled two ways, plus 3 explained below:

- **72 symbols take a `__c_locale` argument.** The donor mangles it `Pi` (`int*`); GCC 16's
  baseline mangles it `P15__locale_struct`. `config/locale/generic/c_locale.h:49` has
  `typedef int* __c_locale;`, `config/locale/gnu/c_locale.h:62` has `typedef __locale_t __c_locale;`,
  and the donor's installed header `SYS:usr/include/c++/k1om-mpss-linux/bits/c++locale.h:49` is
  the generic one (`_GLIBCXX_NUM_CATEGORIES 0`, `:43`). So the MPSS donor was configured with
  `--enable-clocale=generic`, while `acinclude.m4:2806-2808` picks `gnu` for `linux*` by default.
  The affected exports are the `ctype`, `codecvt`, `collate`, `messages`, `numpunct`,
  `moneypunct`, `__timepunct`, `time_get/put`, `money_get/put`, `num_get/put` constructors and
  `_M_initialize_*` functions, `locale::facet::_S_{create,clone,destroy}_c_locale`, and
  `__convert_to_v<float|double|long double>`, in both the old and the `__cxx11` namespaces.
  Donor-built objects reference them only when they construct a facet with an explicit
  `__c_locale` or instantiate a `num_get`/`num_put` for a non-default iterator; the library's own
  explicit instantiations cover the ordinary `iostream` path. Inferred: building GCC 16's
  libstdc++ with `--enable-clocale=generic` reproduces the donor's names and makes the export set a
  superset; this is also the only model for which `std::locale("")` behaves as on the donor
  (the generic model accepts only `"C"`, `config/locale/generic/c_locale.cc:239-247`; the sysroot
  has no `usr/lib/locale` or `usr/share/locale`, so named locales have no data anyway, card
  contents unknown).
- `_ZNSt18condition_variable4waitERSt11unique_lockISt5mutexE@@GLIBCXX_3.4.11`: GCC 16 exports the
  default version at `GLIBCXX_3.4.30` and keeps `@GLIBCXX_3.4.11` as a non-default compatibility
  version (`baseline_symbols.txt:3006-3007`, `src/c++11/compatibility-condvar.cc:107`). Donor-built
  binaries bind to the old version; satisfied.
- `_ZSt11__once_call` and `_ZSt15__once_callable` (`TLS`, `GLIBCXX_3.4.11`): still exported by
  `gnu.ver:1325-1326` and defined under `_GLIBCXX_HAVE_TLS` (`src/c++11/mutex.cc:33-35`); the
  x86_64 baseline file simply omits TLS entries. With native TLS (S3-14) they exist in our build.

Nothing in the comparison concerns function semantics or vendor patches inside the donor; it is
a name-and-version check. Unknown: whether MPSS patched any libstdc++ behaviour.

### 2.3 Dual ABI (proven)

Both libraries default to the new ABI: donor `c++config.h:204` `_GLIBCXX_USE_DUAL_ABI 1`, `:212`
`_GLIBCXX_USE_CXX11_ABI 1` (1,205 `__cxx11` symbols in `DONOR`); GCC 16 `include/bits/c++config:363-374`
with `GLIBCXX_DEFAULT_ABI` default `new`. Donor-built and GCC 16-built objects therefore agree on
`std::string`/`std::list` layout by default, and `-D_GLIBCXX_USE_CXX11_ABI=0` interoperates with
old-ABI code the usual way. Mangling: GCC 16 defaults `-fabi-version` to the latest
(`gcc/c-family/c-opts.cc:1112`) versus GCC 5's 8; the differences (`-Wabi`) affect rare signatures
(attributes on function types, `nullptr_t`, some lambda and abi_tag cases), not the standard
library's exported interface, which is fixed by `gnu.ver`.

### 2.4 Coexistence: private, superset-capable (owner decision for libgcc_s applies)

- The card's system software needs the donor library: `SYS:usr/lib64/libzypp.so.810` and
  `SYS:usr/lib64/libcoi_device.so.0` list `libstdc++.so.6` and `libgcc_s.so.1` as `NEEDED`
  (readelf `-d`). Replacing `/usr/lib64/libstdc++.so.6` is the same class of change the owner
  refused for `libgcc_s` (`docs/research/s7-06-acceptance.md:3-6`): private directory, donor
  untouched, rollback by deletion.
- The S7-09 mechanism carries over unchanged: install into `.work/_shared/gcc-knc-16.2.0`, put the
  `.so` in `lib` next to `bin`, link with `DT_RPATH $ORIGIN/../lib` (`tools/s7_09_checks.py:12-14`,
  `:42`, `:135`); on the card, the shared program loaded `libgfortran.so.5` and `libgcc_s.so.1` from
  there even with the donor on `LD_LIBRARY_PATH` (`CURRENT_STATE.md:68`).
- One `libstdc++.so.6` per process: the loader matches `NEEDED` by SONAME against objects already
  loaded (glibc `ld.so`), so a GCC 16-built program (RPATH) pulls ours and any donor-built DSO it
  loads (libcoi, libzypp) is served by ours: this is where the superset matters. The reverse, a
  donor-run process dlopening a GCC 16-built plugin, fails to load with "version GLIBCXX_3.4.2x
  not found" as soon as the plugin uses anything newer than 3.4.21. Inferred; no crash, a load
  error.
- The g++ driver adds `-shared-libgcc` for C++ links (`gcc/cp/g++spec.cc:140`, `:304-307`), so
  every C++ program also needs `libgcc_s.so.1` at run time; both the private S7-06 copy and the
  donor's `/lib64/libgcc_s.so.1` carry the nodes libstdc++ needs (below).

## 3. Runtime features

### 3.1 Exceptions (proven at source level; S7 proved the unwinder)

`libsupc++` resolves `_Unwind_RaiseException`, `_Unwind_Resume`, `_Unwind_DeleteException`,
`_Unwind_Get*`, `_Unwind_Set*` (`GCC_3.0`), `_Unwind_Resume_or_Rethrow` (`GCC_3.3`) and
`_Unwind_GetIPInfo` (`GCC_4.2.0`); `DONOR` imports exactly this set
(`docs/research/knc-libgcc-shared.md:81`), and the donor `libgcc_s` chain goes up to `GCC_4.8.0`
(`:59-61`). S7-05/S7-06 ran cross-DSO throw/catch both ways, backtrace across a DSO and signal
unwind with the candidate `libgcc_s.so.1` (`docs/research/s7-06-acceptance.md:9-11`). Thread-local
destructors use glibc's `__cxa_thread_atexit_impl` (`GLIBC_2.18`). `-fexceptions` codegen on KNC
itself was exercised by those payloads. Unknown: a GCC 16-built `libstdc++.so.6` throwing through
its own `__cxa_throw` on the card; this is the first acceptance item.

### 3.2 RTTI (proven)

`libsupc++/typeinfo:58-81`: `__GXX_MERGED_TYPEINFO_NAMES 0` and `__GXX_TYPEINFO_EQUALITY_INLINE 0`
on ELF, so `type_info` equality is a `strcmp` of mangled names through the library. `dynamic_cast`
and `typeid` therefore agree across DSOs and across donor-built and GCC 16-built objects, given
the same mangling (section 2.3). `__float128` typeinfo is present in both libraries.

### 3.3 `std::thread`, `mutex`, `condition_variable` on glibc 2.21 (proven at source level)

- Threads are available (`_GLIBCXX_HAS_GTHREADS`, section 1.4), but because glibc 2.21 keeps
  `libpthread` separate and `_GLIBCXX_GTHREAD_USE_WEAK` stays 1 (`os_defines.h:83-86`), the gthread
  layer references `pthread_*` weakly (`libgcc/gthr-posix.h:106`, `:217-290`) and tests
  `__pthread_key_create`. A program linked without `-pthread` (`gcc/config/gnu-user.h:102` adds
  `-lpthread`) gets `std::thread` throwing `system_error(EPERM, "Enable multithreading to use
  std::thread")` (`src/c++11/thread.cc:185-190`) and no-op mutexes. Rule for E6-06 tests and for
  users: link with `-pthread`. `DONOR` itself imports `pthread_cond_*`/`pthread_mutex_*` from libc's
  `GLIBC_2.14` forwarders, the same model.
- `std::mutex`, `timed_mutex` (`pthread_mutex_timedlock`, `pthread.h:769`), `shared_timed_mutex`
  (`pthread_rwlock_t`) are native. `condition_variable::wait_until` on `steady_clock` converts to
  `system_clock` (`include/std/condition_variable:74-79`, `:130-150`) because `pthread_cond_clockwait`
  is missing; a wall-clock step on the card shortens or lengthens such waits. `std::call_once`,
  `atomic::wait/notify`, `latch`, `semaphore`, `barrier` use the futex syscalls of section 1.5.
- `this_thread::get_id()` uses the `__gthread_active_p()` form (`os_defines.h:71-80`): single-
  threaded programs report thread id 1.
- `std::thread::hardware_concurrency()` returns `get_nprocs()` (`src/c++11/thread.cc:49-66`), the
  card's online CPUs (240), not the cores a job is pinned to (40-59, 80 logical CPUs). Tests must
  not size work by it.

### 3.4 `std::atomic` of 1 to 16 bytes (proven for the compiler; libatomic inferred)

- 1, 2, 4 and 8 bytes: lock-free and inline (`__GCC_ATOMIC_*_LOCK_FREE 2`,
  `__GCC_HAVE_SYNC_COMPARE_AND_SWAP_1/2/4/8`, macro dump); `is_always_lock_free` true
  (`include/bits/atomic_base.h:1410-1411`, `include/std/atomic:292-294` use
  `__atomic_always_lock_free`). `shared_ptr` uses the atomic lock policy (`acinclude.m4:3864`).
- 16 bytes (`__int128`, `long double` with `__SIZEOF_LONG_DOUBLE__ 16`, two-pointer structs):
  `is_always_lock_free` false; every operation becomes `__atomic_*_16` through
  `gcc/config/i386/i386-knc.cc:815-845` (S2-06). These resolve only with `-latomic`; GCC does not
  add it (the libstdc++ testsuite uses `dg-add-options libatomic`, 53 of the 54 `29_atomics` run
  tests). Today `-latomic` resolves to the donor's static libatomic and the card has no
  `libatomic.so.1` (`CURRENT_STATE.md:94`, `:98`). The k1om libatomic from section 1.1 is generic
  (`config/posix/lock.c` locks for 16 bytes, builtins below). Inferred: build and ship it with
  libstdc++; a 16-byte `std::atomic` program is an acceptance item.

### 3.5 `std::filesystem` (proven at source level)

Enabled (`GLIBCXX_ENABLE_FILESYSTEM_TS` auto on Linux, `configure.ac:620-621`). All probed
dependencies exist in glibc 2.21 (section 1.4 table); `copy_file` uses `sendfile`; `last_write_time`
uses `utimensat`; `permissions` uses `fchmodat`; `space` uses `statvfs`; `temp_directory_path`
follows `TMPDIR` and falls back to `/tmp`, which on the card is `/var/volatile/tmp`
(`CURRENT_STATE.md:98`). Tests need a writable working directory.

### 3.6 `<random>` (proven)

`random_device` on KNC offers `default`, `/dev/urandom`, `/dev/random` and `mt19937`; the
`rdrand`, `rdseed`, `hw` and `getentropy` tokens are compiled out (`src/c++11/random.cc:88-95`,
`:332-356`) and an unknown token throws `runtime_error`. Distributions are header templates and use
the generic `opt_random.h` (no SSE3 path). `std::mt19937` and friends are unaffected.

### 3.7 `hardware_destructive_interference_size` (proven)

`gcc/config/i386/i386-options.cc:2853-2857` sets `param_destruct_interfere_size` and
`param_construct_interfere_size` to 64 unless given (S8-10), the macro dump shows
`__GCC_DESTRUCTIVE_SIZE 64` and `__GCC_CONSTRUCTIVE_SIZE 64`, and `<new>` exposes both constants
under `__cpp_lib_hardware_interference_size` (`include/bits/version.def:429-435`, C++17 and later,
conditional on `__GCC_DESTRUCTIVE_SIZE`). Nothing in libstdc++ needs changing for KNC.

## 4. Default standard

- GCC 16 defaults C++ to `gnu++20` (`gcc/c-family/c-opts.cc:277-279`, "Set C++ standard to C++20
  if not specified"). The donor GCC 5.1 defaulted to `gnu++98`
  (`releases/gcc-5.1.0:gcc/c-family/c-common.c:261`, `cxx_dialect = cxx98`).
- The corpus's only C++ program is HPCG 3.1 (`docs/research/corpus-and-coverage.md:22`, `:70`; the
  rest is C and Fortran). S0-07 compiled it with GCC 14.4 (default `gnu++17`); the one failure,
  `ComputeResidual.cpp:56` `default(none)`, is an OpenMP rule change, not a dialect issue
  (`corpus-and-coverage.md:136`). A grep of its 83 `.cpp`/`.hpp` files (extracted from
  `.work/_shared/corpus/hpcg-3.1.tar.gz`, copy deleted afterwards) finds no construct that C++20
  breaks or changes: no user
  `operator==`/`!=` (comparison rewriting), no `u8` literals (`char8_t`), no `register`, no dynamic
  exception specifications, no `auto_ptr`/`bind1st`/`ptr_fun`/`unary_function`, no compound
  `volatile` operations, no identifiers named `concept`, `requires`, `consteval`, `constinit`,
  `co_*`, `module`, `import` or `export`. Headers used: `cassert`, `fstream`, `string`, `set`,
  `map`, `cmath`, `iostream`, `vector`, `unordered_map`, `algorithm`, `cstdlib`, `cstring`.
  Inferred: HPCG compiles under `gnu++20`; proof is the E6-06 host compile.
- HPCG needs `-fopenmp` (`setup/Make.GCC_OMP:121`; 11 source files have `#pragma omp`), and the
  GCC 16 configure disables libgomp (`tools/toolchain.py:72`). Running the corpus's C++ program on
  the card needs a k1om libgomp, which is outside E6-06. Flag for the lead.
- Does KNC need a different default? No. The dialect is target-independent, and changing it would
  be a shared-code change (`gcc/c-family`) against ADR-0006's portability rule for no KNC reason.
  The KNC-specific defaults belong in the libstdc++ configure: `--enable-clocale=generic` and the
  unchanged `--with-default-libstdcxx-abi=new`, both matching the donor. Donor-built C++98 objects
  mix with `gnu++20` objects through the ABI (section 2), not the dialect.

## 5. Testing

### 5.1 What the libstdc++ testsuite is (proven)

`libstdc++-v3/testsuite` holds 10,177 `.cc` tests; 4,004 are `dg-do run`, 3,841 compile, assemble,
link or preprocess only. Of the run tests, 2,224 carry no `dg-require*`, `dg-add-options`,
`dg-additional-*`, `dg-shouldfail` or `dg-output` directive: they are self-contained programs whose
`VERIFY` aborts on failure (`testsuite/util/testsuite_hooks.h:61-67`), so exit status is the
verdict. Requirements across run tests: 288 need gthreads or `-pthread`, 170 need the filesystem or
file I/O, 56 need named locales or iconv, 53 need `libatomic`, 68 need `cmath`/string conversions.

| Area | `dg-do run` | All `.cc` |
| --- | --- | --- |
| 18_support (exceptions, RTTI, new, interference size) | 54 | 167 |
| 19_diagnostics | 43 | 76 |
| 20_util | 486 | 1,627 |
| 21_strings | 221 | 487 |
| 22_locale | 69 | 629 |
| 23_containers | 1,010 | 1,720 |
| 25_algorithms | 332 | 841 |
| 26_numerics (random: 222 of 293) | 290 | 551 |
| 27_io (filesystem: 113 of 125) | 284 | 1,153 |
| 28_regex | 119 | 171 |
| 29_atomics | 54 | 123 |
| 30_threads | 252 | 386 |
| std, experimental, ext, tr1, special_functions | 695 | 1,774 |

### 5.2 What can run on the card through the lead's runner (proven constraints, inferred plan)

DejaGnu's `libstdc++.exp` runs executables through `remote_exec target`; the card is reachable only
through `tools/card_run`, which runs one program with a staged `--file-list` (`tools/card_run:848-866`)
under the lead's hands (`docs/DEVELOPMENT_CYCLE.md:197-206`). So the testsuite harness itself cannot
drive the card. Three slices fit the project's way of working:

1. **Host only, whole suite compile:** `make check-compile` (`testsuite/Makefile.am:168-170`,
   `scripts/check_compile:47` compiles each test to an executable with the k1om compiler). Catches
   header, dialect and link problems for all 10,177 tests without the card.
2. **Host only, ABI:** `make new-abi-baseline` once, commit it as
   `config/abi/post/k1om-linux-gnu/baseline_symbols.txt`, then `make check-abi` on every change
   (`Makefile.am:158-161`; `extract_symvers` uses `readelf`). Plus `abi_compare.py` against the
   donor (0 missing is the superset criterion).
3. **Card batch:** compile a chosen list of `dg-do run` tests on the host (with `-pthread`,
   `-latomic` where the directives say so), name them `claude-*.mic`, stage them with a `run.sh`
   like `.work/_shared/S7-08/run.sh` (loop, exit status, `PASS`/`FAIL` lines) and run the batch in
   one `card_run --file-list` job in `/var/volatile/tmp`. Skip `22_locale` named-locale tests
   (generic model) and anything with `dg-output`/`dg-shouldfail` unless the driver compares output.

### 5.3 Minimal acceptance slice (inferred)

About 30 programs, all host-compiled, each exit 0 on the card. From the testsuite:

- Exceptions and RTTI: `18_support/exception_ptr/{current_exception,rethrow_exception,lifespan,move}.cc`,
  `18_support/nested_exception/{rethrow_nested,throw_with_nested,rethrow_if_nested}.cc`,
  `18_support/uncaught_exceptions/uncaught_exceptions.cc`, `18_support/bad_cast/cons_virtual_derivation.cc`,
  `18_support/bad_typeid/cons_virtual_derivation.cc`, `18_support/new_aligned.cc`,
  `18_support/headers/new/synopsis.cc` (interference size constants).
- Threads (`-pthread`): `30_threads/thread/cons/{1,2,3,4,5}.cc`, `30_threads/condition_variable/members/{1,2,3}.cc`,
  `30_threads/future/members/{get,wait,wait_for,wait_until}.cc`, `30_threads/call_once/{call_once1,once_flag}.cc`.
- Atomics: `29_atomics/atomic/is_always_lock_free.cc`, `29_atomics/atomic/lock_free_aliases.cc`,
  `29_atomics/atomic_integral/is_always_lock_free.cc`, `29_atomics/atomic/cons/user_pod.cc`
  (`-latomic`), `29_atomics/atomic/wait_notify/1.cc` (`-pthread`).
- Numerics and I/O: `26_numerics/random/random_device/cons/{default,token}.cc`,
  `27_io/filesystem/operations/{copy_file,status,last_write_time,temp_directory_path,remove_all}.cc`.

Plus three project programs (new test files, like S7-05's payloads):

- `claude-cxx-xdso`: a GCC 16 program throwing into and catching from a donor-built DSO and the
  reverse, with `typeid` and `dynamic_cast` across the boundary.
- `claude-cxx-donor-prog`: a donor-built program (iostream, string, `locale("C")`, exception)
  run with the loader's `--library-path` pointing at our `libstdc++.so.6`; the superset check.
- `claude-cxx-atomic16`: 4 threads on `std::atomic<__int128>` with our `libatomic`, expected
  counts printed and compared byte for byte, as S2-06 did.

## 6. Recommended E6-06 tickets

1. **E6-06a: build libstdc++ and libatomic for k1om.** Configure with `--enable-languages=c,c++,fortran
   --enable-clocale=generic --with-libstdcxx-zoneinfo=static` (keep every existing flag; libgomp
   stays off here); add `config/abi/post/k1om-linux-gnu/baseline_symbols.txt` from
   `make new-abi-baseline`. Acceptance: the configure log shows `cpu/generic`, `gnu` symvers,
   gthreads yes, float128 yes, rdrand no, futex yes, clocale generic; `libstdc++.so.6.0.36` and
   `libatomic.so.1` link against the sysroot; `abi_compare.py` reports 0 donor symbols missing and
   0 size differences; `make check-abi` passes against the new baseline; `make check-compile` has
   no unexpected compile failures outside skipped areas. Card checks (lead): static and shared
   hello-iostream, one throw/catch, one `dynamic_cast` program.
2. **E6-06b: packaging into the private prefix.** Install into `.work/_shared/gcc-knc-16.2.0`
   like S7-09 (`lib` next to `bin`, `DT_RPATH $ORIGIN/../lib`, `libatomic.so.1` included), and a
   g++ link guard mirroring S7-09's: fail a link whose `-lstdc++` resolves to a library without
   `GLIBCXX_3.4.36`. Acceptance: readelf shows SONAME, nodes and RPATH; card: the shared program
   loads ours with the donor directory on `LD_LIBRARY_PATH`; `claude-cxx-donor-prog` passes
   against ours; the donor program still passes against the donor library.
3. **E6-06c: runtime slice.** The section 5.3 batch plus `claude-cxx-xdso` and `claude-cxx-atomic16`
   (`new_test_files: 3`). Acceptance: every program exits 0 on the card in one `card_run` batch,
   outputs byte-identical to host-side expected files; the note's known deviations
   (`system_clock` condvar, `hardware_concurrency` 240, `from_chars(_Float128)` precision) are
   recorded as tests that document behaviour, not as failures.
4. **E6-06d (optional, after c): HPCG on the card.** Needs a k1om libgomp; if the lead schedules
   it, acceptance is HPCG's own `--rt` check with the `default(none)` line fixed as S0-07 did.

## 7. Risks

- **C-locale model decision.** `generic` matches the donor and the card (no locale data), but
  loses `gnu`-only behaviour (named locales, `messages`). Choosing `gnu` instead makes 72 symbols
  differ from the donor's and the library stops being a drop-in for donor-built code that touches
  facets. Lead decision; this note recommends `generic`.
- **Weak pthread references.** Every threaded C++ program must link `-pthread`; forgetting it is a
  run-time `EPERM`, not a link error. Document in the driver notes or add `-pthread` to the KNC
  link spec (a shared-code change; not recommended without an ADR).
- **16-byte atomics need `-latomic` and a shipped `libatomic.so.1`.** Until E6-06a/b, such programs
  fail to link or load, as S2-06's counter did (`CURRENT_STATE.md:98`).
- **`from_chars(_Float128)` precision** (section 1.7) and no `_Float128` math: glibc 2.21 limit.
- **`condition_variable` on `system_clock`** and **`hardware_concurrency()` = 240**: behaviour,
  not defects, but tests sized by them mislead.
- **Binutils 2.22.52** passes the probes on paper; a failure of `--gc-sections` or
  `--version-script` with that linker shows up only in the build.
- **libbacktrace and `tzdb`** are the two optional components most likely to need a flag
  (`--disable-libstdcxx-backtrace`, zoneinfo static).
- **One libstdc++ per process**: GCC 16-built plugins cannot load into donor-run hosts.
- **Vendor patches** in the donor libstdc++ are invisible to a symbol comparison.
- **libgomp** is outside E6-06, yet the corpus's only C++ program needs it.
