# Shared libgcc for KNC (S7-01 / E6-01 input)

Research date: 2026-11-06. **Recommendation (inferred):** implement a
donor-compatible `libgcc_s.so.1`, initially installed in a private toolchain
directory. Merely removing the shared-build prohibition would not produce a
drop-in replacement. Restore the donor's symbol versions, six TF compatibility
aliases, SF helper exports, and CPU-model ABI before considering replacement.
There is no identified unavoidable requirement for glibc newer than 2.21 or a
kernel newer than 2.6.38 in the selected KNC runtime sources. That is a source
assessment, not a linked-library or native result.

## Evidence and scope

**Proven** means directly observed in a source file or ELF symbol/section table;
**inferred** means a consequence of those observations that has not been built
or run; **unknown** identifies an implementation or runtime acceptance item.
Unqualified paths below are relative to `.work/_shared/gcc`, branch `knc`,
observed HEAD `a81ac500361e`. `sysroot/` means
`.work/_shared/toolchain/sysroot`. Existing static-libgcc support and the donor's
GCC 5.1.1 origin are ticket premises, not re-established here.

Only host-side source and ELF inspection was performed. No compiler build,
configure probe, target execution, or card job was run. The sysroot headers say
glibc 2.21 (`sysroot/usr/include/features.h:356-357`); kernel 2.6.38 is the ticket's
target constraint, not a newly measured running-kernel version.

Read-only symbol extraction used the supplied
`toolchain/cross/bin/k1om-mpss-linux-readelf.exe` with
`-W --dyn-syms --version-info -d -l -S`. It visited ELF files recursively under
`lib64`, `usr/lib64`, `bin`, `sbin`, `usr/bin`, and `usr/sbin` in that sysroot:
252 ELF paths, zero readelf errors, six paths with undefined `@GCC_*` symbols.
Aliases are counted as paths; they are not claimed to be distinct libraries.
The extraction command was:

```text
python tools/run.py --name S7-01-symbols --inputs ../_shared/S7-01/inspect.py -- python ../_shared/S7-01/inspect.py
```

Its log is `.work/_state/logs/S7_01_symbols-20261106-135631.log`;
the reduced symbol output is `.work/_shared/S7-01/symbols.txt`. The tables below
preserve the relevant results in this note. A separate `nm -g --defined-only`
inspection of the existing
`.work/_shared/gcc-build/k1om-mpss-linux/libgcc/libgcc.a` is recorded in
`.work/_shared/S7-01/static-symbols.txt`. It describes that archive, not the
as-yet-unbuilt shared library.

## 1. Donor exports and sysroot consumers

**Proven:** `sysroot/lib64/libgcc_s.so.1` has SONAME `libgcc_s.so.1`, a single
DT_NEEDED dependency `libc.so.6`, 12 GCC version-definition nodes plus the base
SONAME node, and **153 exported symbol-version pairs / 147 distinct names**.
The complete export listing appears below. Six pairs are nondefault compatibility
aliases; all other listed pairs are default `@@` definitions. `__cpu_model` is
a 16-byte exported object; the other listed symbols are functions.

The GCC version-parent chain, in order, is:

```text
GCC_3.0 -> GCC_3.3 -> GCC_3.3.1 -> GCC_3.3.4 -> GCC_3.4
-> GCC_3.4.2 -> GCC_3.4.4 -> GCC_4.0.0 -> GCC_4.2.0
-> GCC_4.3.0 -> GCC_4.7.0 -> GCC_4.8.0
```

**Proven:** the donor's only GLIBC version requirement is `GLIBC_2.14`, for
`abort`, `dl_iterate_phdr`, `free`, `pthread_mutex_lock`,
`pthread_mutex_unlock`, `__cxa_finalize`, `malloc`, `calloc`, and `realloc`.
The mutex functions and `__cxa_finalize` are weak imports. Its unversioned weak
undefined names are `__pthread_key_create`, `pthread_getspecific`,
`pthread_key_create`, `pthread_once`, `pthread_setspecific`, `__gmon_start__`,
`_ITM_deregisterTMCloneTable`, `_ITM_registerTMCloneTable`, and
`_Jv_RegisterClasses`. Source: donor `.dynsym` and `.gnu.version_r`.

**Proven:** the following are the versioned GCC imports found in the sysroot
scan. Every pair exists in the donor export set. No path under the inspected
program directories, or `lib64`, had an undefined `@GCC_*` entry.

