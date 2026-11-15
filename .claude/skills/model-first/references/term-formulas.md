# Terms, units and overlap

Use the project's machine file for architecture values. The formulas below use
symbols, so a change of target does not silently retain another target's timing.
The KNC mapping is [knc-machine.yaml](../../../../docs/research/knc-machine.yaml).

## Normalize before taking a maximum

Choose one work quantum. For example, a core round completes one iteration on
each of its `t` workers; a card round completes such a round on every active core.
Let `B_j` be bundles in worker j's iteration, `g` its minimum issue interval,
`r_b` the shared core bundle rate, `N_r,j` operations occupying resource r, and
`r_r` that resource's throughput. For a balanced core round:

| Term | Time for the common quantum | Qualification |
| --- | --- | --- |
| Thread issue | `max_j(g * B_j)` | Long-run initiation interval; count a legal U+V pair once, and count slow decode occupancy |
| Core issue | `sum_j(B_j) / r_b` | One shared capacity, not a capacity per worker |
| U-pipe / VPU / other unit | `sum_j(N_r,j) / r_r` | Count occupancy for the exact class; selected stores may use another pipe |
| Recurrence | `max_j(L_chain,j / a_j)` | Independent interleaved chains `a_j`; with unequal chains use the critical recurrence, not their average |
| Address interlock | Critical dependency-path time including address setup | Include only exposed constraints; do not add the entire setup delay to every load |
| L1-L2 transfer | `lines_transferred * cycles_per_line` | Distinguish transfer service rate from dependent load latency |
| Memory | `bytes_for_card_quantum / sustainable_BW` | Same traffic convention and configuration; an empirical roof yields a conditional term |
| Concurrency | `lines_for_quantum * loaded_latency / available_outstanding` | Steady-state Little's-law capacity estimate; separate queue classes and residence |
| Gather/scatter | Sum of complete-loop costs by occupied lines, cache level and active mask | Retry/index/mask overhead is visible; gather does not price scatter |
| Parallel work/span | `max(T_work/P, T_span_with_mandatory_sync)` | Add barrier cost only where it is on the critical path and not already counted |

Do not divide every term by thread count. For a core round, aggregate shared
resource work across workers, while taking the maximum of per-worker dependency
times. For a card round, take the maximum of the core-local times and combine
with the card-wide bandwidth term. Imbalance can require a critical-worker model.
Report per-update throughput only after this normalization; it is not latency.

`T_lb = max(T_i)` is valid only for independently valid lower bounds on identical
work. Taking a maximum avoids summing constraints that describe the same work.
A missing term makes the bound weaker, not zero-cost. Uncertain experimental
roofs may be exceeded; show a conditional bound and sensitivity rather than
declaring the observed kernel a physical ceiling.

Convert cycles to seconds with the relevant core clock. Convert TSC ticks with
the measured TSC frequency. If approximating one with the other, state its error.
Use decimal bandwidth units consistently; do not confuse bytes with elements,
useful traffic with DRAM transactions, or capacity with usable bandwidth.

## Prediction and memory-level parallelism

A prediction needs a declared overlap graph. A useful initial in-order scenario
is `T_serial,j = T_in_core,j + T_nonoverlapped_transfers,j` for each worker, then
`T_pred = max(max_j(T_serial,j), shared_core_terms, card_memory_term)`.
This is a serial-transfer scenario: allow other workers' execution during a
requesting worker's stall, and charge their combined shared-resource demand.
Refine it for actual prefetch/pipeline overlap; do not add latency once per line
when independent requests run concurrently, or add a stall already in the chain.
The max-plus expression is an explicit model assumption, not a universal ECM
equation or proof of achievable scheduling. Explain warmup/tails/completion when
they are material to the measured quantum.

At target bandwidth `b`, line size `C` and loaded latency `L`, required outstanding
lines are `Q_needed = b*L/C`. At a matching resource scope the optimistic rate is
`b_concurrency = Q_available*C/L`. Do not add L1 miss slots, L2 MSHRs and hardware
prefetch streams as if they were independent pools of identical requests.
Use idle latency only as an explicitly optimistic scenario; it cannot replace a
missing loaded-latency measurement. Threads share per-core queues.

Initial prefetch lookahead in loop iterations is
`d_near = ceil(L_next_level / T_iteration)` and
`d_far = ceil(L_memory_loaded / T_iteration)`.
Account for lines consumed per iteration, streams, cache/TLB footprint, instruction
overhead, density and bounds. These are starting hypotheses; missing loaded
latency means unknown lookahead. Historical near/far optima are not universal.

## Diagnosis and ratios

For resource r, modeled utilization is `u_r = T_r/T_meas`; report the separate
`T_lb/T_meas` and `T_pred/T_meas` ratios. A ratio above one requires examining the
model, scope and uncertainty. It is not evidence of super-peak execution.
When the lower bound is credible, remaining regional headroom is at most
`T_meas/T_lb`. Use that headroom in Amdahl's law before investing in a change.

Count split-loop temporary traffic, write ownership reads, fences, reduction
bridges, calls, spills and padding/control instructions where they actually run.
Cache reuse can raise useful byte rate without raising channel utilization.
Do not put a FLOP roof on integer/control-only code, or price divide/sqrt as FMA.

## Method references

The repository's
[design survey](../../../../docs/research/model-first-optimization-method.md),
sections 2 and 4-6, supplies these references. These are method citations; no
publication's text, pseudocode, tables or implementation is reproduced here.

- Treibig, Hager and Wellein, performance engineering and patterns,
  arXiv:1206.3738: model, measure, diagnose and revise.
- Williams, Waterman and Patterson, Roofline, CACM 2009,
  DOI 10.1145/1498765.1498785: resource ceilings and arithmetic intensity.
- Stengel et al., ECM, arXiv:1410.5010: in-core and hierarchy transfer timing.
- Hofmann et al., 2016 preprint arXiv:1604.01890, CCPE 29:e3921:
  KNC ECM extension for the Kahan dot product, including prefetch instruction
  work and ring effects. Cite the model; do not transplant its workload timings.
