## 2026-11-03T23:19:18+00:00

Base: `releases/gcc-16.2.0`; KNC: `a3f37b51987a4f5dee7e4e4048c43b80d1955d38`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `7eb405c3d119d4fc84b31f21d6499069fbfedad8`; date: 2026-11-01T21:20:39-05:00.

Conflicts: 2

#### `gcc/config/i386/i386-c.cc`

```diff
<<<<<<< upstream/master
  /* For some of the k6/pentium variants there weren't separate ISA bits to
=======
  if (isa_flag & OPTION_MASK_ISA_KNC)
    {
      def_or_undef (parse_in, "__KNC__");
      def_or_undef (parse_in, "__k1om__");
      def_or_undef (parse_in, "__k1om");
      /* KNC shares generic costs, but has no generic x86 arch macro.  */
      arch = PROCESSOR_max;
    }

  /* For some of the k6/pentium varients there weren't separate ISA bits to
>>>>>>> knc
```

#### `gcc/config/i386/i386-protos.h`

```diff
<<<<<<< upstream/master
extern void ix86_expand_crc_using_pclmul (scalar_mode, scalar_mode, rtx *);
extern void ix86_expand_reversed_crc_using_pclmul (scalar_mode, scalar_mode,
						   rtx *);
=======
extern void ix86_expand_knc_cas (rtx *);
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +44 | -21 |
| `gcc/config.gcc` | +93 | -158 |
| `gcc/config.host` | +10 | -2 |
| `gcc/config/i386/constraints.md` | +6 | -0 |
| `gcc/config/i386/i386-c.cc` | +5 | -3 |
| `gcc/config/i386/i386-expand.cc` | +3390 | -478 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +140 | -91 |
| `gcc/config/i386/i386-protos.h` | +20 | -16 |
| `gcc/config/i386/i386.cc` | +1306 | -448 |
| `gcc/config/i386/i386.h` | +67 | -46 |
| `gcc/config/i386/i386.md` | +2394 | -1445 |
| `gcc/config/i386/i386.opt` | +19 | -6 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +1929 | -163 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/configure` | +1043 | -920 |
| `gcc/configure.ac` | +367 | -378 |
| `libgcc/config.host` | +13 | -23 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |

### x86 handoff to S3-11 (not executed in S3-12)

From the ticket worktree, with the shared toolchain's `cross/bin` and
`cygwin/bin` on PATH, use its Cygwin Python:

```sh
python3 tools/run.py --name S3-11-x86 -- python3 tools/portability.py x86 --tree releases/gcc-16.2.0 --tree knc
```

Do not supply `--inputs` here: the GCC refs are external to this worktree and can
change independently of the tool. Exit status is 0 for identical assembly or
matching failures, 1 for differences, and 2 for tool/infrastructure errors.
Both compilers always run for each file. Each option set reports identical,
different, both-failed and error counts. Both-failed means both compilations
failed with identical diagnostics and is neutral for the exit status. One-sided
failures or different failure diagnostics count as different, with both sides'
diagnostics printed. Successful assembly differences include unified diffs.

The default torture option is `-w` (from `gcc/testsuite/lib/c-torture.exp` and
`gcc/testsuite/gcc.c-torture/compile/compile.exp`). The tool also preserves the
unconditional `-std=...`, `-fpermissive` and `-fno-permissive` options in each
file's `dg-options`/`dg-additional-options` directives, as used by `gcc-dg.exp`.
It prints the default and each file's dialect options. Other DejaGNU directives
and target selectors are outside this fixed assembly comparison.

With `S` denoting the absolute Cygwin path to `.work/_shared`, the tool first
checks `tasklist.exe /FI 'IMAGENAME eq make.exe' /FO CSV /NH`. It resolves both
tree commits, then would run these commands (no fetch):

