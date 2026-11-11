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
## 2026-11-05T00:20:07+00:00

Base: `releases/gcc-16.2.0`; KNC: `ae8a033c5f3a544c092478ff7269f366e828ee81`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 5

#### `gcc/config/i386/i386-c.cc`

```diff
<<<<<<< upstream/master
  /* For some of the k6/pentium variants there weren't separate ISA bits to
=======
  if (isa_flag & OPTION_MASK_ISA_KNC)
    arch = ix86_knc_target_macros (parse_in, def_or_undef);

  /* For some of the k6/pentium varients there weren't separate ISA bits to
>>>>>>> ae8a033c5f3
```

#### `gcc/config/i386/i386.cc`

```diff
<<<<<<< upstream/master
=======
  if (TARGET_KNC && !ix86_knc_check_abi_type (arg.type, arg.mode))
    return true;
  CUMULATIVE_ARGS *cum = get_cumulative_args (cum_v);

>>>>>>> ae8a033c5f3
```

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* ADR-0007 point 7: KNC masked accesses are 64-byte aligned only.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost *= 1000;
>>>>>>> ae8a033c5f3
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

  ix86_fixup_binary_operands_no_copy (<CODE>, <MODE>mode, operands);
})
=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
  "ix86_fixup_binary_operands_no_copy (<CODE>, <MODE>mode, operands);")
>>>>>>> ae8a033c5f3
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
>>>>>>> ae8a033c5f3
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
>>>>>>> ae8a033c5f3
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

### S4-06 classification (KNC `ae8a033c5f3`)

`upstream/releases/gcc-16` (`4b03dde2e3a`): 0 conflicts. `upstream/master`
(`b88c2821e21`): 5 files, 6 hunks; log `.work/_state/logs/S4_06_drill-20261104-192007.log`.

| File | Kind | Reason |
| --- | --- | --- |
| `i386-c.cc` | textual | Upstream fixed the "varients" typo in the comment line right after the KNC macro hook. |
| `i386.cc` (pass_by_reference) | textual | Upstream split the body into `ix86_pass_by_reference_abi`; the KNC guard moves into the `cum_v` wrapper. Upstream va_arg calls `_abi` directly, but KNC's va_arg entry guard already rejects first. |
| `i386.cc` (add_stmt_cost, new from S4-03) | textual | Upstream moved the `stmt_cost == -1` default line up into its restructured block; the ADR-0007 point 7 term re-anchors after it. |
| `sse.md` (plusminus expander, new; S3-09 widening) | logic | Upstream changed operand 2 to `vector_or_const_vector_operand` and added the +1 to -1 rewrite and constant `force_reg`; with `VI_AVX2_KNC` these now run for V16SI/V8DI on KNC and need a KNC check (constant move and inverse op). |
| `configure`, `configure.ac` | textual | Upstream replaced the Solaris `case "$target:$gas"` body with an `as_flavor` test; keep `k1om-*-linux*` in the label. |

## 2026-11-05T04:45:24+00:00

Base: `releases/gcc-16.2.0`; KNC: `c759f17f1b98c4ecc0664b50ffc1d7434fbeef58`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 5

#### `gcc/config/i386/i386-c.cc`

```diff
<<<<<<< upstream/master
  /* For some of the k6/pentium variants there weren't separate ISA bits to
=======
  if (isa_flag & OPTION_MASK_ISA_KNC)
    arch = ix86_knc_target_macros (parse_in, def_or_undef);

  /* For some of the k6/pentium varients there weren't separate ISA bits to
>>>>>>> c759f17f1b9
```

#### `gcc/config/i386/i386.cc`

```diff
<<<<<<< upstream/master
=======
  if (TARGET_KNC && !ix86_knc_check_abi_type (arg.type, arg.mode))
    return true;
  CUMULATIVE_ARGS *cum = get_cumulative_args (cum_v);

>>>>>>> c759f17f1b9
```

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* ADR-0007 point 7: KNC masked accesses are 64-byte aligned only.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost *= 1000;
>>>>>>> c759f17f1b9
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
  ix86_expand_cond_fma (operands, false, false);
=======
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_cond_fma (<MODE>mode, operands[0], operands[1],
				   operands[2], operands[3], operands[4],
				   operands[5]));
      DONE;
    }
  rtx tmp = gen_reg_rtx (<MODE>mode);
  emit_insn (gen_fma<mode>4 (tmp,
			     operands[2],
			     operands[3],
			     operands[4]));
  emit_move_insn (operands[0], gen_rtx_VEC_MERGE (<MODE>mode,
						  tmp,
						  operands[5],
						  operands[1]));
>>>>>>> c759f17f1b9
```

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
{
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_plusminus (<CODE>, <MODE>mode, operands[0],
				    operands[1], operands[2]));
      DONE;
    }
>>>>>>> c759f17f1b9
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
>>>>>>> c759f17f1b9
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
>>>>>>> c759f17f1b9
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


### S4-07 classification (KNC `c759f17f1b9`)

`upstream/releases/gcc-16` (`4b03dde2e3a`): 0 conflicts. `upstream/master`
(`b88c2821e21`): 5 files, 7 hunks, all textual; log `.work/_state/logs/S4_07_drill-20261104-234522.log`.

| File | Kind | Reason |
| --- | --- | --- |
| `i386-c.cc` | textual | Upstream fixed the "varients" typo in the comment line right after the KNC macro hook. |
| `i386.cc` (pass_by_reference) | textual | As S4-06: the KNC guard moves into the `cum_v` wrapper; KNC's va_arg entry guard covers the direct `_abi` call. |
| `i386.cc` (add_stmt_cost, S4-03) | textual | As S4-06: the ADR-0007 point 7 term re-anchors after upstream's moved `stmt_cost == -1` default line. |
| `sse.md` (cond_fma, new from S4-05) | textual | Upstream `18d2e513be7` replaced the body with `ix86_expand_cond_fma (operands, false, false)` and kept the iterator and `TARGET_AVX512F` condition; keep the KNC condition term and the entry dispatch to `@knc_cond_fma` (DONE) ahead of the new call, which KNC never reaches. |
| `sse.md` (plusminus expander) | textual (was logic in S4-06) | S4-04's entry dispatch runs first under KNC; taking upstream's `vector_or_const_vector_operand` for operand 2 is safe because `@knc_plusminus` sends constants to registers (`ix86_knc_fixup_binary_operands`), and the +1 to -1 rewrite and `force_reg` sit after the dispatch. |
| `configure`, `configure.ac` | textual | Upstream replaced the Solaris `case "$target:$gas"` body with an `as_flavor` test; keep `k1om-*-linux*` in the label. |

Clean-merging S4-05 hunks checked by hand: upstream has not changed the finish_cost
masked-epilogue condition (the `TARGET_KNC && ix86_knc_masked_epilogue_p` term stays beside
`X86_TUNE_AVX512_MASKED_EPILOGUES`) or the FP `cond_mul` body that `VFH_KNC` now reaches.
## 2026-11-05T19:33:44+00:00

Base: `releases/gcc-16.2.0`; KNC: `9690ac8906a6457c177dcce94b3f09f76ba994ec`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 5

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

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* ADR-0007 point 7: KNC masked accesses are 64-byte aligned only.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost *= 1000;
  /* ADR-0008 point 1: a two-input KNC permute is vpermd plus vpermd.  */
  if (TARGET_KNC && kind == vec_perm
      && ix86_knc_two_input_perm_p (mode, stmt_info, node))
    stmt_cost *= 2;
>>>>>>> knc
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
  ix86_expand_cond_fma (operands, false, false);
=======
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_cond_fma (<MODE>mode, operands[0], operands[1],
				   operands[2], operands[3], operands[4],
				   operands[5]));
      DONE;
    }
  rtx tmp = gen_reg_rtx (<MODE>mode);
  emit_insn (gen_fma<mode>4 (tmp,
			     operands[2],
			     operands[3],
			     operands[4]));
  emit_move_insn (operands[0], gen_rtx_VEC_MERGE (<MODE>mode,
						  tmp,
						  operands[5],
						  operands[1]));
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
{
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_plusminus (<CODE>, <MODE>mode, operands[0],
				    operands[1], operands[2]));
      DONE;
    }
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


### S5-17 classification and change size (KNC `9690ac8906a`)

The drill above used local upstream refs: master `b88c2821e21` has five
conflicted files and seven textual hunks; release `4b03dde2e3a` has zero
conflicts. No structural or design conflict was found.
Drill log: `.work/_state/logs/S5_17_drill-20261105-143344.log`.

| Conflict | Resolution |
| --- | --- |
| `i386-c.cc` | Keep upstream's spelling correction and insert the KNC macro hook before the comment. |
| `i386.cc`, pass by reference | Keep the KNC ABI guard in the new `cum_v` wrapper. The existing KNC `va_arg` guard covers the direct ABI helper path. |
| `i386.cc`, statement cost | Re-anchor the KNC alignment penalty and two-input permute cost after upstream's moved default-cost assignment. The two penalties retain their separate predicates. |
| `sse.md`, conditional FMA | Keep the KNC condition and entry dispatch before upstream's `ix86_expand_cond_fma` call. The KNC dispatch emits its instruction and finishes expansion. |
| `sse.md`, plus/minus | Retain the KNC iterator, condition and entry dispatch. Take upstream's constant-capable operand and its rewrite after that dispatch; the KNC binary-operand helper already forces constants to registers. |
| `configure`, `configure.ac` | Retain the KNC target label with upstream's Solaris `as_flavor` test. |

Change-size measurement from this ticket's initial run, against
`releases/gcc-16.2.0`: additions plus deletions in `gcc/config/i386` and
`gcc/common/config/i386`, excluding the four KNC-only files below; hunks use
Git's default three-line context.

| Scope | Changed lines | Hunks |
| --- | ---: | ---: |
| Shared i386 files | 381 | 85 |
| `i386-knc.cc` (KNC only) | 1013 | 1 |
| `i386-knc.h` (KNC only) | 84 | 1 |
| `imci.md` (KNC only) | 1363 | 1 |
| `linux-k1om.h` (KNC only) | 72 | 1 |
| KNC-only total | 2532 | 4 |

The x86 identity check is assigned to the lead by the S5-17 ticket answer.
The lead also runs the full execute suite, `s4_masks` and `s5_ops` on the card
after merge; this ticket does not claim native execution results.

### S5-17 ICE sweeps

At KNC `9690ac8906a`, the existing `tools/torture_compile.py` runner compiled
all 2,003 C torture compile cases at each requested flag set. Its `LEVELS`
table was set in memory to `O2: [-O2, -ftree-vectorize]` and `O3: [-O3]`;
all other classification, directive, assembler, lint and timeout behavior
was unchanged. Four workers completed 4,006 measurements in 772.530 seconds.

| Flags (also `-march=knc`) | Pass | Compiler error | User inline asm rejected | ICE | Hang | Assembler rejection | Lint failure | Infrastructure failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `-O2 -ftree-vectorize` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |
| `-O3` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |

The wrapper returned PASS (exit 0). Neither level had a slow retry or an FP
ABI error. Compiler errors and rejected user inline asm remain reported
separately from successful cases.

Log: `.work/_state/logs/S5_17_sweep-20261105-143722.log`.
Classification summary and detailed failures:
`.work/_shared/tmp/S5-17-sweep/summary.txt` and its containing directory.
## 2026-11-06T07:38:27+00:00

Base: `releases/gcc-16.2.0`; KNC: `656cb9ef09634a398121a115fe9e38902c75f2fe`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 5

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

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* ADR-0007 point 7: KNC masked accesses are 64-byte aligned only.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost *= 1000;
  /* ADR-0008 point 1: a two-input KNC permute is vpermd plus vpermd.  */
  if (TARGET_KNC && kind == vec_perm
      && ix86_knc_two_input_perm_p (mode, stmt_info, node))
    stmt_cost *= 2;
>>>>>>> knc
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
  ix86_expand_cond_fma (operands, false, false);
=======
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_cond_fma (<MODE>mode, operands[0], operands[1],
				   operands[2], operands[3], operands[4],
				   operands[5]));
      DONE;
    }
  rtx tmp = gen_reg_rtx (<MODE>mode);
  emit_insn (gen_fma<mode>4 (tmp,
			     operands[2],
			     operands[3],
			     operands[4]));
  emit_move_insn (operands[0], gen_rtx_VEC_MERGE (<MODE>mode,
						  tmp,
						  operands[5],
						  operands[1]));
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
{
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_plusminus (<CODE>, <MODE>mode, operands[0],
				    operands[1], operands[2]));
      DONE;
    }
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
| `gcc/config/i386/i386-builtins.cc` | +45 | -5 |
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
| `gcc/config/i386/i386-builtins.cc` | +0 | -0 |
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


### S5-18 classification and change size (KNC `656cb9ef096`)

The local upstream master `b88c2821e21` has five conflicted files and
seven textual hunks. The release branch `4b03dde2e3a` has no conflicts.
No structural or logic conflict was found; the resolutions below preserve
both the upstream change and KNC's existing entry hooks and predicates.

| Conflict | Textual resolution |
| --- | --- |
| `i386-c.cc` (1 hunk) | Keep upstream's spelling correction and the KNC macro hook before the comment. |
| `i386.cc`, pass by reference (1 hunk) | Keep the KNC ABI guard at entry to upstream's `cum_v` wrapper; keep upstream's moved helper and the existing KNC `va_arg` guard. |
| `i386.cc`, statement cost (1 hunk) | Re-anchor the KNC alignment and two-input permute penalties after upstream's moved default-cost assignment, retaining each predicate. |
| `sse.md`, conditional FMA (1 hunk) | Retain the KNC condition and entry dispatch before upstream's `ix86_expand_cond_fma`; the KNC branch finishes expansion. |
| `sse.md`, plus/minus (1 hunk) | Keep the KNC iterator, condition and entry dispatch, and take upstream's constant-capable operand and rewrite after that dispatch. The KNC expander calls `ix86_knc_fixup_binary_operands` before emitting the operation. |
| `configure`, `configure.ac` (1 hunk each) | Retain the KNC target label with upstream's Solaris `as_flavor` test. |

Drill log: `.work/_state/logs/S5_18_drill-20261106-023827.log`.

Change size against `releases/gcc-16.2.0`: additions plus deletions under
`gcc/config/i386` and `gcc/common/config/i386`, excluding the four KNC-only
files below. Hunks use Git's default three-line context.

| Scope | Changed lines | Hunks |
| --- | ---: | ---: |
| Shared i386 files | 546 | 107 |
| `i386-knc.cc` (KNC only) | 1466 | 1 |
| `i386-knc.h` (KNC only) | 99 | 1 |
| `imci.md` (KNC only) | 1860 | 1 |
| `linux-k1om.h` (KNC only) | 72 | 1 |
| KNC-only total | 3497 | 4 |

The shared build wrapper skipped its build because the clean source tree
was already built (build stamp commit `e1112842e87`, same tree as the merge
head). Log: `.work/_state/logs/S5_18_build-20261106-023807.log`.

The S5-18 ticket assigns the x86 identity check at `-O2` and
`-O2 -mavx512f` in `portability-claude` to the lead. Those results are pending.
After merge the lead also runs the full execute suite, `s4_masks`, `s5_ops`,
and S5-16's `knc-byte-guard.mic --native` on the card. No native execution
result is claimed here.

### S5-18 ICE sweeps

The existing `tools/torture_compile.py` runner compiled all 2,003 C torture
compile cases at each requested flag set. Its `LEVELS` table was set in
memory to `O2: [-O2, -ftree-vectorize]` and `O3: [-O3]`; directive handling,
classification, assembly, lint and timeout behavior remained unchanged.
Four workers completed 4,006 measurements in 603.116 seconds. The wrapper
returned PASS (exit 0).

| Flags (also `-march=knc`) | Pass | Compiler error | User inline asm rejected | ICE | Hang | Assembler rejection | Lint failure | Infrastructure failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `-O2 -ftree-vectorize` | 1967 | 34 | 2 | 0 | 0 | 0 | 0 | 0 |
| `-O3` | 1967 | 34 | 2 | 0 | 0 | 0 | 0 | 0 |

Neither level had a slow retry or an FP ABI error. Compared with S5-17's
classification summary, `pr70240.c` is the one additional compiler-error
case at both levels: line 8 receives `unsupported KNC register ABI mode`.
This diagnostic is reported as a compiler error, not a successful compile
or an ICE. No compiler change was made in this check ticket.

Log: `.work/_state/logs/S5_18_sweep-20261106-023923.log`.
Summary: `.work/_shared/S5-18/sweep/summary.txt`.
Detailed failure logs are beside that summary, including
`O2/pr70240.c.log` and `O3/pr70240.c.log`.
## 2026-11-07T11:47:02+00:00

Base: `releases/gcc-16.2.0`; KNC: `57bec527e002086375881870c44a664542b3bb53`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 7

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

#### `gcc/config/i386/i386-options.cc`

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
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

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* Only gather/scatter needs statement-specific KNC costs here.  Other
     KNC defaults have already received the x86 lowering adjustments.  */
  if (TARGET_KNC
      && (kind == vector_gather_load || kind == vector_scatter_store))
    {
      int cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
      if (cost >= 0)
        stmt_cost = cost;
    }
  /* ADR-0007 point 7: KNC masked accesses are 64-byte aligned only.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost *= 1000;
  /* ADR-0008 point 1: a two-input KNC permute is vpermd plus vpermd.  */
  if (TARGET_KNC && kind == vec_perm
      && ix86_knc_two_input_perm_p (mode, stmt_info, node))
    stmt_cost *= 2;
>>>>>>> knc
```

