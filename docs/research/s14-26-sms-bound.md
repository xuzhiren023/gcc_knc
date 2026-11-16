# S14-26: software-pipelining bound, incomplete

Evidence date: 2026-11-16. **No-go for starting S14-02 on the available
evidence; the quantitative decision remains blocked.** Six current public-corpus
objects were compiled with the installed GCC-KNC at `-O2 -march=knc`, and all six
selected innermost regions converted with `from_binary.py --loop`. Static loop
bounds succeeded. However, two actual modulo attempts (GEMM and Jacobi) returned
`unsupported: explored region contains an interior label`: the binary adapter
labels every instruction, while the scheduling explorer rejects interior labels.
Neither attempt produced an II, register-pressure estimate, candidate, or result
class. Thus the required >=5% whole-program bound on two programs is **not
established**, rather than disproved. No labels or instructions were removed to
work around an unsupported result. Real-trace simulation and rollup remain unrun;
substituting adapter live-in zeros or an unchanged baseline as a modulo candidate
would not answer the ticket. The two-failure rule requires a question to the lead.

## Model

The accounting unit is one execution of the selected compiled body in one
context, in modeled core cycles. Bounds use `card-7120-measured`, the default
`fixed_level/l1` memory scenario, and `all_predicted` branches. These are
optimistic resource/recurrence bounds, not measurements or executable pipelines.
The objects are today's builds, not the historical profile executables. Sources
are the existing public `.work/_shared/corpus-build/sources` tree, using the
corpus script's dimensions and serial NPB class-A configuration. No sealed files
were read. The compile recipe is `tools/s14_26_sms_bound.py`.
The installed driver reports GCC 16.2.0; its exact compiler commit is not
established by that version string. No current-checkout commit is substituted.

| Program; function; object-relative head | Body instructions | ResMII | RecMII | MII | Static critical path | Today's simulated cycles/iteration | Modulo II / register pressure | Status / result_class |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| PB-gemm; main; 0x9c8 | 10 | 10 | 1 | 10 | 10 | unknown, not run | unavailable / unavailable | bounds: ok / conditional_bound; modulo: unsupported / absent |
| PB-jacobi-2d; main; 0x250 | 123 | 210 | 2 | 210 | 27 | unknown, not run | unavailable / unavailable | bounds: ok / conditional_bound; modulo: unsupported / absent |
| PB-heat-3d; main; 0x660 | 29 | 48 | 1 | 48 | 30 | unknown, not run | not run / not run | bounds: ok / conditional_bound |
| NPB-MG; resid_; 0x6470 | 21 | 32 | 1 | 32 | 22 | unknown, not run | not run / not run | bounds: ok / conditional_bound |
| NPB-CG; conj_grad_; 0x10c8 | 8 | 8 | 12 | 12 | 16 | unknown, not run | not run / not run | bounds: ok / conditional_bound |
| zlib; slide_hash; 0x58 | 10 | 10 | 3 | 10 | 6 | unknown, not run | not run / not run | bounds: ok / conditional_bound |

All numbers above are exactly the successful `bounds --loop --trace-source
static` outputs. The zlib body has an internal conditional branch: the twin
explicitly charges **both arms** in its static-body basis and says a dynamic
iteration that skips an arm can be shorter. Its MII must not be treated as a
universal bound on actual dynamic iterations. The chosen dense bodies are vector
loops; CG is the indexed x87 sparse-product body; zlib is scalar hash sliding.
The other bodies were not passed to modulo after the second failed attempt.

| Term | Formula / inputs | Source | GEMM / Jacobi / heat / MG / CG / zlib |
| --- | --- | --- | --- |
| Core issue | twin minimum issue events per static body | each `bounds/result.json`, `prediction.res_mii_terms.core_issue_events` | 5 / 105 / 24 / 16 / 4 / 5 |
| Context spacing | twin issue events times modeled context gap | same, `per_context_spacing`; machine input `thread_issue_interval` | 10 / 210 / 48 / 32 / 8 / 10 |
| L1 port | twin resource occupancy per body | same, `l1_port` | 6 / 84 / 16 / 14 / 3 / 2 |
| x87 occupancy | twin x87 resource occupancy | same, `x87_unit_occupancy` | N/A / N/A / N/A / N/A / 3 / N/A |
| Recurrence | maximum modeled circuit latency/distance | same, `prediction.rec_mii` | 1 / 2 / 1 / 1 / 12 / 3 |
| T_lb | max(ResMII, ceil(RecMII)) under stated static-body assumptions | same, `prediction.mii_cycles_per_iteration` | 10 / 210 / 48 / 32 / 12 / 10 |
| T_pred; T_meas; utilization | unknown; no faithful live-in/input snapshot supplied for these selected current regions, no matching per-body measurement | adapter `provenance.live_in_registers_placeholders`; historical PC profiles below | unknown for every body |
| Candidate gain; program gain | needs valid baseline cycles, achieved II, pressure and qualified share | modulo attempts did not produce a candidate | unknown for every program |

The machine input is `docs/research/knc-machine.yaml`, notably
`thread_issue_interval` (V; R01 pp.19,23-24 and R17 slides 10-14;
architectural description, not a stepping-qualified experiment),
`x87_dependency` and `x87_core_reciprocal_throughput` (R; reported S6-03 project
measurements on the production card), and `l1_l2_transfer_service` (E; unknown).
No unknown transfer rate was filled in. The bounds do not use a trace's
`dependency_critical_path` cold-start estimate.