| Consumer path under sysroot | Undefined GCC symbols |
| --- | --- |
| `usr/lib64/libcoi_device.so.0` | `_Unwind_Resume@GCC_3.0` |
| `usr/lib64/librpmio-5.4.so` | `_Unwind_Resume@GCC_3.0`, `__gcc_personality_v0@GCC_3.3.1` |
| `usr/lib64/libstdc++.so.6`, `usr/lib64/libstdc++.so.6.0.21` | `_Unwind_DeleteException`, `_Unwind_GetDataRelBase`, `_Unwind_GetLanguageSpecificData`, `_Unwind_GetRegionStart`, `_Unwind_GetTextRelBase`, `_Unwind_RaiseException`, `_Unwind_Resume`, `_Unwind_SetGR`, `_Unwind_SetIP`, all at `GCC_3.0`; `_Unwind_Resume_or_Rethrow@GCC_3.3`; `_Unwind_GetIPInfo@GCC_4.2.0` |
| `usr/lib64/libzypp.so.810`, `usr/lib64/libzypp.so.810.1.0` | `_Unwind_Resume@GCC_3.0`, `__powixf2@GCC_4.0.0` |

That is 13 distinct imported symbol-version pairs, not the full compatibility
contract. **Proven:** printable strings in `sysroot/lib64/libpthread-2.21.so`
include `libgcc_s.so.1`, `_Unwind_Resume`, `__gcc_personality_v0`,
`_Unwind_ForcedUnwind`, `_Unwind_GetCFA`, and the diagnostic that libgcc_s must
be installed for pthread cancellation. `sysroot/lib64/libc-2.21.so` contains
the same SONAME plus `_Unwind_Resume`, `__gcc_personality_v0`,
`_Unwind_Backtrace`, `_Unwind_GetIP`, and `_Unwind_GetCFA`.
**Inferred:** these identify additional runtime lookup/cancellation/backtrace
dependencies which an undefined-versioned-symbol scan does not enumerate.
**Unknown:** the complete unversioned/dlsym lookup graph and the inventory of
programs installed on the actual card but absent from this sysroot. Preserve
the complete donor export ABI, rather than only the 13 observed imports.

### Complete donor export table

**Proven:** extracted from the donor `.dynsym`; `[compat]` means a single-`@`
nondefault alias. Counts include these aliases and exclude ABS version labels.

**GCC_3.0 (75)**

```text
_Unwind_DeleteException _Unwind_Find_FDE _Unwind_ForcedUnwind _Unwind_GetDataRelBase
_Unwind_GetGR _Unwind_GetIP _Unwind_GetLanguageSpecificData _Unwind_GetRegionStart
_Unwind_GetTextRelBase _Unwind_RaiseException _Unwind_Resume _Unwind_SetGR _Unwind_SetIP
__absvdi2 __absvsi2 __addsf3 __addvdi3 __addvsi3 __ashlti3 __ashrti3 __clear_cache
__cmpti2 __deregister_frame __deregister_frame_info __deregister_frame_info_bases
__divsf3 __divti3 __eqsf2 __ffsdi2 __ffsti2 __fixdfti __fixsfsi __fixsfti __fixunsdfdi
__fixunsdfti __fixunssfdi __fixunssfti __fixunsxfdi __fixunsxfti __fixxfti __floatsisf
__floattidf __floattisf __floattixf __gesf2 __gtsf2 __gttf2 [compat] __lesf2 __lshrti3
__ltsf2 __lttf2 [compat] __modti3 __mulsf3 __multi3 __mulvdi3 __mulvsi3 __negsf2
__negti2 __negvdi2 __negvsi2 __nesf2 __netf2 [compat] __register_frame
__register_frame_info __register_frame_info_bases __register_frame_info_table
__register_frame_info_table_bases __register_frame_table __subsf3 __subvdi3 __subvsi3
__ucmpti2 __udivmodti4 __udivti3 __umodti3
```

**GCC_3.3 (4)**

```text
_Unwind_Backtrace _Unwind_FindEnclosingFunction _Unwind_GetCFA _Unwind_Resume_or_Rethrow
```

**GCC_3.3.1 (1)**

```text
__gcc_personality_v0
```

**GCC_3.3.4 (1)**

```text
__unordsf2
```