#### `gcc/config/i386/i386.opt`

```diff
<<<<<<< upstream/master
mavx10v2aux
Target Mask(ISA2_AVX10V2AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V2AUX built-in functions and code generation.

macev1
Target Mask(ISA2_ACEV1) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and ACEV1 built-in functions and code generation.

mavx10v1aux
Target Mask(ISA2_AVX10V1AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V1AUX built-in functions and code generation.
=======
-param=knc-threads-per-core=
Target Joined UInteger Var(knc_threads_per_core) Init(4) IntegerRange(1, 4) Param Optimization
Assumed active KNC threads per core for latency hiding (1 to 4, default 4).
>>>>>>> knc
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
  ix86_expand_cond_fma (operands, false, false);
=======
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_cond_fma (<MODE>mode, operands[0], operands[1],
				   operands[2], operands[3], operands[4],
				   operands[5]));
      DONE;
    }
  rtx tmp = gen_reg_rtx (<MODE>mode);
  emit_insn (gen_fma<mode>4 (tmp,
			     operands[2],
			     operands[3],
			     operands[4]));
  emit_move_insn (operands[0], gen_rtx_VEC_MERGE (<MODE>mode,
						  tmp,
						  operands[5],
						  operands[1]));
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
{
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_plusminus (<CODE>, <MODE>mode, operands[0],
				    operands[1], operands[2]));
      DONE;
    }
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
| `gcc/config/i386/i386-builtins.cc` | +45 | -5 |
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
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +2036 | -286 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +1 | -1 |
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
| `gcc/config/i386/i386-builtins.cc` | +0 | -0 |
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
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |


### S6-08 classification and change size (KNC `57bec527e002`)

The drill used local refs only: upstream master `b88c2821e219` has seven
conflicted files and ten textual hunks; gcc-16 `4b03dde2e3ad` has no conflicts.
Every conflict has a textual resolution; no structural conflict was found.

| Conflict | Textual resolution |
| --- | --- |
| `i386-c.cc` (1 hunk) | Retain the KNC macro hook and upstream's spelling correction. |
| `i386-options.cc` (2 hunks) | Retain the `ix86_knc_tune_cost` wrapper at both assignments and upstream's comment spelling. |
| `i386.cc`, pass by reference (1 hunk) | Retain the KNC ABI entry guard in upstream's `cum_v` wrapper; keep upstream's relocated helper and the existing KNC `va_arg` guard. |
| `i386.cc`, statement cost (1 hunk) | Retain upstream's moved default-cost assignment, then the KNC gather/scatter override and alignment/permute penalties, each with its existing predicate. Preserve upstream's surrounding block structure. |
| `i386.opt` (1 hunk) | Keep both upstream's new AVX option entries and the independent KNC threads-per-core parameter entry. |
| `sse.md`, conditional FMA (1 hunk) | Retain the KNC entry dispatch, which finishes expansion, then upstream's `ix86_expand_cond_fma` call for the remaining targets. |
| `sse.md`, plus/minus (1 hunk) | Retain the KNC iterator, condition and entry dispatch; take upstream's constant-capable operand and rewrite after the dispatch. KNC's binary-operand helper forces constants to registers. |
| `configure`, `configure.ac` (1 hunk each) | Retain the KNC target label together with upstream's Solaris `as_flavor` test. |

Drill log: `.work/_state/logs/S6_08_drill-20261107-064701.log`.

Change size against `releases/gcc-16.2.0`: additions plus deletions under
`gcc/config/i386` and `gcc/common/config/i386`, excluding the five KNC-only
files below. Hunks use Git's default three-line context. The new KNC-only
scheduler file is excluded from the shared count, just like `imci.md`.

| Scope | Changed lines | Hunks |
| --- | ---: | ---: |
| Shared i386 files | 644 | 122 |
| `i386-knc.cc` (KNC only) | 1733 | 1 |
| `i386-knc.h` (KNC only) | 104 | 1 |
| `imci.md` (KNC only) | 1978 | 1 |
| `knc.md` (KNC only) | 94 | 1 |
| `linux-k1om.h` (KNC only) | 72 | 1 |
| KNC-only i386 total | 3981 | 5 |

Outside that i386 measurement scope, KNC-only libgcc files contain 37 lines
in `knc-crtfastmath.c`, 13 in `knc-sfp-machine.h`, and 17 in `t-knc`.

The shared build wrapper skipped the build: the clean tree
`ebd0bda6940ccb3e1832d3e0d77d1938310a1ba4` was already built at
`c192fef7e7d3bd207e90867c767cfd4dec7d4db4` (same tree as the checked head).
Build log: `.work/_state/logs/S6_08_build-20261107-064642.log`.

The S6-08 ticket assigns x86 identity and card execution to the lead.
Those results must be recorded on the ticket before approval. No native
execution result is claimed by this engineer report.

### S6-08 ICE sweeps

At KNC `57bec527e002`, `tools/torture_compile.py` compiled all 2,003 C torture
compile cases at each requested flag set. Its `LEVELS` table was set in memory
to `O2: [-O2, -ftree-vectorize]` and `O3: [-O3]`; all directive handling,
classification, assembly, lint and timeout behavior remained unchanged.
Four workers completed 4,006 measurements in 447.429 seconds. The wrapper
returned PASS (exit 0).

| Flags (also `-march=knc`) | Pass | Compiler error | User inline asm rejected | ICE | Hang | Assembler rejection | Lint failure | Infrastructure failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `-O2 -ftree-vectorize` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |
| `-O3` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |

Neither level had a slow retry or an FP ABI error. Compiler errors and
rejected user inline assembly are reported separately from passing cases.

Log: `.work/_state/logs/S6_08_sweep-20261107-064705.log`.
Summary: `.work/_shared/S6-08/sweep/summary.txt`.
Detailed failure logs are beside that summary. The small sweep launcher is
`.work/_shared/S6-08/sweep.py`.

## 2026-11-08T07:42:55+00:00

Base: `releases/gcc-16.2.0`; KNC: `497bbe8bedf0e3855d4779e6e8f468bf706ee681`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 8

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

#### `gcc/config/i386/i386-options.cc`

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
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

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* Only gather/scatter needs statement-specific KNC costs here.  Other
     KNC defaults have already received the x86 lowering adjustments.  */
  if (TARGET_KNC
      && (kind == vector_gather_load || kind == vector_scatter_store))
    {
      int cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
      if (cost >= 0)
        stmt_cost = cost;
    }
  /* ADR-0007 point 7: KNC masked accesses are 64-byte aligned only.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost *= 1000;
  /* ADR-0008 point 1: a two-input KNC permute is vpermd plus vpermd.  */
  if (TARGET_KNC && kind == vec_perm
      && ix86_knc_two_input_perm_p (mode, stmt_info, node))
    stmt_cost *= 2;
>>>>>>> knc
```

#### `gcc/config/i386/i386.opt`

```diff
<<<<<<< upstream/master
mavx10v2aux
Target Mask(ISA2_AVX10V2AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V2AUX built-in functions and code generation.

macev1
Target Mask(ISA2_ACEV1) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and ACEV1 built-in functions and code generation.

mavx10v1aux
Target Mask(ISA2_AVX10V1AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V1AUX built-in functions and code generation.
=======
-param=knc-threads-per-core=
Target Joined UInteger Var(knc_threads_per_core) Init(4) IntegerRange(1, 4) Param Optimization
Assumed active KNC threads per core for latency hiding (1 to 4, default 4).
>>>>>>> knc
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
  ix86_expand_cond_fma (operands, false, false);
=======
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_cond_fma (<MODE>mode, operands[0], operands[1],
				   operands[2], operands[3], operands[4],
				   operands[5]));
      DONE;
    }
  rtx tmp = gen_reg_rtx (<MODE>mode);
  emit_insn (gen_fma<mode>4 (tmp,
			     operands[2],
			     operands[3],
			     operands[4]));
  emit_move_insn (operands[0], gen_rtx_VEC_MERGE (<MODE>mode,
						  tmp,
						  operands[5],
						  operands[1]));
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
{
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_plusminus (<CODE>, <MODE>mode, operands[0],
				    operands[1], operands[2]));
      DONE;
    }
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

#### `libgfortran/configure`

```diff
<<<<<<< upstream/master
#line 13245 "configure"
=======
#line 13250 "configure"
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 13351 "configure"
=======
#line 13356 "configure"
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +67 | -22 |
| `gcc/config.gcc` | +93 | -158 |
| `gcc/config.host` | +10 | -2 |
| `gcc/config/i386/i386-builtins.cc` | +45 | -5 |
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
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +2036 | -286 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +1 | -1 |
| `gcc/configure` | +1043 | -920 |
| `gcc/configure.ac` | +367 | -378 |
| `libgcc/config.host` | +13 | -23 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +2 | -1 |
| `libgfortran/Makefile.in` | +7 | -2 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +142 | -16 |
| `libgfortran/configure.ac` | +14 | -4 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |

### upstream/releases/gcc-16

Commit: `4b03dde2e3ad210db469ee763194c0cbec22cf45`; date: 2026-11-03T10:43:47+01:00.

Conflicts: 0

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +3 | -1 |
| `gcc/config.gcc` | +0 | -0 |
| `gcc/config.host` | +0 | -0 |
| `gcc/config/i386/i386-builtins.cc` | +0 | -0 |
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
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +0 | -0 |
| `libgfortran/Makefile.in` | +0 | -0 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +0 | -0 |
| `libgfortran/configure.ac` | +0 | -0 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |


### S7-10 classification and change size (KNC `497bbe8bedf0`)

The drill used local refs only: upstream master `b88c2821e219` has eight
conflicted files and twelve hunks; gcc-16 `4b03dde2e3ad` has no conflicts.
Every conflict has a textual resolution; no structural conflict was found.
The seven files and ten hunks from S6-08 are unchanged and resolve as recorded
there. The new one:

| Conflict | Textual resolution |
| --- | --- |
| `libgfortran/configure` (2 hunks) | Generated `#line` numbers only; regenerate `configure` from the merged `configure.ac`. |

Drill log: `.work/_state/logs/S7_10_drill-20261108-024255.log`.

Change size against `releases/gcc-16.2.0`, measured as in S6-08:

| Scope | Changed lines | Hunks |
| --- | ---: | ---: |
| Shared i386 files | 644 | 122 |
| `i386-knc.cc` (KNC only) | 1733 | 1 |
| `i386-knc.h` (KNC only) | 104 | 1 |
| `imci.md` (KNC only) | 1978 | 1 |
| `knc.md` (KNC only) | 94 | 1 |
| `linux-k1om.h` (KNC only) | 68 | 1 |
| KNC-only i386 total | 3977 | 5 |

The shared build wrapper skipped the build: the clean tree
`1f03d65c71a35263359d7bf82a1bef03e0916c86` was already built at
`9af4eb014e32` (same tree as the checked head).
Build log: `.work/_state/logs/S7_10_build-20261108-024243.log`.

`python tools/check t0 t1 t2 --compiler gcc16`: exit 0, 305 PASS, no FAIL.
Log: `.work/_state/logs/check_gcc16_t0_t1_t2-20261108-025104.log`.

The S7-10 ticket assigns x86 identity and card execution to the lead. Since
S6-08 the shared i386 files and `gcc/configure` are unchanged; only
KNC-only `linux-k1om.h` and libgfortran changed. No native execution result is
claimed by this engineer report.

### S7-10 ICE sweeps

| Flags (also `-march=knc`) | Pass | Compiler error | User inline asm rejected | ICE | Hang | Assembler rejection | Lint failure | Infrastructure failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `-O2 -ftree-vectorize` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |
| `-O3` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |

Same counts as S6-08. No slow retry or FP ABI error.

Log: `.work/_state/logs/S7_10_sweep-20261108-030046.log`.
Summary: `.work/_shared/S7-10/sweep/summary.txt`, launcher
`.work/_shared/S7-10/sweep.py`.
## 2026-11-10T18:21:54+00:00

Base: `releases/gcc-16.2.0`; KNC: `fe7ed380f149f775a6737639ec8a93b1e80d7c97`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 12

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

#### `gcc/config/i386/i386-options.cc`

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
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

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* Only gather/scatter needs statement-specific KNC costs here.  Other
     KNC defaults have already received the x86 lowering adjustments.  */
  if (TARGET_KNC
      && (kind == vector_gather_load || kind == vector_scatter_store))
    {
      int cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
      if (cost >= 0)
        stmt_cost = cost;
    }
  /* ADR-0009 amendment 1 point 9: a KNC masked access of unknown
     alignment is a gather or scatter.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
  /* ADR-0008 point 1: a two-input KNC permute is vpermd plus vpermd.  */
  if (TARGET_KNC && kind == vec_perm
      && ix86_knc_two_input_perm_p (mode, stmt_info, node))
    stmt_cost *= 2;
>>>>>>> knc
```

#### `gcc/config/i386/i386.opt`

```diff
<<<<<<< upstream/master
mavx10v2aux
Target Mask(ISA2_AVX10V2AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V2AUX built-in functions and code generation.

macev1
Target Mask(ISA2_ACEV1) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and ACEV1 built-in functions and code generation.

mavx10v1aux
Target Mask(ISA2_AVX10V1AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V1AUX built-in functions and code generation.
=======
-param=knc-threads-per-core=
Target Joined UInteger Var(knc_threads_per_core) Init(4) IntegerRange(1, 4) Param Optimization
Assumed active KNC threads per core for latency hiding (1 to 4, default 4).

-param=knc-prefetch-l1-distance=
Target Joined UInteger Var(knc_prefetch_l1_distance) Init(16) IntegerRange(1, 4096) Param Optimization
KNC L1 software prefetch distance in cache lines (default 16; halved when distance x streams x threads per core exceeds a quarter of L1; kept below the L2 distance).

-param=knc-prefetch-l2-distance=
Target Joined UInteger Var(knc_prefetch_l2_distance) Init(32) IntegerRange(1, 4096) Param Optimization
KNC L2 software prefetch distance in cache lines (default 32).

mphinix
Target Driver RejectNegative Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: -O3 and the measured GCC-KNC defaults in one flag, with a banner and a progress bar on a terminal; IEEE semantics stay.

mphinix-banner
Target Driver Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: print the -mphinix banner on a terminal (default on).

mprogress
Target Driver Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: draw a progress bar, one step per driver job, on a terminal (default with -mphinix).
>>>>>>> knc
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
   (V16SF "TARGET_AVX512F") (V8SF "TARGET_AVX") V4SF
   (V8DF "TARGET_AVX512F") (V4DF "TARGET_AVX") (V2DF "TARGET_SSE2")
   (V8DI "TARGET_AVX512F") (V4DI "TARGET_AVX") (V2DI "TARGET_SSE2")
   (V16SI "TARGET_AVX512F") (V8SI "TARGET_AVX") (V4SI "TARGET_SSE2")
   (V32HI "TARGET_AVX512F") (V16HI "TARGET_AVX") (V8HI "TARGET_SSE2")
   (V64QI "TARGET_AVX512F") (V32QI "TARGET_AVX") (V16QI "TARGET_SSE2")])
=======
   (V8DI "TARGET_AVX512F || TARGET_KNC") (V4DI "TARGET_AVX") (V2DI "TARGET_SSE2")
   (V16SF "TARGET_AVX512F || TARGET_KNC") (V8SF "TARGET_AVX") V4SF
   (V8DF "TARGET_AVX512F || TARGET_KNC") (V4DF "TARGET_AVX") (V2DF "TARGET_SSE2")
   (V16SI "TARGET_KNC")])
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_expand_cond_fma (operands, false, false);
=======
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_cond_fma (<MODE>mode, operands[0], operands[1],
				   operands[2], operands[3], operands[4],
				   operands[5]));
      DONE;
    }
  rtx tmp = gen_reg_rtx (<MODE>mode);
  emit_insn (gen_fma<mode>4 (tmp,
			     operands[2],
			     operands[3],
			     operands[4]));
  emit_move_insn (operands[0], gen_rtx_VEC_MERGE (<MODE>mode,
						  tmp,
						  operands[5],
						  operands[1]));
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
{
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_plusminus (<CODE>, <MODE>mode, operands[0],
				    operands[1], operands[2]));
      DONE;
    }
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

#### `libgfortran/configure`

```diff
<<<<<<< upstream/master
#line 13245 "configure"
=======
#line 13250 "configure"
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 13351 "configure"
=======
#line 13356 "configure"
>>>>>>> knc
```

#### `libgomp/configure`

```diff
<<<<<<< upstream/master
=======
USE_FORTRAN_FALSE
USE_FORTRAN_TRUE
LIBGOMP_RUNTIME_GUARD_FILE
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 11865 "configure"
=======
#line 11862 "configure"
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 11971 "configure"
=======
#line 11968 "configure"
>>>>>>> knc
```

#### `libgomp/env.c`

```diff
<<<<<<< upstream/master
      fputs ("  [all] GOMP_RUNTIME_USM = '", stderr);
      switch (gomp_runtime_usm_var)
	{
	case GOMP_RUNTIME_USM_DISABLED:
	  fputs ("DISABLED", stderr);
	  break;
	case GOMP_RUNTIME_USM_AUTO:
	  fputs ("AUTO", stderr);
	  break;
	case GOMP_RUNTIME_USM_ENABLED:
	  fputs ("ENABLED", stderr);
	  break;
	}
      fputs ("'\n", stderr);
      fprintf (stderr, "  [host] GOMP_BARRIER_TYPE = '%s'\n",
	       gomp_barrier_request == GOMP_FLAT_BARRIER   ? "flat"
	       : gomp_barrier_request == GOMP_TREE_BARRIER ? "tree"
	       : gomp_barrier_request == GOMP_CENTRALIZED_BARRIER
		 ? "centralized"
		 : "auto");
      fprintf (stderr, "  [host] GOMP_FORKJOIN_BARRIER_TYPE = '%s'\n",
	       gomp_forkjoin_barrier_request == GOMP_FLAT_BARRIER   ? "flat"
	       : gomp_forkjoin_barrier_request == GOMP_TREE_BARRIER ? "tree"
	       : gomp_forkjoin_barrier_request == GOMP_CENTRALIZED_BARRIER
		 ? "centralized"
		 : "auto");
=======
#ifdef __k1om__
      gomp_knc_display_delay (stderr);
      gomp_knc_display_malloc (stderr);
#endif
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  parse_barrier_choice ("GOMP_BARRIER_TYPE", &gomp_barrier_request);
  gomp_forkjoin_barrier_request = gomp_barrier_request;
  parse_barrier_choice ("GOMP_FORKJOIN_BARRIER_TYPE",
			&gomp_forkjoin_barrier_request);
=======
#ifdef __k1om__
  gomp_knc_init_arenas ((none != NULL
			 && gomp_get_icv_flag (none->flags, GOMP_ICV_STACKSIZE))
			|| (all != NULL
			    && gomp_get_icv_flag (all->flags,
						  GOMP_ICV_STACKSIZE)));
#endif
>>>>>>> knc
```

#### `libgomp/libgomp.h`

```diff
<<<<<<< upstream/master
#ifdef __AMDGCN__
/* Parameters needed to kick off new threads on AMD GCN.  They correspond to
   various fields in gomp_thread.  This struct, and all its contents, should
   only be modified by gomp_team_start, and stay untouched until the threads
   of a team reach the final barrier.  */

struct gomp_thread_start_data
{
  /* Team the new thread is part of.  */
  struct gomp_team *team;
  /* Active nesting level.  */
  unsigned level, active_level;
  /* Parent task.  */
  struct gomp_task *parent_task;
  /* Previous ICVs.  */
  struct gomp_task_icv prev_icvs;
  /* Task group for the new threads implicit task.  */
  struct gomp_taskgroup *taskgroup;
};
=======
#ifdef __k1om__
/* KNC: a member that starts a cache line of its own.  */
#define GOMP_KNC_LINE __attribute__((aligned (64)))
#else
#define GOMP_KNC_LINE
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#ifdef __AMDGCN__
  /* Used on AMD GCN to inform threads how to launch in a team.  */
  struct gomp_thread_start_data thr_start_data;
#elif LIBGOMP_USE_PTHREADS
  /* Cache to help initialise each secondary threads `task` when re-using a
     team very many times.  This allows each secondary thread to perform the
     re-initialisation instead of having the primary thread need to perform
     that initialisation.  */
  struct thread_init {
    struct gomp_task_icv task_icv_init;
    struct gomp_task *task_parent_init;
    struct gomp_taskgroup *task_taskgroup;
    uintptr_t def_allocator;
    unsigned int num_teams;
    unsigned int team_num;
    void (*fn) (void *data);
    void *data;
  } ti;
  struct prev_place_vars {
    unsigned int place_partition_off;
    unsigned int place_partition_len;
    char bind;
  } ppv;
#endif
  bool reused;

  /* This array contains structures for implicit tasks.  */
  struct gomp_task implicit_task[];
=======
  /* This array contains structures for implicit tasks.  Use
     gomp_implicit_task to index it.  */
  struct gomp_task implicit_task[] GOMP_KNC_LINE;
>>>>>>> knc
```

