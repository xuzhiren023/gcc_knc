# Exact register integer and predicate source experiment

Declared before execution, 2026-10-23. Source-only; no compiler, translation,
local ELF build, card contact, native preparation or verified rule is authorized
by this plan. Existing family40 and signed-extension sources stay unchanged.

The varying factor is one fixed lowering for each retained register-only
integer/predicate occurrence in DP exp source374ab37e, using its already retained
family40 report9b77a3bb. This is two disjoint domains, not a broader109-site
qualification domain:

| Domain | Exact sites | Families | Epochs | Planned raw bytes including32B header |
|---|---:|---|---:|---:|
| materialize |50|20 VPCMPEQD,28 self-VPTEST,2 VMOVDQA|256|166502432|
| selection |59|15 VPCMPD EQ,14 TERNLOG254,9 VPSRLVD,8 VPAND,5 VPADDQ,8 full-ZMM logical/immediate shifts|256|196472864|

Each site covers all four RC modes and64 prior sticky states. Each domain stays
below192 MiB per variant. Four source-memory sites, signed20, old49, scalar
BTR/CMOVA, lane extraction/alignment and masked memory remain outside these
literal domains. No unobserved width, tuple, mask, immediate or alias is admitted.

Expected signature: the candidate preserves the source result, upper-zero,
all ordinary vector/GPR/mask registers, flags and VCSR, source page and private
scratch except explicitly predicted physical effects. The independent oracle
uses source integer equations, a literal TERNLOG truth table, exact64-bit sums
and the VPTEST flag definition. It imports no candidate/interpreter/native gate.
Full6464B target states must agree with separately written physical equations
for candidate, wrong-operation and wrong-width programs.

Materialization uses one own readonly64B-aligned all-ones constant. Equality
temporarily uses K7 and restores255; R11 finishes255. VPTEST alone saves original
RAX/R11 in body-RSP[-8,-1]/[-16,-9], restores both registers, and leaves those
two original values in independently predicted scratch cells. VPTEST uses
VTESTMD, scalar SETE and SAHF to set CF=1, ZF from the low256 source, and clears
OF/SF/AF/PF. Body RSP may have any of eight8B-aligned modulo64 residues; caller
RSP is unchanged. No64B frame, source-memory/fault-suppression premise or page
access is introduced. Selection uses only Z29-31/R11 scratch as reported per
literal recipe, restores any temporary K7, and does not write private memory.

Metrics/falsifier: exact site/literal counts, per-domain candidate source
mismatches, independent full-state mismatches for every variant, negative
semantic mismatches, RC/sticky/residue coverage and rejected outside-domain
forms. Any candidate mismatch, missing site, escaped premise or independent
physical disagreement fails the experiment. Negative programs must diverge in
each domain and each source family on directed inputs; finite sampling is not
native ISA proof.

Bound: exactly three new source-control groups: retained scope and rejection;
the50-site full-state grid; the59-site full-state grid including directed
truth/flags/carry/width controls. One fresh bounded execution only. Preserve a
failed attempt and its consumed source before any repair; rerun only affected
new groups. Stop before native preparation. Native syntax, actual ELF/static
bindings, complete raw target comparisons and source-specific admission remain
future prerequisites owned by the root.
