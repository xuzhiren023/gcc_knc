# What the WRF/IMCI project offers gcc_knc (survey, 2026-11-04)

The owner asked for this. A read-only Claude survey of `C:\Users\xuzhi\Documents\PhiWeather` (another
project; read-only for us, and not a requirement). Paths are relative to that folder. Nothing was
copied.

## How they build (learn only)

They do not compile for KNC with a KNC compiler. Host GCC 14.3 emits scalar SSE2 x86_64 assembly
(no vectorization, `-ffixed-r11`, `-frounding-math`), and
`native/translation/strict-arithmetic/single-lane/translate.py` rewrites it into one-lane masked
IMCI. The card then assembles and links it with a native GCC 5-era `as`/`ld` that they built and
staged in the card's `/tmp`. Their older production build used the apc-llc `gcc-5.1.1-knc` fork,
our donor. Our compiler is the path that vectorizes; theirs is a translator.

## Reusable, mapped to our roadmap

| Item | Where | Our use |
|---|---|---|
| WRF v4.8.0 source (public domain), build lists, reference case and old x87 outputs | `native/upstream/WRF` (948 `.F`, 373 `.f90`), `native/toolchains/build-wrf-*.sh`, `testcases/x1` | **M5 corpus and output oracle**: a large Fortran compile corpus (modules, derived types with pointers, cpp, namelist and I/O, OpenMP tiles, MPI) |
| Small Fortran probes | `native/reference/{fortran-features,openmp-probe,mpi-probe,netcdf*-probe}.f90` | **M3 first tests** for our libgfortran slice, libgomp and MPI bindings (sources only) |
| MPICH 3.4.3, netCDF-C 4.9.2 / Fortran 4.6.1, HDF5 1.10.10, zlib 1.3.1 recipes and patches | `.tools/knc-bootstrap/scientific-*`, `native/patches/mpich` | **M3 (S8) recipes.** Their binaries are gfortran 5 ABI (`.mod` version 14, `libgfortran.so.3`), which is incompatible with GCC 16 gfortran, so we rebuild them with our compiler |
| libgomp with a futex wait and `pause` replaced by `nop` | `native/patches/gcc-knc/0003-libgomp-knc-spin-hint.patch` | **M3 (S8)**: same need; we already have a KNC spin-hint pattern |
| OpenMP runtime settings | their state notes (`MALLOC_ARENA_MAX=64`, `OMP_WAIT_POLICY=ACTIVE`, close binding; the arena change took 14.07 to 5.52 s/step) | **M3/M4** defaults to test, and a performance lesson |
| CORE-MATH (MIT) and openlibm sources; 63 scalar libm objects; the vector-function names WRF calls | `.tools/wrf-strict-math/`, `native/translation/libknc_mvec/symbols.json` (36 `_ZGVeN16v_*` names) | **M4 vector math (S10)**: correctly rounded scalar oracles, and a demand list for our vector function ABI |
| GCC 5 LRA secondary-move reload patch | `native/patches/gcc-knc/0002-*.patch` | Read when we touch secondary reloads; check that GCC 16 KNC does not need it |
| Reviews written about this project | `docs/reviews/GCC_KNC_TECHNICAL_RESEARCH_REPORT_20261101.md`, `..._INDEPENDENT_RESEARCH_REVIEW_20261101.md` | Read before M2 planning |

## KNC facts they found (checked against ours)

- MXCSR bit 21 (DUE) must stay set; bits 7-12 and 20 raise #GP; loading `0x1f80` faults
  (`native/translation/ABI_KNC_MXCSR.md`). Our `crtfastmath` reads, sets FTZ and DAZ, and writes
  back, so it is safe. Any future code that loads an MXCSR constant must keep bit 21: a lint
  candidate.
- MPSS binutils is required (stock 2.36 in k1om mode rejects `kmov` and `vpackstore*`); we use it.
- The MPSS `ld` fails on merged `.debug_str` relocations in `libgcc`; they link with
  `--strip-debug`. Worth knowing if our debug builds fail to link.
- x87 raises DE on denormal loads; `pause` does not exist; the card's libc/libm differ from the
  sysroot's.

## Not reusable

Their binaries (gfortran 5 ABI; the MPSS sysroot's redistribution review is open), their
translator, and their card packet tooling (ssh-based; we run everything through `tools/card_run`).
We already share the ledger protocol.
