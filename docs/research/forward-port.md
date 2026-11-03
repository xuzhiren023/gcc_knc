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