```sh
git -c core.autocrlf=false -c core.fileMode=false -C "$S/gcc" worktree add --detach "$S/portability/x86-a/source" releases/gcc-16.2.0
git -c core.autocrlf=false -c core.fileMode=false -C "$S/gcc" worktree add --detach "$S/portability/x86-b/source" knc
# In each $S/portability/x86-{a,b}/build directory:
bash ../source/configure --build=x86_64-pc-cygwin --host=x86_64-pc-cygwin --target=x86_64-pc-cygwin --enable-languages=c --disable-bootstrap --disable-multilib --disable-nls --without-isl
make -j8 all-gcc 'CFLAGS=-O2 -g1' 'CXXFLAGS=-O2 -g1'
# For every $S/gcc/gcc/testsuite/gcc.c-torture/compile/**/*.c, with both cc1s:
# dialect_options is the array of that file's unconditional dialect options.
"$S/portability/x86-a/build/gcc/cc1.exe" -quiet -w -O2 "${dialect_options[@]}" "$file" -o "$temporary/a.s"
"$S/portability/x86-b/build/gcc/cc1.exe" -quiet -w -O2 "${dialect_options[@]}" "$file" -o "$temporary/b.s"
"$S/portability/x86-a/build/gcc/cc1.exe" -quiet -w -O2 -mavx512f "${dialect_options[@]}" "$file" -o "$temporary/a.s"
"$S/portability/x86-b/build/gcc/cc1.exe" -quiet -w -O2 -mavx512f "${dialect_options[@]}" "$file" -o "$temporary/b.s"
```

### upstream/releases/gcc-16

Commit: `eafaaddd92e971ab059c6bfa9b8bd93baeb16d19`; date: 2026-11-02T00:20:15Z.

Conflicts: 0

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +3 | -1 |
| `gcc/config.gcc` | +0 | -0 |
| `gcc/config.host` | +0 | -0 |
| `gcc/config/i386/constraints.md` | +0 | -0 |
| `gcc/config/i386/i386-c.cc` | +0 | -0 |
| `gcc/config/i386/i386-expand.cc` | +23 | -10 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +0 | -0 |
| `gcc/config/i386/i386-protos.h` | +0 | -0 |
| `gcc/config/i386/i386.cc` | +34 | -46 |
| `gcc/config/i386/i386.h` | +0 | -0 |
| `gcc/config/i386/i386.md` | +73 | -28 |
| `gcc/config/i386/i386.opt` | +0 | -0 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |

## 2026-11-03T23:34:32+00:00

Base: `releases/gcc-16.2.0`; KNC: `e96ad3079588b83c5484dd98760e9a39a4a94af8`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 2

#### `gcc/config/i386/i386-c.cc`

```diff
<<<<<<< upstream/master
  /* For some of the k6/pentium variants there weren't separate ISA bits to
=======
  if (isa_flag & OPTION_MASK_ISA_KNC)
    {
      def_or_undef (parse_in, "__KNC__");
      def_or_undef (parse_in, "__k1om__");
      def_or_undef (parse_in, "__k1om");
      /* KNC shares generic costs, but has no generic x86 arch macro.  */
      arch = PROCESSOR_max;
    }

  /* For some of the k6/pentium varients there weren't separate ISA bits to
>>>>>>> knc
```

#### `gcc/config/i386/i386-protos.h`

```diff
<<<<<<< upstream/master
extern void ix86_expand_crc_using_pclmul (scalar_mode, scalar_mode, rtx *);
extern void ix86_expand_reversed_crc_using_pclmul (scalar_mode, scalar_mode,
						   rtx *);
=======
extern void ix86_expand_knc_cas (rtx *);
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +67 | -22 |
| `gcc/config.gcc` | +93 | -158 |
| `gcc/config.host` | +10 | -2 |
| `gcc/config/i386/constraints.md` | +6 | -0 |
| `gcc/config/i386/i386-c.cc` | +10 | -5 |
| `gcc/config/i386/i386-expand.cc` | +3463 | -508 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +142 | -91 |
| `gcc/config/i386/i386-protos.h` | +21 | -16 |
| `gcc/config/i386/i386.cc` | +1369 | -459 |
| `gcc/config/i386/i386.h` | +70 | -48 |
| `gcc/config/i386/i386.md` | +2401 | -1450 |
| `gcc/config/i386/i386.opt` | +24 | -6 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +2036 | -286 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/configure` | +1043 | -920 |
| `gcc/configure.ac` | +367 | -378 |
| `libgcc/config.host` | +13 | -23 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |

### upstream/releases/gcc-16

Commit: `4b03dde2e3ad210db469ee763194c0cbec22cf45`; date: 2026-11-03T10:43:47+01:00.

Conflicts: 0

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +3 | -1 |
| `gcc/config.gcc` | +0 | -0 |
| `gcc/config.host` | +0 | -0 |
| `gcc/config/i386/constraints.md` | +0 | -0 |
| `gcc/config/i386/i386-c.cc` | +0 | -0 |
| `gcc/config/i386/i386-expand.cc` | +23 | -10 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +0 | -0 |
| `gcc/config/i386/i386-protos.h` | +0 | -0 |
| `gcc/config/i386/i386.cc` | +35 | -47 |
| `gcc/config/i386/i386.h` | +0 | -0 |
| `gcc/config/i386/i386.md` | +73 | -28 |
| `gcc/config/i386/i386.opt` | +0 | -0 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |

## 2026-11-04T02:55:05+00:00

Base: `releases/gcc-16.2.0`; KNC: `c4a350644aabe7f6aea7277b01225744e1a1b458`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 1

#### `gcc/config/i386/i386-c.cc`

```diff
<<<<<<< upstream/master
  /* For some of the k6/pentium variants there weren't separate ISA bits to
=======
  if (isa_flag & OPTION_MASK_ISA_KNC)
    arch = ix86_knc_target_macros (parse_in, def_or_undef);

  /* For some of the k6/pentium varients there weren't separate ISA bits to
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +67 | -22 |
| `gcc/config.gcc` | +93 | -158 |
| `gcc/config.host` | +10 | -2 |
| `gcc/config/i386/i386-c.cc` | +10 | -5 |
| `gcc/config/i386/i386-expand.cc` | +3463 | -508 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +142 | -91 |
| `gcc/config/i386/i386-protos.h` | +21 | -16 |
| `gcc/config/i386/i386.cc` | +1369 | -459 |
| `gcc/config/i386/i386.h` | +70 | -48 |
| `gcc/config/i386/i386.md` | +2401 | -1450 |
| `gcc/config/i386/i386.opt` | +24 | -6 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +2036 | -286 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/configure` | +1043 | -920 |
| `gcc/configure.ac` | +367 | -378 |
| `libgcc/config.host` | +13 | -23 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |

### upstream/releases/gcc-16

Commit: `4b03dde2e3ad210db469ee763194c0cbec22cf45`; date: 2026-11-03T10:43:47+01:00.

Conflicts: 0

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +3 | -1 |
| `gcc/config.gcc` | +0 | -0 |
| `gcc/config.host` | +0 | -0 |
| `gcc/config/i386/i386-c.cc` | +0 | -0 |
| `gcc/config/i386/i386-expand.cc` | +23 | -10 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +0 | -0 |
| `gcc/config/i386/i386-protos.h` | +0 | -0 |
| `gcc/config/i386/i386.cc` | +35 | -47 |
| `gcc/config/i386/i386.h` | +0 | -0 |
| `gcc/config/i386/i386.md` | +73 | -28 |
| `gcc/config/i386/i386.opt` | +0 | -0 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |

## 2026-11-04T06:05:50+00:00

Base: `releases/gcc-16.2.0`; KNC: `eb8fb3e902a91e885354edac02f5edb7751100de`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 4

#### `gcc/config/i386/i386-c.cc`

```diff
<<<<<<< upstream/master
  /* For some of the k6/pentium variants there weren't separate ISA bits to
=======
  if (isa_flag & OPTION_MASK_ISA_KNC)
    arch = ix86_knc_target_macros (parse_in, def_or_undef);

  /* For some of the k6/pentium varients there weren't separate ISA bits to
>>>>>>> knc
```

#### `gcc/config/i386/i386.cc`

```diff
<<<<<<< upstream/master
=======
  if (TARGET_KNC && !ix86_knc_check_abi_type (arg.type, arg.mode))
    return true;
  CUMULATIVE_ARGS *cum = get_cumulative_args (cum_v);

>>>>>>> knc
```

