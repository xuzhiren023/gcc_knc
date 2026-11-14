# KNC libgfortran slice: E6-02 implementation input

S7-02, 2026-11-06. Static research only: no configure, compiler invocation,
build, test, or card job was run. **Proven** below means established by source
or an explicitly supplied ticket fact, not a new native result. **Inferred**
means a design recommendation or consequence of those facts. **Unknown** marks
an unresolved implementation or hardware question.

Source paths without a prefix are relative to `.work/_shared/gcc`, whose
checked-out branch is `knc`. `SYS:` means
`.work/_shared/toolchain/sysroot/`. `GCC5:` means the local GCC repository's
`releases/gcc-5.1.0` tag, read with `git show`, without changing the checkout;
it is an upstream layout reference, not proof of every MPSS vendor patch.
Current-branch ChangeLogs independently locate the later descriptor changes.
The ticket's cited donor-inventory line ranges do not match this worktree's
note; the settled facts are taken directly from S7-02 rather than re-derived.

## 1. FP environment: the entry points and the missing KNC policy

**S12-13 supersession (2026-11-14).** The missing-backend proposal and
selection gap below are historical. Current `libgfortran/config/fpu-knc.h`
implements KNC flag, rounding and state handling with conservative unsupported
mixed-domain halting/underflow-control reports. Source presence is not a
native qualification. References below resolve in [the index](knc-references.md).

**Proven (ticket facts).** KNC reports no SSE, so the existing fpu-387 SSE
paths do not manage its MXCSR. The lead's 2026-11-03 card probe establishes
that MXCSR exception-mask bits 7-12 are reserved and setting them faults;
bit 21 must be preserved. These are inputs to this note, not new experiments.
KNC must not enable any SSE/AVX target flag to reach MXCSR.

**Proven (selection gap).** `libgfortran/configure.host:24-39` defaults to a
generic backend or selects a libc backend from function availability. Its
x86 case at `:42-54` matches only `i?86 | x86_64`, not `k1om`.
`libgfortran/configure.ac:700-701` probes `feenableexcept`, and `:740-750`
selects the header and IEEE module support. Thus merely building the current
k1om target does not explicitly select fpu-387, much less a KNC-safe backend.
**Inferred:** it may select fpu-glibc when that symbol links; link success
says nothing about its KNC safety. `libgfortran/config/fpu-glibc.h:448-457`
delegates environment save/restore to libc.

The following call paths are **proven**. The required KNC behavior is a
**recommended/inferred** contract; uncertain hardware details are listed next.
Internal C names below use the `_gfortrani_` prefix in module bindings.

| Caller and source | Backend operation | Required x87 / KNC behavior |
| --- | --- | --- |
| `_gfortran_set_fpe`, `runtime/fpu.c:33-40`; startup `runtime/main.c:73-74` (both under `libgfortran/`) | `set_fpu` -> `set_fpu_trap_exceptions`; `config/fpu-387.h:155-201` | Preserve x87 precision and rounding while changing its mask bits. Never translate masks to MXCSR bits 7-12. Define unsupported vector-halting behavior explicitly. |
| `libgfortran/ieee/ieee_exceptions.F90:175-205` | `IEEE_GET_FLAG`, `IEEE_SET_FLAG` -> `get/set_fpu_except_flags` | Read the union of supported x87 and vector sticky flags; clear requested flags in both domains. Preserve unrelated state. Raising a flag and causing a trap are distinct from writing a mask. |
| `libgfortran/ieee/ieee_exceptions.F90:209-270` | `IEEE_GET/SET_HALTING_MODE`, `IEEE_SUPPORT_HALTING`, `IEEE_SUPPORT_FLAG` | x87 masks are usable. KNC vector halting is not established; do not inherit fpu-387's unconditional support claims. |
| `libgfortran/ieee/ieee_arithmetic.F90:1244-1279`, `:1015-1025` | `IEEE_GET/SET_ROUNDING_MODE`, `IEEE_SUPPORT_ROUNDING` -> rounding helpers | Synchronize x87 RC bits 10-11 and MXCSR RC bits 13-14. Preserve x87 precision. Support the four binary modes; no ties-away mode. The RADIX=10 setter already returns without changing binary state. |
| `libgfortran/ieee/ieee_arithmetic.F90:1285-1312`, `:1038-1047` | `IEEE_GET/SET_UNDERFLOW_MODE`, support query | FTZ affects the vector domain; x87 does not gain abrupt-underflow control. Do not report whole-kind support merely because FTZ is writable. DAZ also affects input subnormals and must not be silently changed. |
| `libgfortran/ieee/ieee_exceptions.F90:96-138` | `IEEE_GET/SET_MODES` | Calls rounding, underflow and halting helpers separately; any unsupported policy must also hold here. |
| `libgfortran/ieee/ieee_exceptions.F90:143-170` | `IEEE_GET/SET_STATUS` -> `get/set_fpu_state` | Save both domains; restore valid controls and sticky flags, without loading an ordinary x86 default MXCSR or reserved mask bits. |
| `libgfortran/ieee/ieee_helper.c:178-201` | `_gfortran_ieee_procedure_entry/exit` | Save state and clear flags on entry; restore entry state and merge newly raised flags on exit. Include vector flags and controls; avoid losing them across an IEEE-using call. |
| `libgfortran/io/read.c:224-296` | formatted real input temporarily calls `get/set_fpu_rounding_mode` around conversion | Both domains must change and be restored, even without an explicit IEEE module call. |
| `libgfortran/runtime/stop.c:53` | exception summary reads `get_fpu_except_flags` | Include supported vector flags in the summary. |

