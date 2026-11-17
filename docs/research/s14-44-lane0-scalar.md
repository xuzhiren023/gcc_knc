# S14-44: scalar lane 0 feasibility — no-go

2026-11-17. **Do not start compiler implementation on this evidence.** No
complete tree model or 5% whole-program gain on two M4 programs is established.
**Verdict: no-go on the available evidence**, closing the research gate as
directed by the lead on 2026-11-17. This is not proof that lane 0 can never help.
No GCC change/build, card job, application
source change, or x86 check was made. Predictions below are not native results.

## Model

Hardware: reported production project card, stepping unspecified; twin engine
0.4.0, profile `card-7120-measured`. Machine inputs are `knc-machine.yaml` and
`knc-characterization.md`. Architectural evidence uses the R-number index.
R27 is an early KNC specification, not a production measurement.

Fixed work: nine octant decisions, eight ordered ludcmp products per context,
or one complete application run for Amdahl. No matching native region timing
exists: T_lb/T_meas, T_pred/T_meas and term utilization are unknown. Use 20%
separation for screening these unvalidated shapes; smaller differences need
card decisions. One or two contexts share one modeled core as labeled below.

### Whole-run cap (retained window-14 evidence)

Source: `C:/Users/xuzhi/Documents/knc-boinc/runs/card/w14/S8-09/`,
`batch-3-core-small-240.txt` and `batch-3-large-240.txt`, PHASE rows.
The 240-CPU grant does not imply that all phases use 240 workers.

| Term | core-small | large |
| --- | ---: | ---: |
| Whole run | 62.300974148 s | 30.610028089 s |
| Setup | 61.045101898 s | 1.110266230 s |
| Tree | 0.393688563 s / 33 calls | 10.078718534 s / 111 calls |
| Force | 0.777955700 s / 33 calls | 19.430285279 s / 111 calls |
| Tree share p | 0.00632 | 0.32926 |
| Whole-run speedup with 1.5x tree | 1.0021x | 1.1233x |
| Whole-run cap with free tree | 1.0064x | 1.4909x |

Formula: `1/(1-p+p/s)`, all other phases unchanged. These are Amdahl scenarios,
not instruction-schedule bounds. Do not combine the older 13.2 s tree number
with these timers. The large receipt also reports insertion 3.238936074 s,
center of mass 2.252465757 s, threading 1.785386262 s, quadrupoles 2.460644230 s,
expansion 0.159325856 s and partition 0.180233253 s. Deleting insertion entirely
would give only about 1.474x on this tree timer. Octant optimization is a subset
of that hypothetical deletion; this cap does not cover changing every FP phase.

### Inputs resolved after the lead answer

The main knc-boinc checkout contains upstream tree code. Its S8-09 worktree
contains the tree-variant and instrumentation patches already applied. The
experiment compiles that actual TU and the three supplied probes directly;
third-party source was not copied or modified. The worktree's saved
`build/card/.build-options` supplies includes and macros: tree variant 2,
phase timers 1, static integrate 1, parallel quad 1, walk layout 1, vector
gravity 0. Its optimization is O3. That current file alone does not prove the
configuration of the historical window-14 executable.

`core-small/params.lua` declares 4000 bodies. `large/params.lua` obtains nbody
from argument 1; the matching receipt reports `totalSimulated = 20000`.

All 40 compile/assemble operations succeeded: tree, subindex, df and walk,
each in ten flag configurations. Objects and assembly are under
`.work/_shared/S14-44/` as `tree-<variant>.s/.o`, etc. Compiler: installed
`gcc-knc-16.2.0`; this was not a GCC build. The patched tree TU exposes OpenMP
workers, allocation, timers and recursive moment/quad routines. Full
`nbMakeTree` timing is still unknown: real entry memory, callee behavior and
path/residency frequencies are unmodeled. No invented-cost stubs were used.
The octant study is not a complete tree model. Per the lead answer, carry this
gap forward without another request for tree source.

## Phase 0: existing flags

General-purpose recommendation: retain the conservative baseline
`-O2 -march=knc -fno-fast-math -ffp-contract=off`, with runtime PC=53 and
the application's required rounding/FTZ/DAZ state. This is a contract-preserving
starting point, **not a demonstrated fastest flag set**. No change to
`-mphinix` is justified. The scheduling-density and no-scheduling candidates
below are tied within uncertainty on one example; there is no M4/M5-wide
flag ranking. Do not generalize the example's no-errno, aliasing or OpenMP
options into a compiler preset. Existing callers' errno requirements remain.