#### `libgomp/team.c`

```diff
<<<<<<< upstream/master
		     + sizeof (team->implicit_task[0]);
      size_t team_extra = nthreads * extra;
      size_t barrier_padding = 0;
      if (barrier_extra_alloc.size)
	{
	  /* `offsetof` in case the structure is padded and `implicit_task` is
	     not at the end of `sizeof (*team)`.  */
	  size_t barrier_offset
	    = offsetof (struct gomp_team, implicit_task) + team_extra;
	  gomp_assert (barrier_extra_alloc.align
			 <= __alignof (struct gomp_team),
		       "barrier extra alignment too large: %lu > %lu",
		       (unsigned long) barrier_extra_alloc.align,
		       (unsigned long) __alignof (struct gomp_team));
	  barrier_padding = ((barrier_offset + barrier_extra_alloc.align - 1)
			     & ~(barrier_extra_alloc.align - 1))
			    - barrier_offset;
	}
      size_t alloc_extra
	= team_extra + barrier_padding + barrier_extra_alloc.size;
=======
		     + GOMP_IMPLICIT_TASK_STRIDE;
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
	  nthr->place = place;
=======
	  nthr->ts.def_allocator = thr->ts.def_allocator;
#ifdef HAVE_SYNC_BUILTINS
	  nthr->ts.single_count = 0;
#endif
	  nthr->ts.static_trip = 0;
	  nthr->num_teams = thr->num_teams;
	  nthr->team_num = thr->team_num;
	  nthr->task = gomp_implicit_task (team, i);
	  nthr->place = place;
	  gomp_init_task (nthr->task, task, icv);
	  gomp_implicit_task (team, i)->icv.nthreads_var = nthreads_var;
	  gomp_implicit_task (team, i)->icv.bind_var = bind_var;
	  nthr->task->taskgroup = taskgroup;
	  nthr->fn = fn;
	  nthr->data = data;
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
      start_data->team = team;
      start_data->team_id = i;

      start_data->active_level = thr->ts.active_level;
=======
      start_data->fn = fn;
      start_data->fn_data = data;
      start_data->ts.team = team;
      start_data->ts.work_share = &team->work_shares[0];
      start_data->ts.last_work_share = NULL;
      start_data->ts.team_id = i;
      start_data->ts.level = team->prev_ts.level + 1;
      start_data->ts.active_level = thr->ts.active_level;
      start_data->ts.def_allocator = thr->ts.def_allocator;
#ifdef HAVE_SYNC_BUILTINS
      start_data->ts.single_count = 0;
#endif
      start_data->ts.static_trip = 0;
      start_data->num_teams = thr->num_teams;
      start_data->team_num = thr->team_num;
      start_data->task = gomp_implicit_task (team, i);
      gomp_init_task (start_data->task, task, icv);
      gomp_implicit_task (team, i)->icv.nthreads_var = nthreads_var;
      gomp_implicit_task (team, i)->icv.bind_var = bind_var;
      start_data->task->taskgroup = taskgroup;
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +67 | -22 |
| `gcc/config.gcc` | +93 | -158 |
| `gcc/config.host` | +10 | -2 |
| `gcc/config/i386/i386-builtins.cc` | +45 | -5 |
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
| `gcc/config/i386/knc-driver.cc` | +0 | -0 |
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +2036 | -286 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/t-knc` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +1 | -1 |
| `gcc/configure` | +1043 | -920 |
| `gcc/configure.ac` | +367 | -378 |
| `gcc/cp/g++spec.cc` | +1 | -1 |
| `gcc/doc/tm.texi` | +177 | -69 |
| `gcc/doc/tm.texi.in` | +55 | -39 |
| `gcc/gcc.cc` | +160 | -59 |
| `gcc/target.def` | +160 | -39 |
| `gcc/tree-ssa-loop-ivopts.cc` | +286 | -97 |
| `gcc/tree-ssa-loop-prefetch.cc` | +20 | -12 |
| `libgcc/config.host` | +13 | -23 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +2 | -1 |
| `libgfortran/Makefile.in` | +7 | -2 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +142 | -16 |
| `libgfortran/configure.ac` | +14 | -4 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |
| `libgomp/Makefile.am` | +7 | -5 |
| `libgomp/Makefile.in` | +32 | -25 |
| `libgomp/config/linux/knc/affinity.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/card.h` | +0 | -0 |
| `libgomp/config/linux/knc/futex.h` | +0 | -0 |
| `libgomp/config/linux/knc/guard.ld` | +0 | -0 |
| `libgomp/config/linux/knc/mutex.c` | +0 | -0 |
| `libgomp/config/linux/knc/simple-bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/spincount.h` | +0 | -0 |
| `libgomp/configure` | +135 | -271 |
| `libgomp/configure.ac` | +83 | -27 |
| `libgomp/configure.tgt` | +19 | -16 |
| `libgomp/env.c` | +146 | -6 |
| `libgomp/libgomp.h` | +159 | -11 |
| `libgomp/libgomp.texi` | +907 | -133 |
| `libgomp/team.c` | +462 | -101 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/baseline_symbols.txt` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc-static.ld` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc.ld` | +0 | -0 |
| `libstdc++-v3/src/Makefile.am` | +20 | -0 |
| `libstdc++-v3/src/Makefile.in` | +22 | -1 |

### upstream/releases/gcc-16

Commit: `4b03dde2e3ad210db469ee763194c0cbec22cf45`; date: 2026-11-03T10:43:47+01:00.

Conflicts: 0

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +3 | -1 |
| `gcc/config.gcc` | +0 | -0 |
| `gcc/config.host` | +0 | -0 |
| `gcc/config/i386/i386-builtins.cc` | +0 | -0 |
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
| `gcc/config/i386/knc-driver.cc` | +0 | -0 |
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/t-knc` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `gcc/cp/g++spec.cc` | +0 | -0 |
| `gcc/doc/tm.texi` | +0 | -0 |
| `gcc/doc/tm.texi.in` | +0 | -0 |
| `gcc/gcc.cc` | +0 | -0 |
| `gcc/target.def` | +0 | -0 |
| `gcc/tree-ssa-loop-ivopts.cc` | +8 | -3 |
| `gcc/tree-ssa-loop-prefetch.cc` | +0 | -0 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +0 | -0 |
| `libgfortran/Makefile.in` | +0 | -0 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +0 | -0 |
| `libgfortran/configure.ac` | +0 | -0 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |
| `libgomp/Makefile.am` | +0 | -0 |
| `libgomp/Makefile.in` | +0 | -0 |
| `libgomp/config/linux/knc/affinity.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/card.h` | +0 | -0 |
| `libgomp/config/linux/knc/futex.h` | +0 | -0 |
| `libgomp/config/linux/knc/guard.ld` | +0 | -0 |
| `libgomp/config/linux/knc/mutex.c` | +0 | -0 |
| `libgomp/config/linux/knc/simple-bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/spincount.h` | +0 | -0 |
| `libgomp/configure` | +0 | -0 |
| `libgomp/configure.ac` | +0 | -0 |
| `libgomp/configure.tgt` | +0 | -0 |
| `libgomp/env.c` | +0 | -0 |
| `libgomp/libgomp.h` | +0 | -0 |
| `libgomp/libgomp.texi` | +0 | -0 |
| `libgomp/team.c` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/baseline_symbols.txt` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc-static.ld` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc.ld` | +0 | -0 |
| `libstdc++-v3/src/Makefile.am` | +0 | -0 |
| `libstdc++-v3/src/Makefile.in` | +0 | -0 |


### S8-11 classification and change size (KNC `fe7ed380f149`)

The drill used local refs only: upstream master `b88c2821e219` has twelve
conflicted files and 23 hunks; gcc-16 `4b03dde2e3ad` has no conflicts. Every
conflict has a textual resolution. The S7-10 hunks resolve as recorded there
(`i386.opt` now also carries S8-03's prefetch parameters and S8-16's `-mphinix`
entries in the same hunk; keep both sides). New since S7-10:

| Conflict | Textual resolution |
| --- | --- |
| `sse.md`, `STORENT_MODE` (1 hunk, S8-13) | Take upstream's list (new `V16SI`, `V32HI`, `V64QI` under AVX512F) and add `\|\| TARGET_KNC` to `V8DI`, `V16SF`, `V8DF` and `V16SI`. |
| `libgomp/configure` (3 hunks) | Generated: two `#line` numbers and the KNC substitution names; regenerate from the merged `configure.ac`. |
| `libgomp/env.c` (2 hunks) | Keep upstream's `GOMP_RUNTIME_USM` and barrier-type display and parsing, then the `__k1om__` blocks (`gomp_knc_display_*`, `gomp_knc_init_arenas`). |
| `libgomp/libgomp.h` (2 hunks) | Keep upstream's AMD GCN `gomp_thread_start_data` and the `GOMP_KNC_LINE` macro; keep upstream's new `gomp_team` fields (`ti`, `ppv`, `reused`) and put `GOMP_KNC_LINE` on `implicit_task[]`. |
| `libgomp/team.c` (3 hunks) | Take upstream's restructured team start (thread-init cache, `start_data` fields) and replace each `&team->implicit_task[i]` with `gomp_implicit_task (team, i)`; in the allocation size use `GOMP_IMPLICIT_TASK_STRIDE` as the per-thread `extra` term before upstream's barrier padding. |

