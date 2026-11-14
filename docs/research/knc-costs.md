# KNC costs v1 (S6-05)

`-march=knc` implies `-mtune=knc`. The KNC tuning selects its own
`processor_costs`, including when target options are restored between functions.
It does not enable SSE or AVX. Size optimization retains the x86 size table.

The source of measured values is
`docs/research/knc-characterization.md` (S6-03, 2026-11-06), especially
points 1–8 and the named `.rt` rows. Each initializer in `i386-knc.cc`
identifies its source or labels an estimate and its reason. Costs use core
throughput: one cycle per vector operation and half a cycle per independent
mask operation. Scalar integer additions use the measured dependent latency
of one core cycle at four threads: the independent half-cycle throughput
underprices induction-variable recurrences. GCC instruction costs use
`COSTS_N_INSNS`; register and
memory move costs use twice the cycle count.

`--param=knc-threads-per-core=N` accepts 1–4 and defaults to 4. The measured
four-cycle add/multiply/FMA latency needs two independent chains at 1, 2 or
3 threads, and one at 4 threads. One thread cannot issue more often than
every other cycle, so four accumulators are unnecessary. KNC addition and
multiplication reductions feed the existing x86 `reduc_lat_mult_thr` /
`m_suggested_unroll_factor` path. The table caps vector unrolling at two;
the existing `--param=ix86-vect-unroll-limit` remains available. Floating
point reassociation still requires explicit permission such as `-ffast-math`.

**Historical S6 defaults, superseded as current settings (S12-13, 2026-11-14).**
The cache defaults are L1 32 KB, L2 512 KB and 64-byte lines; both caches
are 8-way. GCC's processor costs and cache parameters have no associativity
field, so no fictitious associativity option is added. Prefetch latency is
estimated as 360 instructions from the measured memory latency and one issue
per cycle. Four simultaneous prefetches are an estimate of one per hardware
thread. Explicit user parameter values take precedence. This change supplies
costs; prefetch insertion and streaming-store tuning remain future work.

**Current source:** `knc_processor_costs` at GCC `619e14b479a9` exposes
32/256/64 for L1 KiB/effective L2 KiB/line bytes and 1024 software-prefetch
bookkeeping slots. Physical L2 remains 512 KiB; 256 KiB models the 64×4 KiB
first-level translation reach (R01 pp.22–23, [index](knc-references.md)).
Two-level prefetch is implemented at 16/32 lines with a stream/density footprint
rule, and NGO stores have eligibility/fencing support. Neither four nor 1024
is a measured hardware queue size (R01 p.19; R27 pp.393–398,641).

Gather costs estimate the lines touched. Unknown indices assume one line per
lane. Known constant strides use `ceil(lanes * abs(byte_stride) / 64)`, at
least one line, capped at one per lane. This assumes a favorable starting
alignment; arbitrary starting alignment may touch one more line. The estimate
`7 * lines + floor(lines * (lines - 1) / 16)` matches the measured one-line
cost of 7 and sixteen-line cost of 127 cycles. Its intermediate values are
interpolations, not measurements; a stride-2 FP32 gather costs 14. Scatter
uses the same line-service estimate until it is measured separately.

**S12-13 qualification:** R05 §V.D/Table II p.4 measures full gather loops,
with distinct L1/L2 costs and active-line distributions. It does not validate
our interpolation or scatter estimate. Retain setup/mask/retry work and cache
residence in any replacement; S12-07 owns that diagnostic.

Masked moves and memory conversions cost one vector issue; unaligned pairs
cost two. Permutes cost one issue, with the existing two-input lowering
charging two. Register conversions use the measured one-issue throughput.
The memory bridge for scalar/vector transfers has a dependency cost of
`ceil(12 / max(2, threads))` issues from `spill_reload.lat`; independent
load/store costs use measured throughput. Register-allocation bridge costs
remain conservative at the full dependent latency. x87 add/multiply/divide
cost 1/2/38 cycles per core. Unmeasured integer division, branches, size
thresholds and alignment are estimates; comments identify the retained
generic heuristics. String operations use libc pending measured crossovers.

