# Donor inventory (S0-05)

Status: full-tree donor inventory and GCC 16.2 runtime/LRA source review complete.
The targeted full-source follow-up shows that the previously suspected missing
`1320(%rsp)` load is benign: the donor reloads the descriptor before both uses.
Submission follows the owner's 2026-11-02 decision allowing function-level
benign-load evidence. **No reduced patch 0002 reproducer is claimed**; that
original acceptance item remains unticked. No GCC 16 execution or card result
is claimed.

- [x] Entire donor tree covered against its recorded gcc-5 branch baseline.
- [x] Donor changes classified with reasons and GCC 16 landing locations.
- [x] Separate GCC 16.2 runtime dependency audit (F6), with file:line evidence.
- [x] Vector code generation scope and tuning recorded.
- [x] GCC 16 secondary-reload mechanism inspected.
- [ ] Reduced 0002 reproducer in `tests/regress/` (suspected full-source load difference is benign; see follow-up).

## Comparison boundary

Donor: <https://github.com/apc-llc/gcc-5.1.1-knc>, commit
`af7cc04cef723da3166f0d6f1539f02525fe5a93`.
Local reference checkout:
`C:/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/gcc-source`.

The earliest imported commit is
`cfd753e8744fd1515a0640a6c162d20732412b47`. Its message identifies its input as
`svn co svn://gcc.gnu.org/svn/gcc/branches/gcc-5-branch -r 222343 gcc-5.1.1`.
This supplies an identifiable gcc-5 branch baseline, rather than comparing only
the i386 directory. Its content has not been independently compared with FSF
r222343. The next commit, `cee3ea59c`, imports Intel's MPSS 3.6.1 patch;
`627ec4bc0` adds a fix for GCC bug 55930. Subsequent donor commits add README
instructions, disable CMOV, disable libitm in the documented configuration,
select MPSS assembler/linker explicitly, and add intrinsic wrappers.

Reproduce the inventory against these committed trees (the local checkout also
has later working-tree portability patches, which are outside this boundary):

```text
git diff --stat cfd753e87 af7cc04
git diff --name-only cfd753e87 af7cc04
git diff cfd753e87 af7cc04 -- <path>
```

The full-tree diff reports **85 files, 1498 insertions, 278 deletions**. It
includes generated configure scripts and non-KNC Intel compiler compatibility
edits; those must not be mistaken for 85 independent KNC backend changes.

## Disposition of donor changes

`port` means retain the behavior; `rewrite` means retain the requirement with a
new implementation; `drop` means do not carry the donor implementation. These
are research recommendations, not authorization to implement backend changes.

