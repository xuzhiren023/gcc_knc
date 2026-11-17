# S14-44: scalar lane 0 feasibility (input review, incomplete)

2026-11-17. No go/no-go verdict yet. No compiler change, GCC build, card
job, or new native performance measurement has been made. Phase 0 must
precede a recommendation. The three supplied C probes have been inspected;
none is a complete `nbMakeTree` reproducer.

## Model

Fixed work: one complete application run for each existing window-14 case.
Hardware: knc-boinc's reported card run, 240 CPUs granted; this does not
establish the active context count during a serial phase. Compiler identity
and complete build flags need to accompany the reduced input. These are
reported existing measurements, not results reproduced by this ticket.

Source: `C:/Users/xuzhi/Documents/knc-boinc/runs/card/w14/S8-09/`,
`batch-3-core-small-240.txt` and `batch-3-large-240.txt`, `PHASE` rows.
The labels below retain the application's timer scope. Setup and tree are
separate phases; the tree timer includes multiple constituent operations.

| Term | core-small | large | Evidence / interpretation |
| --- | ---: | ---: | --- |
| Whole run | 62.300974148 s | 30.610028089 s | Reported `whole_run` |
| Setup | 61.045101898 s | 1.110266230 s | Reported `setup` |
| Tree | 0.393688563 s / 33 calls | 10.078718534 s / 111 calls | Reported `nbMakeTree` |
| Force | 0.777955700 s / 33 calls | 19.430285279 s / 111 calls | Reported `nbMapForceBody` |
| Tree share p = tree / whole | about 0.00632 | about 0.32926 | Inference from those matching timers |
| Whole-run speedup if tree is 1.5x faster | about 1.0021x | about 1.1233x | Amdahl scenario: 1 / (1 - p + p/1.5) |
| Whole-run cap if tree is free | about 1.0064x | about 1.4909x | Amdahl scenario: 1 / (1 - p) |

These caps assume all other phases unchanged and comparable timer nesting.
They are not bounds on an instruction schedule. In particular, the small
case is overwhelmingly setup dominated and cannot validate a useful
whole-program tree-only gain. The ticket's older 13.2 s tree measurement
must not be combined with these different whole-run timers.

T_lb and T_pred for a complete tree invocation: unknown pending its code,
inputs, path frequencies, residency and call behavior. T_lb/T_meas,
T_pred/T_meas and per-resource utilization: unknown. No supported twin
prediction exists yet for this ticket, so no flag winner is selected.

## Available inputs and the missing work

Read-only probes are under
`C:/Users/xuzhi/Documents/knc-boinc/.work/S8-09/probes/`.

| Input | Work actually represented | Limitation |
| --- | --- | --- |
| `s8_subindex.c` | Three ordered `<=` decisions and one integer result store | An octant decision, not tree construction; no measured share within tree insertion |
| `s8_df_reuse.c` | Five-point expressions, division and sqrt in `s8_df_node` | Calls `sample_potential` and `sample_density` without definitions; no matching inputs or measured callee costs supplied |
| `walk-prefetch.c` | Data-dependent successor traversal with FP distance and division | Force walk, not `nbMakeTree`; needs real node layout/data and branch paths |

`SAMPLES_READ_ONLY` changes the optimizer's knowledge of the callees and
is not an existing-flag-only candidate. The probe itself says the real
dispatchers initialize parameters lazily. Do not enable that macro without
the separately proven ready-model API. Do not replace the callees with
zero-cost or invented-cost stubs for ranking.

The supplied `S8-08/docs/research/s8-force-model.md` reports unsupported
scalar twin runs and budget-exhausted vector runs on its captured force
walks. It explicitly has no usable prediction. Those statuses cannot be
reused as a ranking for the present flags or as a tree-build model.

## Existing timing evidence to carry into the operation table

All values here are reported production-card measurements, with stepping
unspecified, from `knc-machine.yaml` and the named rows in
`knc-characterization.md`. They are TSC ticks per operation per thread,
not an assertion that every count equals core cycles. The machine file's
`vector_arithmetic_latency` separately supplies a rounded four-core-cycle
dependency model (reported, R17 slide 12 architectural overview).