**S12-13 qualification:** R03 pp.15–22 establishes call clobbers and preserved
controls, not transfer latency. R02 pp.32–34,56 requires operand/encoding-aware
pairing; a throughput price does not make every scalar or mask spill free.
Source sqrt=38 is still an estimate. S12-06/08 and S12-12 G05/G07 supply the
missing scalar-path and branch/library evidence.

The accepted T1 checks are the scattered gather rejection and the runtime
double reduction with one default accumulator and at least two at density 1.
The scan counts self-updating `vaddpd` destinations inside backward loops,
including masked destinations, and excludes horizontal epilogues.

Native correctness and M2 before/after benchmark windows are lead-only.
Host compilation and linting do not establish a native pass. x86 and torture
comparisons belong to the next batch check.

## First green attempt, 2026-11-06

GCC commit `4698d90a9e0` built successfully (26.8 minutes). T0 passed
52 tests. Both density reduction scans passed: one accumulator by default,
at least two with `--param=knc-threads-per-core=1`. T2 passed.

T1 has three failures, so this implementation is not green:

- `knc-cost-gather.c` still emits `vgatherdps`.
- `knc-reduce-int.c` finds a stack reference in `sum_i32`'s backward loop.
- `knc-vec-fold-O3.c` does not find the required register-form `vaddps`
  in `add_f32`.

The gather failure has a concrete source-level explanation:
`tree-vect-stmts.cc`, in the `VMAT_GATHER_SCATTER_LEGACY` costing branch,
records `cnunits` instances of `scalar_load`, not `vector_gather_load`.
Consequently the new gather-cost switch does not see KNC's legacy builtin
gathers. A follow-up must distinguish those vector-side records from the
scalar baseline and account for their lane count before charging line costs.

A diagnostic compile intended to save assembly and vectorizer dumps failed
with `xgcc: fatal error: no input files`, despite the subprocess argument list
containing the source. It used Cygwin Python directly without the normal
toolchain PATH trampoline. No diagnostic dumps were produced; the two other
T1 failures have not yet been reduced further. No existing scans were weakened.

The following binaries built and passed lint under `.work/_shared/S6-05/`:
`m2-kernels.mic`, `s5_ops/o2v.mic`, `s5_ops/o3.mic`, `s5_ops/fast.mic`,
and `s5_ops/neg.mic`. They reflect the first green attempt and have not run
on the card. M2 before/after measurements, native correctness, torture change
listing and the x86 batch check remain pending.

Logs under `.work/_state/logs/`:

- `S6_05_build-20261106-163310.log`
- `S6_05_t0-20261106-163724.log`
- `check_gcc16_t1_t2-20261106-170011.log` (full T1/T2 results)
- `S6_05_m2-20261106-170010.log`
- `S6_05_s5_ops-20261106-170010.log`
- `S6_05_diagnose-20261106-170318.log`

Shared GCC changes against `b12c3242595`: `i386-common.cc` +1/-1,
1 hunk; `i386-options.cc` +8/-2, 3 hunks; `i386.cc` +20/-0, 3 hunks;
`i386.opt` +4/-0, 1 hunk. Total shared: +33/-3, 8 hunks. KNC-only
files: `i386-knc.cc` +156/-1, 2 hunks; `i386-knc.h` +4/-0, 1 hunk.
Project harness `tools/check.py`: +22/-2, 3 hunks including the accepted
red-test selector and accumulator scanner. Commit `8989b25acde` restores
LF endings accidentally changed in the preceding shared-code commit;
the final diff contains no line-ending churn.

## Follow-up diagnosis, 2026-11-06

GCC `5bc3a6af7de` implements the lead's three corrections: vector-side
legacy gather/scatter records are normalized from lane counts to vector
counts, zero data-reference steps retain the unknown-index estimate, and
the late KNC override only handles gather/scatter. The other cost kinds
retain the x86 lowering adjustments. The incremental build passed.

