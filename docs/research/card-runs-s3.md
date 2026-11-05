# Card runs, Sprint 3

All jobs were run by the lead through `tools/card_run`, under the shared card rules. They used
cores 30-59 (logical CPUs 121-240), and boot ID `e9bfb0ab-e90a-4a5e-9df4-2899a9fd93a4` was
unchanged. No timing figures are given: the ledger shows another agent's jobs overlapping.

## 2026-11-03 evening (UTC 00:15-00:30 on 11-04)

The compiler was the shared GCC 16 build. The vector copy checks used S3-06's branch build (it
contains S3-04 and S3-05); the FP checks used the merged `knc` at `0da1f525ed2` (S3-06's merge).
The sources are in `tests/acceptance/s3_vec_card/`.

| Program | Flags | Result on the card |
|---|---|---|
| `vec_card.c`: S3-04/S3-05 packed copies, 4 types (aligned, zero, pool constant; unaligned pairs at every element offset of source and destination, with sentinels; pairs flush against unmapped guard pages; vectors live across calls at four stack alignments) | `-O0` | `S3-VEC PASS cases=780 failures=0` |
| same | `-O2` | `S3-VEC PASS cases=780 failures=0` |
| same, `-DBROKEN_ALIGN` (negative control: aligned moves on unaligned addresses) | `-O2` | Segmentation fault, as it must |
| `fp_card.c`: S3-06 V16SF/V8DF add, sub, mul and broadcast-multiply, exact values | `-O0` | `S3-FP PASS cases=8 failures=0` |
| same, plus FMA where fused and unfused differ (`vfmadd` present) | `-O2` | `S3-FP PASS cases=10 failures=0` |
| S2-08's 256 `gcc.c-torture/execute` programs, rebuilt with S3-06's branch build at `-O2 -march=knc` | `-O2`, `-j 30` | 256 of 256 PASS |

Card minutes: about 0.18 in total.

Runner issue: two attempts at the torture job were refused with `unknown process identity in
snapshot: b'PROC\t242373\t\tkworker/u:7\t\t'` while a `gpt61` job ran. The third attempt passed.
S3-17 fixes the cause.

## m1_affine, early (2026-11-04 01:50 UTC)

Built with S3-07's branch build (`dd28677d065`, before S3-07 merged): `loops.c` at `-O2
-ftree-vectorize -march=knc`, and `driver.c` by GCC 16 or by the donor. `-fopt-info-vec` reports
both affine loops vectorized with 64-byte vectors. With `-ffp-contract=off` they use `vmulp*` and
`vaddp*`; with `fast`, `vfmadd*`. All four builds lint clean.

| `loops.c` contraction | `driver.c` built by | Card |
|---|---|---|
| off | GCC 16 | `ACCEPT-PASS scalar=3.00 failures=0` |
| off | donor (ABI cross-check) | `ACCEPT-PASS scalar=3.00 failures=0` (first attempt refused by the runner, S3-19) |
| fast | GCC 16 | `ACCEPT-PASS scalar=3.00 failures=0` |
| fast | donor | `ACCEPT-PASS scalar=3.00 failures=0` |

S3-07 merged as `daedd869681`, with no compiler change after `dd28677d065`, so these are the
merged code's results. After the merge, S2-08's 256 torture programs, rebuilt with vectorization on
by default, pass 256 of 256. Only 10 of them contain packed zmm code, so that is a regression check,
not a vector test; the full execute suite follows. Two attempts were refused by the S3-19 race
before one ran.

## Full `gcc.c-torture/execute` suite after S3-07 (2026-11-04 02:30 UTC)

The merged `knc` (`daedd869681`) at `-O2 -march=knc`, vectorization on by default, each file's own
`dg-options` applied. Built on the laptop; six card jobs of up to 300 programs each, `-j 30`.

- Of 1,692 sources: 1,661 linked; 94 of them contain packed zmm code. There were 30 compile errors:
  21 for other targets or features, and 5 the expected "unsupported KNC register ABI mode". There
  was 1 ICE, `pr85169.c` (S3-20).
- **On the card: 1,659 of 1,661 PASS.**
  - `930529-1.c` is a harness failure. My script missed its brace-form `dg-options { "-fwrapv" }`,
    and built with `-fwrapv` it passes.
  - **`pr65369.c` is wrong code from vectorization.** It segfaults; built with
    `-fno-tree-vectorize`, `-O0` or the donor, it passes. SLP put a V16SI `vloadunpackld/hd` pair on
    a byte-aligned address, and the pairs need element alignment (Intel 327364 p.361). S3-21 fixes
    it, and ADR-0005 point 4 is amended.
- No runner refusals in six chunks (S3-18 and S3-19 had merged by then).

## Full execute suite after S3-21 (2026-11-04 03:50 UTC)

S3-21's build (`29781633082`), which has the same compiler sources as the merged `knc`
(`10ce7e12b64`). The suite was rebuilt at `-O2 -march=knc`, with brace-form `dg-options` now
parsed (so `930529-1` gets `-fwrapv`). 1,661 linked, 93 with packed zmm code (`pr65369` no longer
vectorizes), and 1 ICE (`pr85169`, S3-20).

**On the card: 1,661 of 1,661 PASS**, in six chunks with no runner refusals.

## S3-21 before merge (2026-11-04 03:20 UTC)

S3-21's branch build (`29781633082`):

- The engineer's guard program at `-O2` and `-O3` prints `PASS S3-21 all four modes,
  source/destination offsets 0-63, sentinels and guards`.
- `pr65369` rebuilt at `-O2` now exits 0 on the card; before the fix it segfaulted.

## m1_affine with the Fortran twin, after S3-08 (2026-11-04 02:45 UTC)

`driver.c -DKNC_WITH_FORTRAN`, `loops.c` and `affine_fortran.f90` (GCC 16 `gfortran`, vectorized),
at contraction `off` and `fast`: both print `ACCEPT-PASS scalar=3.00 failures=0`.

## FP state and special values (2026-11-04 01:30 UTC)

`tests/acceptance/s3_vec_card/fp_special.c`, built with S3-07's branch build (`dd28677d065`,
which contains S3-06), at `-O0` and `-O2`, `-lm`. Both print `S3-FPSPECIAL PASS cases=96
failures=0`.

- **Startup state without fast-math:** MXCSR `0x00200000` (bit 21 only: no FTZ, no DAZ, so
  gradual underflow) and x87 control word `0x037f`.
- **CPUID leaf 1:** `eax=0x00000b12 edx=0x1101137f`, so **SSE and SSE2 are reported absent**. A
  runtime that gates MXCSR writes on CPUID SSE, like libgfortran's `config/fpu-387.h`, skips them:
  it does not fault, but it also leaves the vector unit's exceptions and rounding unmanaged.
- **Lanes:** V16SF and V8DF add, sub and mul on ±0, ±∞, NaN, the smallest normal, ±subnormals, the
  largest finite value and half-normals all match an x87 long double reference rounded to the
  element type. That covers the sign of zero, and subnormal results are kept rather than flushed.
- **Flags** seen by `fetestexcept`: the same for vector and x87 ops. `inexact` on 1+1e-30,
  `invalid` on ∞-∞, `overflow inexact` on MAX×4, and nothing on an exact subnormal product, as
  IEEE says.

One first `-O0` attempt ended `infrastructure-failure` (exit 126). Its reason was not kept, and 5
`hello` reruns passed; S3-18 keeps receipts so the next one can be diagnosed.

After S3-17 merged (runner fix): `hello` matched, and the same 256 torture programs passed 256 of 256 while a `gpt61` job overlapped.

## Native TLS after S3-14 (2026-11-04 04:30 UTC)

Built with S3-14's branch build (`cc1` from `0235ff44771`, HAVE_AS_TLS defined). S3-14 merged as
`edf7c69d617`; the merge differs only in the reverted picflag lines, which do not reach `cc1`, so
these are the merged compiler's results. Sources and build: `tests/acceptance/s3_tls_card/`. Every
GCC 16 object and library was checked for `__emutls` before linking (none), and all lint clean.

Each of 4 threads writes its own value to `__thread` variables defined by the donor, by GCC 16 and
in a shared library, then reads them back through the other compiler's code after a barrier; the
main thread must still see the initial values.

| Variant | Built how | Card job | Result |
|---|---|---|---|
| A | main and `tls_new` by GCC 16 `-O2`; `tls_donor` and the `.so` by the donor | `claude-985a0cc8…` | `S3-TLS PASS checks=59 failures=0` |
| B | as A, GCC 16 at `-O0` | `claude-e8a82b81…` | same |
| C | main by the donor; `tls_new` and the `.so` (global- and local-dynamic) by GCC 16 `-O2` | `claude-41ac1b6a…` | same |
| D | as C, GCC 16 at `-O0` | `claude-80f64600…` | same |
| X | control: plain globals instead of `__thread` | `claude-ebd13244…` | `S3-TLS FAIL checks=59 failures=46`, exit 1, as it must |

This ticks S3-14's native line: donor-defined used from GCC 16, the reverse, and a donor `.so`,
each from 4 threads. S3-10 need not rebuild it.

## Full `gcc.c-torture/execute` suite after S3-14 (2026-11-04 04:45-04:58 UTC)

The merged `knc` (`edf7c69d617`, native TLS) at `-O2 -march=knc`, built with
`harness/card/build_suite.py` before S3-15's rebuild started (`cc1` unchanged from start to end of
the build). 1,692 sources, 1,661 linked, 93 with packed zmm code, 30 compile errors as before, and
1 ICE (`pr85169`, S3-20). **On the card: 1,661 of 1,661 PASS**, in six jobs, with no retries. That
is the same as the baseline at `10ce7e12b64`, so native TLS caused no regression.

## S3-15: complex values and rounding mode across calls (2026-11-04 05:35 UTC)

The cross-links S3-15's T2 left in `.work/_shared/scalar-abi/`, built at 00:29 local by S3-15's
branch build (`cc1` of 00:24, from `eb2efcdcf04`). S3-15 merged as `eb8fb3e902a` with no compiler
change after that, and `cc1` was not rebuilt, so these are the merged compiler's results. All lint
clean. Suffix `-0` is a GCC 16 caller and donor callee, `-1` the reverse.

| Program | Card | Result |
|---|---|---|
| `abi-gaps-O0-0`, `-O0-1`, `-O2-0`, `-O2-1` | `claude-a49bd551…`, `claude-c0c8a9b0…`, `claude-36f63a5c…`, `claude-12a37489…` | `complex ABI PASS` with `_Complex float`, `double` and `long double` exact (long double keeps its 2^-60 tail); `rounding PASS` in all 4 modes |
| `scalar-abi-O2-0`, `-O2-1` (S2-02's suite, now built with `-frounding-math`) | `claude-c6ef8fff…`, `claude-78afe6b4…` | `S2-02 scalar ABI PASS` |

The rounding case adds 2^-53 to ±1, a halfway value, so each mode stores a different double; it
also checks that the x87 control word and MXCSR rounding bits are the same before and after the
call. `fesetround` on the card sets both. A mode lost across the call would print a wrong value,
so the expectations are their own control.

Full execute suite after S3-15 (`eb8fb3e902a`): the build gives the same result for every one of
the 1,692 sources as after S3-14 (the new guard rejects nothing that compiled before), and on the
card **1,661 of 1,661 PASS**, six jobs, no retries.

## S3-10 batch (2026-11-04 06:05-06:30 UTC)

Built by S3-10 from merged `knc` `eb8fb3e902a` (S3-15, native TLS) into `.work/_shared/tmp/S3-10/`
(`batch.txt`); all programs lint clean. Run by the lead, one card job per row, the torture list in
six jobs at `-j 30`. Receipts and raw output: `.work/_state/card/S3-10/`.

| Row | Card job | Result |
|---|---|---|
| `claude-m1` (`m1_affine`, GCC 16 both units, `-ffp-contract=off`) | `claude-c0e96863…` | `ACCEPT-PASS scalar=3.00 failures=0` |
| `claude-m1-donor` (driver by the donor: ABI cross-check) | `claude-8ccb0f64…` | same |
| `claude-m1-fortran` (Fortran twin of the loops) | `claude-cf4fb526…` | same |
| `claude-vec-O0`, `-O2` (S3-04/05 packed copies) | `claude-1751bdce…`, `claude-50579eb4…` | `S3-VEC PASS cases=780 failures=0` |
| `claude-fp-O0`, `-O2` (S3-06 arithmetic, FMA at `-O2`) | `claude-d41924d5…`, `claude-8c5efcaa…` | `S3-FP PASS` |
| `claude-special-O0`, `-O2` (signed zeros, ∞, NaN, subnormals, flags) | `claude-5b586e13…`, `claude-cb9cff4c…` | `S3-FPSPECIAL PASS cases=96 failures=0` |
| `claude-abi-O0-0`, `-O0-1`, `-O2-0`, `-O2-1` (S3-15 complex and rounding, both ways) | `claude-2588b1c9…`, `claude-9a8b3c58…`, `claude-cc92f081…`, `claude-1b508f28…` | `complex ABI PASS` and 4 × `rounding PASS`. The expected files differ only in `%La` spelling of the same long double (host libc `0x1.c00000000000001p+0`, card glibc `0xe.000000000000008p-3`); the program compares the values exactly |
| `claude-inexact` (affine f32 and f64, contraction on, inexact inputs, offsets 0-15) | `claude-6a72ef8a…` | `S3-INEXACT PASS failures=0`: every element within 1 ULP of a long double reference; 0 elements differ between the x87 peel or remainder and the vector body at every offset |
| 1,680 `gcc.c-torture/execute` programs, `-O2 -march=knc` | six jobs | **1,680 of 1,680 PASS** |

S3-14's TLS cross-check passed earlier on the same compiler (above). S3-10 links 1,680 of 1,692
torture sources against the lead harness's 1,661: `harness/card/build_suite.py` passed Windows
paths to the Cygwin driver, so 19 sources with quoted includes failed to compile there. Fixed in
the harness (forward-slash paths); those 19 are in the 1,680 above.

**Sprint 3's card batch passes in full.** `pr85169` (S3-20) is the only execute source not
covered, because it ICEs.

## Full suite after S3-20 (`73cc9c03798`, lead, 2026-11-04 04:20)

`cc1` built from S3-20's tested commits (`086fe1c3cc7`, tree identical to the merge); its SHA-1
was the same before and after the suite build, so S3-22's build did not overlap. 1,692 sources,
**0 ICE**, 11 compile errors (the expected `dg-` options and targets), 1,681 linked. On the card in
six jobs (`claude-caee0087…` to `claude-a60b2c4c…`, receipts in
`.work/_state/card/claude-suite-s3-20/`): **1,681 of 1,681 PASS**, `pr85169` included.

## M1 final head (lead, 2026-11-04)

GCC `knc` `f4fa4944b8a` (S3-23 merged; tree identical to the tested `2139411dc6c`). `cc1` SHA-1
`38c0e244086dfd98b977dfa67cd201e46f82d9c9` before and after every build and run below. These are
the first runs on cores 40-59 (logical CPUs 161-240) after the owner's allocation change.

- Execute suite: 1,692 sources, **0 ICE**, 11 compile errors, 1,681 linked, 98 with packed zmm.
  Six jobs (`claude-42a31411…` to `claude-ec1cf199…`, receipts in
  `.work/_state/card/claude-suite-m1/`): **1,681 of 1,681 PASS**.
- S3-10 batch, rebuilt into `.work/_shared/tmp/claude-s3-10-m1/` from copies of
  `tools/{prepare,run}_s3_10.py` with only the output directory changed, because the original
  directory's files belong to the sandbox user. 14 rows, torture excluded (covered above), all
  program exit 0. The 10 non-ABI rows match their expected files byte for byte, `m1_affine`
  three ways included. The 4 ABI rows print 5 × PASS each; their expected files differ only in
  the host's `%La` spelling of equal long double values (checked exactly), as in S3-10's run.
- S3-23 atomic counter, relinked with the donor's static `libatomic.a`, lint clean:
  `atomic=400000 sync=400000 expected=400000` (`claude-2b44033c…`).

## Sprint 4: S4-09 merged (lead, 2026-11-04)

GCC `knc` `04cd3cfc307`, `cc1` SHA-1 `760061600d09…`. `tests/acceptance/s4_masks` passes 1,576,200
checks at `-O2 -ftree-vectorize` (`claude-5da7c514…`) and `-O3` (`claude-5f80806a…`). The negative
control fails (`claude-7d93916c…`), and the guard control faults on the guard page
(`claude-cde346e2…`). The execute suite: 1,681 linked, 0 ICE, **1,681 of 1,681 PASS** in six jobs
(`claude-aeb81556…` to `claude-26812bbb…`).

## Sprint 4: S3-09 merged (lead, 2026-11-04)

GCC `knc` `7836668cc9a`, `cc1` SHA-1 `0c72b4b06626…`. `tests/acceptance/s4_masks` (its integer
kernels now use `vpaddd`, `vpsubd` and `vpmulld`) passes 1,576,200 checks at
`-O2 -ftree-vectorize` (`claude-21ae9dba…`) and at `-O3` (`claude-62b73842…`).

## Sprint 4: S4-02 merged (lead, 2026-11-04)

GCC `knc` `e201456c64b`, `cc1` SHA-1 `b10511dacf36…` (the same before and after the builds). `s4_masks`
(12 vector compares in its kernels) passes 1,576,200 checks at `-O2 -ftree-vectorize`
(`claude-43a66c94…`) and at `-O3` (`claude-80b60912…`). Execute suite: 1,681 linked, 0 ICE,
102 with packed zmm, **1,681 of 1,681 PASS** at `-j 60` (`claude-40988071…` to `claude-603a66ff…`).
That covers the three scalar functions whose register allocation changed with `*knc_movqi`.
Earlier, the post-S4-09 suite rerun at `-j 60` with 96 MiB per program also passed 1,681 of 1,681,
which validated the owner's 3-threads-per-core rule.

## Sprint 4: S4-12 merged, packed staging (lead, 2026-11-04)

`hello` passes through the new path (`claude-ca84a867…`, pinned to logical CPUs 161-240). The full
execute suite from S4-02's build runs as **one** job through `--file-list` at `-j 80` with 96 MiB per
program (7,680 MiB, inside the 10 GiB budget): **1,681 of 1,681 PASS** (`claude-685d1bc9…`). Before,
it took six jobs of 300 files, with about 600 SSH connections each.

## Sprint 4: S4-03 merged (lead, 2026-11-04)

GCC `knc` `ae8a033c5f3`, `cc1` SHA-1 `ef3ff3ec0fc6…` (the same before and after). `s4_masks` (56 masked
operations and 12 compares in its kernels) passes 1,576,200 checks at `-O2 -ftree-vectorize`
(`claude-a87b9b50…`), at `-O3` (`claude-981cb27c…`) and at `-O2 -ftree-vectorize -fno-trapping-math`
(`claude-52205208…`). The last build is the only one with a `vcmpnltps`, from S4-03's UNGE-as-nlt
mapping, so that mapping is exact on real NaNs. Execute suite: 1,681 linked, 0 ICE, 103 with packed
zmm, **1,681 of 1,681 PASS** in one packed job (`claude-54700e73…`).

## Sprint 4: S4-04 merged (lead, 2026-11-04)

GCC `knc` `0d5b9f4563f`, `cc1` SHA-1 `dd3ada06a18a…` (the same before and after). `s4_masks`, now with
S4-05's aligned kernels and with `vpaddsetcd`/`vpsubsetbd` carry sequences in `add_i64`/`sub_i64`,
passes 1,589,070 checks at `-O2 -ftree-vectorize` (`claude-40374bef…`), `-O3` (`claude-486a2498…`),
`-fno-trapping-math` (`claude-be006d9e…`) and `-fvect-cost-model=unlimited` (`claude-48d96b03…`).
That last build forces S4-03's element-wise misaligned fallback, which was untested until now; it
is exact and stays inside the arrays. The aligned guard control faults on the guard line after the
array (`kernel=add_al_f32 n=1 where=2`, real address; `claude-c47aa755…`). Execute suite: 1,681
linked, 0 ICE, 104 with packed zmm, **1,681 of 1,681 PASS** in one job (`claude-748d87e7…`).

## Sprint 4: S4-05 merged (lead, 2026-11-04)

GCC `knc` `20a310961ac`, `cc1` SHA-1 `65a88218b1ad…` (the same before and after). The aligned kernels now
end in masked epilogues (31 GPR-to-`k` mask moves at `-O2`). `s4_masks` passes 1,589,070 checks at
`-O2 -ftree-vectorize` (`claude-41f25ed4…`), `-O3` (`claude-8c3d968c…`), `-fno-trapping-math`
(`claude-177f1ddc…`) and `-fvect-cost-model=unlimited` (`claude-9dc32942…`). Each aligned array
ends on a line boundary with a guard page after it, so the empty-mask epilogues at n = 16, 32, 48
and 64 prove the guards. The aligned guard control faults as designed (`claude-d7b318ca…`). S3-10
rows rebuilt at this head: `m1_affine` (GCC 16, donor and Fortran drivers), inexact, vector-O2 and
FP-O2 pass. ABI-O2-0 prints 5 × PASS with equal values; its expected file came from a stale lead
copy without S4-08's spelling fix, and the copy is now refreshed. Execute suite: **1,681 of 1,681
PASS** (`claude-11534d89…`).

## Sprint 4 head (lead, 2026-11-05, owner allowed the run)

GCC `knc` `c759f17f1b9` (S4-14's merge, the sprint head), `cc1` SHA-1 `2818504de6f7…`. `s4_masks`
passes 1,589,070 checks in all six data builds: `-O2 -ftree-vectorize` (`claude-a61fe776…`), `-O3`
(`claude-15c668c2…`), `-fno-trapping-math` (`claude-1d7adbc4…`), and the three builds that force
S4-14's guarded split: `-fvect-cost-model=unlimited` (`claude-c6e04c26…`), plus
`--param vect-max-peeling-for-alignment=0` (`claude-0007e7ff…`) and
`--param vect-partial-vector-usage=1` (`claude-ab2e0a4d…`). Those three hold 18, 18 and 171 `vpermd`
rotations, and the `-O2` build holds none, so the split ran on real hardware for the first time: exact
at every length 0-65 and offset 0-15, inside guard pages on both sides. The aligned guard control
faults on the guard line after the array as designed (`kernel=add_al_f32 n=1 where=2`,
`claude-1df30e7a…`). Execute suite: 1,681 linked, 0 ICE, **1,681 of 1,681 PASS** in one packed job.
S3-10 rows rebuilt at this head (`claude-s3-10-m1`, compiler `c759f17f1b9`): all 14 match their
expected files: `m1_affine` with the GCC 16, donor and Fortran drivers (`claude-55d3f4a7…`,
`claude-0c08605c…`, `claude-f19bea17…`), vector, FP and special values at `-O0` and `-O2`, the four
ABI cross-links, and inexact (`claude-e5c64f9d…`).
