# KNC configure-case audit (S3-14)

Scope: `gcc/configure.ac`, `libgcc/configure.ac`, `libgcc/config.host`,
`libgfortran/configure.ac`, and every `config/*.m4` in the shared GCC 16 tree.
Locations refer to the pre-fix source (line numbers are unchanged by the fix).
The decision is for `k1om-mpss-linux`, not for the Cygwin build machine.

The table inventories every line containing an x86_64 triplet alternative,
including OS-specific alternatives and the already-covered S1-02 case. This
checkout contains 52 such lines (54 alternatives), rather than the ticket's
approximate 73. Non-triplet uses are accounted for below.

"Before" and "after" describe configure dispatch and resulting settings, derived
from the case bodies. They are not claims that unsupported OS/ISA variants were
built. Measured configure/build/test results are recorded separately below.
"Same" means the preceding result is deliberately retained.

Reference mechanisms checked in the donor: `gcc/configure.ac` native TLS cases
at 3042/3086 and PIE copy-relocation case at 4718. These mechanisms still exist in
GCC 16. The native TLS probe body is reused unchanged. No ISA flags, floating-point
modes or target runtime helper sets are added; code generation uses existing
backend patterns.

## `gcc/configure.ac`

| Line / alternative | Use x86_64 branch? | Reason | Before | After |
|---|---|---|---|---|
| 2366 `x86_64-*-*` | Yes; changed | Respect explicit CLD and frame-pointer options on the shared scalar x86 backend. Neither requires SSE/AVX. | Options ignored; default has neither tm_define. | Explicit yes adds USE_IX86_CLD=1 / USE_IX86_FRAME_POINTER=1; default unchanged. |
| 2892 `x86_64-*-solaris2*:yes` | No | Solaris GNU ld emulations are not the KNC ELF ABI. | Solaris branch skipped. | Same. |
| 2896 `x86_64-*-*:yes` | No | elf_i386 / elf_x86_64 would select the wrong ELF machine. KNC ld already defaults to elf_k1om. | ld_32_opt and ld_64_opt unset. | Same; keep KNC linker default. |
| 3548 `x86_64-*-solaris2.*` | No | Solaris read-only .eh_frame workaround, not Linux GNU as. | Solaris workaround skipped; normal CFI probe applies. | Same. |
| 3562 `x86_64-*-darwin*` | No | Mach-O compact unwind workaround, not KNC ELF. | Darwin CFI disabling skipped. | Same. |
| 3718 `x86_64-*-solaris2*` | No | Sun as #exclude syntax, not KNC GNU as. | Solaris fallback skipped. | Same. |
| 3815 `x86_64-*-solaris2*` | No | Sun .group COMDAT syntax, not KNC GNU as. | Solaris fallback skipped. | Same. |
| 3995 `x86_64-*-*` | Yes; changed | Enter the existing ELF TLS probe; donor gcc/configure.ac has this same KNC branch. | Probe not selected; HAVE_AS_TLS undefined. | Select .tdata and 64-bit native TLS probe; rebuild result below. |
| 3997 `x86_64-*-solaris2*:no` | No | Sun as lowercase TLS section flag is Solaris-specific. | No Solaris match; no TLS_SECTION_ASM_FLAG override. | Default TLS section flag T; no override. |
| 4011 `x86_64-*-linux-gnuabi32` / `x86_64-*-mingw32abi32` | No | i386/x32 TLS uses %gs, %ebx and 32-bit relocations; KNC is LP64. | 32-bit TLS branch skipped. | Same; select 64-bit branch instead. |
| 4028 `x86_64-*-*` | Yes; changed | Use the donor-compatible %fs, RIP-relative TLSGD/TLSLD/GOTTPOFF and TPOFF probe. | 64-bit TLS body not selected. | tls_as_opt=as_64_opt, which is empty for k1om (`gcc/acinclude.m4` gcc_GAS_FLAGS sets it only for i?86 and x86_64), so the probe ran without `--64` (`configure:28417` in `gcc-build/gcc/config.log`); it assembles because k1om `as` is 64-bit by default. |
| 4810 `x86_64-*-*` | Already covered | S1-02 already included k1om for scalar x86 assembler probes. | Shared x86 assembler probes selected. | Same; no change. |
| 6145 `x86_64-*-linux*` | Yes; changed | KNC ELF Linux uses the same scalar RIP-relative PIE/copy-relocation test; donor includes KNC here. | gcc_cv_ld_pie_copyreloc=no without probing. | Run probe with KNC default ld emulation; measured result below. |
| 6374 `x86_64-*-darwin*` | No | This dispatch is build,host for executing Darwin cross-architecture tests, not the compiler target. | Darwin exception inapplicable to Cygwin host. | Same. |
| 7896 `x86_64-*-*gnu*` | No | GNU/glibc x86 default for __fentry__ is not an MPSS runtime capability check. The canonical target is `k1om-mpss-linux-gnu`, so the pattern would match if k1om were added; it is left out because only `-pg` uses it, mcount works, and `__fentry__` support was not checked on the card (lead correction, 2026-11-03). | ENABLE_X86_64_MFENTRY=0. | Same. |