Not a conflict but needed by a forward port: upstream master changes the
libgomp barrier interface (`gomp_barrier_init` takes a pointer, the wait
functions take a thread id or increment, new `gomp_barrier_extra_alloc`,
`gomp_barrier_can_hold`, `gomp_team_barrier_wake_on_increment`), and adds a
`futex_waitv` tree barrier. KNC's own `libgomp/config/linux/knc/bar.{h,c}`
(S9-09's per-core group barrier) merges cleanly as a new file but must be
ported to that interface before libgomp builds on master.

Drill log: `.work/_state/logs/S8_11_drill-20261110-132154.log`.

Change size against `releases/gcc-16.2.0`, measured as in S6-08; the new
KNC-only `knc-driver.cc` and `t-knc` (S8-16) are counted with the KNC-only files:

| Scope | Changed lines | Hunks |
| --- | ---: | ---: |
| Shared i386 files | 718 | 132 |
| `i386-knc.cc` (KNC only) | 2144 | 1 |
| `i386-knc.h` (KNC only) | 117 | 1 |
| `imci.md` (KNC only) | 2158 | 1 |
| `knc.md` (KNC only) | 97 | 1 |
| `linux-k1om.h` (KNC only) | 115 | 1 |
| `knc-driver.cc` (KNC only) | 352 | 1 |
| `t-knc` (KNC only) | 4 | 1 |
| KNC-only i386 total | 4987 | 7 |

Shared i386 files changed since S7-10 (644/122: S8-03, S8-13, S8-15, S8-16,
S8-19 hooks), so the lead's x86 identity check is needed at this head.

Build: tree 2 (`gcc-build-2`) at `fe7ed380f149`, clean.
Log: `.work/_state/logs/S8_11_build-20261110-133249.log`.

### S8-11 ICE sweeps

| Flags (also `-march=knc`) | Pass | Compiler error | User inline asm rejected | ICE | Hang | Assembler rejection | Lint failure | Infrastructure failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `-O2 -ftree-vectorize` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |
| `-O3` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |

Same counts and lists as S7-10 (the summaries differ only in wall time and
worker count). No slow retry or FP ABI error.

Log: `.work/_state/logs/S8_11_sweep-20261110-140943.log`.
Summary: `.work/_shared/S8-11/sweep/summary.txt`, launcher
`.work/_shared/S8-11/sweep.py` (run under the toolchain's Cygwin Python).

### S8-11 T0-T2

`python tools/check t0 t1 t2 --compiler gcc16` on tree 2: exit 0, 328 PASS, no FAIL.
Log: `.work/_state/logs/check_gcc16_t0_t1_t2-20261110-141753.log`.

### S8-11 compiler-prefetch column case (lead note 2026-11-08)

`tests/bench/prefetch-column/` (29 float arrays, 51 k trips at a 1092-byte step,
8-float rows, built by `build.py`). Built and linted, not run:
`.work/_shared/S8-11/prefetch-column/column.mic`
(log `.work/_state/logs/S8_11_prefetch_build-20261110-140932.log`).

Finding: with `-fprefetch-loop-arrays` the S8 head emits **no** prefetch on this
shape, so `column_pf` and `column_nopf` are the same code apart from the name, and a
card pairing would only measure noise. Cause: the vectorizer turns each 8-float
row into a 16-lane `.MASK_LOAD` (mask of 8 lanes), and
`gather_memory_references` in `tree-ssa-loop-prefetch.cc` only looks at
`GIMPLE_ASSIGN`s, so the loop has no memory references to prefetch (the aprefetch
dump stops after "Processing loop 1:"). The same file with 16-float rows gets 58
`vprefetch` instructions; scalar code (`-fno-tree-vectorize`) at 8 or 16 floats
gets none. A row of fewer than 16 floats, as in WRF's 8-float rows, is never
prefetched by the compiler. Lead's call: run as specified, change the case to
16-float rows, or open a ticket for masked loads in the prefetch pass.

### S8-11 paired M2 and card staging (lead runs)

Sprint 7's compiler (`497bbe8bedf0`) was rebuilt in tree 2 only for `cc1`
(target libgomp failed against the Sprint 8 configure, which M2 does not use;
log `.work/_state/logs/S8_11_build_s7-20261110-145350.log`), its M2 objects
kept in `.work/_shared/S8-11/m2-s7`, and tree 2 rebuilt clean at `fe7ed380f149`
(log `.work/_state/logs/S8_11_build-20261110-152151.log`). The paired binary
links Sprint 7's `kernels-gcc.o` as `gcc_before`; its Sprint 8 `kernels-gcc.s`
equals the one built before the switch.

| Card job | Binary |
| --- | --- |
| Paired M2 (S8 vs S7) | `.work/_shared/S8-11/m2-paired/m2-kernels.mic`, `m2-negative.mic` (log `S8_11_m2_paired-20261110-160138.log`) |
| M2 at S8 alone | `.work/_shared/S8-11/m2-s8/m2-kernels.mic`, `m2-negative.mic` |
| Execute suite | `.work/_shared/S8-11/execute/` (1692 sources, 1681 linked, 11 compile errors, 0 ICE; `build.tsv`, log `S8_11_execute_build-20261110-143346.log`) |
| Prefetch column | `.work/_shared/S8-11/prefetch-column/column.mic` (see finding above) |

Profiles 3100/5100/7100 (S9-14): the same binaries through `card_run --profile`;
nothing profile-specific is built. x86 identity not run (lead).
## 2026-11-11T08:23:02+00:00

Base: `releases/gcc-16.2.0`; KNC: `e6b6b55b5dc2b7cfe69d6de7f646904c1f3b9039`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 12

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

#### `gcc/config/i386/i386-options.cc`

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
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

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* Only gather/scatter needs statement-specific KNC costs here.  Other
     KNC defaults have already received the x86 lowering adjustments.  */
  if (TARGET_KNC
      && (kind == vector_gather_load || kind == vector_scatter_store))
    {
      int cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
      if (cost >= 0)
        stmt_cost = cost;
    }
  /* ADR-0009 amendment 1 point 9: a KNC masked access of unknown
     alignment is a gather or scatter.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
  /* ADR-0008 point 1: a two-input KNC permute is vpermd plus vpermd.  */
  if (TARGET_KNC && kind == vec_perm
      && ix86_knc_two_input_perm_p (mode, stmt_info, node))
    stmt_cost *= 2;
>>>>>>> knc
```

#### `gcc/config/i386/i386.opt`

```diff
<<<<<<< upstream/master
mavx10v2aux
Target Mask(ISA2_AVX10V2AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V2AUX built-in functions and code generation.

macev1
Target Mask(ISA2_ACEV1) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and ACEV1 built-in functions and code generation.

mavx10v1aux
Target Mask(ISA2_AVX10V1AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V1AUX built-in functions and code generation.
=======
-param=knc-threads-per-core=
Target Joined UInteger Var(knc_threads_per_core) Init(4) IntegerRange(1, 4) Param Optimization
Assumed active KNC threads per core for latency hiding (1 to 4, default 4).

-param=knc-prefetch-l1-distance=
Target Joined UInteger Var(knc_prefetch_l1_distance) Init(16) IntegerRange(1, 4096) Param Optimization
KNC L1 software prefetch distance in cache lines (default 16; halved when distance x streams x threads per core exceeds a quarter of L1; kept below the L2 distance).

-param=knc-prefetch-l2-distance=
Target Joined UInteger Var(knc_prefetch_l2_distance) Init(32) IntegerRange(1, 4096) Param Optimization
KNC L2 software prefetch distance in cache lines (default 32).

mphinix
Target Driver RejectNegative Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: -O3 and the measured GCC-KNC defaults in one flag, with a banner and a progress bar on a terminal; IEEE semantics stay.

mphinix-banner
Target Driver Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: print the -mphinix banner on a terminal (default on).

mknc-card=
Target Driver Joined RejectNegative Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: tune for a card model: generic (default), 3100, 5100, 7100, a card name such as 7120P, or native.

mprogress
Target Driver Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: draw a progress bar, one step per driver job, on a terminal (default with -mphinix).
>>>>>>> knc
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
   (V16SF "TARGET_AVX512F") (V8SF "TARGET_AVX") V4SF
   (V8DF "TARGET_AVX512F") (V4DF "TARGET_AVX") (V2DF "TARGET_SSE2")
   (V8DI "TARGET_AVX512F") (V4DI "TARGET_AVX") (V2DI "TARGET_SSE2")
   (V16SI "TARGET_AVX512F") (V8SI "TARGET_AVX") (V4SI "TARGET_SSE2")
   (V32HI "TARGET_AVX512F") (V16HI "TARGET_AVX") (V8HI "TARGET_SSE2")
   (V64QI "TARGET_AVX512F") (V32QI "TARGET_AVX") (V16QI "TARGET_SSE2")])
=======
   (V8DI "TARGET_AVX512F || TARGET_KNC") (V4DI "TARGET_AVX") (V2DI "TARGET_SSE2")
   (V16SF "TARGET_AVX512F || TARGET_KNC") (V8SF "TARGET_AVX") V4SF
   (V8DF "TARGET_AVX512F || TARGET_KNC") (V4DF "TARGET_AVX") (V2DF "TARGET_SSE2")
   (V16SI "TARGET_KNC")])
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_expand_cond_fma (operands, false, false);
=======
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_cond_fma (<MODE>mode, operands[0], operands[1],
				   operands[2], operands[3], operands[4],
				   operands[5]));
      DONE;
    }
  rtx tmp = gen_reg_rtx (<MODE>mode);
  emit_insn (gen_fma<mode>4 (tmp,
			     operands[2],
			     operands[3],
			     operands[4]));
  emit_move_insn (operands[0], gen_rtx_VEC_MERGE (<MODE>mode,
						  tmp,
						  operands[5],
						  operands[1]));
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
{
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_plusminus (<CODE>, <MODE>mode, operands[0],
				    operands[1], operands[2]));
      DONE;
    }
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

#### `libgfortran/configure`

```diff
<<<<<<< upstream/master
#line 13245 "configure"
=======
#line 13250 "configure"
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 13351 "configure"
=======
#line 13356 "configure"
>>>>>>> knc
```

#### `libgomp/configure`

```diff
<<<<<<< upstream/master
=======
USE_FORTRAN_FALSE
USE_FORTRAN_TRUE
LIBGOMP_RUNTIME_GUARD_FILE
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 11865 "configure"
=======
#line 11862 "configure"
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 11971 "configure"
=======
#line 11968 "configure"
>>>>>>> knc
```

#### `libgomp/env.c`

```diff
<<<<<<< upstream/master
      fputs ("  [all] GOMP_RUNTIME_USM = '", stderr);
      switch (gomp_runtime_usm_var)
	{
	case GOMP_RUNTIME_USM_DISABLED:
	  fputs ("DISABLED", stderr);
	  break;
	case GOMP_RUNTIME_USM_AUTO:
	  fputs ("AUTO", stderr);
	  break;
	case GOMP_RUNTIME_USM_ENABLED:
	  fputs ("ENABLED", stderr);
	  break;
	}
      fputs ("'\n", stderr);
      fprintf (stderr, "  [host] GOMP_BARRIER_TYPE = '%s'\n",
	       gomp_barrier_request == GOMP_FLAT_BARRIER   ? "flat"
	       : gomp_barrier_request == GOMP_TREE_BARRIER ? "tree"
	       : gomp_barrier_request == GOMP_CENTRALIZED_BARRIER
		 ? "centralized"
		 : "auto");
      fprintf (stderr, "  [host] GOMP_FORKJOIN_BARRIER_TYPE = '%s'\n",
	       gomp_forkjoin_barrier_request == GOMP_FLAT_BARRIER   ? "flat"
	       : gomp_forkjoin_barrier_request == GOMP_TREE_BARRIER ? "tree"
	       : gomp_forkjoin_barrier_request == GOMP_CENTRALIZED_BARRIER
		 ? "centralized"
		 : "auto");
=======
#ifdef __k1om__
      gomp_knc_display_delay (stderr);
      gomp_knc_display_malloc (stderr);
#endif
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  parse_barrier_choice ("GOMP_BARRIER_TYPE", &gomp_barrier_request);
  gomp_forkjoin_barrier_request = gomp_barrier_request;
  parse_barrier_choice ("GOMP_FORKJOIN_BARRIER_TYPE",
			&gomp_forkjoin_barrier_request);
=======
#ifdef __k1om__
  gomp_knc_init_arenas ((none != NULL
			 && gomp_get_icv_flag (none->flags, GOMP_ICV_STACKSIZE))
			|| (all != NULL
			    && gomp_get_icv_flag (all->flags,
						  GOMP_ICV_STACKSIZE)));
#endif
>>>>>>> knc
```

#### `libgomp/libgomp.h`

```diff
<<<<<<< upstream/master
#ifdef __AMDGCN__
/* Parameters needed to kick off new threads on AMD GCN.  They correspond to
   various fields in gomp_thread.  This struct, and all its contents, should
   only be modified by gomp_team_start, and stay untouched until the threads
   of a team reach the final barrier.  */

struct gomp_thread_start_data
{
  /* Team the new thread is part of.  */
  struct gomp_team *team;
  /* Active nesting level.  */
  unsigned level, active_level;
  /* Parent task.  */
  struct gomp_task *parent_task;
  /* Previous ICVs.  */
  struct gomp_task_icv prev_icvs;
  /* Task group for the new threads implicit task.  */
  struct gomp_taskgroup *taskgroup;
};
=======
#ifdef __k1om__
/* KNC: a member that starts a cache line of its own.  */
#define GOMP_KNC_LINE __attribute__((aligned (64)))
#else
#define GOMP_KNC_LINE
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#ifdef __AMDGCN__
  /* Used on AMD GCN to inform threads how to launch in a team.  */
  struct gomp_thread_start_data thr_start_data;
#elif LIBGOMP_USE_PTHREADS
  /* Cache to help initialise each secondary threads `task` when re-using a
     team very many times.  This allows each secondary thread to perform the
     re-initialisation instead of having the primary thread need to perform
     that initialisation.  */
  struct thread_init {
    struct gomp_task_icv task_icv_init;
    struct gomp_task *task_parent_init;
    struct gomp_taskgroup *task_taskgroup;
    uintptr_t def_allocator;
    unsigned int num_teams;
    unsigned int team_num;
    void (*fn) (void *data);
    void *data;
  } ti;
  struct prev_place_vars {
    unsigned int place_partition_off;
    unsigned int place_partition_len;
    char bind;
  } ppv;
#endif
  bool reused;

  /* This array contains structures for implicit tasks.  */
  struct gomp_task implicit_task[];
=======
  /* This array contains structures for implicit tasks.  Use
     gomp_implicit_task to index it.  */
  struct gomp_task implicit_task[] GOMP_KNC_LINE;
>>>>>>> knc
```

#### `libgomp/team.c`