| Donor paths / change | Disposition | Reason and proposed GCC 16 landing location |
| --- | --- | --- |
| `gcc/config.gcc`, `gcc/config.host`: k1om target/host routing, defaults, malloc headers, TLS/offload routing | rewrite | Add explicit KNC cases to the same files; do not inherit every x86-64 feature or accelerator assumption. |
| `gcc/configure.ac`, `gcc/configure`: TLS, assembler/linker feature probes and target cases | rewrite | Update `gcc/configure.ac` and regenerate; probe the KNC tools rather than transplanting old x86 tests. |
| `gcc/config/i386/linuxk1om.h`: target defaults, loader, assembler/linker specs | port | Preserve `/lib64/ld-linux-k1om.so.2`, `--march=k1om`, `elf_k1om` in a KNC target header selected by `gcc/config.gcc`; re-evaluate the unused 32-bit configuration. |
| `gcc/config/i386/i386.opt`, `i386.h`, `i386-c.c`: KNC option, aliases, macros, CMOV/CX16 exclusions | rewrite | Put independent KNC flags/options in `i386.opt`, option handling in `i386-options.cc`, macros in `i386-c.cc`; keep SSE/AVX flags off and remove unused KNF aliases. |
| `gcc/config/i386/constraints.md`, `predicates.md`: KNC register classes and alignment predicates | rewrite | Use these same descriptions for KNC-specific constraints without enabling SSE or AVX-512 instructions. |
| `gcc/config/i386/i386.c`: ABI argument/result/varargs register enabling | rewrite | Audit `gcc/config/i386/i386.cc` ABI hooks for KNC registers independently of SSE capability. |
| `gcc/config/i386/i386.c`: `knc_cost`, memcpy/memset algorithm tables | rewrite | Translate into `gcc/config/i386/x86-tune-costs.h` and current tuning hooks; preserve visible transfer costs and treat unmeasured values as provisional. |
| `gcc/config/i386/i386.c`, `i386-protos.h`: masked scalar stores, misalignment moves, scratch selection, secondary reloads | rewrite | Implement in `gcc/config/i386/imci.md` plus minimal `i386.cc` hooks/prototypes; expose scratches, stack transfers and clobbers to the optimizer. |
| `gcc/config/i386/i386.md`, `knc.md`: scalar ABI moves using vector hardware, masks, reload patterns | rewrite | Place KNC patterns in `gcc/config/i386/imci.md` under `TARGET_KNC`; avoid widening shared SSE patterns indiscriminately. |
| `gcc/config/i386/i386.md`: KNC `kmov` spelling and prohibited mask logic/peepholes | port | Preserve the architectural restrictions and unsuffixed `kmov` in `imci.md`, with narrowly scoped shared exclusions where necessary. |
| `gcc/config/i386/i386.c`, `sse.md`: MXCSR builtin/pattern availability | rewrite | Add KNC-specific control-register support in `imci.md` and the current builtin implementation; MXCSR support does not establish SSE support. |
| `gcc/config/i386/sync.md`: locked stack OR instead of SSE2 fence | port | Add a KNC-specific fence alternative in `sync.md`/`imci.md`, preserving optimizer-visible memory effects. |
| `gcc/config/i386/avx512fintrin.h`: swizzle, reverse and multiply-reduction wrappers | rewrite | Use a separate KNC intrinsic header and `imci.md` patterns; inline assembly and AVX-512 feature pragmas are not a vectorizer implementation. |
| `gcc/lra-constraints.c`: memory-output secondary reload hook, SCRATCH exclusion, requeue transformed instructions | rewrite | Evaluate the equivalent paths in `gcc/lra-constraints.cc` first; shared allocator edits need independent justification and separate commits. |
| `gcc/lra-eliminations.c`: removed debug-insn guard | drop | No demonstrated KNC requirement; revisit only with a failing reproducer in `gcc/lra-eliminations.cc`. |
| `libgcc/config.host`: x86 routing, soft-float, CRT, unwind, cpuinfo | rewrite | Add a dedicated KNC configuration in `libgcc/config.host`; copying the x86 CRT/soft-float choices can retain unsupported instructions. |
| `libgomp/configure.tgt`: select linux/x86 futex runtime | rewrite | Select a KNC-safe runtime in `libgomp/configure.tgt`; x86 spin hints require separate source review. |
| `libgfortran/configure.host`: select `fpu-387`, IEEE support | rewrite | Audit `libgfortran/configure.host` and `config/fpu-387.h` before selecting it; x87 and MXCSR handling need separate validation. |
| `libstdc++-v3/configure.host`: i486 atomics, `-march=native`, ABI baseline, Darwin case | rewrite | Use explicit KNC routing in `libstdc++-v3/configure.host`; cross builds must not tune target atomics to the host or assume the x86-64 ABI baseline. |
| `libstdc++-v3/include/bits/{basic_string.h,list.tcc,stl_bvector.h,stl_deque.h,stl_iterator_base_types.h,stl_list.h,stl_vector.h}`, `include/debug/{deque,list,vector}`, `include/ext/vstring.h`, `include/profile/{deque,list,map.h,multimap.h,multiset.h,set.h,vector}` | drop | These are Intel-compiler C++ compatibility changes, not KNC ISA support; no GCC 16 landing changes proposed. |
| `libatomic/Makefile.am`, `Makefile.in`: optional dependency generation | drop | Build-system accommodation rather than KNC atomics; only revisit in the current Makefile if independently required. |
| `libatomic/configure`: k1om libtool/architecture cases | rewrite | Generate from current libtool/configure inputs after defining a safe KNC atomic implementation; this is not 16-byte atomic support. |
| `libquadmath/configure`: k1om libtool cases | rewrite | Generate from current inputs only after TFmode ABI/runtime support is audited; no donor quadmath arithmetic source changes exist. |
| `libitm/configure.tgt`, `configure`: x86-64 architecture/TLS routing | drop | The donor README subsequently disables libitm because it enforces SSE; these changes do not constitute usable KNC transactional memory support. Future support needs a separate runtime port. |
| `config.guess`: native k1om Linux recognition | port | Retain canonical native-host recognition in top-level `config.guess`, following the current config machinery. |
| `config/dfp.m4`: enable BID decimal float for k1om | rewrite | Audit target ABI and helpers before extending current `config/dfp.m4`; no implicit precision or representation change. |
| `libtool.m4`, `libgo/config/libtool.m4`: k1om treated as x86-64 linker emulation | rewrite | Use current libtool inputs with `elf_k1om`; the donor's `elf_x86_64` assignment must not be copied. |
| `boehm-gc/configure.ac`, `configure`: Linux thread/debug routing | drop | Legacy Java GC integration is not needed for the new compiler/runtime port; no landing changes proposed. |
| `libcilkrts/configure.ac`, `configure`: x86 selection | drop | Do not revive legacy Cilk runtime support as part of KNC enablement. |
| `libffi/configure.host`, `configure`: x86 target selection | rewrite | A future libffi port needs a verified KNC ABI implementation in `libffi/configure.host`/its x86 backend; selecting x86 alone is insufficient. |
| `libgo/configure.ac`, `configure`: x86 target case | drop | No demonstrated KNC Go ABI/runtime support; defer rather than carrying a misleading target alias. |
| `libcpp/configure.ac`, `configure`, `lex.c`: SSE scanner probes/guards returning null | drop | A host compiler runs on the host; native KNC support, if needed, must use a correct scalar scanner in `libcpp/lex.cc`, not null-returning SIMD stubs. |
| `libsanitizer/configure.tgt`, `configure`: advertise KNC ASan/TSan/LSan | drop | Architecture aliases alone do not establish runtime compatibility; no sanitizer enablement proposed. |
| `libsanitizer/sanitizer_common/sanitizer_internal_defs.h`, `sanitizer_platform_limits_posix.cc`: prefetch and absent SCSI header/ioctl guards | rewrite | If sanitizer support is pursued, use current platform capability checks in those runtime sources rather than broad historical KNC exceptions. |
| `README.md` | drop | Preserve useful architectural/build observations here; do not import donor-local installation commands. |
| `gcc/DATESTAMP` | drop | Donor date change is not a KNC feature; retain the new compiler's own version metadata. |