## `libgcc/configure.ac`

| Line / alternative | Use x86_64 branch? | Reason | Before | After |
|---|---|---|---|---|
| 519 `x86_64-*-solaris2*` | No | Solaris linker ZERO-terminator .eh_frame test is not Linux. | Solaris unwind-terminator test skipped. | Same. |
| 634 `x86_64-*-*` | No | vzeroupper is AVX; KNC must never enable AVX. | AVX probe skipped; HAVE_AS_AVX undefined. | Same. |

## `libgcc/config.host`

| Line / alternative | Use x86_64 branch? | Reason | Before | After |
|---|---|---|---|---|
| 131 `x86_64-*-*` | Already covered separately | Immediately following k1om case already maps cpu_type to i386. | cpu_type=i386 through k1om case. | Same; no change. |
| 229 `x86_64-*-darwin2[0-2]*` | No | Darwin 20-22 deployment minimum and libgcc_s stubs are not Linux. | Darwin minimum/stub files omitted. | Same. |
| 383 `x86_64-*-mingw*` | No | Windows executable-stack implementation uses a different OS API. | enable_execute_stack=enable-execute-stack-empty.c. | Same. |
| 386 `x86_64-*-cygwin*` | No | Cygwin executable-stack implementation is for target Windows, not the build host. | enable_execute_stack=enable-execute-stack-empty.c. | Same. |
| 739 `x86_64-*-darwin*` | No | Mach-O CRT, unwind and heap trampoline build rules are not KNC Linux. | Darwin target branch skipped. | Same. |
| 752 `x86_64-*-elf*` / `x86_64-*-rtems*` | No | Bare ELF/RTEMS CRT layout is not Linux; KNC already has its own CRT/runtime selection. | Bare ELF/RTEMS branch skipped. | Same. |
| 755 `x86_64-*-rtems*` | No | RTEMS crti/crtn startup objects are OS-specific. | RTEMS extra_parts not added. | Same. |
| 760 `x86_64-*-fuchsia*` | No | Fuchsia runtime layout is not Linux. | Fuchsia branch skipped. | Same. |
| 767 `x86_64-*-dragonfly*` | No | DragonFly unwinder and runtime rules are OS-specific. | DragonFly branch skipped. | Same. |
| 775 `x86_64-*-freebsd*` | No | FreeBSD unwinder and runtime rules are OS-specific. | FreeBSD branch skipped. | Same. |
| 782 `x86_64-*-netbsd*` | No | NetBSD runtime selection is OS-specific. | NetBSD branch skipped. | Same. |
| 787 `x86_64-*-openbsd*` | No | OpenBSD target branch is not Linux. | OpenBSD branch skipped. | Same. |
| 816 `x86_64-*-linux*` | No; KNC branch already supplies the applicable pieces | Preceding k1om branch intentionally uses i386/t-knc, t-tls, binary128 soft-fp and Linux unwinding. x86_64 adds unaudited decimal/x87 precision constructors and heap trampolines. | KNC extra_parts includes crtfastmath.o; tmake_file includes i386/t-crtstuff t-tls t-softfp-tf i386/t-knc t-softfp; Linux/value unwind headers. | Same. |
| 823 `x86_64-*-kfreebsd*-gnu` | No | GNU/kFreeBSD target runtime is not MPSS Linux. | kFreeBSD branch skipped. | Same. |
| 828 `x86_64-*-gnu*` | No | GNU Hurd unwind ABI differs from Linux. | Hurd branch skipped. | Same. |
| 846 `x86_64-*-solaris2*` | No | Solaris CRT precision constructors and MS ABI rules do not apply. | Solaris branch skipped. | Same. |
| 852 `x86_64-wrs-vxworks*` | No | VxWorks target case is OS-specific. | VxWorks branch skipped. | Same. |
| 873 `x86_64-*-cygwin*` | No | Cygwin DLL, PE/SEH and stack-probe runtime rules are not ELF Linux. | Cygwin target branch skipped. | Same. |
| 927 `x86_64-*-mingw*` | No | MinGW DLL, thread-model and SEH runtime rules are not ELF Linux. | MinGW target branch skipped. | Same. |
| 1596 `x86_64-*-*` | No | KNC runtime deliberately excludes generic x86 CPU dispatch; no shared dispatch implementation has been ported. | i386/t-cpuinfo[-static] not selected. | Same. |
| 1609 `x86_64-*-linux*` | No; applicable TLS rule already supplied | KNC has t-tls in its own branch. The remaining t-linux, t-msabi, shared libgcc and x86 stack rules would undo the deliberately static KNC runtime selection. | KNC t-tls selected; x86 MS ABI/shared runtime bundle omitted. | Same; rebuild libgcc with native-TLS compiler. |
| 1610 `x86_64-*-kfreebsd*-gnu` | No | kFreeBSD alternative in the same runtime bundle; not Linux. | Runtime bundle skipped. | Same. |
| 1611 `x86_64-*-gnu*` | No | Hurd alternative in the same runtime bundle; not MPSS Linux. | Runtime bundle skipped. | Same. |
| 1623 `x86_64-*-*` | No; binary128 rule already supplied | KNC already has t-softfp-tf and t-softfp plus i386/t-knc. Generic i386/64/t-softfp and i386/t-softfp introduce HF/BF helpers requiring SSE2. | KNC binary128 helpers selected; generic SSE2 helper rules omitted. | Same. |
| 1630 `x86_64-*-linux*` | No; unwind header already supplied | KNC already includes i386/value-unwind.h. Generic x86 Linux backward soft-fp compatibility symbols are not a ported KNC ABI. | value-unwind.h included; i386/64/t-softfp-compat omitted. | Same. |

