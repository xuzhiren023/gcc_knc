# Card runs, Sprint 6

Lead-run card jobs for Sprint 6 (`tools/card_run`; timing only in `--benchmark` windows).

## 2026-11-06: S6-01 timing probe, six exclusive windows

`tests/regress/knc-timing-probe.c` (S6-01), 2048 MiB limit, all exclusive `--benchmark` jobs,
raw output in `.work/_shared/S6-01/claude-bench/run1.out` to `run6.out`:

| Run | Cores x threads per core | Group-median spread | Under 2% |
|---|---|---|---|
| 1-3 | 60 x 4, three independent windows | 0.93%, 1.40%, 0.83% | yes |
| 4 | 60 x 1 | 1.37% | yes |
| 5 | 60 x 2 | 0.82% | yes |
| 6 | 60 x 3 | 10.58% (groups at about 72.6M and 80.7M cycles: bimodal) | **no** |

Single repetitions reach 21% above the median, so the protocol uses medians of groups. The TSC
calibrates at 1232.19 MHz against `CLOCK_MONOTONIC_RAW` in every run. Interpretation, including
the 3-thread bimodality, belongs to S6-01's note (`docs/research/knc-measurement.md`).

## 2026-11-06: S6-07 `gcc.dg/vect` run programs

At GCC `knc` after S6-04, 80 at a time on cores 59-40 (`claude-f7b0e10b…`): **776 of 777 pass**.
`pr121126.c` timed out under the driver's per-program limit. Its loop nest runs about 75 million
middle-loop iterations per outer iteration, so it is probably slow rather than wrong; it is rerun
alone with a longer limit at the next free slot.
