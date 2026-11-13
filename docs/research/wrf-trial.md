# WRF trial with GCC-KNC

## OpenMP continuation (S11-24, 2026-11-13)

Both OpenMP executables linked and are staged with GCC-KNC's shared
libgomp in `smpar/`. ELF/dependency checks and instruction lint passed. No native result is claimed. The lead runs the smoke, scientific
comparison and timing.

All trial paths below are relative to `.work/_shared/wrf-trial/`. The fresh
`src/WRF-4.8.0-smpar/` is WRF 4.8.0 supplied by the lead with seven pinned
physics submodules; the serial source tree is untouched. `smpar-prepare.py`
normalized 4,883 text files, adapted the GNU configure entry to k1om smpar,
skipped submodule Git updates, and retained the serial physics submake
needed for module dependency ordering. `trial-env.sh` removes MSYS variables
and selects GCC-KNC 16.2.0, the bootstrap binutils and Cygwin host tools.
`smpar-configure.sh` performed `./clean -a`, option 1, nesting answer 0,
and reused the installed static netCDF-C 4.9.2/netCDF-Fortran 4.6.1 prefix.

Configuration: `em_real`, OpenMP (`-fopenmp`), no MPI, no nesting; normal
C/Fortran optimization and link flags are `-mphinix -mknc-card=7120`.
The explicit card prevents probing. Observed expansion includes `-O3`,
`-march=knc -mtune=knc`, small-loop unrolling, cacheline data alignment,
loop prefetch, L2/L1 distances 32/16, and `-fno-math-errno`; no fast-math.
WRF's big-endian conversion, four-byte records, free-form line length,
compatibility switches and upstream special optimization rules remain.
GCC/Fortran support uses `-static-libgcc -static-libgfortran`; OpenMP uses
GCC-KNC's shared `libgomp.so.1`, to be staged beside the two executables.

Per-object private `FCOPTIM` overrides retain `-mphinix -mknc-card=7120`:

| Object | Override | Reproducer and finding |
| --- | --- | --- |
| `module_ra_rrtm.o` | `-O1` | `repro/rtrn.f90`; RTRN postreload ICE, S11-23; SLP-only failed in S11-21. S11-23 removes this workaround after prefix reinstall and rebuild. |
| `module_sf_sfclay.o` | `-O1` | `repro/sfclay1d.f90`; SFCLAY1D `do_store_flag` ICE, S11-25; SLP-only failed in S11-21. This workaround stays until S11-25. |
| `module_small_step_em.o` | `-O2` | `repro/advance_uv.f90`; S11-23 postreload constraint ICE, SF move xmm12 to xmm15. Reduced and full module pass at `-O2`; the lead confirmed the reproducer passes at normal phinix flags with S11-23 fix `64c033d1255`. S11-23 removes this workaround after prefix reinstall and rebuild. |
| `module_cu_kf.o` | `-O2` | `repro/kfcps.f90`; S11-23 postreload constraint ICE, SF move to xmm14. SLP-only failed; reduced and full module both pass at `-O2`; the lead confirmed the reproducer passes at normal phinix flags with S11-23 fix `64c033d1255`. S11-23 removes this workaround after prefix reinstall and rebuild. |

`repro/reproduce-kfcps.py` checks the passing `-O2` flag on reduced and full
inputs; `repro/KFCPS-NOTES.txt` retains the failing command and log references.
WRF's licence is retained in `repro/LICENSE-WRF.txt`. No compiler change or
GCC build was made. The resumed build uses `smpar-build.py`/`.sh`; all
build/check invocations go through `tools/run.py`.

Logs under `.work/_state/logs/`:

| Log | Result and wall time |
| --- | --- |
| `S11_24_smpar_configure-20261113-001045.log` | Pass, 0.4 min. |
| `S11_24_smpar_build-20261113-001128.log` | KFCPS ICE, 15.4 min. |
| `S11_24_kfcps_repro_workaround-20261113-002835.log` | Reduced ICE confirmed; SLP-only full-module workaround fails, 0.2 min. |
| `S11_24_kfcps_O2-20261113-004015.log` | Reduced and full-module `-O2` compilation passes, 0.2 min. |