**Proven (x87 mechanics).** `libgfortran/config/fpu-387.h:174-179` changes
x87 masks and clears pending exceptions; `:243-269` reads flags;
`:273-327` clears flags with `fnstenv/fldenv` and raises requested exceptions
through `local_feraiseexcept` (`:110-150`). `:337-426` implements rounding.
`get_fpu_state` restores the control word after `fnstenv` masks exceptions
(`:430-441`); retain this detail. The private state structure is 32 bytes on
this ABI and checked against the allocated buffer at `:72-92`;
`gcc/fortran/libgfortran.h:76` allocates 32 bytes. Reuse that size rather than
casually changing the compiler/runtime interface. The sysroot documents x87
mask, precision and rounding fields at `SYS:usr/include/fpu_control.h:26-55`
and warns that its controls touch only x87 (`:23-24`).

### MXCSR fields: what is and is not established

**Historical knowledge table, superseded by the architectural definitions
(S12-13).** R27 §2.4 p.39 and §4.1 pp.55–56 defines sticky flags 0–5, DAZ 6,
RC 13–14 and FZ 15. Bits 7–12, 16–20 and 22–31 are reserved; DUE bit 21
must remain one (§B.3 p.660). Bit 20 must not be enabled merely because an
MXCSR mask reports it writable. Vector FP traps are explicitly unsupported
(R04 slides 9,18). These replace “unknown” below for the architecture;
instruction-specific native behavior and mixed-domain runtime support remain
separate proof obligations.

| Bits | Status and evidence | Safe implementation consequence |
| --- | --- | --- |
| 0-5 | **Inferred** candidate sticky-exception positions from `libgfortran/config/fpu-387.h:46-54,243-269`; **unknown** which KNC vector instructions set each bit, especially the denormal bit. This x86 definition is not a complete KNC ISA specification. | Establish the KNC valid-flag mask before enabling union/clear behavior and advertising support. Do not equate all six x87 flags with proven vector support. |
| 6 | **Proven source intent**, DAZ, in `libgcc/config/i386/knc-crtfastmath.c:25-35`; native semantics **unknown here**. | Preserve during ordinary flag/rounding operations; changing input-subnormal behavior is an explicit policy choice. |
| 7-12 | **Proven supplied card result:** reserved; writes setting these bits fault. The ordinary x86 operation is at `libgfortran/config/fpu-387.h:187-194`. | Always keep zero. Never execute the x86 trap-mask translation on KNC. |
| 13-14 | **Proven source use** as RC: `gcc/config/i386/i386-knc.cc:1503-1508`; encodings 00 nearest, 01 down, 10 up, 11 zero in `libgcc/config/i386/64/sfp-machine.h:29-34`. Native all-mode correctness **unknown here**. | Explicit legacy-instruction read/modify/write of only these bits; synchronize x87. |
| 15 | **Proven source intent**, FTZ, in `libgcc/config/i386/knc-crtfastmath.c:25-35`; full underflow semantics **unknown here**. | Preserve by default. Keep underflow-control support conservative until scalar/vector semantics are established. |
| 20, 21 | `libgcc/config/i386/knc-crtfastmath.c:27-28` mentions both. **Proven supplied fact:** keep bit 21. Meaning and safe changes to bit 20, and the full role of bit 21, are **unknown** from these sources. | Preserve both; do not invent a KNC exception-mask mapping. |
| 16-19, 22-31 | **Unknown** from the inspected source and sysroot. | No writes that change them; obtain the architectural definition before widening any writable mask. |