Generated-configure-only changes also occur in `libada`, `libbacktrace`, `libcc1`,
`libdecnumber`, `libgcc`, `libgfortran`, `libgomp`, `libiberty`, `libmpx`,
`libobjc`, `liboffloadmic`, `liboffloadmic/plugin`, `libssp`, `libstdc++-v3`,
`libvtv`, `lto-plugin`, and `zlib`. **rewrite** the relevant current build inputs
and regenerate their `configure` files, rather than porting generated edits;
**drop** legacy MPX/MIC-offload-specific build changes without a separately
supported runtime. There are no donor arithmetic or synchronization source edits
hidden in these generated-configure-only directories. Top-level `configure`,
`configure.ac`, `Makefile.def`, `Makefile.tpl` and `config.sub` are unchanged in
this comparison. Unlisted paths have no committed diff within this boundary.

## Vector generation and tuning evidence

The inspected donor additions supply **no KNC packed arithmetic/vectorizer
patterns**. `knc.md` operates on scalar `SI/DI/TI/SF/DF/TF` modes and `HI` masks:
it provides ABI transfers, reloads, masked scalar stores and misalignment
handling. Broadcasts and full-register moves in those paths use vector hardware
but do not implement loop vector arithmetic. Existing AVX-512 patterns remain
feature-gated. The later intrinsic-header additions include inline-assembly
swizzles and calls to AVX-512 intrinsic helpers; their presence is not evidence
of automatic KNC vector code generation. This is a source finding, not a new
compiler or card test result.

Details worth retaining as reference:

- QI/HI mask transfers select unsuffixed `kmov` for KNC, versus `kmovw` (or
  AVX-512DQ `kmovb`) elsewhere. Do not generalize the SSE/AVX-512 spellings.
- `knc_memcpy[64-bit]` and `knc_memset[64-bit]`: loop through 32 bytes,
  `rep_prefix_8_byte` through 8192, then libcall. The 32-bit memcpy entry uses
  `rep_prefix_4_byte` through 256 then libcall; 32-bit memset uses that REP
  algorithm at all sizes. Treat these as donor choices, not measured optima.
- `knc_cost`: multiply startup 11, integer divide/modulo 25, FP add/multiply 3,
  FP divide 39 and square root 70 in instruction-cost units. SSE stores and
  vector/MMX-to-integer moves are penalized at 4096; scalar loads/stores have
  cheaper costs. The table's cache sizes (8/8), zero prefetch fields and mostly
  unit vector costs need measurement rather than blind adoption.
- Disable CMOV, inter-unit register moves and CX16; use memory for transfers.
  Masked stores use mask 1 for one element and mask 3 for 128-bit values.
  The late scratch search can fall back to pushing/popping AX: rewrite this
  with explicit allocator-visible scratch/clobber/stack costs.
- Misalignment handling and TFmode push splitting are correctness mechanisms,
  not proof that wider loads/stores or floating-point reassociation are safe.

## Patch 0002: mechanism survives, memory fast path does not