```diff
<<<<<<< upstream/master
		     + sizeof (team->implicit_task[0]);
      size_t team_extra = nthreads * extra;
      size_t barrier_padding = 0;
      if (barrier_extra_alloc.size)
	{
	  /* `offsetof` in case the structure is padded and `implicit_task` is
	     not at the end of `sizeof (*team)`.  */
	  size_t barrier_offset
	    = offsetof (struct gomp_team, implicit_task) + team_extra;
	  gomp_assert (barrier_extra_alloc.align
			 <= __alignof (struct gomp_team),
		       "barrier extra alignment too large: %lu > %lu",
		       (unsigned long) barrier_extra_alloc.align,
		       (unsigned long) __alignof (struct gomp_team));
	  barrier_padding = ((barrier_offset + barrier_extra_alloc.align - 1)
			     & ~(barrier_extra_alloc.align - 1))
			    - barrier_offset;
	}
      size_t alloc_extra
	= team_extra + barrier_padding + barrier_extra_alloc.size;
=======
		     + GOMP_IMPLICIT_TASK_STRIDE;
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
	  nthr->place = place;
=======
	  nthr->ts.def_allocator = thr->ts.def_allocator;
#ifdef HAVE_SYNC_BUILTINS
	  nthr->ts.single_count = 0;
#endif
	  nthr->ts.static_trip = 0;
	  nthr->num_teams = thr->num_teams;
	  nthr->team_num = thr->team_num;
	  nthr->task = gomp_implicit_task (team, i);
	  nthr->place = place;
	  gomp_init_task (nthr->task, task, icv);
	  gomp_implicit_task (team, i)->icv.nthreads_var = nthreads_var;
	  gomp_implicit_task (team, i)->icv.bind_var = bind_var;
	  nthr->task->taskgroup = taskgroup;
	  nthr->fn = fn;
	  nthr->data = data;
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
      start_data->team = team;
      start_data->team_id = i;

      start_data->active_level = thr->ts.active_level;
=======
      start_data->fn = fn;
      start_data->fn_data = data;
      start_data->ts.team = team;
      start_data->ts.work_share = &team->work_shares[0];
      start_data->ts.last_work_share = NULL;
      start_data->ts.team_id = i;
      start_data->ts.level = team->prev_ts.level + 1;
      start_data->ts.active_level = thr->ts.active_level;
      start_data->ts.def_allocator = thr->ts.def_allocator;
#ifdef HAVE_SYNC_BUILTINS
      start_data->ts.single_count = 0;
#endif
      start_data->ts.static_trip = 0;
      start_data->num_teams = thr->num_teams;
      start_data->team_num = thr->team_num;
      start_data->task = gomp_implicit_task (team, i);
      gomp_init_task (start_data->task, task, icv);
      gomp_implicit_task (team, i)->icv.nthreads_var = nthreads_var;
      gomp_implicit_task (team, i)->icv.bind_var = bind_var;
      start_data->task->taskgroup = taskgroup;
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +67 | -22 |
| `gcc/config.gcc` | +93 | -158 |
| `gcc/config.host` | +10 | -2 |
| `gcc/config/i386/i386-builtins.cc` | +45 | -5 |
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
| `gcc/config/i386/knc-driver.cc` | +0 | -0 |
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +2036 | -286 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/t-knc` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +1 | -1 |
| `gcc/configure` | +1043 | -920 |
| `gcc/configure.ac` | +367 | -378 |
| `gcc/cp/g++spec.cc` | +1 | -1 |
| `gcc/doc/tm.texi` | +177 | -69 |
| `gcc/doc/tm.texi.in` | +55 | -39 |
| `gcc/gcc.cc` | +160 | -59 |
| `gcc/params.opt` | +23 | -5 |
| `gcc/target.def` | +160 | -39 |
| `gcc/tree-ssa-loop-ivcanon.cc` | +9 | -11 |
| `gcc/tree-ssa-loop-ivopts.cc` | +286 | -97 |
| `gcc/tree-ssa-loop-prefetch.cc` | +20 | -12 |
| `libgcc/config.host` | +13 | -23 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +2 | -1 |
| `libgfortran/Makefile.in` | +7 | -2 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +142 | -16 |
| `libgfortran/configure.ac` | +14 | -4 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |
| `libgomp/Makefile.am` | +7 | -5 |
| `libgomp/Makefile.in` | +32 | -25 |
| `libgomp/config/linux/knc/affinity.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/card.h` | +0 | -0 |
| `libgomp/config/linux/knc/futex.h` | +0 | -0 |
| `libgomp/config/linux/knc/guard.ld` | +0 | -0 |
| `libgomp/config/linux/knc/mutex.c` | +0 | -0 |
| `libgomp/config/linux/knc/simple-bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/spincount.h` | +0 | -0 |
| `libgomp/configure` | +135 | -271 |
| `libgomp/configure.ac` | +83 | -27 |
| `libgomp/configure.tgt` | +19 | -16 |
| `libgomp/env.c` | +146 | -6 |
| `libgomp/libgomp.h` | +159 | -11 |
| `libgomp/libgomp.texi` | +907 | -133 |
| `libgomp/team.c` | +462 | -101 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/baseline_symbols.txt` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc-static.ld` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc.ld` | +0 | -0 |
| `libstdc++-v3/src/Makefile.am` | +20 | -0 |
| `libstdc++-v3/src/Makefile.in` | +22 | -1 |

### upstream/releases/gcc-16

Commit: `4b03dde2e3ad210db469ee763194c0cbec22cf45`; date: 2026-11-03T10:43:47+01:00.

Conflicts: 0

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +3 | -1 |
| `gcc/config.gcc` | +0 | -0 |
| `gcc/config.host` | +0 | -0 |
| `gcc/config/i386/i386-builtins.cc` | +0 | -0 |
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
| `gcc/config/i386/knc-driver.cc` | +0 | -0 |
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/t-knc` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `gcc/cp/g++spec.cc` | +0 | -0 |
| `gcc/doc/tm.texi` | +0 | -0 |
| `gcc/doc/tm.texi.in` | +0 | -0 |
| `gcc/gcc.cc` | +0 | -0 |
| `gcc/params.opt` | +0 | -0 |
| `gcc/target.def` | +0 | -0 |
| `gcc/tree-ssa-loop-ivcanon.cc` | +0 | -0 |
| `gcc/tree-ssa-loop-ivopts.cc` | +8 | -3 |
| `gcc/tree-ssa-loop-prefetch.cc` | +0 | -0 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +0 | -0 |
| `libgfortran/Makefile.in` | +0 | -0 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +0 | -0 |
| `libgfortran/configure.ac` | +0 | -0 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |
| `libgomp/Makefile.am` | +0 | -0 |
| `libgomp/Makefile.in` | +0 | -0 |
| `libgomp/config/linux/knc/affinity.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/card.h` | +0 | -0 |
| `libgomp/config/linux/knc/futex.h` | +0 | -0 |
| `libgomp/config/linux/knc/guard.ld` | +0 | -0 |
| `libgomp/config/linux/knc/mutex.c` | +0 | -0 |
| `libgomp/config/linux/knc/simple-bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/spincount.h` | +0 | -0 |
| `libgomp/configure` | +0 | -0 |
| `libgomp/configure.ac` | +0 | -0 |
| `libgomp/configure.tgt` | +0 | -0 |
| `libgomp/env.c` | +0 | -0 |
| `libgomp/libgomp.h` | +0 | -0 |
| `libgomp/libgomp.texi` | +0 | -0 |
| `libgomp/team.c` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/baseline_symbols.txt` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc-static.ld` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc.ld` | +0 | -0 |
| `libstdc++-v3/src/Makefile.am` | +0 | -0 |
| `libstdc++-v3/src/Makefile.in` | +0 | -0 |

### S9-11 classification and change size (KNC `e6b6b55b5dc2`)

The drill used local refs only: upstream master `b88c2821e219` has twelve
conflicted files and 23 hunks; gcc-16 `4b03dde2e3ad` has no conflicts. Every
conflict has a textual resolution. The hunks are the S8-11 hunks unchanged,
except that the `i386.opt` hunk now also carries S9-13's `mknc-card=` driver
entry (keep both sides, as before). Upstream master's libgomp barrier
interface change still needs KNC's `bar.{h,c}` ported before libgomp builds
there (S8-11).

Drill log: `.work/_state/logs/S9_11_drill-20261111-032302.log`.

Change size against `releases/gcc-16.2.0`, measured as in S8-11:

| Scope | Changed lines | Hunks |
| --- | ---: | ---: |
| Shared i386 files | 722 | 132 |
| `i386-knc.cc` (KNC only) | 2158 | 1 |
| `i386-knc.h` (KNC only) | 117 | 1 |
| `imci.md` (KNC only) | 2158 | 1 |
| `knc.md` (KNC only) | 97 | 1 |
| `linux-k1om.h` (KNC only) | 124 | 1 |
| `knc-driver.cc` (KNC only) | 547 | 1 |
| `t-knc` (KNC only) | 4 | 1 |
| KNC-only i386 total | 5205 | 7 |

Shared i386 files changed since S8-11 only in `i386.opt` (+4, S9-13's
`-mknc-card=` hook), so the lead's x86 identity check is needed at this head.
x86 not run (lead).

Build: tree 2 at `e6b6b55b5dc2` (same tree as the stamped build `84c73d3882d`),
clean, skipped as fresh. Log: `.work/_state/logs/S9_11_build-20261111-032256.log`.

### S9-11 ICE sweeps

| Flags (also `-march=knc`) | Pass | Compiler error | User inline asm rejected | ICE | Hang | Assembler rejection | Lint failure | Infrastructure failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `-O2 -ftree-vectorize` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |
| `-O3` | 1968 | 33 | 2 | 0 | 0 | 0 | 0 | 0 |

Same counts and lists as S8-11 (summaries differ only in wall time).
Log: `.work/_state/logs/S9_11_sweep-20261111-032324.log`; summary
`.work/_shared/S9-11/sweep/summary.txt`.

### S9-11 T0-T2

`python tools/check t0 t1 t2 --compiler gcc16` on tree 2: exit 0, 330 PASS, no FAIL.
Log: `.work/_state/logs/check_gcc16_t0_t1_t2-20261111-033046.log`.

### S9-11 card staging (lead runs)

| Card job | Binaries |
| --- | --- |
| Execute suite | `.work/_shared/S9-11/execute/` (1692 sources, 1681 linked, 11 compile errors, 0 ICE, 118 with packed zmm; log `S9_11_execute_build-20261111-034052.log`) |
| C++ slice (S9-05) | `.work/_shared/S9-05/` (S9-24 build, same source tree; run line in `s9_24_build_s9_05-20261111-024344.log`) |
| OpenMP programs (S9-06) | `.work/_shared/S9-06/` (S9-24 build at 03:08, same source tree) |
| S9-07 binding jobs | `.work/_shared/S9-07/` (S9-24 build; explicit settings derived from the job mask) |
| S9-09 suite and measure-hier/flat | `.work/_shared/S9-09/` (S9-24 build; measurements 2/4/5) |

The S9-05/06/07/09 sets were built by S9-24 from `84c73d3882d`, whose tree
equals the final head, so they were not rebuilt. Profiles 3100/5100/7100: the
same binaries through `card_run --profile`.
## 2026-11-11T12:18:59+00:00

Base: `releases/gcc-16.2.0`; KNC: `1900ea2784e030b5061f0acd517d0936d8926a61`.
Local refs only; no fetch, checkout, index update or ref update.

### upstream/master

Commit: `b88c2821e219244d18df873b0bfb344d3dc0b2a7`; date: 2026-11-03T19:41:47+01:00.

Conflicts: 14

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

#### `gcc/config/i386/i386-options.cc`

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_tune_cost = processor_cost_table[ix86_tune];
  /* TODO: ix86_cost should be chosen at instruction or function granularity
=======
  ix86_tune_cost = ix86_knc_tune_cost (opts, processor_cost_table[ix86_tune]);
  /* TODO: ix86_cost should be chosen at instruction or function granuality
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
      case ix86_veclibabi_type_hvml:
	ix86_veclib_handler = &ix86_veclibabi_hvml;
=======
      case ix86_veclibabi_type_knc:
	ix86_veclib_handler = &ix86_knc_veclibabi;
>>>>>>> knc
```

#### `gcc/config/i386/i386-options.h`

```diff
<<<<<<< upstream/master
extern tree ix86_veclibabi_hvml (combined_fn, tree, tree);
=======
extern tree ix86_knc_veclibabi (combined_fn, tree, tree);
>>>>>>> knc
```

#### `gcc/config/i386/i386-opts.h`

```diff
<<<<<<< upstream/master
  ix86_veclibabi_type_hvml
=======
  ix86_veclibabi_type_knc
>>>>>>> knc
```

#### `gcc/config/i386/i386.cc`

```diff
<<<<<<< upstream/master
=======
  if (TARGET_KNC && !ix86_knc_check_abi_arg (get_cumulative_args (cum_v), arg))
    return true;
  CUMULATIVE_ARGS *cum = get_cumulative_args (cum_v);

>>>>>>> knc
```

```diff
<<<<<<< upstream/master
=======
    }
  if (stmt_cost == -1)
    stmt_cost = ix86_default_vector_cost (kind, mode);
  /* Only gather/scatter needs statement-specific KNC costs here.  Other
     KNC defaults have already received the x86 lowering adjustments.  */
  if (TARGET_KNC
      && (kind == vector_gather_load || kind == vector_scatter_store))
    {
      int cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
      if (cost >= 0)
        stmt_cost = cost;
    }
  /* ADR-0009 amendment 1 point 9: a KNC masked access of unknown
     alignment is a gather or scatter.  */
  if (TARGET_KNC && ix86_knc_packed_mode_p (mode)
      && (kind == unaligned_load || kind == unaligned_store)
      && stmt_info && gimple_call_internal_p (stmt_info->stmt))
    stmt_cost = ix86_knc_stmt_cost (kind, mode, stmt_info);
  /* ADR-0008 point 1: a two-input KNC permute is vpermd plus vpermd.  */
  if (TARGET_KNC && kind == vec_perm
      && ix86_knc_two_input_perm_p (mode, stmt_info, node))
    stmt_cost *= 2;
>>>>>>> knc
```

#### `gcc/config/i386/i386.opt`