## `config/cet.m4`

| Line / alternative | Use x86_64 branch? | Reason | Before | After |
|---|---|---|---|---|
| 12 `x86_64-*-linux*` | No | KNC has neither CET nor SSE2; do not enable target-library control-flow protection. | enable_cet=no; CET_FLAGS empty. | Same. |
| 66 `x86_64-*-linux*` | No | CET host-library support applies to the host architecture, not the KNC compiler target. A native KNC host also lacks CET. | Cygwin host takes fallback: enable_cet=no, may_have_cet=no. | Same. |

## `config/dfp.m4`

| Line / alternative | Use x86_64 branch? | Reason | Before | After |
|---|---|---|---|---|
| 42 `x86_64*-*-linux*` | No | KNC libgcc explicitly excludes decimal float; enabling it would advertise missing runtime support. | Automatic enable_decimal_float=no. | Same. |
| 43 `x86_64*-*-gnu*` | No | Hurd/ELFIAMCU decimal target alternatives do not apply to MPSS Linux. | Automatic decimal support remains disabled. | Same. |
| 44 `x86_64*-*-mingw*` | No | MinGW decimal target alternative does not apply. | Automatic decimal support remains disabled. | Same. |
| 45 `x86_64*-*-cygwin*` | No | Cygwin decimal target alternative does not apply. | Automatic decimal support remains disabled. | Same. |
| 59 `x86_64*-*-*` | No | Format dispatch is inside enable_decimal_float=yes. No decimal runtime is ported for KNC; adding a BID branch alone would not supply one. | Automatic no uses default_decimal_float=dpd only for libdecnumber dependency; ENABLE_DECIMAL_FLOAT=0. | Same; explicit decimal enable is outside the supported KNC runtime. |

## `config/picflag.m4`

| Line / alternative | Use x86_64 branch? | Reason | Before | After |
|---|---|---|---|---|
| 26 `x86_64-*-cygwin*` | No | Windows targets need no ELF PIC flag; KNC does. | Cygwin target alternative skipped. | Same. |
| 28 `x86_64-*-mingw*` | No | MinGW targets need no ELF PIC flag; KNC does. | MinGW target alternative skipped. | Same. |
| 59 `x86_64-*-*` | No | On x86-64, -fpic and -fPIC produce the same code. Revert the added KNC alternative: it gains nothing and adds fork surface. | KNC PICFLAG_FOR_TARGET=-fPIC (generic fallback). | Same; explicit user -fpic/-fPIC overrides retained. Host PICFLAG unchanged. |

## Other occurrences and files without a matching case

- `libgfortran/configure.ac` has no x86_64 triplet cases. Its `GCC_CET_FLAGS`
  invocation at 165 expands `config/cet.m4:12`, covered above; CET remains disabled.
- `libgcc/configure.ac:338` uses `__x86_64__` in a C preprocessor word-size
  probe, not a shell triplet. KNC defines that macro and already gets
  `host_address=64`; unchanged.
- `gcc/configure.ac` uses x86_64 in ld emulation names (2894/2898),
  `R_X86_64_CODE_6_GOTTPOFF` probe identifiers/comments (5058-5088), and the
  mfentry option/variable names (7886-7904). These are not additional triplet
  cases. The GOTTPOFF probe is already reached through the S1-02 case at 4810;
  its capability result is not forced to yes.
