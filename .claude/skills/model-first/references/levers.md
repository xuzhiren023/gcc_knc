# Choose a lever from the measured gap

Apply only the row matching the dominant term or a diagnosed missing term.
Recompute the candidate model before measurement. Machine-specific instruction
eligibility and timings come from the machine file and its cited sources.

| Dominant constraint | Candidate change | Cost or legality to keep visible |
| --- | --- | --- |
| Thread/core issue | Reduce address/control overhead, hoist invariant tests, unroll only enough to amortize loop work, pair eligible operations | Code size, prefixes, decode limits, new register pressure and spills |
| U-pipe or VPU | Remove redundant operations/copies, use a legal fused operation | FP contraction/rounding contract; scalar-domain transfers; no implicit fast math |
| Loop-carried recurrence | Interleave independent work; more accumulators only if reordering is legal; keep memory-carried state in registers | A strict reduction cannot be reassociated on profitability alone; longer conversions remain on the chain |
| Address dependency | Schedule independent work between producer and address consumer | Operand-specific setup time; inserted work must not cost more than the stall |
| Cache/memory bytes | Blocking, layout, reuse, eligible no-read stores for cold output | Read-for-ownership, immediate reuse, partial lines/masks, completion and publication ordering |
| Concurrency/overlap | Adjust prefetch distance/density or worker placement for the actual streams | Shared queues, cache/TLB pollution, extra issue work and load under traffic; more threads is not always faster |
| Gather/scatter | Improve occupied-line density or a legal layout; simplify full completion loop | Starting offset, masks, retries, alignment, memory safety and separate scatter costs |
| Parallel span | Balance work, change schedule or remove a redundant barrier | Dependency graph, tasks/cancellation, real runtime and skewed arrival; preserve mandatory synchronization |

If measured time greatly exceeds prediction, first test one explanation using
existing evidence: cache-set aliasing, translation reach, ring traffic, decode,
unaccounted bridges, page backing or imbalance. Do not attribute a cause from a
coincident speed change alone. If prediction greatly exceeds the resource bound,
focus on overlap; if measurement is already near a credible bound, stop or propose
an algorithm/layout change that reduces the dominant term.

Any new experiment remains subject to the ticket's budget and card coordination.
This table is not a mandate to try every lever.