Common flags: `-march=knc -ffp-contract=off -fno-fast-math -fno-math-errno
-fno-strict-aliasing -std=gnu99 -fopenmp`. No-errno is already in the application
configuration and stays constant; it is not recommended for a new caller that
requires errno. Twin state is PC=53, RN, FTZ=DAZ=0. Optimization flags do not set
those runtime controls or affinity.

| Variant | Additional flags | Predicted cycles, nine classifications |
| --- | --- | ---: |
| O2 | `-O2` | 2020 |
| O3 | `-O3` | 2020 |
| phinix | `-O3 -mphinix` | 2020 |
| density1 | `-O2 --param=knc-threads-per-core=1` | 2006 |
| density2 | `-O2 --param=knc-threads-per-core=2` | 2006 |
| density4 | `-O2 --param=knc-threads-per-core=4` | 2020 |
| unroll | `-O2 -funroll-loops` | 2020 |
| nosched | `-O2 -fno-schedule-insns -fno-schedule-insns2` | 2006 |
| frame | `-O2 -fno-omit-frame-pointer` | 2020 |
| inline | `-O2 -finline-limit=1000` | 2020 |

All statuses `ok`; expected results cover eight octants and equality. Inputs
are synthetic assumptions, not captured tree paths. `calls_table` excludes
caller argument setup but retains function entry/return. Scenario is
`line_tracking`, `cold_level: l1`, with default TLB/HWP/service sub-models;
it still reports miss stalls, so this is not an all-hot-L1 result.
The best difference is 0.69%, inside uncertainty: **no supported flag winner**.
Retain the existing application build until A/B. The df probe's sample
dispatchers remain undefined and walk needs real node state; compilation of
these probes is not a usable twin ranking.

### One staged card A/B list

Also staged at `.work/_shared/S14-44/card-ab.txt`, for lead execution only:

| Build | Optimization | Cases |
| --- | --- | --- |
| A | Existing O3, matched macros/runtime/PC=53/contract off | core-small; large |
| B | Replace O3 with `-O2 --param=knc-threads-per-core=1` | same cases |

This resolves uncertainty; B is not an application-speedup claim. Use the
existing knc-boinc build/package flow and coordinated card queue. Hold input,
seed, libraries, affinity and macros constant. Compare deterministic
scientific outputs bit-for-bit (excluding timestamps), and retain whole,
setup, tree, force and tree-subphase times. Reject B on any scientific bit
difference. No full application A/B binaries were built or run here.

## Paired regions

Handwritten candidates: `tools/s14_44_lane0.asm`. Driver:
`tools/s14_44_model.py`. Candidates assembled and passed `knc_lint`.
Only lane 0 performs FP arithmetic. No FMA replaces ordered multiply/subtract.
Completed octant and ludcmp twin runs matched finite external expected results.
This is neither an exceptional-value proof nor a card pass.

| Region / fixed work | Contexts | x87 bound / prediction | lane-0 bound / prediction | Prediction ratio |
| --- | ---: | ---: | ---: | ---: |
| Octant helper, nine calls | 1 | 229 / 2020 | 179 / 1689 | 1.196x |
| PB-ludcmp, eight products per context | 1 | 65 / 163 | 75 / 149 | 1.094x |
| Same ludcmp work on each context | 2 | 66 / 182 | 76 / 151 | 1.205x |
| Integer/hash plus FP-score, 32 bytes | 1/2 | analytical issue floor 254/255; twin unsupported | analytical issue floor 254/255; twin unsupported | unknown |

Units: total core cycles for the fixed work, not per-operation throughput.
Bounds are `conditional_bound`; predictions are `unvalidated_scenario_estimate`.
Do not divide bounds to claim proven speedup. The printed dependency-critical
path is treated as a cold-start estimate, not a floor. Reported bounds above
are the independent issue-spacing terms, which dominate these runs.

Ludcmp baseline is the exact eight-instruction `main:.L31` loop from S12-08's
retained `-O2 -march=knc` `ludcmp.s`: address shift, x87 load/multiply,
counter/compare, subtraction and branch. A standalone wrapper adds return.
Live accumulator is 16, eight products are 1*0.5, expected accumulator is 12.
The candidate keeps addresses/order and charges mask initialization. Both
assert L1 residency; the actual 4096-byte stride requires sensitivity work.
This residual loop has no measured M4 time share. S12-08 also found other
x87 stack traffic was ordered reduction storage, not removable pressure spills.

