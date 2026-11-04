# M1 evidence and recommendation (S3-11)

**Recommend adjust; M1 waits.** Measurements use merged `knc`
`eb8fb3e902a91e885354edac02f5edb7751100de` (GCC 16.2), 2026-11-04. The lead decides
against S3-11's seven criteria. Missing x86/trunk evidence cannot count as success.

## Measured: fixture and card evidence

Every `m1_affine` row in [the acceptance README](../../tests/acceptance/README.md):

| README check | GCC 16 result | Where |
| --- | --- | --- |
| T1 off: assemble and lint | PASS | Host, log F |
| T1 affine f32/f64 packed multiply/add and opt-info | PASS | Host, log F |
| T1 recurrence stays scalar | PASS | Host, log F, off/fast function scans |
| T1 fast: packed FMA in both affine loops | PASS | Host, log F |
| T2 machine 181, K1OM loader, compatible symbol versions | PASS, GCC16 and donor drivers | Host, log F |
| T3 GCC16 driver | Earlier PASS; final S3-10 batch NOT RUN | Card history below |
| T3 donor driver | Earlier PASS; final S3-10 batch NOT RUN | Card history below |

Fortran also passes host off/fast assembly, lint, vectorization and runtime-free link (F).
[Card history](card-runs-s3.md) records C off/fast with both drivers at `dd28677d065`, and
Fortran off/fast after S3-08: expected `ACCEPT-PASS`, but no job IDs in those sections.
TLS has four successful IDs there; complex/rounding has six, including both scalar ABI
directions. The last recorded execute batch at this head passed 1,661/1,661.

S3-10's prepared `tmp/S3-10/batch.txt` explicitly says **Native NOT RUN**: 15 rows, including
the inexact-input affine check and 1,680 linked execute programs out of 1,692 (11 compile
errors, one ICE). No `.actual.txt` results were present. The lead must run this batch and
record its IDs; readiness and the earlier 1,661-program run cannot establish its results.

## Measured: lines and ADR-0006 form

Sprint measure: Git numstat additions plus deletions against `releases/gcc-16.2.0` in
`gcc/config/i386` and `gcc/common/config/i386`, excluding the four KNC-only files below.
Hunks use default three-line context. Columns are cumulative: S0 = release (all zero),
S1 = `6d879ee3154`, S2 = `bdcb9b5c10d`, S3 = final head, not intermediate edit totals.
Paths are under `gcc/config/i386`, except
`i386-common.cc` under `gcc/common/config/i386`.

| File | S1 | S2 | S3 | Final + / - | Final hunks |
| --- | ---: | ---: | ---: | --- | ---: |
| `i386-common.cc` | 3 | 3 | 3 | +3/-0 | 1 |
| `i386-c.cc` | 9 | 15 | 9 | +9/-0 | 2 |
| `i386-expand.cc` | 0 | 39 | 8 | +8/-0 | 4 |
| `i386-options.cc` | 16 | 16 | 5 | +5/-0 | 1 |
| `i386-protos.h` | 0 | 1 | 2 | +2/-0 | 1 |
| `i386.cc` | 0 | 112 | 73 | +61/-12 | 27 |
| `i386.h` | 9 | 11 | 11 | +8/-3 | 3 |
| `i386.md` | 0 | 21 | 22 | +19/-3 | 4 |
| `i386.opt` | 4 | 4 | 4 | +4/-0 | 1 |
| `sse.md` | 0 | 0 | 40 | +26/-14 | 8 |
| `sync.md` | 4 | 21 | 21 | +15/-6 | 3 |
| `t-i386` | 0 | 0 | 4 | +4/-0 | 1 |
| **Shared total** | **45** | **251** | **202** | **+164/-38** | **56** |
| `imci.md` (KNC only) | 0 | 240 | 430 | +430/-0 | 1 |
| `i386-knc.cc` (KNC only) | 0 | 0 | 424 | +424/-0 | 1 |
| `i386-knc.h` (KNC only) | 0 | 0 | 60 | +60/-0 | 1 |
| `linux-k1om.h` (KNC only) | 63 | 72 | 72 | +72/-0 | 1 |
| **KNC-only total** | **63** | **312** | **986** | **+986/-0** | **4** |

Between sprint endpoints, shared churn is 45/206/233 and KNC-only churn 63/249/676;
these count relocation/removal too. Shared cumulative size falls by 49 in S3 while its
hunks rise from 37 to 56. Outside this measure: `gcc/config.gcc` 29, `gcc/config.host` 1,
`gcc/configure{,.ac}` 10 each, `libgcc/config.host` 12; KNC runtime files
`knc-crtfastmath.c` 37, `knc-sfp-machine.h` 13, `t-knc` 17. Whole fork: 24 files,
+1,257/-60 = 1,317 changed lines, including generated configure.

