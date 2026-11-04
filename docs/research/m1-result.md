# M1 evidence and recommendation (S3-11)

**Recommend adjust; M1 waits.** Measurements use merged `knc`
`eb8fb3e902a91e885354edac02f5edb7751100de` (GCC 16.2), 2026-11-04. The lead decides
against S3-11's seven criteria. S3-23 now supplies a successful trunk C-only
build and T1/T2 evidence, with 16 explained ABI diagnostic failures below.

## Measured: fixture and card evidence

Every `m1_affine` row in [the acceptance README](../../tests/acceptance/README.md):

| README check | GCC 16 result | Where |
| --- | --- | --- |
| T1 off: assemble and lint | PASS | Host, log F |
| T1 affine f32/f64 packed multiply/add and opt-info | PASS | Host, log F |
| T1 recurrence stays scalar | PASS | Host, log F, off/fast function scans |
| T1 fast: packed FMA in both affine loops | PASS | Host, log F |
| T2 machine 181, K1OM loader, compatible symbol versions | PASS, GCC16 and donor drivers | Host, log F |
| T3 GCC16 driver | PASS, `ACCEPT-PASS scalar=3.00 failures=0` | Card, `claude-c0e96863…` (S3-10 batch) |
| T3 donor driver | PASS, same line | Card, `claude-8ccb0f64…` (S3-10 batch) |

Fortran also passes host off/fast assembly, lint, vectorization and runtime-free link (F).
[Card history](card-runs-s3.md) records C off/fast with both drivers at `dd28677d065`, and
Fortran off/fast after S3-08: expected `ACCEPT-PASS`, but no job IDs in those sections.
TLS has four successful IDs there; complex/rounding has six, including both scalar ABI
directions. The last recorded execute batch at this head passed 1,661/1,661.

At the original measurement, S3-10's prepared `tmp/S3-10/batch.txt` said **Native NOT RUN**:
15 rows, including the inexact-input affine check and 1,680 linked execute programs out of 1,692 (11 compile
errors, one ICE). No `.actual.txt` results were present. The lead owns this batch and
its IDs; these rows remain pending here as directed in the ticket's 01:18 answer.

**Lead update, 2026-11-04 03:50.** The lead ran S3-10's batch on the card at `eb8fb3e902a` after this note was measured: every row passes, including `m1_affine` with the GCC 16 driver, the donor driver and the Fortran twin, the inexact-input variant within 1 ULP (`S3-INEXACT PASS failures=0`), and 1,680 of 1,680 torture programs. Job IDs are in [card-runs-s3.md](card-runs-s3.md), section "S3-10 batch". Items 1 and 2 are therefore met at that head.

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
TLS target alternative can retain upstream's new `as_flavor` logic. The generated file
is the same TLS conflict, not a fourth independent logic problem.

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
`gcc-build`, and logs the skipped make check explicitly. The baseline is
`78d4ac73dd391005b895a6148cd9831e28e1208b`; KNC remains `eb8fb3e902a9` (X2).

| x86 options | Identical assembly | Different | Matching failures | Tool errors |
| --- | ---: | ---: | ---: | ---: |
| `-O2` | 1,962 | 0 | 41 | 0 |
| `-O2 -mavx512f` | 1,962 | 0 | 41 | 0 |

Each set has 2,003 sources. Matching failures are neutral in `portability.py`, not
assembly passes: direct `cc1` lacks some header search paths, and the fixed comparison
does not supply all dg-options/target selectors (for example `-fgimple`). Other equal
diagnostics concern redefinitions, flexible-array initializers and target/language
restrictions. Every failed source and its matching diagnostics are listed in X2;
there is no assembly comparison for those sources. Both option sets completed with
exit 0. No difference needs attribution to build paths or IDs. X2 took 47.3 minutes
for reconfiguration, incremental compiler builds and both comparisons combined.

Trunk C-only configure succeeded with the four resolutions above, in
`portability/trunk/build`, targeting `k1om-mpss-linux` with the shared sysroot and
K1OM assembler/linker. The object-only precheck failed twice before a full build:
first, `genmatch` lacked build-host `libcpp.a` (Y0); after building `all-build-libcpp`,
`gentarget-def` rejected **duplicate definition of `atomic_storeti`** (Y1).
`imci.md:249` defines the KNC libcall expander; upstream `sync.md:410` now defines
the same name for `TARGET_128BIT_ATOMIC_ENABLED` using SSE. The stock 16.2 `sync.md`
has no such definition. This is a semantic integration conflict beyond the four
textual Git conflicts, not a C++ error or a proven structural design clash.

Reduced build reproducer: in `portability/trunk/build/gcc`, the failed command was
`build/gentarget-def.exe ../../source/gcc/common.md
../../source/gcc/config/i386/i386.md insn-conditions.md > tmp-target-def.h`
(source paths in the log are absolute). No full trunk `cc1` or trunk T1/T2 ran
in S3-11.
The lead's 03:40 answer assigned the follow-up now tracked as S3-23 to integrate
KNC's libcall dispatch with upstream's expander and retry trunk cc1 and T1/T2.
No third trunk attempt was authorized on S3-11.