**GCC_3.4 (8)**

```text
__clzdi2 __clzti2 __ctzdi2 __ctzti2 __paritydi2 __parityti2 __popcountdi2 __popcountti2
```

**GCC_3.4.2 (1)**

```text
__enable_execute_stack
```

**GCC_3.4.4 (5)**

```text
__absvti2 __addvti3 __mulvti3 __negvti2 __subvti3
```

**GCC_4.0.0 (12)**

```text
__divdc3 __divsc3 __divtc3 [compat] __divxc3 __muldc3 __mulsc3 __multc3 [compat]
__mulxc3 __powidf2 __powisf2 __powitf2 [compat] __powixf2
```

**GCC_4.2.0 (5)**

```text
_Unwind_GetIPInfo __floatunsisf __floatuntidf __floatuntisf __floatuntixf
```

**GCC_4.3.0 (37)**

```text
__addtf3 __bswapdi2 __bswapsi2 __divtc3 __divtf3 __emutls_get_address
__emutls_register_common __eqtf2 __extenddftf2 __extendsftf2 __extendxftf2 __fixtfdi
__fixtfsi __fixtfti __fixunstfdi __fixunstfsi __fixunstfti __floatditf __floatsitf
__floattitf __floatunditf __floatunsitf __floatuntitf __getf2 __gttf2 __letf2 __lttf2
__multc3 __multf3 __negtf2 __netf2 __powitf2 __subtf3 __trunctfdf2 __trunctfsf2
__trunctfxf2 __unordtf2
```

**GCC_4.7.0 (2)**

```text
__clrsbdi2 __clrsbti2
```

**GCC_4.8.0 (2)**

```text
__cpu_indicator_init __cpu_model
```


## 2. GCC 16 additions and platform requirements

### Maps describe eligible exports, not an unconditional export list

**Proven:** `libgcc/libgcc-std.ver` is generated, not a checked-in file:
`libgcc/Makefile.in:1001-1003` substitutes prefixes into `libgcc-std.ver.in`.
`Makefile.in:985-995` preprocesses the selected map fragments and combines them
with `nm` output from shared objects. `libgcc/mkmap-symver.awk:117-139` emits
only definitions actually present and removes empty version nodes.
Consequently the highest map node does not imply that every target exports it.

The current KNC selection uses the generic Linux map addition
(`libgcc/config/t-linux:3`, `config.host:304,811`), not the i386 override
(`libgcc/config/i386/t-linux:4`). The latter matters for donor compatibility
and for the HF/BF/_BitInt additions below.

| Candidate addition over the donor | Status and KNC consequence | Source |
| --- | --- | --- |
| `GCC_7.0.0`: `__divmoddi4`, `__divmodti4` | **Proven** map entries. Existing KNC archive defines `__divmodti4`; **inferred** this is the relevant new exported combined signed TI division/remainder helper for this 64-bit configuration. Do not claim both names from the map alone. | `libgcc/libgcc-std.ver.in:1942-1946`; `libgcc/Makefile.in:480-482`; existing archive symbol table |
| `GCC_14.0.0`: `__hardcfr_check`, `__strub_enter`, `__strub_update`, `__strub_leave` | **Proven** generic entries and definitions in the existing KNC archive. **Inferred** exports after shared enablement; strub is configuration-dependent in general. | `libgcc/libgcc-std.ver.in:1948-1953`; `libgcc/Makefile.in:439-443` |
| `GCC_14.0.0`: `__gcc_nested_func_ptr_created`, `__gcc_nested_func_ptr_deleted` | **Proven** generic entries, but the KNC case does not select the heap-trampoline implementation. **Inferred** no such shared exports for the current selection. | `libgcc/libgcc-std.ver.in:1954-1955`; `libgcc/config.host:807-821`; `libgcc/config/i386/t-heap-trampoline:19-20` |
| `GCC_12.0.0`: HF arithmetic/conversions, listed below | **Proven** i386-map additions; current KNC excludes the SSE2 half helpers. **Inferred** absent from a KNC DSO unless separately ported; not required for donor compatibility. | `libgcc/config/i386/libgcc-glibc.ver:198-216`; `libgcc/config/i386/t-knc:1-5`; `libgcc/config/i386/t-softfp:15-36` |
| `GCC_13.0.0`: BF conversions, listed below | **Proven** i386-map additions; current KNC excludes their SSE2 implementation. **Inferred** absent, with no donor compatibility loss. | `libgcc/config/i386/libgcc-glibc.ver:218-228`; `libgcc/config/i386/t-softfp:19,25-32` |
| `GCC_14.0.0`: `_BitInt` arithmetic/conversions, listed below | **Proven** i386-map additions. Eight names exist in the current KNC archive: `__mulbitint3`, `__divmodbitint4`, `__fixsfbitint`, `__fixdfbitint`, `__fixtfbitint`, `__floatbitintsf`, `__floatbitintdf`, `__floatbitinttf`. **Inferred:** simply enabling shared with the generic maps would leave these unexported; select a KNC-safe map policy explicitly. HF/BF/XF entries need separate selection/ABI decisions. | `libgcc/config/i386/libgcc-glibc.ver:230-244`; `libgcc/libgcc2.c:1333-1334`; `libgcc/config/t-softfp:67-87`; `libgcc/config/t-softfp-tf:5`; existing archive symbol table |