- `config/tcl.m4:1596-1604,1612,1658` names Apple's `-arch x86_64` option,
  cached acceptance of that option, and removal/detection of Darwin fat-binary
  options. These are not target triplet cases and should not gain k1om. KNC is
  not a Darwin universal-binary architecture; these host checks are unchanged.
- All other `config/*.m4` have no x86_64 occurrence.

## Regeneration and measured results

The changed `gcc/configure.ac` is committed with `gcc/configure`.
`config/picflag.m4` expands in `gcc/configure`, `libiberty/configure`,
`libgcc/configure` and `libada/configure`. The initial PIC flag change did not
regenerate the latter two; it has been reverted, with `config/picflag.m4` and
`libiberty/configure` restored to the knc versions.

After that revert, `gcc/configure` was regenerated under Cygwin sh with the
shared autotools bin first on PATH, then the shared Cygwin bin. Reported
versions: GNU Autoconf 2.69, GNU M4 1.4.19. Its diff against knc contains only
the four case-line additions implied by `gcc/configure.ac`. No generated file
was edited by hand. Regeneration log:
`.work/_state/logs/s3_14_autoconf_correction-20261103-233627.log`.

Before the fix, the shared build's auto-host.h had HAVE_AS_TLS undefined,
HAVE_LD_PIE_COPYRELOC=0, ENABLE_X86_64_MFENTRY=0; config.log had
PICFLAG_FOR_TARGET=-fPIC. The approved red commit 3f40227 records donor passing
and GCC 16 failing all three native TLS modes.

The fresh configure reports `checking assembler for thread-local storage
support... yes`; auto-host.h now defines HAVE_AS_TLS=1. The newly executed PIE
copy-relocation check reports no (HAVE_LD_PIE_COPYRELOC=0); unsupported capability
is not assumed. That initial configure recorded PICFLAG_FOR_TARGET=-fpic;
the corrected source retains -fPIC. ENABLE_X86_64_MFENTRY remains 0.
Per the lead's correction, no full rebuild is needed: PICFLAG_FOR_TARGET only
affects target libraries we do not build, and libgcc already used its own -fPIC.

The clean C/Fortran rebuild passed via tools/toolchain.py gcc16 (all-gcc;
53.4 minutes including configuration). Log:
`.work/_state/logs/s3_14_gcc16_full-20261103-223032.log`.

Libgcc was rebuilt from source by the new xgcc via tools/toolchain.py libgcc
(all-target-libgcc), not copied from the donor. It passed in 1.4 minutes.
Its configure results are gcc_cv_have_cc_tls=yes, gcc_cv_use_emutls=no,
set_have_cc_tls=-DHAVE_CC_TLS and empty set_use_emutls. Log:
`.work/_state/logs/s3_14_libgcc-20261103-232428.log`.

The requested tools/check.py t0 t1 t2 --compiler gcc16 run passed once, in
173.19 seconds. T1 donor and selected-compiler checks passed in all three TLS
modes (O2, O2-fPIC, O0). Defined and external non-PIC access use %fs with
TPOFF/GOTTPOFF; PIC access uses TLSGD and __tls_get_addr. The ordered TLS
operations match the donor and no __emutls access remains in these tests.
Detailed log:
`.work/_state/logs/check_gcc16_t0_t1_t2-20261103-232642.log`;
wrapper log: `s3_14_regression-20261103-232641.log` in the same directory.

After the PIC flag revert and configure regeneration, the lead-requested
`tools/check.py t1 --compiler gcc16` rerun passed once through `tools/run.py`
in 83.93 seconds. Detailed log:
`.work/_state/logs/check_gcc16_t1-20261103-233701.log`;
wrapper log: `s3_14_t1_correction-20261103-233700.log` in the same directory.

The O2 torture compile/assemble/lint sweep ran once over all 2,003 sources:
1,968 pass, 33 compiler errors, two user inline-asm rejections. There were zero
ICEs, assembler rejections, lint failures, hangs, slow retries or infrastructure
failures. These outcome counts match the prior O2 baseline in
`tests/baseline/gcc16-torture-compile.txt`. The shared summary was overwritten at
`.work/_shared/torture-compile-summary.txt`; detailed outputs remain in the
existing shared torture-compile directory. Log:
`.work/_state/logs/s3_14_torture_o2-20261103-232641.log`.

All builds and tests above ran through tools/run.py.
Native mixed-object/shared-library checks belong to S3-10 and must use objects
built after this fix; no native result is claimed here.