S3-23 continuation: the atomic-store entry dispatch in
[the forward-port recipe](forward-port.md#s3-23-atomic-optab-integration)
resolves Y1 without widening an SSE insn. Upstream trunk
`b88c2821e219244d18df873b0bfb344d3dc0b2a7` plus KNC through
`2139411dc6c44e3207c5430304e99b231cbeee2b` and that resolution builds
C-only `cc1` for `k1om-mpss-linux`. The four-job build exhausted memory
(Cygwin user32.dll error 8, no source diagnostic); the lead-authorized
one-job continuation in the same build directory passed in 9.9 minutes,
including the C self-tests. This is infrastructure recovery, not another
source integration conflict.

The full existing T1/T2 selection against trunk took 122.11 seconds and
exited 1: 206 T1 passes, 16 T1 failures, 23 T2 passes. The 16.2 baseline
at KNC `2139411dc6c` has 222 T1 and 23 T2 passes (104.22 seconds).
All 245 ordered row labels match. Every difference is a packed `VAR_GET`
rejection check: all four element types (`float`, `double`, `int`,
`long long`), vector/record shapes and `-O0`/`-O2`.

These 16 rows have one explained **logic** cause. The existing KNC
`ix86_gimplify_va_arg` guard returns `error_mark_node` after its ABI
diagnostic, and `expand_ifn_va_arg_1` subsequently asserts
`gsi_end_p (i)` (`tree-stdarg.cc:1072`, unchanged between the trees).
Trunk's `CHECKING_P=1` exposes the ICE; the 16.2 build has
`CHECKING_P=0`, under which `diagnostics/context.cc` suppresses an ICE
after an earlier error. Both builds enable assertions. Thus the release
test passes its diagnostic/no-ICE condition despite the latent error-path
flaw. This is a remaining ABI error-recovery finding, not evidence of
an atomic-store regression or a structural backend clash. All other
result rows match; no test was changed. The wrapper verifies trunk's C
`cc1` selection but reuses 16.2 Fortran and target runtime; there was no
native card execution in this drill.

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

Rebase cost: the subtarget has measured 56 shared hunks, four trunk conflict files
and the atomic-store name collision, with x86/trunk builds every milestone;
estimate 1-3 engineer sessions per future rebase
if conflicts remain localized. A separate backend avoids most shared i386 merge conflicts,
but must review upstream fixes to the estimated 7.8-12.4k duplicated lines and adapt GCC
target APIs; estimate 2-6 sessions per rebase. These ranges price one resolution/review
and build/test cycle, not measured historical rebases. Recurring conflict/build costs
must be measured before preferring either estimate.

## Decision: go, M1 accepted (lead, 2026-11-04)

The owner delegated the call on 2026-11-03. All evidence is at the final head, GCC `knc`
`f4fa4944b8a` (S3-23 merged; `cc1` SHA-1 `38c0e244086d…`, the same before and after every run
below). Card jobs ran on cores 40-59.

| Item | Result at the final head |
| --- | --- |
| 1 fixture | **Met.** The S3-10 batch was rebuilt at this head and rerun on the card. `m1_affine` prints `ACCEPT-PASS scalar=3.00 failures=0` with the GCC 16 driver, the donor driver and the Fortran twin (`claude-7f195882…`, `claude-fc4468a1…`, `claude-f58c0292…`). Host T1/T2 rows: 245 pass at this tree (S3-23). |
| 2 card batch | **Met.** All 14 S3-10 rows pass: vector, FP and special values at `-O0` and `-O2`, inexact affine within 1 ULP, and the 4 S3-15 complex and rounding rows. The ABI rows' expected files spell the long double `%La` the host way; each of those rows prints 5 × PASS from its own checks, and the values are exactly equal (checked). The full `gcc.c-torture/execute` suite passes **1,681 of 1,681** in six jobs (`claude-42a31411…` to `claude-ec1cf199…`). S3-23's 4-thread atomic counter prints `atomic=400000 sync=400000 expected=400000` (`claude-2b44033c…`). |
| 3 ICE classes | **Met.** Torture compile at `-O2 -ftree-vectorize` and `-O3`: 1,968 pass, 33 compiler errors, 2 rejected user inline asm, **0 ICE** at each (`.work/_shared/tmp/claude-m1-sweep/summary.txt`). S3-20's XI class is fixed. Nothing reaches S3-22's V4SF varargs assert. |
| 4 x86 unchanged | **Met.** 1,962 identical files at `-O2` and at `-O2 -mavx512f` at S3-22's head (`S3_22_x86-20261104-072142.log`). S3-23 changed only the bodies of two `TARGET_KNC` expanders in `imci.md` and KNC-only files, so x86 assembly cannot change. Not rerun on purpose. |
| 5 portability | **Met.** Drill onto master `b88c2821e21`: four conflicts, all textual, as the lead read them. In `i386.cc`, upstream split `ix86_pass_by_reference`; our guard moves to the new wrapper, and `ix86_gimplify_va_arg` keeps its own KNC check. Release branch: 0 conflicts. Trunk with our diff builds C-only after S3-23's single-hook `atomic_storeti` resolution. T1/T2 match 16.2 except 16 packed `VAR_GET` rows. Their cause is our `va_arg` error path, which returns `error_mark_node` and leaves a broken expansion; trunk's checking build reports the ICE, and 16.2 hides it as "confused by earlier errors". Ticket **S3-25**. It is an ordinary bug in a KNC helper, not a design clash. |
| 6 ADR form | **Met.** **184 shared lines in 53 hunks** (lead recount, numstat and `-U3` against `releases/gcc-16.2.0`). There are no shared function bodies. 17 hunks are named exceptions in `.work/_shared/portability/S3-22-hunks.md`: 13 one-line delegations that return a constant instead of the helper's value, and 4 wiring lines (include, hook registration, `pause` expander, build rule). Two hooks sit mid-function (#15, #19) because an entry return would copy upstream classification (rule 3), and the drill shows no conflict at either. |
| 7 cost | **Met, by the lead's reading of the method.** See below. |

**Criterion 7.** S3-11's method compared two independent ranges and found they overlap: subtarget
211-250 engineer sessions to M2 against 208-337 for a separate backend. That comparison has two
flaws.

1. **The cost to M2 counts on both sides with independent ends.** It is the same work on either
   path, so it cancels, and the comparison reduces to the separate backend's estimated cost to M1
   against the subtarget's measured cost to M1.
2. **The separate backend's low end is below what M1 measurably needed.** That low end is 17 +
   36 tickets, but the subtarget itself took 58 tickets. A separate backend needs every
   KNC-specific piece the subtarget built, plus what the subtarget took from i386.
   - **KNC-specific pieces:** IMCI patterns, the vectorizer, the k1om ABI decisions, TLS,
     `libgcc`, and the card harness.
   - **Taken from i386:** S3-11's own estimate of 7.8-12.4k duplicated lines, which is 12-24
     tickets, plus 8-16 tickets of target plumbing.
   - **Not needed:** only the sharing tickets (S3-12, S3-13, S3-22, S3-23).

A conservative floor is therefore 58 − 4 + 12 + 8 = 74 tickets. At the measured 3.17 scripted
engineer sessions per ticket (184 sessions for 58 tickets, `STATUS.md` at 09:45), that is at least
**235 sessions to M1, against the 184 measured**: at least 51 more sessions, about 119M more input
tokens at 2.33M per session. The floor holds at both ends of the M2 range, because the M2 term
cancels. Rebase cost also favours the subtarget: an estimated 1-3 sessions per rebase, against
2-6. The assumptions are stated: the same cost per ticket on both paths, and S3-11's lowest
duplication counts. Manual and lead effort is excluded from both sides, as in S3-11.

**Open after M1, none blocking:**
- **S3-25** (the `va_arg` error path).
- **S3-22's V4SF assert:** add an alignment check (`CURRENT_STATE.md`).
- **S3-10's ABI expected files:** change them to the card's `%La` spelling, so the batch runner
  does not report FAIL on equal values.

Logs below are relative to `.work/_state/logs/`; large outputs stay in the shared area:

- F: `S3_11_fixture-20261104-010634.log` (PASS, 137.43s).
- T: `S3_11_torture-20261104-010618.log` (PASS, sweep 563.859s).
- R: `S3_11_xi_reproducer-20261104-011126.log` (both expected ICEs reproduced).
- D: `S3_11_drill-20261104-010549.log` (PASS, conflict report generated).
- X: `S3_11_x86-20261104-010533.log` (infrastructure failure).
- K: `S3_11_skip_make_red-20261104-011946.log` (expected failure),
  `S3_11_skip_make-20261104-012005.log` (one test PASS).
- X1: `S3_11_x86-20261104-012011.log` (stock built; KNC build resource failure).
- X2: `S3_11_x86-20261104-025052.log` (PASS, four-job retry; both compiler builds and
  both comparisons completed; 47.3 min combined).
- Y0: `S3_11_trunk-20261104-030721.log` (configure 62.201s, support setup 495.744s;
  missing build-host libcpp in the object precheck; 9.6 min overall).
- Y1: `S3_11_trunk-20261104-031823.log` (libcpp prerequisite fixed; duplicate
  `atomic_storeti` during the object precheck; 2.5 min overall, four jobs, `-O2 -g1`).
- S3-23 build: `S3_23_trunk_build-20261104-084307.log` (four-job memory
  exhaustion), `S3_23_trunk_build_serial-20261104-092423.log` (PASS, 9.9 min).
- S3-23 baseline: `S3_23_gcc16_t1_t2-20261104-084102.log` (245 passing rows).
- S3-23 trunk: `S3_23_trunk_t1_t2-20261104-093427.log` (16 explained T1
  failures; other 229 rows pass), `S3_23_result_comparison-20261104-093743.log`
  (PASS, every changed result enumerated).