Original mix probe `tools/s14_44_mix.c`: rotate/XOR byte hash plus ordered
indexed double score. It is a compression-style diagnostic, not a measured
zlib/bzip2 region or copied codec code. Both objects exist. The x87 adapter
returned `unsupported` for `rol $0x5,%eax`. No cost was invented or workload
rewritten to evade this limitation. The lane version also contains `rol` and
has no claimed prediction. Both objects passed instruction linting.

### Mix analytical bound (lead-authorized unsupported fallback)

This is an analytical model, **not a twin prediction**. Sources for operation
counts are `mix-x87.s:.L3` in the shared ticket directory and
`tools/s14_44_lane0.asm:.Lmix`. Fixed work is 32 bytes and 32 ordered indexed
double additions per context, on one core with one or two contexts. Assume
resident code/data, predicted loop branches and independent private outputs.
The 256-entry score table occupies 2048 bytes; each stream reads 32 byte
elements and 32 doubles and stores one final double: **296 logical bytes**.
This is not 296 bytes of physical memory traffic; reuse, cache-line fills and
write allocation depend on residency. With the stated all-L1 assumption,
lower-level demand fills are zero; cold/missing-cache costs are excluded.

| Model term, per iteration | x87 | lane 0 |
| --- | --- | --- |
| Instructions | 7 | 8 |
| Integer/control | byte load, rotate, pointer add, XOR, compare, branch | same six |
| FP work | one memory-operand add | one broadcast load plus masked add |
| Logical reads | 1 + 8 bytes | 1 + 8 bytes |
| Optimistic minimum issue bundles | 1 unpaired x87 + ceil(6/2) = 4 | ceil(8/2) = 4 |
| FP accumulator recurrence | 3 cycles | 4 cycles |
| Indexed input path, excluding issue/AGI | byte load 3 + operand read 1 + add 3 = 7 cycles | byte load 3 + vector load 5 + add 4 = 12 cycles |
| Hash recurrence | rotate latency + XOR latency, rotate unknown | identical unknown chain |

Issue inputs: machine `thread_issue_interval=2` and `core_bundle_rate=1`
(V, architectural evidence R01 pp.19,23-24; R02 pp.34,56; not stepping-specific).
The optimistic packing is a lower bound on bundles, not a claim that every
adjacent pair is legal. X87 unpaired issue is reported production-card S12-31
evidence in twin `parameters.md:pairing.x87_pairs_with_scalar`. FP latencies
come from machine `x87_dependency` / `vector_arithmetic_latency` and twin
`latency.x87_add=3`, `latency.vector_arith=4` (R, project production card;
vector architectural support R17 slide 12). The split memory costs 3/1/5
come from twin `latency.scalar_load_l1` (reported S6-03),
`latency.x87_mem_operand_load` and `latency.vector_load_l1` (derived, E;
production-card S12-31/S6-03 composites, not isolated measurements).
The full indexed-input path is cold-start latency, **not a recurrence floor**:
loads for later iterations can overlap. Rotate timing is deliberately unknown;
no vendor latency has been invented to fill the adapter gap.

For C contexts each doing N=32 iterations, a finite body issue-span floor is
`max(2*(4*N-1), (4*N*C-1)/1)` = **254 core cycles for C=1, 255 for C=2**,
for either implementation. The endpoint subtraction excludes the final
instruction's completion latency, so this is also a conservative completion
floor. The FP recurrence contributes 96 cycles (x87) or 128 cycles (lane),
and cannot strengthen that floor. Two loads per iteration would
require at least 64/128 core load slots at C=1/2, also below the issue bound.
Thus **T_lb=254/255 cycles for either body at one/two contexts** under
these assumptions; the asymptotic issue budget is eight cycles per iteration.
Entry, exit, mask initialization, initial accumulator and final store are
outside this body-only budget: x87 has eight entry instructions and two exit
instructions; lane has eight entry instructions and two exit instructions.
Alignment padding is also omitted, making this optimistic. No bound ratio is
a speedup estimate. T_pred and native T_meas remain unknown because rotate
timing and the executable pairing schedule are unsupported; all utilization
ratios are unknown. Integer issue and indexed loads remain in both versions,
and lane 0 adds an instruction and lengthens the FP chain. This provides no
demonstrated gain for a codec or the general integer/FP mix.