Exact architecture-map candidate lists (**proven**, source ranges in the table):

```text
GCC_12.0.0:
  __divhc3 __mulhc3 __eqhf2 __nehf2 __extendhfdf2 __extendhfsf2
  __extendhftf2 __extendhfxf2 __fixhfti __fixunshfti __floattihf
  __floatuntihf __truncdfhf2 __truncsfhf2 __trunctfhf2 __truncxfhf2
GCC_13.0.0:
  __extendbfsf2 __floattibf __floatuntibf __truncdfbf2 __truncsfbf2
  __trunctfbf2 __truncxfbf2 __trunchfbf2
GCC_14.0.0 (i386 additions to the generic node):
  __mulbitint3 __divmodbitint4 __fixsfbitint __fixdfbitint
  __fixxfbitint __fixtfbitint __floatbitintbf __floatbitinthf
  __floatbitintsf __floatbitintdf __floatbitintxf __floatbitinttf
```

**Proven:** the generic map also has nodes absent from the donor but older than
GCC 5: empty `GCC_3.3.2` and `GCC_4.1.0`, `GCC_4.4.0` sync helpers,
`GCC_4.5.0` unordered XF/TF comparisons, and `GCC_4.6.0` split-stack entries
(`libgcc/libgcc-std.ver.in:212-214,275-277,1824-1921`). Its `GCC_4.7.0`
also lists split-stack operations (`1923-1936`). These are not new GCC 16
requirements. KNC does not select the x86 `t-stack` fragment
(`libgcc/config.host:1608-1617`); the i386 map relocates TF comparisons to the
donor's versions. Neither inspected generic nor i386 Linux map adds a
`GCC_15.*` or `GCC_16.*` node. Other architecture maps are not KNC's contract.

### glibc, kernel, instruction set, and binary128