S3-13 moved helper bodies/prototypes to `i386-knc.*`; `i386-protos.h` now only includes
the KNC header. Shared vector changes are expanders/iterators, not widened SSE insns.
Nevertheless a strict rules 1-4 audit is **not clean**: `ix86_zero_call_used_regs` still
contains a KNC error/return block; `setup_incoming_varargs_64` still selects TI transport
and emits the KNC save; `ix86_target_macros` directly undefines the CAS macro. These are
small relocatable blocks, not evidence of a structural backend clash. Lead review/tickets
are needed before marking criterion 6 met. No GCC fix was included in this research ticket.

## Measured: ICE classes

Final-head compile sweep (T): **PASS**, 2,003 compile sources per option set, four workers,
563.859s. `-march=knc` throughout; existing per-file unconditional dg-options are appended
by `tools/torture_compile.py` (M1 wrapper explicitly adds `-ftree-vectorize` at O2).

| Options | Compile/assemble/lint pass | Compiler error | User inline asm rejected | ICE |
| --- | ---: | ---: | ---: | ---: |
| `-O2 -ftree-vectorize` | 1,968 | 33 | 2 | 0 |
| `-O3` | 1,968 | 33 | 2 | 0 |

Both sets have zero hangs, slow retries, FP ABI errors, generated assembler rejections,
lint failures and infrastructure failures. No shared SSE/AVX ICE class is open in this
sweep. Full classifications are in `.work/_shared/torture-compile-summary.txt`, with
failure diagnostics in `.work/_shared/torture-compile/{O2,O3}/`. This is compile/assemble/
lint, not execution or the complete DejaGNU target-selector matrix.

Separately, S3-10's execute-corpus compile still has **one open class, S3-20**: XImode
memory-to-memory transport, unrecognizable insn in `extract_insn` during `vregs`.
This reduced case ICEs at both requested option sets at the final head (R; wrapper PASS
means reproduced ICE). It lacks KNC transport legalization, not an SSE/AVX assertion.

```c
typedef char V __attribute__((vector_size(64)));
static void __attribute__((noipa)) foo(V *p) {
  V v = *p; v[63] = 1; *p = v;
}
int main(void) { V v = (V){}; foo(&v); return v[63] != 1; }
```

The packed unnamed-argument ABI class is fixed by S3-15 (early KNC type guards): a
reduced shape is `typedef float V __attribute__((vector_size(64))); extern void f(int,...);
void g(V *p) { f(0,*p); }`. The VAR_GET/MS variants in `tests/regress/knc-abi-gaps.c`
and final-head host checks (F) verify diagnostics instead of an ICE. Shared SSE register
assumptions were the source of that ABI class; rejection of an unsupported ABI is intentional.

## Measured: portability and x86

[Final drill](forward-port.md), log D: newest locally available master
`b88c2821e219` (2026-11-03) has four conflict files; release branch `4b03dde2e3ad`
(2026-11-03) has zero. No fetch occurred. Master conflicts: `i386-c.cc` (comment typo
beside our macro hook); `i386.cc` (upstream extracted `ix86_pass_by_reference_abi`, while
our entry guard and cumulative-argument declaration occupy the old context);
`configure.ac` and generated `configure` (upstream Solaris assembler detection changed
next to our k1om TLS case). The ABI entry guard can stay in the public wrapper and the
TLS target alternative can retain upstream's new `as_flavor` logic, but these resolutions
have **not** been built. They look localized; calling all four proven textual conflicts
would overstate the evidence. The generated file is the same TLS conflict, not a fourth
independent logic problem.

The four scratch-tree resolutions preserve KNC behavior: `i386-c.cc` keeps the macro
hook and upstream's comment spelling (**textual**); `i386.cc` keeps the ABI type guard
in the public `ix86_pass_by_reference` wrapper, before the cumulative-argument lookup,
and upstream's extracted helper (**textual relocation**, no guard logic change).
`configure.ac` and generated `configure` retain upstream's `as_flavor` test while
adding K1OM to the target alternative (**textual**, same TLS behavior). None required
redesigning KNC logic. Build/test evidence is reported separately below.

The initial x86 invocation failed before builds because `tasklist.exe` returns Access
denied (X). The lead-authorized `--skip-make-check` now prints `make check skipped`;
one tool test went red then passed (K). Before the retry, no build of this ticket was
running (`Get-Process make` returned none). Stock x86 C-only `cc1` built, but the KNC
x86 build stopped with Cygwin `unable to load user32.dll, Win32 error 8` (X1), an
infrastructure resource failure. The retry uses four jobs instead of eight, retains
the existing objects and separate `portability/x86-{a,b}/build` directories outside
`gcc-build`, and logs the skipped make check explicitly.

## Measured cost versus estimates

[STATUS.md](../../STATUS.md), snapshot at session start: 54/57 tickets done; scripted
engineers 173 sessions / 362.7M input tokens, lead 172 / 55.9M; manual Claude 7 / 516.8M
and GPT 1 / 0.9M (manual roles unattributed). Total 353 sessions / 936.3M input tokens;
context rereads are included, so these are not uncached billing tokens. The 1,317-line
fork is not the whole project effort: the totals include harness, tools and research.
S0-06's measured log reports configure 60.112s, full C+Fortran all-gcc 2,725.762s,
`i386.cc` incremental 168.536s, `i386.md` incremental 264.552s, build 2.304 GiB logical.
Source: `.work/_state/logs/S0_06_timing-20261102-065354.log`. Those are historical
measurements, not promised final-head rebuild times.