## Per-operation evidence and remaining unknowns

Reported production-card measurements from `knc-characterization.md`, S6-03,
**TSC ticks per operation per thread**, one / two contexts:

| Form | Dependency | Reciprocal throughput |
| --- | --- | --- |
| x87 add | 3.02 / 3.08 | 2.08 / 2.07 |
| x87 multiply | 3.02 / 4.08 | 2.08 / 4.02 |
| x87 divide | 39.25 / 76.30 | 38.24 / 76.27 |
| IMCI add (measured PS) | 4.02 / 4.08 | 2.08 / 2.07 |
| IMCI multiply (PS) | 4.03 / 4.08 | 2.08 / 2.07 |
| IMCI FMA (PS) | 4.02 / 4.08 | 2.08 / 2.07 |
| IMCI double to int32 | 7.04 / 7.11 | 2.08 / 2.07 |
| IMCI int32 to float32 | 4.03 / 4.08 | 2.08 / 2.07 |
| Masked load composite | 12.11 / 12.17 | 2.08 / 2.37 |
| Masked store composite | 12.11 / 12.17 | 2.08 / 2.08 (source flags latter) |

PS results are not measured DF results. Machine key
`vector_arithmetic_latency` is a rounded four-core-cycle model, reported from
the characterization and R17 slide 12 (architectural overview). Memory
latencies above are composite chains, not isolated load or bridge costs.

Completed twin probes: **total core cycles for 32 operations plus return**,
one / two contexts; every context executes 32 operations. These predict
chain completion, not independent-operation reciprocal throughput:

| Probe | x87 | lane 0 |
| --- | --- | --- |
| add | 98 / 100 | 129 / 131 |
| subtract | 98 / 100 | 129 / 131 |
| multiply | 98 / 132 | 129 / 131 |
| FMA | N/A | 129 / 131 |
| divide | 1216 / 2432 | not run |
| sqrt | 2240 / 4480 | not run |
| compare + status/mask transfer + test + branch | 355 / 645 | 259 / 261 |
| load + store same double | 320 / 322 | 384 / 386 |
| x87 store + broadcast to lane 0 | 198 / 199 | N/A (bridge sequence) |
| lane-0 packstore + x87 load + pop | 387 / 389 | N/A (bridge sequence) |
| int32 load/convert + int32 store/convert, RN | 320 / 322 | not run |
| double to int32, repeated independent source | N/A | 69 / 70 |

Compare rows are composite fixed-input paths, not isolated compare latency.
Sqrt uses the twin's **assumed** 70-cycle P5 prior, not measured KNC evidence.
FMA is inventory only; contraction stays off. These operation probes have no
independent expected-value oracle: tracing them is not numerical qualification.
The double-to-int row uses the same source register for each operation, so
it is an independent-input stream, not a conversion dependency chain. The
measured 7.04/7.11 latency and 2.08/2.07 reciprocal throughput above remain
the appropriate per-operation evidence. The x87 integer roundtrip uses RN;
it excludes C truncation's control-word save/change/restore sequence.
Bridge rows include scratch dependencies and, for lane-to-x87, a balancing
pop; repeated x87-to-lane stores have no feedback from the broadcast result.
Their cycles divided by 32 are composite stream costs, not isolated ABI
latencies. None may be subtracted wholesale from a caller's execution time.

The operation batch stopped because its two-context load/store input shared
scratch: `context 0 stores to lines that context 1 loads; contexts communicating
through memory are not supported by the sequential functional model`. The
reporting helper then mishandled the null prediction. Both staging bugs are
fixed (private scratch and nullable prediction). The lead-authorized single
rerun on 2026-11-17 passed: 34 simulations and 34 bounds returned `ok`, with
`unsupported: []`; assembly and instruction lint also passed. No native test
ran. Log: `.work/_state/logs/s14_44_operations_fixed-20261117-092440.log`.