Inspected local patch:
`C:/Users/xuzhi/Documents/PhiWeather/native/patches/gcc-knc/0002-preserve-secondary-move-address-reloads.patch`.
It moves `check_and_process_move` ahead of address processing in
`curr_insn_transform`. The documented donor failure is that a secondary move
deletes the original instruction after `process_address` accumulates BEFORE/AFTER
reloads; an early return loses those reloads and the replacement store uses an
uninitialized address pseudo. New instructions are queued for their own processing.

GCC 16.2 source reviewed read-only at `../_shared/gcc`, release tag
`releases/gcc-16.2.0`, commit `78d4ac7` (owner-provided identity). All line numbers
in the rest of this report refer to that tree, not the donor.

In `gcc/lra-constraints.cc`:

- Lines 4496-4505 initialize local `before`/`after` and call `process_address`.
- Lines 4512-4514 call `check_and_process_move` and return immediately on true.
- Lines 1465-1483 still call `targetm.secondary_reload` in both directions.
- Lines 1502-1518 emit the secondary instruction sequence and insert its own
  local `before` with `lra_process_new_insns`. This is a different local from
  the address reload list in `curr_insn_transform`.
- Lines 1521-1530 delete `curr_insn` and return true if no intermediate register
  was needed (`new_reg == NULL_RTX`, i.e. an instruction-code secondary reload).
- The ordinary final insertion of the outer address sequences is at line 5173;
  the early return bypasses it. Thus deletion and loss of those outer sequences
  remain structurally possible if both transformations occur on the same insn.
- **Critical difference:** lines 1442-1443 reject the fast path unless both source
  and destination are registers (after stripping SUBREGs). The donor inventory's
  memory-output secondary-reload extension is not present. A simple register move
  has no memory operand to reload; the donor memory-store failure cannot be
  inferred from the surviving ordering alone. Extending this guard for KNC would
  require preserving the pending address reloads or processing the replacement
  before address transformation, justified by a failing test.

Recommendation: **rewrite** any required memory-output support and **do not port
0002 blindly**. The secondary-reload hook, code-generation path, deletion and
caller early return still exist; this review does not demonstrate a live GCC 16
bug. No shared allocator modification is made by this research ticket.

### Earlier reproducer attempts (before corrected flags and module paths)

Copied only the ticket-specified
`PhiWeather/.tools/knc-bootstrap/hydro-knc/src/Routing/module_channel_routing.F90`
to ignored `tests/out/module_channel_routing.F90`. PhiWeather was read-only.
Commands below ran through `tools/run.py` using the bootstrap Cygwin
`python3.12.exe`; bootstrap `cross/bin` and `cygwin/bin` were prepended to PATH.
No card or assembler was invoked (`-S` is compile only).

```text
python3.12.exe tools/run.py --name S0-05-donor-routing --inputs tests/out/module_channel_routing.F90 -- k1om-mpss-linux-gfortran -O1 -S -cpp -ffree-line-length-none -J tests/out tests/out/module_channel_routing.F90 -o tests/out/routing.s
python3.12.exe tools/run.py --name S0-05-reference-routing --inputs tests/out/module_channel_routing.F90 -- k1om-mpss-linux-gfortran -BC:/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/reference/gcc-lra-diagnostic/ -O1 -S -cpp -ffree-line-length-none -J tests/out tests/out/module_channel_routing.F90 -o tests/out/routing.s
python3.12.exe tools/run.py --name S0-05-donor-routing-modules --inputs tests/out/module_channel_routing.F90 -- k1om-mpss-linux-gfortran -O1 -S -cpp -DMPP_LAND -ffree-line-length-none -I /cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/hydro-knc/src/mod -J tests/out tests/out/module_channel_routing.F90 -o tests/out/routing.s
```

Results, all exit 1:

| Attempt | Actual result | Log under `.work/_state/logs/` |
| --- | --- | --- |
| Donor, no defines | `int64` has no implicit type, reservoir CALL syntax errors, then missing `module_rt_data.mod` at line 1544; never reached LRA. | `S0_05_donor_routing-20261101-234024.log` |
| Reference selection | Driver rejected `/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/reference/gcc-lra-diagnostic/` as nonexistent: Windows drive-letter prefix was not a usable Cygwin `-B` argument. Reference f951 did not run. | `S0_05_reference_routing-20261101-234032.log` |
| Donor, MPP_LAND and module include | Missing `module_mpp_land.mod` at line 3; never reached LRA. | `S0_05_donor_routing_modules-20261101-234044.log` |

Earlier PowerShell launches using the Cygwin symlink names `python`/`python3`
were rejected by Windows file association before the runner started; selecting
`python3.12.exe` resolved that launcher issue. There is no compiler result from
those launches. After two source-compilation failures, stop and request the
original preprocessing definitions and matching module include directories (or
a self-contained preprocessed input). A corrected reference selection must use
Cygwin path syntax. Neither executable's patch status has been established by
behavior. No substitute regression test was committed; the copied source was
removed after recording these results. The reproducer criterion stays unticked.

