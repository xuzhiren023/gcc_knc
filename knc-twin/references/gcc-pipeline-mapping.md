# Relation to GCC's pipeline description (`gcc/config/i386/knc.md`)

GCC schedules with a DFA built from `define_cpu_unit` / `define_insn_reservation`
(gccint, *Processor pipeline description*). gcc_knc's `knc.md` models one KNC *thread's* issue
opportunities: a scheduler cycle is one issue opportunity (two or more core cycles), units
`knc-u`, `knc-v`, `knc-fp`, with latencies in core cycles converted by `ix86_adjust_cost`.

The twin models the *core*: cycles, four contexts, the picker and the pairing decision per
cycle. The two agree on the vocabulary below and can be cross-checked with `simulate` on the
assembly GCC emits (GAS subset) when the instruction forms are in the table.

| knc.md | twin class(es) | twin latency parameter | note |
|---|---|---|---|
| `knc_scalar` (alu, imov, lea, incdec, ishift, icmp, test, ibr, setcc, icmov; `knc-u\|knc-v`, 2) | `scalar_alu`, `scalar_rmw`, `branch`, `mask_op` (nop takes no V partner, jmp does not go to V: `validation.md`) | `latency.scalar_alu` (1 core cycle), `latency.mask_op` | knc.md's 2 is one issue opportunity, i.e. the twin's spacing rule, not a core latency |
| `knc_scalar_load` (3) | `scalar_load` | `latency.scalar_load_l1` 3 (measured) | |
| `knc_vector` (`knc-u`, 4) | `vector_arith` | `latency.vector_arith` 4 | U-only in both |
| `knc_vector_mem` (`knc-u`, 12) | `vector_load`, folded loads | `latency.vector_load_l1` 5 and `latency.store_to_load_same_line` 7 (the measured 12-cycle chains are store-then-reload chains, `validation.md`); R08 says 3 | the twin charges folded loads no extra latency on an L1 hit (C9); knc.md's 12 is the whole spill/reload path |
| `knc_vector_long` (6), `knc_convert_df` (7) | `vector_long`, `vector_convert_df` | `latency.vector_long`, `latency.vector_convert_df` | |
| `knc_gather` (`(knc-u+knc-v)*7`, 15) | `vector_gather` | `latency.gather_first_line`, `occupancy.gather_cycles_per_line`, `latency.gather_mask_cycles` | the twin scales occupancy and latency with the distinct lines actually touched; the measured catalog shows the gather occupying a gather unit, not both pipes (kmov/gather/jknzd fit in 7 ticks), and the completion mask readable after 2 cycles |
| `knc_pair` (unpack/pack, two U issues) | `vector_load` x2 records | | write the two instructions as two records |
| `knc_fp`, `knc_fmul`, `knc_fdiv` | `x87_*` | `latency.x87_*`, `occupancy.x87_*` | x87 serialized per context in the twin |
| `knc_special=prefetch` -> scalar slot | `prefetch_l1`, `prefetch_l2` | `occupancy.vprefetch_l2_core_cycles` | the twin also models the prefetch's memory effect |
| `knc_serial` (`knc-u+knc-v`, 4) | not represented | | uncharacterized instructions are rejected by the twin instead of given a serial cost |
| (none) | `fence` | `latency.fence` (unknown) | |

What the DFA cannot express and the twin adds: context interleaving (1-4 threads), the
no-back-to-back rule as a cycle-level fact, pairing decided per dynamic pair with the
`cmp/jcc` exception and encoding hints, demand-miss stalls vs nonblocking prefetches, the
outstanding-miss limit, AGI as a 3-cycle address availability rule, loop-carried recurrence
bounds (RecMII) comparable with what `modulo-sched.cc` computes.

Using the twin to check a scheduler change: compile the kernel before and after, strip to the
loop (GAS subset), give identical init/expected state, run `simulate` on both with the same
profile, then `compare`. The `pair_fraction`, `core_issue_utilization` and stall breakdown say
whether the new order pairs better or merely moves stalls.