Missing: independent throughput for unmeasured forms, isolated conversion
and bridge latencies, int32-to-double lane-0 cost and lane-0 S10-09 div/sqrt
costs. Machine-file values do not supply these missing sequence costs;
their one/two-context latency and reciprocal throughput remain **unknown**.
Subtraction uses the twin add class (prediction); its isolated production
latency/throughput was not measured here. X87 FMA has no single-instruction
equivalent and contraction is forbidden. The S10-09 masked
`div_kernel_n`/`sqrt_kernel_n` assembly and ADR-0003 qualification were inspected.
Instruction counts are not scalar latency. No fast reciprocal or scalar x87
path is presented as the correctly rounded IMCI sequence's cost.

## Semantics and implementation boundary

ADR-0003 points 1-4 and ADR-0004 points 4-6 apply. SF/DF arguments/results
already use zmm lane 0, so internal arithmetic can change without changing
that external ABI. Long double remains x87. Default policy needs an ADR-0003
amendment and ADR-0004 clarification of the internal domain and scratch rules.

Verified R27 pp.39,55-56 (early KNC specification): x87 FCW/FSW and IMCI MXCSR
are distinct state; IMCI uses MXCSR rounding/FTZ/DAZ and reports flags without
unmasked FP traps. PC=53 does not synchronize rounding modes. A
`-frounding-math` implementation must respect both domains; static RN/SAE is
not a general replacement. Verified R27 pp.114-115,144-147: arithmetic masks
suppress inactive elements, compare masks zero inactive destination bits,
and ordered LE needs signaling-NaN handling. The candidate uses predicate 2.
No production exception test ran.

PC=53 retains x87's extended exponent range. Lane-0 DF can overflow/underflow
earlier and differ in subnormal rounding and flags. PC=53 does not force float
intermediates to 24 bits either. Contraction-off does not ensure bit identity
against existing x87 output. Source-format lane-0 arithmetic is plausibly
closer to SSE2 x86-64 results — an **inference**, not demonstrated identity.
Libraries, evaluation order, NaN payload choices and FP state still matter.

Arithmetic instructions do not implement libm errno policy: preserve caller
requirements and required fallback behavior. Existing application no-errno
flags are separate from compiler-default semantics. S10-09 sequences retain
their proven rounding/FTZ/DAZ conditions. Internal FMA in a correctly rounded
algorithm does not authorize contracting application expressions.

If the go gate later clears: KNC-only SF/DF arithmetic, compare and conversion
patterns in imci.md; scalar masks/moves; costed bridges; secondary reload/spill
classes; allocation across caller-saved zmm/k registers; mixed long-double
conversions; call/varargs, fenv, exceptional-value and rounding checks. Never
enable SSE/AVX/AVX512 flags. Forward-port cost is nontrivial: KNC patterns are
isolated, but shared i386 mode/class, reload and scalar-expansion gates need
re-audit at each donor update. No quantitative staffing estimate is established.

## Qualification and handoff

### General-purpose decision, including M4/M5 coverage

The primary evidence is the M4 scalar/reduction work, not knc-boinc's tree.
S12-06 and S12-08 do not provide a removable whole-program gain for the
lane-0 proposal. The latter's modeled ludcmp residual is outside its selected
hot factorization ranges. Its 1.094x/1.205x predictions apply only to eight
products per context, not ludcmp as a whole. To obtain a 1.05x program speedup,
`p >= (1-1/1.05)/(1-1/s)`: at the exact modeled ratios 163/149 and 182/151,
the changed region would need **55.4% / 28.0%** of program time. Its share
is unknown. The two-context figure also does not represent the serial M4
primary configuration.

NPB-EP has 51.174 s of transform/call-site CPU exposure and 36.794 s in the
log path in S12-06; those are sampled CPU attribution estimates, not measured
wall fractions of a lane-0-removable region. `m4-baseline.md` records
97.999557 s interior wall and 97.990 s user time for the matching sampled
run. Even treating 51.174/97.999557 = 52.2% as a conditional share would
require about **1.100x** over that entire site for 1.05x whole-program speedup.
No such lane-0 transform prediction exists; the log library body is not a
compiler-removal budget. S12-06's returned diagnostic used 240 workers and
established no serial whole-program improvement or removable-time floor.

S11-20's `code-style-coverage.md` lists C/N checks Q1/Q2 (ray/container and
small double value types), Q3 (MD) and Q5 (smallpt) as proposed unscored checks,
with no performance results. No retained S11-20 shared experiment directory
is present here. This ticket has no compiled/timed C/N flag ranking and no
M5 generalization claim. The compression-style probe is original synthetic
work, not measured zlib/bzip2 execution; its rotate adapter failure and equal
analytical issue floors cannot establish a codec gain. These are coverage
gaps, retained rather than replaced with application-specific successes.