#### `gcc/configure`

```diff
<<<<<<< upstream/master
  i?86-*-* | x86_64-*-*)
    if test x$as_flavor = xsolaris; then
      tls_section_flag=t
=======
  i?86-*-* | x86_64-*-* | k1om-*-linux*)
    case "$target:$gas" in
      i?86-*-solaris2*:no | x86_64-*-solaris2*:no)
	tls_section_flag=t
>>>>>>> knc
```

#### `gcc/configure.ac`

```diff
<<<<<<< upstream/master
  i?86-*-* | x86_64-*-*)
    if test x$as_flavor = xsolaris; then
      tls_section_flag=t
=======
  i?86-*-* | x86_64-*-* | k1om-*-linux*)
    case "$target:$gas" in
      i?86-*-solaris2*:no | x86_64-*-solaris2*:no)
	tls_section_flag=t
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +67 | -22 |
| `gcc/config.gcc` | +93 | -158 |
| `gcc/config.host` | +10 | -2 |
| `gcc/config/i386/i386-c.cc` | +10 | -5 |
| `gcc/config/i386/i386-expand.cc` | +3463 | -508 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +142 | -91 |
| `gcc/config/i386/i386-protos.h` | +21 | -16 |
| `gcc/config/i386/i386.cc` | +1369 | -459 |
| `gcc/config/i386/i386.h` | +70 | -48 |
| `gcc/config/i386/i386.md` | +2401 | -1450 |
| `gcc/config/i386/i386.opt` | +24 | -6 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +2036 | -286 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/configure` | +1043 | -920 |
| `gcc/configure.ac` | +367 | -378 |
| `libgcc/config.host` | +13 | -23 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |

### upstream/releases/gcc-16

Commit: `4b03dde2e3ad210db469ee763194c0cbec22cf45`; date: 2026-11-03T10:43:47+01:00.

Conflicts: 0

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +3 | -1 |
| `gcc/config.gcc` | +0 | -0 |
| `gcc/config.host` | +0 | -0 |
| `gcc/config/i386/i386-c.cc` | +0 | -0 |
| `gcc/config/i386/i386-expand.cc` | +23 | -10 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +0 | -0 |
| `gcc/config/i386/i386-protos.h` | +0 | -0 |
| `gcc/config/i386/i386.cc` | +35 | -47 |
| `gcc/config/i386/i386.h` | +0 | -0 |
| `gcc/config/i386/i386.md` | +73 | -28 |
| `gcc/config/i386/i386.opt` | +0 | -0 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |


Trunk build finding (S3-11, KNC `eb8fb3e902a9` onto master `b88c2821e219`): `atomic_storeti` in KNC `imci.md:249` collides with upstream `sync.md:410`; this is a logic conflict, not a textual one. S3-23 integrates the dispatch below.

## S3-23: atomic optab integration

Red baseline: the existing S3-11 trunk tree still fails its target-definition
generator with `sync.md:410:1: duplicate definition of 'atomic_storeti'`.
From `portability/trunk/build/gcc`, run
`build/gentarget-def.exe ../../source/gcc/common.md ../../source/gcc/config/i386/i386.md insn-conditions.md`.
Exit 1, before any source change; log
`.work/_state/logs/S3_23_red-20261104-081007.log`. This reuses the existing
build check; S3-23 adds no tests.

### Resolution recipe

On 16.2, keep both `atomic_storeti` and `atomic_exchangeti` in `imci.md`,
conditioned on `TARGET_KNC`. Each body calls its helper in `i386-knc.cc`
(`ix86_knc_expand_atomic_store` or `ix86_knc_expand_atomic_exchange`) then
`DONE`. The helpers retain the original libatomic calls, operands, result move
and `MEMMODEL_BASE_MASK` filtering. Declare them in `i386-knc.h`.

When rebasing onto upstream `d9e21f7c4d1` or later:

1. Drop only KNC's `atomic_storeti` expander from `imci.md`.
2. In upstream `sync.md`'s `atomic_storeti` **expander**, change its condition
   to `TARGET_128BIT_ATOMIC_ENABLED || TARGET_KNC` and add this entry hook
   before upstream's `enum memmodel model` declaration:

   ```c++
   if (TARGET_KNC)
     {
       ix86_knc_expand_atomic_store (operands);
       DONE;
     }
   ```

The upstream operand numbers still mean memory, value and memory model.
Its `nonimmediate_operand` value accepts the register supplied by generic
atomic expansion; the helper passes the TI argument through the ordinary
libcall machinery. Keep upstream's SSE body and `atomic_storeti_sse`
condition unchanged. This is an entry dispatch and a condition term under
ADR-0006 rules 1 and 2; no SSE instruction pattern is widened.
There is no upstream `atomic_exchangeti` collision on this trunk, so retain
the KNC exchange expander. Its helper gives a future collision the same
single-hook resolution.

### Upstream atomic load check

On master `b88c2821e219`, both `atomic_loadti` and `atomic_loadti_sse`
require `TARGET_128BIT_ATOMIC_ENABLED`, defined in `i386.h` as
`TARGET_CX16 && TARGET_SSE2 && TARGET_128BIT_ATOMIC`. With `-march=knc`,
SSE2 is disabled. Adding `-m128bit-atomic` does **not** enable SSE2, so the
load expander remains unavailable and TI loads retain the libatomic path.
Explicit SSE options are rejected by `ix86_knc_option_override` after ISA
dependency expansion.

One nuance in `i386-options.cc`: `-m128bit-atomic` explicitly enables CX16
later than that KNC option hook, unless `-mno-cx16` was explicit. Thus the
reason the load expander cannot activate with that flag is **SSE2**, not
an assertion that CX16 always remains clear. This late CX16 enablement is
an upstream option interaction to track; S3-23 does not change option
semantics. Do not widen `atomic_loadti` or either SSE insn condition.

### 16.2 refactor evidence

The before compiler is merged KNC `9b6cbb9f4e1`; the after compiler is
S3-23 `2139411dc6c`. Both were built in the existing shared `gcc-build`
with `make -j4 all-gcc CFLAGS='-O2 -g1' CXXFLAGS='-O2 -g1'`, each after
its object precheck. The refactor changes only `i386-knc.cc`,
`i386-knc.h` and `imci.md`; there is no shared i386 code change on 16.2.

`tests/t1/knc-atomics.c -march=knc -S` produces byte-identical assembly
before and after at both `-O0` and `-O2`. The existing
`check.py t1 t2 --compiler gcc16 --atomics` checks also match: capability
macros, atomic libcalls, spin hints, assembler/lint and pthread counter
link all pass. Lock-free queries remain false / a libatomic runtime query.
The counter was linked, not run natively.

Logs in `.work/_state/logs/`:

- `S3_23_baseline_objects-20261104-081042.log` (pass).
- `S3_23_baseline_build-20261104-081207.log` (pass, 13.7 minutes).
- `S3_23_atomics_before-20261104-082611.log` (pass).
- `S3_23_objects-20261104-082651.log` (pass).
- `S3_23_build-20261104-082837.log` (pass, 11.7 minutes).
- `S3_23_atomics_after-20261104-084028.log` (pass, both assembly
  comparisons and identical `tools/atomics.py` results).

The full existing `check.py t1 t2 --compiler gcc16` run at
`2139411dc6c` passes (104.22 seconds), log
`S3_23_gcc16_t1_t2-20261104-084102.log` in the same directory.

### Trunk replay

The existing S3-11 `portability/trunk/source` tree retains its four
recorded resolutions. The intervening `eb8fb3e902a9..9b6cbb9f4e1` KNC
diff applies cleanly to it (six files), followed by S3-23's helper
extraction and the store recipe above. Thus the replay uses upstream
`b88c2821e219244d18df873b0bfb344d3dc0b2a7` with the KNC diff through
`2139411dc6c`, rather than leaving the S3-11 snapshot's KNC fixes behind.
The existing C-only configuration targets `k1om-mpss-linux` and uses
the shared sysroot, assembler and linker. Build invocations are serialized;
`Get-Process make` was empty before each new compiler build.

