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

**Stage 2: netCDF-C compiled and installed successfully; netCDF-Fortran compilation failed.** The clean
build produced `build-netcdf-c-nomsys/liblib/.libs/libnetcdf.a` (1,770,676 bytes)
with GCC-KNC 16.2.0, `-O2 -march=knc`, and no source patch. `make -j8` completed;
the first `make install` failed while creating the include directory. The
relative-directory installation described below succeeded. This was a
host filesystem/tool interaction, not a compiler diagnostic. netCDF-Fortran
configured with GCC 16 and the installed C library, then failed on the classic
Fortran source path. No Fortran library or complete module set was installed. WRF and MPI
remain unbuilt; no executable is staged for the card.
There was no observed GCC-KNC ICE or wrong assembler output, so no compiler
reproducer is applicable.

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

The next wrapped command ran `netcdf-fortran.sh`. Configure succeeded and
automatically added `-fallow-argument-mismatch` to the GCC 16 Fortran flags;
the compile errors above are not argument-mismatch diagnostics. `make -j8`
failed before installation. No dependency patch was applied. Two failed
wrapped attempts in this resume (absolute C install, then Fortran build)
require a ticket question before another attempt under AGENTS.md.

Reduced build targets for the lead (extracted from the failure; not rerun):

```sh
# Under trial-env.sh, from the worktree:
make -C ../_shared/wrf-trial/build-netcdf-fortran/fortran netcdf.lo module_netcdf_nf_data.lo
```

The specific next decision is whether to patch the copied classic Fortran
path to use the distributed expanded/eight-byte sources and make its
quantization constants available consistently, or select a corrected
netCDF-Fortran source baseline. The proposed patch is not implemented or
tested; its exact replacement includes need source inspection before editing.
The analogous PhiWeather source directory also lacks the subset include files.

### Time, disk and logs

Earlier attempts: directory creation failed in less than 0.1 minute;
contaminated configuration plus partial compilation took 4.4 minutes.
The fresh configuration and overly strict pre-build guard took **4.2 minutes**;
this was configuration time, with no make invocation. The subsequent clean
compilation plus failed install took **0.8 minutes**. No WRF compilation time
is available. The successful C install took **0.1 minute**; Fortran configure
and partial compilation took **1.9 minutes** together. Make was capped at 8 jobs.

After the Fortran failure, the trial contains **65,435,787 logical file bytes**
(65.4 MB decimal, 62.4 MiB) in 4,229 file entries, including both C build trees,
the installed C library, archives, and partial Fortran build. This measurement
uses `os.walk` and `lstat` without following Cygwin reparse files; allocated disk
blocks were not measured. It is well below the 25 GB budget. A first size walk
that followed links failed on a Cygwin link in the stale build; it made no
changes. Stale files remain for lead cleanup as directed.

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

## Vectorization

No WRF loop compilation result is available: stage 4 was not reached. No
`-fopt-info-vec` report was generated, and no loop is claimed to have vectorized.
The input in
`docs/research/wrf-input-2026-11-06.md` prioritizes short innermost `i` rows in
`j/k/i` loops, k extents around 50–51, constant `/12` and `/60`, gathers,
unaligned accesses, and invariant `sin`/`SIZE`. Its GCC 5 and hand-written
kernel measurements are prior input, not observations about this compiler.
Do not substitute synthetic kernel results for whole WRF loop reports.

## Proposed E7-20 work

These are proposed work packages, not dispatched tickets. Estimates are
engineering effort, not measured build times.

1. **Reproducible source/configuration baseline (0.5–1 day):** export a pristine
   WRF 4.8.0 revision from the read-only source repository, preserve its licence,
   and isolate only the necessary cross configuration from PhiWeather's local
   changes. Establish host tools versus target tools and classic netCDF options.
2. **GCC 16 dependency stack (1–2 days, after this trial):** retain the
   corrected environment and successful relative-directory installation of
   netCDF-C, resolve the classic Fortran missing includes and quantization
   guards (or select a corrected dependency release), then build fresh modules and
   target-runtime links;
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