The crtfastmath comment calls 7-12 exception masks. **Proven:** its actual
code only ORs `0x8040`; it does not set 7-12. The supplied card result takes
precedence over that inherited terminology. Do not reuse the comment as proof
that KNC implements ordinary x86 masks.

### Smallest safe design

**Inferred recommendation:** add an explicit `k1om` backend selection and a
small `config/fpu-knc.h`, implementing the existing helper interface. Reuse
x87 logic but centralize legacy `stmxcsr`/`ldmxcsr` access and sanitized
read/modify/write. No CPUID SSE workaround, SIMD intrinsic, VEX encoding,
opaque bytes, or full x86 default-state constant is needed. KNC already uses
legacy access in `libgcc/config/i386/knc-sfp-machine.h:7-12` and
`gcc/config/i386/imci.md:1911-1915`.

For a change or saved-state restore, let W contain only KNC fields whose
writability and semantics have been established. Merge desired W bits into a
fresh live value; preserve the other live bits, explicitly keep 7-12 zero,
and retain live bit 21. Initially RC is the identified control field; add
validated sticky flags and any deliberately supported underflow field later.
Do not blindly `ldmxcsr` an arbitrary saved x86 word. Save/restore must still
restore all supported semantic fields, not silently discard flags.

**Proven dependency:** KNC libgcc reads its soft-fp rounding from MXCSR
(`libgcc/config/i386/knc-sfp-machine.h:8-12`), while its exception raiser
uses x87 without SSE (`libgcc/config/i386/t-knc:4-8` and
`libgcc/config/i386/sfp-exceptions.c:44-91`). Thus x87-only rounding is
insufficient even for software binary128, and x87-only flag observation is
insufficient for IMCI. The inherited `FP_TRAPPING_EXCEPTIONS` calculation
still shifts MXCSR by seven (`libgcc/config/i386/sfp-machine.h:65`,
`libgcc/config/i386/64/sfp-machine.h:24`); its meaning on KNC needs a separate
audit rather than treating the existing soft-fp port as IEEE validation.

**Historical unknown/release-gate rationale, superseded by R27 pp.39,55–56
(S12-13):** KNC vector halting support and the full flag mask.
The absence of x86 mask bits does not by itself prove that KNC has no other
trap mechanism. Until resolved, conservatively report vector-wide halting
unsupported and reject or clearly constrain requests for it; do not report
success while trapping only x87. Retaining x87-only halting can be a documented
restricted mode, but is not a general IEEE guarantee for vectorized Fortran.
Do not emulate halting by hidden polling after every vector operation.
Likewise, initially report underflow control unsupported across mixed x87/IMCI
execution; the current x87 backend already returns false without SSE
(`libgfortran/config/fpu-387.h:459-498`). Full IEEE modules must not advertise
unsupported capabilities merely to make a smoke test pass.

**Current unresolved issue (S12-13):** R04 slide 9 and R27 pp.36,39 describe
gradual output underflow with FZ clear, whereas current `fpu-knc.h` reports
observed output flushing regardless of FTZ. Input-subnormal tests do not settle
that discrepancy. Retrieve original instruction/control-state evidence before
changing policy. R12 CD19 p.23 also means a faulting vector instruction's
MXCSR snapshot is not a clean arithmetic oracle. CD28 p.25 affects clearing
unmasked x87 exceptions with FNCLEX; the current flag helper uses
`fnstenv`/status edit/`fldenv`, which avoids that instruction but is not proof
of all libc/libgcc recovery paths or the specified FNSAVE/FRSTOR workaround.