| Measured form | Dependency 1 / 2 contexts | Reciprocal throughput 1 / 2 contexts |
| --- | --- | --- |
| `x87_add` | 3.02 / 3.08 | 2.08 / 2.07 |
| `x87_mul` | 3.02 / 4.08 | 2.08 / 4.02 |
| `x87_div` | 39.25 / 76.30 | 38.24 / 76.27 |
| `masked_load` | 12.11 / 12.17 | 2.08 / 2.37 |
| `masked_store` | 12.11 / 12.17 | 2.08 / 2.08 (flagged in source) |
| `spill_reload` | 12.11 / 12.98 | 5.09 / 4.20 |

The memory dependency rows describe the characterization's composite
chains. They are not isolated load/store latency and cannot stand in for
a zmm-to-x87 or x87-to-zmm ABI bridge. Missing forms, including subtraction,
conversion, scalar compare/branch, sqrt, and the complete S10-09 sequences,
still require the requested faithful schedules and qualified twin output.
The full per-operation comparison is outstanding. Add/mul alone do not
establish an advantage for lane 0.

## Contract and phase-0 screening requirements

ADR-0003 points 1-4 retain x87 scalar bodies and distinguish source-format
FP from x87 excess precision. ADR-0004 points 4-6 already pass SF/DF in zmm
lane 0, retain x87 for long double, and expose transfer scratch registers.
Changing the internal arithmetic domain need not change the argument/result
ABI, but it does require an explicit policy decision about existing scalar
results. The ISA-page review, exception/errno analysis and forward-port
inventory remain outstanding; this input review is not semantic approval.

Phase-0 candidates should hold the FP contract fixed: 53-bit x87 precision
control, contraction off, no fast-math, same rounding/FTZ/DAZ state and
library implementation. A compiler scheduling density parameter does not
set runtime affinity or change the number of threads executing a serial
tree. FP reassociation, changing the pure-callee promise, and application
source transformations cannot be counted as flag-only gains.

The intended bounded screen is O2 versus O3/mphinix, assumed densities
1/2/4, unrolling, scheduling disabled, frame-pointer retention, and an
inlining-limit candidate, keeping each actual option list with its emitted
assembly. It has not run. Bit identity must be checked for the complete
application before a candidate can be recommended, particularly where
vectorization or spills change intermediate rounding.

After ranking, the lead's A/B list should contain both `core-small` and
`large`, with the existing baseline and one candidate build on identical
inputs, runtime libraries, FP setup and placement. Retain output bit
comparison, whole-run/setup/tree/force times and tree subphase times.
The list is not staged as executable card jobs because there is no selected
candidate or full application build input yet.

## Lead input needed before proceeding

1. Supply `nbMakeTree`'s reduced reproducer or the matching built object,
   complete build options, required callees and representative entry inputs
   via the lead, as the ticket requests. Include core-small/large branch
   data and the measured share of any proposed extracted subregion.
2. Supply definitions/captured behavior for the sample functions in
   `s8_df_node`, or identify justified costed stubs and their source. Provide
   representative force-walk inputs for the phase-0 comparison.
3. Clarify the no-hashing rule for mandatory twin adapters. Both
   `from_gcc_s.py` and `from_binary.py` generate source hashes; the former's
   `convert` writes `source_sha256` into `provenance` (line 425 in the
   inspected checkout). AGENTS.md forbids hashing and provenance files.
   No adapter was run and no workaround or local twin modification made.
   Is the existing tool's automatic metadata exempt, or should the lead
   supply a compliant normalized kernel path?

Completed host command, through the required wrapper:

```text
python tools/run.py --name s14-44-capabilities --inputs docs/research/knc-machine.yaml -- python C:/Users/xuzhi/Documents/knc-twin/scripts/knc_twin.py capabilities --out C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/S14-44/capabilities
```

Exit 0, status `ok`, engine 0.4.0. This is a capability query, not a
simulation, benchmark or native pass. Log:
`.work/_state/logs/s14_44_capabilities-20261117-010242.log`.
The capability output and validation reference were inspected: unlisted
instructions are unsupported, executed external calls need costed stubs,
and unvalidated shapes do not inherit the sparse-loop calibration band.
The three required paired region studies, full operation table, staged
card A/B list and final verdict remain open.