Full T1 then still failed the gather rejection, integer reduction loop scan
and unaligned arithmetic scan. Four further decisions changed:
`knc-gather8-f64.c`, `knc-gather8-i64.c`, `knc-scatter8-f64.c` and
`knc-scatter8-i64.c` now stay scalar. Both density reduction tests passed.
The diagnostic compile succeeded using the toolchain PATH trampoline.
Assembly and vectorizer dumps are under `.work/_shared/S6-05/` with the
test stems and `.s` / `.vect` suffixes.

The diagnostics explain the remaining issues:

- `knc-cost-gather.c` takes `VMAT_GATHER_SCATTER_IFN`, not the legacy
  builtin path. The IFN branch in `tree-vect-stmts.cc` also records one
  scalar access per lane. Its dump still charged 64 for the gather,
  giving vector-body cost 72 versus scalar-iteration cost 12 and VF 16.
  GCC `7fdd15cf40a` extends the normalization to that native IFN path;
  emulated accesses and the scalar baseline remain unchanged.
- The eight-lane tests take the legacy path. For example, the double
  gather now costs 236 per eight-lane instruction, with two instructions
  per vector iteration: total body cost 484 versus scalar cost 12 and
  VF 16. Rejection follows the scattered-index estimate. Requiring these
  loops to emit gathers conflicts with the new profitability decision.
- `sum_i32` has a register accumulator in its actual vector loop `.L6`.
  The stack transfer follows horizontal reduction at `.L32`, outside
  that loop. The scanner treats every backward jump as a loop, including
  `.L42: ... jmp .L4` and the peel exits jumping back to `.L5`; these
  linear text ranges include the epilogue stack transfer. Changing costs
  to suppress this layout would conceal a scanner limitation.
- `add_f32` vectorizes. Alignment peeling aligns `a`, then emits
  `vaddps 0(%r13,%rdx), %zmm0, %zmm0`; `b` is loaded by an unpack pair.
  The existing scan assumes unannotated inputs cannot become aligned and
  requires register arithmetic. The folded operand here is the input
  aligned by peeling. The positive `b64` cases remain part of the test.

No existing scans were changed or weakened. The remaining scan conflicts
need the lead's decision before claiming unchanged T1.

Final follow-up validation at GCC `7fdd15cf40a`: incremental build PASS;
all three accepted cost scans PASS (gather rejected, one default reduction
accumulator, at least two at density 1). Full T1 still FAILS nine files:
the six remaining failures from the preceding run, plus
`knc-gather16-f32.c`, `knc-gather16-i32.c` and `knc-gather16-masked.c`.
These three now fail their required gather-instruction scans after IFN
costing is enabled. The unmasked FP32 test has the same indexed-copy loop
as the accepted gather rejection test. No further tuning or scan edits
were made after this second failed T1 attempt.

M2 and all four s5_ops binaries were rebuilt and linted successfully with
this final compiler, overwriting the paths listed above. They have not run
on the card. T0 and T2 retain the earlier passing results and were not
rerun in this follow-up. Torture changes and x86 remain for the batch check;
native correctness and M2 benchmark windows remain pending with the lead.

Follow-up logs under `.work/_state/logs/`:

- `S6_05_build-20261106-171136.log`
- `S6_05_t1-20261106-171325.log`
- `S6_05_diagnose-20261106-171548.log`
- `S6_05_build-20261106-171654.log`
- `S6_05_t1-20261106-171854.log`
- `S6_05_m2-20261106-171854.log`
- `S6_05_s5_ops-20261106-171854.log`

Final shared GCC changes against `b12c3242595`: `i386-common.cc` +1/-1,
1 hunk; `i386-options.cc` +8/-2, 3 hunks; `i386.cc` +36/-0, 4 hunks;
`i386.opt` +4/-0, 1 hunk. Total shared: +49/-3, 9 hunks. KNC-only
files: `i386-knc.cc` +157/-1, 2 hunks; `i386-knc.h` +4/-0, 1 hunk.
No project harness or test changes in this follow-up.

## Lead-approved scan corrections, 2026-11-06

