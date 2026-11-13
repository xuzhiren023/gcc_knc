# Exploratory WRF build with GCC-KNC (S11-21)

## Scope and inventory

This is a host-side, learn-only investigation dated 2026-11-12. It is not an
M4 acceptance workload or a native correctness/performance result. The first
target is serial `em_real`, without MPI or OpenMP, using GCC-KNC 16.2.0 and
`-O2 -march=knc`, without `-ffast-math`.

PhiWeather's `.tools/knc-bootstrap/wrf-knc/README` identifies WRF **4.8.0**.
Its git worktree points to `native/upstream/WRF/.git`, branch
`phiweather/wrf-knc`, whose committed revision inspected for this inventory was
`06d4240ae989cc3e50af412bb472df3d9048783c`. This does not establish that its
working sources are unmodified. Its configuration contains a local
`Linux k1om, PhiWeather GNU KNC scalar baseline` serial entry, so that tree
must not be treated as an unmodified upstream release without separating the
local configuration and source changes.

The retained serial `configure.wrf` records compiler choice 1 and nesting 0.
WRF's `configure` accepts `-os` and `-mach`; its local KNC entry can be selected
with Linux/k1om. `SFC`, `SCC`, `CCOMP`, `AR`, and `RANLIB` use cross tools;
`CC_TOOLS=gcc` builds host utilities. The old entry uses `-mknc`, `-O1`, and
`-fno-tree-vectorize`; those are recipe facts, not flags for this trial.
The GCC 16 adaptation needs `-march=knc`, `-O2`, fresh netCDF Fortran modules,
and an isolated library prefix. Keep real word size 4, big-endian unformatted
I/O and 4-byte record markers as in the recipe. Serial nesting can use WRF's
bundled STUBMPI; a no-nesting serial build needs no external MPI.

| Dependency | PhiWeather recipe facts | Trial choice |
| --- | --- | --- |
| netCDF-C 4.9.2 | Static; no HDF5, DAP, byterange, plugins, utilities, testsets or libxml2; NCZarr enabled. Recorded `libnetcdf.settings` lists `-lm -ldl`, bundled tinyxml2, CDF5 and netCDF-4 API, but no HDF5 storage. | Rebuild the classic recipe with GCC 16 C and C++ cross drivers at `-O2 -march=knc`. |
| netCDF-Fortran 4.6.1 | Static; `--disable-fortran-type-check --enable-netcdf-4 --disable-doxygen --disable-examples`; C uses `-DLONGLONG_IS_LONG`; link with netCDF-C and static GCC/Fortran runtimes. | Must rebuild with GCC 16; never reuse GCC 5 `.mod` files. |
| MPICH 3.4.3 | Static; no C++ bindings; all Fortran bindings; `ch3:sock`, `gforker`, measured cross ABI file. | Defer for the permitted serial first target. Rebuild Fortran bindings for GCC 16 before any MPI target. |
| WRF bundled libraries | FFTPACK, GRIB1/GRIB shared I/O, internal I/O, bundled ESMF time, netCDF I/O wrapper. | Build from the eventual isolated WRF source copy. |
| System/runtime libraries | Target libc/libm and GCC/Fortran runtimes; optional HDF5/zlib in the currently retained WRF configuration. | Use the installed cross toolchain/sysroot. Disable HDF5-dependent WRF features for the classic target; do not inherit the retained netCDF4 prefix. |

All three dependency recipes use `--build=x86_64-pc-cygwin` and
`--host=x86_64-linux-gnu` with explicitly selected `k1om-mpss-linux-*`
compilers. The host alias is a configure convention in these recipes, not
evidence of x86 target code. The copied settings are reference material only.

## Retained inputs and commands

Everything large is under `.work/_shared/wrf-trial/`, with a 25 GB budget.
`src/PROVENANCE.md` records original paths, versions and patch status, as
explicitly required by this ticket. The two dependency archives preserve their
licences. `src/recipes/` retains the two WRF configuration files and selected
dependency configure command/compiler-variable facts. No PhiWeather file is
modified. No vendor headers or vendor implementation material is involved.

`prepare.py` copies inputs; `netcdf-c.sh` extracts the C archive and configures,
builds (`make -j8`) and installs it under `wrf-trial/install`. Its PATH selects
`.work/_shared/gcc-knc-16.2.0/bin` first, then PhiWeather's cross binutils and
Cygwin host utilities. The preparation and current clean build use `tools/run.py` (the build-only
continuation follows the already completed fresh configure):

```text
python tools/run.py --name S11-21-inputs -- python ../_shared/wrf-trial/prepare.py
python tools/run.py --name S11-21-netcdf-c-make --inputs ../_shared/wrf-trial/trial-env.sh ../_shared/wrf-trial/netcdf-c.sh -- C:/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/cygwin/bin/bash.exe ../_shared/wrf-trial/trial-env.sh bash ../_shared/wrf-trial/netcdf-c.sh build-only
```

## Stage reached and blockers