| Concern | Finding and evidence |
| --- | --- |
| GLIBC import ceiling | **Unknown** for the future linked DSO: no GCC 16 shared object was produced. Require every undefined versioned symbol to have a provider in this exact sysroot; `max(GLIBC version) <= 2.21` alone is insufficient. **Proven** donor baseline is `GLIBC_2.14`. **Inferred** building and linking against only the card headers/libraries should avoid host GLIBC requirements; inspect the final DSO to establish the actual ceiling. |
| `_dl_find_object` | **Proven** optional compile-time path, guarded by `DLFO_STRUCT_HAS_EH_DBASE` in `libgcc/unwind-dw2-fde-dip.c:545-561`. That macro and API are absent from this sysroot's `link.h`/`dlfcn.h`; `_dl_find_object` is absent from inspected libc/loader dynamic symbols. **Inferred** the old-header build uses `dl_iterate_phdr`, so it need not import the newer API (the ticket's glibc 2.35 example). Defining the macro as zero would still select this path: it must remain undefined. |
| Ordinary allocation, threading, TLS | **Proven** `libgcc/emutls.c:104-198` uses allocation and gthread keys/locks; `libgcc/gthr-posix.h:123-157,273-277` maps to POSIX functions with the glibc weak-thread probe. `libgcc/config/t-tls:2` enables native TLS use internally. **Inferred** these do not inherently demand a post-2.21 API; the selected card providers and final TLS relocations remain build-audit requirements. Retain exported emutls ABI even though KNC supports native TLS. |
| Kernel newer than 2.6.38 | **Inferred:** no mandatory newer syscall was identified in the selected arithmetic, hardcfr, strub, emutls, or DWARF unwinder mechanisms. Arithmetic is implemented in libgcc; hardcfr uses a trap (`libgcc/hardcfr.c:262`), strub scrubs memory (`libgcc/strub.c:96-136`), and thread services go through glibc. `libgcc/config/i386/linux-unwind.h:51-64` recognizes the existing rt_sigreturn sequence; it is not a new syscall request. **Unknown:** exhaustive runtime reachability and card execution. A GLIBC symbol ceiling does not prove a kernel ceiling. |
| Unwinder atomics | **Proven** `libgcc/unwind-dw2-fde.c:39-48` enables the registered-frame b-tree when mutexes and 4-byte CAS are available. The implementation uses pointer-sized atomics (`unwind-dw2-btree.h:63-67,81-121,166-172`). **Inferred** this does not introduce a modern kernel API, but generated instructions and unresolved atomic helpers need checking; do not turn on CX16 or silently introduce libatomic to solve it. |
| SSE/AVX helpers | **Proven** `libgcc/config/i386/t-softfp:15-43` and `64/t-softfp:4-9` explicitly request SSE2. `i386/t-msabi:2-13` adds AVX/SSE register-save assembly to the static archive. KNC skips these selections (`config.host:807-815,1608-1626`). **Inferred** copying the whole x86 runtime recipe is wrong even when the shared exports look compatible. The MS-ABI files are static-only, not additional libgcc_s ABI exports. |
| CPU detection | **Proven** donor exports `__cpu_indicator_init@@GCC_4.8.0` and 16-byte `__cpu_model@@GCC_4.8.0`; KNC currently selects neither cpuinfo fragment (`config.host:1595-1606`). `libgcc/config/i386/cpuinfo.c:38-68` preserves the model ABI and keeps extra feature state out of the shared ABI. Its common implementation executes CPUID (`gcc/common/config/i386/cpuinfo.h:1223-1237`) and conditionally performs XGETBV using literal bytes when OSXSAVE is set (`796-843`). **Unknown:** KNC-safe execution/feature semantics of importing that implementation wholesale. Supply an audited KNC detector with the original object layout and versions; do not infer that KNC IMCI is AVX512F or retain opaque instruction bytes to evade the assembler. |
| CET / shadow stack | **Proven** `config/cet.m4:11-49` only enables target CET for i386/x86_64 Linux triples and sets other hosts to no. `libgcc/config/i386/linux-unwind.h:25-28` includes the shadow-stack code only with both SHSTK and the CET return-protection bit. The code uses `_get_ssp`/`_inc_ssp` (`shadow-stack-unwind.h:25-42`). **Inferred** CET is not a baseline requirement; keep its flags off for KNC. Enabling it would require unsupported hardware/OS facilities, not an ordinary symbol-version fix. |
| `__float128`, `_Float128`, TF helpers | **Proven** TFmode is accepted in `gcc/config/i386/i386.cc:25140-25147`; `libgcc/soft-fp/quad.h:68-69` defines its binary128 arithmetic type by TF mode; `libgcc/config/t-softfp-tf:1-6` selects software arithmetic/conversions. KNC uses its own MXCSR access and x87 exception path (`knc-sfp-machine.h:1-13`, `t-knc:4-9`, `sfp-exceptions.c:44-91`). The donor already exports the TF helpers; binary128 arithmetic is not a newly imposed glibc feature. **Inferred** compiler-generated binary128 arithmetic can remain in libgcc without newer libc Float128 math functions. **Unknown** mixed-donor/new-compiler ABI and rounding/exception conformance for both language spellings until tested. Do not equate their arithmetic helpers with libc `*f128` math/format APIs or libquadmath. |
| Long double and precision | **Proven** `gcc/config/i386/linux-k1om.h:37-40` retains x87 precision with 16-byte storage; `libgcc/config/i386/t-knc:9` uses `-mlong-double-80`. **Inferred** shared enablement must preserve this; changing long double to binary128 is neither necessary nor ABI-compatible. |
| Heap trampolines | **Proven** not selected for KNC (`config.host:807-821`). The x86 implementation uses mmap/munmap, with Linux `MAP_ANON | MAP_PRIVATE`, rather than a new Linux syscall (`libgcc/config/i386/heap-trampoline.c:144-156,248`). **Unknown** KNC instruction/ABI suitability; leave this feature outside initial shared enablement. |