### Corrected compilation and bounded reduction

The lead supplied the original command location:
`PhiWeather/artifacts/native/hydro-0bfbfddab62748249fdc0f108bdbb158.json:1296-1329`.
On the next attempt, both compilers successfully compiled the full source with
the missing definitions, `-mknc`, and module paths. These commands ran from this
worktree through `tools/run.py`, with the bootstrap Cygwin `python3.12.exe`.
In the shell commands below, `base` is the read-only bootstrap directory:

```sh
base=/cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap
export PATH="$base/cross/bin:/usr/bin:/bin"
# Donor: extra is empty. Reference: extra=(-B"$base/reference/gcc-lra-diagnostic/").
"$base/scientific-mpich/bin/mpif90" "${extra[@]}" \
  -cpp -DMPP_LAND -DWRF_HYDRO -DPRECIP_DOUBLE -w \
  -ffree-form -ffree-line-length-none -fconvert=big-endian -frecord-marker=4 \
  -std=legacy -O1 -mknc -fno-tree-vectorize \
  -I"$base/hydro-knc/src/Routing" -I"$base/hydro-knc/src/Data_Rec" \
  -I"$base/hydro-knc/src/MPP" -I"$base/hydro-knc/src/mod" \
  -I"$base/scientific-netcdf4/include" -Jtests/out -S -fdump-rtl-reload \
  -o "tests/out/$name.s" tests/out/module_channel_routing.F90
```

Runner invocations used names `S0-05-donor-routing-complete` and
`S0-05-reference-routing-complete`, inputs
`tests/out/module_channel_routing.F90 tests/out/compile-routing.sh`, and command
`bash tests/out/compile-routing.sh donor` or `reference`. The script expanded
the command above with the selected name and extra argument. Both exited 0
without diagnostics. The original assembly differed: for example, the reference
loaded `1320(%rsp)` into `%r14` where the donor did not, and later stack offsets
and register choices differed. These differences alone do **not** demonstrate
wrong code or identify either executable as failing patch 0002.

Preprocessing the full source with the same command plus `-E` succeeded. From
that output, extracted only `SUBMUSKINGCUNGE` into a module with the original
module name and `use iso_fortran_env, only: int64`. Removed comments, line
directives and blank lines. Its first compile failed on the diagnostic print
using imported `linkls_s(my_id+1)`; removed that print to eliminate its module
dependency. The resulting source was self-contained (about 280 lines).

Compiled that extraction once with each compiler using:

```sh
"$base/scientific-mpich/bin/mpif90" "${extra[@]}" -w \
  -ffree-form -ffree-line-length-none -fconvert=big-endian -frecord-marker=4 \
  -std=legacy -O1 -mknc -fno-tree-vectorize -Jtests/out -S -fdump-rtl-reload \
  -o "tests/out/$name.s" tests/out/reduced.f90
```

Both exited 0, and the two assembly files were identical. Both reload dumps
deleted memory move 1935, `[r2106:DI]=r2107:SF`, replacing it with masked store
3271. Crucially, **both retained** address load 3267,
`r2106:DI=[argp:DI+0x2b8]`, in the final RTL before store 3271. Thus a
`Deleting move` message on a memory store is insufficient evidence of the bug.
This extraction does not preserve the original difference and is not a valid
regression reproducer. It was not committed to `tests/regress/` as a substitute.

Logs under `.work/_state/logs/`:

| Run | Result | Log |
| --- | --- | --- |
| Corrected donor, initial script launch | Exit 1: CRLF shell script passed a trailing carriage return in the input filename; compiler did not read the source. Fixed script line endings. | `S0_05_donor_routing_complete-20261101-234659.log` |
| Corrected donor full source | Exit 0, no diagnostics. | `S0_05_donor_routing_complete-20261101-234707.log` |
| Corrected reference full source | Exit 0, no diagnostics. | `S0_05_reference_routing_complete-20261101-234717.log` |
| Full source preprocessing | Exit 0, no diagnostics. | `S0_05_preprocess_routing-20261101-234804.log` |
| First extracted routine | Exit 1: `my_id` has no implicit type in imported diagnostic expression. | `S0_05_reduced_routing-20261101-234904.log` |
| Extraction with imported diagnostic removed, both compilers | Both exit 0; identical assembly and preserved address load in both final reload dumps. Runner success records compilation only, not reproduction of the bug. | `S0_05_reduced_routing-20261101-234915.log` |