**Stage 2 complete: both dependency libraries are built and installed, and
`nf_create`/`nf90_create` now link. The lead completed the WRF export.
Stage 3 now has a complete serial, no-nesting GCC-KNC configuration, with
RPC selected by target preprocessing. Two em_real attempts failed: first
on the trial architecture terminator, then on CRLF Registry input and a
stale host object. Partial physics compilation produced vectorization
reports; neither wrf.exe nor real.exe linked.** The installed static archives are
`install/lib/libnetcdf.a` (1,770,676 bytes) and `libnetcdff.a` (1,561,006 bytes).
Both use GCC-KNC 16.2.0 at `-O2 -march=knc`. Fortran needed the classic-path
patch below. Installed module verification passed in the preceding session
and was not repeated.

Following the lead's 20:21 answer, removing `-lstdc++` resolved the link without
other link-line changes. No archive member pulled into this probe required
C++ runtime symbols; other optional netCDF APIs were not tested.
`netcdf-link.exe` is retained under the trial root and was not run.
`readelf -d` confirmed no NEEDED entry for `libgfortran.so.5`, `libstdc++.so.6`,
or `libgcc_s.so.1`.

All trial links must use static GCC 16 runtimes: `-static-libgcc` and
`-static-libgfortran`, plus `-static-libstdc++` if C++ is actually required.
The card has MPSS GCC 5 runtimes. Apply this rule in WRF's
`configure.wrf` `LDFLAGS_LOCAL` when configuration is reached.
WRF and MPI remain unbuilt, with no WRF binary staged for the card. No
GCC-KNC ICE or wrong assembler output was observed; no compiler reproducer
is applicable.

The lead authorized retaining the contaminated `build-netcdf-c` as stale and
using `build-netcdf-c-nomsys`. Every configure and make runs through
`trial-env.sh`, which unsets `MSYSTEM`, `MSYSTEM_PREFIX`, `MINGW_PREFIX`, and
`MSYSTEM_CHOST` and selects the GCC 16 installation first on PATH.

The fresh netCDF-C configure completed successfully. In this release, false
`ISMSYS` and `ISMINGW` values are **empty**, rather than literal `no`;
`ISMSYS_TRUE`, `ISMINGW_TRUE`, and `REGEDIT_TRUE` are all `#`. The generated
makefile comments out `am__append_8 = dreg.c`, excluding the registry source
from compilation. The initial pre-build guard incorrectly required literal
`no` and stopped before make. It was corrected to accept the false values
and require all three disabled conditionals. The build-only continuation
uses this successful configuration without repeating configure.

| Finding | Classification | Evidence and disposition |
| --- | --- | --- |
| Cygwin `mkdir -p` failed on a parent of the trial directory. | Host infrastructure. | Resolved in the earlier session by creating authorized directories with native PowerShell. |
| `libdispatch/dreg.c:13:10: fatal error: windows.h: No such file or directory`. | Cross-configuration/environment contamination. | Inherited `MSYSTEM=MINGW64` enabled `REGEDIT` despite Linux host. The clean environment now disables it; no source patch. |
| Removal/recreation of the old build directory was blocked by host policy. | Host execution policy. | Lead explicitly authorized retaining it and using `build-netcdf-c-nomsys`; nothing was deleted. |
| Preparation used a `Path.write_text(newline=...)` keyword unsupported by the host Python. | Trial orchestration. | No edit occurred. An inadvertently launched old-directory configure was interrupted and its orphan subprocess group terminated before make. Changed file writing to `Path.open`; accepted results use only the new directory. |
| `make install` could not create `install/include`; Cygwin reported permission denied on `/cygdrive/c/Users/xuzhi`. | Host infrastructure during dependency installation. | Lead precreated destinations; an install-only retry still failed at the absolute path. The authorized relative-directory approach succeeded without recompilation. |
| Guard required `ISMSYS='no'`, while configure represents false with an empty value. | Trial verification script. | Fresh configure exited zero; wrapper exited one before make. Guard corrected from observed configuration semantics. |
| netCDF-Fortran configure warns that `--enable-netcdf-4` and `--disable-examples` are unrecognized. | Dependency recipe/configuration mismatch. | These inherited recipe switches do not select the intended features in 4.6.1. Configure succeeded, reported netCDF-4 API disabled, and selected `netcdf.F90`. |
| `fortran/netcdf.F90:57` includes missing `netcdf_expanded_subset.f90`; the diagnostic is displayed at line 58. | Dependency source/build-input issue, not demonstrated GCC strictness or backend defect. | The copied source has `netcdf_expanded.F90` instead. The subsequent includes name `netcdf_get_nd_expanded.f90` and `netcdf_eightbyte_subset.f90`; no generation rule for the first two was found in the inspected Automake/CMake/configure inputs. Only the first missing file was diagnosed by this compile. |
| `fortran/module_netcdf_nf_data.F90:167-168` refers to undefined `NC_NOQUANTIZE` and `NC_QUANTIZE_BITGROOM`. | Dependency source/configuration guard inconsistency. | Their definitions in `module_netcdf_nc_data.F90:420-421` are inside `USE_NETCDF4` (lines 317-423), while these uses are unconditional. The actual classic configuration omits `USE_NETCDF4`. No ICE or assembler error occurred. |