## 2. Descriptors, objects, modules and runtime isolation

**Proven:** GCC 16's internal descriptor is defined at
`libgfortran/libgfortran.h:368-392` and constructed by the front end at
`gcc/fortran/trans-types.cc:2076-2112`:

```c
struct dimension { index_type stride, lower_bound, upper_bound; };
struct dtype { size_t elem_len; int version;
               signed char rank, type; signed short attribute; };
struct descriptor { void *base_addr; size_t offset; struct dtype dtype;
                    index_type span; struct dimension dim[]; };
```

**Proven historical reference:** `GCC5:libgfortran/libgfortran.h:322-337`
has `base_addr`, `size_t offset`, one `index_type dtype`, then dimensions,
with no span. Its dtype encodes rank in bits 0-2, type starting at bit 3,
and element size starting at bit 6 (`GCC5:gcc/fortran/libgfortran.h:154-159`).
The current branch records addition of span and ABI version 5 in
`libgfortran/ChangeLog-2017:276-280`, and replacement of packed dtype by the
structured form in `libgfortran/ChangeLog-2018:1637-1652`. This agrees with
the ticket's settled pre-GCC-8 versus GCC-16 incompatibility; the exact
vendor binary's internal patches were not inspected.

**Inferred LP64 offsets**, not measured in a compilation: both begin with
base at 0, offset at 8, dtype at 16. GCC 5 dimensions begin at 24; GCC 16's
16-byte dtype is followed by span at 32 and dimensions at 40. Each dimension
contains three 8-byte indices. Rank limits are 7 and 15 respectively
(`GCC5:gcc/fortran/libgfortran.h:154`, `gcc/fortran/libgfortran.h:192`). An
old routine reading a new descriptor interprets fields at the wrong offsets.
Do not repair this by renaming symbols or casting pointers.

**Inferred policy:** rebuild all Fortran objects and their modules with the
GCC 16 KNC compiler and matching runtime. In particular, assumed-shape,
allocatable, pointer and descriptor-using intrinsic boundaries must not mix
versions. Descriptor-free scalar calls are not proof of general object ABI
compatibility: hidden character arguments, derived types and runtime entry
points also need agreement. A deliberately audited `BIND(C)` boundary using
plain C-compatible scalars or pointers plus explicit sizes can isolate old
code; neither side may pass private Fortran descriptors or ownership across
it. That bridge is outside this slice.

**Proven:** GCC 16 writes module format "16" and accepts "15" as an older
format (`gcc/fortran/module.cc:85-89,7826-7840`); GCC 5's upstream format is
"14" (`GCC5:gcc/fortran/module.c:95`). Module-format compatibility is not a
compiler release number or a promise of object ABI compatibility. Rebuild
user `.mod` files and the runtime's IEEE `.mod` files; do not edit their
version strings. ISO_C_BINDING and ISO_FORTRAN_ENV are compiler-provided
modules (`gcc/fortran/module.cc:7726-7741`); IEEE module files are built and
installed by `libgfortran/Makefile.am:89-93,1101-1116`.

**Proven:** `CFI_cdesc_t` is a separate C interoperability descriptor with
`base_addr, elem_len, version, rank, attribute, type, dim[]`
(`libgfortran/ISO_Fortran_binding.h:37-38,63-89`). It is not the internal GCC
descriptor or a compatibility bridge to GCC 5. Install GCC 16's matching
header and CFI runtime if exposing this interface.

**Proven source versions:** `libgfortran/libtool-version:6` is `5:0:0`
versus `GCC5:libgfortran/libtool-version:6` at `3:0:0`. The ELF SONAMEs are
therefore **inferred** `libgfortran.so.5` and `.so.3`; the new output has not
been built or inspected. Current symbol-version nodes start at `GFORTRAN_8`
(`libgfortran/gfortran.map:1`) with later additions through `:2036`.
These provide useful loader/linker failure boundaries, not a conversion layer.

**Inferred deployment recommendation:**

- Use a private GCC 16 KNC prefix for compiler, `libgfortran.spec`, archive,
  shared runtime and modules. Ensure link-time search resolves the new
  unversioned `-lgfortran`, not the old card/sysroot linker name. SONAME alone
  cannot prevent linking the wrong library initially.