Temporary source copies, scripts, module files, assembly and RTL dumps were
removed after inspection. No compiler build, assembler, GCC 16 compiler execution
or card test ran. At that point the lead's session bound applied; the owner later lifted it. The
reduced reproducer remains unticked; neither executable's patch status is proven
by those runs.

## Separate GCC 16.2 runtime audit (F6)

This is a source dependency audit of the new compiler's own runtimes, separate
from the donor diff. Listed dependencies are conditional on configuration,
macros and selected code paths; they are not claims that every library always
executes every instruction. A future KNC configuration must select safe paths
without defining SSE/AVX feature macros. No runtime was built or run here.

### SSE (and adjacent AVX assumptions)

| Source evidence | Dependency and disposition |
| --- | --- |
| `libgcc/config/i386/t-softfp:15-32` | Explicit `-msse2` flags on half/bfloat conversion and bitint helpers. **rewrite** the KNC makefile selection; soft-float naming does not imply an SSE-free build. |
| `libgcc/config/i386/sfp-exceptions.c:44-50` | SSE-math branch forces `x` operands; alternate branch forces x87 `t`/`f`. **rewrite** exception raising for KNC, rather than enabling SSE to satisfy constraints. |
| `libgcc/config/i386/t-msabi:2-13`, `i386-asm.h:100-104,119-121`; selected for Linux x86 by `libgcc/config.host:1600` | MS-to-SysV save/restore helpers contain XMM/YMM transfers, including MOVAPS/VMOVAPS. **drop** this unsupported optional calling-convention machinery from initial KNC configuration. |
| `libitm/Makefile.am:71-78`, `libitm/libitm.h:234-240`, `libitm/config/x86/x86_sse.cc:31-40` | ARCH_X86 adds SSE/AVX barrier units and explicitly appends `-msse` (and `-mavx` when enabled). **drop** initial libitm enablement; its 128-bit transactional transfers are not proof of 16-byte lock-free atomics. |
| `libstdc++-v3/config/cpu/i486/opt/bits/opt_random.h:33,45,70-73`, `opt/ext/opt_random.h:37,47-54` | SSE3/SSE2 optimized random routines are macro-gated. **port** scalar fallbacks and keep those feature macros off for KNC; do not advertise SIMD headers as supported IMCI implementations. |
| `libatomic/config/x86/fenv.c:50-56`, `libgfortran/config/fpu-387.h:94-104` | Exception raising chooses SSE-register arithmetic or x87 constraints. **rewrite** KNC exception paths in these locations; do not select x86 SSE arithmetic merely because KNC has MXCSR. |
| `libatomic/config/x86/host-config.h:117-136` | AVX `vmovdqa` and `mfence` in the dispatched 16-byte load/store alternative. **drop** that alternative for KNC; see atomics below. |

### `pause`

| Source evidence | Dependency and disposition |
| --- | --- |
| `libgomp/config/linux/x86/futex.h:120-123`; routing at `libgomp/configure.tgt:88-89` | `cpu_relax` unconditionally uses `__builtin_ia32_pause`. **rewrite** KNC relaxation/routing; a Linux/x86 alias imports the hint. |
| `libstdc++-v3/include/bits/atomic_wait.h:141-148` | Architecture macro check alone selects `pause`; alternate branch yields. **rewrite** guard for KNC or select its supported relaxation behavior. |
| `libstdc++-v3/src/c++11/random.cc:117-133` | RDSEED retry loop uses `pause` in a separately targeted function. **drop** unsupported hardware random alternatives for KNC; retain software/OS fallback. |
| `libitm/config/x86/target.h:61-65` | Unconditional pause in x86 cpu_relax. **drop** initial libitm configuration; any future port must rewrite it. |

The inspected libatomic POSIX lock implementation uses pthread mutexes, not an
inline x86 pause loop (`libatomic/config/posix/lock.c:68-76,94-99`). That fallback
still depends on the target pthread implementation, outside this GCC source tree.

### 16-byte atomics

`libatomic/configure.tgt:86-117` maps x86-64 to the x86 implementation and requests
IFUNC for 16-byte loads. `config/x86/host-config.h:58-60` distinguishes AVX+CX16
and CX16-only alternatives; lines 72-87 advertise their atomic capabilities.
Lines 102-114 use `__sync_val_compare_and_swap_16`; lines 117-136 implement the
AVX aligned load/store alternative. **rewrite** KNC selection so neither CX16
nor AVX is assumed. Feature dispatch is conditional, not a reason to claim the
base implementation intrinsically requires CX16.