No GCC build, x86 check, benchmark or card job was started. MPI remains
deferred for the lead-approved serial, no-nesting target. The netCDF-Fortran
4.6.1 configure script contains no `MSYSTEM`, `ISMSYS`, or `ISMINGW` detection;
its build used the same environment wrapper. A read-only search of PhiWeather's
WRF `configure` also found no `MSYSTEM`, `ISMSYS`, or `ISMINGW` test. WRF
configuration itself was not run.

The successful C compilation emitted nonfatal warnings for `strndup`
redefinition in `libdispatch/ncuri.c:81`, an old-style definition in
`libdispatch/dcrc32.c:263`, and moved `libstdc++.la` paths. None was suppressed
or patched. The log contains no fatal compiler diagnostic.

The reduced infrastructure command below is the failing command from the
install log, not a separately rerun test:

```sh
# Under trial-env.sh:
/usr/bin/mkdir -p /cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/wrf-trial/install/include
```

The lead precreated the install destinations. The install-only retry still
failed because absolute Cygwin `mkdir -p` walked the inaccessible parent.
`install-netcdf-c.sh` then ran `make install` from the trial root with
`MKDIR_P="bash $TRIAL/mkdir-relative.sh"`. That helper validates destinations
are inside the trial install prefix, changes to the trial root, and calls
plain `mkdir -p` on relative paths. This lead-authorized approach succeeded
without deleting anything, changing sources, or recompiling C. It is also
selected for netCDF-Fortran installation. All commands use `trial-env.sh`
and `tools/run.py`.

### Classic Fortran patch and earlier link blocker

The earlier unpatched Fortran build failed before installation. The lead's
2026-11-12 19:59 answer authorized patching copied 4.6.1 sources, retaining the
no-HDF5 C library and old build tree. A read-only byte comparison of every
regular member of the pristine archive against PhiWeather's extracted
`scientific-sources/netcdf-fortran-4.6.1` found no differing or missing members;
there were no subset files to adopt.

`src/patches/netcdf-fortran-4.6.1-classic.patch` now contains only these changes:

- Replace the three nonexistent subset includes in `fortran/netcdf.F90` with
  the distributed `netcdf_expanded.F90` and `netcdf_eightbyte.F90`.
- Move the two quantization constant definitions outside `USE_NETCDF4`.
- Move `NC_ENOPAR` outside the same guard; the nonparallel stubs use it even
  when netCDF-4 is disabled.

`netcdf-fortran.sh` applies the patch to a fresh archive extraction under
`src/netcdf-fortran-p1/` and configures `build-netcdf-fortran-p1/`. It omits
the two unrecognized inherited configure options. The first p1 make exposed
`NC_ENOPAR` and libtool metadata errors; after correcting both, an incremental
make and install passed without repeating configure. Installation used the
existing relative `MKDIR_P` helper and needed no new top-level directory.

| New finding | Classification | Evidence and disposition |
| --- | --- | --- |
| `nf_nc_noparallel.F90:33,49,64`: undefined `NC_ENOPAR`. | Upstream dependency classic-path guard bug. | Its definition was inside `USE_NETCDF4`, although the nonparallel stubs are built without that macro. Moving that one definition outside the guard resolved compilation. |
| Libtool rejects a missing `gcc-install/.../lib64/libstdc++.la`. | Relocated toolchain metadata / dependency link configuration. | Two stale absolute entries in this trial's `install/lib/libnetcdf.la` `dependency_libs` were normalized to `-lstdc++`. The script records the adjustment. No toolchain file was edited. Fortran make/install then passed. |
| Tiny netCDF link selects shared `libstdc++.so` and fails on versioned GCC runtime references. | Runtime-link configuration; not established as a GCC-KNC backend defect. | `netcdf-link.sh` uses `-static-libgcc -static-libgfortran` but plain `-lstdc++`. Undefined symbols include quad conversions/comparisons, 128-bit integer division, and unwind functions. Resolved in the current continuation by removing unnecessary `-lstdc++` as directed by the lead. Static C++ selection was not needed. |

All 19 unresolved references in the link log are:
`__extendxftf2`, `__udivti3`, `_Unwind_Resume`, `_Unwind_Resume_or_Rethrow`,
`_Unwind_DeleteException`, `_Unwind_GetRegionStart`, `__getf2`, `__eqtf2`,
`__unordtf2`, `_Unwind_SetGR`, `_Unwind_GetIPInfo`, `_Unwind_SetIP`,
`_Unwind_RaiseException`, `__letf2`, `__trunctfxf2`,
`_Unwind_GetLanguageSpecificData`, `__udivmodti4`, `_Unwind_GetTextRelBase`,
and `_Unwind_GetDataRelBase`. Their required GCC symbol versions are in the log.

The installed modules were checked once: compressed header inspection,
comparison with the build outputs, and the build's GCC 16.2.0 identification.
`netcdf.mod` is 17,591 bytes and `netcdf_nf_data.mod` is 8,076 bytes. The link
program uses both modules. The API link now passes; native behavior remains
untested. The shared `netcdf-link.f90` is a link probe,
not a repository test or a card job.