**Estimated separate-backend duplication**, sized from stock GCC 16.2 source, informed by
[donor inventory](donor-inventory.md): retain the indicated fraction of each source span,
discarding x86 variants while preserving KNC semantics. Bounds are judgments, not measured
implementations. Retained lines include comments/blank lines, like the sprint measure.

| Responsibility | GCC16 source span(s), inclusive | Retained fraction | Estimated lines |
| --- | --- | --- | ---: |
| x87 conversions/arithmetic | `i386.md` 5311-6500, 23894-26027 | 40-60% of 3,324 | 1,330-1,994 |
| Integer arithmetic/shifts | `i386.md` 6501-10500, 14501-19000 | 25-40% of 8,500 | 2,125-3,400 |
| ABI classification/varargs | `i386.cc` 1800-5240 | 40-65% of 3,441 | 1,376-2,237 |
| Frame/prologue/epilogue | `i386.cc` 6076-10825 | 35-55% of 4,750 | 1,662-2,613 |
| Atomics/fences | `sync.md` 1-1285 | 30-55% | 386-707 |
| Scalar transfers | `i386.md` 2388-5310 | 30-50% of 2,923 | 877-1,462 |

Estimated duplication: **7,756-12,413 lines**, before address/constraint/output plumbing
and IMCI; source samples are not complete dependencies. Donor's 85-file +1,498/-278 diff
extends i386 and supplies no packed arithmetic/vectorizer patterns, per its inventory.

Effort estimate method: use 173/54 = 3.20 scripted engineer sessions per completed ticket
(2.10M input tokens/session) as a rough calibration, not a causal productivity rate.
For a separate backend from the start, assume 17 common foundation tickets plus 36-64
backend/validation tickets: 12-24 across the six responsibilities above, 8-16 target
plumbing, 8-12 IMCI/vectorization, 8-12 integration/validation. That gives **170-260
sessions / 356-545M tokens to M1**. Foundation count is a proxy; overlap/retained fractions
and unusually large manual runs make this estimate weak. Identical existing IMCI assets
could lower a switch's future cost; all actual spending would remain sunk.

To M2, estimate another 12-24 ticket-equivalents (38-77 sessions / 80-161M tokens) on
either path for more operations, masks/control, costing and validation. Subtarget total:
**211-250 scripted engineer sessions / 443-524M tokens**, using its measured 173/362.7M
baseline. Separate from-start total: **208-337 / 436-706M**. Manual/lead effort is excluded
from both estimates because comparable role attribution is absent. Ranges overlap:
criterion 7's strict cost inequality is **not established**; neither is a robust reversal.

Rebase cost: the subtarget has measured 56 shared hunks and four trunk conflict files,
plus x86/trunk builds every milestone; estimate 1-3 engineer sessions per future rebase
if conflicts remain localized. A separate backend avoids most shared i386 merge conflicts,
but must review upstream fixes to the estimated 7.8-12.4k duplicated lines and adapt GCC
target APIs; estimate 2-6 sessions per rebase. These ranges price one resolution/review
and build/test cycle, not measured historical rebases. Recurring conflict/build costs
must be measured before preferring either estimate.

## Decision against S3-11's fixed criteria

| Item | Assessment |
| --- | --- |
| 1 fixture | Host green; final S3-10 native rows pending. Not met. |
| 2 card batch | Final batch/inexact native results absent; earlier results do not substitute. Not met. |
| 3 ICE classes | Met in the requested sweep: zero shared SSE/AVX ICEs; other class S3-20 is ticketed and reproduced. |
| 4 x86 unchanged | Infrastructure blocked before builds. Unmeasured. |
| 5 portability | Release clean; four trunk conflict files, no trunk build/T1/T2. Not met. |
| 6 ADR form | 202 shared lines/56 hunks; residual blocks need relocation/review. Not met. |
| 7 cost | Smaller source surface measured; effort estimates overlap. Not proven. |

No structural clash is demonstrated. The lead must resolve/ticket items 4-6, tighten
item 7, run S3-10 and decide again after required fixes merge. S3-20 is a listed,
ticketed non-SSE/AVX class; criterion 3 does not itself require that class to close.

Logs below are relative to `.work/_state/logs/`; large outputs stay in the shared area:

- F: `S3_11_fixture-20261104-010634.log` (PASS, 137.43s).
- T: `S3_11_torture-20261104-010618.log` (PASS, sweep 563.859s).
- R: `S3_11_xi_reproducer-20261104-011126.log` (both expected ICEs reproduced).
- D: `S3_11_drill-20261104-010549.log` (PASS, conflict report generated).
- X: `S3_11_x86-20261104-010533.log` (infrastructure failure).
- K: `S3_11_skip_make_red-20261104-011946.log` (expected failure),
  `S3_11_skip_make-20261104-012005.log` (one test PASS).
- X1: `S3_11_x86-20261104-012011.log` (stock built; KNC build resource failure).