The first resumed build stopped after 29.1 min at `advance_uv`; the isolated
routine reproduces the ICE without WRF module inputs, using a reduced
configuration type. `repro/reproduce-advance-uv.py` confirmed the ICE and
compiled both reduced/full inputs at `-O2` in 0.2 min. Logs:
`S11_24_smpar_resume_O2-20261113-004107.log` and
`S11_24_advance_uv_repro_workaround-20261113-011143.log`.

The final incremental continuation passed in **36.9 min**:
`S11_24_smpar_resume_four_workarounds-20261113-011256.log`.
The three model-build attempts total about **81.4 min** (15.4 + 29.1 + 36.9),
including failed/interrupted work; this is not a clean-build benchmark.
Reproducer/workaround checks totaled 0.6 min, vector diagnostics 1.2 min.
No further ICE was reported in the successful continuation.

`smpar-stage.py` passed in 0.1 min:
`S11_24_smpar_stage-20261113-015003.log`. Both models and the private runtime
are ELF64 little-endian K1OM (machine 181). `readelf -d` results are retained
in `smpar/elf-checks.txt`:

| Staged artifact | Bytes | Dynamic NEEDED entries |
| --- | --- | --- |
| `smpar/wrf.exe` | 70,717,358 | `libm.so.6`, `libdl.so.2`, `libgomp.so.1`, `libpthread.so.0`, `libc.so.6` |
| `smpar/real.exe` | 52,488,940 | Same as wrf.exe. |
| `smpar/libgomp.so.1` | 2,436,655 | `libdl.so.2`, `libpthread.so.0`, `libc.so.6` |

GCC and Fortran support are static; OpenMP is the shared runtime copied
from `.work/_shared/gcc-knc-16.2.0/`, not the card's GCC 5 library.
Measured trial storage after staging is **2,043,508,160 logical bytes**
(links not followed), including the untouched serial tree; logs are separate.
`smpar/RUN-NOTES.md` gives the 60/120/240-thread launch settings, libgomp
selection, binding/place defaults, stack sizing, namelist tiles, workarounds
and vector notes. Instruction lint of both executables and the supplied
libgomp passed (exit 0, no violations) in 5.2 min:
`S11_24_smpar_binary_lint-20261113-015020.log`. No card job or x86 check ran.

## Serial baseline (S11-21)

Serial, no-nesting `em_real` linked at `-O2 -march=knc` with the RRTM and
SFCLAY per-file `-O1` workarounds above. The final incremental build and
ELF/internal-I/O archive checks passed in 65.4 min (not a clean-build time):
`S11_21_wrf_two_workarounds-20261112-223524.log`. Both executables were K1OM
and needed only `libm.so.6`, `libdl.so.2`, `libc.so.6`; GCC support was static.
`wrf.exe` was 65,234,334 bytes; `real.exe` was 48,208,178 bytes. Trial storage
was 984,383,044 logical bytes. Instruction lint had no recorded completion;
no native test or timing was performed. The lead handles serial-tree removal.

The serial vector check passed in 0.9 min:
`S11_21_wrf_vector_notes-20261112-231545.log`; reports remain in
`vector-notes/module_mp_wsm5.vec.txt` and `module_advect_em.vec.txt`.
At `-O2`, WSM5's inner horizontal temperature/species-copy loop at generated
line 147 and `advect_u` inner rows at 186/199 use 64-byte vectors, factor 16,
with masked epilogues. WSM5 effective-radius loops at 1896/1904/1912 miss
because of unsupported control flow; outer loops also miss where nests
contain multiple consecutive inner loops. The smpar WSM5 check at `-mphinix -mknc-card=7120 -fopenmp` passed in
0.1 min (`S11_24_smpar_vector_wsm5-20261113-005110.log`): line 147
retains the same vector width/factor/masked epilogue, and 1896/1904/1912
retain the same control-flow misses. The advection check passed in 1.1 min
(`S11_24_smpar_vector_advection-20261113-011204.log`): `advect_u`
rows 186/199 retain the same 64-byte vectors, factor 16 and masked epilogues;
the outer loop at 181 still misses because of consecutive inner loops.
These are compiler decisions, not native performance/correctness results.
The hot-loop input is `docs/research/wrf-input-2026-11-06.md`.

Prior setup transcripts and historical stops were moved out of this report
to `.work/_state/logs/S11_24_wrf_trial_previous_report.log`. Shared setup
scripts retain cross-configuration, static runtime linking, target RPC
preprocessing, netCDF compatibility fixes and the physics ordering workaround.