Commands for this continuation (all through `tools/run.py` and `trial-env.sh`):

```text
S11-21-netcdf-fortran-p1: bash netcdf-fortran.sh
S11-21-netcdf-fortran-p1-resume: bash netcdf-fortran.sh build-only
S11-21-netcdf-link: bash netcdf-link.sh
```

Reduced failing link, from the trial root under `trial-env.sh`:

```sh
k1om-mpss-linux-gfortran -O2 -march=knc -Iinstall/include netcdf-link.f90 -Linstall/lib -static-libgcc -static-libgfortran -lnetcdff -lnetcdf -lstdc++ -lm -ldl -o netcdf-link.exe
```

The preceding continuation stopped after two failed attempts. The lead then
directed removing `-lstdc++` first. That passed on this continuation's only
build/test invocation (including the requested dynamic-dependency check):

```text
python tools/run.py --name S11-21-netcdf-link-no-cxx --inputs ../_shared/wrf-trial/netcdf-link.sh ../_shared/wrf-trial/netcdf-link.f90 -- C:/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/cygwin/bin/bash.exe ../_shared/wrf-trial/trial-env.sh bash ../_shared/wrf-trial/netcdf-link.sh
```

### Current blocker: WRF source preparation

Read-only inspection identifies upstream tag `v4.8.0` at
`06d4240ae989cc3e50af412bb472df3d9048783c` in
`C:/Users/xuzhi/Documents/PhiWeather/native/upstream/WRF`. Its seven physics
submodules are `GFL`, `MYNN-EDMF`, `MYNN-SFC`, `TEMPO`, `fire_behavior`,
`noahmp`, and `physics_mmm`; local object repositories exist under
`.git/modules/phys`. A pristine export must include their pinned gitlinks.

The planned script would export that tag and pinned physics submodules into
`wrf-trial/src/`, preserve licences, and record origins in `PROVENANCE.md`.
The project PreToolUse hook rejected the command to write the script before
it ran, with this reason:

> Copying trees and downloading are how this project would run out of space.
> Reuse the shared build area, or ask the lead to allow it on this ticket.

Classification: **host/project execution policy**, not a compiler defect.
The destination was already the ticket-authorized shared area. No script,
export, extraction, configure, or WRF build resulted. AGENTS.md prohibits
bypassing a hook refusal. The lead must provide the source export or an
approved preparation path; no alternate copying method was attempted.

Read-only comparison identifies pending cross-configuration issues, not
observed compile failures: upstream `configure:700-717` executes host
`gfortran` to choose compatibility flags; PhiWeather instead queries the
selected compiler's `-dumpversion`. WRF already specifies
`-fallow-argument-mismatch -fallow-invalid-boz` for GCC newer than 9.
Upstream `configure:617-628` executes fseek probes and `configure:1036-1037`
executes an RPC probe; cross configuration must avoid target execution.
PhiWeather's RPC adaptation uses a `rpc_type_cross` make target. The serial
KNC entry needs GCC 16 flags, host `CC_TOOLS`, static runtime flags, and
`NETCDF_classic=1`. No WRF compatibility patch has been applied.

### Time, disk and logs

Earlier attempts: directory creation failed in less than 0.1 minute;
contaminated configuration plus partial compilation took 4.4 minutes.
The fresh configuration and overly strict pre-build guard took **4.2 minutes**;
this was configuration time, with no make invocation. The subsequent clean
compilation plus failed install took **0.8 minutes**. No WRF compilation time
is available. The successful C install took **0.1 minute**; Fortran configure
and partial compilation took **1.9 minutes** together. Make was capped at 8 jobs.

The p1 configure/partial make took **2.7 minutes**. The successful incremental
make/install took **0.6 minute**; the failed link probe took under 0.1 minute.
Configure and make times are combined where the wrapper ran both. No WRF
compilation timing is available.

Before this continuation, the trial contained **79,439,526 logical file bytes**
(79.4 MB decimal, 75.8 MiB) in 4,619 file entries. This includes archives,
stale trees retained at the lead's direction, patched sources, installed
libraries/modules and the link input. The `os.walk`/`lstat` measurement does
not follow Cygwin reparse files; allocated disk blocks were not measured.
The trial remains below its 25 GB budget. Nothing was deleted.

Logs under `.work/_state/logs/`:

- `S11_21_inputs-20261112-191724.log`: input copying passed.
- `S11_21_netcdf_c-20261112-191731.log`: initial mkdir failure.
- `S11_21_netcdf_c_configure-20261112-191753.log`: original registry-source failure.
- `S11_21_netcdf_c_nomsys-20261112-193023.log`: interrupted old-directory configure; not an accepted build result.
- `S11_21_netcdf_c_clean_build-20261112-193107.log`: fresh configure succeeded; overly strict guard stopped the wrapper before make.
- `S11_21_netcdf_c_make-20261112-193558.log`: disabled-platform checks and C compilation passed; install failed at mkdir (line 392). Archive creation is at lines 358-359.
- `S11_21_netcdf_c_install-20261112-194235.log`: install-only retry after destination precreation failed at absolute mkdir (less than 0.1 minute).
- `S11_21_netcdf_c_install_relative-20261112-194327.log`: relative-directory installation passed (0.1 minute).
- `S11_21_netcdf_fortran-20261112-194351.log`: configure passed; classic Fortran compilation failed (1.9 minutes). Missing-include diagnostic at line 307; undefined constants at lines 313-322.

