# Pipeline progress after instruction families 29–31

This is one report-only pass over seven affected retained assemblies, using
one translator session. No compiler output was regenerated, no full census
was scanned, and no target math export is qualified. Unchanged wrappers were
skipped. The report took23.688 seconds.

| Retained unit | Unsupported names | Unsupported occurrences | Newly admitted |
|---|---:|---:|---:|
| ip1.knl.s | 57 | 497 | 31 |
| e_hyperbolic_export.knl.s | 41 | 284 | 25 |
| e_atan_export.knl.s | 40 | 451 | 39 |
| e_expf_export.knl.s | 6 | 13 | 5 |
| e_logf_export.knl.s | 13 | 63 | 18 |
| e_exp_export.knl.s | 20 | 140 | 28 |
| e_log_export.knl.s | 22 | 157 | 23 |

The expf unit is closest: six remaining names,13 occurrences. Its queue is
`after-families29-31-20261023/e_expf_export.knl.json`: two VPGATHERQQ, two
VPADDQ, five masked VMOVDQU32 stores, one masked VMOVDQA32 load, two VPSRLVD
and one memory VPBLENDMD. These are real operand/footprint gaps; no spelling
alias or register-only proof admits the masked memory operations.

A separate QWORD add/sub native batch is held-prepared. The gather source
investigation has four exact expf/exp witnesses; only expf table indices have
a retained small-table bound so far. The current runtime configure stopped on
an unrelated YMM VPANDN alias tuple, whose native batch is now running.

Evidence: `artifacts/test-state/after-families29-31-20261023/summary.json`.
G5 remains0/36 target-qualified exports. Whole Phase3/G3/G6/G10 remain open.