```diff
<<<<<<< upstream/master
Enum(ix86_veclibabi) String(hvml) Value(ix86_veclibabi_type_hvml)
=======
Enum(ix86_veclibabi) String(knc) Value(ix86_veclibabi_type_knc)
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
mavx10v2aux
Target Mask(ISA2_AVX10V2AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V2AUX built-in functions and code generation.

macev1
Target Mask(ISA2_ACEV1) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and ACEV1 built-in functions and code generation.

mavx10v1aux
Target Mask(ISA2_AVX10V1AUX) Var(ix86_isa_flags2) Save
Support MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2,
AVX10.1 and AVX10V1AUX built-in functions and code generation.
=======
-param=knc-threads-per-core=
Target Joined UInteger Var(knc_threads_per_core) Init(4) IntegerRange(1, 4) Param Optimization
Assumed active KNC threads per core for latency hiding (1 to 4, default 4).

-param=knc-prefetch-l1-distance=
Target Joined UInteger Var(knc_prefetch_l1_distance) Init(16) IntegerRange(1, 4096) Param Optimization
KNC L1 software prefetch distance in cache lines (default 16; halved when distance x streams x threads per core exceeds a quarter of L1; kept below the L2 distance).

-param=knc-prefetch-l2-distance=
Target Joined UInteger Var(knc_prefetch_l2_distance) Init(32) IntegerRange(1, 4096) Param Optimization
KNC L2 software prefetch distance in cache lines (default 32).

mphinix
Target Driver RejectNegative Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: -O3 and the measured GCC-KNC defaults in one flag, with a banner and a progress bar on a terminal; IEEE semantics stay.

mphinix-banner
Target Driver Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: print the -mphinix banner on a terminal (default on).

mknc-card=
Target Driver Joined RejectNegative Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: tune for a card model: generic (default), 3100, 5100, 7100, a card name such as 7120P, or native.

mprogress
Target Driver Condition({defined (KNC_DRIVER_OPTIONS)})
KNC only: draw a progress bar, one step per driver job, on a terminal (default with -mphinix).
>>>>>>> knc
```

#### `gcc/config/i386/sse.md`

```diff
<<<<<<< upstream/master
   (V16SF "TARGET_AVX512F") (V8SF "TARGET_AVX") V4SF
   (V8DF "TARGET_AVX512F") (V4DF "TARGET_AVX") (V2DF "TARGET_SSE2")
   (V8DI "TARGET_AVX512F") (V4DI "TARGET_AVX") (V2DI "TARGET_SSE2")
   (V16SI "TARGET_AVX512F") (V8SI "TARGET_AVX") (V4SI "TARGET_SSE2")
   (V32HI "TARGET_AVX512F") (V16HI "TARGET_AVX") (V8HI "TARGET_SSE2")
   (V64QI "TARGET_AVX512F") (V32QI "TARGET_AVX") (V16QI "TARGET_SSE2")])
=======
   (V8DI "TARGET_AVX512F || TARGET_KNC") (V4DI "TARGET_AVX") (V2DI "TARGET_SSE2")
   (V16SF "TARGET_AVX512F || TARGET_KNC") (V8SF "TARGET_AVX") V4SF
   (V8DF "TARGET_AVX512F || TARGET_KNC") (V4DF "TARGET_AVX") (V2DF "TARGET_SSE2")
   (V16SI "TARGET_KNC")])
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  ix86_expand_cond_fma (operands, false, false);
=======
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_cond_fma (<MODE>mode, operands[0], operands[1],
				   operands[2], operands[3], operands[4],
				   operands[5]));
      DONE;
    }
  rtx tmp = gen_reg_rtx (<MODE>mode);
  emit_insn (gen_fma<mode>4 (tmp,
			     operands[2],
			     operands[3],
			     operands[4]));
  emit_move_insn (operands[0], gen_rtx_VEC_MERGE (<MODE>mode,
						  tmp,
						  operands[5],
						  operands[1]));
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  [(set (match_operand:VI_AVX2 0 "register_operand")
	(plusminus:VI_AVX2
	  (match_operand:VI_AVX2 1 "vector_operand")
	  (match_operand:VI_AVX2 2 "vector_or_const_vector_operand")))]
  "TARGET_SSE2"
{
  /* Expand vector add/sub 1 as vector sub/add -1.  */
  if (rtx_equal_p (operands[2], CONST1_RTX (<MODE>mode)))
    {
      operands[2] = force_reg (<MODE>mode, CONSTM1_RTX (<MODE>mode));
      emit_insn (gen_<inv_insn><mode>3 (operands[0], operands[1],
					operands[2]));
      DONE;
    }

  if (CONST_VECTOR_P (operands[2]))
    operands[2] = force_reg (<MODE>mode, operands[2]);

=======
  [(set (match_operand:VI_AVX2_KNC 0 "register_operand")
	(plusminus:VI_AVX2_KNC
	  (match_operand:VI_AVX2_KNC 1 "vector_operand")
	  (match_operand:VI_AVX2_KNC 2 "vector_operand")))]
  "TARGET_SSE2 || ix86_knc_packed_mode_p (<MODE>mode)"
{
  if (TARGET_KNC)
    {
      emit_insn (gen_knc_plusminus (<CODE>, <MODE>mode, operands[0],
				    operands[1], operands[2]));
      DONE;
    }
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

#### `libgfortran/configure`

```diff
<<<<<<< upstream/master
#line 13245 "configure"
=======
#line 13250 "configure"
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 13351 "configure"
=======
#line 13356 "configure"
>>>>>>> knc
```

#### `libgomp/configure`

```diff
<<<<<<< upstream/master
=======
USE_FORTRAN_FALSE
USE_FORTRAN_TRUE
LIBGOMP_RUNTIME_GUARD_FILE
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 11865 "configure"
=======
#line 11862 "configure"
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#line 11971 "configure"
=======
#line 11968 "configure"
>>>>>>> knc
```

#### `libgomp/env.c`

```diff
<<<<<<< upstream/master
      fputs ("  [all] GOMP_RUNTIME_USM = '", stderr);
      switch (gomp_runtime_usm_var)
	{
	case GOMP_RUNTIME_USM_DISABLED:
	  fputs ("DISABLED", stderr);
	  break;
	case GOMP_RUNTIME_USM_AUTO:
	  fputs ("AUTO", stderr);
	  break;
	case GOMP_RUNTIME_USM_ENABLED:
	  fputs ("ENABLED", stderr);
	  break;
	}
      fputs ("'\n", stderr);
      fprintf (stderr, "  [host] GOMP_BARRIER_TYPE = '%s'\n",
	       gomp_barrier_request == GOMP_FLAT_BARRIER   ? "flat"
	       : gomp_barrier_request == GOMP_TREE_BARRIER ? "tree"
	       : gomp_barrier_request == GOMP_CENTRALIZED_BARRIER
		 ? "centralized"
		 : "auto");
      fprintf (stderr, "  [host] GOMP_FORKJOIN_BARRIER_TYPE = '%s'\n",
	       gomp_forkjoin_barrier_request == GOMP_FLAT_BARRIER   ? "flat"
	       : gomp_forkjoin_barrier_request == GOMP_TREE_BARRIER ? "tree"
	       : gomp_forkjoin_barrier_request == GOMP_CENTRALIZED_BARRIER
		 ? "centralized"
		 : "auto");
=======
#ifdef __k1om__
      gomp_knc_display_delay (stderr);
      gomp_knc_display_malloc (stderr);
#endif
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
  parse_barrier_choice ("GOMP_BARRIER_TYPE", &gomp_barrier_request);
  gomp_forkjoin_barrier_request = gomp_barrier_request;
  parse_barrier_choice ("GOMP_FORKJOIN_BARRIER_TYPE",
			&gomp_forkjoin_barrier_request);
=======
#ifdef __k1om__
  gomp_knc_init_arenas ((none != NULL
			 && gomp_get_icv_flag (none->flags, GOMP_ICV_STACKSIZE))
			|| (all != NULL
			    && gomp_get_icv_flag (all->flags,
						  GOMP_ICV_STACKSIZE)));
#endif
>>>>>>> knc
```

#### `libgomp/libgomp.h`

```diff
<<<<<<< upstream/master
#ifdef __AMDGCN__
/* Parameters needed to kick off new threads on AMD GCN.  They correspond to
   various fields in gomp_thread.  This struct, and all its contents, should
   only be modified by gomp_team_start, and stay untouched until the threads
   of a team reach the final barrier.  */

struct gomp_thread_start_data
{
  /* Team the new thread is part of.  */
  struct gomp_team *team;
  /* Active nesting level.  */
  unsigned level, active_level;
  /* Parent task.  */
  struct gomp_task *parent_task;
  /* Previous ICVs.  */
  struct gomp_task_icv prev_icvs;
  /* Task group for the new threads implicit task.  */
  struct gomp_taskgroup *taskgroup;
};
=======
#ifdef __k1om__
/* KNC: a member that starts a cache line of its own.  */
#define GOMP_KNC_LINE __attribute__((aligned (64)))
#else
#define GOMP_KNC_LINE
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
#ifdef __AMDGCN__
  /* Used on AMD GCN to inform threads how to launch in a team.  */
  struct gomp_thread_start_data thr_start_data;
#elif LIBGOMP_USE_PTHREADS
  /* Cache to help initialise each secondary threads `task` when re-using a
     team very many times.  This allows each secondary thread to perform the
     re-initialisation instead of having the primary thread need to perform
     that initialisation.  */
  struct thread_init {
    struct gomp_task_icv task_icv_init;
    struct gomp_task *task_parent_init;
    struct gomp_taskgroup *task_taskgroup;
    uintptr_t def_allocator;
    unsigned int num_teams;
    unsigned int team_num;
    void (*fn) (void *data);
    void *data;
  } ti;
  struct prev_place_vars {
    unsigned int place_partition_off;
    unsigned int place_partition_len;
    char bind;
  } ppv;
#endif
  bool reused;

  /* This array contains structures for implicit tasks.  */
  struct gomp_task implicit_task[];
=======
  /* This array contains structures for implicit tasks.  Use
     gomp_implicit_task to index it.  */
  struct gomp_task implicit_task[] GOMP_KNC_LINE;
>>>>>>> knc
```

#### `libgomp/team.c`

```diff
<<<<<<< upstream/master
		     + sizeof (team->implicit_task[0]);
      size_t team_extra = nthreads * extra;
      size_t barrier_padding = 0;
      if (barrier_extra_alloc.size)
	{
	  /* `offsetof` in case the structure is padded and `implicit_task` is
	     not at the end of `sizeof (*team)`.  */
	  size_t barrier_offset
	    = offsetof (struct gomp_team, implicit_task) + team_extra;
	  gomp_assert (barrier_extra_alloc.align
			 <= __alignof (struct gomp_team),
		       "barrier extra alignment too large: %lu > %lu",
		       (unsigned long) barrier_extra_alloc.align,
		       (unsigned long) __alignof (struct gomp_team));
	  barrier_padding = ((barrier_offset + barrier_extra_alloc.align - 1)
			     & ~(barrier_extra_alloc.align - 1))
			    - barrier_offset;
	}
      size_t alloc_extra
	= team_extra + barrier_padding + barrier_extra_alloc.size;
=======
		     + GOMP_IMPLICIT_TASK_STRIDE;
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
	  nthr->place = place;
=======
	  nthr->ts.def_allocator = thr->ts.def_allocator;
#ifdef HAVE_SYNC_BUILTINS
	  nthr->ts.single_count = 0;
#endif
	  nthr->ts.static_trip = 0;
	  nthr->num_teams = thr->num_teams;
	  nthr->team_num = thr->team_num;
	  nthr->task = gomp_implicit_task (team, i);
	  nthr->place = place;
	  gomp_init_task (nthr->task, task, icv);
	  gomp_implicit_task (team, i)->icv.nthreads_var = nthreads_var;
	  gomp_implicit_task (team, i)->icv.bind_var = bind_var;
	  nthr->task->taskgroup = taskgroup;
	  nthr->fn = fn;
	  nthr->data = data;
>>>>>>> knc
```

```diff
<<<<<<< upstream/master
      start_data->team = team;
      start_data->team_id = i;

      start_data->active_level = thr->ts.active_level;
=======
      start_data->fn = fn;
      start_data->fn_data = data;
      start_data->ts.team = team;
      start_data->ts.work_share = &team->work_shares[0];
      start_data->ts.last_work_share = NULL;
      start_data->ts.team_id = i;
      start_data->ts.level = team->prev_ts.level + 1;
      start_data->ts.active_level = thr->ts.active_level;
      start_data->ts.def_allocator = thr->ts.def_allocator;
#ifdef HAVE_SYNC_BUILTINS
      start_data->ts.single_count = 0;
#endif
      start_data->ts.static_trip = 0;
      start_data->num_teams = thr->num_teams;
      start_data->team_num = thr->team_num;
      start_data->task = gomp_implicit_task (team, i);
      gomp_init_task (start_data->task, task, icv);
      gomp_implicit_task (team, i)->icv.nthreads_var = nthreads_var;
      gomp_implicit_task (team, i)->icv.bind_var = bind_var;
      start_data->task->taskgroup = taskgroup;