## 3. Replacement versus coexistence

**Proven source blockers:** the present runtime and driver deliberately prohibit
shared libgcc (`libgcc/config/i386/t-knc:11-13`,
`gcc/config/i386/linux-k1om.h:57-63`). The generic Linux map would move several
frame-registration functions to `GLIBC_2.0`
(`libgcc/config/libgcc-glibc.ver:25-55`), whereas the donor exports them at
`GCC_3.0`. This is an **export-version mismatch**, not a dependency on
glibc 2.0. The i386 map's x86_64 conditional avoids that move
(`libgcc/config/i386/libgcc-glibc.ver:25-57`); KNC's 64-bit compiler defines
`__x86_64__` (`gcc/config/i386/i386-c.cc:914-921`).

**Proven:** the existing static archive lacks these 17 donor names:

```text
__addsf3 __divsf3 __eqsf2 __fixsfsi __floatsisf __floatunsisf
__gesf2 __gtsf2 __lesf2 __ltsf2 __mulsf3 __negsf2 __nesf2
__subsf3 __unordsf2 __cpu_indicator_init __cpu_model
```

That is 15 SF helpers and two CPU ABI names. **Inferred:** flipping the shared
switch does not restore them. Source corroboration: KNC's soft-fp mode list is
TF-only (`libgcc/config/t-softfp-tf:1-4`), generic libgcc2 selections are in
`libgcc/Makefile.in:453-482`, and KNC skips cpuinfo. Implement the missing
compatibility functions without SSE or implicit precision changes.

**Proven:** the donor's six TF aliases are:

| Symbol | Compatibility version | Default version |
| --- | --- | --- |
| `__gttf2`, `__lttf2`, `__netf2` | `GCC_3.0` | `GCC_4.3.0` |
| `__divtc3`, `__multc3`, `__powitf2` | `GCC_4.0.0` | `GCC_4.3.0` |

The mechanism still exists: `libgcc/config/i386/64/t-softfp-compat:5-15`
selects wrappers; `64/getf2.c:1-14`, `64/letf2.c:1-14`,
`64/eqtf2.c:1-14`, and `64/_divtc3.c:1-16` show the shared-only `.symver`
aliases. The map gives TF defaults at `GCC_4.3.0`
(`i386/libgcc-glibc.ver:63-154`). KNC currently selects neither this map nor
the compatibility fragment (`config.host:807-815,1629-1635`).
**Inferred:** both the wrappers and version assignments are needed; adding
names to a map does not manufacture the missing alias definitions.

**Inferred compatibility decision:** GCC 16 can be engineered as a superset
under the same SONAME; neither a compiler major-version increase nor the
absence of CET/half helpers requires a new SONAME. It is **not currently
established as a replacement**. Acceptance must compare all 153 donor pairs,
including default/nondefault status and `__cpu_model` size, then establish
calling conventions, exception behavior, and existing-client operation.
Preserving only unwind symbols would accommodate the visible versioned
consumers but would not meet the full donor contract.

Keep donor and candidate installed in different directories during validation,
selecting the candidate explicitly for isolated processes. **Inferred:** this
supports rollback without requiring both unwinders in one process. A different
filename/path with the same SONAME is not a promise of independent runtime
namespaces. A different SONAME would not automatically satisfy existing
DT_NEEDED or glibc's `libgcc_s.so.1` lookups and risks multiple unwinders and
symbol interposition. **Unknown:** simultaneous in-process coexistence; it is
not the recommended implementation route. Any system-wide donor replacement
must await the lead's native acceptance, not this research result.

## 4. Unwinder and old-glibc support

**Proven:** the sysroot's `libgcc_s.so.1`, `libc-2.21.so`,
`libpthread-2.21.so`, and `ld-2.21.so` each contain `.eh_frame`,
`.eh_frame_hdr`, and `PT_GNU_EH_FRAME` (readelf section/program tables).
`libc-2.21.so` exports `dl_iterate_phdr@@GLIBC_2.14`; the donor imports it
at that same version. `sysroot/usr/include/elf.h:586` defines
`PT_GNU_EH_FRAME`; `sysroot/usr/include/link.h:140-168` supplies the program
header iterator and its add/subtract counters and TLS fields.