**No-go:** neither a >=1.5x complete-tree bound nor >=5% whole-program gain
on two M4 programs is established. The tree example's octant prediction is
1.196x, below 1.5x even before accounting for unchanged tree work; it is not
a bound on all tree phases. The whole-run free-tree caps are 1.0064x
(core-small) and 1.4909x (large). The latter does not itself disqualify the
tree-local gate; it limits the payoff even if that gate later clears.
Strict FP remains a separate gate: ordinary lane-0 DF changes x87 exponent
range and exception behavior, so no default replacement is approved.

Phase 0 likewise yields **no supported faster general-purpose flag set**:
retain the conservative baseline and do not alter `-mphinix`. The sole
ranked example differs by 0.69%, inside model uncertainty. Keep the staged
core-small/large A/B list as a falsifiable secondary example for the lead,
not as primary evidence or a per-application compiler policy. Remaining
sequence-cost and corpus gaps do not reopen this ticket: the lead directed
recording them and closing with this no-go, with no further card/GCC work.

Successful predictions report `unsupported: []`, calibration state
`imported_microbenchmarks_with_compiled_heldout_check`, and
`unvalidated_scenario_estimate`. The 105 compiled-loop validation set is HPCG
plus a sparse microbenchmark family; these shapes do not inherit its error band.

Leading printed constraints (context-cycle attribution, not additive bounds):

- Octant x87: miss_stall 888, x87_serial 421, dependency 249, core_busy 174.
- Octant lane: dependency 755, miss_stall 607, spacing 137, agi 9.
- Ludcmp one-context x87: spacing 48, x87_serial 40, agi 8; lane: spacing 57, dependency 24, agi 8.
- Ludcmp two-context x87: spacing 96, x87_serial 80, not_picked 27, agi 16; lane: spacing 114, dependency 48, agi 16, core_busy 1.

Operation rerun constraints below reproduce the printed context-cycle
attributions (not additive bounds). `S=spacing`, `D=dependency`,
`B=core_busy`, `N=not_picked`, `R=resource`, `X=x87_serial`,
`I=store_interlock`; omitted constraints were not printed.

| Probe | One context | Two contexts |
| --- | --- | --- |
| x87 add/sub | S32 D31 | S64 D62 B1 N1 |
| x87 multiply | S32 D31 | S64 R63 D62 N2 |
| x87 divide | D1116 S32 | R2330 D2232 S64 N63 |
| x87 sqrt | D2108 S32 | R4346 D4216 S64 N63 |
| lane add/sub/multiply/FMA | D62 S32 | D124 S64 B1 N1 |
| x87 compare | B224 S32 | B897 N129 S64 |
| lane compare | S96 D64 | S192 D128 B1 N1 |
| x87 load/store and int roundtrip | X157 I64 S32 | X314 I128 S64 B1 |
| lane load/store | D189 S64 I64 | D378 S128 I128 B1 |
| x87 to lane | S64 I64 | S128 I128 B1 N1 |
| lane to x87 | X160 S64 I64 | X320 S128 I128 B1 |
| lane to int | S32 | S64 B1 N1; core_issue_slots: issue utilization 0.99: the core issues nearly every cycle |

Successful commands used tools/run.py. Logs under `.work/_state/logs/`:

- `s14_44_phase0-20261117-011337.log`: PASS; 40 compilations and ten octant models.
- `s14_44_regions-20261117-011751.log`: FAIL at unsupported mix rol; preceding octant/ludcmp results retained.
- `s14_44_operations-20261117-012000.log`: FAIL at scratch sharing/null reporting; preceding operation results retained.
- `s14_44_operations_fixed-20261117-092440.log`: PASS; authorized single rerun, all 68 model results ok and assembly/lint passed.

Artifacts remain in shared S14-44. Tool-generated cache hashes are not copied
or committed. Do not rerun passing batches; narrow a follow-up to missing work.
The lead resolved the previous ask: retain unsupported rotate, use an
analytical mix bound, rerun operations once and close the gate. No further
tree-source or twin-support request; no passing experiment was rerun except
the explicitly authorized operations batch.

## Twin assumptions retained verbatim (region runs)

