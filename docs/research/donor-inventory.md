# Donor inventory (S0-05, incomplete)

Status: donor history and full-tree changed-path inventory inspected. Acceptance is
**not met**: GCC 16.2 runtime sources and `lra-constraints.cc` were not available
locally or retrievable, and the original patch 0002 reproducer was not located.
The destination paths below are proposed landing locations, not a verified GCC
16.2 source audit. No compilation or card execution was performed.

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

## Patch 0002: identified failure, GCC 16 answer pending

Inspected local patch:
`C:/Users/xuzhi/Documents/PhiWeather/native/patches/gcc-knc/0002-preserve-secondary-move-address-reloads.patch`.
It moves `check_and_process_move` ahead of address processing in
`curr_insn_transform`. The documented failure is that a secondary move deletes
the original instruction after `process_address` accumulates BEFORE/AFTER
reloads; an early return loses those reloads and the replacement store uses an
uninitialized address pseudo. The replacement instructions are queued for their
own address processing.

Required GCC 16 inspection: find `check_and_process_move`,
`targetm.secondary_reload`, `process_address`, the BEFORE/AFTER sequence handling
and deletion/early-return paths in `gcc/lra-constraints.cc`. Neither continued
existence nor removal of this exact mechanism has been established here.
No substitute reproducer was invented, and no test was added or claimed to
fail. The original reduced source must be supplied or located and preserved in
`tests/regress/` before this acceptance item can be closed.

## Separate GCC 16.2 runtime audit (F6): blocked

These are explicit outstanding source-review questions, **not verified GCC
16.2 findings**. Donor routing cannot answer them.

| Dependency | Required GCC 16.2 source inspection |
| --- | --- |
| SSE | `libgcc/config/i386` CRT/helper assembly, `libitm` x86 paths, libstdc++ CPU-specific primitives, and libatomic x86 alternatives: establish all target-selected SSE uses and safe replacements. |
| `pause` | Inspect libgomp x86 futex/spin paths, libstdc++ atomic wait/spin helpers, libitm locks and libatomic spin implementations; use a KNC-safe hint or scalar fallback. |
| 16-byte atomics | Inspect libatomic x86 dispatch/assembly and generic lock fallback, libstdc++ lock-free queries, and libitm wide operations; do not assume x86-64 implies CX16 or advertise unsupported lock freedom. |
| `__float128` | Inspect libquadmath configuration/ABI, libgcc TFmode and complex helpers, libgfortran kind selection and quadmath calls, and libstdc++ float128 integration; establish software arithmetic and calling convention requirements. |
| MXCSR | Inspect libgcc fast-math CRT and soft-float exception support, libgfortran FPU/IEEE handling and libquadmath floating-environment code; distinguish control-register access from SSE arithmetic and preserve default precision/modes. |

Local shell retrieval of the release-tagged `gcc/lra-constraints.cc` failed with
`WinError 10051` (unreachable network). Web retrieval of release-tagged GitHub
raw/blob, Google Git and gcc.gnu.org source endpoints also failed (cache miss or
inaccessible URL). The release announcement alone cannot establish source
behavior. Supply a shared GCC 16.2.0 source tree/archive and the patch 0002
reproducer to complete the two blocked acceptance items.
