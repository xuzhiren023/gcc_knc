# Phase 5 source progress — target qualification open

There are now36 source-defined exports out of the final36, covering all
2,879 retained calls. Target-qualified exports remain0. These source and host
accuracy results are useful prerequisites, not G5 or a target-performance claim.

| Newly assayed operation | Worst sampled ULP | Evidence |
| --- | ---: | --- |
| powf |0.505089906|POWF_SOURCE_STATUS.md|
| pow |0.506832021|POW_SOURCE_STATUS.md|
| log10f |0.818855575|LOG10_SOURCE_STATUS.md|
| log10 |0.515543249|LOG10_SOURCE_STATUS.md|
| sinf / cosf |0.499998942 /0.499999602|TRIG_SOURCE_STATUS.md|
| sin / cos |0.770570913 /0.745124649|TRIG_SOURCE_STATUS.md|
| tanf / tan |0.499999729 /0.792255917|TAN_SOURCE_STATUS.md|
| atanf / atan2f / atan2 |0.499999991 /0.499999117 /0.918082165|ATAN_SOURCE_STATUS.md|
| sinhf / sinh |0.499998875 /0.530940535|HYPERBOLIC_SOURCE_STATUS.md|
| coshf / cosh |0.499997815 /0.533171500|HYPERBOLIC_SOURCE_STATUS.md|
| tanhf / tanh |0.499998883 /0.499998984|HYPERBOLIC_SOURCE_STATUS.md|

Every operation has a fresh assay above one million inputs per precision and
contraction variant, independent MPFR directed endpoints at256/384 bits,
specials and completed wrong-result controls. Compact wiring checks cover the
observed e/b/d exports, inactive poison, aliases and host FP controls. These
are sampled strict-SSE2 host results with no FMA; they do not establish target
ABI, native masks, directed rounding, complete exception/errno behavior or FMA.
The earlier exp/log definitions and their receipts remain unchanged.

The concrete target blocker is the incomplete ISA pipeline: IP-1 currently
reports82 unsupported mnemonics /2,005 occurrences, including memory,
arithmetic and conversions. The exported kernels must pass that same pipeline,
then actual card ABI/mask/numerical qualification. There is no scalar fallback.
A first DP atan2 composition exceeded the1-ulp target (1.007862114) and is
retained as a failed candidate. The separately assayed compensated revision
passes at0.918082165ULP and supplies the current export. The full36-symbol
host archive links with no duplicate definitions, unresolved library symbols
or scalar math fallback. Its1,152 public calls/10,752 lanes pass the explicitly
labeled aggregate policy: finite/zero/infinite results, flags, full MXCSR and
inputs exact; one separate-reference NaN payload/sign difference is reported
as unqualified. Public exports match their own actual library pointers bitwise
on every lane. The strict failed comparison remains intact; no accuracy corpus
was rerun or threshold relaxed. See COMPLETE_SOURCE_STATUS.md and
D3_NEW_SOURCE_COMPILE_STATUS.md for the actual records and new-source ISA queue.
