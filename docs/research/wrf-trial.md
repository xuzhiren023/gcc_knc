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
Cygwin host utilities. Both run through `tools/run.py`:

```text
python tools/run.py --name S11-21-inputs -- python ../_shared/wrf-trial/prepare.py
python tools/run.py --name S11-21-netcdf-c-configure -- C:/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/cygwin/bin/bash.exe ../_shared/wrf-trial/netcdf-c.sh
```

## Stage reached and blockers

**Stopped in stage 2, during netCDF-C compilation.** Configure completed and
some C objects compiled, but no complete dependency library was installed.
netCDF-Fortran, MPI and WRF were not built. No `wrf.exe` or `real.exe` exists
from this trial, nothing is staged for a card run, and no native test ran.
No GCC-KNC ICE or assembler defect was observed.

| Finding | Classification | Evidence and disposition |
| --- | --- | --- |
| Cygwin `mkdir -p` failed on `/cygdrive/c/Users/xuzhi` while trying to create the authorized trial build/install directories. | Host infrastructure, before cross configuration; not a WRF or GCC defect. | Initial wrapped attempt exited 1 before configure. Created just the two trial directories with native PowerShell and removed the shell directory-creation step. The next attempt passed this point. |
| `libdispatch/dreg.c:13:10: fatal error: windows.h: No such file or directory`. | Cross-configuration/environment contamination; not GCC 16 strictness or a GCC-KNC defect. | The parent environment has `MSYSTEM=MINGW64`. netCDF-C `configure:5945–5948` sets `ISMINGW=yes` and `ISMSYS=yes` for any nonempty `MSYSTEM`, even with Linux `--host`. `configure:24278` enables `REGEDIT` from `ISMSYS`; `libdispatch/Makefile.am:55–57` consequently adds Windows registry source `dreg.c` to the target library. The generated makefile has `am__append_8 = dreg.c`; `config.log` confirms `ISMSYS=yes`, `ISMINGW=yes`, and enabled `REGEDIT`. |

The second attempt selected the intended GCC 16.2.0 C and C++ executables
(the wrapper log records their paths) and used `-O2 -march=knc`. The missing
Windows header is the only fatal compiler diagnostic in that attempt.
Warnings also reported `strndup` redefinition in `libdispatch/ncuri.c:81`
and an old-style function definition in `libdispatch/dcrc32.c:263`; both
were nonfatal and were not changed or suppressed. Configure warnings about
disabled DAP/S3/filter features, a missing documentation `dot` tool and the
cross-prefix/host-alias difference were also nonfatal.

The likely next action is to **unset inherited `MSYSTEM` for the Cygwin
build subprocess**, reconfigure the existing trial build directory, and resume
the same build with no netCDF source patch. This fix has **not been tested**.
The session stops with a ticket question because AGENTS.md requires `pm.py ask`
after two real failed attempts. This is a procedural stop with a concrete
environment diagnosis, not evidence that netCDF or WRF cannot build with
GCC-KNC. No third attempt was made.

A reduced reproduction using the retained generated makefile is:

```sh
# In the supplied Cygwin, with the PATH from wrf-trial/netcdf-c.sh:
make -C /cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/wrf-trial/build-netcdf-c/libdispatch libdispatch_la-dreg.lo
```

This target is the failing command identified in the build log; it has not
been rerun as a separate test. The issue can also be inspected without a build
by tracing `MSYSTEM` → `ISMSYS` → `REGEDIT` in the retained configure script
and generated makefile. A compiler-defect reproducer is not applicable.

### Time, disk and logs

The initial directory-creation failure took less than 0.1 minute. The second
wrapper reports **4.4 minutes** for configuration plus the failed parallel
build, including partial compilation; it does not measure compilation alone.
No WRF compilation time is available. Parallel make was capped at **8** jobs.
After the failed build, the trial tree held **46,685,850 logical file bytes**
(46.7 MB decimal, about 44.5 MiB), across 3,044 files, including the copied
archives and extracted C source. This is well below either interpretation of
the 25 GB budget; filesystem allocation overhead was not measured.

Logs, relative to `.work/_state/logs/`:

- `S11_21_inputs-20261112-191724.log`: input copying passed; 8,389,536 initial
  trial bytes.
- `S11_21_netcdf_c-20261112-191731.log`: initial mkdir infrastructure failure.
- `S11_21_netcdf_c_configure-20261112-191753.log`: configure and partial build;
  exit 2, 644 lines, fatal diagnostic at line 632.

The current source, configuration, partial objects, reference recipes and
scripts remain in `.work/_shared/wrf-trial/`; no per-attempt build tree was
created. No GCC build, x86 check, benchmark or card job was started.

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
2. **GCC 16 dependency stack (1–2 days, after the ticket response):** remove
   inherited MSYS detection from the Cygwin subprocess environment, reconfigure,
   and build static
   netCDF-C followed by netCDF-Fortran, fresh modules and target-runtime links;
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