- `S11_21_netcdf_fortran_p1-20261112-200815.log`: patch applied and configure passed; make failed on `NC_ENOPAR` (lines 327-341) and stale C++ libtool metadata (lines 347-358).
- `S11_21_netcdf_fortran_p1_resume-20261112-201201.log`: corrected incremental make and install passed (0.6 minute).
- `S11_21_netcdf_link-20261112-201304.log`: GCC/module checks passed; link failed (undefined references at lines 5-23). No execution.

Current continuation: link plus dynamic-dependency check took less than
**0.1 minute** (wrapper: 0.0 minute); WRF compilation has not started.
Current logical disk usage before this documentation append is **84,286,462 bytes**
(using lstat for Cygwin links), below 25 GB. The initial stat-based accounting
could not follow a stale Cygwin HDF4 link; no build was involved.
Log: `.work/_state/logs/S11_21_netcdf_link_no_cxx-20261112-202434.log`.
The source-preparation refusal is in the tool response, not a build log.

### Continuation after the lead's WRF export

The lead's 20:32 ticket answer authorizes building the exported source at
`src/WRF-4.8.0`; `src/PROVENANCE-WRF.md` records the intended v4.8.0 tag
and seven pinned submodules. Inspection in this continuation found that
the export root contains **only `phys/`**. That directory contains all seven
named submodule directories, with 645 files totaling 167,825,584 logical
bytes. The top-level WRF sources, including `configure`, are absent.
The recorded export size therefore does not establish that the main WRF
repository was exported successfully.

Classification: **build-input preparation / host infrastructure**, not a
WRF compile error, GCC 16 strictness change, or GCC-KNC defect. A reduced
reproducer is `Get-ChildItem ../_shared/wrf-trial/src/WRF-4.8.0 -Force`:
the only entry is `phys`. Reading its `configure` fails with file not found.
No WRF configure or compilation was attempted. The earlier source-export
hook refusal remains applicable; no alternative export or copying method
was tried. The lead needs to supply the main repository export into this
directory before the authorized serial build can proceed.

The existing dependency results were not rerun. Additional build time is
zero. A PowerShell recursive file-length measurement gives **252,113,993
logical bytes** across 5,267 trial files, below the 25 GB budget; this is
not allocated disk usage. A preceding Python measurement command failed
at argument parsing because PowerShell removed its string quotes and
made no filesystem changes. No new build/test log exists for this
continuation; the last successful test remains
`S11_21_netcdf_link_no_cxx-20261112-202434.log`.

The first E7-20 work package below must first complete the main WRF export;
the seven submodule directories alone are insufficient. Compiler override
selection, static-runtime WRF link flags, and hot-loop reports remain
pending actual WRF configuration and compilation.

### Continuation after the corrected main export

The lead's 20:42 answer and `src/PROVENANCE-WRF.md` correction supersede
the incomplete-export blocker above. No dependency test was repeated.
`configure-wrf.py` added a serial Linux k1om entry derived from upstream's
GNU Linux entry. Target C and Fortran use GCC-KNC; `CC_TOOLS=gcc` selects
Cygwin host utilities. Flags are `-O2 -march=knc`, static GCC/Fortran runtime
link options and `-fopt-info-vec` for optimized Fortran. No fast math.

`src/patches/wrf-4.8.0-knc-cross.patch` retains the architecture addition and
a cross-configuration patch. Upstream `configure:700-717` executes a program
compiled with bare host `gfortran` to select compatibility flags. The patch
queries the selected cross compiler with `-dumpversion` instead, preserving
the upstream major-version-greater-than-nine condition. Generated `FCCOMPAT`
contains `-fallow-argument-mismatch` and `-fallow-invalid-boz`. These are WRF's
existing compatibility choices, not observed scientific-source failures.

`wrf-configure.sh` runs through `trial-env.sh`, selects `-os Linux -mach k1om`,
compiler 1 and nesting 0. `NETCDF_classic=1` disables HDF5 features, and
`NETCDF_LDFLAGS` selects the installed archives plus `-lm -ldl`, without C++.
Inspection found no MSYSTEM/MINGW test in WRF configure. The wrapper continues
to unset all four variables. MPI and OpenMP are disabled.

Two failed attempts require a ticket handoff under AGENTS.md:

1. Preparation initially used `Path.write_text(newline=...)`, unsupported by
   the Windows Python version. It failed before modifying WRF. Using
   `Path.open(..., newline=...)` fixed it. Classification: host tooling.
