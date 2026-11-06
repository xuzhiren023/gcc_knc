# S6-10 partial results

The DI non-CMOV ffs change passes both reduced and upstream pr109011-4/5
compile/lint checks. The mask recognition guard is unsuccessful: all six
remaining reduced and upstream cases still ICE on a constant -1 into k1.
The diagnostic changes from unsatisfied constraints to unrecognizable insn.

Reproducer: tests/regress/s6-07-vect/vect-63.c, with
`-O2 -ftree-vectorize -fno-tree-loop-distribute-patterns -fno-vect-cost-model
-fno-common -march=knc`. The failing RTL remains
`(set (reg:HI 69 k1) (const_int -1))` at cprop_hardreg/extract_insn.
The question for the lead is whether the next attempt should replace the
recognition guard with HI mask constant secondary reload through a GPR,
and trace where this already-invalid move originates.

Two failed attempts: an initial build failed after accidental CRLF conversion
of imci.md; LF endings were restored and committed. The corrected full build
at GCC 812636a4542 passed, but its mask fix fails the reproducer checks.

All eight original ICEs were reproduced with tools/s6_10_checks.py --red.
The initial vect_ice_check invocation lacked tree-vect.h include paths for
the two double-reduction cases; the ticket checker supplies those paths.

T0 and T1 passed. T2 stopped with an infrastructure failure: permission denied
writing _shared/S5-21/short-vector-O2-0.mic. No workaround or rerun was attempted.
Torture measured all 8,012 cases. Classifications are unchanged from the tracked
baseline at O0/O2/O2-g/O3: 1967/1968/1968/1968 passes, 34/33/33/33 compiler
errors, and two user inline-asm rejections at each level. All other classes
are zero. Assembly differences were not measured.

Shared i386 changes total +15/-10 lines in eight hunks, in separate commits:
the generalized ffs split in i386.md and KNC hard-register guard in i386.cc.
The KNC-only imci.md changes total +4/-2 lines in two hunks.

No native card execution was performed. Linted card binaries are
_shared/S6-10/s4_masks-o2v.mic and s4_masks-o3.mic. The six affected upstream
run binaries could not build. No native acceptance is claimed.

Logs under .work/_state/logs:

- s6_10_reproduce-20261106-092937.log (initial missing-header issue)
- s6_10_red-20261106-093008.log (all eight expected ICEs)
- s6_10_build-20261106-093203.log (failed CRLF build)
- s6_10_build-20261106-093638.log (successful corrected build)
- s6_10_cases-20261106-101433.log
- s6_10_tiers-20261106-101433.log
- s6_10_torture-20261106-101433.log

Individual diagnostics, tiers.txt, and torture-summary.txt are under
.work/_shared/S6-10. The successful-build stamp remains current.