Project commit `f3e7257` implements the lead's 17:24 instructions. GCC remains
at `7fdd15cf40a`; no compiler edits or rebuild were needed in this session.
The seven gather/scatter lowering tests now request
`-fvect-cost-model=unlimited`. The folding test disables alignment peeling
with `--param=vect-max-peeling-for-alignment=0`, with a comment explaining
the unaligned-input premise. No scan lines changed.

`tools/check.py::loops` now splits basic blocks at labels and after jumps
and returns. Unconditional jumps and returns end fallthrough; conditional
and mask branches retain it. For each layout-backward edge, it intersects
forward reachability from the header with reverse reachability from the
latch, without crossing the header again. This includes cold blocks on a
cycle regardless of layout and excludes backward jumps that close no cycle.
Both mask-branch operand orders are recognized. The same loop bodies feed
the stack, arithmetic and accumulator scans.

For the saved `.work/_shared/S6-05/knc-reduce-int.s`, `sum_i32` has exactly
these cycle block sets:

| Header / latch | Blocks | Instructions |
| --- | --- | --- |
| `.L6` | `.L6` | Two `vpaddd` operations, pointer update, compare and `jne .L6` |
| `.L7` | `.L7` | Scalar remainder add, updates, compare and `jg .L7` |
| `.L35` | `.L35` | Scalar fallback add, updates, compare and `jg .L35` |

The horizontal reduction and stack transfer at `.L32` are outside every
cycle. The branch from `.L6` falls through to `.L32` only on loop exit;
the paths from `.L32` go to the remainder `.L7` or return at `.L1`, with
no path back to `.L6`. `.L42 -> .L4` and the peel exits into `.L5` do not
close cycles. The inspection log is
`.work/_state/logs/S6_05_cfg-20261106-172606.log`.

The complete observed T1 decision changes and the nine prior failures are:

| Test / decision | Effect of the costs and resolution |
| --- | --- |
| `knc-cost-gather` | Scattered FP32 indexed copy now stays scalar, as required by the measured line-service cost. |
| `knc-cost-reduce-one-thread` | Density 1 now selects at least two reduction accumulators through the existing x86 unroll path; the default-density companion retains one. |
| `knc-gather16-f32` | Indexed FP32 copy now stays scalar under normal profitability; unlimited costs restore its gather/retry lowering check. |
| `knc-gather16-i32` | Indexed integer copy now stays scalar under normal profitability; unlimited costs restore its gather/retry lowering check. |
| `knc-gather16-masked` | Conditional gather now stays scalar under normal profitability; unlimited costs restore its mask/gather lowering check. |
| `knc-gather8-f64` | Eight-lane double gather now stays scalar; unlimited costs restore its two-gather lowering check. |
| `knc-gather8-i64` | Eight-lane integer gather now stays scalar; unlimited costs restore its two-gather lowering check. |
| `knc-scatter8-f64` | Eight-lane double scatter now stays scalar; unlimited costs restore its two-scatter lowering check. |
| `knc-scatter8-i64` | Eight-lane integer scatter now stays scalar; unlimited costs restore its two-scatter lowering check. |
| `knc-reduce-int` | The prior linear-range scanner counted the post-loop bridge at `.L32`; CFG membership fixes the false failure without changing costs or scans. |
| `knc-vec-fold-O3` | Peeling now chosen for a, b by unpack pair. Alignment permits folding a; disabling peeling restores the test's unaligned-input premise. |

The last nine rows identify the nine failing files from the preceding run;
the integer-reduction row is a scanner correction, not a new profitability
decision. The first two rows are the accepted cost-decision checks.

This session changes shared project `tools/check.py` by +51/-4 in one hunk;
the eight T1 source files change by +9/-8 in eight hunks. Shared GCC totals
remain +49/-3 in nine hunks, as listed above.

Final validation ran once after these corrections:

```
python tools/run.py --name S6_05_final_t0_t1_t2 --inputs tools tests toolchain -- python tools/check.py t0 t1 t2 --compiler gcc16 --worker
```