**Proven:** Linux's `t-eh-dw2-dip` selects `unwind-dw2-fde-dip.c`
(`libgcc/config.host:304`, `libgcc/config/t-eh-dw2-dip:1-3`). That source
enables PT_GNU_EH_FRAME for sufficiently old glibc already, provided
`HAVE_LD_EH_FRAME_HDR` is defined (`unwind-dw2-fde-dip.c:49-53`). It first
looks for explicitly registered FDEs (`541-543`), then uses the optional
new loader API or the `dl_iterate_phdr` path (`545-573`). Without the
PT_GNU_EH_FRAME configuration it includes the registration-based unwinder
(`576-579`). CRT registration choices likewise depend on linker/header
support (`libgcc/crtstuff.c:108-140,476-486`).

**Inferred:** the old iterator plus `.eh_frame_hdr` lookup is the appropriate
GCC 16 path on this sysroot. Retain linker `--eh-frame-hdr` support and the
matching CRT behavior. Do not suppress frame registration exports merely
because ordinary DSOs use program headers: callers may register frames
explicitly, and the donor exports those interfaces.

**Unknown runtime items:** exceptions across old/new DSOs; forced unwind for
pthread cancellation; backtrace; load/unload and explicit frame registration;
signal-frame unwinding and KNC register restoration. The Linux fallback shares
the x86_64 signal-context layout (`libgcc/config/i386/linux-unwind.h:39-107`;
`sysroot/usr/include/sys/ucontext.h:28-138`), but source similarity is not
native proof. Likewise the registered-frame atomics discussed above must
produce KNC-legal code. No `_dl_find_object` compatibility shim is justified
by the source: the old API fallback already exists.

## 5. What shared configure changes, and static blockers

**Proven:** libgcc configure accepts shared enablement
(`libgcc/configure.ac:55-69`). Linux already selects PIC CRT/runtime,
DWARF program-header lookup, shared ELF versioning, and the generic Linux map
(`libgcc/config.host:303-305`). KNC adds `i386/t-crtstuff`, `t-tls`,
`t-softfp-tf`, `i386/t-knc`, and `t-softfp`, plus its soft-fp and Linux unwind
headers (`807-814`). The included `t-knc` subsequently sets
`enable_shared := no`, overriding configure's yes. Thus `--enable-shared`
alone presently changes no final KNC shared-runtime availability.

Once that intentional guard is removed as part of an audited port:

* **Proven build mechanism:** shared-object rules build additional `_s` objects
  (`libgcc/shared-object.mk:13-17`); PIC comes from
  `libgcc/config/t-libgcc-pic:2`. Shared unwind objects and a separate
  `libgcc_eh.a` are selected (`libgcc/Makefile.in:869-886,976-977`), while
  `libgcc.a` remains. The version script is generated from actual shared-object
  definitions (`985-1003`).
* **Proven link/install mechanism:** `libgcc/config/t-slibgcc:21-29,43-54`
  supplies SONAME version 1, `-shared -nodefaultlibs`, and explicit `-lc`;
  `t-slibgcc-gld:4-5` adds SONAME/version-script linker options. Installation
  and symlinks are in `t-slibgcc:58-64`. This is GCC's libgcc make machinery;
  it does not require porting unrelated libtool runtime libraries.
* **Proven driver blocker:** `gcc/config/i386/linux-k1om.h:60-63` rejects
  `-shared-libgcc` and always selects `-lgcc`. A real enablement must change
  driver policy as well as the library. Preserve K1OM assembler/emulation and
  loader selection (`linux-k1om.h:42-51`), and support explicit
  `-static-libgcc` and static links after shared enablement.
* **Proven map/implementation blockers:** wrong generic frame-registration
  versions; absent TF version wrappers and default remapping; missing SF/CPU
  names; `_BitInt` definitions without the i386 export map. These are detailed
  above. Simply importing `i386/t-linux` also adds `USE_ELF_SYMVER` and CET
  flags (`libgcc/config/i386/t-linux:4-7`); audit CPU default-version behavior
  rather than assuming it reproduces the donor's `@@` entries.
* **Proven missing selection, inferred integration requirement:** KNC omits
  `t-slibgcc-libgcc`, selected for Linux x86 in `config.host:1608-1612`.
  Its purpose is a `libgcc_s.so` linker script grouping the shared object and
  `-lgcc` for static-only helpers (`libgcc/config/t-slibgcc-libgcc:19-29`).
  Decide the KNC driver/link-script combination together and verify static-only
  helpers still resolve. Do not indiscriminately import the adjacent SSE/AVX,
  split-stack, or half-precision selections.
