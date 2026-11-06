# KNC costs v1 (S6-05)

`-march=knc` implies `-mtune=knc`. The KNC tuning selects its own
`processor_costs`, including when target options are restored between functions.
It does not enable SSE or AVX. Size optimization retains the x86 size table.

The source of measured values is
`docs/research/knc-characterization.md` (S6-03, 2026-11-06), especially
points 1–8 and the named `.rt` rows. Each initializer in `i386-knc.cc`
identifies its source or labels an estimate and its reason. Costs use core
throughput: one cycle per vector operation, half a cycle per scalar integer
or mask operation. GCC instruction costs use `COSTS_N_INSNS`; register and
memory move costs use twice the cycle count.

`--param=knc-threads-per-core=N` accepts 1–4 and defaults to 4. The measured
four-cycle add/multiply/FMA latency needs two independent chains at 1, 2 or
3 threads, and one at 4 threads. One thread cannot issue more often than
every other cycle, so four accumulators are unnecessary. KNC addition and
multiplication reductions feed the existing x86 `reduc_lat_mult_thr` /
`m_suggested_unroll_factor` path. The table caps vector unrolling at two;
the existing `--param=ix86-vect-unroll-limit` remains available. Floating
point reassociation still requires explicit permission such as `-ffast-math`.

The cache defaults are L1 32 KB, L2 512 KB and 64-byte lines; both caches
are 8-way. GCC's processor costs and cache parameters have no associativity
field, so no fictitious associativity option is added. Prefetch latency is
estimated as 360 instructions from the measured memory latency and one issue
per cycle. Four simultaneous prefetches are an estimate of one per hardware
thread. Explicit user parameter values take precedence. This change supplies
costs; prefetch insertion and streaming-store tuning remain future work.

Gather costs estimate the lines touched. Unknown indices assume one line per
lane. Known constant strides use `ceil(lanes * abs(byte_stride) / 64)`, at
least one line, capped at one per lane. This assumes a favorable starting
alignment; arbitrary starting alignment may touch one more line. The estimate
`7 * lines + floor(lines * (lines - 1) / 16)` matches the measured one-line
cost of 7 and sixteen-line cost of 127 cycles. Its intermediate values are
interpolations, not measurements; a stride-2 FP32 gather costs 14. Scatter
uses the same line-service estimate until it is measured separately.

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