The generic CAS fallback remains at `libatomic/cas_n.c:98-121`, using
`protect_start`/`protect_end`; POSIX locks live in `config/posix/lock.c:48-76`.
**port** the lock-backed requirement, with scalar transfers visible to the
compiler. KNC 16-byte atomic operations may be library calls and need not be
lock-free. `libstdc++-v3/include/std/atomic:280-294` delegates runtime and compile
time lock-free answers to `__atomic_is_lock_free` and
`__atomic_always_lock_free`; **port** those queries without falsely enabling
CX16 or promising lock freedom. libitm's M128 barriers above are transactional
memory ABI functions, not a substitute for these atomic guarantees.

### `__float128` / TFmode

| Source evidence | Dependency and disposition |
| --- | --- |
| `libquadmath/quadmath.h:30-47`, `libquadmath/math/acosq.c:150-153` | Public binary128/complex ABI and arithmetic implemented using `__float128`. **rewrite** KNC enablement only after TFmode argument/result ABI and software helpers are correct; no silent replacement with double/long double. |
| `libgcc/config/i386/32/tf-signs.c:26-53`, `libgcc/config/i386/t-softfp:9-11` | Explicit float128 sign helpers and TF conversion families. **rewrite** target helper selection/ABI in libgcc configuration; do not infer correctness from the donor's scalar TF moves. |
| `libgfortran/mk-kinds-h.sh:71-75`, `kinds-override.h:28-30`, `libgfortran.h:61-62`, `configure.ac:679-696`, `acinclude.m4:264-314` | Fortran kind 16 may be `_Float128`; configuration probes usable binary128 and selects quadmath or IEC libc support. **port** honest probes and only expose kinds supported by the KNC compiler/runtime pair. |
| `libstdc++-v3/include/bits/cpp_type_traits.h:316-323`, `include/bits/std_abs.h:149-157` | Conditional float128 type traits/operations. **port** feature gating after ABI/helper support; presence in headers alone does not establish KNC binary128 support. |

### MXCSR and floating environment

| Source evidence | Dependency and disposition |
| --- | --- |
| `libgcc/config/i386/crtfastmath.c:28-33,82-97` | Assumes every x86-64 target has SSE/DAZ; constructor reads/writes MXCSR and sets DAZ/FTZ. **rewrite** KNC selection/control access; do not link this to change default precision or denormal handling implicitly. |
| `libgcc/config/i386/64/sfp-machine.h:26-38`, `64/dfp-machine.h:6,16-19` | Soft-float rounding reads MXCSR; decimal code also restores it. **rewrite** KNC control-register access and keep rounding/exception semantics. Turning off SSE macros is insufficient to remove these dependencies. |
| `libgfortran/config/fpu-387.h:30-42,174-194` and later IEEE environment routines | `has_sse` tests SSE availability and uses it to gate MXCSR access; x87 state is handled separately. **rewrite** KNC FPU selection (`configure.host:46-51`) so MXCSR support is independent of SSE arithmetic and valid KNC control state is preserved. |
| `libquadmath/quadmath-imp.h:274-299,309-330`, `quadmath-rounding-mode.h:27-34` | Uses target libc fenv/rounding services, with degraded fallbacks if unavailable. No direct MXCSR assembly was found in libquadmath sources. **port** the fenv dependency and verify target libc semantics in the eventual port; the GCC source audit cannot establish libc's instruction safety. |

MXCSR support is a control-state requirement, not authorization to set
`TARGET_AVX512F`, SSE/AVX flags, fast-math, or reduced precision. libgomp and
libitm dependencies above are independently relevant even without floating-point
work. These findings identify port work; they claim no native runtime passes.


## Targeted function-level follow-up (2026-11-02)

The owner required the full-source difference to be traced before further
reduction, and authorized submission once function-level evidence shows that
load difference is benign. This pass reaches that alternative. It does not
establish whole-program correctness or a passing/failing patch 0002 pair.

Copied the same ticket-specified original into
`tests/out/module_channel_routing.F90`, and ran the exact complete-flags command
in **Corrected compilation and bounded reduction**, including
`-S -fdump-rtl-reload`, with `name=donor` / `reference`. After each compile the
script moved `tests/out/module_channel_routing.F90.*reload` to
`tests/out/$name.reload`, preserving both dumps for comparison. Module output
and assembly stayed in this worktree; PhiWeather was read-only.

Exact runner commands (bootstrap `cross/bin` and `cygwin/bin` on PATH, bootstrap
Cygwin `python3.12.exe`):

```text
python3.12.exe tools/run.py --name S0-05-donor-trace --inputs tests/out/module_channel_routing.F90 tests/out/compile-routing.sh -- bash tests/out/compile-routing.sh donor
python3.12.exe tools/run.py --name S0-05-reference-trace --inputs tests/out/module_channel_routing.F90 tests/out/compile-routing.sh -- bash tests/out/compile-routing.sh reference
```