The operation rerun uses the same printed precision, fixed-level memory,
prefix/loop-boundary, resident-code, forward-branch, result-availability and
x87-serialization assumptions below, plus this printed conversion assumption:

- vcvtfxpntpd2dq/udq write the 8 results to the low lanes and zero the upper 8 (assumed)

- L2 hardware prefetcher sub-model: a stream per 4 KiB page after two accesses with the same stride (<= 2 lines), prefetching 16 lines ahead within the page into L2; prefetched fills do not use L1 demand-miss slots (assumed)
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged
- TLB sub-model: 64-entry fully associative LRU first-level DTLB for 4096-byte pages; a miss adds 29 cycles; second-level TLB reach and page walks are not modeled
- a taken forward branch, call or return costs the core 1 issue cycle(s) for the prefetch-buffer refill (R02 ch.4; S8-01 C10 fixed-direction row at four threads); loop back-edges pay nothing (S8-01 C9 at two threads); hidden at one thread by the same-context spacing
- calls_table supplies argument registers between function calls without caller instruction costs; memory, caches and other registers persist; expected outputs describe the final call
- fixed_level memory scenario: access levels are asserted by the scenario, so software prefetches change no access level and only cost issue slots
- front end: crossing a 16-byte or 64-byte boundary and the loop-head offset cost nothing (S12-31 mis_4..mis_60 within 0.45 ns per row)
- front end: instruction bytes come from the listing; each two-cycle prefix (66, 67, lock, segment, rep: R02 p.56) delays that instruction's issue to 2 cycles per prefix after the previous issue of its context, which the 2-cycle same-context spacing hides for one prefix (S12-31 padding rows); an instruction with such a prefix does not pair (assumed)
- instruction cache: code is assumed resident in the L1 instruction cache (steady-state hot region)
- line_tracking: true LRU replacement stands in for the hardware's pseudo-LRU; the L1 and L2 are modeled as private to the core with no coherence traffic
- load-to-use beyond L1 = level latency + (L1 form latency - scalar L1 latency); the extra form cost is assumed additive
- memory service sub-model: one memory fill per 20 core cycles for this core (measured sequential-stream rate, includes the hardware prefetcher); card-level sharing not modeled
- register results are available to any context's dependent instruction exactly latency cycles after issue; no bypass penalties beyond the measured latencies
- sign/zero extensions (movslq, movs*, movz*, cltq) cost a plain mov or scalar load plus latency.scalar_extend_extra and pair per pairing.extend_v_pairs: evidence E, inferred, no KNC source
- x87 instructions issue on U only (register-file diagram, R01) and alone (S12-31); a memory-operand x87 load or arithmetic instruction holds its context until its result is complete; x87 stores retire like scalar stores
- x87 precision control is 53-bit: results round to that significand with the extended exponent range

Assumed/derived parameters used by those runs (values as printed):

| Parameter | Value | Status | Unit |
| --- | --- | --- | --- |
| frontend.taken_branch_core_bubble_cycles | 1 | derived | core issue cycles lost after a taken branch |
| l2.hw_prefetch_depth_lines | 16 | derived | lines ahead per confirmed stream |
| latency.branch_taken_bubble | 0 | derived | cycles |
| latency.mask_op | 1 | assumed | cycles |
| latency.memory | 328 | derived | cycles |
| latency.scalar_extend_extra | 0 | assumed | cycles added to the plain mov/ALU (register form) or scalar load (memory form) latency of movslq, movs*, movz*, cltq, cltd, cqto |
| latency.store_to_load_same_line | 7 | derived | cycles after a store issues before a load of the same line sees the data |
| latency.vector_load_l1 | 5 | derived | cycles, L1 hit plain vector load to dependent use |
| latency.x87_control | 7 | assumed | cycles |
| latency.x87_compare | 3 | assumed | cycles |
| latency.x87_move | 3 | assumed | cycles |
| latency.x87_sqrt | 70 | assumed | cycles |
| latency.x87_load | 3 | derived | cycles from issue until the loaded value is on the x87 stack |
| latency.x87_mem_operand_load | 1 | derived | cycles for the memory operand of an x87 arithmetic instruction before the operation starts |
| pairing.load_store_pair | True | derived | boolean |
| pairing.u_instruction_can_be_branch | False | assumed | boolean |
| store.load_after_store_interlock_cycles | 4 | derived | cycles after a store before the same context may issue a load |
| x87.mem_operand_serializes | True | derived | boolean |
