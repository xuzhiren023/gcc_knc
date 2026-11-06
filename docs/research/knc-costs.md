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