PASS, exit 0, 542.07 seconds. T0 passed all 52 tests; full T1 and T2 passed.
All nine previously failing files now pass. `knc-div-f32`,
`knc-fp-minmax-strict`, `knc-cost-reduce` and
`knc-cost-reduce-one-thread` retain their passing verdicts with the CFG
scanner. The scattered-gather profitability check also passes.
Log: `.work/_state/logs/S6_05_final_t0_t1_t2-20261106-172632.log`.

The final compiler's previously built and linted card binaries remain at
`.work/_shared/S6-05/m2-kernels.mic` and
`.work/_shared/S6-05/s5_ops/{o2v,o3,fast,neg}.mic`. This session did not
execute them on the card. Per the lead's 17:24 instruction, native M2 and
s5_ops correctness and before/after M2 benchmark windows remain with the
lead; torture changes and x86 validation remain with the next batch check.

## Stencil regression correction, 2026-11-06 evening

The owner's reopened task follows the lead's paired card measurements:
stencil1 is 4.8--6.4% slower and stencil2 is 2.9% slower than M2-final;
mat8 measures about 20% faster. The lead also recorded passing M2 and
s5_ops correctness for GCC `7fdd15cf40a`. Those results precede this fix.

GCC `97f4b6c04b7` changes only the scalar add entry of the KNC processor
cost table, from `COSTS_N_INSNS (1) / 2` to `COSTS_N_INSNS (1)`.
The old entry used independent throughput (`scalar_add.rt`, 0.55 core
cycles). Induction-variable updates form dependent chains; the measured
`scalar_add.lat` is 4.19 cycles per thread at four threads, or 1.05 per
core. One is the rounded cost for these updates. This correction applies
to scalar adds generally and does not recognize benchmark names, source
shapes, or trip counts. No vector cost, lowering, test option, or scan
changes in this follow-up.

`tools/s6_05_stencils.py` compiles the unchanged M2 fixture with its build
options and saves assembly, `-fdump-tree-vect-details`, and
`-fdump-tree-ivopts-details` under `.work/_shared/S6-05/`. The saved sets are
`stencils-before.*` (GCC `7fdd15cf40a`, KNC tuning), `stencils-knc.*`
(corrected KNC tuning), and `stencils-generic.*` (diagnostic control).
The generic control retains current KNC statement hooks, so it is **not**
a historical compiler dump. Its two stencil functions nevertheless
reproduce M2-final's saved assembly after ignoring local label numbers.
The before/after KNC dumps directly isolate the add-cost correction.

The vectorizer decisions did not cause these regressions. Before and after
the fix, each stencil vectorizes one loop with VF 16, no alignment peeling,
and runtime/static profitability thresholds of 16. Stencil1's vector-body,
scalar-iteration, and vector-epilogue costs remain 32, 24, and 208;
stencil2's remain 48, 40, and 336. The changes occur later in IV selection:

| Function | Previous S6-05 decision | Corrected decision and assembly |
| --- | --- | --- |
| stencil1 | Vector-loop IV set costs 19; two pointers advance by 64, requiring two adds per iteration. | IV set costs 22; one byte-offset IV advances by 64 and serves both bases. The complete function matches M2-final after label normalization. |
| stencil2 | Outer-loop IV set costs 31; compare elimination replaces `iv + 64 < n` with equality against a derived bound. This introduces a bound stack slot, an extra row guard, and extra branching. | IV set costs 49; restores the original unsigned comparison against `n`. The vector loop and outer-loop control match M2-final, with no bound spill. |
| mat8 | Scalar loops; no loop vectorization. | Instructions and alignment directives match the preceding S6-05 function after label normalization. |

Stencil2 retains one extra LEA in scalar-remainder setup compared with
M2-final: it forms the preceding element's index separately. It is outside
the vector loop and the full-row path used by the L2 benchmark; the fixed
vector and outer loops have the original instruction sequences. This is
the only remaining function-local assembly difference from M2-final after
normalizing labels.