- Prefer `-static-libgfortran -static-libgcc` for the first slice. The driver
  surrounds `-lgfortran` with static/dynamic selection at
  `gcc/fortran/gfortranspec.cc:163-177`; this still needs the correct archive
  search path. It does not make libc/libm static or automatically isolate
  every transitive dependency. KNC currently deliberately builds only static
  libgcc (`libgcc/config/i386/t-knc:11-13`).
- If distributing shared libgfortran, retain `.so.5` and symbol versions;
  package it privately and set a deployment-relative runtime path, e.g.
  `$ORIGIN/../lib`. Inspect DT_NEEDED, SONAME, RPATH/RUNPATH and transitive
  dependencies in the implementation ticket. RUNPATH/environment search order
  and dependency-local lookup must be checked on the card's loader. Never
  symlink `.so.5` to `.so.3` or overwrite the system runtime.
- When quadmath is enabled, select its matching runtime separately;
  `libgfortran/acinclude.m4:363-403` implements `-static-libquadmath` handling
  and independent quadmath linkage. Clear old module/library search paths in
  the deployment invocation. Do not use global LD_LIBRARY_PATH as the sole
  guarantee of isolation.

**Unknown:** actual loader behavior and symbol requirements of a newly built
GCC 16 runtime against the old card libc. No deployment or native compatibility
is claimed here.

## 3. REAL(16) and libquadmath

**Proven type distinction:** the front end derives kind from mode precision,
not padded storage size (`gcc/fortran/trans-types.cc:520-545`). Given the
settled S1 x87 80-bit long double ABI, it is kind 10 even in 16 storage bytes.
Kind 16, if enabled, is binary128/TFmode, corresponding to `__float128` and
C `_Float128`, with 113 significand bits rather than x87's 64.
`libgfortran/mk-kinds-h.sh:53-86` explicitly maps kind 10 to long double and
kind 16 to `_Float128` when `c_long_double != 16`. No precision-preserving
interpretation permits replacing kind 16 with the padded 80-bit type.

**Proven source feasibility, unknown build result:** libquadmath's gate is
usable `__float128` and complex arithmetic, not SSE
(`libquadmath/configure.ac:234-270`). Its local soft-fp square-root support
uses integer words and `fegetround` (`libquadmath/sfp-machine.h:1-47`). KNC
already selects TF soft-fp in `libgcc/config.host:807-813`, with no SSE2 helper
makefile (`libgcc/config/i386/t-knc:1-8`). Consequently absence of SSE is not
an intrinsic reason libquadmath cannot build. This is not proof that all its
sources compile, link, or behave correctly with today's KNC ABI. The SSE2
probe in generated `libquadmath/configure:13563-13593` belongs to optional
x86 CET detection, not the float128 gate.

**Proven remaining dependency:** libquadmath calls libc's FP-environment
functions. For example `libquadmath/math/expq.c:139-143` saves/holds state and
sets nearest rounding; `libquadmath/math/fmaq.c:182-245` changes rounding and
examines flags. `libquadmath/quadmath-imp.h:274-297` supplies no-op fallbacks
when functions are unavailable, and `:309-339` saves/changes/restores rounding.
The old sysroot header declares x87-plus-MXCSR `fenv_t`
(`SYS:usr/include/bits/fenv.h:71-94`), but does not prove that out-of-line
libm functions preserve KNC bit 21 or avoid bits 7-12. Fixing libgfortran's
private backend will not fix these libc calls. Their runtime behavior is
**unknown** and must gate binary128 support.

**Inferred decision:** defer kind 16 in the first deployable slice; retain
real kinds 4, 8 and 10 without changing their precision. Configure compiler
and target runtime consistently with `--disable-libquadmath-support` and
omit the quadmath library using `--disable-libquadmath` at top level. The
front-end TF-kind gate is `gcc/fortran/trans-types.cc:525-530`; top-level
switches are `configure.ac:481-499`. Disabling only library construction
while leaving the compiler advertising kind 16 is unsafe:
`libgfortran/acinclude.m4:272-323` checks runtime support and
`libgfortran/kinds-override.h:28-29` errors if generated kinds advertise
float128 without HAVE_FLOAT128. Prefer a clear unsupported-kind diagnostic
and negative selected-real-kind result over missing symbols or reduced
precision. This is a proposed first-slice restriction, not an already
configured property of the shared compiler.