2. Configure returned zero and the wrapper printed PASS, but log lines 93-94
   report that `tools/rpc_test.exe` cannot execute on Windows, followed by an
   empty shell comparison. Classification: **cross-configuration**.
   `configure:1031` executes a target program to distinguish RPC header
   families. `tools/rpc_test.c` checks `_RPC_TYPES_H` and `_TIRPC_TYPES_H`.
   Generated `CFLAGS_LOCAL` has no `RPC_TYPES`: the following sed also assumes
   a comment marker absent from the custom entry. Proposed next action:
   identify the target header family by preprocessing, set `RPC_TYPES`
   explicitly, and replace the execution probe with that compile-time answer
   in the retained patch. This fix is **not applied or tested**. The reduced
   reproducer is the command substitution at `configure:1031`; the target
   executable need not be run again on Windows.

No WRF scientific source changed. No ICE or assembler defect occurred; no
compiler reproducer is applicable. No em_real compilation, WRF link, hot-loop
report or card run occurred. Configuration took **0.2 minute**, including its
compile/link probes. Logical trial size before this update: **532,862,730
bytes** in 10,221 files (532.9 MB decimal), below 25 GB. Nothing was deleted.

Configuration command:

```text
python tools/run.py --name S11-21-wrf-configure --inputs ../_shared/wrf-trial/trial-env.sh ../_shared/wrf-trial/wrf-configure.sh ../_shared/wrf-trial/src/patches/wrf-4.8.0-knc-cross.patch -- C:/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/cygwin/bin/bash.exe ../_shared/wrf-trial/trial-env.sh bash ../_shared/wrf-trial/wrf-configure.sh
```

Log: `.work/_state/logs/S11_21_wrf_configure-20261112-204658.log`.
Read-only inspection log: `S11_21_wrf_config_inspect-20261112-204505.log`.
The hook required the initial combined inspection to use the wrapper and
rejected a broad log read; subsequent reads used targeted searches.

E7-20 plan update: work package 1 below now starts from the complete export,
not a new export request. Its remaining work is the RPC cross-probe correction
and making configure diagnostics fail the wrapper. Host/target tool selection,
static runtime flags and classic netCDF configuration are established. Other
work packages and effort estimates remain pending the serial build.

### Continuation after the 20:52 RPC answer

`wrf-post-configure.sh` preprocesses a file including `<rpc/types.h>` with
`k1om-mpss-linux-gcc -march=knc -E -dM`. The target defines `_RPC_TYPES_H=1`.
It writes `-DRPC_TYPES=1` into generated `CFLAGS_LOCAL`; no target program
is executed. No TIRPC probe or landread fallback was needed. This resolves
the preceding **cross-configuration** blocker. The initial post-configure
step passed in less than 0.1 minute, log
`S11_21_wrf_rpc-20261112-205505.log`.

The first `./compile -j 8 em_real` failed in **0.4 minute**. The trial's
custom stanza had been appended after `#ARCH NULL` without a following
`#ARCH` marker. `arch/Config.pl:490` only switches to the postamble when it
sees that next marker. Consequently `configure.wrf` lacked suffix rules,
`NETCDFPATH`, combined compiler/link flags and other common definitions.
This is a **trial cross-configuration error**, not an upstream WRF or GCC
defect. Log: `S11_21_wrf_em_real-20261112-205523.log`.

The resulting error inventory is:

| Location | Construct/diagnostic | Classification |
| --- | --- | --- |
| `frame`, log 56/142 | Missing `externals` rule and `module_state_description.o` prerequisite | Missing generated postamble/rules |
| `external/io_netcdf/diffwrf.F90:56` (preprocessor diagnostic), log 152/162 | `netcdf.inc` absent from `-I/include`; then `wrf_data.mod` missing | Empty `NETCDFPATH`, cascading configuration failure |
| `external/io_netcdf/wrf_io.f:369`, `field_routines.f:41`, `module_wrfsi_static.f:9`, log 185/193/201 | `netcdf.inc` cannot be opened | Same configuration failure |
| `external/io_netcdfpar/diffwrf.F90:56`, log 224/234 | `netcdf.inc`, then `wrf_data_ncpar.mod` missing | Missing I/O selection from postamble also attempted this unselected parallel backend |
| `external/io_netcdfpar/wrf_io.f`, `field_routines.f`, `module_wrfsi_static.f`, log 257/265/273 | Missing `mpif.h` or `netcdf.inc` | Same unselected parallel backend/configuration failure |
| `share`, `phys`, `dyn_em`, `main`, log 364/423/451/458 | Missing rules/prerequisites for `module_model_constants.o`, `ccpp_kind_types.o`, `module_bc.o`, `module_wrf_top.o` | Cascades from missing common rules |
| `phys/Makefile:441` submodule recipes, log 382-408 | Git searches upward into GCC-KNC and rejects dubious ownership | Exported-source host integration; no Git safety configuration was relaxed |

`fix-wrf-configure.py` adds the terminating marker and retains the diff in
`src/patches/wrf-4.8.0-knc-configure-fix.patch`, applied after the previous
cross patch. It also makes `WRF_KNC_CROSS=1` defer the RPC execution probe
to the post-configure script; normal configure behavior is unchanged.
Both wrappers set `GIT_CEILING_DIRECTORIES` to the trial root to keep source
export Git discovery out of the parent repository.