There is an important limit to the mat8 preservation claim: the **original**
S6-05 mat8 function also matches M2-final's instructions and alignment
directives after label normalization. Thus the observed 20% gain cannot
be attributed to a changed mat8 instruction sequence. Placement remains
a possible explanation, not a demonstrated cause. This fix preserves its
instructions but changes preceding code sizes; only the lead's paired
rerun can establish whether the measured gain survives. No function-specific
padding or alignment tuning was added.

This follow-up changes shared GCC files by **0 lines / 0 hunks**;
`i386-knc.cc` changes +3/-1 in one hunk. Total shared GCC changes for the
ticket remain +49/-3 in nine hunks against `b12c3242595`;
the KNC-only source total is now +159/-1 in two hunks. The project adds
the diagnostic helper and updates this report; existing scans and the
shared scanner are unchanged.

The incremental compiler build passed. M2 and all four s5_ops variants
were rebuilt and linted at the standard handoff paths:
`.work/_shared/S6-05/m2-kernels.mic` and
`.work/_shared/S6-05/s5_ops/{o2v,o3,fast,neg}.mic`.
They have not been run natively with this correction. Correctness and
paired performance reruns remain with the lead; torture/x86 remain with
the batch check.

Logs under `.work/_state/logs/`:

- `S6_05_stencil_diagnose-20261106-222639.log`
- `S6_05_stencil_build-20261106-222730.log`
- `S6_05_stencil_fixed-20261106-222920.log`
- `S6_05_stencil_m2-20261106-222949.log`
- `S6_05_stencil_s5_ops-20261106-222949.log`

Full T0/T1/T2 ran once after the compiler correction and passed, exit 0,
560.99 seconds, with no test or scan edits:

```
python tools/run.py --name S6_05_stencil_t0_t1_t2 -- python tools/check.py t0 t1 t2 --compiler gcc16 --worker
```

Log: `.work/_state/logs/S6_05_stencil_t0_t1_t2-20261106-222949.log`.
The accepted gather rejection and both reduction-density checks retain
their passing verdicts. No additional T1 verdict changes were observed.

## `-mtune=knc` tune flags (S8-08, E5-12)

`-mtune=knc` maps to `PROCESSOR_GENERIC` (`i386-common.cc`), so it inherits the generic
`x86-tune.def` flags. `ix86_knc_tune_features` (`i386-knc.cc`, called from
`set_ix86_tune_features` before `-mtune-ctrl`, which still wins) changes only flags with a
documented or measured KNC reason. `-mdump-tune-features` shows the result. Sources: SSDG p.16-22
(`knc-optimization-sources.md` I-10, I-12), `knc-characterization.md` points 1-8.

**Locator correction, S12-13:** the SSDG pp.16–22 citation above and p.16
prefix citation below belong to the earlier unidentified 163-page edition.
They are superseded for new work by R01 p.19 (prefix/latency facts) and
pp.23–24 (threading/ready buffers), with R02 p.56 for pairing restrictions.