>>>>>>> knc
```

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +67 | -22 |
| `gcc/config.gcc` | +93 | -158 |
| `gcc/config.host` | +10 | -2 |
| `gcc/config/i386/i386-builtins.cc` | +45 | -5 |
| `gcc/config/i386/i386-c.cc` | +10 | -5 |
| `gcc/config/i386/i386-expand.cc` | +3463 | -508 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +142 | -91 |
| `gcc/config/i386/i386-options.h` | +1 | -0 |
| `gcc/config/i386/i386-opts.h` | +2 | -1 |
| `gcc/config/i386/i386-protos.h` | +21 | -16 |
| `gcc/config/i386/i386.cc` | +1369 | -459 |
| `gcc/config/i386/i386.h` | +70 | -48 |
| `gcc/config/i386/i386.md` | +2401 | -1450 |
| `gcc/config/i386/i386.opt` | +24 | -6 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/knc-driver.cc` | +0 | -0 |
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +2036 | -286 |
| `gcc/config/i386/sync.md` | +57 | -3 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/t-knc` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +1 | -1 |
| `gcc/configure` | +1043 | -920 |
| `gcc/configure.ac` | +367 | -378 |
| `gcc/cp/g++spec.cc` | +1 | -1 |
| `gcc/doc/tm.texi` | +177 | -69 |
| `gcc/doc/tm.texi.in` | +55 | -39 |
| `gcc/gcc.cc` | +160 | -59 |
| `gcc/params.opt` | +23 | -5 |
| `gcc/target.def` | +160 | -39 |
| `gcc/tree-ssa-loop-ivcanon.cc` | +9 | -11 |
| `gcc/tree-ssa-loop-ivopts.cc` | +286 | -97 |
| `gcc/tree-ssa-loop-prefetch.cc` | +20 | -12 |
| `libgcc/config.host` | +13 | -23 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +2 | -1 |
| `libgfortran/Makefile.in` | +7 | -2 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +142 | -16 |
| `libgfortran/configure.ac` | +14 | -4 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |
| `libgomp/Makefile.am` | +7 | -5 |
| `libgomp/Makefile.in` | +32 | -25 |
| `libgomp/config/linux/knc/affinity.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/card.h` | +0 | -0 |
| `libgomp/config/linux/knc/futex.h` | +0 | -0 |
| `libgomp/config/linux/knc/guard.ld` | +0 | -0 |
| `libgomp/config/linux/knc/mutex.c` | +0 | -0 |
| `libgomp/config/linux/knc/simple-bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/spincount.h` | +0 | -0 |
| `libgomp/configure` | +135 | -271 |
| `libgomp/configure.ac` | +83 | -27 |
| `libgomp/configure.tgt` | +19 | -16 |
| `libgomp/env.c` | +146 | -6 |
| `libgomp/libgomp.h` | +159 | -11 |
| `libgomp/libgomp.texi` | +907 | -133 |
| `libgomp/team.c` | +462 | -101 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/baseline_symbols.txt` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc-static.ld` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc.ld` | +0 | -0 |
| `libstdc++-v3/src/Makefile.am` | +20 | -0 |
| `libstdc++-v3/src/Makefile.in` | +22 | -1 |

### upstream/releases/gcc-16

Commit: `4b03dde2e3ad210db469ee763194c0cbec22cf45`; date: 2026-11-03T10:43:47+01:00.

Conflicts: 0

Upstream line churn since 16.2 in files changed by KNC:

| File | Added | Removed |
| --- | ---: | ---: |
| `gcc/common/config/i386/i386-common.cc` | +3 | -1 |
| `gcc/config.gcc` | +0 | -0 |
| `gcc/config.host` | +0 | -0 |
| `gcc/config/i386/i386-builtins.cc` | +0 | -0 |
| `gcc/config/i386/i386-c.cc` | +0 | -0 |
| `gcc/config/i386/i386-expand.cc` | +23 | -10 |
| `gcc/config/i386/i386-knc.cc` | +0 | -0 |
| `gcc/config/i386/i386-knc.h` | +0 | -0 |
| `gcc/config/i386/i386-options.cc` | +0 | -0 |
| `gcc/config/i386/i386-options.h` | +0 | -0 |
| `gcc/config/i386/i386-opts.h` | +0 | -0 |
| `gcc/config/i386/i386-protos.h` | +0 | -0 |
| `gcc/config/i386/i386.cc` | +35 | -47 |
| `gcc/config/i386/i386.h` | +0 | -0 |
| `gcc/config/i386/i386.md` | +73 | -28 |
| `gcc/config/i386/i386.opt` | +0 | -0 |
| `gcc/config/i386/imci.md` | +0 | -0 |
| `gcc/config/i386/knc-driver.cc` | +0 | -0 |
| `gcc/config/i386/knc.md` | +0 | -0 |
| `gcc/config/i386/linux-k1om.h` | +0 | -0 |
| `gcc/config/i386/sse.md` | +99 | -54 |
| `gcc/config/i386/sync.md` | +0 | -0 |
| `gcc/config/i386/t-i386` | +0 | -0 |
| `gcc/config/i386/t-knc` | +0 | -0 |
| `gcc/config/i386/x86-tune-sched.cc` | +0 | -0 |
| `gcc/configure` | +1 | -1 |
| `gcc/configure.ac` | +1 | -1 |
| `gcc/cp/g++spec.cc` | +0 | -0 |
| `gcc/doc/tm.texi` | +0 | -0 |
| `gcc/doc/tm.texi.in` | +0 | -0 |
| `gcc/gcc.cc` | +0 | -0 |
| `gcc/params.opt` | +0 | -0 |
| `gcc/target.def` | +0 | -0 |
| `gcc/tree-ssa-loop-ivcanon.cc` | +0 | -0 |
| `gcc/tree-ssa-loop-ivopts.cc` | +8 | -3 |
| `gcc/tree-ssa-loop-prefetch.cc` | +0 | -0 |
| `libgcc/config.host` | +1 | -0 |
| `libgcc/config/i386/knc-cpuinfo.c` | +0 | -0 |
| `libgcc/config/i386/knc-crtfastmath.c` | +0 | -0 |
| `libgcc/config/i386/knc-sfp-machine.h` | +0 | -0 |
| `libgcc/config/i386/t-knc` | +0 | -0 |
| `libgfortran/Makefile.am` | +0 | -0 |
| `libgfortran/Makefile.in` | +0 | -0 |
| `libgfortran/config/fpu-knc.h` | +0 | -0 |
| `libgfortran/config/guard-knc.ld` | +0 | -0 |
| `libgfortran/configure` | +0 | -0 |
| `libgfortran/configure.ac` | +0 | -0 |
| `libgfortran/configure.host` | +0 | -0 |
| `libgfortran/libgfortran.spec.in` | +0 | -0 |
| `libgomp/Makefile.am` | +0 | -0 |
| `libgomp/Makefile.in` | +0 | -0 |
| `libgomp/config/linux/knc/affinity.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.c` | +0 | -0 |
| `libgomp/config/linux/knc/bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/card.h` | +0 | -0 |
| `libgomp/config/linux/knc/futex.h` | +0 | -0 |
| `libgomp/config/linux/knc/guard.ld` | +0 | -0 |
| `libgomp/config/linux/knc/mutex.c` | +0 | -0 |
| `libgomp/config/linux/knc/simple-bar.h` | +0 | -0 |
| `libgomp/config/linux/knc/spincount.h` | +0 | -0 |
| `libgomp/configure` | +0 | -0 |
| `libgomp/configure.ac` | +0 | -0 |
| `libgomp/configure.tgt` | +0 | -0 |
| `libgomp/env.c` | +0 | -0 |
| `libgomp/libgomp.h` | +0 | -0 |
| `libgomp/libgomp.texi` | +0 | -0 |
| `libgomp/team.c` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/baseline_symbols.txt` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc-static.ld` | +0 | -0 |
| `libstdc++-v3/config/abi/post/k1om-linux-gnu/libstdc++-knc.ld` | +0 | -0 |
| `libstdc++-v3/src/Makefile.am` | +0 | -0 |
| `libstdc++-v3/src/Makefile.in` | +0 | -0 |


### S10-05 classification and change size (KNC `1900ea2784e`)

The drill used local refs only: upstream master `b88c2821e219` has fourteen
conflicted files and 27 hunks; gcc-16 `4b03dde2e3ad` has no conflicts. Every
conflict has a textual resolution. The S9-11 hunks are unchanged. New since
S9-11: upstream master adds an `hvml` vector math ABI in the same places where
S10-03 added `knc`. Keep both sides in all four:

| Conflict | Textual resolution |
| --- | --- |
| `i386-opts.h` (1 hunk) | Keep both enum values, `ix86_veclibabi_type_hvml` and `ix86_veclibabi_type_knc`, with a comma between them. |
| `i386-options.h` (1 hunk) | Keep both prototypes, `ix86_veclibabi_hvml` and `ix86_knc_veclibabi`. |
| `i386-options.cc` (1 hunk) | Keep both `case`s in the `ix86_veclib_handler` switch. |
| `i386.opt` (1 more hunk) | Keep both `Enum(ix86_veclibabi)` strings, `hvml` and `knc`. |

Upstream master's libgomp barrier interface change still needs KNC's
`bar.{h,c}` ported before libgomp builds there (S8-11).

Drill log: `.work/_state/logs/S10_05_drill-20261111-071858.log`.

Change size against `releases/gcc-16.2.0` (`git diff --numstat`, default-context hunks; this method gives 719 lines at S9-11's head, which recorded 722):

| Scope | Changed lines | Hunks |
| --- | ---: | ---: |
| Shared i386 files | 730 | 135 |
| `i386-knc.cc` (KNC only) | 2289 | 1 |
| `i386-knc.h` (KNC only) | 122 | 1 |
| `imci.md` (KNC only) | 2158 | 1 |
| `knc.md` (KNC only) | 97 | 1 |
| `linux-k1om.h` (KNC only) | 134 | 1 |
| `knc-driver.cc` (KNC only) | 547 | 1 |
| `t-knc` (KNC only) | 4 | 1 |
| KNC-only i386 total | 5351 | 7 |

Shared i386 files changed since S9-11: S10-01 (`i386.cc`, 3 lines changed)
and S10-03 (`i386.opt`, `i386-opts.h`, `i386-options.h`, `i386-options.cc`:
10 added, 1 changed). So the lead's x86 identity check is needed at this head.
x86 not run (lead).

Build: tree 2 at `1900ea2784e`, full rebuild. The first attempt was killed by
the session's time limit partway through `c-parser.o`; the rerun passed. Log:
`.work/_state/logs/S10_05_build-20261111-073148.log`. Prefix
`gcc-knc-16.2.0-2` reinstalled, and libknc_vmath rebuilt with it
(`tools/s7_09_checks.py install`, log `S10_05_install-20261111-074202.log`).

### S10-05 ICE sweeps

| Flags (also `-march=knc`) | Pass | Compiler error | User inline asm rejected | ICE | Hang | Assembler rejection | Lint failure | Infrastructure failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `-O2 -ftree-vectorize` | 1969 | 32 | 2 | 0 | 0 | 0 | 0 | 0 |
| `-O3` | 1969 | 32 | 2 | 0 | 0 | 0 | 0 | 0 |

Same as S9-11 except `pr108892.c`, which moved from compiler error to pass at
both levels. It passes a 64-byte vector by value, and S9-11 rejected it with
"unsupported KNC register ABI mode". S10-01 gives such vectors a register ABI.
Log: `.work/_state/logs/S10_05_sweep-20261111-074518.log`; summary
`.work/_shared/S10-05/sweep/summary.txt`.

### S10-05 T0-T2

`python tools/check t0 t1 t2 --compiler gcc16` on tree 2: exit 0, 344 PASS, no FAIL.
Log: `.work/_state/logs/check_gcc16_t0_t1_t2-20261111-075224.log`.

### S10-05 card staging (lead runs)

| Card job | Binaries |
| --- | --- |
| Execute suite | `.work/_shared/S10-05/execute/` (1692 sources, 1681 linked, 11 compile errors, 0 ICE, 118 with packed zmm; log `S10_05_execute_build-20261111-080309.log`) |
| Vector math qualification | `.work/_shared/S10-02/knc/qualify_f.mic`, `qualify_d.mic` and `libknc_vmath.a`, rebuilt by the prefix install at this head (`tests/vmath/card_qualify.py --set compare`, then full), under the 3100 and 7100 profiles via `card_run --profile` |
| S10-04 timings | `.work/_shared/S10-04/vmath-bench.mic`, rebuilt with the reinstalled prefix (vec calls all six `__knc_vmath_*` entry points, scl none; lint clean; log `S10_05_bench_build-20261111-074446.log`); `python tools/s10_04_vmath_bench.py card` |

The vector math rows are staged at `1900ea2784e`. Per the lead's note of
2026-11-11 07:21, the vector math card parts rerun after S10-08 at the final
head. The host parts above stand at this head.