Regeneration with the corrected stanza passed in **0.1 minute**, including
post-configure checks for `NETCDFPATH` and the `.F.o` rule. Log:
`S11_21_wrf_configure_complete-20261112-205716.log`. The Fortran 2003 IEEE,
ISO_C and FLUSH and Fortran 2008 GAMMA executables exist; `ARCH_LOCAL` has
none of their disabling macros. These are compile/link probe outcomes, not
native execution results. `NETCDF_classic=1` selected classic output, so the
nc4 probe was not run and has no executable. `NETCDF4_IO_OPTS` is a template
definition, while configure reports classic output and no HDF5 libraries.
Generated top-level link flags select static GCC 16 runtimes; the auxiliary
link exception discovered below still needs correction. No dependency tests
were repeated.

The corrected `em_real` attempt ran from **20:57:31 to approximately
21:00:48 (3.3 minutes)** before termination after the second failed attempt.
WRF's recursive `make -i` continued past fatal errors into physics. Interrupting
the wrapper left Cygwin children alive, so its process group's working
directory was checked against the trial source tree and that group was
terminated. A subsequent Cygwin `ps -l` showed no remaining build processes.
The wrapper has no final PASS/FAIL summary for this interrupted attempt.
Log: `S11_21_wrf_em_real_complete_config-20261112-205731.log`.

Two actionable causes remain:

1. **Source-export/host compatibility:** Registry preprocessing at log 1976
   cannot open `Registry/registry.dimspec`, although that regular file exists
   (8,791 bytes). `Registry.EM_COMMON` contains 3,727 CR bytes. In
   `tools/reg_parse.c:127-139`, the include parser copies the name from the
   line and removes LF only, leaving the CR in the filename. The split
   diagnostic in the log agrees with this cause. Proposed correction:
   normalize the copied Registry text to LF, recording it as an export
   compatibility transformation. This correction is **not applied/tested**.
   A reduced invocation for follow-up is `tools/registry -DEM_CORE=1
   -DNMM_CORE=0 -DDA_CORE=0 -DWRFPLUS=0 Registry/Registry` from the copied
   WRF root; the full command actually used is in log 1971. Validate Registry
   generation before rebuilding the model.
2. **Cross-build contamination from the first attempt:** the auxiliary
   `external/io_int/test_io_idx` link fails at log 1362-1366 for `io_int_loc`
   and `io_int_index`, called by the `bind(c)` interfaces in
   `module_io_int_idx.F90:74,84`. The first log, line 314, shows `io_int_idx.c`
   compiled with bare host `cc` because the postamble was missing; the second
   attempt reused that object in `libwrfio_int.a`. Rebuild all products from
   that malformed configuration in a clean trial build, not only this one
   object. This is not evidence of a compiler ABI defect. Also propagate
   `-static-libgcc -static-libgfortran` to auxiliary Fortran link rules:
   `test_io_idx` does not consume the top-level `LDFLAGS`. It failed before
   creating an executable; no dynamic-runtime check was possible.

Remaining diagnostics from that attempt are classified below. Repeated
instances and exact compile commands remain in the log.

| Files/constructs | Diagnostics and classification |
| --- | --- |
| `frame/module_state_description.F`; `module_streams`, `module_driver_constants`, `module_domain_type`, `module_configure`, `module_domain`, `module_io`, `nl_access_routines` | Missing generated source or `switches_and_alarms.inc`, `model_data_order.inc`, `state_subtypes.inc`, `scalar_tables.inc`, `allocs.inc`, `io_form_for_dataset.inc`, `nl_config.inc`; Registry cascade |
| `share/module_io_domain`, `set_timekeeping`, `wrf_bdyin`, `wrf_bdyout`, `dfi`, `mediation_feedback_domain`, `mediation_force_domain`, `mediation_interp_domain`, `mediation_integrate`, `mediation_wrfmain` | Missing `module_io_domain_defs.inc`, `set_timekeeping_defs.inc`, `wrf_bdyin.inc`, `wrf_bdyout.inc`, `actual_new_args.inc`, `dummy_new_args.inc`, `med_last_solve_io.inc`, `fine_stream_input.inc`; Registry cascade |
| `dyn_em/solve_em.int`, `start_domain_em.int` | Missing `dummy_new_args.inc`; Registry cascade |
| Generated `module_streams.f90`, `module_driver_constants.f90`, `module_configure.f90` (including `../frame` paths) | Unexpected EOF after failed preprocessing; Registry cascade, not a Fortran strictness finding |
| Consumers of `module_bc`, `module_comm_dm_0`, `module_configure`, `module_cpl`, `module_date_time`, `module_domain`, `module_domain_type`, `module_driver_constants`, `module_io`, `module_machine`, `module_state_description` | Missing `.mod` files downstream of failed generation/compilation |
| Physics consumer of `ccpp_kind_types` (log 5899-5901) | Missing `.mod` before its producer compile appears at log 5921; possible upstream parallel dependency ordering issue, unresolved independently of Registry |
| `phys/Makefile` submodule checks, log 5840/5842 | Export is not a Git repository; ceiling now prevents parent discovery. Export-aware checks/link setup still needed; no successful network checkout |