The trunk object precheck (`i386-knc.o`, `i386.o`, `i386-c.o`) passes,
including the previously failing target-definition generator; log
`S3_23_trunk_objects-20261104-084102.log` in `.work/_state/logs/`.

The first full build, `S3_23_trunk_build-20261104-084307.log`, failed
at four jobs with Cygwin `unable to load user32.dll, Win32 error 8`:
an infrastructure out-of-memory failure, with no source diagnostic.
Following the lead's continuation instruction, no make/compiler process
was running before resuming the same configuration and objects with
`make -j1 all-gcc CFLAGS='-O2 -g1' CXXFLAGS='-O2 -g1'`. This passed in
9.9 minutes, including `insn-output.o`, `insn-emit-6.o`, the `cc1.exe`
link and 7,711,549 C self-test passes. Log:
`S3_23_trunk_build_serial-20261104-092423.log` in `.work/_state/logs/`.

### Trunk T1/T2 comparison and remaining finding

The existing `portability/trunk/wrappers.py` ran the full
`check.py t1 t2 --compiler gcc16` selection once. Its first output confirms
that C uses `portability/trunk/build/gcc/cc1.exe` (GCC 17.0.0,
20261103 experimental), upstream `b88c2821e219244d18df873b0bfb344d3dc0b2a7`
with KNC through `2139411dc6c44e3207c5430304e99b231cbeee2b` and the
store resolution above. Fortran and the target runtime remain the existing
16.2 build; this is a C-only trunk drill. No target program ran on the card.

| Existing result rows | 16.2 at `2139411dc6c` | Trunk with that KNC diff |
| --- | ---: | ---: |
| T1 pass | 222 | 206 |
| T1 fail | 0 | 16 |
| T2 pass | 23 | 23 |
| T2 fail | 0 | 0 |

All 245 row labels and their order match. The only changed results are
`t1 packed ABI <element> <shape> VAR_GET <level>` for every combination of
`float`, `double`, `int`, `long long`; `vector`, `record`; and `-O0`, `-O2`.
They share one cause: an existing ABI rejection error-recovery **logic**
flaw exposed by the checking configuration, not the atomic optab change.
The other 206 T1 rows and all 23 T2 rows have identical results.

In both source trees, `ix86_gimplify_va_arg`'s KNC entry guard diagnoses
`unsupported KNC register ABI mode` and returns `error_mark_node`
(`i386.cc:5009` on trunk). `expand_ifn_va_arg_1` continues after that error
and reaches `gcc_assert (gsi_end_p (i))` at `tree-stdarg.cc:1072`;
each failing backtrace points there. `tree-stdarg.cc` is unchanged between
these two trees. Both builds enable assertion checking, but their
`gcc/auto-host.h` has `CHECKING_P=0` for 16.2 and `CHECKING_P=1` for trunk.
`diagnostics/context.cc:1462-1476` converts an ICE following an earlier
error to `confused by earlier errors, bailing out` when `CHECKING_P=0`.
Thus 16.2's no-ICE diagnostic check passes while trunk reports the assertion
and fails that check. The backtrace's `diagnostic-global-context.cc:787`
is the ICE reporter, not the original ABI failure. This is an error-path
integration finding for follow-up; no structural backend redesign is
demonstrated, and no test was weakened or rerun to hide it.

Compiler-version metadata changes from 16.2.0 to 17.0.0 as expected;
elapsed time changes from 104.22 to 122.11 seconds. The T1/T2 command exits
1 because of the 16 failures; the comparison itself passes. Evidence in
`.work/_state/logs/`:

- `S3_23_trunk_t1_t2-20261104-093427.log` (full run).
- `S3_23_result_comparison-20261104-093743.log` (245 ordered labels,
  counts and all 16 changed results).

The saved records are `.work/_shared/tmp/s3-23-gcc16.txt` and
`.work/_shared/tmp/s3-23-trunk.txt`; these are result comparisons, not
an assembly-equality claim for the full suites.