A later binary128 ticket should enable both compiler and runtime together,
validate TF/TC argument and return conventions and helper linkage, audit
libc fenv calls or provide a scoped safe replacement, and cover formatted
conversion. Input already dispatches to `strtof128` or `strtoflt128`
(`libgfortran/io/read.c:263-270`); the modern libc `*f128` path must not be
assumed present on the card. `libgfortran/configure.ac:679-698` and
`libgfortran/acinclude.m4:314-323,384-403` select that alternative.

## 4. Slice contents and static build obstacles

**Inferred scope:** use the ordinary runtime with a bounded validation surface,
not a new descriptor ABI or a hand-pruned replacement library. Cover integer,
logical, character and real 4/8/10 programs; array descriptors and allocation;
formatted internal/external I/O; intrinsic modules and truthful IEEE support.
Defer coarray transport, binary128 deployment, and optimized x86 math variants.

| Needed component | Proven source responsibility | Slice implication (inferred) |
| --- | --- | --- |
| Descriptors and array temporaries | `libgfortran/libgfortran.h:368-392`; generic pack/unpack in `libgfortran/Makefile.am:180-183`, typed generated helpers `:617-646` | Exercise non-unit lower bounds, noncontiguous sections and assumed-shape calls, including copy-back. |
| Allocation/deallocation | `gcc/fortran/trans.cc:744-762,1815-1927,2237` lowers ordinary allocation/free/reallocation; `libgfortran/runtime/memory.c:31-94` supplies checked wrappers | Not all ALLOCATE is a libgfortran call. Cover ownership, reallocating assignment and deallocation, using matching compiler/runtime. |
| Formatted I/O | `libgfortran/Makefile.am:119-140` lists format, transfer, list-read, units, files, buffers, locking and async support | Include READ/WRITE, OPEN/CLOSE, internal strings, IOSTAT and real conversion, plus runtime errors/startup/stop. |
| Conversion and rounding | `libgfortran/io/read.c:224-296`; `libgfortran/io/write_float.def:346-405` | Input changes hardware rounding temporarily; output also implements decimal rounding rules. Test restoration and representative ROUND modes, not just printed text. |
| Modules and C interop | `gcc/fortran/module.cc:7726-7741`; `libgfortran/Makefile.am:89-93,1101-1154` | Compiler-provided ISO modules, fresh IEEE module files, matching optional CFI header/runtime; no GCC 5 module reuse. |
| Runtime support/dependencies | `libgfortran/Makefile.am:239-261,54-58` | Memory, bounds, strings, startup, errors, FP, stop, backtrace; link libm and compatible libgcc. Account for libbacktrace too. |

Static obstacles and uncertainties:

1. **Proven FP selection/semantic blocker:** the missing k1om case and unsafe
   x86-mask semantics described above. Selecting fpu-387 alone leaves vector
   state unmanaged; forcing `has_sse` true would introduce the faulting mask
   writes. A generic fallback is not a completed IEEE implementation.
2. **Proven configuration hazard, inferred containment:**
   `libgfortran/configure.ac:808-824` invokes AVX/AVX2/AVX512/FMA probes;
   `libgfortran/acinclude.m4:447-458` replaces CFLAGS with `-O2 -mavx`.
   Generated matmul code contains target-specific functions
   (`libgfortran/generated/matmul_r4.c:79-85,1219-1223`) and CPU dispatch
   (`:2393-2418`). Explicitly keep these probes/features off for k1om, even
   if some compiler probe could accept an x86 option. Successful cross-compile
   detection must not authorize unavailable instructions on KNC.
3. **Proven kind-generation consistency blocker:**
   `libgfortran/configure.ac:222-223` lists candidate kinds; compile probes
   in `libgfortran/mk-kinds-h.sh:61-86` determine emitted kinds. Use the same
   new target C and Fortran compilers and matching feature settings, not the
   host compiler or donor gfortran. The HAVE_FLOAT128 consistency error above
   prevents merely omitting quadmath while still generating kind 16 support.
