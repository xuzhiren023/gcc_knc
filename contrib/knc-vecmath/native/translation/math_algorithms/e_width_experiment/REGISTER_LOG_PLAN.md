# Gather-free DP8 log source declaration

Varying factor: replace only four indexed N128 binary64 data-field loads with
sixteen fixed8-entry register-shuffle shards per field. Preserve Arm invc/logc/
chi/clo payloads, near-one polynomial, compensated far reduction, subnormal
normalization, exceptional paths and FP expression order verbatim. Existing
source and results are immutable. Use no scalar-log delegation and no gather.

Expected signature: all512 original binary64 payloads reconstructed exactly
across128 rotations x8 lanes x4fields; one changed-source Linux-target emission
has zero gathers. Metrics:4096 actual parsed-header lane/field selections,
actual instruction/dependency census, later fresh host and target ULP/flags.
Falsifier: changed table bit, indexed lookup/gather, compiler/source drift or
numerical/state mismatch. Bound one new source/header, one table control, one
Linux-target emission, then one fresh host assay if its independent references
are available. Stop on first failure and retain it; no old compiler/algorithm/
output replay. No card job or G5 credit follows from these source checks.

Phase3 currently41registered/40verified with actual card lane tests; G51/36.
Whole translated exp/logf/log and runtime/IP-1 remain unqualified. This source
preparation is independent Windows work while root serializes native batches.
