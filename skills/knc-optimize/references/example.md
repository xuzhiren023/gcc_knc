# Worked example: the existing S11-09 GEMV screen

This applies the method on paper. It reuses `knc-memory-bandwidth.md`, S11-09,
including Native evidence, Prediction versus target, Executed instruction cost
and What the lever measurements support. No new binary, twin run or card job
was made. It is a retrospective explanation, not a new held-out prediction.
The original screen's optimistic prediction was recorded before its card run.

## 1. Locate and fix the work

The region computes row dot products against a shared fp32 vector. Compare
fp32, fp16 and int8 weights with the documented per-row scale. These are format
alternatives, not permission to quantize an arbitrary model. Correctness in
the screen covers its generated exact finite inputs; application accuracy and
special values need their own contract.

Use the matched density-table rows at 120 workers, 4096 columns, window 1024,
four row streams, unroll four, small pages and near/far hints 8/64. These are
cases 10/20/15 for fp32/fp16/int8, all on the project's production 7120P,
60 compute cores. Those numbers and settings come from S11-09's density and
lever tables. Do not compare only the separate winners, whose shapes differ.
Normalize useful work to one billion weights; this is an accounting unit,
not the allocation size. The profile share in a whole decoder is unknown, so
whole-program speedup is unknown.

## 2. Model

The machine source is `knc-machine.yaml`: `nominal_core_clock` gives
1.238 GHz for this model; `core_bundle_rate` gives one bundle per core cycle.
R02 pp.34,56 permits at most a pair, with restrictions. For an optimistic
issue lower bound, allow every instruction to pair. That relaxation makes
the bound weaker, not an estimate of a feasible schedule.

S11-09's audited bulk paths execute 367/272/199 instructions for 256 weights
in fp32/fp16/int8. They include control, copies, hints and padding, but omit
entry, tails, horizontal reductions and output work. Omitting that work is
acceptable for a lower bound, not for an exact run-time prediction. The counts
are static, not PMU readings.

| Term | Formula / input | fp32 | fp16 | int8 | Status and source |
| --- | --- | --- | --- | --- | --- |
| Weight bytes per billion weights | format bytes times useful work | 4 GB | 2 GB | 1 GB | Counted format traffic; S11-09 format description; excludes other traffic |
| Relaxed issue time | `(1e9/256) * instructions / (2 * 60 * 1.238e9)` seconds | 9.65 ms | 7.15 ms | 5.23 ms | Conditional issue-only lower bound; counts from S11-09, clock/bundles from machine source; maximal pairing assumed |
| Prior read-rate scenario | weight bytes / 186.14 GB/s | 21.49 ms | 10.74 ms | 5.37 ms | S11-09 Prediction versus target, reusing S11-06 read; optimistic prediction, not a bound |
| Matched measured weight rate | S11-09 density table, 120-worker row | 98.55 GB/s | 72.63 GB/s | 53.58 GB/s | Reported production-card medians, cases 10/20/15 |
| Useful rate | weight rate / bytes per weight | 24.64 Gweights/s | 36.32 Gweights/s | 53.58 Gweights/s | Derived from the preceding row |
| Normalized measured time | one billion / useful rate | 40.59 ms | 27.54 ms | 18.66 ms | Derived, not a separately timed billion-weight run |
| Issue bound / measured time | ratio of the rows above | 0.238 | 0.260 | 0.280 | Modeled utilization, not counter utilization |
| Prior scenario / measured time | ratio of the rows above | 0.529 | 0.390 | 0.288 | Prediction misses grow for packed formats; not proof of conversion-unit saturation |

`T_lb` here is only the relaxed issue bound. No qualified maximum physical
memory rate, loaded latency, complete pairing schedule or per-format conversion
service limit is available in this example. Those terms are unknown, not zero.
Do not call the read-rate scenario a memory lower bound or combine it with the
issue term to claim a hardware ceiling. Its assumptions are equal delivered
weight-byte rate across formats and no charged GEMV overhead, as in the prior
S11-09 prediction. Cache, ring, conversions, reductions and output can all make
the real job slower.

This is a whole-card comparison. `knc-twin` was not invoked: a one-core result
would not model the measured shared-delivery experiment. For a later inner-loop
implementation ticket, invoke the installed twin on the faithful compiled
function and preserve its status and unsupported forms. Do not claim that the
arithmetic above is twin output.

## 3. Choose the dominant gap

The original equal-byte-rate scenario predicts useful-work order
int8 faster than fp16 faster than fp32. The matched card rows have exactly
that order. The relaxed instruction-accounting order agrees as well, but
neither predicts the exact times.

All formats fall well below the optimistic read-rate scenario. S11-09's
disassembly shows address/hint control and register copies, with more expanded
loads and arithmetic per physical weight line for packed formats. The leading
diagnosis is instruction and dependence cost per byte, with delivery effects
still possible. Calling the lowest weight GB/s the worst format would reverse
the useful-work conclusion. No PMU measurement in that run isolates a conversion
or cache ceiling.

## 4. Choose practices using existing controls

Use V9 (control work), V10 (independent work), V14 (packed formats), M1
(blocking cost) and M5 (lookahead) in [practices](practices.md). The candidate
for a future code ticket is to move invariant hint-mode/address decisions out
of the bulk path, keep accumulators resident and reduce redundant copies.
Its exact gain is unknown until the changed compiled path is modeled.

The existing comparisons reject blind parameter escalation:

- At the same density, deeper 32/256 hints lose to 8/64 for all formats
  (S11-09 hint table); plain read responds differently.
- Unroll eight adds no robust gain over unroll four (S11-09 unroll table).
  It continues the same accumulator chains.
- Int8 improves from 53.58 to 70.04 weight GB/s when density rises from
  120 to 240 workers, while fp32/fp16 do not follow that trend (S11-09 density
  table). Use that as a format-specific starting point, not a general rule.
- Smaller windows increase reductions/traversal and lose in the measured
  packed-format comparisons (S11-09 window table). Cache footprint alone did
  not predict the outcome.

## 5. Verify against the existing card evidence

S11-09 reports valid output for every recorded case and completed-worker
envelope timing, with fences and skew included. Reuse that evidence here.
The opening/closing references drift, especially int8; the separate fp32
winner has a 12.5% spread (S11-09 Native evidence). The screen supports large
mechanism differences, not small new defaults. Its correctness check does not
establish arbitrary-model quantization accuracy.

## 6. Stop

The coarse prediction's ranking matches the measured rows, and its numerical
miss identifies omitted kernel cost. The bound has not been reached. This
paper task stops because no new implementation or card experiment is in scope.
Retain the existing results and stage a focused control-cost ticket if the
caller authorizes one. Do not report a speedup from a change that has not been
implemented, and do not select a within-noise candidate from these screen rows.
