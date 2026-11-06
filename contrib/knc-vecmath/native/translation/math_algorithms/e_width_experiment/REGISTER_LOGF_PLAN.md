# Gather-free logf table selection declaration

This new candidate replaces only the two indexed16-entry binary64 table loads
in preserved e_logf.c with four fixed64B uint32 register-shuffle vectors. The
original Arm coefficients, FP expression order, special paths, subnormal
normalization and neutral-input mask policy are preserved verbatim. The older
source and evidence remain unchanged. No scalar-log delegation is introduced.

Varying factor: selected low/high DWORD halves instead of indexed memory loads.
Expected signature: bit-identical selection of all32 original binary64 values,
zero gathers in one changed-source Linux-target emission, then fresh sampled
host accuracy<=1ULP with exact specials/flags/merge. Metrics:32 payload matches,
16x16 lane/index assignments, actual gather/unsupported-form census, active and
inactive mismatch counts/ULP histogram. Falsifier:any altered table bit, gather,
source/command drift, compiler failure or numeric/state mismatch. Bound one
source implementation, one exact table-identity control, one Linux-target
emission and a fresh host assay of this changed source; stop on first failure.
No old algorithm/output, compiler report, numerical output or card replay.

This is an unqualified source candidate. It is not a target export or G5 pass.
Target ISA forms, actual ELF/call/static binding and >=1e6 target input lanes
against independent reference remain later root-owned work. Phase3 starts40/39
and G51/36; existing qualified receipts and scientific source bytes stay fixed.
