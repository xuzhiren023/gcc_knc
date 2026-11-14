# S12-19: source-join coverage and implementation status

The host analysis contract passes all 10 approved tests. Production attribution
is blocked: none of the 15,109 sampled workload PCs in the available S11-15
profiles resolves to a source line in its sampled ELF. HPCG has no sampled
capture. These are missing inputs, not evidence that no hot loops were missed.
This is an interim finding; the ticket's corpus ranking is not complete.

## Implemented analysis

`tools/vec_triage.py` parses GCC opt-info diagnostics, distinguishes successful
loop vectorization from SLP and candidate messages, recognizes the six tested
reason categories, and joins diagnostics to supplied source-loop intervals.
Unknown diagnostic text remains visible in the row's diagnostic evidence;
silence or an unrecognized reason produces `unknown`.

The join assigns each sample once, to the innermost established source region.
PC intervals are half-open. Files, modules and program/variant identities must
match. Ambiguous regions and unknown source lines stay unmapped. Queried PCs
are individual observations; addr2line lookup does not fill gaps between them.
Successful vectorization takes precedence over failed candidate-mode reports.
Multiple reasons each receive the loop's time once, so reason totals overlap.
CPU time is the caller-supplied profile CPU total multiplied by sample share;
the caller must qualify that estimate using the profile's cadence and overhead.

`join` consumes an opt-info capture, established source regions, sampled-ELF
addr2line output, attributed PC text and CPU seconds, and writes ranked JSON.
`audit` queries the existing sampled executables without rebuilding or running
them. Neither command establishes source-loop boundaries from function names.
Automatic compilation/opt-info collection, production source-region discovery,
ranked Markdown tables and the final corpus reason summary remain unfinished.

## Existing profile coverage

The audit reads `S11-18/builds.json`, `S11-15/batch-attribution.json`,
`S11-15/batch-attribution-pcs.txt`, and the separate PB-gemm pilot
`S11-15/attribution-pcs.txt` under `.work/_shared`. It restricts executable access
to the 14 development programs. No held-out executable or source was opened.
The batch PC addresses were already normalized to ELF addresses by
`tools/s11_15_batch_attribution.py`; the pilot uses
`tools/s11_15_attribution.py`. Source queries use the frozen workload ELF for
each variant, or `S11-15/gemm` for the pilot, never a rebuilt executable.

| Program | Profile | Total samples | Workload samples | Workload samples with source lines |
| --- | --- | ---: | ---: | ---: |
| STREAM | serial | 797 | 491 | 0 |
| STREAM | openmp | 97 | 31 | 0 |
| NPB-CG | serial | 2976 | 2967 | 0 |
| NPB-CG | openmp | 130 | 97 | 0 |
| NPB-EP | serial | 9798 | 6093 | 0 |
| NPB-EP | openmp | 416 | 223 | 0 |
| NPB-MG | openmp | 78 | 49 | 0 |
| NPB-IS | serial | 1201 | 1195 | 0 |
| NPB-IS | openmp | 54 | 43 | 0 |
| HPCG | absent | — | — | — |
| SQLite | serial | 173 | 153 | 0 |
| PB-gemm | six-launch pilot | 521 | 466 | 0 |
| PB-atax | serial | 93 | 93 | 0 |
| PB-cholesky | serial | 1244 | 1238 | 0 |
| PB-ludcmp | serial | 1756 | 1755 | 0 |
| PB-jacobi-2d | serial | 68 | 61 | 0 |
| PB-heat-3d | serial | 49 | 37 | 0 |
| zlib | serial | 121 | 117 | 0 |

These counts cover 1,199 distinct workload addresses summed across captures.
OpenMP and serial profiles are separate observations; these totals are a
coverage inventory, not a combined performance score. NPB-MG only has the
OpenMP profile in the batch attribution. HPCG's batch-capture directory contains
only `serial-HPCG-plain.stdout` and `.stderr`, with no sample files. The ticket's
previous round reports that the plain launch timed out.

Raw addr2line captures and `profile-coverage.json` are under
`.work/_shared/S12-19/`. The JSON retains existing function rankings and profile
qualification issues. A named hot function, or the earlier disassembly's
candidate backedge envelopes, does not establish which source loop generated
its PCs. Applying new `-g` executable addresses to these old samples would be
an invalid join. Dynamic strides and mask occupancies are also unobserved by
the PC sampler; compiler candidate access messages alone cannot supply them.

## Validation and next required input

Both commands ran once on 2026-11-14:

```text
python tools/run.py --name s12-19-vec-triage-green --inputs tools/vec_triage.py tests/tools/test_vec_triage.py tests/tools/test_vec_triage_mapping.py -- python -m unittest discover -s tests/tools -p test_vec_triage*.py -v
python tools/run.py --name s12-19-profile-coverage --inputs tools/vec_triage.py -- python tools/vec_triage.py audit
```

The fixture run passed 10 tests. The audit completed successfully and exposed
the source-coverage blocker. Logs:

- `.work/_state/logs/s12_19_vec_triage_green-20261114-150628.log`
- `.work/_state/logs/s12_19_profile_coverage-20261114-150628.log`

No GCC change/build, corpus rebuild, native test, card job or x86 check ran.
The existing mapping fixture already supplies a real installed-prefix
opt-info capture, including the strict-FP sum's cost refusal; that is fixture
evidence only, not a corpus result.

To complete the requested source join, the lead needs to supply debug information
belonging to the frozen sampled ELFs, or authorize a replacement profiling set
with debug-enabled development executables and arrange its card capture.
HPCG needs a usable sample capture either way. The engineer cannot start card
jobs under AGENTS.md. If the frozen profiles must remain the sole input,
manual source-to-assembly correspondence needs a separately agreed evidence
standard before those samples can be assigned to source loops.

The requested final three compiler changes cannot yet be ranked by covered hot
missed time. Their legality conditions and measurement plans will follow the
completed join; proposing them now would substitute conjecture for the ticket's
required evidence.