No ICE or wrong-assembly diagnostic was found. No GCC defect is claimed and
no compiler reproducer is warranted. These are not native failures. Total
new configure/build time is approximately **3.8 minutes**; the second build
was deliberately interrupted. Logical trial disk use after termination:
**556,344,525 bytes in 11,071 files** (556.3 MB decimal), below 25 GB. No WRF
executable or native run was staged. Stale outputs await lead-directed cleanup.

## Vectorization

The interrupted second attempt emitted `-fopt-info-vec` output while WRF's
make continued into physics. These are partial compiler reports, not proof
of linked/native correctness or measured hotness. Lines refer to retained
preprocessed Fortran in `src/WRF-4.8.0/phys/`:

| Routine and generated source | Loop/construct | Compiler report |
| --- | --- | --- |
| `wsm5`, `module_mp_wsm5.f90:147` | Inner `i` loop under `j/k`, computing temperature from `th*pii` and copying cloud/rain/snow arrays | 64-byte vectors, factor 16; masked epilogue reported |
| `cuddrafn`, `physics_mmm/cu_ntiedtke.tmp.f90:2617` | Inner `jl` loop under descending `jk`, zeroing a rate and conditionally updating a cloud-top index | 64-byte vectors, factor 16; masked epilogue reported |
| `THL_RT_FROM_TH_R_MF`, `module_bl_mfshconvpbl.f90:2095,2098` | Array expressions summing water species and correcting potential temperature | 64-byte vectors, factor 16 (log 13688/13786) |

The first two match the input's short-row/inner-horizontal-loop concerns;
no particular short trip count or performance gain was established here.
No `missed:` diagnostics were emitted by the selected `-fopt-info-vec`
setting. Absence of a success message does not establish a missed-vector
reason. Dynamics and systematic missed-reason analysis remain blocked;
collect `-fopt-info-vec-all` on selected files after the build blockers clear.
The input in
`docs/research/wrf-input-2026-11-06.md` prioritizes short innermost `i` rows in
`j/k/i` loops, k extents around 50–51, constant `/12` and `/60`, gathers,
unaligned accesses, and invariant `sin`/`SIZE`. Its GCC 5 and hand-written
kernel measurements are prior input, not observations about this compiler.
Do not substitute synthetic kernel results for whole WRF loop reports.

## Proposed E7-20 work

These are proposed work packages, not dispatched tickets. Estimates are
engineering effort, not measured build times.

Latest ordering correction: package 1 starts with the supplied export,
normalizes copied Registry text to LF, fixes exported-source submodule
checks, and regenerates in a clean build state to discard stale host
objects. Retain the architecture terminator and RPC preprocessing patches;
validate Registry generation first. Package 3 must propagate static-runtime
flags to auxiliary links and investigate the `ccpp_kind_types` parallel
dependency before another full attempt. The estimates below are unchanged.

1. **Reproducible source/configuration baseline (0.5–1 day):** export a pristine
   WRF 4.8.0 revision from the read-only source repository, preserve its licence,
   and isolate only the necessary cross configuration from PhiWeather's local
   changes. First obtain a lead-approved export path; include all seven pinned
   physics submodules and replace host/target execution configure probes. Establish host tools versus target tools and classic netCDF options.
2. **GCC 16 dependency stack (1–2 days, after this trial):** retain the
   corrected environment and successful relative-directory installation of
   netCDF-C, retain the now-built classic Fortran compatibility patch and fresh GCC 16
   modules, and retain the passed no-C++ API link and static GCC/Fortran runtime
   rule;
   classify strictness versus cross-probe failures without executing target
   probes on the host. Any compiler defect gets a separate reduced case and
   lead-built compiler fix before this work resumes.
3. **Serial `em_real` compile/link (1–3 days after dependencies):** generate
   configuration, use documented compatibility flags only where diagnostics
   justify them, and build `real.exe`/`wrf.exe`. Record every source/strictness,
   cross-configuration or compiler blocker and any minimal patch.
4. **Hot-loop compiler evidence (0.5–1 day after compilation):** collect
   `-fopt-info-vec-all` with file/line/routine identification on selected
   dynamics/physics loops matching the supplied hot-loop input. Record missed
   legality/cost/data-dependence reasons; do not enable fast math to improve
   counts. Split demonstrated backend gaps into separate tickets.
5. **Lead-coordinated serial native smoke (0.5–1 day plus card scheduling):**
   stage linked programs and required target runtime libraries. Agree on a
   small, single-domain WPS `met_em` case, namelist, WRF runtime tables, output
   space and measured memory requirement with PhiWeather. Run `real.exe`, then
   a short `wrf.exe` forecast with one process/thread; compare initialization,
   termination and scientific outputs with an agreed reference. No memory or
   correctness claim is supportable until the actual case is specified.
6. **MPI/OpenMP and realistic cases (2–4 days plus card scheduling):** rebuild
   MPICH's Fortran bindings, verify cross ABI settings, then progress through
   `dmpar` and `dm+sm`. Reassess memory per rank and thread count using observed
   affinity/scaling; the input's 2-threads/core preference is workload-specific.
   Native runs belong to the lead. Keep performance tuning separate from
   correctness and avoid treating this exploratory build as milestone credit.