Both exited 0 with no diagnostics. Logs under `.work/_state/logs/`:
`S0_05_donor_trace-20261102-001047.log` and
`S0_05_reference_trace-20261102-001057.log`. These successes mean compilation
completed, not that either generated program ran correctly.

### Function comparison

Split each assembly at `.type <symbol>, @function` through its matching `.size`.
Of 18 functions, 15 were byte-for-byte identical. `checkreach_` differed only in
local numeric labels (identical after renaming labels in order of occurrence).
The two functions with other differences were:

| Symbol | Observation |
| --- | --- |
| `__module_channel_routing_MOD_drive_channel_rsl` | Holds the reported missing prologue load. Register allocation, reload placement and spill-slot offsets differ; the specific descriptor setup is preserved, as traced below. |
| `__module_channel_routing_MOD_drive_channel` | Different register allocation, stack frame (1256 vs 1240 bytes), spill offsets and instruction sequences. This separate difference is not evidence of a dropped setup, and has not been proved globally benign. It is not the function holding the reported prologue load. |

### The reported load is preserved at its uses

The reference's `reference.s:3894`, `movq 1320(%rsp), %r14`, belongs to
`drive_channel_rsl`. Final reload RTL identifies it as insn **38**, loading the
`typel` descriptor (argument 10), not a missing address setup for a masked
floating store. Its `REG_EQUIV` is `[argp+24]`. Both functions have the same
1240-byte local frame and CFA offset 1296, so `[rsp+1320]` names the same
incoming argument in each.

The reference keeps that descriptor in `%r14` through its two descriptor reads.
The donor rematerializes it in `%rax` immediately before each read, with no
intervening branch or clobber. The matching original instruction IDs and source
annotations identify the same operations:

| Operation | Donor final reload RTL | Reference final reload RTL |
| --- | --- | --- |
| Descriptor stride at source line 1615 | **6253**: `ax = [sp+1320]` (`typel`); immediately **288**: `ax = [ax+24]` (`typel.dim[0].stride`) | **38**: `r14 = [sp+1320]` in entry block; **288**: `ax = [r14+24]` |
| Save stride | **6046**: `[sp+280] = ax` | **6046**: `[sp+280] = ax` |
| Descriptor data pointer at source line 1615 | **6252**: `ax = [sp+1320]` (`typel`); immediately **294**: `ax = [ax]` (`typel.data`) | **294**: `ax = [r14]`, still using entry load **38** |
| Save data pointer | **5325**: `[sp+32] = ax` | **5325**: `[sp+16] = ax` |
| First later element use, source line 1952 | **5821** loads `typel.0` from `[sp+32]`; **2447** forms `r9 = bx + ax*4`; **2448** compares `[r9]` with 2 | Same original IDs, using `[sp+16]` for the pointer spill |
| Second later element use, source line 2067 | **5238** loads `typel.0` from `[sp+32]` into `r8`; **3033** compares `[r8+r11*4]` with 2 | Same original IDs, using `[sp+16]` for the pointer spill |

For locating these in regenerated full dumps, this run's donor positions were
`donor.reload:220918` (6253), `220922` (288), `220948` (6252), `220952` (294),
`220955` (5325), `230337` (5821), and `232612` (5238). Reference positions were
`reference.reload:189585` (38), `190149` (288), `190175` (294), `190178` (5325),
`199315` (5821), and `201594` (5238). Instruction IDs and the expressions above
are the durable comparison evidence; dump line numbers depend on the command.

The matching donor assembly reads:

```asm
movq 1320(%rsp), %rax
movq 24(%rax), %rax
movq %rax, 280(%rsp)
# stride-zero test and possible replacement by 1
movq 1320(%rsp), %rax
movq (%rax), %rax
movq %rax, 32(%rsp)
```

Thus there is no store with an uninitialized address attributable to the
reported missing load: its two uses are descriptor **loads**, and both have
explicit, preserved address setup in the donor. The resulting data pointer is
saved and reloaded at the later element comparisons in both variants. Absence
of the reference's early `%r14` load is benign for this chain. It cannot justify
extracting `SUBMUSKINGCUNGE`, or treating any mere assembly difference or
`Deleting move` diagnostic as a patch 0002 failure.

Step 3 therefore did not find the alleged dropped setup; step 4 (extracting a
function with a demonstrated failure) has no established symptom to preserve.
No substitute regression was added. The reduced-reproducer checkbox remains
unticked, explicitly using the owner's benign-load submission condition. The
GCC 16 register-only guard finding above remains unchanged. Temporary full
source, modules, assembly, dumps and comparison files were removed after this
inspection. No additional compile, compiler build, assembler, or card run was
performed.
