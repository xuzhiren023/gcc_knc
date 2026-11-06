# S6-10 results

The resumed fix adds zero and all-ones alternatives to both KNC HI and QI
moves: KXOR and KXNOR respectively (Intel 327364-001). Other immediates still
require a GPR. The failed recognition guard and shared i386.cc guard are removed.
GCC commit: 7d96f2cef8c.

The lead traced the first invalid move in vect-63.c to peephole2:
`v.c.344r.peephole2`, `gen_peephole2_12`. The shared i386.md peephole at
line 3329 folds `cx = -1; k1 = cx` into `k1 = -1`. The KNC alternatives now
implement that output directly; the peephole itself is unchanged.

The existing DI non-CMOV ffs fix generalizes the SI split to SWI48. Relative
to the S6-09 base b12c3242595, shared i386 changes are confined to i386.md:
+10/-10 lines in two hunks with default three-line diff context: the
expander dispatch and the existing no-CMOV split.
There is no remaining i386.cc delta. KNC-only imci.md totals +20/-9 in five
hunks. No flags enable SSE, AVX or AVX-512.

Red: all eight reduced reproducers failed with the expected original ICEs,
recorded by the existing red commit 6d297ad and
`.work/_state/logs/s6_10_red-20261106-093008.log`.

The committed full build passed in 10.6 minutes:
`.work/_state/logs/s6_10_mask_build-20261106-105644.log`.
All eight reduced and all eight upstream reproducers compile and lint clean.
Both s4_masks variants compile and lint clean:
`.work/_state/logs/s6_10_mask_cases-20261106-110733.log`.

The following linted binaries are staged under `.work/_shared/S6-10/` for
the lead's card run:

- vect-63.mic
- vect-outer-2b.mic
- vect-outer-2d.mic
- vect-double-reduc-3.mic
- vect-double-reduc-7.mic
- vect-simd-17.mic
- s4_masks-o2v.mic
- s4_masks-o3.mic

The ffs upstream cases are compile tests. No native card execution has been
performed by this engineer; runtime acceptance remains for the lead.
T0/T1/T2 passed, including the formerly permission-blocked T2 cases.
Tier log: `.work/_state/logs/s6_10_mask_tiers-20261106-110752.log`;
full tier results: `.work/_shared/S6-10/tiers.txt`.

Torture passed all 8,012 measurements (2,003 files, four levels). Compared
with the tracked baseline and the preceding S6-10 run, the classifications
and failure lists are unchanged: O0/O2/O2-g/O3 have 1967/1968/1968/1968
passes, 34/33/33/33 compiler errors, and two user inline-asm rejections at
each level. Every other class is zero. There are no torture classification
changes to list. Assembly differences were not measured. The generated
summary omits historical baseline commentary and updates timing/measurement
metadata; those are not classification changes.
Torture log: `.work/_state/logs/s6_10_mask_torture-20261106-110752.log`;
summary: `.work/_shared/S6-10/torture-summary.txt`.