4. **Proven unsuitable shortcut:** `LIBGFOR_MINIMAL` is currently false
   (`libgfortran/configure.ac:212-217`). Enabling it removes almost all I/O
   (`libgfortran/Makefile.am:122-140`) and startup/FP pieces (`:247-261`), so
   it does not satisfy this slice. Reduce the acceptance surface, not required
   runtime functions.
5. **Unknown cross-build outcomes:** old libc/libm symbols, locale facilities,
   pthreads, generated files and backtrace linkage. Function probes are at
   `libgfortran/configure.ac:301-346`, while `Makefile.am:54-58` links
   libbacktrace/libm and requests shared-libgcc. The latter needs explicit
   resolution against KNC's static-only libgcc policy, not accidental use of
   the GCC 5 shared library. Do not force positive cache results for unavailable
   APIs. Header presence is not proof of binary compatibility.
6. **Unknown runtime fenv safety outside libgfortran:** libc conversion and
   libquadmath calls can bypass the new private backend. Audit this boundary
   before enabling binary128 or claiming complete IEEE support.

## Recommended E6-02 ticket split and acceptance

All four are proposed implementation tickets. Their acceptance tests are
future work; none ran in S7-02. Code work follows the project's red-test-first
rule. Engineers build/lint card binaries in the shared ticket directory;
the lead schedules native runs and records the actual results.

1. **KNC FP backend and capability contract.** Resolve the flag-bit and
   vector-halting unknowns from architectural evidence and lead-run probes;
   implement explicit backend selection, safe legacy MXCSR access, synchronized
   rounding and complete supported-state save/restore. Acceptance: all four
   binary rounding modes agree across x87 and IMCI; each supported flag can be
   observed and cleared from either domain; nested IEEE procedure state merges
   flags correctly; bit 21 and unrelated controls survive every setter and
   restore; no 7-12 mask writes or illegal ISA instructions. Unsupported
   halting/underflow capabilities are reported truthfully, with explicit
   behavior for attempted enabling. Include formatted-input rounding restore.
2. **Build the base runtime and exercise the descriptor/I/O slice.** Keep
   kinds 4/8/10 consistent, exclude x86 AVX/FMA variants, resolve old-sysroot
   and static-libgcc linkage, and build fresh IEEE modules. Acceptance: linted
   KNC executables plus lead-run allocation/reallocation/deallocation,
   noncontiguous assumed-shape copy-back, non-default bounds, formatted
   internal/external read/write, IOSTAT failure handling, kind-10 conversion,
   and module-use tests. Include a negative kind-16 compile and
   selected_real_kind check for the disabled configuration. No native result
   is accepted from compilation alone.
3. **Runtime isolation and packaging.** Install in a private versioned prefix;
   make the first static-runtime invocation reproducible, and only offer a
   shared variant after its libgcc dependency is resolved. Acceptance: link
   map identifies the new archive/spec and fresh module directory; static
   executable has no old libgfortran/libgcc shared dependency. If shared is
   offered, verify `.so.5` SONAME, symbol versions and private loader path on
   the card, including with `.so.3` installed. A deliberate old-runtime link
   or module selection must fail visibly, not execute through an ABI mismatch.
4. **Optional binary128 enablement.** Build libquadmath without SSE, audit
   libc fenv and KNC TF/TC ABI/helpers, then enable kind 16 consistently.
   Acceptance: distinguish kind 10/64-bit significand from kind 16/113-bit
   significand; link and lint arithmetic, conversion and representative math
   entry points; lead-run directed rounding, exceptional values/flags,
   complex argument/return and formatted input/output tests. Verify MXCSR
   preservation through quadmath's environment operations. If this cannot be
   met, keep binary128 explicitly unsupported; never substitute long double.

**Risks / open decisions:** vector halting and the full KNC status-bit map
remain the largest semantic gaps; preserving bit 21 is necessary but not a
complete fenv specification. Mixed x87/IMCI and soft-fp code can disagree on
rounding or exception state even when a scalar smoke test passes. Old libc
fenv behavior and shared-libgcc availability can defeat a correct private
libgfortran backend. Descriptor and `.mod` contamination can occur at build
time before SONAME protections matter. Binary128 adds ABI, soft-fp and libc
rounding dependencies and should not block the explicitly restricted first
slice. No buildability, loader compatibility, performance, or native IEEE
conformance is claimed by this static note.