| Flag (generic value) | KNC | Reason |
|---|---|---|
| `fast_prefix` (on) | **off** | 0x66/0x67 prefixes take 2 decode cycles (SSDG p.16). HImode register ALU, `and`+test and `and $-65536` become SImode forms; 16-bit memory operands, stores and compares keep the prefix (no equivalent unprefixed form). T1 `knc-tune-prefix.c`. |
| `lcp_stall` (on) | on | Avoids 16-bit immediates with a 0x66 prefix; same direction as the prefix cost. |
| `schedule` (on) | on | KNC scheduler `knc.md` (S6-06). |
| `fuse_cmp_and_branch_*`, `fuse_alu_and_branch*` (on) | on, inert | Only read by `x86-tune-sched.cc`, where `ix86_macro_fusion_p` already returns false for `CPU_KNC` (S6-06: KNC pairs, it does not fuse). |
| `partial_reg_dependency` (on), `partial_reg_stall` (off), `partial_flag_reg_stall` (off), `movx` (on) | unchanged | No partial-register penalty is documented or measured for KNC; zero-extending loads (`movx`) are one op either way. |
| `read_modify`, `read_modify_write` (on) | unchanged | P5 turns them off for U/V pairing; KNC's pairing of memory-operand integer forms is not measured (characterization measures vector memory operands only). KNC is not P5 (I-10). |
| `use_incdec` (off) | unchanged | Off avoids the partial-flags write; no KNC measurement either way. |
| `push_memory`, `use_leave` (on); `single_push`, `double_push`, `single_pop`, `double_pop`, `pad_returns`, `pad_short_function` (off) | unchanged | No KNC measurement; the P5 push/pop pairing rules are not documented for KNC. |
| `memory_mismatch_stall` (on) | unchanged | Store forwarding of a narrower load is not measured; on is the safe direction. |
| `avoid_mfence` (on) | on | KNC has no `mfence` (`tests/isa/mfence.s`); the `lock or` fence is required, not a tuning choice. |
| `use_sahf` (on) | inert | `-march=knc` sets `PTA_NO_SAHF`. |
| `use_cltd`, `use_bt`, `shift1`, `double_with_add`, `promote_himode_imul`, `promote_qimode`, `himode_math`, `qimode_math`, `unroll_strlen`, `misaligned_move_string_pro_epilogues` (on) | unchanged | Generic scalar code shape; no KNC measurement. |
| `ext_80387_constants`, `always_fancy_math_387` (on) | unchanged | x87 is KNC's scalar FP unit; no measurement against loading constants from memory. |
| `align_tight_loops` (on) | **off** (S8-19) | `pass_align_tight_loops` puts `.p2align ceil_log2(size)` with no max-skip before every loop up to `prefetch_block` (64) bytes, for the decoded-icache rules of big cores; KNC has none. Entered by fallthrough, the gap is nops run on every outer trip: m2_mat8 `.L101` got `.p2align 6`, 56 nops per outer trip, 1.105x slower at L2 (lead card 2026-11-10). Loops keep the generic alignment (below). T1 `knc-tune-tight-loops*.c`. |
| `sse_*`, `avx*`, `inter_unit_*`, `use_gather_*`, `use_scatter_*`, `avoid_*fma*_chains`, `prefer_bcst_from_integer`, `avoid_false_dep_for_bmi` | inert | KNC never sets SSE/AVX/AVX-512F/BMI; IMCI gathers and scatters use their own expanders (`i386-knc.cc`). |
| every other flag (off in generic) | unchanged | No KNC reason found. |

### Code alignment

`-mtune=knc` defaults `-falign-functions=64`; loops, jumps and labels keep the generic
alignment (loops `.p2align 4,,10` then `3`). The lead's A/A pairs on the card (2026-11-09, L2, 4 threads: one
`kernels-gcc.s` linked twice, the second copy shifted half a line, a whole line at 64) measure
the placement swing as the ratio away from 1.00:

| `-falign-*` | mat8 | stencil1 | affine_f32 | short 5 | short 13 |
|---|---|---|---|---|---|
| generic (functions 16) | 1.344 | 0.955 | 1.033 | 1.010 | 0.999 |
| 16 | 1.346 | 1.011 | 1.002 | 1.001 | 1.002 |
| 32 | 0.764 | 1.005 | 1.004 | 1.074 | 1.051 |
| 64 | 1.001 | 1.018 | 1.001 | 1.006 | 1.002 |

64 removes the mat8 swing. Loops stay generic: `-falign-loops=64` has no max-skip, so an inner
loop entered by fallthrough (mat8 `.L101`) ran up to 63 bytes of nops per outer trip. Against
knc with only `.p2align` changed (lead, card 2026-11-10) the loop-and-function 64 build ran
mat8 1.106, mat16 1.173, short 5 1.048/1.027, short 13 1.044/1.052 and stencil2 L1 1.064
slower. `ix86_default_align` reads the per-processor table, so `ix86_knc_vectorizer_params`
(`i386-knc.cc`, no shared line) replaces its function choice with the `align_func` of the KNC
cost table. An explicit `-falign-functions=` still wins, and `-Os` or `-fno-align-functions`
leaves it off; an `optimize` attribute or pragma reruns `ix86_default_align` and gets 16. T1
`knc-tune-align.c` and `knc-tune-align-user.c`.