* **Unknown until linked:** relocation types, text relocations, weak-symbol
  binding, TLS access, constructor code, linker-script syntax with the supplied
  K1OM binutils, undefined helper closure, and the exact GLIBC import set.
  Existing PIC fragment selection is evidence of intent, not proof of a clean
  shared link. Verify the whole DSO including unwind/soft-fp/CPU constructors
  for unsupported SSE, AVX, CET, CMOV/CX16 paths rather than only arithmetic
  entry points. New DSO behavior must retain visible helper and memory costs.

## Recommended E6-01 ticket split and risks

The following are **inferred implementation recommendations**, not work
performed by S7-01. Four tickets keep source compatibility, shared integration,
and lead-coordinated card acceptance reviewable.

1. **E6-01a â€” Donor ABI compatibility objects and map.** Restore the 15 SF
   helper names, the two CPU ABI names, TF default versions and all six
   aliases, and KNC-appropriate `_BitInt` export entries. Reuse existing
   compatibility mechanisms where safe; retain original long-double precision
   and KNC feature flags. Acceptance: a test-first donor symbol/version fixture
   detects missing or wrongly versioned exports; an isolated candidate symbol
   table contains all 153 donor pairs with the correct defaults and 16-byte
   CPU object, and the intended supported additions. CPU and SF implementations
   pass KNC instruction lint; no unsupported HF/BF/decimal implementation is
   pulled in merely to populate a map. Keep any shared-i386 edits separate.
2. **E6-01b â€” Shared build and driver integration.** Remove the guards only
   alongside the compatible map/objects; establish `-shared-libgcc`, default
   runtime selection, `-static-libgcc`, CRTs, and static-helper link-script
   policy. Acceptance: the prescribed committed-tree build through
   `tools/gcc_build.py --if-stale` produces an ELF K1OM DSO with SONAME
   `libgcc_s.so.1`; host audit verifies the donor superset, required
   `PT_GNU_EH_FRAME`, no unexpected unresolved helpers/text relocations, and
   every required versioned import resolves in the card sysroot with no
   post-2.21 GLIBC requirement or `_dl_find_object` dependency. Link probes
   cover executable, shared object, and explicit static runtime selection;
   lint the DSO and probes. Install only to a private validation directory.
3. **E6-01c â€” Compatibility and unwind card payloads.** Build/lint old-client
   and new-client payloads covering the SF/TF interfaces, six explicit version
   aliases, CPU object ABI/initializer, binary128 rounding/exceptions, and
   supported new helpers; cover cross-DSO throw/catch, pthread cancellation,
   backtrace, signal unwind, and dlopen/dlclose/frame registration. Acceptance
   for the engineer: binaries and expected results staged under
   `.work/_shared/<ticket>/`, with explicit donor and candidate search paths
   and no system-library overwrite; native outcomes remain pending the lead.
4. **E6-01d â€” Lead-coordinated native acceptance and installation decision.**
   The lead schedules card jobs through `tools/card_run`, including existing
   sysroot consumers where runnable. Acceptance: actual recorded results for
   E6-01c on glibc 2.21/kernel 2.6.38; no unsupported-instruction or loader
   failures; evidence that cancellation/backtrace load the candidate; agreement
   on private deployment versus donor replacement and a rollback procedure.
   An infrastructure failure is not a native pass. Any broader batch checks
   belong in the applicable batch-check ticket.

**Risks / remaining unknowns:** matching names and versions does not prove
floating ABI or unwinder behavior; the sysroot is not a complete card-program
inventory; runtime glibc lookups escape ordinary versioned-import scans; a
constructor can fault before a requested helper is called; host headers or
libraries could silently raise the GLIBC floor; generated atomics can introduce
unsupported instructions or an unintended libatomic dependency; and two
unwinders in one process can undermine otherwise correct exception tests.
The highest-risk proven gaps are the 17 missing donor names, the generic
Linux frame-registration version map, and the six TF aliases. Resolve these
before claiming a drop-in replacement. Native compatibility and the final
linked import ceiling remain explicitly unknown until the implementation
tickets supply their evidence.