T_lb/T_meas, T_pred/T_meas and every term's T_i/T_meas are unknown, since no
matched loop-cycle measurement exists here. A speculative regional speedup and
Amdahl cap are not asserted. The 30% unvalidated-shape decision caution in the
handoff remains applicable; no candidate ranking or hardware win is claimed.

## Profile evidence and why no rollup is reported

Existing M4 profiles were found under `.work/_shared/S11-15`, so no host timed
run was started. They locate hot bodies but are conditional CPU-PC shares, not
automatically whole-program wall-time shares. Historical addresses below are
distinct from today's object-relative addresses above. Several profiles fail
their own sample qualification. MG has only the OpenMP profile in the inspected
batch, whereas today's selected object is serial. These are leads for obtaining
matching shares, not values silently fed to rollup.

| Program | Historical hot region / available PC share | Qualification |
| --- | --- | --- |
| PB-gemm | vector GEMM body: 439/521 = 84.261% | `attribution.md`: capture/count/cadence/overhead and function attribution pass; wall attribution requires interpretation |
| PB-jacobi-2d | 0x400ba0..0x400f1d: 29/68 = 42.647% | `batch-attribution.json`: fewer than 300 PCs |
| PB-heat-3d | 0x400fc0..0x401084: 18/49 = 36.735% | same: fewer than 300 PCs |
| NPB-MG | OpenMP resid body 0x4023d0..0x402466: 9/78 = 11.538% | same: cadence, overhead, fewer than 300 PCs, worker coverage; not a serial share |
| NPB-CG | indexed sparse product 0x402480..0x402499: 2507/2976 = 84.241% | same: issues=[]; today's corresponding body has changed instruction order |
| zlib | second slide_hash loop 0x401da0..0x401dbb: 16/121 = 13.223% | same: fewer than 300 PCs; total function share is not the selected-loop share |

Rollup has **not run**: neither a simulated executable modulo pipeline nor an
II-to-region candidate interface was produced. Its documented candidate path
simulates a reordered body, not the hypothetical overlapped II. Reporting that
ratio as SMS benefit would be misleading even with qualified time shares.
No zero-gain rollup, fictitious time share, host-to-card timing extrapolation,
or native pass is reported.

## Exact retained evidence and reduced reproducer

Outputs live under `.work/_shared/S14-26/<program>/`: `binary.dis`,
`coverage.json`, `loop-overlay.json`, `loop.json`, `loop-coverage.json`, and
`bounds/result.json`. The first two programs also have `modulo/result.json`.
All six selected-loop adapters report complete parser, ISA, functional and
timing coverage. Whole-function discovery reports are not whole-function
execution results.

Reproducer, from this worktree after compilation:

```text
python tools/run.py --name S14-26-modulo-gemm --inputs knc-twin tools/s14_26_sms_bound.py -- python knc-twin/scripts/knc_twin.py schedule ../_shared/S14-26/PB-gemm/loop.json --method modulo --out ../_shared/S14-26/PB-gemm/modulo
```

The GEMM loop has no internal control branch: only its final back edge. The
adapter's `a9cf` record has `label: .A_9cf`, as do the other instruction records.
`knc_model/scheduling.py::_Region` rejects any noninitial labeled instruction
before functional tracing. Jacobi independently reproduces the same refusal.
No twin code was changed; acceptance says unsupported results must stand.

Both modulo results print `status=unsupported`,
`message="explored region contains an interior label"`,
`assumptions=[]`,
`unsupported=["explored region contains an interior label"]`, and
`limiting_constraints=[]`. `result_class` and `prediction` are absent. All six
bound results print `assumptions=[]`, `unsupported=[]`, and prediction class
`conditional_bound`; their resource terms are in the Model table. They do not
print `limiting_constraints`. Profile calibration metadata remains attached in
the result files and is not evidence that these six shapes are validated.
The used assumed/derived parameters are `latency.vector_load_l1=5` (derived,
GEMM/Jacobi/heat/MG; profile attribution to S6-03 spill_reload.lat and c9.memory.u1)
and `latency.scalar_extend_extra=0` (assumed, CG/zlib; explicitly unmeasured,
lead decision 2026-11-15). These are model inputs, not new hardware findings.

Run logs under `.work/_state/logs/`:

* `S14_26_capabilities-20261116-135336.log`: PASS.
* `S14_26_compile-20261116-135529.log`: PASS, six current objects, installed GCC version captured.
* `S14_26_inspect-20261116-135617.log`: discovery completed; individual whole-function unsupported coverage retained.
* `S14_26_loop_bounds-20261116-135738.log`: six selected-loop adapters and six static bounds PASS.
* `S14_26_modulo_gemm-20261116-135817.log`: FAIL, twin exit 3, unsupported interior label.
* `S14_26_modulo_jacobi-20261116-135820.log`: FAIL, twin exit 3, same unsupported status.

Lead question: should this ticket close as unsupported/no-go evidence, or wait
for a twin fix accepting unreferenced adapter labels, matching loop inputs/shares,
and an approved way to roll up hypothetical modulo II? A successful reorder-only
rollup would not establish the requested overlapped-program bound.
