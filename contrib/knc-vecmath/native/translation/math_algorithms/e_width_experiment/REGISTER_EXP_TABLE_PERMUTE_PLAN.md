# Exact32 masked static-table VPERMD source experiment

The single varying factor is the lowering of the 32 retained DP exp table
permutations in assembly374ab37e. Load its exact readable, readonly and
64-aligned static64B table into reserved ZMM31, zero the distinct destination,
then apply native merging-mask VPERMD. The index is ZMM12 and every destination
is different. Unconditional table loading is justified only by this explicit
static premise; it is not a general masked-memory recipe.

Expected signature: exact source destination words including zeroed inactive
lanes, with only ZMM31 as declared physical scratch. All GPRs, other vectors,
masks, flags, native VCSR, memory page and scratch bytes remain unchanged.
Metrics are complete6464B comparisons, source-effect matches, full physical
matches, negative signatures and parent/table/line authentication. The source
schedule is32literal forms times256epochs, all four native rounding controls
and64sticky-flag combinations, boundary/random selectors and directed/random
16-bit masks. Two intentionally wrong programs remove masking or swap operands.

Falsifiers are any candidate/independent-equation mismatch, missed negative
effect, state corruption, parent/table mutation or admitted unlisted tuple.
Bounded effort: four new local source-control groups, under30seconds; stop on
failure and preserve the result. These controls execute no compiler, FP kernel,
card instruction or old scientific sample. Syntax probes and randomized native
whole-state qualification remain required before activation. Final linked table
payload, address, alignment and readonly mapping still need separate admission.
